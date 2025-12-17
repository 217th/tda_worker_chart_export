# Схема `flow_runs/{runId}` и оркестрация (prototype)

## Зафиксированные решения

- **Один запуск = один символ**.
- **Оркестрация по Firestore update `flow_run`** (явные переходы по статусам).
- **Хранение шагов внутри одного документа** `flow_runs/{runId}` (без подколлекции `steps` на старте).
- **История попыток не нужна**: храним только *последний статус и последнюю ошибку*, подробности — в логах.
- **Артефакты/крупные списки** (например, много PNG ссылок) — в **GCS**; в `flow_run` хранить только **ссылку на manifest**.
- **`runId` = docId** в Firestore и он **человекочитаемый**.

## Канонический документ `flow_runs/{runId}` (рекомендованная структура)

### Верхний уровень

- `schemaVersion: number` — версия схемы документа.
- `runId: string` — **docId** в Firestore в формате:
  - `YYYYMMDD-HHmmss_<symbolSlug>_<shortSuffix>`
  - `<symbolSlug>`: например `BTC-USDT`
  - `<shortSuffix>`: 3–6 символов (защита от коллизий)
- `flowKey: string` — человекочитаемый ключ флоу **с версией суффиксом**, например:
  - `scheduled_month_week_report_v1`
  - `user_multi_tf_report_v1`
  - `recommendation_with_account_v1`
- `status: "PENDING"|"RUNNING"|"SUCCEEDED"|"FAILED"|"CANCELLED"`.
- `createdAt`, `updatedAt?`, `finishedAt?`: RFC3339 timestamps.
- `trigger`: объект источника запуска.
- `scope`: параметры запуска.
- `progress?`: агрегированные счётчики и `currentStepId` (опционально).
- `steps`: map шагов по `stepId`.
- `error?`: последняя ошибка на уровне всего run (если `status=FAILED`).

### `trigger`

- `type: "SCHEDULER"|"USER"|"SYSTEM"|"DEBUG_HTTP"`
- `source: string` (job name / api endpoint)

### `scope`

Обязательно:

- `symbol: string`

Опционально (по мере роста прототипа, чтобы не ломать схему):

- любые дополнительные параметры флоу как `scope.*`

## Модель шага внутри `steps[stepId]`

Каждый шаг — объект:

- `stepType: "OHLCV_EXPORT"|"CHART_EXPORT"|"LLM_REPORT"|"LLM_RECOMMENDATION"|"ACCOUNT_EXPORT"|"INDICATORS_ON_DEMAND"|"NEWS_EXPORT"`
- `status: "PENDING"|"READY"|"RUNNING"|"SUCCEEDED"|"FAILED"|"SKIPPED"|"CANCELLED"`
- `timeframe?: string`
- `createdAt`, `finishedAt?`
- `dependsOn: string[]` — список `stepId` зависимостей (учёт Flow 1–7 и динамики Flow 5)
- `inputs`: ссылки/идентификаторы (GCS URIs, reportIds, templateIds, promptId/modelId)
- `outputs`: ссылки на результаты (GCS URIs, manifest URI, reportId/recommendationId)
- `error?: { code: string, message: string, details?: object }`

## Соглашение по `stepId` (детерминированность)

Рекомендация: `stepType:timeframe:variant` где `variant` включает template/prompt/model при необходимости.
Примеры:

- `ohlcv_export:1M`
- `charts:1M:ctpl_default_v1`
- `llm_report:1M:prompt_month_v1:model_gpt_4o_mini`
- `llm_report:1w:prompt_week_v1:model_gpt_4o_mini`
- `llm_reco:prompt_reco_v1:model_gpt_4o_mini`
- `account_export`
- `news_export`
- `indicators_on_demand:1d:req_01J...` (для Flow 5, динамически)

## Где хранить результаты

### GCS (каноническое содержимое)

- OHLCV JSON, PNG графики, manifests, LLM отчёты/рекомендации (как файлы).
- В `flow_run` хранить:
  - `gcs_uri`
  - `signed_url` + `expires_at` (если нужно делиться ссылкой наружу)
  - для множественных файлов: `outputsManifestGcsUri`

### Firestore (индекс метаданных отчётов/рекомендаций)

Чтобы учесть будущую фильтрацию/ревизию без миграций:

- Отдельные коллекции **в будущем** (не обязательно сразу реализовывать):
  - `reports/{reportId}`: метаданные + `gcsUri`
  - `recommendations/{recoId}`: метаданные + `gcsUri`
- В `flow_run` тогда хранить `reportId/recommendationId` + `gcsUri`.

## Оркестрация по Firestore update (логика переходов)

- Функция `advance_flow` (Firestore trigger) реагирует на изменения `flow_runs/{runId}` и:
  - вычисляет какие шаги стали выполнимыми (`dependsOn` все `SUCCEEDED`)
  - переводит их `PENDING -> READY`
  - при ошибке шага может помечать run как `FAILED` или ставить `SKIPPED`/ветвление по политике.
- Функции-воркеры (`worker_ohlcv_export`, `worker_charts`, `worker_llm_report`, …) реагируют на `steps.*.status=READY`, ставят `RUNNING`, делают работу, пишут артефакты в GCS, затем `SUCCEEDED/FAILED`.

## Почему это учитывает Flow 1–7 без переделок

- Повторы по таймфреймам — просто новые `stepId` с разными `timeframe`.
- Зависимость 1w отчёта от 1M отчёта — `dependsOn`.
- Flow 3 агрегирует отчёты — `inputs.reportRefs[]`.
- Flow 4 добавляет `account_export` как зависимость рекомендации.
- Flow 5 добавляет динамические `indicators_on_demand:*` шаги и включает их в зависимости LLM.
- Flow 6 добавляет `news_export` шаги.
- Flow 7 — повторяющиеся `flow_run` по расписанию с фильтром по `recommendation.signal_strength`.

## Следующие шаги спецификации контрактов

- (DONE) Зафиксировать JSON Schema для `flow_runs/{runId}`.
  - results:
    - @docs\contracts\schemas\flow_run.schema.json
    - @docs\contracts\examples\flow_run.example.json
- (DONE) Зафиксировать JSON Schema для manifest’ов GCS:
  - `charts_manifest.json` (список png + индикаторы/параметры)
  - `ohlcv_export.json` (временной ряд)
  - `llm_report.json` / `llm_recommendation.json`
- (DONE) Определить минимальные OpenAPI эндпоинты только для debug/manual:
  - `POST /runs:trigger` (создать `flow_run`)
  - `GET /runs/{runId}` (прочитать)
- (DONE) Зафиксировать правила именования изображений с графиками