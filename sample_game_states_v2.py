#!/usr/bin/env python3
"""
Improved Game State Sampling Script

This script samples game states by actually playing through games
and capturing the state at various points, ensuring proper game progression.
"""

import json
import time
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GameState:
    """Represents a captured game state"""
    turn: int
    phase: str
    player_id: int
    state: Dict[str, Any]
    timestamp: float
    description: str

class GameStateSampler:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.samples: List[GameState] = []
        
    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state from API"""
        try:
            response = requests.get(f"{self.api_url}/game-state", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("game_state", {})
        except Exception as e:
            print(f"Error getting game state: {e}")
            return {}
    
    def execute_action(self, action: str, data: Dict[str, Any]) -> bool:
        """Execute a game action"""
        try:
            response = requests.post(f"{self.api_url}/{action}", json=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error executing {action}: {e}")
            return False
    
    def sample_state(self, turn: int, phase: str, player_id: int, description: str):
        """Capture a game state sample"""
        state = self.get_game_state()
        if state:
            sample = GameState(
                turn=turn,
                phase=phase,
                player_id=player_id,
                state=state,
                timestamp=time.time(),
                description=description
            )
            self.samples.append(sample)
            print(f"✓ Sampled: Turn {turn}, Phase {phase}, Player {player_id} - {description}")
    
    def start_new_game(self, num_players: int = 3) -> bool:
        """Start a new game"""
        try:
            response = requests.post(f"{self.api_url}/new-game", 
                                   json={"num_players": num_players}, 
                                   timeout=10)
            response.raise_for_status()
            print(f"✓ Started new game with {num_players} players")
            return True
        except Exception as e:
            print(f"Error starting new game: {e}")
            return False
    
    def play_reinforce_phase(self, player_id: int, turn: int) -> bool:
        """Play through reinforce phase"""
        print(f"  Playing reinforce phase for player {player_id}")
        
        # Sample initial reinforce state
        self.sample_state(turn, "reinforce", player_id, "Start of reinforce phase")
        
        # Get current state
        state = self.get_game_state()
        if not state:
            return False
            
        # Check if player has cards to trade
        players = state.get("players", [])
        if player_id >= len(players):
            print(f"Player {player_id} not found in game state")
            return False
            
        player = players[player_id]
        cards = player.get("cards", [])
        
        if len(cards) >= 3:
            # Try to trade cards
            self.sample_state(turn, "reinforce", player_id, f"Before trading {len(cards)} cards")
            
            # Simple card trading strategy: trade first 3 cards if possible
            if self.execute_action("trade_cards", {
                "player_id": player_id,
                "card_indices": [0, 1, 2]
            }):
                self.sample_state(turn, "reinforce", player_id, "After trading cards")
        
        # Get territories owned by player
        territories = player.get("territories", [])
        
        # Simple reinforcement: put armies on first territory
        if territories:
            territory = territories[0]
            armies_to_place = 3  # Simple strategy
            
            if self.execute_action("reinforce", {
                "player_id": player_id,
                "territory": territory,
                "num_armies": armies_to_place
            }):
                self.sample_state(turn, "reinforce", player_id, f"After reinforcing {territory}")
        
        # Advance to attack phase
        if self.execute_action("advance_phase", {"player_id": player_id}):
            self.sample_state(turn, "attack", player_id, "Start of attack phase")
            return True
        
        return False
    
    def play_attack_phase(self, player_id: int, turn: int) -> bool:
        """Play through attack phase"""
        print(f"  Playing attack phase for player {player_id}")
        
        # Get current state
        state = self.get_game_state()
        if not state:
            return False
        
        # Find attack opportunities
        players = state.get("players", [])
        if player_id >= len(players):
            return False
            
        player = players[player_id]
        player_territories = player.get("territories", [])
        player_armies = player.get("armies", {})
        
        attack_made = False
        for territory_name in player_territories:
            armies = player_armies.get(territory_name, 0)
            if armies > 1:
                # Find adjacent enemy territories
                board = state.get("board", {})
                territory_data = board.get("territories", {}).get(territory_name, {})
                adjacent = territory_data.get("adjacent_territories", [])
                
                for adj_name in adjacent:
                    # Check if adjacent territory is enemy-controlled
                    is_enemy = True
                    for other_player in players:
                        if other_player["id"] != player_id and adj_name in other_player.get("territories", []):
                            # Found attack opportunity
                            if self.execute_action("attack", {
                                "player_id": player_id,
                                "from_territory": territory_name,
                                "to_territory": adj_name,
                                "num_dice": min(3, armies - 1),
                                "repeat": False
                            }):
                                self.sample_state(turn, "attack", player_id, 
                                                f"After attacking {adj_name} from {territory_name}")
                                attack_made = True
                                break
                    if attack_made:
                        break
            if attack_made:
                break
        
        # Advance to fortify phase
        if self.execute_action("advance_phase", {"player_id": player_id}):
            self.sample_state(turn, "fortify", player_id, "Start of fortify phase")
            return True
        
        return False
    
    def play_fortify_phase(self, player_id: int, turn: int) -> bool:
        """Play through fortify phase"""
        print(f"  Playing fortify phase for player {player_id}")
        
        # Get current state
        state = self.get_game_state()
        if not state:
            return False
        
        # Find fortify opportunities
        players = state.get("players", [])
        if player_id >= len(players):
            return False
            
        player = players[player_id]
        player_territories = player.get("territories", [])
        player_armies = player.get("armies", {})
        
        if len(player_territories) >= 2:
            # Simple fortify: move armies from first to second territory
            from_territory = player_territories[0]
            to_territory = player_territories[1]
            
            from_armies = player_armies.get(from_territory, 0)
            if from_armies > 1:
                if self.execute_action("fortify", {
                    "player_id": player_id,
                    "from_territory": from_territory,
                    "to_territory": to_territory,
                    "num_armies": 1
                }):
                    self.sample_state(turn, "fortify", player_id, 
                                    f"After fortifying {to_territory} from {from_territory}")
        
        # Advance to next turn
        if self.execute_action("advance_phase", {"player_id": player_id}):
            return True
        
        return False
    
    def play_full_turn(self, player_id: int, turn: int) -> bool:
        """Play through a complete turn for a player"""
        print(f"Playing turn {turn} for player {player_id}")
        
        # Reinforce phase
        if not self.play_reinforce_phase(player_id, turn):
            return False
        
        # Attack phase
        if not self.play_attack_phase(player_id, turn):
            return False
        
        # Fortify phase
        if not self.play_fortify_phase(player_id, turn):
            return False
        
        print(f"✓ Completed turn {turn} for player {player_id}")
        return True
    
    def sample_game(self, num_players: int = 3, max_turns: int = 5) -> bool:
        """Sample a complete game"""
        print(f"Starting game sampling with {num_players} players, max {max_turns} turns")
        
        # Start new game
        if not self.start_new_game(num_players):
            return False
        
        # Sample initial state
        self.sample_state(0, "setup", 0, "Initial game setup")
        
        # Play through turns
        for turn in range(1, max_turns + 1):
            for player_id in range(num_players):
                if not self.play_full_turn(player_id, turn):
                    print(f"Failed to complete turn {turn} for player {player_id}")
                    return False
                
                # Check if game is over
                state = self.get_game_state()
                if state.get("game_over", False):
                    print("Game ended, sampling final state")
                    self.sample_state(turn, "end", player_id, "Game over")
                    return True
        
        print(f"Completed {max_turns} turns")
        return True
    
    def save_samples(self, filename: str = "game_state_samples.json"):
        """Save all samples to a JSON file"""
        output = []
        for sample in self.samples:
            output.append({
                "turn": sample.turn,
                "phase": sample.phase,
                "player_id": sample.player_id,
                "state": sample.state,
                "timestamp": sample.timestamp,
                "description": sample.description
            })
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✓ Saved {len(self.samples)} samples to {filename}")
    
    def print_summary(self):
        """Print a summary of collected samples"""
        print(f"\n=== Sample Summary ===")
        print(f"Total samples: {len(self.samples)}")
        
        # Group by phase
        phases = {}
        for sample in self.samples:
            phase = sample.phase
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(sample)
        
        for phase, samples in phases.items():
            print(f"{phase}: {len(samples)} samples")
            for sample in samples[:3]:  # Show first 3
                print(f"  - Turn {sample.turn}, Player {sample.player_id}: {sample.description}")
            if len(samples) > 3:
                print(f"  ... and {len(samples) - 3} more")

def main():
    """Main function to run the sampler"""
    sampler = GameStateSampler()
    
    # Sample a game
    success = sampler.sample_game(num_players=3, max_turns=3)
    
    if success:
        sampler.print_summary()
        sampler.save_samples()
    else:
        print("Failed to complete game sampling")

if __name__ == "__main__":
    main() 