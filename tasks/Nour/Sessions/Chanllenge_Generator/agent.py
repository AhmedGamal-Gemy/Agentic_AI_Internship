
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

import os
import requests
from exa_py import Exa

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8007")
exa = Exa(api_key=os.getenv("EXA_API_KEY"))


def exa_search(query: str) -> str:
    """its a tool for the agent, it Search the web for current, relevant information on a topic.
    Use this before generating a challenge to ground it in real,
    up-to-date examples rather than relying on memory alone.

    Args:
        query: The search topic or question

    Returns:
        A short summary of the most relevant search results
    """
    results = exa.search(
        query, type="auto", num_results=5, contents={"highlights": True}
    )
    """auto:automatically use the best searching method,Return max 5 search results, highlight:to extract important text highlight from each page.results is not a normal list , its exa response object that stores each individual's value(title,url,highlight)  """
    
    lines = []
    
    for item in results.results:
        highlight = item.highlights[0] if item.highlights else ""
        lines.append(f"- {item.title}: {highlight}")
    
    return "\n".join(lines) if lines else "No results found."

   

def save_to_database(topic: str, difficulty:str, description:str ,solution:str) ->str:
    """ save a generated challenge to persistent storage

        this keeps a permanent record of every challenge generated,
        and its seperate from what's shown on the leaderboard
    
    Args:
        tpoic: challenge topic
        difficulty: easy, medium, hard
        description: full challenge description

    Returns:
        confirmation message including save challenge id"""

    
    payload = {
        "Topic": tpoic ,
        "difficulty": difficulty,
        "description" : description,
        "Solution": solution,
        }
    
    response = requests.post(f"{SERVER_URL}/save", json=payload , timeout=5)
        #payload->json
    reponse.raise_for_status()
    
    data = response.json()
        #reslut, or data comes from json-> python dictionary
    return f"Challenge saved successfully with id {data['id']}"


def push_to_leaderboard(tpoic:str , difficulty: str , description: str, solution:str) ->str:
   """Post a challenge live to the leaderboard display.

    This sets the CURRENT challenge shown on the leaderboard HTML —
    it updates within 5 seconds on the projector.

    Args:
        topic: The challenge topic
        difficulty: One of "easy", "medium", or "hard"
        description: The full challenge description

    Returns:
        Confirmation message """

    payload = {"topic": topic,"difficulty": difficulty,"description": description,"solution": solution,}

    response = requests.post(f"{SERVER_URL}/challenge", json=payload, timeout=5)
    if response.status_code != 200:
        print("VALIDATION ERROR:", response.text)
    response.raise_for_status()
    
    return "Challenege posted to leaderboard live!"
    
 
 def check_duplicate_challenge():
     
# agent consists of : llm , tools, instructions
root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='root_agent',
    description='A helpful assistant for generating coding challenges for an internship.',
    instruction="""
        You are a Challenge Generator agent. Follow this sequence:

        1. Call exa_search with a query related to the requested topic. WAIT for the result.
        2. Using the search results, write a challenge with a topic, difficulty, description, and solution.
        3. Call save_to_database AND push_to_leaderboard TOGETHER in the same turn, both with the same challenge details.

        Do not call exa_search at the same time as the other tools — it must run first, alone, since you need its results before writing the challenge. But save_to_database and push_to_leaderboard should always be called together in a single turn once the challenge is written.
        """,
    tools=[save_to_database, push_to_leaderboard,exa_search]

)
