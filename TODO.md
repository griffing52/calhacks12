# TODO: Voice Agent Integration & Deployment

This document provides a step-by-step checklist to integrate and deploy the voice agent system with Twilio, Temporal, and LiveKit telephony for a working demo.

## ✅ Pre-Implementation Checklist

All implementation steps are complete:
- [x] Step 1: Voice agent goal and tool definition
- [x] Step 2: Twilio/LiveKit activity implementation
- [x] Step 3: Workflow signals and state management
- [x] Step 4: API endpoint for voice initiation
- [x] Step 5: Frontend form and UI integration

**Status:** Implementation complete, ready for integration and deployment.

---

## 🔧 Phase 1: Environment Setup & API Accounts

### 1.1 Twilio Account Setup

- [ ] **Create Twilio Account**
  - Go to https://www.twilio.com/try-twilio
  - Sign up for free trial or paid account
  - Verify your email and phone number

- [ ] **Get Twilio Credentials**
  ```bash
  # Navigate to Twilio Console: https://console.twilio.com/
  # Copy these values:
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_auth_token_here
  ```

- [ ] **Purchase/Configure Phone Number**
  - Go to Phone Numbers → Buy a Number
  - Purchase a phone number with Voice capabilities
  - Copy the phone number (E.164 format):
    ```bash
    TWILIO_PHONE_NUMBER=+1234567890
    ```

- [ ] **Configure TwiML App (for webhooks later)**
  - Go to Voice → TwiML Apps → Create new TwiML App
  - Name: "Voice Agent App"
  - Voice Request URL: (will set up later)
  - Voice Status Callback URL: (will set up later)

### 1.2 LiveKit Account Setup

- [ ] **Create LiveKit Cloud Account** (Option A - Recommended)
  - Go to https://livekit.io/cloud
  - Sign up for account
  - Create a new project
  - Copy credentials:
    ```bash
    LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
    LIVEKIT_API_SECRET=your_secret_here
    LIVEKIT_URL=wss://your-project.livekit.cloud
    ```

- [ ] **OR Self-Host LiveKit** (Option B - Advanced)
  - Follow: https://docs.livekit.io/deploy/
  - Deploy LiveKit server (Docker, K8s, or cloud)
  - Generate API key/secret
  - Note your LiveKit URL

- [ ] **Configure LiveKit AI Agent** (Critical)
  - Set up LiveKit AI agent with OpenAI or other LLM
  - Configure agent to:
    - Receive goal and context from TwiML
    - Conduct conversation based on goal
    - Send signals back to Temporal workflow when needed
  - Documentation: https://docs.livekit.io/agents/overview/

### 1.3 LLM API Setup

- [ ] **Choose and Configure LLM Provider**
  
  **Option A: OpenAI (Recommended)**
  - Go to https://platform.openai.com/api-keys
  - Create API key
  - Copy:
    ```bash
    LLM_MODEL=openai/gpt-4o
    LLM_KEY=sk-proj-xxxxxxxxxxxxxxxx
    ```

  **Option B: Anthropic Claude**
  - Go to https://console.anthropic.com/
  - Create API key
  - Copy:
    ```bash
    LLM_MODEL=anthropic/claude-3-5-sonnet-20240620
    LLM_KEY=sk-ant-xxxxxxxxxxxxxxxx
    ```

  **Option C: Google Gemini**
  - Go to https://makersuite.google.com/app/apikey
  - Create API key
  - Copy:
    ```bash
    LLM_MODEL=gemini/gemini-2.5-flash-preview-04-17
    LLM_KEY=your_google_api_key
    ```

### 1.4 Environment Configuration

- [ ] **Create `.env` file**
  ```bash
  cd /home/griffing52/calhacks/calhacks12
  cp .env.example .env  # If exists, or create new
  ```

- [ ] **Configure `.env` with all credentials**
  ```bash
  # LLM Configuration (Required)
  LLM_MODEL=openai/gpt-4o
  LLM_KEY=sk-proj-your-key-here

  # Twilio Configuration (Required for production)
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_auth_token_here
  TWILIO_PHONE_NUMBER=+1234567890

  # LiveKit Configuration (Required for production)
  LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
  LIVEKIT_API_SECRET=your_secret_here
  LIVEKIT_URL=wss://your-project.livekit.cloud

  # Agent Configuration (Optional)
  AGENT_GOAL=goal_voice_support
  GOAL_CATEGORIES=voice,hr,travel-flights,fin,ecommerce
  ```

