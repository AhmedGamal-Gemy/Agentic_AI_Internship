from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

intent_classifier = Agent(
    name="intent_classifier",
    # model=LiteLlm("groq/meta-llama/llama-prompt-guard-2-22m"),
    model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=1000),
    instruction="""Read the customer message and output ONLY one category:
billing, technical_issue, general_question, or complaint.
Respond with just the category word, nothing else — no punctuation, no explanation. after intent classification return to Orchestrator with the intent""",
disallow_transfer_to_peers=True,
output_key="intent"
)


response_generator = Agent(
    name="response_generator",
    # model=LiteLlm("groq/meta-llama/llama-prompt-guard-2-22m"),
     model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096),
    instruction="""You receive a customer message and its intent category {intent}.
Write a short, appropriate response — professional but warm.
Keep it to 2-3 sentences.""",
 disallow_transfer_to_peers=True
)

root_agent = Agent(
    # model=LiteLlm("groq/meta-llama/llama-prompt-guard-2-22m"),
    model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096),
    name="Orchestartor",
    description='A helpful assistant for user questions.',
    instruction="""You recieve a customer message.
    Step 1: Delegate to intent_classifier to get the category. WAIT for the result.
    Step 2: Delegate to response_generator, passing BOTH the original message AND the category {intent?}. WAIT for the result.
    Step 3: Return the final response to the user — nothing else, no commentary about your process.
    Do not skip either step. Do not generate a response yourself — always delegate.""",
    sub_agents=[intent_classifier , response_generator],
    # disallow_transfer_to_peers=True
)
 