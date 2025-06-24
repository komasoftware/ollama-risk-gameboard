#!/usr/bin/env python3
"""
Main script for running AI agents playing Risk.
Starts a new game and runs it with AI agents.
"""

import json
import sys
import asyncio
import os
from typing import Any, Dict, Optional
from agents.simple_agent import SimpleAgent, AggressiveAgent, DefensiveAgent
from agents.game_orchestrator import run_single_game
import requests
import logging
from datetime import datetime

CONFIG_FILE = "game_config.json"  # Default config file
API_BASE = "http://localhost:8000"
ENDPOINTS = {
    "new_game": f"{API_BASE}/new-game",
    "game_state": f"{API_BASE}/game-state",
}

# Set up logging to both console and file
def setup_logging():
    """Set up logging to both console and file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"risk_game_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    print(f"📝 Logging to: {log_filename}")
    return log_filename

def get_player_names_from_config(path: str) -> list:
    with open(path, "r") as f:
        config = json.load(f)
    players = config.get("players")
    if players:
        return [p["name"] for p in players if "name" in p]
    if "game" in config and "players" in config["game"]:
        return [p["name"] for p in config["game"]["players"] if "name" in p]
    print("Could not find player names in config.")
    sys.exit(1)

def start_new_game(config_file: str):
    response = requests.post(ENDPOINTS["new_game"], json={"config_file": config_file})
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    return response.json()

def get_current_game_state() -> Optional[Dict[str, Any]]:
    """Get the current game state from the server."""
    try:
        response = requests.get(ENDPOINTS["game_state"])
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting game state: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to server: {e}")
        return None

def check_existing_game() -> bool:
    """Check if there's an existing game in progress."""
    game_state = get_current_game_state()
    if game_state and game_state.get("game_state"):
        return True
    return False

def summarize_existing_game() -> Dict[str, Any]:
    """Get a summary of the existing game."""
    game_state = get_current_game_state()
    if not game_state or not game_state.get("game_state"):
        return {}
    
    game_data = game_state["game_state"]
    players = game_data.get("players", [])
    
    summary = {
        "num_players": len(players),
        "players": [],
        "current_player": game_data.get("current_player", "Unknown"),
        "phase": game_data.get("turn_phase", "Unknown"),
        "turn": game_data.get("current_turn", 0),
        "game_over": game_data.get("winner") is not None,
    }
    
    for player in players:
        total_armies = sum(player.get("armies", {}).values())
        summary["players"].append({
            "name": player["name"],
            "territory_count": len(player.get("territories", [])),
            "total_armies": total_armies,
            "cards": len(player.get("cards", [])),
        })
    
    return summary

def summarize_game_config(path: str) -> dict:
    with open(path, "r") as f:
        config = json.load(f)
    summary = {
        "num_players": len(config["players"]),
        "players": [],
    }
    for player in config["players"]:
        total_armies = sum(t["armies"] for t in player["territories"])
        summary["players"].append({
            "name": player["name"],
            "territory_count": len(player["territories"]),
            "total_armies": total_armies,
        })
    return summary

def get_user_choice() -> str:
    """Get user choice for game mode."""
    print("\n🎮 Game Options:")
    print("1. Start a new game with config file")
    print("2. Continue with existing game (default)")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3, or press Enter for default): ").strip()
        if not choice:
            choice = "2"  # Default to continue with existing game
        if choice in ["1", "2", "3"]:
            return choice
        print("Invalid choice. Please enter 1, 2, or 3.")

def get_config_file_path() -> str:
    """Get config file path from user."""
    print(f"\n📁 Current default config: {CONFIG_FILE}")
    print("💡 Note: This should be a path on the Risk API server, not a local path.")
    
    while True:
        config_path = input("Enter server config file path (or press Enter for default): ").strip()
        if not config_path:
            config_path = CONFIG_FILE
        
        # Since this is a server path, we can't validate it locally
        # The server will handle validation and return an error if the file doesn't exist
        return config_path

def display_game_summary(summary: Dict[str, Any], is_existing: bool = False):
    """Display a summary of the game."""
    if is_existing:
        print(f"\n📊 Existing Game Summary:")
        print(f"  Current Player: {summary.get('current_player', 'Unknown')}")
        print(f"  Phase: {summary.get('phase', 'Unknown')}")
        print(f"  Turn: {summary.get('turn', 0)}")
        if summary.get('game_over'):
            print(f"  Status: Game Over - Winner: {summary.get('winner', 'Unknown')}")
        else:
            print(f"  Status: In Progress")
    else:
        print(f"\n📊 New Game Configuration:")
    
    print(f"  Players: {summary.get('num_players', 0)}")
    for player in summary.get('players', []):
        status = " (Current)" if player['name'] == summary.get('current_player') else ""
        print(f"    - {player['name']}: {player['territory_count']} territories, {player['total_armies']} armies{status}")
        if 'cards' in player:
            print(f"      Cards: {player['cards']}")

async def main():
    """Main function to start a new game and run it with AI agents."""
    log_filename = setup_logging()  # Set up logging to file and console
    
    print("🤖 AI Agents Playing Risk")
    print("=" * 50)
    
    # Check for existing game
    has_existing_game = check_existing_game()
    
    if has_existing_game:
        existing_summary = summarize_existing_game()
        display_game_summary(existing_summary, is_existing=True)
    
    # Get user choice
    choice = get_user_choice()
    
    if choice == "3":
        print("👋 Goodbye!")
        return
    
    if choice == "1":
        # Start new game
        config_file = get_config_file_path()
        print(f"\n🎮 Starting new game with config: {config_file}")
        
        player_names = get_player_names_from_config(config_file)
        strategy_classes = [AggressiveAgent, SimpleAgent, DefensiveAgent]
        agents = []
        for idx, name in enumerate(player_names):
            strat_cls = strategy_classes[idx % len(strategy_classes)]
            agents.append(strat_cls(name))
        
        print(f"✅ Players in this game: {player_names}")
        print(f"\nCreated {len(agents)} agents:")
        for agent in agents:
            print(f"  - {agent.get_strategy_description()}")
        
        game_config_summary = summarize_game_config(config_file)
        display_game_summary(game_config_summary)
        
        start_new_game(config_file)
        result = await run_single_game(agents, game_config_summary)
        
    elif choice == "2":
        # Continue existing game
        if not has_existing_game:
            print("❌ No existing game found. Please start a new game.")
            return
        
        existing_summary = summarize_existing_game()
        if existing_summary.get('game_over'):
            print("❌ The existing game is already over. Please start a new game.")
            return
        
        print(f"\n🎮 Continuing existing game...")
        
        # Create agents based on existing players
        player_names = [p['name'] for p in existing_summary['players']]
        strategy_classes = [AggressiveAgent, SimpleAgent, DefensiveAgent]
        agents = []
        for idx, name in enumerate(player_names):
            strat_cls = strategy_classes[idx % len(strategy_classes)]
            agents.append(strat_cls(name))
        
        print(f"✅ Continuing with players: {player_names}")
        print(f"\nCreated {len(agents)} agents:")
        for agent in agents:
            print(f"  - {agent.get_strategy_description()}")
        
        result = await run_single_game(agents, existing_summary)
    
    print(f"\n🎯 Game completed! Check {log_filename} for detailed logs.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1) 