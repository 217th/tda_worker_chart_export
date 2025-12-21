# Входные данные

- `c4-diagram.xml` (формат draw.io) / `c4-diagram-pdf` - запроектированная мной схема компонентов/контейнеров
- `user_flows.md` - описанное мной видение воркфлоу (по мере убывания очерёдности реализации)
- `flowrun_plan` - ПРЕДВАРИТЕЛЬНЫЙ документ, с которого началась выработка архитектуры, может быть неактуальным, оставлен для истории
- `gcp_links.md` - неполный, собранный вручную список ссылок на документацию по сервисам Google Cloud, участвующим в разработке и запуске event-driven приложений

# Contracts (prototype)

Здесь лежат **контракты данных** для прототипа:

- Firestore документ `flow_runs/{runId}`: `schemas/flow_run.schema.json`
- GCS manifest’ы (когда шаг пишет **много файлов**): `schemas/*_manifest.schema.json`
- OHLCV export файл (метаданные + данные): `schemas/ohlcv_export_file.schema.json`
- LLM report/recommendation файл (метаданные + summary + details): `schemas/llm_*_file.schema.json`

## Общие соглашения

- **URI в GCS**: поле `gcs_uri` всегда в формате `gcs://<bucket>/<path>`.
- **Signed URL** (если нужен UI/шаринг): храним в Firestore только `signed_url` + `expires_at`, не считаем его каноническим.
- **JSON Schema**: draft `2020-12` (совместимо с OpenAPI 3.1).

## Рекомендованные пути в GCS (конвенция)

Формально схема путей не валидируется JSON Schema, но для читабельности и отладки придерживаемся:

- `runs/<runId>/ohlcv/<timeframe>.json`
- `charts/<runId>/<stepId>/manifest.json`
- `charts/<runId>/<stepId>/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`
- `runs/<runId>/reports/<timeframe>/<stepId>.json`
- `runs/<runId>/recommendations/<stepId>.json`

Подробнее: см. `docs/contracts/charts_images_naming.md`

## Content-Type (рекомендация)

- OHLCV export: `application/json`
- Chart PNG: `image/png`
- Manifest JSON: `application/json`
- LLM report/recommendation: `application/json` (внутри `summary.markdown`/`summary.html`)


