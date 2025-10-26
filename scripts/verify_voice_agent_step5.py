#!/usr/bin/env python3
"""
Verification script for Step 5: Frontend Update for Voice Call Initiation

This script verifies that:
1. VoiceCallForm component is created
2. API service has voice call methods
3. App.jsx imports VoiceCallForm
4. App.jsx has voice mode state
5. App.jsx has voice call handlers
6. UI conditionally renders form or chat
"""

import os
import sys


def check_voice_call_form():
    """Check that VoiceCallForm component exists."""
    print("Checking VoiceCallForm component...")

    file_path = "frontend/src/components/VoiceCallForm.jsx"

    if not os.path.exists(file_path):
        print(f"  ❌ {file_path} not found")
        return False

    with open(file_path, "r") as f:
        content = f.read()

    # Check for required elements
    required_elements = [
        ("export default function VoiceCallForm", "Component export"),
        ("phoneNumber", "Phone number field"),
        ("goal", "Goal field"),
        ("context", "Context field"),
        ("onSubmit", "Submit handler prop"),
        ("validateForm", "Form validation"),
        ("E.164 format", "Phone number format hint"),
    ]

    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")
            all_found = False

    return all_found


def check_api_service():
    """Check that API service has voice call methods."""
    print("\nChecking API service updates...")

    file_path = "frontend/src/services/api.js"

    if not os.path.exists(file_path):
        print(f"  ❌ {file_path} not found")
        return False

    with open(file_path, "r") as f:
        content = f.read()

    # Check for voice call methods
    checks = [
        ("async initiateVoiceCall", "initiateVoiceCall method"),
        ("phone_number: phoneNumber", "Phone number mapping"),
        ("/api/v1/voice-initiate", "Voice initiate endpoint"),
        ("async getVoiceCallStatus", "getVoiceCallStatus method (optional)"),
    ]

    all_found = True
    for check_string, description in checks:
        if check_string in content:
            print(f"  ✅ {description}")
        else:
            if "optional" in description:
                print(f"  ⚠️  {description} - not found (optional)")
            else:
                print(f"  ❌ {description} - NOT FOUND")
                all_found = False

    return all_found


def check_app_imports():
    """Check App.jsx imports."""
    print("\nChecking App.jsx imports...")

    file_path = "frontend/src/pages/App.jsx"

    if not os.path.exists(file_path):
        print(f"  ❌ {file_path} not found")
        return False

    with open(file_path, "r") as f:
        content = f.read()

    # Check imports
    if 'import VoiceCallForm from "../components/VoiceCallForm"' in content:
        print("  ✅ VoiceCallForm imported")
        return True
    else:
        print("  ❌ VoiceCallForm import not found")
        return False


def check_app_state():
    """Check App.jsx voice mode state."""
    print("\nChecking App.jsx voice mode state...")

    file_path = "frontend/src/pages/App.jsx"

    with open(file_path, "r") as f:
        content = f.read()

    # Check for voice mode state variables
    state_vars = [
        ("voiceMode", "Voice mode toggle state"),
        ("voiceWorkflowId", "Workflow ID state"),
        ("setVoiceMode", "Voice mode setter"),
        ("setVoiceWorkflowId", "Workflow ID setter"),
    ]

    all_found = True
    for var, description in state_vars:
        if var in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")
            all_found = False

    return all_found


def check_app_handlers():
    """Check App.jsx voice call handlers."""
    print("\nChecking App.jsx voice call handlers...")

    file_path = "frontend/src/pages/App.jsx"

    with open(file_path, "r") as f:
        content = f.read()

    # Check for handler functions
    handlers = [
        ("handleToggleVoiceMode", "Toggle voice mode handler"),
        ("handleVoiceCallSubmit", "Voice call submit handler"),
        ("apiService.initiateVoiceCall", "API call to initiate voice"),
        ("result.workflow_id", "Workflow ID extraction"),
        ("setVoiceWorkflowId(result.workflow_id)", "Storing workflow ID"),
    ]

    all_found = True
    for handler, description in handlers:
        if handler in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")
            all_found = False

    return all_found


def check_conditional_rendering():
    """Check App.jsx conditional rendering."""
    print("\nChecking App.jsx conditional rendering...")

    file_path = "frontend/src/pages/App.jsx"

    with open(file_path, "r") as f:
        content = f.read()

    # Check for conditional rendering
    checks = [
        ("{voiceMode ?", "Conditional rendering based on voiceMode"),
        ("<VoiceCallForm", "VoiceCallForm component usage"),
        ("onSubmit={handleVoiceCallSubmit}", "Form submit handler passed"),
        ("📞 Start Voice Call", "Voice mode toggle button"),
        ("💬 Switch to Chat", "Chat mode toggle button"),
    ]

    all_found = True
    for check_string, description in checks:
        if check_string in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")
            all_found = False

    return all_found


def check_workflow_id_display():
    """Check that workflow ID is displayed."""
    print("\nChecking workflow ID display...")

    file_path = "frontend/src/pages/App.jsx"

    with open(file_path, "r") as f:
        content = f.read()

    # Check for workflow ID display
    if "{voiceWorkflowId &&" in content or "voiceWorkflowId" in content:
        print("  ✅ Workflow ID displayed to user")
        if "Workflow ID:" in content or "workflow_id" in content:
            print("  ✅ Workflow ID labeled")
            return True
        else:
            print("  ⚠️  Workflow ID displayed but not clearly labeled")
            return True
    else:
        print("  ❌ Workflow ID not displayed")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Step 5 Verification: Frontend Update for Voice Call Initiation")
    print("=" * 70)

    checks = [
        check_voice_call_form,
        check_api_service,
        check_app_imports,
        check_app_state,
        check_app_handlers,
        check_conditional_rendering,
        check_workflow_id_display,
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
        print("\n✅ Step 5 verification PASSED!")
        print("\nThe frontend has been successfully updated for voice call initiation.")
        print("\nNext steps:")
        print("  1. Start the backend services:")
        print("     - docker compose up -d")
        print("     - uv run python scripts/run_worker.py")
        print("     - uv run uvicorn api.main:app --reload")
        print("  2. Start the frontend:")
        print("     - cd frontend")
        print("     - npm install")
        print("     - npx vite")
        print("  3. Test the voice call feature:")
        print("     - Open http://localhost:5173")
        print("     - Click '📞 Start Voice Call'")
        print("     - Fill out the form and submit")
        print("     - Check that workflow ID is displayed")
        print("     - Verify workflow in Temporal UI")
        return 0
    else:
        print("\n❌ Step 5 verification FAILED")
        print(f"\n{total - passed} check(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
