"""
Production-ready LiveKit Voice Agent for Temporal AI Workflows
Handles outbound voice calls on behalf of users to complete goals.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from dotenv import load_dotenv

try:
    from livekit import agents, rtc
    from livekit.agents import (
        JobContext,
        WorkerOptions,
        AutoSubscribe,
        JobProcess,
    )
    # Import the voice Agent (new API in livekit-agents 1.2+)
    from livekit.agents import llm, stt, tts
    from livekit.agents.voice import Agent as VoiceAgent
    from livekit.plugins import openai
    HAS_VOICE_ASSISTANT = True
except ImportError as e:
    print(f"Error importing LiveKit dependencies: {e}")
    print("\nTo fix this, install the required packages:")
    print("  Run from project root: uv sync")
    print("\nThis will install:")
    print("  - livekit")
    print("  - livekit-agents")  
    print("  - livekit-plugins-openai")
    raise

# Load environment variables
load_dotenv("../.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voice-agent")


class TemporalVoiceAgent:
    """
    AI Voice Assistant that conducts conversations on behalf of the user.
    
    Features:
    - Goal-oriented conversations
    - Context-aware responses
    - Information collection and validation
    - Error handling and graceful failures
    - Integration with Temporal workflows via webhooks
    """

    def __init__(
        self,
        call_sid: str,
        goal: str,
        context: str,
        user_name: str = "Griffin Galimi",
        webhook_url: Optional[str] = None,
    ) -> None:
        """
        Initialize the voice assistant.
        
        Args:
            call_sid: Twilio Call SID for tracking
            goal: The objective of the call (e.g., "schedule appointment")
            context: Additional context about the situation
            user_name: Name of the person the agent is calling on behalf of
            webhook_url: URL to send events back to Temporal workflow
        """
        self.call_sid = call_sid
        self.goal = goal
        self.context = context
        self.user_name = user_name
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        
        # Conversation state
        self.conversation_started = False
        self.information_collected: Dict[str, Any] = {}
        self.requires_user_input = False
        self.pending_question: Optional[str] = None
        
        # Build dynamic instructions based on goal and context
        self.instructions = self._build_instructions()
        
        logger.info(
            f"TemporalVoiceAgent initialized - Call SID: {call_sid}, "
            f"Goal: {goal}, User: {user_name}"
        )

    def _build_instructions(self) -> str:
        """Build dynamic instructions for the AI based on goal and context."""
        return f"""You are a professional AI assistant calling on behalf of {self.user_name}.

GOAL: {self.goal}

CONTEXT: {self.context}

PERSONALITY & STYLE:
- Professional, friendly, and confident
- Speak naturally and conversationally
- Use the caller's name if they provide it
- Be concise but thorough
- Show empathy and understanding

CONVERSATION FLOW:
1. Greet the person warmly and introduce yourself
2. Explain you're calling on behalf of {self.user_name}
3. State the purpose of your call clearly (the goal)
4. Listen carefully to their responses
5. Collect any necessary information
6. Handle objections gracefully
7. Confirm next steps before ending

IMPORTANT RULES:
- If you need information that only {self.user_name} has (like confirmation codes, passwords, account numbers), 
  say "I need to get that information from {self.user_name}. One moment please."
- Never make up information you don't have
- If the person is busy, offer to call back at a better time
- Be respectful if they decline or hang up
- Stay focused on the goal but be flexible in how you achieve it

INFORMATION TO COLLECT (if relevant to the goal):
- Person's name and contact information
- Availability for appointments/meetings
- Specific requirements or preferences
- Any concerns or questions they have
- Confirmation that the goal was achieved

