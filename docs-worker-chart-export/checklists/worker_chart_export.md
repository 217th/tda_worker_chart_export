# CHART_EXPORT Worker — Checklist

- Inputs: `requests[]` with `chartTemplateId`; `minImages`; `scope.symbol` (базовый, например `BTCUSDT`) и `timeframe` из шага. См. `docs-worker-chart-export/contracts/flow_run.schema.json`.
- Outputs: PNG files per naming rule (`docs-worker-chart-export/contracts/charts_images_naming.md`); manifest at `runs/<runId>/steps/<stepId>/charts/manifest.json` obeying `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`.
- Success rule: SUCCEEDED when `len(items) >= minImages`; otherwise FAILED. См. `docs-general/contracts/orchestration_rules.md`.
- Idempotency: manifest path детерминированный для `runId+stepId`. На retry воркер должен обеспечивать консистентность: перезаписывать manifest детерминированно и, по возможности, не плодить “лишние” PNG (или гарантировать, что downstream использует только `manifest.items[]`).
- Error handling: populate `failures[]` in manifest with codes/messages; set step `error` when below threshold.
- External Chart API: Chart-IMG API v2, TradingView Snapshot v2 Advanced Chart (`POST https://api.chart-img.com/v2/tradingview/advanced-chart` с JSON-body и заголовком `x-api-key`); воркер не передаёт OHLCV, только `chartImgSymbol`/`interval` (где `chartImgSymbol` получен из `chartImgSymbolTemplate` + `scope.symbol`) и настройки из `chartTemplateId`; поддерживаются несколько API-ключей с per-account логированием.
- Performance / limits: parallelize chart renders but cap to per-account daily limit (~44 req/day per key) and handle 429/5xx with bounded retries/backoff и переключением между ключами.
- Testing: validate manifest with ajv; verify READY promotion of dependent steps after SUCCEEDED.
- Cloud Run Functions specifics: Firestore update event (Eventarc) trigger; retries только при идемпотентности; concurrency=1; timeout под latency внешнего Chart API; runtime SA с доступом к Firestore + GCS; VPC connector если egress должен быть контролируемым.
