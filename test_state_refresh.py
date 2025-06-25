#!/usr/bin/env python3
"""
Minimal test to verify server state changes after reinforce actions.
"""

import requests
import json
import time

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

def execute_reinforce(player_id, territory, num_armies):
    """Execute a reinforce action"""
    try:
        payload = {"player_id": player_id, "territory": territory, "num_armies": num_armies}
        print(f"🔧 API CALL: POST /reinforce with data: {payload}")
        
        response = requests.post("http://localhost:8000/reinforce", json=payload, timeout=10)
        response.raise_for_status()
        
        print(f"✅ API SUCCESS: reinforce")
        return True
    except Exception as e:
        print(f"❌ API ERROR: reinforce failed - {e}")
        return False

def main():
    print("=== Testing Server State Refresh ===")
    
    # Get initial state
    print("\n1. Getting initial game state...")
    initial_state = get_game_state()
    if not initial_state:
        print("Failed to get initial state")
        return
    
    print(f"Initial reinforcement_armies: {initial_state.get('reinforcement_armies', 'N/A')}")
    print(f"Initial possible_actions count: {len(initial_state.get('possible_actions', []))}")
    
    # Execute reinforce
    print("\n2. Executing reinforce action...")
    success = execute_reinforce(0, "Quebec", 3)
    if not success:
        print("Failed to execute reinforce")
        return
    
    # Wait a moment
    print("\n3. Waiting 0.5 seconds...")
    time.sleep(0.5)
    
    # Get state after reinforce
    print("\n4. Getting game state after reinforce...")
    after_state = get_game_state()
    if not after_state:
        print("Failed to get state after reinforce")
        return
    
    print(f"After reinforcement_armies: {after_state.get('reinforcement_armies', 'N/A')}")
    print(f"After possible_actions count: {len(after_state.get('possible_actions', []))}")
    
    # Compare states
    print("\n5. State Comparison:")
    initial_armies = initial_state.get('reinforcement_armies', 0)
    after_armies = after_state.get('reinforcement_armies', 0)
    
    print(f"  reinforcement_armies: {initial_armies} → {after_armies}")
    print(f"  Changed: {initial_armies != after_armies}")
    
    if initial_armies == after_armies:
        print("❌ PROBLEM: reinforcement_armies did not change!")
        print("This suggests the server is not updating state between requests.")
    else:
        print("✅ SUCCESS: reinforcement_armies changed as expected.")
    
    # Check if reinforce actions are still available
    possible_actions = after_state.get('possible_actions', [])
    reinforce_actions = [a for a in possible_actions if isinstance(a, dict) and "Reinforce" in a]
    
    print(f"\n6. Reinforce actions after: {len(reinforce_actions)}")
    if reinforce_actions:
        print("  Sample reinforce action:", reinforce_actions[0])
    
    if after_armies == 0 and len(reinforce_actions) > 0:
        print("❌ PROBLEM: No armies left but reinforce actions still available!")
    elif after_armies == 0 and len(reinforce_actions) == 0:
        print("✅ SUCCESS: No armies left and no reinforce actions available.")

if __name__ == "__main__":
    main() 