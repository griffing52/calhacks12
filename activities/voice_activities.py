"""
Voice Activities for Temporal Workflows
Handles voice call initiation via Twilio and LiveKit integration
"""

import os
import random
import string
from typing import Dict, Any

from dotenv import load_dotenv
from temporalio import activity

load_dotenv(override=True)


@activity.defn
async def initiate_voice_call_activity(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Temporal Activity to initiate a voice call using Twilio and LiveKit.
    
    This activity is registered as a Temporal activity and can be called from workflows
    to initiate outbound voice calls for customer support.
    
    Args:
        args: Dictionary containing:
            - phone_number (str): Phone number in E.164 format (e.g., +14155551234)
            - goal (str): Purpose of the call (e.g., "password reset")
            - context (str): Additional information about the user's issue
            - userConfirmation (str): User's consent to initiate the call
    
    Returns:
        Dictionary with call status and details:
        - status: "success" or "error"
        - call_sid: Unique call identifier
        - message: Human-readable status message
        - Additional metadata (phone_number, goal, context, etc.)
    
    Note:
        This is a STUB IMPLEMENTATION for demonstration purposes.
        In production, this would use the Twilio SDK to make actual API calls.
        The full Twilio/LiveKit integration requires:
        1. Installing twilio SDK: pip install twilio
        2. Setting environment variables (TWILIO_ACCOUNT_SID, etc.)
        3. Implementing the actual API calls (see tools/initiate_voice_call.py)
    """
    activity.logger.info(f"Voice call activity started with args: {args}")
    
    phone_number = args.get("phone_number")
    goal = args.get("goal")
    context = args.get("context", "")
    
    # Validation
    if not phone_number:
        activity.logger.error("Phone number is required")
        return {
            "status": "error",
            "error": "Phone number is required",
            "message": "Failed to initiate call: missing phone number"
        }
    
    if not goal:
        activity.logger.error("Goal/reason for call is required")
        return {
            "status": "error",
            "error": "Goal/reason for call is required",
            "message": "Failed to initiate call: missing goal"
        }
    
    # Get credentials from environment
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.com")
    
    # Check if we have all required credentials
    has_credentials = all([
        twilio_account_sid,
        twilio_auth_token,
        twilio_phone_number,
        livekit_api_key,
        livekit_api_secret
    ])
    
    if not has_credentials:
        # STUB MODE - No actual API calls
        activity.logger.info(
            f"Running in STUB mode (no credentials). "
            f"Would call {phone_number} for goal: {goal}"
        )
        
        # Generate a mock Call SID
        mock_call_sid = "CA" + ''.join(random.choices(string.hexdigits.lower(), k=32))
        
        # Print stub message as requested
        stub_message = f"Calling {phone_number} to fulfill goal: {goal}"
        activity.logger.info(stub_message)
        print(f"[STUB] {stub_message}")
        
        return {
            "status": "success",
            "call_sid": mock_call_sid,
            "message": f"[STUB MODE] {stub_message}",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "mode": "stub",
            "note": "This is a stub implementation. Set TWILIO_* and LIVEKIT_* environment variables for production mode."
        }
    
    # PRODUCTION MODE - Actual Twilio API integration
    # NOTE: This requires the twilio package to be installed: pip install twilio
    activity.logger.info(
        f"Running in PRODUCTION mode. Initiating real call to {phone_number}"
    )
    
    try:
        # Import Twilio SDK (only when credentials are available)
        from twilio.rest import Client
        
        # Initialize Twilio client
        client = Client(twilio_account_sid, twilio_auth_token)
        
        # Build webhook URL with metadata
        webhook_base_url = os.getenv(
            "VOICE_WEBHOOK_BASE_URL",
            "https://your-server.com/voice/twiml"
        )
        
        import urllib.parse
        query_params = urllib.parse.urlencode({
            "goal": goal,
            "context": context,
            "livekit_url": livekit_url,
            "livekit_api_key": livekit_api_key
        })
        twiml_url = f"{webhook_base_url}?{query_params}"
        
        activity.logger.info(f"Calling Twilio API with webhook URL: {webhook_base_url}")
        
        # Make the actual Twilio API call
        call = client.calls.create(
            to=phone_number,
            from_=twilio_phone_number,
            url=twiml_url,
            method="POST",
            status_callback=os.getenv("VOICE_STATUS_CALLBACK_URL"),
            status_callback_event=["initiated", "ringing", "answered", "completed"]
        )
        
        activity.logger.info(
            f"Successfully initiated call. Call SID: {call.sid}, Status: {call.status}"
        )
        
        return {
            "status": "success",
            "call_sid": call.sid,
            "message": f"Voice call initiated successfully to {phone_number}",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "call_status": call.status,
            "mode": "production",
            "twilio_account_sid": twilio_account_sid[-4:],  # Last 4 chars for verification
        }
        
    except ImportError as e:
        activity.logger.error("Twilio SDK not installed")
        return {
            "status": "error",
            "error": "Twilio SDK not installed. Run: pip install twilio",
            "message": "Failed to initiate call: missing dependencies"
        }
    except Exception as e:
        activity.logger.error(f"Failed to initiate call: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to initiate voice call: {str(e)}",
            "error_type": type(e).__name__
        }


# Alias for backward compatibility with the existing tool implementation
# This allows the activity to be called either way
async def voice_call_activity(args: Dict[str, Any]) -> Dict[str, Any]:
    """Alias for initiate_voice_call_activity"""
    return await initiate_voice_call_activity(args)
