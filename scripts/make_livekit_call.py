"""
Script to initiate an outbound call using LiveKit Agent Dispatch.

This replaces the previous Twilio-based call initiation with direct
LiveKit SIP dispatch, which automatically handles the SIP trunk integration.

Usage:
    python scripts/make_livekit_call.py --goal "password reset" --context "User locked out" --phone "+15555551234"
"""

import asyncio
import json
import os
import argparse
from dotenv import load_dotenv
from livekit import api

load_dotenv()

# Get LiveKit configuration from environment
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "outbound-caller")

# Default from/to numbers
DEFAULT_FROM_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+13105825023")
DEFAULT_TO_NUMBER = "+13109388969"


async def create_dispatch_call(goal: str, context: str = "", phone_number: str = None):
    """
    Create a LiveKit agent dispatch to initiate an outbound call.
    
    Args:
        goal: Purpose of the call (e.g., "password reset assistance")
        context: Additional context about the user's issue
        phone_number: Phone number to call (defaults to DEFAULT_TO_NUMBER)
    """
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        print("❌ Error: Missing LiveKit credentials in .env file")
        print("   Required: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")
        return
    
    # Use provided phone number or default
    transfer_to = phone_number or DEFAULT_TO_NUMBER
    
    # Initialize LiveKit API client
    lkapi = api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    
    # Generate unique room name for this call
    import random
    import string
    room_name = "call-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    # Build metadata for the dispatch
    # This metadata will be passed to the agent
    metadata = {
        "phone_number": DEFAULT_FROM_NUMBER,  # Number calling FROM (shown to recipient)
        "transfer_to": transfer_to,           # Number to call TO (recipient)
        "goal": goal,
        "context": context
    }
    
    print(f"\n🚀 Creating LiveKit Agent Dispatch:")
    print(f"   Agent: {LIVEKIT_AGENT_NAME}")
    print(f"   Room: {room_name}")
    print(f"   From: {DEFAULT_FROM_NUMBER}")
    print(f"   To: {transfer_to}")
    print(f"   Goal: {goal}")
    print(f"   Context: {context}")
    print(f"\n   Metadata: {json.dumps(metadata, indent=2)}")
    
    try:
        # Create the agent dispatch - this initiates the call via LiveKit SIP
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=LIVEKIT_AGENT_NAME,
                room=room_name,
                metadata=json.dumps(metadata)
            )
        )
        
        print(f"\n✅ Dispatch created successfully!")
        print(f"   Dispatch ID: {dispatch.id}")
        print(f"   Room: {dispatch.room}")
        
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


def main():
    parser = argparse.ArgumentParser(
        description="Initiate an outbound call using LiveKit Agent Dispatch"
    )
    parser.add_argument(
        "--goal",
        type=str,
        default="",
        help="Purpose of the call (e.g., 'password reset assistance')"
    )
    parser.add_argument(
        "--context",
        type=str,
        default="",
        help="Additional context about the user's issue"
    )
    parser.add_argument(
        "--phone",
        type=str,
        default=None,
        help=f"Phone number to call (default: {DEFAULT_TO_NUMBER})"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  LiveKit Agent Dispatch Call Initiator")
    print("="*60)
    
    asyncio.run(create_dispatch_call(
        goal=args.goal,
        context=args.context,
        phone_number=args.phone
    ))
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
