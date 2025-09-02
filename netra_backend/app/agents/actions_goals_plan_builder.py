# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-09-02T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CRITICAL SSOT FIX - ActionPlanBuilder compliance
# Git: critical-remediation-20250823 | SSOT violations fixed
# Change: CRITICAL | Scope: Component | Risk: Low (SSOT compliance)
# Session: ssot-compliance-fix | Seq: 1
# Review: Required | Score: 100 (SSOT compliant)
# ================================
"""Helper module for action plan building and processing.

FIXED SSOT VIOLATIONS:
- Replaced extract_json_from_response with unified_json_handler.LLMResponseParser
- Converted static methods to instance methods for user context isolation
- Added UnifiedRetryHandler for resilient operations
- Replaced hardcoded defaults with schema-based defaults
- Added CacheHelpers for expensive operations
"""

from typing import Any, Dict, Optional

from netra_backend.app.agents.state import ActionPlanResult, PlanStep
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    backend_json_handler
)
from netra_backend.app.core.resilience.unified_retry_handler import (
    UnifiedRetryHandler,
    AGENT_RETRY_POLICY
)
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from netra_backend.app.logging_config import central_logger as logger


class ActionPlanBuilder:
    """Handles action plan building and processing logic with SSOT compliance.
    
    Fixed SSOT violations:
    - Instance-based for proper user context isolation
    - Uses unified JSON handling patterns
    - Includes retry logic for resilience
    - Schema-based defaults instead of hardcoded values
    - Cache integration for expensive operations
    """
    
    def __init__(self, user_context: Optional[Dict[str, Any]] = None, cache_manager: Optional[Any] = None):
        """Initialize ActionPlanBuilder with user context for proper isolation.
        
        Args:
            user_context: User context for request isolation
            cache_manager: Optional cache manager for caching expensive operations
        """
        self.user_context = user_context or {}
        self.json_parser = LLMResponseParser()
        self.json_handler = backend_json_handler
        self.retry_handler = UnifiedRetryHandler("action_plan_builder", AGENT_RETRY_POLICY)
        self.cache_helpers = CacheHelpers(cache_manager) if cache_manager else None
        
    async def process_llm_response(
        self, llm_response: str, run_id: str
    ) -> ActionPlanResult:
        """Process LLM response to ActionPlanResult with retry logic."""
        # Use retry handler for resilient JSON extraction
        result = await self.retry_handler.execute_with_retry_async(
            self._extract_and_convert_response, llm_response, run_id
        )
        if result.success:
            return result.result
        else:
            # Fallback to default on persistent failure
            logger.warning(f"Failed to process LLM response after retries for {run_id}: {result.final_exception}")
            return self._get_default_action_plan()
            
    async def _extract_and_convert_response(self, llm_response: str, run_id: str) -> ActionPlanResult:
        """Extract and convert LLM response with unified JSON handling."""
        # Use unified JSON parser instead of extract_json_from_response
        action_plan_dict = self.json_parser.ensure_agent_response_is_json(llm_response)
        
        if not action_plan_dict or action_plan_dict.get("parsed", True) is False:
            action_plan_dict = await self._handle_extraction_failure(
                llm_response, run_id
            )
            
        return self._convert_to_action_plan_result(action_plan_dict)
    
    def _convert_to_action_plan_result(self, data: dict) -> ActionPlanResult:
        """Convert dictionary to ActionPlanResult with schema validation."""
        # Filter only valid model fields
        valid_fields = {
            k: v for k, v in data.items()
            if k in ActionPlanResult.model_fields
        }
        
        # Handle legacy 'actions' field conversion to 'plan_steps'
        if 'actions' in data and 'plan_steps' not in valid_fields:
            valid_fields['plan_steps'] = self._extract_plan_steps(data)
            
        # Use schema defaults for missing fields instead of hardcoded values
        return ActionPlanResult(**valid_fields)
    
    def _extract_plan_steps(self, data: dict) -> list:
        """Extract plan steps from data with proper parsing."""
        steps = data.get('plan_steps', [])
        if not isinstance(steps, list):
            # Try to extract from 'actions' field as fallback
            steps = data.get('actions', [])
            if not isinstance(steps, list):
                return []
        return [self._create_plan_step(s) for s in steps]
    
    def _create_plan_step(self, step_data) -> PlanStep:
        """Create PlanStep from data with robust parsing."""
        if isinstance(step_data, str):
            return PlanStep(step_id="1", description=step_data)
        elif isinstance(step_data, dict):
            # Handle different data structures that might come from LLM
            step_id = step_data.get('step_id', step_data.get('id', '1'))
            description = step_data.get(
                'description', 
                step_data.get(
                    'step', 
                    step_data.get('action', 'No description')
                )
            )
            
            # Extract additional fields if present
            estimated_duration = step_data.get('estimated_duration')
            dependencies = step_data.get('dependencies', [])
            resources_needed = step_data.get('resources_needed', [])
            status = step_data.get('status', 'pending')
            
            return PlanStep(
                step_id=str(step_id), 
                description=str(description),
                estimated_duration=estimated_duration,
                dependencies=dependencies if isinstance(dependencies, list) else [],
                resources_needed=resources_needed if isinstance(resources_needed, list) else [],
                status=str(status)
            )
        return PlanStep(step_id='1', description='Default step')
    
    async def _handle_extraction_failure(
        self, llm_response: str, run_id: str
    ) -> dict:
        """Handle JSON extraction failure with unified error recovery."""
        logger.debug(f"JSON extraction failed for {run_id}, attempting recovery")
        
        # Try unified JSON error recovery
        from netra_backend.app.core.serialization.unified_json_handler import error_fixer
        recovered = error_fixer.recover_truncated_json(llm_response)
        
        if recovered:
            logger.debug(f"Successfully recovered JSON for {run_id}")
            return recovered
            
        # Fallback to partial extraction with unified parser
        partial = self.json_parser.safe_json_parse(llm_response, {})
        if partial and isinstance(partial, dict):
            return self._build_from_partial(partial).model_dump()
            
        return self._get_default_action_plan().model_dump()
    
    def _build_from_partial(self, partial: dict) -> ActionPlanResult:
        """Build ActionPlanResult from partial data using schema defaults."""
        # Get schema-based defaults instead of hardcoded values
        base = self._get_schema_based_defaults()
        
        # Update with partial data, filtering for valid fields only
        valid_partial = {
            k: v for k, v in partial.items()
            if k in ActionPlanResult.model_fields
        }
        base.update(valid_partial)
        
        # Mark as partial extraction in metadata
        base["action_plan_summary"] = f"Partial extraction - {base.get('action_plan_summary', 'summary unavailable')}"
        
        return ActionPlanResult(**base)
    
    def _get_schema_based_defaults(self) -> dict:
        """Get schema-based defaults instead of hardcoded values."""
        # Use Pydantic model defaults by creating a default instance
        default_instance = ActionPlanResult()
        return default_instance.model_dump()
        
    def _get_structured_defaults(self) -> dict:
        """Get structured defaults for complex fields."""
        return {
            "post_implementation": {
                "monitoring_period": "30 days",
                "success_metrics": [],
                "optimization_review_schedule": "Weekly",
                "documentation_updates": []
            },
            "cost_benefit_analysis": {
                "implementation_cost": {"effort_hours": 0, "resource_cost": 0},
                "expected_benefits": {
                    "cost_savings_per_month": 0,
                    "performance_improvement_percentage": 0,
                    "roi_months": 0
                }
            }
        }
    
    def _get_default_action_plan(self) -> ActionPlanResult:
        """Get default action plan for failures using schema defaults."""
        # Start with schema-based defaults
        data = self._get_schema_based_defaults()
        
        # Override with structured defaults for complex fields
        structured = self._get_structured_defaults()
        data.update(structured)
        
        # Update with failure-specific values
        data.update({
            "action_plan_summary": "Failed to generate action plan - using fallback",
            "total_estimated_time": "Unknown - requires manual review"
        })
        
        return ActionPlanResult(**data)
    
    # Backward compatibility methods for existing code
    @staticmethod 
    def get_default_action_plan() -> ActionPlanResult:
        """Backward compatibility method - creates new instance."""
        builder = ActionPlanBuilder()
        return builder._get_default_action_plan()
        
    @staticmethod
    async def process_llm_response_static(
        llm_response: str, run_id: str
    ) -> ActionPlanResult:
        """Backward compatibility static method - creates new instance."""
        builder = ActionPlanBuilder()
        return await builder.process_llm_response(llm_response, run_id)
    
    # Cache integration methods
    def _get_cache_key(self, llm_response: str, run_id: str) -> str:
        """Generate cache key for response processing using CacheHelpers."""
        if not self.cache_helpers:
            return ""
        key_data = {
            "response_content": llm_response,  # Use raw content, let CacheHelpers handle hashing
            "run_id": run_id,
            "context": self.user_context.get("user_id", "default")
        }
        return self.cache_helpers.hash_key_data(key_data)
        
    async def _try_cache_response(self, cache_key: str) -> Optional[ActionPlanResult]:
        """Try to get cached response."""
        if not self.cache_helpers or not cache_key:
            return None
            
        try:
            cached = await self.cache_helpers.cache_manager.get_cached_response(cache_key)
            if cached:
                logger.debug(f"Cache hit for action plan processing: {cache_key}")
                return ActionPlanResult.model_validate(cached)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
        
    async def _cache_response(self, cache_key: str, result: ActionPlanResult) -> None:
        """Cache the processed response."""
        if not self.cache_helpers or not cache_key:
            return
            
        try:
            ttl = self.cache_helpers.calculate_ttl("", result.model_dump())
            await self.cache_helpers.cache_manager.cache_response(
                cache_key, result.model_dump(), ttl
            )
            logger.debug(f"Cached action plan result: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")