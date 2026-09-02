from pathlib import Path
import json

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm


PROGRESS_FILE = Path(__file__).with_name("progress.json")

DEFAULT_PROGRESS = {
    "topic": "",
    "current_week": 1,
    "current_topic": "",
    "completed_topics": [],
    "quiz_score": 0,
    "total_questions": 0,
    "difficulty": "easy",
    "topics_that_need_review": [],
}


def read_progress_file() -> dict:
    """Read progress.json safely and create it if it does not exist."""
    if not PROGRESS_FILE.exists():
        write_progress_file(DEFAULT_PROGRESS.copy())
        return DEFAULT_PROGRESS.copy()

    try:
        progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        progress = DEFAULT_PROGRESS.copy()
        write_progress_file(progress)

    return progress


def write_progress_file(progress: dict) -> None:
    """Write progress data to progress.json."""
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2),
        encoding="utf-8",
    )


def progress_tool(action: str, updates: dict | None = None) -> dict:
    """
    Read, update, or reset learning progress.

    Args:
        action: Use "read", "update", or "reset".
        updates: Fields to update when action is "update".
    """
    progress = read_progress_file()

    if action == "read":
        return progress

    if action == "reset":
        progress = DEFAULT_PROGRESS.copy()
        write_progress_file(progress)
        return progress

    if action == "update":
        if updates is None:
            updates = {}

        # Keep old progress and update only the fields provided.
        progress.update(updates)

        write_progress_file(progress)
        return progress

    return {
        "error": "Invalid action. Use 'read', 'update', or 'reset'."
    }


quiz_agent = Agent(
    model=LiteLlm(
        model="openrouter/meta/muse-spark-1.2",
        max_tokens=4096,
    ),
    name="root_agent",
    description="A quiz agent for a Learning / Career Coach system.",
    instruction="""
You are the Quiz Agent for a Learning / Career Coach system.

Your job is to help the user practice the current learning topic using short,
adaptive multiple-choice quizzes.

You must always use progress_tool for reading and updating progress.
Do not manually assume progress values without reading progress first.

Workflow:

1. Read the user's progress using progress_tool with action="read".

2. Identify:
   - the main learning topic
   - the current learning topic
   - the current difficulty
   - quiz_score
   - total_questions
   - completed_topics
   - topics_that_need_review

3. If progress is missing important fields, ask the user for their learning goal
   or current topic before generating a quiz.

4. Generate exactly one quiz question based on the current learning topic.

5. The quiz question must:
   - match the current difficulty: easy, medium, or hard
   - be multiple choice
   - include exactly 4 answer choices
   - label choices as A, B, C, and D
   - have exactly one correct answer
   - be dynamically generated, not hard-coded

6. When asking the question:
   - do not reveal the correct answer
   - ask the user to reply with A, B, C, or D

7. When the user answers:
   - check whether the answer is correct
   - say "Correct!" or "Incorrect."
   - give a short explanation
   - update total_questions by 1
   - update quiz_score by 1 only if the answer is correct

8. Adapt difficulty after each answer:
   - easy + correct -> medium
   - medium + correct -> hard
   - hard + correct -> hard
   - easy + wrong -> easy
   - medium + wrong -> easy
   - hard + wrong -> medium

9. Save the new difficulty in progress.json using progress_tool.

10. If the answer was correct:
    - add the current topic to completed_topics when appropriate
    - continue with another useful question

11. If the answer was wrong:
    - keep or lower the difficulty
    - add the current topic to topics_that_need_review
    - give a helpful explanation without being too long

12. After giving feedback, ask the next quiz question unless the user says exit.

13. If the user asks for a recap, generate a Weekly Recap using progress_tool.
    The recap should include:
    - completed topics
    - quiz score
    - current difficulty
    - topics that need review
    - recommended next step

Important rules:

- Always read progress before generating a quiz or checking an answer.
- Always update progress after checking an answer.
- Never generate more than one quiz question at a time.
- Never reveal the correct answer before the user answers.
- Never hard-code quiz questions.
- Keep responses concise and beginner-friendly.
""",
    tools=[progress_tool],
)