- [ ] **Verify `.env` file**
  ```bash
  # Check that file exists and has all required vars
  cat .env | grep -E "(TWILIO|LIVEKIT|LLM)"
  ```

---

## 🏗️ Phase 2: Webhook Implementation

**Why needed:** Twilio and LiveKit need to send events back to your Temporal workflows via webhooks.

### 2.1 Create Twilio Webhook Endpoints

- [ ] **Add Twilio status callback endpoint to `api/main.py`**
  
  Create new endpoint to receive call status updates:
  
  ```python
  from fastapi import Request, Form
  from typing import Optional
  
  @app.post("/webhooks/twilio/status")
  async def twilio_status_callback(
      CallSid: str = Form(...),
      CallStatus: str = Form(...),
      From: Optional[str] = Form(None),
      To: Optional[str] = Form(None)
  ):
      """
      Twilio sends call status updates here.
      
      Status values: initiated, ringing, in-progress, completed, 
                     busy, failed, no-answer, canceled
      """
      try:
          # Look up workflow by Call SID
          # You'll need to maintain a mapping of Call SID -> Workflow ID
          workflow_id = await get_workflow_id_by_call_sid(CallSid)
          
          if not workflow_id:
              return {"status": "ok", "message": "Workflow not found"}
          
          # Send signal to workflow
          handle = temporal_client.get_workflow_handle(workflow_id)
          await handle.signal(
              "call_update", 
              CallStatus, 
              f"Call status: {CallStatus}"
          )
          
          return {"status": "ok"}
      except Exception as e:
          print(f"Error in Twilio webhook: {e}")
          return {"status": "error", "message": str(e)}
  ```

- [ ] **Create Call SID tracking mechanism**
  
  Add to `api/main.py`:
  
  ```python
  # Simple in-memory mapping (use Redis/DB for production)
  call_sid_to_workflow_id = {}
  
  async def store_call_sid_mapping(call_sid: str, workflow_id: str):
      """Store mapping of Call SID to Workflow ID."""
      call_sid_to_workflow_id[call_sid] = workflow_id
  
  async def get_workflow_id_by_call_sid(call_sid: str) -> Optional[str]:
      """Get Workflow ID for a given Call SID."""
      return call_sid_to_workflow_id.get(call_sid)
  ```

- [ ] **Update voice initiate endpoint to store Call SID**
  
  Modify the `/api/v1/voice-initiate` endpoint response handling:
  
  ```python
  # After workflow starts successfully
  # Store the mapping when we get Call SID from activity
  # This requires polling or a callback from the activity
  ```

### 2.2 Create LiveKit Webhook Endpoints

- [ ] **Add LiveKit event webhook endpoint**
  
  ```python
  @app.post("/webhooks/livekit/events")
  async def livekit_events(request: Request):
      """
      LiveKit AI agent sends events here.
      
      Events:
      - agent_needs_info: AI needs additional info from user
      - call_complete: Call ended successfully
      - call_error: Error during call
      """
      try:
          data = await request.json()
          
          call_sid = data.get("call_sid")
          event_type = data.get("event_type")
          
          # Get workflow ID
          workflow_id = await get_workflow_id_by_call_sid(call_sid)
          if not workflow_id:
              return {"status": "ok", "message": "Workflow not found"}
          
          handle = temporal_client.get_workflow_handle(workflow_id)
          
          # Handle different event types
          if event_type == "agent_needs_info":
              question = data.get("question")
              await handle.signal("required_info_needed", question)
          
          elif event_type == "call_complete":
              summary = data.get("summary", "Call completed")
              await handle.signal("call_ended", "goal_complete", summary)
          
          elif event_type == "call_error":
              error = data.get("error", "Unknown error")
              await handle.signal("call_ended", "error", f"Error: {error}")
          
          return {"status": "ok"}
      
      except Exception as e:
          print(f"Error in LiveKit webhook: {e}")
          return {"status": "error", "message": str(e)}
  ```

