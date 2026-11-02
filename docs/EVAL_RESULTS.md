# Evaluation results

Fill in after each change. Command: `.venv/bin/python eval.py` (add `--runs 3` for stability).

| Date | Change | Retrieval | Recall | Answer checks | Summary | Notes |
|------|--------|-----------|--------|---------------|---------|-------|
| Oct 30 | v1 steel thread (1 RFP, 3 docs) | embed | - | 3/5 | - | 3.2 internal tone, 3.4 missing Enterprise |
| Oct 30 | prompt fixes + temperature 0 + plan check | embed | - | 15/15 (3 runs) | - | |
| Nov 1 | 25 docs, 3 RFPs, permissions, library (first run at scale) | embed | 30/30 | 16/30 | not run | 11 fails are a scorer bug ("not current" matches "not currently"); real errors: 3.3 + R-12 SOC 2 judged not_supported (expected conditional), R-11 30-day deletion judged not_supported (expected supported). 0 false "supported". |
| Nov 1 | scorer: whole-word match; prompt: "meets or beats the number" + "past audit period -> conditional" | embed | 30/30 | 29/30 | not run | 0 false "supported". Remaining: 3.3 status right, but the answer tells the customer the report "is not current" (a caveat that belongs in conditions). |
| Nov 1 | prompt: never tell the customer our own report/document is out of date; state its period | embed | 30/30 | 30/30 | not run | 0 false "supported". 1 run only; stability (`--runs 3`) not yet checked. |
| Nov 1 | stability check, same code (`--runs 3`, with summary agent) | embed | 90/90 | 90/90 | 9/9 | no flaky items, no invented prices |
| Nov 1 | answer library follows the latest decision; identical CRM write skipped | embed | 30/30 | 30/30 | not run | write paths are not in the eval; covered by 3 new unit tests + a headless UI run |
| Nov 1 | untrusted-input rule in all prompts; failed model call -> needs review for that item | embed | 30/30 | 30/30 | 3/3 | separate 12-item stress RFP (own, unscored): two injection attempts ignored, restricted discounts not revealed |
| Nov 1 | extraction completeness check in code (skipped requirements recovered + flagged) | embed | 30/30 | 30/30 | not run | no false "missed" alarms; live Meridian run with 3.5 forced missing: recovered, not_supported, flagged |
| Nov 2 | summary counts written by code; price tool item names from the price list; "$" escaped in the UI | embed | 30/30 | 30/30 | 3/3 | every get_pricing call valid on the first try. Separate check of Meridian 3.3 (one live UI run had judged it not_supported): 30/30 conditional across 6 full pipeline runs + 24 direct assess calls; no code fix: the rules that would catch it also break three correct answers |
