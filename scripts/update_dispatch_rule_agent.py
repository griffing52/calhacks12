#!/usr/bin/env python3
"""
Update SIP dispatch rule to add agent name via LiveKit API.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from livekit import api

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

async def main():
    """Update the dispatch rule to include agent name."""
    
    # Get dispatch rule ID from command line
    if len(sys.argv) < 2:
        print("Usage: python update_dispatch_rule_agent.py <DISPATCH_RULE_ID> [AGENT_NAME]")
        print("\nExample:")
        print("  python update_dispatch_rule_agent.py SDR_T9qGfmGCkiim voice-assistant")
        sys.exit(1)
    
    dispatch_rule_id = sys.argv[1]
    agent_name = sys.argv[2] if len(sys.argv) > 2 else "voice-assistant"
    
    print(f"Updating dispatch rule {dispatch_rule_id} with agent: {agent_name}")
    print(f"LiveKit URL: {LIVEKIT_URL}")
    
    # Initialize LiveKit API
    lkapi = api.LiveKitAPI(
        url=LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://"),
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    
    try:
        # List current dispatch rules to verify
        from livekit.protocol.sip import ListSIPDispatchRuleRequest
        
        print("\nCurrent dispatch rules:")
        list_request = ListSIPDispatchRuleRequest()
        response = await lkapi.sip.list_sip_dispatch_rule(list_request)
        rules = response.items
        for rule in rules:
            print(f"  - {rule.sip_dispatch_rule_id}: {rule.name} (Type: {rule.rule}, Agents: {rule.room_agent_dispatch})")
        
        # Update the dispatch rule with agent name
        from livekit.protocol.sip import (
            UpdateSIPDispatchRuleRequest,
            SIPDispatchRuleInfo,
            SIPDispatchRuleIndividual,
            RoomAgentDispatch,
        )
        
        # Create the agent dispatch configuration
        agent_dispatch = RoomAgentDispatch(
            agent_name=agent_name,
        )
        
        # Create update request
        # Note: We need to preserve the existing rule configuration
        # Find the existing rule first
        existing_rule = None
        for rule in rules:
            if rule.sip_dispatch_rule_id == dispatch_rule_id:
                existing_rule = rule
                break
        
        if not existing_rule:
            print(f"❌ Dispatch rule {dispatch_rule_id} not found!")
            await lkapi.aclose()
            return
        
        print(f"\nFound existing rule: {existing_rule.name}")
        print(f"  Type: {existing_rule.rule}")
        print(f"  Trunk IDs: {existing_rule.trunk_ids}")
        
        # Create updated rule info
        updated_rule = SIPDispatchRuleInfo(
            sip_dispatch_rule_id=dispatch_rule_id,
            name=existing_rule.name or "voice-agent-dispatch",
            trunk_ids=existing_rule.trunk_ids,
            rule=existing_rule.rule,  # Preserve the rule type (individual, direct, etc.)
            room_agent_dispatch=agent_dispatch,  # Add agent dispatch
        )
        
        # Send update request
        request = UpdateSIPDispatchRuleRequest(
            sip_dispatch_rule_id=dispatch_rule_id,
            name=updated_rule.name,
            trunk_ids=updated_rule.trunk_ids,
            rule=updated_rule.rule,
            room_agent_dispatch=agent_dispatch,
        )
        
        result = await lkapi.sip.update_sip_dispatch_rule(request)
        print(f"\n✅ Successfully updated dispatch rule!")
        print(f"   Rule ID: {result.sip_dispatch_rule_id}")
        print(f"   Name: {result.name}")
        print(f"   Agent: {agent_name}")
        
    except Exception as e:
        print(f"❌ Error updating dispatch rule: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
