import asyncio
import os
from dotenv import load_dotenv
import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

print(f"using {os.getenv('GEMINI_MODEL')}")

from risk.agent import risk_agent
from utils import call_agent_async, display_state
from risk_api import RiskAPIClient
from game_state import GameStateRoot

risk_api_client = RiskAPIClient(os.getenv("RISK_API_BASE_URL"))
risk_api_response = risk_api_client.get_game_state()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session_service = InMemorySessionService()


try:
    with open(os.path.join(os.path.dirname(__file__), "risk-map.svg"), "r", encoding="utf-8") as f:
        risk_map_svg_content = f.read()
except Exception as e:
    print(f"Error reading risk-map.svg: {e}")
    risk_map_svg_content = None

initial_state = {
    "user_name": "Koen",
    "game_state": GameStateRoot.from_risk_api_response(risk_api_response),
    "risk_map_svg": risk_map_svg_content,
}


async def main_async():
    # Setup constants
    APP_NAME = "Risk Agent"
    USER_ID = "koen"

    new_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state=initial_state,
    )
    SESSION_ID = new_session.id
    print(f"Created new session: {SESSION_ID}")

    # ===== PART 4: Agent Runner Setup =====
    # Create a runner with the memory agent
    runner = Runner(
        agent=risk_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # ===== PART 5: Interactive Conversation Loop =====
    print("\nWelcome to Risk Agent Chat!")
    print("You can ask to start a new game with 1 to 6 players.")
    print("Or you can ask about the current game and the strategic positions of each player.\n")
    print("And finally, you can ask to play a round in the current game..\n")

    while True:
        # Get user input
        user_input = input("You: ")

        # Check if user wants to exit
        if user_input.lower() in ["exit", "quit"]:
            print("Ending the game.")
            break

        # Process the user query through the agent
        await call_agent_async(runner, USER_ID, SESSION_ID, user_input)


if __name__ == "__main__":
    asyncio.run(main_async())
