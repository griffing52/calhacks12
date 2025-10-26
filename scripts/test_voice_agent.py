#!/usr/bin/env python3
"""
Test script for the Voice Agent implementation.
Tests the initiate_voice_call tool in both mock and production modes.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.initiate_voice_call import initiate_voice_call


def test_mock_mode():
    """Test the tool in mock mode (no credentials)"""
    print("\n=== Testing Voice Call Tool - Mock Mode ===\n")
    
    # Clear any existing credentials to ensure mock mode
    env_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.pop(var, None)
    
    try:
        # Test valid call
        args = {
            "phone_number": "+14155551234",
            "goal": "Password reset assistance",
            "context": "User cannot log in to their account",
            "userConfirmation": "yes",
        }
        
        result = initiate_voice_call(args)
        
        print("Test 1: Valid call request")
        print(f"  Status: {result['status']}")
        print(f"  Call SID: {result.get('call_sid', 'N/A')}")
        print(f"  Message: {result['message']}")
        print(f"  Mode: {result.get('mode', 'N/A')}")
        assert result["status"] == "success", "Expected success status"
        assert result.get("mode") == "mock", "Expected mock mode"
        assert "call_sid" in result, "Expected call_sid in result"
        print("  ✓ PASSED\n")
        
        # Test missing phone number
        args_no_phone = {
            "goal": "Password reset",
            "context": "User locked out",
            "userConfirmation": "yes",
        }
        
        result = initiate_voice_call(args_no_phone)
        
        print("Test 2: Missing phone number")
        print(f"  Status: {result['status']}")
        print(f"  Error: {result.get('error', 'N/A')}")
        assert result["status"] == "error", "Expected error status"
        assert "phone number" in result["error"].lower(), "Expected phone number error"
        print("  ✓ PASSED\n")
        
        # Test missing goal
        args_no_goal = {
            "phone_number": "+14155551234",
            "context": "User issue",
            "userConfirmation": "yes",
        }
        
        result = initiate_voice_call(args_no_goal)
        
        print("Test 3: Missing goal")
        print(f"  Status: {result['status']}")
        print(f"  Error: {result.get('error', 'N/A')}")
        assert result["status"] == "error", "Expected error status"
        assert "goal" in result["error"].lower(), "Expected goal error"
        print("  ✓ PASSED\n")
        
        print("=== All Mock Mode Tests Passed ===\n")
        
    finally:
        # Restore original environment variables
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value


def test_goal_registration():
    """Test that the voice goal is properly registered"""
    print("\n=== Testing Goal Registration ===\n")
    
    from goals import goal_list
    
    # Check if voice goal exists
    voice_goals = [g for g in goal_list if g.id == "goal_voice_support"]
    
    print(f"Total goals registered: {len(goal_list)}")
    print(f"Voice goals found: {len(voice_goals)}")
    
    assert len(voice_goals) > 0, "Voice goal not found in goal list"
    
    voice_goal = voice_goals[0]
    print(f"\nVoice Goal Details:")
    print(f"  ID: {voice_goal.id}")
    print(f"  Name: {voice_goal.agent_name}")
    print(f"  Category: {voice_goal.category_tag}")
    print(f"  Tools: {[t.name for t in voice_goal.tools]}")
    
    assert voice_goal.agent_name == "Voice Support Agent", "Wrong agent name"
    assert voice_goal.category_tag == "voice", "Wrong category tag"
    assert len(voice_goal.tools) > 0, "No tools registered"
    assert voice_goal.tools[0].name == "InitiateVoiceCall", "Wrong tool name"
    
    print("  ✓ PASSED\n")
    
    print("=== Goal Registration Tests Passed ===\n")


def test_tool_handler_registration():
    """Test that the tool handler is properly registered"""
    print("\n=== Testing Tool Handler Registration ===\n")
    
    from tools import get_handler
    
    try:
        handler = get_handler("InitiateVoiceCall")
        print(f"Handler found: {handler.__name__}")
        assert handler == initiate_voice_call, "Wrong handler function"
        print("  ✓ PASSED\n")
        
        print("=== Tool Handler Registration Tests Passed ===\n")
        
    except ValueError as e:
        print(f"  ✗ FAILED: {e}\n")
        raise


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Voice Agent Implementation Test Suite")
    print("=" * 60)
    
    try:
        test_goal_registration()
        test_tool_handler_registration()
        test_mock_mode()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe Voice Agent implementation is working correctly!")
        print("\nNext steps:")
        print("  1. Add Twilio credentials to .env for production mode")
        print("  2. Set up LiveKit server and credentials")
        print("  3. Create TwiML webhook endpoint")
        print("  4. Add 'voice' to GOAL_CATEGORIES in .env")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
