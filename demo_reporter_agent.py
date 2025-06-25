import json
import os
from agents.reporter_agent import ReporterAgent
from agents.risk_api import GamePhase
from types import SimpleNamespace

def load_json_game_state(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def create_mock_player(player_data):
    """Create a mock player object with the expected attributes."""
    player = SimpleNamespace()
    player.id = player_data['id']
    player.name = player_data['name']
    player.territories = []
    player.cards = []
    player.army_supply = player_data.get('army_supply', 0)
    player.total_armies = player_data.get('total_armies', 0)
    
    # Convert territories from names to objects with armies
    for territory_name in player_data.get('territories', []):
        territory = SimpleNamespace()
        territory.name = territory_name
        territory.armies = player_data['armies'].get(territory_name, 0)
        player.territories.append(territory)
    
    # Convert cards
    for card_data in player_data.get('cards', []):
        card = SimpleNamespace()
        card.kind = card_data['kind']
        card.territory = card_data.get('territory')
        player.cards.append(card)
    
    return player

def create_mock_game_state(data):
    """Create a mock GameState object from the real API structure."""
    game_state_data = data['game_state']
    
    # Map phase string to GamePhase enum
    phase_map = {
        'Reinforce': GamePhase.REINFORCE,
        'Attack': GamePhase.ATTACK,
        'Fortify': GamePhase.FORTIFY,
        'MoveArmies': GamePhase.MOVE_ARMIES
    }
    phase = phase_map.get(game_state_data['turn_phase'], GamePhase.REINFORCE)
    
    # Create mock players
    mock_players = {}
    for player_data in game_state_data['players']:
        player = create_mock_player(player_data)
        mock_players[player.name] = player
    
    # Create mock territories from board data
    mock_territories = {}
    if 'board' in game_state_data and 'territories' in game_state_data['board']:
        for territory_name, territory_data in game_state_data['board']['territories'].items():
            territory = SimpleNamespace()
            territory.name = territory_name
            territory.continent = territory_data['continent']
            territory.adjacent_territories = territory_data['adjacent_territories']
            # Find owner
            territory.owner = None
            for player_name, player in mock_players.items():
                if territory_name in [t.name for t in player.territories]:
                    territory.owner = player_name
                    territory.armies = player_data['armies'].get(territory_name, 0)
                    break
            mock_territories[territory_name] = territory
    
    # Build the mock GameState
    mock_game_state = SimpleNamespace(
        phase=phase,
        current_player=game_state_data['current_player'],
        players=mock_players,
        territories=mock_territories,
        reinforcement_armies=game_state_data.get('reinforcement_armies', 0)
    )
    
    return mock_game_state, phase

def main():
    testdata_dir = 'testdata'
    files = [f for f in os.listdir(testdata_dir) if f.endswith('.json')]
    reporter = ReporterAgent()
    
    for fname in sorted(files):
        print(f"\n=== Testing {fname} ===")
        data = load_json_game_state(os.path.join(testdata_dir, fname))
        
        # Create mock game state from real structure
        mock_game_state, phase = create_mock_game_state(data)
        
        # For each player, print the focused prompt
        for player_name in mock_game_state.players.keys():
            print(f"\n--- Player: {player_name} (Phase: {phase.value}) ---")
            
            prompt = reporter.generate_focused_prompt(player_name, mock_game_state, phase)
            print(prompt)
            print("-"*60)

if __name__ == "__main__":
    main() 