#!/usr/bin/env python3
"""
Simple Risk Player Agent using Google ADK
Uses MCP tools to interact with the Risk game
"""

import os
import logging
from typing import Dict, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.models import Gemini

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/stream')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')
PROJECT_ID = os.getenv('PROJECT_ID', 'your-project-id')
LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', 'global')

def create_risk_player_agent() -> LlmAgent:
    """Create a Risk player agent with MCP tools"""
    
    # Initialize MCP toolset
    mcp_toolset = MCPToolset(
        url=MCP_SERVER_URL,
        headers={"accept": "application/json, text/event-stream"}
    )
    
    # Create the agent
    agent = LlmAgent(
        model=Gemini(
            model=GEMINI_MODEL,
            vertexai=True,
            location=LOCATION,
            project_id=PROJECT_ID
        ),
        name="RiskPlayer",
        description="A Risk game player agent that can play turns using MCP tools",
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
        4. When "EndPhase" appears in possible_actions, you can call advance_phase to move to the next phase. Do this if other possible actions are not strategically interesting.
        5. When "EndPhase" is the only possible action, then you must call advance_phase to move to the next phase
        6. Follow the proper Risk game phases: Reinforce -> Attack -> Fortify
        7. Make strategic decisions based on the available actions and game state
        8. After completing your turn, explain your strategy for future reference
        
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
    
    return agent

# Create the agent instance
risk_player_agent = create_risk_player_agent()

if __name__ == "__main__":
    # For testing - you can run this directly
    print("Risk Player Agent created successfully!")
    print(f"MCP Server URL: {MCP_SERVER_URL}")
    print(f"Gemini Model: {GEMINI_MODEL}")
    print(f"Project ID: {PROJECT_ID}") 