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
from app.core.reliability_utils import create_agent_reliability_wrapper
from app.core.fallback_utils import create_agent_fallback_strategy


class ActionsToMeetGoalsSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ActionsToMeetGoalsSubAgent", description="This agent creates a plan of action.")
        self.tool_dispatcher = tool_dispatcher
        
        # Initialize reliability wrapper
        self.reliability = create_agent_reliability_wrapper("ActionsToMeetGoalsSubAgent")

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have optimizations and data results to work with."""
        return state.optimizations_result is not None and state.data_result is not None
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the actions to meet goals logic."""
        
        async def _execute_action_plan():
            # Update status via WebSocket
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processing",
                    "message": "Creating action plan based on optimization strategies..."
                })

            prompt = actions_to_meet_goals_prompt_template.format(
                optimizations=state.optimizations_result,
                data=state.data_result,
                user_request=state.user_request
            )

            # Check response size and potentially adjust approach
            response_size_mb = len(prompt) / (1024 * 1024)
            if response_size_mb > 1:  # If prompt is larger than 1MB
                logger.info(f"Large prompt detected ({response_size_mb:.2f}MB) for run_id: {run_id}")
            
            llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='actions_to_meet_goals')
            
            # Log response size for monitoring
            if llm_response_str:
                logger.debug(f"Received LLM response of {len(llm_response_str)} characters for run_id: {run_id}")
            
            # Try enhanced JSON extraction with recovery mechanisms
            action_plan_result = extract_json_from_response(llm_response_str, max_retries=5)
            
            # If full extraction fails, try partial extraction of critical fields
            if not action_plan_result:
                logger.debug(
                    f"Full JSON extraction failed for run_id: {run_id}. "
                    f"Response length: {len(llm_response_str) if llm_response_str else 0} chars. "
                    f"Attempting partial extraction..."
                )
                
                # Try to extract at least the critical fields
                required_fields = ['action_plan_summary', 'total_estimated_time', 'actions']
                partial_result = extract_partial_json(llm_response_str, required_fields=None)  # Get whatever we can
                
                if partial_result:
                    # If we got substantial data, this is actually a success
                    if len(partial_result) > 10:
                        logger.info(f"Successfully recovered {len(partial_result)} fields via partial extraction for run_id: {run_id}")
                    else:
                        logger.warning(f"Partial extraction recovered only {len(partial_result)} fields for run_id: {run_id}")
                    
                    # Build a complete structure with extracted partial data
                    action_plan_result = self._build_action_plan_from_partial(partial_result)
                else:
                    logger.error(
                        f"Both full and partial JSON extraction failed for run_id: {run_id}. "
                        f"First 500 chars of response: {llm_response_str[:500] if llm_response_str else 'None'}"
                    )
                    # Provide a more comprehensive default action plan structure
                    action_plan_result = self._get_default_action_plan()
                    action_plan_result["error"] = "JSON extraction failed - using default structure"

            state.action_plan_result = action_plan_result
            
            # Update with results
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processed",
                    "message": "Action plan created successfully",
                    "result": action_plan_result
                })
            
            return action_plan_result
        
        async def _fallback_action_plan():
            """Fallback action plan when main operation fails"""
            logger.warning(f"Using fallback action plan for run_id: {run_id}")
            fallback_result = self._get_default_action_plan()
            fallback_result["metadata"] = {
                "fallback_used": True,
                "reason": "Primary action plan generation failed"
            }
            state.action_plan_result = fallback_result
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed_with_fallback",
                    "message": "Action plan completed with fallback method",
                    "result": fallback_result
                })
            
            return fallback_result
        
        # Execute with reliability protection
        await self.reliability.execute_safely(
            _execute_action_plan,
            "execute_action_plan",
            fallback=_fallback_action_plan,
            timeout=45.0
        )
    
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
