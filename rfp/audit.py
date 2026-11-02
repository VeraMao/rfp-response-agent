"""Append-only log of who approved, edited or wrote what, and when."""
import json
from datetime import datetime

from rfp import config


def log(event, user, **details):
    config.OUTPUTS.mkdir(exist_ok=True)
    entry = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, "user": user, **details}
    with open(config.OUTPUTS / "audit.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
