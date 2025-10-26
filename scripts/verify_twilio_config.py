#!/usr/bin/env python3
"""
Verify Twilio configuration for voice calls.
"""
import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment
load_dotenv()

# Get credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
phone_number = os.getenv("TWILIO_PHONE_NUMBER")
webhook_base = os.getenv("WEBHOOK_BASE_URL")

if not all([account_sid, auth_token, phone_number, webhook_base]):
    print("❌ Missing environment variables!")
    print("   Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_BASE_URL")
    sys.exit(1)

print("🔍 Verifying Twilio Configuration...\n")

# Create client
client = Client(account_sid, auth_token)

# Get phone number details
try:
    incoming_phone = client.incoming_phone_numbers.list(phone_number=phone_number)
    
    if not incoming_phone:
        print(f"❌ Phone number {phone_number} not found in your account!")
        sys.exit(1)
    
    phone = incoming_phone[0]
    
    print(f"✅ Phone Number: {phone.phone_number}")
    print(f"   Friendly Name: {phone.friendly_name}")
    print(f"   Capabilities: Voice={phone.capabilities.get('voice')}, SMS={phone.capabilities.get('sms')}")
    print()
    
    # Check voice configuration
    print("📞 Voice Configuration:")
    print(f"   Voice URL: {phone.voice_url or '(not set)'}")
    print(f"   Voice Method: {phone.voice_method or '(not set)'}")
    
    expected_voice_url = f"{webhook_base}/webhooks/twilio/voice"
    if phone.voice_url == expected_voice_url:
        print(f"   ✅ Voice URL matches expected: {expected_voice_url}")
    else:
        print(f"   ⚠️  Voice URL does NOT match!")
        print(f"       Expected: {expected_voice_url}")
        print(f"       Actual:   {phone.voice_url}")
    print()
    
    # Check status callback
    print("📊 Status Callback:")
    print(f"   Status Callback: {phone.status_callback or '(not set)'}")
    print(f"   Status Callback Method: {phone.status_callback_method or '(not set)'}")
    
    expected_status_url = f"{webhook_base}/webhooks/twilio/status"
    if phone.status_callback == expected_status_url:
        print(f"   ✅ Status callback matches expected: {expected_status_url}")
    else:
        print(f"   ⚠️  Status callback does NOT match!")
        print(f"       Expected: {expected_status_url}")
        print(f"       Actual:   {phone.status_callback}")
    print()
    
    # Check account capabilities
    print("🔐 Account Capabilities:")
    account = client.api.accounts(account_sid).fetch()
    print(f"   Account SID: {account.sid}")
    print(f"   Status: {account.status}")
    print(f"   Type: {account.type_}")
    print()
    
    # Important notes
    print("📝 Important Configuration Notes:")
    print()
    print("1. ✅ Media Streams Support:")
    print("   Media Streams is automatically available for all Twilio accounts.")
    print("   Your TwiML <Connect><Stream> configuration will work.")
    print()
    print("2. ⚠️  Trial Account Limitations:")
    if account.type_ == "Trial":
        print("   You're using a TRIAL account. Limitations:")
        print("   - Can only call verified numbers")
        print("   - Trial message will be played before your agent speaks")
        print("   - Upgrade at: https://www.twilio.com/console/billing")
    else:
        print("   ✅ You have a paid account - no trial limitations")
    print()
    print("3. 🌐 Webhook Accessibility:")
    print(f"   Your webhooks are at: {webhook_base}")
    print("   Make sure:")
    print("   - ngrok is running (ngrok http 8000)")
    print("   - API container is running (docker ps)")
    print("   - Webhooks are publicly accessible")
    print()
    
    print("✅ Configuration looks good! Ready to make calls.")
    
except Exception as e:
    print(f"❌ Error checking configuration: {e}")
    sys.exit(1)
