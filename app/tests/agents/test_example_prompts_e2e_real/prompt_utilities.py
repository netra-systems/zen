"""
Prompt utilities for example prompts E2E tests.
Handles prompt variation creation and response quality validation.
"""

from typing import Union
from app.schemas.llm_config_types import (
    CostOptimizationContext,
    LatencyOptimizationContext,
    CapacityPlanningContext,
    FunctionOptimizationContext,
    ModelSelectionContext,
    AuditContext,
    MultiObjectiveContext,
    ToolMigrationContext,
    RollbackAnalysisContext,
    DefaultContext
)
from app.services.quality_gate_service import QualityGateService, ContentType


class PromptUtilities:
    """Utilities for creating prompt variations and validating responses"""
    
    def create_prompt_variation(self, base_prompt: str, variation_num: int, context: Union[
        CostOptimizationContext,
        LatencyOptimizationContext,
        CapacityPlanningContext,
        FunctionOptimizationContext,
        ModelSelectionContext,
        AuditContext,
        MultiObjectiveContext,
        ToolMigrationContext,
        RollbackAnalysisContext,
        DefaultContext
    ]) -> str:
        """Create a unique variation of the base prompt"""
        variations = {
            0: self._original_prompt,
            1: self._budget_variation,
            2: self._urgent_variation,
            3: self._gpu_info_variation,
            4: self._team_perspective_variation,
            5: self._region_context_variation,
            6: self._error_constraint_variation,
            7: self._caps_variation,
            8: self._follow_up_variation,
            9: self._gpu_count_variation
        }
        
        return variations.get(variation_num, self._original_prompt)(base_prompt, context)
    
    def _original_prompt(self, prompt: str, context) -> str:
        """Return the original prompt unchanged"""
        return prompt
    
    def _budget_variation(self, prompt: str, context) -> str:
        """Add budget information to the prompt"""
        if hasattr(context, 'current_costs'):
            daily_cost = getattr(getattr(context, 'current_costs', None), 'daily', 500)
            return f"{prompt} Also, my current budget is ${daily_cost}/day."
        return prompt
    
    def _urgent_variation(self, prompt: str, context) -> str:
        """Add urgency to the prompt"""
        return f"URGENT: {prompt} Need solution within 24 hours."
    
    def _gpu_info_variation(self, prompt: str, context) -> str:
        """Add GPU information to the prompt"""
        if hasattr(context, 'infrastructure'):
            gpu_type = getattr(getattr(context, 'infrastructure', None), 'gpu_type', 'A100')
            return f"{prompt} PS: We're using {gpu_type} GPUs."
        return prompt
    
    def _team_perspective_variation(self, prompt: str, context) -> str:
        """Convert to team perspective"""
        return prompt.replace("I need", "Our team needs").replace("my", "our")
    
    def _region_context_variation(self, prompt: str, context) -> str:
        """Add region context to the prompt"""
        if hasattr(context, 'system_info'):
            region = getattr(getattr(context, 'system_info', None), 'region', 'us-east-1')
            return f"Context: Running in {region}. {prompt}"
        return prompt
    
    def _error_constraint_variation(self, prompt: str, context) -> str:
        """Add error rate constraint to the prompt"""
        if hasattr(context, 'constraints'):
            max_error_rate = getattr(getattr(context, 'constraints', None), 'max_error_rate', 0.01)
            return f"{prompt} (Error rate must stay below {max_error_rate})"
        return prompt
    
    def _caps_variation(self, prompt: str, context) -> str:
        """Convert prompt to uppercase for urgency"""
        return prompt.upper()
    
    def _follow_up_variation(self, prompt: str, context) -> str:
        """Add follow-up context to the prompt"""
        return f"Following up on yesterday's discussion: {prompt}"
    
    def _gpu_count_variation(self, prompt: str, context) -> str:
        """Add GPU count information to the prompt"""
        if hasattr(context, 'infrastructure'):
            gpu_count = getattr(getattr(context, 'infrastructure', None), 'gpu_count', 4)
            return f"{prompt} Note: We have {gpu_count} GPUs available."
        return prompt
    
    async def validate_response_quality(
        self, 
        response: str, 
        quality_service: QualityGateService, 
        content_type: ContentType
    ) -> bool:
        """Validate response quality using quality gates"""
        # Basic validation for mock testing
        if not response or not isinstance(response, str) or len(response) < 50:
            return False
        
        # Content-specific validation
        content_validator = self._get_content_specific_validation(content_type)
        if not content_validator(response):
            return False
        
        # Check for general optimization indicators
        optimization_keywords = [
            "optimize", "reduce", "improve", "efficient", "recommend", "suggest", "strategy"
        ]
        
        response_lower = response.lower()
        has_keywords = any(keyword in response_lower for keyword in optimization_keywords)
        if not has_keywords:
            return False
        
        # Check response structure (should have actionable recommendations)
        structure_indicators = ["1.", "2.", "-", "•", "step", "action"]
        has_structure = any(indicator in response for indicator in structure_indicators)
        if not has_structure:
            return False
        
        return True
    
    def determine_content_type(self, prompt: str) -> ContentType:
        """Determine content type based on prompt content"""
        prompt_lower = prompt.lower()
        
        if "audit" in prompt_lower:
            return ContentType.DATA_ANALYSIS
        elif "rollback" in prompt_lower:
            return ContentType.ACTION_PLAN
        elif any(word in prompt_lower for word in ["cost", "latency", "optimize", "improve"]):
            return ContentType.OPTIMIZATION
        else:
            return ContentType.OPTIMIZATION  # Default for most prompts
    
    def _validate_cost_optimization_response(self, response: str) -> bool:
        """Validate response for cost optimization prompts"""
        cost_keywords = ["cost", "budget", "price", "expense", "save", "reduce", "efficient"]
        return any(keyword in response.lower() for keyword in cost_keywords)
    
    def _validate_latency_optimization_response(self, response: str) -> bool:
        """Validate response for latency optimization prompts"""
        latency_keywords = ["latency", "speed", "performance", "fast", "time", "delay"]
        return any(keyword in response.lower() for keyword in latency_keywords)
    
    def _validate_audit_response(self, response: str) -> bool:
        """Validate response for audit prompts"""
        audit_keywords = ["analyze", "review", "assess", "examine", "cache", "optimization"]
        return any(keyword in response.lower() for keyword in audit_keywords)
    
    def _validate_action_plan_response(self, response: str) -> bool:
        """Validate response for action plan prompts"""
        action_keywords = ["action", "plan", "step", "implement", "execute", "rollback"]
        return any(keyword in response.lower() for keyword in action_keywords)
    
    def _get_content_specific_validation(self, content_type: ContentType) -> callable:
        """Get content-specific validation function"""
        validators = {
            ContentType.OPTIMIZATION: self._validate_cost_optimization_response,
            ContentType.DATA_ANALYSIS: self._validate_audit_response,
            ContentType.ACTION_PLAN: self._validate_action_plan_response
        }
        return validators.get(content_type, self._validate_cost_optimization_response)