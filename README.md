# Risk Agentic Web Platform

A sophisticated agentic web platform that demonstrates AI agents playing the classic Risk board game using cutting-edge technologies: **Google ADK (Agent Development Kit)**, **MCP (Model Context Protocol)**, and **A2A (Agent-to-Agent) protocol**.

## 🎯 Overview

This project showcases a complete agentic web architecture where AI agents can autonomously play Risk through multiple layers of abstraction:

- **Risk Game Server**: Rust-based game engine with REST API
- **MCP Server**: Protocol bridge exposing game functions as tools
- **ADK Agent**: Google's Agent Development Kit with Gemini integration
- **A2A Protocol**: Agent-to-agent communication framework

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ADK Agent     │    │   MCP Server    │    │  Risk API       │
│   (Gemini)      │◄──►│   (HTTP/SSE)    │◄──►│  (Rust Server)  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   A2A Protocol  │    │   Cloud Run     │    │   Game State    │
│   (Agent Exec)  │    │   (Deployed)    │    │   (JSON Config) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
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

### 3. **ADK Agent** (`agents/player_agent/`)
- **`agent_player.py`**: Google ADK agent with Gemini integration
- **Features**:
  - MCP toolset integration over HTTP/SSE
  - Strategic Risk gameplay logic
  - Session management and state tracking
  - A2A protocol compatibility

### 4. **Test Data Generator** (`generate_testdata.py`)
- Automated game scenario generation
- Captures meaningful game states for testing
- Tracks card trading, conquests, continent control
- Generates comprehensive test datasets

## 🛠️ Technology Stack

### Core Technologies
- **Google ADK**: Agent Development Kit for LLM-powered agents
- **MCP (Model Context Protocol)**: Standardized tool calling protocol
- **A2A Protocol**: Agent-to-agent communication framework
- **Gemini 2.5 Flash Lite**: Advanced LLM for game strategy

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

#### Run ADK Agent
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

# Build ADK agent
docker build -t risk-adk-agent agents/player_agent/

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

# Deploy ADK agent
gcloud run deploy risk-adk-agent \
  --image risk-adk-agent \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated
```

## 🎮 Game Flow

1. **Initialization**: Agent connects to MCP server via HTTP/SSE
2. **Game State**: Agent retrieves current game state
3. **Strategy**: Gemini analyzes game state and formulates strategy
4. **Action Selection**: Agent chooses optimal actions using MCP tools
5. **Execution**: Actions are executed through Risk API
6. **Iteration**: Process repeats until game completion

## 🔧 Development

### Project Structure
```
risk/
├── agents/
│   └── player_agent/
│       ├── agent_player.py      # ADK agent implementation
│       ├── requirements.txt     # Python dependencies
│       └── Dockerfile          # Agent containerization
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

#### ADK Agent Setup
```python
self.agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite-preview-06-17"),
    name=self.name,
    instruction="You are a Risk game player agent..."
)
self.agent.tools = [self.toolset]
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

- Google ADK team for the agent development framework
- MCP community for the protocol specification
- Risk game community for inspiration and testing

---

**Built with ❤️ for the Agentic Web Revolution** 