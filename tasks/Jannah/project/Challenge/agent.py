from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

def factorial (num : int) -> int :
    '''return factorial of a non negative number'''
    res = 1 
    for i in range(1 , num+1) :
        res*=i 
    return res

def add (first : float , second : float ) ->float :
    '''add two numbers'''
    return first + second 

def absolute (first : float , second : float ) ->float :
    '''return the absolute differnce between two numbers'''
    return abs(first - second)
  

def dif (first : float , second : float ) ->float :
    """Subtract the second number from the first.""" 
    return first - second

def mul (first : float , second : float ) -> float :
    """Multiply two numbers"""
    return first*second
 
def div (first : float , second : float ) -> float :
    """Divide the first number by the second"""
    if(second ==0 ) :
         raise ValueError("Cannot divide by zero")
    return first/second


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile") ,
    name='Challenge_Agent',
    description='A helpful Assestant to help you in solving problems',
    instruction='''You are an AI specialized in reading and analysis problems and find
    the best , fastest code to this problem
    ''',
    tools = [
        factorial , add , absolute , div , mul , dif  , 
    ], 
)
