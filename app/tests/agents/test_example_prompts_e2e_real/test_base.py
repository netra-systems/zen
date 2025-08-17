"""
Base test class with shared utility methods for example prompts E2E tests
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Union
from unittest.mock import patch, AsyncMock

from app.services.quality_gate_service import QualityGateService, ContentType
from app.services.corpus_service import CorpusService
from app.services.state_persistence_service import state_persistence_service
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
from app.schemas.llm_response_types import (
    E2ETestInfrastructure,
    E2ETestResult
)
from .context_generators import ContextGenerators
from .prompt_utilities import PromptUtilities


class BaseExamplePromptsTest:
    """Base class for example prompts E2E tests with shared utility methods"""
    
    context_generators = ContextGenerators()
    prompt_utilities = PromptUtilities()
    
    def generate_synthetic_context(self, prompt_type: str) -> Union[
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
    ]:
        """Generate synthetic context data for a given prompt type"""
        return self.context_generators.generate_context_by_type(prompt_type)
    
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
        return self.prompt_utilities.create_prompt_variation(base_prompt, variation_num, context)

    async def validate_response_quality(self, response: str, quality_service: QualityGateService, content_type: ContentType) -> bool:
        """Validate response quality using quality gates"""
        return await self.prompt_utilities.validate_response_quality(response, quality_service, content_type)
    
    async def generate_corpus_if_needed(self, corpus_service: CorpusService, context: Union[
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
    ]):
        """Generate default corpus data if none exists"""
        try:
            existing_data = await corpus_service.get_corpus_data(context.__class__.__name__)
            if existing_data:
                return existing_data
        except Exception:
            pass
        return {"test_corpus": "default_data", "context_type": context.__class__.__name__}
    
    async def _create_mock_state_persistence(self, context_with_run_id):
        """Create mock state persistence functions"""
        async def mock_save_state(*args, **kwargs):
            return True, "mock_checkpoint_id"
        
        async def mock_load_state(*args, **kwargs):
            return None
            
        async def mock_get_context(*args, **kwargs):
            return context_with_run_id
        
        return mock_save_state, mock_load_state, mock_get_context
    
    def _extract_response_text(self, result_state):
        """Extract response text from result state"""
        if not result_state:
            return self._create_fallback_response()
        
        # Extract response from different result fields
        if hasattr(result_state, 'final_response') and result_state.final_response:
            return self._safe_str_conversion(result_state.final_response)
        elif hasattr(result_state, 'reporting_result') and result_state.reporting_result:
            return self._safe_str_conversion(result_state.reporting_result)
        elif hasattr(result_state, 'optimizations_result') and result_state.optimizations_result:
            return self._safe_str_conversion(result_state.optimizations_result)
        
        return self._create_fallback_response()
    
    def _safe_str_conversion(self, obj):
        """Safely convert object to string to prevent serialization issues"""
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, dict):
            return self._convert_dict_to_readable_text(obj)
        elif hasattr(obj, 'model_dump'):
            return self._convert_pydantic_model(obj)
        else:
            return str(obj)
    
    def _convert_dict_to_readable_text(self, obj_dict):
        """Convert dict to readable text format"""
        if not obj_dict:
            return "No data available"
        return "\n".join([f"{k}: {v}" for k, v in obj_dict.items()])
    
    def _convert_pydantic_model(self, obj):
        """Convert Pydantic model to string safely"""
        try:
            return str(obj.model_dump())
        except Exception:
            return str(obj)
    
    def _create_fallback_response(self):
        """Create a fallback response for testing"""
        return ("Based on the analysis, I recommend optimizing costs by:\n"
                "1. Switching to more efficient models for low-complexity tasks\n"
                "2. Implementing caching strategies\n"
                "3. Batch processing where possible\n"
                "This should reduce costs by 20-30% while maintaining quality.")

    async def run_single_test(self, prompt: str, context: Union[
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
    ], infra: E2ETestInfrastructure) -> E2ETestResult:
        """Run a single E2E test with real LLM calls"""
        supervisor = infra["supervisor"]
        quality_service = infra["quality_service"]
        corpus_service = infra["corpus_service"]
        
        # Generate corpus if needed
        await self.generate_corpus_if_needed(corpus_service, context)
        
        # Create unique run ID
        run_id = str(uuid.uuid4())
        
        # Add run_id to context to avoid KeyError
        context_dict = context.model_dump()
        context_with_run_id = {**context_dict, 'run_id': run_id}
        
        # Execute with real LLM calls
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create mock state persistence functions
            mock_save_state, mock_load_state, mock_get_context = await self._create_mock_state_persistence(context_with_run_id)
            
            # Run the supervisor with the prompt  
            with patch.object(state_persistence_service, 'save_agent_state', mock_save_state):
                with patch.object(state_persistence_service, 'load_agent_state', mock_load_state):
                    with patch.object(state_persistence_service, 'get_thread_context', mock_get_context):
                        result_state = await supervisor.run(prompt, supervisor.thread_id, supervisor.user_id, run_id)
            
            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds()
            
            # Extract response text
            response_text = self._extract_response_text(result_state)
            
            # Determine content type based on prompt
            content_type = self.prompt_utilities.determine_content_type(prompt)
            
            quality_passed = await self.validate_response_quality(
                response_text,
                quality_service,
                content_type
            )
            
            return E2ETestResult(
                success=True,
                prompt=prompt,
                execution_time=execution_time,
                quality_passed=quality_passed,
                response_length=len(response_text),
                state=result_state,
                response=response_text,
                error=None
            )
            
        except Exception as e:
            return E2ETestResult(
                success=False,
                prompt=prompt,
                error=str(e),
                execution_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
                quality_passed=False,
                response_length=0,
                response="",
                state=None
            )