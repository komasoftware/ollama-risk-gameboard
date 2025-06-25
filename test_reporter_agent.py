"""
Test suite for Reporter Agent functionality and integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from agents.reporter_agent import ReporterAgent
from agents.risk_api import GameState, GamePhase
from agents.simple_agent import SimpleAgent
from agents.game_orchestrator import GameOrchestrator

class TestReporterAgent:
    """Test cases for Reporter Agent functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.reporter_agent = ReporterAgent()
        
    def test_reporter_agent_initialization(self):
        """Test that ReporterAgent initializes correctly."""
        assert self.reporter_agent is not None
        assert hasattr(self.reporter_agent, 'failure_patterns')
        assert hasattr(self.reporter_agent, 'coaching_history')
        assert hasattr(self.reporter_agent, 'risk_client')
        
    def test_generate_focused_prompt_reinforce(self):
        """Test focused prompt generation for reinforce phase."""
        # Mock game state
        mock_game_state = Mock(spec=GameState)
        mock_game_state.phase = GamePhase.REINFORCE
        
        # Mock player
        mock_player = Mock()
        mock_player.id = 0
        mock_player.territories = [Mock(name="Alaska", armies=3), Mock(name="Ontario", armies=2)]
        mock_player.cards = []
        
        mock_game_state.players = {"TestPlayer": mock_player}
        
        # Mock risk client
        with patch.object(self.reporter_agent.risk_client, 'get_reinforcement_armies', return_value=5):
            prompt = self.reporter_agent.generate_focused_prompt("TestPlayer", mock_game_state, GamePhase.REINFORCE)
            
        assert prompt is not None
        assert "TestPlayer" in prompt
        assert "REINFORCE PHASE" in prompt
        assert "REINFORCEMENT ARMIES: 5" in prompt
        assert "PLAYER ID: 0" in prompt
        
    def test_analyze_function_call_failure(self):
        """Test function call failure analysis."""
        player_name = "TestPlayer"
        phase = GamePhase.REINFORCE
        function_call = "reinforce(player_id=0, territory='InvalidTerritory', num_armies=3)"
        error_message = "Territory not found"
        
        feedback = self.reporter_agent.analyze_function_call_failure(
            player_name, phase, function_call, error_message
        )
        
        assert feedback is not None
        assert "FUNCTION CALL FAILURE ANALYSIS" in feedback
        assert "REINFORCE" in feedback
        assert "Territory not found" in feedback
        
        # Check that failure pattern was recorded
        assert player_name in self.reporter_agent.failure_patterns
        assert phase.value in self.reporter_agent.failure_patterns[player_name]
        
    def test_get_failure_statistics(self):
        """Test failure statistics retrieval."""
        # Add some test failure data
        self.reporter_agent.failure_patterns["TestPlayer"] = {
            "reinforce": [{"function_call": "test", "error": "test error", "timestamp": 123.0}]
        }
        
        stats = self.reporter_agent.get_failure_statistics("TestPlayer")
        assert "reinforce" in stats
        assert len(stats["reinforce"]) == 1
        
        # Test global statistics
        all_stats = self.reporter_agent.get_failure_statistics()
        assert "TestPlayer" in all_stats
        
    def test_reset_failure_tracking(self):
        """Test failure tracking reset functionality."""
        # Add test data
        self.reporter_agent.failure_patterns["TestPlayer"] = {"test": []}
        self.reporter_agent.coaching_history["TestPlayer"] = {"test": "coaching"}
        
        # Reset for specific player
        self.reporter_agent.reset_failure_tracking("TestPlayer")
        assert "TestPlayer" not in self.reporter_agent.failure_patterns
        assert "TestPlayer" not in self.reporter_agent.coaching_history
        
        # Test global reset
        self.reporter_agent.failure_patterns["TestPlayer2"] = {"test": []}
        self.reporter_agent.reset_failure_tracking()
        assert len(self.reporter_agent.failure_patterns) == 0
        assert len(self.reporter_agent.coaching_history) == 0

class TestReporterAgentIntegration:
    """Test cases for Reporter Agent integration with other components."""
    
    def test_game_orchestrator_integration(self):
        """Test that GameOrchestrator properly integrates ReporterAgent."""
        agents = [SimpleAgent("TestPlayer")]
        orchestrator = GameOrchestrator(agents)
        
        # Check that ReporterAgent was initialized
        assert hasattr(orchestrator, 'reporter_agent')
        assert isinstance(orchestrator.reporter_agent, ReporterAgent)
        
    def test_simple_agent_focused_prompt_integration(self):
        """Test that SimpleAgent uses focused prompts from ReporterAgent."""
        agent = SimpleAgent("TestPlayer")
        
        # Set a focused prompt
        agent._current_focused_prompt = "FOCUSED PROMPT FROM REPORTER AGENT"
        
        # Mock game state
        mock_game_state = Mock(spec=GameState)
        mock_game_state.players = {"TestPlayer": Mock()}
        
        # Test that focused prompt is used
        prompt = agent._create_prompt(mock_game_state)
        assert "FOCUSED PROMPT FROM REPORTER AGENT" in prompt
        
        # Test that focused prompt is cleared after use
        assert agent._current_focused_prompt is None
        
    def test_simple_agent_fallback_prompt(self):
        """Test that SimpleAgent falls back to original prompt when no focused prompt is available."""
        agent = SimpleAgent("TestPlayer")
        
        # Mock game state
        mock_game_state = Mock(spec=GameState)
        mock_game_state.phase = GamePhase.REINFORCE
        mock_player = Mock()
        mock_player.id = 0
        mock_player.territories = []
        mock_player.cards = []  # Mock cards as empty list
        mock_player.armies = 5  # Mock armies
        mock_game_state.players = {"TestPlayer": mock_player}
        
        # Test fallback prompt generation
        prompt = agent._create_prompt(mock_game_state)
        assert "TestPlayer" in prompt
        assert "REINFORCE PHASE" in prompt
        assert "PLAYER ID: 0" in prompt

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 