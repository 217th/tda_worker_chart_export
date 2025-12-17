## docs-worker-chart-export — TDA Service Bundle (pilot)

Цель: собрать **ровно достаточную** спецификацию для реализации сервиса `worker-chart-export` отдельным агентом/проектом, не полагаясь на старый `docs/`.

### Входы/выходы (source of truth)
- Контракты:
  - `contracts/flow_run.schema.json` (входной документ `flow_runs/{runId}`)
  - `contracts/charts_outputs_manifest.schema.json` (выходной manifest)
  - `contracts/charts_images_naming.md` (правила именования PNG)
- Чеклист реализации:
  - `checklists/worker_chart_export.md`

### Что должен делать сервис
- Реагировать на изменения `flow_runs/{runId}` и брать в работу только `CHART_EXPORT` шаги со статусом `READY`.
- Писать PNG в GCS по соглашению именования.
- Писать `ChartsOutputsManifest` в GCS.
- Обновлять step в `flow_run` (status/outputs/error/finishedAt) по правилам оркестрации.

### Что не входит (пока)
- Спецификация внешнего Chart API и формат `chartTemplateId`/индикаторов (см. вопросы).

### Вопросы перед передачей в разработку
См. `questions/open_questions.md`.


