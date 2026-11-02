# RFP Response Agent

Turns an incoming RFP into a draft response a sales rep can review in minutes. Every answer is
backed by a citation to an internal company document, and nothing goes to the customer, or into
the CRM, without a human approving it.

## How it works

```
RFP text
  -> 1. Extract requirements     structured outputs: customer + numbered requirements
  -> 2. Retrieve evidence         embeddings (or hybrid embeddings + keywords), top-k per requirement,
                                  only from documents the user is allowed to see
  -> 3. Assess each requirement   supported / conditional / not_supported / not_found
                                  + customer-facing answer, conditions, citations, conflict, owner
  -> 4. Code checks               invented citations dropped; no evidence -> needs review; stale source
                                  (> 1 year) or conflicting sources -> never "supported"; plan
                                  conditions enforced; every flag gets an owner
  -> 5. Draft for review          riskiest items first
  -> 6. Deal summary agent        decides whether to look up CRM / pricing (read-only tools)
  -> 7. Human approval            approved answers go to the answer library; CRM write needs a confirm
```

Steps 1-5 are a fixed pipeline: they are the same for every requirement. Step 6 is an agent
because what to look up depends on the results.

**Design rule: the model assesses, the code validates.** A wrong "yes" in an RFP can become a
contractual commitment, so mechanical rules live in code and anything without valid evidence is
flagged for a human.

## What the data covers

- `data/knowledge/`: 25 documents (56 sections) for a fictional company, Northwind Analytics.
  Each has `last_updated`, `owner` and `visibility`. Some are deliberately stale or conflicting
  (a 2024 sales deck promising 99.95% uptime, a 2023 whitepaper, a 2024 FAQ promising unlimited
  users), one is an internal roadmap (plans must never be promised), and two are restricted
  (discount policy, legal negotiation positions).
- `data/rfps/`: 3 RFPs, 30 requirements: Meridian Health (healthcare), Harbor Bank (financial
  services, EU), Lumen Retail (retail, Asia-Pacific).
- `data/expected/`: the correct outcome per requirement, used by the eval.
- `data/users.json`: Dana (sales rep), Marco (sales manager), Priya (legal).

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                                   # then put your OpenAI key in .env

.venv/bin/python rfp_agent.py                          # CLI: meridian, as Dana
.venv/bin/python rfp_agent.py --rfp harbor_bank --user marco --review
.venv/bin/streamlit run app.py                         # review UI in the browser
```

## Tests and evaluation

```bash
.venv/bin/python -m pytest -q                          # offline unit tests, no API calls
.venv/bin/python eval.py                               # all RFPs, scored against data/expected
.venv/bin/python eval.py --runs 3 --no-summary         # stability, cheaper
.venv/bin/python eval.py --mode hybrid                 # compare retrieval modes
.venv/bin/python eval.py --user marco                  # as a sales manager
```

The eval reports two scores so failures are blamed on the right step: **retrieval recall** (did we
find the documents a correct answer needs?) and **answer checks** (status, conditions, no internal
notes in the answer, conflicts, citations, owner). It also checks the summary agent never invents
a price. Results are appended to `outputs/eval_history.jsonl`; see `docs/EVAL_RESULTS.md`.

## Project layout

```
rfp_agent.py          CLI
app.py                Streamlit review UI
eval.py               evaluation
rfp/
  config.py           paths and settings
  llm.py              the only place that calls the API (structured outputs, cached embeddings)
  knowledge.py        documents, front matter, chunks, plan names
  permissions.py      who can see which documents (filtered before retrieval)
  retrieve.py         embedding / hybrid search
  extract.py          step 1
  assess.py           step 3
  checks.py           step 4
  draft.py            step 5
  summary_agent.py    step 6
  library.py          approved answers, reused only if their sources haven't changed
  crm.py              mock CRM and pricing; the write needs approval
  audit.py            append-only audit log
  scoring.py          eval scoring (unit-tested)
tests/                offline tests with a fake embedding and a fake model
```
