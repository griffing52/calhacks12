"""
Voice call initiation tool using LiveKit Agent Dispatch.
This tool initiates an outbound voice call to assist with customer support.

This is a synchronous wrapper around the Temporal activity for compatibility
with the dynamic tool execution system.
"""

import os
from typing import Dict

from dotenv import load_dotenv


def initiate_voice_call(args: Dict) -> Dict:
    """
    Initiate a voice call using LiveKit Agent Dispatch.
    
    This function serves as a synchronous wrapper that is called by the
    dynamic_tool_activity. The actual implementation is in activities/voice_activities.py
    which is registered as a Temporal activity.
    
    Args:
        args: Dictionary containing:
            - phone_number: str - Phone number to call (E.164 format, e.g., +1234567890)
            - goal: str - The purpose/goal of the call
            - context: str - Additional context about the user's issue
            - userConfirmation: str - User's confirmation to initiate the call
    
    Returns:
        Dictionary containing:
            - status: str - "success" or "error"
            - call_sid: str - Unique identifier for the call (dispatch ID)
            - message: str - Human-readable status message
            - error: str - Error message if status is "error"
    
    Note:
        When called from a Temporal workflow, this delegates to the activity.
        When called standalone (e.g., in tests), it executes directly.
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
    
    # Get LiveKit credentials from environment
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.com")
    
    # Check if we're in mock mode (no credentials provided)
    use_mock = not all([
        livekit_api_key,
        livekit_api_secret,
        livekit_url
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
    
    # Real implementation with LiveKit dispatch
    try:
        from livekit import api
        import json
        import asyncio
        
        # Initialize LiveKit API client
        lkapi = api.LiveKitAPI(
            url=livekit_url,
            api_key=livekit_api_key,
            api_secret=livekit_api_secret,
        )
        
        # Generate unique room name for this call
        import random
        import string
        room_name = "call-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Agent name from environment or default
        agent_name = os.getenv("LIVEKIT_AGENT_NAME", "outbound-caller")
        
        # Transfer number (the phone to actually call)
        from_number = phone_number
        
        # The phone number shown as caller (from environment)
        transfer_to = os.getenv("TWILIO_PHONE_NUMBER", "+13105825023")
        
        # Build metadata for the dispatch
        metadata = {
            "phone_number": from_number,  # The number calling FROM
            "transfer_to": transfer_to,    # The number to call TO
            "goal": goal,
            "context": context
        }
        
        # Create the agent dispatch - this initiates the call via LiveKit
        async def create_dispatch():
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room_name,
                    metadata=json.dumps(metadata)
                )
            )
            await lkapi.aclose()
            return dispatch
        
        # Run the async dispatch creation
        dispatch = asyncio.run(create_dispatch())
        
        return {
            "status": "success",
            "call_sid": dispatch.id,  # Use dispatch ID as call identifier
            "message": f"Voice call initiated successfully to {phone_number}",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "room_name": room_name,
            "dispatch_id": dispatch.id,
            "agent_name": agent_name
        }
        
    except ImportError:
        return {
            "status": "error",
            "error": "LiveKit SDK not installed. Run: pip install livekit",
            "message": "Failed to initiate call: missing dependencies"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to initiate voice call: {str(e)}"
        }
