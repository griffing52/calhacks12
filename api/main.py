import asyncio
import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Form, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from temporalio.api.enums.v1 import WorkflowExecutionStatus
from temporalio.client import Client
from temporalio.exceptions import TemporalError
from twilio.twiml.voice_response import VoiceResponse, Dial

from goals import goal_list
from goals.voice_agent import goal_voice_support
from models.data_types import AgentGoalWorkflowParams, CombinedInput
from shared.config import TEMPORAL_TASK_QUEUE, get_temporal_client
from workflows.agent_goal_workflow import AgentGoalWorkflow

app = FastAPI()
temporal_client: Optional[Client] = None

# Load environment variables
load_dotenv("../.env")


# Request models
class VoiceInitiateRequest(BaseModel):
    """Request model for voice call initiation."""

    phone_number: str = Field(
        ...,
        description="Phone number to call in E.164 format (e.g., +14155551234)",
        example="+14155551234",
    )
    goal: str = Field(
        ...,
        description="The goal or reason for the call",
        example="Reset password",
    )
    context: str = Field(
        ...,
        description="Additional context about the user's issue or request",
        example="User is unable to log in to their account",
    )


def get_initial_agent_goal():
    """Get the agent goal from environment variables."""
    env_goal = os.getenv(
        "AGENT_GOAL", "goal_event_flight_invoice"
    )  # if no goal is set in the env file, default to single agent mode
    for listed_goal in goal_list:
        if listed_goal.id == env_goal:
            return listed_goal


@app.on_event("startup")
async def startup_event():
    global temporal_client
    temporal_client = await get_temporal_client()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",  # Allow both localhost and 127.0.0.1
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/webhooks/twilio/status")
async def twilio_status_callback(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    From: Optional[str] = Form(None),
    To: Optional[str] = Form(None)
):
    """
    Twilio sends call status updates here.
    
    Status values: initiated, ringing, in-progress, completed, 
                   busy, failed, no-answer, canceled
    """
    try:
        # Look up workflow by Call SID
        # You'll need to maintain a mapping of Call SID -> Workflow ID
        workflow_id = await get_workflow_id_by_call_sid(CallSid)
        
        if not workflow_id:
            return {"status": "ok", "message": "Workflow not found"}
        
        # Send signal to workflow
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.signal(
            "call_update", 
            CallStatus, 
            f"Call status: {CallStatus}"
        )
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Error in Twilio webhook: {e}")
        return {"status": "error", "message": str(e)}

# Simple in-memory mapping (use Redis/DB for production)
call_sid_to_workflow_id = {}

async def store_call_sid_mapping(call_sid: str, workflow_id: str):
    """Store mapping of Call SID to Workflow ID."""
    call_sid_to_workflow_id[call_sid] = workflow_id

async def get_workflow_id_by_call_sid(call_sid: str) -> Optional[str]:
    """Get Workflow ID for a given Call SID."""
    return call_sid_to_workflow_id.get(call_sid)


