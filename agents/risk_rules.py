"""
risk_rules.py

Logic for computing valid Risk actions (reinforce, attack, fortify) for a given player and game state.
This module is designed to be independently testable and portable.
"""
from typing import List, Dict, Any, Set
from collections import defaultdict

# These imports assume the existing agent/game state dataclasses
from .risk_api import GameState, Player, Territory, GamePhase


def get_valid_reinforce_actions(game_state: Any, player: dict, risk_client=None) -> List[Dict[str, Any]]:
    """
    Return a list of valid reinforce actions for the player in the current game state.
    Each action is a dict: { 'territory': str, 'max_armies': int }
    
    Based on server logic: if reinforcement_armies > 0, player can reinforce any of their territories
    with up to reinforcement_armies armies.
    """
    actions = []
    
    # Check if we're in reinforce phase and have armies to place
    if getattr(game_state, 'phase', None) != GamePhase.REINFORCE:
        return actions
    
    # Get fresh reinforcement armies from server if possible
    if risk_client:
        reinforcement_armies = risk_client.get_reinforcement_armies()
    else:
        reinforcement_armies = getattr(game_state, 'reinforcement_armies', 0)
    
    if reinforcement_armies == 0:
        return actions
    
    # Player can reinforce any of their territories
    for territory_name in player['territories']:
        actions.append({
            'territory': territory_name,
            'max_armies': reinforcement_armies
        })
    
    return actions


def get_valid_attack_actions(game_state: Any, player: dict) -> List[Dict[str, Any]]:
    """
    Return a list of valid attack actions for the player in the current game state.
    Each action is a dict: { 'from': str, 'to': str, 'max_dice': int }
    
    Based on server logic: player can attack from any territory they own to any adjacent
    enemy territory, with max_dice = min(armies_in_from_territory - 1, 3)
    """
    actions = []
    
    # Check if we're in attack phase
    if getattr(game_state, 'phase', None) != GamePhase.ATTACK:
        return actions
    
    # For each territory the player owns
    for from_territory_name in player['territories']:
        from_territory = game_state.territories.get(from_territory_name)
        if not from_territory:
            continue
        
        # Check armies in the territory (must have at least 2 to attack)
        armies_in_territory = player['armies'].get(from_territory_name, 0)
        if armies_in_territory <= 1:
            continue
        
        # Calculate max dice (min of armies-1 and 3)
        max_dice = min(armies_in_territory - 1, 3)
        if max_dice <= 0:
            continue
        
        # Check adjacent territories
        for adjacent_name in from_territory.adjacent_territories:
            # Find owner of adjacent territory
            adjacent_owner = None
            for p in game_state.players:
                if adjacent_name in p['territories']:
                    adjacent_owner = p['name']
                    break
            if adjacent_owner is None or adjacent_owner == player['name']:
                continue
            
            actions.append({
                'from': from_territory_name,
                'to': adjacent_name,
                'max_dice': max_dice
            })
    
    return actions


def get_valid_fortify_actions(game_state: Any, player: dict) -> List[Dict[str, Any]]:
    """
    Return a list of valid fortify actions for the player in the current game state.
    Each action is a dict: { 'from': str, 'to': str, 'max_armies': int }
    
    Based on server logic: player can move armies from any territory to any connected
    territory they own, with max_armies = armies_in_from_territory - 1
    """
    actions = []
    
    # Check if we're in fortify phase
    if getattr(game_state, 'phase', None) != GamePhase.FORTIFY:
        return actions
    
    # For each territory the player owns
    player_territories_set = set(player['territories'])
    for from_territory_name in player['territories']:
        from_territory = game_state.territories.get(from_territory_name)
        if not from_territory:
            continue
        
        # Check armies in the territory (must have at least 2 to fortify)
        armies_in_territory = player['armies'].get(from_territory_name, 0)
        if armies_in_territory <= 1:
            continue
        
        # Calculate max armies that can be moved
        max_armies = armies_in_territory - 1
        if max_armies <= 0:
            continue
        
        # Find all connected territories using BFS
        connected_territories = _find_connected_territories(
            game_state, player, from_territory_name, player_territories_set
        )
        
        # Can fortify to any connected territory (except the source)
        for to_territory_name in connected_territories:
            if to_territory_name == from_territory_name:
                continue
            
            actions.append({
                'from': from_territory_name,
                'to': to_territory_name,
                'max_armies': max_armies
            })
    
    return actions


