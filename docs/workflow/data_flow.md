# Data Flow: worker_chart_export

Это черновик описания полного пути данных для сервиса worker_chart_export. Документ будет уточняться по мере развития требований.

## 1) Получение события
- Источник: Firestore update `flow_runs/{runId}` (Eventarc) или CLI `run-local` (чтение файла flow_run).
- Быстрый фильтр: проверка, что коллекция `flow_runs`, есть шаги типа `CHART_EXPORT` и хотя бы один READY.
- Модули/функции: `worker_chart_export.entrypoints.cloud_event.worker_chart_export`; парсинг и фильтр — `ingest.parse_flow_run_event`, `ingest.is_firestore_update_event`.

## 2) Выбор шага
- Если `stepId` не задан: детерминированно выбирается первый READY `CHART_EXPORT` (сортировка по `stepId`).
- Если `stepId` задан: валидируем наличие шага и `stepType=="CHART_EXPORT"`, статус READY/допустимый.
- Модули/функции: `ingest.pick_ready_chart_export_step`; проверки шага — `core._get_step`.

## 3) Claim шага (идемпотентность)
- Транзакция Firestore: `READY -> RUNNING`. Повтор на RUNNING/SUCCEEDED/FAILED даёт безопасный no-op.
- Логируется результат claim.
- Модули/функции: `orchestration.claim_step_transaction`, `core.run_chart_export_step` (обёртка).

## 4) Подготовка запросов Chart-IMG
- Читаются `inputs.requests[]`, `minImages`.
- Загружаются шаблоны из `chart_templates/{chartTemplateId}`.
- Валидация: отсутствие дубликатов, `minImages <= len(requests)`, корректный `chartImgSymbolTemplate`, `scope.symbol` без “/”.
- Строится payload: `symbol = chartImgSymbolTemplate({symbol})`, `interval = timeframe`, `timezone = charts_default_timezone`.
- Формируется список items и per-request failures (VALIDATION_FAILED).
- Модули/функции: `templates.build_chart_requests`, `templates.FirestoreChartTemplateStore`, `core._get_requests/_get_min_images/_get_scope_symbol/_get_timeframe`.

## 5) Выбор аккаунта и учёт лимитов
- Для каждого запроса: транзакционно читается/сбрасывается `chart_img_accounts_usage/{accountId}`, сравнивается `dailyLimit`, инкрементируется `usageToday`.
- При 429/LimitExceeded помечаем аккаунт exhausted и пробуем следующий; при полном исчерпании всех аккаунтов → `CHART_API_LIMIT_EXCEEDED`.
- Модули/функции: `usage.select_account_for_request`, `usage.mark_account_exhausted`.

## 6) Вызов Chart-IMG
- Режимы: `real | mock | record`.
- Запрос `/v2/tradingview/advanced-chart` с apiKey аккаунта; retries с backoff для ретраибл ошибок (5xx/timeout/429).
- Классификация ошибок: `CHART_API_FAILED`, `CHART_API_LIMIT_EXCEEDED`, `CHART_API_MOCK_MISSING`.
- Успех → PNG bytes; неуспех → failure с кодом.
- Модули/функции: `chart_img.ChartImgClient.fetch`, `chart_img.fetch_with_retries`, `core._execute_chart_request`.

## 7) Загрузка артефактов в GCS
- Для каждого успешного PNG: путь `runs/<runId>/charts/<timeframe>/<chartTemplateId>/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`, где `symbolSlug = scope.symbol`.
- Формируется manifest: `schemaVersion=1`, `runId`, `stepId`, `createdAt` (RFC3339), `symbol`, `timeframe`, `minImages`, `requested`, `items`, `failures`.
- Валидируется manifest по JSON Schema; запись в `runs/<runId>/steps/<stepId>/charts/manifest.json` (`gs://` URI).
- Модули/функции: `gcs_artifacts.upload_pngs`, `gcs_artifacts.build_manifest`, `gcs_artifacts.validate_manifest`, `gcs_artifacts.write_manifest`.

## 8) Итоговый статус шага
- Успех, если `itemsCount >= minImages`; иначе FAILED с кодом первого failure или `VALIDATION_FAILED`.
- Ошибки записи: `GCS_WRITE_FAILED` / `MANIFEST_WRITE_FAILED`; ошибки схемы manifest → `VALIDATION_FAILED`.
- Модули/функции: логика в `core.run_chart_export_step`; финальный выбор кода через `_finalize_failure`.

## 9) Финализация шага
- Патч Firestore (минимальный): `status=SUCCEEDED` + `outputsManifestGcsUri` или `status=FAILED` + `error{code,message,details}`, `finishedAt`.
- Идемпотентно: повторный finalize на SUCCEEDED/FAILED не портит состояние.
- Модули/функции: `orchestration.finalize_step`, `orchestration.build_finalize_*` (косвенно), вызываются из core.

## 10) Логирование и безопасность
- События: `cloud_event_received`, `claim_attempt`, `chart_api_call_start/finished`, `manifest_written`, `step_completed`, `finalize_failed`.
- Логи без секретов (apiKey/PII). URIs только `gs://`, без `signed_url/expires_at`.
- Модули/функции: `logging.log_event`, точки вызова — `entrypoints.cloud_event`, `core.run_chart_export_step` при ключевых действиях.

## 11) Хранилища и секреты
- Firestore: `flow_runs` (вход), `chart_templates` (шаблоны), `chart_img_accounts_usage` (usage).
- GCS: общий `ARTIFACTS_BUCKET` для PNG и manifest.
- Secret Manager: `chart-img-accounts` → env `CHART_IMG_ACCOUNTS_JSON` (парсится один раз при старте).
- Модули/функции: `config.WorkerConfig.from_env` (чтение env/секрета), `runtime.get_config` (кэш), `templates.FirestoreChartTemplateStore`, `usage` транзакции, `gcs_artifacts.GcsUploader`.

## 12) Адаптеры
- CLI: тонкая обёртка, читает `flow_run` JSON, опциональный `stepId`, overrides env (bucket/mode/accounts), summary (text/json), exit code 0/!=0.
- CloudEvent: парсит событие, выбирает шаг, вызывает тот же core.
- Модули/функции: `cli._run_local/main`, `entrypoints.cloud_event.worker_chart_export`.
