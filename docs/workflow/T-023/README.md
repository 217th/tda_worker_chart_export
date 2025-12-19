# T-023: GCP real-env integration tests (local invoke) & runbook alignment

## Summary

- Этап 1 (T-023): подготовить реальное GCP окружение и провести интеграционные тесты через локальный запуск (CLI), используя реальные Firestore/GCS/Secret Manager/Logging.
- Этап 2 (отдельная задача T-024): деплой в Cloud Run Functions gen2 + Eventarc trigger и повторение сценариев в облаке (автоматизированный деплой и запуск).

## Goal

- Иметь воспроизводимый набор gcloud команд для создания тестового окружения и прогон end-to-end тестов (CLI, локальный invoke) с реальными Firestore/GCS/Secret Manager/Logging.
- Зафиксировать зависимость для T-024 (облачный деплой + Eventarc).

## Scope (T-023)

- Роли runtime SA по шаблонам prod_runbook_gcp.md (Firestore RW, GCS write на ARTIFACTS_BUCKET, Secret Manager access, Logging).
- Использовать ARTIFACTS_BUCKET и секрет `chart-img-accounts`.
- Настроить Firestore: `chart_templates`, `chart_img_accounts_usage`, `flow_runs` (тестовые данные).
- Настроить GCS bucket (uniform access; public read — опционально; gs:// канон).
- Прогон ручных/CLI сценариев в real GCP (mock/real Chart-IMG), фиксация ожидаемых результатов.
- Облачный деплой + Eventarc — вынести в T-024 (следующий этап).

## Planned Scenarios (TDD)

### Scenario 1: Подготовка ресурсов через gcloud
**Prerequisites**: PROJECT_ID, REGION, ARTIFACTS_BUCKET, RUNTIME_SA.  
**Steps**:
1) Создать/проверить GCS bucket (uniform).  
2) Выдать роли на bucket, Firestore, Secret Manager, Logging runtime SA.  
3) Создать секрет `chart-img-accounts` и загрузить JSON.  
4) Заполнить Firestore: chart_templates, chart_img_accounts_usage, flow_runs (READY шаг).  
**Expected**: Ресурсы созданы, роли назначены, данные загружены.

### Scenario 2: CLI happy path (mock) на реальном GCP
**Prerequisites**: Secrets/Firestore/GCS готовы; CHARTS_API_MODE=mock; flow_run doc READY.  
**Steps**: Запустить CLI run-local с gs:// bucket.  
**Expected**: Exit 0; PNG и manifest в bucket; step SUCCEEDED в Firestore.

### Scenario 3: CLI invalid stepId
**Steps**: Запуск с несуществующим stepId.  
**Expected**: Exit !=0, errorCode=VALIDATION_FAILED, Firestore шаг не изменён, нет новых файлов в GCS.

### Scenario 4: Account exhaustion
**Steps**: Установить usageToday=dailyLimit для всех account docs, запуск CLI.  
**Expected**: FAILED, errorCode=CHART_API_LIMIT_EXCEEDED, PNG нет, manifest failures[].

### Scenario 5: GCS write failure
**Steps**: Временно убрать роль storage.objectAdmin у RUNTIME_SA или указать неверный bucket и запустить.  
**Expected**: FAILED, errorCode=GCS_WRITE_FAILED/MANIFEST_WRITE_FAILED, PNG/manifest не записаны.

### Scenario 6: Idempotent retry
**Steps**: Повторный запуск на SUCCEEDED шаге.  
**Expected**: No-op, статус остаётся SUCCEEDED, manifest URI без изменений.

### Scenario 7 (перенесено в T-024): Eventarc path
**Примечание**: деплой Cloud Run Functions gen2 и проверка Eventarc будут выполнены в задаче T-024.

## gcloud команды (шаблоны) — T-023 (локальный invoke)

```bash
# Vars
PROJECT_ID=...; REGION=...; ARTIFACTS_BUCKET=...; RUNTIME_SA=worker-chart-export-test@${PROJECT_ID}.iam.gserviceaccount.com

# Bucket (если нет)
gcloud storage buckets create gs://${ARTIFACTS_BUCKET} --uniform-bucket-level-access --project=${PROJECT_ID}

# IAM: Firestore/Datastore
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/datastore.user"

# IAM: GCS bucket write
gcloud storage buckets add-iam-policy-binding gs://${ARTIFACTS_BUCKET} \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/storage.objectAdmin"

# IAM: Secret Manager
gcloud secrets add-iam-policy-binding chart-img-accounts \
  --project=${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"

# IAM: Logging
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/logging.logWriter"

# Secret: загрузить accounts JSON
echo '[{"id":"acc1","apiKey":"XXX","dailyLimit":44}]' | \
  gcloud secrets versions add chart-img-accounts --project=${PROJECT_ID} --data-file=-

# Firestore: chart_templates (пример через gcloud firestore export/import или консоль; для локальной загрузки можно использовать Python script)
# Firestore: chart_img_accounts_usage
# Firestore: flow_runs/{runId} c шагом READY (см. test_vectors/flow_run_ready_chart_step.json; подставить chartTemplateId и bucket)

# Деплой Eventarc/Cloud Run Functions отложен в T-024
```

## Risks

- Реальный Chart-IMG (mode=real) расходует лимиты; основное тестирование проводить в mock.
- Права bucket/Firestore можно сузить (objectCreator вместо objectAdmin), адаптировать под политику.
- Публичный bucket не обязателен в тестовой среде; учитывать требования безопасности.

## Verify Steps (T-023)

- CLI сценарии 2–6 на реальном GCP, фиксация exit code, Firestore патчей, наличия PNG/manifest в GCS.
- Eventarc сценарий вынесен в T-024.

## Rollback Plan

- Удалить тестовые документы из Firestore, объекты из GCS; при необходимости удалить роли/секреты/функцию.
