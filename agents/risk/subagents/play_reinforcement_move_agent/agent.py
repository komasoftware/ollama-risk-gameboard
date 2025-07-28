from callbacks import after_agent_callback_update_game_state
import os


from google.adk.agents import Agent
from tools import play_reinforcement_move

play_reinforcement_move_agent = Agent(
    name="play_reinforcement_move_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="""
You are responsible for reinforcing territories in the game of Risk.
You have {reinforcement_armies} reinforcement armies to distribute.

Your territories are:
{current_player_territories_str}

The adversaries hold the following territories:
{adversaries_territories_str}

This is the list of possible reinforcement actions that you can take:
{possible_actions_str}

Choose exactly one action and use the play_reinforcement_move tool to reinforce a territory.
You must execute exactly one call to the play_reinforcement_move tool.

Return the result of the reinforcement.
If an error occurs, report it clearly.
Do not take any further action after returning the result or error.
""",
    description="Capable of playing a reinforcement move in the game of Risk.",
    tools=[play_reinforcement_move],
    after_agent_callback=after_agent_callback_update_game_state,
)


