# Risk Player Agent

This directory contains the Risk Player Agent implementation using Google ADK (Agent Development Kit) with MCP (Model Context Protocol) tools. The agent can play Risk games by communicating with the Risk MCP server.

## 🏗️ Architecture

The Player Agent is built using:
- **Google ADK**: Agent Development Kit for LLM-powered agents
- **MCP Tools**: Model Context Protocol for tool calling
- **A2A Protocol**: Agent-to-Agent communication protocol
- **Gemini 2.5 Flash Lite**: AI model for game decision making
- **Cloud Run**: Serverless deployment platform

### Components
- **agent_player.py**: Main agent implementation with ADK and MCP integration
- **Dockerfile**: Containerization configuration
- **requirements.txt**: Python dependencies
- **deploy.sh**: Deployment script for Cloud Run
- **test-deployment.sh**: Testing script for deployed agent

## 🌐 Deployed Service

### Production URL
- **Player Agent**: Configured via environment variables in `.env` file
- **A2A Agent Endpoint**: Configured via `SERVICE_URL` in `.env` file

### Google Cloud Resources
- **Project**: Configured via `PROJECT_ID` in `.env` file
- **Region**: Configured via `REGION` in `.env` file
- **Artifact Registry**: Configured via `ARTIFACT_REGISTRY` in `.env` file

## 🐳 Docker Image

### Image Reference
```bash
# Configured via ARTIFACT_REGISTRY, IMAGE_NAME, and IMAGE_TAG in .env file
${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
```

### Build Commands
```bash
# Build image locally (uses .env configuration)
docker build -t ${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .

# Push to Artifact Registry (uses .env configuration)
docker push ${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
```

## 🚀 Deployment

### Prerequisites
1. **Google Cloud CLI** installed and authenticated
2. **Docker** installed and configured
3. **Environment configuration**: Copy `env.template` to `.env` and configure your values

### Quick Deployment
Use the provided deployment script:
```bash
./deploy.sh
```

### Manual Deployment Steps

1. **Build Docker Image**
   ```bash
   # Load environment variables first
   export $(cat .env | grep -v '^#' | xargs)
   docker build -t ${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .
   ```

2. **Push to Artifact Registry**
   ```bash
   docker push ${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy ${SERVICE_NAME} \
     --image ${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
     --region ${REGION} \
     --allow-unauthenticated \
     --platform managed \
     --memory ${MEMORY:-1Gi} \
     --cpu ${CPU:-1} \
     --max-instances ${MAX_INSTANCES:-10} \
     --timeout ${TIMEOUT:-300} \
     --set-env-vars "MCP_SERVER_URL=$MCP_SERVER_URL,GEMINI_MODEL=$GEMINI_MODEL,GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,AGENT_NAME=$AGENT_NAME"
   ```

## 🔧 Environment Configuration

### Setup Environment Variables
1. **Copy the template**: `cp env.template .env` (or `cp env.example .env` for placeholder values)
2. **Edit the file**: Update `.env` with your actual values
3. **Never commit**: The `.env` file is ignored by git

**Template Files:**
- `env.template`: Contains actual example values (for reference)
- `env.example`: Contains placeholder values (for easy setup)

### Environment Variables
- `PROJECT_ID`: Google Cloud project ID
- `REGION`: Google Cloud region
- `ARTIFACT_REGISTRY`: Docker registry URL
- `SERVICE_NAME`: Cloud Run service name
- `IMAGE_NAME`: Docker image name
- `IMAGE_TAG`: Docker image tag
- `AGENT_NAME`: Agent name for the Risk player
- `MCP_SERVER_URL`: MCP server endpoint URL
- `GEMINI_MODEL`: Gemini model to use
- `GOOGLE_GENAI_USE_VERTEXAI`: Use Vertex AI for Gemini model
- `GOOGLE_CLOUD_LOCATION`: Google Cloud location for AI services

### Required for Local Development
```bash
# Load environment variables from .env file
export $(cat .env | grep -v '^#' | xargs)
```

### Cloud Run Environment Variables
- `MCP_SERVER_URL`: MCP server endpoint URL
- `GEMINI_MODEL`: Gemini model configuration
- `GOOGLE_GENAI_USE_VERTEXAI`: Vertex AI configuration
- `GOOGLE_CLOUD_LOCATION`: AI services location
- `AGENT_NAME`: Agent name
- `PORT`: Server port (default: 8080)

## 🧪 Testing

### Test Player Agent Connectivity
```bash
# Load environment variables first
export $(cat .env | grep -v '^#' | xargs)
curl -s -f --max-time 10 "$SERVICE_URL"
```

### Test A2A Agent Endpoints
```bash
# Test agent card endpoint
curl ${SERVICE_URL}/agent-card

# Test health endpoint (if available)
curl ${SERVICE_URL}/health
```

### Test MCP Server Connection
```bash
curl -H "accept: application/json, text/event-stream" \
     ${MCP_SERVER_URL}
```

## 🔍 Debugging

### Check Cloud Run Service Status
```bash
gcloud run services describe ${SERVICE_NAME} --region=${REGION}
```

### View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" --limit=50
```

### Check Artifact Registry
```bash
# Load environment variables first
export $(cat .env | grep -v '^#' | xargs)
gcloud artifacts docker images list ${ARTIFACT_REGISTRY} --include-tags
```

## 📚 Dependencies

### Python Dependencies (requirements.txt)
```
a2a-sdk>=0.2.5
uvicorn>=0.24.0
starlette>=0.27.0
fastapi>=0.104.0
pydantic>=2.0.0
google-adk
google-cloud-aiplatform
google-auth
```

### External Dependencies
- **Risk MCP Server**: Configured via `MCP_SERVER_URL` in `.env` file
- **Google Cloud Run**: Serverless deployment platform
- **Artifact Registry**: Docker image storage
- **Vertex AI**: AI model hosting platform

## 🛠️ Development

### Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables from .env file
export $(cat .env | grep -v '^#' | xargs)

# Run locally
python agent_player.py
```

### Agent Capabilities
The Player Agent can perform the following Risk game actions:
1. **get_game_state** - Get current game state
2. **reinforce** - Add armies to territories
3. **attack** - Attack enemy territories
4. **fortify** - Move armies between connected territories
5. **move_armies** - Move armies after successful attacks
6. **trade_cards** - Trade cards for bonus armies
7. **advance_phase** - Advance to next game phase
8. **new_game** - Start a new game
9. **get_reinforcement_armies** - Get available reinforcement armies
10. **get_possible_actions** - Get list of possible actions

### Code Quality Standards
- **Type Hints**: Always use type hints in Python code
- **Error Handling**: Comprehensive exception handling with logging
- **Logging**: Use structured logging with appropriate levels
- **Documentation**: JSDoc-style comments for all public APIs

## ⚠️ Important Notes

1. **Always verify URLs and endpoints** before making changes
2. **Test agent interactions** thoroughly before deployment
3. **Monitor Cloud Run logs** for debugging production issues
4. **Keep dependencies updated** and check for security vulnerabilities
5. **Use semantic versioning** for Docker image tags
6. **Document all API changes** and update this README accordingly
7. **Ensure MCP server is accessible** from the deployed agent

## 🔗 Related Services

- **Risk MCP Server**: Configured via `MCP_SERVER_URL` in `.env` file
- **Risk API Server**: Backend game engine (external service)
- **Risk UI**: React-based interface (external repo)

## 🎮 Game Integration

The Player Agent integrates with the Risk game through:
- **MCP Tools**: Standardized tool calling interface
- **A2A Protocol**: Agent-to-agent communication
- **Google ADK**: LLM-powered decision making
- **Gemini Model**: AI reasoning for game strategy

The agent follows proper Risk game phases:
1. **Reinforce** - Add armies to territories
2. **Attack** - Attack enemy territories
3. **Fortify** - Move armies between connected territories

---

**Remember: This is a cutting-edge AI agent for Risk gameplay. Always test thoroughly and monitor performance in production deployments.** 