"""Shared test helpers: a fake embedding so tests never call the API."""
import hashlib
import math
import re


def fake_embed(texts, dims=64):
    """Bag-of-words hashed into a small vector: similar words -> similar vectors. Deterministic."""
    out = []
    for t in texts:
        v = [0.0] * dims
        for w in re.findall(r"[a-z0-9]+", t.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dims] += 1
        norm = math.sqrt(sum(x * x for x in v)) or 1
        out.append([x / norm for x in v])
    return out


def chunk(cid, text, updated="2026-09-01", visibility="public", roles=()):
    return {"id": cid, "doc": cid.split("#")[0], "heading": cid.split("#")[1], "text": text,
            "updated": updated, "owner": "Product", "visibility": visibility, "allowed_roles": list(roles)}


def result(status="supported", citations=("a.md#X",), conditions=None, conflict=None, owner=None,
           answer="We do it."):
    return {"status": status, "answer": answer, "conditions": conditions, "citations": list(citations),
            "conflict": conflict, "owner": owner}
