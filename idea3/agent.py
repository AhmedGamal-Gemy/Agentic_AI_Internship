from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
import dotenv  
from idea3.plan_generator.agent import plan_generator
dotenv.load_dotenv()
from google.adk.agents.sequential_agent import SequentialAgent
from idea3.goal_analyzer.agent import goal_analyzer
from idea3.quiz_agent.agent import quiz_agent


model = LiteLlm("openrouter/meta/muse-spark-1.2", max_tokens=4096)

seq_agent=SequentialAgent(
    name="Sequential_Agent",
    sub_agents=[goal_analyzer, plan_generator],

)

orchestration_agent = Agent(
    name="Orchestration_Agent",
    sub_agents=[seq_agent, quiz_agent],
)

root_agent =orchestration_agent



