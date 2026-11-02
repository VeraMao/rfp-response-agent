"""Paths and settings in one place."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KNOWLEDGE = DATA / "knowledge"
RFPS = DATA / "rfps"
EXPECTED = DATA / "expected"
OUTPUTS = ROOT / "outputs"
CACHE = ROOT / ".cache"


def load_env():
    """Read ROOT/.env into the environment (.env wins over old shell values). Values are never printed."""
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"')


load_env()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
EMBED_MODEL = "text-embedding-3-small"
TOP_K = int(os.getenv("TOP_K", "4"))            # passages given to the model per requirement
RETRIEVAL = os.getenv("RETRIEVAL", "embed")     # "embed" or "hybrid" (embeddings + keywords)
STALE_DAYS = 365                                # a cited source older than this is flagged
LIBRARY_MATCH = 0.85                            # similarity needed to reuse an approved answer

STATUSES = ["supported", "conditional", "not_supported", "not_found"]
OWNERS = ["Security", "Legal", "Product", "Implementation", "Infrastructure", "Support", "Sales"]
