from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='root_agent',
    description="Hello,I'm Root Agent.I can tell you the current time in a specified city.",
    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
    tools=[get_current_time],
)