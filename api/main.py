import asyncio
import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from temporalio.api.enums.v1 import WorkflowExecutionStatus
from temporalio.client import Client
from temporalio.exceptions import TemporalError

from goals import goal_list
from goals.voice_agent import goal_voice_support
from models.data_types import AgentGoalWorkflowParams, CombinedInput
from shared.config import TEMPORAL_TASK_QUEUE, get_temporal_client
from workflows.agent_goal_workflow import AgentGoalWorkflow

app = FastAPI()
temporal_client: Optional[Client] = None

# Load environment variables
load_dotenv()


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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def get_conversation_history():
    """Calls the workflow's 'get_conversation_history' query."""
    try:
        handle = temporal_client.get_workflow_handle("agent-workflow")

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
async def send_confirm():
    """Sends a 'confirm' signal to the workflow."""
    workflow_id = "agent-workflow"
    handle = temporal_client.get_workflow_handle(workflow_id)
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


@app.post("/api/v1/voice-initiate")
async def voice_initiate(request: VoiceInitiateRequest):
    """
    Initiate a voice call workflow.

    This endpoint starts a new AgentGoalWorkflow configured for voice support.
    It creates a workflow with the voice agent goal and provides the phone number,
    goal, and context as the initial user prompt.

    Args:
        request: VoiceInitiateRequest containing phone_number, goal, and context

    Returns:
        dict: Contains the workflow_id and status message

    Raises:
        HTTPException: If workflow creation fails
    """
    try:
        # Generate a unique workflow ID for this voice call
        workflow_id = f"voice-call-{uuid.uuid4()}"

        # Create combined input with voice support goal
        combined_input = CombinedInput(
            tool_params=AgentGoalWorkflowParams(None, None),
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

        return {
            "workflow_id": workflow_id,
            "message": f"Voice call workflow initiated successfully",
            "phone_number": request.phone_number,
            "goal": request.goal,
            "context": request.context,
        }

    except TemporalError as e:
        error_message = str(e)
        print(f"Temporal error while initiating voice call: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate voice call workflow: {error_message}",
        )
    except Exception as e:
        error_message = str(e)
        print(f"Unexpected error while initiating voice call: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {error_message}",
        )
