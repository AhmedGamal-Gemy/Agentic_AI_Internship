from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
def calculate(a,b):
    """function to calculate the sum of two numbers"""
    sum = a + b
    return sum
root_agent = Agent (
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='challenge_assistant',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[calculate]
)