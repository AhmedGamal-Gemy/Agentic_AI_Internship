# Kareem's Agentic AI Project

Three agents built with Google ADK for the Agentic AI Internship.

## Agents

- `challenge_generator/` — generates coding challenges, calibrates difficulty, posts them live
- `xp_calculator/` — evaluates GitHub pushes and awards XP to interns
- `solution_reviewer/` — reviews intern code submissions and awards quality bonus XP

## Running

```bash
cd tasks/Kareem

# seed the leaderboard (needs Redis credentials in .env)
python seed_interns.py

# start the server
uvicorn challenge_generator.server:app --port 8008 --reload
```

## Environment Variables

```
GROQ_API_KEY=
EXA_API_KEY=
REDIS_HOST=
REDIS_PORT=
REDIS_USERNAME=
REDIS_PASSWORD=
GITHUB_WEBHOOK_SECRET=
SERVER_URL=http://localhost:8008
```
