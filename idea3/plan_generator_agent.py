from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096)

plan_generator_agent = Agent(
    model= model,
    name='plan_generator_agent',
    description='A helpful assistant for generating plans.',
    instruction='Generate detailed plans based on user requirements',
)



