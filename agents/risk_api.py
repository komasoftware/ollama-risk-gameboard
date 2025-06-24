"""
Risk API Client for interacting with the Risk game server.
Handles all HTTP requests to the Risk API running on port 8000.
"""

import requests
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging


class GamePhase(Enum):
    """Game phases in Risk."""
    REINFORCE = "reinforce"
    ATTACK = "attack"
    FORTIFY = "fortify"
    MOVE_ARMIES = "movearmies"


@dataclass
class Territory:
    """Represents a territory on the Risk board."""
    name: str
    owner: Optional[str]
    armies: int
    continent: str
    adjacent_territories: List[str]


@dataclass
class Player:
    """Represents a player in the game."""
    id: int
    name: str
    territories: List[str]
    armies: int
    cards: List[str]
    total_armies: int


@dataclass
class GameState:
    """Represents the current state of the Risk game."""
    territories: Dict[str, Territory]
    players: Dict[str, Player]
    current_player: str
    phase: GamePhase
    current_turn: int
    game_over: bool
    winner: Optional[str]
    possible_actions: List[Dict[str, Any]]
    conquer_probs: List[List[Any]]


class RiskAPIClient:
    """Client for interacting with the Risk API server."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_game_state(self) -> GameState:
        """Get the current game state."""
        response = self.session.get(f"{self.base_url}/game-state")
        response.raise_for_status()
        data = response.json()
        return self._parse_game_state(data)
    
    def reinforce(self, player_id: int, territory: str, num_armies: int) -> bool:
        """Reinforce a territory with additional armies."""
        logger = logging.getLogger(__name__)
        
        payload = {"player_id": player_id, "territory": territory, "num_armies": num_armies}
        logger.info(f"[REINFORCE] Sending payload: {payload}")
        
        response = self.session.post(f"{self.base_url}/reinforce", json=payload)
        logger.info(f"[REINFORCE] Response status: {response.status_code}")
        
        try:
            response_text = response.text
            logger.info(f"[REINFORCE] Response body: {response_text}")
        except Exception as e:
            logger.error(f"[REINFORCE] Could not decode response body: {e}")
        
        success = response.status_code == 200
        logger.info(f"[REINFORCE] Request {'SUCCEEDED' if success else 'FAILED'}")
        return success
    
    def attack(self, player_id: int, from_territory: str, to_territory: str, num_armies: int, num_dice: int, repeat: bool = False) -> Dict[str, Any]:
        """Attack from one territory to another."""
        payload = {
            "player_id": player_id,
            "from_territory": from_territory,
            "to_territory": to_territory,
            "num_armies": num_armies,
            "num_dice": num_dice,
            "repeat": repeat
        }
        response = self.session.post(f"{self.base_url}/attack", json=payload)
        response.raise_for_status()
        return response.json()
    
    def fortify(self, player_id: int, from_territory: str, to_territory: str, num_armies: int) -> bool:
        """Move armies from one territory to another during fortify phase."""
        payload = {
            "player_id": player_id,
            "from_territory": from_territory,
            "to_territory": to_territory,
            "num_armies": num_armies
        }
        response = self.session.post(f"{self.base_url}/fortify", json=payload)
        return response.status_code == 200
    
    def move_armies(self, player_id: int, from_territory: str, to_territory: str, num_armies: int) -> bool:
        """Move armies after a successful attack."""
        payload = {
            "player_id": player_id,
            "from_territory": from_territory,
            "to_territory": to_territory,
            "num_armies": num_armies
        }
        response = self.session.post(f"{self.base_url}/move_armies", json=payload)
        return response.status_code == 200
    
    def trade_cards(self, player_id: int, card_indices: List[int]) -> bool:
        """Trade in cards for additional armies."""
        payload = {"player_id": player_id, "card_indices": card_indices}
        response = self.session.post(f"{self.base_url}/trade_cards", json=payload)
        return response.status_code == 200
    
    def advance_phase(self) -> bool:
        """Advance to the next phase of the turn."""
        response = self.session.post(f"{self.base_url}/advance_phase")
        return response.status_code == 200
    
    def new_game(self) -> bool:
        """Start a new game."""
        response = self.session.post(f"{self.base_url}/new-game")
        return response.status_code == 200
    
    def get_reinforcement_armies(self) -> int:
        """Get the current reinforcement armies directly from the server."""
        response = self.session.get(f"{self.base_url}/game-state")
        response.raise_for_status()
        data = response.json()
        game_data = data.get("game_state", data)
        return game_data.get("reinforcement_armies", 0)
    
    def _parse_game_state(self, data: Dict[str, Any]) -> GameState:
        """Parse the game state from API response."""
        # The API response has a nested game_state structure
        game_data = data.get("game_state", data)
        
        territories = {}
        for territory_name, territory_data in game_data.get("board", {}).get("territories", {}).items():
            # Find the owner and armies from the players data
            owner = None
            armies = 1  # Default to 1 army
            
            for player_data in game_data.get("players", []):
                if territory_name in player_data.get("territories", []):
                    owner = player_data["name"]
                    armies = player_data.get("armies", {}).get(territory_name, 1)
                    break
            
            territory = Territory(
                name=territory_name,
                owner=owner,
                armies=armies,
                continent=territory_data.get("continent", "Unknown"),
                adjacent_territories=territory_data.get("adjacent_territories", [])
            )
            territories[territory.name] = territory
        
        players = {}
        current_player_name = game_data.get("current_player", "Unknown")
        reinforcement_armies = game_data.get("reinforcement_armies", 0)
        
        for player_data in game_data.get("players", []):
            # Use reinforcement_armies for current player during reinforce phase
            # Otherwise use army_supply from player data
            if (game_data.get("turn_phase", "").lower() == "reinforce" and 
                player_data["name"] == current_player_name):
                armies = reinforcement_armies
            else:
                armies = player_data.get("army_supply", 0)
            
            # Calculate total armies by summing all armies in territories
            total_armies = sum(player_data.get("armies", {}).values())
            
            player = Player(
                id=player_data.get("id", -1),
                name=player_data["name"],
                territories=player_data.get("territories", []),
                armies=armies,
                cards=player_data.get("cards", []),
                total_armies=total_armies
            )
            players[player.name] = player
        
        # Map phase string to enum
        phase_str = game_data.get("turn_phase", "reinforce").lower()
        if phase_str == "reinforce":
            phase = GamePhase.REINFORCE
        elif phase_str == "attack":
            phase = GamePhase.ATTACK
        elif phase_str == "fortify":
            phase = GamePhase.FORTIFY
        elif phase_str == "movearmies":
            phase = GamePhase.MOVE_ARMIES
        else:
            phase = GamePhase.REINFORCE  # Default
        
        return GameState(
            territories=territories,
            players=players,
            current_player=game_data.get("current_player", "Unknown"),
            phase=phase,
            current_turn=game_data.get("current_turn", 0),
            game_over=len(game_data.get("defeated_players", [])) >= len(players) - 1,
            winner=game_data.get("winner"),
            possible_actions=game_data.get("possible_actions", []),
            conquer_probs=game_data.get("conquer_probs", [])
        ) 