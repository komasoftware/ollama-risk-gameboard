import os
import httpx
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("risk_api_client")

class RiskAPIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("RISK_API_URL", "http://localhost:8080")
        self.client = httpx.AsyncClient()

    async def get_game_state(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/game-state"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            logger.info(f"Fetched game state from {url}")
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching game state: {e}")
            return None

    async def start_new_game(self, num_players: int = 2) -> bool:
        url = f"{self.base_url}/new-game"
        try:
            resp = await self.client.post(url, json={"num_players": num_players})
            resp.raise_for_status()
            logger.info(f"Started new game with {num_players} players")
            return True
        except Exception as e:
            logger.error(f"Error starting new game: {e}")
            return False

    async def close(self):
        await self.client.aclose() 