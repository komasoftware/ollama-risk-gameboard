"""
Game Orchestrator for managing AI agents playing Risk.
Coordinates multiple agents and manages game flow.
"""

import asyncio
import time
import re
import logging
from typing import List, Dict, Optional, Any
from .risk_api import RiskAPIClient, GameState, GamePhase
from datetime import datetime

# Configure logging to write to file only, not terminal
def setup_logging():
    """Setup logging to write to file only."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"risk_game_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add file handler to logger
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

class GameOrchestrator:
    """Orchestrates games between multiple AI agents."""
    
    def __init__(self, agents: List[Any], max_turns: int = 100, turn_timeout: int = 60, game_config_summary: dict = None):
        self.agents = agents
        self.max_turns = max_turns
        self.turn_timeout = turn_timeout
        self.risk_client = RiskAPIClient()
        self.game_log = []
        self.game_config_summary = game_config_summary or {}
    
    async def start_game(self) -> Dict[str, Any]:
        self.game_log = []
        self.risk_client = RiskAPIClient()
        print(f"\n{'🎮'*20} GAME START {'🎮'*20}")
        print(f"Starting new game with {len(self.agents)} agents:")
        for agent in self.agents:
            print(f"  - {agent.get_strategy_description()}")
        if self.game_config_summary:
            logger.info(f"Game config summary: {self.game_config_summary}")
        turn_counter = 0
        while True:
            # Always fetch fresh state from server
            game_state = self.risk_client.get_game_state()
            if game_state.game_over:
                break
            
            current_agent = self._get_agent_for_player(game_state.current_player)
            if not current_agent:
                logger.error(f"No agent found for player {game_state.current_player}")
                break
            
            logger.info(f"Player {current_agent.name} turn {turn_counter}, phase: {game_state.phase.value}")
            
            # Handle the current phase based on what the server tells us
            if game_state.phase == GamePhase.REINFORCE:
                await self._handle_reinforce_phase(current_agent)
            elif game_state.phase == GamePhase.ATTACK:
                await self._handle_attack_phase(current_agent)
            elif game_state.phase == GamePhase.FORTIFY:
                await self._handle_fortify_phase(current_agent)
            elif game_state.phase == GamePhase.MOVE_ARMIES:
                await self._handle_move_armies_phase(current_agent)
            else:
                logger.warning(f"Unknown phase: {game_state.phase.value}. Advancing phase.")
                self.risk_client.advance_phase()
            
            # Check if player changed (turn ended)
            new_game_state = self.risk_client.get_game_state()
            if new_game_state.current_player != game_state.current_player:
                turn_counter += 1
        
        logger.info("Game over!")
        return self._summarize_game(self.risk_client.get_game_state())

    async def _handle_reinforce_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        my_player = game_state.players.get(agent.name)
        if not my_player:
            logger.info(f"Player {agent.name} not found in game state. Skipping.")
            return
        
        # Get fresh reinforcement armies from server - NEVER use my_player.armies
        armies_before = self.risk_client.get_reinforcement_armies()
        logger.info(f"[DEBUG] {agent.name} reinforcement armies: {armies_before}, territories: {my_player.territories}")
        
        if not my_player.territories:
            logger.info(f"Player {agent.name} has no territories and is eliminated. Skipping turn.")
            return
        
        if armies_before == 0:
            logger.info(f"Player {agent.name} has no armies to reinforce.")
            return
        
        logger.info(f"{agent.name} planning and executing reinforcements...")
        
        from agents.risk_rules import get_valid_reinforce_actions
        valid_reinforce = get_valid_reinforce_actions(game_state, my_player, self.risk_client)
        valid_territories = [action['territory'] for action in valid_reinforce]
        logger.info(f"Valid reinforce territories for {agent.name}: {valid_territories}")
        
        if not valid_territories:
            logger.info(f"No valid reinforce actions for {agent.name}.")
            return
        
        # Let the agent place armies until no more armies are available
        while True:
            # Check if we still have armies to place
            current_armies = self.risk_client.get_reinforcement_armies()
            if current_armies == 0:
                logger.info(f"{agent.name} has no more armies to place.")
                break
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            logger.info(f"{agent.name} reinforce action: {result}")
            
            # Get fresh reinforcement armies from server after the action
            armies_after = self.risk_client.get_reinforcement_armies()
            logger.info(f"[DEBUG] {agent.name} reinforcement armies before: {current_armies}, after: {armies_after}")
            
            # If armies didn't change, the action failed or we're done
            if armies_after == current_armies:
                logger.info(f"{agent.name} reinforcement armies didn't change after reinforce action.")
                break

    async def _handle_attack_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        my_player = game_state.players.get(agent.name)
        if not my_player:
            logger.info(f"Player {agent.name} not found in game state. Skipping.")
            return
        
        logger.info(f"{agent.name} planning and executing attacks...")
        
        # Let the agent make attacks until no more valid attacks are available
        while True:
            from agents.risk_rules import get_valid_attack_actions
            valid_attacks = get_valid_attack_actions(game_state, my_player)
            
            if not valid_attacks:
                logger.info(f"{agent.name} has no more valid attack actions. Advancing to next phase.")
                self.risk_client.advance_phase()
                break
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            logger.info(f"{agent.name} attack action: {result}")
            
            # Get fresh game state after the attack
            game_state = self.risk_client.get_game_state()
            my_player = game_state.players.get(agent.name)
            if not my_player:
                logger.info(f"Player {agent.name} not found in game state after attack.")
                break

    async def _handle_fortify_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        my_player = game_state.players.get(agent.name)
        if not my_player:
            logger.info(f"Player {agent.name} not found in game state. Skipping.")
            return
        
        logger.info(f"{agent.name} planning and executing fortifications...")
        
        # Let the agent make fortify moves until no more valid moves are available
        while True:
            from agents.risk_rules import get_valid_fortify_actions
            valid_fortifies = get_valid_fortify_actions(game_state, my_player)
            
            if not valid_fortifies:
                logger.info(f"{agent.name} has no more valid fortify actions. Advancing to next phase.")
                self.risk_client.advance_phase()
                break
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            logger.info(f"{agent.name} fortify action: {result}")
            
            # Get fresh game state after the fortify
            game_state = self.risk_client.get_game_state()
            my_player = game_state.players.get(agent.name)
            if not my_player:
                logger.info(f"Player {agent.name} not found in game state after fortify.")
                break

    async def _handle_move_armies_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        my_player = game_state.players.get(agent.name)
        if not my_player:
            logger.info(f"Player {agent.name} not found in game state. Skipping.")
            return
        
        logger.info(f"{agent.name} planning and executing army movements after attack...")
        
        # Let the agent move armies until no more valid moves are available
        while True:
            from agents.risk_rules import get_valid_move_armies_actions
            valid_moves = get_valid_move_armies_actions(game_state, my_player)
            
            if not valid_moves:
                logger.info(f"{agent.name} has no more valid move armies actions. Advancing to next phase.")
                self.risk_client.advance_phase()
                break
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            logger.info(f"{agent.name} move armies action: {result}")
            
            # Get fresh game state after the move
            game_state = self.risk_client.get_game_state()
            my_player = game_state.players.get(agent.name)
            if not my_player:
                logger.info(f"Player {agent.name} not found in game state after move armies.")
                break

    async def _handle_generic_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        try:
            logger.info(f"Player {agent.name} in {game_state.phase.value} phase, getting decision")
            result = await asyncio.wait_for(
                agent.take_turn(None),
                timeout=self.turn_timeout
            )
            print(f"Action from {agent.name}: {result}")
            logger.info(f"Player {agent.name} action: {result}")
            self.game_log.append({ "turn": game_state.current_turn, "player": agent.name, "phase": game_state.phase.value, "result": result })
        except asyncio.TimeoutError:
            print(f"⌛️ Timeout: {agent.name} took too long. Advancing phase to prevent stall.")
            logger.warning(f"Player {agent.name} timed out in {game_state.phase.value} phase, advancing")
            self.risk_client.advance_phase()

    def _find_agent(self, player_name: str) -> Optional[Any]:
        """Find an agent by player name."""
        for agent in self.agents:
            if agent.name == player_name:
                return agent
        return None
    
    def _create_game_result(self, final_state: GameState) -> Dict[str, Any]:
        """Create a game result summary."""
        return {
            "winner": final_state.winner,
            "total_turns": final_state.current_turn,
            "game_over": final_state.game_over,
            "final_state": {
                "players": {name: {
                    "territories": len(player.territories),
                    "armies": player.armies
                } for name, player in final_state.players.items()},
                "phase": final_state.phase.value
            },
            "game_log": self.game_log
        }
    
    def print_game_summary(self, result: Dict[str, Any]):
        """Print a summary of the game results."""
        print(f"\n{'📊'*25} GAME SUMMARY {'📊'*25}")
        print(f"🏆 Winner: {result['winner']}")
        print(f"🔄 Total turns: {result['total_turns']}")
        print(f"🎯 Game over: {result['game_over']}")
        
        print(f"\n📈 Final player states:")
        for player_name, state in result['final_state']['players'].items():
            print(f"  🏰 {player_name}: {state['territories']} territories, {state['armies']} armies")
        
        print(f"\n📋 Final phase: {result['final_state']['phase']}")
        print(f"{'📊'*25} GAME SUMMARY {'📊'*25}")

    def _advance_phase_until_phase_changes(self, old_phase, player_name, max_retries=5):
        """Advance phase until the phase or player changes, with retries."""
        for attempt in range(max_retries):
            self.risk_client.advance_phase()
            new_state = self.risk_client.get_game_state()
            if new_state.phase != old_phase or new_state.current_player != player_name:
                return new_state
            logger.warning(f"Phase did not advance from {old_phase.value} for player {player_name}, retry {attempt+1}/{max_retries}")
            time.sleep(0.5)
        raise RuntimeError(f"Failed to advance phase from {old_phase.value} for player {player_name} after {max_retries} attempts")

    def _advance_phase_until_player_changes(self, old_state, max_retries=5):
        """Advance phase until the player changes, with retries."""
        for attempt in range(max_retries):
            self.risk_client.advance_phase()
            new_state = self.risk_client.get_game_state()
            if new_state.current_player != old_state.current_player:
                return new_state
            logger.warning(f"Player did not change from {old_state.current_player}, retry {attempt+1}/{max_retries}")
            time.sleep(0.5)
        raise RuntimeError(f"Failed to advance to next player from {old_state.current_player} after {max_retries} attempts")

    def _get_agent_for_player(self, player_name: str) -> Optional[Any]:
        """Find an agent by player name."""
        for agent in self.agents:
            if agent.name == player_name:
                return agent
        return None

    def _summarize_game(self, final_state: GameState) -> Dict[str, Any]:
        """Summarize the game results."""
        result = self._create_game_result(final_state)
        self.print_game_summary(result)
        return result

async def run_single_game(agents: List[Any], game_config_summary: dict = None) -> Dict[str, Any]:
    """Run a single game with the given agents and config summary."""
    orchestrator = GameOrchestrator(agents, game_config_summary=game_config_summary)
    result = await orchestrator.start_game()
    orchestrator.print_game_summary(result)
    return result


async def run_tournament(agents: List[Any], games_per_matchup: int = 1) -> Dict[str, Any]:
    """Run a tournament between agents."""
    print(f"Starting tournament with {len(agents)} agents, {games_per_matchup} games per matchup")
    
    results = []
    win_counts = {agent.name: 0 for agent in agents}
    
    # Run games for each possible matchup
    for i, agent1 in enumerate(agents):
        for j, agent2 in enumerate(agents):
            if i >= j:  # Skip same agent and avoid duplicate matchups
                continue
            
            print(f"\nMatchup: {agent1.name} vs {agent2.name}")
            
            for game_num in range(games_per_matchup):
                print(f"  Game {game_num + 1}/{games_per_matchup}")
                
                # Create fresh agents for each game
                fresh_agent1 = type(agent1)(agent1.name, agent1.model, agent1.strategy)
                fresh_agent2 = type(agent2)(agent2.name, agent2.model, agent2.strategy)
                
                result = await run_single_game([fresh_agent1, fresh_agent2])
                results.append(result)
                
                if result['winner']:
                    win_counts[result['winner']] += 1
    
    # Print tournament results
    print("\n" + "="*50)
    print("TOURNAMENT RESULTS")
    print("="*50)
    for agent_name, wins in sorted(win_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{agent_name}: {wins} wins")
    print("="*50)
    
    return {
        "results": results,
        "win_counts": win_counts,
        "total_games": len(results)
    } 