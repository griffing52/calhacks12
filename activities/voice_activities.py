"""
Voice Activities for Temporal Workflows
Handles voice call initiation via LiveKit Agent Dispatch
"""

import os
import uuid
from typing import Dict, Any

from dotenv import load_dotenv
from temporalio import activity

load_dotenv(override=True)


@activity.defn
async def initiate_voice_call_activity(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Temporal Activity to initiate a voice call using LiveKit Agent Dispatch.
    
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
        - call_sid: Unique call identifier (dispatch ID)
        - message: Human-readable status message
        - Additional metadata (phone_number, goal, context, room_name, etc.)
    
    Note:
        Uses LiveKit Agent Dispatch to initiate calls via SIP.
        Requires LiveKit credentials (LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL).
        Falls back to STUB mode if credentials are not provided.
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
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.com")
    
    # Check if we have all required credentials
    has_credentials = all([
        livekit_api_key,
        livekit_api_secret,
        livekit_url
    ])
    
    if not has_credentials:
        # STUB MODE - No actual API calls
        activity.logger.info(
            f"Running in STUB mode (no credentials). "
            f"Would call {phone_number} for goal: {goal}"
        )
        
        # Generate a fake Call SID using uuid
        fake_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        # Print stub message as requested
        stub_message = f"Calling {phone_number} to fulfill goal: {goal}"
        activity.logger.info(stub_message)
        print(f"[STUB] {stub_message}")
        
        # Return Call SID immediately so workflow can track it
        return {
            "status": "success",
            "call_sid": fake_sid,  # Important!
            "message": f"[STUB] Calling {phone_number}...",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "mode": "stub",
            "note": "This is a stub implementation. Set TWILIO_* and LIVEKIT_* environment variables for production mode."
        }
    
    # PRODUCTION MODE - Actual LiveKit Agent Dispatch
    # NOTE: This requires the livekit package to be installed: pip install livekit
    activity.logger.info(
        f"Running in PRODUCTION mode. Initiating real call to {phone_number} via LiveKit"
    )
    
    try:
        # Import LiveKit SDK (only when credentials are available)
        from livekit import api
        import json
        import random
        import string
        
        # Initialize LiveKit API client
        lkapi = api.LiveKitAPI(
            url=livekit_url,
            api_key=livekit_api_key,
            api_secret=livekit_api_secret,
        )
        
        # Generate unique room name for this call
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
        
        activity.logger.info(f"Creating LiveKit dispatch with agent: {agent_name}, room: {room_name}")
        activity.logger.info(f"Metadata: {metadata}")
        
        # Create the agent dispatch - this initiates the call via LiveKit
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=json.dumps(metadata)
            )
        )
        
        await lkapi.aclose()
        
        activity.logger.info(
            f"Successfully created dispatch. Dispatch ID: {dispatch.id}, Room: {room_name}"
        )
        
        # Return dispatch ID as call_sid for tracking
        return {
            "status": "success",
            "call_sid": dispatch.id,  # Important! Use dispatch ID as identifier
            "message": f"Voice call initiated to {phone_number}",
            "phone_number": phone_number,
            "goal": goal,
            "context": context,
            "room_name": room_name,
            "dispatch_id": dispatch.id,
            "agent_name": agent_name,
            "mode": "production",
        }
        
    except ImportError as e:
        activity.logger.error("LiveKit SDK not installed")
        return {
            "status": "error",
            "error": "LiveKit SDK not installed. Run: pip install livekit",
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
