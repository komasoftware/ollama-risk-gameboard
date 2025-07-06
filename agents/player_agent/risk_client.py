#!/usr/bin/env python3
"""
Risk Agent Client - CLI interface for interacting with the Risk Player Agent
Handles A2A streaming protocol properly with connection management
"""

import json
import requests
import sys
from typing import Dict, Any, Optional
import time

class RiskAgentClient:
    """Client for interacting with the Risk Player Agent via A2A protocol"""
    
    def __init__(self, agent_url: str = "http://localhost:8080"):
        self.agent_url = agent_url
        self.session = requests.Session()
    
    def send_turn_request(self, player_id: int, persona: str, message: str = "Play your turn") -> Optional[Dict[str, Any]]:
        """
        Send a turn request to the agent and wait for response
        
        Args:
            player_id: Player ID (1-6)
            persona: Persona description
            message: Text message to send
            
        Returns:
            Response data or None if failed
        """
        # Prepare the A2A streaming request
        request_data = {
            "jsonrpc": "2.0",
            "id": f"turn-{int(time.time())}",
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": f"msg-{int(time.time())}",
                    "parts": [
                        {
                            "type": "text",
                            "text": message
                        },
                        {
                            "type": "data",
                            "data": {
                                "player_id": str(player_id),
                                "persona": persona
                            }
                        }
                    ]
                }
            }
        }
        
        print(f"🎮 Sending turn request for Player {player_id}...")
        print(f"📝 Persona: {persona}")
        print("⏳ Waiting for response...")
        
        try:
            # Send streaming request
            response = self.session.post(
                self.agent_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=120  # 2 minute timeout
            )
            
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                return None
            
            # Process streaming response
            agent_response = None
            task_completed = False
            
            try:
                start_time = time.time()
                timeout = 30  # 30 second timeout
                
                for line in response.iter_lines():
                    # Check timeout
                    if time.time() - start_time > timeout:
                        print("⏰ Timeout reached, closing connection")
                        break
                        
                    if line:
                        line_str = line.decode('utf-8')
                        
                        # Handle ping messages (keep-alive)
                        if line_str.startswith(': ping'):
                            continue
                        
                        # Handle data messages
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                
                                # Check if this is our response
                                if 'result' in data and 'kind' in data['result'] and data['result']['kind'] == 'message':
                                    agent_response = data['result']
                                    print("✅ Received agent response!")
                                
                                # Check if task is completed
                                if 'result' in data and 'kind' in data['result'] and data['result']['kind'] == 'status-update':
                                    if 'status' in data['result'] and 'state' in data['result']['status']:
                                        if data['result']['status']['state'] == 'completed':
                                            task_completed = True
                                            print("✅ Task completed!")
                                            # Exit the loop after task completion
                                            break
                                    
                            except json.JSONDecodeError:
                                print(f"⚠️  Could not parse JSON: {line_str}")
                                continue
                                
                        # If we have a response and task is completed, we can exit
                        if agent_response and task_completed:
                            break
                                
            except Exception as e:
                # If we get a connection error but we already have a response, that's okay
                if agent_response:
                    print(f"⚠️  Connection closed (expected): {e}")
                else:
                    print(f"❌ Connection error: {e}")
                    return None
            
            # Close the connection gracefully
            try:
                response.close()
            except:
                pass  # Connection might already be closed
            
            if agent_response:
                return agent_response
            else:
                print("❌ No response received from agent")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test if the agent is reachable"""
        try:
            # Send a simple test request to see if agent responds
            test_data = {
                "jsonrpc": "2.0",
                "id": "test-connection",
                "method": "message/stream",
                "params": {
                    "message": {
                        "role": "user",
                        "messageId": "test",
                        "parts": [{"type": "text", "text": "test"}]
                    }
                }
            }
            response = self.session.post(
                self.agent_url,
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

def print_banner():
    """Print the client banner"""
    print("=" * 60)
    print("🎯 RISK AGENT CLIENT")
    print("=" * 60)
    print("Interactive client for the Risk Player Agent")
    print("Uses A2A streaming protocol for real-time responses")
    print("=" * 60)

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
    
    if 'parts' in response and response['parts']:
        for part in response['parts']:
            if 'text' in part:
                print(part['text'])
    
    print("=" * 60)

def main():
    """Main CLI interface"""
    print_banner()
    
    # Initialize client
    client = RiskAgentClient()
    
    # Test connection
    print("🔍 Testing connection to agent...")
    if not client.test_connection():
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
            response = client.send_turn_request(player_id, persona)
            
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
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break
    
    print("🎯 Thanks for using the Risk Agent Client!")

if __name__ == "__main__":
    main() 