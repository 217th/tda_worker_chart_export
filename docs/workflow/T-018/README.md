# T-018: Update symbol mapping via chartImgSymbolTemplate

## Summary

- Align specs and templates so `flow_run.scope.symbol` is a base symbol (e.g. `BTCUSDT`) and Chart‑IMG symbol is derived from a required template field `chartImgSymbolTemplate`.

## Goal

- Remove ambiguity between `BTC/USDT` and TradingView `EXCHANGE:SYMBOL` by making exchange mapping explicit in chart templates.

## Scope

- Update docs/specs to define `scope.symbol` format (`BTCUSDT`) and `chartImgSymbolTemplate` usage.
- Add `chartImgSymbolTemplate` to all chart templates (required field).
- Update test vectors to use `BTCUSDT` and document the mapping.
- Produce per‑file patch artifacts for external sync.

## Planned Scenarios (TDD)

### Scenario 1: scope.symbol is base symbol (BTCUSDT)

**Prerequisites**
- Updated flow_run schema and test vectors.
- Requires human-in-the-middle: NO

**Steps**
1) Read `flow_run.schema.json` and test vectors.

**Expected result**
- `scope.symbol` is documented/used as `BTCUSDT` (no slash).

### Scenario 2: chartImgSymbolTemplate required in templates

**Prerequisites**
- Updated chart templates and README.
- Requires human-in-the-middle: NO

**Steps**
1) Inspect chart templates and template README.

**Expected result**
- Each template contains `chartImgSymbolTemplate` (e.g. `BINANCE:{symbol}`) and it is marked required.

### Scenario 3: Chart‑IMG symbol derived from template

**Prerequisites**
- Updated implementation contract.
- Requires human-in-the-middle: NO

**Steps**
1) Read `implementation_contract.md` symbol section.

**Expected result**
- Worker derives `chartImgSymbol` from `chartImgSymbolTemplate` + `scope.symbol`.

### Scenario 4: Mock fixture key uses derived symbol

**Prerequisites**
- Updated mock/record section.
- Requires human-in-the-middle: NO

**Steps**
1) Read fixture naming rules.

**Expected result**
- Fixture key uses `chartImgSymbol` (after template substitution), not raw `scope.symbol`.

### Scenario 5: Patch files exist per document

**Prerequisites**
- Changes applied.
- Requires human-in-the-middle: NO

**Steps**
1) Inspect `docs/workflow/T-018/pr/patches/`.

**Expected result**
- There is one patch file per modified document.

## Risks

- Downstream consumers may still assume `BTC/USDT`; ensure tests and examples are updated.

## Verify Steps

- Check updated specs + patch artifacts.

## Rollback Plan

- Revert the commit; restore prior symbol semantics.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs-worker-chart-export/chart-templates/README.md`
- `docs-worker-chart-export/chart-templates/ctpl_price_ma1226_bb_macd1226_v1.json`
- `docs-worker-chart-export/chart-templates/ctpl_price_ma1226_vol_v1.json`
- `docs-worker-chart-export/chart-templates/ctpl_price_psar_adi_v1.json`
- `docs-worker-chart-export/chart-templates/ctpl_price_rsi14_stochrsi_v1.json`
- `docs-worker-chart-export/chart-templates/ctpl_price_vpvr_obv_v1.json`
- `docs-worker-chart-export/checklists/worker_chart_export.md`
- `docs-worker-chart-export/contracts/charts_images_naming.md`
- `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`
- `docs-worker-chart-export/contracts/flow_run.schema.json`
- `docs-worker-chart-export/questions/open_questions.md`
- `docs-worker-chart-export/spec/handoff_checklist.md`
- `docs-worker-chart-export/spec/implementation_contract.md`
- `docs-worker-chart-export/test_vectors/expected_flow_run_step_patch.json`
- `docs-worker-chart-export/test_vectors/expected_manifest.json`
- `docs-worker-chart-export/test_vectors/flow_run_ready_chart_step.json`
- `docs/workflow/T-018/pr/diffstat.txt`
- `docs/workflow/T-018/pr/meta.json`
- `docs/workflow/T-018/pr/patches/docs-worker-chart-export__chart-templates__README.md.patch`
- `docs/workflow/T-018/pr/patches/docs-worker-chart-export__chart-templates__ctpl_price_ma1226_bb_macd1226_v1.json.patch`
<!-- END AUTO SUMMARY -->
