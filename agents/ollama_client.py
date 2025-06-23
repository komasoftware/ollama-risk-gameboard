"""
Ollama Client for AI agent interactions with function calling support.
Handles communication with Ollama models and function calling for Risk API.
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import ollama
from .risk_api import RiskAPIClient, GameState

logger = logging.getLogger(__name__)

@dataclass
class FunctionDefinition:
    """Definition of a function that can be called by the AI agent."""
    name: str
    description: str
    parameters: Dict[str, Any]


class OllamaAgentClient:
    """Client for AI agent interactions using Ollama with function calling."""
    
    def __init__(self, model: str = "llama3.2", risk_client: Optional[RiskAPIClient] = None):
        self.model = model
        self.risk_client = risk_client or RiskAPIClient()
        self.functions = self._define_functions()
    
    def _define_functions(self) -> List[FunctionDefinition]:
        """Define the functions that can be called by the AI agent."""
        return [
            FunctionDefinition(
                name="get_game_state",
                description="Get the current state of the Risk game",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            FunctionDefinition(
                name="reinforce",
                description="Add armies to a territory during the reinforce phase",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer", "description": "Your unique player ID"},
                        "territory": {"type": "string", "description": "Name of the territory to reinforce"},
                        "num_armies": {"type": "integer", "description": "Number of armies to add"}
                    },
                    "required": ["player_id", "territory", "num_armies"]
                }
            ),
            FunctionDefinition(
                name="attack",
                description="Attack from one territory to another",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer", "description": "Your unique player ID"},
                        "from_territory": {"type": "string", "description": "Name of the attacking territory"},
                        "to_territory": {"type": "string", "description": "Name of the defending territory"},
                        "num_armies": {"type": "integer", "description": "Number of armies to use in the attack"},
                        "num_dice": {"type": "integer", "description": "Number of dice to roll in the attack"},
                        "repeat": {"type": "boolean", "description": "Whether to continue attacking after this attack (true) or stop (false)"}
                    },
                    "required": ["player_id", "from_territory", "to_territory", "num_armies", "num_dice", "repeat"]
                }
            ),
            FunctionDefinition(
                name="fortify",
                description="Move armies from one territory to another during fortify phase",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer", "description": "Your unique player ID"},
                        "from_territory": {"type": "string", "description": "Name of the source territory"},
                        "to_territory": {"type": "string", "description": "Name of the destination territory"},
                        "num_armies": {"type": "integer", "description": "Number of armies to move"}
                    },
                    "required": ["player_id", "from_territory", "to_territory", "num_armies"]
                }
            ),
            FunctionDefinition(
                name="move_armies",
                description="Move armies after a successful attack",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer", "description": "Your unique player ID"},
                        "from_territory": {"type": "string", "description": "Name of the attacking territory"},
                        "to_territory": {"type": "string", "description": "Name of the newly conquered territory"},
                        "num_armies": {"type": "integer", "description": "Number of armies to move"}
                    },
                    "required": ["player_id", "from_territory", "to_territory", "num_armies"]
                }
            ),
            FunctionDefinition(
                name="trade_cards",
                description="Trade in cards for additional armies",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer", "description": "Your unique player ID"},
                        "cards": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of card names to trade"
                        }
                    },
                    "required": ["player_id", "cards"]
                }
            )
        ]
    
    def _function_map(self) -> Dict[str, Callable]:
        """Map function names to their implementations."""
        return {
            "get_game_state": self.risk_client.get_game_state,
            "reinforce": self.risk_client.reinforce,
            "attack": self.risk_client.attack,
            "fortify": self.risk_client.fortify,
            "move_armies": self.risk_client.move_armies,
            "trade_cards": self.risk_client.trade_cards
        }
    
    async def get_agent_response(self, prompt: str, player_name: str, player_id: Optional[int] = None, use_tools: bool = True) -> str:
        """Get a response from the AI agent with function calling support."""
        # Create the system prompt
        system_prompt = f"""You are an AI agent playing the board game Risk. Your name is {player_name}.

