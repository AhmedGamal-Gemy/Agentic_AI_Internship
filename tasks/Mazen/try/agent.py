from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

fit_classifier = Agent (
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="fit_classifier",
    instruction="""Read the candidate summary and output ONLY one category:
    strong_fit, weak_fit, or needs_review.Base this on whether their stated experience matches a junior Python developer role.
    Respond with just the category word, nothing else.after fit classification return to orchestrator with intent then to feedback_writer""",
    disallow_transfer_to_peers=True,
    output_key="fit"
)

feedback_writer = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="feedback_writer",
    instruction="""You receive a candidate summary and their fit category {fit}.
    Write a 2-sentence internal note explaining the categorization
    and one concrete next step: interview, reject, or request more info.
    Do not invent information that is not present in the candidate summary.""",
    disallow_transfer_to_peers=True
)

root_agent = Agent( 
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="orchestrator",
    instruction="""You receive an input.
    Step 1: Delegate to fit_classifier to get the category {fit?}.
    WAIT for the result.
    Step 2: Delegate to feedback_writer, passing BOTH the original input
    AND the category returned by fit_classifier.
    WAIT for the result.
    Step 3: Return the final response to the user — nothing else.
    Do not skip either step.
    Do not generate a response yourself.
    Always delegate.""",
    sub_agents=[fit_classifier,feedback_writer],
    disallow_transfer_to_peers=True
)
