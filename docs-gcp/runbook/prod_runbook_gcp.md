## TDA Prod Runbook (GCP) — Cloud Run Functions (gen2) + Firestore triggers + Scheduler

Этот документ описывает **минимальный** набор ресурсов/ролей/настроек в GCP, чтобы флоу из `docs-general/requirements_mvp.md` могли выполняться **в prod окружении** на Cloud Run Functions (gen2), с Eventarc/Firestore triggers и Cloud Scheduler.

Ссылки на официальную документацию собраны в `docs-gcp/links/gcp_links.md`.

---

## 0) Обозначения (переменные)
Заполни значения и используй их консистентно в настройках/командах/terraform:
- **PROJECT_ID**: GCP project id
- **PROJECT_NUMBER**: GCP project number
- **REGION**: регион деплоя функций (например `europe-west1`)
- **FIRESTORE_DB**: обычно `(default)`
- **ARTIFACTS_BUCKET**: GCS bucket для артефактов run’ов (например `trading-agents-artifacts-prod`)
- **RUNTIME_SA**: runtime service account email (например `ta-runtime@PROJECT_ID.iam.gserviceaccount.com`)
- **SCHEDULER_SA**: service account для Cloud Scheduler OIDC (например `ta-scheduler@PROJECT_ID.iam.gserviceaccount.com`)
- **PROD_TRIGGER_URL**: internal URL production entrypoint (HTTP) для запуска run’ов (например `https://run-trigger.example.internal`)
- **DEBUG_API_URL**: internal URL debug API (через Cloud Run Functions)

---

## 1) Минимальные GCP ресурсы (MVP)
### 1.1 Firestore (Native mode)
- **Firestore database** включена в проекте.
- Коллекция: `flow_runs`
- Документы: `flow_runs/{runId}` по контракту `docs-general/contracts/schemas/flow_run.schema.json`
- Дополнительно для `worker-chart-export`:
  - коллекция `chart_templates` (runtime source of truth для `chartTemplateId`, см. `docs-worker-chart-export/spec/implementation_contract.md`);
  - коллекция `chart_img_accounts_usage` для персистентного учёта использования лимитов аккаунтов внешнего Chart API (минимум поля `usageToday`, `windowStart`, опционально `dailyLimit`/`priority`, см. `docs-worker-chart-export/spec/implementation_contract.md`, раздел 14.4).

### 1.2 Cloud Storage
- **Один bucket** для артефактов run’ов (OHLCV, charts PNG, manifests, LLM outputs).
- Рекомендуемое соглашение путей: см. `docs-general/contracts/README.md`

Дополнительно для `worker-chart-export`:
- bucket для charts PNG/manifest должен быть настроен с public read (роль `Storage Object Viewer` для `allUsers` и включённый uniform bucket-level access), если не оговорено иное в политике безопасности.

### 1.3 Secrets (Secret Manager)
Минимально (MVP):
- **LLM_API_KEY** (для `worker-llm-report`, `worker-llm-recommendation`)
- **chart-img-accounts** — JSON-массив `{ id, apiKey }` для аккаунтов внешнего Chart-IMG API; монтируется в env `CHART_IMG_ACCOUNTS_JSON` для воркера `worker-chart-export`
- Прочие (например BigQuery creds) **не должны** храниться в Firestore/логах.

### 1.4 Cloud Run Functions (gen2)
Минимальные функции для MVP:
- **HTTP (prod entrypoint)**: `prod-run-trigger` (рекомендуется; см. раздел 5.2)
- **HTTP (debug/internal)**: `debug-http-api`
- **Event** (Firestore update via Eventarc):
  - `advance-flow`
  - `worker-ohlcv-export`
  - `worker-chart-export`
  - `worker-llm-report`
  - `worker-llm-recommendation`

