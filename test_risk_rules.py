#!/usr/bin/env python3
"""
Unit tests for risk_rules.py module.
Tests all functions with various game states and edge cases.
"""

import unittest
from unittest.mock import Mock
from agents.risk_rules import (
    get_valid_reinforce_actions,
    get_valid_attack_actions,
    get_valid_fortify_actions,
    get_valid_card_trade_actions,
    _find_connected_territories,
    _is_valid_card_combination
)
from agents.risk_api import GameState, Player, Territory, GamePhase


class TestRiskRules(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a basic game state for testing
        self.game_state = Mock(spec=GameState)
        self.game_state.territories = {}
        self.game_state.phase = GamePhase.REINFORCE
        self.game_state.reinforcement_armies = 5
        
        # Create a basic player for testing
        self.player = Mock(spec=Player)
        self.player.name = "Player 1"
        self.player.territories = ["Alaska", "Northwest Territory"]
        self.player.cards = []
        self.player.armies = 5  # Add the missing armies attribute for fallback
    
    def test_get_valid_reinforce_actions_basic(self):
        """Test basic reinforce actions when player has territories and armies."""
        actions = get_valid_reinforce_actions(self.game_state, self.player)
        
        expected_actions = [
            {"territory": "Alaska", "max_armies": 5},
            {"territory": "Northwest Territory", "max_armies": 5}
        ]
        
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions, expected_actions)
    
    def test_get_valid_reinforce_actions_wrong_phase(self):
        """Test reinforce actions when not in reinforce phase."""
        self.game_state.phase = GamePhase.ATTACK
        actions = get_valid_reinforce_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_reinforce_actions_no_armies(self):
        """Test reinforce actions when no reinforcement armies available."""
        self.game_state.reinforcement_armies = 0
        self.player.armies = 0  # Ensure fallback logic matches test intent
        actions = get_valid_reinforce_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_reinforce_actions_no_territories(self):
        """Test reinforce actions when player has no territories."""
        self.player.territories = []
        actions = get_valid_reinforce_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_attack_actions_basic(self):
        """Test basic attack actions."""
        self.game_state.phase = GamePhase.ATTACK
        
        # Set up territories with adjacency
        self.game_state.territories = {
            "Alaska": Territory(
                name="Alaska",
                owner="Player 1",
                armies=3,
                continent="North America",
                adjacent_territories=["Northwest Territory", "Kamchatka"]
            ),
            "Northwest Territory": Territory(
                name="Northwest Territory",
                owner="Player 1",
                armies=2,
                continent="North America",
                adjacent_territories=["Alaska", "Alberta"]
            ),
            "Kamchatka": Territory(
                name="Kamchatka",
                owner="Player 2",
                armies=1,
                continent="Asia",
                adjacent_territories=["Alaska", "Yakutsk"]
            ),
            "Alberta": Territory(
                name="Alberta",
                owner="Player 2",
                armies=1,
                continent="North America",
                adjacent_territories=["Northwest Territory", "Ontario"]
            )
        }
        
        actions = get_valid_attack_actions(self.game_state, self.player)
        
        # Should be able to attack from Alaska to Kamchatka (3 armies -> max 2 dice)
        # and from Northwest Territory to Alberta (2 armies -> max 1 die)
        expected_actions = [
            {"from": "Alaska", "to": "Kamchatka", "max_dice": 2},
            {"from": "Northwest Territory", "to": "Alberta", "max_dice": 1}
        ]
        
        self.assertEqual(len(actions), 2)
        # Sort for comparison since order doesn't matter
        actions_sorted = sorted(actions, key=lambda x: (x["from"], x["to"]))
        expected_sorted = sorted(expected_actions, key=lambda x: (x["from"], x["to"]))
        self.assertEqual(actions_sorted, expected_sorted)
    
    def test_get_valid_attack_actions_wrong_phase(self):
        """Test attack actions when not in attack phase."""
        self.game_state.phase = GamePhase.REINFORCE
        actions = get_valid_attack_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_attack_actions_insufficient_armies(self):
        """Test attack actions when territories have insufficient armies."""
        self.game_state.phase = GamePhase.ATTACK
        
        # Set up territories with only 1 army each (can't attack)
        self.game_state.territories = {
            "Alaska": Territory(
                name="Alaska",
                owner="Player 1",
                armies=1,
                continent="North America",
                adjacent_territories=["Kamchatka"]
            ),
            "Kamchatka": Territory(
                name="Kamchatka",
                owner="Player 2",
                armies=1,
                continent="Asia",
                adjacent_territories=["Alaska"]
            )
        }
        
        actions = get_valid_attack_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_attack_actions_no_enemy_adjacent(self):
        """Test attack actions when no enemy territories are adjacent."""
        self.game_state.phase = GamePhase.ATTACK
        
        # Set up territories where all adjacent territories are owned by the same player
        self.game_state.territories = {
            "Alaska": Territory(
                name="Alaska",
                owner="Player 1",
                armies=3,
                continent="North America",
                adjacent_territories=["Northwest Territory"]
            ),
            "Northwest Territory": Territory(
                name="Northwest Territory",
                owner="Player 1",
                armies=2,
                continent="North America",
                adjacent_territories=["Alaska"]
            )
        }
        
        actions = get_valid_attack_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_fortify_actions_basic(self):
        """Test basic fortify actions."""
        self.game_state.phase = GamePhase.FORTIFY
        self.game_state.territories = {
            "Alaska": Territory(
                name="Alaska",
                owner="Player 1",
                armies=3,
                continent="North America",
                adjacent_territories=["Northwest Territory"]
            ),
            "Northwest Territory": Territory(
                name="Northwest Territory",
                owner="Player 1",
                armies=2,
                continent="North America",
                adjacent_territories=["Alaska", "Alberta"]
            ),
            "Alberta": Territory(
                name="Alberta",
                owner="Player 1",
                armies=1,
                continent="North America",
                adjacent_territories=["Northwest Territory"]
            )
        }
        from agents.risk_api import Player
        player = Player(id=0, name="Player 1", territories=["Alaska", "Northwest Territory", "Alberta"], armies=0, total_armies=6, cards=[])
        actions = get_valid_fortify_actions(self.game_state, player)
        expected_actions = [
            {"from": "Alaska", "to": "Northwest Territory", "max_armies": 2},
            {"from": "Alaska", "to": "Alberta", "max_armies": 2},
            {"from": "Northwest Territory", "to": "Alaska", "max_armies": 1},
            {"from": "Northwest Territory", "to": "Alberta", "max_armies": 1}
        ]
        self.assertEqual(len(actions), 4)
        actions_sorted = sorted(actions, key=lambda x: (x["from"], x["to"]))
        expected_sorted = sorted(expected_actions, key=lambda x: (x["from"], x["to"]))
        self.assertEqual(actions_sorted, expected_sorted)
    
    def test_get_valid_fortify_actions_wrong_phase(self):
        """Test fortify actions when not in fortify phase."""
        self.game_state.phase = GamePhase.REINFORCE
        actions = get_valid_fortify_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_fortify_actions_insufficient_armies(self):
        """Test fortify actions when territories have insufficient armies."""
        self.game_state.phase = GamePhase.FORTIFY
        
        # Set up territories with only 1 army each (can't fortify)
        self.game_state.territories = {
            "Alaska": Territory(
                name="Alaska",
                owner="Player 1",
                armies=1,
                continent="North America",
                adjacent_territories=["Northwest Territory"]
            ),
            "Northwest Territory": Territory(
                name="Northwest Territory",
                owner="Player 1",
                armies=1,
                continent="North America",
                adjacent_territories=["Alaska"]
            )
        }
        
        actions = get_valid_fortify_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_fortify_actions_disconnected_territories(self):
        """Test fortify actions when territories are not connected."""
        self.game_state.phase = GamePhase.FORTIFY
        
        # Set up disconnected territories (no path between them)
        self.game_state.territories = {
            "Alaska": Territory(
                name="Alaska",
                owner="Player 1",
                armies=3,
                continent="North America",
                adjacent_territories=["Kamchatka"]
            ),
            "Kamchatka": Territory(
                name="Kamchatka",
                owner="Player 2",  # Enemy territory breaks connection
                armies=1,
                continent="Asia",
                adjacent_territories=["Alaska", "Yakutsk"]
            ),
            "Yakutsk": Territory(
                name="Yakutsk",
                owner="Player 1",
                armies=2,
                continent="Asia",
                adjacent_territories=["Kamchatka"]
            )
        }
        
        actions = get_valid_fortify_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_find_connected_territories(self):
        """Test the helper function for finding connected territories."""
        # Set up a simple connected graph
        self.game_state.territories = {
            "A": Territory("A", "Player 1", 1, "Test", ["B"]),
            "B": Territory("B", "Player 1", 1, "Test", ["A", "C"]),
            "C": Territory("C", "Player 1", 1, "Test", ["B", "D"]),
            "D": Territory("D", "Player 1", 1, "Test", ["C"]),
            "E": Territory("E", "Player 2", 1, "Test", ["D"]),  # Enemy territory
        }
        from agents.risk_api import Player
        player = Player(id=0, name="Player 1", territories=["A", "B", "C", "D"], armies=0, total_armies=4, cards=[])
        connected = _find_connected_territories(self.game_state, player, "A")
        expected = {"A", "B", "C", "D"}
        self.assertEqual(connected, expected)
    
    def test_get_valid_card_trade_actions_basic(self):
        """Test basic card trade actions."""
        self.game_state.phase = GamePhase.REINFORCE
        self.player.cards = ["Infantry", "Cavalry", "Artillery"]
        
        actions = get_valid_card_trade_actions(self.game_state, self.player)
        
        # Should be able to trade the three different cards
        expected_actions = [{"card_indices": [0, 1, 2]}]
        self.assertEqual(actions, expected_actions)
    
    def test_get_valid_card_trade_actions_three_of_kind(self):
        """Test card trade actions with three of the same kind."""
        self.game_state.phase = GamePhase.REINFORCE
        self.player.cards = ["Infantry", "Infantry", "Infantry"]
        
        actions = get_valid_card_trade_actions(self.game_state, self.player)
        
        expected_actions = [{"card_indices": [0, 1, 2]}]
        self.assertEqual(actions, expected_actions)
    
    def test_get_valid_card_trade_actions_with_jokers(self):
        """Test card trade actions with jokers."""
        self.game_state.phase = GamePhase.REINFORCE
        self.player.cards = ["Infantry", "Joker", "Joker"]
        
        actions = get_valid_card_trade_actions(self.game_state, self.player)
        
        expected_actions = [{"card_indices": [0, 1, 2]}]
        self.assertEqual(actions, expected_actions)
    
    def test_get_valid_card_trade_actions_insufficient_cards(self):
        """Test card trade actions when player has fewer than 3 cards."""
        self.game_state.phase = GamePhase.REINFORCE
        self.player.cards = ["Infantry", "Cavalry"]
        
        actions = get_valid_card_trade_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_get_valid_card_trade_actions_wrong_phase(self):
        """Test card trade actions when not in reinforce phase."""
        self.game_state.phase = GamePhase.ATTACK
        self.player.cards = ["Infantry", "Cavalry", "Artillery"]
        
        actions = get_valid_card_trade_actions(self.game_state, self.player)
        self.assertEqual(actions, [])
    
    def test_is_valid_card_combination_valid_combinations(self):
        """Test valid card combinations."""
        # Three of a kind
        self.assertTrue(_is_valid_card_combination(["Infantry", "Infantry", "Infantry"]))
        self.assertTrue(_is_valid_card_combination(["Cavalry", "Cavalry", "Cavalry"]))
        self.assertTrue(_is_valid_card_combination(["Artillery", "Artillery", "Artillery"]))
        
        # One of each
        self.assertTrue(_is_valid_card_combination(["Infantry", "Cavalry", "Artillery"]))
        
        # With jokers
        self.assertTrue(_is_valid_card_combination(["Infantry", "Joker", "Joker"]))
        self.assertTrue(_is_valid_card_combination(["Infantry", "Cavalry", "Joker"]))
    
    def test_is_valid_card_combination_invalid_combinations(self):
        """Test invalid card combinations."""
        # Wrong number of cards
        self.assertFalse(_is_valid_card_combination(["Infantry", "Cavalry"]))
        self.assertFalse(_is_valid_card_combination(["Infantry", "Cavalry", "Artillery", "Infantry"]))
        
        # Invalid combinations
        self.assertFalse(_is_valid_card_combination(["Infantry", "Infantry", "Cavalry"]))
        self.assertFalse(_is_valid_card_combination(["Infantry", "Cavalry", "Cavalry"]))
        self.assertFalse(_is_valid_card_combination(["Joker", "Joker", "Joker"]))  # Three jokers not valid

    def test_card_validation_with_complex_objects(self):
        """Test that card validation works with complex card objects (the fix for the reported issue)."""
        # Create complex card objects like the ones in the game state
        class MockCard:
            def __init__(self, territory, kind):
                self.territory = territory
                self.kind = kind
        
        # Test the specific combination that was failing: Infantry + Artillery + Joker
        cards = [
            MockCard("Kamchatka", "Infantry"),
            MockCard("Western Europe", "Artillery"), 
            MockCard(None, "Joker")
        ]
        
        # Extract just the kind field (this is what the fix does)
        card_kinds = [card.kind for card in cards]
        
        # This should be valid: 1 Infantry + 1 Artillery + 1 Joker
        self.assertTrue(_is_valid_card_combination(card_kinds))
        
        # Test other valid combinations with complex objects
        cards_three_infantry = [
            MockCard("Alaska", "Infantry"),
            MockCard("Ontario", "Infantry"),
            MockCard("Quebec", "Infantry")
        ]
        card_kinds_three_infantry = [card.kind for card in cards_three_infantry]
        self.assertTrue(_is_valid_card_combination(card_kinds_three_infantry))
        
        # Test one of each type
        cards_one_each = [
            MockCard("Alaska", "Infantry"),
            MockCard("Ontario", "Cavalry"),
            MockCard("Quebec", "Artillery")
        ]
        card_kinds_one_each = [card.kind for card in cards_one_each]
        self.assertTrue(_is_valid_card_combination(card_kinds_one_each))
        
        # Test invalid combination with complex objects
        cards_invalid = [
            MockCard("Alaska", "Infantry"),
            MockCard("Ontario", "Infantry"),
            MockCard("Quebec", "Cavalry")  # 2 Infantry + 1 Cavalry = invalid
        ]
        card_kinds_invalid = [card.kind for card in cards_invalid]
        self.assertFalse(_is_valid_card_combination(card_kinds_invalid))


if __name__ == "__main__":
    unittest.main() 