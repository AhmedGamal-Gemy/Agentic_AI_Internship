from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import LiteLlm 

    
def print_hello():
    print("Hello Nour!")
    
def save_to_database(challenge : str , solution : str):
    print(f"challenge is {challenge}, and solution is {solution}") 
    
def save_to_database(challenge :str):
     print(f"challenge is {challenge}, and solution is {solution}") 


def add(x,y):
    return x+y

def multiply(x,y):
    return x*y
                  
root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='Chanllenger',
    description='A helpful assistant for generating questions to help you develop your skills.',
    instruction='focus on generating valid coding questions. Then call save_to_database'),

tools=[print_hello, save_to_database , add , multiply] , 