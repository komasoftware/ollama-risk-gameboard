# ADK Risk Player Agent

Simple Google ADK agent for playing Risk games using MCP tools.

## Overview

This is a simplified ADK agent that uses Google's Agent Development Kit (ADK) to interact with the Risk game through MCP (Model Context Protocol) tools. The agent follows the proper ADK structure with each agent in its own directory.

## Architecture

```
ADK Web UI -> Player Agent -> MCP Tools -> Risk API Server
```

## Quick Start

### Prerequisites

1. **Google Cloud Setup**
   ```bash
   # Install Google Cloud CLI
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

### Running the Player Agent

1. **Start ADK Web UI**
   ```bash
   adk web
   ```

2. **Open Web UI**
   - Navigate to the URL shown in the terminal (usually http://localhost:8080)
   - The player agent will be available for interaction

3. **Test the Agent**
   ```bash
   python test_agent.py
   ```

## Agent Structure

Following ADK best practices, the agent is structured as:

```
player/
├── agent.py          # Main ADK agent definition
├── test_agent.py     # Test script
├── requirements.txt  # Dependencies
├── env.example      # Environment template
└── README.md        # This file
```

## Agent Capabilities

The Risk Player Agent can:

- **Get Game State**: Check current game status, players, territories
- **Play Turns**: Execute complete turns following Risk rules
- **Make Strategic Decisions**: Choose actions based on game state
- **Follow Game Phases**: Reinforce → Attack → Fortify
- **Use MCP Tools**: Interact with Risk API through standardized tools

## MCP Tools Available

- `get_game_state` - Get current game state
- `get_possible_actions` - Get available actions
- `get_reinforcement_armies` - Get reinforcement armies
- `reinforce` - Add armies to territories
- `attack` - Attack enemy territories
- `fortify` - Move armies between territories
- `move_armies` - Move armies after conquest
- `trade_cards` - Trade cards for bonus armies
- `advance_phase` - Move to next game phase
- `new_game` - Start a new game

## Usage Examples

### Basic Interaction

1. Start the ADK Web UI: `adk web`
2. Open the browser interface
3. Send messages like:
   - "What's the current game state?"
   - "Start a new game with 4 players"
   - "Play a turn for player 1"

### Testing

```bash
# Test agent configuration
python test_agent.py

# Run ADK Web UI
adk web
```

## Configuration

### Environment Variables

- `PROJECT_ID`: Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION`: AI services location
- `MCP_SERVER_URL`: MCP server endpoint
- `GEMINI_MODEL`: Gemini model to use

### MCP Server

The agent connects to the Risk MCP server at:
`https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/stream`

## Development

### Adding New Agents

1. Create a new directory for each agent
2. Create `agent.py` with the ADK agent definition
3. Add MCP tools as needed
4. Test with `adk web`

### Debugging

- Use ADK's built-in debugging features
- Check MCP server connectivity
- Monitor agent responses in Web UI
- Review logs for detailed execution flow

## Comparison with Previous Implementation

### What We Simplified

- **Removed A2A Protocol**: No more complex agent-to-agent communication
- **Removed Session Management**: ADK handles sessions automatically
- **Removed Artifact Services**: ADK provides built-in artifact management
- **Simplified Deployment**: Just run `adk web` instead of complex Docker setup
- **Proper ADK Structure**: Each agent in its own directory with `agent.py`

### What We Kept

- **MCP Tools**: Same powerful Risk game tools
- **Gemini Model**: Same AI model for decision making
- **Game Logic**: Same Risk game rules and strategies

## Benefits

1. **Simpler Architecture**: Fewer moving parts
2. **Built-in Web UI**: No need for custom interfaces
3. **Better Debugging**: ADK provides excellent debugging tools
4. **Easier Testing**: Direct interaction through Web UI
5. **Faster Development**: Less boilerplate code
6. **Proper ADK Structure**: Follows Google's ADK best practices

## Troubleshooting

### Common Issues

1. **MCP Connection Failed**
   - Check `MCP_SERVER_URL` in environment
   - Verify MCP server is running

2. **Google Cloud Authentication**
   - Run `gcloud auth login`
   - Set correct `PROJECT_ID`

3. **ADK Web UI Not Starting**
   - Check if port 8080 is available
   - Verify all dependencies are installed

### Getting Help

- Check ADK documentation: https://ai.google.dev/docs/adk
- Review MCP server logs
- Use ADK's built-in debugging features 