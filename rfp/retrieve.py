"""Find the passages most relevant to a requirement, among the ones the user is allowed to see."""
import math
import re
from collections import Counter

from rfp import config, llm, permissions

STOPWORDS = set("a an and are as at be by for from has have in is it its must of on or our shall should "
                "that the their this to vendor we will with within your".split())


def tokens(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words if w not in STOPWORDS]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


class Index:
    """Embeddings for every chunk (heading + text), plus keyword statistics for hybrid search."""

    def __init__(self, chunks, embed_fn=None):
        self.chunks = chunks
        self.embed_fn = embed_fn or llm.embed                     # tests pass a fake, no API needed
        self.vectors = self.embed_fn([f"{c['heading']}\n{c['text']}" for c in chunks])
        self.tf = [Counter(tokens(f"{c['heading']} {c['text']}")) for c in chunks]
        df = Counter(w for tf in self.tf for w in tf)
        n = len(chunks)
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    def _keyword(self, q_tokens, i):
        """BM25-style score: rare words that appear in the chunk count most."""
        tf = self.tf[i]
        return sum(self.idf.get(w, 0) * tf[w] * 2.2 / (tf[w] + 1.2) for w in q_tokens if w in tf)

    def hidden_count(self, role):
        return sum(not permissions.can_see(role, c) for c in self.chunks)

    def search(self, query, role, k=None, mode=None):
        """Top-k (score, chunk) pairs. Chunks the role can't see are removed before any scoring."""
        k = k or config.TOP_K
        mode = mode or config.RETRIEVAL
        allowed = [i for i, c in enumerate(self.chunks) if permissions.can_see(role, c)]
        q_vec = self.embed_fn([query])[0]
        semantic = {i: cosine(q_vec, self.vectors[i]) for i in allowed}
        if mode == "hybrid":
            q_tokens = tokens(query)
            kw = {i: self._keyword(q_tokens, i) for i in allowed}
            top = max(kw.values(), default=0) or 1
            scores = {i: 0.7 * semantic[i] + 0.3 * kw[i] / top for i in allowed}
        else:
            scores = semantic
        ranked = sorted(allowed, key=lambda i: scores[i], reverse=True)[:k]
        return [(scores[i], self.chunks[i]) for i in ranked]
