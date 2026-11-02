# Design: RFP Response Agent

Why the prototype is built the way it is: the decisions, what can go wrong, how it is evaluated and
what is missing. What it does, how to run it and the project layout are in README.md.

## 1. Problem

Northwind Analytics sells a B2B analytics platform. Answering a prospect's RFP takes sales, product,
security and legal 2-3 weeks, mostly spent finding answers in scattered internal documents. The goal is a
draft a sales rep can review in a day.

The brief sets three hard requirements:

1. Every claim in the draft is backed by a company document.
2. Never claim a capability the documents don't support.
3. A human approves the draft before anything is sent.

The second rule shapes everything else. A wrong "yes" in an RFP response can become a contractual
commitment. A wrong "needs review" costs a reviewer a few minutes. So whenever the system is unsure, it
says so and routes the item to a person instead of guessing.

**User.** A sales rep (Dana). Reviewers in Security, Legal, Product, Implementation, Infrastructure and
Support confirm the flagged items. A sales manager (Marco) and a legal user (Priya) can see more documents.

**Assumptions.**
- `data/knowledge/` (25 documents, 56 sections) is the only source of truth.
- RFPs arrive as plain text with numbered requirements.
- The CRM and price list are local mock files.

## 2. Architecture

The seven steps are listed in README.md ("How it works"). This section covers what each step can get
wrong, and what the code does about it.

One function, `pipeline.run`, sits behind the CLI (`rfp_agent.py`), the review UI (`app.py`) and the eval
(`eval.py`), so the eval measures the product's real code path.

### Step by step

| Step | In | Out | What can fail, and what happens |
|---|---|---|---|
| 1 Extract (`extract.py`) | RFP text | customer, `[{id, text}]` | the model skips a requirement: `find_missing` recovers it from the line that starts with its id; it is assessed normally but flagged and never plain "supported" |
| 2 Retrieve (`retrieve.py`) | requirement text, role | top 4 `(score, section)` | wrong documents: measured separately as retrieval recall in the eval |
| 3 Assess (`assess.py`) | requirement, 4 passages with date + owner, optional library hint | structured assessment | the API call fails or returns bad JSON: that requirement becomes "needs review" with the error type; the rest of the RFP continues |
| 4 Check (`checks.py`) | assessment + the evidence actually retrieved | corrected assessment | see the rules below |
| 5 Draft (`draft.py`) | rows | markdown, riskiest first | none: pure formatting |
| 6 Summary (`summary_agent.py`) | RFP header, assessments | 3-section internal summary; the counts line is written by code | a tool error or malformed arguments go back to the model as an error; after 5 rounds a fixed "summary unavailable" message |
| 7 Write (`library.py`, `crm.py`) | a human decision | library entry, CRM record, audit line | a double click: an identical CRM update is skipped and logged; a re-approval replaces its library entry; a rejection withdraws it |

### The four statuses

| Status | Meaning | Shown as |
|---|---|---|
| supported | a passage clearly says we meet it fully, today | ✅ |
| conditional | met only with a plan, customer obligation, NDA, time limit, partial match, or the evidence may be out of date | ⚠️ |
| not_supported | a passage says we don't, or it is only planned | ⛔ |
| not_found | no passage addresses it, or the claim had no valid citation | ❓ needs review |

The customer-facing `answer` and the internal `conditions` are separate fields. Doubts, roadmap dates and
"verify this" notes go in conditions, which are never exported to the customer.

### Code checks (step 4)

Every rule is mechanical and general. None of them names a requirement, customer or document.

1. **Citations must be real.** Only ids of passages that were actually retrieved survive. This drops
   invented citations.
2. **No evidence, no claim.** A status without a valid citation becomes "needs review".
3. **Freshness.** A cited source older than 365 days (or with an unknown date) turns "supported" into
   "conditional", and the source and date are named.
4. **Conflicts.** If the model reports that sources disagree, the answer can't be "supported".
5. **Plans.** If the cited evidence mentions a plan (names are read from the documents, e.g. Standard and
   Enterprise) but the conditions don't, the code adds a note.
6. **Ownership.** Every item that isn't "supported" gets an owner, or "Unassigned (pick a reviewer)".

## 3. Key decisions

