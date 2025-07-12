#!/bin/bash

# Start the test environment
echo "🚀 Starting Risk Game Test Environment..."
echo ""

# Start all services
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Display service URLs
echo ""
echo "📋 Service URLs:"
echo "=================="
echo "Risk API Server:     http://localhost:8084"
echo "MCP Server:          http://localhost:8083"
echo "Workflow Agent:      http://localhost:8080"
echo ""
echo "Player Agents:"
echo "  Player 1:          http://localhost:8081"
echo "  Player 2:          http://localhost:8082"
echo "  Player 3:          http://localhost:8085"
echo "  Player 4:          http://localhost:8086"
echo ""

# Check service health
echo "🔍 Checking service health..."
echo ""

# Check Risk API
echo "Risk API Server:"
if curl -s http://localhost:8084/ > /dev/null; then
    echo "  ✅ Running"
else
    echo "  ❌ Not responding"
fi

# Check Workflow Agent
echo "Workflow Agent:"
if curl -s http://localhost:8080/health > /dev/null; then
    echo "  ✅ Running"
else
    echo "  ❌ Not responding"
fi

# Check Player Agents
for i in 1 2 3 4; do
    port=$((8080 + i))
    if [ $i -eq 3 ]; then
        port=8085
    elif [ $i -eq 4 ]; then
        port=8086
    fi
    echo "Player Agent $i:"
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "  ✅ Running (port $port)"
    else
        echo "  ❌ Not responding (port $port)"
    fi
done

echo ""
echo "🎮 Test Environment Ready!"
echo ""
echo "Useful commands:"
echo "  View logs:          docker-compose logs -f"
echo "  Stop services:      docker-compose down"
echo "  Restart services:   docker-compose restart"
echo "  Test workflow:      curl http://localhost:8080/health"
echo "" 