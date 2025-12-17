## Open questions — worker-chart-export (TDA)

Эти вопросы нужно закрыть, чтобы передать бандл в разработку и не словить “дыр” в контракте.

### 1) Внешний Chart API — **закрыто**
- Договорённости по провайдеру, endpoint’у, аутентификации, формату запроса/ответа, rate-limit’ам, источнику данных (OHLCV vs TradingView) и классификации ошибок Chart API зафиксированы в:
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **12) Внешний Chart API (Chart-IMG, API v2)**;
  - `docs-worker-chart-export/checklists/worker_chart_export.md` (пункты про External Chart API и Performance / limits);
  - `docs-worker-chart-export/spec/handoff_checklist.md`, раздел **5) Внешний Chart API (Chart-IMG)**.

Дальнейшие изменения по API считаются эволюцией контракта, а не “дырой” в спецификации.

### 2) Семантика `chartTemplateId` — **частично закрыто**
- Принято, что:
  - runtime source of truth для шаблонов — коллекция в Firestore (`chart_templates/{chartTemplateId}`) с JSON-документами вида `{ id, description, request }`;
  - репозиторий `docs-worker-chart-export/chart-templates/*.json` содержит те же структуры и служит эталонным набором/seed’ом;
  - `description` интерпретируется как человекочитаемый kind и в MVP попадает в `ChartsOutputsManifest.items[*].kind`;
  - один `chartTemplateId` в рамках одного запуска шага даёт не более **одного** изображения.
- Детали коллекции и процесса синхронизации репо → Firestore остаются в зоне реализации и могут быть уточнены отдельно.
- См.:
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **13) Семантика chartTemplateId и репозиторий шаблонов**;
  - `docs-worker-chart-export/chart-templates/README.md`;
  - `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json` (описание поля `kind`).

### 3) `CHART_EXPORT.inputs.requests[]` — **закрыто**
- Для MVP:
  - `requests[]` — список объектов `{ chartTemplateId }`, где каждый элемент соответствует не более чем **одной** картинке в `ChartsOutputsManifest.items[]`;
  - поле `kind` в `items[*]` заполняется из шаблона (`description` соответствующего `chartTemplateId`);
  - один и тот же `chartTemplateId` в рамках одного запуска шага не порождает несколько PNG с разными kind’ами.
- См.:
  - `docs-worker-chart-export/contracts/flow_run.schema.json`, описание `chartExportStep.inputs.requests`;
  - `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`, описание `chartItem.kind`;
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **13.3 Отражение шаблонов в manifest и minImages**.

### 4) Идемпотентность PNG — **закрыто**
- Допустимо и ожидаемо, что при retry (повторном выполнении шага для того же `runId+stepId`) воркер создаёт **новые** PNG с другим `generatedAt` в имени, не переиспользуя старые файлы.
- Воркер не обязан чистить директорию от старых PNG; инвариант идемпотентности обеспечивается тем, что:
  - итоговое состояние для `runId+stepId` определяется **только** последним `ChartsOutputsManifest`;
  - downstream-системы обязаны ориентироваться на `manifest.items[]`, а не на “все PNG в runs/<runId>/charts/...`.
- См.:
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **9) Retries и идемпотентность**;
  - `docs-worker-chart-export/contracts/charts_images_naming.md`.

### 5) Порог `minImages` — **закрыто**
- `minImages` задаётся триггером/создателем `flow_run` (в payload шага) и копируется воркером в manifest без изменений.
- Семантика:
  - шаг `CHART_EXPORT` считается успешным, если `len(ChartsOutputsManifest.items) >= minImages`, где каждый `items[*]` соответствует одному успешному `chartTemplateId` из `inputs.requests[]`;
  - пример: при 5 шаблонах и `minImages = 2` любые два успешно сгенерированных изображения достаточно для статуса `SUCCEEDED`.
- См.:
  - `docs-worker-chart-export/contracts/flow_run.schema.json`, поле `chartExportStep.inputs.minImages`;
  - `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`, поле `minImages`;
  - `docs-worker-chart-export/spec/implementation_contract.md`, разделы **6) Формирование ChartsOutputsManifest** и **13.3 Отражение шаблонов в manifest и minImages**;
  - `docs-general/contracts/orchestration_rules.md`, раздел про правило успеха `CHART_EXPORT`.

### 6) GCS signed URLs — **закрыто**
- Для MVP:
  - GCS bucket с PNG и manifest открыт на чтение (public read) без дополнительной аутентификации;
  - воркер не генерирует signed URLs ни для PNG, ни для manifest; поля `signed_url`/`expires_at` в схемах зарезервированы на будущее.
- Клиентский слой (UI/прокси) может строить публичные HTTPS-ссылки по `gs://` URI, используя стандартный формат `https://storage.googleapis.com/<bucket>/<objectPath>`.
- См.:
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **12.6 GCS доступ к PNG и manifest (public read, без signed URL)**;
  - `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json` и `docs-worker-chart-export/contracts/flow_run.schema.json` (поля `signed_url`/`expires_at` для совместимости).

