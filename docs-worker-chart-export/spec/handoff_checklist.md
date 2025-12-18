## Handoff checklist — worker-chart-export (TDA)

Цель: агент разработки получает этот бандл и может реализовать воркер без “догадок”.

### 1) Scope и зависимости
- [ ] Реализован только `CHART_EXPORT` воркер (никаких других stepType).
- [ ] Приняты и учтены инварианты оркестрации: `READY -> RUNNING -> SUCCEEDED|FAILED`, READY выставляет только `advance-flow`.
- [ ] Конвенция логирования из GCP runbook соблюдается (runId/flowKey/stepId/error.code).

### 2) Контракты и ссылки
- [ ] Чтение `flow_run` соответствует `contracts/flow_run.schema.json`.
- [ ] Запись manifest соответствует `contracts/charts_outputs_manifest.schema.json`.
- [ ] PNG naming соответствует `contracts/charts_images_naming.md`.

### 3) Acceptance criteria (Definition of Done)
- [ ] Воркер корректно находит `CHART_EXPORT` шаги в `READY` и делает claim в транзакции.
- [ ] При отсутствии READY шагов — no-op и корректный INFO лог.
- [ ] На успех:
  - [ ] пишет PNG (>= `minImages`) в GCS
  - [ ] пишет manifest в GCS
  - [ ] обновляет step: `status=SUCCEEDED`, `outputs.outputsManifestGcsUri` задан, `finishedAt` задан
- [ ] На неуспех:
  - [ ] обновляет step: `status=FAILED`, `error.code/message` заданы, `finishedAt` задан
  - [ ] manifest может быть записан для диагностики (опционально)
- [ ] Retry-safe:
  - [ ] повторное событие не приводит к двойному выполнению (claim-only при READY)
  - [ ] downstream опирается на `manifest.items[]`

### 5) Внешний Chart API (Chart-IMG)
- [ ] Используется Chart-IMG API v2, TradingView Snapshot v2 Advanced Chart (`POST https://api.chart-img.com/v2/tradingview/advanced-chart` с JSON-body).
- [ ] Аутентификация реализована через заголовок `x-api-key`, без утечек ключей в логи/артефакты.
- [ ] Воркер не передаёт OHLCV в Chart API, а только `chartImgSymbol`/`interval` (где `chartImgSymbol` вычислен из `chartImgSymbolTemplate` + `scope.symbol`) и параметры из `chartTemplateId`; источник данных — Chart-IMG/TradingView.
- [ ] Поддерживаются несколько API-ключей (аккаунтов), есть стратегия выбора аккаунта и логирование `accountId` для каждого вызова.
- [ ] Ошибки Chart API классифицированы (retriable/non-retriable) и обрабатываются согласно `implementation_contract.md` (включая 429/Limit Exceeded и 5xx/timeout).

### 6) Конфиги, секреты и учёт лимитов
- [ ] Заведён Secret Manager секрет `chart-img-accounts` с JSON-массивом `{ id, apiKey }`, как описано в `implementation_contract.md` (раздел **11.1 Аккаунты внешнего Chart API (секреты)**).
- [ ] Cloud Run/функция получает этот секрет в env `CHART_IMG_ACCOUNTS_JSON`; локальный CLI использует тот же формат (через файл/`.env`).
- [ ] Реализован персистентный учёт использования аккаунтов в Firestore (коллекция `chart_img_accounts/{accountId}` или эквивалент) с полями `priority`, `dailyLimit`, `usageToday`, `windowStart` и логикой сброса окна, как в `implementation_contract.md` (раздел **14.4 Учёт использования аккаунтов**).
- [ ] Воркер не использует Cloud Monitoring API для принятия решений о выборе аккаунта; мониторинг делается через лог‑метрики.

### 4) Тестовые векторы (минимум)
Использовать файлы из `test_vectors/`:
- [ ] `flow_run_ready_chart_step.json` — входной документ содержит READY шаг `CHART_EXPORT`
- [ ] `expected_manifest.json` — пример валидного manifest
- [ ] `expected_flow_run_step_patch.json` — ожидаемые изменения в step при SUCCEEDED


