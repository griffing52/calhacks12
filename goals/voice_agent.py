from typing import List

import tools.tool_registry as tool_registry
from models.tool_definitions import AgentGoal

starter_prompt_voice = (
    "Welcome! I'm your voice support assistant. "
    "I can help you by calling you directly to discuss your needs. "
    "Please provide your phone number and describe what you need help with."
)

goal_voice_support = AgentGoal(
    id="goal_voice_support",
    category_tag="voice",
    agent_name="Voice Support Agent",
    agent_friendly_description="Initiate a voice call to provide personalized customer support.",
    tools=[
        tool_registry.initiate_voice_call_tool,
    ],
    description=(
        "The user wants to receive voice-based customer support. "
        "To assist with that goal, help the user gather the required information: "
        "1. Phone number (in E.164 format, e.g., +1234567890) "
        "2. Support goal/reason for the call "
        "3. Any relevant context about their issue "
        "Once you have all the information, use the InitiateVoiceCall tool to start the call."
    ),
    starter_prompt=starter_prompt_voice,
    example_conversation_history="\n ".join(
        [
            "user: I need help with my account",
            "agent: I'd be happy to help you with your account! To provide the best support, I can call you directly. "
            "May I have your phone number?",
            "user: +14155551234",
            "agent: Great! And can you briefly describe what you need help with regarding your account?",
            "user: I can't log in and need to reset my password",
            "agent: I understand - you're having trouble logging in and need a password reset. "
            "Let me initiate a voice call to walk you through the process. Please confirm if you'd like me to call you now.",
            "user: yes",
            "user_confirmed_tool_run: <user clicks confirm on InitiateVoiceCall tool>",
            'tool_result: {"status": "success", "call_sid": "CA1234567890abcdef", "message": "Voice call initiated successfully"}',
            "agent: Perfect! I've initiated a call to +14155551234. You should receive a call shortly where our voice assistant "
            "will help you reset your password. The call ID is CA1234567890abcdef for your reference.",
        ]
    ),
)

voice_goals: List[AgentGoal] = [
    goal_voice_support,
]
