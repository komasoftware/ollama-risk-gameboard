#!/usr/bin/env python3
"""
Risk Agent using Google ADK with MCP Tools (HTTP Version)
Integrates with Risk MCP server using MCPToolset over HTTP
"""

import logging
import os
import time  # Add this at the top with other imports
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
from google.auth import default

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
# Suppress noisy third-party loggers
logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

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
        logger.debug("RiskADKAgentHTTP instance created")
    
    async def initialize(self):
        """Initialize the agent with MCP tools over HTTP"""
        logger.debug(f"Initializing Risk ADK Agent with MCP server at {self.mcp_server_url}")
        
       
        # Create MCP toolset for Risk server using HTTP connection
        logger.debug(f"Creating MCP toolset with URL: {self.mcp_server_url}")
        self.toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=self.mcp_server_url,
                headers={"accept": "application/json, text/event-stream"},  # Required for both JSON and SSE
                timeout=30.0,  # 30 second timeout
                sse_read_timeout=30.0  # 30 second SSE read timeout
            )
        )
        logger.debug("MCP toolset created successfully")
        
        # Create the LLM agent
        model = Gemini(
            model=os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17'),
            use_vertex_ai=True,
            # Use global endpoint instead of region-specific
            location="global"
        )
        
        logger.debug(f"Using Gemini model: {model.model}")
        
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
        
        logger.debug("Risk ADK Agent (HTTP) initialized successfully")
   
    
    async def play_turn(self, player_id: int, persona_description: str = None) -> Dict[str, Any]:
        """Play exactly one turn for the given player"""
        
        # Build persona-specific prompt
        persona_instruction = ""
        if persona_description:
            persona_instruction = f"""
            PERSONA: {persona_description}
            
            Play according to this persona. Your personality and strategy should reflect this description.
            """
        
        query = f"""
        You are playing Risk as Player {player_id}. 
        
        {persona_instruction}
        
        CRITICAL INSTRUCTIONS:
        - Play all phases of the player's turn and then STOP
        - Check the possible actions for each phase by getting the game state and play them one at a time
        - Check the game state after each action to see if you can do more actions and if it's still your turn
        - Always decide on the next action based on the game state and the possible actions
        - Do NOT wait for other players or future turns
        - Do NOT continue playing after completing your turn
        - If it's not your turn, simply state that and stop
        
        TURN EXECUTION:
        1. First, get the current game state
        2. Check if it's your turn (current_player should match Player {player_id})
        3. If it's your turn, play through the phases: Reinforce → Attack → Fortify or other possible actions
        4. Reason about your strategy and explain your actions
        5. If it's NOT your turn, explain why and stop immediately
        6. After completing your turn, stop and provide a summary of your strategy
        
        Make your moves one at a time and explain your reasoning.
        STOP after completing your turn - do not continue.
        """
        
        content = types.Content(role='user', parts=[types.Part(text=query)])
        
        logger.warning("Gemini model call started")
        start = time.monotonic()
        events_async = self.runner.run_async(
            session_id=self.session.id, 
            user_id=self.session.user_id, 
            new_message=content
        )
        result = None
        tool_calls = 0
        async for event in events_async:
            # Log only tool calls and their results
            if hasattr(event, 'tool_calls') and event.tool_calls:
                tool_calls += len(event.tool_calls)
                logger.warning(f"LLM Tool Calls: {event.tool_calls}")
            elif hasattr(event, 'tool_results') and event.tool_results:
                logger.debug(f"LLM Tool Results: {event.tool_results}")
            elif hasattr(event, 'content') and event.content:
                result = event.content
                logger.warning(f"LLM Final Response: {event.content}")
            elif hasattr(event, 'text') and event.text:
                result = event.text
                logger.warning(f"LLM Final Response: {event.text}")
        elapsed = time.monotonic() - start
        logger.warning(f"Gemini model call finished in {elapsed:.2f} seconds with {tool_calls} tool calls")
        return {
            "player_id": player_id,
            "response": result,
            "session_id": self.session.id
        }

    
    async def close(self):
        """Clean up resources"""
        logger.debug("[CLOSE] Closing RiskADKAgentHTTP resources")
        if self.toolset:
            await self.toolset.close()
        logger.debug("[CLOSE] Risk ADK Agent (HTTP) closed")

