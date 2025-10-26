# LiveKit Voice Agent

Production-ready AI voice agent for conducting phone conversations on behalf of users.

## Features

- 🎯 **Goal-Oriented Conversations** - Completes specific tasks through natural dialogue
- 🧠 **Intelligent Response Generation** - Uses Claude/GPT-4 for context-aware responses
- 📞 **Professional Phone Etiquette** - Introduces itself, states purpose, confirms details
- 🔄 **Real-Time Integration** - Syncs with Temporal workflows via webhooks
- 💬 **Hybrid Communication** - Accepts both voice and text input from web UI
- 📊 **Conversation Tracking** - Maintains state and generates summaries
- 🛡️ **Error Handling** - Graceful fallbacks for API failures
- 🎙️ **High-Quality Audio** - Uses Deepgram STT and ElevenLabs TTS

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Twilio    │────────▶│   LiveKit    │────────▶│  Temporal    │
│   (Calls)   │         │   (Agent)    │         │  (Workflow)  │
│             │◀────────│              │◀────────│              │
└─────────────┘         └──────────────┘         └──────────────┘
                              │  ▲
                              │  │
                              ▼  │
                        ┌──────────────┐
                        │   Web UI     │
                        │  (User Info) │
                        └──────────────┘
```

## Installation

```bash
cd livekit_agent

# Install dependencies
pip install -r requirements.txt

# Or with uv
uv pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Configure your API keys:
```bash
# Required: LLM Provider
ANTHROPIC_API_KEY=sk-ant-xxxxx
# or
OPENAI_API_KEY=sk-xxxxx

# Required: Speech Services
DEEPGRAM_API_KEY=xxxxx
ELEVENLABS_API_KEY=xxxxx

# Required: LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxx
LIVEKIT_API_SECRET=xxxxx

# Required: Webhook
WEBHOOK_BASE_URL=https://your-api.com
```

## Usage

### Running the Agent

```bash
# Start the LiveKit agent worker
python agent.py

# Or with uv
uv run python agent.py
```

The agent will:
1. Connect to your LiveKit server
2. Wait for incoming calls
3. Conduct conversations based on room metadata
4. Send events back to your Temporal workflow

### Room Metadata Format

When creating a LiveKit room for a call, include this metadata:

```json
{
  "goal": "Schedule a meeting with the dentist",
  "context": "Need an appointment for next Tuesday afternoon",
  "user_name": "Griffin Galimi",
  "call_sid": "CA562ab2481710b6e2c5d394c13c5d63e2",
  "workflow_id": "voice-call-abc123"
}
```

## Agent Behavior

### Conversation Flow

1. **Introduction**: "Hello! This is an assistant calling on behalf of [User Name]."
2. **State Purpose**: Clearly explains the reason for the call
3. **Information Gathering**: Asks questions to complete the goal
4. **Confirmation**: Repeats back important details
5. **Closure**: Thanks the person and confirms next steps

### System Prompt

The agent follows a comprehensive system prompt that defines:
- Professional phone etiquette
- Goal-oriented behavior
- Information handling procedures
- Error recovery strategies

### Example Conversations

**Scheduling a Meeting:**
```
Agent: Hello! This is an assistant calling on behalf of Griffin Galimi. 
       I'm calling to schedule a meeting. Do you have a moment to help with this?

Person: Sure, what kind of meeting?

Agent: We'd like to schedule a dentist appointment for next Tuesday afternoon. 
       What times do you have available?

Person: I have 2 PM or 4 PM open.

Agent: The 2 PM slot would be perfect. Can I confirm that's Tuesday, 
       January 15th at 2 PM?

Person: Yes, that's correct.

Agent: Excellent! I've scheduled the appointment for Tuesday, January 15th 
       at 2 PM. Is there anything else you need from me?

Person: No, that's all.

Agent: Thank you so much for your help. Have a great day!
```

**Password Reset:**
```
Agent: Hello! This is an assistant calling on behalf of Griffin Galimi. 
       I'm calling to help with a password reset. User locked out of account. 
       Do you have a moment to help with this?

Person: Yes, I can help. What's the email address on the account?

Agent: Let me check on that information for you. One moment please.
       [Requests info from web UI]
       
Agent: The email address is griffin@example.com.

Person: Okay, I've sent a reset code to that email. The user will need to 
        enter that code on the reset page.

Agent: Perfect! So Griffin should check his email for the reset code and 
       use it on the password reset page. Is that correct?

Person: Yes, exactly.

Agent: Thank you so much for your help. That takes care of everything. 
       Have a great day!
```

## Web UI Integration

### Sending Information to the Agent

The web UI can send information to the agent during a call:

```javascript
// From the web UI
const response = await fetch('/api/v1/voice-provide-info', {
  method: 'POST',
  body: JSON.stringify({
    workflow_id: 'voice-call-abc123',
    answer: 'griffin@example.com'
  })
});
```

The agent receives this via LiveKit data channels and incorporates it into the conversation.

### Receiving Events from the Agent

The agent sends events back to the workflow:

