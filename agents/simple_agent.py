"""
Simple AI Agent implementation for playing Risk.
A basic agent that uses direct implementation without base class inheritance.
"""

from .risk_api import GameState, GamePhase, RiskAPIClient
from .ollama_client import OllamaAgentClient
from .risk_rules import get_valid_reinforce_actions, get_valid_attack_actions, get_valid_fortify_actions, get_valid_move_armies_actions


class SimpleAgent:
    """A simple agent with a configurable strategy (balanced, aggressive, defensive)."""
    
    def __init__(self, name: str, model: str = "llama3.2", strategy: str = "balanced"):
        self.name = name
        self.model = model
        self.strategy = strategy
        self.risk_client = RiskAPIClient()
        self.ollama_client = OllamaAgentClient(model=model, risk_client=self.risk_client)
        self.game_history = []
    
    async def take_turn(self, _):
        # Always fetch fresh state at the start
        game_state = self.risk_client.get_game_state()
        use_tools = True
        player_id = game_state.players[self.name].id if self.name in game_state.players else None
        prompt = self._create_prompt(game_state)
        result = await self.ollama_client.get_agent_response(prompt, self.name, player_id=player_id, use_tools=use_tools)
        # Get fresh game state after the LLM response (which may have executed function calls)
        fresh_game_state = self.risk_client.get_game_state()
        my_player = fresh_game_state.players.get(self.name)
        if my_player:
            # Get fresh reinforcement armies for debug logging
            reinforcement_armies = self.risk_client.get_reinforcement_armies()
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[DEBUG] {self.name} fresh game state after turn: reinforcement_armies={reinforcement_armies}, phase={fresh_game_state.phase.value}, current_player={fresh_game_state.current_player}")
        return result

    def get_strategy_description(self) -> str:
        """Return a string describing the agent's strategy."""
        return f"{self.name} ({self.strategy} strategy) using {self.model}"

    def record_action(self, action: str, result: str):
        """Record an action and its result for learning purposes."""
        import asyncio
        self.game_history.append({
            "action": action,
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        })

    def _create_prompt(self, game_state: GameState) -> str:
        """Create a detailed, phase-specific prompt for the AI."""
        my_player = game_state.players.get(self.name)
        if not my_player:
            return "Error: Could not find myself in the game state."

        player_id = my_player.id
        phase = game_state.phase
        
        if phase == GamePhase.REINFORCE:
            # --- Continent analysis ---
            board = getattr(game_state, 'board', None)
            continents_info = None
            if board is None and hasattr(game_state, '_raw_state'):
                board = game_state._raw_state.get('board', {})
            if board is None:
                # Try to get from global state (for testability)
                import sys
                if 'game' in sys.modules:
                    board = getattr(sys.modules['game'], 'board', None)
            continents_info = None
            if board is None and hasattr(game_state, 'continents'):
                continents_info = game_state.continents
            else:
                continents_info = board.get('continents', {}) if board else {}

            # --- Continent bonus section ---
            if continents_info:
                prompt = "--- Continent Bonuses ---\n"
                for cname, cdata in continents_info.items():
                    prompt += f"- {cname}: {cdata.get('bonus_armies', 0)} armies\n"
                prompt += "-------------------------\n"
            else:
                prompt = ""

            # Build continent/territory mapping
            owned_territories = set(my_player.territories)
            controlled = []
            nearly_controlled = []
            if hasattr(game_state, 'continents') and game_state.continents:
                for cname, cdata in game_state.continents.items():
                    terrs = set(cdata['territories'])
                    owned = len(owned_territories & terrs)
                    total = len(terrs)
                    if owned == total:
                        controlled.append((cname, cdata.get('bonus_armies', 0)))
                    elif owned >= total - 1:
                        missing = list(terrs - owned_territories)
                        nearly_controlled.append((cname, owned, total, missing))

            if controlled:
                prompt += "\nYou fully control the following continents and receive bonus armies each turn:\n"
                for cname, bonus in controlled:
                    prompt += f"- {cname} (bonus: {bonus} armies)\n"
                prompt += "Consider defending the borders of these continents to keep your bonus.\n"
            if nearly_controlled:
                prompt += "\nYou are close to controlling these continents:\n"
                for cname, owned, total, missing in nearly_controlled:
                    missing_str = ', '.join(missing)
                    prompt += f"- {cname}: you own {owned}/{total} territories (missing: {missing_str})\n"
                prompt += "Consider focusing your reinforcements or attacks to complete these continents for a bonus.\n"
            if not controlled and not nearly_controlled:
                prompt += "\nYou do not currently control or nearly control any continent. Consider focusing your efforts on capturing all territories in a continent to receive bonus armies each turn.\n"

            # --- List valid reinforce actions ---
            valid_reinforce = get_valid_reinforce_actions(game_state, my_player, self.risk_client)
            valid_territories = [action['territory'] for action in valid_reinforce]
            prompt += "\n--- VALID REINFORCE ACTIONS ---\n"
            if valid_reinforce:
                for action in valid_reinforce:
                    prompt += f"- {action['territory']}: up to {action['max_armies']} armies\n"
                prompt += f"\nVALID TERRITORY NAMES: [{', '.join(valid_territories)}]\n"
                prompt += "You MUST use exactly one of the above territory names for each reinforce function call. Do NOT invent, modify, or misspell names. If you use an invalid name, your action will be ignored and replaced with a valid one.\n"
            else:
                prompt += "(No valid reinforce actions available.)\n"
            prompt += "-------------------------------\n\n"

            # Get fresh reinforcement armies from server for the prompt
            reinforcement_armies = self.risk_client.get_reinforcement_armies()
            prompt += f"It's your turn in the REINFORCE phase. Your player ID is {player_id}. You MUST include this ID in every function call.\n"
            prompt += f"You have {reinforcement_armies} armies to place.\n"
            prompt += "You MUST use the reinforce function to place armies. Only function calls will be executed. Do NOT output text instructions.\n"
            prompt += "CRITICAL: When calling the reinforce function, you MUST provide a valid territory name from the list above. Never use empty strings or None for the territory parameter.\n"
            prompt += "Place ALL your armies using multiple reinforce function calls. The phase will advance automatically when you have no more armies to place.\n"
        elif phase == GamePhase.ATTACK:
            prompt = f"It's your turn in the ATTACK phase. Your player ID is {player_id}. You MUST include this ID in every function call.\n"
            prompt += f"You are Player {self.name} with a {self.strategy} strategy.\n"
            prompt += f"You own {len(my_player.territories)} territories: {', '.join(my_player.territories)}\n"
            prompt += "🎯 ATTACK PHASE - BE AGGRESSIVE! 🎯\n"
            prompt += "🔥 YOUR GOAL: ANNIHILATE ALL ENEMIES! 🔥\n"
            prompt += "You should attack enemy territories to expand your empire and eliminate opponents.\n"
            prompt += "💎 BONUS: You earn a card every time you conquer a territory!\n"
            prompt += "Look for territories with fewer defending armies than your attacking armies.\n"
            prompt += "You can attack multiple times. Use the `attack` function for each attack.\n"
            prompt += "For each attack, you MUST choose how many dice to roll. The allowed number of dice is 1, 2, or 3, but you cannot roll more dice than you have armies in the attacking territory minus one.\n"
            prompt += "When you are finished attacking (or if you choose not to attack), the phase will advance automatically.\n"
            prompt += "\nCRITICAL: You MUST choose your attack ONLY from the list of valid attack actions below. Do NOT invent, guess, or modify territory names or attack parameters. If you attempt an invalid attack, your action will be ignored and your turn may be skipped.\n"
            prompt += "\n--- Your territories and armies ---\n"
            for t in my_player.territories:
                territory_data = game_state.territories.get(t)
                armies = territory_data.armies if territory_data else '?'
                prompt += f"- {t}: {armies} armies\n"
            prompt += "-----------------------------------\n"
            
            # --- List valid attack actions ---
            valid_attacks = get_valid_attack_actions(game_state, my_player)
            prompt += "\n--- VALID ATTACK ACTIONS ---\n"
            if valid_attacks:
                for action in valid_attacks:
                    from_terr = action['from']
                    to_terr = action['to']
                    max_dice = action['max_dice']
                    
                    # Find success probability for this attack
                    success_prob = "Unknown"
                    for prob_data in game_state.conquer_probs:
                        if len(prob_data) >= 3 and prob_data[0] == from_terr and prob_data[1] == to_terr:
                            success_prob = f"{prob_data[2]*100:.1f}%"
                            break
                    
                    prompt += f"- {from_terr} -> {to_terr}: up to {max_dice} dice (Success: {success_prob})\n"
                prompt += f"\nVALID ATTACK TERRITORIES: from_territory=[{', '.join(set(action['from'] for action in valid_attacks))}], to_territory=[{', '.join(set(action['to'] for action in valid_attacks))}]\n"
                prompt += "You MUST use exactly one of the above from_territory and to_territory names for each attack function call. Do NOT invent, modify, or misspell names. If you use an invalid name, your action will be ignored.\n"
                prompt += "CRITICAL: When calling the attack function, you MUST provide valid from_territory and to_territory names from the list above. Never use empty strings or None for territory parameters.\n"
            else:
                prompt += "(No valid attacks available this turn.)\n"
            prompt += "-------------------------------\n\n"
            
            prompt += "You MUST use the attack function to make attacks. Only function calls will be executed. Do NOT output text instructions.\n"
            prompt += "For each attack you want to make, call the attack function with the exact from_territory and to_territory names from the list above.\n"
            prompt += "You can make multiple attacks in one turn. After each attack, you can choose to continue attacking or stop.\n"
            prompt += "When you are done attacking (or if you choose not to attack), the phase will advance automatically.\n"
            
            prompt += "\n💡 ATTACK STRATEGY:\n"
            prompt += "- Attack when you have more armies than the defender\n"
            prompt += "- Focus on attacks with high success probabilities (80%+ is excellent)\n"
            prompt += "- Prioritize attacks with 90%+ success rate for maximum efficiency\n"
            prompt += "- Focus on weak enemy positions\n"
            prompt += "- Try to capture territories to expand your empire\n"
            prompt += "- Don't be afraid to take calculated risks!\n"
            prompt += "- Every conquered territory gives you a card for future reinforcements!\n"
            prompt += "- Remember: You must eliminate ALL enemies to win!\n"
            prompt += "\nIf no valid attacks are listed, the phase will advance automatically. Otherwise, use the attack function for each attack you want to make.\n"
        elif phase == GamePhase.FORTIFY:
            valid_fortifies = get_valid_fortify_actions(game_state, my_player)
            prompt = f"It's your turn in the FORTIFY phase. Your player ID is {player_id}. You MUST include this ID in every function call.\n"
            prompt += f"You may move armies between two of your connected territories (a single move).\n"
            prompt += "You MUST use the fortify function to move armies. Only function calls will be executed. Do NOT output text instructions.\n"
            prompt += "The phase will advance automatically when you have no more valid fortify actions.\n"
            prompt += "\n--- VALID FORTIFY MOVES ---\n"
            if valid_fortifies:
                for action in valid_fortifies:
                    from_terr = action['from']
                    to_terr = action['to']
                    max_armies = action['max_armies']
                    prompt += f"- {from_terr} -> {to_terr}: up to {max_armies} armies\n"
                prompt += f"\nVALID FORTIFY MOVES: from_territory=[{', '.join(set(a['from'] for a in valid_fortifies))}], to_territory=[{', '.join(set(a['to'] for a in valid_fortifies))}]\n"
                prompt += "You MUST use exactly one of the above from_territory and to_territory names for each fortify function call. Do NOT invent, modify, or misspell names. If you use an invalid name, your action will be ignored.\n"
                prompt += "CRITICAL: When calling the fortify function, you MUST provide valid from_territory and to_territory names from the list above. Never use empty strings or None for territory parameters.\n"
                prompt += "You can make one fortify move per turn. After making a move (or if you choose not to move), the phase will advance automatically.\n"
            else:
                prompt += "(No valid fortify moves available this turn.)\n"
            prompt += "-------------------------------\n\n"
            prompt += "If no valid fortify moves are listed, the phase will advance automatically. Otherwise, use the fortify function for your move.\n"
        elif phase == GamePhase.MOVE_ARMIES:
            prompt = f"It's your turn in the MOVE ARMIES phase. Your player ID is {player_id}. You MUST include this ID in every function call.\n"
            prompt += f"You have successfully conquered a territory and must now move some of your attacking armies into the newly conquered territory.\n"
            prompt += "You MUST use the move_armies function to move armies. Only function calls will be executed. Do NOT output text instructions.\n"
            prompt += "The server will tell you the valid move options including the minimum and maximum armies you can move.\n"
            prompt += "After moving armies, the phase will advance automatically.\n"
            
            # --- List valid move armies actions ---
            valid_moves = get_valid_move_armies_actions(game_state, my_player)
            prompt += "\n--- VALID MOVE ARMIES ACTIONS ---\n"
            if valid_moves:
                for action in valid_moves:
                    from_terr = action['from']
                    to_terr = action['to']
                    min_armies = action['min_armies']
                    max_armies = action['max_armies']
                    prompt += f"- {from_terr} -> {to_terr}: {min_armies} to {max_armies} armies\n"
                prompt += f"\nVALID MOVE ARMIES: from_territory=[{', '.join(set(action['from'] for action in valid_moves))}], to_territory=[{', '.join(set(action['to'] for action in valid_moves))}]\n"
                prompt += "You MUST use exactly one of the above from_territory and to_territory names for each move_armies function call. Do NOT invent, modify, or misspell names. If you use an invalid name, your action will be ignored.\n"
                prompt += "CRITICAL: When calling the move_armies function, you MUST provide valid from_territory and to_territory names from the list above. Never use empty strings or None for territory parameters.\n"
            else:
                prompt += "(No valid move armies actions available.)\n"
            prompt += "-------------------------------\n\n"
            
            prompt += "\n💡 MOVE ARMIES STRATEGY:\n"
            prompt += "- Move enough armies to defend your newly conquered territory\n"
            prompt += "- Keep enough armies in your attacking territory to defend it\n"
            prompt += "- Consider the strategic value of both territories\n"
            prompt += "- The server will enforce the minimum and maximum army limits\n"
            prompt += "\nUse the move_armies function with the exact from_territory and to_territory names provided by the server.\n"

        return prompt


