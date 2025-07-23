from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field

class Territory(BaseModel):
    name: str
    continent: str
    adjacent_territories: List[str]

class Continent(BaseModel):
    name: str
    bonus_armies: int
    territories: List[str]

class Board(BaseModel):
    territories: Dict[str, Territory]
    continents: Dict[str, Continent]

class Player(BaseModel):
    id: int
    name: str
    territories: List[str]
    armies: Dict[str, int]
    cards: List  # Could be List[str] if cards are always strings
    army_supply: int
    total_armies: int

class FortifyAction(BaseModel):
    from_: str = Field(..., alias='from')
    to: str
    max_armies: int

class PossibleAction(BaseModel):
    Fortify: Optional[FortifyAction] = None
    # Add other possible action types as needed

PossibleActionType = Union[PossibleAction, str]

class GameState(BaseModel):
    current_player: str
    current_turn: int
    round: int
    turn_phase: str
    conquered_territory: bool
    reinforcement_armies: int
    initial_reinforcement_armies: int
    defeated_players: List[str]
    possible_actions: List[Union[PossibleAction, str]]
    players: List[Player]
    board: Board
    conquer_probs: List[List[Union[str, float]]]  # Or use a custom model/validator

class GameStateRoot(BaseModel):
    game_state: GameState
    error: Optional[str]

    @classmethod
    def from_risk_api_response(cls, response: dict) -> "GameStateRoot":
        """
        Instantiate GameStateRoot from a Risk API response dict.
        Handles nested model conversion as needed.
        """
        return cls.model_validate(response)