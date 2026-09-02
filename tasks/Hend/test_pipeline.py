import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Set required API keys
os.environ["GOOGLE_API_KEY"] = "AIzaSy...test...key"
os.environ["EXA_API_KEY"] = "e376f7db-20e2-4c9d-adc3-bbdaf132ddb4"

from problem_solver.agent import root_agent, extract_event_info
from google.genai import types

# Test with a sample problem
user_message = "How does blockchain consensus work?"

message = types.Content(
    role="user",
    parts=[types.Part(text=user_message)]
)

print(f"Sending query: {user_message}")
print("-" * 60)

try:
    final_text = []
    steps = []
    
    async def run_test():
        from google.adk.runners import InMemoryRunner
        runner = InMemoryRunner(agent=root_agent, app_name="problem_solver")
        
        session = await runner.session_service.create_session(
            app_name="problem_solver", user_id="test_user"
        )
        
        async for event in runner.run_async(
            user_id="test_user", session_id=session.id, new_message=message
        ):
            info = extract_event_info(event)
            if info:
                steps.append(info)
                if info["type"] == "text":
                    final_text.append(info["content"])
        
        return " ".join(final_text), steps
    
    import asyncio
    result, steps = asyncio.run(run_test())
    print(f"RESULT: {result}")
    print(f"\nSTEPS: {len(steps)} events captured")
    for i, step in enumerate(steps):
        print(f"  Step {i+1}: {step.get('type')} - {str(step.get('content', ''))[:100]}...")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()