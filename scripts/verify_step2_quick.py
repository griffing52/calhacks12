#!/usr/bin/env python3
"""
Lightweight verification for Step 2 - checks file structure and code patterns
without requiring full dependency installation
"""

from pathlib import Path


def main():
    print("\n" + "=" * 60)
    print("Step 2: Voice Activity - Quick Verification")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent
    
    # Check files exist
    print("\n1. Checking required files...")
    
    voice_activities = project_root / "activities/voice_activities.py"
    activities_init = project_root / "activities/__init__.py"
    worker_script = project_root / "scripts/run_worker.py"
    
    assert voice_activities.exists(), "Missing activities/voice_activities.py"
    print("   ✓ activities/voice_activities.py exists")
    
    assert activities_init.exists(), "Missing activities/__init__.py"
    print("   ✓ activities/__init__.py exists")
    
    # Check voice_activities.py content
    print("\n2. Verifying voice_activities.py implementation...")
    
    content = voice_activities.read_text()
    
    checks = [
        ("@activity.defn", "Activity decorator present"),
        ("async def initiate_voice_call_activity", "Activity function defined"),
        ("args: Dict[str, Any]", "Correct function signature"),
        ("activity.logger.info", "Activity logging implemented"),
        ("Calling {phone_number} to fulfill goal: {goal}", "Stub message present"),
        ('print(f"[STUB] {stub_message}")', "Stub print statement"),
        ('"mode": "stub"', "Stub mode indicator"),
        ('"mode": "production"', "Production mode support"),
        ("from twilio.rest import Client", "Twilio integration ready"),
        ("TWILIO_ACCOUNT_SID", "Twilio env var check"),
        ("LIVEKIT_API_KEY", "LiveKit env var check"),
    ]
    
    for check_string, description in checks:
        assert check_string in content, f"Missing: {description}"
        print(f"   ✓ {description}")
    
    # Check activities/__init__.py
    print("\n3. Verifying activities/__init__.py exports...")
    
    init_content = activities_init.read_text()
    
    assert "from .voice_activities import" in init_content, "Missing voice_activities import"
    print("   ✓ Voice activities imported")
    
    assert "initiate_voice_call_activity" in init_content, "Missing activity export"
    print("   ✓ Activity exported")
    
    # Check worker registration
    print("\n4. Verifying worker registration...")
    
    worker_content = worker_script.read_text()
    
    assert "from activities.voice_activities import initiate_voice_call_activity" in worker_content, \
        "Worker missing voice activity import"
    print("   ✓ Worker imports voice activity")
    
    assert "initiate_voice_call_activity," in worker_content, \
        "Worker missing activity registration"
    print("   ✓ Worker registers voice activity")
    
    # Success!
    print("\n" + "=" * 60)
    print("✓ STEP 2 COMPLETE - All Checks Passed!")
    print("=" * 60)
    print("\nWhat was implemented:")
    print("  • Temporal activity: initiate_voice_call_activity")
    print("  • Decorated with @activity.defn")
    print("  • Stub mode: prints message + returns dummy Call SID")
    print("  • Production mode: uses Twilio SDK for real calls")
    print("  • Registered in worker (scripts/run_worker.py)")
    print("  • Exported from activities module")
    print("\nStub Implementation:")
    print('  Prints: "[STUB] Calling {phone_number} to fulfill goal: {goal}"')
    print('  Returns: {"status": "success", "call_sid": "CA...", "mode": "stub"}')
    print("\nTo test with full dependencies:")
    print("  uv run python scripts/verify_voice_agent_step2.py")
    print("\n" + "=" * 60)
    
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except AssertionError as e:
        print(f"\n✗ CHECK FAILED: {e}\n")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
