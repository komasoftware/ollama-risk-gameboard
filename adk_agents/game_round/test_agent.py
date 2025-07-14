#!/usr/bin/env python3
"""
Test script for the ADK Game Round Agent
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import root_agent
from google.adk.tools.mcp_tool import MCPToolset

def test_agent():
    """Test the Game Round agent"""
    
    print("🧪 Testing ADK Game Round Agent...")
    print("=" * 50)
    
    # Test 1: Check if agent is created
    print("✅ Agent created successfully")
    print(f"   Name: {root_agent.name}")
    print(f"   Description: {root_agent.description}")
    print(f"   Sub-agents: {len(root_agent.sub_agents)} sub-agent(s)")
    
    # Test 2: Check sub-agents
    expected_agents = [
        "GameCoordinator",
        "RiskPlayer_Player1",  # Player 1
        "RiskPlayer_Player2",  # Player 2
        "RiskPlayer_Player3",  # Player 3
        "RiskPlayer_Player4",  # Player 4
        "RiskPlayer_Player5",  # Player 5
        "RiskPlayer_Player6"   # Player 6
    ]
    
    for i, sub_agent in enumerate(root_agent.sub_agents):
        print(f"   Sub-agent {i+1}: {sub_agent.name}")
        print(f"     Description: {sub_agent.description}")
        print(f"     Tools: {len(sub_agent.tools)} tool(s)")
        
        # Check for MCP toolset
        mcp_toolset = None
        for tool in sub_agent.tools:
            if isinstance(tool, MCPToolset):
                mcp_toolset = tool
                break
        
        if mcp_toolset:
            print(f"     ✅ MCP Toolset found")
        else:
            print(f"     ❌ MCP Toolset not found")
    
    # Test 3: Check configuration
    print("\n⚙️  Configuration:")
    print(f"   Project ID: {os.getenv('PROJECT_ID', 'koen-gcompany-demo')}")
    print(f"   Location: {os.getenv('GOOGLE_CLOUD_LOCATION', 'global')}")
    print(f"   Use Vertex AI: {os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE')}")
    print(f"   Max Players: {os.getenv('MAX_PLAYERS', '6')}")
    print(f"   Game Timeout: {os.getenv('GAME_TIMEOUT', '300')}s")
    print(f"   Turn Timeout: {os.getenv('TURN_TIMEOUT', '60')}s")
    print(f"   Google Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")
    print(f"   MCP Server URL: {os.getenv('MCP_SERVER_URL', 'https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/stream')}")
    
    print("\n" + "=" * 50)
    print("🎯 To test the agent properly:")
    print("1. Run: adk web")
    print("2. Open the Web UI in your browser")
    print("3. Send messages to the agent")
    print("4. The agent will coordinate game rounds using ADK delegation!")
    print("\nExample messages:")
    print("- 'Start a new game with 4 players'")
    print("- 'Play a complete round'")
    print("- 'Check the current game state'")
    print("- 'Delegate to RiskPlayer_Player1: Play your turn'")
    
    print("\n🔧 ADK Delegation Pattern:")
    print("- The GameCoordinator can delegate to any player agent")
    print("- Player agents will execute their turns using MCP tools")
    print("- All agents share the same session state")
    print("- No HTTP calls needed - pure ADK delegation")

def main():
    """Main test function"""
    test_agent()

if __name__ == "__main__":
    main() 