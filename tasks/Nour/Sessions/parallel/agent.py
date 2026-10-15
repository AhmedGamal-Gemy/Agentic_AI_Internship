from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.sequential_agent import SequentialAgent

model = LiteLlm(model="groq/llama-3.3-70b-versatile")

hate_speech_detector = LlmAgent(
    name="hate_speech_detector",
    model=model,
    instruction="""Read the message. Output ONLY one word: flagged or clean.
Flag anything containing hate speech, slurs, or targeted harassment.""",
    output_key="is_hate",
)

spam_detector = LlmAgent(
    name="spam_detector",
    model=model,
    instruction="""Read the message. Output ONLY one word: spam or not_spam.
Flag promotional content, repeated links, or obvious bot-like patterns.
Hate speech result: {is_hate}""",
    output_key="is_spam",
)

moderation_pipeline = SequentialAgent(
    name="moderation_pipeline",
    sub_agents=[hate_speech_detector, spam_detector],
)

root_agent = moderation_pipeline