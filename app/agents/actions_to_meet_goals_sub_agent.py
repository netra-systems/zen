# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:58.914949+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to sub-agents
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: ca70b55b-5f0c-4900-9648-9218422567b5 | Seq: 5
# Review: Pending | Score: 85
# ================================
import json

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import actions_to_meet_goals_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response, extract_partial_json
from app.logging_config import central_logger as logger
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_communication, log_agent_input, log_agent_output
)
from app.core.reliability_utils import create_agent_reliability_wrapper
from app.core.fallback_utils import create_agent_fallback_strategy
from app.agents.input_validation import validate_agent_input


class ActionsToMeetGoalsSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ActionsToMeetGoalsSubAgent", description="This agent creates a plan of action.")
        self.tool_dispatcher = tool_dispatcher
        
        # Initialize reliability wrapper and fallback strategy
        self.reliability = create_agent_reliability_wrapper("ActionsToMeetGoalsSubAgent")
        self.fallback_strategy = create_agent_fallback_strategy("ActionsToMeetGoalsSubAgent")

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have optimizations and data results to work with."""
        return state.optimizations_result is not None and state.data_result is not None
    
    @validate_agent_input('ActionsToMeetGoalsSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the actions to meet goals logic."""
        # Log agent communication start
        log_agent_communication("Supervisor", "ActionsToMeetGoalsSubAgent", run_id, "execute_request")
        
        main_executor = self._create_main_executor(state, run_id, stream_updates)
        fallback_executor = self._create_fallback_executor(state, run_id, stream_updates)
        result = await self._execute_with_protection(main_executor, fallback_executor, run_id)
        await self._apply_reliability_protection(result)
        
        # Log agent communication completion
        log_agent_communication("ActionsToMeetGoalsSubAgent", "Supervisor", run_id, "execute_response")

    def _create_main_executor(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create main execution function."""
        async def _execute_action_plan():
            await self._send_processing_update(run_id, stream_updates)
            prompt = self._build_action_plan_prompt(state)
            llm_response = await self._get_llm_response(prompt, run_id)
            action_plan_result = await self._process_llm_response(llm_response, run_id)
            state.action_plan_result = action_plan_result
            await self._send_completion_update(run_id, stream_updates, action_plan_result)
            return action_plan_result
        return _execute_action_plan

    def _create_fallback_executor(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create fallback execution function."""
        async def _fallback_action_plan():
            fallback_result = self.fallback_strategy.create_default_fallback_result(
                "action_plan_generation", **self._get_default_action_plan())
            state.action_plan_result = fallback_result
            await self._send_fallback_update(run_id, stream_updates, fallback_result)
            return fallback_result
        return _fallback_action_plan

    async def _send_processing_update(self, run_id: str, stream_updates: bool):
        """Send processing status update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Creating action plan based on optimization strategies..."
            })

    def _build_action_plan_prompt(self, state: DeepAgentState) -> str:
        """Build prompt for action plan generation."""
        return actions_to_meet_goals_prompt_template.format(
            optimizations=state.optimizations_result,
            data=state.data_result,
            user_request=state.user_request
        )

    async def _get_llm_response(self, prompt: str, run_id: str) -> str:
        """Get response from LLM with size monitoring."""
        correlation_id = generate_llm_correlation_id()
        
        # Start heartbeat for LLM operation
        start_llm_heartbeat(correlation_id, "ActionsToMeetGoalsSubAgent")
        
        try:
            self._log_prompt_size(prompt, run_id)
            
            # Log input to LLM
            log_agent_input("ActionsToMeetGoalsSubAgent", "LLM", len(prompt), correlation_id)
            
            llm_response = await self.llm_manager.ask_llm(prompt, llm_config_name='actions_to_meet_goals')
            
            # Log output from LLM
            log_agent_output("LLM", "ActionsToMeetGoalsSubAgent", 
                           len(llm_response) if llm_response else 0, "success", correlation_id)
            
            self._log_response_size(llm_response, run_id)
            return llm_response
        finally:
            # Stop heartbeat
            stop_llm_heartbeat(correlation_id)

    def _log_prompt_size(self, prompt: str, run_id: str):
        """Log prompt size if large."""
        response_size_mb = len(prompt) / (1024 * 1024)
        if response_size_mb > 1:
            logger.info(f"Large prompt detected ({response_size_mb:.2f}MB) for run_id: {run_id}")

    def _log_response_size(self, llm_response: str, run_id: str):
        """Log LLM response size."""
        if llm_response:
            logger.debug(f"Received LLM response of {len(llm_response)} characters for run_id: {run_id}")

    async def _process_llm_response(self, llm_response: str, run_id: str) -> dict:
        """Process LLM response with fallback extraction."""
        action_plan_result = extract_json_from_response(llm_response, max_retries=5)
        if not action_plan_result:
            action_plan_result = await self._handle_extraction_failure(llm_response, run_id)
        return action_plan_result

    async def _handle_extraction_failure(self, llm_response: str, run_id: str) -> dict:
        """Handle JSON extraction failure with partial recovery."""
        self._log_extraction_failure(llm_response, run_id)
        partial_result = extract_partial_json(llm_response, required_fields=None)
        if partial_result:
            return self._process_partial_extraction(partial_result, run_id)
        else:
            return self._create_error_fallback_plan(llm_response, run_id)

    def _log_extraction_failure(self, llm_response: str, run_id: str):
        """Log JSON extraction failure details."""
        response_length = len(llm_response) if llm_response else 0
        logger.debug(f"Full JSON extraction failed for run_id: {run_id}. "
                    f"Response length: {response_length} chars. Attempting partial extraction...")

    def _process_partial_extraction(self, partial_result: dict, run_id: str) -> dict:
        """Process partial extraction results."""
        field_count = len(partial_result)
        if field_count > 10:
            logger.info(f"Successfully recovered {field_count} fields via partial extraction for run_id: {run_id}")
        else:
            logger.warning(f"Partial extraction recovered only {field_count} fields for run_id: {run_id}")
        return self._build_action_plan_from_partial(partial_result)

    def _create_error_fallback_plan(self, llm_response: str, run_id: str) -> dict:
        """Create fallback plan when extraction completely fails."""
        response_preview = llm_response[:500] if llm_response else 'None'
        logger.error(f"Both full and partial JSON extraction failed for run_id: {run_id}. "
                    f"First 500 chars of response: {response_preview}")
        action_plan_result = self._get_default_action_plan()
        action_plan_result["error"] = "JSON extraction failed - using default structure"
        return action_plan_result

    async def _send_completion_update(self, run_id: str, stream_updates: bool, action_plan_result: dict):
        """Send completion status update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Action plan created successfully",
                "result": action_plan_result
            })

    async def _send_fallback_update(self, run_id: str, stream_updates: bool, fallback_result: dict):
        """Send fallback completion update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "completed_with_fallback",
                "message": "Action plan completed with fallback method",
                "result": fallback_result
            })

    async def _execute_with_protection(self, main_executor, fallback_executor, run_id: str):
        """Execute with unified fallback strategy."""
        return await self.fallback_strategy.execute_with_fallback(
            main_executor, fallback_executor, "action_plan_generation", run_id)

    async def _apply_reliability_protection(self, result):
        """Apply reliability protection to result."""
        async def result_operation():
            return result
        await self.reliability.execute_safely(
            result_operation, "execute_action_plan_with_fallback", timeout=45.0)
    
    def _build_action_plan_from_partial(self, partial_data: dict) -> dict:
        """Build a complete action plan structure from partial extracted data."""
        base_structure = self._get_base_action_plan_structure()
        for key, default_value in base_structure.items():
            base_structure[key] = partial_data.get(key, default_value)
        
        base_structure["partial_extraction"] = True
        base_structure["extracted_fields"] = list(partial_data.keys())
        return base_structure
    
    def _get_base_action_plan_structure(self) -> dict:
        """Get base action plan structure with defaults."""
        return {
            "action_plan_summary": "Partial extraction - summary unavailable",
            "total_estimated_time": "To be determined",
            "required_approvals": [],
            "actions": [],
            "execution_timeline": [],
            "supply_config_updates": [],
            "post_implementation": self._get_default_post_implementation(),
            "cost_benefit_analysis": self._get_default_cost_benefit()
        }
    
    def _get_default_post_implementation(self) -> dict:
        """Get default post implementation structure."""
        return {
            "monitoring_period": "30 days",
            "success_metrics": [],
            "optimization_review_schedule": "Weekly",
            "documentation_updates": []
        }
    
    def _get_default_cost_benefit(self) -> dict:
        """Get default cost benefit analysis structure."""
        return {
            "implementation_cost": {"effort_hours": 0, "resource_cost": 0},
            "expected_benefits": {
                "cost_savings_per_month": 0,
                "performance_improvement_percentage": 0,
                "roi_months": 0
            }
        }
    
    def _get_default_action_plan(self) -> dict:
        """Get a default action plan structure when extraction completely fails."""
        base_plan = self._get_base_action_plan_structure()
        base_plan["action_plan_summary"] = "Failed to generate action plan from LLM response"
        base_plan["total_estimated_time"] = "Unknown"
        return base_plan
    
    def get_health_status(self) -> dict:
        """Get agent health status"""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
