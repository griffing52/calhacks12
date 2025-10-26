#!/usr/bin/env python3
"""
Complete Voice Agent Implementation Verification

This script runs all 5 step verifications in sequence and provides
a comprehensive summary of the implementation status.

Usage:
    python scripts/verify_voice_agent_complete.py
"""

import subprocess
import sys


def run_verification(step_num, script_name):
    """Run a verification script and return success status."""
    print(f"\n{'=' * 70}")
    print(f"Running Step {step_num} Verification: {script_name}")
    print(f"{'=' * 70}\n")

    try:
        result = subprocess.run(
            ["python", f"scripts/{script_name}"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Print output
        print(result.stdout)

        if result.stderr:
            print("STDERR:", result.stderr)

        # Check exit code
        success = result.returncode == 0

        if success:
            print(f"\n✅ Step {step_num} verification PASSED")
        else:
            print(f"\n❌ Step {step_num} verification FAILED (exit code: {result.returncode})")

        return success

    except subprocess.TimeoutExpired:
        print(f"\n❌ Step {step_num} verification TIMEOUT")
        return False
    except Exception as e:
        print(f"\n❌ Step {step_num} verification ERROR: {e}")
        return False


def main():
    """Run all verification steps."""
    print("\n" + "=" * 70)
    print(" " * 15 + "VOICE AGENT IMPLEMENTATION VERIFICATION")
    print("=" * 70)
    print("\nThis script will verify all 5 implementation steps:")
    print("  Step 1: Goal and Tool Definition")
    print("  Step 2: Activity Implementation")
    print("  Step 3: Workflow Logic Updates")
    print("  Step 4: API Endpoint for Call Initiation")
    print("  Step 5: Frontend Update")
    print("\n" + "=" * 70)

    # Define verification scripts
    verifications = [
        (1, "verify_voice_agent_step1.py"),
        (2, "verify_voice_agent_step2.py"),
        (3, "verify_voice_agent_step3.py"),
        (4, "verify_voice_agent_step4.py"),
        (5, "verify_voice_agent_step5.py"),
    ]

    # Run all verifications
    results = {}
    for step_num, script_name in verifications:
        success = run_verification(step_num, script_name)
        results[step_num] = success

    # Print summary
    print("\n" + "=" * 70)
    print(" " * 25 + "FINAL SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(results.values())

    print(f"\nVerification Results: {passed}/{total} steps passed\n")

    for step_num, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  Step {step_num}: {status}")

    print("\n" + "=" * 70)

    if all(results.values()):
        print("\n🎉 ALL VERIFICATIONS PASSED! 🎉")
        print("\nThe voice agent implementation is complete!")
        print("\nNext steps:")
        print("  1. Start services:")
        print("     Terminal 1: docker compose up -d")
        print("     Terminal 2: uv run python scripts/run_worker.py")
        print("     Terminal 3: uv run uvicorn api.main:app --reload")
        print("     Terminal 4: cd frontend && npx vite")
        print("\n  2. Test the implementation:")
        print("     - Open http://localhost:5173")
        print("     - Click '📞 Start Voice Call'")
        print("     - Fill out and submit the form")
        print("     - Verify workflow in http://localhost:8081")
        print("\n  3. Review documentation:")
        print("     - VOICE_AGENT_IMPLEMENTATION_SUMMARY.md")
        print("     - STEP1_COMPLETE.md through STEP5_COMPLETE.md")
        print("     - docs/voice-agent-setup.md")
        print("\n" + "=" * 70)
        return 0
    else:
        print("\n❌ SOME VERIFICATIONS FAILED")
        print(f"\n{total - passed} step(s) need attention.")
        print("\nReview the output above for details on what failed.")
        print("\nYou can run individual verifications:")
        for step_num in results:
            if not results[step_num]:
                print(f"  python scripts/verify_voice_agent_step{step_num}.py")
        print("\n" + "=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
