# T-018 — Scenarios Verification Report

Source checklist: `docs/workflow/T-018/pr/scenarios.md`

Date: 2025-12-18
Environment: local dev (no external services)

## Scenario 1) scope.symbol is base symbol (BTCUSDT)

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "BTCUSDT" docs-worker-chart-export/contracts/flow_run.schema.json docs-worker-chart-export/test_vectors/flow_run_ready_chart_step.json docs-worker-chart-export/test_vectors/expected_manifest.json`

**Results**
- Pass. Output:
  - `flow_run.schema.json` description references `BTCUSDT`
  - test vectors use `BTCUSDT` for `scope.symbol` and manifest symbol

## Scenario 2) chartImgSymbolTemplate required in templates

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "chartImgSymbolTemplate" docs-worker-chart-export/chart-templates/README.md docs-worker-chart-export/chart-templates/*.json`

**Results**
- Pass. Output shows README requirement and field present in all template JSON files.

## Scenario 3) Chart‑IMG symbol derived from template + scope.symbol

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "chartImgSymbol" docs-worker-chart-export/spec/implementation_contract.md`

**Results**
- Pass. `implementation_contract.md` documents derivation and validation.

## Scenario 4) Mock fixture key uses derived chartImgSymbol

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "chartImgSymbol" docs-worker-chart-export/spec/implementation_contract.md docs-worker-chart-export/questions/open_questions.md`

**Results**
- Pass. Fixture key references `chartImgSymbol`.

## Scenario 5) PNG naming uses base symbol slug

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "BTCUSDT" docs-worker-chart-export/contracts/charts_images_naming.md docs-worker-chart-export/test_vectors/expected_manifest.json`

**Results**
- Pass. PNG naming examples use `BTCUSDT`.

## Scenario 6) Per-file patch artifacts exist

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `ls docs/workflow/T-018/pr/patches`

**Results**
- Pass. Patch files exist for each modified document.

## Human-in-the-middle required scenarios

- None for this task.

## Fixes required during verification

- None.
