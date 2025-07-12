# Feature: Workflow Agent for Risk Game Orchestration

## 🎯 Overview

Implement a workflow agent that acts as a game master to orchestrate multi-player Risk games. The workflow agent will coordinate up to 6 player agents, manage game flow, and ensure proper turn execution without using LLM reasoning for orchestration.

## 🏗️ Architecture

### Current State
- Individual player agents that can play single turns
- MCP server with game state tools
- A2A protocol for agent communication
- Risk game server managing game state

### Target Architecture
```
         ┌──────────────────────┐
         │  Workflow Agent      │
         │  (Game Master)       │
         │  (Pure Logic)        │
         └───────┬───────┬──────┘
                 │       │
                 │       │
                 ▼       ▼
          ┌──────────┐  ┌─────────────────────────────┐
          │ Risk API │  │      Player Agents          │
          │(Rust Srv)│  │ ┌──────────────┐            │
          └──────────┘  │ │ Player Agent │            │
                        │ │  Service #1  │            │
                        │ └──────┬───────┘            │
                        │        │                    │
                        │        ▼                    │
                        │   ┌──────────────┐          │
                        │   │  MCP Server  │          │
                        │   └──────────────┘          │
                        │                             │
                        │ (repeat for #2...#N)        │
                        └─────────────────────────────┘
```

**Note:**
- Workflow agent communicates directly with both the Risk API (for game state/control) and the player agents (to assign turns and coordinate play).
- Player agents communicate with the MCP server for tool-based game actions.
- MCP server communicates with the Risk API.
- Workflow agent does **not** use MCP tools.

## 🎮 Game Flow Logic

### Workflow Agent Predefined Logic (LoopAgent)
- The workflow agent will be implemented as a **LoopAgent** ([ADK docs](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/)), which repeatedly executes its sub-agents until the game is over or a maximum number of iterations is reached.
- **LoopAgent Sub-Agents:**
  1. **Game State Checker**: Calls the Risk API to check the current game state and determine whose turn it is or if the game is over.
  2. **Player Turn Dispatcher**: Sends the turn to the correct player agent and waits for their response.
- The loop terminates when the game state indicates the game is over, or after a max number of iterations (as a safety net).

### Stepwise / External Control Mode
- The workflow agent can also be run in a **stepwise/external control mode**:
  - The agent exposes an endpoint (e.g., `/play-turn` or `/step`) in its FastAPI app.
  - When this endpoint is called, the agent executes exactly one player turn (checks game state, dispatches the turn, waits for response, returns result).
  - The agent then waits for the next external call to proceed.
  - This allows integration with UIs, test harnesses, or manual control, and is fully supported by the agent SDK architecture.
  - This is an alternative to the LoopAgent 'run until done' pattern, and can be implemented alongside or instead of it.

### LoopAgent Execution Flow
1. **Initialize Game**
   - Start new game via Risk API
   - Configure player agents (up to 6)
   - Set initial game state

2. **Game Loop (LoopAgent)**
   - Check game state via Risk API (Game State Checker)
   - If game is over, end workflow (LoopAgent terminates)
   - If current player exists, send turn task (Player Turn Dispatcher)
   - Wait for player response
   - Continue loop

3. **Player Turn Execution**
   - Route task to appropriate player agent
   - Include player_id and persona in A2A request
   - Wait for completion response
   - Handle any errors or timeouts

4. **Game State Management**
   - Monitor game phases (reinforce, attack, fortify)
   - Track player elimination
   - Detect game completion conditions

## 🛠️ Implementation Phases

### Phase 1: Basic Workflow Agent Structure
**Goal**: Create a LoopAgent-based workflow agent with direct Risk API communication and basic game monitoring

**Components**:
- Workflow agent implemented as a LoopAgent (ADK)
- Sub-agents: Game State Checker, Player Turn Dispatcher
- Direct HTTP client for Risk API communication
- Basic game loop implementation
- Error handling and logging
- **Stepwise/external control endpoint** for single-turn execution

**Deliverables**:
- `workflow_agent.py` - Core LoopAgent implementation and stepwise endpoint
- `risk_api_client.py` - Direct Risk API HTTP client
- `workflow_config.py` - Configuration management
- Basic Docker setup for local testing

### Phase 2: Player Agent Integration
**Goal**: Integrate with existing player agents via A2A protocol

**Components**:
- A2A client integration for player communication
- Player agent discovery and connection management
- Task routing and response handling
- Player agent health monitoring

**Deliverables**:
- `player_manager.py` - Player agent pool management
- `a2a_client.py` - A2A communication wrapper
- Updated workflow agent with player integration

### Phase 3: Multi-Service Architecture
**Goal**: Deploy multiple player agent services in Cloud Run

**Components**:
- Separate Cloud Run deployments for each player agent
- Service discovery and configuration
- Load balancing and health checks
- Environment-specific configurations

**Deliverables**:
- `docker-compose.yml` - Local multi-agent setup
- Cloud Run deployment scripts
- Service configuration templates

### Phase 4: Advanced Game Management
**Goal**: Implement full game orchestration with error handling

**Components**:
- Complete game flow logic
- Error recovery and retry mechanisms
- Game statistics and monitoring
- Performance optimization

**Deliverables**:
- Complete workflow agent with full game logic
- Monitoring and logging infrastructure
- Performance benchmarks and optimization

