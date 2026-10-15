"""Support Triage Agent
======================

Pipeline:

    Classifier Agent  -->  Knowledge Agent (uses `search_faq` and `generate_response` tools)

1. CLASSIFIER_AGENT   - reads the raw ticket, outputs category/urgency/escalation/keywords
                         as JSON, saved to state["classification"].
2. KNOWLEDGE_AGENT     - calls `search_faq` to retrieve relevant policies, then calls
                         `generate_response` to draft and save the final customer reply.

Run this file directly (`python agent.py`) to try it against a sample ticket, or
point `adk web` / `adk run` at this module (it exposes `root_agent`).
"""

import json
import os
import re
from typing import Optional

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
MODEL = LiteLlm("groq/openai/gpt-oss-20b", drop_params=True)
FAQ_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq.md")


# ---------------------------------------------------------------------------
# 1. Knowledge tools - search_faq & generate_response
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "and",
    "or", "in", "on", "with", "my", "i", "me", "how", "do", "does", "can",
    "you", "your", "it", "this", "that", "please", "help", "need", "im",
    "have", "has", "be", "get",
}


def search_faq(query: str) -> dict:
    """Searches the local company FAQ/policy file for entries relevant to a query.

    The FAQ file is a Markdown document made up of "Q: ..." / "A: ..." pairs
    (one question per "Q:" line, its policy answer on the following "A:"
    line/lines). This function scores every entry by how many significant
    words from the query it contains, and returns the best-matching entries
    so an agent can ground its reply in actual company policy instead of
    guessing.

    Args:
        query: A short phrase describing what the customer needs help with,
            e.g. "refund for duplicate charge" or "app crashes on login".

    Returns:
        dict: {
            "status": "success" | "not_found" | "error",
            "matches": [{"question": str, "answer": str, "score": int}, ...],
            "message": str (only present on "error")
        }
    """
    if not os.path.exists(FAQ_PATH):
        return {
            "status": "error",
            "matches": [],
            "message": f"FAQ file not found at {FAQ_PATH}",
        }

    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    raw_entries = re.split(r"(?m)^Q:\s*", content)[1:]
    entries = []
    for raw in raw_entries:
        parts = re.split(r"(?m)^A:\s*", raw, maxsplit=1)
        if len(parts) != 2:
            continue
        question, answer = parts
        entries.append({"question": question.strip(), "answer": answer.strip()})

    query_words = {
        w for w in re.findall(r"[a-z0-9']+", query.lower()) if w not in _STOPWORDS
    }
    if not query_words:
        return {"status": "not_found", "matches": []}

    scored = []
    for entry in entries:
        haystack = (entry["question"] + " " + entry["answer"]).lower()
        score = sum(1 for w in query_words if w in haystack)
        if score > 0:
            scored.append({**entry, "score": score})

    scored.sort(key=lambda e: e["score"], reverse=True)
    top = scored[:3]

    if not top:
        return {"status": "not_found", "matches": []}
    return {"status": "success", "matches": top}


def generate_response(
    category: str, urgency: str, escalate: bool, reply: str
) -> dict:
    """Formats and creates the final structured response string for the user.

    Args:
        category: The ticket category (e.g. billing, technical, account).
        urgency: The urgency level (e.g. critical, high, medium, low).
        escalate: Whether the ticket requires human escalation.
        reply: The customer-facing reply message grounded in FAQ context.

    Returns:
        dict: {"status": "success", "formatted_response": str}
    """
    formatted_response = (
        f"Category:{category}\n"
        f"Urgency:{urgency}\n"
        f"Escalate:{str(escalate).lower()}\n"
        f"Reply:{reply}"
    )
    return {"status": "success", "formatted_response": formatted_response}


# ---------------------------------------------------------------------------
# 2. Classifier Agent
# ---------------------------------------------------------------------------

CLASSIFIER_AGENT = Agent(
    model=MODEL,
    name="classifier_agent",
    description="Classifies support tickets into categories and urgency levels",
    instruction="""You are a Support Ticket Classifier Agent. Your task is to analyze raw customer support messages and determine:

1. TICKET CATEGORY (choose one):
   - "billing" - payment, invoices, subscriptions, charges
   - "technical" - bugs, errors, setup, configuration, integration issues
   - "account" - login, permissions, profile, access issues
   - "feature_request" - new feature ideas, enhancement suggestions
   - "general" - other miscellaneous inquiries

2. URGENCY LEVEL (choose one):
   - "critical" - immediate action needed, severe business impact, safety concerns
   - "high" - significant impact, needs attention today
   - "medium" - normal priority, will be addressed soon
   - "low" - minor issue, can wait

3. ESCALATION FLAG:
   - Set to "true" if urgency is "critical"
   - Set to "false" otherwise

4. KEYWORDS: Extract 2-3 key phrases that influenced your decision.

Respond ONLY with a JSON object with keys: category, urgency, escalation, keywords.
Do not include any text before or after the JSON object.

Analyze the message carefully and be precise in your categorization.""",
    output_key="classification",
    disallow_transfer_to_peers=True,
)


# ---------------------------------------------------------------------------
# 3. Knowledge Agent (incorporates FAQ search & response generation)
# ---------------------------------------------------------------------------

knowledge_agent = Agent(
    model=MODEL,
    name="knowledge_agent",
    instruction="""You are a support knowledge and response agent.
Read the customer's message and classification from session state: {classification}.

Steps to perform:
1. Call `search_faq` using relevant terms from the ticket to find matching policies.
2. Draft a polite, concise response using ONLY information found in the FAQ. Do not invent policies.
3. If `escalation` in classification is "true" or urgency is "critical", clearly state in the reply that human support will assist them.
4. Call `generate_response` passing category, urgency, escalate, and reply.

Return only the final result.""",
    tools=[search_faq, generate_response],
    output_key="final_response",
    disallow_transfer_to_peers=True,
)


# ---------------------------------------------------------------------------
# 4. Orchestrator
# ---------------------------------------------------------------------------

orchestrator_agent = SequentialAgent(
    name="orchestrator_agent",
    description="Classifies a support ticket, retrieves policy, and drafts a reply",
    sub_agents=[CLASSIFIER_AGENT, knowledge_agent],
)

root_agent = orchestrator_agent


# ---------------------------------------------------------------------------
# 5. Local test runner - `python agent.py`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    APP_NAME = "support_triage_app"
    USER_ID = "demo_user"
    SESSION_ID = "demo_session"

    SAMPLE_TICKETS = [
        "I've been charged TWICE for my subscription this month and the app "
        "keeps crashing every time I try to open my billing history. I need "
        "this fixed today, this is really frustrating.",
        "Hey, would it be possible to add a dark mode to the mobile app at "
        "some point? Not urgent, just a nice-to-have.",
    ]

    async def run_ticket(runner: Runner, session_service: InMemorySessionService, message: str) -> None:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID
        )
        content = types.Content(role="user", parts=[types.Part(text=message)])

        print(f"\n{'=' * 70}\nTICKET: {message}\n{'=' * 70}")
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session.id, new_message=content
        ):
            if event.content and event.content.parts:
                text = "".join(p.text or "" for p in event.content.parts if p.text)
                if text.strip():
                    print(f"\n[{event.author}]\n{text.strip()}")

        final_session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session.id
        )
        print("\n--- session.state ---")
        for key in ("classification", "final_response"):
            print(f"{key}: {final_session.state.get(key)}")

    async def main() -> None:
        session_service = InMemorySessionService()
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        for ticket in SAMPLE_TICKETS:
            await run_ticket(runner, session_service, ticket)

    asyncio.run(main())