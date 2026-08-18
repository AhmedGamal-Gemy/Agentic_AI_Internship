# problem_solver

Multi-agent system that solves coding problems: the user submits a problem,
the orchestrator delegates to specialized agents (planner, researcher, solver,
critic), and only a **verified** solution (passed code execution + critique)
is returned. Built with Google ADK + LiteLLM.