## 🐳 Local Development Setup

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  workflow-agent:
    build: ./agents/workflow_agent
    environment:
      - RISK_API_URL=http://risk-api-server:8080
      - PLAYER_AGENT_URLS=http://player-agent-1:8080,http://player-agent-2:8080
    depends_on:
      - risk-api-server
      - player-agent-1
      - player-agent-2

  player-agent-1:
    build: ./agents/player_agent
    environment:
      - AGENT_NAME=Player1
      - MCP_SERVER_URL=http://mcp-server:8080/mcp/stream
    ports:
      - "8081:8080"

  player-agent-2:
    build: ./agents/player_agent
    environment:
      - AGENT_NAME=Player2
      - MCP_SERVER_URL=http://mcp-server:8080/mcp/stream
    ports:
      - "8082:8080"

  mcp-server:
    build: ./mcp-server
    environment:
      - RISK_API_BASE_URL=http://risk-api-server:8080
    ports:
      - "8083:8080"

  risk-api-server:
    image: risk-board-game-server
    ports:
      - "8084:8080"
```

### Local Development Commands
```bash
# Start all services locally
docker-compose up -d

# View logs
docker-compose logs -f workflow-agent

# Test workflow agent
curl -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "start_game", "num_players": 2}'
```

## ☁️ Cloud Deployment

### Player Agent Services
Each player agent will be deployed as a separate Cloud Run service:

```bash
# Deploy player agent services
for i in {1..6}; do
  gcloud run deploy risk-player-agent-$i \
    --image gcr.io/PROJECT_ID/risk-player-agent \
    --platform managed \
    --region europe-west4 \
    --allow-unauthenticated \
    --set-env-vars AGENT_NAME=Player$i
done
```

### Workflow Agent Service
```bash
# Deploy workflow agent
gcloud run deploy risk-workflow-agent \
  --image gcr.io/PROJECT_ID/risk-workflow-agent \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --set-env-vars RISK_API_URL=https://risk-api-server-xxx.a.run.app,PLAYER_AGENT_URLS=https://risk-player-agent-1-xxx.a.run.app,https://risk-player-agent-2-xxx.a.run.app
```

## 🔧 Technical Specifications

### Workflow Agent Configuration
```python
class WorkflowAgentConfig:
    # Player agent URLs (up to 6)
    player_agent_urls: List[str]
    
    # Risk API configuration
    risk_api_url: str
    
    # Game configuration
    max_players: int = 6
    game_timeout: int = 300  # seconds
    turn_timeout: int = 60   # seconds
    
    # Player personas
    player_personas: Dict[int, str] = {
        1: "aggressive",
        2: "defensive", 
        3: "balanced",
        4: "opportunistic",
        5: "cautious",
        6: "random"
    }

    # LoopAgent configuration
    max_iterations: int = 500  # Safety net for infinite loops
```

### LoopAgent Structure
- **Root agent**: LoopAgent
- **Sub-agents**:
  - Game State Checker (checks game state, signals loop termination if game is over)
  - Player Turn Dispatcher (assigns turn to player agent, waits for response)

### Player Agent Startup
Player agents will receive configuration via A2A DataPart:
```json
{
  "player_id": 1,
  "persona": "aggressive",
  "mcp_server_url": "https://risk-mcp-server.a.run.app/mcp/stream"
}
```

### Game State Monitoring
Workflow agent will use direct Risk API calls to:
- `GET /game-state` - Check current game state
- `GET /players` - Get player information and current turn
- `POST /new-game` - Start new games
- `GET /game-status` - Check if game is completed

## 🧪 Testing Strategy

### Unit Tests
- Workflow agent logic testing
- Player agent communication testing
- Risk API client integration testing

### Integration Tests
- Full game flow testing
- Multi-player scenario testing
- Error handling and recovery testing

### Performance Tests
- Concurrent player agent testing
- Game completion time benchmarking
- Resource usage monitoring

## 📊 Monitoring and Observability

### Key Metrics
- Game completion rate
- Average turn execution time
- Player agent response times
- Error rates and types

### Logging
- Workflow agent orchestration logs
- Player agent communication logs
- Game state transition logs
- Error and exception logs

## 🚀 Success Criteria

### Phase 1 Success
- [ ] Workflow agent is implemented as a LoopAgent
- [ ] LoopAgent terminates when game is over or max iterations reached
- [ ] Workflow agent can start a new game
- [ ] Workflow agent can monitor game state
- [ ] Basic game loop implementation
- [ ] Local Docker setup working
- [ ] Workflow agent exposes a stepwise/external control endpoint to play a single turn on demand

### Phase 2 Success
- [ ] Workflow agent can communicate with player agents
- [ ] Turn routing and response handling working
- [ ] Player agent health monitoring
- [ ] Error handling for player communication

### Phase 3 Success
- [ ] Multiple Cloud Run services deployed
- [ ] Service discovery and configuration working
- [ ] Load balancing and health checks
- [ ] Environment-specific configurations

### Phase 4 Success
- [ ] Complete game orchestration working
- [ ] Error recovery and retry mechanisms
- [ ] Game statistics and monitoring
- [ ] Performance optimization completed

## 🔄 Future Enhancements

### Potential Improvements
- LLM integration for game commentary
- Advanced player personas and strategies
- Game replay and analysis features
- Tournament mode with multiple games
- Real-time game visualization

### Scalability Considerations
- Horizontal scaling of player agents
- Game state persistence
- Multi-game orchestration
- Cross-region deployment

---

**Implementation Priority**: Start with Phase 1 to establish the foundation, then progress through phases based on testing and feedback. 