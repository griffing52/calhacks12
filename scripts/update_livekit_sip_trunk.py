#!/usr/bin/env python3
"""
Update LiveKit SIP Trunk to allow Twilio IP addresses.

This fixes error 32011 (Request timeout) by whitelisting Twilio's signaling IPs.
"""

import os
import requests
from livekit import api

# LiveKit credentials from environment
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://wait-less-22pf77bb.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "APIXuwGXkLhyAW7")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Twilio signaling IP ranges (North America + all regions for redundancy)
TWILIO_SIGNALING_IPS = [
    # North America
    "54.172.60.0/30",   # Virginia
    "54.244.51.0/30",   # Oregon
    # Europe (for redundancy)
    "54.171.127.192/30",  # Ireland
    "35.156.191.128/30",  # Frankfurt
    # Asia-Pacific (for redundancy)
    "54.65.63.192/30",    # Tokyo
    "54.169.127.128/30",  # Singapore
    "54.252.254.64/30",   # Sydney
    # South America (for redundancy)
    "177.71.206.192/30",  # São Paulo
]

SIP_TRUNK_ID = "ST_kngPd5bsM8U4"


def update_sip_trunk():
    """Update SIP trunk with allowed Twilio IP addresses."""
    
    if not LIVEKIT_API_SECRET:
        print("❌ Error: LIVEKIT_API_SECRET not set in environment")
        print("   Please set it in your .env file or export it:")
        print("   export LIVEKIT_API_SECRET=your_secret_here")
        return False
    
    try:
        # Use LiveKit API to update trunk
        # Note: We need to use the REST API directly since Python SDK may not expose this
        
        # Create API token for authentication
        from livekit.api import AccessToken, SipGrant
        
        # For now, let's use curl command approach
        print("📝 To update the SIP trunk, run this command:\n")
        
        # Build allowed addresses list
        allowed_ips = ",".join(TWILIO_SIGNALING_IPS)
        
        print(f"""
lk sip inbound update \\
  --id {SIP_TRUNK_ID} \\
  --allowed-addresses "{allowed_ips}"
""")
        
        print("\nOr update via LiveKit Cloud dashboard:")
        print("1. Go to https://cloud.livekit.io/projects/wait-less/settings/sip")
        print("2. Click on 'Twilio Inbound Trunk'")
        print("3. Add these allowed addresses:")
        for ip in TWILIO_SIGNALING_IPS:
            print(f"   - {ip}")
        
        print("\n💡 Tip: You only need North America IPs if your Twilio account is in US region")
        print("   Virginia: 54.172.60.0/30")
        print("   Oregon: 54.244.51.0/30")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🔧 Updating LiveKit SIP Trunk for Twilio Integration")
    print("=" * 60)
    update_sip_trunk()
