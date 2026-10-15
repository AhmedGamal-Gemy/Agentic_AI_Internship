"""
New code for Session 5 — Memory / Progress Tracker
Add these to your existing agent.py / server.py, then wire the three
new functions into your evaluator agent's tools=[...] list.
"""

import json
import time

HISTORY_KEY_PREFIX = "history:"  # one Redis list per intern: history:{name}


def update_intern_history(name: str, xp_awarded: int, commit_count: int, files_changed: int) -> None:
    """Record one push event to an intern's permanent history."""
    event = {
        "timestamp": time.time(),
        "xp_awarded": xp_awarded,
        "commit_count": commit_count,
        "files_changed": files_changed,
    }
    r.rpush(f"{HISTORY_KEY_PREFIX}{name}", json.dumps(event))


def get_intern_history(name: str) -> list[dict]:
    """Return the full list of past push events for one intern."""
    raw_events = r.lrange(f"{HISTORY_KEY_PREFIX}{name}", 0, -1)
    return [json.loads(e) for e in raw_events]


def summarize_progress(name: str) -> str:
    """Summarize an intern's activity using their real history."""
    history = get_intern_history(name)
    if not history:
        return f"{name} has no recorded activity yet."
    total_xp = sum(e["xp_awarded"] for e in history)
    total_pushes = len(history)
    return f"{name} has pushed {total_pushes} times, earning {total_xp} XP total."


# ── Add this call inside assign_xp, right after XP is awarded ──
#
# update_intern_history(
#     name=pusher_name,
#     xp_awarded=xp_awarded,
#     commit_count=commit_count,
#     files_changed=files_changed,
# )

# ── Add to your evaluator agent's tools list ──
#
# tools=[assign_xp, update_intern_history, get_intern_history, summarize_progress]