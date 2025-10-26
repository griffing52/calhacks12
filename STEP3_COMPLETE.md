# Step 3 Complete: Workflow Logic Updates for Voice Calls

## Summary

Step 3 has been successfully completed! The `AgentGoalWorkflow` now includes comprehensive voice call support with signals, state management, and waiting logic for external events from Twilio/LiveKit webhooks.

## What Was Implemented

### 1. Voice Call State Variables

Added 5 new state variables to track voice call status:

```python
# Voice call specific state
self.voice_call_active: bool = False  # indicates an active voice call
self.voice_call_sid: Optional[str] = None  # Twilio Call SID for tracking
self.voice_call_status: str = "not_started"  # Status: not_started, initiated, ringing, in_progress, completed, failed
self.voice_info_needed: bool = False  # indicates LiveKit AI needs info from user
self.voice_pending_question: Optional[str] = None  # question from LiveKit AI
```

**State Tracking:**
- `voice_call_active` - Whether a call is currently in progress
- `voice_call_sid` - Twilio Call SID for correlation with webhooks
- `voice_call_status` - Current status of the call
- `voice_info_needed` - Flag indicating LiveKit AI awaits user input
- `voice_pending_question` - The specific question awaiting answer

### 2. Voice Call Signals

Implemented 4 new workflow signals for external event handling:

#### `call_update(status: str, message: str)`

**Purpose**: Receive call status updates from Twilio webhooks

**Parameters:**
- `status` - Call status (initiated, ringing, in_progress, completed, failed, etc.)
- `message` - Human-readable status message

**Example:**
```python
await workflow_handle.signal("call_update", "ringing", "Call is ringing...")
```

**Behavior:**
- Updates `voice_call_status`
- Logs update to conversation history with timestamp
- Sets `voice_call_active` based on status
- Terminal statuses (completed, failed, etc.) set active = False

#### `call_ended(reason: str, final_summary: str)`

**Purpose**: Handle call termination and receive summary

**Parameters:**
- `reason` - Why the call ended (goal_complete, caller_hung_up, error, etc.)
- `final_summary` - Summary of what was accomplished

**Example:**
```python
await workflow_handle.signal("call_ended", "goal_complete", "Password successfully reset")
```

**Behavior:**
- Sets `voice_call_active = False`
- Sets `voice_call_status = "completed"`
- Logs termination info to conversation history
- Adds prompt to process call completion
- Allows workflow to continue or end gracefully

#### `required_info_needed(question: str)`

**Purpose**: Handle LiveKit AI requests for additional user information

**Parameters:**
- `question` - Question that needs to be answered

**Example:**
```python
await workflow_handle.signal("required_info_needed", "What is your confirmation code?")
```

**Behavior:**
- Sets `voice_info_needed = True`
- Stores question in `voice_pending_question`
- Logs info request to conversation history
- Adds prompt to ask user for information
- Workflow can display question to user in UI

#### `voice_info_provided(answer: str)`

**Purpose**: Receive user's answer to LiveKit AI's question

**Parameters:**
- `answer` - User's answer to the pending question

**Example:**
```python
await workflow_handle.signal("voice_info_provided", "123456")
```

**Behavior:**
- Validates that info was actually needed
- Clears `voice_info_needed` flag
- Logs answer to conversation history
- Clears `voice_pending_question`
- Answer can be forwarded to LiveKit AI via webhook

### 3. Voice Call Query

Added new query method to retrieve voice call status:

```python
@workflow.query
def get_voice_call_status(self) -> Dict[str, Any]:
    """Query handler to retrieve current voice call status."""
    return {
        "active": self.voice_call_active,
        "call_sid": self.voice_call_sid,
        "status": self.voice_call_status,
        "info_needed": self.voice_info_needed,
        "pending_question": self.voice_pending_question
    }
```

**Usage:**
```python
status = await workflow_handle.query("get_voice_call_status")
print(f"Call active: {status['active']}")
print(f"Call SID: {status['call_sid']}")
print(f"Status: {status['status']}")
```

### 4. Voice Call Execution Logic

Modified `execute_tool()` method to detect and handle voice calls specially:

```python
async def execute_tool(self, current_tool: str) -> bool:
    # ...
    
    # Special handling for voice call initiation
    if current_tool == "InitiateVoiceCall":
        await self.execute_voice_call()
        return waiting_for_confirm
    
    # Regular tool execution for other tools
    # ...
```

### 5. Voice Call Execution Method

Implemented new `execute_voice_call()` method:

```python
async def execute_voice_call(self) -> None:
    """
    Execute voice call initiation and enter waiting state for call events.
    
    This method:
    1. Executes the InitiateVoiceCall activity
    2. Stores the Call SID for tracking
    3. Sets voice_call_active = True
    4. Waits for external signals
    """
```

