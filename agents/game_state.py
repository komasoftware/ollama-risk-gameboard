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

class ReinforceAction(BaseModel):
    territory: str
    max_armies: int

class AttackAction(BaseModel):
    from_: str = Field(..., alias='from')
    to: str
    max_dice: int

class MoveArmiesAction(BaseModel):
    from_: str = Field(..., alias='from')
    to: str
    max_armies: int

class TradeCardsAction(BaseModel):
    card_indices: List[int]

class EndPhaseAction(BaseModel):
    pass

class PossibleAction(BaseModel):
    Fortify: Optional[FortifyAction] = None
    Reinforce: Optional[ReinforceAction] = None
    Attack: Optional[AttackAction] = None
    MoveArmies: Optional[MoveArmiesAction] = None
    TradeCards: Optional[TradeCardsAction] = None
    EndPhase: Optional[EndPhaseAction] = None
    # Add other possible action types as needed

PossibleActionType = Union[PossibleAction, dict, str]

class GameState(BaseModel):
    current_player: str
    current_turn: int
    round: int
    turn_phase: str
    conquered_territory: bool
    reinforcement_armies: int
    initial_reinforcement_armies: int
    defeated_players: List[str]
    possible_actions: List[Union[PossibleAction, dict, str]]
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

    def get_current_player(self):
        """
        Returns the Player object for the current player.
        """
        current_name = self.game_state.current_player
        for player in self.game_state.players:
            if player.name == current_name:
                return player
        raise ValueError(f"Current player '{current_name}' not found in players list.")

    def get_current_player_id(self) -> int:
        """
        Returns the id of the current player by matching the current_player name to the players list.
        Raises ValueError if not found.
        """
        return self.get_current_player().id

    def get_current_player_name(self) -> str:
        """
        Returns the current player's name.
        """
        return self.get_current_player().name

    def get_current_player_territories(self) -> list:
        """
        Returns the list of territories for the current player.
        """
        return self.get_current_player().territories

    def get_current_player_territory_armies(self) -> dict:
        """
        Returns a dict {territory: army_count} for the current player.
        """
        player = self.get_current_player()
        return {territory: player.armies.get(territory, 0) for territory in player.territories}

    def get_possible_actions(self) -> list:
        """
        Returns the list of possible actions for the current turn, as provided by the backend (list of strings or single-key dicts).
        """
        return self.game_state.possible_actions

    def get_possible_actions_str(self) -> str:
        """
        Returns a readable, multi-line string describing all possible actions for the current turn.
        """
        actions = self.get_possible_actions()
        lines = []
        for action in actions:
            if isinstance(action, str):
                if action.lower() == "endphase":
                    lines.append("* End phase (finish your turn)")
                else:
                    lines.append(f"* {action}")
            elif isinstance(action, dict):
                key, value = next(iter(action.items()))
                k = key.lower()
                if k == "fortify":
                    lines.append(f"* Fortify: move armies from {value['from']} to {value['to']} (max {value['max_armies']})")
                elif k == "reinforce":
                    lines.append(f"* Reinforce: add up to {value['max_armies']} armies to {value['territory']}")
                elif k == "attack":
                    lines.append(f"* Attack: from {value['from']} to {value['to']} (max {value['max_armies']} armies, max dice: {value['max_dice']})")
                elif k == "movearmies":
                    lines.append(f"* Move armies: from {value['from']} to {value['to']} (max {value['max_armies']})")
                elif k == "tradecards":
                    lines.append(f"* Trade cards: indices {value['card_indices']}")
                elif k == "endphase":
                    lines.append("* End phase (finish your turn)")
                else:
                    lines.append(f"* {key}: {value}")
            else:
                lines.append(f"* Unknown action: {action}")
        return '\n'.join(lines)

    def get_adversaries_territories(self) -> dict:
        """
        Returns a dictionary mapping each adversary's player id to their territories and army counts.
        Example: {0: {"North Europe": 15, ...}, 2: {"North America": 1, ...}, ...}
        The current player is excluded.
        """
        current_id = self.get_current_player_id()
        adversaries = {}
        for player in self.game_state.players:
            if player.id != current_id:
                adversaries[player.id] = dict(player.armies)
        return adversaries

    def get_adversary_territory_armies(self, player_id: int) -> dict:
        """
        Returns a dict {territory: army_count} for the given adversary player_id.
        """
        for player in self.game_state.players:
            if player.id == player_id:
                return dict(player.armies)
        raise ValueError(f"Adversary with player_id {player_id} not found.")

    def get_current_turn_phase(self) -> str:
        """
        Returns the current turn phase (e.g., 'Reinforcement', 'Attack', etc.).
        """
        return self.game_state.turn_phase

    @staticmethod
    def format_territory_armies_str(territory_armies: dict) -> str:
        """
        Formats a dict {territory: army_count} into a readable, multi-line string for prompt inclusion.
        Example:
         * Ecuador: 5 armies
         * West-Europe: 1 army
        """
        lines = []
        for territory, n_armies in territory_armies.items():
            army_word = 'army' if n_armies == 1 else 'armies'
            lines.append(f"* {territory}: {n_armies} {army_word}")
        return '\n'.join(lines)

    def get_current_player_territories_str(self) -> str:
        """
        Returns the current player's territories as a readable, multi-line string for prompt inclusion.
        """
        territory_armies = self.get_current_player_territory_armies()
        return self.format_territory_armies_str(territory_armies)

    def get_adversaries_territories_str(self) -> str:
        """
        Returns all adversaries' territories as readable, multi-line strings for prompt inclusion.
        Each adversary is prefixed by their name and player id.
        """
        lines = []
        for player in self.game_state.players:
            if player.id == self.get_current_player_id():
                continue
            lines.append(f"{player.name} (player_id={player.id}):")
            lines.append(self.format_territory_armies_str(dict(player.armies)))
        return '\n'.join(lines)
    
    def get_current_game_round(self) -> int:
        """
        Returns the current game round.
        """
        return self.game_state.round
    