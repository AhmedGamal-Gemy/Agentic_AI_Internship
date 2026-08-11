from dotenv import load_dotenv
load_dotenv()

from challenge_generator.agent import root_agent as challenge_agent
from xp_calculator.agent import root_agent as xp_agent
from solution_reviewer.agent import root_agent as reviewer_agent


def main():
    print(f"challenge agent: {challenge_agent.name}")
    print(f"xp agent: {xp_agent.name}")
    print(f"reviewer agent: {reviewer_agent.name}")


if __name__ == "__main__":
    main()
