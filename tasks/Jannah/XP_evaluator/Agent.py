from google.adk.runners import InMemoryRunner 
from coding_challenge.agent import  root_agent , save_to_database , push_to_leaderBoard

runner = InMemoryRunner(
    agent=root_agent,
    app_name="xp_evaluator"
)