- [x] **Add endpoint to provide info back to LiveKit**
  
  ✅ **IMPLEMENTED** in `api/main.py`:
  - Endpoint: `/api/v1/voice-provide-info`
  - Function: `send_info_to_livekit(call_sid, answer)`
  - Modes: Stub mode (logs) and Production mode (LiveKit API)
  - Documentation: `docs/livekit-integration.md`
  - Test script: `scripts/test_livekit_integration.py`
  
  To enable production mode:
  ```bash
  # Add to .env:
  LIVEKIT_URL=wss://your-project.livekit.cloud
  LIVEKIT_API_KEY=APIxxxxx
  LIVEKIT_API_SECRET=xxxxx
  
  # Install dependencies:
  uv sync --extra voice
  ```

### 2.3 Update Activity to Return Call SID

- [ ] **Modify `activities/voice_activities.py`**
  
  Update the activity to return the Call SID immediately:
  
  ```python
  @activity.defn
  async def initiate_voice_call_activity(args: dict) -> dict:
      # ... existing code ...
      
      if use_production_mode:
          # Create call
          call = client.calls.create(
              to=phone_number,
              from_=from_number,
              url=twiml_url,
              status_callback=status_callback_url,
              status_callback_event=['initiated', 'ringing', 'answered', 'completed']
          )
          
          # Return Call SID immediately so workflow can track it
          return {
              "status": "success",
              "call_sid": call.sid,  # Important!
              "message": f"Voice call initiated to {phone_number}",
              "phone_number": phone_number
          }
      else:
          # Stub mode - generate fake Call SID
          fake_sid = f"CA{uuid.uuid4().hex[:32]}"
          return {
              "status": "success",
              "call_sid": fake_sid,
              "message": f"[STUB] Calling {phone_number}...",
              "phone_number": phone_number
          }
  ```

### 2.4 Configure Twilio TwiML

- [ ] **Create TwiML endpoint for call instructions**
  
  Add to `api/main.py`:
  
  ```python
  @app.post("/webhooks/twilio/voice")
  async def twilio_voice_twiml(
      CallSid: str = Form(...),
      From: str = Form(...)
  ):
      """
      Twilio calls this endpoint when call connects.
      Returns TwiML to connect to LiveKit.
      """
      try:
          # Get workflow info by Call SID
          workflow_id = await get_workflow_id_by_call_sid(CallSid)
          
          # Get goal and context from workflow
          if workflow_id:
              handle = temporal_client.get_workflow_handle(workflow_id)
              # Query workflow for goal/context (you'll need to add this query)
              # call_info = await handle.query("get_voice_call_info")
          
          # Generate TwiML that connects to LiveKit
          twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
          <Response>
              <Connect>
                  <Stream url="wss://{LIVEKIT_URL}/twilio">
                      <Parameter name="call_sid" value="{CallSid}" />
                      <Parameter name="goal" value="password_reset" />
                      <Parameter name="context" value="user_needs_help" />
                  </Stream>
              </Connect>
          </Response>
          """
          
          return Response(content=twiml, media_type="application/xml")
      
      except Exception as e:
          print(f"Error generating TwiML: {e}")
          # Fallback TwiML
          return Response(
              content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, an error occurred.</Say></Response>',
              media_type="application/xml"
          )
  ```

---

## 🌐 Phase 3: Webhook Exposure (for Development)

**Problem:** Twilio/LiveKit need to reach your local webhooks.

**Solution:** Use ngrok or similar tunnel service.

### 3.1 Set Up ngrok

- [ ] **Install ngrok**
  ```bash
  # MacOS
  brew install ngrok
  
  # Linux
  curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
    sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
    sudo tee /etc/apt/sources.list.d/ngrok.list && \
    sudo apt update && sudo apt install ngrok
  ```

- [ ] **Sign up and configure ngrok**
  ```bash
  # Sign up at https://dashboard.ngrok.com/signup
  # Get auth token from dashboard
  ngrok config add-authtoken YOUR_AUTH_TOKEN
  ```

- [ ] **Start ngrok tunnel**
  ```bash
  # Tunnel to your API (port 8000)
  ngrok http 8000
  
  # Note the forwarding URL, e.g.:
  # Forwarding: https://abc123.ngrok.io -> http://localhost:8000
  ```

- [ ] **Update environment with ngrok URL**
  ```bash
  # Add to .env
  WEBHOOK_BASE_URL=https://abc123.ngrok.io
  ```

### 3.2 Configure Twilio Webhooks