🔥 CRITICAL VICTORY CONDITION: You must ELIMINATE ALL OTHER PLAYERS to win! 🔥
This means you need to conquer every territory on the board and eliminate every opponent.
Territory control alone is not enough - you must annihilate your enemies completely!

CARD SYSTEM:
- You earn a card EVERY TIME you conquer a territory (not just at the end of turn)
- Cards come in four types: Infantry, Cavalry, Artillery, and Joker (wild).
- During the Reinforce Phase, you can trade sets of 3 cards for bonus armies:
  * 3 Infantry = 4 armies
  * 3 Cavalry = 6 armies
  * 3 Artillery = 8 armies
  * 1 Infantry + 1 Cavalry + 1 Artillery = 10 armies
  * Jokers can substitute for any type; any valid 3-card combo with jokers = 10 armies
- If you trade a card that matches a territory you own, you get +2 bonus armies placed on that territory.
- You can trade multiple times per turn if you have enough cards.
- Trade cards using the `trade_cards` function.

You interact with the game by calling functions. A player's turn has three phases: Reinforce, Attack, and Fortify. The phase will advance automatically when you have no more valid actions in the current phase.

**CRITICAL: You MUST use the function calling mechanism provided by Ollama. DO NOT write function calls as text. Use the tools parameter to make actual function calls.**

**Turn Workflow:**
1.  **Reinforce Phase**: Place all your reinforcement armies across your territories using the `reinforce` function. You can call it multiple times. The phase will advance automatically when you have no more armies to place.
2.  **Attack Phase**: 🎯 BE AGGRESSIVE! Attack enemy territories to expand your empire and eliminate opponents. You earn a card for every territory you conquer! You can call `attack` multiple times. The phase will advance automatically when you have no more valid attacks.
    - **IMPORTANT:** You MUST use the `attack` function to attack. Plain text or reasoning alone will NOT result in any attacks. Only function calls will be executed.
    - **EXAMPLE:**
      To attack from Alaska to Northwest Territory with 3 armies and 3 dice, use the attack function with these parameters:
      - player_id: 0
      - from_territory: "Alaska"
      - to_territory: "Northwest Territory"
      - num_armies: 3
      - num_dice: 3
    - You can call `attack` multiple times in a single turn. The phase will advance automatically when you have no more valid attacks.
3.  **Fortify Phase**: You can move armies between two of your connected territories once. Use the `fortify` function for this. The phase will advance automatically when you have no more valid fortify actions.

Analyze the game state provided in the user prompt and make strategic decisions. Focus on making the best moves in each phase - the game will automatically advance phases when appropriate.

