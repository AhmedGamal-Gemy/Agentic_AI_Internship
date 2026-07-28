from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

import os
import requests
from exa_py import Exa
root_agent = Agent(
     model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction="You evaluate one GitHub push and award XP to the intern who made it.\n"
        "You'll receive their name, commit count, and files changed.\n"
        "1. Decide a fair XP amount from commit_count and files_changed.\n"
        "2. Call assign_xp exactly once with the intern's name and your XP decision.\n"
        "Always use the provided tools rather than describing function calls in text.",
)
