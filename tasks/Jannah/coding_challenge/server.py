"""
server.py — tiny FastAPI bridge between:
  - the agent's tools (save_to_database, push_to_leaderboard)
  - leaderboard.html (polls /leaderboard and /challenge every 5s)
  - Redis Cloud (TCP-only, so the browser can't talk to it directly)

Run with: python server.py
Or:       uvicorn server:app --reload --port 8000
"""


import os   # to read from env
import json # redis save string , dic -> dupm -> str   , <- loads  (req is json)
import time # time stamp
# obj -> model_dump -> dic -> json.dumps () -> str

from fastapi import FastAPI 

app = FastAPI() # make a socket 

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel 
import redis

from dotenv import load_dotenv
load_dotenv() # load data before getenv

# request -> middleware(acc or reject , add inf , edit) -> server(endpoint)
# origin (protocol , domain & port ) -> if diff port : diff origin 
# CROS Error : if going to server in different origin , this server must give you access

# Allow the browser (leaderboard.html) to fetch from this server.
# Without this, the fetch silently fails in the browser console only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # all origins 
    allow_methods=["*"], # GET , POST , PUT , DELETE , PATCH
    allow_headers=["*"], 
)

# db connection
# ── Redis Cloud connection ──────────────────────────────
# Get these values from your Redis Cloud dashboard: Database > Public endpoint
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 6379)), # redis default port  , return str
    username=os.getenv("REDIS_USERNAME"), 
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,  # redis return data in bytes ("hello" ->b"hello") , so decode it to str
)




CURRENT_CHALLENGE_KEY = "current_challenge" #  curr -> use set (delete last)
CHALLENGE_LOG_KEY = "challenge_log"       # full history of all generated challenges use rpush
LEADERBOARD_KEY = "leaderboard"           # intern XP data, wired up in a later session


 # validation (no missing input) 
 # change from json(input) to object 
 # type converion if can(str to int) 
 # model dump 
 # dictionary  
class Challenge(BaseModel):
    topic: str
    difficulty: str
    description: str
    solution: str


# ── Health check — test this first, before anything else ─
# check server not redis
@app.get("/health")
def health():
    return {"status": "ok"}


# ── Called by the agent's save_to_database tool ─────────
# Persists every challenge ever generated to a Redis list (the permanent record)
@app.post("/save")
def save_to_database(challenge: Challenge):

    record = challenge.model_dump() #obj -> dic
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
#   using unix timestamp
#    record = {
#   "id" : 1,
#   "saved_at" : "8:11"  
#   "topic": "div in html",
#   "difficulty": "easy",
#   "description": "bla bla ",
#   "solution": "bla bla "
#   }

    r.rpush(CHALLENGE_LOG_KEY, json.dumps(record))

    return {"status": "saved", "id": record["id"]}

# called by agent to save in leaderBoard
@app.post("/challenge")
def push_to_leaderBoard(challenge : Challenge) :
    record = challenge.model_dump()
    record['id'] = int(time.time())
    r.set(CURRENT_CHALLENGE_KEY , json.dumps(record))
    return {'status':'done' , 'id' : record['id']}

#chech current challenge by leaderboard 
@app.get('/challenge')
def get_current_challenge () :
    data = r.get(CURRENT_CHALLENGE_KEY) # return str
    if data :
        return json.loads(data)   # return as a dictionary
    return {}

from google.adk.runners import InMemoryRunner 
from google.genai import types
from agent import root_agent 

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

runner = InMemoryRunner(agent = root_agent , app_name="coding_challenge")
# run runner 
@app.post("/run_agent")
# diff to every session 
async def run_agent(user_messege : str) : 
    session = await runner.session_service.create_session(
        app_name="coding_challenge" , user_id = "jjjjjjjjj" 
    )
    message = types.Content(role="user" , parts=[types.Part(text = user_messege)])
    # have any type
    steps = [] 
    final_text = [] 

    async for event in runner.run_async (
        user_id = "jjjjjjjjj" , session_id= session.id , new_message= message
    ):
        info = extract_event_info(event)
        if info:
            print(f"[{info['type']}]", info)

            steps.append(info)

            if info["type"] == "text":

                final_text.append(info["content"])

    return {"response": " ".join(final_text), "steps": steps}


# update standing
@app.get('/leaderboard')
def get_leaderBoard():
    pass 

from fastapi import Request , BackgroundTasks , HTTPException 
import hmac 
import hashlib 

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
async def get_github_webhook(request: Request , background_tasks : BackgroundTasks) :
    body = await request.body() 

    signature = request.headers.get("X-Hub-Signature-256") # hashed secret

    event_type = request.headers.get("X-Github-Event")

    expected = "sha256="+ hmac.new(WEBHOOK_SECRET , body , hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected , signature):
        raise HTTPException(status_code= 401 , detail= "Invalid signature")

    payload = await request.json()

    if(event_type == "ping") :
        print("received ping - webhook connected successfully !")
        return {"status" : "pong"}

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

def handle_push(text_msg : str) :
    print(text_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)