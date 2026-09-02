from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

hate_speech_detector = Agent(
    name="hate_speech_detector9",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the message. Output ONLY one word: flagged or clean.
    Flag anything containing hate speech, slurs, or targeted harassment.""",
    output_key="is_hate"
)
spam_detector = Agent(
    name="spam_detector",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the message. Output ONLY one word: spam or not_spam.
    Flag promotional content, repeated links, or obvious bot-like patterns.""",
    output_key="is_spam"
)

report_generator = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="report_generator"
)

root_agent = ParallelAgent(
    
    name='root_agent',
    sub_agents=[hate_speech_detector,spam_detector]
)

moderation_pipeline = SequentialAgent(
    name="moderation_pipeline",
    sub_agents=[root_agent,report_generator]    
)
