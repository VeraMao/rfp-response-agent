# Roadmap: from steel thread to a realistic prototype

**Status (Nov 2): all milestones below are built and committed. 53 offline tests pass; the eval
scores 30/30 on retrieval recall and 30/30 on answer checks (see docs/EVAL_RESULTS.md).
This file is kept as the original build plan; for the current design see README.md.**

Work through the milestones in order. Each milestone ends with: pytest green, eval score
reported, README updated, one git commit with the score in the message.

---

## M0 - Baseline (15 min)
- Run `eval.py --runs 3`. Fix anything failing from the latest changes (B: conflicts/freshness).
- First commit: `v2: pipeline + summary agent + conflicts/freshness (eval X/Y)`.

## M1 - Restructure without changing behavior (1 h)
- Move code into a package `rfp/`: `llm.py` (ask_json, client), `knowledge.py` (front matter,
  chunking, embedding cache), `retrieve.py`, `assess.py`, `checks.py`, `draft.py`,
  `summary_agent.py`, `crm.py` (tools + approved write). Keep `rfp_agent.py` and `eval.py`
  as thin entry points.
- Cache embeddings on disk (`.cache/embeddings.json`, keyed by a hash of the chunk text)
  so repeated runs don't re-embed. Add `.cache/` to .gitignore.
- Add `tests/` with offline pytest tests (fake model results, no API): check() drops invented
  citations, stale source downgrades supported, plan-name rule, price-invention check,
  front-matter parsing.
- Acceptance: eval score unchanged, pytest green.

## M2 - Scale: realistic knowledge base + more RFPs (2-3 h)  [roadmap item A]
- Grow `data/knowledge/` to ~25 documents across: product, security, compliance, legal
  (MSA, DPA), implementation, support/SLA, pricing policy, integrations, data residency,
  accessibility, plus 3-4 deliberately stale or conflicting marketing docs. All fictional
  company "Northwind Analytics". Each with front matter (last_updated, owner, visibility).
- Add `data/rfps/` with 3 RFPs of 10-15 requirements each, from different industries
  (healthcare, financial services, retail). Include: synonyms ("SAML" vs "SSO"),
  requirements needing two documents, things the docs don't cover, conflicts, stale facts.
- One expected file per RFP: `data/expected/<rfp>.json` with status, conditions_must_mention,
  answer_must_not_mention, conflict, and **expected_evidence** (doc ids that should be retrieved).
- eval.py: `--rfp <name>` or all; add **retrieval recall@k** (did we retrieve the expected
  evidence?) separately from answer correctness, so failures can be blamed on retrieval
  vs assessment.
- Retrieval: if recall is low, try hybrid search (embeddings + a simple keyword score,
  combined) and report before/after numbers. Keep whichever is better, note the trade-off.
- Acceptance: eval runs over all 3 RFPs and prints per-RFP and overall scores + recall.

## M3 - Learning loop: approved answers are reused (1-2 h)  [roadmap item A]
- `data/answer_library.json`: answers a human approved (requirement text, answer, citations,
  approved_by, approved_on).
- When a reviewer approves an answer (CLI now, UI in M5), save it to the library.
- Retrieval also searches the library; a close match is shown to the model as a previously
  approved answer (with its date) and is still checked against current documents
  (a library answer older than its source documents is treated as stale).
- Acceptance: run RFP 1, approve answers, run RFP 2 with an overlapping requirement and show
  the reused answer + citation in the draft. Add an eval check for reuse.

## M4 - Permissions (1-2 h)  [roadmap item C]
- `data/users.json`: users with roles: sales_rep, sales_manager, legal.
- Document front matter `visibility`: public | internal | restricted (e.g. discount floors,
  legal negotiation positions are restricted to sales_manager / legal).
- **Filter before retrieval**, so restricted text never reaches the model for a user who
  can't see it. get_pricing returns list price to reps; discount floors only to managers.
- CLI flag `--user <id>`. Draft shows "some sources hidden by your permissions" when relevant.
- Acceptance: pytest proves a sales_rep can never retrieve a restricted chunk; eval runs as
  a sales_rep and as a manager.

## M5 - Review UI (2-3 h)  [roadmap item D]
- `app.py` with Streamlit: pick an RFP and a user, run the pipeline, show the summary and a
  list of requirements with status badges (risky first), conflicts highlighted, evidence in
  expanders, editable answer text, Approve / Reject per requirement.
- Export the final response (markdown) only when every requirement is approved.
- The CRM update button shows exactly what will be written and needs a confirm click.
- Audit log `outputs/audit.jsonl`: who approved/edited what, when.
- Acceptance: a full demo flow in the browser in under 3 minutes.

## M6 - Polish for the presentation (1 h)
- README: architecture diagram, how to run the UI, eval results table per milestone.
- `docs/EVAL_RESULTS.md`: scores after each milestone (the story of improvement).
