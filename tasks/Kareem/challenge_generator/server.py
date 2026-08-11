import os
import sys
import json
import time
import hmac
import hashlib
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from google.adk.runners import InMemoryRunner
from google.genai import types

from challenge_generator.agent import root_agent as challenge_generator_agent
from xp_calculator.agent import root_agent as xp_evaluator_agent
from solution_reviewer.agent import root_agent as solution_reviewer_agent

app = FastAPI(title="Kareem's Agentic AI Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_redis():
    host = os.getenv("REDIS_HOST")
    if not host:
        return None
    try:
        r = redis.Redis(
            host=host,
            port=int(os.getenv("REDIS_PORT", 6379)),
            username=os.getenv("REDIS_USERNAME"),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            ssl=True,
            ssl_cert_reqs=None,
            socket_timeout=4,
        )
        r.ping()
        return r
    except Exception as e:
        print(f"Redis unavailable, using in-memory fallback: {e}")
        return None


r_client = get_redis()

CURRENT_CHALLENGE_KEY = "current_challenge"
CHALLENGE_LOG_KEY = "challenge_log"
LEADERBOARD_KEY = "leaderboard"
HISTORY_KEY_PREFIX = "history:"
PROCESSED_COMMITS_KEY = "processed_commits"
PROCESSED_PUSHES_KEY = "processed_pushes"

DEFAULT_LEADERBOARD = [
    [1, "Kareem", 200],
    [2, "Omar", 180],
    [3, "Gemy", 175],
    [4, "Julie", 130],
    [5, "Mariam", 125],
    [6, "Mazen", 115],
    [7, "Shahd", 110],
    [8, "Nour", 100],
]

mem_current_challenge: Dict[str, Any] = {}
mem_challenge_log: List[Dict[str, Any]] = []
mem_leaderboard: List[List[Any]] = [list(item) for item in DEFAULT_LEADERBOARD]
mem_history: Dict[str, List[Dict[str, Any]]] = {}
mem_processed_commits: set = set()
mem_processed_pushes: set = set()
mem_counter: int = 0


class Challenge(BaseModel):
    topic: str
    difficulty: str
    description: str
    solution: str


class XPAward(BaseModel):
    name: str
    xp_awarded: int
    commit_count: int
    files_changed: int
    commit_sha: str = ""


class SolutionSubmission(BaseModel):
    intern_name: str
    challenge_id: Optional[int] = 1
    code: str
    language: str = "python"


class SolutionReviewPayload(BaseModel):
    intern_name: str
    quality_score: int
    bonus_xp: int
    feedback: str


challenge_runner = InMemoryRunner(agent=challenge_generator_agent, app_name="challenge_generator")
evaluator_runner = InMemoryRunner(agent=xp_evaluator_agent, app_name="xp_evaluator")
reviewer_runner = InMemoryRunner(agent=solution_reviewer_agent, app_name="solution_reviewer")


def extract_event_info(event) -> Optional[dict]:
    if not event.content or not event.content.parts:
        return None
    for part in event.content.parts:
        if part.text:
            return {"type": "text", "content": part.text}
        if part.function_call:
            return {"type": "tool_call", "tool": part.function_call.name, "args": part.function_call.args}
        if part.function_response:
            return {"type": "tool_result", "tool": part.function_response.name, "result": part.function_response.response}
    return None


def update_intern_history(name: str, xp_awarded: int, commit_count: int, files_changed: int) -> None:
    event = {"timestamp": time.time(), "xp_awarded": xp_awarded, "commit_count": commit_count, "files_changed": files_changed}
    if r_client:
        try:
            r_client.rpush(f"{HISTORY_KEY_PREFIX}{name}", json.dumps(event))
            return
        except Exception:
            pass
    if name not in mem_history:
        mem_history[name] = []
    mem_history[name].append(event)


def is_known_intern(name: str) -> bool:
    if r_client:
        try:
            data = r_client.get(LEADERBOARD_KEY)
            if data:
                return name in {entry[1] for entry in json.loads(data)}
        except Exception:
            pass
    return name in {entry[1] for entry in mem_leaderboard}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/save")
def save_to_database(challenge: Challenge):
    global mem_counter
    record = challenge.model_dump()
    record["saved_at"] = time.time()
    if r_client:
        try:
            record["id"] = r_client.incr("challenge_counter")
            r_client.rpush(CHALLENGE_LOG_KEY, json.dumps(record))
            return {"status": "saved", "id": record["id"]}
        except Exception as e:
            print(f"Redis save error: {e}")
    mem_counter += 1
    record["id"] = mem_counter
    mem_challenge_log.append(record)
    return {"status": "saved", "id": record["id"]}


@app.post("/challenge")
def push_to_leaderboard(challenge: Challenge):
    global mem_current_challenge
    record = challenge.model_dump()
    record["id"] = int(time.time())
    if r_client:
        try:
            r_client.set(CURRENT_CHALLENGE_KEY, json.dumps(record))
            return {"status": "posted", "id": record["id"]}
        except Exception as e:
            print(f"Redis error: {e}")
    mem_current_challenge = record
    return {"status": "posted", "id": record["id"]}


@app.get("/challenge")
def get_current_challenge():
    if r_client:
        try:
            data = r_client.get(CURRENT_CHALLENGE_KEY)
            if data:
                return json.loads(data)
        except Exception:
            pass
    return mem_current_challenge


@app.get("/leaderboard")
def get_leaderboard():
    if r_client:
        try:
            data = r_client.get(LEADERBOARD_KEY)
            if data:
                return json.loads(data)
        except Exception:
            pass
    return mem_leaderboard


@app.post("/run_agent")
async def run_agent(user_message: str):
    session = await challenge_runner.session_service.create_session(app_name="challenge_generator", user_id="manual_trigger")
    message = types.Content(role="user", parts=[types.Part(text=user_message)])
    steps = []
    final_text = []
    async for event in challenge_runner.run_async(user_id="manual_trigger", session_id=session.id, new_message=message):
        info = extract_event_info(event)
        if info:
            steps.append(info)
            if info["type"] == "text":
                final_text.append(info["content"])
    return {"response": " ".join(final_text), "steps": steps}


WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "default_secret").encode()


def parse_push_payload(payload: dict) -> dict:
    pusher_name = payload.get("pusher", {}).get("name", "unknown")
    commits = payload.get("commits", [])
    files_changed = set()
    for commit in commits:
        files_changed.update(commit.get("added", []))
        files_changed.update(commit.get("modified", []))
        files_changed.update(commit.get("removed", []))
    return {
        "pusher_name": pusher_name,
        "commit_count": len(commits),
        "files_changed": len(files_changed),
        "commit_shas": [c.get("id") or c.get("sha") for c in commits],
        "head_sha": payload.get("after") or "",
    }


async def handle_push(pusher_name: str, message_text: str, head_sha: str = ""):
    if not is_known_intern(pusher_name):
        print(f"Push from {pusher_name} not on leaderboard, skipping.")
        return
    session = await evaluator_runner.session_service.create_session(app_name="xp_evaluator", user_id=pusher_name)
    message = types.Content(role="user", parts=[types.Part(text=message_text)])
    async for event in evaluator_runner.run_async(user_id=pusher_name, session_id=session.id, new_message=message):
        info = extract_event_info(event)
        if info:
            print(f"[xp_evaluator {info['type']}]", info)
    if head_sha:
        if r_client:
            try:
                r_client.sadd(PROCESSED_PUSHES_KEY, head_sha)
                return
            except Exception:
                pass
        mem_processed_pushes.add(head_sha)


@app.post("/github_webhook")
async def get_github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event")
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    if signature and not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = await request.json()
    if event_type == "ping":
        return {"status": "pong"}
    if event_type != "push":
        return {"status": "ignored", "event": event_type}
    facts = parse_push_payload(payload)
    if not facts["commit_shas"]:
        return {"status": "ignored", "reason": "no commits"}
    if facts["head_sha"]:
        is_dup = False
        if r_client:
            try:
                is_dup = bool(r_client.sismember(PROCESSED_PUSHES_KEY, facts["head_sha"]))
            except Exception:
                is_dup = facts["head_sha"] in mem_processed_pushes
        else:
            is_dup = facts["head_sha"] in mem_processed_pushes
        if is_dup:
            return {"status": "duplicate", "head_sha": facts["head_sha"]}
    message_text = (
        f"Pusher: {facts['pusher_name']}.\n"
        f"Commits: {facts['commit_count']}.\n"
        f"Commit SHAs: {facts['commit_shas']}.\n"
        f"Push head SHA: {facts['head_sha']}.\n"
        f"Files changed: {facts['files_changed']}.\n"
        f"Evaluate this push and award fair XP."
    )
    background_tasks.add_task(handle_push, facts['pusher_name'], message_text, facts["head_sha"])
    return {"status": "received", "pusher": facts["pusher_name"]}


