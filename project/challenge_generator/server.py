"""
server.py — tiny FastAPI bridge between:
  - the agent's tools (save_to_database, push_to_leaderboard)
  - leaderboard.html (polls /leaderboard and /challenge every 5s)
  - Redis Cloud (TCP-only, so the browser can't talk to it directly)

Run with: python server.py
Or:       uvicorn server:app --reload --port 8000
"""

import os
import json
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Allow the browser (leaderboard.html) to fetch from this server.
# Without this, the fetch silently fails in the browser console only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)




# ── Redis Cloud connection ──────────────────────────────
# Get these values from your Redis Cloud dashboard: Database > Public endpoint
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)






CURRENT_CHALLENGE_KEY = "current_challenge"
CHALLENGE_LOG_KEY = "challenge_log"       # full history of all generated challenges
LEADERBOARD_KEY = "leaderboard"           # intern XP data, wired up in a later session


class Challenge(BaseModel):
    topic: str
    difficulty: str
    description: str
    solution: str





# ── Health check — test this first, before anything else ─
@app.get("/health")
def health():
    return {"status": "ok"}






# ── Called by the agent's save_to_database tool ─────────
# Persists every challenge ever generated to a Redis list (the permanent record)
@app.post("/save")
def save_to_database(challenge: Challenge):

    record = challenge.model_dump()

#   record = {
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }

    record["id"] = r.incr("challenge_counter")

#   record = {
#   "id" : 5
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }


    record["saved_at"] = time.time()

    # record = {
#   "id" : 1,
#   "saved_at" : "8:11"  
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }


    r.rpush(CHALLENGE_LOG_KEY, json.dumps(record))

    return {"status": "saved", "id": record["id"]}


# ── Called by the agent's push_to_leaderboard tool ──────
# Sets the CURRENT challenge — this is what leaderboard.html displays live
@app.post("/challenge")
def push_to_leaderboard(challenge: Challenge):
    record = challenge.model_dump()

    record["id"] = int(time.time())  # changing id triggers the flash animation
    r.set(CURRENT_CHALLENGE_KEY, json.dumps(record))
    return {"status": "posted", "id": record["id"]}


# ── Polled by leaderboard.html every 5 seconds ──────────
@app.get("/challenge")
def get_current_challenge():
    data = r.get(CURRENT_CHALLENGE_KEY)
    if not data:
        return {}
    return json.loads(data)


# ── Polled by leaderboard.html every 5 seconds ──────────
# Returns [[id, name, xp], ...] — matches leaderboard.html's expected shape
@app.get("/leaderboard")
def get_leaderboard():
    data = r.get(LEADERBOARD_KEY)
    if not data:
        return []  # frontend falls back to DEFAULT_DATA automatically
    return json.loads(data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)



