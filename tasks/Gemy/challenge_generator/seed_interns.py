"""
seed_interns.py — run this ONCE against the shared Redis instance.

Writes real intern records into the `leaderboard` key, replacing what
was previously only hardcoded in leaderboard.html's DEFAULT_DATA.

Shape matches what leaderboard.html expects: [id, name, xp]
`name` is set to each person's GitHub username, since that's what
GitHub's push payload sends as `pusher.name` — this keeps it consistent
with the pusher-name filter already built into evaluate_task().

⚠️ Run this once. Running it again will RESET everyone's XP back to 0
unless you set PRESERVE_EXISTING_XP = True below.
"""

import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────
PRESERVE_EXISTING_XP = True  # if True, keeps current XP for anyone already in the list
LEADERBOARD_KEY = "leaderboard"

# ── Edit this list if names/usernames change ────────────
INTERNS = [
    {"id": 1,  "name": "AmoryCR"},
    {"id": 2,  "name": "ay032-ops"},
    {"id": 3,  "name": "carolmagedcm-stack"},
    {"id": 4,  "name": "esraa295"},
    {"id": 5,  "name": "Far7etna"},
    {"id": 6,  "name": "gannaosama137"},
    {"id": 7,  "name": "Hendmostafa44"},
    {"id": 8,  "name": "JayanneAbdelmotteleb"},
    {"id": 9,  "name": "jolie-selem"},
    {"id": 10, "name": "karim-wael"},
    {"id": 11, "name": "mahmoud-aymann"},
    {"id": 12, "name": "MariamSaber33"},
    {"id": 13, "name": "Mohamed44Ashraf"},
    {"id": 14, "name": "Mohammed-Gadd"},
    {"id": 15, "name": "Nourelganainy23"},
    {"id": 16, "name": "shahd-kh"},
    {"id" : 17, "name":"Gemy"},
]

# ── Redis connection (shared instance) ───────────────────
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)


def seed():
    existing_raw = r.get(LEADERBOARD_KEY)
    existing = json.loads(existing_raw) if existing_raw else []
    existing_by_name = {entry[1]: entry[2] for entry in existing}  # name -> xp

    new_leaderboard = []
    for intern in INTERNS:
        name = intern["name"]
        if PRESERVE_EXISTING_XP and name in existing_by_name:
            xp = existing_by_name[name]
            print(f"Keeping existing XP for {name}: {xp}")
        else:
            xp = 0
            print(f"Seeding {name} with XP: 0")
        new_leaderboard.append([intern["id"], name, xp])

    r.set(LEADERBOARD_KEY, json.dumps(new_leaderboard))
    print(f"\nDone. {len(new_leaderboard)} interns written to Redis under '{LEADERBOARD_KEY}'.")


if __name__ == "__main__":
    seed()
    