"""Quality validation checks module.

This module contains validation logic separated from the supervisor
to maintain the 300-line and 8-line function limits per CLAUDE.md.
"""

from typing import Dict, Optional, Any
from app.logging_config import central_logger
from app.agents.supervisor.execution_context import AgentExecutionContext
from app.agents.state import DeepAgentState
from app.services.quality_gate_service import (
    QualityGateService, ContentType, ValidationResult
)

logger = central_logger.get_logger(__name__)


class QualityValidator:
    """Handles quality validation logic for supervisor agents."""
    
    def __init__(self, quality_gate_service: Optional[QualityGateService],
                 strict_mode: bool = False):
        """Initialize quality validator."""
        self.quality_gate_service = quality_gate_service
        self.strict_mode = strict_mode
        self.quality_stats: Dict[str, int] = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'retried': 0,
            'fallbacks_used': 0
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
        
        content_type = self._get_content_type_for_agent(agent_name)
        validation_result = await self._perform_validation(
            agent_output, content_type, context, agent_name, state
        )
        
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
        return await self.quality_gate_service.validate_content(
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
        agent_output_map = {
            'TriageSubAgent': lambda s: s.triage_result.get('summary', '') if hasattr(s, 'triage_result') else None,
            'DataSubAgent': lambda s: s.data_result.get('data', '') if hasattr(s, 'data_result') else None,
            'OptimizationsCoreSubAgent': lambda s: s.optimizations_result.get('recommendations', '') if hasattr(s, 'optimizations_result') else None,
            'ActionsToMeetGoalsSubAgent': lambda s: s.actions_result.get('actions', '') if hasattr(s, 'actions_result') else None,
            'ReportingSubAgent': lambda s: s.report_result.get('report', '') if hasattr(s, 'report_result') else None
        }
        return agent_output_map.get(agent_name)
    
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


class QualityActions:
    """Handles quality-based actions like retries and fallbacks."""
    
    def __init__(self, quality_validator: QualityValidator,
                 fallback_service: Optional['FallbackResponseService']):
        """Initialize quality actions handler."""
        self.validator = quality_validator
        self.fallback_service = fallback_service
    
    async def handle_validation_failure(self,
                                      context: AgentExecutionContext,
                                      agent_name: str,
                                      state: DeepAgentState,
                                      validation_result: ValidationResult,
                                      agents: Dict[str, Any]) -> None:
        """Handle validation failure with retry or fallback."""
        if validation_result.retry_suggested:
            await self._retry_with_quality_adjustments(
                context, agent_name, state, validation_result, agents
            )
        else:
            await self._apply_fallback_response(
                context, agent_name, state, validation_result
            )
    
    async def _retry_with_quality_adjustments(self,
                                            context: AgentExecutionContext,
                                            agent_name: str,
                                            state: DeepAgentState,
                                            validation_result: ValidationResult,
                                            agents: Dict[str, Any]) -> None:
        """Retry agent execution with quality-based prompt adjustments."""
        self.validator.quality_stats['retried'] += 1
        agent = agents.get(agent_name)
        if not agent:
            return
        
        await self._apply_prompt_adjustments(agent, validation_result)
        await self._execute_agent_retry(agent, state, context.run_id)
        self._restore_original_prompt(agent)
    
    async def _apply_prompt_adjustments(self, agent: Any, 
                                      validation_result: ValidationResult) -> str:
        """Apply prompt adjustments for quality improvement."""
        original_prompt = getattr(agent, 'prompt_template', None)
        if not validation_result.retry_prompt_adjustments or not original_prompt:
            return original_prompt
        
        quality_instructions = self._build_quality_instructions(validation_result)
        if quality_instructions and hasattr(agent, 'prompt_template'):
            agent.prompt_template = f"{original_prompt}\\n\\nQUALITY REQUIREMENTS:\\n{quality_instructions}"
        
        return original_prompt
    
    def _build_quality_instructions(self, validation_result: ValidationResult) -> str:
        """Build quality instructions from validation result."""
        return "\\n".join(
            validation_result.retry_prompt_adjustments.get('additional_instructions', [])
        )
    
    async def _execute_agent_retry(self, agent: Any, state: DeepAgentState, run_id: str) -> None:
        """Execute agent retry."""
        logger.info(f"Retrying {agent.name if hasattr(agent, 'name') else 'unknown'} with quality adjustments")
        await agent.execute(state, run_id, stream_updates=True)
    
    def _restore_original_prompt(self, agent: Any, original_prompt: Optional[str] = None) -> None:
        """Restore original prompt if modified."""
        if hasattr(agent, 'prompt_template') and original_prompt:
            agent.prompt_template = original_prompt
    
    async def _apply_fallback_response(self,
                                     context: AgentExecutionContext,
                                     agent_name: str,
                                     state: DeepAgentState,
                                     validation_result: ValidationResult) -> None:
        """Apply fallback response when quality is too low."""
        if not self.fallback_service:
            return
        
        fallback_context = self._build_fallback_context(
            agent_name, state, validation_result, context
        )
        fallback_response = await self._generate_fallback(fallback_context)
        self._apply_fallback_to_state(state, agent_name, fallback_response)
        
        self.validator.quality_stats['fallbacks_used'] += 1
        logger.info(f"Applied fallback response for {agent_name} due to low quality")
    
    def _build_fallback_context(self, agent_name: str, state: DeepAgentState,
                               validation_result: ValidationResult,
                               context: AgentExecutionContext) -> 'FallbackContext':
        """Build fallback context."""
        from app.services.fallback_response_service import (
            FallbackContext, FailureReason
        )
        
        return FallbackContext(
            agent_name=agent_name,
            content_type=self.validator._get_content_type_for_agent(agent_name),
            failure_reason=FailureReason.LOW_QUALITY,
            user_request=state.user_request,
            attempted_action=f"Generate {agent_name} output",
            quality_metrics=validation_result.metrics,
            retry_count=context.retry_count if hasattr(context, 'retry_count') else 0
        )
    
    async def _generate_fallback(self, fallback_context: 'FallbackContext') -> Dict[str, Any]:
        """Generate fallback response."""
        return await self.fallback_service.generate_fallback(
            fallback_context,
            include_diagnostics=True,
            include_recovery=True
        )
    
    def _apply_fallback_to_state(self, state: DeepAgentState, 
                               agent_name: str, fallback_response: Dict[str, Any]) -> None:
        """Apply fallback response to state."""
        self._replace_agent_output(state, agent_name, fallback_response['response'])
        self._mark_fallback_used(state, agent_name)
    
    def _replace_agent_output(self, state: DeepAgentState, agent_name: str, new_output: str) -> None:
        """Replace an agent's output in the state."""
        updater = self._get_output_updater(agent_name)
        if updater:
            updater(state, new_output)
    
    def _get_output_updater(self, agent_name: str):
        """Get output updater function for agent."""
        agent_update_map = {
            'TriageSubAgent': lambda s, o: setattr(s, 'triage_result', {'summary': o, 'category': 'Fallback'}),
            'DataSubAgent': lambda s, o: setattr(s, 'data_result', {'data': o}),
            'OptimizationsCoreSubAgent': lambda s, o: setattr(s, 'optimizations_result', {'recommendations': o}),
            'ActionsToMeetGoalsSubAgent': lambda s, o: setattr(s, 'actions_result', {'actions': o}),
            'ReportingSubAgent': lambda s, o: setattr(s, 'report_result', {'report': o})
        }
        return agent_update_map.get(agent_name)
    
    def _mark_fallback_used(self, state: DeepAgentState, agent_name: str) -> None:
        """Mark that fallback was used for this agent."""
        if not hasattr(state, 'fallbacks_used'):
            state.fallbacks_used = {}
        state.fallbacks_used[agent_name] = True