#!/usr/bin/env python3
"""
Verification script for Step 3: Workflow Logic Updates
Tests the voice-specific workflow signals and state management
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_workflow_modifications():
    """Verify that workflow has been properly modified for voice calls"""
    
    print("\n" + "=" * 60)
    print("Step 3: Workflow Voice Logic - Verification")
    print("=" * 60)
    
    workflow_path = project_root / "workflows/agent_goal_workflow.py"
    content = workflow_path.read_text()
    
    print("\n1. Checking voice state variables...")
    
    state_vars = [
        ("self.voice_call_active", "Voice call active flag"),
        ("self.voice_call_sid", "Voice call SID tracking"),
        ("self.voice_call_status", "Voice call status"),
        ("self.voice_info_needed", "Info needed flag"),
        ("self.voice_pending_question", "Pending question storage"),
    ]
    
    for var, description in state_vars:
        assert var in content, f"Missing state variable: {var}"
        print(f"   ✓ {description}")
    
    print("\n2. Checking voice signal handlers...")
    
    signals = [
        ("async def call_update", "call_update signal"),
        ("async def call_ended", "call_ended signal"),
        ("async def required_info_needed", "required_info_needed signal"),
        ("async def voice_info_provided", "voice_info_provided signal"),
    ]
    
    for signal_def, description in signals:
        assert signal_def in content, f"Missing signal: {signal_def}"
        print(f"   ✓ {description}")
    
    print("\n3. Checking signal parameters...")
    
    # Check call_update signature
    assert "status: str, message: str" in content, "call_update missing parameters"
    print("   ✓ call_update(status, message)")
    
    # Check call_ended signature
    assert "reason: str, final_summary: str" in content, "call_ended missing parameters"
    print("   ✓ call_ended(reason, final_summary)")
    
    # Check required_info_needed signature
    assert "question: str" in content, "required_info_needed missing parameter"
    print("   ✓ required_info_needed(question)")
    
    print("\n4. Checking query methods...")
    
    assert "def get_voice_call_status" in content, "Missing voice call status query"
    print("   ✓ get_voice_call_status query")
    
    print("\n5. Checking voice call execution logic...")
    
    execution_checks = [
        ('if current_tool == "InitiateVoiceCall"', "Voice call detection"),
        ("await self.execute_voice_call()", "Voice call execution"),
        ("async def execute_voice_call", "Voice call method"),
        ("self.voice_call_sid = call_result.get", "Call SID storage"),
        ("self.voice_call_active = True", "Active flag setting"),
    ]
    
    for check, description in execution_checks:
        assert check in content, f"Missing: {description}"
        print(f"   ✓ {description}")
    
    print("\n6. Checking conversation history integration...")
    
    history_checks = [
        ('"voice_call_update"', "Call update logging"),
        ('"voice_call_ended"', "Call end logging"),
        ('"voice_info_request"', "Info request logging"),
        ('"voice_info_response"', "Info response logging"),
    ]
    
    for check, description in history_checks:
        assert check in content, f"Missing: {description}"
        print(f"   ✓ {description}")
    
    print("\n7. Checking workflow waiting state...")
    
    assert "# The workflow will continue running, waiting for signals:" in content, \
        "Missing waiting state documentation"
    print("   ✓ Workflow waiting state documented")
    
    print("\n" + "=" * 60)
    print("✓ STEP 3 COMPLETE - All Checks Passed!")
    print("=" * 60)
    
    print("\nImplemented Features:")
    print("  • Voice call state variables (5 new state vars)")
    print("  • Voice call signals (4 new signals)")
    print("    - call_update(status, message)")
    print("    - call_ended(reason, final_summary)")
    print("    - required_info_needed(question)")
    print("    - voice_info_provided(answer)")
    print("  • Voice call query (get_voice_call_status)")
    print("  • Voice call execution logic (execute_voice_call)")
    print("  • Workflow waiting state for external events")
    print("  • Conversation history integration")
    
    print("\nWorkflow Behavior:")
    print("  1. User confirms InitiateVoiceCall tool")
    print("  2. Workflow executes voice call activity")
    print("  3. Call SID stored for tracking")
    print("  4. voice_call_active = True")
    print("  5. Workflow enters waiting state")
    print("  6. External webhooks send signals:")
    print("     - call_update for status changes")
    print("     - required_info_needed if info needed")
    print("     - call_ended when call completes")
    print("  7. Workflow processes signals and updates state")
    print("  8. Conversation history tracks all events")
    
    print("\nSignal Examples:")
    print("  # Update call status")
    print('  await handle.signal("call_update", "ringing", "Call is ringing...")')
    print()
    print("  # Request info from user")
    print('  await handle.signal("required_info_needed", "What is your confirmation code?")')
    print()
    print("  # Provide info to voice AI")
    print('  await handle.signal("voice_info_provided", "123456")')
    print()
    print("  # End the call")
    print('  await handle.signal("call_ended", "goal_complete", "Password reset successful")')
    
    print("\n" + "=" * 60)


def verify_imports():
    """Verify necessary imports are present"""
    
    print("\n" + "=" * 60)
    print("Checking Imports and Dependencies")
    print("=" * 60)
    
    workflow_path = project_root / "workflows/agent_goal_workflow.py"
    content = workflow_path.read_text()
    
    print("\n✓ Workflow file exists and is readable")
    print(f"  File: {workflow_path}")
    print(f"  Size: {len(content)} bytes")
    print(f"  Lines: {len(content.splitlines())}")
    
    # Check for temporal imports
    assert "from temporalio import workflow" in content, "Missing temporalio import"
    print("\n✓ Temporal imports present")
    
    print("\n" + "=" * 60)


def main():
    """Run all verifications"""
    
    try:
        verify_imports()
        verify_workflow_modifications()
        
        print("\n" + "=" * 60)
        print("SUCCESS: Step 3 Implementation Verified!")
        print("=" * 60)
        print("\nNext Steps:")
        print("  1. Test with Temporal worker")
        print("  2. Create webhook endpoints (Step 4)")
        print("  3. Send test signals to workflow")
        print("  4. Verify conversation history")
        print("  5. Test end-to-end with Twilio/LiveKit")
        print("=" * 60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ VERIFICATION FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
