## MVP Requirements (Flows 1–3) — TDA (Trading Decisions Assistant)

Этот документ — **минимально достаточные требования для разработки MVP**. Он опирается на контракты данных в `docs/contracts/*` и не описывает backlog-компоненты.

### Goals (что делаем)
- **G1**: Запускать и исполнять флоу анализа/рекомендаций для **одного symbol на один run** (один документ `flow_runs/{runId}`).
- **G2**: Реализовать **Flows 1–3** из `docs/user_flows.md` как **несколько разных flow templates** (разные `flowKey`), а не как “набор шагов внутри одного универсального run”:
  - иногда нужно запускать только Flow 1,
  - иногда — Flow 2,
  - иногда — Flow 3,
  - допускаются шаблоны, которые включают 2–3 при необходимости (но всё равно как **один выбранный flowKey на один run**).
- **G3**: Сделать систему event-driven на **Google Cloud Run Functions (gen2)**: Firestore update → оркестрация → воркеры шагов.
- **G4**: Обеспечить **идемпотентность и корректность при at-least-once delivery** (event triggers с retry).
- **G5**: Хранить большие результаты **в GCS**, а в Firestore держать только метаданные и ссылки (GCS URI, при необходимости signed URL + expiry).

### Non-goals (чего пока не делаем)
- **NG1**: `configuration_service` (централизованная конфигурация/шаблоны/модели) — позже.
- **NG2**: `ACCOUNT_EXPORT`, `NEWS_EXPORT`, `INDICATORS_ON_DEMAND` — позже.
- **NG3**: UI/портал/кабинет пользователя — вне MVP (внешнее потребление результатов допускается “вне приложения”).
- **NG4**: История попыток выполнения шагов — **не храним**; только последний статус/ошибка (подробности — в логах).

## Source of truth (контракты)
- **Firestore документ `flow_runs/{runId}`**: `docs/contracts/schemas/flow_run.schema.json`
- **Правила статусов/оркестрации**: `docs/contracts/orchestration_rules.md`
- **GCS артефакты**:
  - OHLCV export file: `docs/contracts/schemas/ohlcv_export_file.schema.json`
  - Charts manifest: `docs/contracts/schemas/charts_outputs_manifest.schema.json`
  - LLM report file: `docs/contracts/schemas/llm_report_file.schema.json`
  - LLM recommendation file: `docs/contracts/schemas/llm_recommendation_file.schema.json`
  - Naming PNG: `docs/contracts/charts_images_naming.md`
- **Debug API**: `docs/contracts/openapi/debug.openapi.yaml`

## Components (MVP)
### `debug-http-api` (HTTP Cloud Run Function)
- **Purpose**: ручной запуск run и просмотр текущего состояния; debug-only операции simulate/advance/cancel.
- **Contract**: строго следует `docs/contracts/openapi/debug.openapi.yaml`.
- **Security**: в prod — **IAM only** (без публичного доступа).

### `advance-flow` (Firestore trigger Cloud Run Function)
- **Purpose**: оркестратор: переводит `PENDING -> READY`, обновляет прогресс, ставит `flow_run.status` в терминальные состояния по правилам.
- **Contract**: следует `docs/contracts/orchestration_rules.md`.
- **Safety**: корректен при retry и конкуренции (идемпотентность; атомарные обновления).

### Worker functions (Firestore trigger)
#### `worker-ohlcv-export`
- Пишет OHLCV JSON в GCS и обновляет `steps[stepId].outputs.gcs_uri`.

#### `worker-chart-export`
- Рендерит набор PNG, пишет их в GCS по конвенции, пишет manifest (`ChartsOutputsManifest`) и обновляет `steps[stepId].outputs.outputsManifestGcsUri`.

#### `worker-llm-report`
- Собирает контекст (OHLCV + chart manifest + optional prior reports), вызывает LLM, пишет `LLMReportFile` в GCS, обновляет `steps[stepId].outputs.gcs_uri`.

#### `worker-llm-recommendation` (Flow 3)
- Берёт `reportIds[]`, вызывает LLM, пишет `LLMRecommendationFile` в GCS, обновляет `steps[stepId].outputs.gcs_uri`.

## Execution model (Cloud Run Functions gen2)
## Flow templates (MVP)
Цель этого раздела — зафиксировать **набор “готовых” flowKey**, чтобы систему можно было запускать по-разному (Flow 1 отдельно, Flow 2 отдельно, Flow 3 отдельно).

Принцип:
- **1 run = 1 flowKey** (один выбранный template).
- template определяет **набор шагов** и их `dependsOn`.

