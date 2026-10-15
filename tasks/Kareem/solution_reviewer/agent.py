import os
import requests
import asyncio
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

import litellm

load_dotenv()
litellm.drop_params = True
litellm.num_retries = 8
litellm.retry_strategy = "exponential_backoff_retry"

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8008")


def analyze_code_quality(code: str, language: str = "python") -> str:
    lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
    word_count = len(code.split())
    has_type_hints = "->" in code or ": " in code
    has_docstring = '"""' in code or "'''" in code
    has_error_handling = any(kw in code for kw in ["try", "except", "raise", "if not"])

    score = 50
    if len(lines) > 5: score += 10
    if has_type_hints: score += 15
    if has_docstring: score += 15
    if has_error_handling: score += 10

    label = "EXCELLENT" if score >= 85 else "GOOD" if score >= 65 else "NEEDS_IMPROVEMENT"

    return (
        f"Quality: {label} ({score}/100)\n"
        f"Lines: {len(lines)}, Words: {word_count}\n"
        f"Type hints: {has_type_hints}, Docstrings: {has_docstring}, Error handling: {has_error_handling}"
    )


async def award_solution_bonus(intern_name: str, quality_score: int, feedback: str) -> str:
    bonus_xp = max(5, min(50, int(quality_score * 0.4)))
    payload = {
        "intern_name": intern_name,
        "quality_score": quality_score,
        "bonus_xp": bonus_xp,
        "feedback": feedback,
    }
    try:
        response = await asyncio.to_thread(requests.post, f"{SERVER_URL}/solution_review", json=payload, timeout=10)
        response.raise_for_status()
        return f"Awarded {bonus_xp} bonus XP to {intern_name}. Review saved."
    except Exception as e:
        return f"Solution review completed (server notice: {e})"


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="solution_reviewer_agent",
    description="Reviews intern code submissions and awards quality bonus XP.",
    instruction=(
        "You review intern coding submissions for accuracy, quality, and performance.\n"
        "1. Call analyze_code_quality on the submitted code.\n"
        "2. Write clear, constructive feedback.\n"
        "3. Call award_solution_bonus with the intern's name, a score (0-100), and your feedback.\n"
        "Always use the provided tools."
    ),
    tools=[analyze_code_quality, award_solution_bonus],
)