async def send_info_to_livekit(call_sid: str, answer: str) -> bool:
    """
    Send user-provided information to the LiveKit AI agent.
    
    This function forwards information from the user (via the web UI) to the
    LiveKit AI agent that is conducting the voice conversation. This enables
    a hybrid flow where sensitive information can be provided via text instead
    of spoken over the phone.
    
    Args:
        call_sid: The Twilio Call SID identifying the active call
        answer: The information/answer provided by the user
    
    Returns:
        True if successfully sent, False otherwise
    
    Implementation Options:
        1. LiveKit Data Channels: Send as data message to the room
        2. LiveKit Webhooks: POST to LiveKit agent's webhook endpoint
        3. LiveKit Server API: Use REST API to send message to agent
        
    Currently implements Option 3 (stub) - would need LiveKit SDK in production.
    """
    try:
        # Get LiveKit configuration
        livekit_url = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.com")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        has_livekit_credentials = all([livekit_api_key, livekit_api_secret])
        
        if not has_livekit_credentials:
            # STUB MODE - Log the information that would be sent
            print(f"[STUB] Would send to LiveKit (Call SID: {call_sid}): {answer}")
            return True
        
        # PRODUCTION MODE - Send via LiveKit API
        # Option 1: Using LiveKit REST API to send data to room/participant
        try:
            import httpx
            from livekit import api
            
            # Initialize LiveKit API client
            # The LiveKit Python SDK provides methods to interact with rooms and participants
            livekit_client = api.LiveKitAPI(
                url=livekit_url.replace("wss://", "https://"),
                api_key=livekit_api_key,
                api_secret=livekit_api_secret
            )
            
            # Find the room associated with this call
            # In practice, you'd need to map Call SID -> Room Name
            # For now, we'll use Call SID as room identifier
            room_name = f"call-{call_sid}"
            
            # Send data message to the room
            # The LiveKit agent in the room will receive this
            await livekit_client.room.send_data(
                room=room_name,
                data=answer.encode('utf-8'),
                kind=api.DataPacket.Kind.RELIABLE,
                destination_sids=[]  # Empty = broadcast to all participants
            )
            
            print(f"✓ Sent info to LiveKit room {room_name}: {answer[:50]}...")
            return True
            
        except ImportError:
            # LiveKit SDK not installed
            print(f"⚠️  LiveKit SDK not installed. Install with: pip install livekit-api")
            print(f"[FALLBACK] Would send to LiveKit: {answer}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending to LiveKit: {e}")
            # Fallback: log the data but don't fail
            print(f"[FALLBACK] Info that failed to send: {answer}")
            return False
    
    except Exception as e:
        print(f"❌ Unexpected error in send_info_to_livekit: {e}")
        return False


async def poll_for_call_sid(workflow_id: str, max_attempts: int = 10, delay: float = 0.5):
    """
    Poll the workflow for Call SID and store the mapping.
    
    This function runs in the background after workflow starts.
    It queries the workflow's voice call status to get the Call SID,
    then stores the mapping for webhook routing.
    
    Args:
        workflow_id: The workflow ID to poll
        max_attempts: Maximum number of polling attempts
        delay: Delay between polling attempts in seconds
    """
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        for attempt in range(max_attempts):
            try:
                # Query workflow for voice call status
                status = await handle.query("get_voice_call_status")
                
                call_sid = status.get("call_sid")
                if call_sid:
                    # Store the mapping
                    await store_call_sid_mapping(call_sid, workflow_id)
                    print(f"✓ Stored Call SID mapping: {call_sid} -> {workflow_id}")
                    return
                
                # Wait before next attempt
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Query might fail if workflow hasn't progressed yet
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                else:
                    print(f"⚠️  Failed to get Call SID for {workflow_id} after {max_attempts} attempts: {e}")
    
    except Exception as e:
        print(f"❌ Error polling for Call SID for {workflow_id}: {e}")

@app.post("/webhooks/livekit/events")
async def livekit_events(request: Request):
    """
    LiveKit AI agent sends events here.
    
    Events:
    - agent_needs_info: AI needs additional info from user
    - call_complete: Call ended successfully
    - call_error: Error during call
    """
    try:
        data = await request.json()
        print(f"[LiveKit Webhook] Received event: {data}")
        
        call_sid = data.get("call_sid")
        event_type = data.get("event_type")
        
        # Get workflow ID
        workflow_id = await get_workflow_id_by_call_sid(call_sid)
        if not workflow_id:
            return {"status": "ok", "message": "Workflow not found"}
        
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Handle different event types
        if event_type == "agent_needs_info":
            question = data.get("question")
            await handle.signal("required_info_needed", question)
        
        elif event_type == "call_complete":
            summary = data.get("summary", "Call completed")
            await handle.signal("call_ended", "goal_complete", summary)
        
        elif event_type == "call_error":
            error = data.get("error", "Unknown error")
            await handle.signal("call_ended", "error", f"Error: {error}")
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Error in LiveKit webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/")
def root():
    return {"message": "Temporal AI Agent!"}


