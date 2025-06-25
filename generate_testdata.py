#!/usr/bin/env python3
"""
Test Data Generator - Play Until All Required Scenarios Found

This script plays Risk games until it encounters ALL required scenarios:
- Card trading (player has 3+ cards)
- Successful conquests (move_armies phase)
- Continent control
- End-game scenarios
- Player elimination

Only saves meaningful states for testing, not every turn.
"""

import json
import time
import requests
import os
import random
import sys
import argparse
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

class TestDataGenerator:
    def __init__(self, config_file: str = "game_config.json"):
        self.config_file = config_file
        self.current_config = config_file
        self.testdata_dir = Path("testdata")
        self.testdata_dir.mkdir(exist_ok=True)
        self.saved_files = set()  # Track saved files to avoid duplicates
        self.saved_turn_phases = set()
        self.found_scenarios = {
            "Reinforce": set(),
            "Attack": set(),
            "Fortify": set(),
            "MoveArmies": set(),
            "GameOver": set()
        }
        self.game_count = 0
        self.max_games = 10
        self.max_turns_per_game = 50
        self.api_base_url = "http://localhost:8000"
        
        # Track which scenarios we've found for each player
        self.found_scenarios = {
            "card_trading": set(),  # Track which players have card trading scenarios
            "conquest": set(),      # Set of player IDs who have conquest scenarios
            "move_armies": set(),   # Set of player IDs who have move armies scenarios
            "continent_control": set(),  # Track which players have continent control scenarios
            "player_elimination": False,  # Track if we have player elimination scenarios
            "end_game": False,  # Track if we have end-game scenarios
            "attack_phase": False,  # Track if we have attack phase scenarios
            "fortify_phase": False,  # Track if we have fortify phase scenarios
        }
    
    def prompt_start_mode(self):
        print("\nTest Data Generation Options:")
        print("1. Start a new game from game_config.json")
        print("2. Attach to existing game on server (default)")
        while True:
            choice = input("Enter your choice (1-2, or press Enter for default): ").strip()
            if not choice:
                choice = "2"
            if choice in ["1", "2"]:
                return choice
            print("Invalid choice. Please enter 1 or 2.")

    def start_new_game(self) -> bool:
        """Start a new game using game_config.json"""
        try:
            response = requests.post(f"{self.api_base_url}/new-game", 
                                   json={"config_file": self.config_file}, 
                                   timeout=10)
            response.raise_for_status()
            print("✓ Started new game using game_config.json")
            self.current_config = self.config_file
            return True
        except Exception as e:
            print(f"Error starting new game: {e}")
            return False

    def attach_existing_game(self) -> bool:
        # Just set config to 'existing' for filename prefixing
        self.current_config = "existing"
        print("✓ Attached to existing game on server.")
        return True

    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state from API"""
        try:
            response = requests.get(f"{self.api_base_url}/game-state", timeout=10)
            response.raise_for_status()
            data = response.json()
            # The API returns game_state nested under a game_state key
            return data.get("game_state", data)
        except Exception as e:
            print(f"Error getting game state: {e}")
            return {}
    
    def execute_action(self, action: str, data: Dict[str, Any]) -> bool:
        """Execute an action on the API"""
        try:
            # Fix parameter names for API compatibility
            if action == "reinforce":
                # API expects num_armies, not max_armies
                if "max_armies" in data:
                    data["num_armies"] = data.pop("max_armies")
            
            if action == "attack":
                # API expects from_territory and to_territory
                if "from" in data:
                    data["from_territory"] = data.pop("from")
                if "to" in data:
                    data["to_territory"] = data.pop("to")
                # API expects num_dice, not max_dice
                if "max_dice" in data:
                    data["num_dice"] = data.pop("max_dice")
                # API expects repeat field
                if "repeat" not in data:
                    data["repeat"] = False
            
            if action == "fortify":
                # API expects from_territory and to_territory
                if "from" in data:
                    data["from_territory"] = data.pop("from")
                if "to" in data:
                    data["to_territory"] = data.pop("to")
                # API expects num_armies, not max_armies
                if "max_armies" in data:
                    data["num_armies"] = data.pop("max_armies")
            
            if action == "move_armies":
                # API expects from_territory and to_territory
                if "from" in data:
                    data["from_territory"] = data.pop("from")
                if "to" in data:
                    data["to_territory"] = data.pop("to")
                # API expects num_armies, not max_armies
                if "max_armies" in data:
                    data["num_armies"] = data.pop("max_armies")
            
            print(f"🔧 API CALL: POST /{action} with data: {data}")
            response = requests.post(f"{self.api_base_url}/{action}", 
                                    json=data, 
                                    timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ API ERROR: {action} failed - {e}")
            return False
    
    def save_game_state(self, description: str):
        """Save a meaningful game state for testing"""
        # Generate descriptive filename based on scenario
        filename = self.generate_scenario_filename(description)
        
        if filename in self.saved_files:
            return  # Already saved this scenario
        
        state = self.get_game_state()
        if not state:
            return
        
        # Add config prefix to filename
        config_prefix = "game_config"  # Default prefix
        if hasattr(self, 'current_config') and self.current_config:
            config_prefix = self.current_config.replace('.json', '').replace('/', '_').replace('\\', '_')
        
        # Add config prefix to filename
        prefixed_filename = f"{config_prefix}_{filename}"
        
        if prefixed_filename in self.saved_files:
            return  # Already saved this scenario
        
        # Save the game state
        filepath = self.testdata_dir / prefixed_filename
        with open(filepath, 'w') as f:
            json.dump({
                "description": description,
                "game_state": state
            }, f, indent=2)
        
        self.saved_files.add(prefixed_filename)
        print(f"✓ Saved: {prefixed_filename} - {description}")
    
    def generate_scenario_filename(self, description: str) -> str:
        """Generate descriptive filename based on scenario description"""
        import re
        
        # Continent control scenarios
        if "controls entire" in description:
            match = re.search(r"Player (\d+) controls entire (.+)", description)
            if match:
                player_id = match.group(1)
                continent = match.group(2).replace(" ", "_")
                return f"continent_control_{continent}_Player{player_id}.json"
        
        # Player elimination scenarios
        if "players eliminated" in description:
            match = re.search(r"(\d+) players eliminated", description)
            if match:
                count = match.group(1)
                return f"player_elimination_{count}players.json"
        
        # Conquest scenarios
        if "conquered a territory" in description:
            match = re.search(r"Player (\d+) conquered", description)
            if match:
                player_id = match.group(1)
                return f"conquest_Player{player_id}_territory.json"
        
        # End-game scenarios
        if "End-game:" in description:
            match = re.search(r"End-game: (\d+) players remaining", description)
            if match:
                count = match.group(1)
                return f"end_game_{count}players.json"
        
        # Game over scenarios
        if "Game Over" in description:
            return f"game_over_final_state.json"
        
        # Card trading scenarios
        if "card trading" in description.lower():
            match = re.search(r"Player (\d+)", description)
            if match:
                player_id = match.group(1)
                return f"card_trading_Player{player_id}.json"
        
        # Move armies scenarios
        if "move_armies" in description.lower():
            match = re.search(r"Player (\d+)", description)
            if match:
                player_id = match.group(1)
                return f"move_armies_Player{player_id}.json"
        
        # Default: use timestamp for unknown scenarios
        import time
        timestamp = int(time.time())
        return f"scenario_{timestamp}.json"
    
    def check_for_card_trading(self, player_id: int) -> bool:
        """Check if player has cards to trade"""
        state = self.get_game_state()
        if not state:
            return False
        
        for player in state.get("players", []):
            if player["id"] == player_id:
                cards = player.get("cards", [])
                if len(cards) >= 3:
                    self.save_game_state(f"Player {player_id} has {len(cards)} cards for trading")
                    return True
        return False
    
    def check_for_conquest(self, player_id: int) -> bool:
        """Check if player just conquered a territory"""
        state = self.get_game_state()
        if not state:
            return False
        
        if state.get("conquered_territory", False):
            self.save_game_state(f"Player {player_id} conquered a territory")
            return True
        return False
    
    def check_for_move_armies(self, player_id: int) -> bool:
        """Check if player is in move armies phase after conquest"""
        state = self.get_game_state()
        if not state:
            return False
        
        possible_actions = state.get("possible_actions", [])
        for action in possible_actions:
            if isinstance(action, dict) and "MoveArmies" in action:
                self.save_game_state(f"Player {player_id} in move_armies phase")
                return True
        return False
    
    def check_for_continent_control(self) -> bool:
        """Check if any player controls an entire continent"""
        state = self.get_game_state()
        if not state:
            return False
        
        players = state.get("players", [])
        board = state.get("board", {})
        continents = board.get("continents", {})
        
        for player in players:
            player_id = player["id"]
            territories = player.get("territories", [])
            
            for continent_name, continent_data in continents.items():
                continent_territories = continent_data.get("territories", [])
                owned_in_continent = sum(1 for t in territories if t in continent_territories)
                total_in_continent = len(continent_territories)
                
                if owned_in_continent == total_in_continent and total_in_continent > 0:
                    self.save_game_state(
                        f"Player {player_id} controls entire {continent_name}"
                    )
                    return True
        return False
    
    def check_for_player_elimination(self) -> bool:
        """Check if any player has been eliminated"""
        state = self.get_game_state()
        if not state:
            return False
        
        active_players = [p for p in state.get("players", []) if p.get("territories", [])]
        if len(active_players) < len(state.get("players", [])):
            eliminated = len(state.get("players", [])) - len(active_players)
            self.save_game_state(f"{eliminated} players eliminated")
            return True
        return False
    
    def check_for_end_game(self) -> bool:
        """Check if game is in end-game state (2 or fewer players)"""
        state = self.get_game_state()
        if not state:
            return False
        
        active_players = [p for p in state.get("players", []) if p.get("territories", [])]
        if len(active_players) <= 2:
            self.save_game_state(f"End-game: {len(active_players)} players remaining")
            return True
        return False
    
    def get_possible_actions(self) -> List[Dict[str, Any]]:
        """Get current possible actions from game state"""
        state = self.get_game_state()
        return state.get("possible_actions", [])
    
    def can_advance_phase(self) -> bool:
        """Check if we can advance to the next phase"""
        possible_actions = self.get_possible_actions()
        # Look for EndPhase in possible actions
        for action in possible_actions:
            if action == "EndPhase":
                return True
        return False
    
    def get_current_player_id(self) -> int:
        """Get current player ID from game state"""
        state = self.get_game_state()
        if not state:
            return 0
        
        current_player = state.get("current_player", 0)
        players = state.get("players", [])
        
        # If current_player is a string (name), map to id
        if isinstance(current_player, str):
            # Handle "Player 1" format
            if current_player.startswith("Player "):
                try:
                    current_player = int(current_player.split(" ")[1]) - 1  # Convert "Player 1" to 0
                except (IndexError, ValueError):
                    current_player = 0
            else:
                # Handle player names like "Bob"
                for p in players:
                    if p.get("name") == current_player:
                        current_player = p.get("id")
                        break
        
        return current_player
    
    def get_active_players(self) -> List[int]:
        """Get list of active player IDs (those with territories)"""
        state = self.get_game_state()
        if not state:
            return []
        
        players = state.get("players", [])
        active_players = []
        
        for player in players:
            if len(player.get("territories", [])) > 0:
                active_players.append(player["id"])
        
        return sorted(active_players)  # Return sorted list
    
    def play_game_and_save_states(self):
        """Play a complete game and save meaningful states"""
        print("\n[INFO] Playing game and saving all states after every action...")
        
        while True:
            # Always get fresh game state
            state = self.get_game_state()
            if not state:
                print("[ERROR] Could not fetch game state. Exiting.")
                break
            
            # Check if game is over
            if state.get("game_over", False):
                print("[INFO] Game over detected.")
                break
                
            # Always get current player from fresh game state
            current_player = self.get_current_player_id()
            active_players = self.get_active_players()
            defeated_players = state.get("defeated_players", [])
            
            # Check if game ended (only one player remaining)
            active_players_count = len(active_players)
            if active_players_count <= 1:
                print(f"Game ended - {len(defeated_players)} players eliminated, only {active_players_count} remains - GAME OVER")
                # Save final game state for GameOver phase
                self.save_game_state("Game Over - Final State")
                self.saved_turn_phases.add("GameOver")
                break
            
            # Check for meaningful scenarios and save test data
            current_player = self.get_current_player_id()
            
            # Check for continent control
            if self.check_for_continent_control():
                self.saved_turn_phases.add(state.get("turn_phase", "Unknown"))
            
            # Check for player elimination
            if self.check_for_player_elimination():
                self.saved_turn_phases.add(state.get("turn_phase", "Unknown"))
            
            # Check for end-game state
            if self.check_for_end_game():
                self.saved_turn_phases.add(state.get("turn_phase", "Unknown"))
            
            # Check for card trading opportunities
            if self.check_for_card_trading(current_player):
                self.saved_turn_phases.add(state.get("turn_phase", "Unknown"))
            
            # Check for conquest (territory conquered)
            if self.check_for_conquest(current_player):
                self.saved_turn_phases.add(state.get("turn_phase", "Unknown"))
            
            # Check for move armies phase after conquest
            if self.check_for_move_armies(current_player):
                self.saved_turn_phases.add(state.get("turn_phase", "Unknown"))
            
            # Get possible actions from fresh state
            possible_actions = state.get("possible_actions", [])
            if not possible_actions:
                print(f"No possible actions for player {current_player}, ending turn.")
                break
            
            # Choose action based on player strategy
            chosen_action = self.choose_action(current_player, possible_actions, state)
            
            if chosen_action:
                # Execute the chosen action
                if isinstance(chosen_action, str):
                    # EndPhase or similar
                    if chosen_action == "EndPhase":
                        self.execute_action("advance_phase", {"player_id": current_player})
                    else:
                        print(f"[INFO] Unhandled string action: {chosen_action}")
                        break
                elif isinstance(chosen_action, dict):
                    action_type = list(chosen_action.keys())[0]
                    params = chosen_action[action_type]
                    params = dict(params)  # copy
                    params["player_id"] = current_player
                    
                    # Convert action type to API endpoint name using explicit mapping
                    action_map = {
                        "reinforce": "reinforce",
                        "attack": "attack",
                        "fortify": "fortify",
                        "movearmies": "move_armies",
                        "tradecards": "trade_cards",
                        "endphase": "advance_phase"
                    }
                    api_action = action_type.lower()
                    api_action = action_map.get(api_action, api_action)
                    self.execute_action(api_action, params)
                else:
                    print(f"[INFO] Unknown action format: {chosen_action}")
                    break
            else:
                print(f"No valid action found for player {current_player}")
                break
            
            time.sleep(0.1)  # Small delay to avoid hammering the server
        
        self.game_count += 1
        print(f"✅ Game {self.game_count} completed")
    
    def choose_action(self, player_id: int, possible_actions: list, state: dict):
        """Choose action based on player strategy and available actions"""
        import random
        
        # Player 0 (lowest index) is aggressive - prioritize attacks and card trading
        if player_id == 0:
            # First priority: Trade cards if possible
            trade_actions = [a for a in possible_actions if "TradeCards" in a]
            if trade_actions:
                return random.choice(trade_actions)
            
            # Second priority: Attack if possible
            attack_actions = [a for a in possible_actions if "Attack" in a]
            if attack_actions:
                return random.choice(attack_actions)
            
            # Third priority: Move armies after conquest
            move_actions = [a for a in possible_actions if "MoveArmies" in a]
            if move_actions:
                return random.choice(move_actions)
        
        # For all players: randomize from available actions
        return random.choice(possible_actions)

    def print_summary(self):
        """Print a summary of collected test data"""
        print("\n" + "="*60)
        print("📊 TEST DATA GENERATION SUMMARY")
        print("="*60)
        
        print(f"\n🎮 Games Played: {self.game_count}")
        print(f"📁 Total Files Saved: {len(self.saved_files)}")
        print(f"🔄 Turn Phases Encountered: {len(self.saved_turn_phases)}")
        
        if self.saved_turn_phases:
            print(f"   Phases: {', '.join(sorted(self.saved_turn_phases))}")
        
        print(f"\n📋 Saved Files by Scenario Type:")
        
        # Group files by scenario type
        scenario_groups = {}
        for filename in sorted(self.saved_files):
            # Extract scenario type from filename
            if filename.startswith("game_config_"):
                scenario_part = filename.replace("game_config_", "")
            else:
                scenario_part = filename
            
            # Determine scenario type
            if "continent_control" in scenario_part:
                scenario_type = "Continent Control"
            elif "player_elimination" in scenario_part:
                scenario_type = "Player Elimination"
            elif "conquest" in scenario_part:
                scenario_type = "Territory Conquest"
            elif "end_game" in scenario_part:
                scenario_type = "End Game"
            elif "game_over" in scenario_part:
                scenario_type = "Game Over"
            elif "card_trading" in scenario_part:
                scenario_type = "Card Trading"
            elif "move_armies" in scenario_part:
                scenario_type = "Move Armies"
            else:
                scenario_type = "Other Scenarios"
            
            if scenario_type not in scenario_groups:
                scenario_groups[scenario_type] = []
            scenario_groups[scenario_type].append(filename)
        
        # Print organized summary
        for scenario_type, files in scenario_groups.items():
            print(f"\n  {scenario_type} ({len(files)} files):")
            for filename in files:
                print(f"    • {filename}")
        
        print(f"\n📂 Test data saved in: {self.testdata_dir.absolute()}")
        print("="*60)

def main():
    generator = TestDataGenerator()
    mode = generator.prompt_start_mode()
    if mode == "1":
        if not generator.start_new_game():
            print("Failed to start new game. Exiting.")
            return
    else:
        if not generator.attach_existing_game():
            print("Failed to attach to existing game. Exiting.")
            return
    generator.play_game_and_save_states()
    generator.print_summary()

if __name__ == "__main__":
    main() 