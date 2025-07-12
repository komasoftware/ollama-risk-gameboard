# Risk Workflow Agent

This directory contains the Risk Workflow Agent implementation. The workflow agent acts as the game master, orchestrating the Risk game by communicating directly with the Risk API and coordinating player agents.

## 🏗️ Overview
- **Purpose**: Orchestrate multi-player Risk games by assigning turns, monitoring game state, and coordinating player agents.
- **Direct Communication**: Talks directly to the Risk API for game state and control.
- **Agent Coordination**: Assigns turns and tasks to player agents via A2A or HTTP.
- **No LLM**: Pure logic for orchestration (no LLM reasoning in the workflow agent).

## 📁 Directory Structure
```
workflow_agent/
├── workflow_agent.py      # Main agent implementation
├── requirements.txt       # Python dependencies
├── Dockerfile             # Containerization
├── README.md              # Documentation
├── env.example            # Environment variable template
└── __init__.py            # Python package marker
```

## ⚙️ Configuration
- All configuration is via environment variables (see `env.example`).
- Key variables:
  - `RISK_API_URL`: URL of the Risk API server
  - `PLAYER_AGENT_URLS`: Comma-separated list of player agent endpoints
  - `AGENT_NAME`: Name for this workflow agent instance

## 🚀 Running Locally
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or copy env.example to .env and export)
export RISK_API_URL=http://localhost:8080
export PLAYER_AGENT_URLS=http://localhost:8081,http://localhost:8082
export AGENT_NAME=RiskWorkflowAgent

# Run the agent
python workflow_agent.py
```

## 🐳 Docker
- Build the image:
  ```bash
  docker build -t risk-workflow-agent .
  ```
- Run the container:
  ```bash
  docker run --env-file env.example -p 8080:8080 risk-workflow-agent
  ```

## 📝 Agent Logic
- The workflow agent will:
  1. Start a new game via the Risk API
  2. Poll game state and determine whose turn it is
  3. Assign turns to player agents and wait for their responses
  4. Repeat until the game is complete

---

**This agent is under active development. See the feature doc for architectural details and implementation phases.** 