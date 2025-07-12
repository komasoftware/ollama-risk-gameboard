import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Any

from workflow_config import WorkflowAgentConfig
from risk_api_client import RiskAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflow_agent")

# Load config from environment variables
RISK_API_URL = os.environ.get("RISK_API_URL", "http://localhost:8080")
PLAYER_AGENT_URLS = os.environ.get("PLAYER_AGENT_URLS", "http://localhost:8081,http://localhost:8082")
AGENT_NAME = os.environ.get("AGENT_NAME", "RiskWorkflowAgent")
PORT = int(os.environ.get("PORT", 8080))

logger.info(f"Starting {AGENT_NAME}")
logger.info(f"Risk API URL: {RISK_API_URL}")
logger.info(f"Player agent URLs: {PLAYER_AGENT_URLS}")

app = FastAPI(title=AGENT_NAME)

class HealthResponse(BaseModel):
    status: str
    agent: str

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", agent=AGENT_NAME)

@app.get("/test-game-state")
async def test_game_state():
    config = WorkflowAgentConfig()
    client = RiskAPIClient(base_url=config.risk_api_url)
    result = await client.get_game_state()
    await client.close()
    if result is not None:
        return {"success": True, "game_state": result}
    else:
        return {"success": False, "error": "Could not fetch game state"}

@app.get("/test-agent-cards")
async def test_agent_cards():
    config = WorkflowAgentConfig()
    agent_cards = []
    for url in config.player_agent_urls:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    agent_cards.append({
                        "url": url,
                        "card": response.json()
                    })
                else:
                    agent_cards.append({
                        "url": url,
                        "error": f"HTTP {response.status_code}"
                    })
        except Exception as e:
            agent_cards.append({
                "url": url,
                "error": str(e)
            })
    return {"agent_cards": agent_cards}

if __name__ == "__main__":
    uvicorn.run("workflow_agent:app", host="0.0.0.0", port=PORT, log_level="info") 