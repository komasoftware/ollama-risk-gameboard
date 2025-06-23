#!/usr/bin/env python3

import asyncio
import json
import ollama

def test_function_calling():
    """Test function calling with Ollama."""
    
    # Simple function definition
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_game_state",
                "description": "Get the current state of the Risk game",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]
    
    try:
        print("Testing Ollama function calling...")
        print(f"Tools: {json.dumps(tools, indent=2)}")
        
        response = ollama.chat(
            model='llama3.2',
            messages=[
                {"role": "system", "content": "You are a Risk game agent. Use the available functions to get game information."},
                {"role": "user", "content": "Get the current game state"}
            ],
            tools=tools,
            stream=False
        )
        
        print(f"Response: {response}")
        
        if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
            print(f"Tool calls: {response.message.tool_calls}")
        else:
            print("No tool calls in response")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_function_calling() 