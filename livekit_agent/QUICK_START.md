# LiveKit Voice Agent - Quick Start Guide

## Installation Complete! ✅

The LiveKit voice agent dependencies have been successfully installed via `uv sync`.

### Installed Packages
- `livekit` - Core LiveKit SDK
- `livekit-agents` - Agent framework
- `livekit-plugins-openai` - OpenAI integration (STT, TTS, LLM)

## Configuration

### 1. Set up environment variables in `.env`:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxx

# OpenAI (for voice models)
OPENAI_API_KEY=sk-proj-xxxxxxxxxx

# Webhook URL (where agent sends events)
WEBHOOK_BASE_URL=https://your-api.example.com

# User name (who the agent represents)
USER_NAME="Griffin Galimi"
```

### 2. Copy the example file (optional):
```bash
cd livekit_agent
cp .env.example .env
# Then edit .env with your credentials
```

## Running the Agent

### Development Mode
```bash
# From project root
cd livekit_agent
uv run python agent.py dev
```

### Production Mode  
```bash
# From project root  
cd livekit_agent
uv run python agent.py start
```

## How It Works

### Agent Flow
```
1. Twilio initiates call → TwiML connects to LiveKit room
2. LiveKit agent joins the room
3. Agent extracts goal/context from room metadata
4. Agent introduces itself and starts conversation
5. Agent collects information toward the goal
6. If needs user input → sends webhook to Temporal
7. User provides info via web UI → forwarded to agent
8. Agent completes goal → sends completion webhook
```

### Integration Points

#### 1. Room Metadata (from Twilio TwiML)
```json
{
  "call_sid": "CAxxxxx",
  "goal": "Schedule appointment",
  "context": "Customer wants to book a consultation",
  "user_name": "Griffin Galimi"
}
```

#### 2. Webhook Events (to Temporal)
```json
// Agent needs info
{
  "call_sid": "CAxxxxx",
  "event_type": "agent_needs_info",
  "question": "What's the confirmation code?",
  "timestamp": "2025-10-26T12:00:00Z"
}

// Call complete
{
  "call_sid": "CAxxxxx",
  "event_type": "call_complete",
  "success": true,
  "summary": "Appointment scheduled for Oct 30 at 2pm",
  "information_collected": {...},
  "timestamp": "2025-10-26T12:05:00Z"
}

// Call error
{
  "call_sid": "CAxxxxx",
  "event_type": "call_error",
  "error": "Customer hung up",
  "timestamp": "2025-10-26T12:02:00Z"
}
```

#### 3. Data Messages (from Web UI via send_info_to_livekit)
The agent listens for data packets sent through LiveKit's data channel:
```python
# User provides info via web UI
# API calls send_info_to_livekit(call_sid, "Confirmation code: 123456")
# Agent receives it and continues conversation
```

## Testing

### Test the agent locally:
```bash
cd livekit_agent
uv run python test_agent.py
```

### Test with mock room:
```bash
# Requires LiveKit credentials
uv run python -c "
from livekit_agent.agent import TemporalVoiceAgent

agent = TemporalVoiceAgent(
    call_sid='CA123test',
    goal='Test conversation',
    context='This is a test',
    user_name='Test User'
)

print('Agent initialized successfully!')
print(f'Instructions preview: {agent.instructions[:200]}...')
"
```

## Troubleshooting

### Import Errors
If you see `ImportError: cannot import name 'openai'`:
```bash
# Re-sync dependencies
cd /path/to/project/root
uv sync
```

### Missing Credentials
The agent will log warnings if credentials are missing:
- Check `.env` file exists
- Verify all required variables are set
- Restart the agent after updating `.env`

### Agent Not Joining Room
1. Check LiveKit URL is correct (wss://...)
2. Verify API key/secret are valid
3. Check room name matches Call SID format: `call-{call_sid}`
4. Review LiveKit dashboard for connection errors

### Webhooks Not Received
1. Verify WEBHOOK_BASE_URL is accessible from LiveKit
2. Check API endpoint `/webhooks/livekit/events` exists
3. Review API logs for webhook requests
4. Test webhook manually:
   ```bash
   curl -X POST http://localhost:8000/webhooks/livekit/events \
     -H "Content-Type: application/json" \
     -d '{"call_sid": "test", "event_type": "test"}'
   ```

## Next Steps

1. **Configure LiveKit Cloud**
   - Create project at https://livekit.io/cloud
   - Get API credentials
   - Add to `.env`

2. **Set up Twilio TwiML**
   - Configure webhook to connect calls to LiveKit
   - Pass metadata with goal/context
   - See `TODO.md` Phase 2.4

3. **Test End-to-End**
   - Start Temporal worker
   - Start API server
   - Start LiveKit agent
   - Initiate test call from frontend
   - Verify conversation works

4. **Deploy to Production**
   - Deploy agent to cloud (AWS, GCP, etc.)
   - Use production LiveKit credentials
   - Configure proper webhook URLs
   - Monitor logs and metrics

## Architecture

```
┌─────────────┐
│   Twilio    │ Initiates call
│   Call      │ 
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   TwiML     │ Connects to LiveKit
│   Webhook   │ with metadata
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         LiveKit Room                │
│  ┌───────────────────────────────┐  │
│  │   Voice Agent                 │  │
│  │   - STT (Whisper)             │  │
│  │   - LLM (GPT-4)               │  │
│  │   - TTS (OpenAI)              │  │
│  │   - Goal-oriented logic       │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
       │                    ▲
       │ Webhooks           │ Data messages
       ▼                    │
┌─────────────┐      ┌─────────────┐
│  Temporal   │◀────▶│   Web UI    │
│  Workflow   │      │   (React)   │
└─────────────┘      └─────────────┘
```

## Resources

- **LiveKit Docs**: https://docs.livekit.io/agents/
- **Voice Assistant Guide**: https://docs.livekit.io/agents/voice-assistant/
- **Project README**: `livekit_agent/README.md`
- **Integration TODO**: `TODO.md`
- **API Documentation**: `docs/livekit-integration.md`

## Support

For issues:
1. Check agent logs for errors
2. Review LiveKit dashboard
3. Verify all credentials in `.env`
4. Test components individually (STT, TTS, LLM)
5. Check network connectivity to LiveKit

Happy calling! 🎉📞
