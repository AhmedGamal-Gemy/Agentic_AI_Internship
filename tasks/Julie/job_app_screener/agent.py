from google.adk.agents.llm_agent import Agent 
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent

# root_agent = Agent(
#     model='<FILL_IN_MODEL>',
#     name='root_agent',
#     description='A helpful assistant for user questions.',
#     instruction='Answer user questions to the best of your knowledge',
# )

model =LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096)

# Option A: Job Application Screener (Parallel: Skills + Culture Fit)
# Parallel agents:

skills_checker = Agent(
    name="skills_checker",
    model=model,
    instruction="""Read the candidate summary. Output ONLY: strong_skills, weak_skills, or unclear.
    Judge based on stated technical experience relevant to a web developer role.""",
    output_key="skills"
)

culture_checker = Agent(
    name="culture_checker",
    model=model,
    instruction="""Read the candidate summary. Output ONLY: good_fit or needs_review.
    Judge based on communication style and stated values, not technical skill.""",
    output_key="culture"
)

parallel_checks = ParallelAgent(
    name="parallel_checks",
    sub_agents=[skills_checker, culture_checker],
)

# --- Final decision step (sequential after parallel) ---
final_decision = Agent(
    name="final_decision",
    model=model,
    instruction="""You receive results from skills_checker AND culture_checker {skills} , {culture}.
    Write a 2-sentence hiring recommendation using BOTH results – do not make a decision based on only one of them.""",
)

# --- Full pipeline: parallel first, then sequential ---
job_screener_pipeline = SequentialAgent(
    name="job_screener_pipeline",
    sub_agents=[parallel_checks, final_decision],
)

# --- Root agent entry point ---
root_agent = job_screener_pipeline

