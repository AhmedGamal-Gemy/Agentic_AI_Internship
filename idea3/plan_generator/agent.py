from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import dotenv  


dotenv.load_dotenv()

model = LiteLlm("openrouter/meta/muse-spark-1.2", max_tokens=4096)

plan_generator = Agent(
    name="plan_generator",
    model=model,
    description="Generates a customized learning plan based on the Goal Analyzer's output.",
    instruction="""You are the Plan Generator Agent.

Create a customized learning plan only when a valid Goal Analyzer output is provided.

Use the user's topic, goal, level, and duration from the Goal Analyzer's output.

If the input is not a valid Goal Analyzer output, do not create a learning plan.
Return a short message asking for a valid learning goal.

When a valid goal is provided:
- Divide the plan into weeks.
- Include objectives, topics, exercises, and a small task.
- Make it realistic, progressive, and practical.
- Return valid JSON only.""",
    output_key="learning_plan"
)


