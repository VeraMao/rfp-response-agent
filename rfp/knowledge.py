"""Company documents: front matter, chunking by '## ' section, and plan names."""
import re
from datetime import date

from rfp import config


def read_front_matter(text):
    """'---\nlast_updated: 2026-09-15\nowner: Product\n---\n...' -> ({'last_updated': ..., ...}, rest)"""
    if not text.startswith("---\n"):
        return {}, text
    head, _, rest = text[4:].partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, rest


def load_chunks(folder=None):
    """Every '## ' section of every document becomes one chunk that carries its document's metadata."""
    folder = folder or config.KNOWLEDGE
    chunks = []
    for path in sorted(folder.glob("*.md")):
        meta, text = read_front_matter(path.read_text())
        roles = [r.strip() for r in meta.get("allowed_roles", "").split(",") if r.strip()]
        for section in text.split("\n## ")[1:]:                     # skip the '# Title' line
            heading, _, body = section.partition("\n")
            chunks.append({
                "id": f"{path.name}#{heading.strip()}", "doc": path.name, "heading": heading.strip(),
                "text": body.strip(), "updated": meta.get("last_updated", "unknown"),
                "owner": meta.get("owner"), "visibility": meta.get("visibility", "internal"),
                "allowed_roles": roles,
            })
    return chunks


NOT_PLAN_NAMES = {"Every", "Each", "All", "Any", "This", "That", "Our", "Your", "The", "One", "No"}


def plan_names(chunks):
    """Plan names found in the documents, e.g. 'Enterprise plan' -> 'Enterprise'. Never hard-coded.
    Words like 'Every plan' look the same, so a short list of determiners is excluded."""
    text = " ".join(c["text"] for c in chunks)
    return sorted(set(re.findall(r"\b([A-Z][a-z]+) plan\b", text)) - NOT_PLAN_NAMES)


def age_days(updated, today=None):
    try:
        return ((today or date.today()) - date.fromisoformat(updated)).days
    except ValueError:
        return config.STALE_DAYS + 1                  # an unknown date counts as stale
