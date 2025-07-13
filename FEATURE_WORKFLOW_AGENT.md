# Feature: Workflow Agent for Risk Game Orchestration

## 🎯 Overview

Implement a workflow agent that acts as a game master to orchestrate multi-player Risk games. The workflow agent will coordinate up to 6 player agents, manage game flow, and ensure proper turn execution. Users interact directly with the workflow agent via HTTP endpoints.

## 🏗️ Architecture

### Simplified Architecture
```
         ┌──────────────────────┐
         │  Workflow Agent      │
         │  (Game Master)       │
         │  (FastAPI Service)   │
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
- **Workflow Agent**: FastAPI service that users interact with directly via HTTP endpoints
- **Player Agents**: ADK agents that receive turn assignments via A2A messages
- **Risk API**: Rust server managing game state

## 🎮 Game Flow Logic

### Workflow Agent (Game Master)
- **FastAPI Service**: Users interact directly via HTTP endpoints
- **LoopAgent Pattern**: Implements game loop logic for full rounds
- **Sub-Agents**:
  1. **Game State Checker**: Calls the Risk API to check current game state
  2. **Player Turn Dispatcher**: Sends A2A messages to player agents for turns
- **Full Round Execution**: Ensures every player takes exactly one turn per round

### HTTP Endpoints
- `POST /start-game` - Start a new game with N players
- `POST /play-full-round` - Play a complete round where every player takes one turn
- `GET /game-status` - Get current game status
- `GET /health` - Health check

### Full Round Execution Flow
1. **Start Game**
   - User sends HTTP request: `POST /start-game {"num_players": 4}`
   - Workflow agent starts new game via Risk API
   - Configure player agents (up to 6)

2. **Play Full Round**
   - User sends HTTP request: `POST /play-full-round`
   - Workflow agent ensures every player takes exactly one turn
   - For each player:
     - Check if it's their turn
     - Send turn task to player agent via A2A
     - Wait for player response
     - Record turn result
   - Return summary of the full round

3. **Player Turn Execution**
   - Workflow agent sends A2A message to appropriate player agent
   - Include player_id and persona in A2A DataPart
   - Wait for completion response via A2A
   - Handle any errors or timeouts

4. **Game State Management**
   - Monitor game phases (reinforce, attack, fortify)
   - Track player elimination
   - Detect game completion conditions

## 🛠️ Implementation

### Current Implementation Status

**✅ Infrastructure Complete:**
- Multi-agent Docker Compose setup working
- Configuration management with JSON parsing
- Health endpoints and service verification
- Agent card integration tested and working

**🔄 Next Steps - Full Round Implementation:**

1. **Implement Full Round Logic**
   - Add `play_full_round()` method to LoopAgent
   - Ensure every player takes exactly one turn
   - Track round completion and player turn order
   - Return comprehensive round summary

2. **Add HTTP Endpoint**
   - Add `POST /play-full-round` endpoint to workflow agent
   - Accept optional parameters (timeout, player order, etc.)
   - Return detailed round results

3. **Test Full Round Execution**
   - Test with 2-4 players
   - Verify each player takes exactly one turn
   - Test error handling and timeouts
   - Test game completion scenarios

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  # Workflow Agent (Game Master)
  workflow-agent:
    build:
      context: ./workflow_agent
      dockerfile: Dockerfile
    container_name: risk-workflow-agent
    ports:
      - "8080:8080"
    environment:
      - AGENT_NAME=RiskWorkflowAgent
      - RISK_API_URL=https://risk-api-server-xxx.a.run.app
      - PLAYER_AGENT_URLS=["http://player-agent-1:8080/.well-known/agent.json","http://player-agent-2:8080/.well-known/agent.json","http://player-agent-3:8080/.well-known/agent.json","http://player-agent-4:8080/.well-known/agent.json"]
    restart: unless-stopped

  # Player Agents (1-4)
  player-agent-1:
    build:
      context: ./player_agent
      dockerfile: Dockerfile
    container_name: risk-player-agent-1
    ports:
      - "8081:8080"
    environment:
      - AGENT_NAME=Player1
      - MCP_SERVER_URL=https://risk-mcp-server-xxx.a.run.app/mcp/stream
    restart: unless-stopped

  player-agent-2:
    build:
      context: ./player_agent
      dockerfile: Dockerfile
    container_name: risk-player-agent-2
    ports:
      - "8082:8080"
    environment:
      - AGENT_NAME=Player2
      - MCP_SERVER_URL=https://risk-mcp-server-xxx.a.run.app/mcp/stream
    restart: unless-stopped

  player-agent-3:
    build:
      context: ./player_agent
      dockerfile: Dockerfile
    container_name: risk-player-agent-3
    ports:
      - "8083:8080"
    environment:
      - AGENT_NAME=Player3
      - MCP_SERVER_URL=https://risk-mcp-server-xxx.a.run.app/mcp/stream
    restart: unless-stopped

  player-agent-4:
    build:
      context: ./player_agent
      dockerfile: Dockerfile
    container_name: risk-player-agent-4
    ports:
      - "8084:8080"
    environment:
      - AGENT_NAME=Player4
      - MCP_SERVER_URL=https://risk-mcp-server-xxx.a.run.app/mcp/stream
    restart: unless-stopped
```

