# Agentic AI Internship

A one-month, hands-on internship where you build production-grade multi-agent systems using **Google ADK** — by hand, first. AI coding assistance (OpenCode + OMO) is revealed only in the final session, once you've felt every concept in your fingers.

---

## Repo structure

```
.
├── project/            # The instructor's build — do not edit
├── sessions/           # Live-build code from each session, one subfolder per session
├── tasks/
│   ├── your-name/      # Your personal folder — gap-day homework and challenge submissions
│   ├── another-name/
│   └── ...
└── README.md
```

**`project/`**
This is the instructor's own build, developed live across sessions as a running example of everything the internship covers. It's here for reference — read it, learn from it, but it isn't where your work goes.

**`sessions/`**
One folder per session (`session-01/`, `session-02/`, …). This is where you commit the code built live in class plus your in-session exercise. Keep it — you'll build on top of it in later sessions.

**`tasks/`**
One folder per intern, named after you (e.g. `tasks/jane-doe/`). All your gap-day homework and challenge submissions go inside your own folder — organize it however makes sense to you (e.g. `tasks/jane-doe/challenge-01/`). Keep your work inside your own folder only — don't commit into someone else's.

---

## Setup

```bash
# clone and checkout your branch
git clone <repo-url>
cd <repo-name>
git checkout <your-branch-name>

# python environment + dependencies (uv handles both)
uv init
uv add google-adk litellm python-dotenv

# set your Groq API key
cp .env.example .env
# then open .env and paste your key in:
# GROQ_API_KEY=your-key-here
```

**Never commit your `.env` file.** Make sure `.env` is in `.gitignore` before your first push.

Every agent in this program uses **Groq models via LiteLLM**, not the ADK default (Gemini/Vertex). Your model config will look like:

```python
from dotenv import load_dotenv
load_dotenv()

from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent

root_agent = Agent(
    model=LiteLlm(model="groq/llama-3.3-70b-versatile"),
    name="my_agent",
    instruction="...",
    tools=[...],
)
```

Run any agent with:

```bash
uv run adk web
```

---

## Workflow

1. Work happens **in session** (concept → live build → exercise) and **on gap days** (homework, feeding into the next session's opener).
2. Commit your session work to `sessions/session-XX/` before the next session starts.
3. Submit gap-day homework to your personal folder under `tasks/<your-name>/`.
4. One core file per project must be `manual_agent.py`: written entirely by hand, with inline comments explaining your design decisions. No AI assistance on this file — ever, including after the final-session reveal.

---

## Ground rules

- **No AI coding assistance until Session 12.** Every agent, tool, and orchestration pattern is written by hand until then. This is the whole point — you can't judge what a tool is doing for you until you've done it yourself.
- **Type annotations are mandatory** on every tool function parameter.
- **Every tool needs a docstring.**
- Break things on purpose sometimes. It's how you learn what the annotations and structure are actually for.

---

## Capstone requirements (non-negotiable, announced Session 1)

Your own capstone lives in `sessions/` and later gets its own dedicated project space as the internship progresses. Every capstone must meet all five requirements below:

| # | Requirement | Definition |
|---|---|---|
| 1 | At least 2 agents | An orchestrator + at least one sub-agent. Multiple tool calls on one agent doesn't count. |
| 2 | At least 1 MCP server | Public or custom-built. |
| 3 | Webhook or event trigger | Must react to a real external event, not just a manual API call. |
| 4 | Eval suite | At least 5 documented test cases with pass/fail results. |
| 5 | `manual_agent.py` | One core component, written entirely by hand, inline comments explaining every decision. |

---

## Questions

Ask in session, or open an issue in this repo. If it's a good question, it might become next week's challenge.