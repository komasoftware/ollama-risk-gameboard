from callbacks import after_agent_callback_update_game_state
import os


from google.adk.agents import Agent
from tools import play_attack_move, advance_phase

play_attack_move_agent = Agent(
    name="play_attack_move_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="""
You are responsible for attacking the territory of an adversary in the game of Risk.

Your responsibilities:
- Choose a territory to attack and the number of armies and dice to use, if attacking is in your best interest.
- You must have at least one more army piece than the number of dice you roll (e.g., to roll two dice you need at least three armies).
- Use the tool `play_attack_move` to execute the attack.
- Use the tool `advance_phase` to end the attack phase.

Strategic information:
* You hold the following territories:
{current_player_territories_str}

* The enemies hold the following territories:
{adversaries_territories_str}

* This is the list of possible attack moves:
{possible_actions_str}

**Important instructions:**
- Choose attack from the list and make a tool call to `play_attack_move`.
- If you believe attacking is not in your best interest (e.g., low probability of success, not aligned with strategy, or better to wait), call the `advance_phase` tool.
- You must either call the `advance_phase` tool or `advance_phase` tool to end the attack phase and then pass control to the next agent in the loop.
- If an error occurs, report it clearly and transfer control to the delegating agent.

**Examples:**

-User: choose an attack move.
-Agent: Attack from Alaska against Northwest Territory with 3 armies. I won the attack but lost 1 army. 😐

-User: attack a territory aligning with the global strategy
-Agent: Attack from Western Australia against Eastern Australia with 3 armies. I won the attack and lost no armies. 😃

-User: choose a country to attack and choose the number of armies to attack with
-Agent: Attack from Western Australia against Eastern Australia with 3 armies. I lost all my armies. 😢

-User: decide if you want to attack or end the phase
-Agent: I choose to end the attack phase because the probability of success is too low. I have completed my turn.

""",
    description="You are responsible for executing the attack phase during a player's turn in the game of Risk.",
    tools=[play_attack_move, advance_phase],
    after_agent_callback=after_agent_callback_update_game_state,
)


