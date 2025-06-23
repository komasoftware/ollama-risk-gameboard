# AI Agents Playing Risk

This project creates AI agents that play the classic board game Risk against each other using Ollama for AI decision-making and function calling to interact with a Risk API server.

## 🎯 Project Overview

The project focuses exclusively on developing AI agents that can play Risk autonomously. The Risk API server and UI are external dependencies that should not be modified.

## 🏗️ Architecture

- **AI Agents**: Python-based agents using Ollama for decision-making
- **Function Calling**: Agents use function calling to interact with the Risk API
- **Game Orchestration**: Manages multi-agent games and tournaments
- **Risk API Server**: External Rust server (unchanged)
- **Risk UI**: External React frontend (unchanged)

## 📋 Prerequisites

1. **Risk API Server**: Must be running on `http://localhost:8000`
   - Clone from: https://github.com/Krilecy/risk-board_game-server
   - Run with: `cargo run`

2. **Ollama**: Must be installed and running
   - Install from: https://ollama.ai
   - Pull the model: `ollama pull llama3.2`

3. **Python**: Python 3.8+ with pip

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Risk server** (in a separate terminal):
   ```bash
   cd risk-board_game-server
   cargo run
   ```

3. **Run the AI agents**:
   ```bash
   python main.py
   ```

## 🤖 Available Agents

- **SimpleAgent**: Basic strategic thinking
- **AggressiveAgent**: Focuses on attacking and expansion
- **DefensiveAgent**: Focuses on building strong defensive positions

## 🎮 Game Modes

1. **Single Game**: Run one game with multiple agents
2. **Tournament**: Run multiple games between all agent combinations

## 📁 Project Structure

```
risk/
├── agents/                    # AI agent implementations
│   ├── __init__.py
│   ├── risk_api.py           # Risk API client
│   ├── ollama_client.py      # Ollama integration with function calling
│   ├── base_agent.py         # Base agent class
│   ├── simple_agent.py       # Concrete agent implementations
│   └── game_orchestrator.py  # Game management and tournaments
├── main.py                   # Main script to run agents
├── requirements.txt          # Python dependencies
├── risk-board_game-server/   # Risk API server (external)
└── Risk-UI/                  # React frontend (external)
```

## 🔧 Configuration

### Agent Configuration

Agents can be configured with different:
- **Names**: Player names in the game
- **Models**: Ollama models to use (default: llama3.2)
- **Strategies**: Playing styles (balanced, aggressive, defensive)

### Game Configuration

- **Max turns**: Maximum turns per game (default: 1000)
- **Turn timeout**: Timeout for agent decisions (default: 30 seconds)
- **Games per matchup**: Number of games in tournaments

## 🧪 Testing

The system includes:
- Error handling for API failures
- Timeout handling for slow agent responses
- Game state validation
- Comprehensive logging

## 📊 Monitoring

The system tracks:
- Game results and winners
- Turn-by-turn actions
- Agent performance metrics
- Error rates and timeouts

## 🔄 Development

### Adding New Agents

1. Create a new class inheriting from `BaseAgent`
2. Implement the `make_decision` method
3. Optionally override phase-specific methods for custom behavior

### Adding New Strategies

1. Create strategy-specific prompts in agent classes
2. Implement strategy-specific decision logic
3. Test with different agent combinations

## 🐛 Troubleshooting

### Common Issues

1. **Risk server not running**: Make sure the server is running on port 8000
2. **Ollama not responding**: Check if Ollama is running and the model is pulled
3. **Function calling errors**: Verify the Risk API endpoints are working

### Debug Mode

Enable debug logging by setting environment variables:
```bash
export DEBUG=1
python main.py
```

## 📚 API Reference

### Risk API Endpoints

- `GET /game-state`: Get current game state
- `POST /reinforce`: Add armies to territory
- `POST /attack`: Attack between territories
- `POST /fortify`: Move armies between territories
- `POST /trade_cards`: Trade cards for armies
- `POST /advance_phase`: Move to next phase
- `POST /new-game`: Start new game

### Function Calling

Agents can call these functions:
- `get_game_state()`: Retrieve current game state
- `reinforce(territory, armies)`: Add armies to territory
- `attack(from_territory, to_territory, armies)`: Attack between territories
- `fortify(from_territory, to_territory, armies)`: Move armies
- `trade_cards(cards)`: Trade cards for armies
- `advance_phase()`: Move to next phase

## 🤝 Contributing

This project focuses on AI agent development. The Risk API server and UI are external dependencies and should not be modified.

## 📄 License

This project is for educational and research purposes. The Risk game mechanics are implemented by the external Risk API server. 