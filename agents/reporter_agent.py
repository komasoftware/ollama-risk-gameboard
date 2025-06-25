"""
Reporter Agent for Risk Game - Dual Purpose Agent
Handles both prompt generation and function call feedback/corrections.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from .risk_api import GameState, GamePhase, RiskAPIClient
from .risk_rules import (
    get_valid_reinforce_actions, 
    get_valid_attack_actions, 
    get_valid_fortify_actions, 
    get_valid_move_armies_actions, 
    get_valid_card_trade_actions
)

logger = logging.getLogger(__name__)

class ReporterAgent:
    """
    Dual-purpose agent that:
    1. Generates focused, personalized prompts for each player
    2. Analyzes function call failures and provides corrections/coaching
    """
    
    def __init__(self):
        self.risk_client = RiskAPIClient()
        self.failure_patterns = {}  # Track failure patterns per player
        self.coaching_history = {}  # Track coaching provided to each player
        
    def generate_focused_prompt(self, player_name: str, game_state: GameState, phase: GamePhase) -> str:
        """
        Generate a focused, personalized prompt for a specific player in a specific phase.
        This reduces prompt complexity by only including relevant information.
        """
        my_player = game_state.players.get(player_name)
        if not my_player:
            return "Error: Player not found in game state."
            
        player_id = my_player.id
        
        # Base prompt structure
        prompt = f"You are {player_name} playing Risk. You MUST use Ollama's function calling mechanism.\n\n"
        prompt += "🔥 CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings. 🔥\n\n"
        prompt += f"CURRENT PHASE: {phase.value}\n"
        prompt += f"PLAYER ID: {player_id}\n\n"
        
        # Add phase-specific focused information
        if phase == GamePhase.REINFORCE:
            prompt += self._generate_reinforce_prompt(my_player, game_state)
        elif phase == GamePhase.ATTACK:
            prompt += self._generate_attack_prompt(my_player, game_state)
        elif phase == GamePhase.FORTIFY:
            prompt += self._generate_fortify_prompt(my_player, game_state)
        elif phase == GamePhase.MOVE_ARMIES:
            prompt += self._generate_move_armies_prompt(my_player, game_state)
            
        # Add personalized coaching based on failure patterns
        coaching = self._get_personalized_coaching(player_name, phase)
        if coaching:
            prompt += f"\nPERSONALIZED COACHING:\n{coaching}\n"
            
        # Add strategic guidance
        prompt += self._generate_strategic_guidance(my_player, game_state, phase)
        
        return prompt
    
    def analyze_function_call_failure(self, player_name: str, phase: GamePhase, 
                                    function_call: str, error_message: str) -> str:
        """
        Analyze a function call failure and provide specific feedback/corrections.
        This helps agents learn from their mistakes.
        """
        # Record the failure pattern
        if player_name not in self.failure_patterns:
            self.failure_patterns[player_name] = {}
        if phase.value not in self.failure_patterns[player_name]:
            self.failure_patterns[player_name][phase.value] = []
            
        self.failure_patterns[player_name][phase.value].append({
            'function_call': function_call,
            'error': error_message,
            'timestamp': self._get_timestamp()
        })
        
        # Generate specific feedback based on the error
        feedback = self._generate_failure_feedback(player_name, phase, function_call, error_message)
        
        # Store coaching for future prompts
        if player_name not in self.coaching_history:
            self.coaching_history[player_name] = {}
        self.coaching_history[player_name][phase.value] = feedback
        
        return feedback
    
    def _generate_reinforce_prompt(self, my_player: Any, game_state: GameState) -> str:
        """Generate focused reinforce phase prompt."""
        prompt = "REINFORCE PHASE - Place your armies on your territories.\n\n"
        
        # Get reinforcement armies
        reinforcement_armies = self.risk_client.get_reinforcement_armies()
        prompt += f"REINFORCEMENT ARMIES: {reinforcement_armies}\n\n"
        
        # Add card trading information if applicable
        if my_player.cards:
            prompt += f"YOUR CARDS ({len(my_player.cards)}): {[getattr(card, 'kind', str(card)) for card in my_player.cards]}\n"
            valid_trades = get_valid_card_trade_actions(game_state, my_player)
            if valid_trades:
                prompt += f"VALID CARD TRADES: {len(valid_trades)} available\n"
                for i, trade in enumerate(valid_trades[:3]):  # Show first 3 trades
                    prompt += f"  Trade {i+1}: Cards {trade['card_indices']} = {trade['armies_gained']} armies\n"
            prompt += "\n"
        
        # Add territory information
        prompt += f"YOUR TERRITORIES ({len(my_player.territories)}):\n"
        for territory in my_player.territories:
            prompt += f"  {territory.name}: {territory.armies} armies\n"
        
        # Add continent information
        continent_info = self._get_continent_analysis(my_player, game_state)
        if continent_info:
            prompt += f"\nCONTINENT ANALYSIS:\n{continent_info}\n"
        
        # Add valid actions
        valid_actions = get_valid_reinforce_actions(game_state, my_player, self.risk_client)
        if valid_actions:
            prompt += f"\nVALID REINFORCE ACTIONS: {len(valid_actions)} available\n"
            for action in valid_actions[:5]:  # Show first 5 actions
                prompt += f"  - Place {action['max_armies']} armies on {action['territory']}\n"
        
        return prompt
    
    def _generate_attack_prompt(self, my_player: Any, game_state: GameState) -> str:
        """Generate focused attack phase prompt."""
        prompt = "ATTACK PHASE - Attack enemy territories from your territories.\n\n"
        
        # Add territory information with adjacent enemies
        prompt += "YOUR TERRITORIES WITH ADJACENT ENEMIES:\n"
        attack_opportunities = 0
        for territory in my_player.territories:
            if territory.armies > 1:  # Can attack
                adjacent_enemies = self._get_adjacent_enemies(territory.name, game_state, my_player)
                if adjacent_enemies:
                    attack_opportunities += len(adjacent_enemies)
                    prompt += f"  {territory.name} ({territory.armies} armies) → {adjacent_enemies}\n"
        
        if attack_opportunities == 0:
            prompt += "  No attack opportunities available.\n"
        
        # Add valid attack actions
        valid_actions = get_valid_attack_actions(game_state, my_player)
        if valid_actions:
            prompt += f"\nVALID ATTACK ACTIONS: {len(valid_actions)} available\n"
            for action in valid_actions[:5]:  # Show first 5 actions
                prompt += f"  - Attack {action['to_territory']} from {action['from_territory']} with {action['max_dice']} dice\n"
        
        return prompt
    
    def _generate_fortify_prompt(self, my_player: Any, game_state: GameState) -> str:
        """Generate focused fortify phase prompt."""
        prompt = "FORTIFY PHASE - Move armies between your connected territories.\n\n"
        
        # Add territory information
        prompt += f"YOUR TERRITORIES ({len(my_player.territories)}):\n"
        for territory in my_player.territories:
            prompt += f"  {territory.name}: {territory.armies} armies\n"
        
        # Add valid fortify actions
        valid_actions = get_valid_fortify_actions(game_state, my_player)
        if valid_actions:
            prompt += f"\nVALID FORTIFY ACTIONS: {len(valid_actions)} available\n"
            for action in valid_actions[:5]:  # Show first 5 actions
                prompt += f"  - Move {action['max_armies']} armies from {action['from_territory']} to {action['to_territory']}\n"
        else:
            prompt += "\nNo valid fortify actions available.\n"
        
        return prompt
    
    def _generate_move_armies_prompt(self, my_player: Any, game_state: GameState) -> str:
        """Generate focused move armies phase prompt."""
        prompt = "MOVE ARMIES PHASE - Move armies after conquering a territory.\n\n"
        
        # Add valid move armies actions
        valid_actions = get_valid_move_armies_actions(game_state, my_player)
        if valid_actions:
            prompt += f"VALID MOVE ARMIES ACTIONS: {len(valid_actions)} available\n"
            for action in valid_actions:
                prompt += f"  - Move {action['max_armies']} armies from {action['from_territory']} to {action['to_territory']}\n"
        else:
            prompt += "No valid move armies actions available.\n"
        
        return prompt
    
    def _generate_strategic_guidance(self, my_player: Any, game_state: GameState, phase: GamePhase) -> str:
        """Generate strategic guidance based on current game state."""
        guidance = "\nSTRATEGIC GUIDANCE:\n"
        
        if phase == GamePhase.REINFORCE:
            guidance += "- Reinforce border territories adjacent to enemy territories\n"
            guidance += "- Consider continent bonuses when placing armies\n"
            guidance += "- Card trading gives bonus armies: 3 of a kind = 4-8 armies, 1 of each = 10 armies\n"
        elif phase == GamePhase.ATTACK:
            guidance += "- Attack from territories with more armies to territories with fewer armies\n"
            guidance += "- Target weak enemy positions and try to eliminate players\n"
            guidance += "- Consider continent control for bonus armies\n"
        elif phase == GamePhase.FORTIFY:
            guidance += "- Move armies to strengthen border territories\n"
            guidance += "- Protect continent bonuses by defending key territories\n"
            guidance += "- Consolidate armies for future attacks\n"
        
        # Add continent-specific guidance
        continent_guidance = self._get_continent_strategy(my_player, game_state)
        if continent_guidance:
            guidance += f"\nCONTINENT STRATEGY:\n{continent_guidance}\n"
        
        guidance += "\nCRITICAL INSTRUCTIONS:\n"
        guidance += "1. Use ONLY the function calling mechanism provided by Ollama\n"
        guidance += "2. DO NOT write function calls as text strings\n"
        guidance += "3. Make direct function calls with ALL required parameters\n"
        guidance += "4. Focus on the action, not the explanation\n"
        
        return guidance
    
    def _get_continent_analysis(self, my_player: Any, game_state: GameState) -> str:
        """Analyze continent control and provide insights."""
        continents = {
            "North America": {"territories": 9, "bonus": 5, "owned": 0},
            "South America": {"territories": 4, "bonus": 2, "owned": 0},
            "Europe": {"territories": 7, "bonus": 5, "owned": 0},
            "Africa": {"territories": 6, "bonus": 3, "owned": 0},
            "Asia": {"territories": 12, "bonus": 7, "owned": 0},
            "Australia": {"territories": 4, "bonus": 2, "owned": 0}
        }
        
        # Count owned territories per continent
        for territory in my_player.territories:
            continent = self._get_territory_continent(territory.name)
            if continent in continents:
                continents[continent]["owned"] += 1
        
        analysis = []
        for continent, info in continents.items():
            if info["owned"] > 0:
                progress = f"{info['owned']}/{info['territories']}"
                if info["owned"] == info["territories"]:
                    analysis.append(f"✅ {continent}: FULL CONTROL (+{info['bonus']} bonus)")
                else:
                    remaining = info["territories"] - info["owned"]
                    analysis.append(f"🔄 {continent}: {progress} territories ({remaining} to control for +{info['bonus']} bonus)")
        
        return "\n".join(analysis) if analysis else "No continent progress yet."
    
    def _get_continent_strategy(self, my_player: Any, game_state: GameState) -> str:
        """Provide continent-specific strategic advice."""
        # Find closest continent to control
        continent_progress = {}
        for territory in my_player.territories:
            continent = self._get_territory_continent(territory.name)
            if continent not in continent_progress:
                continent_progress[continent] = {"owned": 0, "total": 0, "bonus": 0}
            continent_progress[continent]["owned"] += 1
        
        # Add continent totals
        continent_totals = {
            "North America": 9, "South America": 4, "Europe": 7,
            "Africa": 6, "Asia": 12, "Australia": 4
        }
        continent_bonuses = {
            "North America": 5, "South America": 2, "Europe": 5,
            "Africa": 3, "Asia": 7, "Australia": 2
        }
        
        for continent in continent_progress:
            continent_progress[continent]["total"] = continent_totals.get(continent, 0)
            continent_progress[continent]["bonus"] = continent_bonuses.get(continent, 0)
        
        # Find best opportunities
        opportunities = []
        for continent, progress in continent_progress.items():
            if progress["owned"] > 0 and progress["owned"] < progress["total"]:
                remaining = progress["total"] - progress["owned"]
                opportunities.append((continent, remaining, progress["bonus"]))
        
        if not opportunities:
            return "Focus on expanding to new continents."
        
        # Sort by bonus/remaining ratio (efficiency)
        opportunities.sort(key=lambda x: x[2] / x[1], reverse=True)
        
        strategy = []
        for continent, remaining, bonus in opportunities[:3]:
            strategy.append(f"Prioritize {continent}: {remaining} territories needed for +{bonus} bonus")
        
        return "\n".join(strategy)
    
    def _get_adjacent_enemies(self, territory_name: str, game_state: GameState, my_player: Any) -> List[str]:
        """Get list of adjacent enemy territories."""
        # This is a simplified version - in a real implementation, you'd have adjacency data
        # For now, return empty list as placeholder
        return []
    
    def _get_territory_continent(self, territory_name: str) -> str:
        """Get the continent for a given territory."""
        # Simplified continent mapping - in real implementation, this would be comprehensive
        continent_map = {
            "Alaska": "North America", "Northwest Territory": "North America", "Greenland": "North America",
            "Alberta": "North America", "Ontario": "North America", "Quebec": "North America",
            "Western United States": "North America", "Eastern United States": "North America", "Central America": "North America",
            "Venezuela": "South America", "Peru": "South America", "Brazil": "South America", "Argentina": "South America",
            "Iceland": "Europe", "Great Britain": "Europe", "Scandinavia": "Europe", "Ukraine": "Europe",
            "Western Europe": "Europe", "Northern Europe": "Europe", "Southern Europe": "Europe",
            "North Africa": "Africa", "Egypt": "Africa", "East Africa": "Africa", "Congo": "Africa",
            "South Africa": "Africa", "Madagascar": "Africa",
            "Ural": "Asia", "Siberia": "Asia", "Yakutsk": "Asia", "Kamchatka": "Asia",
            "Irkutsk": "Asia", "Kazakhstan": "Asia", "China": "Asia", "Mongolia": "Asia",
            "Japan": "Asia", "Middle East": "Asia", "India": "Asia", "Southeast Asia": "Asia",
            "Indonesia": "Asia", "New Guinea": "Asia", "Western Australia": "Asia",
            "Eastern Australia": "Asia"
        }
        return continent_map.get(territory_name, "Unknown")
    
    def _generate_failure_feedback(self, player_name: str, phase: GamePhase, 
                                 function_call: str, error_message: str) -> str:
        """Generate specific feedback based on function call failure."""
        feedback = f"FUNCTION CALL FAILURE ANALYSIS:\n"
        feedback += f"Phase: {phase.value}\n"
        feedback += f"Error: {error_message}\n\n"
        
        # Common error patterns and solutions
        if "missing" in error_message.lower():
            feedback += "SOLUTION: Ensure ALL required parameters are provided.\n"
        elif "invalid" in error_message.lower():
            feedback += "SOLUTION: Check parameter values are valid for current game state.\n"
        elif "not found" in error_message.lower():
            feedback += "SOLUTION: Verify territory names and player IDs are correct.\n"
        elif "not allowed" in error_message.lower():
            feedback += "SOLUTION: This action is not valid in the current game state.\n"
        
        # Phase-specific guidance
        if phase == GamePhase.REINFORCE:
            feedback += "REINFORCE TIPS:\n"
            feedback += "- Use reinforce() function with territory name and number of armies\n"
            feedback += "- Card trading requires exactly 3 card indices\n"
        elif phase == GamePhase.ATTACK:
            feedback += "ATTACK TIPS:\n"
            feedback += "- Use attack() function with from_territory, to_territory, and num_dice\n"
            feedback += "- You can only attack from territories with >1 army\n"
        elif phase == GamePhase.FORTIFY:
            feedback += "FORTIFY TIPS:\n"
            feedback += "- Use fortify() function to move armies between connected territories\n"
            feedback += "- Must leave at least 1 army in source territory\n"
        
        return feedback
    
    def _get_personalized_coaching(self, player_name: str, phase: GamePhase) -> str:
        """Get personalized coaching based on previous failures."""
        if player_name in self.coaching_history and phase.value in self.coaching_history[player_name]:
            return self.coaching_history[player_name][phase.value]
        return ""
    
    def _get_timestamp(self) -> float:
        """Get current timestamp for tracking."""
        import time
        return time.time()
    
    def get_failure_statistics(self, player_name: str = None) -> Dict[str, Any]:
        """Get failure statistics for analysis."""
        if player_name:
            return self.failure_patterns.get(player_name, {})
        return self.failure_patterns
    
    def reset_failure_tracking(self, player_name: str = None):
        """Reset failure tracking for a player or all players."""
        if player_name:
            if player_name in self.failure_patterns:
                del self.failure_patterns[player_name]
            if player_name in self.coaching_history:
                del self.coaching_history[player_name]
        else:
            self.failure_patterns.clear()
            self.coaching_history.clear() 