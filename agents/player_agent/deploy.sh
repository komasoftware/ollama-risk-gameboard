#!/bin/bash

# Risk Player Agent Deployment Script
# This script builds, pushes, and deploys the player agent to Google Cloud Run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    log_info "Loaded environment variables from .env file"
else
    log_error ".env file not found. Please copy env.template to .env and configure your values."
    exit 1
fi

# Configuration (loaded from .env file)
FULL_IMAGE_NAME="${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "Google Cloud CLI is not installed. Please install gcloud first."
        exit 1
    fi
    
    # Check if user is authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with Google Cloud. Please run 'gcloud auth login' first."
        exit 1
    fi
    
    # Check if project is set
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        log_warning "Current project is '$CURRENT_PROJECT', but we need '$PROJECT_ID'"
        log_info "Setting project to $PROJECT_ID..."
        gcloud config set project $PROJECT_ID
    fi
    
    log_success "Prerequisites check passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image: $FULL_IMAGE_NAME"
    
    # Build the image
    docker build -t $FULL_IMAGE_NAME .
    
    if [ $? -eq 0 ]; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

# Push image to Artifact Registry
push_image() {
    log_info "Pushing image to Artifact Registry..."
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
    
    # Push the image
    docker push $FULL_IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        log_success "Image pushed successfully to Artifact Registry"
    else
        log_error "Failed to push image to Artifact Registry"
        exit 1
    fi
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    # Deploy the service
    gcloud run deploy $SERVICE_NAME \
        --image $FULL_IMAGE_NAME \
        --region $REGION \
        --allow-unauthenticated \
        --platform managed \
        --port 8080 \
        --memory ${MEMORY:-1Gi} \
        --cpu ${CPU:-1} \
        --max-instances ${MAX_INSTANCES:-10} \
        --timeout ${TIMEOUT:-300} \
        --set-env-vars "MCP_SERVER_URL=$MCP_SERVER_URL,GEMINI_MODEL=$GEMINI_MODEL,GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,AGENT_NAME=$AGENT_NAME"
    
    if [ $? -eq 0 ]; then
        log_success "Deployed successfully to Cloud Run"
    else
        log_error "Failed to deploy to Cloud Run"
        exit 1
    fi
}

# Get service URL
get_service_url() {
    log_info "Getting service URL..."
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    
    if [ -n "$SERVICE_URL" ]; then
        log_success "Service URL: $SERVICE_URL"
        log_info "A2A Agent endpoint: $SERVICE_URL"
    else
        log_error "Failed to get service URL"
        exit 1
    fi
}

# Test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    
    # Test basic connectivity
    if curl -s -f --max-time 10 "$SERVICE_URL" > /dev/null; then
        log_success "Basic connectivity test passed"
    else
        log_warning "Basic connectivity test failed"
    fi
    
    # Test A2A agent endpoint
    if curl -s -f --max-time 10 "$SERVICE_URL/health" > /dev/null; then
        log_success "A2A agent health check passed"
    else
        log_warning "A2A agent health check failed (this might be expected if no health endpoint)"
    fi
}

# Show deployment info
show_deployment_info() {
    log_info "=== Deployment Information ==="
    echo "Project ID: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Service Name: $SERVICE_NAME"
    echo "Image: $FULL_IMAGE_NAME"
    echo "Service URL: $(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")"
    echo "A2A Agent: $(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")"
    echo ""
    log_info "=== Useful Commands ==="
    echo "View logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit=50"
    echo "Check status: gcloud run services describe $SERVICE_NAME --region=$REGION"
    echo "List images: gcloud artifacts docker images list $ARTIFACT_REGISTRY --include-tags"
    echo ""
    log_info "=== Agent Configuration ==="
    echo "Agent Name: $AGENT_NAME"
    echo "MCP Server: $MCP_SERVER_URL"
    echo "Gemini Model: $GEMINI_MODEL"
    echo "Vertex AI: $GOOGLE_GENAI_USE_VERTEXAI"
}

# Main deployment function
main() {
    log_info "Starting Risk Player Agent deployment..."
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"
    log_info "Service: $SERVICE_NAME"
    log_info "Image: $FULL_IMAGE_NAME"
    log_info "Agent: $AGENT_NAME"
    echo ""
    
    # Run deployment steps
    check_prerequisites
    build_image
    push_image
    deploy_to_cloud_run
    get_service_url
    test_deployment
    show_deployment_info
    
    log_success "Deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --build-only   Only build the Docker image"
        echo "  --push-only    Only push the Docker image"
        echo "  --deploy-only  Only deploy to Cloud Run (assumes image is already pushed)"
        echo ""
        echo "Default behavior: Build, push, and deploy"
        exit 0
        ;;
    --build-only)
        log_info "Building only..."
        check_prerequisites
        build_image
        log_success "Build completed"
        exit 0
        ;;
    --push-only)
        log_info "Pushing only..."
        check_prerequisites
        push_image
        log_success "Push completed"
        exit 0
        ;;
    --deploy-only)
        log_info "Deploying only..."
        check_prerequisites
        deploy_to_cloud_run
        get_service_url
        test_deployment
        show_deployment_info
        log_success "Deploy completed"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac 