"""Who may see which documents. Filtering happens BEFORE retrieval, so hidden text never reaches the model."""
import json

from rfp import config


def load_users():
    return json.loads((config.DATA / "users.json").read_text())


def get_user(user_id):
    users = load_users()
    if user_id not in users:
        raise SystemExit(f"Unknown user '{user_id}'. Known users: {', '.join(sorted(users))}")
    return {"id": user_id, **users[user_id]}


def can_see(role, chunk):
    """public / internal: every employee. restricted: only the roles listed in allowed_roles."""
    if chunk["visibility"] in ("public", "internal"):
        return True
    return role in chunk["allowed_roles"]


def visible(chunks, role):
    return [c for c in chunks if can_see(role, c)]
