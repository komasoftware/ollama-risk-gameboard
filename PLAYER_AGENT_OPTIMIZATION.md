# Player Agent Optimization Feature Implementation

Optimize the Risk player agent to support dynamic persona descriptions, single turn execution, and better input/output structure for agent communication.

## ✅ Feature Status: COMPLETED

The parameter passing implementation is working perfectly! The agent successfully:
- Extracts `player_id` and `persona` from A2A DataPart
- Converts string `player_id` to integer properly
- Plays turns for different players with custom personas
- Provides detailed responses with strategy explanations
- Has a comprehensive Agent Card interface specification
- Supports A2A streaming protocol with proper connection management

**✅ Solution Implemented**: Created Python client with CLI interface that properly handles streaming responses

## Completed Tasks

- [x] Initial analysis of current agent implementation
- [x] Revised approach - simple parameter-based personas
- [x] Design simple parameter-based persona system
- [x] Modify agent to accept persona description as parameter
- [x] Implement single turn execution (agent stops after one turn)
- [x] Add basic persona support in prompts
- [x] Fix parameter passing - implement correct A2A DataPart approach
- [x] Remove hardcoded player_id fallback and implement proper type conversion
- [x] Add comprehensive Agent Card interface specification with parameter documentation
- [x] Enable streaming support in Agent Card capabilities
- [x] Clean up verbose logging and simplify parameter extraction logic
- [x] Test parameter extraction with different player IDs and personas
- [x] Create Python client with CLI interface for proper A2A streaming interaction
- [x] Implement 5 predefined personas for easy testing
- [x] Add proper connection management and response parsing

## In Progress Tasks

- [ ] Monitor and optimize agent performance and response times

## Future Tasks

- [ ] Experiment with improved prompts and structured parameters
- [ ] Improve agent response structure (include strategy used)
- [ ] Clean up debugging code and improve logging
- [ ] Create simple test cases with different persona descriptions
- [ ] Experiment with different persona descriptions
- [ ] Document new parameter structure and usage

## Current Issues to Address

### 1. Streaming/Timeout Problem 🔄 IN PROGRESS
**Issue**: HTTP connections hang, never receive `TaskState.completed`
**Impact**: Client requests timeout, poor user experience
**Solution Needed**: Investigate A2A streaming behavior and fix connection closure

### 2. Parameter Passing Problem ✅ RESOLVED
**Issue**: Using non-existent `context.context` field for structured parameters
**Impact**: Agent couldn't extract parameters properly
**Solution**: Implemented correct A2A DataPart approach for structured data

### 3. Hardcoded Player ID ✅ RESOLVED
**Issue**: Agent had hardcoded `player_id = 1` fallback
**Impact**: Agent always played as Player 1 regardless of input
**Solution**: Removed hardcoded fallback and implemented proper type conversion

### 4. Agent Card Interface ✅ RESOLVED
**Issue**: Missing detailed interface specification for calling systems
**Impact**: Calling systems couldn't understand expected parameters
**Solution**: Added comprehensive parameter documentation and streaming support

## Implementation Plan

### Core Design Decisions

1. **Simple Parameter-Based Personas**: Pass persona descriptions as parameters to agent calls
2. **Creative LLM Descriptions**: Allow natural language descriptions like "Bob is outspoken but timid"
3. **Single Turn Enforcement**: Implement strict turn boundaries and validation
4. **Better Response Structure**: Include strategy used and reasoning in agent responses
5. **Experiment-First Approach**: Start simple and iterate based on results
6. **No Complex Systems**: Avoid over-engineering with discrete properties or complex structures

### Architecture Components

- **Parameter Handler**: Accept persona descriptions as simple string parameters
- **Prompt Builder**: Create prompts using persona description and game context
- **Turn Validator**: Ensure single turn execution and validate actions
- **Response Formatter**: Include strategy used and reasoning in responses
- **Simple Testing**: Basic test cases with different persona descriptions

### Relevant Files

- `risk/agents/player_agent/agent_player.py` - Main agent implementation ✅ (Parameter passing working, Agent Card enhanced)
- `risk/agents/player_agent/risk_client.py` - Python CLI client ✅ (Proper A2A streaming interaction)
- `risk/agents/player_agent/tests/` - Test data and test cases (to be created)
- `risk/agents/player_agent/config.py` - Configuration and parameter handling (to be created)

### Technical Requirements

- Accept persona descriptions as simple string parameters
- Require player_id parameter for all game actions (reinforce, attack, fortify, etc.)
- Dynamic prompt generation based on game state and persona description
- Strict turn execution boundaries
- Include strategy used and reasoning in agent responses
- Comprehensive logging for debugging
- Simple test cases with different persona descriptions
- Backward compatibility with existing agent interface

### Example Usage

```bash
# Clean working example - A2A protocol with structured parameters
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "id": "test-2", 
    "method": "message/send", 
    "params": {
      "message": {
        "role": "user", 
        "messageId": "msg-2", 
        "parts": [
          {
            "type": "text", 
            "text": "Play your turn"
          }, 
          {
            "type": "data", 
            "data": {
              "player_id": "3", 
              "persona": "You are a defensive player who focuses on fortifying territories"
            }
          }
        ]
      }
    }
  }'
```

```python
# Python CLI client example - RECOMMENDED APPROACH
from risk_client import RiskAgentClient

# Initialize client
client = RiskAgentClient("http://localhost:8080")

# Send turn request with persona
response = client.send_turn_request(
    player_id=5,
    persona="You are a risk-taker who makes bold moves and takes chances"
)

# Response includes strategy used and reasoning
if response:
    print(response['parts'][0]['text'])  # Agent response

# Or use the interactive CLI
# python risk_client.py
```

### Parameter Passing Methods (A2A Protocol Compliant)

1. **A2A DataPart (Recommended)**: Pass parameters using `DataPart` with structured data
   ```json
   {
     "type": "data",
     "data": {
       "player_id": 1,
       "persona": "Bob is aggressive and always attacks"
     }
   }
   ```

2. **Text Only (Fallback)**: Pass parameters in the message text
   ```json
   {
     "type": "text", 
     "text": "Play turn for player 1 with persona: Bob is aggressive"
   }
   ```

3. **Game State Fallback**: Agent automatically determines current player from game state
   - Most reliable method
   - Used when no explicit player_id is provided
   - Ensures agent plays for the correct player
