#!/usr/bin/env python3
"""
Test script for the voice initiate API endpoint.

This script tests the /api/v1/voice-initiate endpoint by sending a POST request
with phone number, goal, and context.

Usage:
    uv run python scripts/test_voice_initiate_endpoint.py
"""

import asyncio
import sys

import httpx


async def test_voice_initiate_endpoint():
    """Test the voice initiate endpoint with a sample request."""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/voice-initiate"

    # Test data
    test_request = {
        "phone_number": "+14155551234",
        "goal": "Reset password",
        "context": "User is unable to log in to their account and needs assistance resetting their password",
    }

    print("Testing Voice Initiate Endpoint")
    print("=" * 60)
    print(f"Endpoint: {endpoint}")
    print(f"Request data:")
    for key, value in test_request.items():
        print(f"  {key}: {value}")
    print()

    try:
        async with httpx.AsyncClient() as client:
            # Send POST request
            print("Sending POST request...")
            response = await client.post(endpoint, json=test_request, timeout=10.0)

            # Check response
            print(f"Response Status: {response.status_code}")
            print()

            if response.status_code == 200:
                result = response.json()
                print("✅ SUCCESS - Workflow initiated!")
                print()
                print("Response data:")
                for key, value in result.items():
                    print(f"  {key}: {value}")
                print()
                print(f"Workflow ID: {result.get('workflow_id')}")
                print()
                print("You can view the workflow in the Temporal UI:")
                print(f"  http://localhost:8081/namespaces/default/workflows/{result.get('workflow_id')}")
                return True
            else:
                print(f"❌ FAILED - HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False

    except httpx.ConnectError:
        print("❌ FAILED - Could not connect to API server")
        print()
        print("Make sure the API server is running:")
        print("  uv run uvicorn api.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ FAILED - Unexpected error: {e}")
        return False


async def test_endpoint_validation():
    """Test the endpoint with invalid data to verify validation."""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/voice-initiate"

    print("\nTesting Input Validation")
    print("=" * 60)

    test_cases = [
        {
            "name": "Missing phone_number",
            "data": {"goal": "Test", "context": "Test context"},
        },
        {
            "name": "Missing goal",
            "data": {"phone_number": "+14155551234", "context": "Test context"},
        },
        {
            "name": "Missing context",
            "data": {"phone_number": "+14155551234", "goal": "Test goal"},
        },
        {
            "name": "Empty request",
            "data": {},
        },
    ]

    try:
        async with httpx.AsyncClient() as client:
            for test_case in test_cases:
                print(f"\nTest: {test_case['name']}")
                response = await client.post(
                    endpoint, json=test_case["data"], timeout=10.0
                )

                if response.status_code == 422:  # Validation error
                    print(f"  ✅ Validation working - got expected 422 error")
                else:
                    print(
                        f"  ⚠️  Unexpected status code: {response.status_code} (expected 422)"
                    )

    except httpx.ConnectError:
        print("❌ API server not running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True


async def main():
    """Run all tests."""
    print("Voice Initiate Endpoint Test Suite")
    print("=" * 60)
    print()

    # Test valid request
    success = await test_voice_initiate_endpoint()

    # Test validation
    validation_ok = await test_endpoint_validation()

    print()
    print("=" * 60)
    if success and validation_ok:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
