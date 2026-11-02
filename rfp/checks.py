"""Step 4: the model assesses, the code validates. Every rule here is mechanical and general."""
import re

from rfp import config, knowledge


def check(result, evidence, plans, today=None):
    """Fix or flag the model's assessment of one requirement. `evidence` = [(score, chunk), ...]."""
    by_id = {c["id"]: c for _, c in evidence}

    # 1. Only passages we actually retrieved can be cited (drops invented citations).
    result["citations"] = [c for c in result["citations"] if c in by_id]

    # 2. Any claim, yes or no, needs evidence. Without it, a human must look.
    if result["status"] != "not_found" and not result["citations"]:
        result["conditions"] = "The model gave a status but cited no valid passage."
        result["status"] = "not_found"

    # 3. Freshness: a claim resting on an old source is not a firm "yes".
    stale = [c for c in result["citations"] if knowledge.age_days(by_id[c]["updated"], today) > config.STALE_DAYS]
    if stale:
        note = " ".join(f"Source {c} was last updated {by_id[c]['updated']}; confirm it is still accurate."
                        for c in stale)
        result["conditions"] = f"{result['conditions'] or ''} {note}".strip()
        if result["status"] == "supported":
            result["status"] = "conditional"

    # 4. Conflicting sources: a human decides, so never a plain "supported".
    if result["conflict"] and result["status"] == "supported":
        result["status"] = "conditional"

    # 5. A plan named in the cited evidence but missing from the conditions is easy to miss and costly.
    if result["status"] == "conditional":
        result["conditions"] = result["conditions"] or "Conditional, but no condition stated. Check manually."
        cited = " ".join(by_id[c]["text"] for c in result["citations"])
        mentioned = [p for p in plans if re.search(rf"\b{p}\b", cited)]
        if mentioned and not any(p.lower() in result["conditions"].lower() for p in plans):
            result["conditions"] += (f" Check plan requirement: the cited evidence mentions the "
                                     f"{' / '.join(mentioned)} plan.")

    # 6. Every flagged item needs a person.
    if result["status"] != "supported" and not result["owner"]:
        result["owner"] = "Unassigned (pick a reviewer)"
    return result
