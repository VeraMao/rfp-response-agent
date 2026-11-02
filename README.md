# RFP Response Agent

Turns an incoming RFP into a draft response a sales rep can review in minutes. Every answer is
backed by a citation to an internal company document, and nothing goes to the customer, or into
the CRM, without a human approving it.

## How it works

```text
RFP text (untrusted: written by the customer)
 1 Extract        model, strict JSON -> customer + requirements with the RFP's own ids
   + check        code: every line numbered in the same style must be in the list; missing ones are
                  recovered from the text and flagged
 2 Retrieve       embeddings, top 4 sections per requirement, only from documents the user's role may see
 3 Assess         one model call per requirement -> status, answer, conditions, citations, conflict, owner
 4 Code checks    rfp/checks.py: the model assesses, the code validates
 5 Draft          markdown / UI cards, riskiest first
 6 Deal summary   the only agent: decides whether to look up the CRM and pricing (read-only tools, max 5 rounds)
 7 Human          edit, approve or reject each answer; export only when all are approved;
                  approved answers -> answer library; CRM write after an explicit confirmation; audit log
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

### Review UI

```bash
.venv/bin/streamlit run app.py
```

Then open http://localhost:8501. If the sidebar is hidden on a narrow window, use the `>>` arrow at the top left.

1. In the sidebar, pick an **RFP** (`meridian`, `harbor_bank` or `lumen_retail`) and a **Reviewer**:
   - Dana Lee (sales_rep)
   - Marco Ruiz (sales_manager)
   - Priya Shah (legal)

   The reviewer's role decides which documents are searched and the discount limit.
2. Click **Run agent**. It takes about 15-30 seconds (Meridian, 5 requirements: ~16 s; Harbor Bank, 13: ~31 s).
3. At the top of the result:
   - the count per status;
   - how many document sections were hidden by the reviewer's permissions;
   - the **Deal summary**, which lists what the agent looked up.
4. One card per requirement, riskiest first. Each card has:
   - the customer answer, which you can edit;
   - the internal conditions;
   - any source conflict;
   - **Evidence**: the cited sections, each with its date and owner;
   - who should confirm it;
   - Pending / Approve / Reject.

   Approving saves the answer to the answer library. Reject or Pending withdraws it again.
   Editing an approved answer sets it back to Pending: an approval covers one exact text.
5. **Export:** the download button appears only when every answer is approved. The file contains exactly the
   text that was approved, never the conditions.
6. **Update CRM:** shows the exact JSON to be written. Tick "I have reviewed this update", then click
   **Write to CRM**. An identical second write is skipped.

The UI writes to:
- `data/answer_library.json`, on approvals;
- `outputs/audit.jsonl`;
- `outputs/crm_updates.json`.

After a demo, restore the library with `git checkout -- data/answer_library.json`.

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

## Limitations

- **The reviewer picker is not authentication.** Anyone using the UI can pick the manager or legal role.
  Retrieval is filtered correctly for the role that is picked, so this shows role-aware retrieval, not
  production access control; in production the role would come from the company's sign-in (SSO).
- **Citations are checked, not proven.** The code checks that every cited section was actually retrieved
  and allowed for the role, and flags stale or conflicting sources. It cannot prove that a cited passage
  supports every sentence of the answer, so a human reviews every answer before it goes out.
- **The eval is small and self-made.** 30/30 is on three fictional RFPs with labels written for this prototype. It shows the
  pipeline works and that fixes didn't break anything; it is not a general accuracy number.
- **Plain text input only.** Real RFPs arrive as PDFs and spreadsheets; the completeness check only
  catches requirements numbered in one consistent style.

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
