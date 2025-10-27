# Voice Agent Clarification Feature

## Overview

The voice agent can now request clarification from the user interface when it doesn't know an answer during a phone call. This enables a seamless human-in-the-loop workflow where the AI agent can ask for help without interrupting the call.

## How It Works

### Workflow Flow

```
┌─────────────────┐
│  Voice Call     │
│  In Progress    │
└────────┬────────┘
         │
         │ Agent encounters question it can't answer
         ▼
┌─────────────────┐
│  Send Signal    │
│  "required_info │
│   _needed"      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  UI Shows       │
│  Question +     │
│  Input Field    │
└────────┬────────┘
         │
         │ User types answer
         ▼
┌─────────────────┐
│  Send Signal    │
│  "voice_info_   │
│   provided"     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent Relays   │
│  Info to Caller │
└─────────────────┘
```

## Backend Implementation

### Workflow Signals

**1. Agent Needs Information**
```python
@workflow.signal
async def required_info_needed(self, question: str) -> None:
    """Signal when LiveKit AI needs additional information."""
    self.voice_info_needed = True
    self.voice_pending_question = question
```

**2. User Provides Answer**
```python
@workflow.signal
async def voice_info_provided(self, answer: str) -> None:
    """Signal when user provides requested information."""
    # Send answer to LiveKit AI via webhook/API
    # Clear pending question
    self.voice_info_needed = False
    self.voice_pending_question = None
```

### Workflow Query

```python
@workflow.query
def get_voice_call_status(self) -> Dict[str, Any]:
    """Query current voice call status including pending questions."""
    return {
        "active": self.voice_call_active,
        "call_sid": self.voice_call_sid,
        "status": self.voice_call_status,
        "info_needed": self.voice_info_needed,
        "pending_question": self.voice_pending_question
    }
```

### API Endpoints

**GET `/voice-call-status/{workflow_id}`**
- Returns workflow status including pending questions
- Response includes `voice_status` object with:
  - `info_needed`: Boolean
  - `pending_question`: String or null

**POST `/voice-provide-answer/{workflow_id}`**
- Send user's answer to the workflow
- Form parameter: `answer` (string)

## Frontend Implementation

### VoiceCallStatus Component

**New State:**
```javascript
const [pendingQuestion, setPendingQuestion] = useState(null);
const [userAnswer, setUserAnswer] = useState('');
const [submittingAnswer, setSubmittingAnswer] = useState(false);
```

**Status Polling:**
```javascript
// Check for pending questions
if (result.voice_status?.info_needed && result.voice_status?.pending_question) {
    setPendingQuestion(result.voice_status.pending_question);
    setStatus({
        stage: 'needs_info',
        message: '❓ Agent needs clarification',
        details: result.voice_status.pending_question,
        timestamp: new Date()
    });
}
```

**Answer Submission:**
```javascript
const handleSubmitAnswer = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('answer', userAnswer.trim());
    
    await fetch(`/voice-provide-answer/${workflowId}`, {
        method: 'POST',
        body: formData
    });
    
    setUserAnswer('');
    setPendingQuestion(null);
};
```

## Usage Example

### Scenario: Account Verification

1. **User initiates voice call** requesting password reset
2. **Agent calls user** and starts conversation
3. **Agent asks** "What is your account number?"
4. **User doesn't know** their account number
5. **Agent signals workflow**:
   ```python
   await handle.signal(
       AgentGoalWorkflow.required_info_needed,
       "What is the user's account number?"
   )
   ```
6. **UI displays question** with input field
7. **Support staff types** "ACC-12345678"
8. **UI sends answer**:
   ```python
   await handle.signal(
       AgentGoalWorkflow.voice_info_provided,
       "ACC-12345678"
   )
   ```
9. **Agent tells caller** "Your account number is ACC-12345678"
10. **Call continues** normally

## Testing

### Manual Testing

1. Start a voice call workflow
2. Use test script to simulate clarification:
   ```bash
   uv run python scripts/test_voice_clarification.py <workflow_id>
   ```
3. Select option "1. Simulate agent needs clarification"
4. Enter a question (e.g., "What is the verification code?")
5. Check UI - question should appear
6. Type answer in UI input field
7. Click "Send"
8. Verify answer is sent to workflow

### Automated Testing

See `tests/test_voice_clarification.py` for test cases covering:
- Signal handling
- State transitions
- Query responses
- Error handling

## Integration with LiveKit

To relay answers from the UI to the LiveKit AI agent, implement one of these approaches:

### Option 1: Data Channel
```python
# In voice activity or webhook
from livekit import api

livekit_client = api.LiveKitAPI(...)
await livekit_client.room.send_data(
    room=room_name,
    data=answer.encode('utf-8'),
    kind=api.DataPacket.Kind.RELIABLE
)
```

### Option 2: HTTP Webhook
```python
# Send answer to LiveKit agent's webhook endpoint
import httpx

async with httpx.AsyncClient() as client:
    await client.post(
        f"{livekit_webhook_url}/voice-info",
        json={"answer": answer, "call_sid": call_sid}
    )
```

### Option 3: Pub/Sub
```python
# Use Redis/RabbitMQ to publish answer
await redis_client.publish(
    f"voice_call:{call_sid}:info",
    json.dumps({"answer": answer})
)
```

## UI Screenshots

### Normal Call Status
```
┌─────────────────────────────────────┐
│ 📞 Voice Call Status                │
├─────────────────────────────────────┤
│ ███████████░░░░░░░ 75%              │
│ Initiating → Calling → Connected    │
├─────────────────────────────────────┤
│ ✅ Call connected!                  │
│ You are now speaking with the AI... │
└─────────────────────────────────────┘
```

### Needs Clarification
```
┌─────────────────────────────────────┐
│ 📞 Voice Call Status                │
├─────────────────────────────────────┤
│ ██████████████░░░ 65%               │
│ Initiating → Calling → Connected    │
├─────────────────────────────────────┤
│ ❓ Agent needs clarification        │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ ❓ Agent Needs Information      │ │
│ │                                 │ │
│ │ What is the user's verification │ │
│ │ code?                           │ │
│ │                                 │ │
│ │ ┌────────────────┬────┐         │ │
│ │ │ Type answer... │Send│         │ │
│ │ └────────────────┴────┘         │ │
│ │                                 │ │
│ │ 💡 Agent will relay this info   │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Configuration

No additional configuration required. The feature is enabled by default when using voice call workflows.

## Troubleshooting

**Question not appearing in UI:**
- Check workflow status query is working: `get_voice_call_status()`
- Verify polling is active (every 2 seconds)
- Check browser console for errors

**Answer not reaching workflow:**
- Verify `/voice-provide-answer/{workflow_id}` endpoint is accessible
- Check Temporal worker is processing signals
- Review workflow logs for signal reception

**Agent not relaying answer to caller:**
- Implement LiveKit integration (see above)
- Check voice activity webhook is configured
- Verify room data channel is working

## Future Enhancements

1. **Multiple Choice Questions** - Present options instead of free text
2. **Rich Media** - Support images, files for verification
3. **Answer History** - Show all Q&A during the call
4. **Suggested Answers** - AI-powered answer suggestions
5. **Voice Input** - Speech-to-text for answer entry
