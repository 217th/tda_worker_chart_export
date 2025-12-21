## worker-chart-export — Implementation Contract (TDA)

Этот документ фиксирует **точную спецификацию поведения** воркера `worker-chart-export` для MVP.

### Source of truth (что использовать)
- `docs-worker-chart-export/contracts/flow_run.schema.json`
- `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`
- `docs-worker-chart-export/contracts/charts_images_naming.md`
- Оркестрационные правила (общие): `docs-general/contracts/orchestration_rules.md`

---

## 1) Назначение
`worker-chart-export` отвечает за выполнение шагов `CHART_EXPORT`:
- берёт в работу только шаги со статусом `READY`
- генерирует PNG артефакты (через внешний Chart API)
- пишет `ChartsOutputsManifest` в GCS
- обновляет `flow_runs/{runId}.steps[stepId]` до `SUCCEEDED` или `FAILED`

---

## 2) Trigger и фильтрация событий
Воркер вызывается Firestore update event’ом на документ `flow_runs/{runId}`.

### 2.1 Быстрый фильтр (обязателен)
При получении события воркер обязан быстро определить: есть ли в документе хотя бы один шаг `steps[*]`, удовлетворяющий:
- `stepType == "CHART_EXPORT"`
- `status == "READY"`

Если нет — **no-op** (только INFO лог и выход 200/OK).

### 2.2 Выбор шага (если READY шагов несколько)
Для MVP выбираем простое правило (чётко зафиксировать в реализации):
- **Rule**: брать первый `READY` шаг в детерминированном порядке (например сортировка по `stepId` по возрастанию).

---

## 3) Захват шага и статусы (атомарность)
### 3.1 Claim (обязателен)
Перед выполнением работы воркер обязан атомарно перевести шаг:
- `READY -> RUNNING`

**Требования**:
- выполнять перевод в транзакции (Firestore transaction)
- если шаг уже не `READY`, воркер **не делает работу** (no-op)

### 3.2 Завершение
После выполнения:
- `RUNNING -> SUCCEEDED` (если успех по критериям ниже)
- `RUNNING -> FAILED` (если успех-критерий не выполнен или произошла ошибка)

Воркер **никогда не пишет `READY`** (это обязанность `advance-flow`).

---

## 4) Входные данные шага (flow_run)
Воркер читает:
- `runId` (из документа)
- `scope.symbol` (базовый символ, например `BTCUSDT`)
- `steps[stepId].timeframe` (строка)
- `steps[stepId].inputs.minImages` (integer)
- `steps[stepId].inputs.requests[]` где каждый элемент имеет `chartTemplateId`

### 4.1 Валидация входов (обязательна)
Если входы некорректны/неполны:
- завершить шаг `FAILED`
- заполнить `steps[stepId].error.code = "VALIDATION_FAILED"`
Минимальные проверки:
- `scope.symbol` должен быть в базовом формате без слэша (например `BTCUSDT`);
- у каждого `chartTemplateId` должна быть доступна валидная запись шаблона с `chartImgSymbolTemplate`.

---

## 5) Выходы: артефакты в GCS
### 5.1 PNG paths
Для каждого успешно полученного изображения воркер пишет PNG в директорию:
- `charts/<runId>/<stepId>/`

Имя файла PNG (см. `charts_images_naming.md`):
- `<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`

### 5.2 Manifest path
Воркер пишет один `ChartsOutputsManifest` JSON в:
- `charts/<runId>/<stepId>/manifest.json`

**Важно (привязка к шагу)**:
- Путь к manifest зависит только от `runId` и `stepId`, а **не** от конкретного `chartTemplateId`.
- Все запрошенные шаблоны и результаты отражаются внутри manifest (`requested[]`, `items[]`, `failures[]`), а не в его пути.
- Это упрощает случаи, когда один шаг `CHART_EXPORT` содержит несколько разных `chartTemplateId`, и избавляет от выбора “главного” шаблона на уровне директорий.

---