### 1.5 Cloud Scheduler
Нужно минимум 1 job для Flow 1:
- job вызывает `POST /runs:trigger` (или иной prod-safe entrypoint) с OIDC identity (**SCHEDULER_SA**)
- body создаёт `flow_runs/{runId}` с нужным `flowKey` (например `scheduled_month_week_report_v1`)

#### Пример: Cloud Scheduler job (OIDC) для Flow 1
Ниже — шаблон команды. Важно:
- endpoint должен быть **IAM-protected**
- job должен вызывать **`PROD_TRIGGER_URL`** (рекомендуется `prod-run-trigger`)

```bash
gcloud scheduler jobs create http flow1-scheduled-month-week-report \
  --location=REGION \
  --schedule="0 */4 * * *" \
  --time-zone="UTC" \
  --http-method=POST \
  --uri="PROD_TRIGGER_URL/runs:trigger" \
  --oidc-service-account-email="SCHEDULER_SA" \
  --oidc-token-audience="PROD_TRIGGER_URL" \
  --headers="Content-Type=application/json" \
  --message-body='{"flowKey":"scheduled_month_week_report_v1","symbol":"BTC/USDT","triggerSource":"cloud-scheduler"}'
```

Если нужно запускать список символов, рекомендуется:
- создать **несколько jobs** (по одному на символ/группу), либо
- вынести логику “обойти список” в отдельную функцию/джобу (backlog).

---

## 2) IAM: сервисные аккаунты и роли (минимум)
### 2.1 Runtime SA (RUNTIME_SA)
Принцип: отдельный runtime SA, least privilege.

Минимальные права (по смыслу, конкретные роли уточняются под выбранные API и режимы доступа):
- **Firestore/Datastore**: чтение/запись `flow_runs/*` (оркестрация флоу), а также чтение `chart_templates/*` и чтение/запись `chart_img_accounts_usage/*` для воркера `worker-chart-export`
- **GCS**: запись/чтение в `ARTIFACTS_BUCKET` (желательно bucket-scope)
- **Secret Manager**: доступ к нужным секретам (read)
- **BigQuery** (если OHLCV читает из BigQuery): read на нужные dataset/table
- **Logging**: запись логов (если политика/окружение требует явных прав)

### 2.2 Scheduler SA (SCHEDULER_SA)
- Нужен для OIDC вызова HTTP endpoint’а запуска.
- Должен иметь право вызывать `prod-run-trigger` (invoker) и/или `debug-http-api` **если** он используется как entrypoint в prod.

### 2.3 Invoker policy для HTTP функций
Для `prod-run-trigger` и `debug-http-api`:
- **prod: IAM-only**, без публичного доступа.
- Разрешить invoke только ограниченному списку principals (например SCHEDULER_SA + админы/ops).

### 2.4 Примеры IAM policy bindings (gcloud)
Ниже — **рабочие шаблоны команд**. Они зависят от выбранной структуры (dataset-level vs project-level) и политик безопасности, поэтому перед применением стоит согласовать с security/ops.\n\n#### 2.4.1 RUNTIME_SA: Firestore + GCS + Secret Manager (+ BigQuery)

