import datetime
import os
from typing import Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
# from risk_api import RiskAPIClient

# risk_api_client = RiskAPIClient(os.getenv("RISK_API_BASE_URL"))

def play_move(move: str, tool_context: ToolContext) -> dict:
    """Play a move in the game of Risk."""
    print(f"--- Tool: play_move with move: {move} ---")
    # risk_api_client.play_move(move=move)
    print(f"--- TODO: implement play_move ---")
    return {"status": "success", "move": move}


play_move_agent = Agent(
    name="play_move_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="""
    You are responsible for playing a move in the game of Risk.
    When requested, play a move in the game of Risk.
    Return the result of the move.

    If an error occurs, report it clearly.
    
    * After returning the result or error, do not take any further action and return control to the delegating agent *

    """,
    description="You are responsible for playing a move in the game of Risk.",
    tools=[play_move],
)


