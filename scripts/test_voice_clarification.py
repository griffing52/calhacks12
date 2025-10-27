#!/usr/bin/env python3
"""
Test script to simulate a voice call where the agent needs clarification.

This demonstrates the workflow signal flow:
1. Start a voice call workflow
2. Simulate the agent needing information (required_info_needed signal)
3. User provides answer via UI (voice_info_provided signal)
4. Agent continues with the call
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from temporalio.client import Client
from workflows.agent_goal_workflow import AgentGoalWorkflow


async def main():
    """Demonstrate the voice clarification flow."""
    
    # Get workflow ID from command line or use a test ID
    if len(sys.argv) > 1:
        workflow_id = sys.argv[1]
    else:
        print("Usage: python test_voice_clarification.py <workflow_id>")
        print("\nOr run without args to see example signals:")
        print("\n=== Example Workflow Signals for Voice Clarification ===\n")
        print("1. Agent needs clarification during call:")
        print("   await handle.signal(AgentGoalWorkflow.required_info_needed, 'What is your account number?')")
        print()
        print("2. User provides answer via UI:")
        print("   await handle.signal(AgentGoalWorkflow.voice_info_provided, '12345678')")
        print()
        print("3. Call status updates:")
        print("   await handle.signal(AgentGoalWorkflow.call_update, 'in_progress', 'Call connected')")
        print()
        print("4. Call ends:")
        print("   await handle.signal(AgentGoalWorkflow.call_ended, 'goal_complete', 'Account verified successfully')")
        print()
        print("\n=== Query Voice Call Status ===\n")
        print("   status = await handle.query(AgentGoalWorkflow.get_voice_call_status)")
        print("   # Returns: {")
        print("   #   'active': True/False,")
        print("   #   'call_sid': 'CA123...',")
        print("   #   'status': 'in_progress',")
        print("   #   'info_needed': True/False,")
        print("   #   'pending_question': 'What is...?' or None")
        print("   # }")
        print()
        return
    
    # Connect to Temporal
    client = await Client.connect("localhost:7233")
    
    # Get workflow handle
    handle = client.get_workflow_handle(workflow_id)
    
    print(f"🔍 Testing workflow: {workflow_id}\n")
    
    # Get current status
    try:
        voice_status = await handle.query(AgentGoalWorkflow.get_voice_call_status)
        print("📊 Current Voice Call Status:")
        print(f"   Active: {voice_status['active']}")
        print(f"   Call SID: {voice_status['call_sid']}")
        print(f"   Status: {voice_status['status']}")
        print(f"   Info Needed: {voice_status['info_needed']}")
        print(f"   Pending Question: {voice_status['pending_question']}")
        print()
    except Exception as e:
        print(f"⚠️  Could not query status: {e}\n")
    
    # Interactive menu
    print("=== Actions ===")
    print("1. Simulate agent needs clarification")
    print("2. Provide answer to pending question")
    print("3. Update call status")
    print("4. End call")
    print("5. Query current status")
    print("0. Exit")
    
    choice = input("\nEnter choice: ").strip()
    
    if choice == "1":
        question = input("Enter question from agent: ").strip()
        if question:
            await handle.signal(AgentGoalWorkflow.required_info_needed, question)
            print(f"✅ Sent clarification request: {question}")
    
    elif choice == "2":
        answer = input("Enter answer: ").strip()
        if answer:
            await handle.signal(AgentGoalWorkflow.voice_info_provided, answer)
            print(f"✅ Sent answer: {answer}")
    
    elif choice == "3":
        status = input("Enter status (initiated/ringing/in_progress/completed): ").strip()
        message = input("Enter message: ").strip()
        if status and message:
            await handle.signal(AgentGoalWorkflow.call_update, status, message)
            print(f"✅ Updated call status: {status}")
    
    elif choice == "4":
        reason = input("Enter reason (goal_complete/caller_hung_up/error): ").strip()
        summary = input("Enter summary: ").strip()
        if reason and summary:
            await handle.signal(AgentGoalWorkflow.call_ended, reason, summary)
            print(f"✅ Ended call: {reason}")
    
    elif choice == "5":
        voice_status = await handle.query(AgentGoalWorkflow.get_voice_call_status)
        print("\n📊 Voice Call Status:")
        for key, value in voice_status.items():
            print(f"   {key}: {value}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
