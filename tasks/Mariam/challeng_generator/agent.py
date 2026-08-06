from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from exa_py import Exa
import os


exa = Exa(api_key=os.getenv("EXA_API_KEY"))

def exa_search(query: str) -> str:
    exa_results = exa.search_and_contents(
        query,
        num_results=3,
        highlights=True,

    )

    lines = []
    for item in exa_results.results:
        highlight = item.highlights[0] if item.highlights else ""
        lines.append(f"- {item.title}: {highlight}")

    return "\n".join(lines) if lines else "No results found."


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="root_agent",
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[exa_search]
)
