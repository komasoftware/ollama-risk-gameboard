#!/bin/bash

# Risk MCP Server Deployment Test Script
# This script tests the deployed MCP server endpoints

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
    
    # For MCP servers, a 404 on root endpoint is expected
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url")
    if [ "$HTTP_CODE" = "404" ]; then
        log_success "Basic connectivity test passed (404 expected for MCP server root endpoint)"
        return 0
    elif [ "$HTTP_CODE" = "200" ]; then
        log_success "Basic connectivity test passed (200 response)"
        return 0
    else
        log_error "Basic connectivity test failed (HTTP code: $HTTP_CODE)"
        return 1
    fi
}

# Test MCP stream endpoint
test_mcp_stream() {
    local url=$1
    local mcp_url="$url/mcp/stream"
    log_info "Testing MCP stream endpoint: $mcp_url"
    
    # For MCP servers, a 400 with "Missing session ID" is expected when no session is provided
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "accept: application/json, text/event-stream" "$mcp_url")
    if [ "$HTTP_CODE" = "400" ]; then
        log_success "MCP stream endpoint test passed (400 expected - server is responding correctly)"
        return 0
    elif [ "$HTTP_CODE" = "200" ]; then
        log_success "MCP stream endpoint test passed (200 response)"
        return 0
    else
        log_error "MCP stream endpoint test failed (HTTP code: $HTTP_CODE)"
        return 1
    fi
}

# Test Risk API connection
test_risk_api() {
    local risk_api_url="$RISK_API_BASE_URL"
    log_info "Testing Risk API connection: $risk_api_url"
    
    if curl -s -f --max-time 10 "$risk_api_url/game-state" > /dev/null; then
        log_success "Risk API connection test passed"
        return 0
    else
        log_warning "Risk API connection test failed (this might be expected if the API server is not running)"
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

# Main test function
main() {
    log_info "Starting Risk MCP Server deployment tests..."
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"
    log_info "Service: $SERVICE_NAME"
    echo ""
    
    # Get service URL
    SERVICE_URL=$(get_service_url)
    log_info "Service URL: $SERVICE_URL"
    log_info "MCP Stream URL: $SERVICE_URL/mcp/stream"
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
    
    # Test 2: MCP stream endpoint
    total_tests=$((total_tests + 1))
    if test_mcp_stream "$SERVICE_URL"; then
        tests_passed=$((tests_passed + 1))
    fi
    echo ""
    
    # Test 3: Risk API connection
    total_tests=$((total_tests + 1))
    if test_risk_api; then
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
        log_success "All tests passed! The MCP server is working correctly."
    else
        log_warning "Some tests failed. Check the logs above for details."
    fi
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