## 6) Формирование ChartsOutputsManifest
Воркер обязан сформировать manifest, соответствующий `charts_outputs_manifest.schema.json`:
- `schemaVersion`: integer >= 1
- `runId`, `stepId`, `createdAt`, `symbol` (копия `scope.symbol`), `timeframe`
- `minImages` (копия inputs.minImages)
- `requested[]` (копия inputs.requests[])
- `items[]`: для каждого успешного PNG:
  - `chartTemplateId`, `kind`, `generatedAt` (RFC3339 UTC), `png_gcs_uri` (формат URI: `gs://...`)
  - optional: `label`, `signed_url`, `expires_at`, `meta`
- `failures[]`: для каждого неуспеха:
  - `request` (как в requested)
  - `error.code`, `error.message`, optional `error.details`

---

## 7) Критерий успеха шага (статус SUCCEEDED/FAILED)
Источник: `docs-general/contracts/orchestration_rules.md`

### 7.1 Success rule
Шаг `CHART_EXPORT` считается `SUCCEEDED`, если:
- `len(manifest.items) >= inputs.minImages`

Иначе шаг `FAILED`.

### 7.2 Обновление flow_run.outputs
При `SUCCEEDED`:
- `steps[stepId].outputs.outputsManifestGcsUri` **обязателен** и указывает на manifest в GCS.
При `FAILED`:
- `outputs.outputsManifestGcsUri` **может** быть записан (для диагностики), если manifest сформирован и сохранён.

---

## 8) Ошибки (Error model)
Минимальные `error.code` для воркера:
- `VALIDATION_FAILED`
- `CHART_API_FAILED`
- `CHART_API_LIMIT_EXCEEDED`
- `CHART_API_MOCK_MISSING`
- `GCS_WRITE_FAILED`
- `MANIFEST_WRITE_FAILED`

Требование:
- `error.message` всегда человекочитаемое
- `error.details` не содержит секретов (keys/tokens/PII)

- `CHART_API_FAILED` используется для ошибок внешнего Chart API, **не связанных с лимитами** (HTTP 4xx/5xx, см. 13.5), когда тот же запрос с теми же входами и аккаунтом не должен автоматически ретраиться.
- `CHART_API_LIMIT_EXCEEDED` фиксирует ситуацию, когда для логического запроса к Chart-IMG **невозможно выбрать аккаунт из-за лимитов**:
  - либо после попыток с доступными аккаунтами воркер получает только ответы 429 / `"Limit Exceeded"` от провайдера (см. 13.4–13.5);
  - либо воркер детерминированно видит по `chart_img_accounts_usage/*`, что у всех доступных аккаунтов `usageToday >= dailyLimit`, и **не делает реальный HTTP‑запрос**, сразу помечая запрос как неуспешный;
  - при этом воркер продолжает оценивать шаг по общему правилу `minImages` (см. 7.1) и записывает отказ в `failures[]` manifest’а.
- `CHART_API_MOCK_MISSING` используется для локального/mock‑режима (см. 12.2):
  - означает, что при `CHARTS_API_MODE=mock` для данного запроса к Chart API не найдена ни успешная, ни error‑фикстура;
  - в этом случае воркер **не делает** реальный HTTP‑запрос к внешнему API и записывает неуспех в `failures[]` manifest’а;
  - такой код может использоваться в тестах и локальной отладке для контроля полноты покрытия фикстурами и не должен появляться в прод‑запусках при `CHARTS_API_MODE=real`.

---

## 9) Retries и идемпотентность
Event trigger может быть at-least-once.

Требования:
- воркер обязан корректно работать при повторном событии:
  - повторный claim должен быть безопасен (если шаг уже не READY — no-op)
  - manifest должен быть детерминированным по `runId+stepId` (перезапись допускается)
  - downstream должен ориентироваться на `manifest.items[]`, а не на “все PNG в директории”
  - при повторном успешном выполнении воркер может создать **новые PNG-файлы** (с новым `generatedAt` в имени) и обновить manifest; старые PNG в директории считаются “старыми версиями” и игнорируются downstream.
    - Требование MVP: воркер **не обязан** удалять/очищать старые PNG при retry.
    - Критерий идемпотентности: для фиксированных `runId+stepId` итоговое состояние определяется **только** содержимым последнего `ChartsOutputsManifest`, а не набором файлов в `charts/<runId>/<stepId>/...`.

---

## 10) Логирование (обязательный минимум)
Логи должны следовать конвенции из `docs-gcp/runbook/prod_runbook_gcp.md` (раздел Logging).

Минимальные события:
- received event (raw CloudEvent; may not include runId/flowKey)
- parsed event (runId, flowKey) — emitted after flow_run parsing
- claim succeeded/failed
- chart api call started/finished (+ duration)
- manifest written (+ gcs uri)
- step completed (SUCCEEDED/FAILED + error.code)
- global chart-img accounts exhaustion: структурированное событие с `error.code = "CHART_API_LIMIT_EXCEEDED"`, перечнем исчерпанных аккаунтов (`exhaustedAccounts[]`/`accountIds[]`), `service`, `env`, `runId`, `stepId` и `severity` уровня не ниже `ERROR` (предназначено для log-based метрик и алёртов)

---

## 11) Конфиги и секреты воркера

### 11.1 Аккаунты внешнего Chart API (секреты)

- Source of truth для **самих API-ключей** Chart-IMG — **Secret Manager**:
  - один секрет `chart-img-accounts` с JSON-массивом объектов вида:
    ```json
    [
      { "id": "acc1", "apiKey": "XXX" },
      { "id": "acc2", "apiKey": "YYY" }
    ]
    ```
  - `id`: стабильный идентификатор аккаунта (используется в логах/метриках и в документах Firestore);
  - `apiKey`: значение для заголовка `x-api-key`.
- Воркер читает этот секрет как **env‑переменную** `CHART_IMG_ACCOUNTS_JSON` (через интеграцию Cloud Run ↔ Secret Manager) и парсит её на старте.
- Локальный режим:
  - допускается файл `chart-img.accounts.local.json` с тем же форматом, который CLI/обёртка читает при запуске и пробрасывает содержимое в env `CHART_IMG_ACCOUNTS_JSON`;
  - таким образом, и в проде, и локально воркер работает с одним и тем же JSON‑форматом.
- Безопасность:
  - значение `apiKey` **никогда не логируется** и не записывается в manifest/flow_run;
  - в логах и метриках используется только `id` (или маскированный suffix ключа).

### 11.2 Прочие конфиги
- Дополнительные конфиги (например, имя GCS bucket’а для PNG/manifest, дефолтный `timezone`) также могут приходить через env:
  - пример: `CHARTS_BUCKET`, `CHARTS_DEFAULT_TIMEZONE`.
- Точное именование и формат этих переменных задаётся в README/infra‑репозитории и не жёстко фиксируется в этом контракте.

---

## 12) Локальный режим отладки и mock Chart API

### 12.1 CLI-запуск воркера
- Должна быть CLI-обёртка вокруг воркера `worker-chart-export`, которая:
  - умеет запускаться в локальном режиме как подкоманда, например `worker-chart-export run-local ...`;
  - принимает путь к локальному JSON в формате `flow_run.schema.json` (флаг `--flow-run-path=./flow_run.sample.json`);
  - по желанию принимает `--step-id=<stepId>`:
    - если флаг задан — выбирает конкретный шаг `steps[stepId]` и проверяет `stepType == "CHART_EXPORT"`;
    - если не задан — выбирает первый шаг `CHART_EXPORT` со статусом `READY` по тем же правилам, что и прод‑воркер;
  - читает указанный файл, формирует `inputs.requests[]` и остальные входы шага так же, как в проде;
  - выполняет **ту же логику**, что и при запуске из Firestore‑события (валидация, выбор аккаунта Chart API, вызов Chart API или mock/record, запись PNG и manifest);
  - пишет PNG и manifest с использованием **той же формулы путей**, что и реальный воркер (GCS bucket конфигурируется отдельно, см. 11.2).

