# Lessons Learned: Firestore 409 Too much contention on these documents

## Краткое резюме
При локальном запуске `worker_chart_export` (CLI `run-local`) мы получали ошибку:
`google.api_core.exceptions.Aborted: 409 Too much contention on these documents` при
`claim` и `finalize` шагов, а также при учёте usage‑документов.
Проблема не была вызвана параллельными процессами — единственный писатель в audit‑логах был пользователь.
Решение: убрать Firestore‑транзакции и перейти на **optimistic update** с precondition (`update_time`)
и короткими ретраями.

## Симптомы
- Ошибка `Aborted (409)` на `transaction.commit()` при попытке записать:
  - `flow_runs/{runId}` (claim/finalize)
  - `chart_img_accounts_usage/{accountId}` (usage)
- В audit‑логах:
  - `BeginTransaction`
  - `BatchGetDocuments`
  - `Commit` с `status.code=10` (Aborted), `processingDuration ~19s`
  - `Rollback`
- Параллельные процессы отсутствовали (Eventarc/Functions/Cloud Run/Scheduler — пусто).

## Диагностика (что подтвердили)
1) **Нет внешних писателей**:
   - `gcloud eventarc triggers list` → 0
   - `gcloud functions list --gen2` → 0
   - `gcloud run services list` → 0
   - `gcloud scheduler jobs list` → 0
2) **Audit logs** показали, что писатель один и тот же (principalEmail = пользователь).
3) **Прямой update без транзакции** работает:
   ```bash
   python -c "from google.cloud import firestore; client=firestore.Client(database='tda-db'); doc=client.collection('flow_runs').document('...'); doc.update({'steps.<stepId>.status':'RUNNING'}); print('updated')"
   ```
   Это исключает проблему со схемой/документом.

## Вывод по причине
Проблема связана с **нестабильностью транзакций** в данной среде/базе:
commit транзакции длится долго и завершаетcя `Aborted` даже без конкурентов.
Это не ошибка схемы и не конфликт от сторонних процессов.

## Решение (применено)
Переведены ВСЕ записи в Firestore с транзакций на optimistic update:

1) **Claim шага (flow_runs/{runId})**
   - Чтение snapshot
   - Проверка `status == READY`
   - `doc_ref.update(update, option=write_option(last_update_time=snapshot.update_time))`
   - Ретраи (3 попытки, backoff 0.2 / 0.4 / 0.8s)
   - Если precondition fail → no‑op (claimed=false)

2) **Finalize шага (flow_runs/{runId})**
   - Аналогично claim: update по precondition
   - Если шаг уже final → no‑op
   - Если статус не RUNNING → no‑op

3) **Usage accounting (chart_img_accounts_usage/{accountId})**
   - `_try_claim_account`: increment usage через precondition
   - `mark_account_exhausted`: обновление usageToday через precondition
   - При precondition‑fail: retry, затем best‑effort/no‑op

## Изменения в коде
- `worker_chart_export/orchestration.py`
  - `claim_step_transaction` → optimistic update + retry + INFO‑лог `firestore_claim_precondition_failed`
  - `finalize_step` → optimistic update + retry + INFO‑лог `firestore_finalize_precondition_failed`
- `worker_chart_export/usage.py`
  - `_try_claim_account` → optimistic update + retry
  - `mark_account_exhausted` → optimistic update + retry
  - событие `chart_api_usage_claim_conflict` при конфликте

## Проверки и тесты
- `tests/tasks/T-004/test_orchestration.py` (finalize/claim invariants)
- `tests/tasks/T-006/test_usage.py` (usage selection)
- `tests/tasks/T-023/test_orchestration_claim.py` (claim precondition)

Все тесты прошли.

## Практические рекомендации
1) **Избегать транзакций** на горячих/крупных документах `flow_runs`.
2) Использовать **precondition по update_time** для атомарного claim/finalize.
3) Делать короткие ретраи с backoff.
4) Для диагностики использовать audit‑логи:
   - `google.firestore.v1.Firestore.Commit`
   - `status.code=10` (Aborted)
   - `principalEmail` для выявления писателей
5) Если всё же нужны транзакции:
   - применять официальный `@firestore.transactional`
   - минимизировать длительность транзакции (никаких сетевых вызовов внутри)

## Открытые вопросы
- Нужна ли дополнительная метрика/алерт по `firestore_*_precondition_failed`?
- Нужна ли политика отдельного документа под часто меняющиеся поля (если flow_runs начнут активно обновляться)?
