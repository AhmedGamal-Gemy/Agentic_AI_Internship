from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import SequentialAgent
from google.adk.agents import ParallelAgent


model = LiteLlm(model="groq/llama-3.3-70b-versatile")


# hate_speech_detector = Agent(
#     name="hate_speech_detector",
#     model=model,
#     instruction="""
#     Read the message.
#     Output ONLY one word: flagged or clean.

#     Flag anything containing hate speech, slurs, or targeted harassment.
#     """,
#     output_key="hate_speech_flag"
# )


# spam_detector = Agent(
#     name="spam_detector",
#     model=model,
#     instruction="""
#     Read the message.
#     Output ONLY one word: spam or not_spam.

#     Flag promotional content, repeated links, or obvious bot-like patterns.
#     """,
#     output_key="spam_flag"
# )


# parallel_agent = ParallelAgent(
#     name="moderation_agent",
#     sub_agents=[
#         hate_speech_detector,
#         spam_detector
#     ]
# )

# report_generator = Agent(
#     name="report_generator",
#     model=model,
#     instruction="""
#     Generate a moderation report based on the flags detected.
#     """,
#     output_key="moderation_report"
# )


# moderation_agent = SequentialAgent(
#     name="moderation_agent",
#     sub_agents=[
#         parallel_agent,
#         report_generator
#     ]
# )


# root_agent = moderation_agent


skills_checker = Agent(
    name="skills_checker",
    model=model,
    instruction="""Read the candidate summary. Output ONLY: strong_skills, weak_skills, or unclear.
    Judge based on stated technical experience relevant to a Python developer role."""

)

culture_fit_checker = Agent(
    name="culture_fit_checker",
    model=model,
    instruction="""Read the candidate summary. Output ONLY: good_fit or needs_review.
    Judge based on communication style and stated values, not technical skill.""")


parallel_agent = ParallelAgent(
    name="parallel_check",
    sub_agents=[skills_checker,culture_fit_checker])


final_decision = Agent(
    name="final_decision",
    model=model,
    instruction="""You receive results from skills_checker AND culture_checker.
    Write a 2-sentence hiring recommendation using BOTH results — do not
    make a decision based on only one of them."""
)

seq_agent=SequentialAgent(
    name="Sequential_Agent",
    sub_agents=[parallel_agent,final_decision]
)

root_agent =seq_agent

