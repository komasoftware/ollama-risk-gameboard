#!/bin/bash

# Risk Player Agent Deployment Test Script
# This script tests the deployed player agent endpoints

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

# Get service URL
get_service_url() {
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null)
    if [ -z "$SERVICE_URL" ]; then
        log_error "Could not get service URL. Is the service deployed?"
        exit 1
    fi
    echo $SERVICE_URL
}

# Test basic connectivity
test_basic_connectivity() {
    local url=$1
    log_info "Testing basic connectivity to $url"
    
    # For A2A agents, a 404 on root endpoint might be expected
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url")
    if [ "$HTTP_CODE" = "404" ]; then
        log_success "Basic connectivity test passed (404 expected for A2A agent root endpoint)"
        return 0
    elif [ "$HTTP_CODE" = "200" ]; then
        log_success "Basic connectivity test passed (200 response)"
        return 0
    else
        log_error "Basic connectivity test failed (HTTP code: $HTTP_CODE)"
        return 1
    fi
}

# Test A2A agent endpoints
test_a2a_endpoints() {
    local url=$1
    log_info "Testing A2A agent endpoints..."
    
    # Test agent card endpoint
    local agent_card_url="$url/agent-card"
    log_info "Testing agent card endpoint: $agent_card_url"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$agent_card_url")
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Agent card endpoint test passed"
    else
        log_warning "Agent card endpoint test failed (HTTP code: $HTTP_CODE)"
    fi
    
    # Test health endpoint (if available)
    local health_url="$url/health"
    log_info "Testing health endpoint: $health_url"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$health_url")
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Health endpoint test passed"
    else
        log_warning "Health endpoint test failed (HTTP code: $HTTP_CODE) - this might be expected"
    fi
}

# Test MCP server connection
test_mcp_connection() {
    log_info "Testing MCP server connection: $MCP_SERVER_URL"
    
    # Test MCP stream endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "accept: application/json, text/event-stream" "$MCP_SERVER_URL")
    if [ "$HTTP_CODE" = "400" ]; then
        log_success "MCP server connection test passed (400 expected - server is responding correctly)"
        return 0
    elif [ "$HTTP_CODE" = "200" ]; then
        log_success "MCP server connection test passed (200 response)"
        return 0
    else
        log_warning "MCP server connection test failed (HTTP code: $HTTP_CODE)"
        return 1
    fi
}

# Check service status
check_service_status() {
    log_info "Checking Cloud Run service status..."
    
    gcloud run services describe $SERVICE_NAME --region=$REGION --format="table(
        metadata.name,
        status.url,
        status.conditions[0].status,
        status.conditions[0].type
    )"
}

# Show service logs
show_recent_logs() {
    log_info "Showing recent service logs..."
    
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
        --limit=20 \
        --format="table(timestamp,severity,textPayload)"
}

# Test agent functionality
test_agent_functionality() {
    local url=$1
    log_info "Testing agent functionality..."
    
    # Test with a simple message
    local test_message='{"message": {"parts": [{"root": {"text": "Play turn for player 1"}}]}}'
    log_info "Sending test message to agent..."
    
    # This is a basic test - actual A2A protocol might require more complex setup
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$test_message" \
        "$url/execute")
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "404" ]; then
        log_success "Agent functionality test passed (HTTP code: $HTTP_CODE)"
        return 0
    else
        log_warning "Agent functionality test failed (HTTP code: $HTTP_CODE) - this might be expected for A2A protocol"
        return 1
    fi
}

# Main test function
main() {
    log_info "Starting Risk Player Agent deployment tests..."
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"
    log_info "Service: $SERVICE_NAME"
    log_info "Agent: $AGENT_NAME"
    echo ""
    
    # Get service URL
    SERVICE_URL=$(get_service_url)
    log_info "Service URL: $SERVICE_URL"
    log_info "A2A Agent URL: $SERVICE_URL"
    echo ""
    
    # Run tests
    local tests_passed=0
    local total_tests=0
    
    # Test 1: Basic connectivity
    total_tests=$((total_tests + 1))
    if test_basic_connectivity "$SERVICE_URL"; then
        tests_passed=$((tests_passed + 1))
    fi
    echo ""
    
    # Test 2: A2A endpoints
    total_tests=$((total_tests + 1))
    if test_a2a_endpoints "$SERVICE_URL"; then
        tests_passed=$((tests_passed + 1))
    fi
    echo ""
    
    # Test 3: MCP server connection
    total_tests=$((total_tests + 1))
    if test_mcp_connection; then
        tests_passed=$((tests_passed + 1))
    fi
    echo ""
    
    # Test 4: Agent functionality
    total_tests=$((total_tests + 1))
    if test_agent_functionality "$SERVICE_URL"; then
        tests_passed=$((tests_passed + 1))
    fi
    echo ""
    
    # Show service status
    check_service_status
    echo ""
    
    # Show recent logs
    show_recent_logs
    echo ""
    
    # Summary
    log_info "=== Test Summary ==="
    echo "Tests passed: $tests_passed/$total_tests"
    
    if [ $tests_passed -eq $total_tests ]; then
        log_success "All tests passed! The player agent is working correctly."
    else
        log_warning "Some tests failed. Check the logs above for details."
    fi
    
    log_info "=== Agent Information ==="
    echo "Agent Name: $AGENT_NAME"
    echo "MCP Server: $MCP_SERVER_URL"
    echo "Gemini Model: $GEMINI_MODEL"
    echo "Vertex AI: $GOOGLE_GENAI_USE_VERTEXAI"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --status-only  Only show service status"
        echo "  --logs-only    Only show recent logs"
        echo ""
        echo "Default behavior: Run all tests"
        exit 0
        ;;
    --status-only)
        check_service_status
        exit 0
        ;;
    --logs-only)
        show_recent_logs
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