@app.post("/xp")
def award_xp(xp: XPAward):
    global mem_leaderboard
    data = None
    if r_client:
        try:
            data = r_client.get(LEADERBOARD_KEY)
        except Exception:
            pass
    leaderboard = json.loads(data) if data else mem_leaderboard
    total_xp = 0
    found = False
    for entry in leaderboard:
        if entry[1] == xp.name:
            found = True
            if xp.commit_sha:
                already_processed = False
                if r_client:
                    try:
                        already_processed = bool(r_client.sismember(PROCESSED_COMMITS_KEY, xp.commit_sha))
                    except Exception:
                        already_processed = xp.commit_sha in mem_processed_commits
                else:
                    already_processed = xp.commit_sha in mem_processed_commits
                if already_processed:
                    return {"status": "already_processed", "message": f"Commit {xp.commit_sha} already recorded."}
            entry[2] += xp.xp_awarded
            total_xp = entry[2]
            update_intern_history(name=xp.name, xp_awarded=xp.xp_awarded, commit_count=xp.commit_count, files_changed=xp.files_changed)
            if xp.commit_sha:
                if r_client:
                    try:
                        r_client.sadd(PROCESSED_COMMITS_KEY, xp.commit_sha)
                    except Exception:
                        mem_processed_commits.add(xp.commit_sha)
                else:
                    mem_processed_commits.add(xp.commit_sha)
            break
    if not found:
        return {"status": "failed", "name": xp.name, "error": "Intern not on leaderboard"}
    if r_client:
        try:
            r_client.set(LEADERBOARD_KEY, json.dumps(leaderboard))
        except Exception:
            pass
    mem_leaderboard = leaderboard
    return {"status": "awarded", "name": xp.name, "total_xp": total_xp}


@app.post("/solution_review")
def record_solution_review(review: SolutionReviewPayload):
    global mem_leaderboard
    data = None
    if r_client:
        try:
            data = r_client.get(LEADERBOARD_KEY)
        except Exception:
            pass
    leaderboard = json.loads(data) if data else mem_leaderboard
    total_xp = 0
    for entry in leaderboard:
        if entry[1] == review.intern_name:
            entry[2] += review.bonus_xp
            total_xp = entry[2]
            break
    if r_client:
        try:
            r_client.set(LEADERBOARD_KEY, json.dumps(leaderboard))
            r_client.rpush(f"reviews:{review.intern_name}", json.dumps(review.model_dump()))
        except Exception:
            pass
    mem_leaderboard = leaderboard
    return {"status": "reviewed", "intern_name": review.intern_name, "bonus_xp": review.bonus_xp, "total_xp": total_xp}


@app.post("/submit_solution")
async def submit_solution(submission: SolutionSubmission, background_tasks: BackgroundTasks):
    message_text = (
        f"Intern Name: {submission.intern_name}\n"
        f"Language: {submission.language}\n"
        f"Code:\n```\n{submission.code}\n```\n"
        f"Analyze code quality and award bonus XP."
    )

    async def run_solution_agent():
        session = await reviewer_runner.session_service.create_session(app_name="solution_reviewer", user_id=submission.intern_name)
        message = types.Content(role="user", parts=[types.Part(text=message_text)])
        async for event in reviewer_runner.run_async(user_id=submission.intern_name, session_id=session.id, new_message=message):
            info = extract_event_info(event)
            if info:
                print(f"[solution_reviewer {info['type']}]", info)

    background_tasks.add_task(run_solution_agent)
    return {"status": "submitted", "intern": submission.intern_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
