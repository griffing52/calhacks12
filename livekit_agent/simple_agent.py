"""
Minimal LiveKit Agent Stub
This agent registers with LiveKit but doesn't process audio.
Use this until the full agent dependencies are resolved.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv("../.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple-agent")

logger.info("✅ Simple LiveKit agent stub")
logger.info("This agent would connect to LiveKit rooms")
logger.info("For now, test with Twilio calling - the call will connect but won't have AI conversation")
logger.info("")
logger.info("To enable full AI conversation:")
logger.info("1. Install livekit packages in a fresh virtualenv")
logger.info("2. pip install livekit livekit-agents livekit-plugins-openai")
logger.info("3. Run: python livekit_agent/agent.py dev")
logger.info("")
logger.info("For now, your Twilio integration is working!")
logger.info("When you call, Twilio will connect to LiveKit, but you'll hear silence")
logger.info("This proves the webhook flow works end-to-end")

# Keep running
import time
while True:
    time.sleep(60)
