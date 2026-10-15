from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

intent_classifier = Agent(
    name="intent_classifier",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the customer message and output ONLY one category:
    billing, technical_issue, general_question, or complaint.
    Respond with just the category word, nothing else — no punctuation, no explanation. after intent classifier return to Orchestrator """,
    disallow_transfer_to_peers = True,
    output_key = "intent"
    )

response_generator = Agent(
    name="response_generator",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You receive a customer message and its intent category {intent?}.
    Write a short, appropriate response — professional but warm. Keep it to 2-3 sentences.""",
    disallow_transfer_to_peers = True
    )

bug_classifier = Agent(
    name="bug_classifier",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the bug report and output ONLY one category:
    crash, ui_issue, feature_request, or performance.
    Respond with just the category word, nothing else.""",
    disallow_transfer_to_peers = True,
    output_key = "bug_category")

triage_writer = Agent(
    name="triage_writer",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You receive a bug report and its category {bug_category?}.
    Write a 2-sentence triage note: what team should handle it, and a suggested
    priority (low/medium/high/critical). Base priority on severity implied by the category
    (crash = usually high/critical, feature_request = usually low).""",
    disallow_transfer_to_peers = True)

root_agent = Agent(
     model=LiteLlm("groq/llama-3.3-70b-versatile"),
     name="Orchestrator",
     instruction="""You receive a customer message.
     Step 1: Delegate to bug_classifier to get the category. WAIT for the result.
     Step 2: Delegate to triage_writer, passing BOTH the original message AND the category{bug_category?}. WAIT for the result.
     Step 3: Return the final response to the user — nothing else, no commentary about your process.
     Do not skip either step. Do not generate a response yourself — always delegate.""",
     sub_agents=[bug_classifier, triage_writer],
     )