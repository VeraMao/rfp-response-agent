# CLAUDE.md: RFP Response Agent

## What this project is
A prototype that turns a customer's RFP into a draft response a sales rep can review,
where every answer is backed by a citation to an internal company document.
Built as an interview case study by Vera (Jiaming) Mao. She must be able to explain
every file in an interview, so **simple, readable code beats clever code.**

Read first: `README.md`, `BRIEF.md`, `docs/ROADMAP.md` (the build plan).

## Commands
```bash
.venv/bin/python rfp_agent.py --rfp meridian --user dana   # CLI -> outputs/draft_meridian.md
.venv/bin/streamlit run app.py                            # review UI
.venv/bin/python eval.py --no-summary                     # eval over all RFPs (uses the API)
.venv/bin/python -m pytest -q                             # offline unit tests (no API calls)
```

## Non-negotiable rules
1. **Secrets:** never read, print, cat, grep or commit `.env`. Before every commit run
   `git status` and confirm `.env` is not staged.
2. **The model assesses, the code validates.** Mechanical rules (citations exist, stale
   sources, plan names, prices) live in code. Judgment lives in prompts.
3. **No false claims.** Anything without valid evidence becomes "needs review". A wrong
   "yes" is worse than a "needs review".
4. **Writes need a human.** The model never gets a write tool. Code proposes, a human
   approves, code writes, and the write is logged.
5. **No overfitting.** Never write logic that names a specific requirement id, customer,
   or test case. Rules must be general (e.g. plan names are read from the documents).
6. **Every behavior change is measured.** After each milestone: run pytest and eval, report
   the score, then commit. If a score drops, fix it before moving on.
7. **Model calls:** structured outputs with `strict: True`, `temperature=0`, model from
   `OPENAI_MODEL` (default gpt-4.1-mini). Keep API cost low: cache embeddings, `--runs 1`
   by default.
8. **Dependencies:** keep them minimal (openai, pytest, streamlit). Ask before adding others.

## Style
- Plain Python, small functions, a short docstring saying WHAT and a comment saying WHY
  for any non-obvious rule.
- Keep each step of the pipeline in its own small module once restructured (M1).
- DESIGN.md was drafted at Vera's request (2026-11-02); she owns it. Change it only when she asks.
  You may update README.md and docs/.