- `call_started` - Call has begun
- `agent_needs_info` - Agent needs information from web UI
- `call_complete` - Goal accomplished
- `call_ended` - Call has ended

## Customization

### Changing the Voice

ElevenLabs voices:
- `Sarah` - Professional female (default)
- `Adam` - Professional male
- `Antoni` - Calm male
- `Bella` - Friendly female

```python
agent_tts = elevenlabs.TTS(
    voice="Adam",  # Change here
    model="eleven_turbo_v2",
)
```

### Adjusting LLM Temperature

```python
agent_llm = anthropic.LLM(
    model="claude-3-5-sonnet-20241022",
    temperature=0.5,  # 0.0 = deterministic, 1.0 = creative
)
```

### Customizing System Prompt

Edit the `_build_system_prompt()` method to change agent behavior:

```python
def _build_system_prompt(self) -> str:
    return f"""You are a highly professional assistant...
    
    YOUR SPECIAL INSTRUCTIONS:
    - Always speak in a calm, reassuring tone
    - Never interrupt the person
    - Take notes on important details
    ...
    """
```

## Monitoring

The agent logs all important events:

```
2025-01-15 14:30:00 [INFO] voice-agent: Agent initialized for goal: Schedule meeting
2025-01-15 14:30:05 [INFO] voice-agent: Call started - Goal: Schedule meeting
2025-01-15 14:30:10 [INFO] voice-agent: Received speech: Sure, what kind of meeting?
2025-01-15 14:30:15 [INFO] voice-agent: Webhook sent: call_started
2025-01-15 14:32:30 [INFO] voice-agent: Call ended
```

## Testing

### Local Testing

```bash
# Start the agent
python agent.py

# In another terminal, use LiveKit CLI to test
lk room create test-room
lk room join test-room --publish-microphone
```

### Production Testing

1. Start ngrok: `ngrok http 8000`
2. Update webhook URL in `.env`
3. Start agent: `python agent.py`
4. Initiate call from web UI
5. Monitor logs and Temporal workflow

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "agent.py"]
```

### Environment Variables in Production

```bash
# Set in your deployment platform
ANTHROPIC_API_KEY=sk-ant-xxxxx
DEEPGRAM_API_KEY=xxxxx
ELEVENLABS_API_KEY=xxxxx
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxx
LIVEKIT_API_SECRET=xxxxx
WEBHOOK_BASE_URL=https://your-api.com
```

### Scaling

The agent worker can be scaled horizontally:

```bash
# Run multiple instances
python agent.py --worker-id worker-1 &
python agent.py --worker-id worker-2 &
python agent.py --worker-id worker-3 &
```

LiveKit will distribute calls across available workers.

## Troubleshooting

### Agent Not Connecting

```bash
# Check LiveKit credentials
echo $LIVEKIT_URL
echo $LIVEKIT_API_KEY

# Test connection
lk-cli --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY test connection
```

### Speech Not Recognized

```bash
# Check Deepgram API key
curl -H "Authorization: Token $DEEPGRAM_API_KEY" \
     https://api.deepgram.com/v1/projects
```

### Voice Not Playing

```bash
# Check ElevenLabs API key
curl -H "xi-api-key: $ELEVENLABS_API_KEY" \
     https://api.elevenlabs.io/v1/voices
```

### Webhooks Not Received

- Verify `WEBHOOK_BASE_URL` is accessible
- Check ngrok is running for local development
- Review API logs for webhook errors

## Performance Optimization

### Latency Reduction

1. **Use Turbo Models**:
   - ElevenLabs: `eleven_turbo_v2`
   - OpenAI: `gpt-4o-mini`

2. **Regional Deployment**:
   - Deploy agent workers near LiveKit servers
   - Use regional Deepgram endpoints

3. **Connection Pooling**:
   - Reuse HTTP connections for webhooks
   - Maintain persistent LLM connections

## Cost Optimization

### Typical Call Costs

- **LLM (Claude)**: ~$0.015 per minute
- **STT (Deepgram)**: ~$0.012 per minute  
- **TTS (ElevenLabs)**: ~$0.30 per 1000 characters
- **LiveKit**: Variable based on usage

**Estimated cost per 5-minute call**: $0.25 - $0.50

### Cost Reduction Tips

1. Use GPT-4o-mini instead of Claude for simple calls
2. Use OpenAI TTS instead of ElevenLabs ($0.015/1000 chars)
3. Implement conversation caching
4. Set max call duration limits

## Security

### API Key Management

- Never commit API keys to git
- Use environment variables or secrets manager
- Rotate keys regularly
- Use different keys for dev/staging/prod

### Webhook Security

```python
# Add webhook signature verification
import hmac

def verify_webhook(payload: bytes, signature: str) -> bool:
    secret = os.getenv("WEBHOOK_SECRET")
    expected = hmac.new(secret.encode(), payload, "sha256").hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Support

- **LiveKit Docs**: https://docs.livekit.io/agents/
- **Issues**: Open an issue in the repository
- **Logs**: Check agent logs for detailed error messages

## License

MIT License - See main repository LICENSE file
