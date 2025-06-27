#!/usr/bin/env python3
"""
Risk Agent using Google ADK with MCP Tools (HTTP Version)
Integrates with Risk MCP server using MCPToolset over HTTP
"""

import asyncio
import logging
import os
from typing import Dict, Any
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.models import Gemini
from google.genai import types

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskADKAgentHTTP:
    """Risk game agent using Google ADK with MCP tools over HTTP"""
    
    def __init__(self, name: str = "RiskPlayer", mcp_server_url: str = "http://localhost:8080"):
        self.name = name
        self.mcp_server_url = mcp_server_url
        self.agent = None
        self.toolset = None
        self.runner = None
        self.session_service = None
        self.session = None
    
    async def initialize(self):
        """Initialize the agent with MCP tools over HTTP"""
        logger.info(f"Initializing Risk ADK Agent with MCP server at {self.mcp_server_url}")
        
        # Create MCP toolset for Risk server using HTTP connection
        self.toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=self.mcp_server_url,
                headers={},  # Add any required headers
                timeout=30.0,  # 30 second timeout
                sse_read_timeout=30.0  # 30 second SSE read timeout
            )
        )
        
        # Create the LLM agent
        self.agent = LlmAgent(
            model=Gemini(model_name='gemini-2.5-flash-lite-preview-06-17'),
            name=self.name,
            instruction="""
            You are a Risk game player agent. You can use the following tools:
            1. get_game_state - Get the current state of the Risk game
            2. reinforce - Add armies to a territory during the reinforce phase
            3. attack - Attack from one territory to another
            4. fortify - Move armies between connected territories during fortify phase
            5. move_armies - Move armies after a successful attack
            6. trade_cards - Trade in cards for additional armies
            7. advance_phase - Advance to the next phase of the turn
            8. new_game - Start a new game
            9. get_reinforcement_armies - Get current reinforcement armies
            10. get_possible_actions - Get list of possible actions
            
            Always check the game state first to understand the current situation.
            Make strategic decisions based on the available actions and game state.
            When asked to play a turn, follow the proper Risk game phases: Reinforce -> Attack -> Fortify.
            """
        )
        
        # Add the MCP toolset to the agent
        self.agent.tools = [self.toolset]
        
        # Initialize services
        self.session_service = InMemorySessionService()
        self.artifacts_service = InMemoryArtifactService()
        
        # Create session
        self.session = await self.session_service.create_session(
            state={}, 
            app_name='risk_game_app', 
            user_id='risk_player'
        )
        
        # Create runner
        self.runner = Runner(
            app_name='risk_game_app',
            agent=self.agent,
            artifact_service=self.artifacts_service,
            session_service=self.session_service,
        )
        
        logger.info("Risk ADK Agent (HTTP) initialized successfully")
    
    async def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state"""
        query = "Get the current game state"
        content = types.Content(role='user', parts=[types.Part(text=query)])
        
        events_async = self.runner.run_async(
            session_id=self.session.id, 
            user_id=self.session.user_id, 
            new_message=content
        )
        
        result = None
        async for event in events_async:
            logger.info(f"Event: {type(event).__name__}")
            # Extract result from the event
            if hasattr(event, 'content') and event.content:
                result = event.content
            elif hasattr(event, 'text') and event.text:
                result = event.text
        
        return result
    
    async def play_turn(self, player_id: int) -> Dict[str, Any]:
        """Play a complete turn for the given player"""
        query = f"""
        You are playing Risk as Player {player_id}. 
        
        Please play your turn strategically:
        1. First, get the current game state
        2. Reinforce your territories with available armies
        3. Attack enemy territories if possible
        4. Fortify by moving armies between your connected territories
        5. Trade cards for bonus armies if you have 3+ cards
        6. Advance to the next phase when ready
        
        Make your moves one at a time and explain your strategy.
        """
        
        content = types.Content(role='user', parts=[types.Part(text=query)])
        
        events_async = self.runner.run_async(
            session_id=self.session.id, 
            user_id=self.session.user_id, 
            new_message=content
        )
        
        result = None
        async for event in events_async:
            logger.info(f"Event: {type(event).__name__}")
            if hasattr(event, 'content') and event.content:
                result = event.content
            elif hasattr(event, 'text') and event.text:
                result = event.text
        
        return {
            "player_id": player_id,
            "response": result,
            "session_id": self.session.id
        }
    
    async def make_specific_move(self, action: str, **kwargs) -> Dict[str, Any]:
        """Make a specific move using the appropriate tool"""
        query = f"Execute the {action} action with parameters: {kwargs}"
        content = types.Content(role='user', parts=[types.Part(text=query)])
        
        events_async = self.runner.run_async(
            session_id=self.session.id, 
            user_id=self.session.user_id, 
            new_message=content
        )
        
        result = None
        async for event in events_async:
            logger.info(f"Event: {type(event).__name__}")
            if hasattr(event, 'content') and event.content:
                result = event.content
            elif hasattr(event, 'text') and event.text:
                result = event.text
        
        return result
    
    async def close(self):
        """Clean up resources"""
        if self.toolset:
            await self.toolset.close()
        logger.info("Risk ADK Agent (HTTP) closed")

async def main():
    """Main function to test the Risk ADK agent over HTTP"""
    
    print("🤖 Risk Agent with Google ADK (HTTP)")
    print("====================================")
    
    # Create and initialize the agent
    # You can change the URL to point to your Cloud Run deployment
    agent = RiskADKAgentHTTP("RiskPlayer", mcp_server_url="https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/streamable-http")
    
    try:
        await agent.initialize()
        
        # Test getting game state
        print("\n📊 Getting game state...")
        try:
            game_state = await agent.get_game_state()
            print(f"✅ Game state: {game_state}")
        except Exception as e:
            print(f"❌ Error getting game state: {e}")
        
        # Test playing a turn
        print("\n🎮 Playing a turn...")
        try:
            turn_result = await agent.play_turn(player_id=0)
            print(f"✅ Turn result: {turn_result}")
        except Exception as e:
            print(f"❌ Error playing turn: {e}")
        
        # Test specific move
        print("\n⚔️ Making a specific move...")
        try:
            move_result = await agent.make_specific_move("new_game")
            print(f"✅ Move result: {move_result}")
        except Exception as e:
            print(f"❌ Error making move: {e}")
    
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
    
    finally:
        # Clean up
        await agent.close()
        print("\n✅ Agent test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 