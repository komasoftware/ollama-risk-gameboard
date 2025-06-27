#!/usr/bin/env python3
"""
Risk MCP Server - HTTP Version for Cloud Run
Exposes Risk API functions as MCP tools over HTTP
"""

from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, List, Any, Optional
from risk_api import RiskAPIClient
import uvicorn
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
server = FastMCP("Risk Game Server")

# Initialize the Risk API client
risk_client = RiskAPIClient(base_url="https://risk-api-server-441582515789.europe-west4.run.app")

@server.tool(
    name="get_game_state", 
    description="Get the current state of the Risk game including players, territories, armies, and possible actions"
)
def get_game_state() -> Dict[str, Any]:
    """Get the current game state as raw data."""
    logger.info("[MCP] Getting game state")
    try:
        result = risk_client.get_game_state()
        logger.info(f"[MCP] Game state retrieved successfully")
        return {
            "success": True,
            "game_state": result
        }
    except Exception as e:
        logger.error(f"[MCP] Error getting game state: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="reinforce", 
    description="Add armies to a territory during the reinforce phase"
)
def reinforce(player_id: int, territory: str, num_armies: int) -> Dict[str, Any]:
    """Reinforce a territory with additional armies."""
    logger.info(f"[MCP] Reinforcing {territory} with {num_armies} armies for player {player_id}")
    try:
        success = risk_client.reinforce(player_id, territory, num_armies)
        return {
            "success": success,
            "message": f"Reinforced {territory} with {num_armies} armies" if success else "Reinforcement failed"
        }
    except Exception as e:
        logger.error(f"[MCP] Error reinforcing: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="attack", 
    description="Attack from one territory to another"
)
def attack(player_id: int, from_territory: str, to_territory: str, num_armies: int, num_dice: int, repeat: bool = False) -> Dict[str, Any]:
    """Attack from one territory to another."""
    logger.info(f"[MCP] Attacking from {from_territory} to {to_territory} with {num_armies} armies, {num_dice} dice")
    try:
        result = risk_client.attack(player_id, from_territory, to_territory, num_armies, num_dice, repeat)
        return {
            "success": True,
            "attack_result": result
        }
    except Exception as e:
        logger.error(f"[MCP] Error attacking: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="fortify", 
    description="Move armies from one territory to another during fortify phase"
)
def fortify(player_id: int, from_territory: str, to_territory: str, num_armies: int) -> Dict[str, Any]:
    """Move armies from one territory to another during fortify phase."""
    logger.info(f"[MCP] Fortifying: moving {num_armies} armies from {from_territory} to {to_territory}")
    try:
        success = risk_client.fortify(player_id, from_territory, to_territory, num_armies)
        return {
            "success": success,
            "message": f"Moved {num_armies} armies from {from_territory} to {to_territory}" if success else "Fortification failed"
        }
    except Exception as e:
        logger.error(f"[MCP] Error fortifying: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="move_armies", 
    description="Move armies after a successful attack"
)
def move_armies(player_id: int, from_territory: str, to_territory: str, num_armies: int) -> Dict[str, Any]:
    """Move armies after a successful attack."""
    logger.info(f"[MCP] Moving {num_armies} armies from {from_territory} to {to_territory} after conquest")
    try:
        success = risk_client.move_armies(player_id, from_territory, to_territory, num_armies)
        return {
            "success": success,
            "message": f"Moved {num_armies} armies from {from_territory} to {to_territory}" if success else "Move armies failed"
        }
    except Exception as e:
        logger.error(f"[MCP] Error moving armies: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="trade_cards", 
    description="Trade in cards for additional armies"
)
def trade_cards(player_id: int, card_indices: List[int]) -> Dict[str, Any]:
    """Trade in cards for additional armies."""
    logger.info(f"[MCP] Trading cards with indices {card_indices} for player {player_id}")
    try:
        success = risk_client.trade_cards(player_id, card_indices)
        return {
            "success": success,
            "message": f"Traded cards {card_indices} for bonus armies" if success else "Card trading failed"
        }
    except Exception as e:
        logger.error(f"[MCP] Error trading cards: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="advance_phase", 
    description="Advance to the next phase of the turn"
)
def advance_phase() -> Dict[str, Any]:
    """Advance to the next phase of the turn."""
    logger.info("[MCP] Advancing to next phase")
    try:
        success = risk_client.advance_phase()
        return {
            "success": success,
            "message": "Advanced to next phase" if success else "Phase advancement failed"
        }
    except Exception as e:
        logger.error(f"[MCP] Error advancing phase: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="new_game", 
    description="Start a new game"
)
def new_game() -> Dict[str, Any]:
    """Start a new game."""
    logger.info("[MCP] Starting new game")
    try:
        success = risk_client.new_game()
        return {
            "success": success,
            "message": "New game started" if success else "Failed to start new game"
        }
    except Exception as e:
        logger.error(f"[MCP] Error starting new game: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="get_reinforcement_armies", 
    description="Get the current number of reinforcement armies available"
)
def get_reinforcement_armies() -> Dict[str, Any]:
    """Get the current reinforcement armies directly from the server."""
    logger.info("[MCP] Getting reinforcement armies")
    try:
        armies = risk_client.get_reinforcement_armies()
        return {
            "success": True,
            "reinforcement_armies": armies
        }
    except Exception as e:
        logger.error(f"[MCP] Error getting reinforcement armies: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@server.tool(
    name="get_possible_actions", 
    description="Get the list of possible actions from the current game state"
)
def get_possible_actions() -> Dict[str, Any]:
    """Get the list of possible actions from the current game state."""
    logger.info("[MCP] Getting possible actions")
    try:
        game_state = risk_client.get_game_state()
        possible_actions = RiskAPIClient.get_possible_actions(game_state)
        return {
            "success": True,
            "possible_actions": possible_actions
        }
    except Exception as e:
        logger.error(f"[MCP] Error getting possible actions: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    logger.info("Starting Risk MCP Server (HTTP)...")
    
    # Get port from environment variable (Cloud Run sets PORT)
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"  # Bind to all interfaces for Cloud Run
    
    logger.info(f"Starting HTTP server on {host}:{port}")
    
    # Run the server with uvicorn
    uvicorn.run(
        server.streamable_http_app(),
        host=host,
        port=port,
        log_level="info"
    ) 