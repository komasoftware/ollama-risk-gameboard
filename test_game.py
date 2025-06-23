#!/usr/bin/env python3
"""
Simple test script to start a game with AI agents.
"""

import asyncio
from agents.simple_agent import SimpleAgent, AggressiveAgent, DefensiveAgent
from agents.game_orchestrator import run_single_game


async def main():
    """Test a simple game with AI agents."""
    print("🤖 Starting AI Agents Test Game")
    print("=" * 50)
    
    # Create agents with the correct player names
    agents = [
        SimpleAgent("Player 1", strategy="balanced"),
        AggressiveAgent("Player 2"),
        DefensiveAgent("Player 3"),
        SimpleAgent("Player 4", strategy="balanced"),
        AggressiveAgent("Player 5"),
        DefensiveAgent("Player 6")
    ]
    
    print(f"Created {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent.get_strategy_description()}")
    
    print("\n🎮 Starting game...")
    result = await run_single_game(agents)
    
    print(f"\n✅ Game completed!")
    print(f"Winner: {result['winner']}")
    print(f"Total turns: {result['total_turns']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc() 