#!/usr/bin/env python3
"""
Risk Agent using Google ADK with MCP Tools (HTTP Version)
Integrates with Risk MCP server using MCPToolset over HTTP
"""

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
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TaskState, TextPart, TaskStatusUpdateEvent, TaskStatus, Message, Role, Part
import uvicorn
import google.auth
from google.auth import default

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskADKAgentHTTP:
    
    
    def __init__(self, name: str = None, mcp_server_url: str = None):
        # Use environment variables with fallbacks
        self.name = name or os.environ.get('AGENT_NAME', 'RiskPlayer')
        self.mcp_server_url = mcp_server_url or os.environ.get('MCP_SERVER_URL', 'https://risk-mcp-server-jn3e4lhybq-ez.a.run.app/mcp/stream')
        self.agent = None
        self.toolset = None
        self.runner = None
        self.session_service = None
        self.session = None
        logger.info("RiskADKAgentHTTP instance created")
    
    async def initialize(self):
        """Initialize the agent with MCP tools over HTTP"""
        logger.info(f"[INIT] Initializing Risk ADK Agent with MCP server at {self.mcp_server_url}")
        
       
        # Create MCP toolset for Risk server using HTTP connection
        logger.info(f"[INIT] Creating MCP toolset with URL: {self.mcp_server_url}")
        self.toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=self.mcp_server_url,
                headers={"accept": "application/json, text/event-stream"},  # Required for both JSON and SSE
                timeout=30.0,  # 30 second timeout
                sse_read_timeout=30.0  # 30 second SSE read timeout
            )
        )
        logger.info(f"[INIT] MCP toolset created successfully")
        
        # Create the LLM agent
        model = Gemini(
            model=os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17'),
            use_vertex_ai=True,
            # Use global endpoint instead of region-specific
            location="global"
        )
        
        logger.info(f"Using Gemini model: {model.model}")
        
        self.agent = LlmAgent(
            model=model,
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
        
        logger.info("[INIT] Risk ADK Agent (HTTP) initialized successfully")
   
    
    async def play_turn(self, player_id: int) -> Dict[str, Any]:
        """Play a complete turn for the given player"""
        logger.info(f"[PLAY_TURN] Starting play_turn for player_id={player_id}")
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
        
        logger.info(f"[PLAY_TURN] About to run agent with session_id={self.session.id}")
        events_async = self.runner.run_async(
            session_id=self.session.id, 
            user_id=self.session.user_id, 
            new_message=content
        )
        
        result = None
        async for event in events_async:
            logger.info(f"[PLAY_TURN] Event received: {type(event).__name__}")
            if hasattr(event, 'content') and event.content:
                logger.info(f"[PLAY_TURN] Event content: {event.content}")
                result = event.content
            elif hasattr(event, 'text') and event.text:
                logger.info(f"[PLAY_TURN] Event text: {event.text}")
                result = event.text
        logger.info(f"[PLAY_TURN] Finished play_turn for player_id={player_id}, result={result}")
        return {
            "player_id": player_id,
            "response": result,
            "session_id": self.session.id
        }

    
    async def close(self):
        """Clean up resources"""
        logger.info("[CLOSE] Closing RiskADKAgentHTTP resources")
        if self.toolset:
            await self.toolset.close()
        logger.info("[CLOSE] Risk ADK Agent (HTTP) closed")

class PlayerAgentExecutor(AgentExecutor):
    def __init__(self):
        self.risk_agent = None
        logger.info("PlayerAgentExecutor initialized")
    
    async def execute(self, context, event_queue):
        logger.info(f"[EXECUTE] Called with context: {context}, event_queue: {event_queue}")
        # context.message.parts is a list, so we need to access the first part
        if context.message.parts and len(context.message.parts) > 0:
            logger.info(f"[EXECUTE] context.message.parts: {context.message.parts}")
            first_part = context.message.parts[0]  # Get the first part from the list
            user_message = first_part.root.text if hasattr(first_part.root, 'text') else None
            data = getattr(first_part.root, 'data', None)
        else:
            logger.warning("[EXECUTE] No message parts found in context")
            user_message = None
            data = None
            
        if user_message:
            logger.info(f"[EXECUTE] play turn with user_message: {user_message}")
            # Initialize the Risk agent if not already done
            if self.risk_agent is None:
                logger.info("[EXECUTE] Initializing RiskADKAgentHTTP instance")
                self.risk_agent = RiskADKAgentHTTP()
                await self.risk_agent.initialize()
            
            # Extract player_id from message (default to 1)
            player_id = 1
            if "player" in user_message.lower():
                import re
                match = re.search(r'player\s*(\d+)', user_message, re.IGNORECASE)
                if match:
                    player_id = int(match.group(1))
                    logger.info(f"[EXECUTE] Extracted player_id: {player_id}")
            
            # Execute the turn
            try:
                logger.info(f"[EXECUTE] Calling play_turn for player_id={player_id}")
                result = await self.risk_agent.play_turn(player_id)
                response = f"Executed turn for Player {player_id}. Result: {result.get('response', 'No response')}"
                logger.info(f"[EXECUTE] play_turn result: {result}")
            except Exception as e:
                logger.error(f"[EXECUTE] Error executing turn: {e}")
                response = f"Error executing turn: {str(e)}"
            
            # Send response message using enqueue_event
            logger.info(f"[EXECUTE] Sending response message: {response}")
            await event_queue.enqueue_event(Message(
                contextId=context.context_id,
                messageId=f"response-{context.task_id}",
                parts=[Part(root=TextPart(text=response))],
                role=Role.agent,
                taskId=context.task_id
            ))
            await event_queue.enqueue_event(TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(state=TaskState.completed),
                final=True
            ))
        else:
            logger.warning("[EXECUTE] user_message is None, input required")
            await event_queue.enqueue_event(TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(state=TaskState.input_required),
                final=False
            ))
    
    async def cancel(self, context, event_queue):
        """Cancel the current task"""
        logger.info(f"[CANCEL] Cancelling task {context.task_id}")
        await event_queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=context.task_id,
            contextId=context.context_id,
            status=TaskStatus(state=TaskState.cancelled),
            final=True
        ))

# --- Agent Card (metadata) ---
agent_card = AgentCard(
    name='Player Agent',
    description='Handles player actions for Risk game',
    url=os.environ.get('AGENT_CARD_URL', 'http://localhost:8000/'),  # Will be updated to Cloud Run URL after deployment
    version='1.0.0',
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id='play_turn',
            name='Play Turn',
            description='Plays a turn in the Risk game',
            tags=['risk', 'game', 'turn']
        ),
    ],
)

# --- Register executor and build app ---
agent_executor = PlayerAgentExecutor()
request_handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=InMemoryTaskStore()
)
a2a_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
)

# --- For ADK/Cloud Run deployment ---
root_agent = agent_executor

# --- Local dev entrypoint ---
def main():
    uvicorn.run(a2a_app.build(), host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main() 