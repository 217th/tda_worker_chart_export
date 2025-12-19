# T-022: Core engine wiring

## Summary

- Реализовать `run_chart_export_step` как единый энд‑ту‑энд пайплайн CHART_EXPORT, связывающий блоки из T-003..T-008. Обеспечить полноценное выполнение как из CloudEvent, так и из CLI.

## Goal

- После задачи CLI и CloudEvent адаптеры должны выполнять реальную работу: claim шага, вызов Chart-IMG (или mock/record), запись PNG/manifest в GCS, корректный финал статуса.

## Scope

- `run_chart_export_step(flow_run, step_id, config)`: детерминированный выбор шага (если не указан), валидация входа, claim RUNNING, построение chart requests, выбор аккаунта/usage, вызов Chart-IMG с ретраями, сбор items/failures, запись PNG/manifest (gs://), вычисление статуса по minImages, finalize шаг SUCCEEDED/FAILED.
- Логирование ключевых событий без утечек секретов.
- Возврат `CoreResult` с полями status, runId, stepId, outputsManifestGcsUri, itemsCount, failuresCount, minImages, errorCode.
- Идемпотентность: повторный вызов на уже RUNNING/SUCCEEDED/FAILED не портит состояние.
- CLI и CloudEvent используют тот же core (никаких ветвлений).

## Planned Scenarios (TDD)

### Scenario 1: Happy path real/mock — SUCCEEDED
**Prerequisites**
- flow_run с одним READY шагом CHART_EXPORT, корректные templates и accounts, CHARTS_API_MODE=mock (или real с валидным ключом), GCS доступен.
- Requires human-in-the-middle: NO (mock) / YES (real key).

**Steps**
1) Запустить core через CLI или тестовый вызов с данным flow_run.

**Expected result**
- Claim READY→RUNNING, вызов Chart-IMG, PNG+manifest записаны, status=SUCCEEDED, outputsManifestGcsUri установлен, itemsCount>=minImages.

### Scenario 2: Invalid stepId / нет READY — VALIDATION_FAILED
**Prerequisites**
- flow_run без указанного шага или шаг не CHART_EXPORT/не READY.

**Steps**
1) Запуск core с невалидным stepId или без READY шагов.

**Expected result**
- status=FAILED, errorCode=VALIDATION_FAILED, никаких сетевых/GCS вызовов, finalize не портит шаги.

### Scenario 3: Duplicate chartTemplateId или minImages>len(requests)
**Prerequisites**
- flow_run.inputs.requests с дубликатами либо minImages превышает количество запросов.

**Steps**
1) Запуск core.

**Expected result**
- status=FAILED, errorCode=VALIDATION_FAILED, manifest не пишется, finalize фиксирует ошибку.

### Scenario 4: Template missing / chartImgSymbolTemplate invalid
**Prerequisites**
- Один запрос с отсутствующим template или chartImgSymbolTemplate без {symbol}.

**Steps**
1) Запуск core.

**Expected result**
- failures[] содержит VALIDATION_FAILED для этого запроса; по minImages вычисляется итоговый статус (может быть FAILED если minImages не выполнен).

### Scenario 5: Account limit exhaustion / 429
**Prerequisites**
- accounts_usage у всех аккаунтов указывает, что dailyLimit исчерпан (или смоделировать 429).

**Steps**
1) Запуск core.

**Expected result**
- errorCode=CHART_API_LIMIT_EXCEEDED; Chart-IMG не вызывается (при полной исчерпанности) или вызывается до 429 и помечает аккаунт exhausted; finalize=FAILED.

### Scenario 6: Chart-IMG 4xx/5xx/non-PNG
**Prerequisites**
- Смоделировать ответ 4xx/5xx или 200 non-PNG (mock/fixture).

**Steps**
1) Запуск core.

**Expected result**
- failures[] с error.code=CHART_API_FAILED (или CHART_API_LIMIT_EXCEEDED для 429), retries уважают лимит, итоговый статус по minImages.

### Scenario 7: GCS write fail / manifest validation fail
**Prerequisites**
- Смоделировать ошибку загрузки PNG или manifest; отдельный кейс — невалидный manifest.

**Steps**
1) Запуск core.

**Expected result**
- PNG фейл → failure с GCS_WRITE_FAILED; manifest write фейл → MANIFEST_WRITE_FAILED; schema fail → VALIDATION_FAILED; статус по minImages/ошибке.

### Scenario 8: Idempotent retry (already RUNNING/SUCCEEDED/FAILED)
**Prerequisites**
- flow_run со шагом в RUNNING/SUCCEEDED/FAILED.

**Steps**
1) Повторно вызвать core.

**Expected result**
- Без изменений/ошибок; возвращает текущее состояние, не затирает поля.

### Scenario 9: Metrics/logs fields present, no secrets
**Prerequisites**
- Любой успешный/неуспешный сценарий.

**Steps**
1) Проверить логи на поля (runId, stepId, eventId?, error.code, chartsApi.accountId/httpStatus/durationMs/chartTemplateId/mode/fixtureKey) и отсутствие apiKey/секретов.

**Expected result**
- Структурированные логи соответствуют контракту; секреты отсутствуют.

## Acceptance Criteria

- `run_chart_export_step` выполняет end-to-end пайплайн и возвращает CoreResult с заполненными полями.
- CLI и CloudEvent пути используют один и тот же core без расхождений.
- Все Planned Scenarios можно воспроизвести (mock/fixtures для сетевых/GCS ошибок).

## Risks

- Несогласованность статусов/кодов ошибок между шагами (templates/accounts/GCS). Нужны единые маппинги.
- Транзакции Firestore при высоком конкурентном трафике (ABORTED) — нужны ретраи/идемпотентность.

## Verify Steps

- Unit/regression: добавить/обновить тесты (T-010) для core path.
- Integration (mock/fake): прогон сценариев с fake Firestore/GCS (T-011/T-020 harness).

## Rollback Plan

- Revert core wiring; CLI/CloudEvent останутся с NotImplemented, как сейчас.
