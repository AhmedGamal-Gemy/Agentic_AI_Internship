"""
server.py — tiny FastAPI bridge between:
  - the agent's tools (save_to_database, push_to_leaderboard)
  - leaderboard.html (polls /leaderboard and /challenge every 5s)
  - Redis Cloud (TCP-only, so the browser can't talk to it directly)

Run with: python server.py
Or:       uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis 
import os
from pydantic import BaseModel
import time
import json
import requests
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
) #dy bt5lly ay 7d mn elfront (html) y2dr yaccess elserver bta3y



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

#elstr ely fo2 da hyb2a elnateg bta3o kda 
# record = {
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }

    record["id"] = r.incr("challenge_counter")

#elstr ely fo2 da hyb2a elnateg bta3o kda 
#   record = {
#   "id" : 5
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }


    record["saved_at"] = time.time()

#elstr ely fo2 da hyb2a elnateg bta3o kda 
    # record = {
#   "id" : 1,
#   "saved_at" : "8:11"  
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }


    r.rpush(CHALLENGE_LOG_KEY, json.dumps(record))
    # r.lrange(CHALLENGE_LOG_KEY,start=0,end=5)
    return {"status": "saved", "id": record["id"]}



 #── Called by the agent's push_to_leaderboard tool ──────
# Sets the CURRENT challenge — this is what leaderboard.html displays live
@app.post("/challenge")
def push_to_leaderboard(challenge: Challenge):
    record = challenge.model_dump()

    record["id"] = int(time.time())  # changing id triggers the flash animation
    r.set(CURRENT_CHALLENGE_KEY, json.dumps(record))
    return {"status": "posted", "id": record["id"]}


#── Polled by leaderboard.html every 5 seconds ──────────
@app.get("/challenge")
def get_current_challenge():
    data = r.get(CURRENT_CHALLENGE_KEY)
    # print("Data from redis:",repr(data))
    if not data:
        return {}
    return json.loads(data)


# ── Polled by leaderboard.html every 5 seconds ──────────
#Returns [[id, name, xp], ...] — matches leaderboard.html's expected shape
@app.get("/leaderboard")
def get_leaderboard():
    data = r.get(LEADERBOARD_KEY)
    if not data:
        return []  # frontend falls back to DEFAULT_DATA automatically
    return json.loads(data)



from google.adk.runners import InMemoryRunner
from google.genai import types
from agent import root_agent

runner=InMemoryRunner(agent=root_agent,app_name="challenge_generator") #initialization of runner (elagent 7atenah fel runner 3shan byrun el agent)

def extract_event_info(event) -> dict | None:
    """Pull out whatever's meaningful from an event: text, tool call, or tool result."""

    if not event.content or not event.content.parts:
        return None

    for part in event.content.parts:
        if part.text:
            return {
                "type": "text",
                "content": part.text
            }

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

    session = await runner.session_service.create_session( #await msh bt3ml block llexecuation lw 7sl moshkla f btstna w da far3 mn elbrmaga asmo async programming 3shan kda mst5dmen async def
        app_name="challenge_generator",
        user_id="manual_trigger"
    ) #hna 3mlna initialization l session gdeda best5dam el runner

    message = types.Content( #bn3ml message 3shan el runner yst3mlo 3latoul felrun
        role="user",
        parts=[types.Part(text=user_message)]
    )

    steps = []
    final_text = []

    async for event in runner.run_async(
        user_id="manual_trigger",
        session_id=session.id,
        new_message=message
    ):
       
        info= extract_event_info(event)
        if info:
            print(f"[{info['type']}]",info)
            steps.append(info)
            if info["type"]=="text":
                final_text.append(info["content"])
    return {"response":"".join(final_text),"steps":steps}            


from fastapi import Request, BackgroundTasks, HTTPException
import hmac
import hashlib
# import os

# يجب أن يكون نفس الـ Secret الموجود في GitHub Webhook
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode()


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
        "commit_shas":[commit.get("id") or commit.get("sha") for commit in commits], #7aga zy id lkol commit
        "head_sha":payload.get("after") or "", #7aga zy id llwad3 el7aly
    }

#github -> /github_webhook

