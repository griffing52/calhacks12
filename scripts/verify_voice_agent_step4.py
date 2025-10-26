#!/usr/bin/env python3
"""
Verification script for Step 4: API Endpoint for Call Initiation

This script verifies that:
1. The voice initiate endpoint is defined in api/main.py
2. The endpoint accepts the correct request model
3. The endpoint creates a unique workflow ID
4. The endpoint uses the voice support goal
5. The endpoint constructs the initial prompt correctly
"""

import ast
import sys


def check_imports():
    """Check that required imports are present."""
    print("Checking imports...")

    with open("api/main.py", "r") as f:
        content = f.read()

    required_imports = [
        "import uuid",
        "from pydantic import BaseModel",
        "from goals.voice_agent import goal_voice_support",
    ]

    missing = []
    for imp in required_imports:
        if imp not in content:
            missing.append(imp)

    if missing:
        print("  ❌ Missing imports:")
        for imp in missing:
            print(f"     - {imp}")
        return False

    print("  ✅ All required imports present")
    return True


def check_request_model():
    """Check that VoiceInitiateRequest model is defined."""
    print("\nChecking request model...")

    with open("api/main.py", "r") as f:
        content = f.read()

    # Check for model definition
    if "class VoiceInitiateRequest(BaseModel):" not in content:
        print("  ❌ VoiceInitiateRequest model not found")
        return False

    # Check for required fields
    required_fields = ["phone_number", "goal", "context"]
    missing_fields = []

    for field in required_fields:
        if f"{field}:" not in content:
            missing_fields.append(field)

    if missing_fields:
        print("  ❌ Missing fields in VoiceInitiateRequest:")
        for field in missing_fields:
            print(f"     - {field}")
        return False

    print("  ✅ VoiceInitiateRequest model correctly defined")
    print(f"     Fields: {', '.join(required_fields)}")
    return True


def check_endpoint_definition():
    """Check that the voice-initiate endpoint is defined."""
    print("\nChecking endpoint definition...")

    with open("api/main.py", "r") as f:
        content = f.read()

    # Check for endpoint decorator and function
    if '@app.post("/api/v1/voice-initiate")' not in content:
        print("  ❌ Endpoint decorator not found")
        return False

    if "async def voice_initiate(" not in content:
        print("  ❌ Endpoint function not found")
        return False

    if "request: VoiceInitiateRequest" not in content:
        print("  ❌ Endpoint doesn't accept VoiceInitiateRequest")
        return False

    print("  ✅ Endpoint correctly defined")
    print('     Route: POST /api/v1/voice-initiate')
    print('     Function: async def voice_initiate(request: VoiceInitiateRequest)')
    return True


def check_workflow_creation():
    """Check that the endpoint creates workflow correctly."""
    print("\nChecking workflow creation logic...")

    with open("api/main.py", "r") as f:
        content = f.read()

    checks = [
        ('workflow_id = f"voice-call-{uuid.uuid4()}"', "Unique workflow ID generation"),
        ("agent_goal=goal_voice_support", "Uses voice support goal"),
        (
            "f\"Initiate voice call to {request.phone_number}",
            "Constructs prompt with phone number",
        ),
        ("with goal: {request.goal}", "Includes goal in prompt"),
        ("and context: {request.context}", "Includes context in prompt"),
        ("start_signal=\"user_prompt\"", "Uses user_prompt signal"),
    ]

    all_passed = True
    for check_string, description in checks:
        if check_string in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")
            all_passed = False

    return all_passed


def check_response_structure():
    """Check that the endpoint returns correct response."""
    print("\nChecking response structure...")

    with open("api/main.py", "r") as f:
        content = f.read()

    # Look for return statement in voice_initiate function
    if '"workflow_id": workflow_id' not in content:
        print("  ❌ Response missing workflow_id")
        return False

    response_fields = [
        '"workflow_id": workflow_id',
        '"message":',
        '"phone_number": request.phone_number',
        '"goal": request.goal',
        '"context": request.context',
    ]

    missing = []
    for field in response_fields:
        if field not in content:
            missing.append(field)

    if missing:
        print("  ❌ Missing response fields:")
        for field in missing:
            print(f"     - {field}")
        return False

    print("  ✅ Response structure correct")
    print("     Returns: workflow_id, message, phone_number, goal, context")
    return True


def check_error_handling():
    """Check that the endpoint has proper error handling."""
    print("\nChecking error handling...")

    with open("api/main.py", "r") as f:
        content = f.read()

    # Check for try-except blocks
    if "except TemporalError as e:" not in content:
        print("  ⚠️  Warning: No TemporalError handling in voice_initiate")
        return False

    if "except Exception as e:" not in content:
        print("  ⚠️  Warning: No generic exception handling in voice_initiate")
        return False

    if "raise HTTPException" not in content:
        print("  ⚠️  Warning: No HTTPException raised for errors")
        return False

    print("  ✅ Error handling implemented")
    print("     - TemporalError handling")
    print("     - Generic exception handling")
    print("     - HTTPException for API errors")
    return True


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Step 4 Verification: API Endpoint for Call Initiation")
    print("=" * 70)

    checks = [
        check_imports,
        check_request_model,
        check_endpoint_definition,
        check_workflow_creation,
        check_response_structure,
        check_error_handling,
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Check failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 70)
    print("Verification Summary")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total} checks")

    if all(results):
        print("\n✅ Step 4 verification PASSED!")
        print("\nThe voice initiate endpoint is correctly implemented.")
        print("\nNext steps:")
        print("  1. Start the Temporal server: docker compose up -d")
        print("  2. Start the worker: uv run python scripts/run_worker.py")
        print("  3. Start the API: uv run uvicorn api.main:app --reload")
        print("  4. Test the endpoint: uv run python scripts/test_voice_initiate_endpoint.py")
        return 0
    else:
        print("\n❌ Step 4 verification FAILED")
        print(f"\n{total - passed} check(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
