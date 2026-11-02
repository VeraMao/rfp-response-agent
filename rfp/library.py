"""Answer library: answers a human approved are saved and offered again for similar requirements.

A saved answer is only a hint. It is reused only if its sources haven't changed since it was approved
and the current user is allowed to see all of them; the model must still cite today's documents.
"""
import json
from datetime import date

from rfp import config, permissions, retrieve


def _file():
    return config.DATA / "answer_library.json"


def load():
    f = _file()
    return json.loads(f.read_text()) if f.is_file() else []


def _save(entries):
    _file().write_text(json.dumps(entries, indent=2) + "\n")


def add(row, approver, source, today=None):
    """Save an approved answer. `source` (e.g. 'harbor_bank:R-04') identifies where it was approved:
    approving the same requirement again replaces its entry instead of adding a duplicate."""
    entries = [e for e in load() if e.get("source") != source]
    next_num = max((int(e["id"].split("-")[1]) for e in load()), default=0) + 1   # ids are never reused
    entry = {"id": f"L-{next_num:03d}", "source": source, "requirement": row["text"], "status": row["status"],
             "answer": row["answer"], "conditions": row["conditions"], "citations": row["citations"],
             "approved_by": approver, "approved_on": (today or date.today()).isoformat()}
    _save(entries + [entry])
    return entry


def remove(source):
    """Withdraw an approval (the reviewer changed their mind). Returns True if an entry was removed."""
    entries = load()
    kept = [e for e in entries if e.get("source") != source]
    _save(kept)
    return len(kept) < len(entries)


def find(requirement_text, entries, embed_fn):
    """Best (score, entry) if similar enough, else None."""
    if not entries:
        return None
    vectors = embed_fn([requirement_text] + [e["requirement"] for e in entries])
    q, rest = vectors[0], vectors[1:]
    score, entry = max(((retrieve.cosine(q, v), e) for v, e in zip(rest, entries)), key=lambda p: p[0])
    return (score, entry) if score >= config.LIBRARY_MATCH else None


def usable(entry, chunks_by_id, role):
    """(ok, note). Not usable if a source was removed, updated after approval, or is hidden from this role."""
    for cid in entry["citations"]:
        chunk = chunks_by_id.get(cid)
        if chunk is None:
            return False, f"{entry['id']} cites {cid}, which no longer exists. Not reused."
        if not permissions.can_see(role, chunk):
            return False, f"{entry['id']} relies on a source you can't see. Not reused."
        if chunk["updated"] > entry["approved_on"]:
            return False, f"{entry['id']} was approved before {cid} was updated ({chunk['updated']}). Not reused."
    return True, None


def hint(entry):
    return (f"Previously approved answer {entry['id']} (approved {entry['approved_on']} by "
            f"{entry['approved_by']}, status {entry['status']}): \"{entry['answer']}\" "
            f"Conditions: {entry['conditions'] or 'none'}.")
