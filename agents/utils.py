import logging
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.genai import types
from game_state import GameStateRoot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

run_config = RunConfig(
    streaming_mode=StreamingMode.NONE,
    max_llm_calls=100  # <-- Set your desired limit here
)

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


async def display_state(
    session_service, app_name, user_id, session_id, label="Current State"
):
    """Display the current session state in a formatted way."""
    try:
        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

        # Format the output with clear sections
        logger.info(f"\n{'-' * 10} {label} {'-' * 10}")

        # Handle the user name
        user_name = session.state.get("user_name", "Unknown")
        game_state: GameStateRoot = session.state.get("game_state")

        logger.info(f"🧑‍💼 User: {user_name}")
        logger.info(f"🎲 Player: {game_state.get_current_player_name()}")
        logger.info(f"🔁 Round: {game_state.get_current_game_round()}")
        logger.info(f"⏳ Phase: {game_state.get_current_turn_phase()}")
        logger.info(
            f"🗺️ Territories: \n{game_state.get_current_player_territories_str()}"
        )

        logger.info("-" * (22 + len(label)))
    except Exception as e:
        logger.info(f"Error displaying state: {e}")


async def process_agent_response(event):
    """Process and display agent response events."""
    # Log basic event info
    logger.info(f"Event ID: {event.id}, Author: {event.author}")

    # Check for final response after specific parts
    final_response = None
    if event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            final_response = event.content.parts[0].text.strip()
            # Use colors and formatting to make the final response stand out
            logger.info(
                f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╔══ AGENT RESPONSE ═════════════════════════════════════════{Colors.RESET}"
            )
            logger.info(f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}")
            logger.info(
                f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╚═════════════════════════════════════════════════════════════{Colors.RESET}\n"
            )
        else:
            logger.info(
                f"\n{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD}==> Final Agent Response: [No text content in final event]{Colors.RESET}\n"
            )

    return final_response


async def call_agent_async(runner, user_id, session_id, query):
    """Call the agent asynchronously with the user's query."""
    content = types.Content(role="user", parts=[types.Part(text=query)])
    logger.info(
        f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}--- Running Query: {query} ---{Colors.RESET}"
    )
    final_response_text = None

    # Display state before processing
    await display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State BEFORE processing",
    )

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content, run_config=run_config
        ):
            # Process each event and get the final response if available
            response = await process_agent_response(event)
            if response:
                final_response_text = response
    except Exception as e:
        logger.info(f"Error during agent call: {e}")

    # Display state after processing the message
    await display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State AFTER processing",
    )

    return final_response_text
