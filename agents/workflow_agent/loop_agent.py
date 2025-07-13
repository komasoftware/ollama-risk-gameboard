import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from workflow_config import WorkflowAgentConfig
from risk_api import RiskAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("loop_agent")

class GameState(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class GameStatus:
    state: GameState
    current_player: Optional[int] = None
    game_id: Optional[str] = None
    error_message: Optional[str] = None

class GameStateChecker:
    """Sub-agent responsible for checking game state and determining if loop should continue"""
    
    def __init__(self, risk_api_client: RiskAPIClient):
        self.risk_api_client = risk_api_client
    
    async def check_game_state(self) -> GameStatus:
        """Check current game state and return status"""
        try:
            game_state = self.risk_api_client.get_game_state()
            if game_state is None:
                return GameStatus(state=GameState.ERROR, error_message="Could not fetch game state")
            
            # Parse game state to determine current status
            # This is a simplified implementation - would need to parse actual game state
            if game_state.get("game_over", False):
                return GameStatus(state=GameState.COMPLETED, game_id=game_state.get("game_id"))
            elif game_state.get("current_player"):
                return GameStatus(
                    state=GameState.PLAYING,
                    current_player=game_state.get("current_player"),
                    game_id=game_state.get("game_id")
                )
            else:
                return GameStatus(state=GameState.WAITING, game_id=game_state.get("game_id"))
                
        except Exception as e:
            logger.error(f"Error checking game state: {e}")
            return GameStatus(state=GameState.ERROR, error_message=str(e))

class PlayerTurnDispatcher:
    """Sub-agent responsible for dispatching turns to player agents"""
    
    def __init__(self, player_agent_urls: List[str]):
        self.player_agent_urls = player_agent_urls
    
    async def dispatch_turn(self, player_id: int, game_state: Dict[str, Any], turn_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a turn to the specified player agent with optional context from previous turns"""
        try:
            # Get the player agent URL for this player
            if player_id > len(self.player_agent_urls):
                raise ValueError(f"Player {player_id} not found in available agents")
            
            agent_card_url = self.player_agent_urls[player_id - 1]
            
            # For now, return a mock response with detailed strategy information
            # TODO: Implement actual A2A communication with contextual prompts
            logger.info(f"Dispatching turn to player {player_id} via {agent_card_url}")
            
            # Mock detailed turn result with strategy information
            mock_strategy = self._generate_mock_strategy(player_id, turn_context)
            
            return {
                "success": True,
                "player_id": player_id,
                "action": "mock_turn_action",
                "strategy": mock_strategy,
                "territories_attacked": ["Alaska", "Northwest Territory"],
                "territories_defended": ["Alberta"],
                "reinforcements_placed": 3,
                "cards_played": ["Infantry", "Cavalry"],
                "reasoning": f"Player {player_id} chose an aggressive strategy, focusing on expanding into North America",
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error dispatching turn to player {player_id}: {e}")
            return {
                "success": False,
                "player_id": player_id,
                "error": str(e)
            }
    
    def _generate_mock_strategy(self, player_id: int, turn_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock strategy information based on player and context"""
        strategies = {
            1: "aggressive",
            2: "defensive", 
            3: "balanced",
            4: "opportunistic",
            5: "cautious",
            6: "random"
        }
        
        strategy = strategies.get(player_id, "balanced")
        
        # Include context from previous turns if available
        context_summary = ""
        if turn_context and "previous_turns" in turn_context:
            context_summary = f"Based on previous turns: {turn_context['previous_turns']}"
        
        # Include contextual prompt if available
        contextual_prompt = ""
        if turn_context and "contextual_prompt" in turn_context:
            contextual_prompt = f"Contextual prompt received: {turn_context['contextual_prompt']}"
        
        return {
            "type": strategy,
            "description": f"Player {player_id} used {strategy} strategy",
            "context_considered": context_summary,
            "contextual_prompt_used": contextual_prompt,
            "key_decisions": [
                "Expanded into North America",
                "Built defensive positions in Alberta",
                "Collected cards for future bonus"
            ]
        }

class RiskLoopAgent:
    """Main LoopAgent that orchestrates Risk games"""
    
    def __init__(self, config: WorkflowAgentConfig):
        self.config = config
        self.risk_api_client = RiskAPIClient(base_url=config.risk_api_url)
        self.game_state_checker = GameStateChecker(self.risk_api_client)
        self.player_turn_dispatcher = PlayerTurnDispatcher(config.player_agent_urls)
        self.iteration_count = 0
        self.turn_history = []  # Track turn history for context
        self.game_summary = {}  # Track game summary for HostAgent
        
    async def start_game(self, num_players: int = 2) -> bool:
        """Start a new Risk game"""
        try:
            success = self.risk_api_client.new_game(num_players=num_players)
            if success:
                logger.info(f"Started new game with {num_players} players")
                self.iteration_count = 0
                self.turn_history = []  # Reset turn history
                self.game_summary = {
                    "num_players": num_players,
                    "start_time": asyncio.get_event_loop().time(),
                    "turns_completed": 0,
                    "player_strategies": {}
                }
            return success
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            return False
    
    def _create_turn_context(self, current_player: int) -> Dict[str, Any]:
        """Create contextual information for the current player's turn"""
        context = {
            "current_player": current_player,
            "turn_number": len(self.turn_history) + 1,
            "previous_turns": []
        }
        
        # Add recent turn history (last 3 turns for context)
        recent_turns = self.turn_history[-3:] if self.turn_history else []
        for turn in recent_turns:
            context["previous_turns"].append({
                "player": turn.get("player_id"),
                "strategy": turn.get("strategy", {}).get("type", "unknown"),
                "actions": {
                    "attacked": turn.get("territories_attacked", []),
                    "defended": turn.get("territories_defended", []),
                    "reinforcements": turn.get("reinforcements_placed", 0)
                },
                "reasoning": turn.get("reasoning", "")
            })
        
        return context
    
    def _update_game_summary(self, turn_result: Dict[str, Any]):
        """Update game summary with turn result information"""
        player_id = turn_result.get("player_id")
        if player_id:
            # Update player strategy tracking
            if "player_strategies" not in self.game_summary:
                self.game_summary["player_strategies"] = {}
            
            strategy = turn_result.get("strategy", {})
            self.game_summary["player_strategies"][player_id] = {
                "type": strategy.get("type", "unknown"),
                "description": strategy.get("description", ""),
                "key_decisions": strategy.get("key_decisions", [])
            }
            
            # Update turn count
            self.game_summary["turns_completed"] = len(self.turn_history)
            
            # Add turn to history
            self.turn_history.append(turn_result)
    
    async def run_game_loop(self) -> Dict[str, Any]:
        """Main game loop - runs until game is complete or max iterations reached"""
        logger.info("Starting game loop")
        
        while self.iteration_count < self.config.max_iterations:
            self.iteration_count += 1
            logger.info(f"Game loop iteration {self.iteration_count}")
            
            # Check game state
            game_status = await self.game_state_checker.check_game_state()
            
            if game_status.state == GameState.COMPLETED:
                logger.info("Game completed")
                return {
                    "status": "completed",
                    "game_id": game_status.game_id,
                    "iterations": self.iteration_count,
                    "game_summary": self.game_summary,
                    "turn_history": self.turn_history
                }
            
            elif game_status.state == GameState.ERROR:
                logger.error(f"Game error: {game_status.error_message}")
                return {
                    "status": "error",
                    "error": game_status.error_message,
                    "iterations": self.iteration_count
                }
            
            elif game_status.state == GameState.PLAYING and game_status.current_player:
                # Create contextual information for this turn
                turn_context = self._create_turn_context(game_status.current_player)
                
                # Dispatch turn to current player with context
                logger.info(f"Dispatching turn to player {game_status.current_player} with context")
                
                # Get current game state for the turn
                game_state = self.risk_api_client.get_game_state()
                turn_result = await self.player_turn_dispatcher.dispatch_turn(
                    game_status.current_player, 
                    game_state or {},
                    turn_context
                )
                
                if not turn_result.get("success"):
                    logger.error(f"Turn failed for player {game_status.current_player}")
                    return {
                        "status": "error",
                        "error": f"Turn failed: {turn_result.get('error')}",
                        "iterations": self.iteration_count
                    }
                
                # Update game summary with turn result
                self._update_game_summary(turn_result)
                
                # Wait a bit before next iteration
                await asyncio.sleep(1)
            
            else:
                # Game is waiting - just continue
                await asyncio.sleep(1)
        
        # Max iterations reached
        logger.warning(f"Max iterations ({self.config.max_iterations}) reached")
        return {
            "status": "max_iterations_reached",
            "iterations": self.iteration_count,
            "game_summary": self.game_summary,
            "turn_history": self.turn_history
        }
    
    async def play_single_turn(self) -> Dict[str, Any]:
        """Play a single turn and return the result with detailed information"""
        logger.info("Playing single turn")
        
        # Check current game state
        game_status = await self.game_state_checker.check_game_state()
        
        if game_status.state == GameState.COMPLETED:
            return {
                "status": "game_completed",
                "message": "Game is already completed",
                "game_summary": self.game_summary,
                "turn_history": self.turn_history
            }
        
        elif game_status.state == GameState.ERROR:
            return {
                "status": "error",
                "error": game_status.error_message
            }
        
        elif game_status.state == GameState.PLAYING and game_status.current_player:
            # Create contextual information for this turn
            turn_context = self._create_turn_context(game_status.current_player)
            
            # Get current game state for the turn
            game_state = self.risk_api_client.get_game_state()
            turn_result = await self.player_turn_dispatcher.dispatch_turn(
                game_status.current_player, 
                game_state or {},
                turn_context
            )
            
            # Update game summary with turn result
            self._update_game_summary(turn_result)
            
            return {
                "status": "turn_completed",
                "player_id": game_status.current_player,
                "turn_result": turn_result,
                "game_summary": self.game_summary,
                "turn_history": self.turn_history
            }
        
        else:
            return {
                "status": "waiting",
                "message": "Game is waiting for next turn"
            }
    
    async def play_single_turn_with_context(self, contextual_prompt: str, target_player: int = None) -> Dict[str, Any]:
        """Play a single turn with contextual prompt from HostAgent"""
        logger.info(f"Playing single turn with contextual prompt for player {target_player}")
        
        # Check current game state
        game_status = await self.game_state_checker.check_game_state()
        
        if game_status.state == GameState.COMPLETED:
            return {
                "status": "game_completed",
                "message": "Game is already completed",
                "game_summary": self.game_summary,
                "turn_history": self.turn_history
            }
        
        elif game_status.state == GameState.ERROR:
            return {
                "status": "error",
                "error": game_status.error_message
            }
        
        elif game_status.state == GameState.PLAYING and game_status.current_player:
            # Create contextual information for this turn
            turn_context = self._create_turn_context(game_status.current_player)
            
            # Add the contextual prompt to the turn context
            if contextual_prompt:
                turn_context["contextual_prompt"] = contextual_prompt
                turn_context["prompt_source"] = "host_agent"
            
            # Get current game state for the turn
            game_state = self.risk_api_client.get_game_state()
            turn_result = await self.player_turn_dispatcher.dispatch_turn(
                game_status.current_player, 
                game_state or {},
                turn_context
            )
            
            # Update game summary with turn result
            self._update_game_summary(turn_result)
            
            return {
                "status": "turn_completed",
                "player_id": game_status.current_player,
                "turn_result": turn_result,
                "contextual_prompt_used": contextual_prompt,
                "game_summary": self.game_summary,
                "turn_history": self.turn_history
            }
        
        else:
            return {
                "status": "waiting",
                "message": "Game is waiting for next turn"
            }
    
    async def close(self):
        """Clean up resources"""
        # The new risk_api client doesn't need explicit cleanup
        pass

# Factory function to create LoopAgent
async def create_loop_agent() -> RiskLoopAgent:
    """Create and return a configured LoopAgent"""
    config = WorkflowAgentConfig()
    return RiskLoopAgent(config) 