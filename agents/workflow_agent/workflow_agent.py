import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Any

from workflow_config import WorkflowAgentConfig
from risk_api import RiskAPIClient
from loop_agent import create_loop_agent, RiskLoopAgent

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

class StartGameRequest(BaseModel):
    num_players: int = 2

class StartGameResponse(BaseModel):
    success: bool
    message: str

class PlayTurnResponse(BaseModel):
    status: str
    message: str
    data: dict = {}

# Global LoopAgent instance
loop_agent: RiskLoopAgent = None

@app.on_event("startup")
async def startup_event():
    """Initialize the LoopAgent on startup"""
    global loop_agent
    loop_agent = await create_loop_agent()
    logger.info("LoopAgent initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up the LoopAgent on shutdown"""
    global loop_agent
    if loop_agent:
        await loop_agent.close()
        logger.info("LoopAgent cleaned up")

@app.get("/.well-known/agent.json")
async def agent_card():
    """Return the agent card for A2A discovery"""
    return {
        "name": "Risk Workflow Agent",
        "description": "ADK agent for orchestrating Risk games and managing game flow",
        "url": "http://localhost:8080/",
        "version": "1.0.0",
        "defaultInputModes": ["text", "data"],
        "defaultOutputModes": ["text"],
        "capabilities": {
            "streaming": True
        },
        "skills": [
            {
                "id": "start_game",
                "name": "Start Game",
                "description": "Start a new Risk game with specified number of players",
                "inputModes": ["text", "data"],
                "outputModes": ["text"],
                "tags": ["risk", "game", "orchestration", "workflow"]
            },
            {
                "id": "play_turn",
                "name": "Play Turn",
                "description": "Play a single turn in the current game",
                "inputModes": ["text", "data"],
                "outputModes": ["text"],
                "tags": ["risk", "game", "turn", "orchestration"]
            },
            {
                "id": "play_turn_with_context",
                "name": "Play Turn with Context",
                "description": "Play a single turn with contextual prompt from HostAgent",
                "inputModes": ["text", "data"],
                "outputModes": ["text"],
                "tags": ["risk", "game", "turn", "orchestration", "context"]
            },
            {
                "id": "run_game",
                "name": "Run Game",
                "description": "Run the complete game loop until completion",
                "inputModes": ["text", "data"],
                "outputModes": ["text"],
                "tags": ["risk", "game", "orchestration", "workflow"]
            }
        ]
    }

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", agent=AGENT_NAME)

@app.post("/start-game", response_model=StartGameResponse)
async def start_game(request: StartGameRequest):
    """Start a new Risk game"""
    global loop_agent
    if not loop_agent:
        return StartGameResponse(success=False, message="LoopAgent not initialized")
    
    try:
        success = await loop_agent.start_game(request.num_players)
        if success:
            return StartGameResponse(success=True, message=f"Started game with {request.num_players} players")
        else:
            return StartGameResponse(success=False, message="Failed to start game")
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return StartGameResponse(success=False, message=f"Error: {str(e)}")

@app.post("/play-turn", response_model=PlayTurnResponse)
async def play_turn():
    """Play a single turn (stepwise mode)"""
    global loop_agent
    if not loop_agent:
        return PlayTurnResponse(status="error", message="LoopAgent not initialized")
    
    try:
        result = await loop_agent.play_single_turn()
        return PlayTurnResponse(
            status=result.get("status", "unknown"),
            message=result.get("message", ""),
            data=result
        )
    except Exception as e:
        logger.error(f"Error playing turn: {e}")
        return PlayTurnResponse(status="error", message=f"Error: {str(e)}")

@app.post("/play-turn-with-context")
async def play_turn_with_context(request: dict):
    """Play a single turn with contextual prompt from HostAgent"""
    global loop_agent
    if not loop_agent:
        return {"status": "error", "message": "LoopAgent not initialized"}
    
    try:
        contextual_prompt = request.get("contextual_prompt", "")
        target_player = request.get("target_player")
        
        # Store the contextual prompt for the next turn
        if hasattr(loop_agent, 'next_contextual_prompt'):
            loop_agent.next_contextual_prompt = contextual_prompt
            loop_agent.next_target_player = target_player
        
        result = await loop_agent.play_single_turn_with_context(contextual_prompt, target_player)
        return result
    except Exception as e:
        logger.error(f"Error playing turn with context: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}

@app.post("/run-game")
async def run_game():
    """Run the complete game loop until completion"""
    global loop_agent
    if not loop_agent:
        return {"status": "error", "message": "LoopAgent not initialized"}
    
    try:
        result = await loop_agent.run_game_loop()
        return result
    except Exception as e:
        logger.error(f"Error running game: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}

@app.get("/test-game-state")
async def test_game_state():
    config = WorkflowAgentConfig()
    client = RiskAPIClient(base_url=config.risk_api_url)
    result = client.get_game_state()
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