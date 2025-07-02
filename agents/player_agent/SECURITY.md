# Player Agent Security Configuration

## 🔒 Sensitive Values Management

This document outlines the security measures implemented to protect sensitive configuration values in the Player Agent deployment.

## 📋 Changes Made

### 1. Environment Variables Migration
- **Before**: Hardcoded sensitive values in scripts and documentation
- **After**: All sensitive values moved to `.env` file (gitignored)

### 2. Files Updated

#### Scripts
- `deploy.sh`: Now loads configuration from `.env` file
- `test-deployment.sh`: Now loads configuration from `.env` file

#### Code
- `agent_player.py`: Now uses environment variables for configuration
  - `AGENT_NAME`: Agent name configuration
  - `MCP_SERVER_URL`: MCP server endpoint URL
  - `AGENT_CARD_URL`: A2A agent card URL

#### Documentation
- `README.md`: Updated to reference environment variables instead of hardcoded values

### 3. New Files Created
- `env.template`: Template file with actual example values
- `env.example`: Template file with placeholder values for easy setup
- `.env`: Local configuration file (gitignored)
- `SECURITY.md`: This security documentation

## 🚨 Sensitive Values Identified

### Google Cloud Configuration
- `PROJECT_ID`: Google Cloud project identifier
- `REGION`: Google Cloud region
- `ARTIFACT_REGISTRY`: Docker registry URL

### Service URLs (contain project-specific identifiers)
- `MCP_SERVER_URL`: MCP server endpoint URL
- `MCP_SERVER_ALTERNATIVE_URL`: Alternative MCP server endpoint
- `AGENT_CARD_URL`: A2A agent card URL

### Agent Configuration
- `SERVICE_NAME`: Cloud Run service name
- `IMAGE_NAME`: Docker image name
- `IMAGE_TAG`: Docker image tag
- `AGENT_NAME`: Agent name for the Risk player

### AI Model Configuration
- `GEMINI_MODEL`: Gemini model identifier
- `GOOGLE_GENAI_USE_VERTEXAI`: Vertex AI configuration
- `GOOGLE_CLOUD_LOCATION`: AI services location

## 🔧 Setup Instructions

### For New Developers
1. Copy the environment template:
   ```bash
   # Option 1: Use template with actual example values
   cp env.template .env
   
   # Option 2: Use template with placeholder values
   cp env.example .env
   ```

2. Edit `.env` with your actual values:
   ```bash
   nano .env
   ```

3. Never commit the `.env` file to version control

### For Deployment
The scripts automatically load environment variables from `.env`:
```bash
./deploy.sh        # Uses .env configuration
./test-deployment.sh  # Uses .env configuration
```

## ✅ Security Checklist

- [x] All hardcoded sensitive values removed from scripts
- [x] All hardcoded sensitive values removed from documentation
- [x] Environment variables properly loaded in all scripts
- [x] `.env` file added to `.gitignore`
- [x] Template file (`env.template`) provided for easy setup
- [x] Documentation updated to reference environment variables
- [x] Code updated to use environment variables
- [x] AI model configuration externalized
- [x] MCP server URLs externalized

## 🛡️ Best Practices

1. **Never commit `.env` files** to version control
2. **Use different values** for different environments (dev, staging, prod)
3. **Rotate sensitive values** regularly
4. **Limit access** to production environment variables
5. **Use secrets management** for production deployments
6. **Secure AI model access** with proper authentication
7. **Monitor agent interactions** for security issues

## 🔍 Verification

To verify the security configuration:
1. Check that `.env` is in `.gitignore`
2. Verify no hardcoded sensitive values remain in scripts
3. Test that scripts load environment variables correctly
4. Confirm documentation references environment variables
5. Verify AI model configuration is externalized
6. Check MCP server URLs are configurable

## 📞 Support

If you encounter issues with environment configuration:
1. Check that `.env` file exists and is properly formatted
2. Verify all required environment variables are set
3. Ensure scripts have proper permissions to read `.env`
4. Verify Google Cloud authentication is configured
5. Check MCP server connectivity

## 🎯 Agent-Specific Security Considerations

### AI Model Security
- **Gemini Model Access**: Ensure proper authentication for Vertex AI
- **Model Versioning**: Use specific model versions for reproducibility
- **Rate Limiting**: Monitor API usage to prevent abuse

### MCP Server Security
- **Connection Security**: Use HTTPS for all MCP server connections
- **Authentication**: Implement proper authentication for MCP tools
- **Input Validation**: Validate all inputs to MCP tools

### A2A Protocol Security
- **Agent Authentication**: Implement proper agent authentication
- **Message Validation**: Validate all A2A protocol messages
- **Rate Limiting**: Implement rate limiting for agent interactions 