```bash
# Firestore (Datastore API) read/write для `flow_runs/*`, а также доступ к `chart_templates/*` и `chart_img_accounts_usage/*`
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/datastore.user"

# GCS доступ к bucket артефактов (упрощённо для MVP)
gcloud storage buckets add-iam-policy-binding gs://ARTIFACTS_BUCKET \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/storage.objectAdmin"

# Secret Manager read (точечно по секретам)
gcloud secrets add-iam-policy-binding LLM_API_KEY \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding chart-img-accounts \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/secretmanager.secretAccessor"

# BigQuery (если OHLCV читает из BigQuery):
# - jobUser нужен для запуска query jobs
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/bigquery.jobUser"

# - dataViewer лучше выдавать на dataset/table уровне; ниже — упрощённый вариант на проект
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/bigquery.dataViewer"

# Logging (если требуется явное право писать логи)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/logging.logWriter"
```

#### 2.4.2 SCHEDULER_SA: право вызывать HTTP entrypoint

```bash
# Разрешаем Cloud Scheduler OIDC identity вызывать prod entrypoint
gcloud run services add-iam-policy-binding prod-run-trigger \
  --region=REGION \
  --member="serviceAccount:SCHEDULER_SA" \
  --role="roles/run.invoker"

# Если Scheduler вызывает debug-http-api (не рекомендуется для prod, но возможно):
gcloud run services add-iam-policy-binding debug-http-api \
  --region=REGION \
  --member="serviceAccount:SCHEDULER_SA" \
  --role="roles/run.invoker"
```

---

## 3) Настройки функций (минимальные требования)
### 3.1 Concurrency
Для функций, мутирующих `flow_runs/{runId}`:
- **concurrency = 1** (упрощает соблюдение инвариантов и идемпотентность)

### 3.2 Retries
- **Event triggers**: retry допустим и ожидаем (at-least-once). Включать retry только если функция строго идемпотентна.
- **HTTP trigger**: платформенный retry не предполагается; caller должен решать повторы.

### 3.3 Timeouts & ресурсы
Минимум:
- `worker-llm-*`: timeout под SLA модели + сеть
- `worker-chart-export`: timeout под latency внешнего API
- `worker-ohlcv-export`: timeout под BigQuery/объём данных

### 3.4 Build & deploy (Cloud Run Functions gen2)
- Артефакты сборки функций (gen2) хранятся в Artifact Registry, обычно в репозитории вида `REGION-docker.pkg.dev/PROJECT/gcf-artifacts`.
- Если включаются изолированные сборки (private pools / worker pools), заранее проверить права на worker pool (обычно требуется выдать `cloudbuild.workerPoolUser` нужному service agent’у функций).
- Для prod избегать “default compute SA” как runtime identity: всегда явный `RUNTIME_SA`.

### 3.5 Networking & security (минимум)
- Ingress для HTTP entrypoints: internal-only / internal-and-gclb (никакого public в prod).
- Egress: при необходимости контролируем исходящий трафик через Serverless VPC Access (и соответствующую настройку egress).
- Секреты: только Secret Manager (или эквивалент), никаких секретов в Firestore, env, логах.

### 3.6 Runtime service agents (важно для деплоя)
В prod стоит помнить про service agents (их удаление/поломка часто ломает deploy/update/delete функций):
- `service-PROJECT_NUMBER@gcf-admin-robot.iam.gserviceaccount.com` (Cloud Functions / gen2).

---

## 4) Eventarc / Firestore triggers (prod)
### 4.1 Общая логика
- Firestore update triggers должны реагировать на изменения `flow_runs/{runId}`.
- Оркестрация: `advance-flow` управляет `PENDING→READY` и `flow_run.status` (см. `docs-general/contracts/orchestration_rules.md`).
- Воркеры “забирают” работу только через транзакционный `READY→RUNNING`.

### 4.2 Фильтрация событий
Рекомендация (чтобы не делать лишнюю работу на каждом апдейте документа):
- На уровне кода воркера быстро отсеивать события, если “нет READY шагов нужного типа”.
- На уровне триггера, если возможно, использовать максимально узкие фильтры (но не жертвовать корректностью).

---

## 5) Prod запуск флоу (MVP templates)
Источник истины: `docs-general/requirements_mvp.md` (раздел “Flow templates (MVP)”).

### 5.1 Flow 1 (scheduled)
- Scheduler вызывает prod entrypoint (рекомендуется `prod-run-trigger`) и создаёт `flow_run` с `flowKey=scheduled_month_week_report_v1`.
- Дальше всё идёт event-driven через Firestore triggers.

### 5.2 Flow 2 (user-triggered)
Цель: дать пользователю/оператору способ запускать Flow 2 **в prod**, не раскрывая debug-функционал и не открывая систему наружу.

#### Вариант A (минимум): использовать `debug-http-api` как entrypoint
Подходит для ранней стадии, но требует дисциплины:
- endpoint IAM-protected, internal-only
- операции `simulate/advance/cancel` должны быть либо отключены в prod, либо доступны только ops (отдельный allowlist)
- валидация тела запроса и allowlist `flowKey` обязательны

#### Вариант B (рекомендуется): отдельная функция `prod-run-trigger`
**Роли и ответственность**:
- принимает один endpoint вида `POST /runs:trigger` (или аналогичный)
- проверяет IAM identity caller
- валидирует вход (минимум: `flowKey`, `symbol`, опциональные параметры запуска)
- **allowlist flowKey**: разрешены только `scheduled_month_week_report_v1`, `user_multi_tf_report_v1`, `recommendation_from_reports_v1`
- создаёт `flow_runs/{runId}` по `docs-general/contracts/schemas/flow_run.schema.json`
- не реализует debug-операции (simulate/advance/cancel)

**Кто вызывает**:
- Cloud Scheduler (Flow 1)
- внутренний оператор/инструмент (Flow 2)

**IAM**:
- invoker доступ ограничен (SCHEDULER_SA + ops)
- функция работает от `RUNTIME_SA`

### 5.3 Flow 3 (recommendation)
- Запускается отдельно, `flowKey=recommendation_from_reports_v1`, вход: `reportIds[]` (>=1).

### 5.4 Guardrails для `prod-run-trigger` (минимум для prod)
Цель: снизить риск случайного запуска “не того” флоу/символа, а также упростить аудит.

#### 5.4.1 Allowlist и валидация входа
- **allowlist `flowKey`** (жёстко в коде): только
  - `scheduled_month_week_report_v1`
  - `user_multi_tf_report_v1`
  - `recommendation_from_reports_v1`
- **allowlist/валидация `symbol`**:
  - формат (минимум `^[A-Z0-9]{2,10}/[A-Z0-9]{2,10}$` либо ваша договорённость)
  - опционально: allowlist известных symbol’ов для prod
- Отбрасывать неизвестные поля (`additionalProperties=false` на input DTO) и писать понятный `400` с кодом ошибки.

#### 5.4.2 Rate limiting / quotas (минимальные варианты)
Платформенный “rate limit” для Cloud Run Functions зависит от окружения. Минимально-практичные меры:
- **IAM allowlist invoker’ов** (SCHEDULER_SA + ops) — снижает риск внешнего спама.
- **max instances** ограничить на HTTP entrypoint (чтобы не заспайкать создание run’ов).
- **квоты на уровне кода**:
  - ограничение частоты запусков per `flowKey`/per `symbol` (например, не чаще N в минуту)
  - дедупликация по `idempotencyKey` (см. ниже)

Если нужен настоящий L7 rate limit, обычно добавляют API Gateway / Cloud Endpoints / Load Balancer + Cloud Armor (как отдельный проектный слой).

#### 5.4.3 Idempotency для запуска (рекомендуется)
Чтобы Scheduler/клиент мог безопасно ретраить:
- принимать заголовок `Idempotency-Key` (или поле в body)
- хранить короткую запись “ключ→runId” (например в Firestore отдельной коллекцией) и возвращать тот же `runId` при повторе

#### 5.4.4 Audit logging (что логировать)
В структурных логах `prod-run-trigger` фиксировать минимум:
- `requestId` (или `trace`), `caller` (principal email/subject)
- `flowKey`, `symbol`
- `runId` (созданный/возвращённый по идемпотентности)
- `triggerSource`
- итог: `status` (created / duplicate / rejected) + `error.code` при ошибке

---

## 6) Pre-deploy checks (обязательные)
В репозитории есть минимальная проверка контрактов:
- `npm run validate`
  - валидирует пример `docs-general/contracts/examples/flow_run.example.json` по `docs-general/contracts/schemas/flow_run.schema.json`
  - делает lint OpenAPI:
    - `docs-general/contracts/openapi/debug.openapi.yaml`
    - `docs-general/contracts/openapi/prod.openapi.yaml`

---

## 7) Post-deploy verification (prod smoke)
Минимальные проверки после деплоя:
- Создание run (через Scheduler или ручной вызов entrypoint’а) создаёт `flow_runs/{runId}`.
- В логах видно срабатывание `advance-flow` на update.
- Статусы шагов идут: `PENDING → READY → RUNNING → SUCCEEDED|FAILED`.
- В GCS появляются артефакты по конвенциям путей.
- Артефакты соответствуют схемам (`docs-general/contracts/schemas/*`).

---

## 8) Logging & Observability (Cloud Logging) — минимум для prod
Цель: чтобы в prod было возможно быстро ответить на вопросы:
- что выполнялось (run/step), кем и почему
- где “застряло” (статусы/ретраи/латентность)
- что сломалось (ошибки, коды, корреляция с trace/request)

### 8.1 Структура application logs (обязательная конвенция)
Все функции TDA должны писать структурные JSON-логи (stdout) минимум с полями:
- `service`: имя функции/сервиса (например `advance-flow`, `worker-llm-report`)
- `env`: `prod|staging|dev`
- `runId`, `flowKey`
- `stepId` (если применимо)
- `eventId` (если приходит из Eventarc/trigger)
- `requestId` (для HTTP) и/или `trace` (для корреляции)
- `severity`: `DEBUG|INFO|WARNING|ERROR`
- `message`
- `error.code`, `error.message`, `error.details` (только когда есть ошибка)

Рекомендуемые дополнительные поля:
- `transition.from`, `transition.to` (для смены статусов шага)
- `gcs_uri` (если пишем/читаем артефакт)
- `duration_ms` (для вызовов внешних API и общего шага)

### 8.2 Cloud Logging: что настроить (минимум)
- Убедиться, что в проекте включён Cloud Logging и функции реально пишут логи в **Cloud Logging**.
- Для prod рекомендуется завести отдельный **Log bucket** с ретеншном (например 30–90 дней) и пометкой окружения.
- Для долгого хранения/аналитики — **Log sink** в BigQuery или GCS (по политике организации).

### 8.3 Audit Logs (рекомендуется)
Включить Admin/Data access audit logs для ключевых API (минимум):
- Cloud Run / Cloud Functions (deploy/update)
- IAM (изменения ролей и policy bindings)
- Secret Manager (доступ к секретам)
И регулярно проверять в Cloud Logging.

### 8.4 Метрики и алёрты (минимум)
Создать log-based metrics (или аналог) и алёрты:
- **HTTP 5xx spikes** (для `prod-run-trigger`, `debug-http-api`)
- **FAILED шаги**: счётчик по `error.code` и `stepType`
- **retry storms**: рост количества повторных обработок одного `runId/stepId` за окно времени
- **stuck runs**: run в `RUNNING` дольше X минут (по полям `createdAt/updatedAt/finishedAt` и/или логам)

### 8.5 Быстрые фильтры для расследований (примеры)
- По одному run:
  - фильтр по `jsonPayload.runId="<runId>"` (или по `textPayload` если нет JSON)
- По одной функции:
  - фильтр по `resource.type="cloud_run_revision"` и имени сервиса/функции
- По ошибкам конкретного кода:
  - `jsonPayload.error.code="LLM_TIMEOUT"` (пример)

---

## 9) Troubleshooting (частые причины)
- Фильтровать Cloud Logging по `resource.type="cloud_run_revision"` и имени функции/сервиса.
- Ошибки деплоя часто связаны с:
  - отсутствием прав на Artifact Registry
  - поломанными service-agent биндингами
  - неверным ingress / VPC connector / egress settings


