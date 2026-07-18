# from google.adk.agents.llm_agent import Agent

# root_agent = Agent(
#     model='gemini-3.5-flash',
#     name='root_agent',
#     description='A helpful assistant for user questions.',
#     instruction='Answer user questions to the best of your knowledge',
# )

from google.adk.agents.llm_agent import Agent


# Tool 1
def generate_challenge(topic: str) -> str:
    """
    Generate a coding challenge.
    """
    return f"Create a coding challenge about {topic}"


# Tool 2
def save_to_database(challenge: str, solution: str) -> str:
    """
    Save challenge and solution to database.
    """
    print(f"Saving: {challenge}")
    print(f"Solution: {solution}")

    return "Saved successfully"


# Tool 3
def push_to_leaderboard(username: str, score: int) -> str:
    """
    Push user score to leaderboard.
    """
    return f"{username} added with score {score}"


root_agent = Agent(
    model="groq/llama-3.1-8b-instant",
    name="challenge_generator",
    description="AI assistant for generating coding challenges.",
    
    instruction="""
You are a Coding Challenge Assistant.

Your job:
1. Generate programming challenges.
2. Save challenges when requested.
3. Update leaderboard.

Always use tools when needed.
""",

    tools=[
        generate_challenge,
        save_to_database,
        push_to_leaderboard
    ],
)