@app.get("/tool-data")
async def get_tool_data():
    """Calls the workflow's 'get_tool_data' query."""
    try:
        # Get workflow handle
        handle = temporal_client.get_workflow_handle("agent-workflow")

        # Check if the workflow is completed
        workflow_status = await handle.describe()
        if workflow_status.status == 2:
            # Workflow is completed; return an empty response
            return {}

        # Query the workflow
        tool_data = await handle.query("get_latest_tool_data")
        return tool_data
    except TemporalError as e:
        # Workflow not found; return an empty response
        print(e)
        return {}


@app.get("/get-conversation-history")
async def get_conversation_history(workflow_id: Optional[str] = None):
    """Calls the workflow's 'get_conversation_history' query.
    
    Args:
        workflow_id: Optional workflow ID. Defaults to 'agent-workflow' for backward compatibility.
    """
    try:
        # Use provided workflow_id or fall back to default
        wf_id = workflow_id or "agent-workflow"
        handle = temporal_client.get_workflow_handle(wf_id)

        failed_states = [
            WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TERMINATED,
            WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_CANCELED,
            WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED,
        ]

        description = await handle.describe()
        if description.status in failed_states:
            print("Workflow is in a failed state. Returning empty history.")
            return []

        # Set a timeout for the query
        try:
            conversation_history = await asyncio.wait_for(
                handle.query("get_conversation_history"),
                timeout=5,  # Timeout after 5 seconds
            )
            return conversation_history
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=404,
                detail="Temporal query timed out (worker may be unavailable).",
            )

    except TemporalError as e:
        error_message = str(e)
        print(f"Temporal error: {error_message}")

        # If worker is down or no poller is available, return a 404
        if "no poller seen for task queue recently" in error_message:
            raise HTTPException(
                status_code=404, detail="Workflow worker unavailable or not found."
            )

        if "workflow not found" in error_message:
            await start_workflow()
            return []
        else:
            # For other Temporal errors, return a 500
            raise HTTPException(
                status_code=500, detail="Internal server error while querying workflow."
            )


@app.get("/agent-goal")
async def get_agent_goal():
    """Calls the workflow's 'get_agent_goal' query."""
    try:
        # Get workflow handle
        handle = temporal_client.get_workflow_handle("agent-workflow")

        # Check if the workflow is completed
        workflow_status = await handle.describe()
        if workflow_status.status == 2:
            # Workflow is completed; return an empty response
            return {}

        # Query the workflow
        agent_goal = await handle.query("get_agent_goal")
        return agent_goal
    except TemporalError as e:
        # Workflow not found; return an empty response
        print(e)
        return {}

