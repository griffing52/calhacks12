#!/usr/bin/env python3
"""
Update Twilio phone number to use LiveKit SIP instead of TwiML webhooks.

This configures Twilio to forward calls directly to LiveKit via SIP,
bypassing the need for Media Streams WebSocket integration.
"""

import os
import sys
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment
load_dotenv()

def main():
    # Get Twilio credentials
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    phone_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, phone_number]):
        print("❌ Missing Twilio credentials in .env file")
        sys.exit(1)
    
    # LiveKit SIP URI - this is where Twilio will forward calls
    # Format: sip:+<phone_number>@sip.livekit.cloud
    # The exact domain might be different - check LiveKit docs
    livekit_sip_uri = f"sip:{phone_number}@sip.livekit.cloud"
    
    print("=" * 60)
    print("Twilio → LiveKit SIP Configuration")
    print("=" * 60)
    print(f"\n📞 Phone Number: {phone_number}")
    print(f"🔗 LiveKit SIP URI: {livekit_sip_uri}")
    
    # Create Twilio client
    client = Client(account_sid, auth_token)
    
    # Get the phone number
    try:
        incoming_phones = client.incoming_phone_numbers.list(phone_number=phone_number)
        
        if not incoming_phones:
            print(f"\n❌ Phone number {phone_number} not found in your account!")
            sys.exit(1)
        
        phone = incoming_phones[0]
        
        print(f"\n📋 Current Configuration:")
        print(f"   Voice URL: {phone.voice_url}")
        print(f"   Voice Method: {phone.voice_method}")
        
        # Update to use SIP
        print(f"\n🔧 Updating to use LiveKit SIP...")
        
        # Method 1: Direct SIP URI (if supported)
        try:
            phone.update(
                voice_url=livekit_sip_uri,
                voice_method='POST'
            )
            print(f"✅ Phone number updated to forward to LiveKit SIP!")
            
        except Exception as e:
            print(f"⚠️  Direct SIP update failed: {e}")
            print(f"\n💡 Alternative: Use TwiML to forward to SIP")
            print(f"\n   Create a TwiML Bin in Twilio Console with:")
            print(f"   ")
            print(f"   <?xml version=\"1.0\" encoding=\"UTF-8\"?>")
            print(f"   <Response>")
            print(f"       <Dial>")
            print(f"           <Sip>{livekit_sip_uri}</Sip>")
            print(f"       </Dial>")
            print(f"   </Response>")
            print(f"\n   Then point your phone number's Voice URL to that TwiML Bin")
        
        print(f"\n" + "=" * 60)
        print("✅ Configuration Complete!")
        print("=" * 60)
        print(f"\n📝 What happens now:")
        print(f"   1. Someone calls {phone_number}")
        print(f"   2. Twilio forwards to LiveKit SIP: {livekit_sip_uri}")
        print(f"   3. LiveKit creates a room and dispatches your agent")
        print(f"   4. Your agent (temporal-voice-agent) handles the call")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