### Flow 1 template (scheduled)
- **flowKey**: `scheduled_month_week_report_v1` (используется в `docs/contracts/examples/flow_run.example.json`).
- **steps**:
  - OHLCV_EXPORT: `ohlcv_export:1M` → CHART_EXPORT: `charts:1M:<variant>` → LLM_REPORT: `llm_report:1M:<variant>`
  - OHLCV_EXPORT: `ohlcv_export:1w` → CHART_EXPORT: `charts:1w:<variant>` → LLM_REPORT: `llm_report:1w:<variant>`
  - LLM_REPORT(1w) должен иметь `inputs.reportIds[]` со ссылкой(ами) на 1M отчёт.

### Flow 2 template (user-triggered)
- **flowKey**: `user_multi_tf_report_v1` (название встречается в `docs/flowrun_plan.md`, финально фиксируем здесь).
- **steps**:
  - включает шаги Flow 1 (как минимум 1M+1w), и добавляет 1d и 4h по описанию в `docs/user_flows.md`.
  - LLM_REPORT(1d) использует `reportIds[]` для контекста 1w.
  - LLM_REPORT(4h) использует `reportIds[]` для контекста 1d.

### Flow 3 template (recommendation)
- **flowKey**: `recommendation_from_reports_v1` (фиксируем здесь).
- **steps**:
  - один LLM_RECOMMENDATION step, который принимает `inputs.reportIds[]` (>=1).

### Notes on stepId and CHART_EXPORT variants
- `stepId` остаётся детерминированным (`stepType:timeframe:variant`).
- Если один шаг CHART_EXPORT делает несколько запросов (`inputs.requests[]` содержит несколько `chartTemplateId`), то **variant stepId** и директория manifest/PNG должны быть привязаны к **variant шага** (например `charts:1M:ctpl_default_v1`), а фактические `chartTemplateId` отражаются в `ChartsOutputsManifest.requested[]/items[]`.

### Triggers
- **Event triggers**: Firestore update events (Eventarc) для `advance-flow` и всех worker’ов.
- **HTTP trigger**: только для `debug-http-api`.

### Idempotency & retries
- Для event triggers допускается **at-least-once**; retry включаем только для функций, у которых поведение идемпотентно.
- Идемпотентный ключ: **`runId + stepId`** (см. `docs/contracts/orchestration_rules.md`).
- Воркеры обязаны:
  - атомарно “забирать” шаг (`READY -> RUNNING`), если он всё ещё `READY`;
  - писать артефакты по **детерминированным путям** в GCS;
  - завершать шаг `RUNNING -> SUCCEEDED|FAILED` и не трогать `READY`.

### Concurrency
- Для функций, которые мутируют `flow_runs/{runId}`, требуется **request concurrency = 1** (не-реэнтерабельная логика + простая модель инвариантов).

## Data model requirements
- Структура `flow_run` должна соответствовать `docs/contracts/schemas/flow_run.schema.json`.
- Любые дополнительные поля в `scope` допускаются (расширяемость).
- Для шагов MVP должны быть определены и неизменяемы:
  - `stepId` (детерминированность),
  - `dependsOn` (граф зависимостей без циклов),
  - required `inputs` для выполнения,
  - required `outputs` для SUCCEEDED.

## Observability requirements
- Все функции пишут структурные логи (минимум: `runId`, `stepId`, `flowKey`, `operationId` для HTTP).
- Ошибки шага пишутся в `steps[stepId].error{code,message,details}` и дублируются в лог.

## Security requirements
- **No secrets in Firestore/GCS paths/logs**.
- Секреты — через Secret Manager (или аналогичный механизм), доступ по least privilege.
- Debug HTTP API в prod: **закрыт IAM**, ingress ограничен.

## Definition of done (MVP)
- **MVP считается готовым только в продакшн-окружении GCP**, не только через debug API.

Минимальные критерии:
- **Деплой**: `debug-http-api`, `advance-flow`, `worker-ohlcv-export`, `worker-chart-export`, `worker-llm-report`, `worker-llm-recommendation` задеплоены как Cloud Run Functions (gen2) в проекте GCP.
- **Триггеры**: Firestore update triggers (Eventarc) настроены и реально вызывают `advance-flow` и воркеры.
- **Хранилище**: GCS bucket для артефактов доступен runtime SA; результаты пишутся по конвенциям путей.
- **Запуск Flow templates**:
  - Flow 1 запускается по расписанию (Cloud Scheduler или эквивалентный механизм) и завершается артефактами в GCS.
  - Flow 2 запускается по пользовательскому запросу (через prod-safe entrypoint) и завершается артефактами в GCS.
  - Flow 3 запускается отдельно, используя `reportIds[]` (>=1), и создаёт `LLMRecommendationFile`.
- **Валидация контрактов**: артефакты валидируются по JSON Schema (OHLCV/manifest/LLM report/LLM recommendation), а `flow_run` соответствует `flow_run.schema.json`.
- **Debug API**: допускается как internal инструмент, но **не является требованием**, чтобы “только через него всё работало”.