Remember: You represent {self.user_name} professionally. Make them proud!"""

    async def send_webhook_event(
        self, 
        event_type: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send event to Temporal workflow via webhook.
        
        Args:
            event_type: Type of event (e.g., "agent_needs_info", "call_complete")
            data: Additional event data
            
        Returns:
            True if webhook sent successfully, False otherwise
        """
        try:
            event_data = {
                "call_sid": self.call_sid,
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                **(data or {})
            }
            
            webhook_endpoint = f"{self.webhook_url}/webhooks/livekit/events"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook_endpoint,
                    json=event_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Webhook sent successfully: {event_type}")
                    return True
                else:
                    logger.warning(
                        f"Webhook returned {response.status_code}: {response.text}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False

    async def request_user_information(self, question: str) -> None:
        """
        Request information from the user via the web UI.
        
        Args:
            question: The question to ask the user
        """
        self.requires_user_input = True
        self.pending_question = question
        
        logger.info(f"Requesting user input: {question}")
        
        await self.send_webhook_event(
            "agent_needs_info",
            {
                "question": question,
                "goal": self.goal,
                "context": self.context
            }
        )

    async def handle_user_response(self, answer: str) -> None:
        """
        Handle response from user via web UI.
        
        Args:
            answer: The user's answer to the pending question
        """
        if self.pending_question:
            logger.info(f"Received user answer: {answer}")
            self.information_collected[self.pending_question] = answer
            self.requires_user_input = False
            self.pending_question = None

    async def complete_call(
        self, 
        success: bool, 
        summary: str,
        collected_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark the call as complete and send results to workflow.
        
        Args:
            success: Whether the goal was achieved
            summary: Summary of what happened on the call
            collected_info: Any information collected during the call
        """
        logger.info(f"Call completing - Success: {success}, Summary: {summary}")
        
        await self.send_webhook_event(
            "call_complete",
            {
                "success": success,
                "summary": summary,
                "goal": self.goal,
                "information_collected": collected_info or self.information_collected,
                "requires_followup": self.requires_user_input
            }
        )

    async def handle_error(self, error: str) -> None:
        """
        Handle and report errors during the call.
        
        Args:
            error: Description of the error
        """
        logger.error(f"Call error: {error}")
        
        await self.send_webhook_event(
            "call_error",
            {
                "error": error,
                "goal": self.goal
            }
        )


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the LiveKit agent.
    
    Extracts goal and context from room metadata and conducts the conversation.
    """
    logger.info(f"Agent starting for room: {ctx.room.name}")
    
    # Extract metadata from room (passed from Twilio TwiML)
    metadata = ctx.room.metadata or "{}"
    import json
    try:
        room_data = json.loads(metadata) if isinstance(metadata, str) else metadata
    except json.JSONDecodeError:
        room_data = {}
    
    # Get call parameters
    call_sid = room_data.get("call_sid", ctx.room.name.replace("call-", ""))
    goal = room_data.get("goal", "assist the caller")
    context = room_data.get("context", "")
    user_name = room_data.get("user_name", os.getenv("USER_NAME", "Griffin Galimi"))
    
    logger.info(f"Call parameters - SID: {call_sid}, Goal: {goal}")
    
    # Create the voice assistant manager
    agent_manager = TemporalVoiceAgent(
        call_sid=call_sid,
        goal=goal,
        context=context,
        user_name=user_name,
    )
    
    # Set up data channel listener for web UI messages
    @ctx.room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        """Handle data messages from the web UI (via send_info_to_livekit)."""
        try:
            message = data.data.decode("utf-8")
            logger.info(f"Received data from web UI: {message}")
            
            # If we're waiting for user input, process it
            if agent_manager.requires_user_input:
                asyncio.create_task(agent_manager.handle_user_response(message))
        except Exception as e:
            logger.error(f"Error processing data packet: {e}")
    
    if HAS_VOICE_ASSISTANT:
        # Build initial greeting
        initial_greeting = f"Hello! This is an AI assistant calling on behalf of {user_name}. I am supposed to {goal}. Is now a good time to talk?"
        
        logger.info(f"Agent will greet with: {initial_greeting}")
        
        # Create the voice agent using the new API
        # https://docs.livekit.io/agents/voice-agent/
        assistant = VoiceAgent(
            vad=agents.stt.VAD.load(),  # Voice activity detection
            stt=openai.STT(model="whisper-1"),  # Speech-to-text
            llm=openai.LLM(model="gpt-4o"),  # Language model
            tts=openai.TTS(voice="coral"),  # Text-to-speech
            instructions=agent_manager.instructions,  # System instructions
        )
        
        # Start the voice assistant
        assistant.start(ctx.room)
        
        logger.info("Voice agent started!")
        
        # Greet when participant connects
        async def on_participant_connected(participant: rtc.RemoteParticipant):
            """Greet when caller joins the room"""
            if participant.identity.startswith("twilio-"):
                logger.info(f"Twilio participant connected: {participant.identity}")
                await asyncio.sleep(0.5)  # Brief delay for stability
                await assistant.say(initial_greeting, allow_interruptions=True)
                logger.info("✓ Agent greeted the caller!")
        
        ctx.room.on("participant_connected", on_participant_connected)
        
        logger.info("Agent ready and waiting for caller to connect...")
        
        # Keep running until call ends
        await asyncio.sleep(3600)
    else:
        # Fallback: just log that we're ready
        logger.warning("VoiceAgent not available - agent will not respond to audio")
        logger.info(f"Agent ready for room {ctx.room.name}")
        logger.info(f"Goal: {goal}")
        logger.info(f"Context: {context}")
        
        # Keep the agent running
        await asyncio.sleep(3600)  # Sleep for 1 hour
    
    # The assistant will automatically:
    # - Detect when the user speaks (VAD)
    # - Transcribe their speech (STT)
    # - Generate a response using the LLM with the system instructions
    # - Speak the response (TTS)
    # - Continue the conversation until the call ends


if __name__ == "__main__":
    # Run the agent
    logger.info("Starting LiveKit Voice Agent worker...")
    
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Register with the agent name that matches the dispatch rule
            agent_name="voice-assistant",
        )
    )