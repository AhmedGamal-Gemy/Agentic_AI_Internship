from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from exa_py import Exa
import os

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="root_agent",
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
)


