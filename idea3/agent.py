from google.adk.models.lite_llm import LiteLlm
import dotenv  
from idea3.plan_generator.agent import plan_generator
dotenv.load_dotenv()
from google.adk.agents.sequential_agent import SequentialAgent


model = LiteLlm("openrouter/meta/muse-spark-1.2", max_tokens=4096)

seq_agent=SequentialAgent(
    name="Sequential_Agent",
    sub_agents=[plan_generator,]
)

root_agent =seq_agent



