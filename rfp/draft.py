"""Step 5: the markdown draft a sales rep reviews. Riskiest items first; nothing is sent."""
ICON = {"supported": "✅ Supported", "conditional": "⚠️ Conditional",
        "not_supported": "⛔ Not supported", "not_found": "❓ Needs review"}
ORDER = {"not_found": 0, "not_supported": 1, "conditional": 2, "supported": 3}


def counts(rows):
    return {s: sum(r["status"] == s for r in rows) for s in ORDER}


def build(customer, rows, user, summary=None, calls_made=(), hidden=0):
    n = counts(rows)
    lines = [f"# DRAFT RFP Response: {customer} (NOT SENT, needs human approval)", "",
             f"Prepared for {user['name']} ({user['role']}). {len(rows)} requirements: "
             f"{n['supported']} supported, {n['conditional']} conditional, {n['not_supported']} not supported, "
             f"{n['not_found']} need review.", ""]
    if hidden:
        lines += [f"_{hidden} document sections were hidden by your permissions._", ""]
    if summary:
        lines += ["## Deal summary (internal)", "", summary, "",
                  f"_Looked up by the agent: {', '.join(calls_made) or 'nothing'}_", "", "---", ""]
    for r in sorted(rows, key=lambda r: ORDER[r["status"]]):
        lines += [f"## {r['id']}  {ICON[r['status']]}", f"> {r['text']}", "",
                  f"- **Draft answer:** {r['answer']}"]
        if r["conditions"]:
            lines.append(f"- **Conditions:** {r['conditions']}")
        if r.get("conflict"):
            lines.append(f"- **⚡ Conflicting sources:** {r['conflict']}")
        if r["status"] == "not_found":
            lines.append(f"- **Searched (no match):** {', '.join(r['searched'])}")
        else:
            lines.append(f"- **Evidence:** {', '.join(r['citations'])}")
        if r.get("reused_from"):
            lines.append(f"- **♻️ Reused approved answer:** {r['reused_from']}")
        if r.get("library_note"):
            lines.append(f"- **Library:** {r['library_note']}")
        if r["owner"]:
            lines.append(f"- **Confirm with:** {r['owner']}")
        lines.append("")
    return "\n".join(lines)
