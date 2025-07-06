#!/usr/bin/env python3
"""
Risk Agent Client - A2A client for interacting with Risk Player Agents
Uses A2A SDK for proper persistent streaming connections
"""

import json
import sys
import asyncio
from typing import Dict, Any, Optional
import httpx
from a2a.client import A2AClient
from a2a.types import SendStreamingMessageRequest, Message, TextPart, DataPart
import uuid
import re

class RiskAgentClient:
    """A2A client for interacting with Risk Player Agents - uses A2A SDK for persistent streaming"""
    
    def __init__(self, agent_url: str = "http://localhost:8080", risk_api_url: str = "https://risk-api-server-jn3e4lhybq-ez.a.run.app"):
        self.agent_url = agent_url
        self.risk_api_url = risk_api_url
        self.a2a_client = None
        self.httpx_client = None
        self.last_response = None
        self.connection_active = False
        self.session_id = str(uuid.uuid4())
    
    async def initialize(self):
        """Initialize the A2A client connection"""
        if not self.connection_active:
            self.httpx_client = httpx.AsyncClient()
            self.a2a_client = A2AClient(url=self.agent_url, httpx_client=self.httpx_client)
            self.connection_active = True
            print(f"🔌 [A2A] A2A client initialized (session id: {self.session_id})")
    
    async def send_turn_request(self, player_id: int, persona: str, message: str = "Play your turn") -> Optional[Dict[str, Any]]:
        """
        Send a turn request to the agent using A2A SDK streaming client
        
        Args:
            player_id: Player ID (1-6)
            persona: Persona description
            message: Text message to send
            
        Returns:
            Response data or None if failed
        """
        
        # Generate per-request UUIDs
        request_uuid = str(uuid.uuid4())
        task_uuid = str(uuid.uuid4())
        
        # Log request for debugging
        print(f"🎮 [A2A] Sending turn request for Player {player_id} (request id: {request_uuid}, task id: {task_uuid})")
        print(f"📝 [A2A] Persona: {persona}")
        
        try:
            
            # Create the message parts
            parts = [
                TextPart(text=f"Player ID: {player_id}"),
                TextPart(text=f"Persona: {persona}"),
                TextPart(text=f"Message: {message}"),
                DataPart(data={
                    "session_id": self.session_id,
                    "player_id": player_id,
                    "persona": persona
                })
            ]
            
            # Create the streaming request
            request = SendStreamingMessageRequest(
                id=request_uuid,
                params={
                    "message": Message(
                        role="user",
                        messageId=request_uuid,
                        taskId=task_uuid,
                        parts=parts
                    )
                }
            )
            
            # Send streaming message and collect responses
            responses = []
            agent_message = None
            try:
                async for response in self.a2a_client.send_message_streaming(request):
                    # Only print a single debug line for troubleshooting
                    # print(f"[DEBUG] Received response of type: {type(response)}")

                    # Check if this is a message response for our request
                    if (
                        hasattr(response, 'root') and hasattr(response.root, 'id') and response.root.id == request_uuid and
                        hasattr(response.root, 'result') and hasattr(response.root.result, 'kind') and response.root.result.kind == 'message'
                    ):
                        # Extract the agent's message
                        if hasattr(response.root.result, 'parts'):
                            for part in response.root.result.parts:
                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                    agent_message = part.root.text
                                elif hasattr(part, 'text'):
                                    agent_message = part.text
                        break
                    
                    # Check if this is a completion event for our task
                    elif (
                        hasattr(response, 'root') and hasattr(response.root, 'result') and hasattr(response.root.result, 'kind') and 
                        response.root.result.kind == 'status-update' and 
                        hasattr(response.root.result, 'status') and hasattr(response.root.result.status, 'state') and
                        response.root.result.status.state == 'completed' and
                        hasattr(response.root.result, 'taskId') and response.root.result.taskId == task_uuid
                    ):
                        break

            except Exception as e:
                print(f"⚠️  [A2A] Streaming error: {e}")
                if not responses:
                    raise
            
            # Show the agent's response in the UI
            if agent_message:
                print("\n" + "=" * 60)
                print("🤖 AGENT RESPONSE")
                print("=" * 60)
                print(agent_message)
                print("=" * 60)
                return {"agent_message": agent_message}
            else:
                print("❌ [A2A] No response received from agent")
                return None
                
        except Exception as e:
            print(f"❌ [A2A] Request failed: {e}")
            return None
    
    async def close_session(self):
        """Close the A2A client connection gracefully when client exits"""
        try:
            print("🔌 [A2A] Closing A2A client connection...")
            if self.httpx_client:
                try:
                    await self.httpx_client.aclose()
                except asyncio.CancelledError:
                    # Ignore cancellation errors during shutdown
                    pass
                except Exception as e:
                    print(f"⚠️  [A2A] Error closing httpx client: {e}")
                self.connection_active = False
                print("✅ [A2A] A2A client connection closed gracefully")
        except Exception as e:
            print(f"⚠️  [A2A] Error closing A2A client connection: {e}")
    
    async def test_connection(self) -> bool:
        """Test if the agent is reachable using A2A SDK"""
        try:
            # Initialize A2A client for testing with httpx client
            async with httpx.AsyncClient() as test_httpx_client:
                test_client = A2AClient(url=self.agent_url, httpx_client=test_httpx_client)
                
                # Generate per-request UUIDs
                request_uuid = str(uuid.uuid4())
                # Create a simple test message
                test_parts = [
                    TextPart(text="test"),
                    DataPart(data={"session_id": self.session_id})
                ]
                test_request = SendStreamingMessageRequest(
                    id=request_uuid,
                    params={
                        "message": Message(
                            role="user",
                            messageId=request_uuid,
                            parts=test_parts
                        )
                    }
                )
                
                # Try to send a test message
                async for response in test_client.send_message_streaming(test_request):
                    # If we get any response, the connection works
                    return True
                
                return False
        except Exception as e:
            print(f"❌ [A2A] Connection test failed: {e}")
            return False

    async def get_current_player(self) -> Optional[Dict[str, Any]]:
        """Fetch the current game state from the Risk API server and return the current player info."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.risk_api_url}/game-state")
                resp.raise_for_status()
                data = resp.json()
                # Try both 'game_state' and root for compatibility
                game_state = data.get('game_state', data)
                current_player = game_state.get('current_player')
                players = game_state.get('players', [])
                if current_player is not None and players:
                    # Extract numeric player ID from current_player string (e.g., "Player 5" -> 5)
                    if isinstance(current_player, str):
                        match = re.search(r'(\d+)', current_player)
                        if match:
                            numeric_id = int(match.group(1))
                            # Find player info by matching the numeric ID
                            player_info = next((p for p in players if p.get('id') == numeric_id - 1), None)
                            return {"id": numeric_id, "info": player_info}
                    elif isinstance(current_player, int):
                        # If current_player is already numeric, use it directly
                        player_info = next((p for p in players if p.get('id') == current_player), None)
                        return {"id": current_player + 1, "info": player_info}
                return None
        except Exception as e:
            print(f"⚠️  Could not fetch game state: {e}")
            return None

def print_banner():
    """Print the client banner"""
    print("=" * 60)
    print("🎯 RISK AGENT CLIENT")
    print("=" * 60)
    print("Interactive client for the Risk Player Agent")
    print("Uses A2A streaming protocol for real-time responses")
    print("=" * 60)
    # Print session id for debugging
    # The client is initialized in main(), so we print session id after client creation

def get_persona_choice() -> str:
    """Get persona choice from user"""
    personas = {
        "1": "You are an aggressive player who always attacks when possible",
        "2": "You are a defensive player who focuses on fortifying territories", 
        "3": "You are a balanced player who adapts strategy based on game state",
        "4": "You are a risk-taker who makes bold moves and takes chances",
        "5": "You are a cautious player who prioritizes safety and consolidation"
    }
    
    print("\n🎭 Available Personas:")
    for key, persona in personas.items():
        print(f"  {key}. {persona}")
    
    while True:
        choice = input("\nSelect persona (1-5): ").strip()
        if choice in personas:
            return personas[choice]
        else:
            print("❌ Invalid choice. Please select 1-5.")

def get_player_id() -> int:
    """Get player ID from user"""
    while True:
        try:
            player_id = int(input("\n🎮 Enter player ID (1-6): ").strip())
            if 1 <= player_id <= 6:
                return player_id
            else:
                print("❌ Player ID must be between 1 and 6.")
        except ValueError:
            print("❌ Please enter a valid number.")

def print_response(response: Dict[str, Any]):
    """Pretty print the agent response"""
    print("\n" + "=" * 60)
    print("🤖 AGENT RESPONSE")
    print("=" * 60)
    
    if 'agent_message' in response:
        print(response['agent_message'])
    else:
        print("❌ No agent message found in response")
    
    print("=" * 60)

async def main():
    """Main CLI interface"""
    print_banner()
    
    # Initialize client
    client = RiskAgentClient()
    print(f"🆔 Session ID: {client.session_id}")
    
    # Initialize A2A client connection
    await client.initialize()
    
    # Test connection
    print("🔍 Testing connection to agent...")
    if not await client.test_connection():
        print("❌ Cannot connect to agent. Make sure it's running on http://localhost:8080")
        sys.exit(1)
    print("✅ Connected to agent successfully!")
    
    # Main interaction loop
    while True:
        try:
            # Fetch current player from Risk API
            current_player = await client.get_current_player()
            if current_player:
                player_id = current_player["id"]  # Already converted to 1-based ID
                player_name = current_player["info"].get("name") if current_player["info"] else None
                print(f"\n🎮 Current player: {str(player_name) if player_name else 'Unknown'} (Player {player_id})")
            else:
                print("\n⚠️  Could not determine current player. Defaulting to Player 1.")
                player_id = 1

            persona = get_persona_choice()
            
            # Send request
            response = await client.send_turn_request(player_id, persona)
            
            if response:
                print_response(response)
            else:
                print("❌ Failed to get response from agent")
            
            # Ask if user wants to continue
            continue_choice = input("\n🔄 Send another request? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes']:
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            await client.close_session()
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break
    
    # Graceful cleanup when client exits
    await client.close_session()
    print("🎯 Thanks for using the Risk Agent Client!")

if __name__ == "__main__":
    asyncio.run(main()) 