def _find_connected_territories(game_state: Any, player: dict, start_territory: str, player_territories_set: Set[str] = None) -> Set[str]:
    """
    Find all territories connected to start_territory via player-owned territories.
    Uses BFS to traverse the connected component.
    """
    if player_territories_set is None:
        player_territories_set = set(player['territories'])
    visited = set()
    queue = [start_territory]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        current_territory = game_state.territories.get(current)
        if not current_territory:
            continue
        for adjacent in current_territory.adjacent_territories:
            if adjacent not in visited and adjacent in player_territories_set:
                queue.append(adjacent)
    return visited


def get_valid_card_trade_actions(game_state: Any, player: dict) -> List[Dict[str, Any]]:
    """
    Return a list of valid card trade actions for the player.
    Each action is a dict: { 'card_indices': List[int] }
    
    Based on server logic: must trade exactly 3 cards in valid combinations.
    """
    actions = []
    
    # Check if we're in reinforce phase
    if getattr(game_state, 'phase', None) != GamePhase.REINFORCE:
        return actions
    
    # Must have at least 3 cards to trade
    if len(player['cards']) < 3:
        return actions
    
    # Generate all 3-card combinations
    from itertools import combinations
    seen_combinations = set()
    
    for combo in combinations(range(len(player['cards'])), 3):
        # Sort the combination to avoid duplicates
        sorted_combo = tuple(sorted(combo))
        if sorted_combo in seen_combinations:
            continue
        
        # Check if this is a valid trade combination
        card_kinds = [player['cards'][i]['kind'] if isinstance(player['cards'][i], dict) else getattr(player['cards'][i], 'kind', str(player['cards'][i])) for i in sorted_combo]
        if _is_valid_card_combination(card_kinds):
            seen_combinations.add(sorted_combo)
            actions.append({
                'card_indices': list(sorted_combo)
            })
    
    return actions


def _is_valid_card_combination(cards: List[str]) -> bool:
    """
    Check if a combination of 3 cards is valid for trading.
    Valid combinations are:
    - 3 of the same kind (Infantry, Cavalry, Artillery)
    - 1 of each kind (Infantry, Cavalry, Artillery)
    - Any combination with Jokers (which can substitute for any type)
    """
    if len(cards) != 3:
        return False
    
    # Count each type
    infantry_count = sum(1 for card in cards if card == "Infantry")
    cavalry_count = sum(1 for card in cards if card == "Cavalry")
    artillery_count = sum(1 for card in cards if card == "Artillery")
    joker_count = sum(1 for card in cards if card == "Joker")
    
    # Check valid combinations
    if infantry_count == 3 or cavalry_count == 3 or artillery_count == 3:
        return True
    
    if infantry_count == 1 and cavalry_count == 1 and artillery_count == 1:
        return True
    
    # Check combinations with jokers (but not three jokers)
    if joker_count > 0 and joker_count < 3:
        # Jokers can substitute for any type
        total_non_jokers = infantry_count + cavalry_count + artillery_count
        if total_non_jokers + joker_count == 3:
            return True
    
    return False


def get_valid_move_armies_actions(game_state: Any, player: dict) -> List[Dict[str, Any]]:
    """
    Return a list of valid move armies actions for the player in the current game state.
    Each action is a dict: { 'from': str, 'to': str, 'max_armies': int, 'min_armies': int }
    
    Based on server logic: player can move armies from the attacking territory to the conquered territory
    after a successful attack, with constraints on min/max armies.
    """
    actions = []
    
    # Check if we're in move armies phase
    if getattr(game_state, 'phase', None) != GamePhase.MOVE_ARMIES:
        return actions
    
    # Parse the possible actions from the game state
    if not hasattr(game_state, 'possible_actions'):
        return actions
    
    for action in game_state.possible_actions:
        if isinstance(action, dict) and 'MoveArmies' in action:
            move_action = action['MoveArmies']
            actions.append({
                'from': move_action['from'],
                'to': move_action['to'],
                'max_armies': move_action['max_armies'],
                'min_armies': move_action['min_armies']
            })
    
    return actions 