@app.post("/webhooks/twilio/voice")
async def twilio_voice_twiml(
    CallSid: str = Form(...),
    From: str = Form(...)
):
    """
    Twilio calls this endpoint when call connects.
    Returns TwiML to forward call to LiveKit via SIP.
    """
    try:
        print(f"[TwiML-SIP] Generating TwiML for Call SID: {CallSid}, From: {From}")

        twilio_phone = os.getenv("TWILIO_PHONE_NUMBER", "+13105825023")

        # LiveKit SIP URI from project settings
        # The SIP domain is DIFFERENT from the WebSocket subdomain!
        # Must include phone number in SIP URI for LiveKit to route correctly
        livekit_sip_uri = f"sip:{twilio_phone}@4uw4hf4g79e.sip.livekit.cloud"

        print(f"[TwiML-SIP] Forwarding to LiveKit SIP URI: {livekit_sip_uri}")

        # Use Twilio VoiceResponse library for proper TwiML generation
        response = VoiceResponse()
        dial = Dial()
        dial.sip(livekit_sip_uri)
        response.append(dial)

        twiml_str = str(response)
        print(f"[TwiML-SIP] TwiML generated successfully")
        return Response(content=twiml_str, media_type="application/xml")

    except Exception as e:
        print(f"[TwiML-SIP] Error generating TwiML: {e}")
        import traceback
        traceback.print_exc()

        # Fallback TwiML
        response = VoiceResponse()
        response.say("Sorry, an error occurred connecting to the assistant.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

@app.post("/send-prompt")
async def send_prompt(prompt: str):
    # Create combined input with goal from environment
    combined_input = CombinedInput(
        tool_params=AgentGoalWorkflowParams(None, None),
        agent_goal=get_initial_agent_goal(),
        # change to get from workflow query
    )

    workflow_id = "agent-workflow"

    # Start (or signal) the workflow
    await temporal_client.start_workflow(
        AgentGoalWorkflow.run,
        combined_input,
        id=workflow_id,
        task_queue=TEMPORAL_TASK_QUEUE,
        start_signal="user_prompt",
        start_signal_args=[prompt],
    )

    return {"message": f"Prompt '{prompt}' sent to workflow {workflow_id}."}


@app.post("/confirm")
async def send_confirm(workflow_id: Optional[str] = None):
    """Sends a 'confirm' signal to the workflow.
    
    Args:
        workflow_id: Optional workflow ID. Defaults to 'agent-workflow' for backward compatibility.
    """
    wf_id = workflow_id or "agent-workflow"
    handle = temporal_client.get_workflow_handle(wf_id)
    await handle.signal("confirm")
    return {"message": "Confirm signal sent."}


@app.post("/end-chat")
async def end_chat():
    """Sends a 'end_chat' signal to the workflow."""
    workflow_id = "agent-workflow"

    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.signal("end_chat")
        return {"message": "End chat signal sent."}
    except TemporalError as e:
        print(e)
        # Workflow not found; return an empty response
        return {}


@app.post("/start-workflow")
async def start_workflow():
    initial_agent_goal = get_initial_agent_goal()

    # Create combined input
    combined_input = CombinedInput(
        tool_params=AgentGoalWorkflowParams(None, None),
        agent_goal=initial_agent_goal,
    )

    workflow_id = "agent-workflow"

    # Start the workflow with the starter prompt from the goal
    await temporal_client.start_workflow(
        AgentGoalWorkflow.run,
        combined_input,
        id=workflow_id,
        task_queue=TEMPORAL_TASK_QUEUE,
        start_signal="user_prompt",
        start_signal_args=["### " + initial_agent_goal.starter_prompt],
    )

    return {
        "message": f"Workflow started with goal's starter prompt: {initial_agent_goal.starter_prompt}."
    }

@app.post("/api/v1/voice-provide-info")
async def voice_provide_info(
    workflow_id: str,
    answer: str
):
    """
    Frontend calls this when user provides info.
    This endpoint forwards the answer to LiveKit.
    """
    try:
        # Send signal to workflow
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.signal("voice_info_provided", answer)
        
        # Also forward to LiveKit AI agent
        call_sid = None
        for sid, wf_id in call_sid_to_workflow_id.items():
            if wf_id == workflow_id:
                call_sid = sid
                break
        
        if call_sid:
            # Send to LiveKit (implementation depends on LiveKit setup)
            await send_info_to_livekit(call_sid, answer)
        
        return {"status": "ok"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}



@app.post("/api/v1/voice-initiate")
async def voice_initiate(request: VoiceInitiateRequest, background_tasks: BackgroundTasks):
    """
    Initiate a voice call workflow.

    This endpoint starts a new AgentGoalWorkflow configured for voice support.
    It creates a workflow with the voice agent goal and provides the phone number,
    goal, and context as the initial user prompt.
    
    After starting the workflow, it polls in the background for the Call SID
    and stores the mapping for webhook routing.

    Args:
        request: VoiceInitiateRequest containing phone_number, goal, and context
        background_tasks: FastAPI background tasks for async polling

    Returns:
        dict: Contains the workflow_id and status message

    Raises:
        HTTPException: If workflow creation fails
    """
    import time
    start_time = time.time()
   
    try:
        # Generate a unique workflow ID for this voice call
        workflow_id = f"voice-call-{uuid.uuid4()}"

        # Create combined input with voice support goal
        combined_input = CombinedInput(
            tool_params=AgentGoalWorkflowParams(
                conversation_summary=None,
                prompt_queue=None
            ),
            agent_goal=goal_voice_support,
        )

        # Construct the initial prompt with all the information
        # This prompt will guide the agent to collect any missing info and initiate the call
        initial_prompt = (
            f"Initiate voice call to {request.phone_number} "
            f"with goal: {request.goal} "
            f"and context: {request.context}"
        )

        # Start the workflow with the voice support goal and initial prompt
        await temporal_client.start_workflow(
            AgentGoalWorkflow.run,
            combined_input,
            id=workflow_id,
            task_queue=TEMPORAL_TASK_QUEUE,
            start_signal="user_prompt",
            start_signal_args=[initial_prompt],
        )

        # Add background task to poll for Call SID and store mapping
        # This allows the endpoint to return immediately while the Call SID
        # is retrieved asynchronously from the workflow
        background_tasks.add_task(poll_for_call_sid, workflow_id)

        response = {
            "workflow_id": workflow_id,
            "message": f"Voice call workflow initiated successfully",
            "phone_number": request.phone_number,
            "goal": request.goal,
            "context": request.context,
        }
        return response

    except TemporalError as e:
        elapsed = time.time() - start_time
        error_message = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate voice call workflow: {error_message}",
        )
    except Exception as e:
        elapsed = time.time() - start_time
        error_message = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {error_message}",
        )