class PlayerAgentExecutor(AgentExecutor):
    def __init__(self):
        self.risk_agent = None
        logger.debug("PlayerAgentExecutor initialized")
    
    async def execute(self, context, event_queue):
        logger.debug(f"Execute called for task {context.task_id}")

        # Extract message content using proper A2A protocol approach
        user_message = None
        player_id = None  # Will be extracted from DataPart
        persona_description = None
        
        if context.message.parts:
            
            # Iterate through all message parts to find text and data
            for part in context.message.parts:
                # Handle TextPart for user message
                if hasattr(part.root, 'type') and part.root.type == 'text':
                    if hasattr(part.root, 'text'):
                        user_message = part.root.text
                
                # Handle DataPart for structured parameters
                elif hasattr(part.root, 'type') and part.root.type == 'data':
                    if hasattr(part.root, 'data') and isinstance(part.root.data, dict):
                        data = part.root.data
                        
                        # Extract structured parameters
                        if 'player_id' in data:
                            player_id = int(data['player_id'])
                        
                        if 'persona' in data:
                            persona_description = data['persona']
                
                # Also check if it's a DataPart by kind attribute
                elif hasattr(part.root, 'kind') and part.root.kind == 'data':
                    if hasattr(part.root, 'data') and isinstance(part.root.data, dict):
                        data = part.root.data
                        
                        # Extract structured parameters
                        if 'player_id' in data:
                            player_id = int(data['player_id'])
                        
                        if 'persona' in data:
                            persona_description = data['persona']
                
                # Fallback: try to get text from any part (for backward compatibility)
                elif hasattr(part.root, 'text') and not user_message:
                    user_message = part.root.text
        else:
            logger.warning("No message parts found in context")
            
        if user_message and player_id is not None:
            # Initialize the Risk agent if not already done
            if self.risk_agent is None:
                self.risk_agent = RiskADKAgentHTTP()
                await self.risk_agent.initialize()
            
            # Execute the turn
            try:
                result = await self.risk_agent.play_turn(player_id, persona_description)
                response = f"Executed turn for Player {player_id}. Persona: {persona_description or 'Default'}. Result: {result.get('response', 'No response')}"
            except Exception as e:
                logger.error(f"Error executing turn: {e}")
                response = f"Error executing turn: {str(e)}"
            
            # Send response message using enqueue_event
            logger.debug(f"Sending response message for task {context.task_id}")
            response_message = Message(
                contextId=context.context_id,
                messageId=f"response-{context.task_id}",
                parts=[Part(root=TextPart(text=response))],
                role=Role.agent,
                taskId=context.task_id
            )
            await event_queue.enqueue_event(response_message)
            logger.debug(f"Response message sent successfully")
            
            # Send task completion event
            logger.debug(f"Sending task completion event for task {context.task_id}")
            completion_event = TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(state=TaskState.completed),
                final=True
            )
            await event_queue.enqueue_event(completion_event)
            logger.debug(f"Task completion event sent successfully")
        elif user_message is None:
            logger.warning("user_message is None, input required")
            await event_queue.enqueue_event(TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(state=TaskState.input_required),
                final=False
            ))
        elif player_id is None:
            logger.warning("player_id is missing from request")
            await event_queue.enqueue_event(TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(state=TaskState.input_required),
                final=False
            ))
    
    async def cancel(self, context, event_queue):
        """Cancel the current task"""
        logger.debug(f"Cancelling task {context.task_id}")
        await event_queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=context.task_id,
            contextId=context.context_id,
            status=TaskStatus(state=TaskState.cancelled),
            final=True
        ))

# --- Agent Card (metadata) ---
agent_card = AgentCard(
    name='Risk Player Agent',
    description='AI agent for playing Risk board game turns with customizable personas',
    url=os.environ.get('AGENT_CARD_URL', 'http://localhost:8080/'),
    version='1.0.0',
    defaultInputModes=['text', 'data'],
    defaultOutputModes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id='play_turn',
            name='Play Turn',
            description='Plays a single turn in the Risk game for a specific player with a given persona',
            inputModes=['text', 'data'],
            outputModes=['text'],
            tags=['risk', 'game', 'turn', 'strategy'],
            streaming=True,
            parameters={
                'player_id': {
                    'type': 'integer',
                    'description': 'The player ID (1, 2, or 3) for whom to play the turn',
                    'required': True
                },
                'persona': {
                    'type': 'string',
                    'description': 'Description of the player persona/strategy (e.g., "aggressive", "defensive", "balanced")',
                    'required': False
                }
            }
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