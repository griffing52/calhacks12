#!/usr/bin/env python3
"""
Simple demonstration of the voice call activity
Shows both stub and production mode behavior
"""

import asyncio
import os


async def demo_stub_mode():
    """Demonstrate the activity in stub mode"""
    
    print("\n" + "=" * 60)
    print("DEMO: Voice Call Activity - Stub Mode")
    print("=" * 60)
    
    # Import the activity
    from activities.voice_activities import initiate_voice_call_activity
    
    # Clear credentials to ensure stub mode
    for var in ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
                "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]:
        os.environ.pop(var, None)
    
    # Call the activity
    print("\nCalling activity with:")
    print("  Phone: +14155551234")
    print("  Goal: Help user reset their password")
    print("  Context: User forgot security questions\n")
    
    result = await initiate_voice_call_activity({
        "phone_number": "+14155551234",
        "goal": "Help user reset their password",
        "context": "User forgot security questions",
        "userConfirmation": "yes"
    })
    
    print("\nActivity Result:")
    print(f"  Status: {result['status']}")
    print(f"  Mode: {result['mode']}")
    print(f"  Call SID: {result['call_sid']}")
    print(f"  Message: {result['message']}")
    
    print("\n" + "=" * 60)
    print("✓ Stub mode demonstration complete!")
    print("=" * 60)
    print("\nKey Points:")
    print("  • No Twilio credentials needed")
    print("  • Prints stub message to console")
    print("  • Returns dummy Call SID (starts with 'CA')")
    print("  • Perfect for development and testing")
    print("\nTo enable production mode:")
    print("  1. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")
    print("  2. Set LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL")
    print("  3. Install Twilio SDK: uv add twilio")
    print("  4. Re-run this demo")
    print("=" * 60 + "\n")


async def main():
    """Run the demonstration"""
    await demo_stub_mode()


if __name__ == "__main__":
    asyncio.run(main())
