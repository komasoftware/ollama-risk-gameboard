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
        phase_repeat_count = {}  # Track repeated phase/player combinations
        
        while True:
            # Always fetch fresh state from server
            game_state = self.risk_client.get_game_state()
            if game_state.game_over:
                break
            
            current_agent = self._get_agent_for_player(game_state.current_player)
            if not current_agent:
                logger.error(f"No agent found for player {game_state.current_player}")
                break
            
            # Track phase/player combinations to detect infinite loops
            phase_key = f"{game_state.current_player}_{game_state.phase.value}"
            phase_repeat_count[phase_key] = phase_repeat_count.get(phase_key, 0) + 1
            
            # Safety check: if same phase/player repeats too many times, advance phase
            if phase_repeat_count[phase_key] > 10:
                logger.warning(f"Phase {game_state.phase.value} for {game_state.current_player} repeated {phase_repeat_count[phase_key]} times. Advancing phase to prevent infinite loop.")
                self.risk_client.advance_phase()
                phase_repeat_count[phase_key] = 0  # Reset counter
                continue
            
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
                # Reset phase repeat counters when player changes
                phase_repeat_count.clear()
        
        logger.info("Game over!")
        return self._summarize_game(self.risk_client.get_game_state())

    async def _handle_reinforce_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        my_player = game_state.players.get(agent.name)
        if not my_player:
            logger.info(f"Player {agent.name} not found in game state. Skipping.")
            return
        
        print("\n" + "="*40)
        print(f"▶️  {agent.name} entering REINFORCE phase")
        print("="*40)
        
        # Get fresh reinforcement armies from server - NEVER use my_player.armies
        armies_before = self.risk_client.get_reinforcement_armies()
        logger.info(f"[DEBUG] {agent.name} reinforcement armies: {armies_before}, territories: {my_player.territories}")
        
        if not my_player.territories:
            logger.info(f"Player {agent.name} has no territories and is eliminated. Skipping turn.")
            return
        
        # --- CARD TRADING LOGIC ---
        from agents.risk_rules import get_valid_card_trade_actions, get_valid_reinforce_actions
        valid_trades = get_valid_card_trade_actions(game_state, my_player)
        # Force trade if 5+ cards
        while len(my_player.cards) >= 5 and valid_trades:
            print(f"{agent.name} has {len(my_player.cards)} cards and MUST trade before reinforcing.")
            trade_action = valid_trades[0]  # Auto-select first valid set
            print(f"Auto-trading cards: indices {trade_action['card_indices']}")
            try:
                self.risk_client.trade_cards(my_player.id, trade_action['card_indices'])
                # Refresh state after trade
                game_state = self.risk_client.get_game_state()
                my_player = game_state.players.get(agent.name)
                valid_trades = get_valid_card_trade_actions(game_state, my_player)
            except Exception as e:
                logger.error(f"Error during auto-trade: {e}")
                break
        # If 3-4 cards, let agent decide (trade is optional)
        # (Agent prompt should include trade options)
        
        armies_before = self.risk_client.get_reinforcement_armies()
        if armies_before == 0:
            logger.info(f"Player {agent.name} has no armies to reinforce. Advancing phase.")
            self.risk_client.advance_phase()
            return
        
        logger.info(f"{agent.name} planning and executing reinforcements...")
        
        valid_reinforce = get_valid_reinforce_actions(game_state, my_player, self.risk_client)
        valid_territories = [action['territory'] for action in valid_reinforce]
        logger.info(f"Valid reinforce territories for {agent.name}: {valid_territories}")
        
        if not valid_territories:
            logger.info(f"No valid reinforce actions for {agent.name}. Advancing phase.")
            self.risk_client.advance_phase()
            return
        
        # Let the agent place armies until no more armies are available
        retry_count = 0
        max_retries = 10  # Prevent infinite loops
        
        while retry_count < max_retries:
            # Check if we still have armies to place
            current_armies = self.risk_client.get_reinforcement_armies()
            if current_armies == 0:
                logger.info(f"{agent.name} has no more armies to place.")
                break
            
            # Log thinking process (prompt summary) to file only
            if hasattr(agent, '_create_prompt'):
                prompt = agent._create_prompt(game_state)
                logger.info(f"{agent.name} REINFORCE prompt: {prompt[:500]}{'...' if len(prompt) > 500 else ''}")
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            print(f"\n*** {agent.name} LLM FULL RESPONSE in REINFORCE ***\n{result}\n*** END LLM RESPONSE ***\n")
            logger.info(f"{agent.name} reinforce action: {result}")
            
            # Get fresh reinforcement armies from server after the action
            armies_after = self.risk_client.get_reinforcement_armies()
            logger.info(f"[DEBUG] {agent.name} reinforcement armies before: {current_armies}, after: {armies_after}")
            
            # Check if the action was successful
            action_successful = False
            
            # Check for successful reinforce actions
            if "reinforced" in result.lower() and armies_after < current_armies:
                action_successful = True
                retry_count = 0  # Reset retry count on success
            
            # Check for successful card trading
            if "traded cards" in result.lower() and "bonus armies" in result.lower():
                action_successful = True
                retry_count = 0  # Reset retry count on success
            
            # Check for failed actions (error messages)
            if ("error" in result.lower() or 
                "invalid" in result.lower() or 
                "must" in result.lower() or
                "card_indices must be between" in result.lower() or
                "must trade exactly 3 cards" in result.lower()):
                retry_count += 1
                logger.warning(f"{agent.name} made invalid action (attempt {retry_count}/{max_retries}): {result}")
                
                # If we've tried too many times, advance phase
                if retry_count >= max_retries:
                    logger.error(f"{agent.name} exceeded max retries in reinforce phase. Advancing to next phase.")
                    self.risk_client.advance_phase()
                    return
                continue
            
            # If no action was taken and armies didn't change, we might be done
            if not action_successful and armies_after == current_armies:
                retry_count += 1
                logger.warning(f"{agent.name} no action taken (attempt {retry_count}/{max_retries})")
                
                # If we've tried too many times, advance phase
                if retry_count >= max_retries:
                    logger.error(f"{agent.name} exceeded max retries in reinforce phase. Advancing to next phase.")
                    self.risk_client.advance_phase()
                    return
                continue

    async def _handle_attack_phase(self, agent: Any):
        game_state = self.risk_client.get_game_state()  # Always fetch fresh state
        my_player = game_state.players.get(agent.name)
        if not my_player:
            logger.info(f"Player {agent.name} not found in game state. Skipping.")
            return
        
        print("\n" + "="*40)
        print(f"▶️  {agent.name} entering ATTACK phase")
        print("="*40)
        
        logger.info(f"{agent.name} planning and executing attacks...")
        
        # Let the agent make attacks until no more valid attacks are available
        while True:
            from agents.risk_rules import get_valid_attack_actions
            valid_attacks = get_valid_attack_actions(game_state, my_player)
            
            if not valid_attacks:
                logger.info(f"{agent.name} has no more valid attack actions. Advancing to next phase.")
                self.risk_client.advance_phase()
                break
            
            # Log thinking process (prompt summary) to file only
            if hasattr(agent, '_create_prompt'):
                prompt = agent._create_prompt(game_state)
                logger.info(f"{agent.name} ATTACK prompt: {prompt[:500]}{'...' if len(prompt) > 500 else ''}")
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            print(f"\n*** {agent.name} LLM FULL RESPONSE in ATTACK ***\n{result}\n*** END LLM RESPONSE ***\n")
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
        
        print("\n" + "="*40)
        print(f"▶️  {agent.name} entering FORTIFY phase")
        print("="*40)
        
        logger.info(f"{agent.name} planning and executing fortifications...")
        
        # Let the agent make fortify moves until no more valid moves are available
        while True:
            from agents.risk_rules import get_valid_fortify_actions
            valid_fortifies = get_valid_fortify_actions(game_state, my_player)
            
            if not valid_fortifies:
                logger.info(f"{agent.name} has no more valid fortify actions. Advancing to next phase.")
                self.risk_client.advance_phase()
                break
            
            # Log thinking process (prompt summary) to file only
            if hasattr(agent, '_create_prompt'):
                prompt = agent._create_prompt(game_state)
                logger.info(f"{agent.name} FORTIFY prompt: {prompt[:500]}{'...' if len(prompt) > 500 else ''}")
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            print(f"\n*** {agent.name} LLM FULL RESPONSE in FORTIFY ***\n{result}\n*** END LLM RESPONSE ***\n")
            logger.info(f"{agent.name} fortify action: {result}")

            # Fallback: Detect text-based function calls and re-prompt
            if re.search(r"fortify\s*\(", result, re.IGNORECASE) or 'ollama.fortify' in result.lower() or 'fortify' in result.lower() and 'function calling' not in result.lower() and 'executed actions' not in result.lower():
                print(f"\n[WARNING] {agent.name} output a text-based function call. Re-prompting with direct instruction.\n")
                logger.warning(f"{agent.name} output a text-based function call. Re-prompting.")
                # Minimal direct instruction
                direct_prompt = "IMPORTANT: You must use the function calling mechanism. DO NOT write function calls as text. Try again."
                if hasattr(agent, '_create_prompt'):
                    prompt = agent._create_prompt(game_state)
                    prompt += f"\n{direct_prompt}\n"
                    logger.info(f"{agent.name} FORTIFY fallback prompt: {prompt[:500]}{'...' if len(prompt) > 500 else ''}")
                # Re-ask the agent
                result = await agent.take_turn(None)
                print(f"\n*** {agent.name} LLM FULL RESPONSE in FORTIFY (RETRY) ***\n{result}\n*** END LLM RESPONSE ***\n")
                logger.info(f"{agent.name} fortify action (retry): {result}")

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
        
        print("\n" + "="*40)
        print(f"▶️  {agent.name} entering MOVE ARMIES phase")
        print("="*40)
        
        logger.info(f"{agent.name} planning and executing army movements after attack...")
        
        # Let the agent move armies until no more valid moves are available
        retry_count = 0
        max_retries = 5  # Prevent infinite loops
        
        while retry_count < max_retries:
            from agents.risk_rules import get_valid_move_armies_actions
            valid_moves = get_valid_move_armies_actions(game_state, my_player)
            
            if not valid_moves:
                logger.info(f"{agent.name} has no more valid move armies actions. Advancing to next phase.")
                self.risk_client.advance_phase()
                break
            
            # Log thinking process (prompt summary) to file only
            if hasattr(agent, '_create_prompt'):
                prompt = agent._create_prompt(game_state)
                logger.info(f"{agent.name} MOVE ARMIES prompt: {prompt[:500]}{'...' if len(prompt) > 500 else ''}")
            
            result = await agent.take_turn(None)  # Agent will fetch its own state
            print(f"\n*** {agent.name} LLM FULL RESPONSE in MOVE ARMIES ***\n{result}\n*** END LLM RESPONSE ***\n")
            logger.info(f"{agent.name} move armies action: {result}")
            
            # Check if the action was successful (no error messages)
            if ("error" in result.lower() or 
                "invalid" in result.lower() or 
                "must" in result.lower() or
                "card_indices" in result.lower() or
                "reinforced" in result.lower() and game_state.phase.value == "movearmies" or
                "attacked" in result.lower() and game_state.phase.value == "movearmies" or
                "fortified" in result.lower() and game_state.phase.value == "movearmies"):
                retry_count += 1
                logger.warning(f"{agent.name} made invalid move armies action (attempt {retry_count}/{max_retries}): {result}")
                if retry_count >= max_retries:
                    logger.error(f"{agent.name} exceeded max retries in move armies phase. Advancing to next phase.")
                    self.risk_client.advance_phase()
                    break
                continue
            
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