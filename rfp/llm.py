"""The only place that talks to the OpenAI API."""
import hashlib
import json

from rfp import config

_client = None
_cache = None


def client():
    """Created on first use, so offline tests never need the openai package or a key."""
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()
    return _client


def ask_json(instructions, text, schema, name="out"):
    """One model call that MUST return JSON matching the schema (structured outputs)."""
    resp = client().responses.create(
        model=config.MODEL, instructions=instructions, input=text, temperature=0,
        text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}})
    return json.loads(resp.output_text)


def _cache_file():
    return config.CACHE / "embeddings.json"


def _load_cache():
    global _cache
    if _cache is None:
        f = _cache_file()
        _cache = json.loads(f.read_text()) if f.is_file() else {}
    return _cache


def embed(texts):
    """Text -> vectors. Cached on disk by a hash of model + text, so re-runs don't pay again."""
    cache = _load_cache()
    keys = [hashlib.sha256(f"{config.EMBED_MODEL}\n{t}".encode()).hexdigest() for t in texts]
    missing = [(k, t) for k, t in zip(keys, texts) if k not in cache]
    for start in range(0, len(missing), 100):                      # batch API calls
        batch = missing[start:start + 100]
        data = client().embeddings.create(model=config.EMBED_MODEL, input=[t for _, t in batch]).data
        for (k, _), d in zip(batch, data):
            cache[k] = d.embedding
    if missing:
        config.CACHE.mkdir(exist_ok=True)
        _cache_file().write_text(json.dumps(cache))
    return [cache[k] for k in keys]
