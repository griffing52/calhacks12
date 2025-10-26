"""
Voice call initiation tool using Twilio and LiveKit.
This tool initiates an outbound voice call to assist with customer support.
"""

import os
from typing import Dict

from dotenv import load_dotenv


def initiate_voice_call(args: Dict) -> Dict:
    """
    Initiate a voice call using Twilio and LiveKit.
    
    Args:
        args: Dictionary containing:
            - phone_number: str - Phone number to call (E.164 format, e.g., +1234567890)
            - goal: str - The purpose/goal of the call
            - context: str - Additional context about the user's issue
            - userConfirmation: str - User's confirmation to initiate the call
    
    Returns:
        Dictionary containing:
            - status: str - "success" or "error"
            - call_sid: str - Unique identifier for the call (Twilio Call SID)
            - message: str - Human-readable status message
            - error: str - Error message if status is "error"
    """
    load_dotenv(override=True)
    
    phone_number = args.get("phone_number")
    goal = args.get("goal")
    context = args.get("context", "")
    
    if not phone_number:
        return {
            "status": "error",
            "error": "Phone number is required",
            "message": "Failed to initiate call: missing phone number"
        }
    
    if not goal:
        return {
            "status": "error",
            "error": "Goal/reason for call is required",
            "message": "Failed to initiate call: missing goal"
        }
    
    # Get Twilio and LiveKit credentials from environment
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.com")
    
    # Check if we're in mock mode (no credentials provided)
    use_mock = not all([
        twilio_account_sid,
        twilio_auth_token,
        twilio_phone_number,
        livekit_api_key,
        livekit_api_secret
    ])
    
    if use_mock:
        # Return mock response for testing without actual API credentials
        import random
        import string
        
        mock_call_sid = "CA" + ''.join(random.choices(string.hexdigits.lower(), k=32))
        
        return {
            "status": "success",
            "call_sid": mock_call_sid,
            "message": f"[MOCK MODE] Voice call would be initiated to {phone_number} with goal: {goal}",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "mode": "mock"
        }
    
    # Real implementation with Twilio and LiveKit
    try:
        from twilio.rest import Client
        
        # Initialize Twilio client
        client = Client(twilio_account_sid, twilio_auth_token)
        
        # Create TwiML webhook URL that will handle the call
        # This should point to your server endpoint that serves TwiML
        # The endpoint will receive the goal and context as query parameters
        webhook_base_url = os.getenv(
            "VOICE_WEBHOOK_BASE_URL",
            "https://your-server.com/voice/twiml"
        )
        
        # Encode goal and context in the webhook URL
        import urllib.parse
        query_params = urllib.parse.urlencode({
            "goal": goal,
            "context": context,
            "livekit_url": livekit_url,
            "livekit_api_key": livekit_api_key
        })
        twiml_url = f"{webhook_base_url}?{query_params}"
        
        # Initiate the outbound call
        call = client.calls.create(
            to=phone_number,
            from_=twilio_phone_number,
            url=twiml_url,
            method="POST",
            status_callback=os.getenv("VOICE_STATUS_CALLBACK_URL"),
            status_callback_event=["initiated", "ringing", "answered", "completed"]
        )
        
        return {
            "status": "success",
            "call_sid": call.sid,
            "message": f"Voice call initiated successfully to {phone_number}",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "call_status": call.status
        }
        
    except ImportError:
        return {
            "status": "error",
            "error": "Twilio SDK not installed. Run: pip install twilio",
            "message": "Failed to initiate call: missing dependencies"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to initiate voice call: {str(e)}"
        }