- CLI‑обёртка должна поддерживать как минимум следующие флаги/конфиги:
  - `--flow-run-path=PATH` — путь к локальному `flow_run` (обязателен для локального режима);
  - `--step-id=ID` — явный выбор шага `CHART_EXPORT` (опционален);
  - `--charts-api-mode=real|mock|record`:
    - если флаг задан — он имеет приоритет над env `CHARTS_API_MODE`;
    - если флаг не задан — используется значение env `CHARTS_API_MODE` или дефолт (см. 12.2);
  - `--charts-bucket=gs://...` — переопределение имени GCS bucket’а для PNG/manifest поверх env `CHARTS_BUCKET` (см. 11.2);
  - `--accounts-config-path=./chart-img.accounts.local.json`:
    - CLI читает указанный файл с тем же форматом, что и `CHART_IMG_ACCOUNTS_JSON` (см. 11.1);
    - содержимое файла пробрасывается в env `CHART_IMG_ACCOUNTS_JSON` так, что основная логика воркера не различает прод/локалку;
  - `--output-summary=none|text|json`:
    - `none` — только логи (поведение по умолчанию для прод‑запуска);
    - `text` — в конце локального запуска печатается человекочитаемый summary (например `CHART_EXPORT SUCCEEDED: manifest=gs://.../manifest.json, items=3, failures=1, minImages=2`);
    - `json` — в конце локального запуска печатается один JSON‑объект с итогами (например `status`, `runId`, `stepId`, `outputsManifestGcsUri`, `itemsCount`, `failuresCount`, `chartsApiMode`).

- Требования к логированию в локальном режиме:
  - структура логов (поля `runId`, `stepId`, `chartsApi.*`, коды ошибок и т.п.) должна совпадать с прод‑воркером (см. 9 и 10);
  - при старте локального запуска логируется отдельное событие с пометкой режима (`mode="local"`, `chartsApi.mode`, `flowRunPath`, `stepId`);
  - для каждого логического вызова Chart API (включая mock/record) логируются `chartsApi.mode` и ключ фикстуры (если применимо).

### 12.2 Mock внешнего Chart API
- Режим работы внешнего Chart API переключается конфигом (env/флаг):
  - используется переменная окружения `CHARTS_API_MODE`, допускающая значения:
    - `real` — реальные HTTP‑запросы к Chart API;
    - `mock` — полное отключение внешних HTTP‑запросов и использование фикстур;
    - `record` — гибридный режим record/replay для автогенерации фикстур.
  - при наличии флага CLI `--charts-api-mode` он **имеет приоритет** над значением env `CHARTS_API_MODE`;
  - дефолты:
    - для Cloud Run/прода режим по умолчанию конфигурируется как `real` (через деплой‑конфиг);
    - для локального CLI допускается дефолт `mock`, если не указано иное.

- В режиме `real`:
  - воркер обращается к настоящему Chart API согласно его контракту (endpoint, auth и т.д., см. 13);
  - поведение полностью соответствует прод‑режиму, без участия фикстур.

- В режиме `mock`:
  - HTTP‑запросы к внешнему API **не посылаются**;
  - вместо этого воркер использует заранее сохранённые тестовые ответы (record/replay) с тем же форматом данных, что и реальный API;
  - контракт `flow_run` и `ChartsOutputsManifest` **полностью сохраняется**, чтобы поведение в отладке соответствовало прод‑режиму;
  - реализация выбирает фикстуру по детерминированному ключу, зависящему как минимум от:
    - провайдера (`chart-img`);
    - endpoint’а (`advanced-chart-v2`);
    - `chartImgSymbol` (TradingView‑символ, вычисляемый из `chartImgSymbolTemplate` и `flow_run.scope.symbol`);
    - `timeframe` (`steps[stepId].timeframe`);
    - `chartTemplateId`;
  - рекомендуемая структура директорий и нейминг фикстур:
    - корень: `docs-worker-chart-export/fixtures/chart-api/`;
    - для CHART‑IMG Snapshot v2 Advanced Chart: `fixtures/chart-api/chart-img/advanced-chart-v2/`;
    - для успешных ответов (`HTTP 200`, PNG): файлы вида  
      `BINANCE_BTCUSDT__1h__price_psar_adi_v1.png`, где:
        - `BINANCE_BTCUSDT` — `chartImgSymbol` с заменой `:` на `_`;
        - `1h` — `timeframe`;
        - `price_psar_adi_v1` — `chartTemplateId`;
    - для ошибочных ответов (JSON‑ошибка): файлы вида  
      `BINANCE_BTCUSDT__1h__price_psar_adi_v1__429_LIMIT_EXCEEDED.json` или  
      `BINANCE_BTCUSDT__1h__price_psar_adi_v1__400_INVALID_SYMBOL.json`, содержащие то, что вернул Chart‑IMG (status/body);
  - если по ключу не найдена ни успешная, ни error‑фикстура:
    - реальные HTTP‑запросы **не выполняются**;
    - соответствующий запрос помечается как неуспешный с `error.code = "CHART_API_MOCK_MISSING"`;
    - в `failures[]` manifest’а записываются параметры запроса и информация о том, какая именно фикстура не найдена;
    - в логах записывается структурированное событие с ключом фикстуры и кодом `CHART_API_MOCK_MISSING`.

