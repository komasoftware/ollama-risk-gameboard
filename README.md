# Risk Agentic Web Platform

A sophisticated agentic web platform that demonstrates AI agents playing the classic Risk board game using cutting-edge technologies: **Google ADK (Agent Development Kit)**, **MCP (Model Context Protocol)**, and **A2A (Agent-to-Agent) protocol**.

## 🎯 Overview

This project showcases a complete agentic web architecture where AI agents can autonomously play Risk through multiple layers of abstraction:

- **Risk Game Server**: Rust-based game engine with REST API
- **MCP Server**: Protocol bridge exposing game functions as tools
- **ADK Agents**: Google's Agent Development Kit with Gemini integration and built-in Web UI
- **A2A Protocol**: Agent-to-agent communication framework
- **Workflow Agent**: ADK Loop agent orchestrating multi-player games

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ADK Web UI    │    │   ADK Loop      │    │   MCP Server    │
│   (Built-in)    │◄──►│   (Workflow)    │◄──►│   (HTTP/SSE)    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Control  │    │   A2A Protocol  │    │   Risk API      │
│   (Game Master) │    │   (Agent Exec)  │    │   (Rust Server) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Player Agents │    │   Game State    │
                       │   (ADK Agents)  │    │   (JSON Config) │
                       └─────────────────┘    └─────────────────┘
```

## 🚀 Key Components

### 1. **Risk Game Engine** (`game_config.json`)
- Complete Risk board game configuration
- 42 territories across 6 continents
- Player states, armies, and game phases
- Adjacency mapping and continent bonuses

### 2. **MCP Server** (`mcp-server/`)
- **`risk_mcp.py`**: FastMCP server exposing game functions as tools
- **`risk_api.py`**: HTTP client for Risk API communication
- **Available Tools**:
  - `get_game_state` - Retrieve current game state
  - `reinforce` - Add armies to territories
  - `attack` - Attack between territories
  - `fortify` - Move armies between connected territories
  - `move_armies` - Move armies after conquest
  - `trade_cards` - Trade cards for bonus armies
  - `advance_phase` - Progress through game phases
  - `new_game` - Start new games
  - `get_reinforcement_armies` - Get available reinforcements
  - `get_possible_actions` - List valid actions

### 3. **ADK Workflow Agent** (`agents/workflow_agent/`)
- **ADK Loop Agent**: Orchestrates multi-player Risk games
- **Built-in Web UI**: Users interact through ADK's visual Web UI
- **Game Orchestration**: Manages game rounds and player turns
- **A2A Integration**: Communicates with player agents via A2A protocol
- **Real-time Streaming**: Provides live updates during game play

### 4. **ADK Player Agents** (`agents/player_agent/`)
- **`agent_player.py`**: Google ADK agent with Gemini integration
- **Features**:
  - MCP toolset integration over HTTP/SSE
  - Strategic Risk gameplay logic
  - Session management and state tracking
  - A2A protocol compatibility
  - Individual player strategies and personas

### 5. **Test Data Generator** (`generate_testdata.py`)
- Automated game scenario generation
- Captures meaningful game states for testing
- Tracks card trading, conquests, continent control
- Generates comprehensive test datasets

## 🛠️ Technology Stack

### Core Technologies
- **Google ADK**: Agent Development Kit with built-in Web UI and Loop agents
- **MCP (Model Context Protocol)**: Standardized tool calling protocol
- **A2A Protocol**: Agent-to-agent communication framework
- **Gemini 2.5 Flash Lite**: Advanced LLM for game strategy

### ADK Features
- **Built-in Web UI**: Visual interface for development and user interaction
- **Loop Agents**: Orchestration for complex workflows and game rounds
- **Bidirectional Streaming**: Real-time audio/video communication
- **Integrated Debugging**: Step-by-step execution inspection
- **Multi-Agent Support**: Hierarchical agent composition and delegation

### Infrastructure
- **Cloud Run**: Serverless deployment platform
- **Docker**: Containerization for all components
- **HTTP/SSE**: Real-time communication protocols

### Languages & Frameworks
- **Python**: Agent logic and MCP server
- **Rust**: High-performance game engine
- **FastMCP**: Python MCP server framework
- **Uvicorn**: ASGI server for Python components

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker
- Google Cloud credentials
- Risk game server running (external dependency)

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd risk

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r agents/player_agent/requirements.txt
pip install -r agents/workflow_agent/requirements.txt
pip install -r mcp-server/requirements.txt
```

### 2. Configuration
```bash
# Set Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"

# Configure MCP server URL (if using Cloud Run deployment)
export MCP_SERVER_URL="https://your-mcp-server-url.run.app/mcp/stream"
```

### 3. Run Components

#### Start MCP Server
```bash
cd mcp-server
python risk_mcp.py
```

#### Run ADK Workflow Agent
```bash
cd agents/workflow_agent
adk web  # Launches ADK's built-in Web UI
```

#### Run Player Agents
```bash
cd agents/player_agent
python agent_player.py
```

