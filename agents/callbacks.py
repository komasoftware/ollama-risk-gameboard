import os
from risk_api import RiskAPIClient
from typing import Optional

from game_state import GameStateRoot
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

risk_api_client = RiskAPIClient(os.getenv("RISK_API_BASE_URL"))

def update_game_state(state: dict) -> None:
    """
    Update the game state with the latest game state from the Risk API.
    """
    risk_api_response = risk_api_client.get_game_state()

    # After updating state['game_state'], also write flat prompt variables for templating
    game_state_obj = GameStateRoot.from_risk_api_response(risk_api_response)
    state["game_state"] = game_state_obj
    state["current_player_name"] = game_state_obj.get_current_player_name()
    state["current_player_id"] = game_state_obj.get_current_player_id() + 1  # 1-based for prompt
    round_num = game_state_obj.get_current_game_round()
    state["current_game_round"] = f"round {round_num}" if round_num > 0 else "the first round"
    state["current_turn_phase"] = game_state_obj.get_current_turn_phase()
    state["possible_actions_str"] = game_state_obj.get_possible_actions_str()
    state["adversaries_territories_str"] = game_state_obj.get_adversaries_territories_str()


def after_agent_callback_update_game_state(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Update the game state with the latest game state from the Risk API.
    """
    state = callback_context.state
    update_game_state(state)
    
    return None