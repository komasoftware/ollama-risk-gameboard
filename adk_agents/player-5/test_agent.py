#!/usr/bin/env python3
"""
Test script for the ADK Risk Player Agent
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import root_agent
from google.adk.tools.mcp_tool import MCPToolset

def test_agent():
    """Test the Risk player agent"""
    
    print("🧪 Testing ADK Risk Player Agent...")
    print("=" * 50)
    
    # Test 1: Check if agent is created
    print("✅ Agent created successfully")
    print(f"   Name: {root_agent.name}")
    print(f"   Description: {root_agent.description}")
    print(f"   Tools: {len(root_agent.tools)} tool(s)")
    
    # Test 2: Check MCP toolset
    mcp_toolset = None
    for tool in root_agent.tools:
        if isinstance(tool, MCPToolset):
            mcp_toolset = tool
            break
    
    if mcp_toolset:
        print(f"✅ MCP Toolset found")
        print(f"   Type: {type(mcp_toolset)}")
    else:
        print("❌ MCP Toolset not found")
    
    # Test 3: Check configuration
    print("\n⚙️  Configuration:")
    print(f"   MCP Server URL: {os.getenv('MCP_SERVER_URL', 'https://risk-mcp-server-441582515789.europe-west4.run.app/mcp/stream')}")
    print(f"   Gemini Model: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')}")
    print(f"   Project ID: {os.getenv('PROJECT_ID', 'koen-gcompany-demo')}")
    print(f"   Location: {os.getenv('GOOGLE_CLOUD_LOCATION', 'global')}")
    print(f"   Use Vertex AI: {os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE')}")
    print(f"   Google Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")
    
    print("\n" + "=" * 50)
    print("🎯 To test the agent properly:")
    print("1. Run: adk web")
    print("2. Open the Web UI in your browser")
    print("3. Send messages to the agent")
    print("4. The agent will use MCP tools to play Risk!")
    print("\nExample messages:")
    print("- 'What is the current game state?'")
    print("- 'Start a new game with 4 players'")
    print("- 'Play a turn for player 1'")

def main():
    """Main test function"""
    test_agent()

if __name__ == "__main__":
    main() 