### 7) Локальный CLI-режим и mock Chart API — **закрыто**
- Для локального режима предусмотрена CLI-обёртка вокруг воркера `worker-chart-export` (подкоманда `run-local`), которая:
  - принимает путь к локальному JSON в формате `flow_run.schema.json` (`--flow-run-path=...`);
  - по желанию принимает `--step-id=...` для явного выбора шага `CHART_EXPORT`;
  - поддерживает флаги `--charts-api-mode=real|mock|record`, `--charts-bucket=...`, `--accounts-config-path=...`, `--output-summary=none|text|json`;
  - выполняет ту же логику, что и прод-воркер (валидация, вызовы Chart API или mock/record, запись PNG и manifest) с теми же путями в GCS.
- Режим работы внешнего Chart API управляется через `CHARTS_API_MODE` и CLI-флаг `--charts-api-mode`:
  - `real` — реальные HTTP-запросы к Chart-IMG (прод-режим);
  - `mock` — полностью отключённые HTTP-запросы и использование фикстур по детерминированному ключу;
  - `record` — режим record/replay: при отсутствии фикстуры выполняется реальный вызов и ответ сохраняется как новая фикстура.
- Фикстуры для mock/record хранятся **в репозитории**:
  - корень: `docs-worker-chart-export/fixtures/chart-api/`, для CHART-IMG Snapshot v2 Advanced Chart — `fixtures/chart-api/chart-img/advanced-chart-v2/`;
  - ключ построен по провайдеру, endpoint’у, `symbol`, `timeframe`, `chartTemplateId`;
  - успешные ответы — PNG-файлы вида `BINANCE_BTCUSDT__1h__price_psar_adi_v1.png`, ошибочные — JSON-файлы вида `...__429_LIMIT_EXCEEDED.json` и т.п.
- Минимальный набор покрытия mock:
  - для всех `chartTemplateId`, используемых в MVP/эталонных сценариях (sample `flow_run`, автотесты, e2e), есть хотя бы один успешный PNG-fixture и по возможности типовые error-fixture;
  - при `CHARTS_API_MODE=mock` отсутствие нужной фикстуры даёт код ошибки шага `CHART_API_MOCK_MISSING` без реального HTTP-вызова.
- См.:
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **12) Локальный режим отладки и mock Chart API**;
  - `docs-worker-chart-export/spec/implementation_contract.md`, раздел **8) Ошибки (Error model)** (код `CHART_API_MOCK_MISSING`).

### 8) Учёт вызовов внешнего Chart API и управление аккаунтами — **закрыто**
- Как считать и логировать количество **успешных** и **неуспешных** вызовов внешнего Chart API:
  - на уровне одного запуска шага (`runId+stepId`);
  - агрегировано по времени (например, per minute/hour/day) для мониторинга.
- Как учитывать ошибки (какие статусы/коды считаем ошибкой для метрик) и где хранить эти метрики (Cloud Monitoring, отдельный лог, Prometheus и т.п.).
- Как организовано «жонглирование аккаунтами»:
  - по каким правилам выбирается аккаунт/ключ для очередного вызова (round-robin, по остаткам лимита, приоритизация платных/фри-tier и т.п.);
  - как воркер узнаёт об исчерпании лимита по конкретному аккаунту и переключается на другой;
  - нужно ли где-то централизованно хранить состояние по аккаунтам (лимиты, блокировки, timeouts до следующего использования).


