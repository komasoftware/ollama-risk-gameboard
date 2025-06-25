#!/usr/bin/env python3
"""
Debug script to test the exact loop logic from generate_testdata.py
"""

import requests
import time
import random

def get_game_state():
    """Get current game state"""
    try:
        response = requests.get("http://localhost:8000/game-state", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("game_state", {})
    except Exception as e:
        print(f"Error getting game state: {e}")
        return None

def execute_action(action, data):
    """Execute a game action"""
    try:
        print(f"🔧 API CALL: POST /{action} with data: {data}")
        response = requests.post(f"http://localhost:8000/{action}", json=data, timeout=10)
        response.raise_for_status()
        print(f"✅ API SUCCESS: {action}")
        
        # Always get updated game state after API call
        time.sleep(0.2)  # Small delay to ensure API has processed
        return True
    except Exception as e:
        print(f"❌ API ERROR: {action} failed - {e}")
        return False

def execute_random_action(action, player_id):
    """Helper to execute a random action from possible_actions."""
    state = get_game_state()
    reinforcement_armies = state.get("reinforcement_armies", 0)
    
    if action == "EndPhase":
        execute_action("advance_phase", {"player_id": player_id})
    elif isinstance(action, dict):
        if "Reinforce" in action:
            reinforce_action = action["Reinforce"]
            max_armies = reinforce_action["max_armies"]
            if reinforcement_armies > 0 and max_armies > 0:
                execute_action("reinforce", {
                    "player_id": player_id,
                    "territory": reinforce_action["territory"],
                    "num_armies": max_armies
                })
            else:
                print(f"[DEBUG] Skipping reinforce: reinforcement_armies={reinforcement_armies}, max_armies={max_armies}")

def main():
    print("=== Debugging Script Loop ===")
    
    player_id = 0
    loop_count = 0
    max_loops = 10
    
    while loop_count < max_loops:
        loop_count += 1
        print(f"\n--- Loop {loop_count} ---")
        
        # Get fresh state (like in play_turn_for_player)
        state = get_game_state()
        if not state:
            print("Failed to get game state")
            break
            
        if state.get("game_over", False):
            print("Game over")
            break
            
        # Check if player is eliminated
        players = state.get("players", [])
        player = next((p for p in players if p["id"] == player_id), None)
        if not player or len(player.get("territories", [])) == 0:
            print("Player eliminated")
            break

        # Debug: print possible actions and reinforcement_armies
        possible_actions = state.get("possible_actions", [])
        reinforcement_armies = state.get("reinforcement_armies", 0)
        print(f"[DEBUG] Player {player_id} possible_actions: {len(possible_actions)} actions")
        print(f"[DEBUG] Player {player_id} reinforcement_armies: {reinforcement_armies}")

        if not possible_actions:
            print(f"No possible actions for player {player_id}, ending turn.")
            break

        # If only EndPhase is available, just do it
        if len(possible_actions) == 1 and possible_actions[0] == "EndPhase":
            print(f"⏭️ Only EndPhase available for player {player_id}, advancing phase.")
            execute_action("advance_phase", {"player_id": player_id})
            continue

        # Pick a random action (like the attacking agent does)
        action = random.choice(possible_actions)
        print(f"🎲 Random action for player {player_id}: {action}")
        
        # Execute the action
        execute_random_action(action, player_id)
        
        # Continue to next loop iteration (this is where the script should get fresh state)
        print("Continuing to next loop iteration...")
        continue

if __name__ == "__main__":
    main() 