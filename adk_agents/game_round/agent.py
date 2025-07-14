#!/usr/bin/env python3
"""
ADK Game Round Agent
LoopAgent that coordinates a full Risk game round by calling each player in sequence
"""

import os
import logging
import sys
from pathlib import Path
import importlib.util

# Add parent directory to path to import player agents
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.agents import LoopAgent, LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
from google.adk.models import Gemini
from logging_mcp_toolset import wrap_mcp_toolset_with_logging

# Import player agents using importlib for hyphenated directory names
def load_agent_from_path(agent_path, agent_name):
    """Load an agent from a path with hyphenated directory name"""
    spec = importlib.util.spec_from_file_location(agent_name, agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.root_agent

# Load player agents
player_1_agent = load_agent_from_path(
    Path(__file__).parent.parent / "player-1" / "agent.py", 
    "player_1_agent"
)
player_2_agent = load_agent_from_path(
    Path(__file__).parent.parent / "player-2" / "agent.py", 
    "player_2_agent"
)
player_3_agent = load_agent_from_path(
    Path(__file__).parent.parent / "player-3" / "agent.py", 
    "player_3_agent"
)
player_4_agent = load_agent_from_path(
    Path(__file__).parent.parent / "player-4" / "agent.py", 
    "player_4_agent"
)
player_5_agent = load_agent_from_path(
    Path(__file__).parent.parent / "player-5" / "agent.py", 
    "player_5_agent"
)
player_6_agent = load_agent_from_path(
    Path(__file__).parent.parent / "player-6" / "agent.py", 
    "player_6_agent"
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("[GameRoundAgent] Agent module loaded and logging set to DEBUG.")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
PROJECT_ID = os.getenv('PROJECT_ID', 'koen-gcompany-demo')
LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', 'global')
USE_VERTEXAI = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE').upper() == 'TRUE'
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/stream')

# Game configuration
MAX_PLAYERS = int(os.getenv('MAX_PLAYERS', '6'))
GAME_TIMEOUT = int(os.getenv('GAME_TIMEOUT', '300'))  # seconds
TURN_TIMEOUT = int(os.getenv('TURN_TIMEOUT', '60'))   # seconds

# Initialize MCP toolset
mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        headers={"accept": "application/json, text/event-stream"},
        timeout=30.0,
        sse_read_timeout=30.0
    )
)
mcp_toolset = wrap_mcp_toolset_with_logging(mcp_toolset)

# Create a game coordinator agent
game_coordinator = LlmAgent(
    model=Gemini(
        model=GEMINI_MODEL,
        vertexai=USE_VERTEXAI,
        location=LOCATION,
        project=PROJECT_ID
    ),
    name="GameCoordinator",
    description="Coordinates Risk game rounds and delegates turns to player agents",
    instruction="""
    You are the GameCoordinator. You must enforce strict turn order and state checking. For each turn:
    1. Call get_game_state to determine the current player and check if the game is complete.
    2. If the game is complete, announce the winner and stop.
    3. If it is a player’s turn, delegate to that player agent using:
       Delegate to RiskPlayer_PlayerX: It is your turn. Play your turn using MCP tools.
       (Replace X with the player number.)
    4. Wait for the player agent to finish their turn.
    5. Call get_game_state again to update the state.
    6. Repeat for the next player in order.
    
    CRITICAL RULES:
    - NEVER delegate to more than one player at a time.
    - ALWAYS call get_game_state before and after each player turn.
    - ONLY delegate to the player whose turn it is (as indicated by the game state).
    - NEVER call MCP tools for game moves yourself—only delegate.
    - If the game is complete, announce the winner and stop immediately.
    - Monitor the game flow and coordinate the overall process step by step.
    """,
    tools=[mcp_toolset]
)

# Create the LoopAgent with all player agents as sub-agents
root_agent = LoopAgent(
    name="GameRoundAgent",
    description="Orchestrates complete Risk game rounds using LoopAgent with player delegation",
    sub_agents=[
        game_coordinator,
        player_1_agent,
        player_2_agent,
        player_3_agent,
        player_4_agent,
        player_5_agent,
        player_6_agent
    ]
)

if __name__ == "__main__":
    print("Game Round Agent created successfully!")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"Use Vertex AI: {USE_VERTEXAI}")
    print(f"Max Players: {MAX_PLAYERS}")
    print(f"Game Timeout: {GAME_TIMEOUT}s")
    print(f"Turn Timeout: {TURN_TIMEOUT}s")
    print(f"MCP Server URL: {MCP_SERVER_URL}")
    print(f"Sub-agents: {len(root_agent.sub_agents)} agents")
    print("\nAgent is ready to be served with: adk web")
    print("Agent card will be available at: http://localhost:8000/.well-known/agent.json") 