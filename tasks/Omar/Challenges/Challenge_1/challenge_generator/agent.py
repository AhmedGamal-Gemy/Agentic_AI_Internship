from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from groq import Groq
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is missing!")

def tool_1():
    "return the current time"
    return "the current time is: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def tool_2(input_text:str) -> str:
    "generate a challenging question based on the input text"
    return f"Generated challenging question based on: {input_text}"

def tool_3(num1:float , num2:float) -> str:
    "sum two numbers and return the result"
    return f"Sum of {num1} and {num2} is {num1 + num2}"

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile", api_key=api_key),
    name='challenge_generator',
    description='A assistant for generating challenges',
    instruction='Generate challenging questions for users to solve',
    tools = [tool_1,tool_2,tool_3]
)