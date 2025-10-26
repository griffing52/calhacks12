#!/usr/bin/env python3
"""
Verify LiveKit SIP integration is properly configured.
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def check_webhook():
    """Check if the webhook returns correct TwiML."""
    webhook_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
    url = f"{webhook_url}/webhooks/twilio/voice"
    
    print("🔍 Testing webhook endpoint...")
    print(f"   URL: {url}")
    
    try:
        response = requests.post(
            url,
            data={"CallSid": "TEST_VERIFY", "From": "+15551234567"},
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"   ❌ HTTP {response.status_code}")
            return False
        
        twiml = response.text
        expected_sip = "sip:+13105825023@sip.livekit.cloud"
        
        if expected_sip in twiml:
            print(f"   ✅ TwiML correct: {expected_sip}")
            return True
        else:
            print(f"   ❌ TwiML incorrect:")
            print(f"      Expected: {expected_sip}")
            print(f"      Got: {twiml}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_env_vars():
    """Check required environment variables."""
    print("🔍 Checking environment variables...")
    
    required = {
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER"),
        "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
        "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
        "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
    }
    
    all_ok = True
    for name, value in required.items():
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {name}: {masked}")
        else:
            print(f"   ❌ {name}: NOT SET")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 60)
    print("LiveKit SIP Integration Verification")
    print("=" * 60)
    print()
    
    env_ok = check_env_vars()
    print()
    
    webhook_ok = check_webhook()
    print()
    
    print("=" * 60)
    if env_ok and webhook_ok:
        print("✅ Integration appears ready!")
        print()
        print("Next steps:")
        print("1. Ensure LiveKit agent is running:")
        print("   cd livekit_agent && python agent.py dev")
        print()
        print("2. Make a test call to: +13105825023")
        print()
        print("3. Expected: Agent answers and greets you")
        return 0
    else:
        print("❌ Issues detected - review output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
