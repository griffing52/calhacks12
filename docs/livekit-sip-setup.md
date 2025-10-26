# LiveKit SIP Integration Setup Guide

## Current Status ✅

Your LiveKit account already has SIP configured:
- **SIP Trunk ID**: `ST_kngPd5bsM8U4`
- **Phone Number**: `+13105825023`
- **Dispatch Rule**: `SDR_D6y5wdCDWXP2` → Routes to agent `temporal-voice-agent`
- **Room Pattern**: `call-_<caller>_<random>`

## Finding Your LiveKit SIP URI

### Option 1: Check LiveKit Cloud Dashboard
1. Go to https://cloud.livekit.io/
2. Navigate to **SIP** → **Inbound**
3. Find your trunk `ST_kngPd5bsM8U4`
4. The SIP URI should be displayed (format: `sip:+13105825023@sip-<region>.livekit.cloud`)

### Option 2: Common LiveKit SIP URI Format
LiveKit Cloud SIP URIs typically follow this pattern:
```
sip:+13105825023@sip.livekit.cloud
```
or with region:
```
sip:+13105825023@sip-us-west.livekit.cloud
```

## Configuring Twilio

Once you have the LiveKit SIP URI, update your Twilio phone number:

### Method 1: Twilio Console (Recommended)
1. Go to https://console.twilio.com/
2. Navigate to **Phone Numbers** → **Manage** → **Active Numbers**
3. Click on your number: `+13105825023`
4. Under **Voice Configuration**:
   - **Configure with**: TwiML
   - **A CALL COMES IN**: Webhook
   - **URL**: Create a TwiML Bin (see below)
   - **HTTP Method**: POST

### Method 2: TwiML Bin
Create a TwiML Bin with this content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>sip:+13105825023@sip.livekit.cloud</Sip>
    </Dial>
</Response>
```

Steps:
1. Go to **TwiML Bins** in Twilio Console
2. Create a new TwiML Bin
3. Paste the XML above (update SIP URI if different)
4. Save and get the TwiML Bin URL
5. Point your phone number's Voice URL to this TwiML Bin URL

### Method 3: Using the Script
Run the configuration script:
```bash
cd /home/griffing52/calhacks/calhacks12
uv run python scripts/configure_twilio_sip.py
```

## Testing the Integration

1. **Make sure your LiveKit agent is running**:
   ```bash
   cd /home/griffing52/calhacks/calhacks12
   source livekit_venv/bin/activate
   cd livekit_agent
   python agent.py dev
   ```

2. **Call your Twilio number**: `+13105825023`

3. **Expected flow**:
   - Twilio receives the call
   - Twilio forwards to LiveKit SIP URI
   - LiveKit creates room `call-_<your_number>_<random>`
   - LiveKit dispatches `temporal-voice-agent` to the room
   - Agent greets you with: "Hello! This is an AI assistant..."

## Troubleshooting

### Check Agent is Running
```bash
ps aux | grep "python agent.py dev"
```

### Check LiveKit Logs
Watch your agent terminal for:
```
[INFO] livekit.agents: job assigned
[INFO] voice-agent: Agent starting for room: call-...
```

### Check Dispatch Rules
```bash
lk sip dispatch list --api-key="APIXuwGXkLhyAW7" --api-secret="Fq2FhB7oZ4hlVI53VUBesHWJSFfVzllf1u5uIrPYUphB" --url="wss://wait-less-22pf77bb.livekit.cloud"
```

### Verify SIP Trunk
```bash
lk sip inbound list --api-key="APIXuwGXkLhyAW7" --api-secret="Fq2FhB7oZ4hlVI53VUBesHWJSFfVzllf1u5uIrPYUphB" --url="wss://wait-less-22pf77bb.livekit.cloud"
```

## Next Steps

1. ✅ Find your LiveKit SIP URI (from dashboard or try `sip:+13105825023@sip.livekit.cloud`)
2. ✅ Create TwiML Bin in Twilio with `<Dial><Sip>...</Sip></Dial>`
3. ✅ Point your phone number to the TwiML Bin
4. ✅ Make sure LiveKit agent is running
5. ✅ Test by calling your number!