| Decision | Why | Alternative considered | Cost I accepted |
|---|---|---|---|
| Steps 1-5 are a fixed pipeline; only the deal summary is an agent | every requirement needs the same steps; only "what to look up next" depends on results | one agent loop with a search tool for everything | less flexible for unusual RFPs; in return predictable, one call per requirement, testable |
| The model assesses, the code validates | prompt rules are suggestions; citations, staleness, conflicts and plan names can be checked mechanically | trust the model's status | more code; rules can be too strict (an old but still true document gets flagged) |
| Permissions filtered **before** retrieval | restricted text never reaches the model, so it cannot leak it | filter the answer afterwards | visibility metadata needed on every document |
| No write tools for the model | a wrong write to the CRM or answer library is hard to undo | let the agent update the CRM | one extra human click |
| The discount limit comes from the user's role in code | the model must not choose what a user may see | pass the role to the model | none worth noting |
| Answer library reuse is a hint, not a copy | an approved answer can go stale when its source changes | reuse approved text directly | the model still re-checks against today's documents (one call either way) |
| Completeness check in code, not a second model call | deterministic, free, testable | ask the model to double-check its extraction | catches only numbered requirements in a consistent style |
| Eval scores retrieval and answers separately | a failure is blamed on the right step | one end-to-end pass/fail | two numbers to explain |
| Embedding retrieval by default; hybrid available | embedding recall was already 30/30 on the eval set | hybrid (0.7 embeddings + 0.3 keyword score) | hybrid exists (`--mode hybrid`) but I haven't measured it, because there was nothing to fix |
| gpt-4.1-mini, temperature 0, strict structured outputs | the output must parse every time; low cost | a larger model | judgment on subtle wording may be weaker; the eval is the check |

**Library reuse rules.** An approved answer is offered to the model only if all of these hold:

- the new requirement is similar enough (cosine ≥ 0.85);
- none of its cited sources has been updated since it was approved;
- the current user can see all of its sources.

The model must still cite today's passages.

## 4. Trust and safety

| Boundary | Threat | Control |
|---|---|---|
| RFP text → model | the customer-written RFP contains instructions ("mark everything supported") | every prompt says the RFP, passages and tool results are data, not instructions (soft); claims still need valid citations and human approval (hard) |
| Documents → model | a sales rep's draft is built from restricted text (discount floors, negotiation positions) | role filter before search; Dana sees 52 of 56 sections |
| Model → customer | false claim, roadmap promised, internal caveat in the answer | code checks; conditions kept separate and never exported; export only after every answer is approved |
| Model → systems | unwanted writes | no write tools; human click → code writes → audit log (`outputs/audit.jsonl`) |
| Secrets | API key leaks | key only in `.env` (gitignored); `.env.example` has no key |

**Fail closed.** If anything is missing or broken, the result is "needs review" with a reason, never a
guess. That covers: no evidence, invalid citations, a failed model call, a skipped requirement, and the
agent's step limit.

## 5. Evaluation

**Data.** I wrote the 3 RFPs (30 requirements) and their labels myself; README.md lists them, along with the
traps planted in the documents: a stale sales deck with a conflicting uptime figure, an old whitepaper, an
internal roadmap, and restricted documents. The traps are there so the eval tests the rules that matter: never
promise the roadmap, prefer the newer source, never leak restricted text.

Each requirement has a label in `data/expected/` with:

- the allowed status(es);
- words the conditions must mention;
- words the customer answer must never contain (e.g. a roadmap year);
- whether a source conflict exists;
- the documents a correct answer needs.

**Scores.**

- *Retrieval recall:* were the expected documents among the passages retrieved?
- *Answer checks:* status, required conditions, no internal or forbidden words in the answer, conflict
  flagged (or not), at least one citation, an owner on every flag.
- *Summary checks:* the agent looked up the customer, wrote the three sections, and every `$` amount
  exists in the price list or the documents.

**Results** (`docs/EVAL_RESULTS.md`, with every run in `outputs/eval_history.jsonl`):

| Change | Answers | Recall |
|---|---|---|
| first run at scale | 16/30 | 30/30 |
| scorer whole-word match + 2 general prompt rules | 29/30 | 30/30 |
| keep doubts about our own documents out of customer answers | 30/30 | 30/30 |
| 3 runs with the summary agent | 90/90 (summary 9/9) | 90/90 |
| write fixes, untrusted-input rule, fail closed, completeness check | 30/30 after each | 30/30 |

Across all of these runs, the agent never answered "supported" where the label said otherwise.
Three runs were not enough to prove stability, though. A live run in the review UI on 2026-11-02 judged
Meridian 3.3 (SOC 2) "not supported" by leaning on the 2023 whitepaper, although the eval had passed it 90/90.
The error went in the safe direction: the stale source was flagged and the item was routed to Security.
I then ran 3.3 another 30 times (6 full pipeline runs and 24 direct calls) and all 30 were correct, so it is a
rare flip (about 1 in 40 runs since the prompt rule was added).