- В режиме `record`:
  - если по ключу уже существует PNG/JSON‑фикстура — воркер ведёт себя так же, как в режиме `mock` (replay без HTTP);
  - если фикстуры нет:
    - выполняется реальный HTTP‑запрос к Chart‑IMG;
    - ответ сохраняется в соответствующий файл в каталоге фикстур:
      - при успехе — PNG‑файл по правилу для успешных ответов;
      - при ошибке — JSON‑файл по правилу для error‑фикстур;
    - далее текущий запуск обрабатывает ответ так же, как в режиме `real`;
  - режим `record` предназначен в первую очередь для локальной разработки и наполнения набора фикстур.

- Минимальные требования к набору фикстур:
  - для всех `chartTemplateId`, фигурирующих:
    - в эталонных шаблонах `docs-worker-chart-export/chart-templates/*.json`, используемых в MVP‑сценариях;
    - в sample‑`flow_run`, автотестах и e2e‑сценариях, которые должны работать в режиме `mock`;
  - должен существовать хотя бы один успешный PNG‑fixture (для фиксированной пары `chartImgSymbol`+`timeframe`, например `BINANCE:BTCUSDT` + `1h`);
  - по возможности должны существовать 1‑2 типовых error‑фикстуры (например, `429_LIMIT_EXCEEDED`, `500_SOMETHING_WENT_WRONG`) для проверки путей с `failures[]` и кодом `CHART_API_FAILED`;
  - CI‑сценарии, использующие `CHARTS_API_MODE=mock`, не должны зависеть от реального Chart API и опираться только на зафиксированный в репозитории набор фикстур.

---

## 13) Внешний Chart API (Chart-IMG, API v2)

Этот раздел фиксирует ответы на вопрос №1 из `questions/open_questions.md` для MVP.

### 13.1 Провайдер и endpoint