- [ ] **Set TwiML Voice URL**
  - Go to Twilio Console → Phone Numbers
  - Click your phone number
  - Under "Voice & Fax":
    - Voice URL: `https://abc123.ngrok.io/webhooks/twilio/voice`
    - Method: POST
  - Save

- [ ] **Set Status Callback URL in Code**
  
  Update `activities/voice_activities.py`:
  ```python
  webhook_base = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
  status_callback_url = f"{webhook_base}/webhooks/twilio/status"
  ```

---

## 🔄 Phase 4: LiveKit AI Agent Configuration

This is the most complex part - integrating LiveKit AI agent.

### 4.1 Choose LiveKit Integration Approach

**Option A: Use LiveKit Agents Framework (Recommended)**

- [ ] **Set up LiveKit Python Agent**
  
  Create `livekit_agent/agent.py`:
  
  ```python
  from livekit import agents
  from livekit.agents import llm, stt, tts
  import os
  
  class VoiceSupportAgent(agents.VoiceAgent):
      def __init__(self):
          super().__init__(
              llm=llm.OpenAI(
                  model="gpt-4o",
                  api_key=os.getenv("LLM_KEY")
              ),
              stt=stt.AssemblyAI(),  # Or Deepgram, etc.
              tts=tts.ElevenLabs()   # Or Google, Azure, etc.
          )
      
      async def on_call_start(self, room, participant):
          # Get goal and context from room metadata
          goal = room.metadata.get("goal", "general_support")
          context = room.metadata.get("context", "")
          
          # Greet user based on goal
          greeting = f"Hello! I understand you need help with {goal}. {context}. How can I assist you?"
          await self.say(greeting)
      
      async def handle_conversation(self, transcript):
          # Process user input
          # If you need info from user (via Temporal):
          if self.needs_confirmation_code():
              # Send signal to Temporal
              await self.send_webhook(
                  event_type="agent_needs_info",
                  question="What is your confirmation code?"
              )
              # Wait for response...
          
          # Continue conversation...
  
  # Run agent
  if __name__ == "__main__":
      agent = VoiceSupportAgent()
      agents.run(agent)
  ```

- [ ] **Deploy LiveKit Agent**
  ```bash
  cd livekit_agent
  pip install livekit-agents
  python agent.py
  ```

**Option B: Use LiveKit REST API (Simpler but less flexible)**

- [ ] **Configure LiveKit to use pre-built agent**
  - Use LiveKit Cloud's built-in AI agents
  - Configure via LiveKit dashboard
  - Set webhook URLs for events

### 4.2 Configure LiveKit Webhooks

- [ ] **Add webhook URL in LiveKit Dashboard**
  - Go to LiveKit Cloud dashboard
  - Project Settings → Webhooks
  - Add webhook URL: `https://abc123.ngrok.io/webhooks/livekit/events`
  - Enable events: room_created, room_ended, participant_joined, etc.

---

## 🚀 Phase 5: Integration Testing

### 5.1 Start All Services

- [ ] **Terminal 1: Start Temporal**
  ```bash
  cd /home/griffing52/calhacks/calhacks12
  docker compose up -d
  
  # Verify Temporal is running
  docker ps | grep temporal
  
  # Check UI
  open http://localhost:8081
  ```

- [ ] **Terminal 2: Start ngrok**
  ```bash
  ngrok http 8000
  
  # Note the public URL (e.g., https://abc123.ngrok.io)
  # Update .env WEBHOOK_BASE_URL if needed
  ```

- [ ] **Terminal 3: Start Temporal Worker**
  ```bash
  cd /home/griffing52/calhacks/calhacks12
  sudo chown -R $USER:$USER .venv
  uv run python scripts/run_worker.py
  
  # Should see:
  # Worker started, task_queue=temporal-ai-agent-task-queue
  ```

- [ ] **Terminal 4: Start API**
  ```bash
  cd /home/griffing52/calhacks/calhacks12
  uv run uvicorn api.main:app --reload
  
  # Should see:
  # INFO: Uvicorn running on http://127.0.0.1:8000
  ```

- [ ] **Terminal 5: Start Frontend**
  ```bash
  cd /home/griffing52/calhacks/calhacks12/frontend
  npm install
  npx vite
  
  # Should see:
  # Local: http://localhost:5173
  ```

- [ ] **Terminal 6: Start LiveKit Agent (if using custom agent)**
  ```bash
  cd /home/griffing52/calhacks/calhacks12/livekit_agent
  python agent.py
  ```

