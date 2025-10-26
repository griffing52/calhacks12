"""
Production-Ready LiveKit Voice Agent
Conducts intelligent conversations on behalf of users to complete goals.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from livekit import agents, rtc
from livekit.agents import llm, stt, tts, JobContext, WorkerOptions
from livekit.plugins import anthropic, openai, deepgram, elevenlabs
from dotenv import load_dotenv
import httpx

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("voice-agent")


class ConversationState:
    """Tracks the state of the ongoing conversation."""
    
    def __init__(self, goal: str, context: str, user_name: str = "Griffin Galimi"):
        self.goal = goal
        self.context = context
        self.user_name = user_name
        self.conversation_history: List[Dict[str, str]] = []
        self.required_info: Dict[str, Any] = {}
        self.info_requested: Dict[str, bool] = {}
        self.goal_status = "in_progress"  # in_progress, waiting_for_info, completed, failed
        self.start_time = datetime.now()
        self.call_sid: Optional[str] = None
        self.workflow_id: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def mark_info_requested(self, info_key: str):
        """Mark that we've requested specific information."""
        self.info_requested[info_key] = True
    
    def has_requested(self, info_key: str) -> bool:
        """Check if we've already requested this information."""
        return self.info_requested.get(info_key, False)
    
    def set_info(self, key: str, value: Any):
        """Store required information when received."""
        self.required_info[key] = value
        logger.info(f"Stored info: {key} = {value}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate a summary of the conversation."""
        return {
            "goal": self.goal,
            "status": self.goal_status,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "messages_exchanged": len(self.conversation_history),
            "required_info": self.required_info,
            "call_sid": self.call_sid,
            "workflow_id": self.workflow_id
        }


class VoiceAgent(agents.VoiceAgent):
    """
    Production-ready voice agent that conducts conversations on behalf of users.
    
    Features:
    - Intelligent goal-oriented conversations
    - Information gathering from call recipients
    - Integration with Temporal workflows
    - Real-time data exchange with web UI
    - Comprehensive error handling
    - Conversation state management
    """
    
    def __init__(
        self,
        goal: str,
        context: str,
        user_name: str = "Griffin Galimi",
        call_sid: Optional[str] = None,
        workflow_id: Optional[str] = None,
        webhook_url: Optional[str] = None
    ):
        """
        Initialize the voice agent.
        
        Args:
            goal: The objective to accomplish (e.g., "Schedule a meeting")
            context: Additional context about the task
            user_name: Name of the user the agent represents
            call_sid: Twilio Call SID for this call
            workflow_id: Temporal workflow ID for this call
            webhook_url: URL to send events back to the system
        """
        # Initialize LLM (prefer Claude for conversational abilities)
        llm_provider = os.getenv("AGENT_LLM_PROVIDER", "anthropic")
        
        if llm_provider == "anthropic":
            agent_llm = anthropic.LLM(
                model="claude-3-5-sonnet-20241022",
                temperature=0.7,  # Balanced creativity and consistency
            )
        else:
            agent_llm = openai.LLM(
                model="gpt-4o",
                temperature=0.7,
            )
        
        # Initialize STT (Speech-to-Text)
        agent_stt = deepgram.STT(
            model="nova-2-general",
            language="en-US",
            smart_format=True,
            punctuate=True
        )
        
        # Initialize TTS (Text-to-Speech)
        tts_provider = os.getenv("AGENT_TTS_PROVIDER", "elevenlabs")
        
        if tts_provider == "elevenlabs":
            agent_tts = elevenlabs.TTS(
                voice="Sarah",  # Professional, friendly voice
                model="eleven_turbo_v2",
            )
        else:
            agent_tts = openai.TTS(
                voice="nova",
                model="tts-1",
            )
        
        super().__init__(
            llm=agent_llm,
            stt=agent_stt,
            tts=agent_tts
        )
        
        # Initialize conversation state
        self.state = ConversationState(goal, context, user_name)
        self.state.call_sid = call_sid
        self.state.workflow_id = workflow_id
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        
        # System prompt that guides the agent's behavior
        self.system_prompt = self._build_system_prompt()
        
        logger.info(f"Agent initialized for goal: {goal}")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt that defines the agent's behavior."""
        return f"""You are an AI assistant making a phone call on behalf of {self.state.user_name}.

YOUR GOAL: {self.state.goal}

CONTEXT: {self.state.context}

YOUR ROLE:
- You are professional, courteous, and efficient
- You represent {self.state.user_name} and speak on their behalf
- Your job is to accomplish the goal by having a natural conversation
- Be concise but thorough - phone conversations should be efficient
- Listen carefully and ask clarifying questions when needed

CONVERSATION GUIDELINES:
1. **Introduction**: Start by introducing yourself as {self.state.user_name}'s assistant
2. **Purpose**: Clearly state the reason for the call (the goal)
3. **Information Gathering**: Ask for necessary information to complete the goal
4. **Confirmation**: Confirm important details before completing the task
5. **Closure**: Thank the person and confirm next steps before ending

IMPORTANT BEHAVIORS:
- If you need specific information (account numbers, confirmation codes, etc.), ask clearly
- If the person seems confused, rephrase or provide more context
- If you can't complete the goal (wrong department, etc.), politely ask to be transferred
- If the task is complete, clearly confirm what was accomplished
- Be patient and understanding if the person needs to look something up

INFORMATION HANDLING:
- When you receive important information (numbers, dates, names), repeat it back for confirmation
- If you need the web UI to provide information, you can request it (it will be sent to you)
- Keep track of what information you've gathered

Remember: You're making this call to help {self.state.user_name}. Be professional and get the job done!"""
    
    async def on_call_start(self, ctx: JobContext):
        """
        Called when the call starts. Initialize and greet the call recipient.
        """
        logger.info(f"Call started - Goal: {self.state.goal}")
        
        # Extract room and participant
        room = ctx.room
        
        # Store room for later use
        self.room = room
        self.ctx = ctx
        
        # Listen for data messages from the web UI
        room.on("data_received", self._on_data_received)
        
        # Build personalized greeting
        greeting = self._build_greeting()
        
        # Add to conversation history
        self.state.add_message("assistant", greeting)
        
        # Speak the greeting
        await self.say(greeting)
        
        # Send initial status to webhook
        await self._send_webhook_event("call_started", {
            "goal": self.state.goal,
            "greeting": greeting
        })
    
    def _build_greeting(self) -> str:
        """Build an appropriate greeting based on the goal."""
        base_greeting = f"Hello! This is an assistant calling on behalf of {self.state.user_name}."
        
        # Add goal-specific context
        if "schedule" in self.state.goal.lower() or "meeting" in self.state.goal.lower():
            purpose = f"I'm calling to schedule a meeting. {self.state.context}"
        elif "password" in self.state.goal.lower() or "reset" in self.state.goal.lower():
            purpose = f"I'm calling to help with a password reset. {self.state.context}"
        elif "appointment" in self.state.goal.lower():
            purpose = f"I'm calling to book an appointment. {self.state.context}"
        elif "cancel" in self.state.goal.lower():
            purpose = f"I'm calling to cancel a service. {self.state.context}"
        elif "support" in self.state.goal.lower():
            purpose = f"I'm calling regarding a support request. {self.state.context}"
        else:
            purpose = f"I'm calling about: {self.state.goal}. {self.state.context}"
        
        return f"{base_greeting} {purpose} Do you have a moment to help with this?"
    
    async def _on_data_received(self, data: rtc.DataPacket):
        """
        Handle data messages from the web UI.
        This allows the user to provide information via text instead of voice.
        """
        try:
            message = data.data.decode('utf-8')
            logger.info(f"Received data from web UI: {message}")
            
            # Try to parse as JSON (structured data)
            try:
                data_obj = json.loads(message)
                
                # Handle different types of data
                if data_obj.get("type") == "info":
                    # Store the information
                    key = data_obj.get("key", "additional_info")
                    value = data_obj.get("value")
                    self.state.set_info(key, value)
                    
                    # Acknowledge to the person on the call
                    ack = f"Thank you, I've received that information: {value}"
                    await self.say(ack)
                    self.state.add_message("assistant", ack)
                
                elif data_obj.get("type") == "instruction":
                    # User wants to give the agent specific instructions
                    instruction = data_obj.get("instruction")
                    logger.info(f"Received instruction: {instruction}")
                    # Process instruction...
            
            except json.JSONDecodeError:
                # Plain text message
                self.state.set_info("user_provided_text", message)
                
                # Acknowledge in the conversation
                ack = f"I've received some information to share: {message}"
                await self.say(ack)
                self.state.add_message("assistant", ack)
        
        except Exception as e:
            logger.error(f"Error handling data message: {e}")
    
    async def handle_speech(self, transcript: str):
        """
        Handle speech from the call recipient.
        This is the main conversation loop.
        """
        logger.info(f"Received speech: {transcript}")
        
        # Add to conversation history
        self.state.add_message("user", transcript)
        
        # Analyze the response and determine next action
        response = await self._generate_response(transcript)
        
        # Check if we need information from the web UI
        if self._needs_web_ui_info(transcript, response):
            await self._request_info_from_web_ui(transcript)
            # Continue with temporary response
            temp_response = "Let me check on that information for you. One moment please."
            await self.say(temp_response)
            self.state.add_message("assistant", temp_response)
            return
        
        # Check if goal is complete
        if self._is_goal_complete(transcript, response):
            self.state.goal_status = "completed"
            await self._send_webhook_event("call_complete", self.state.get_summary())
        
        # Speak the response
        await self.say(response)
        self.state.add_message("assistant", response)
    
    async def _generate_response(self, user_input: str) -> str:
        """
        Generate an appropriate response using the LLM.
        """
        # Build conversation context
        conversation = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add recent conversation history (last 10 messages)
        recent_history = self.state.conversation_history[-10:]
        for msg in recent_history:
            conversation.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user input if not already in history
        conversation.append({
            "role": "user",
            "content": user_input
        })
        
        # Generate response using LLM
        try:
            response = await self.llm.chat(conversation)
            return response.content
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, I'm having trouble processing that. Could you please repeat?"
    
    def _needs_web_ui_info(self, user_input: str, response: str) -> bool:
        """
        Determine if we need information from the web UI.
        """
        # Keywords that indicate we need user-provided information
        info_keywords = [
            "confirmation code",
            "account number",
            "password",
            "security code",
            "verification",
            "reference number"
        ]
        
        user_lower = user_input.lower()
        response_lower = response.lower()
        
        # Check if the conversation mentions these topics
        for keyword in info_keywords:
            if keyword in user_lower or keyword in response_lower:
                # Check if we haven't already requested this
                if not self.state.has_requested(keyword):
                    return True
        
        return False
    
    async def _request_info_from_web_ui(self, context: str):
        """
        Send a request to the web UI asking the user to provide information.
        """
        # Extract what information we need
        question = f"The agent needs additional information: {context}"
        
        await self._send_webhook_event("agent_needs_info", {
            "question": question,
            "context": context
        })
        
        # Mark that we've requested this
        self.state.mark_info_requested(context)
    
    def _is_goal_complete(self, user_input: str, response: str) -> bool:
        """
        Determine if the goal has been completed.
        """
        completion_indicators = [
            "confirmed",
            "scheduled",
            "completed",
            "done",
            "all set",
            "taken care of",
            "processed",
            "approved"
        ]
        
        combined = (user_input + " " + response).lower()
        
        # Check for completion indicators
        for indicator in completion_indicators:
            if indicator in combined:
                return True
        
        return False
    
    async def _send_webhook_event(self, event_type: str, data: Dict[str, Any]):
        """
        Send an event back to the Temporal workflow via webhook.
        """
        if not self.webhook_url:
            logger.warning("No webhook URL configured, skipping event send")
            return
        
        try:
            payload = {
                "call_sid": self.state.call_sid,
                "workflow_id": self.state.workflow_id,
                "event_type": event_type,
                **data
            }
            
            webhook_endpoint = f"{self.webhook_url}/webhooks/livekit/events"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_endpoint,
                    json=payload,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Webhook sent: {event_type}")
                else:
                    logger.warning(f"Webhook failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
    
    async def on_call_end(self):
        """
        Called when the call ends. Send final summary.
        """
        logger.info("Call ended")
        
        # Generate final summary
        summary = self.state.get_summary()
        
        # Send to webhook
        await self._send_webhook_event("call_ended", summary)


async def entrypoint(ctx: JobContext):
    """
    Entry point for the LiveKit agent.
    This is called when a new call is connected.
    """
    logger.info("Agent entrypoint called")
    
    # Extract call information from room metadata
    room = ctx.room
    metadata = json.loads(room.metadata) if room.metadata else {}
    
    goal = metadata.get("goal", "General support call")
    context = metadata.get("context", "")
    user_name = metadata.get("user_name", "Griffin Galimi")
    call_sid = metadata.get("call_sid")
    workflow_id = metadata.get("workflow_id")
    
    logger.info(f"Starting agent for goal: {goal}")
    
    # Create and run the agent
    agent = VoiceAgent(
        goal=goal,
        context=context,
        user_name=user_name,
        call_sid=call_sid,
        workflow_id=workflow_id
    )
    
    # Connect the agent to the room
    await agent.connect(room)
    
    # Wait for the call to end
    await agent.wait_for_completion()


if __name__ == "__main__":
    # Run the agent worker
    logger.info("Starting LiveKit Voice Agent Worker")
    
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )