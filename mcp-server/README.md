# Risk MCP Server

This directory contains the Model Context Protocol (MCP) server implementation for the Risk agentic web platform. The MCP server provides tools for AI agents to interact with the Risk game API.

## 🏗️ Architecture

The MCP server acts as a bridge between AI agents (using Google ADK) and the Risk game API, providing standardized tool interfaces for game operations.

### Components
- **risk_mcp.py**: FastMCP server implementation with tool definitions
- **risk_api.py**: HTTP client for Risk API interactions
- **Dockerfile**: Containerization configuration
- **requirements.txt**: Python dependencies

## 🌐 Deployed Service

### Production URL
- **MCP Server**: Configured via `RISK_API_BASE_URL` in `.env` file
- **MCP Stream Endpoint**: Configured via `MCP_SERVER_URL` in `.env` file

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
     --platform managed
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
- `MCP_SERVER_URL`: MCP server endpoint URL
- `RISK_API_BASE_URL`: Risk API server endpoint URL

### Required for Local Development
```bash
# Load environment variables from .env file
export $(cat .env | grep -v '^#' | xargs)
```

### Cloud Run Environment Variables
- `RISK_API_BASE_URL`: Risk API server base URL
- `PORT`: Server port (default: 8080)

## 🧪 Testing

### Test MCP Server Connectivity
```bash
# Load environment variables first
export $(cat .env | grep -v '^#' | xargs)
curl -H "accept: application/json, text/event-stream" \
     ${MCP_SERVER_URL}/mcp/stream
```

### Test Risk API Connection
```bash
curl ${RISK_API_BASE_URL}/game-state
```

## 🔍 Debugging

### Check Cloud Run Service Status
```bash
gcloud run services describe risk-mcp-server --region=europe-west4
```

### View Logs
```bash
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=risk-mcp-server" --limit=50
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
fastmcp
requests
uvicorn
```

### External Dependencies
- **Risk API Server**: Configured via `RISK_API_BASE_URL` in `.env` file
- **Google Cloud Run**: Serverless deployment platform
- **Artifact Registry**: Docker image storage

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
python risk_mcp.py
```

### Code Quality Standards
- **Type Hints**: Always use type hints in Python code
- **Error Handling**: Comprehensive exception handling with logging
- **Logging**: Use structured logging with appropriate levels
- **Documentation**: JSDoc-style comments for all public APIs

## ⚠️ Important Notes

1. **Always verify URLs and endpoints** before making changes
2. **Test MCP tool interactions** thoroughly before deployment
3. **Monitor Cloud Run logs** for debugging production issues
4. **Keep dependencies updated** and check for security vulnerabilities
5. **Use semantic versioning** for Docker image tags
6. **Document all API changes** and update this README accordingly

## 🔗 Related Services

- **Player Agent**: Configured via environment variables
- **Risk API Server**: Configured via `RISK_API_BASE_URL` in `.env` file
- **Risk UI**: React-based interface (external repo)

---

**Remember: This is a cutting-edge agentic web platform. Always double-check online documentation and follow best practices for production deployments.** 