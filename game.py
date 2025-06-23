import json
import sys
import asyncio
from typing import Any, Dict
from agents.simple_agent import SimpleAgent, AggressiveAgent, DefensiveAgent
from agents.game_orchestrator import run_single_game
import requests
from main import setup_logging  # Import logging setup from main.py

CONFIG_FILE = "game_config.json"  # Change this to use a different config
API_BASE = "http://localhost:8000"
ENDPOINTS = {
    "new_game": f"{API_BASE}/new-game",
}

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

async def main():
    setup_logging()  # Set up logging to file and console
    player_names = get_player_names_from_config(CONFIG_FILE)
    strategy_classes = [AggressiveAgent, SimpleAgent, DefensiveAgent]
    agents = []
    for idx, name in enumerate(player_names):
        strat_cls = strategy_classes[idx % len(strategy_classes)]
        agents.append(strat_cls(name))
    print(f"Starting new game with agents: {', '.join(player_names)}")
    game_config_summary = summarize_game_config(CONFIG_FILE)
    start_new_game(CONFIG_FILE)
    await run_single_game(agents, game_config_summary)

if __name__ == "__main__":
    asyncio.run(main()) 