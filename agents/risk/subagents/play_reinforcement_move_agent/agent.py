from callbacks import after_agent_callback_update_game_state
import os


from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from risk_api import RiskAPIClient

risk_api_client = RiskAPIClient(os.getenv("RISK_API_BASE_URL"))

def play_reinforcement_move(territory: str, armies: str, tool_context: ToolContext) -> dict:
    """Play a reinforcement move in the game of Risk."""
    print(f"--- Tool: reinforce {territory} with {armies} armies ---")
    # Convert armies to int to match the expected type
    risk_api_client.reinforce(
        player_id=tool_context.state["game_state"].get_current_player_id(),
        territory=territory,
        num_armies=int(armies)
    )
    return {"status": "success", "reinforced": f"reinforced {territory} with {armies} armies"}


play_reinforcement_move_agent = Agent(
    name="play_move_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="""
You are responsible for reinforcing a territory in the game of Risk.

The enemies hold the following territories:
{adversaries_territories_str}

This is the list of possible reinforcement actions that you can take:
{possible_actions_str}

Choose exactly one action and use the play_reinforcement_move tool to reinforce a territory.
You must execute exactly one call to the play_reinforcement_move tool.

Return the result of the reinforcement.
If an error occurs, report it clearly.
Do not take any further action after returning the result or error.
""",
    description="You are responsible for playing a move in the game of Risk.",
    tools=[play_reinforcement_move],
    after_agent_callback=after_agent_callback_update_game_state,
)