#### Generate Test Data
```bash
python generate_testdata.py
```

## 🐳 Docker Deployment

### Build Images
```bash
# Build MCP server
docker build -t risk-mcp-server mcp-server/

# Build ADK workflow agent
docker build -t risk-workflow-agent agents/workflow_agent/

# Build ADK player agents
docker build -t risk-player-agent agents/player_agent/

# Build main application
docker build -t risk-platform .
```

### Deploy to Cloud Run
```bash
# Deploy MCP server
gcloud run deploy risk-mcp-server \
  --image risk-mcp-server \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated

# Deploy ADK workflow agent
gcloud run deploy risk-workflow-agent \
  --image risk-workflow-agent \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated

# Deploy player agents
gcloud run deploy risk-player-agent \
  --image risk-player-agent \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated
```

## 🎮 Game Flow

1. **User Interaction**: User accesses ADK's built-in Web UI
2. **Game Initialization**: Workflow agent starts new game via Risk API
3. **Player Assignment**: Workflow agent configures player agents via A2A
4. **Round Orchestration**: Loop agent manages complete game rounds
5. **Turn Execution**: Each player agent takes turns via A2A communication
6. **Real-time Updates**: Web UI shows live game progress and state
7. **Game Completion**: Workflow agent detects and reports game end

## 🔧 Development

### Project Structure
```
risk/
├── agents/
│   ├── workflow_agent/
│   │   ├── loop_agent.py        # ADK Loop agent implementation
│   │   ├── requirements.txt     # ADK dependencies
│   │   └── Dockerfile          # Workflow agent containerization
│   └── player_agent/
│       ├── agent_player.py      # ADK player agent implementation
│       ├── requirements.txt     # Python dependencies
│       └── Dockerfile          # Player agent containerization
├── mcp-server/
│   ├── risk_mcp.py             # MCP server implementation
│   ├── risk_api.py             # Risk API client
│   ├── requirements.txt        # MCP server dependencies
│   └── Dockerfile              # MCP server containerization
├── testdata/                   # Generated test scenarios
├── game_config.json           # Risk game configuration
├── generate_testdata.py       # Test data generator
└── Dockerfile                 # Main application containerization
```

### Key Design Patterns

#### ADK Loop Agent Setup
```python
from google.adk.agents import LoopAgent

workflow_agent = LoopAgent(
    model="gemini-2.5-flash-lite-preview-06-17",
    name="risk_workflow_agent",
    description="Orchestrates multi-player Risk games",
    instruction="You are a Risk game master that coordinates rounds..."
)
```

#### MCP Tool Integration
```python
@server.tool(
    name="attack", 
    description="Attack from one territory to another"
)
def attack(player_id: int, from_territory: str, to_territory: str, 
           num_armies: int, num_dice: int, repeat: bool = False) -> Dict[str, Any]:
    # Tool implementation
```

#### A2A Protocol Integration
```python
class PlayerAgentExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        # A2A protocol implementation
```

## 🧪 Testing

### Test Data Generation
The `generate_testdata.py` script automatically generates comprehensive test scenarios:

- **Card Trading**: Scenarios with 3+ cards for trading
- **Conquest**: Successful territory conquests
- **Continent Control**: Full continent domination
- **End Game**: Advanced game states
- **Player Elimination**: Player removal scenarios

### Running Tests
```bash
# Generate test scenarios
python generate_testdata.py

# Test specific scenarios
python -m pytest tests/ -v

# Test ADK workflow agent
cd agents/workflow_agent
adk eval  # Run ADK's built-in evaluation
```

## 🔍 Monitoring & Logging

### Log Levels
- **INFO**: General operational logs
- **DEBUG**: Detailed execution traces
- **ERROR**: Error conditions and failures

### Key Metrics
- Game state retrieval latency
- Action execution success rates
- Agent decision-making time
- MCP tool call performance
- ADK Loop agent orchestration efficiency

### ADK Web UI Features
- **Real-time Monitoring**: Live game state and agent activity
- **Step-by-step Debugging**: Inspect agent execution flow
- **Event Inspection**: View A2A messages and responses
- **State Management**: Monitor game state transitions

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** your changes
4. **Add** tests for new functionality
5. **Submit** a pull request

### Development Guidelines
- Follow the established architecture patterns
- Maintain MCP tool compatibility
- Ensure ADK agent integration works
- Add comprehensive logging
- Update documentation for new features
- Test with ADK's built-in evaluation tools

## 📚 Resources

### Documentation
- [Google ADK Documentation](https://developers.google.com/adk)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [A2A Protocol Documentation](https://a2a.dev/)
- [Risk Game Rules](https://en.wikipedia.org/wiki/Risk_(game))

### Related Projects
- **Risk Board Game Server**: Rust-based game engine
- **Risk UI**: React-based game interface
- **MCP Tools**: Standardized tool ecosystem

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google ADK team for the agent development framework and built-in UI
- MCP community for the protocol specification
- Risk game community for inspiration and testing

---

**Built with ❤️ for the Agentic Web Revolution** 