from google.adk.agents.llm_agent import Agent 
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent


model=LiteLlm("openrouter/meta/muse-spark-1.2",max_tokens=4096)

# — Two independent checks — safe to run in parallel —
hate_speech_detector = Agent(
    name="hate_speech_detector",
    model=model,
    instruction="""Read the message. Output ONLY one word: flagged or clean.
    Flag anything containing hate speech, slurs, or targeted harassment.""",
    output_key= "is_hate"
)

spam_detector = Agent(
    name="spam_detector",
    model=model,
    instruction="""Read the message. Output ONLY one word: spam or not_spam.
    Flag promotional content, repeated links, or obvious bot-like patterns. is hate ? {is_hate}""",
    output_key="is_spam"
)
moderation_pipeline=ParallelAgent(
    name="moderation_pipeline" ,
    sub_agents=[hate_speech_detector , spam_detector]
)

parallel_pipeline = ParallelAgent(
    name="parallel_pipeline ",
    sub_agents=[spam_detector, hate_speech_detector],
)

# Needs BOTH detector results — must run after, sequentially —
report_generator = Agent(
    name="report_generator",
    model=model,
    instruction="""You receive results from hate_speech_detector and spam_detector {is_hate} , {is_spam}.
Write a 1-2 sentence moderation report: was this message flagged, for what reason(s), and what action should be taken — approve, remove, or review.""",)


# Combine: parallel step first, then sequential step after —
moderation_pipeline = SequentialAgent(
    name="moderation_pipeline",
    sub_agents=[parallel_pipeline, report_generator],
)
root_agent=moderation_pipeline