IMPORTANT: Use the function calling mechanism provided by Ollama. DO NOT write function calls as text strings."""

        # Conditionally enable tools
        if use_tools:
            # Convert function definitions to Ollama format
            tools = []
            for func in self.functions:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": func.name,
                        "description": func.description,
                        "parameters": func.parameters
                    }
                })

            logger.info(f"[DEBUG] Calling Ollama with tools: {len(tools)} functions defined")
            logger.info(f"[DEBUG] Tools being passed: {json.dumps(tools, indent=2)}")

            # Make the API call to Ollama with function calling
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                stream=False
            )
        else:
            # Make the API call without function calling
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )

        try:
            # Log the AI's thinking process
            ai_thinking = response.message.content
            if ai_thinking and ai_thinking.strip():
                logger.info(f"\n🤔 {player_name} THINKING:\n{ai_thinking}\n")
            
            # Debug: Check if tool_calls exist
            has_tool_calls = hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls
            logger.info(f"[DEBUG] use_tools={use_tools}, has_tool_calls={has_tool_calls}")
            logger.info(f"[DEBUG] Response object type: {type(response)}")
            logger.info(f"[DEBUG] Response message type: {type(response.message)}")
            logger.info(f"[DEBUG] Response message attributes: {dir(response.message)}")
            
            if has_tool_calls:
                logger.info(f"[DEBUG] Tool calls found: {response.message.tool_calls}")
                logger.info(f"[DEBUG] Number of tool calls: {len(response.message.tool_calls)}")
                for i, tool_call in enumerate(response.message.tool_calls):
                    logger.info(f"[DEBUG] Tool call {i}: {tool_call}")
            else:
                logger.info(f"[DEBUG] No tool_calls found in response")
                logger.info(f"[DEBUG] Response message content: {repr(response.message.content)}")
            
            # Check if the response contains tool calls and tools were used
            if use_tools and has_tool_calls:
                # Handle the function calls
                tool_results = await self._handle_function_calls(response.message.tool_calls, player_id=player_id)
                logger.info(f"\n🎯 {player_name} DECISION(S):\n{tool_results}\n")
                return f"Executed actions: {tool_results}"
            else:
                # Fallback: Try to parse function calls from text content
                logger.info(f"[DEBUG] No tool calls found, checking text content for function calls")
                if 'attack' in ai_thinking.lower() or 'function' in ai_thinking.lower():
                    logger.info(f"[DEBUG] Text contains potential function calls, but LLM didn't use tool_calls mechanism")
                    logger.info(f"[DEBUG] This means the LLM is not properly using Ollama's function calling feature")
                return response.message.content
            
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"
    
    async def _handle_function_calls(self, tool_calls, player_id: Optional[int] = None, phase: Optional[str] = None) -> str:
        """Handle function calls from the AI agent."""
        results = []
        function_map = self._function_map()
        
        # Get player name from game state if player_id is provided
        player_name = None
        if player_id is not None:
            try:
                game_state = self.risk_client.get_game_state()
                for p in game_state.players.values():
                    if p.id == player_id:
                        player_name = p.name
                        break
            except Exception as e:
                logger.warning(f"[DEBUG] Could not get player name for id {player_id}: {e}")
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = tool_call.function.arguments
            
            # Enhanced log: include player_id and phase if available
            log_prefix = f"🎯 Player {player_id if player_id is not None else 'Unknown'}"
            if phase:
                log_prefix += f" ({phase})"
            logger.info(f"{log_prefix}: Calling {function_name} with args: {arguments}")
            
            # --- Sanitize and Validate Arguments ---
            # 1. Inject player_id if missing for required functions
            if function_name in ["reinforce", "attack", "fortify", "trade_cards"] and 'player_id' not in arguments and player_id is not None:
                arguments['player_id'] = player_id

            # 2. Ensure 'player_id' is an integer
            if 'player_id' in arguments:
                try:
                    arguments['player_id'] = int(arguments['player_id'])
                except (ValueError, TypeError):
                    if player_id is not None:
                        arguments['player_id'] = player_id
                    else:
                        results.append(f"Invalid or missing player_id for {function_name}")
                        continue

            # 3. Handle army parameters for different functions
            if function_name in ["reinforce", "attack", "fortify", "move_armies"]:
                # Handle both 'armies' and 'num_armies' keys - keep as num_armies for API
                armies_value = None
                if 'num_armies' in arguments:
                    armies_value = arguments['num_armies']
                    # Keep as num_armies, don't delete
                elif 'armies' in arguments:
                    armies_value = arguments['armies']
                    del arguments['armies']
                    arguments['num_armies'] = armies_value
                
                if armies_value is not None:
                    try:
                        armies_value = int(armies_value)
                        arguments['num_armies'] = armies_value
                    except (ValueError, TypeError):
                        results.append(f"Invalid non-integer value for armies: {armies_value}")
                        continue
                else:
                    results.append(f"Missing armies parameter for {function_name}")
                    continue
                
                # Handle num_dice for attack functions
                if function_name == "attack":
                    if 'num_dice' in arguments:
                        try:
                            arguments['num_dice'] = int(arguments['num_dice'])
                        except (ValueError, TypeError):
                            results.append(f"Invalid non-integer value for num_dice: {arguments['num_dice']}")
                            continue
                    else:
                        results.append(f"Missing num_dice parameter for attack")
                        continue
                    
                    # Always set repeat = false
                    arguments['repeat'] = False
                
                # Validate required parameters for each function
                if function_name == "reinforce":
                    required_keys = ['player_id', 'territory', 'num_armies']
                    if not all(key in arguments for key in required_keys):
                        missing = [key for key in required_keys if key not in arguments]
                        results.append(f"Missing required parameters for reinforce: {missing}")
                        continue
                elif function_name == "attack":
                    required_keys = ['player_id', 'from_territory', 'to_territory', 'num_armies', 'num_dice', 'repeat']
                    if not all(key in arguments for key in required_keys):
                        missing = [key for key in required_keys if key not in arguments]
                        results.append(f"Missing required parameters for attack: {missing}")
                        continue
                elif function_name == "fortify":
                    required_keys = ['player_id', 'from_territory', 'to_territory', 'num_armies']
                    if not all(key in arguments for key in required_keys):
                        missing = [key for key in required_keys if key not in arguments]
                        results.append(f"Missing required parameters for fortify: {missing}")
                        continue
                elif function_name == "move_armies":
                    required_keys = ['player_id', 'from_territory', 'to_territory', 'num_armies']
                    if not all(key in arguments for key in required_keys):
                        missing = [key for key in required_keys if key not in arguments]
                        results.append(f"Missing required parameters for move_armies: {missing}")
                        continue
                
                # Remove any unexpected keys
                if function_name == "reinforce":
                    expected_keys = ['player_id', 'territory', 'num_armies']
                elif function_name == "attack":
                    expected_keys = ['player_id', 'from_territory', 'to_territory', 'num_armies', 'num_dice', 'repeat']
                elif function_name == "fortify":
                    expected_keys = ['player_id', 'from_territory', 'to_territory', 'num_armies']
                elif function_name == "move_armies":
                    expected_keys = ['player_id', 'from_territory', 'to_territory', 'num_armies']
                else:
                    expected_keys = []
                    
                for key in list(arguments.keys()):
                    if key not in expected_keys:
                        del arguments[key]
            # --- End Sanitization ---
            
            if function_name in function_map:
                try:
                    # Call the function
                    if function_name == "get_game_state":
                        result = function_map[function_name]()
                        results.append(f"Game state retrieved: Current player is {result.current_player}, phase is {result.phase}")
                    elif function_name == "reinforce":
                        result = function_map[function_name](**arguments)
                        results.append(f"Reinforced {arguments.get('territory')} with {arguments.get('num_armies')} armies")
                        # Get fresh game state after reinforce
                        fresh_state = self.risk_client.get_game_state()
                        logger.info(f"[DEBUG] Fresh game state after reinforce: player armies = {fresh_state.players.get(player_name, 'Unknown').armies if player_name else 'Unknown'}")
                    elif function_name == "attack":
                        # --- BEGIN DETAILED ATTACK LOGGING ---
                        logger.info(f"[ATTACK LOG] Attempting attack with arguments: {arguments}")
                        # --- BEGIN PRE-VALIDATION ---
                        game_state = self.risk_client.get_game_state()
                        # Use the player_name we already got, or try to get it again if not available
                        if not player_name:
                            for p in game_state.players.values():
                                if p.id == arguments['player_id']:
                                    player_name = p.name
                                    break
                        if not player_name:
                            warn_msg = f"[ATTACK LOG] Skipping attack: could not find player name for id {arguments['player_id']}"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        from_terr = arguments['from_territory']
                        to_terr = arguments['to_territory']
                        if from_terr not in game_state.territories:
                            warn_msg = f"[ATTACK LOG] Skipping attack: from_territory '{from_terr}' not found in game state"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        if to_terr not in game_state.territories:
                            warn_msg = f"[ATTACK LOG] Skipping attack: to_territory '{to_terr}' not found in game state"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        from_terr_data = game_state.territories[from_terr]
                        to_terr_data = game_state.territories[to_terr]
                        if from_terr_data.owner != player_name:
                            warn_msg = f"[ATTACK LOG] Skipping attack: from_territory '{from_terr}' is not owned by player {player_name}"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        if to_terr_data.owner == player_name:
                            warn_msg = f"[ATTACK LOG] Skipping attack: to_territory '{to_terr}' is owned by player {player_name} (must be enemy)"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        if to_terr not in from_terr_data.adjacent_territories:
                            warn_msg = f"[ATTACK LOG] Skipping attack: to_territory '{to_terr}' is not adjacent to from_territory '{from_terr}'"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        armies_available = from_terr_data.armies
                        if arguments['num_armies'] > armies_available - 1:
                            warn_msg = f"[ATTACK LOG] Skipping attack: num_armies {arguments['num_armies']} exceeds armies in {from_terr} minus one ({armies_available - 1})"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        if arguments['num_dice'] > min(3, arguments['num_armies']):
                            warn_msg = f"[ATTACK LOG] Skipping attack: num_dice {arguments['num_dice']} exceeds allowed dice for num_armies {arguments['num_armies']}"
                            logger.warning(warn_msg)
                            results.append(warn_msg)
                            continue
                        # --- END PRE-VALIDATION ---
                        try:
                            attack_result = function_map[function_name](**arguments)
                            logger.info(f"[ATTACK LOG] Server response: {attack_result}")
                            results.append(f"Attacked from {arguments.get('from_territory')} to {arguments.get('to_territory')} with {arguments.get('num_armies')} armies (dice: {arguments.get('num_dice')}) | Server response: {attack_result}")
                            # Get fresh game state after attack
                            fresh_state = self.risk_client.get_game_state()
                            logger.info(f"[DEBUG] Fresh game state after attack: current player = {fresh_state.current_player}, phase = {fresh_state.phase}")
                        except Exception as e:
                            import requests
                            error_msg = f"[ATTACK LOG] Error executing attack: {str(e)} | Arguments: {arguments}"
                            if hasattr(e, 'response') and e.response is not None:
                                try:
                                    error_msg += f"\n[ATTACK LOG] Server error response: {e.response.text}"
                                except Exception:
                                    pass
                            logger.error(error_msg)
                            results.append(error_msg)
                        # --- END DETAILED ATTACK LOGGING ---
                    elif function_name == "fortify":
                        result = function_map[function_name](**arguments)
                        results.append(f"Fortified by moving {arguments.get('num_armies')} armies from {arguments.get('from_territory')} to {arguments.get('to_territory')}")
                        # Get fresh game state after fortify
                        fresh_state = self.risk_client.get_game_state()
                        logger.info(f"[DEBUG] Fresh game state after fortify: current player = {fresh_state.current_player}, phase = {fresh_state.phase}")
                    elif function_name == "move_armies":
                        result = function_map[function_name](**arguments)
                        results.append(f"Moved {arguments.get('num_armies')} armies from {arguments.get('from_territory')} to {arguments.get('to_territory')}")
                        # Get fresh game state after move_armies
                        fresh_state = self.risk_client.get_game_state()
                        logger.info(f"[DEBUG] Fresh game state after move_armies: current player = {fresh_state.current_player}, phase = {fresh_state.phase}")
                    else:
                        result = function_map[function_name](**arguments)
                        results.append(f"{function_name} executed successfully")
                        # Get fresh game state after any other function
                        fresh_state = self.risk_client.get_game_state()
                        logger.info(f"[DEBUG] Fresh game state after {function_name}: current player = {fresh_state.current_player}, phase = {fresh_state.phase}")
                except Exception as e:
                    error_msg = f"Error executing {function_name}: {str(e)}"
                    logger.error(error_msg)
                    results.append(error_msg)
            else:
                results.append(f"Unknown function: {function_name}")
        
        return "\n".join(results) 