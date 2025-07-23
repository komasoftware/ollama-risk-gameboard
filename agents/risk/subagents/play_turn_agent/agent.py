import datetime
import os
from typing import ClassVar, Optional

from google.adk.agents import Agent
from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.events import Event, EventActions

from google.adk.tools.tool_context import ToolContext
from risk_api import RiskAPIClient
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing import AsyncGenerator
from risk.subagents.play_reinforcement_move_agent.agent import play_reinforcement_move_agent

class TurnCompleteChecker(BaseAgent):
    previous_player_id: ClassVar[Optional[str]] = None

    async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
        # Fetch the current player ID from session state
        # current_player = context.session.state.get("game_state", {}).get("current_player", None)

        # # Default to False if no current_player_id found
        # should_stop = False
        
        # if current_player is not None:
        #     # Compare current_player_id with previous_player_id
        #     if self.previous_player_id == current_player_id:
        #         should_stop = True  # Stop if IDs match
            
        #     # Update previous_player_id for the next check
        #     self.previous_player_id = current_player_id

        # Yield event to escalate loop exit if should_stop is True
        # yield Event(author=self.name, actions=EventActions(escalate=should_stop))

        yield Event(turn_complete=True, author=self.name, actions=EventActions(escalate=True))

# Create the Refinement Loop Agent
play_turn_agent = LoopAgent(
    name="play_turn_agent",
    max_iterations=2,
    sub_agents=[
        play_reinforcement_move_agent,
        TurnCompleteChecker(name="turn_complete_checker"),
    ],
    description="You are responsible for playing a turn in the game of Risk.",
)

