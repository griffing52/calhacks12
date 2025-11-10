# LiveKit Agent Dispatch Migration

## Overview

This project has been migrated from Twilio-initiated calls to **LiveKit Agent Dispatch** for outbound call initiation. This simplifies the architecture by using LiveKit's native SIP capabilities instead of requiring Twilio API calls.

## What Changed

### Before (Twilio-based)
1. Call `twilio.calls.create()` API
2. Twilio makes outbound call
3. Twilio webhook returns TwiML
4. TwiML forwards call to LiveKit SIP trunk
5. LiveKit agent handles conversation

### After (LiveKit Dispatch)
1. Call `livekit.agent_dispatch.create_dispatch()` API
2. LiveKit creates room and dispatches agent
3. Agent automatically initiates outbound call via SIP
4. Agent handles conversation

## Benefits

✅ **Simpler architecture** - One API call instead of multiple steps  
✅ **Fewer dependencies** - No Twilio SDK required for call initiation  
✅ **Direct integration** - LiveKit handles both SIP and agent management  
✅ **Better control** - Metadata passed directly to agent on dispatch  
✅ **Cleaner code** - Removed webhook complexity for call initiation

## Updated Files

### Core Implementation
- **`tools/initiate_voice_call.py`** - Updated to use LiveKit dispatch instead of Twilio
- **`activities/voice_activities.py`** - Updated activity to use LiveKit dispatch
- **`api/main.py`** - Updated `/api/v1/voice-initiate` endpoint to use LiveKit dispatch

### Utility Scripts
- **`api/make_sip_call.py`** - Enhanced with better documentation and error handling
- **`scripts/make_livekit_call.py`** - New standalone script for testing LiveKit dispatch

## Configuration

### Required Environment Variables

```bash
# LiveKit Configuration (Required)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Agent Configuration
LIVEKIT_AGENT_NAME=outbound-caller  # Name of your deployed agent

# Phone Numbers
TWILIO_PHONE_NUMBER=+1234567890  # Number to call FROM (shown to recipient)
```

### Optional Variables

```bash
# For backward compatibility with existing code
TWILIO_ACCOUNT_SID=...  # Only needed if running old Twilio code
TWILIO_AUTH_TOKEN=...   # Only needed if running old Twilio code
```

## Usage

### 1. Direct Script Execution

Test call initiation directly:

```bash
# Using the API script
python api/make_sip_call.py

# Using the standalone script with arguments
python scripts/make_livekit_call.py \
  --goal "password reset assistance" \
  --context "User locked out of account" \
  --phone "+15555551234"
```

### 2. Via API Endpoint

Make a POST request to initiate a call:

```bash
curl -X POST http://localhost:8000/api/v1/voice-initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+15555551234",
    "goal": "password reset assistance",
    "context": "User is locked out of their account"
  }'
```

Response:
```json
{
  "dispatch_id": "DA_abc123...",
  "room_name": "call-x7k9m2p1",
  "message": "Voice call initiated successfully to +15555551234",
  "phone_number": "+15555551234",
  "goal": "password reset assistance",
  "context": "User is locked out of their account",
  "agent_name": "outbound-caller"
}
```

### 3. From Frontend

The frontend can call the API endpoint:

```javascript
const response = await fetch('http://localhost:8000/api/v1/voice-initiate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    phone_number: '+15555551234',
    goal: 'password reset',
    context: 'User needs help accessing account'
  })
});

const result = await response.json();
console.log('Call initiated:', result.dispatch_id);
```

### 4. From Temporal Workflow

Use the updated tool/activity:

```python
# In a Temporal workflow
result = await workflow.execute_activity(
    initiate_voice_call_activity,
    {
        "phone_number": "+15555551234",
        "goal": "password reset assistance",
        "context": "User locked out"
    },
    start_to_close_timeout=timedelta(seconds=30)
)

dispatch_id = result["call_sid"]  # Actually dispatch_id now
```

## How It Works

### Dispatch Metadata

When creating a dispatch, we pass metadata that the agent receives:

```python
metadata = {
    "phone_number": "+1234567890",  # FROM number (shown to recipient)
    "transfer_to": "+15555551234",  # TO number (recipient)
    "goal": "password reset",
    "context": "User locked out"
}
```

The agent can access this metadata to:
- Make the outbound call to `transfer_to`
- Display `phone_number` as caller ID
- Understand the `goal` and `context` of the conversation

### Room and Agent Flow

```
1. create_dispatch() called
   ↓
2. LiveKit creates unique room (e.g., "call-x7k9m2p1")
   ↓
3. Agent dispatched to room with metadata
   ↓
4. Agent reads metadata and initiates SIP call
   ↓
5. Call connects to recipient
   ↓
6. Agent conducts conversation based on goal/context
```

## Testing

### Mock Mode

If LiveKit credentials are not configured, the system falls back to mock mode:

```python
# Returns a mock response without making actual API calls
{
    "status": "success",
    "call_sid": "DA_mock123...",
    "message": "[MOCK MODE] Voice call would be initiated...",
    "mode": "mock"
}
```

### Production Mode

With proper credentials, actual LiveKit API calls are made:

```python
{
    "status": "success",
    "call_sid": "DA_real_dispatch_id",
    "room_name": "call-x7k9m2p1",
    "dispatch_id": "DA_real_dispatch_id",
    "mode": "production"
}
```

## Troubleshooting

### Common Issues

**1. "Missing LiveKit credentials"**
- Ensure `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` are in `.env`
- Check that `.env` is in the correct location (project root)

**2. "LiveKit SDK not installed"**
```bash
pip install livekit
```

**3. "Agent not found"**
- Verify `LIVEKIT_AGENT_NAME` matches your deployed agent name
- Check agent is running and connected to LiveKit server

**4. Call not connecting**
- Verify SIP trunk is properly configured in LiveKit dashboard
- Check that `transfer_to` phone number is in E.164 format
- Ensure SIP trunk has outbound calling enabled

## Migration Checklist

If migrating existing code:

- [ ] Update environment variables (add `LIVEKIT_*` vars)
- [ ] Deploy LiveKit agent with proper SIP configuration
- [ ] Update any frontend code calling voice initiation endpoints
- [ ] Test with mock mode first
- [ ] Test with real phone numbers in production
- [ ] Remove unused Twilio call initiation code (if desired)
- [ ] Update documentation/runbooks

## Related Files

- Original implementation: `tools/initiate_voice_call.py`
- Activity wrapper: `activities/voice_activities.py`
- API endpoint: `api/main.py` → `/api/v1/voice-initiate`
- Test scripts: `api/make_sip_call.py`, `scripts/make_livekit_call.py`
- Agent configuration: `goals/voice_agent.py`

## Resources

- [LiveKit Agent Dispatch Documentation](https://docs.livekit.io/agents/dispatch/)
- [LiveKit SIP Integration](https://docs.livekit.io/sip/)
- [Agent Development Guide](docs/voice-agent-setup.md)

---

**Last Updated:** November 10, 2025