class AggressiveAgent(SimpleAgent):
    """An aggressive AI agent that focuses on attacking."""
    
    def __init__(self, name: str, model: str = "llama3.2"):
        super().__init__(name, model, strategy="aggressive")
    
    async def make_decision(self, game_state: GameState) -> str:
        """Make aggressive decisions."""
        return "Using aggressive strategy"
    
    async def _handle_attack_phase(self, game_state: GameState) -> str:
        """Handle attack phase with aggressive strategy."""
        prompt = f"""You are an AGGRESSIVE Risk player named {self.name}. Your strategy is to attack whenever possible.

Current game state:
- Your territories: {game_state.players[self.name].territories}
- Total territories: {len(game_state.territories)}

Your aggressive strategy:
1. Attack weak enemy positions whenever possible
2. Expand your territory aggressively
3. Don't be afraid to take risks
4. Focus on eliminating opponents quickly
5. Prioritize attacks over defense

What aggressive actions would you like to take?"""
        
        return await self.ollama_client.get_agent_response(prompt, self.name)


class DefensiveAgent(SimpleAgent):
    """A defensive AI agent that focuses on building strong positions."""
    
    def __init__(self, name: str, model: str = "llama3.2"):
        super().__init__(name, model, strategy="defensive")
    
    async def make_decision(self, game_state: GameState) -> str:
        """Make defensive decisions."""
        return "Using defensive strategy"
    
    async def _handle_reinforce_phase(self, game_state: GameState) -> str:
        """Handle reinforce phase with defensive strategy."""
        prompt = f"""You are a DEFENSIVE Risk player named {self.name}. Your strategy is to build strong defensive positions.

Current game state:
- Your territories: {game_state.players[self.name].territories}
- Your armies to place: {game_state.players[self.name].armies}
- Total territories: {len(game_state.territories)}

Your defensive strategy:
1. Reinforce border territories heavily
2. Build up armies in key defensive positions
3. Focus on continent control for bonuses
4. Avoid risky attacks unless very favorable
5. Prioritize defense over expansion

Where would you like to place your armies defensively?"""
        
        return await self.ollama_client.get_agent_response(prompt, self.name)