from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent

hate_speech_detector = Agent(
    name="hate_speech_detector",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the message. Output ONLY one word: flagged or clean.
    Flag anything containing hate speech, slurs, or targeted harassment.""",
    output_key = "is_hate"
)

spam_detector = Agent(
    name="spam_detector",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""Read the message. Output ONLY one word: spam or not_spam.
    Flag promotional content, repeated links, or obvious bot-like patterns. is hate ? {is_hate?}""",
    output_key="is_spam"
)

#moderation_pipeline = SequentialAgent(
#    name="moderation_pipeline",
#    sub_agents=[hate_speech_detector, spam_detector]
#)

moderation_pipeline = ParallelAgent(
    name="moderation_pipeline",
    sub_agents=[hate_speech_detector, spam_detector]
)

report_generator = Agent(
    name="report_generator",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You receive results from hate_speech_detector and spam_detector{is_hate?, is_spam?}.
    Write a 1-2 sentence moderation report: was this message flagged, for what
    reason(s), and what action should be taken (approve, remove, or review).""",
)

#sequential_modertation_pipeline = SequentialAgent(
#    name="sequential_modertation_pipeline",
#    sub_agents=[moderation_pipeline, report_generator]
#)
#----------------------------------------------------------------
relevance_checker = Agent(
    name="relevance_checker",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You Take The Interests Part In The Content As Input And The Output Is Either Only : relevant or not_relevant. """,
    output_key="is_relevant"
)

safety_checker = Agent(
    name="safety_checker",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You Take A Piece of Content As Input And The Output Is Either Only : safe or unsafe.""",
    output_key="is_safe"
)

parallel_checks = ParallelAgent(
    name="parallel_checks",
    sub_agents=[relevance_checker, safety_checker],
)

recommendation_decision = Agent(
    name="recommendation_decision",
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    instruction="""You Take The Results From relevance_checker and safety_check
    As input {is_relevant?}{is_safe?} And The Output Is Either Only : recommend or do_not_recommend.
    Must Be Relevant And Safe To Be Recommend , Otherwised He Will Be not Recommend""",
)

sequential_modertation_pipeline = SequentialAgent(
    name="sequential_modertation_pipeline",
    sub_agents=[parallel_checks, recommendation_decision]
)

root_agent = sequential_modertation_pipeline