# Data Flow: worker_chart_export

Это черновик описания полного пути данных для сервиса worker_chart_export. Документ будет уточняться по мере развития требований.

## 1) Получение события
- Источник: Firestore update `flow_runs/{runId}` (Eventarc) или CLI `run-local` (чтение файла flow_run).
- Быстрый фильтр: проверка, что коллекция `flow_runs`, есть шаги типа `CHART_EXPORT` и хотя бы один READY.

## 2) Выбор шага
- Если `stepId` не задан: детерминированно выбирается первый READY `CHART_EXPORT` (сортировка по `stepId`).
- Если `stepId` задан: валидируем наличие шага и `stepType=="CHART_EXPORT"`, статус READY/допустимый.

## 3) Claim шага (идемпотентность)
- Транзакция Firestore: `READY -> RUNNING`. Повтор на RUNNING/SUCCEEDED/FAILED даёт безопасный no-op.
- Логируется результат claim.

## 4) Подготовка запросов Chart-IMG
- Читаются `inputs.requests[]`, `minImages`.
- Загружаются шаблоны из `chart_templates/{chartTemplateId}`.
- Валидация: отсутствие дубликатов, `minImages <= len(requests)`, корректный `chartImgSymbolTemplate`, `scope.symbol` без “/”.
- Строится payload: `symbol = chartImgSymbolTemplate({symbol})`, `interval = timeframe`, `timezone = charts_default_timezone`.
- Формируется список items и per-request failures (VALIDATION_FAILED).

## 5) Выбор аккаунта и учёт лимитов
- Для каждого запроса: транзакционно читается/сбрасывается `chart_img_accounts_usage/{accountId}`, сравнивается `dailyLimit`, инкрементируется `usageToday`.
- При 429/LimitExceeded помечаем аккаунт exhausted и пробуем следующий; при полном исчерпании всех аккаунтов → `CHART_API_LIMIT_EXCEEDED`.

## 6) Вызов Chart-IMG
- Режимы: `real | mock | record`.
- Запрос `/v2/tradingview/advanced-chart` с apiKey аккаунта; retries с backoff для ретраибл ошибок (5xx/timeout/429).
- Классификация ошибок: `CHART_API_FAILED`, `CHART_API_LIMIT_EXCEEDED`, `CHART_API_MOCK_MISSING`.
- Успех → PNG bytes; неуспех → failure с кодом.

## 7) Загрузка артефактов в GCS
- Для каждого успешного PNG: путь `runs/<runId>/charts/<timeframe>/<chartTemplateId>/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`, где `symbolSlug = scope.symbol`.
- Формируется manifest: `schemaVersion=1`, `runId`, `stepId`, `createdAt` (RFC3339), `symbol`, `timeframe`, `minImages`, `requested`, `items`, `failures`.
- Валидируется manifest по JSON Schema; запись в `runs/<runId>/steps/<stepId>/charts/manifest.json` (`gs://` URI).

## 8) Итоговый статус шага
- Успех, если `itemsCount >= minImages`; иначе FAILED с кодом первого failure или `VALIDATION_FAILED`.
- Ошибки записи: `GCS_WRITE_FAILED` / `MANIFEST_WRITE_FAILED`; ошибки схемы manifest → `VALIDATION_FAILED`.

## 9) Финализация шага
- Патч Firestore (минимальный): `status=SUCCEEDED` + `outputsManifestGcsUri` или `status=FAILED` + `error{code,message,details}`, `finishedAt`.
- Идемпотентно: повторный finalize на SUCCEEDED/FAILED не портит состояние.

## 10) Логирование и безопасность
- События: `cloud_event_received`, `claim_attempt`, `chart_api_call_start/finished`, `manifest_written`, `step_completed`, `finalize_failed`.
- Логи без секретов (apiKey/PII). URIs только `gs://`, без `signed_url/expires_at`.

## 11) Хранилища и секреты
- Firestore: `flow_runs` (вход), `chart_templates` (шаблоны), `chart_img_accounts_usage` (usage).
- GCS: общий `ARTIFACTS_BUCKET` для PNG и manifest.
- Secret Manager: `chart-img-accounts` → env `CHART_IMG_ACCOUNTS_JSON` (парсится один раз при старте).

## 12) Адаптеры
- CLI: тонкая обёртка, читает `flow_run` JSON, опциональный `stepId`, overrides env (bucket/mode/accounts), summary (text/json), exit code 0/!=0.
- CloudEvent: парсит событие, выбирает шаг, вызывает тот же core.
