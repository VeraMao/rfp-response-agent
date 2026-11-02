"""Pure scoring functions for the eval (no API calls, so they are unit-tested)."""
import re

# Words that belong in internal notes, never in an answer to the customer.
INTERNAL_WORDS = ["not current", "out of date", "verify", "passage", "internal", "the documents"]
SUMMARY_SECTIONS = ["Bottom line", "What it takes to win", "Customer context"]


def mentions(text, word):
    """Whole-word match (plural allowed), so 'not current' does not match 'We do not currently offer'."""
    return re.search(rf"\b{re.escape(word.lower())}s?\b", text) is not None


def score_requirement(exp, result):
    """List of failed checks for one requirement (empty list = pass)."""
    fails = []
    if result["status"] not in exp["status"]:
        fails.append(f"status {result['status']} (expected {'/'.join(exp['status'])})")
    conditions = (result["conditions"] or "").lower()
    for word in exp["conditions_must_mention"]:
        if word not in conditions:
            fails.append(f"conditions missing '{word}'")
    answer = result["answer"].lower()
    for word in INTERNAL_WORDS + exp["answer_must_not_mention"]:
        if mentions(answer, word):
            fails.append(f"answer contains '{word}'")
    if exp["conflict"] is True and not result.get("conflict"):
        fails.append("conflict not flagged")
    if exp["conflict"] is False and result.get("conflict"):
        fails.append("false conflict flagged")
    if result["status"] != "not_found" and not result["citations"]:
        fails.append("no citation")
    if result["status"] != "supported" and not result["owner"]:
        fails.append("no owner")
    return fails


def recall_hit(exp, searched_ids):
    """Retrieval check, separate from the answer: did we retrieve every expected document?"""
    docs = {cid.split("#")[0] for cid in searched_ids}
    return all(d in docs for d in exp["expected_evidence"])


def score_summary(summary, calls_made, allowed_numbers):
    fails = []
    if not any(c.startswith("get_customer") for c in calls_made):
        fails.append("did not look up the customer")
    for heading in SUMMARY_SECTIONS:
        if heading not in (summary or ""):
            fails.append(f"missing section '{heading}'")
    for amount in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)", summary or ""):
        if float(amount.replace(",", "")) not in allowed_numbers:
            fails.append(f"invented price ${amount}")
    return fails


def numbers_in(texts):
    """Every number written in the given texts, e.g. '$250,000' -> 250000.0."""
    return {float(n.replace(",", "")) for t in texts for n in re.findall(r"\d[\d,]*(?:\.\d+)?", t)}
