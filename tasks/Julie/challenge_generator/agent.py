from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

def print_hello():
    print("hello")


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='Challenge_Generator',
    description='A helpful assistant for generating coding challenges for an internship.',
    instruction='Focus on generating valid coding challenges',
    tools=[print_hello]
)

