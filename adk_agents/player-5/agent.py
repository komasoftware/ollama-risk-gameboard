#!/usr/bin/env python3
"""
ADK Risk Player Agent
Simple Google ADK agent that uses MCP tools to play Risk games
"""

import os
import logging
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
from google.adk.models import Gemini
from logging_mcp_toolset import wrap_mcp_toolset_with_logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("[RiskPlayer_Player5] Agent module loaded and logging set to DEBUG.")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/stream')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')
PROJECT_ID = os.getenv('PROJECT_ID', 'koen-gcompany-demo')
LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', 'global')
USE_VERTEXAI = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE').upper() == 'TRUE'

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

# Create the ADK agent
root_agent = LlmAgent(
    model=Gemini(
        model=GEMINI_MODEL,
        vertexai=USE_VERTEXAI,
        location=LOCATION,
        project=PROJECT_ID
    ),
    name="RiskPlayer_Player5",
    description="A Risk game player agent that can play turns using MCP tools - specializes in continent control",
    instruction="""
    You are a Risk game player agent. You can use the following MCP tools:
    
    Game State Tools:
    - get_game_state: Get the current state of the Risk game
    - get_possible_actions: Get list of possible actions
    - get_reinforcement_armies: Get current reinforcement armies
    
    Game Action Tools:
    - reinforce: Add armies to a territory during the reinforce phase
    - attack: Attack from one territory to another
    - fortify: Move armies between connected territories during fortify phase
    - move_armies: Move armies after a successful attack
    - trade_cards: Trade in cards for additional armies
    - advance_phase: Advance to the next phase of the turn
    
    Game Management:
    - new_game: Start a new game
    
    CRITICAL RULES:
    1. ALWAYS check the game state first to understand the current situation
    2. If it's YOUR turn, you MUST select and execute a possible action
    3. NEVER stop or wait when it's your turn - you must take an action
    4. When "EndPhase" appears in possible_actions, call advance_phase to move to the next phase
    5. Follow the proper Risk game phases: Reinforce -> Attack -> Fortify
    6. Make strategic decisions based on the available actions and game state
    7. After completing your turn, explain your strategy for future reference
    
    TURN EXECUTION PROCESS:
    1. Get the current game state
    2. Check if it's your turn (current_player should match your player_id)
    3. If it's your turn, get the possible actions
    4. Select and execute ONE action from the possible actions
    5. If "EndPhase" is the only action or you choose to end the phase, call advance_phase
    6. Repeat steps 1-5 until your turn is complete
    7. If it's NOT your turn, explain why and stop immediately
    
    Remember: You must always take an action when it's your turn. Never pass or wait.
    """,
    tools=[mcp_toolset]
)

if __name__ == "__main__":
    from google.adk.web import serve_agent
    
    print("Risk Player Agent created successfully!")
    print(f"MCP Server URL: {MCP_SERVER_URL}")
    print(f"Gemini Model: {GEMINI_MODEL}")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"Use Vertex AI: {USE_VERTEXAI}")
    print("\nStarting ADK web server...")
    print("Agent card will be available at: http://localhost:8000/.well-known/agent.json")
    
    serve_agent(root_agent) 