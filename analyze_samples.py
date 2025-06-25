#!/usr/bin/env python3
"""
Game State Sample Analysis Script

This script analyzes the collected game state samples to extract
useful patterns and insights for AI agent development.
"""

import json
from typing import Dict, List, Any, Counter
from collections import defaultdict
import statistics

class GameStateAnalyzer:
    def __init__(self, samples_file: str = "game_state_samples.json"):
        self.samples_file = samples_file
        self.samples = []
        self.load_samples()
    
    def load_samples(self):
        """Load samples from JSON file"""
        try:
            with open(self.samples_file, 'r') as f:
                self.samples = json.load(f)
            print(f"✓ Loaded {len(self.samples)} samples from {self.samples_file}")
        except Exception as e:
            print(f"Error loading samples: {e}")
            self.samples = []
    
    def analyze_phases(self):
        """Analyze game phases and their characteristics"""
        print("\n=== Phase Analysis ===")
        
        phase_stats = defaultdict(list)
        for sample in self.samples:
            phase = sample["phase"]
            turn = sample["turn"]
            player_id = sample["player_id"]
            state = sample["state"]
            
            phase_stats[phase].append({
                "turn": turn,
                "player_id": player_id,
                "reinforcement_armies": state.get("reinforcement_armies", 0),
                "possible_actions": len(state.get("possible_actions", [])),
                "description": sample["description"]
            })
        
        for phase, stats in phase_stats.items():
            print(f"\n{phase.upper()} Phase:")
            print(f"  Total samples: {len(stats)}")
            print(f"  Average reinforcement armies: {statistics.mean([s['reinforcement_armies'] for s in stats]):.1f}")
            print(f"  Average possible actions: {statistics.mean([s['possible_actions'] for s in stats]):.1f}")
            
            # Show sample descriptions
            descriptions = [s["description"] for s in stats[:5]]
            for desc in descriptions:
                print(f"    - {desc}")
            if len(stats) > 5:
                print(f"    ... and {len(stats) - 5} more")
    
    def analyze_actions(self):
        """Analyze possible actions across different phases"""
        print("\n=== Action Analysis ===")
        
        action_counts = Counter()
        phase_actions = defaultdict(Counter)
        
        for sample in self.samples:
            phase = sample["phase"]
            actions = sample["state"].get("possible_actions", [])
            
            for action in actions:
                action_type = list(action.keys())[0]
                action_counts[action_type] += 1
                phase_actions[phase][action_type] += 1
        
        print("Overall action distribution:")
        for action, count in action_counts.most_common():
            print(f"  {action}: {count}")
        
        print("\nActions by phase:")
        for phase, actions in phase_actions.items():
            print(f"\n{phase.upper()}:")
            for action, count in actions.most_common():
                print(f"  {action}: {count}")
    
    def analyze_player_progression(self):
        """Analyze how players progress through the game"""
        print("\n=== Player Progression Analysis ===")
        
        player_stats = defaultdict(lambda: {
            "turns": set(),
            "phases": set(),
            "territories": set(),
            "total_armies": []
        })
        
        for sample in self.samples:
            player_id = sample["player_id"]
            turn = sample["turn"]
            phase = sample["phase"]
            state = sample["state"]
            
            player_stats[player_id]["turns"].add(turn)
            player_stats[player_id]["phases"].add(phase)
            
            # Get player data
            players = state.get("players", [])
            if player_id < len(players):
                player = players[player_id]
                territories = player.get("territories", [])
                total_armies = player.get("total_armies", 0)
                
                player_stats[player_id]["territories"].update(territories)
                player_stats[player_id]["total_armies"].append(total_armies)
        
        for player_id, stats in player_stats.items():
            print(f"\nPlayer {player_id}:")
            print(f"  Turns played: {len(stats['turns'])}")
            print(f"  Phases experienced: {sorted(stats['phases'])}")
            print(f"  Territories controlled: {len(stats['territories'])}")
            if stats["total_armies"]:
                print(f"  Average total armies: {statistics.mean(stats['total_armies']):.1f}")
    
    def analyze_territory_control(self):
        """Analyze territory control patterns"""
        print("\n=== Territory Control Analysis ===")
        
        territory_owners = defaultdict(list)
        continent_control = defaultdict(lambda: defaultdict(int))
        
        for sample in self.samples:
            state = sample["state"]
            players = state.get("players", [])
            board = state.get("board", {})
            continents = board.get("continents", {})
            
            # Track territory ownership
            for player in players:
                player_id = player["id"]
                territories = player.get("territories", [])
                
                for territory in territories:
                    territory_owners[territory].append(player_id)
                
                # Track continent control
                for continent_name, continent_data in continents.items():
                    continent_territories = continent_data.get("territories", [])
                    owned_in_continent = sum(1 for t in territories if t in continent_territories)
                    if owned_in_continent == len(continent_territories):
                        continent_control[continent_name][player_id] += 1
        
        print("Most contested territories:")
        contested_territories = [(t, len(owners)) for t, owners in territory_owners.items() if len(set(owners)) > 1]
        contested_territories.sort(key=lambda x: x[1], reverse=True)
        
        for territory, owner_count in contested_territories[:10]:
            print(f"  {territory}: {owner_count} different owners")
        
        print("\nContinent control frequency:")
        for continent, player_counts in continent_control.items():
            print(f"\n{continent}:")
            for player_id, count in sorted(player_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  Player {player_id}: {count} times")
    
    def analyze_reinforcement_patterns(self):
        """Analyze reinforcement patterns"""
        print("\n=== Reinforcement Pattern Analysis ===")
        
        reinforcement_data = []
        
        for sample in self.samples:
            if sample["phase"] == "reinforce":
                state = sample["state"]
                reinforcement_armies = state.get("reinforcement_armies", 0)
                possible_actions = state.get("possible_actions", [])
                
                # Count reinforce actions
                reinforce_actions = [a for a in possible_actions if "Reinforce" in a]
                
                reinforcement_data.append({
                    "turn": sample["turn"],
                    "player_id": sample["player_id"],
                    "reinforcement_armies": reinforcement_armies,
                    "reinforce_options": len(reinforce_actions),
                    "description": sample["description"]
                })
        
        if reinforcement_data:
            avg_armies = statistics.mean([d["reinforcement_armies"] for d in reinforcement_data])
            avg_options = statistics.mean([d["reinforce_options"] for d in reinforcement_data])
            
            print(f"Average reinforcement armies: {avg_armies:.1f}")
            print(f"Average reinforcement options: {avg_options:.1f}")
            
            # Analyze by turn
            turn_stats = defaultdict(list)
            for data in reinforcement_data:
                turn_stats[data["turn"]].append(data["reinforcement_armies"])
            
            print("\nReinforcement armies by turn:")
            for turn in sorted(turn_stats.keys()):
                armies = turn_stats[turn]
                print(f"  Turn {turn}: {statistics.mean(armies):.1f} avg ({min(armies)}-{max(armies)})")
    
    def generate_training_examples(self):
        """Generate training examples for AI agents"""
        print("\n=== Training Example Generation ===")
        
        training_examples = []
        
        for sample in self.samples:
            state = sample["state"]
            phase = sample["phase"]
            player_id = sample["player_id"]
            possible_actions = state.get("possible_actions", [])
            
            if possible_actions:
                # Create a training example
                example = {
                    "context": {
                        "turn": sample["turn"],
                        "phase": phase,
                        "player_id": player_id,
                        "description": sample["description"]
                    },
                    "state": {
                        "current_player": state.get("current_player"),
                        "turn_phase": state.get("turn_phase"),
                        "reinforcement_armies": state.get("reinforcement_armies", 0),
                        "players": state.get("players", []),
                        "board": state.get("board", {})
                    },
                    "available_actions": possible_actions,
                    "timestamp": sample["timestamp"]
                }
                
                training_examples.append(example)
        
        # Save training examples
        output_file = "training_examples.json"
        with open(output_file, 'w') as f:
            json.dump(training_examples, f, indent=2)
        
        print(f"✓ Generated {len(training_examples)} training examples")
        print(f"✓ Saved to {output_file}")
        
        # Show sample training example
        if training_examples:
            print("\nSample training example:")
            example = training_examples[0]
            print(f"  Context: Turn {example['context']['turn']}, Phase {example['context']['phase']}")
            print(f"  Available actions: {len(example['available_actions'])}")
            print(f"  Reinforcement armies: {example['state']['reinforcement_armies']}")
    
    def run_full_analysis(self):
        """Run complete analysis"""
        print("=== Game State Sample Analysis ===")
        print(f"Analyzing {len(self.samples)} samples...")
        
        self.analyze_phases()
        self.analyze_actions()
        self.analyze_player_progression()
        self.analyze_territory_control()
        self.analyze_reinforcement_patterns()
        self.generate_training_examples()
        
        print("\n=== Analysis Complete ===")

def main():
    """Main function"""
    analyzer = GameStateAnalyzer()
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main() 