### Local Development Commands
```bash
# Start all agent services locally
cd risk/agents
docker compose up -d

# View logs
docker compose logs -f workflow-agent

# Test workflow agent health
curl http://localhost:8080/health

# Start a new game
curl -X POST http://localhost:8080/start-game \
  -H "Content-Type: application/json" \
  -d '{"num_players": 4}'

# Play a full round
curl -X POST http://localhost:8080/play-full-round \
  -H "Content-Type: application/json"

# Get game status
curl http://localhost:8080/game-status

# Stop all services
docker compose down
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

### Full Round Response Format
```json
{
  "success": true,
  "round_number": 1,
  "players_processed": 4,
  "round_summary": {
    "player_1": {
      "status": "completed",
      "strategy": "aggressive",
      "actions": ["attacked Alaska", "defended Alberta"]
    },
    "player_2": {
      "status": "completed", 
      "strategy": "defensive",
      "actions": ["defended Ontario", "placed reinforcements"]
    }
  },
  "game_status": "playing",
  "next_round_ready": true
}
```

## 🧪 Testing Strategy

### Unit Tests
- Full round execution logic
- Player turn order tracking
- Game state management
- Error handling

### Integration Tests
- Complete full round with 2-4 players
- A2A communication with player agents
- Game completion scenarios
- Error recovery

### Performance Tests
- Round completion time
- Concurrent round execution
- Resource usage monitoring

## 📊 Monitoring and Observability

### Key Metrics
- Full round completion time
- Individual player turn times
- Round success rate
- Error rates and types

### Logging
- Round start/completion logs
- Player turn execution logs
- A2A message flow logs
- Game state transition logs
- Error and exception logs

## 🚀 Success Criteria

### Core Functionality
- [ ] Workflow agent can start a new game with N players
- [ ] Workflow agent can play a full round where every player takes exactly one turn
- [ ] HTTP endpoints working for game control
- [ ] A2A communication with player agents working
- [ ] Comprehensive round summary returned

### Error Handling
- [ ] Timeout handling for slow player agents
- [ ] Error recovery for failed player turns
- [ ] Game state validation
- [ ] Proper error messages returned

### Testing
- [ ] Full round execution with 2-4 players
- [ ] Game completion scenarios
- [ ] Error scenarios and recovery
- [ ] Performance benchmarks

## 🔄 Future Enhancements

### Potential Improvements
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

**Implementation Priority**: Focus on implementing the full round functionality first, then add error handling and testing. 