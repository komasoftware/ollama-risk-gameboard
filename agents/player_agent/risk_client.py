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

class RiskAgentClient:
    """A2A client for interacting with Risk Player Agents - uses A2A SDK for persistent streaming"""
    
    def __init__(self, agent_url: str = "http://localhost:8080"):
        self.agent_url = agent_url
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
            try:
                async for response in self.a2a_client.send_message_streaming(request):
                    responses.append(response)
                    print(f"🔍 [DEBUG] Raw response: {response}")
                    print(f"🔍 [DEBUG] Response type: {type(response)}")
                    print(f"🔍 [DEBUG] Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

                    # Debug: Print id, contextId, and taskId if available
                    if hasattr(response, 'id'):
                        print(f"🔍 [DEBUG] Response id: {response.id}")
                    if hasattr(response, 'contextId'):
                        print(f"🔍 [DEBUG] ContextId: {response.contextId}")
                    if hasattr(response, 'taskId'):
                        print(f"🔍 [DEBUG] TaskId: {response.taskId}")

                    # Check if this is a message response for our request
                    if (
                        hasattr(response, 'root') and hasattr(response.root, 'id') and response.root.id == request_uuid and
                        hasattr(response.root, 'result') and hasattr(response.root.result, 'kind') and response.root.result.kind == 'message'
                    ):
                        print(f"🔍 [DEBUG] Found message response for our request!")
                        # Print the message content
                        if hasattr(response.root.result, 'parts'):
                            for part in response.root.result.parts:
                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                    print(f"🤖 [A2A] Agent: {part.root.text}")
                                elif hasattr(part, 'text'):
                                    print(f"🤖 [A2A] Agent: {part.text}")
                        print(f"🔍 [DEBUG] Breaking out of streaming loop (matched id)")
                        break
                    
                    # Check if this is a completion event for our task
                    elif (
                        hasattr(response, 'root') and hasattr(response.root, 'result') and hasattr(response.root.result, 'kind') and 
                        response.root.result.kind == 'status-update' and 
                        hasattr(response.root.result, 'status') and hasattr(response.root.result.status, 'state') and
                        response.root.result.status.state == 'completed' and
                        hasattr(response.root.result, 'taskId') and response.root.result.taskId == task_uuid
                    ):
                        print(f"🔍 [DEBUG] Found completion event for our task!")
                        print(f"🔍 [DEBUG] Breaking out of streaming loop (matched taskId)")
                        break

                    # Debug: Print what kind of event we got if not matched
                    if hasattr(response, 'root') and hasattr(response.root, 'result'):
                        print(f"🔍 [DEBUG] Response has result attribute")
                        if hasattr(response.root.result, 'kind'):
                            print(f"🔍 [DEBUG] Event kind: {response.root.result.kind}")
                        else:
                            print(f"🔍 [DEBUG] Result has no kind attribute")
                    else:
                        print(f"🔍 [DEBUG] No result attribute found in response")

            except Exception as e:
                print(f"⚠️  [A2A] Streaming error (this might be expected): {e}")
                # Continue processing if we have responses
                if not responses:
                    raise
            
            # Store the last response
            if responses:
                print(f"🔍 [DEBUG] Storing {len(responses)} responses")
                self.last_response = {
                    "responses": [r.model_dump() if hasattr(r, 'model_dump') else str(r) for r in responses],
                    "final_response": responses[-1].model_dump() if hasattr(responses[-1], 'model_dump') else str(responses[-1])
                }
                print("✅ [A2A] Received agent response!")
                print(f"🔍 [DEBUG] Returning response to main loop")
                return self.last_response
            
            print("❌ [A2A] No response received from agent")
            return None
            
            # This should never be reached with the new approach
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
    
    print(f"🔍 [DEBUG] Response keys: {list(response.keys())}")
    if 'final_response' in response:
        final_response = response['final_response']
        print(f"🔍 [DEBUG] Final response type: {type(final_response)}")
        print(f"🔍 [DEBUG] Final response keys: {list(final_response.keys()) if isinstance(final_response, dict) else 'not a dict'}")
        
        # If it's a message event with top-level parts
        if isinstance(final_response, dict) and final_response.get('kind') == 'message' and 'parts' in final_response:
            print(f"🔍 [DEBUG] Found message with parts: {len(final_response['parts'])} parts")
            for part in final_response['parts']:
                if 'text' in part:
                    print(part['text'])
        elif 'content' in final_response and final_response['content']:
            for part in final_response['content'].get('parts', []):
                if 'text' in part:
                    print(part['text'])
        elif 'message' in final_response and final_response['message']:
            for part in final_response['message'].get('parts', []):
                if 'text' in part:
                    print(part['text'])
        else:
            print(f"🔍 [DEBUG] No matching structure found in final_response")
    elif 'parts' in response and response['parts']:
        for part in response['parts']:
            if 'text' in part:
                print(part['text'])
    else:
        print(f"🔍 [DEBUG] No final_response or parts found in response")
    
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
            # Get user input
            player_id = get_player_id()
            persona = get_persona_choice()
            
            # Send request
            print(f"🔍 [DEBUG] Calling send_turn_request...")
            response = await client.send_turn_request(player_id, persona)
            print(f"🔍 [DEBUG] send_turn_request returned: {response is not None}")
            
            if response:
                print(f"🔍 [DEBUG] Calling print_response...")
                print_response(response)
            else:
                print("❌ Failed to get response from agent")
            
            # Ask if user wants to continue
            continue_choice = input("\n🔄 Send another request? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes']:
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break
    
    # Graceful cleanup when client exits
    await client.close_session()
    print("🎯 Thanks for using the Risk Agent Client!")

if __name__ == "__main__":
    asyncio.run(main()) 