**Workflow:**
1. Executes `InitiateVoiceCall` activity
2. Extracts Call SID from result
3. Sets `voice_call_active = True`
4. Sets `voice_call_status = "initiated"`
5. Adds waiting message to conversation
6. Workflow continues running, waiting for signals
7. Handles both success and failure cases

**Success Response:**
```json
{
    "next": "question",
    "response": "Voice call initiated to +14155551234. Waiting for call to connect..."
}
```

**Failure Response:**
```json
{
    "next": "question",
    "response": "Failed to initiate voice call: <error>. Would you like to try again?"
}
```

### 6. Conversation History Integration

All voice events are logged to conversation history:

```python
# Call updates
self.add_message("voice_call_update", {
    "status": status,
    "message": message,
    "call_sid": self.voice_call_sid,
    "timestamp": workflow.now().isoformat()
})

# Call termination
self.add_message("voice_call_ended", {
    "reason": reason,
    "summary": final_summary,
    "call_sid": self.voice_call_sid,
    "timestamp": workflow.now().isoformat()
})

# Info requests
self.add_message("voice_info_request", {
    "question": question,
    "call_sid": self.voice_call_sid,
    "timestamp": workflow.now().isoformat(),
    "awaiting_response": True
})

# Info responses
self.add_message("voice_info_response", {
    "question": self.voice_pending_question,
    "answer": answer,
    "call_sid": self.voice_call_sid,
    "timestamp": workflow.now().isoformat()
})
```

## Workflow Execution Flow

### Normal Flow (Success)

```
1. User: "I need help resetting my password"
   └─> Goal selected: goal_voice_support

2. Agent: "I can call you to help. What's your phone number?"
   
3. User: "+14155551234"
   
4. Agent: "I'll call +14155551234 to help with password reset. Confirm?"
   
5. User confirms tool
   
6. Workflow executes InitiateVoiceCall activity
   ├─> voice_call_sid = "CA1234..."
   ├─> voice_call_active = True
   └─> voice_call_status = "initiated"

7. Agent: "Voice call initiated. Waiting for call to connect..."
   
8. Workflow enters waiting state
   └─> Waits for: call_update, call_ended, required_info_needed, user_prompt, end_chat

9. External webhook → signal("call_update", "ringing", "Call ringing...")
   └─> voice_call_status = "ringing"

10. External webhook → signal("call_update", "in_progress", "Call answered")
    └─> voice_call_status = "in_progress"

11. External webhook → signal("call_ended", "goal_complete", "Password reset successful")
    ├─> voice_call_active = False
    ├─> voice_call_status = "completed"
    └─> Adds completion prompt to queue

12. Workflow processes completion
    └─> Can continue with follow-up or end
```

### Flow with Info Request

```
1-10. [Same as above]

11. LiveKit AI needs info → signal("required_info_needed", "What is your confirmation code?")
    ├─> voice_info_needed = True
    ├─> voice_pending_question = "What is your confirmation code?"
    └─> Adds prompt to ask user

12. Agent: "The voice assistant needs: What is your confirmation code?"

13. User (via UI): "123456"

14. UI/API → signal("voice_info_provided", "123456")
    ├─> voice_info_needed = False
    ├─> Logs answer to history
    └─> Answer can be sent to LiveKit

15. Call continues...

16. [Call ends as in step 11-12 above]
```

## Files Modified

1. ✅ `workflows/agent_goal_workflow.py` - Added voice call logic

## Verification

Created verification script:

```bash
python scripts/verify_voice_agent_step3.py
```

**Tests:**
- ✅ Voice state variables present
- ✅ All 4 signals implemented
- ✅ Signal parameters correct
- ✅ Query method implemented
- ✅ Voice call execution logic
- ✅ Conversation history integration
- ✅ Waiting state documented

## Signal Usage Examples

### From Twilio Webhook

```python
from temporalio.client import Client

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("workflow-id")

# Call status update
await handle.signal("call_update", "ringing", "Call is ringing...")

# Call answered
await handle.signal("call_update", "in_progress", "Call in progress")

# Call completed
await handle.signal("call_ended", "goal_complete", "Password reset successful")
```

### From LiveKit Webhook

```python
# Request info from user
await handle.signal(
    "required_info_needed",
    "Please provide your account email address"
)

# Later, when user provides info via UI
await handle.signal("voice_info_provided", "user@example.com")
```

### Querying Status

```python
# Get current voice call status
status = await handle.query("get_voice_call_status")

print(f"Active: {status['active']}")
print(f"Call SID: {status['call_sid']}")
print(f"Status: {status['status']}")
print(f"Info needed: {status['info_needed']}")
if status['pending_question']:
    print(f"Pending question: {status['pending_question']}")
```

