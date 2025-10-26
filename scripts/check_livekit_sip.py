#!/usr/bin/env python3
"""
Check and display LiveKit SIP trunk and dispatch rule configuration.
This helps debug why Twilio SIP calls are getting "No Answer" from LiveKit.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import from shared
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import subprocess
import json

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

# Twilio IP ranges that need to be allowed
TWILIO_IP_RANGES = [
    "54.172.60.0/23",
    "54.244.51.0/24", 
    "3.122.181.0/24",
    "18.202.178.0/24",
]

def run_lk_command(args):
    """Run lk CLI command with credentials"""
    cmd = [
        "lk", 
        *args,
        f"--api-key={LIVEKIT_API_KEY}",
        f"--api-secret={LIVEKIT_API_SECRET}",
        f"--url={LIVEKIT_URL}"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ 'lk' CLI not found. Install with: brew install livekit")
        return None

def main():
    print("=" * 80)
    print("LiveKit SIP Configuration Checker")
    print("=" * 80)
    print()
    
    # Check environment
    print("📋 Environment:")
    print(f"  LIVEKIT_URL: {LIVEKIT_URL}")
    print(f"  LIVEKIT_API_KEY: {LIVEKIT_API_KEY[:10]}...")
    print()
    
    # List SIP trunks
    print("📞 SIP Inbound Trunks:")
    trunk_output = run_lk_command(["sip", "inbound", "list"])
    if trunk_output:
        print(trunk_output)
    else:
        print("  ❌ Failed to list trunks")
    print()
    
    # List dispatch rules
    print("📋 SIP Dispatch Rules:")
    dispatch_output = run_lk_command(["sip", "dispatch", "list"])
    if dispatch_output:
        print(dispatch_output)
    else:
        print("  ❌ Failed to list dispatch rules")
    print()
    
    # Show Twilio IPs that should be allowed
    print("🔐 Required Twilio IP Ranges (must be in trunk allowed_addresses):")
    for ip_range in TWILIO_IP_RANGES:
        print(f"  - {ip_range}")
    print()
    
    print("=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print()
    print("1. Check that your SIP trunk has 'allowed_addresses' including Twilio IPs above")
    print("2. Verify dispatch rule has correct 'agent_name' matching your agent")
    print("3. Check that 'numbers' in trunk matches your Twilio number: +13105825023")
    print()
    print("If configuration is wrong, update in LiveKit Cloud dashboard:")
    print("  https://cloud.livekit.io/projects → Select project → SIP")
    print()

if __name__ == "__main__":
    main()
