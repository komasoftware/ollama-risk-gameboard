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
                        "card_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of card indices (0-based) to trade"
                        }
                    },
                    "required": ["player_id", "card_indices"]
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

You interact with the game by calling functions using the function calling mechanism.

**CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings.**

**CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings.**

**CRITICAL: You MUST use the function calling mechanism. DO NOT write function calls as text strings.**

Available functions:
- reinforce: Place armies on your territories
- attack: Attack enemy territories  
- fortify: Move armies between your territories
- move_armies: Move armies after conquering a territory
- trade_cards: Trade cards for bonus armies (only during reinforce phase)

Always use the function calling mechanism. Never write function calls as text.
"""

        # Check if player has enough cards for trading
        can_trade_cards = False
        if player_id is not None:
            try:
                game_state = self.risk_client.get_game_state()
                current_player = game_state.players.get(player_name)
                if current_player and len(current_player.cards) >= 3:
                    can_trade_cards = True
                    logger.info(f"[DEBUG] {player_name} has {len(current_player.cards)} cards - card trading enabled")
                else:
                    logger.info(f"[DEBUG] {player_name} has {len(current_player.cards) if current_player else 0} cards - card trading disabled")
            except Exception as e:
                logger.warning(f"[DEBUG] Could not check card count for {player_name}: {e}")

        # Try different prompt strategies if function calling fails
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Modify prompt based on attempt number
                if attempt == 0:
                    # First attempt: Full context
                    current_prompt = prompt
                elif attempt == 1:
                    # Second attempt: Simplified prompt
                    current_prompt = f"""You are {player_name} playing Risk. 

CURRENT PHASE: {prompt.split('CURRENT PHASE:')[1].split('\n')[0] if 'CURRENT PHASE:' in prompt else 'Unknown'}

{prompt.split('AVAILABLE ACTIONS:')[1] if 'AVAILABLE ACTIONS:' in prompt else 'No actions available'}

Use the function calling mechanism to make ONE action. Include ALL required parameters."""
                else:
                    # Third attempt: Direct instruction
                    current_prompt = f"""You are {player_name}. 

{prompt.split('AVAILABLE ACTIONS:')[1] if 'AVAILABLE ACTIONS:' in prompt else 'No actions available'}

