import os
from risk_api import RiskAPIClient
from google.adk.tools.tool_context import ToolContext
from callbacks import update_game_state

risk_api_client = RiskAPIClient(os.getenv("RISK_API_BASE_URL"))


def play_reinforcement_move(territory: str, num_armies: int, tool_context: ToolContext) -> dict:
    """Play a reinforcement move in the game of Risk."""
    print(f"--- Tool: reinforce {territory} with {num_armies} armies ---")
    # Convert armies to int to match the expected type
    risk_api_client.reinforce(
        player_id=tool_context.state["game_state"].get_current_player_id(),
        territory=territory,
        num_armies=int(num_armies)
    )
    return {"status": "success", "reinforced": f"reinforced {territory} with {num_armies} armies"}

def play_attack_move(from_territory: str, to_territory: str, num_armies: int, num_dice: int,tool_context: ToolContext) -> dict:
    """Play a attack move in the game of Risk."""
    print(f"--- Tool: attack from {from_territory} against {to_territory} with {num_armies} armies ---")
    # Convert armies to int to match the expected type
    old_game_state = tool_context.state["game_state"]
    new_game_state_response = risk_api_client.attack(
        player_id=tool_context.state["game_state"].get_current_player_id(),
        from_territory=from_territory,
        to_territory=to_territory,
        num_armies=num_armies,
        num_dice=num_dice
    )
    update_game_state(new_game_state_response)
    new_game_state = tool_context.state["game_state"]
    

    # Helper functions
    def find_owner(game_state_root, territory):
        for player in game_state_root.game_state.players:
            if territory in player.territories:
                return player.id
        return None

    def get_armies(game_state_root, player_id, territory):
        for player in game_state_root.game_state.players:
            if player.id == player_id:
                return player.armies.get(territory, 0)
        return 0

    attacker_id = tool_context.state["game_state"].get_current_player_id()
    old_owner = find_owner(old_game_state, to_territory)
    new_owner = find_owner(new_game_state, to_territory)
    conquered = (old_owner != attacker_id) and (new_owner == attacker_id)
    old_attacker_armies = get_armies(old_game_state, attacker_id, from_territory)
    new_attacker_armies = get_armies(new_game_state, attacker_id, from_territory)
    old_defender_armies = get_armies(old_game_state, old_owner, to_territory)
    if conquered:
        new_defender_armies = 0
    else:
        new_defender_armies = get_armies(new_game_state, new_owner, to_territory)
    attacker_lost = old_attacker_armies - new_attacker_armies
    defender_lost = old_defender_armies - new_defender_armies

    if conquered:
        attack_result = f"Conquered {to_territory}! Attacker lost {attacker_lost} armies, defender lost {defender_lost} armies."
    else:
        attack_result = f"Did not conquer {to_territory}. Attacker lost {attacker_lost} armies, defender lost {defender_lost} armies."

    return {
        "status": "success",
        "attack": f"attacked from {from_territory} against {to_territory} with {num_armies} armies",
        "attack_result": attack_result
    }


def advance_phase(tool_context: ToolContext) -> dict:
    """End a phase in the game of Risk."""
    print(f"--- Tool: advance_phase ---")
    risk_api_client.advance_phase()
    return {"status": "success", "description": "ended the current turn phase"}