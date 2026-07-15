from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm


def print_hello():
    print("hello ahmed")

def save_to_database(challenge : str, solution : str) -> str:
    """ function to save the challenge and its solution to the database """
    print(f"Challenge is {challenge}, and the solution is {solution}")
    return result 

def push_to_leaderboard(challenge : str) -> str:
    """ function to show the challenge """
    print(f"Challenge is {challenge}")

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='Challenge_Generator',
    description='A helpful assistant for generating coding challenges for an internship',
    instruction='Focus on generating valid coding challenges. and after that call save_to_database tool then show it in the leaderboard',
    tools=[save_to_database, push_to_leaderboard]
)



