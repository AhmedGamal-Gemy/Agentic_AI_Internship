from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import Agent
from google.genai import types, client
import os
from dotenv import load_dotenv
load_dotenv()

# Set API key from provided key
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Use google.genai client directly
genai_client = client.Client()

model_name = "gemini-3.5-flash-lite"


# === EXTRACT EVENT INFO (from server.py pattern) ===
def extract_event_info(event) -> dict | None:
    """Pull out whatever's meaningful from an event: text, tool call, or tool result."""
    if not event.content or not event.content.parts:
        return None

    for part in event.content.parts:
        if part.text:
            return {"type": "text", "content": part.text}
        if part.function_call:
            return {
                "type": "tool_call",
                "tool": part.function_call.name,
                "args": part.function_call.args,
            }
        if part.function_response:
            return {
                "type": "tool_result",
                "tool": part.function_response.name,
                "result": part.function_response.response,
            }
    return None


# === PARALLEL SUB-AGENTS (independent tasks) ===

researcher = Agent(
    name="researcher",
    model=model_name,
    instruction="""Search the web comprehensively for the user's problem.
    Provide key facts, latest developments, and credible sources.
    Output format: concise bullet points with sources.""",
    output_key="research_findings"
)

analysis_agent = Agent(
    name="analyzer",
    model=model_name,
    instruction="""Analyze the user's problem.
    Break down into sub-problems, identify constraints, and suggest approach.
    Output format: structured analysis with priorities.""",
    output_key="problem_analysis"
)

# === PARALLEL AGENT ===
parallel_analysis = ParallelAgent(
    name="independent_analysis",
    sub_agents=[researcher, analysis_agent],
    description="Run research and analysis concurrently"
)

# === SEQUENTIAL SUB-AGENT (synthesis) ===
# Runs AFTER parallel agents complete

synthesizer = Agent(
    name="synthesizer",
    model=model_name,
    instruction="""Synthesize the following into a comprehensive answer:

    Research findings: {research_findings?}
    Problem analysis: {problem_analysis?}

    Provide a complete, well-structured answer that integrates both perspectives.
    Address the original user problem thoroughly.""",
    description="Synthesize parallel agent results into final answer"
)

# === ROOT AGENT (mixed architecture) ===
# Sequential: first parallel analysis, then synthesis
root_agent = SequentialAgent(
    name="problem_solver",
    sub_agents=[
        parallel_analysis,   # Step 1: Run parallel tasks
        synthesizer          # Step 2: Synthesize results
    ],
    description="Solves user problems using mixed sequential/parallel agents"
)