# T-021 — Implemented Scenarios (task-level)

Planned scenarios source: `docs/workflow/T-021/README.md` → Planned Scenarios (TDD)

## 1) README покрывает ключевые разделы

**Scenario**
- Корневой `README.md` содержит все разделы, перечисленные в Scope (overview, quickstart, flow, config, stores, CLI, testing, deploy, observability, limitations, references).

**Implemented in**
- `README.md`

**Limitations / stubs**
- Разделы Deploy/Observability описаны как outline (детализация будет в T-012/T-013).

### Manual test

**Prerequisites**
- Нет
- Requires human-in-the-middle: NO

**Steps**
1) Открыть `README.md`.
2) Убедиться, что перечислены все разделы из Scope.

**Expected result**
- Все разделы присутствуют и согласованы с текущими контрактами.

## 2) README отражает ограничения и TODO

**Scenario**
- В разделе “Known limitations / TODO” перечислены незавершённые части (T-009–T-013, T-017/T-020, T-019).

**Implemented in**
- `README.md`

**Limitations / stubs**
- Список требует актуализации при закрытии связанных задач.

### Manual test

**Prerequisites**
- Нет
- Requires human-in-the-middle: NO

**Steps**
1) Открыть `README.md`.
2) Проверить блок “Known limitations / TODO”.

**Expected result**
- Блок содержит незавершённые элементы и ссылки на задачи.

## 3) README указывает ссылки на спецификации

**Scenario**
- В конце README приведён список ключевых спецификаций (`docs-worker-chart-export/*`, `docs-general/*`, `docs-gcp/*`).

**Implemented in**
- `README.md`

**Limitations / stubs**
- Ссылки требуют актуализации при добавлении новых документов.

### Manual test

**Prerequisites**
- Нет
- Requires human-in-the-middle: NO

**Steps**
1) Открыть `README.md`.
2) Проверить раздел “References”.

**Expected result**
- Перечислены актуальные документы; нет ссылок на запрещённые к правке каталоги.
