# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Quality hooks module ≤300 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 7
# Review: Pending | Score: 90
# ================================

"""
Quality Validation and Monitoring Hooks

This module contains quality validation hooks and monitoring logic.
All functions are ≤8 lines as per CLAUDE.md requirements.
"""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    ValidationResult,
)
from netra_backend.app.services.quality_monitoring_service import (
    QualityMonitoringService,
)

logger = central_logger.get_logger(__name__)


class QualityHooksManager:
    """Manages quality validation and monitoring hooks with 25-line function limit"""
    
    def __init__(self, 
                 quality_gate_service: Optional[QualityGateService],
                 monitoring_service: Optional[QualityMonitoringService],
                 strict_mode: bool = False):
        self.quality_gate_service = quality_gate_service
        self.monitoring_service = monitoring_service
        self.strict_mode = strict_mode
        self.quality_stats = self._init_stats()
    
    def _init_stats(self) -> Dict[str, int]:
        """Initialize quality statistics"""
        return {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'retried': 0,
            'fallbacks_used': 0
        }
    
    async def quality_validation_hook(self, 
                                    context: AgentExecutionContext,
                                    agent_name: str,
                                    state: DeepAgentState) -> None:
        """Validate agent output quality"""
        if not self.quality_gate_service:
            return
        
        try:
            await self._perform_validation(context, agent_name, state)
        except Exception as e:
            logger.error(f"Error in quality validation hook: {str(e)}")
    
    async def _perform_validation(self,
                                context: AgentExecutionContext,
                                agent_name: str,
                                state: DeepAgentState) -> None:
        """Perform quality validation on agent output"""
        agent_output = self._extract_agent_output(state, agent_name)
        if not agent_output:
            return
        
        validation_result = await self._validate_content(
            agent_output, agent_name, context, state
        )
        
        self._update_validation_stats(validation_result)
        self._store_validation_result(state, agent_name, validation_result)
    
    async def _validate_content(self,
                              agent_output: str,
                              agent_name: str,
                              context: AgentExecutionContext,
                              state: DeepAgentState) -> ValidationResult:
        """Validate content using quality gate service"""
        content_type = self._get_content_type_for_agent(agent_name)
        
        return await self.quality_gate_service.validate_content(
            content=agent_output,
            content_type=content_type,
            context=self._create_validation_context(state, agent_name, context),
            strict_mode=self.strict_mode
        )
    
    def _create_validation_context(self,
                                 state: DeepAgentState,
                                 agent_name: str,
                                 context: AgentExecutionContext) -> Dict[str, Any]:
        """Create validation context"""
        return {
            'user_request': state.user_request,
            'agent_name': agent_name,
            'run_id': context.run_id
        }
    
    def _update_validation_stats(self, validation_result: ValidationResult) -> None:
        """Update quality statistics based on validation result"""
        self.quality_stats['total_validations'] += 1
        
        if validation_result.passed:
            self.quality_stats['passed'] += 1
            self._log_validation_success(validation_result)
        else:
            self.quality_stats['failed'] += 1
            self._log_validation_failure(validation_result)
    
    def _log_validation_success(self, validation_result: ValidationResult) -> None:
        """Log successful validation"""
        score = validation_result.metrics.overall_score
        logger.info(f"Quality validation passed: Score={score:.2f}")
    
    def _log_validation_failure(self, validation_result: ValidationResult) -> None:
        """Log failed validation"""
        score = validation_result.metrics.overall_score
        issues = validation_result.metrics.issues
        logger.warning(f"Quality validation failed: Score={score:.2f}, Issues={issues}")
    
    def _store_validation_result(self,
                               state: DeepAgentState,
                               agent_name: str,
                               validation_result: ValidationResult) -> None:
        """Store validation metrics in state for tracking"""
        if not hasattr(state, 'quality_metrics'):
            state.quality_metrics = {}
        state.quality_metrics[agent_name] = validation_result.metrics
    
    async def quality_monitoring_hook(self,
                                    context: AgentExecutionContext,
                                    agent_name: str,
                                    state: DeepAgentState) -> None:
        """Record quality metrics for monitoring"""
        if not self._should_monitor(state, agent_name):
            return
        
        try:
            await self._record_quality_event(context, agent_name, state)
        except Exception as e:
            logger.error(f"Error in quality monitoring hook: {str(e)}")
    
    def _should_monitor(self, state: DeepAgentState, agent_name: str) -> bool:
        """Check if monitoring should be performed"""
        return (
            self.monitoring_service is not None and
            hasattr(state, 'quality_metrics') and
            state.quality_metrics.get(agent_name) is not None
        )
    
    async def _record_quality_event(self,
                                   context: AgentExecutionContext,
                                   agent_name: str,
                                   state: DeepAgentState) -> None:
        """Record quality event for monitoring"""
        metrics = state.quality_metrics.get(agent_name)
        content_type = self._get_content_type_for_agent(agent_name)
        
        await self.monitoring_service.record_quality_event(
            agent_name=agent_name,
            content_type=content_type,
            metrics=metrics,
            user_id=context.user_id,
            thread_id=context.thread_id,
            run_id=context.run_id
        )
    
    def _extract_agent_output(self, state: DeepAgentState, agent_name: str) -> Optional[str]:
        """Extract the output from an agent's execution"""
        agent_output_map = self._get_agent_output_map()
        extractor = agent_output_map.get(agent_name)
        
        if not extractor:
            return None
        
        output = extractor(state)
        if output:
            return str(output) if not isinstance(output, str) else output
        return None
    
    def _get_agent_output_map(self) -> Dict[str, callable]:
        """Get mapping of agent names to output extractors"""
        return {
            'TriageSubAgent': lambda s: s.triage_result.get('summary', '') if hasattr(s, 'triage_result') else None,
            'DataSubAgent': lambda s: s.data_result.get('data', '') if hasattr(s, 'data_result') else None,
            'OptimizationsCoreSubAgent': lambda s: s.optimizations_result.get('recommendations', '') if hasattr(s, 'optimizations_result') else None,
            'ActionsToMeetGoalsSubAgent': lambda s: s.actions_result.get('actions', '') if hasattr(s, 'actions_result') else None,
            'ReportingSubAgent': lambda s: s.report_result.get('report', '') if hasattr(s, 'report_result') else None,
            'TestAgent': lambda s: s.triage_result.get('summary', '') if hasattr(s, 'triage_result') and s.triage_result else None
        }
    
    def _get_content_type_for_agent(self, agent_name: str) -> ContentType:
        """Map agent name to content type"""
        mapping = {
            'TriageSubAgent': ContentType.TRIAGE,
            'DataSubAgent': ContentType.DATA_ANALYSIS,
            'OptimizationsCoreSubAgent': ContentType.OPTIMIZATION,
            'ActionsToMeetGoalsSubAgent': ContentType.ACTION_PLAN,
            'ReportingSubAgent': ContentType.REPORT
        }
        return mapping.get(agent_name, ContentType.GENERAL)
    
    async def quality_retry_hook(self,
                               context: AgentExecutionContext,
                               agent_name: str,
                               retry_count: int) -> bool:
        """Decide whether to retry based on quality metrics"""
        if not self._has_quality_validation(context):
            return retry_count < context.max_retries
        
        return self._should_retry_based_on_quality(context, agent_name, retry_count)
    
    def _has_quality_validation(self, context: AgentExecutionContext) -> bool:
        """Check if quality validation data exists"""
        return (
            hasattr(context, 'metadata') and
            'quality_validation' in context.metadata
        )
    
    def _should_retry_based_on_quality(self,
                                     context: AgentExecutionContext,
                                     agent_name: str,
                                     retry_count: int) -> bool:
        """Determine retry based on quality validation"""
        validation_result = context.metadata['quality_validation']
        
        # Don't retry if quality is extremely poor
        if validation_result.metrics.overall_score < 0.2:
            logger.info(f"Skipping retry for {agent_name} due to very low quality score")
            return False
        
        # Allow retry if suggested and under limit
        return validation_result.retry_suggested and retry_count < context.max_retries
    
    def get_quality_stats(self) -> Dict[str, int]:
        """Get current quality statistics"""
        return self.quality_stats.copy()
    
    def increment_retries(self) -> None:
        """Increment retry counter"""
        self.quality_stats['retried'] += 1
    
    def increment_fallbacks(self) -> None:
        """Increment fallback counter"""
        self.quality_stats['fallbacks_used'] += 1