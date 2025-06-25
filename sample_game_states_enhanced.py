#!/usr/bin/env python3
"""
Enhanced Game State Sampling Script

This script samples game states with a focus on aggressive gameplay
to capture card trading, conquest, and other advanced scenarios.
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

class EnhancedGameStateSampler:
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
    
    def play_aggressive_reinforce_phase(self, player_id: int, turn: int) -> bool:
        """Play through reinforce phase with focus on getting cards"""
        print(f"  Playing aggressive reinforce phase for player {player_id}")
        
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
            
            # Try different card trading strategies
            if len(cards) >= 3:
                # Trade first 3 cards
                if self.execute_action("trade_cards", {
                    "player_id": player_id,
                    "card_indices": [0, 1, 2]
                }):
                    self.sample_state(turn, "reinforce", player_id, "After trading first 3 cards")
                    
                    # Check if we can trade more cards
                    new_state = self.get_game_state()
                    if new_state:
                        new_players = new_state.get("players", [])
                        if player_id < len(new_players):
                            new_cards = new_players[player_id].get("cards", [])
                            if len(new_cards) >= 3:
                                self.sample_state(turn, "reinforce", player_id, f"Can trade more cards ({len(new_cards)} available)")
        
        # Get territories owned by player
        territories = player.get("territories", [])
        
        # Aggressive reinforcement: put armies on border territories
        if territories:
            # Find territories adjacent to enemies for aggressive positioning
            board = state.get("board", {})
            border_territories = []
            
            for territory in territories:
                territory_data = board.get("territories", {}).get(territory, {})
                adjacent = territory_data.get("adjacent_territories", [])
                
                # Check if any adjacent territory is enemy-controlled
                for adj_name in adjacent:
                    is_enemy = False
                    for other_player in players:
                        if other_player["id"] != player_id and adj_name in other_player.get("territories", []):
                            is_enemy = True
                            break
                    if is_enemy:
                        border_territories.append(territory)
                        break
            
            # Reinforce border territories first
            target_territories = border_territories + [t for t in territories if t not in border_territories]
            
            for territory in target_territories:
                reinforcement_armies = state.get("reinforcement_armies", 0)
                if reinforcement_armies > 0:
                    armies_to_place = min(3, reinforcement_armies)
                    
                    if self.execute_action("reinforce", {
                        "player_id": player_id,
                        "territory": territory,
                        "num_armies": armies_to_place
                    }):
                        self.sample_state(turn, "reinforce", player_id, f"After reinforcing {territory} (border: {territory in border_territories})")
                        break
        
        # Advance to attack phase
        if self.execute_action("advance_phase", {"player_id": player_id}):
            self.sample_state(turn, "attack", player_id, "Start of attack phase")
            return True
        
        return False
    
    def play_aggressive_attack_phase(self, player_id: int, turn: int) -> bool:
        """Play through attack phase with focus on conquests"""
        print(f"  Playing aggressive attack phase for player {player_id}")
        
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
        conquest_count = 0
        
        for territory_name in player_territories:
            armies = player_armies.get(territory_name, 0)
            if armies > 1:
                # Find adjacent enemy territories
                board = state.get("board", {})
                territory_data = board.get("territories", {}).get(territory_name, {})
                adjacent = territory_data.get("adjacent_territories", [])
                
                for adj_name in adjacent:
                    # Check if adjacent territory is enemy-controlled
                    is_enemy = False
                    for other_player in players:
                        if other_player["id"] != player_id and adj_name in other_player.get("territories", []):
                            is_enemy = True
                            break
                    
                    if is_enemy:
                        # Found attack opportunity
                        dice_to_use = min(3, armies - 1)
                        
                        if self.execute_action("attack", {
                            "player_id": player_id,
                            "from_territory": territory_name,
                            "to_territory": adj_name,
                            "num_dice": dice_to_use,
                            "repeat": False
                        }):
                            self.sample_state(turn, "attack", player_id, 
                                            f"After attacking {adj_name} from {territory_name}")
                            attack_made = True
                            
                            # Check if territory was conquered
                            new_state = self.get_game_state()
                            if new_state and new_state.get("conquered_territory", False):
                                conquest_count += 1
                                self.sample_state(turn, "conquest", player_id, 
                                                f"Territory conquered! ({conquest_count} conquests)")
                                
                                # Handle move armies phase
                                self.handle_move_armies_phase(player_id, turn)
                                
                                # Check for card trading opportunities
                                self.check_card_trading_opportunities(player_id, turn)
                            
                            break
                if attack_made:
                    break
        
        # Advance to fortify phase
        if self.execute_action("advance_phase", {"player_id": player_id}):
            self.sample_state(turn, "fortify", player_id, "Start of fortify phase")
            return True
        
        return False
    
    def handle_move_armies_phase(self, player_id: int, turn: int):
        """Handle move armies phase after conquest"""
        print(f"    Handling move armies phase for player {player_id}")
        
        state = self.get_game_state()
        if not state:
            return
        
        # Get possible move armies actions
        possible_actions = state.get("possible_actions", [])
        move_actions = [a for a in possible_actions if "MoveArmies" in a]
        
        if move_actions:
            move_action = move_actions[0]["MoveArmies"]
            from_territory = move_action["from"]
            to_territory = move_action["to"]
            max_armies = move_action["max_armies"]
            
            self.sample_state(turn, "move_armies", player_id, "Start of move armies phase")
            
            if self.execute_action("move_armies", {
                "player_id": player_id,
                "from_territory": from_territory,
                "to_territory": to_territory,
                "num_armies": max_armies
            }):
                self.sample_state(turn, "move_armies", player_id, 
                                f"After moving {max_armies} armies to {to_territory}")
    
    def check_card_trading_opportunities(self, player_id: int, turn: int):
        """Check and perform card trading if available"""
        print(f"    Checking card trading opportunities for player {player_id}")
        
        state = self.get_game_state()
        if not state:
            return
        
        players = state.get("players", [])
        if player_id >= len(players):
            return
        
        player = players[player_id]
        cards = player.get("cards", [])
        
        if len(cards) >= 3:
            self.sample_state(turn, "card_trading", player_id, f"Card trading available ({len(cards)} cards)")
            
            # Try to trade cards
            if self.execute_action("trade_cards", {
                "player_id": player_id,
                "card_indices": [0, 1, 2]
            }):
                self.sample_state(turn, "card_trading", player_id, "After trading cards")
    
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
            # Find territories with multiple armies for fortification
            source_territories = [t for t in player_territories if player_armies.get(t, 0) > 1]
            
            if source_territories:
                from_territory = source_territories[0]
                # Find a different territory to fortify
                target_territories = [t for t in player_territories if t != from_territory]
                
                if target_territories:
                    to_territory = target_territories[0]
                    armies_to_move = 1
                    
                    if self.execute_action("fortify", {
                        "player_id": player_id,
                        "from_territory": from_territory,
                        "to_territory": to_territory,
                        "num_armies": armies_to_move
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
        if not self.play_aggressive_reinforce_phase(player_id, turn):
            return False
        
        # Attack phase
        if not self.play_aggressive_attack_phase(player_id, turn):
            return False
        
        # Fortify phase
        if not self.play_fortify_phase(player_id, turn):
            return False
        
        print(f"✓ Completed turn {turn} for player {player_id}")
        return True
    
    def sample_enhanced_game(self, num_players: int = 3, max_turns: int = 5) -> bool:
        """Sample a complete game with enhanced scenarios"""
        print(f"Starting enhanced game sampling with {num_players} players, max {max_turns} turns")
        
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
    
    def save_samples(self, filename: str = "enhanced_game_state_samples.json"):
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
        print(f"\n=== Enhanced Sample Summary ===")
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
    """Main function to run the enhanced sampler"""
    sampler = EnhancedGameStateSampler()
    
    # Sample a game with enhanced scenarios
    success = sampler.sample_enhanced_game(num_players=3, max_turns=3)
    
    if success:
        sampler.print_summary()
        sampler.save_samples()
    else:
        print("Failed to complete enhanced game sampling")

if __name__ == "__main__":
    main() 