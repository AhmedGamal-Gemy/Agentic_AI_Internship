import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()


def get_redis():
    host = os.getenv("REDIS_HOST")
    if not host:
        print("REDIS_HOST not set. Skipping.")
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
            socket_timeout=5,
        )
        r.ping()
        return r
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return None


DEFAULT_INTERNS = [
    [1, "Kareem", 200],
    [2, "Omar", 180],
    [3, "Gemy", 175],
    [4, "Julie", 130],
    [5, "Mariam", 125],
    [6, "Mazen", 115],
    [7, "Shahd", 110],
    [8, "Nour", 100],
]

if __name__ == "__main__":
    r_client = get_redis()
    if r_client:
        r_client.set("leaderboard", json.dumps(DEFAULT_INTERNS))
        print("Leaderboard seeded!")
    else:
        print("No Redis connection.")
