# ADK Game Round Agent

LoopAgent that coordinates complete Risk game rounds by orchestrating player turns in sequence.

## Overview

The Game Round Agent is an ADK LoopAgent that manages complete Risk game rounds. It uses a sub-agent (GameCoordinator) to handle the game logic and coordinate between multiple player agents.

## Architecture

```
ADK Web UI -> Game Round Agent (LoopAgent) -> Game Coordinator (LlmAgent) -> Player Agents
```

## Features

- **LoopAgent**: Orchestrates complete game rounds using ADK's LoopAgent
- **Game Coordination**: Manages player turns in sequence
- **Built-in Web UI**: Visual interface for game control and monitoring
- **Configurable Players**: Supports 1-6 players
- **Game State Management**: Tracks game progress and completion
- **Timeout Handling**: Configurable timeouts for games and turns

## Quick Start

### Prerequisites

1. **Google Cloud Setup**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

### Running the Game Round Agent

1. **Start ADK Web UI**
   ```bash
   adk web
   ```

2. **Open Web UI**
   - Navigate to the URL shown in the terminal (usually http://localhost:8080)
   - The game round agent will be available for interaction

3. **Test the Agent**
   ```bash
   python test_agent.py
   ```

## Agent Capabilities

The Game Round Agent can:

- **Start New Games**: Initialize games with 1-6 players
- **Coordinate Rounds**: Manage complete game rounds
- **Player Turn Management**: Call each player in sequence
- **Game State Monitoring**: Track game progress and completion
- **Timeout Handling**: Manage game and turn timeouts

## Available Tools

- `start_new_game`: Start a new game with specified number of players
- `get_game_state`: Get the current game state
- `play_player_turn`: Play a turn for a specific player
- `check_game_complete`: Check if the game is complete

## Usage Examples

### Basic Interaction

1. Start the ADK Web UI: `adk web`
2. Open the browser interface
3. Send messages like:
   - "Start a new game with 4 players"
   - "Play a complete round"
   - "Check the current game state"

### Game Round Process

1. **Start Game**: Initialize with specified number of players
2. **Player Turns**: Call each player in sequence (1, 2, 3, etc.)
3. **State Monitoring**: Check game state after each turn
4. **Completion Check**: Detect when game is complete
5. **Round Summary**: Provide round results and status

## Configuration

### Environment Variables

- `PROJECT_ID`: Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION`: AI services location
- `MAX_PLAYERS`: Maximum number of players (1-6)
- `GAME_TIMEOUT`: Game timeout in seconds
- `TURN_TIMEOUT`: Turn timeout in seconds
- `PLAYER_AGENT_URLS`: URLs for player agents (future use)

### Game Configuration

- **Max Players**: 6 (configurable)
- **Game Timeout**: 300 seconds (5 minutes)
- **Turn Timeout**: 60 seconds (1 minute)

## Development

### Adding New Features

1. **New Tools**: Add FunctionTool definitions to the agent
2. **Game Logic**: Extend the GameCoordinator sub-agent
3. **Player Communication**: Implement player agent calling
4. **State Management**: Add game state persistence

### Debugging

- Use ADK's built-in debugging features
- Monitor game round progress in Web UI
- Check logs for detailed execution flow
- Review sub-agent interactions

## Future Enhancements

1. **Player Agent Integration**: Direct communication with player agents
2. **MCP Server Integration**: Connect to Risk MCP server for game actions
3. **Game State Persistence**: Save and restore game states
4. **Advanced Game Logic**: Support for different game modes
5. **Real-time Updates**: Live game progress monitoring

## Troubleshooting

### Common Issues

1. **Game Not Starting**
   - Check environment variables
   - Verify Google Cloud credentials
   - Ensure ADK is properly installed

2. **Player Turn Failures**
   - Check player agent availability
   - Verify communication protocols
   - Review timeout settings

3. **LoopAgent Issues**
   - Check sub-agent configuration
   - Verify tool definitions
   - Review agent instructions

### Getting Help

- Check ADK documentation: https://ai.google.dev/docs/adk
- Review agent logs for detailed error messages
- Use ADK's built-in debugging features 