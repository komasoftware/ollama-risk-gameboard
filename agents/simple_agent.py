"""
Simple AI Agent implementation for playing Risk.
A basic agent that uses direct implementation without base class inheritance.
"""

from .risk_api import GameState, GamePhase, RiskAPIClient
from .ollama_client import OllamaAgentClient
from .risk_rules import get_valid_reinforce_actions, get_valid_attack_actions, get_valid_fortify_actions, get_valid_move_armies_actions, get_valid_card_trade_actions


class SimpleAgent:
    """A simple agent with a configurable strategy (balanced, aggressive, defensive)."""
    
    EXAMPLES = (
        """You are playing Risk. Use the function calling mechanism to make your moves.

Example 1 (Reinforce Phase):
Reasoning:
1. Ontario is a central territory in North America, allowing expansion and defense.
2. Reinforcing Great Britain protects my European foothold and threatens attacks.
3. I have 5 reinforcement armies to place.
Action:
Use the reinforce function with all required parameters:
- player_id: 0
- territory: "Ontario"
- num_armies: 3

Use the reinforce function again:
- player_id: 0
- territory: "Great Britain"
- num_armies: 2

Example 2 (Card Trading in Reinforce Phase):
Reasoning:
1. I have 3 Infantry cards that I can trade for 4 bonus armies.
2. Card trading is only available during REINFORCE phase.
3. I must trade exactly 3 cards using the trade_cards function.
Action:
Use the trade_cards function with the correct parameters:
- player_id: 0
- card_indices: [0, 1, 2]

Example 3 (Card Trading - One of Each Type):
Reasoning:
1. I have 1 Infantry, 1 Cavalry, and 1 Artillery card.
2. This combination gives me 10 bonus armies (the maximum).
3. I should trade these cards for maximum benefit.
Action:
Use the trade_cards function with all required parameters:
- player_id: 0
- card_indices: [0, 1, 2]

Example 4 (Card Trading with Jokers):
Reasoning:
1. I have 1 Infantry and 2 Joker cards.
2. Jokers can substitute for any card type.
3. This combination is valid and gives me 10 bonus armies.
Action:
Use the trade_cards function with all required parameters:
- player_id: 0
- card_indices: [0, 1, 2]

Example 5 (Attack Phase):
Reasoning:
1. I want to attack from Alaska to Northwest Territory.
2. I have 4 armies in Alaska, so I can attack with 1-3 armies.
3. I must use the attack function with all required parameters.
Action:
Use the attack function:
- player_id: 0
- from_territory: "Alaska"
- to_territory: "Northwest Territory"
- num_armies: 2
- num_dice: 2
- repeat: false

Example 6 (Move Armies Phase):
Reasoning:
1. I successfully conquered Northwest Territory and need to move armies there.
2. I should move 2 armies to secure the newly conquered territory.
3. This will leave 1 army in the attacking territory as required.
Action:
Use the move_armies function with all required parameters:
- player_id: 0
- from_territory: "Alberta"
- to_territory: "Northwest Territory"
- num_armies: 2

Example 7 (Fortify Phase):
Reasoning:
1. I want to move armies from Quebec to Ontario.
2. I have 3 armies in Quebec, so I can move 1-2 armies.
3. I must use the fortify function with all required parameters.
Action:
Use the fortify function:
- player_id: 0
- from_territory: "Quebec"
- to_territory: "Ontario"
- num_armies: 1

CARD TRADING RULES:
- You can ONLY trade cards during REINFORCE phase
- You MUST trade exactly 3 cards at a time
- Valid combinations: 3 of same type OR 1 of each type (Infantry, Cavalry, Artillery)
- Jokers can substitute for any card type
- 3 of a kind: Infantry=4 armies, Cavalry=6 armies, Artillery=8 armies
- 1 of each type: 10 armies (maximum)
- Use card_indices parameter with exactly 3 integers (0-based indexing)

IMPORTANT: Always use the function calling mechanism. DO NOT write function calls as text strings.
Always include ALL required parameters for each function.
"""
    )

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
        """Create a simplified, phase-specific prompt focused on function calling."""
        my_player = game_state.players.get(self.name)
        if not my_player:
            return "Error: Could not find myself in the game state."

        player_id = my_player.id
        phase = game_state.phase
        
        # Build the prompt
        prompt = f"You are {self.name} playing Risk. You MUST use Ollama's function calling mechanism.\n\n"
        
        # Add explicit function calling instruction
        prompt += "🔥 CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings. 🔥\n\n"
        
        prompt += f"CURRENT PHASE: {phase.value}\n"
        prompt += f"PLAYER ID: {my_player.id}\n\n"
        
        if phase == GamePhase.REINFORCE:
            prompt += self._create_simple_reinforce_prompt(game_state)
        elif phase == GamePhase.ATTACK:
            prompt += self._create_simple_attack_prompt(game_state)
        elif phase == GamePhase.FORTIFY:
            prompt += self._create_simple_fortify_prompt(game_state)
        elif phase == GamePhase.MOVE_ARMIES:
            prompt += self._create_simple_move_armies_prompt(game_state)

        # Add critical instructions
        prompt += f"""

STRATEGIC GUIDANCE:
- Reinforce border territories that are adjacent to enemy territories
- Consider continent bonuses when placing armies - control entire continents for bonus armies
- Attack from territories with more armies to territories with fewer armies
- Target weak enemy positions and try to eliminate players
- Protect your continent bonuses by defending key territories
- Prioritize continents with higher bonuses: Asia (+7), North America/Europe (+5), Africa (+3), South America/Australia (+2)
- Card trading is ONLY available during REINFORCE phase
- Card trading gives bonus armies: 3 of a kind = 4-8 armies, 1 of each = 10 armies

CRITICAL INSTRUCTIONS:
1. Use ONLY the function calling mechanism provided by Ollama
2. DO NOT write function calls as text strings
3. DO NOT provide lengthy reasoning or explanations
4. Make direct function calls with ALL required parameters
5. Focus on the action, not the explanation
6. If you have valid actions available, make them immediately
7. DO NOT ask questions or wait for confirmation

Choose your action now using the function calling mechanism."""

        return prompt

    def _create_simple_reinforce_prompt(self, game_state: GameState) -> str:
        """Create a simplified reinforce prompt focused on function calling."""
        my_player = game_state.players.get(self.name)
        if not my_player:
            return "Error: Could not find myself in the game state."

        player_id = my_player.id
        
        prompt = f"REINFORCE PHASE: Choose actions from the list below.\n"
        prompt += f"Your territories: {', '.join(my_player.territories)}\n"
        prompt += f"Your armies to place: {my_player.armies}\n"
        prompt += f"Your cards: {my_player.cards} (count: {len(my_player.cards)})\n\n"
        
        # IMPORTANT: Only reinforce and trade_cards functions are allowed in this phase
        prompt += "PHASE RESTRICTIONS:\n"
        prompt += "- ONLY reinforce and trade_cards functions are allowed in REINFORCE phase\n"
        prompt += "- DO NOT use attack, fortify, or move_armies functions\n"
        prompt += "- You can reinforce multiple times\n"
        prompt += "- You can trade cards multiple times (if you have enough cards)\n\n"
        
        # Add comprehensive board state information
        # NOTE: Using fresh game_state to ensure enemy positions are current
        prompt += "BOARD STATE:\n"
        for player_name, player_data in game_state.players.items():
            if player_name != self.name:  # Show enemy information
                prompt += f"ENEMY {player_name} (ID {player_data.id}):\n"
                prompt += f"  Territories: {', '.join(player_data.territories)}\n"
                prompt += f"  Total armies: {player_data.total_armies}\n"
                # Show army distribution for key territories (from fresh game state)
                border_territories = []
                for territory in player_data.territories:
                    if territory in game_state.territories:
                        territory_data = game_state.territories[territory]
                        adjacent_to_mine = any(adj in my_player.territories for adj in territory_data.adjacent_territories)
                        if adjacent_to_mine:
                            border_territories.append(f"{territory}({territory_data.armies})")
                if border_territories:
                    prompt += f"  Border territories (adjacent to yours): {', '.join(border_territories)}\n"
                prompt += "\n"
        
        # Add continent information for strategic planning
        prompt += "CONTINENT INFORMATION:\n"
        continent_data = {
            "North America": {"bonus": 5, "territories": ["Alaska", "Northwest Territory", "Alberta", "Ontario", "Quebec", "Greenland", "Western United States", "Eastern United States", "Central America"]},
            "South America": {"bonus": 2, "territories": ["Venezuela", "Peru", "Brazil", "Argentina"]},
            "Europe": {"bonus": 5, "territories": ["Iceland", "Scandinavia", "Great Britain", "Northern Europe", "Western Europe", "Southern Europe", "Ukraine"]},
            "Africa": {"bonus": 3, "territories": ["North Africa", "Egypt", "East Africa", "Congo", "South Africa", "Madagascar"]},
            "Asia": {"bonus": 7, "territories": ["Ural", "Siberia", "Yakutsk", "Kamchatka", "Irkutsk", "Mongolia", "Japan", "China", "Afghanistan", "Middle East", "India", "Siam"]},
            "Australia": {"bonus": 2, "territories": ["Indonesia", "New Guinea", "Western Australia", "Eastern Australia"]}
        }
        
        for continent_name, continent_info in continent_data.items():
            my_territories_in_continent = [t for t in continent_info["territories"] if t in my_player.territories]
            enemy_territories_in_continent = []
            for player_name, player_data in game_state.players.items():
                if player_name != self.name:
                    enemy_territories_in_continent.extend([t for t in continent_info["territories"] if t in player_data.territories])
            
            if my_territories_in_continent:
                prompt += f"{continent_name} (Bonus: +{continent_info['bonus']} armies):\n"
                prompt += f"  Your territories: {', '.join(my_territories_in_continent)}\n"
                if enemy_territories_in_continent:
                    prompt += f"  Enemy territories: {', '.join(enemy_territories_in_continent)}\n"
                    missing = [t for t in continent_info["territories"] if t not in my_territories_in_continent and t not in enemy_territories_in_continent]
                    if missing:
                        prompt += f"  Unclaimed: {', '.join(missing)}\n"
                else:
                    prompt += f"  🎉 YOU CONTROL THIS CONTINENT! (+{continent_info['bonus']} bonus armies)\n"
                prompt += "\n"
        
        # List valid reinforce actions
        valid_reinforce = get_valid_reinforce_actions(game_state, my_player, self.risk_client)
        
        # List valid card trade actions
        valid_trades = get_valid_card_trade_actions(game_state, my_player)
        
        prompt += "AVAILABLE ACTIONS:\n"
        
        # Add card trading actions first (if available)
        if valid_trades:
            prompt += "CARD TRADING (optional - trade 3 cards for bonus armies):\n"
            for i, action in enumerate(valid_trades, 1):
                card_indices = action['card_indices']
                cards_to_trade = [my_player.cards[idx] for idx in card_indices]
                prompt += f"{i}. Trade cards at indices {card_indices} (cards: {', '.join(cards_to_trade)})\n"
                prompt += f"   Valid parameters: card_indices={card_indices}\n"
                prompt += f"   Example: trade_cards(card_indices={card_indices})\n"
                prompt += "\n"
        else:
            # Explain why card trading is not available
            if len(my_player.cards) < 3:
                prompt += f"CARD TRADING: NOT AVAILABLE - you have {len(my_player.cards)} cards, need exactly 3 to trade\n"
                prompt += f"DO NOT try to trade cards - you don't have enough!\n"
            else:
                prompt += "CARD TRADING: No valid 3-card combinations available\n"
            prompt += "\n"
        
        # Add reinforce actions
        if valid_reinforce:
            prompt += "REINFORCE ACTIONS:\n"
            for action in valid_reinforce:
                prompt += f"- reinforce: territory='{action['territory']}', num_armies=1-{action['max_armies']}\n"
        else:
            prompt += "- No valid reinforce actions available\n"
        
        # Add important rules about card trading
        prompt += "\nCARD TRADING RULES:\n"
        prompt += "1. You can only trade exactly 3 cards at a time\n"
        prompt += "2. Valid combinations: 3 of same type OR 1 of each type (Infantry, Cavalry, Artillery)\n"
        prompt += "3. Jokers can substitute for any card type\n"
        prompt += "4. You get bonus armies when trading cards\n"
        prompt += "5. You can only trade cards you actually have\n"
        prompt += f"6. Your current cards: {my_player.cards} (indices 0-{len(my_player.cards)-1 if my_player.cards else -1})\n"
        
        # Add explicit warning if no cards available
        if len(my_player.cards) < 3:
            prompt += f"7. ⚠️  WARNING: You only have {len(my_player.cards)} cards - DO NOT try to trade cards!\n"
            prompt += f"8. ⚠️  Focus on reinforcing territories instead\n"
        
        return prompt

    def _create_simple_attack_prompt(self, game_state: GameState) -> str:
        """Create a simplified attack prompt focused on function calling."""
        my_player = game_state.players.get(self.name)
        if not my_player:
            return "Error: Could not find myself in the game state."

        player_id = my_player.id
        
        prompt = f"You are {self.name} playing Risk. You MUST use Ollama's function calling mechanism.\n\n"
        prompt += "🔥 CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings. 🔥\n\n"
        prompt += f"ATTACK PHASE: Choose an attack from the list below.\n"
        prompt += f"Your territories: {', '.join(my_player.territories)}\n\n"
        
        # IMPORTANT: Only attack function is allowed in this phase
        prompt += "PHASE RESTRICTIONS:\n"
        prompt += "- ONLY attack function is allowed in ATTACK phase\n"
        prompt += "- DO NOT use reinforce, fortify, move_armies, or trade_cards functions\n"
        prompt += "- You can attack multiple times\n\n"
        
        # Add comprehensive board state information
        # NOTE: Using fresh game_state to ensure enemy positions are current
        prompt += "BOARD STATE:\n"
        for player_name, player_data in game_state.players.items():
            if player_name != self.name:  # Show enemy information
                prompt += f"ENEMY {player_name} (ID {player_data.id}):\n"
                prompt += f"  Territories: {', '.join(player_data.territories)}\n"
                prompt += f"  Total armies: {player_data.total_armies}\n"
                # Show army distribution for key territories (from fresh game state)
                border_territories = []
                for territory in player_data.territories:
                    if territory in game_state.territories:
                        territory_data = game_state.territories[territory]
                        adjacent_to_mine = any(adj in my_player.territories for adj in territory_data.adjacent_territories)
                        if adjacent_to_mine:
                            border_territories.append(f"{territory}({territory_data.armies})")
                if border_territories:
                    prompt += f"  Border territories (adjacent to yours): {', '.join(border_territories)}\n"
                prompt += "\n"
        
        # Add continent information for strategic planning
        prompt += "CONTINENT INFORMATION:\n"
        continent_data = {
            "North America": {"bonus": 5, "territories": ["Alaska", "Northwest Territory", "Alberta", "Ontario", "Quebec", "Greenland", "Western United States", "Eastern United States", "Central America"]},
            "South America": {"bonus": 2, "territories": ["Venezuela", "Peru", "Brazil", "Argentina"]},
            "Europe": {"bonus": 5, "territories": ["Iceland", "Scandinavia", "Great Britain", "Northern Europe", "Western Europe", "Southern Europe", "Ukraine"]},
            "Africa": {"bonus": 3, "territories": ["North Africa", "Egypt", "East Africa", "Congo", "South Africa", "Madagascar"]},
            "Asia": {"bonus": 7, "territories": ["Ural", "Siberia", "Yakutsk", "Kamchatka", "Irkutsk", "Mongolia", "Japan", "China", "Afghanistan", "Middle East", "India", "Siam"]},
            "Australia": {"bonus": 2, "territories": ["Indonesia", "New Guinea", "Western Australia", "Eastern Australia"]}
        }
        
        for continent_name, continent_info in continent_data.items():
            my_territories_in_continent = [t for t in continent_info["territories"] if t in my_player.territories]
            enemy_territories_in_continent = []
            for player_name, player_data in game_state.players.items():
                if player_name != self.name:
                    enemy_territories_in_continent.extend([t for t in continent_info["territories"] if t in player_data.territories])
            
            if my_territories_in_continent:
                prompt += f"{continent_name} (Bonus: +{continent_info['bonus']} armies):\n"
                prompt += f"  Your territories: {', '.join(my_territories_in_continent)}\n"
                if enemy_territories_in_continent:
                    prompt += f"  Enemy territories: {', '.join(enemy_territories_in_continent)}\n"
                    missing = [t for t in continent_info["territories"] if t not in my_territories_in_continent and t not in enemy_territories_in_continent]
                    if missing:
                        prompt += f"  Unclaimed: {', '.join(missing)}\n"
                else:
                    prompt += f"  🎉 YOU CONTROL THIS CONTINENT! (+{continent_info['bonus']} bonus armies)\n"
                prompt += "\n"
        
        # List valid attack actions with clear parameter guidance
        valid_attacks = get_valid_attack_actions(game_state, my_player)
        
        prompt += "AVAILABLE ATTACKS:\n"
        if valid_attacks:
            for i, action in enumerate(valid_attacks, 1):
                # Get the territory info to show available armies
                from_territory = game_state.territories.get(action['from'])
                available_armies = from_territory.armies if from_territory else 0
                max_attack_armies = available_armies - 1  # Must leave 1 army behind
                
                prompt += f"{i}. Attack from '{action['from']}' to '{action['to']}'\n"
                prompt += f"   Available armies: {available_armies} (can attack with 1-{max_attack_armies})\n"
                prompt += f"   Valid parameters: num_armies=1-{max_attack_armies}, num_dice=1-{min(action['max_dice'], max_attack_armies)}\n"
                
                # Provide specific valid examples
                if max_attack_armies >= 1:
                    prompt += f"   Example 1: attack(from_territory='{action['from']}', to_territory='{action['to']}', num_armies=1, num_dice=1)\n"
                if max_attack_armies >= 2:
                    prompt += f"   Example 2: attack(from_territory='{action['from']}', to_territory='{action['to']}', num_armies=2, num_dice=2)\n"
                if max_attack_armies >= 3:
                    prompt += f"   Example 3: attack(from_territory='{action['from']}', to_territory='{action['to']}', num_armies=3, num_dice=3)\n"
                
                prompt += "\n"
        else:
            prompt += "- No valid attacks available\n"
        
        prompt += "CRITICAL ATTACK RULES:\n"
        prompt += "1. num_armies: Must be 1 to (available armies - 1)\n"
        prompt += "2. num_dice: Must be 1 to min(num_armies, 3)\n"
        prompt += "3. You must leave at least 1 army in your territory\n"
        prompt += "4. You can roll at most 3 dice\n"
        prompt += "5. Both parameters must be positive integers\n"
        prompt += "6. num_dice CANNOT exceed num_armies\n"
        prompt += "7. num_armies CANNOT exceed available armies minus 1\n"
        
        return prompt

    def _create_simple_fortify_prompt(self, game_state: GameState) -> str:
        """Create a simplified fortify prompt focused on function calling."""
        my_player = game_state.players.get(self.name)
        if not my_player:
            return "Error: Could not find myself in the game state."

        player_id = my_player.id
        
        prompt = f"You are {self.name} playing Risk. You MUST use Ollama's function calling mechanism.\n\n"
        prompt += "🔥 CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings. 🔥\n\n"
        prompt += f"FORTIFY PHASE: Choose a fortify move from the list below.\n"
        prompt += f"Your territories: {', '.join(my_player.territories)}\n\n"
        
        # IMPORTANT: Only fortify function is allowed in this phase
        prompt += "PHASE RESTRICTIONS:\n"
        prompt += "- ONLY fortify function is allowed in FORTIFY phase\n"
        prompt += "- DO NOT use reinforce, attack, move_armies, or trade_cards functions\n"
        prompt += "- You can fortify multiple times\n\n"
        
        # Add continent information for strategic planning
        prompt += "CONTINENT INFORMATION:\n"
        continent_data = {
            "North America": {"bonus": 5, "territories": ["Alaska", "Northwest Territory", "Alberta", "Ontario", "Quebec", "Greenland", "Western United States", "Eastern United States", "Central America"]},
            "South America": {"bonus": 2, "territories": ["Venezuela", "Peru", "Brazil", "Argentina"]},
            "Europe": {"bonus": 5, "territories": ["Iceland", "Scandinavia", "Great Britain", "Northern Europe", "Western Europe", "Southern Europe", "Ukraine"]},
            "Africa": {"bonus": 3, "territories": ["North Africa", "Egypt", "East Africa", "Congo", "South Africa", "Madagascar"]},
            "Asia": {"bonus": 7, "territories": ["Ural", "Siberia", "Yakutsk", "Kamchatka", "Irkutsk", "Mongolia", "Japan", "China", "Afghanistan", "Middle East", "India", "Siam"]},
            "Australia": {"bonus": 2, "territories": ["Indonesia", "New Guinea", "Western Australia", "Eastern Australia"]}
        }
        
        for continent_name, continent_info in continent_data.items():
            my_territories_in_continent = [t for t in continent_info["territories"] if t in my_player.territories]
            enemy_territories_in_continent = []
            for player_name, player_data in game_state.players.items():
                if player_name != self.name:
                    enemy_territories_in_continent.extend([t for t in continent_info["territories"] if t in player_data.territories])
            
            if my_territories_in_continent:
                prompt += f"{continent_name} (Bonus: +{continent_info['bonus']} armies):\n"
                prompt += f"  Your territories: {', '.join(my_territories_in_continent)}\n"
                if enemy_territories_in_continent:
                    prompt += f"  Enemy territories: {', '.join(enemy_territories_in_continent)}\n"
                    missing = [t for t in continent_info["territories"] if t not in my_territories_in_continent and t not in enemy_territories_in_continent]
                    if missing:
                        prompt += f"  Unclaimed: {', '.join(missing)}\n"
                else:
                    prompt += f"  🎉 YOU CONTROL THIS CONTINENT! (+{continent_info['bonus']} bonus armies)\n"
                prompt += "\n"
        
        # List valid fortify actions
        valid_fortifies = get_valid_fortify_actions(game_state, my_player)
        
        prompt += "AVAILABLE ACTIONS:\n"
        if valid_fortifies:
            for i, action in enumerate(valid_fortifies, 1):
                prompt += f"{i}. Fortify from '{action['from']}' to '{action['to']}'\n"
                prompt += f"   Available armies: {action['max_armies']} (can move 1-{action['max_armies']})\n"
                prompt += f"   Valid parameters: from_territory='{action['from']}', to_territory='{action['to']}', num_armies=1-{action['max_armies']}\n"
                
                # Provide specific valid examples
                prompt += f"   Example: fortify(from_territory='{action['from']}', to_territory='{action['to']}', num_armies=1)\n"
                if action['max_armies'] >= 2:
                    prompt += f"   Example: fortify(from_territory='{action['from']}', to_territory='{action['to']}', num_armies=2)\n"
                prompt += "\n"
        else:
            prompt += "- No valid fortify moves available\n"
        
        prompt += "CRITICAL FORTIFY RULES:\n"
        prompt += "1. You MUST use the fortify function with ALL required parameters\n"
        prompt += "2. Required parameters: from_territory, to_territory, num_armies\n"
        prompt += "3. Both territories must be yours and connected\n"
        prompt += "4. You must leave at least 1 army in the source territory\n"
        prompt += "5. num_armies must be a positive integer\n"
        prompt += "6. DO NOT use any other functions in fortify phase\n"
        prompt += "7. DO NOT write function calls as text - use the function calling mechanism\n"
        
        return prompt

    def _create_simple_move_armies_prompt(self, game_state: GameState) -> str:
        """Create a simplified move armies prompt focused on function calling."""
        my_player = game_state.players.get(self.name)
        if not my_player:
            return "Error: Could not find myself in the game state."

        player_id = my_player.id
        
        prompt = f"You are {self.name} playing Risk. You MUST use Ollama's function calling mechanism.\n\n"
        prompt += "🔥 CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings. 🔥\n\n"
        prompt += f"MOVE ARMIES PHASE: Move armies after conquering a territory.\n"
        prompt += f"Your territories: {', '.join(my_player.territories)}\n\n"
        
        # IMPORTANT: Only move_armies function is allowed in this phase
        prompt += "PHASE RESTRICTIONS:\n"
        prompt += "- ONLY move_armies function is allowed in MOVE ARMIES phase\n"
        prompt += "- DO NOT use reinforce, attack, fortify, or trade_cards functions\n"
        prompt += "- This phase happens after successfully conquering a territory\n\n"
        
        # List valid move armies actions
        valid_moves = get_valid_move_armies_actions(game_state, my_player)
        
        prompt += "AVAILABLE ACTIONS:\n"
        if valid_moves:
            for action in valid_moves:
                prompt += f"- move_armies: from_territory='{action['from']}', to_territory='{action['to']}', num_armies={action['min_armies']}-{action['max_armies']}\n"
        else:
            prompt += "- No valid move armies actions available\n"
        
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