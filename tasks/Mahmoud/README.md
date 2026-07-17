# AI Internship Project

A simple Python project created as part of the **Agentic AI Internship** track.

## Preview

![Project Screenshot](<Screenshot (4130).png>)

## Project Contents

- **Basic app** in `main.py` (simple demo run).
- **Modern Python project setup** via `pyproject.toml`.
- **AI agent prototype** in `test/agent.py` using `google-adk` with custom tools for:
  - generating coding challenges
  - saving challenges and solutions (mock behavior)
  - updating a leaderboard (mock behavior)

## Requirements

- Python **3.11+**
- Package manager:
  - `uv` (recommended), or
  - `pip`

## Installation

### Using uv (recommended)

```bash
uv sync
```

### Using pip

```bash
pip install -e .
```

## Run

### Run the main app

```bash
python main.py
```

Expected output:

```text
Hello from projects!
```

## Project Structure

```text
projects/
├── main.py
├── pyproject.toml
├── README.md
├── Screenshot (4130).png
└── test/
    ├── __init__.py
    └── agent.py
```

## Notes

- `test/agent.py` currently contains an AI agent prototype.
- The project can be extended by adding a clear runtime interface for the agent and connecting it to a real data source instead of the current mock setup.