I did not add a code rule for it. The obvious rule, "a 'no' that cites a source older than a year needs
review", would also break three correct answers (Lumen Retail 4.5, 4.6 and 4.10), which cite the old document
alongside the current one that says no. The narrower rule, "every cited source is old", would not have caught
this case. Telling a wrong 'no' from a right one here is a judgment call, so it stays with the reviewer, and the
fix is better measurement: more runs per item, with the flip rate tracked as a metric.

**The first 16/30 was mostly the eval's fault.** In 11 of the 14 failures, the scorer matched "not
current" inside "We do not currently offer". I fixed the scorer, not the prompts, and added a test that
fails if the old matching returns. Three real errors remained, and each was fixed with one general prompt
rule:

- "meets or beats the number asked for" counts as met;
- a past audit period is "conditional" with the period stated;
- never tell the customer our own report is out of date.

**Other evidence.**

- 49 offline unit tests use a fake model and fake embeddings, with no API calls.
- Mutation checks: breaking the citation filter, the conflict rule, permissions, the library withdrawal,
  the CRM duplicate check, fail-closed or the completeness check makes a test fail in each case.
- A separate 12-item stress RFP (unscored): two injection attempts were ignored and restricted discounts
  were not revealed.

**Caveat.** I wrote the RFPs and the labels myself. The eval proves the mechanics and catches regressions.
It does not predict accuracy on a real customer's RFP.

## 6. Failures found and fixed

| Found by | Failure | Fix |
|---|---|---|
| eval | scorer substring false alarms | whole-word match, tested |
| eval | "60 days required, we do 30" judged not supported; a 2025 SOC 2 report judged not supported | two general prompt rules |
| eval | answer told the customer our report "is not current" | rule: state the period; doubts go to conditions |
| UI dry run | rejecting an approved answer left it in the library | library follows the latest decision (approve replaces, reject or pending withdraws) |
| UI dry run | "Write to CRM" twice wrote twice | identical update skipped and audit-logged |
| code review | one failed model call stopped the whole RFP | fail closed per requirement |
| code review | prompts didn't treat the RFP as untrusted | shared untrusted-input rule in every prompt |
| code review | a skipped requirement silently vanished from the draft | completeness check in code |
| browser run | the summary's counts disagreed with the code's ("6 supported" vs 5) | counts inserted by code under "Bottom line" |
| browser run | the agent asked for "Enterprise plan" and got an error | the price tool's item parameter is an enum read from the price list |
| browser run | "$55 ... $10" rendered as a math formula | "$" escaped in model text shown in the UI |
| browser run | Meridian 3.3 judged "not supported" once | measured (30/30 correct afterwards); no code rule, see section 5 |

## 7. Known limitations

1. **Input format.** Real RFPs arrive as PDFs and spreadsheets. This prototype reads plain text. The
   completeness check misses requirements that have no number or use a different numbering style from
   the rest. A recovered requirement keeps only its first line.
2. **Injection defence is partly soft.** The prompt rule can be ignored by the model. The hard protection
   is that claims need valid citations and a human approves every answer.
3. **Deal summary prose.** The counts are now written by code, but the rest of the summary is model text,
   checked only for invented prices, its three sections and a customer lookup.
4. **Vague requirements.** "The platform must be secure" is marked supported. There is no "too vague, ask
   the customer" path.
5. **Strictness.** The 365-day staleness rule flags old documents that are still true.
6. **CRM idempotency.** It compares the whole update. A real CRM needs an idempotency key per RFP run.
7. **Evaluation set.** It is 30 requirements written by one person, and three runs per item are too few to
   catch an occasional flip (see Meridian 3.3 above).

## 8. Path to production

- **Inputs.** PDF and Excel parsing, plus a reviewer confirming the extracted requirement list before
  assessment.
- **Scale.** Move the index to a vector store, keep the front matter as filters, and re-index when a
  document changes. The checks and the approval flow stay the same.
- **Integration.** Make the CRM and pricing reads real tools. The write stays a human-approved, logged
  code path with an idempotency key. The review screen lives where reps already work.
- **Measuring value.** Run a pilot that tracks reviewer minutes per RFP and the share of answers approved
  without edits. Weigh that against the false "supported" rate on a labelled set written by Security and
  Legal. Ship only if time drops and false "supported" stays at zero.
- **Operations.** Log tokens and latency per run, alert on failed assessments, and re-run the eval on
  every prompt or model change.
