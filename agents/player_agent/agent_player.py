#!/usr/bin/env python3
"""
Risk Agent using A2A Protocol with Google Agent SDK
Integrates A2A for agent communication and Google Agent SDK for LLM + MCP tools
"""

import logging
import os
import time
from typing import Dict, Any
import uvicorn

# Google Agent SDK imports
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.models import Gemini
from google.genai import types

# A2A imports
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TaskState, TextPart, TaskStatusUpdateEvent, TaskStatus, Message, Role, Part

# Set up logging
log_level = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)
logger.info(f"Starting Risk Player Agent with log level: {log_level}")

class PlayerAgentExecutor(AgentExecutor):
    def __init__(self):
        # Configuration
        self.mcp_server_url = os.environ.get('MCP_SERVER_URL', 'https://risk-mcp-server-jn3e4lhybq-ez.a.run.app/mcp/stream')
        self.llm_model = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')
        self.project_id = os.environ.get('PROJECT_ID', 'your-project-id-here')
        self.region = os.environ.get('REGION', 'us-central1')
        self.location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'global')
        
        # Google Agent SDK components
        self._initialize_google_agent_sdk()
        
        logger.debug("PlayerAgentExecutor initialized with Google Agent SDK")
    
    def _initialize_google_agent_sdk(self):
        """Initialize Google Agent SDK components"""
        # MCP Tool Integration
        self.toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=self.mcp_server_url,
                headers={"accept": "application/json, text/event-stream"},
                timeout=30.0,
                sse_read_timeout=30.0
            )
        )
        
        # LLM Agent with Tools
        model = Gemini(
            model=self.llm_model,
            vertexai=True,
            location=self.location,
            project_id=self.project_id
        )
        
        self.agent = LlmAgent(
            model=model,
            name="RiskPlayer",
            instruction="""
            You are a Risk game player agent. You can use the following MCP tools:
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
            After completing your turn, explain your strategy for future reference.
            """
        )
        
        # Add the MCP toolset to the agent
        self.agent.tools = [self.toolset]
        
        # Session and Artifact Management
        self.session_service = InMemorySessionService()
        self.artifacts_service = InMemoryArtifactService()
        
        # Runner for orchestration
        self.runner = Runner(
            app_name='risk_game_app',
            agent=self.agent,
            artifact_service=self.artifacts_service,
            session_service=self.session_service,
        )
    
    async def execute(self, context, event_queue):
        """A2A protocol entry point - handles the actual game logic"""
        logger.info(f"Execute called for task {context.task_id}")
        logger.info(f"Context message: {context.message}")
        logger.info(f"Context message parts: {context.message.parts if context.message.parts else 'None'}")

        # Extract A2A message parameters
        player_id = None
        persona = None
        session_id = None
        
        if context.message.parts:
            for part in context.message.parts:
                logger.info(f"Processing part: {part}")
                logger.info(f"Part root: {part.root}")
                logger.info(f"Part root type: {type(part.root)}")
                
                # Check if this is a DataPart
                if hasattr(part.root, 'kind') and part.root.kind == 'data':
                    if hasattr(part.root, 'data') and isinstance(part.root.data, dict):
                        data = part.root.data
                        logger.info(f"Found data part with data: {data}")
                        if 'player_id' in data:
                            player_id = int(data['player_id'])
                            logger.info(f"Extracted player_id: {player_id}")
                        if 'persona' in data:
                            persona = data['persona']
                            logger.info(f"Extracted persona: {persona}")
                        if 'session_id' in data:
                            session_id = data['session_id']
                            logger.info(f"Extracted session_id: {session_id}")
        
        if player_id is None:
            logger.error("player_id is required")
            await self._send_error(event_queue, context, "player_id is required")
            return
        
        logger.info(f"Starting turn execution for Player {player_id} with persona: {persona}")
        
        try:
            # Play turn using Google Agent SDK with Vertex AI
            logger.info("Calling _play_turn method with Google Agent SDK...")
            result = await self._play_turn(player_id, persona, session_id)
            logger.info(f"_play_turn completed with result: {result}")
            
            # Send A2A response
            response = f"Executed turn for Player {player_id}. Session: {result.get('session_id', 'N/A')}. Result: {result.get('result', 'No result')}"
            logger.info(f"Sending response: {response}")
            await self._send_response(event_queue, context, response)
            
        except Exception as e:
            logger.error(f"Error executing turn: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._send_error(event_queue, context, str(e))
    
    async def _play_turn(self, player_id: int, persona: str = None, session_id: str = None):
        """Play a complete turn using Google Agent SDK with session management"""
        
        # Get or create session
        session = None
        if session_id:
            try:
                session = await self.session_service.get_session(session_id)
            except:
                session = None
        
        if not session:
            session = await self.session_service.create_session(
                state={'player_id': player_id, 'persona': persona},
                app_name='risk_game_app',
                user_id=f'player_{player_id}'
            )
        
        # Get strategy artifacts from previous turns
        try:
            strategy_artifact = await self.artifacts_service.get_artifact(
                session.id, 'strategy_history'
            )
            previous_strategy = strategy_artifact.data if strategy_artifact else ""
        except:
            previous_strategy = ""
        
        # Build context-aware prompt
        prompt = f"""
        You are Player {player_id} playing Risk.
        PERSONA: {persona or 'Balanced'}
        
        PREVIOUS STRATEGY: {previous_strategy}
        
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
        
        # Execute turn using Google Agent SDK
        content = types.Content(role='user', parts=[types.Part(text=prompt)])
        
        logger.warning("Google Agent SDK turn execution started")
        start_time = time.monotonic()
        
        events_async = self.runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content
        )
        
        # Collect results
        turn_result = ""
        tool_calls = 0
        async for event in events_async:
            if hasattr(event, 'tool_calls') and event.tool_calls:
                tool_calls += len(event.tool_calls)
                logger.warning(f"Tool Calls: {event.tool_calls}")
            elif hasattr(event, 'content') and event.content:
                turn_result = event.content
                logger.warning(f"Final Response: {event.content}")
            elif hasattr(event, 'text') and event.text:
                turn_result = event.text
                logger.warning(f"Final Response: {event.text}")
        
        elapsed = time.monotonic() - start_time
        logger.warning(f"Google Agent SDK turn execution finished in {elapsed:.2f}s with {tool_calls} tool calls")
        
        # Store strategy artifact for next turn
        try:
            await self.artifacts_service.create_artifact(
                session.id,
                'strategy_history',
                f"{previous_strategy}\nTurn {player_id}: {turn_result}"
            )
        except Exception as e:
            logger.warning(f"Failed to store strategy artifact: {e}")
        
        return {
            "player_id": player_id,
            "session_id": session.id,
            "result": turn_result,
            "tool_calls": tool_calls
        }
    
    async def _send_response(self, event_queue, context, response):
        """Send A2A response"""
        response_message = Message(
            contextId=context.context_id,
            messageId=f"response-{context.task_id}",
            parts=[Part(root=TextPart(text=response))],
            role=Role.agent,
            taskId=context.task_id
        )
        await event_queue.enqueue_event(response_message)
        logger.debug(f"Response message sent successfully")
        
        # Send task completion
        completion_event = TaskStatusUpdateEvent(
            taskId=context.task_id,
            contextId=context.context_id,
            status=TaskStatus(state=TaskState.completed),
            final=True
        )
        await event_queue.enqueue_event(completion_event)
        logger.debug(f"Task completion event sent successfully")
    
    async def _send_error(self, event_queue, context, error_msg):
        """Send A2A error response"""
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
    
    async def close(self):
        """Clean up resources"""
        logger.debug("Closing PlayerAgentExecutor resources")
        if hasattr(self, 'toolset'):
            await self.toolset.close()

# --- Agent Card (metadata) ---
agent_card = AgentCard(
    name='Risk Player Agent',
    description='AI agent for playing Risk board game turns with session management and strategy artifacts',
    url=os.environ.get('AGENT_CARD_URL', 'http://localhost:8080/'),
    version='1.0.0',
    defaultInputModes=['text', 'data'],
    defaultOutputModes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id='play_turn',
            name='Play Turn',
            description='Plays a single turn in the Risk game with session management and strategy artifacts',
            inputModes=['text', 'data'],
            outputModes=['text'],
            tags=['risk', 'game', 'turn', 'strategy', 'session'],
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
                },
                'session_id': {
                    'type': 'string',
                    'description': 'Session ID for multi-turn games (optional)',
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

# --- Local dev entrypoint ---
def main():
    uvicorn.run(a2a_app.build(), host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main() 