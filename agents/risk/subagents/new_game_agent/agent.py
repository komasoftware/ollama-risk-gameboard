
import os

from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from risk_api import RiskAPIClient
from callbacks import after_agent_callback_update_game_state

risk_api_client = RiskAPIClient(os.getenv("RISK_API_BASE_URL"))

# class NewGameResponse(BaseModel):
#     status: str = Field(
#         description="The status of the new game. Should be 'success' or 'error'."
#     )
#     players: int = Field(
#         description="The number of players in the new game."
#     )
#     start_time: datetime.datetime = Field(
#         description="The start time of the new game."
#     )

# def get_current_time() -> dict:
#     """Get the current time in the format YYYY-MM-DD HH:MM:SS"""
#     return {
#         "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#     }

def start_new_game(num_players: int, tool_context: ToolContext) -> dict:
    """Start a new game of Risk."""
    print(f"--- Tool: start_new_game with num_players: {num_players} ---")

    success = risk_api_client.new_game(num_players=num_players)

    return {"status": "success" if success else "error", "players": num_players}


new_game_agent = Agent(
    name="new_game_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="""
    You are responsible for starting a new game of Risk. 

    When requested, initialize a new game for minimum 2 and maximum 6 of players using the Risk API. 
    You start a new game by calling the start_new_game tool.
    Make exactly one call to the start_new_game tool if the number of players is between 2 and 6.

    If less than 2 players or more than 6 players are requested, report an error and return control to the delegating agent.
    If an error occurs, report it clearly. 

    Respond with the result of the start_new_game tool being successful or not.

    example:
    User: Let's start a new game with 4 players
    Response: New game started with 4 players.

    """,
    description="You are responsible for starting a new game of Risk.",
    tools=[start_new_game],
    after_agent_callback=after_agent_callback_update_game_state,
    output_key="new_game_response"
)


