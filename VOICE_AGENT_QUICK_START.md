# Voice Agent Quick Start Guide

## 🚀 Quick Commands

### Start All Services

```bash
# Terminal 1: Temporal
docker compose up -d

# Terminal 2: Worker
uv run python scripts/run_worker.py

# Terminal 3: API
uv run uvicorn api.main:app --reload

# Terminal 4: Frontend
cd frontend && npx vite
```

### Verify Implementation

```bash
# Quick verification of all steps
python scripts/verify_voice_agent_complete.py

# Individual step verification
python scripts/verify_voice_agent_step1.py  # Goal & Tool
python scripts/verify_voice_agent_step2.py  # Activity
python scripts/verify_voice_agent_step3.py  # Workflow
python scripts/verify_voice_agent_step4.py  # API
python scripts/verify_voice_agent_step5.py  # Frontend
```

### Test Endpoints

```bash
# Test voice initiate endpoint
uv run python scripts/test_voice_initiate_endpoint.py

# Manual test with curl
curl -X POST http://localhost:8000/api/v1/voice-initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551234",
    "goal": "Password reset",
    "context": "User cannot log in"
  }'
```

## 📋 URLs

- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8081

## 🔧 Environment Variables

```bash
# Required
LLM_MODEL=openai/gpt-4o
LLM_KEY=your-api-key

# Optional (for production mode)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

## 📁 Key Files

### Created
- `goals/voice_agent.py` - Voice goal
- `tools/initiate_voice_call.py` - Voice tool
- `activities/voice_activities.py` - Twilio/LiveKit activity
- `frontend/src/components/VoiceCallForm.jsx` - UI form

### Modified
- `workflows/agent_goal_workflow.py` - Voice signals
- `api/main.py` - Voice endpoint
- `frontend/src/pages/App.jsx` - Voice mode
- `frontend/src/services/api.js` - API methods

## 🧪 Testing Flow

1. **Open Frontend**
   - Navigate to http://localhost:5173

2. **Click Voice Call Button**
   - Click "📞 Start Voice Call"

3. **Fill Form**
   - Phone: `+14155551234`
   - Goal: `Test call`
   - Context: `Testing voice feature`

4. **Submit & Verify**
   - Click "Initiate Voice Call"
   - Note the workflow ID
   - Check Temporal UI: http://localhost:8081

5. **Expected Results**
   - ✅ Success message displayed
   - ✅ Workflow ID shown
   - ✅ Workflow visible in Temporal UI
   - ✅ Stub mode: "[STUB] Calling..." in logs
   - ✅ Production mode: Actual Twilio call

## 🐛 Troubleshooting

### Worker Issues
```bash
# Check worker is running
ps aux | grep run_worker

# Restart worker
# Ctrl+C in worker terminal, then:
uv run python scripts/run_worker.py
```

### API Issues
```bash
# Check API is running
curl http://localhost:8000/

# Restart API
# Ctrl+C in API terminal, then:
uv run uvicorn api.main:app --reload
```

### Frontend Issues
```bash
# Rebuild frontend
cd frontend
rm -rf node_modules
npm install
npx vite
```

### Temporal Issues
```bash
# Check Temporal is running
docker ps | grep temporal

# Restart Temporal
docker compose down
docker compose up -d
```

## 📊 Workflow States

### Voice Call Status Flow
```
not_started → initiated → ringing → in_progress → completed
                                   ↓
                              failed/busy/no-answer
```

### Signals
```python
# Status updates
call_update(status, message)

# Call completion
call_ended(reason, summary)

# Info requests
required_info_needed(question)
voice_info_provided(answer)
```

### Queries
```python
# Get status
get_voice_call_status()
# Returns: { active, call_sid, status, info_needed, pending_question }
```

## 📚 Documentation

- **Complete Summary**: `VOICE_AGENT_IMPLEMENTATION_SUMMARY.md`
- **Step Details**: `STEP1_COMPLETE.md` - `STEP5_COMPLETE.md`
- **Setup Guide**: `docs/voice-agent-setup.md`
- **This Guide**: `VOICE_AGENT_QUICK_START.md`

## ✅ Verification Checklist

- [ ] All services running
- [ ] Frontend accessible at localhost:5173
- [ ] API accessible at localhost:8000
- [ ] Temporal UI accessible at localhost:8081
- [ ] Voice call button appears in UI
- [ ] Form validates inputs
- [ ] API endpoint responds
- [ ] Workflow starts successfully
- [ ] Workflow ID displayed
- [ ] Workflow visible in Temporal UI

## 🎯 Implementation Status

**All Steps Complete:** ✅

- ✅ Step 1: Goal and Tool Definition
- ✅ Step 2: Activity Implementation  
- ✅ Step 3: Workflow Logic Updates
- ✅ Step 4: API Endpoint Creation
- ✅ Step 5: Frontend Integration

**Verification:** 5/5 passing

**Ready for:** Testing and Production Deployment

---

**Need Help?** Check the troubleshooting section or review the complete documentation.

**Last Updated:** October 26, 2025