@app.get("/voice-call-status/{workflow_id}")
async def get_voice_call_status(workflow_id: str):
    """
    Get the current status of a voice call workflow.
    
    Returns:
    - status: Workflow execution status (RUNNING, COMPLETED, FAILED, etc.)
    - conversation_history: Recent conversation messages
    - call_sid: Twilio Call SID if available
    - voice_status: Voice call specific status (active, pending questions, etc.)
    """
    try:
        if not temporal_client:
            raise HTTPException(status_code=503, detail="Temporal client not initialized")
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Get workflow description to check status
        description = await handle.describe()
        
        # Query conversation history
        try:
            conversation_history = await handle.query(
                AgentGoalWorkflow.get_conversation_history
            )
        except Exception as e:
            print(f"[voice-call-status] Warning: Could not query conversation history: {e}")
            conversation_history = []
        
        # Query voice call specific status
        voice_status = None
        try:
            voice_status = await handle.query(
                AgentGoalWorkflow.get_voice_call_status
            )
        except Exception as e:
            print(f"[voice-call-status] Warning: Could not query voice call status: {e}")
            voice_status = {
                "active": False,
                "call_sid": None,
                "status": "unknown",
                "info_needed": False,
                "pending_question": None
            }
        
        return {
            "workflow_id": workflow_id,
            "status": description.status.name,
            "conversation_history": conversation_history,
            "voice_status": voice_status,
            "call_sid": voice_status.get("call_sid") if voice_status else None,
            "run_id": description.run_id,
            "start_time": description.start_time.isoformat() if description.start_time else None,
        }
    
    except Exception as e:
        print(f"[voice-call-status] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get voice call status: {str(e)}"
        )




@app.post("/voice-provide-answer/{workflow_id}")
async def provide_voice_answer(workflow_id: str, answer: str = Form(...)):
    """
    Provide an answer to a question from the voice AI.
    
    This endpoint allows the UI to send answers back to the workflow
    when the voice AI needs clarification during a call.
    """
    try:
        if not temporal_client:
            raise HTTPException(status_code=503, detail="Temporal client not initialized")
        
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.signal(AgentGoalWorkflow.voice_info_provided, answer)
        
        print(f"[voice-provide-answer] Sent answer to workflow {workflow_id}")
        
        return {
            "status": "success",
            "message": "Answer provided to voice assistant",
            "workflow_id": workflow_id
        }
    
    except Exception as e:
        print(f"[voice-provide-answer] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to provide answer: {str(e)}"
        )
