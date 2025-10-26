# LiveKit Integration Guide

## Overview

The `send_info_to_livekit` function enables sending user-provided information from the web UI to an active LiveKit AI agent during a voice call. This allows for a hybrid interaction model where sensitive information (like confirmation codes, account numbers, etc.) can be provided via text instead of spoken over the phone.

## Installation

### Production Mode (with LiveKit)

Install the optional voice dependencies:

```bash
uv sync --extra voice
# or
uv pip install twilio livekit-api
```

### Development/Stub Mode

No additional dependencies needed - the function will run in stub mode and log what would be sent.

## Configuration

Add LiveKit credentials to your `.env` file:

```bash
# LiveKit Configuration (for production)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=your_secret_here
```

## How It Works

### Flow Diagram

```
User fills web form → /api/v1/voice-provide-info endpoint
                              ↓
                    send_info_to_livekit()
                              ↓
              [Has LiveKit credentials?]
                   ↙              ↘
            YES (Production)    NO (Stub)
                   ↓              ↓
        Use LiveKit API    Log to console
        to send data to         ↓
        active call room    Return success
                   ↓
        AI agent receives
        the information
                   ↓
        Agent continues
        conversation with
        this new context
```

### Implementation Modes

#### Stub Mode (Default)
When LiveKit credentials are not configured, the function logs what would be sent:

```
[STUB] Would send to LiveKit (Call SID: CAxxxx): User provided confirmation code: 123456
```

#### Production Mode
When credentials are configured, the function:
1. Initializes LiveKit API client
2. Finds the room associated with the Call SID
3. Sends a data packet to the room
4. AI agent receives and processes the information

## Usage

### From the Frontend

The frontend already has a form to provide information when the AI agent requests it. The form submits to `/api/v1/voice-provide-info`:

```javascript
// Frontend sends user's answer
const response = await fetch('/api/v1/voice-provide-info', {
  method: 'POST',
  body: JSON.stringify({
    workflow_id: currentWorkflowId,
    answer: userAnswer
  })
});
```

### From the API Endpoint

The endpoint calls `send_info_to_livekit` internally:

```python
@app.post("/api/v1/voice-provide-info")
async def voice_provide_info(workflow_id: str, answer: str):
    # Get Call SID for this workflow
    call_sid = find_call_sid_by_workflow(workflow_id)
    
    # Send to LiveKit
    success = await send_info_to_livekit(call_sid, answer)
    
    return {"status": "ok" if success else "error"}
```

### Direct Function Call

You can also call the function directly:

```python
from api.main import send_info_to_livekit

# Send information to an active call
success = await send_info_to_livekit(
    call_sid="CA562ab2481710b6e2c5d394c13c5d63e2",
    answer="Confirmation code: 123456"
)
```

## LiveKit Agent Setup

For this to work in production, your LiveKit AI agent needs to:

1. **Listen for data messages** in the room
2. **Process the received information** 
3. **Continue the conversation** with this new context

Example LiveKit agent code:

```python
from livekit import rtc, agents

class VoiceAgent(agents.VoiceAgent):
    async def on_data_received(self, data: rtc.DataPacket):
        """Handle information from the web UI."""
        message = data.data.decode('utf-8')
        
        # Process the information
        print(f"Received from web UI: {message}")
        
        # Update conversation context
        self.context["user_provided_info"] = message
        
        # Acknowledge to the user
        await self.say(f"Thank you, I've received your {message}")
        
        # Continue with the goal
        await self.continue_conversation()
```

## Room Naming Convention

By default, the function uses this convention:
- Room name: `call-{call_sid}`
- Example: `call-CA562ab2481710b6e2c5d394c13c5d63e2`

Make sure your LiveKit agent creates/joins rooms with the same naming pattern.

## Error Handling

The function handles errors gracefully:

```python
# Returns True on success, False on failure
success = await send_info_to_livekit(call_sid, answer)

if not success:
    # Information wasn't sent, but we don't fail the request
    # The function logs the error and falls back to logging
    print("Failed to send to LiveKit, but workflow continues")
```

## Testing

### Test in Stub Mode

```bash
# Start API without LiveKit credentials
uv run uvicorn api.main:app --reload

# In another terminal, send test request
curl -X POST http://localhost:8000/api/v1/voice-provide-info \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "voice-call-123", "answer": "Test answer"}'

# Check logs for:
# [STUB] Would send to LiveKit (Call SID: CAxxxx): Test answer
```

### Test in Production Mode

1. Set up LiveKit credentials in `.env`
2. Install voice dependencies: `uv sync --extra voice`
3. Start a real voice call workflow
4. Send information via the endpoint
5. Verify the LiveKit agent receives the data

## Troubleshooting

### Import Error: "livekit could not be resolved"

This is expected when running in stub mode. The import is inside a try/except block and only executes when credentials are configured.

To fix for production:
```bash
uv sync --extra voice
```

### "Room not found" Error

Make sure:
1. The Call SID → Room Name mapping is correct
2. The LiveKit agent created/joined the room
3. The room hasn't already ended

### Data Not Received by Agent

Verify:
1. LiveKit agent is listening for data packets (`on_data_received`)
2. Agent is in the correct room
3. Network connectivity between API and LiveKit server

## Advanced: Alternative Implementations

The function currently uses LiveKit's data channel API. Alternative approaches:

### Option 1: Webhook-based (simpler)
```python
# Agent exposes webhook endpoint
async def send_info_to_livekit(call_sid: str, answer: str):
    webhook_url = f"{LIVEKIT_AGENT_URL}/receive-info"
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "call_sid": call_sid,
            "message": answer
        })
```

### Option 2: Redis/Queue-based (more scalable)
```python
# Use Redis pub/sub for agent communication
async def send_info_to_livekit(call_sid: str, answer: str):
    await redis.publish(f"call:{call_sid}:info", answer)
    # Agent subscribes to this channel
```

## Related Documentation

- [TODO.md](../TODO.md) - Full voice agent integration checklist
- [Voice Agent Setup](voice-agent-setup.md) - Complete setup guide
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [LiveKit Python SDK](https://github.com/livekit/python-sdks)

## Support

For issues with LiveKit integration:
1. Check LiveKit dashboard for room/participant logs
2. Verify API credentials are correct
3. Review LiveKit agent logs
4. Test with LiveKit's example agents first
