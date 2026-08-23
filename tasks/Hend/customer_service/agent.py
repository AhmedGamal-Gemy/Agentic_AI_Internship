from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

# intent_classifier = Agent(
#     name="intent_classifier",
#     model=LiteLlm("groq/llama-3.3-70b-versatile"),
#     instruction="""Read the customer message and output ONLY one category:
#     billing, technical_issue, general_question, or complaint.
#     Respond with just the category word, nothing else — no punctuation, no explanation.""",
#     disallow_transfer_to_peers=True,
#     output_key="intent"


# )

# response_generator = Agent(
#     name="response_generator",
#     model=LiteLlm("groq/llama-3.3-70b-versatile"),
#     instruction="""You receive a customer message and its intent category {intent}.
#     Write a short, appropriate response — professional but warm.
#     Keep it to 2-3 sentences.""",
#     disallow_transfer_to_peers=True
# )

# root_agent = Agent(
#     model=LiteLlm("groq/llama-3.3-70b-versatile"),
#     name="Orchestrator",
#     instruction="""You receive a customer message.
#     Step 1: Delegate to intent_classifier to get the category. WAIT for the result.
#     Step 2: Delegate to response_generator, passing BOTH the original message AND the category {intent?}. WAIT for the result.
#     Step 3: Return the final response to the user — nothing else, no commentary about your process.
#     Do not skip either step. Do not generate a response yourself — always delegate.""",
#     sub_agents=[intent_classifier, response_generator]
# )
topic_classifier = Agent(
    name="topic_classifier",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the student's question and output ONLY one category:
    math, science, history, or language.
    Respond with just the category word, nothing else.""",
    disallow_transfer_to_peers=True,
    output_key="topic"
)
explanation_writer = Agent(
    name="explanation_writer",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You receive a student's question and its subject category {topic}.
    Write a short, clear explanation (3-4 sentences) appropriate for a high school student.""",
    disallow_transfer_to_peers=True
)

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Orchestrator",
    instruction="""You receive an input.
    Step 1: Delegate to topic_classifier to get the category{topic?}. WAIT for the result.
    Step 2: Delegate to explanation_writer, passing BOTH the original input AND the category. WAIT for the result.
    Step 3: Return the final response to the user — nothing else.
    Do not skip either step. Do not generate a response yourself — always delegate.
    For EVERY new input, ALWAYS follow these steps from the beginning """,
    sub_agents=[topic_classifier, explanation_writer]
    )