Make ONE function call using the function calling mechanism. Include ALL required parameters."""

                # Conditionally enable tools
                if use_tools:
                    # Convert function definitions to Ollama format, excluding trade_cards if not available
                    tools = []
                    for func in self.functions:
                        # Skip trade_cards function if player doesn't have enough cards
                        if func.name == "trade_cards" and not can_trade_cards:
                            logger.info(f"[DEBUG] Excluding trade_cards function for {player_name} (insufficient cards)")
                            continue
                        
                        tools.append({
                            "type": "function",
                            "function": {
                                "name": func.name,
                                "description": func.description,
                                "parameters": func.parameters
                            }
                        })

                    logger.info(f"[DEBUG] Attempt {attempt + 1}: Calling Ollama with tools: {len(tools)} functions defined (trade_cards {'enabled' if can_trade_cards else 'disabled'})")

                    # Make the API call to Ollama with function calling
                    response = ollama.chat(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": current_prompt}
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
                            {"role": "user", "content": current_prompt}
                        ],
                        stream=False
                    )

                # Log the AI's thinking process
                ai_thinking = response.message.content
                if ai_thinking and ai_thinking.strip():
                    logger.info(f"\n🤔 {player_name} THINKING (Attempt {attempt + 1}):\n{ai_thinking}\n")
                
                # Debug: Check if tool_calls exist
                has_tool_calls = hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls
                logger.info(f"[DEBUG] Attempt {attempt + 1}: use_tools={use_tools}, has_tool_calls={has_tool_calls}")
                
                # Additional debugging for function calling issues
                if use_tools and not has_tool_calls:
                    logger.warning(f"[DEBUG] Function calling failed for {player_name} - no tool_calls generated")
                    logger.warning(f"[DEBUG] Model: {self.model}")
                    logger.warning(f"[DEBUG] Tools provided: {len(tools)}")
                    logger.warning(f"[DEBUG] Response type: {type(response)}")
                    logger.warning(f"[DEBUG] Response attributes: {dir(response)}")
                    if hasattr(response, 'message'):
                        logger.warning(f"[DEBUG] Message attributes: {dir(response.message)}")
                
                # Check if the response contains tool calls and tools were used
                if use_tools and has_tool_calls:
                    # Handle the function calls
                    tool_results = await self._handle_function_calls(response.message.tool_calls, player_id=player_id)
                    logger.info(f"\n🎯 {player_name} DECISION(S) (Attempt {attempt + 1}):\n{tool_results}\n")
                    # Filter out server response JSON from the results
                    filtered_results = self._filter_server_json(tool_results)
                    return f"Executed actions: {filtered_results}"
                else:
                    # Fallback: Try to parse function calls from text content
                    logger.info(f"[DEBUG] Attempt {attempt + 1}: No tool calls found, checking text content for function calls")
                    if 'attack' in ai_thinking.lower() or 'function' in ai_thinking.lower():
                        logger.info(f"[DEBUG] Attempt {attempt + 1}: Text contains potential function calls, but LLM didn't use tool_calls mechanism")
                        if attempt < max_retries - 1:
                            logger.info(f"[DEBUG] Attempt {attempt + 1} failed, retrying with different prompt...")
                            continue
                    return response.message.content
                
            except Exception as e:
                logger.error(f"[DEBUG] Attempt {attempt + 1} failed with error: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"[DEBUG] Attempt {attempt + 1} failed, retrying...")
                    continue
                else:
                    return f"Error communicating with Ollama after {max_retries} attempts: {str(e)}"
        
        return f"Failed to get valid response after {max_retries} attempts"
    
    def _filter_server_json(self, results: str) -> str:
        """Filter out server response JSON from the results string."""
        if not results:
            return results
        
        # Split by lines and filter out lines containing server response JSON
        lines = results.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that contain server response JSON patterns
            if '| Server response:' in line and ('{' in line or 'game_state' in line):
                # Extract just the action part before the server response
                if '| Server response:' in line:
                    action_part = line.split('| Server response:')[0].strip()
                    if action_part:
                        filtered_lines.append(action_part)
            else:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
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
            if function_name in ["reinforce", "attack", "fortify", "trade_cards", "move_armies"] and 'player_id' not in arguments and player_id is not None:
                arguments['player_id'] = player_id
                logger.info(f"[DEBUG] Injected missing player_id: {player_id} for {function_name}")

            # 2. Ensure 'player_id' is an integer
            if 'player_id' in arguments:
                try:
                    arguments['player_id'] = int(arguments['player_id'])
                except (ValueError, TypeError):
                    if player_id is not None:
                        arguments['player_id'] = player_id
                        logger.info(f"[DEBUG] Fixed invalid player_id, using provided: {player_id}")
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
                    logger.info(f"[DEBUG] Converted 'armies' to 'num_armies': {armies_value}")
                
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
                        logger.info(f"[DEBUG] Removed unexpected key '{key}' from {function_name} arguments")
            
            # Handle trade_cards function separately
            elif function_name == "trade_cards":
                # Validate required parameters for trade_cards
                required_keys = ['player_id', 'card_indices']
                if not all(key in arguments for key in required_keys):
                    missing = [key for key in required_keys if key not in arguments]
                    results.append(f"Missing required parameters for trade_cards: {missing}")
                    continue
                
                # Ensure card_indices is a list of integers
                if 'card_indices' in arguments:
                    try:
                        card_indices = arguments['card_indices']
                        
                        # Handle case where LLM passes string representation of list
                        if isinstance(card_indices, str):
                            # Try to parse string as JSON list
                            import json
                            try:
                                card_indices = json.loads(card_indices)
                                logger.info(f"[DEBUG] Parsed card_indices string to list: {card_indices}")
                            except json.JSONDecodeError:
                                # Try to parse as simple bracket notation
                                try:
                                    # Remove brackets and split by comma
                                    card_indices = card_indices.strip('[]').split(',')
                                    card_indices = [int(x.strip()) for x in card_indices if x.strip()]
                                    logger.info(f"[DEBUG] Parsed card_indices string manually: {card_indices}")
                                except (ValueError, AttributeError):
                                    results.append(f"Invalid card_indices format: {card_indices}. Must be a list of integers.")
                                    continue
                        
                        # Validate it's a list
                        if not isinstance(card_indices, list):
                            results.append(f"card_indices must be a list, got {type(card_indices)}")
                            continue
                        
                        # Validate all elements are integers
                        if not all(isinstance(x, int) for x in card_indices):
                            results.append(f"All card_indices must be integers, got: {card_indices}")
                            continue
                        
                        # Get the actual cards from the game state to validate indices
                        try:
                            game_state = self.risk_client.get_game_state()
                            current_player = game_state.players.get(player_name)
                            
                            if not current_player:
                                results.append(f"Could not find player {player_name} in game state")
                                continue
                            
                            num_cards = len(current_player.cards)
                            
                            # Validate card indices are within valid range
                            if not all(0 <= x < num_cards for x in card_indices):
                                results.append(f"card_indices must be between 0-{num_cards-1}, got: {card_indices}")
                            continue
                        
                        # Validate exactly 3 cards are selected
                        if len(card_indices) != 3:
                            results.append(f"Must trade exactly 3 cards, got {len(card_indices)}: {card_indices}")
                            continue
                        
                        # Validate no duplicate indices
                        if len(set(card_indices)) != 3:
                            results.append(f"Duplicate card indices not allowed: {card_indices}")
                            continue
                            
                            # Check if we're in the correct phase for card trading
                            if function_name == "trade_cards" and game_state.phase.value != "reinforce":
                                results.append(f"Card trading is only allowed during REINFORCE phase, current phase: {game_state.phase.value}")
                                continue
                            
                            # Validate the card combination is actually valid
                            if num_cards >= 3:
                                cards_to_trade = [current_player.cards[idx] for idx in card_indices]
                                # Extract just the kind field from each card object or dict
                                def get_kind(card):
                                    if hasattr(card, 'kind'):
                                        return card.kind
                                    elif isinstance(card, dict) and 'kind' in card:
                                        return card['kind']
                                    else:
                                        raise ValueError(f"Card has no kind: {card}")
                                card_kinds = [get_kind(card) for card in cards_to_trade]
                                from agents.risk_rules import _is_valid_card_combination
                                if not _is_valid_card_combination(card_kinds):
                                    results.append(f"Invalid card combination: {cards_to_trade}. Must be 3 of a kind or 1 of each type.")
                                    continue
                            else:
                                results.append(f"Not enough cards to trade. You have {num_cards} cards, need exactly 3.")
                                continue
                                
                        except Exception as e:
                            logger.warning(f"Could not validate card combination: {e}")
                            results.append(f"Error validating cards: {e}")
                            continue
                        
                        # Update the arguments with the validated list
                        arguments['card_indices'] = card_indices
                        logger.info(f"[DEBUG] Validated card_indices: {card_indices}")
                        
                    except Exception as e:
                        results.append(f"Error validating card_indices: {e}")
                        continue
                
                # Remove any unexpected keys
                expected_keys = ['player_id', 'card_indices']
                for key in list(arguments.keys()):
                    if key not in expected_keys:
                        del arguments[key]
                        logger.info(f"[DEBUG] Removed unexpected key '{key}' from trade_cards arguments")
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
                    elif function_name == "trade_cards":
                        result = function_map[function_name](**arguments)
                        card_indices = arguments.get('card_indices', [])
                        results.append(f"Traded cards with indices {card_indices} for bonus armies")
                        # Get fresh game state after trade_cards
                        fresh_state = self.risk_client.get_game_state()
                        logger.info(f"[DEBUG] Fresh game state after trade_cards: current player = {fresh_state.current_player}, phase = {fresh_state.phase}")
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