#!/usr/bin/env python3
"""
LiveKit Voice Assistant using OpenAI Realtime API
Simple agent for voice calls via Twilio SIP integration.
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins.openai import realtime

# Load environment variables from the correct path
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Get LiveKit credentials from environment and set them explicitly
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Set environment variables explicitly for the worker subprocess
if LIVEKIT_URL:
    os.environ["LIVEKIT_URL"] = LIVEKIT_URL
if LIVEKIT_API_KEY:
    os.environ["LIVEKIT_API_KEY"] = LIVEKIT_API_KEY
if LIVEKIT_API_SECRET:
    os.environ["LIVEKIT_API_SECRET"] = LIVEKIT_API_SECRET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple-voice-agent")

# Log what we found (redact secrets)
logger.info(f"Loaded credentials: URL={LIVEKIT_URL}, API_KEY={'*' * len(LIVEKIT_API_KEY) if LIVEKIT_API_KEY else 'MISSING'}, API_SECRET={'*' * len(LIVEKIT_API_SECRET) if LIVEKIT_API_SECRET else 'MISSING'}")


async def entrypoint(ctx: JobContext):
    """Entry point called when a job is assigned.
    
    Uses OpenAI Realtime API for voice interaction.
    """
    try:
        logger.info("--- New job assigned ---")
        logger.info(f"Room: {ctx.room.name}")
        
        # Connect to the room
        await ctx.connect()
        logger.info("✅ Connected to room")
        
        # Create Realtime session with instructions
        model = realtime.RealtimeModel(
            instructions=(
                "You are a friendly AI assistant helping with customer support. "
                "Be conversational, helpful, and keep responses concise. "
                "Speak clearly and naturally."
            ),
            voice="coral",
        )
        logger.info("✅ Realtime model created")
        
        # Create and start the session
        session = realtime.RealtimeSession(
            model=model,
            room=ctx.room,
        )
        await session.start()
        logger.info("✅ Realtime session started")
        
    except Exception as e:
        logger.exception(f"Error in entrypoint: {e}")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Register with a specific agent name so dispatch rules can target it
            agent_name="voice-assistant",
        )
    )