@app.post("/github_webhook")
async def get_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks, #BackgroundTasks dy btbyn an i recieved the request
):
    # قراءة الـ Body الخام
    body = await request.body()

    # قراءة الـ Headers
    signature = request.headers.get("X-Hub-Signature-256") #emda 3obara 3n el secret bs m3molo encreyption
    event_type = request.headers.get("X-GitHub-Event") #msln push aw ping kda y3ne 

    # حساب الـ Signature المتوقع
    expected = (
        "sha256="
        + hmac.new(
            WEBHOOK_SECRET,
            body,
            hashlib.sha256,
        ).hexdigest()
    )

    # التحقق من صحة الـ Signature
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid signature",
        ) #mn awl expected l8ayt hna dy kolha 5assa bel security

    # تحويل الـ Body إلى JSON
    payload = await request.json()
    # print(payload)
    # إذا كان الحدث Push
    if event_type == "ping":
        print("Received ping - webhook connected successfully!")
        return {"status":"pong"}

    if event_type !="push":
        return {"status" : "ignored" , "event" : event_type}
    
    facts = parse_push_payload(payload)

    if not facts["commit_shas"]:
        return {"status" : "ignored" , "reason" : "no commits (e.g. branch deletion9zz7)"}
    message_text = (
        f"Pusher: {facts['pusher_name']}.\n"
        f"Commits: {facts['commit_count']}.\n"
        f"Commit shas: {facts['commit_shas']}.\n" 
        f"Push head sha (identifies this push — pass it as commit_sha): {facts['head_sha']}.\n"
        f"Files changed: {facts['files_changed']}.\n"
        f"Evaluate this push and award XP."
    )

    if facts['head_sha'] and r.sismember("processed_pushes", facts["head_sha"]):
        print(f"Duplicate push {facts['head_sha']} — already evaluated, skipping.")
        return {"status": "duplicate"}
    
    background_tasks.add_task(handle_push,facts['pusher_name'],message_text, facts["head_sha"])

# def handle_push(message_text):
    # print(message_text)




class XPAward(BaseModel):
    name:str
    xp_awarded: int 
    commit_count:int
    files_changed:int
    commit_sha:str

@app.post("/xp")
def award_xp(xp:XPAward):
    data=r.get(LEADERBOARD_KEY) 
    leaderboard= json.loads(data) if data else []
    total_xp = 0
    
    for entry in leaderboard:
        if entry[1] == xp.name:
            if r.sismember("processed_commits" , xp.commit_sha):
                return f"Already processed commit {xp.commit_sha} — no XP awarded (already recorded)."  
                    
            entry[2] += xp.xp_awarded
            total_xp = entry[2]
            r.sadd("processed_commits" , xp.commit_sha)
            break
    else:
         return {"status" :"failed" , "name" :xp.name , "error": "Maybe the name is not there?"}
        # raise HTTPException(status_code=404 , detail= f"{xp.name} not on leaderboard — run seed_interns.py?")  #lma eltool btdrb w msh bt4t8l btrg3 404 


    r.set(LEADERBOARD_KEY,json.dumps(leaderboard))
    return {"status" :"awarded" , "name" :xp.name , "total_xp": total_xp}



import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))#dy 3shan tzbtly el path bta3 xp_calculator.agent 
from xp_calculator.agent import root_agent  # or just reuse agent.py's import

evaluator_runner = InMemoryRunner(agent=root_agent, app_name="xp_evaluator")


def is_known_intern(name: str) -> bool:
    data = r.get(LEADERBOARD_KEY)
    return bool(data) and name in {entry[1] for entry in json.loads(data)}


async def handle_push(pusher_name: str, message_text: str, head_sha: str):
    if not is_known_intern(pusher_name):
        print(f"Ignoring push from {pusher_name} - not a tracked intern.")
        return

    session = await evaluator_runner.session_service.create_session(
        app_name="xp_evaluator",
        user_id=pusher_name
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )
    async for event in evaluator_runner.run_async(
        user_id=pusher_name,
        session_id=session.id,
        new_message=message
        ):
        info = extract_event_info(event)
        if info:
            print(f"[{info['type']}]: {info}")

    if head_sha:
        r.sadd("processed_pushes" , head_sha)        


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)

