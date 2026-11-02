# Evaluation results

Fill in after each change. Command: `.venv/bin/python eval.py` (add `--runs 3` for stability).

| Date | Change | Retrieval | Recall | Answer checks | Summary | Notes |
|------|--------|-----------|--------|---------------|---------|-------|
| Oct 30 | v1 steel thread (1 RFP, 3 docs) | embed | - | 3/5 | - | 3.2 internal tone, 3.4 missing Enterprise |
| Oct 30 | prompt fixes + temperature 0 + plan check | embed | - | 15/15 (3 runs) | - | |
| Nov 1 | 25 docs, 3 RFPs, permissions, library (first run at scale) | embed | 30/30 | 16/30 | not run | 11 fails are a scorer bug ("not current" matches "not currently"); real errors: 3.3 + R-12 SOC 2 judged not_supported (expected conditional), R-11 30-day deletion judged not_supported (expected supported). 0 false "supported". |
| Nov 1 | scorer: whole-word match; prompt: "meets or beats the number" + "past audit period -> conditional" | embed | 30/30 | 29/30 | not run | 0 false "supported". Remaining: 3.3 status right, but the answer tells the customer the report "is not current" (a caveat that belongs in conditions). |
| Nov 1 | prompt: never tell the customer our own report/document is out of date; state its period | embed | 30/30 | 30/30 | not run | 0 false "supported". 1 run only; stability (`--runs 3`) not yet checked. |