## Integration Points

### With Twilio

Twilio webhooks should send signals to the workflow:

```python
# In your Twilio webhook handler
@app.post("/webhooks/twilio/status")
async def twilio_status_callback(request: Request):
    data = await request.form()
    
    call_sid = data.get("CallSid")
    call_status = data.get("CallStatus")  # initiated, ringing, in-progress, completed, etc.
    
    # Find workflow by call_sid (stored in workflow metadata or database)
    workflow_id = lookup_workflow_by_call_sid(call_sid)
    
    # Send signal to workflow
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("call_update", call_status, f"Call status: {call_status}")
    
    return {"status": "ok"}
```

### With LiveKit

LiveKit AI agent can send signals when it needs info:

```python
# In your LiveKit webhook handler
@app.post("/webhooks/livekit/info_request")
async def livekit_info_request(request: Request):
    data = await request.json()
    
    call_sid = data.get("call_sid")
    question = data.get("question")
    
    # Find workflow
    workflow_id = lookup_workflow_by_call_sid(call_sid)
    
    # Request info from user
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("required_info_needed", question)
    
    return {"status": "ok"}
```

## State Machine Diagram

```
[not_started] 
    ↓ (user confirms tool)
[initiated] ← Call activity executed
    ↓ (call_update: ringing)
[ringing]
    ↓ (call_update: in_progress)
[in_progress] ←→ [info_needed] (required_info_needed / voice_info_provided)
    ↓ (call_ended)
[completed/failed]
    ↓
[voice_call_active = False]
```

## Benefits of This Implementation

### 1. Durable State
- Workflow state persists across worker restarts
- Call tracking survives failures
- No lost updates from webhooks

### 2. Event-Driven
- Workflow responds to external events
- Non-blocking waiting
- Multiple concurrent calls supported

### 3. Audit Trail
- Complete conversation history
- All call events logged with timestamps
- Easy to debug and analyze

### 4. Flexibility
- Supports info requests during call
- Can handle multiple status updates
- Graceful error handling

### 5. Query Support
- Real-time status checking
- UI can display call state
- Monitoring and debugging

## Error Handling

### Call Initiation Failure

```python
# If activity fails
if call_result.get("status") == "error":
    # Workflow continues, user can retry
    self.add_message("agent", {
        "response": "Failed to initiate call. Would you like to try again?"
    })
```

### Unexpected Signal

```python
# If voice_info_provided sent when no info needed
if not self.voice_info_needed:
    workflow.logger.warning("Received voice_info_provided but no info was needed")
    return  # Gracefully ignore
```

### Call Dropped

```python
# Webhook sends call_ended with reason
await handle.signal("call_ended", "caller_hung_up", "Call was disconnected")
# Workflow handles gracefully, asks if user wants to retry
```

## Testing

### Unit Testing Signals

```python
# Test in workflow test
async def test_voice_call_signals():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Start workflow
        async with Worker(...):
            handle = await client.start_workflow(...)
            
            # Send signal
            await handle.signal("call_update", "ringing", "Ringing...")
            
            # Query state
            status = await handle.query("get_voice_call_status")
            assert status["status"] == "ringing"
```

### Integration Testing

```bash
# Start worker
uv run python scripts/run_worker.py

# Start workflow via API
curl -X POST http://localhost:8000/start-chat \
  -H "Content-Type: application/json" \
  -d '{"goal_id": "goal_voice_support"}'

# Send test signals
python scripts/test_voice_signals.py --workflow-id <id>
```

## Next Steps

### Step 4: Create Webhook Endpoints

Create FastAPI endpoints to receive and forward signals:

```python
@app.post("/webhooks/twilio/status")
async def twilio_status(...):
    # Parse Twilio webhook
    # Find workflow by call_sid
    # Send call_update signal
    pass

@app.post("/webhooks/livekit/events")
async def livekit_events(...):
    # Parse LiveKit event
    # Send required_info_needed or call_ended signal
    pass
```

### Step 5: LiveKit Integration

Configure LiveKit AI agent to:
1. Receive goal and context from TwiML
2. Conduct conversation
3. Send signals when needing info
4. Send completion signal with summary

## Success Criteria ✅

- [x] Voice state variables added (5 vars)
- [x] Voice signals implemented (4 signals)
- [x] Signal parameters correct
- [x] Voice query method added
- [x] Voice call execution logic
- [x] Conversation history integration
- [x] Waiting state for external events
- [x] Error handling for failures
- [x] Verification script passing
- [x] Documentation complete

**Status: COMPLETE** 🎉

Ready to proceed with Step 4 (Webhook Endpoints)!
