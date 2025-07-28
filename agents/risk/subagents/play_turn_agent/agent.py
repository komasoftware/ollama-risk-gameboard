import datetime
import os
import risk.subagents.play_turn_agent.agent
from typing import ClassVar, Optional

from google.adk.agents import Agent
from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.events import Event, EventActions

from google.adk.tools.tool_context import ToolContext
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing import AsyncGenerator
from risk.subagents.play_reinforcement_move_agent.agent import (
    play_reinforcement_move_agent,
)
from game_state import GameStateRoot
from risk.subagents.play_attack_move_agent.agent import play_attack_move_agent
from google.genai import types


class PhaseCompleteChecker(BaseAgent):
    phase: str
    player_id: int = None
    name: str

    def __init__(self, phase):
        super().__init__(phase=phase, name=f"{phase}_phase_complete_checker")

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        gamestate: GameStateRoot = context.session.state.get("game_state")

        phase_ongoing = gamestate.get_current_turn_phase().lower() == self.phase.lower()

        if self.player_id is None:
            self.player_id = gamestate.get_current_player_id()
            player_ongoing = True
        elif self.player_id != gamestate.get_current_player_id():
            player_ongoing = False
        else:
            player_ongoing = True

        if self.player_id is None:
            eventText = f"The {self.phase} phase has started."
        if not player_ongoing:
            eventText = f"Your turn is completed ! Exit the loop."
        elif phase_ongoing:
            eventText = f"The {self.phase} phase is still ongoing. Pick your next action."
        else:
            eventText = f"The {self.phase} phase is complete. Exit the loop."


        print(f"*** {self.name}: Event: {eventText} ***")

        # yield Event(
        #     author=self.name,
        #     actions=EventActions(escalate=False),
        #     content=eventText,
        # )
        yield Event(
            turn_complete=True,
            author=self.name,
            actions=EventActions(escalate=not phase_ongoing),
            content=types.Content(parts=[types.Part(text=eventText)])
        )


play_reinforcement_phase_agent = LoopAgent(
    name="play_reinforcement_phase_agent",
    max_iterations=10,
    sub_agents=[
        PhaseCompleteChecker(phase="Reinforce"),
        play_reinforcement_move_agent,
    ],
    description="Capable of playing all the moves of the reinforcement phase of a turn in the game of Risk.",
)

play_attack_phase_agent = LoopAgent(
    name="play_attack_phase_agent",
    max_iterations=25,
    sub_agents=[
        PhaseCompleteChecker(phase="Attack"),
        play_attack_move_agent,
    ],
    description="Capable of playing all the moves of the attack phase of a turn in the game of Risk.",
)

play_turn_agent = SequentialAgent(
    name="play_turn_agent",
    sub_agents=[
        play_reinforcement_phase_agent,
        play_attack_phase_agent,
    ],
    description="Capable of playing a turn during a game of Risk.",
)
