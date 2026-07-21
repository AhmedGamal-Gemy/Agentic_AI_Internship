from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from exa_py import Exa
import os


# Agent : model ( llm ), tools, instructions

# framework   litellm   providers -> lock in 


exa = Exa(api_key=os.getenv("EXA_API_KEY"))


def exa_search(query: str) -> str:
    """Search the web for current, relevant information on a topic.

    Use this before generating a challenge to ground it in real,
    up-to-date examples rather than relying on memory alone.

    Args:
        query: The search topic or question

    Returns:
        A short summary of the most relevant search results
    """
    exaaaaa = exa.search(
        query, type="auto", num_results=5, contents={"highlights": True}
    )
    
    lines = []

    # You're about to step into the exciting world of AI agents. Forget simple chatbots that just answer questions. We're diving deep into the Agent Development Kit (ADK
    # Beginner Note: ADK applications are built using two main classes: Agent (defines an AI's instructions, tools, and behavior) and
    
    for item in exaaaaa.results:
        highlight = item.highlights[0] if item.highlights else ""

        lines.append(f"- {item.title}: {highlight}")
    
    return "\n".join(lines) if lines else "No results found."




root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools= [exa_search]

)