### 5.2 Test Voice Call Flow

- [ ] **Test 1: Initiate call from UI**
  1. Open http://localhost:5173
  2. Click "📞 Start Voice Call"
  3. Fill form:
     - Phone: `+1YOUR_VERIFIED_NUMBER` (use your actual phone)
     - Goal: `Password reset test`
     - Context: `Testing the voice agent system`
  4. Click "Initiate Voice Call"
  5. Expected: Success message with workflow ID

- [ ] **Test 2: Verify call initiation**
  1. Check Temporal UI: http://localhost:8081
  2. Find workflow: `voice-call-<uuid>`
  3. Check workflow is running
  4. Verify InitiateVoiceCall activity executed

- [ ] **Test 3: Receive actual phone call**
  1. Your phone should ring within seconds
  2. Answer the call
  3. Expected: Hear AI agent greeting you
  4. Have a conversation with the agent

- [ ] **Test 4: Verify webhooks**
  1. Check API logs for webhook calls:
     ```bash
     # Should see logs like:
     # POST /webhooks/twilio/status - 200 OK
     # POST /webhooks/livekit/events - 200 OK
     ```
  2. Check Temporal UI for signals received:
     - call_update signals
     - call_ended signal (when call completes)

- [ ] **Test 5: End-to-end flow**
  1. Initiate call from UI
  2. Answer phone
  3. Have conversation with AI
  4. Hang up
  5. Check workflow completed in Temporal UI
  6. Verify final status in conversation history

### 5.3 Debug Common Issues

- [ ] **Issue: Call not received**
  - Check Twilio Console → Calls for errors
  - Verify phone number is E.164 format
  - Check TwiML URL is accessible via ngrok
  - Verify Twilio can reach your webhook

- [ ] **Issue: Webhooks not received**
  - Check ngrok is running: `curl https://your-ngrok-url.ngrok.io/`
  - Check API logs for errors
  - Verify webhook URLs in Twilio/LiveKit match ngrok URL
  - Test webhook manually:
    ```bash
    curl -X POST https://your-ngrok-url.ngrok.io/webhooks/twilio/status \
      -d "CallSid=CA123&CallStatus=ringing"
    ```

- [ ] **Issue: LiveKit not connecting**
  - Check LiveKit credentials in .env
  - Verify LiveKit agent is running (if custom)
  - Check LiveKit dashboard for errors
  - Verify TwiML Stream URL is correct

- [ ] **Issue: Workflow not updating**
  - Check worker is running and processing
  - Verify signals are being sent
  - Check workflow logs in Temporal UI
  - Verify Call SID mapping is working

---

## 📊 Phase 6: Production Deployment

### 6.1 Deploy to Cloud

- [ ] **Choose deployment platform**
  - Option A: AWS (ECS, Lambda, or EC2)
  - Option B: Google Cloud (Cloud Run, GKE)
  - Option C: Azure (Container Apps, AKS)
  - Option D: DigitalOcean (App Platform, Droplets)

