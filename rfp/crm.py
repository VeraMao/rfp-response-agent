"""Mock CRM and price list. Reads are tools for the agent; the write needs a human."""
import json
from datetime import date

from rfp import audit, config


def _load(name):
    return json.loads((config.DATA / name).read_text())


def get_customer(name):
    crm = _load("crm.json")
    if name not in crm:
        return {"error": f"No CRM account named '{name}'. Known accounts: {sorted(crm)}"}
    return {"name": name, **crm[name]}


def get_pricing(item, role):
    """List prices are visible to everyone; each role sees only its own discount limit."""
    pricing = _load("pricing.json")
    if item not in pricing["items"]:
        return {"error": f"No pricing for '{item}'. Known items: {sorted(pricing['items'])}"}
    result = {"item": item, **pricing["items"][item]}
    limit = pricing["discount_limits_pct"].get(role)
    if limit is not None:
        result["your_max_discount_pct"] = limit
    return result


def known_price_numbers():
    """Every number in the price list; used by eval to catch invented prices."""
    pricing = _load("pricing.json")
    nums = {v for item in pricing["items"].values() for v in item.values() if isinstance(v, (int, float))}
    return nums | set(pricing["discount_limits_pct"].values())


def propose_update(customer, rows):
    from rfp.draft import counts
    n = counts(rows)
    return {"account": customer, "activity": "RFP draft prepared", "date": date.today().isoformat(),
            "summary": f"{n['supported']} supported, {n['conditional']} conditional, "
                       f"{n['not_supported']} not supported, {n['not_found']} need review",
            "open_items": [f"{r['id']} -> {r['owner']}" for r in rows if r["status"] != "supported"]}


def write_update(update, approver):
    """Only called after a human approved. Writes to a file that stands in for the CRM.
    Returns (file, written). An update identical to one already written is skipped, so a double
    click or a re-run never creates a duplicate record in the system of record."""
    log_file = config.OUTPUTS / "crm_updates.json"
    entries = json.loads(log_file.read_text()) if log_file.is_file() else []
    if any({k: e.get(k) for k in update} == update for e in entries):
        audit.log("crm_write_skipped_duplicate", approver, account=update["account"])
        return log_file, False
    entries.append({**update, "approved_by": approver})
    config.OUTPUTS.mkdir(exist_ok=True)
    log_file.write_text(json.dumps(entries, indent=2) + "\n")
    audit.log("crm_write", approver, account=update["account"])
    return log_file, True
