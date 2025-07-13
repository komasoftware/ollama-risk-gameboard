"""
Risk API Client for interacting with the Risk game server.
Handles all HTTP requests to the Risk API running on port 8000.
"""

import requests
import json
from typing import Dict, List, Optional, Any
from enum import Enum
import logging


class GamePhase(Enum):
    """Game phases in Risk."""
    REINFORCE = "reinforce"
    ATTACK = "attack"
    FORTIFY = "fortify"
    MOVE_ARMIES = "movearmies"


class RiskAPIClient:
    """Client for interacting with the Risk API server."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        # Add timeout to prevent hanging requests
        self.timeout = 30  # 30 seconds timeout
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state as raw data."""
        response = self.session.get(f"{self.base_url}/game-state", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
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
    
    def new_game(self, config_file: Optional[str] = None, num_players: Optional[int] = None) -> bool:
        """Start a new game."""
        logger = logging.getLogger(__name__)
        
        payload = {}
        if config_file is not None:
            payload["config_file"] = config_file
        if num_players is not None:
            payload["num_players"] = num_players
        
        logger.info(f"[NEW_GAME] Starting new game with payload: {payload}")
        
        try:
            response = self.session.post(f"{self.base_url}/new-game", json=payload)
            logger.info(f"[NEW_GAME] Response status: {response.status_code}")
            
            try:
                response_text = response.text
                logger.info(f"[NEW_GAME] Response body: {response_text}")
            except Exception as e:
                logger.error(f"[NEW_GAME] Could not decode response body: {e}")
            
            success = response.status_code == 200
            logger.info(f"[NEW_GAME] Request {'SUCCEEDED' if success else 'FAILED'}")
            return success
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[NEW_GAME] Request failed: {e}")
            return False
    
    def get_reinforcement_armies(self) -> int:
        """Get the current reinforcement armies directly from the server."""
        response = self.session.get(f"{self.base_url}/game-state")
        response.raise_for_status()
        data = response.json()
        game_data = data.get("game_state", data)
        return game_data.get("reinforcement_armies", 0)

    @staticmethod
    def get_possible_actions(game_state: dict) -> list:
        game_data = game_state.get("game_state", game_state)
        return game_data.get("possible_actions", []) 