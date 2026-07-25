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


# update standing
@app.get('/leaderboard')
def get_leaderBoard():
    pass 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)