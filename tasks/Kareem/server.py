import os
import sys
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path so `chigga.agent` is importable
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from google.adk.runners import InMemoryRunner
from google.genai import types
from chigga.agent import root_agent

runner = InMemoryRunner(agent=root_agent, app_name="challenge_generator")

app = FastAPI(title="Challenge Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "Challenge Generator Server"}


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
            socket_timeout=3,
        )
        r.ping()
        return r
    except Exception as e:
        print(f"Redis cloud connection notice: {e}")
        return None


r_client = None
try:
    r_client = get_redis()
except Exception as e:
    print(f"Redis setup notice: {e}")

memory_db = []
current_challenge_mem = {}
leaderboard_mem = []
counter_mem = 0

CURRENT_CHALLENGE_KEY = "current_challenge"
CHALLENGE_LOG_KEY = "challenge_log"
LEADERBOARD_KEY = "leaderboard"


class Challenge(BaseModel):
    topic: str
    difficulty: str
    description: str
    solution: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/save")
def save_to_database(challenge: Challenge):
    global counter_mem
    record = challenge.model_dump()
    record["saved_at"] = time.time()

    if r_client:
        try:
            record["id"] = r_client.incr("challenge_counter")
            r_client.rpush(CHALLENGE_LOG_KEY, json.dumps(record))
            return {"status": "saved", "id": record["id"]}
        except Exception as e:
            print(f"Redis save fallback: {e}")

    counter_mem += 1
    record["id"] = counter_mem
    memory_db.append(record)
    return {"status": "saved", "id": record["id"]}


@app.post("/challenge")
def push_to_leaderboard(challenge: Challenge):
    global current_challenge_mem
    record = challenge.model_dump()
    record["id"] = int(time.time())

    if r_client:
        try:
            r_client.set(CURRENT_CHALLENGE_KEY, json.dumps(record))
            return {"status": "posted", "id": record["id"]}
        except Exception as e:
            print(f"Redis challenge fallback: {e}")

    current_challenge_mem = record
    return {"status": "posted", "id": record["id"]}


@app.get("/challenge")
def get_current_challenge():
    if r_client:
        try:
            data = r_client.get(CURRENT_CHALLENGE_KEY)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis get_challenge fallback: {e}")
    return current_challenge_mem


@app.get("/leaderboard")
def get_leaderboard():
    if r_client:
        try:
            data = r_client.get(LEADERBOARD_KEY)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis leaderboard fallback: {e}")
    return leaderboard_mem


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

    try:
        async for event in runner.run_async(
            user_id="manual_trigger", session_id=session.id, new_message=message
        ):
            info = extract_event_info(event)
            if info:
                print(f"[{info['type']}]", info)
                steps.append(info)
                if info["type"] == "text":
                    final_text.append(info["content"])
    except Exception as e:
        print(f"Notice during agent run: {e}")

    return {"response": " ".join(final_text), "steps": steps}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8008)
