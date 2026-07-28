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

from google.adk.runners import InMemoryRunner
from google.genai import types
from agent import root_agent
runner = InMemoryRunner(agent=root_agent, app_name="challenge_generator")

def extract_event_info(event) -> dict | None:
    """Pull out whatever's meaningful from an event: text, tool call, or tool result."""
    if not event.content or not event.content.parts:
        return None
    for part in event.content.parts:
        if part.text:
            return {"type": "text", "content": part.text}
        if part.function_call:
            return {
                "type": "tool_call",
                "tool": part.function_call.name,
                "args": part.function_call.args,
            }
        if part.function_response:
            return {
                "type": "tool_result",
                "tool": part.function_response.name,
                "result": part.function_response.response,
            }
    return None

@app.post("/run_agent")
async def run_agent(user_message: str):
    session = await runner.session_service.create_session(
        app_name="challenge_generator", user_id="manual_trigger"
    )
    message = types.Content(
        role="user", 
        parts=[
            types.Part(
                text=user_message
                )
        ]
    )    
    steps = []
    final_text = []
    async for event in runner.run_async(
        user_id="manual_trigger", session_id=session.id, new_message=message
    ):
        info = extract_event_info(event)
        if info:
            print(f"[{info['type']}]", info)
            steps.append(info)
            if info["type"] == "text":
                final_text.append(info["content"])
    return {"response": " ".join(final_text), "steps": steps}

from fastapi import Request, BackgroundTasks, HTTPException
import hmac
import hashlib
import os

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET").encode()

def parse_push_payload(payload: dict) -> dict:
    pusher_name = payload["pusher"]["name"]
    commits = payload["commits"]
    commit_count = len(commits)

    files_changed = set()
    for commit in commits:
        files_changed.update(commit["added"])
        files_changed.update(commit["modified"])
        files_changed.update(commit["removed"])

    return {
        "pusher_name": pusher_name,
        "commit_count": commit_count,
        "files_changed": len(files_changed),
    }
@app.post("/github_webhook")
async def get_github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event")
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = await request.json()

    # print(payload)
    if event_type == "ping":
        print("Received ping — webhook connected successfully!")
        return {"status": "pong"}

    facts = parse_push_payload(payload)
    message_text = (
        f"Pusher: {facts['pusher_name']}. "
        f"Commits: {facts['commit_count']}. "
        f"Files changed: {facts['files_changed']}. "
        f"Evaluate this push and award XP."
    )

    if event_type == "push":
        background_tasks.add_task(handle_push, message_text)
    return {"status": "received"}

def handle_push(message_text):
    print(message_text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)