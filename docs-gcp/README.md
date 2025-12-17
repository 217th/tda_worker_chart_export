## docs-gcp — TDA Platform (GCP) Bundle

Этот бандл предназначен для platform/GCP-агента (или команды), которая отвечает за:
- инфраструктуру (Firestore, GCS, Secret Manager)
- деплой Cloud Run Functions (gen2)
- Eventarc/Firestore triggers
- Cloud Scheduler
- IAM bindings и правила доступа

### Содержимое
- `runbook/prod_runbook_gcp.md`: основной runbook по прод окружению.
- `links/gcp_links.md`: ссылки на официальную документацию.

### Примечание
По мере миграции все ссылки внутри runbook должны вести на `docs-general/...` и service bundles, а не на старый `docs/...`.


