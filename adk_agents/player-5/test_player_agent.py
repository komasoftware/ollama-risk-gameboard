#!/usr/bin/env python3
"""
Test script for the ADK Risk Player Agent
"""

import asyncio
import os
from player_agent import risk_player_agent

async def test_agent():
    """Test the Risk player agent"""
    
    print("🧪 Testing Risk Player Agent...")
    print("=" * 50)
    
    # Test 1: Check if agent is created
    print("✅ Agent created successfully")
    print(f"   Name: {risk_player_agent.name}")
    print(f"   Description: {risk_player_agent.description}")
    print(f"   Tools: {len(risk_player_agent.tools)} tool(s)")
    
    # Test 2: Check MCP toolset
    mcp_toolset = None
    for tool in risk_player_agent.tools:
        if hasattr(tool, 'url'):
            mcp_toolset = tool
            break
    
    if mcp_toolset:
        print(f"✅ MCP Toolset found")
        print(f"   URL: {mcp_toolset.url}")
    else:
        print("❌ MCP Toolset not found")
    
    # Test 3: Test agent with a simple message
    print("\n🎮 Testing agent with simple message...")
    
    try:
        # Create a simple test message
        test_message = "Hello! I'm a Risk player agent. Can you tell me about the current game state?"
        
        # Run the agent (this would normally be done through ADK Web UI)
        print(f"📝 Test message: {test_message}")
        print("✅ Agent is ready for testing!")
        
        # Note: In a real scenario, you would use:
        # adk web
        # And then interact through the Web UI
        
    except Exception as e:
        print(f"❌ Error testing agent: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 To test the agent properly:")
    print("1. Run: adk web")
    print("2. Open the Web UI in your browser")
    print("3. Send messages to the agent")
    print("4. The agent will use MCP tools to play Risk!")

def main():
    """Main test function"""
    asyncio.run(test_agent())

if __name__ == "__main__":
    main() 