- Внешний сервис: **CHART-IMG** ([docs](https://doc.chart-img.com/#base-api-endpoint)).
- Базовый URL: `https://api.chart-img.com`.
- Для генерации изображений используем endpoint **TradingView Snapshot v2 — Advanced Chart** ([docs](https://doc.chart-img.com/#tradingview-snapshot-v2)):
  - HTTP method: `POST`
  - Path: `/v2/tradingview/advanced-chart`
  - Полный URL: `https://api.chart-img.com/v2/tradingview/advanced-chart`

### 13.2 Аутентификация и аккаунты

- Аутентификация API v2 — через заголовок `x-api-key: <API_KEY>` ([docs](https://doc.chart-img.com/#authentication)).
- Воркер должен уметь работать с **несколькими API-ключами** (аккаунтами Chart-IMG), которые приходят из конфига/секрета (например, список ключей в env или Secret Manager).
- При каждом запросе воркер:
  - выбирает один из аккаунтов согласно внутренней стратегии (см. 12.4);
  - добавляет в HTTP-запрос заголовок `x-api-key` с ключом выбранного аккаунта;
  - логирует идентификатор аккаунта в structured log (например, `chartsApi.accountId` или безопасный suffix ключа).

### 13.3 Формат запроса/ответа и источник данных

- Endpoint Snapshot v2 Advanced Chart использует **JSON-body**, а не query-string, для параметров (`symbol`, `interval`, `width`, `height`, `overrides`, `drawings` и т.д.) — см. раздел TradingView Snapshot v2 в [документации Chart-IMG](https://doc.chart-img.com/#tradingview-snapshot-v2).
- `worker-chart-export`:
  - **не передаёт OHLCV-данные** в Chart API;
  - передаёт TradingView-совместимый `symbol` (например, `BINANCE:BTCUSDT`) и `interval`, а источник котировок остаётся на стороне Chart-IMG/TradingView;
  - остальные параметры (layout, индикаторы, стили, размеры и т.п.) получает из разрешённого `chartTemplateId`.
- Семантика `chartTemplateId` для API-запроса:
  - каждый `chartTemplateId` указывает на JSON-шаблон с полем `request`, который описывает **форму и оформление** графика (theme, style, studies, overrides, drawings и т.п.);
  - шаблон **обязательно** содержит `chartImgSymbolTemplate` (строка, например `BINANCE:{symbol}` или `BYBIT:{symbol}.P`);
  - `chartImgSymbol` вычисляется как `chartImgSymbolTemplate` с подстановкой `{symbol} = flow_run.scope.symbol` (например `BTCUSDT`);
  - `symbol` в запросе = `chartImgSymbol`, а `interval` берётся из `flow_run.steps[stepId].timeframe` и подставляется воркером (не зашивается в шаблон);
  - если `chartImgSymbolTemplate` отсутствует или `flow_run.scope.symbol` невалиден — запрос отмечается `VALIDATION_FAILED`.
- Ответ Chart-IMG v2 для Advanced Chart:
  - при успехе (HTTP 200) — бинарное PNG-изображение;
  - при ошибках (HTTP 4xx/5xx) — JSON с сообщением и/или списком ошибок согласно разделу **Errors / API v2 / v3** в [документации](https://doc.chart-img.com/#base-api-endpoint).

### 13.4 Rate limit и управление несколькими аккаунтами

- Текущее ограничение: **до 44 запросов в сутки на каждый аккаунт** (план Chart-IMG); это значение может меняться и должно рассматриваться как конфигурационный параметр.
- Требования к реализации:
  - воркер должен уметь варьировать аккаунты (API-ключи), а не использовать всегда один и тот же;
  - по каждому аккаунту ведём **независимый** учёт запросов через **логи**:
    - каждое обращение к Chart-IMG логируется как отдельное событие (например, `chartsApi.request`) с полями: `accountId`, `runId`, `stepId`, `symbol` (TradingView `chartImgSymbol`), `timeframe`/`interval`, `chartTemplateId`, `status`, `httpStatus`, `errorCode` (если есть);
    - дальнейшая агрегация до метрик (суточный счётчик запросов на аккаунт, доля ошибок и т.п.) выполняется внешней системой логирования/мониторинга.
  - при получении от Chart-IMG статуса 429 (`Too Many Requests`) или сообщений вида `"Limit Exceeded"` для конкретного ключа:
    - воркер помечает аккаунт как **временно исчерпанный** (в рамках процесса) и больше не использует его до конца текущего окна (best-effort);
    - при наличии других доступных аккаунтов воркер пытается повторить запрос с другим ключом;
  - если после перебора доступных аккаунтов все они исчерпаны, воркер:
    - помечает соответствующие запросы как неуспешные с `error.code = "CHART_API_LIMIT_EXCEEDED"` (см. 8);
    - пишет структурированное лог‑событие об исчерпании всех аккаунтов Chart-IMG (см. 10);
    - продолжает оценку шага по общему правилу `minImages` (см. 7.1).

### 13.5 Классификация ошибок Chart API (retriable / non-retriable)

На основе раздела **Errors / API v2 / v3** в [документации Chart-IMG](https://doc.chart-img.com/#base-api-endpoint):

- **Non-retriable для тех же входных данных и аккаунта**:
  - HTTP 400 / 401 / 403 / 404 / 409 / 422;
  - примеры сообщений: `"Invalid Request"`, `"Forbidden"`, `"Invalid Symbol"`, `"Invalid Interval"`, `"Layout Forbidden"`;
  - для таких ответов воркер не делает автоматический retry с тем же payload и тем же аккаунтом; ошибка отражается:
    - в `failures[]` manifest’а (с `error.code = "CHART_API_FAILED"` и деталями статуса/сообщения),
    - в логах (структурированное поле с `httpStatus`, `message`).
- **Retriable (ограниченное число попыток)**:
  - сетевые ошибки/timeout на уровне HTTP-клиента;
  - HTTP 500 / 504 (например `"Something Went Wrong"`, `"External Request Timeout"`, `"Endpoint request timed out"`);
  - HTTP 429 / `Too Many Requests`:
    - сначала рассматривается как сигнал об исчерпании лимита конкретного аккаунта (см. 12.4),
    - далее, при наличии других аккаунтов, допускается retry с другим ключом.
- Количество попыток на один логический запрос к Chart-IMG:
  - ограничено небольшим числом (например, максимум 3 попытки суммарно по всем аккаунтам) с экспоненциальным backoff;
  - должно укладываться в общий `timeout` шага и ограничения Cloud Run.

В итоге ошибки Chart API попадают в общую модель ошибок шага (раздел 8):
- `error.code = "CHART_API_FAILED"` (или более специфичный `CHART_API_LIMIT_EXCEEDED`);
- `error.details` не содержит секретов (ключей, токенов и т.п.).

### 13.6 GCS доступ к PNG и manifest (public read, без signed URL)

- PNG и `ChartsOutputsManifest` пишутся в GCS bucket с **публичным доступом на чтение** (роль `Storage Object Viewer` для `allUsers` на уровне bucket’а, с включённым uniform bucket-level access по рекомендациям GCS).
- Для CHART_EXPORT воркер:
  - заполняет только поля `png_gcs_uri` в `ChartsOutputsManifest.items[*]` и `outputs.outputsManifestGcsUri` в шаге;
  - **не генерирует** `signed_url` / `expires_at` ни для PNG, ни для манифеста (они зарезервированы на будущее, если политика доступа изменится).
- Клиентские слои (UI/прокси) могут преобразовывать `gs://` URI в HTTPS (`https://storage.googleapis.com/<bucket>/<objectPath>`) без участия воркера.

Подробнее про публичный доступ к объектам GCS см. официальную документацию Google Cloud Storage, например разделы про **making data public** и **uniform bucket-level access** (`https://cloud.google.com/storage/docs/access-control/making-data-public`).

---

## 14) Семантика `chartTemplateId` и репозиторий шаблонов

### 14.1 Где живут шаблоны

- Runtime source of truth для `chartTemplateId` — коллекция в Firestore (например, `chart_templates/{chartTemplateId}`), где:
  - `chartTemplateId` = `id` документа;
  - документ содержит JSON-объект с полями `id`, `description`, `chartImgSymbolTemplate`, `request` (по форме, описанной в `docs-worker-chart-export/chart-templates/README.md`).
- Репозиторий `docs-worker-chart-export/chart-templates/*.json` служит:
  - эталонным набором шаблонов для MVP;
  - исходником/seed’ом для загрузки в Firestore (ручной или автоматизированный импорт).

### 14.2 Что входит в шаблон

- Минимальные поля шаблона:
  - `id`: строка, совпадает с `chartTemplateId` и именем файла/документа;
  - `description`: человекочитаемое описание “вида” изображения; в MVP используется как `kind` в manifest;
  - `chartImgSymbolTemplate`: TradingView‑шаблон символа (например `BINANCE:{symbol}` или `BYBIT:{symbol}.P`);
  - `request`: фрагмент тела запроса к `POST /v2/tradingview/advanced-chart`, описывающий:
    - `height`, `style`, `theme`, `scale`, `timezone` (по необходимости);
    - `studies[]` (индикаторы) и их `input`/`override`;
    - `drawings[]` и связанные `input`/`override`.
- Ограничения MVP:
  - один `chartTemplateId` → **одна картинка** на один запуск шага (нет multiple PNG per template);
  - параметры рынка (`symbol`, `interval`) не зашиваются в `request` шаблона; `symbol` вычисляется через `chartImgSymbolTemplate` + `flow_run.scope.symbol`, `interval` приходит из `flow_run` (см. 12.3).

### 14.3 Отражение шаблонов в manifest и `minImages`

- Для каждого элемента `flow_run.steps[stepId].inputs.requests[*]` с `chartTemplateId = T`:
  - воркер делает не более одного вызова Chart-IMG и, в случае успеха, пишет **один** элемент в `ChartsOutputsManifest.items[]` с:
    - `chartTemplateId = T`;
    - `kind` = `description` шаблона `T` (для MVP);
    - `png_gcs_uri` указывает на конкретный PNG-файл (см. `charts_images_naming.md`);
    - `generatedAt` = время генерации изображения.
- `minImages`:
  - задаётся **триггером**/создателем `flow_run` и копируется воркером в manifest как есть;
  - интерпретация: шаг `CHART_EXPORT` считается `SUCCEEDED`, если `len(manifest.items) >= minImages`, где:
    - каждый `items[i]` соответствует одному успешному шаблону из `inputs.requests[]`;
    - один шаблон не даёт более одной записи в `items[]` за запуск.

### 14.4 Учёт использования аккаунтов (персистентное состояние)

- Для строгого соблюдения дневного лимита запросов по аккаунтам используется **персистентное состояние в Firestore**:
  - коллекция, например, `chart_img_accounts_usage/{accountId}`;
  - документ для каждого аккаунта содержит:
    - `usageToday`: integer — количество запросов за текущий день;
    - `windowStart`: string (RFC3339 date-time, UTC) — начало текущего окна учёта (например, `YYYY-MM-DDT00:00:00Z` для суток);
    - optional: `dailyLimit`: integer — фактический лимит, если хотим переопределить значение из конфига.
- Алгоритм перед использованием аккаунта (упрощённо):
  1. В транзакции Firestore читаем `chart_img_accounts_usage/{accountId}`.
  2. Если `windowStart` отсутствует или относится к прошлому дню (по UTC) — сбрасываем:
     - `windowStart = сегодня 00:00:00Z`;
     - `usageToday = 0`.
  3. Если `usageToday >= dailyLimit` (из секрета или документа) — аккаунт считается исчерпанным, пробуем следующий по приоритету.
  4. Иначе инкрементируем `usageToday` и коммитим транзакцию; только после успешного коммита используем аккаунт для вызова Chart-IMG.
- Обработка 429/`Limit Exceeded`:
  - при получении 429 от Chart-IMG воркер помечает аккаунт как исчерпанный до конца текущего окна:
    - в Firestore можно установить `usageToday = dailyLimit` (или отдельный флаг/поле, если потребуется);
    - далее в рамках текущих суток аккаунт больше не выбирается.
- Глобальное исчерпание всех аккаунтов в окне:
  - если по всем доступным аккаунтам после применения алгоритма выше выполняется `usageToday >= dailyLimit`, воркер **не делает реальные HTTP‑запросы** к Chart-IMG для соответствующих запросов;
  - такие запросы помечаются как неуспешные с `error.code = "CHART_API_LIMIT_EXCEEDED"` (см. 8, 13.4) и попадают в `failures[]` manifest’а;
  - воркер пишет единичное (best-effort) структурированное событие об исчерпании всех аккаунтов (см. 10);
  - допускается использование in‑memory cache этого состояния на короткое время (например, до конца текущего окна или на несколько минут), чтобы снизить нагрузку на Firestore и логи при повторных шагах в период исчерпания лимитов.
- Взаимодействие с Cloud Monitoring:
  - воркер **не использует** Cloud Monitoring API для принятия решений о выборе аккаунта;
  - Cloud Monitoring применяется только для построения дашбордов и алертов на основе логов (log-based metrics).
