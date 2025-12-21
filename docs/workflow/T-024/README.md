# T-024: GCP deploy & Eventarc demo

## Summary

- Развернуть worker-chart-export в Cloud Run Functions gen2, подключить Eventarc к Firestore update `flow_runs/{runId}`, повторить E2E-сценарии в облаке.

## Goals

- Подтвердить end‑to‑end обработку Eventarc → worker → Firestore/GCS/Logging.
- Проверить идемпотентность при повторных событиях.
- Убедиться, что Secret Manager и GCS используются корректно в облаке.
- Подтвердить доставку stdout/err из Cloud Run Functions gen2 в Cloud Logging и наличие ключевых структурированных событий.
- Автоматизировать деплой через gcloud.

## Expected Demonstration Result

1) Обновление `flow_runs/{runId}` (READY шаг) вызывает Eventarc и функцию.
2) Шаг становится `SUCCEEDED`.
3) В GCS появляются PNG + manifest.
4) В Cloud Logging фиксируются события `claim_attempt`, `chart_api_call_*`, `step_completed` (stdout/err автоматически экспортируется Cloud Run Functions gen2).
5) Повторный update приводит к no‑op (step остаётся `SUCCEEDED`).

## Planned Scenarios (TDD)

### Scenario 1: Happy path (Eventarc update → SUCCEEDED)
**Prerequisites**: READY flow_run, valid chart_templates, Secret Manager, GCS bucket.  
**Steps**:
1) Создать/обновить `flow_runs/{runId}` с READY шагом CHART_EXPORT.  
2) Подождать Eventarc‑вызова и обработки.  
3) Проверить Firestore, GCS и Cloud Logging.  
**Expected**: step SUCCEEDED; PNG + manifest в GCS; корректные логи в Cloud Logging.

### Scenario 2: Idempotent retry
**Steps**: Повторить update того же `flow_runs/{runId}` после SUCCEEDED.  
**Expected**: no‑op; статус SUCCEEDED; новых объектов в GCS нет.

### Scenario 3: Invalid stepId
**Steps**: Обновить flow_run с несуществующим stepId.  
**Expected**: FAILED, `VALIDATION_FAILED`, без записей в GCS.

### Scenario 4: GCS write failure
**Steps**: Неверный bucket или отсутствие роли у SA.  
**Expected**: FAILED, `MANIFEST_WRITE_FAILED` или `GCS_WRITE_FAILED`, без PNG/manifest.

### Scenario 5: Eventarc filter sanity
**Steps**: Внести изменения в другие коллекции или удалить документ.  
**Expected**: функция не вызывается.

### Scenario 6: Missing chart template
**Steps**: Указать chartTemplateId без документа в `chart_templates/{id}`.  
**Expected**: failure per-request; итог по `minImages`.

### Scenario 7: Secret Manager misconfig
**Steps**: Передать пустой/невалидный секрет.  
**Expected**: CONFIG_ERROR (fail fast), нет GCS записей.

## Preparation (GCP)

### Required APIs
```bash
gcloud services enable \
  run.googleapis.com eventarc.googleapis.com firestore.googleapis.com \
  secretmanager.googleapis.com storage.googleapis.com logging.googleapis.com \
  --project ${PROJECT_ID}
```

### Service account and roles
```bash
RUNTIME_SA=tda-worker-chart-export-test@${PROJECT_ID}.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/datastore.user"

gcloud storage buckets add-iam-policy-binding gs://${ARTIFACTS_BUCKET} \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/storage.objectAdmin"

gcloud secrets add-iam-policy-binding chart-img-accounts \
  --project=${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/logging.logWriter"
```

### Secret Manager
```bash
gcloud secrets create chart-img-accounts --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets versions add chart-img-accounts --project=${PROJECT_ID} --data-file=/tmp/chart-img-accounts.json
```

### Firestore data
- `chart_templates/{chartTemplateId}`: импортировать `docs-worker-chart-export/chart-templates/*.json`
- `chart_img_accounts_usage/{accountId}`: для каждого id из секрета:
  - `windowStart`: текущая дата 00:00:00Z
  - `usageToday`: 0
  - `dailyLimit`: по желанию
- `flow_runs/{runId}`: READY шаг `CHART_EXPORT` (в базе `tda-db-europe-west4`)

## Deploy (Cloud Run Functions gen2)

```bash
gcloud functions deploy worker-chart-export \
  --gen2 \
  --runtime=python313 \
  --region=${REGION} \
  --source=. \
  --entry-point=worker_chart_export \
  --trigger-location=${REGION} \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.updated" \
  --trigger-event-filters="database=tda-db-europe-west4" \
  --trigger-event-filters="namespace=(default)" \
  --trigger-event-filters-path-pattern="document=flow_runs/{runId}" \
  --service-account=${RUNTIME_SA} \
  --set-env-vars="CHARTS_BUCKET=gs://${ARTIFACTS_BUCKET},CHARTS_API_MODE=record,CHARTS_DEFAULT_TIMEZONE=Etc/UTC,FIRESTORE_DB=tda-db-europe-west4,ARTIFACTS_BUCKET=${ARTIFACTS_BUCKET}" \
  --set-secrets="CHART_IMG_ACCOUNTS_JSON=projects/${PROJECT_ID}/secrets/chart-img-accounts:latest" \
  --concurrency=1 \
  --retry
```

## Verification Steps

1) Создать/обновить READY `flow_runs/{runId}`.  
2) Дождаться обработки.  
3) Проверить:
   - Firestore: шаг SUCCEEDED, outputsManifestGcsUri заполнен  
   - GCS: PNG + manifest существуют  
   - Cloud Logging: события claim/chart_api/step_completed (stdout/err ingestion)  
4) Повторить update для идемпотентности.  

## Risks

- Runtime `python313` может быть недоступен в gen2 (тогда нужен container‑based deploy).
- Ошибки Secret Manager приводят к CONFIG_ERROR и падению функции.
- Record‑режим расходует лимиты Chart‑IMG; для частых тестов использовать mock.
- `runId` должен соответствовать regex схемы манифеста (без `_` в суффиксе).

## Rollback Plan

- Удалить функцию, Eventarc‑триггер, тестовые документы и объекты из GCS.
- Отозвать роли у SA при необходимости.

## References

- @docs-gcp/runbook/prod_runbook_gcp.md
- @docs-worker-chart-export/implementation_contract.md
- @docs-worker-chart-export/contracts/flow_run.schema.json
- @docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json
- @docs/workflow/lessons_learned_cloud_functions_gen2_deploy.md

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
