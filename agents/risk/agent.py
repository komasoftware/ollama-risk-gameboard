import os
from google.adk.agents import Agent
from risk.subagents.new_game_agent.agent import new_game_agent
from risk.subagents.play_turn_agent.agent import play_turn_agent

# Create the Sequential Pipeline
risk_agent = Agent(
    name="risk_game_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="you are a risk game agent",
    description="""
    You are a friendly and helpful assistant that can help with the risk game.
    You are responsible for starting a new game of Risk, playing a turn in the game of Risk.  

    """,
    sub_agents=[new_game_agent, play_turn_agent],
    tools=[],
)
