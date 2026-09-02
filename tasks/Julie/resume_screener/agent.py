from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm


fit_classifier = Agent(
    name="fit_classifier",
    model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096),
    instruction="""Read the candidate summary and output ONLY one category:
strong_fit, weak_fit, or needs_review.
Base this on whether their stated experience matches a junior web developer role.""",
disallow_transfer_to_peers=True,
output_key="fit_category"
)

feedback_writer = Agent(
    name="feedback_writer",
    model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096),
    instruction="""You receive a candidate summary and their fit category {fit_category}.
Write a 2-sentence internal note explaining the categorization and one
concrete next step (interview, reject, or request more info).""",
disallow_transfer_to_peers=True
)


root_agent = Agent(
    # model=LiteLlm("groq/meta-llama/llama-prompt-guard-2-22m"),
    model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096),
    name="Orchestartor",
    description='A helpful assistant for user questions.',
    instruction="""You recieve a resume.
    Step 1: Delegate to fit_classifier to get the category. WAIT for the result.
    Step 2: Delegate to feedback_writer, passing BOTH the original message AND the category {fit_category?}. WAIT for the result.
    Step 3: Return the final response to the user — nothing else, no commentary about your process.
    Do not skip either step. Do not generate a response yourself — always delegate.""",
    sub_agents=[fit_classifier , feedback_writer],
    # disallow_transfer_to_peers=True
)
