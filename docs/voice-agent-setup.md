# Voice Agent Setup Guide

## Overview

The Voice Agent enables voice-driven customer support workflows using Twilio and LiveKit. When a user requests voice support, the system can initiate an outbound call to assist them with their needs.

## Implementation Summary

### Files Created/Modified

**Created:**
1. `goals/voice_agent.py` - Voice agent goal definition
2. `tools/initiate_voice_call.py` - Tool implementation for initiating voice calls

**Modified:**
1. `tools/tool_registry.py` - Added `initiate_voice_call_tool` definition
2. `tools/__init__.py` - Registered `initiate_voice_call` handler
3. `goals/__init__.py` - Added `voice_goals` to goal list

## Environment Variables

The voice agent requires the following environment variables. Add them to your `.env` file:

```bash
# Twilio Configuration (Required for production)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number  # E.164 format, e.g., +14155551234

# LiveKit Configuration (Required for production)
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-livekit-server.com

# Voice Agent Webhook Configuration
VOICE_WEBHOOK_BASE_URL=https://your-server.com/voice/twiml
VOICE_STATUS_CALLBACK_URL=https://your-server.com/voice/status
```

### Development Mode

If environment variables are not set, the tool will run in **mock mode**:
- No actual calls are made
- Returns a mock Call SID for testing
- Useful for development and testing workflows

## How It Works

### 1. Goal Definition

The `goal_voice_support` goal is triggered when a user requests voice-based support:

```python
goal_voice_support = AgentGoal(
    id="goal_voice_support",
    category_tag="voice",
    agent_name="Voice Support Agent",
    agent_friendly_description="Initiate a voice call to provide personalized customer support.",
    tools=[initiate_voice_call_tool],
    ...
)
```

### 2. Tool Execution

The `InitiateVoiceCall` tool requires:
- **phone_number**: Phone number in E.164 format (e.g., +14155551234)
- **goal**: Description of what the call should accomplish
- **context**: Additional information about the user's issue
- **userConfirmation**: User confirmation to initiate the call

### 3. Call Flow

1. User provides phone number and describes their issue
2. Agent gathers goal and context information
3. User confirms they want to receive a call
4. Tool initiates Twilio call with metadata
5. Twilio calls the webhook URL with goal/context parameters
6. Your TwiML endpoint uses this metadata to configure the LiveKit AI agent
7. LiveKit AI conducts the voice conversation to resolve the user's issue

## Example Conversation

```
user: I need help with my account
agent: I'd be happy to help you with your account! To provide the best support, 
       I can call you directly. May I have your phone number?
user: +14155551234
agent: Great! And can you briefly describe what you need help with regarding your account?
user: I can't log in and need to reset my password
agent: I understand - you're having trouble logging in and need a password reset. 
       Let me initiate a voice call to walk you through the process. 
       Please confirm if you'd like me to call you now.
user: yes
[User confirms tool execution]
agent: Perfect! I've initiated a call to +14155551234. You should receive a call 
       shortly where our voice assistant will help you reset your password.
```

## Integration with Twilio & LiveKit

### Twilio Setup

1. Create a Twilio account and purchase a phone number
2. Set up a webhook endpoint that returns TwiML
3. Configure environment variables with your credentials

### TwiML Webhook Endpoint

Your webhook endpoint should:
1. Receive `goal` and `context` as query parameters
2. Return TwiML that connects to your LiveKit room
3. Example TwiML response:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://your-livekit-server.com/stream">
            <Parameter name="goal" value="password_reset"/>
            <Parameter name="context" value="User cannot log in"/>
        </Stream>
    </Connect>
</Response>
```

### LiveKit AI Agent

Your LiveKit AI agent should:
1. Receive the goal and context from the stream parameters
2. Conduct a natural voice conversation
3. Use the context to provide personalized assistance
4. Execute backend actions (password reset, account updates, etc.)

## Testing

### Mock Mode Testing

Without credentials, the tool runs in mock mode:

```python
# Returns:
{
    "status": "success",
    "call_sid": "CAabcd1234...",
    "message": "[MOCK MODE] Voice call would be initiated to +14155551234...",
    "mode": "mock"
}
```

### Integration Testing

With credentials configured:
1. Set all required environment variables
2. Deploy a webhook endpoint that returns valid TwiML
3. Test with a real phone number
4. Verify the call is initiated and connected to LiveKit

## Dependencies

For production use, install the Twilio SDK:

```bash
uv pip install twilio
```

Or add to `pyproject.toml`:

```toml
[project.dependencies]
twilio = ">=8.0.0"
```

## Error Handling

The tool provides detailed error responses:

```python
# Missing credentials
{
    "status": "error",
    "error": "Phone number is required",
    "message": "Failed to initiate call: missing phone number"
}

# API errors
{
    "status": "error",
    "error": "Authentication failed",
    "message": "Failed to initiate voice call: Authentication failed"
}
```

## Next Steps

After completing this step, you'll need to:

1. **Step 2**: Create a new API endpoint that accepts phone number, goal, and context
2. **Step 3**: Set up the TwiML webhook endpoint
3. **Step 4**: Configure LiveKit AI agent
4. **Step 5**: Integrate everything and test end-to-end

## Enabling the Voice Goal

To enable the voice agent in your agent selection:

```bash
# In .env, add 'voice' to GOAL_CATEGORIES
GOAL_CATEGORIES=hr,travel-flights,travel-trains,fin,ecommerce,mcp-integrations,food,voice
```

Or set it as the default goal:

```bash
AGENT_GOAL=goal_voice_support
```

## Architecture Notes

- **Tool Type**: Native tool (not MCP)
- **Activity Pattern**: Uses dynamic tool execution via `dynamic_tool_activity`
- **Durability**: Leverages Temporal's reliability for call tracking
- **State Management**: Call SID returned for status tracking
- **Approval Required**: Uses `userConfirmation` parameter for user consent

## Support

For issues or questions about the voice agent implementation:
1. Check the error messages in the tool response
2. Verify all environment variables are set correctly
3. Review Twilio and LiveKit logs for call details
4. Ensure webhook endpoints are publicly accessible
