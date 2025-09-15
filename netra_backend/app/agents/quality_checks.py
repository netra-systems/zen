"""Quality validation checks module.

This module contains validation logic separated from the supervisor
to maintain the 450-line and 25-line function limits per CLAUDE.md.
"""

from typing import Any, Dict, Optional

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.core.interfaces_quality import (
    QualityValidator as CoreQualityValidator,
)
from netra_backend.app.core.quality_types import ContentType, ValidationResult
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.quality_types import (
    QualityValidationResult,
    QualityValidatorInterface,
)
from netra_backend.app.services.quality_gate_service import QualityGateService

logger = central_logger.get_logger(__name__)


class QualityValidator(QualityValidatorInterface):
    """Handles quality validation logic for supervisor agents - delegates to core implementation."""
    
    def __init__(self, quality_gate_service: Optional[QualityGateService],
                 strict_mode: bool = False):
        """Initialize quality validator."""
        self._initialize_services(quality_gate_service, strict_mode)
        self.quality_stats = self._initialize_stats()
    
    def _initialize_services(self, quality_gate_service: Optional[QualityGateService], strict_mode: bool) -> None:
        """Initialize quality gate services."""
        self.quality_gate_service = quality_gate_service
        self.strict_mode = strict_mode
        self._core_validator = CoreQualityValidator(quality_gate_service, strict_mode)
    
    def _initialize_stats(self) -> Dict[str, int]:
        """Initialize quality statistics."""
        return {
            'total_validations': 0, 'passed': 0, 'failed': 0,
            'retried': 0, 'fallbacks_used': 0
        }
    
    async def validate_agent_output(self, 
                                  context: AgentExecutionContext,
                                  agent_name: str,
                                  state: DeepAgentState) -> Optional[ValidationResult]:
        """Validate agent output and return validation result."""
        if not self.quality_gate_service:
            return None
        
        agent_output = self._extract_agent_output(state, agent_name)
        if not agent_output:
            return None
        
        return await self._validate_and_finalize(agent_output, agent_name, context, state)
    
    async def _validate_and_finalize(self, agent_output: str, agent_name: str, 
                                   context: AgentExecutionContext, state: DeepAgentState) -> ValidationResult:
        """Execute validation and finalize result."""
        validation_result = await self._execute_validation(agent_output, agent_name, context, state)
        return self._finalize_validation(validation_result, agent_name)
    
    async def _execute_validation(
        self, agent_output: str, agent_name: str, context: AgentExecutionContext, state: DeepAgentState
    ) -> ValidationResult:
        """Execute validation process."""
        content_type = self._get_content_type_for_agent(agent_name)
        return await self._perform_validation(
            agent_output, content_type, context, agent_name, state
        )
    
    def _finalize_validation(self, validation_result: ValidationResult, agent_name: str) -> ValidationResult:
        """Finalize validation with stats and logging."""
        self._update_validation_stats(validation_result)
        self._log_validation_result(validation_result, agent_name)
        return validation_result
    
    async def _perform_validation(self, 
                                agent_output: str,
                                content_type: ContentType,
                                context: AgentExecutionContext,
                                agent_name: str,
                                state: DeepAgentState) -> ValidationResult:
        """Perform the actual validation."""
        return await self._core_validator.validate_content(
            content=agent_output,
            content_type=content_type,
            context=self._build_validation_context(state, agent_name, context),
            strict_mode=self.strict_mode
        )
    
    def _build_validation_context(self, 
                                state: DeepAgentState,
                                agent_name: str, 
                                context: AgentExecutionContext) -> Dict[str, Any]:
        """Build validation context dictionary."""
        return {
            'user_request': state.user_request,
            'agent_name': agent_name,
            'run_id': context.run_id
        }
    
    def _update_validation_stats(self, validation_result: ValidationResult) -> None:
        """Update quality statistics."""
        self.quality_stats['total_validations'] += 1
        if validation_result.passed:
            self.quality_stats['passed'] += 1
        else:
            self.quality_stats['failed'] += 1
    
    def _log_validation_result(self, 
                             validation_result: ValidationResult,
                             agent_name: str) -> None:
        """Log validation result."""
        score = validation_result.metrics.overall_score
        if validation_result.passed:
            logger.info(f"Quality validation passed for {agent_name}: Score={score:.2f}")
        else:
            issues = validation_result.metrics.issues
            logger.warning(f"Quality validation failed for {agent_name}: "
                         f"Score={score:.2f}, Issues={issues}")
    
    def store_validation_metrics(self, 
                               state: DeepAgentState,
                               agent_name: str,
                               validation_result: ValidationResult) -> None:
        """Store validation metrics in state."""
        if not hasattr(state, 'quality_metrics'):
            state.quality_metrics = {}
        state.quality_metrics[agent_name] = validation_result.metrics
    
    def _extract_agent_output(self, state: DeepAgentState, agent_name: str) -> Optional[str]:
        """Extract the output from an agent's execution."""
        extractor = self._get_output_extractor(agent_name)
        if not extractor:
            return None
        
        output = extractor(state)
        return self._convert_output_to_string(output)
    
    def _get_output_extractor(self, agent_name: str):
        """Get output extractor function for agent."""
        agent_extractors = self._build_agent_extractor_map()
        return agent_extractors.get(agent_name)
    
    def _build_agent_extractor_map(self) -> Dict[str, Any]:
        """Build mapping of agent names to output extractors."""
        return {
            'TriageSubAgent': lambda s: s.triage_result.get('summary', '') if hasattr(s, 'triage_result') else None,
            'DataSubAgent': lambda s: s.data_result.get('data', '') if hasattr(s, 'data_result') else None,
            'OptimizationsCoreSubAgent': lambda s: s.optimizations_result.get('recommendations', '') if hasattr(s, 'optimizations_result') else None,
            'ActionsToMeetGoalsSubAgent': lambda s: s.actions_result.get('actions', '') if hasattr(s, 'actions_result') else None,
            'ReportingSubAgent': lambda s: s.report_result.get('report', '') if hasattr(s, 'report_result') else None
        }
    
    def _convert_output_to_string(self, output: Any) -> Optional[str]:
        """Convert output to string if needed."""
        if not output:
            return None
        return str(output) if not isinstance(output, str) else output
    
    def _get_content_type_for_agent(self, agent_name: str) -> ContentType:
        """Map agent name to content type."""
        mapping = {
            'TriageSubAgent': ContentType.TRIAGE,
            'DataSubAgent': ContentType.DATA_ANALYSIS,
            'OptimizationsCoreSubAgent': ContentType.OPTIMIZATION,
            'ActionsToMeetGoalsSubAgent': ContentType.ACTION_PLAN,
            'ReportingSubAgent': ContentType.REPORT
        }
        return mapping.get(agent_name, ContentType.GENERAL)
    
    # Interface Implementation Methods
    async def validate_content(
        self, 
        content: str, 
        content_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> QualityValidationResult:
        """Validate content and return detailed quality results"""
        if not self.quality_gate_service:
            return self._create_default_validation_result(content)
        
        content_type_enum = self._convert_content_type_string(content_type)
        return await self._execute_core_validation(content, content_type_enum, context)
    
    async def _execute_core_validation(self, content: str, content_type_enum, 
                                     context: Optional[Dict[str, Any]]) -> QualityValidationResult:
        """Execute core validation process."""
        return await self._core_validator.validate_content(
            content=content,
            content_type=content_type_enum,
            context=context or {},
            strict_mode=self.strict_mode
        )
    
    def _convert_content_type_string(self, content_type: Optional[str]) -> ContentType:
        """Convert string content type to ContentType enum"""
        if not content_type:
            return ContentType.GENERAL
        try:
            return ContentType(content_type.lower())
        except ValueError:
            return ContentType.GENERAL
    
    def _create_default_validation_result(self, content: str) -> QualityValidationResult:
        """Create default validation result when no quality gate service available"""
        metrics = self._build_default_metrics(content)
        return self._build_default_validation_result(metrics)
    
    def _build_default_metrics(self, content: str):
        """Build default quality metrics."""
        from netra_backend.app.schemas.quality_types import QualityLevel, QualityMetrics
        base_scores = self._get_default_scores()
        additional_metrics = self._get_default_additional_metrics(content)
        return QualityMetrics(**base_scores, **additional_metrics)
    
    def _get_default_scores(self) -> Dict[str, Any]:
        """Get default scoring values."""
        return {
            'overall_score': 50.0, 'quality_level': self._get_default_quality_level(),
            'specificity_score': 50.0, 'actionability_score': 50.0,
            'quantification_score': 50.0, 'relevance_score': 50.0,
            'completeness_score': 50.0, 'novelty_score': 50.0, 'clarity_score': 50.0
        }
    
    def _get_default_quality_level(self):
        """Get default quality level."""
        from netra_backend.app.schemas.quality_types import QualityLevel
        return QualityLevel.ACCEPTABLE
    
    def _get_default_additional_metrics(self, content: str) -> Dict[str, Any]:
        """Get default additional metrics."""
        return {
            'word_count': len(content.split()), 'generic_phrase_count': 0,
            'circular_reasoning_detected': False, 'hallucination_risk': 0.0,
            'redundancy_ratio': 0.0, 'issues': [], 'suggestions': []
        }
    
    def _build_default_validation_result(self, metrics) -> QualityValidationResult:
        """Build default validation result structure."""
        from netra_backend.app.schemas.quality_types import QualityValidationResult
        return QualityValidationResult(
            passed=True, metrics=metrics, retry_suggested=False,
            retry_prompt_adjustments=[], validation_duration_ms=0.0
        )
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "validator_type": "SupervisorQualityValidator",
            "has_quality_gate_service": self.quality_gate_service is not None,
            "strict_mode": self.strict_mode,
            "quality_stats": self.quality_stats.copy()
        }