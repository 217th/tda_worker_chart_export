# T-018 — Implemented Scenarios (task-level)

This file lists the concrete scenarios implemented in this task. If some logic is incomplete, explicitly mark limitations.

Planned scenarios source:
- `docs/workflow/T-018/README.md` → **Planned Scenarios (TDD)**
- Each implemented scenario should map to a planned one (or explicitly note a justified deviation).

References:
- Spec(s):
  - `docs-worker-chart-export/spec/implementation_contract.md`
  - `docs-worker-chart-export/contracts/flow_run.schema.json`
  - `docs-worker-chart-export/chart-templates/README.md`

---

## 1) scope.symbol is base symbol (BTCUSDT)

**Scenario**
- `flow_run.scope.symbol` documented/used as base symbol without slash (e.g. `BTCUSDT`).

**Implemented in**
- `docs-worker-chart-export/contracts/flow_run.schema.json`
- `docs-worker-chart-export/test_vectors/flow_run_ready_chart_step.json`
- `docs-worker-chart-export/test_vectors/expected_manifest.json`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Inspect `flow_run.schema.json` symbol description.
2) Inspect test vectors for `scope.symbol` and `manifest.symbol` values.

**Expected result**
- `scope.symbol` is `BTCUSDT` (no slash) and manifest carries the same base symbol.

---

## 2) chartImgSymbolTemplate required in templates

**Scenario**
- Each chart template defines `chartImgSymbolTemplate` and README marks it as required.

**Implemented in**
- `docs-worker-chart-export/chart-templates/README.md`
- `docs-worker-chart-export/chart-templates/*.json`

**Limitations / stubs**
- All templates set `chartImgSymbolTemplate` to `BINANCE:{symbol}` (single exchange for now).

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Inspect `chart-templates/README.md` for required field.
2) Inspect each template JSON for `chartImgSymbolTemplate`.

**Expected result**
- Each template contains `chartImgSymbolTemplate` and README documents it as required.

---

## 3) Chart‑IMG symbol derived from template + scope.symbol

**Scenario**
- Worker derives `chartImgSymbol` from `chartImgSymbolTemplate` and base `scope.symbol`.

**Implemented in**
- `docs-worker-chart-export/spec/implementation_contract.md`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Inspect the symbol derivation rules in `implementation_contract.md`.

**Expected result**
- `chartImgSymbol` derivation is explicitly documented and required for Chart‑IMG calls.

---

## 4) Mock fixture key uses derived chartImgSymbol

**Scenario**
- Fixture key is based on `chartImgSymbol` (TradingView symbol), not raw `scope.symbol`.

**Implemented in**
- `docs-worker-chart-export/spec/implementation_contract.md`
- `docs-worker-chart-export/questions/open_questions.md`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Inspect fixture key description and naming examples.

**Expected result**
- Fixture naming explicitly references `chartImgSymbol`.

---

## 5) PNG naming uses base symbol slug

**Scenario**
- PNG naming uses `symbolSlug` derived from base `scope.symbol` (e.g. `BTCUSDT`).

**Implemented in**
- `docs-worker-chart-export/contracts/charts_images_naming.md`
- `docs-worker-chart-export/test_vectors/expected_manifest.json`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Inspect `charts_images_naming.md` example.
2) Inspect `expected_manifest.json` PNG path.

**Expected result**
- PNG name uses `BTCUSDT` (no slash, no exchange prefix).

---

## 6) Per-file patch artifacts exist

**Scenario**
- Each modified spec/template/vector file has its own patch file for external sync.

**Implemented in**
- `docs/workflow/T-018/pr/patches/*.patch`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) List patch files under `docs/workflow/T-018/pr/patches/`.

**Expected result**
- One patch file per modified document.
