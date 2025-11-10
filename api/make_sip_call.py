"""
LiveKit Agent Dispatch Call Initiator

This module demonstrates how to initiate outbound calls using LiveKit's
Agent Dispatch API. It replaces the previous Twilio-based approach.

Usage:
    python api/make_sip_call.py

Configuration:
    Set the following in your .env file:
    - LIVEKIT_URL: Your LiveKit server URL
    - LIVEKIT_API_KEY: Your LiveKit API key
    - LIVEKIT_API_SECRET: Your LiveKit API secret
    - LIVEKIT_AGENT_NAME: Name of your deployed agent (default: "outbound-caller")
    - TWILIO_PHONE_NUMBER: The phone number to call FROM (shown to recipient)

The dispatch will:
    1. Create a unique room for the call
    2. Dispatch the specified agent to that room
    3. The agent will initiate an outbound call via SIP trunk
    4. Pass goal and context metadata to the agent for conversation handling
"""

from livekit import api
import json
import asyncio
import os
import random
import string
from dotenv import load_dotenv

load_dotenv("../.env")

# Get configuration from environment
livekit_url = os.getenv("LIVEKIT_URL")
livekit_api_key = os.getenv("LIVEKIT_API_KEY")
livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
agent_name = os.getenv("LIVEKIT_AGENT_NAME", "outbound-caller")

# Phone numbers
from_number = os.getenv("TWILIO_PHONE_NUMBER", "+13105825023")  # Number calling FROM
to_number = "+13109388969"  # Number to call TO (recipient)


async def create_dispatch_call(goal: str, context: str = "", callee_number: str = None):
    """
    Create a LiveKit agent dispatch to initiate an outbound call.
    
    Args:
        goal: Purpose of the call (e.g., "password reset assistance")
        context: Additional context about the user's issue
        callee_number: Phone number to call (defaults to to_number above)
    
    Returns:
        Dictionary with dispatch details
    """
    if not all([livekit_url, livekit_api_key, livekit_api_secret]):
        print("❌ Error: Missing LiveKit credentials in .env file")
        print("   Required: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")
        return None
    
    # Initialize LiveKit API client
    lkapi = api.LiveKitAPI(
        url=livekit_url,
        api_key=livekit_api_key,
        api_secret=livekit_api_secret,
    )
    
    # Generate unique room name for this call
    room_name = "call-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    # Use provided transfer_to or default
    recipient = callee_number or to_number
    
    # Build metadata for the dispatch
    # This metadata will be passed to the agent
    metadata = {
        "phone_number": recipient,  # Number calling FROM (shown to recipient)
        "transfer_to": from_number,     # Number to call TO (recipient)
        "goal": goal,
        "context": context
    }
    
    print(f"\n🚀 Creating LiveKit Agent Dispatch:")
    print(f"   Agent: {agent_name}")
    print(f"   Room: {room_name}")
    print(f"   From: {from_number}")
    print(f"   To: {recipient}")
    print(f"   Goal: {goal}")
    print(f"   Context: {context}")
    
    try:
        # Create the agent dispatch - this initiates the call via LiveKit SIP
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=json.dumps(metadata)
            )
        )
        
        print(f"\n✅ Dispatch created successfully!")
        print(f"   Dispatch ID: {dispatch.id}")
        print(f"   Room: {dispatch.room}")
        print(f"   Agent: {dispatch.agent_name}")
        
        # List all dispatches in this room to verify
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
        print(f"\n📊 Total dispatches in room '{room_name}': {len(dispatches)}")
        
        await lkapi.aclose()
        
        return {
            "dispatch_id": dispatch.id,
            "room_name": room_name,
            "status": "success"
        }
        
    except Exception as e:
        print(f"\n❌ Error creating dispatch: {str(e)}")
        import traceback
        traceback.print_exc()
        await lkapi.aclose()
        return None


# Main execution
if __name__ == "__main__":
    print("\n" + "="*70)
    print("  LiveKit Agent Dispatch - Outbound Call Initiator")
    print("="*70)
    
    # Example call - customize these parameters
    goal = "Help customer with password reset"
    context = "Customer is locked out of their account and needs assistance"
    
    asyncio.run(create_dispatch_call(goal=goal, context=context))
    
    print("\n" + "="*70)