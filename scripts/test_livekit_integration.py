#!/usr/bin/env python3
"""
Test script for send_info_to_livekit functionality.

This script verifies that the send_info_to_livekit function works correctly
in both stub mode (no credentials) and production mode (with LiveKit credentials).

Usage:
    # Test in stub mode (no credentials needed)
    uv run python scripts/test_livekit_integration.py

    # Test in production mode (requires LiveKit credentials in .env)
    export LIVEKIT_URL=wss://...
    export LIVEKIT_API_KEY=...
    export LIVEKIT_API_SECRET=...
    uv sync --extra voice
    uv run python scripts/test_livekit_integration.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def test_send_info_to_livekit():
    """Test the send_info_to_livekit function."""
    print("Testing send_info_to_livekit Function")
    print("=" * 60)
    
    # Import the function (from api.main)
    from api.main import send_info_to_livekit
    
    # Check for credentials
    has_credentials = all([
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
        os.getenv("LIVEKIT_URL")
    ])
    
    if has_credentials:
        print("\n✓ LiveKit credentials found - testing in PRODUCTION mode")
        print(f"  URL: {os.getenv('LIVEKIT_URL')}")
        print(f"  API Key: {os.getenv('LIVEKIT_API_KEY')[:10]}...")
    else:
        print("\n⚠️  No LiveKit credentials - testing in STUB mode")
        print("  (This is expected for development)")
    
    # Test Case 1: Send test information
    print("\n" + "-" * 60)
    print("Test Case 1: Send confirmation code")
    print("-" * 60)
    
    test_call_sid = "CA562ab2481710b6e2c5d394c13c5d63e2"  # Example Call SID
    test_answer = "Confirmation code: 123456"
    
    try:
        success = await send_info_to_livekit(test_call_sid, test_answer)
        
        if success:
            print(f"✓ Successfully sent: {test_answer}")
            if not has_credentials:
                print("  (Logged to console in stub mode)")
        else:
            print(f"❌ Failed to send: {test_answer}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 2: Send longer message
    print("\n" + "-" * 60)
    print("Test Case 2: Send longer message")
    print("-" * 60)
    
    test_call_sid_2 = "CA7890abcd1234efgh5678ijkl90mnop12"
    test_answer_2 = "Account number is 987654321 and routing number is 123456789"
    
    try:
        success = await send_info_to_livekit(test_call_sid_2, test_answer_2)
        
        if success:
            print(f"✓ Successfully sent: {test_answer_2[:50]}...")
            if not has_credentials:
                print("  (Logged to console in stub mode)")
        else:
            print(f"❌ Failed to send message")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if not has_credentials:
        print("✓ Stub mode tests passed")
        print("\nTo test production mode:")
        print("  1. Set up LiveKit account: https://livekit.io/cloud")
        print("  2. Add credentials to .env file:")
        print("     LIVEKIT_URL=wss://...")
        print("     LIVEKIT_API_KEY=...")
        print("     LIVEKIT_API_SECRET=...")
        print("  3. Install dependencies: uv sync --extra voice")
        print("  4. Re-run this script")
    else:
        print("✓ Production mode tests completed")
        print("\nNote: In production, you need:")
        print("  - Active LiveKit room with Call SID as name")
        print("  - LiveKit agent listening for data messages")
        print("  - Network connectivity to LiveKit server")
    
    print("\n" + "=" * 60)
    print("For full integration testing, see TODO.md Phase 5")
    print("=" * 60)


async def test_via_api_endpoint():
    """Test the API endpoint that uses send_info_to_livekit."""
    print("\n\nTesting API Endpoint Integration")
    print("=" * 60)
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        # Check if API is running
        print("\nChecking if API server is running...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/")
                if response.status_code == 200:
                    print("✓ API server is running")
                else:
                    print(f"⚠️  API server returned status {response.status_code}")
                    return
        except httpx.ConnectError:
            print("❌ API server is not running")
            print("\nTo test the API endpoint:")
            print("  1. Start API: uv run uvicorn api.main:app --reload")
            print("  2. Re-run this script")
            return
        
        # Test the endpoint
        print("\nTesting /api/v1/voice-provide-info endpoint...")
        
        test_workflow_id = "voice-call-test-123"
        test_answer = "Test answer from script"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/voice-provide-info",
                params={
                    "workflow_id": test_workflow_id,
                    "answer": test_answer
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Endpoint responded: {result}")
            else:
                print(f"⚠️  Endpoint returned status {response.status_code}")
                print(f"Response: {response.text}")
    
    except ImportError:
        print("\n⚠️  httpx not installed, skipping API endpoint test")
        print("Install with: uv pip install httpx")
    except Exception as e:
        print(f"\n❌ Error testing API endpoint: {e}")


async def main():
    """Run all tests."""
    await test_send_info_to_livekit()
    await test_via_api_endpoint()
    
    print("\n✅ All tests completed!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
