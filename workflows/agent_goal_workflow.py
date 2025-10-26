from collections import deque
from datetime import timedelta
from typing import Any, Deque, Dict, List, Optional, TypedDict, Union

from temporalio import workflow
from temporalio.common import RetryPolicy

from models.data_types import (
    ConversationHistory,
    EnvLookupInput,
    EnvLookupOutput,
    NextStep,
    ValidationInput,
)
from models.tool_definitions import AgentGoal
from workflows import workflow_helpers as helpers
from workflows.workflow_helpers import (
    LLM_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
    LLM_ACTIVITY_START_TO_CLOSE_TIMEOUT,
)

with workflow.unsafe.imports_passed_through():
    from activities.tool_activities import ToolActivities, mcp_list_tools
    from goals import goal_list
    from models.data_types import CombinedInput, ToolPromptInput
    from prompts.agent_prompt_generators import generate_genai_prompt
    from tools.tool_registry import create_mcp_tool_definitions

# Constants
MAX_TURNS_BEFORE_CONTINUE = 250


# ToolData as part of the workflow is what's accessible to the UI - see LLMResponse.jsx for example
class ToolData(TypedDict, total=False):
    next: NextStep
    tool: str
    args: Dict[str, Any]
    response: str
    force_confirm: bool = True


@workflow.defn
class AgentGoalWorkflow:
    """Workflow that manages tool execution with user confirmation and conversation history."""

    def __init__(self) -> None:
        self.conversation_history: ConversationHistory = {"messages": []}
        self.prompt_queue: Deque[str] = deque()
        self.conversation_summary: Optional[str] = None
        self.chat_ended: bool = False
        self.tool_data: Optional[ToolData] = None
        self.confirmed: bool = (
            False  # indicates that we have confirmation to proceed to run tool
        )
        self.tool_results: List[Dict[str, Any]] = []
        self.goal: AgentGoal = {"tools": []}
        self.show_tool_args_confirmation: bool = (
            True  # set from env file in activity lookup_wf_env_settings
        )
        self.multi_goal_mode: bool = (
            False  # set from env file in activity lookup_wf_env_settings
        )
        self.mcp_tools_info: Optional[dict] = None  # stores complete MCP tools result
        
        # Voice call specific state
        self.voice_call_active: bool = False  # indicates an active voice call
        self.voice_call_sid: Optional[str] = None  # Twilio Call SID for tracking
        self.voice_call_status: str = "not_started"  # not_started, initiated, ringing, in_progress, completed, failed
        self.voice_info_needed: bool = False  # indicates LiveKit AI needs info from user
        self.voice_pending_question: Optional[str] = None  # question from LiveKit AI

    # see ../api/main.py#temporal_client.start_workflow() for how the input parameters are set
    @workflow.run
    async def run(self, combined_input: CombinedInput) -> str:
        """Main workflow execution method."""
        # setup phase, starts with blank tool_params and agent_goal prompt as defined in tools/goal_registry.py
        params = combined_input.tool_params
        self.goal = combined_input.agent_goal

        await self.lookup_wf_env_settings(combined_input)

        # If the goal has an MCP server definition, dynamically load MCP tools
        if self.goal.mcp_server_definition:
            await self.load_mcp_tools()

        # add message from sample conversation provided in tools/goal_registry.py, if it exists
        if params and params.conversation_summary:
            self.add_message("conversation_summary", params.conversation_summary)
            self.conversation_summary = params.conversation_summary

        if params and params.prompt_queue:
            self.prompt_queue.extend(params.prompt_queue)

        waiting_for_confirm = False
        current_tool = None

        # This is the main interactive loop. Main responsibilities:
        #   - Selecting and changing goals as directed by the user
        #   - reacting to user input (from signals)
        #   - validating user input to make sure it makes sense with the current goal and tools
        #   - calling the LLM through activities to determine next steps and prompts
        #   - executing the selected tools via activities
        while True:
            # wait indefinitely for input from signals - user_prompt, end_chat, or confirm as defined below
            await workflow.wait_condition(
                lambda: bool(self.prompt_queue) or self.chat_ended or self.confirmed
            )

            # handle chat should end. When chat ends, push conversation history to workflow results.
            if self.chat_should_end():
                return f"{self.conversation_history}"

            # Execute the tool
            if self.ready_for_tool_execution(waiting_for_confirm, current_tool):
                waiting_for_confirm = await self.execute_tool(current_tool)
                continue

            # process forward on the prompt queue if any
            if self.prompt_queue:
                # get most recent prompt
                prompt = self.prompt_queue.popleft()
                workflow.logger.info(
                    f"workflow step: processing message on the prompt queue, message is {prompt}"
                )

                # Validate user-provided prompts
                if self.is_user_prompt(prompt):
                    self.add_message("user", prompt)

                    # Validate the prompt before proceeding
                    validation_input = ValidationInput(
                        prompt=prompt,
                        conversation_history=self.conversation_history,
                        agent_goal=self.goal,
                    )
                    validation_result = await workflow.execute_activity_method(
                        ToolActivities.agent_validatePrompt,
                        args=[validation_input],
                        schedule_to_close_timeout=LLM_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
                        start_to_close_timeout=LLM_ACTIVITY_START_TO_CLOSE_TIMEOUT,
                        retry_policy=RetryPolicy(
                            initial_interval=timedelta(seconds=5), backoff_coefficient=1
                        ),
                    )

                    # If validation fails, provide that feedback to the user - i.e., "your words make no sense, puny human" end this iteration of processing
                    if not validation_result.validationResult:
                        workflow.logger.warning(
                            f"Prompt validation failed: {validation_result.validationFailedReason}"
                        )
                        self.add_message(
                            "agent", validation_result.validationFailedReason
                        )
                        continue

                # If valid, proceed with generating the context and prompt
                context_instructions = generate_genai_prompt(
                    agent_goal=self.goal,
                    conversation_history=self.conversation_history,
                    multi_goal_mode=self.multi_goal_mode,
                    raw_json=self.tool_data,
                    mcp_tools_info=self.mcp_tools_info,
                )

                prompt_input = ToolPromptInput(
                    prompt=prompt, context_instructions=context_instructions
                )

                # connect to LLM and execute to get next steps
                tool_data = await workflow.execute_activity_method(
                    ToolActivities.agent_toolPlanner,
                    prompt_input,
                    schedule_to_close_timeout=LLM_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
                    start_to_close_timeout=LLM_ACTIVITY_START_TO_CLOSE_TIMEOUT,
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5), backoff_coefficient=1
                    ),
                )

                tool_data["force_confirm"] = self.show_tool_args_confirmation
                self.tool_data = tool_data

                # process the tool as dictated by the prompt response - what to do next, and with which tool
                next_step = tool_data.get("next")
                current_tool = tool_data.get("tool")

                workflow.logger.info(
                    f"next_step: {next_step}, current tool is {current_tool}"
                )

                # make sure we're ready to run the tool & have everything we need
                if next_step == "confirm" and current_tool:
                    args = tool_data.get("args", {})
                    # if we're missing arguments, ask for them
                    if await helpers.handle_missing_args(
                        current_tool, args, tool_data, self.prompt_queue
                    ):
                        continue

                    waiting_for_confirm = True

                    # We have needed arguments, if we want to force the user to confirm, set that up
                    if self.show_tool_args_confirmation:
                        self.confirmed = False  # set that we're not confirmed
                        workflow.logger.info("Waiting for user confirm signal...")
                    # if we have all needed arguments (handled above) and not holding for a debugging confirm, proceed:
                    else:
                        self.confirmed = True
                # else if the next step is to pick a new goal, set that to be the goal
                elif next_step == "pick-new-goal":
                    workflow.logger.info("All steps completed. Resetting goal.")
                    self.change_goal("goal_choose_agent_type")

                # else if the next step is to be done with the conversation such as if the user requests it via asking to "end conversation"
                elif next_step == "done":
                    self.add_message("agent", tool_data)

                    # here we could send conversation to AI for analysis

                    # end the workflow
                    return str(self.conversation_history)

                self.add_message("agent", tool_data)
                await helpers.continue_as_new_if_needed(
                    self.conversation_history,
                    self.prompt_queue,
                    self.goal,
                    MAX_TURNS_BEFORE_CONTINUE,
                    self.add_message,
                )

    # Signal that comes from api/main.py via a post to /send-prompt
    @workflow.signal
    async def user_prompt(self, prompt: str) -> None:
        """Signal handler for receiving user prompts."""
        workflow.logger.info(f"signal received: user_prompt, prompt is {prompt}")
        if self.chat_ended:
            workflow.logger.info(f"Message dropped due to chat closed: {prompt}")
            return
        self.prompt_queue.append(prompt)

    # Signal that comes from api/main.py via a post to /confirm
    @workflow.signal
    async def confirm(self) -> None:
        """Signal handler for user confirmation of tool execution."""
        workflow.logger.info("Received user signal: confirmation")
        self.confirmed = True

    # Signal that comes from api/main.py via a post to /end-chat
    @workflow.signal
    async def end_chat(self) -> None:
        """Signal handler for ending the chat session."""
        workflow.logger.info("signal received: end_chat")
        self.chat_ended = True

    # Signal that can be sent from Temporal Workflow UI to enable debugging confirm and override .env setting
    @workflow.signal
    async def enable_debugging_confirm(self) -> None:
        """Signal handler for enabling debugging confirm UI & associated logic."""
        workflow.logger.info("signal received: enable_debugging_confirm")
        self.enable_debugging_confirm = True

    # Signal that can be sent from Temporal Workflow UI to disable debugging confirm and override .env setting
    @workflow.signal
    async def disable_debugging_confirm(self) -> None:
        """Signal handler for disabling debugging confirm UI & associated logic."""
        workflow.logger.info("signal received: disable_debugging_confirm")
        self.enable_debugging_confirm = False

    # ========== Voice Call Signals ==========
    
    @workflow.signal
    async def call_update(self, status: str, message: str) -> None:
        """
        Signal handler for voice call status updates from external services (Twilio/LiveKit webhooks).
        
        Args:
            status: Call status (e.g., "initiated", "ringing", "in_progress", "completed")
            message: Human-readable status message
        
        Example:
            await workflow_handle.signal("call_update", "ringing", "Call is ringing...")
        """
        workflow.logger.info(f"signal received: call_update, status={status}, message={message}")
        
        self.voice_call_status = status
        
        # Add update to conversation history
        update_data = {
            "status": status,
            "message": message,
            "call_sid": self.voice_call_sid,
            "timestamp": workflow.now().isoformat()
        }
        self.add_message("voice_call_update", update_data)
        
        # Update active status based on call status
        if status in ["completed", "failed", "no-answer", "busy", "canceled"]:
            self.voice_call_active = False
            workflow.logger.info(f"Voice call ended with status: {status}")
        elif status in ["initiated", "ringing", "in_progress"]:
            self.voice_call_active = True
    
    @workflow.signal
    async def call_ended(self, reason: str, final_summary: str) -> None:
        """
        Signal handler for voice call termination.
        
        Args:
            reason: Reason for call ending (e.g., "caller_hung_up", "goal_complete", "error")
            final_summary: Summary of what was accomplished during the call
        
        Example:
            await workflow_handle.signal("call_ended", "goal_complete", "Password successfully reset")
        """
        workflow.logger.info(f"signal received: call_ended, reason={reason}")
        
        self.voice_call_active = False
        self.voice_call_status = "completed"
        
        # Add termination info to conversation history
        end_data = {
            "reason": reason,
            "summary": final_summary,
            "call_sid": self.voice_call_sid,
            "timestamp": workflow.now().isoformat()
        }
        self.add_message("voice_call_ended", end_data)
        
        # Add a prompt to process the call completion
        completion_prompt = f"###Voice call ended. Reason: {reason}. Summary: {final_summary}"
        self.prompt_queue.append(completion_prompt)
        
        workflow.logger.info(f"Voice call completed: {final_summary}")
    
    @workflow.signal
    async def required_info_needed(self, question: str) -> None:
        """
        Signal handler for when LiveKit AI needs additional information from the user.
        
        Args:
            question: Question that needs to be answered by the user
        
        Example:
            await workflow_handle.signal("required_info_needed", "What is your confirmation code?")
        """
        workflow.logger.info(f"signal received: required_info_needed, question={question}")
        
        self.voice_info_needed = True
        self.voice_pending_question = question
        
        # Add the question to conversation history
        question_data = {
            "question": question,
            "call_sid": self.voice_call_sid,
            "timestamp": workflow.now().isoformat(),
            "awaiting_response": True
        }
        self.add_message("voice_info_request", question_data)
        
        # Add a prompt to ask the user for the information
        info_prompt = f"###The voice assistant needs additional information: {question}"
        self.prompt_queue.append(info_prompt)
        
        workflow.logger.info(f"Voice AI needs info: {question}")
    
    @workflow.signal
    async def voice_info_provided(self, answer: str) -> None:
        """
        Signal handler for when user provides requested information to the voice AI.
        
        Args:
            answer: The user's answer to the pending question
        
        Example:
            await workflow_handle.signal("voice_info_provided", "123456")
        """
        workflow.logger.info(f"signal received: voice_info_provided, answer provided")
        
        if not self.voice_info_needed:
            workflow.logger.warning("Received voice_info_provided but no info was needed")
            return
        
        self.voice_info_needed = False
        
        # Add the answer to conversation history
        answer_data = {
            "question": self.voice_pending_question,
            "answer": answer,
            "call_sid": self.voice_call_sid,
            "timestamp": workflow.now().isoformat()
        }
        self.add_message("voice_info_response", answer_data)
        
        self.voice_pending_question = None
        
        workflow.logger.info("Voice info provided by user")

    @workflow.query
    def get_conversation_history(self) -> ConversationHistory:
        """Query handler to retrieve the full conversation history."""
        return self.conversation_history

    @workflow.query
    def get_agent_goal(self) -> AgentGoal:
        """Query handler to retrieve the current goal of the agent."""
        return self.goal

    @workflow.query
    def get_summary_from_history(self) -> Optional[str]:
        """Query handler to retrieve the conversation summary if available.
        Used only for continue as new of the workflow."""
        return self.conversation_summary

    @workflow.query
    def get_latest_tool_data(self) -> Optional[ToolData]:
        """Query handler to retrieve the latest tool data response if available."""
        return self.tool_data

    @workflow.query
    def get_voice_call_status(self) -> Dict[str, Any]:
        """
        Query handler to retrieve current voice call status.
        
        Returns:
            Dictionary containing:
                - active: bool - Whether a voice call is currently active
                - call_sid: str - Twilio Call SID (if available)
                - status: str - Current call status
                - info_needed: bool - Whether additional info is needed from user
                - pending_question: str - Question awaiting answer (if any)
        """
        return {
            "active": self.voice_call_active,
            "call_sid": self.voice_call_sid,
            "status": self.voice_call_status,
            "info_needed": self.voice_info_needed,
            "pending_question": self.voice_pending_question
        }

    def add_message(self, actor: str, response: Union[str, Dict[str, Any]]) -> None:
        """Add a message to the conversation history.

        Args:
            actor: The entity that generated the message (e.g., "user", "agent")
            response: The message content, either as a string or structured data
        """
        if isinstance(response, dict):
            response_str = str(response)
            workflow.logger.debug(f"Adding {actor} message: {response_str[:100]}...")
        else:
            workflow.logger.debug(f"Adding {actor} message: {response[:100]}...")

        self.conversation_history["messages"].append(
            {"actor": actor, "response": response}
        )

    def change_goal(self, goal: str) -> None:
        """Change the goal (usually on request of the user).

        Args:
            goal: goal to change to)
        """
        if goal is not None:
            for listed_goal in goal_list:
                if listed_goal.id == goal:
                    self.goal = listed_goal
                    workflow.logger.info("Changed goal to " + goal)
            if goal is None:
                workflow.logger.warning(
                    "Goal not set after goal reset, probably bad."
                )  # if this happens, there's probably a problem with the goal list

    # workflow function that defines if chat should end
    def chat_should_end(self) -> bool:
        if self.chat_ended:
            workflow.logger.info("Chat-end signal received. Chat ending.")
            return True
        else:
            return False

    # define if we're ready for tool execution
    def ready_for_tool_execution(
        self, waiting_for_confirm: bool, current_tool: Any
    ) -> bool:
        if self.confirmed and waiting_for_confirm and current_tool and self.tool_data:
            return True
        else:
            return False

    # LLM-tagged prompts start with "###"
    # all others are from the user
    def is_user_prompt(self, prompt) -> bool:
        if prompt.startswith("###"):
            return False
        else:
            return True

    # look up env settings in an activity so they're part of history
    async def lookup_wf_env_settings(self, combined_input: CombinedInput) -> None:
        env_lookup_input = EnvLookupInput(
            show_confirm_env_var_name="SHOW_CONFIRM",
            show_confirm_default=True,
        )
        env_output: EnvLookupOutput = await workflow.execute_activity_method(
            ToolActivities.get_wf_env_vars,
            env_lookup_input,
            start_to_close_timeout=LLM_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5), backoff_coefficient=1
            ),
        )
        self.show_tool_args_confirmation = env_output.show_confirm
        self.multi_goal_mode = env_output.multi_goal_mode

    # execute the tool - return False if we're not waiting for confirm anymore (always the case if it works successfully)
    #
    async def execute_tool(self, current_tool: str) -> bool:
        workflow.logger.info(
            f"workflow step: user has confirmed, executing the tool {current_tool}"
        )
        self.confirmed = False
        waiting_for_confirm = False
        confirmed_tool_data = self.tool_data.copy()
        confirmed_tool_data["next"] = "user_confirmed_tool_run"
        self.add_message("user_confirmed_tool_run", confirmed_tool_data)

        # Special handling for voice call initiation
        if current_tool == "InitiateVoiceCall":
            await self.execute_voice_call()
            return waiting_for_confirm

        # execute the tool by key as defined in tools/__init__.py
        await helpers.handle_tool_execution(
            current_tool,
            self.tool_data,
            self.tool_results,
            self.add_message,
            self.prompt_queue,
            self.goal,
        )

        # set new goal if we should
        if len(self.tool_results) > 0:
            if (
                "ChangeGoal" in self.tool_results[-1].values()
                and "new_goal" in self.tool_results[-1].keys()
            ):
                new_goal = self.tool_results[-1].get("new_goal")
                self.change_goal(new_goal)
            elif (
                "ListAgents" in self.tool_results[-1].values()
                and self.goal.id != "goal_choose_agent_type"
            ):
                self.change_goal("goal_choose_agent_type")
        return waiting_for_confirm

    async def execute_voice_call(self) -> None:
        """
        Execute voice call initiation and enter waiting state for call events.
        
        This method:
        1. Executes the InitiateVoiceCall activity
        2. Stores the Call SID for tracking
        3. Sets voice_call_active = True
        4. Waits for external signals (call_update, call_ended, required_info_needed)
        """
        workflow.logger.info("Executing voice call initiation")
        
        # Execute the voice call activity
        await helpers.handle_tool_execution(
            "InitiateVoiceCall",
            self.tool_data,
            self.tool_results,
            self.add_message,
            self.prompt_queue,
            self.goal,
        )
        
        # Extract call result
        if len(self.tool_results) > 0:
            call_result = self.tool_results[-1]
            
            if call_result.get("status") == "success":
                self.voice_call_sid = call_result.get("call_sid")
                self.voice_call_active = True
                self.voice_call_status = "initiated"
                
                workflow.logger.info(
                    f"Voice call initiated successfully. Call SID: {self.voice_call_sid}"
                )
                
                # Add notification that we're waiting for call events
                waiting_message = {
                    "next": "question",
                    "response": f"Voice call initiated to {self.tool_data.get('args', {}).get('phone_number')}. "
                               f"Waiting for call to connect... You can track the call status or end this chat. "
                               f"I'll update you when the call progresses or completes."
                }
                self.add_message("agent", waiting_message)
                
                # The workflow will continue running, waiting for signals:
                # - call_update: for status updates
                # - call_ended: for completion
                # - required_info_needed: if LiveKit AI needs info
                # - user_prompt: if user sends messages during the call
                # - end_chat: if user ends the session
                
            else:
                # Call initiation failed
                error_message = call_result.get("error", "Unknown error")
                workflow.logger.error(f"Voice call initiation failed: {error_message}")
                
                failure_response = {
                    "next": "question",
                    "response": f"Failed to initiate voice call: {error_message}. "
                               f"Would you like to try again or get help another way?"
                }
                self.add_message("agent", failure_response)

    # debugging helper - drop this in various places in the workflow to get status
    # also don't forget you can look at the workflow itself and do queries if you want
    def print_useful_workflow_vars(self, status_or_step: str) -> None:
        print(f"***{status_or_step}:***")
        if self.goal:
            print(f"current goal: {self.goal.id}")
        if self.tool_data:
            print(f"force confirm? {self.tool_data['force_confirm']}")
            print(f"next step: {self.tool_data.get('next')}")
            print(f"current_tool: {self.tool_data.get('tool')}")
        else:
            print("no tool data initialized yet")
        print(f"self.confirmed: {self.confirmed}")

    async def load_mcp_tools(self) -> None:
        """Load MCP tools dynamically from the server definition"""
        if not self.goal.mcp_server_definition:
            return

        workflow.logger.info(
            f"Loading MCP tools from server: {self.goal.mcp_server_definition.name}"
        )

        # Get the list of tools to include (if specified)
        include_tools = self.goal.mcp_server_definition.included_tools

        # Call the MCP list tools activity
        mcp_tools_result = await workflow.execute_activity(
            mcp_list_tools,
            args=[self.goal.mcp_server_definition, include_tools],
            start_to_close_timeout=LLM_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5), backoff_coefficient=1
            ),
            summary=f"{self.goal.mcp_server_definition.name}",
        )

        if mcp_tools_result.get("success", False):
            tools_info = mcp_tools_result.get("tools", {})
            workflow.logger.info(f"Successfully loaded {len(tools_info)} MCP tools")

            # Store complete MCP tools result for use in prompt generation
            self.mcp_tools_info = mcp_tools_result

            # Convert MCP tools to ToolDefinition objects and add to goal
            mcp_tool_definitions = create_mcp_tool_definitions(tools_info)
            self.goal.tools.extend(mcp_tool_definitions)

            workflow.logger.info(f"Added {len(mcp_tool_definitions)} MCP tools to goal")
        else:
            error_msg = mcp_tools_result.get("error", "Unknown error")
            workflow.logger.error(f"Failed to load MCP tools: {error_msg}")
            # Continue execution without MCP tools