- [ ] **Deploy API**
  - Containerize with Docker
  - Deploy to cloud platform
  - Get public URL (e.g., https://api.yourdomain.com)

- [ ] **Deploy Worker**
  - Run as background service/container
  - Configure auto-scaling based on queue depth
  - Ensure it can reach Temporal server

- [ ] **Deploy Frontend**
  - Build production bundle: `npm run build`
  - Deploy to:
    - Option A: Vercel (easiest)
    - Option B: Netlify
    - Option C: AWS S3 + CloudFront
    - Option D: Your own CDN

- [ ] **Use Temporal Cloud** (Recommended) or self-host
  - Sign up: https://cloud.temporal.io/
  - Create namespace
  - Update connection details in code
  - OR self-host Temporal on Kubernetes

### 6.2 Configure Production Webhooks

- [ ] **Update Twilio webhooks with production URLs**
  - Voice URL: `https://api.yourdomain.com/webhooks/twilio/voice`
  - Status Callback: `https://api.yourdomain.com/webhooks/twilio/status`

- [ ] **Update LiveKit webhooks**
  - Webhook URL: `https://api.yourdomain.com/webhooks/livekit/events`

- [ ] **Remove ngrok dependency**
  - Update WEBHOOK_BASE_URL to production URL
  - Test webhooks reach production API

### 6.3 Security & Monitoring

- [ ] **Secure webhooks**
  - Verify Twilio signatures
  - Verify LiveKit webhook signatures
  - Add authentication to sensitive endpoints

- [ ] **Add monitoring**
  - Set up logging (CloudWatch, Datadog, etc.)
  - Monitor workflow success/failure rates
  - Track call metrics (duration, completion, errors)
  - Set up alerts for failures

- [ ] **Add error handling**
  - Retry logic for failed calls
  - Graceful degradation
  - User notifications for errors

---

## 🎯 Phase 7: Final Verification

### 7.1 Pre-Launch Checklist

- [ ] All environment variables set
- [ ] Twilio account funded (if trial ended)
- [ ] LiveKit configured and tested
- [ ] All webhooks configured and accessible
- [ ] Worker running and processing workflows
- [ ] API accessible and responding
- [ ] Frontend deployed and accessible
- [ ] End-to-end test successful
- [ ] Error handling tested
- [ ] Monitoring configured

### 7.2 Demo Script

Prepare a demo script for pitch:

1. **Show UI**: "Here's our voice agent interface"
2. **Fill Form**: Fill in phone number, goal, context
3. **Submit**: "Watch as we initiate the call"
4. **Show Temporal**: "Here's the workflow orchestrating everything"
5. **Receive Call**: Answer phone, have conversation
6. **Show Updates**: Show real-time updates in UI
7. **Complete**: Show workflow completion

---

## 📝 Quick Reference

### Environment Variables Needed
```bash
LLM_MODEL=openai/gpt-4o
LLM_KEY=sk-proj-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=...
LIVEKIT_URL=wss://...
WEBHOOK_BASE_URL=https://...
```

### Services to Run
1. Temporal server (Docker)
2. ngrok (dev) or public URL (prod)
3. Temporal worker
4. FastAPI backend
5. Vite frontend
6. LiveKit agent (if custom)

### Webhook Endpoints
- `/webhooks/twilio/voice` - TwiML generation
- `/webhooks/twilio/status` - Call status updates
- `/webhooks/livekit/events` - LiveKit events
- `/api/v1/voice-initiate` - Start voice call
- `/api/v1/voice-provide-info` - Provide info to AI

### Testing Commands
```bash
# Verify all steps
python scripts/verify_voice_agent_complete.py

# Test API
curl http://localhost:8000/

# Test webhook
curl -X POST http://localhost:8000/webhooks/twilio/status \
  -d "CallSid=CA123&CallStatus=ringing"
```

---

## 🚨 Important Notes

### Cost Considerations
- **Twilio**: ~$1/month per phone number + $0.01-0.02/minute for calls
- **LiveKit**: Free tier available, then usage-based
- **OpenAI**: ~$0.01-0.03 per conversation depending on length
- **Temporal Cloud**: Free tier available, then $25+/month

### Development vs Production
- **Development**: Use ngrok, stub mode, test phone numbers
- **Production**: Use real domains, production APIs, proper auth

### Known Limitations
- Stub mode doesn't make real calls (testing only)
- Call SID mapping is in-memory (use Redis/DB for production)
- No authentication on webhooks (add for production)
- No call recording (can be added via Twilio)

---

## ✅ Success Criteria

You'll know everything is working when:

1. ✅ Frontend loads without errors
2. ✅ Voice call form accepts input
3. ✅ Submitting form creates Temporal workflow
4. ✅ Phone actually rings
5. ✅ AI agent answers and has conversation
6. ✅ Workflow updates in real-time via signals
7. ✅ Call completes successfully
8. ✅ Workflow shows final status

**You're ready to pitch when all boxes above are checked!** 🎉

---

## 🆘 Need Help?

### Documentation
- Twilio: https://www.twilio.com/docs
- LiveKit: https://docs.livekit.io
- Temporal: https://docs.temporal.io

### Support
- Check verification scripts for implementation issues
- Review step-by-step documentation (STEP1-5_COMPLETE.md)
- Check Temporal UI for workflow errors
- Review webhook logs for connectivity issues

### Quick Fixes
```bash
# Restart everything
docker compose down
docker compose up -d
# Ctrl+C all terminal processes, restart them

# Clear workflow state
# Go to Temporal UI, terminate stuck workflows

# Check logs
docker logs temporal
tail -f api.log
```

Good luck with your pitch! 🚀
