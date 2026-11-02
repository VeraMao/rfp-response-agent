"""The whole flow, used by the CLI, the UI and the eval.

RFP -> 1 extract -> 2 retrieve (only what the user may see) -> 3 assess -> 4 code checks
    -> 5 draft -> 6 deal summary agent.  Step 7 (CRM write) happens outside, after human approval.
"""
from rfp import assess, checks, config, extract, knowledge, library, permissions, retrieve, summary_agent


def build_index():
    return retrieve.Index(knowledge.load_chunks())


def extract_requirements(rfp_text, log=print):
    """Step 1 plus a completeness check in code: (customer, requirements, ids recovered by code)."""
    extracted = extract.extract(rfp_text)
    missing = extract.find_missing(rfp_text, extracted["requirements"])
    if missing:
        log(f"Step 1: extraction missed {[m['id'] for m in missing]}; recovered from the RFP text")
    return extracted["customer"], extracted["requirements"] + missing, {m["id"] for m in missing}


def assess_requirements(requirements, index, user, use_library=True, log=print, today=None, recovered=()):
    role = user["role"]
    plans = knowledge.plan_names(permissions.visible(index.chunks, role))
    entries = library.load() if use_library else []
    chunks_by_id = {c["id"]: c for c in index.chunks}
    rows = []
    for req in requirements:
        evidence = index.search(req["text"], role)
        hint = reused = note = None
        match = library.find(req["text"], entries, index.embed_fn)
        if match:
            ok, note = library.usable(match[1], chunks_by_id, role)
            if ok:
                hint, reused = library.hint(match[1]), match[1]["id"]
        try:
            assessed = assess.assess(req, evidence, hint, today)
        except Exception as exc:          # fail closed: one bad call must not stop the RFP or pass silently
            log(f"[{req['id']}] assessment failed: {type(exc).__name__}: {exc}")
            assessed = checks.failed_assessment(exc)
        result = checks.check(assessed, evidence, plans, today)
        if req["id"] in recovered:
            result = checks.flag_recovered(result)
        result.update(searched=[c["id"] for _, c in evidence], reused_from=reused, library_note=note)
        log(f"[{req['id']}] {result['status']:<13} {result['citations']}"
            f"{'  (reused ' + reused + ')' if reused else ''}")
        rows.append({**req, **result})
    return rows


def run(rfp_name, user_id, with_summary=True, use_library=True, index=None, log=print):
    rfp_text = (config.RFPS / f"{rfp_name}.txt").read_text()
    user = permissions.get_user(user_id)
    customer, requirements, recovered = extract_requirements(rfp_text, log)
    customer = customer or rfp_name
    log(f"Step 1: {customer}: {len(requirements)} requirements")
    index = index or build_index()
    rows = assess_requirements(requirements, index, user, use_library, log, recovered=recovered)
    summary, calls = None, []
    if with_summary:
        log("Step 6: deal summary agent")
        header = "\n".join(rfp_text.splitlines()[:4])
        summary, calls = summary_agent.run(header, customer, rows, user, log)
    return {"rfp": rfp_name, "customer": customer, "user": user, "rows": rows, "summary": summary,
            "calls": calls, "hidden": index.hidden_count(user["role"])}
