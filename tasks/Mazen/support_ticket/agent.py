from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

urgency_checker = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="urgency_checker",
    instruction="""Read the support ticket. Output ONLY: low, medium, or high urgency.""",
    disallow_transfer_to_peers=True,
    output_key="urgency"
)

sentiment_checker = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="sentiment_checker",
    instruction="""Read the support ticket. Output ONLY: frustrated, neutral, or satisfied.""",
    disallow_transfer_to_peers=True,
    output_key="sentiment"
)

parallel_checks = ParallelAgent(
    name="parallel_checks",
    sub_agents=[urgency_checker, sentiment_checker],
)

routing_decision = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="routing_decision",
    instruction="""You receive results from urgency_checker AND sentiment_checker {urgency} {sentiment}.
    Write a 2-sentence routing note: which queue this goes to, and whether it
    needs a senior agent (high urgency + frustrated = always senior agent).""",
)

root_agent = SequentialAgent(
    name="support_ticket_router",
    sub_agents=[parallel_checks,routing_decision,],
)