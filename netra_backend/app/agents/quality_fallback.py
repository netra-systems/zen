# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Quality fallback handling module ≤300 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 8
# Review: Pending | Score: 90
# ================================

"""
Quality Fallback Response Handling

This module handles fallback response generation and agent output replacement
when quality validation fails. All functions are ≤8 lines.
"""

from typing import Dict, Any, Optional
from datetime import datetime, UTC

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.fallback_response_service import (
    FallbackResponseService, FallbackContext, FailureReason
)
from netra_backend.app.services.quality_gate_service import ValidationResult, ContentType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class QualityFallbackManager:
    """Manages quality-based fallback responses with 25-line function limit"""
    
    def __init__(self, fallback_service: Optional[FallbackResponseService]):
        self.fallback_service = fallback_service
        self.fallback_stats = {'fallbacks_used': 0, 'retries_attempted': 0}
    
    async def fallback_generation_hook(self,
                                     context: AgentExecutionContext,
                                     error: Exception,
                                     agent_name: str) -> None:
        """Generate fallback response on error"""
        if not self.fallback_service:
            return
        await self._safe_generate_error_fallback(context, error, agent_name)
    
    async def _safe_generate_error_fallback(self, context: AgentExecutionContext, error: Exception, agent_name: str) -> None:
        """Safely generate error fallback with exception handling"""
        try:
            await self._generate_error_fallback(context, error, agent_name)
        except Exception as e:
            logger.error(f"Error generating fallback: {str(e)}")
    
    async def _generate_error_fallback(self,
                                     context: AgentExecutionContext,
                                     error: Exception,
                                     agent_name: str) -> None:
        """Generate fallback for error conditions"""
        fallback_context = self._create_error_fallback_context(context, error, agent_name)
        fallback_response = await self._get_error_fallback_response(fallback_context)
        self._store_error_fallback(context, fallback_response, agent_name)
    
    async def _get_error_fallback_response(self, fallback_context) -> Dict[str, Any]:
        """Get fallback response from service"""
        return await self.fallback_service.generate_fallback(
            fallback_context,
            include_diagnostics=True,
            include_recovery=True
        )
    
    def _create_error_fallback_context(self,
                                     context: AgentExecutionContext,
                                     error: Exception,
                                     agent_name: str) -> FallbackContext:
        """Create fallback context for error conditions"""
        return self._build_error_fallback_context(
            agent_name, context, error
        )
    
    def _build_error_fallback_context(self,
                                     agent_name: str,
                                     context: AgentExecutionContext,
                                     error: Exception) -> FallbackContext:
        """Build fallback context with error details"""
        return self._construct_error_fallback_context(
            agent_name, context, error
        )
    
    def _construct_error_fallback_context(self,
                                         agent_name: str,
                                         context: AgentExecutionContext,
                                         error: Exception) -> FallbackContext:
        """Construct fallback context object"""
        basic_params = self._get_basic_error_context_params(agent_name, context)
        error_params = self._get_error_context_params(error, context)
        return FallbackContext(**basic_params, **error_params)
    
    def _get_basic_error_context_params(self, agent_name: str, context: AgentExecutionContext) -> Dict[str, Any]:
        """Get basic error context parameters"""
        return {
            'agent_name': agent_name,
            'content_type': self._get_content_type_for_agent(agent_name),
            'failure_reason': FailureReason.LLM_ERROR,
            'user_request': context.metadata.get('user_request', ''),
        }
    
    def _get_error_context_params(self, error: Exception, context: AgentExecutionContext) -> Dict[str, Any]:
        """Get error-specific context parameters"""
        return {
            'attempted_action': f"Execute {context.metadata.get('agent_name', 'agent')}",
            'error_details': str(error),
            'retry_count': context.retry_count
        }
    
    def _store_error_fallback(self,
                            context: AgentExecutionContext,
                            fallback_response: Dict[str, Any],
                            agent_name: str) -> None:
        """Store error fallback in context"""
        context.metadata['fallback_response'] = fallback_response
        self.fallback_stats['fallbacks_used'] += 1
        logger.info(f"Generated fallback response for {agent_name} error")
    
    async def retry_with_quality_adjustments(self,
                                           context: AgentExecutionContext,
                                           agent_name: str,
                                           state: DeepAgentState,
                                           validation_result: ValidationResult,
                                           agents: Dict[str, Any]) -> None:
        """Retry agent execution with quality-based prompt adjustments"""
        await self._safe_retry_with_adjustments(context, agent_name, state, validation_result, agents)
    
    async def _safe_retry_with_adjustments(self,
                                         context: AgentExecutionContext,
                                         agent_name: str,
                                         state: DeepAgentState,
                                         validation_result: ValidationResult,
                                         agents: Dict[str, Any]) -> None:
        """Safely retry with adjustments and exception handling"""
        try:
            await self._perform_retry_with_adjustments(context, agent_name, state, validation_result, agents)
        except Exception as e:
            logger.error(f"Error in quality retry: {str(e)}")
    
    async def _perform_retry_with_adjustments(self,
                                            context: AgentExecutionContext,
                                            agent_name: str,
                                            state: DeepAgentState,
                                            validation_result: ValidationResult,
                                            agents: Dict[str, Any]) -> None:
        """Perform retry with quality adjustments"""
        self._increment_retry_stats()
        agent = self._get_agent(agents, agent_name)
        if agent:
            await self._execute_retry_with_adjustments(agent, validation_result, state, context)
    
    def _increment_retry_stats(self) -> None:
        """Increment retry statistics"""
        self.fallback_stats['retries_attempted'] += 1
    
    def _get_agent(self, agents: Dict[str, Any], agent_name: str) -> Optional[Any]:
        """Get agent from agents dictionary"""
        return agents.get(agent_name)
    
    async def _execute_retry_with_adjustments(self, agent: Any, validation_result: ValidationResult, state: DeepAgentState, context: AgentExecutionContext) -> None:
        """Execute retry with quality adjustments"""
        original_prompt = self._apply_prompt_adjustments(agent, validation_result)
        await self._perform_agent_retry(agent, state, context)
        self._restore_original_prompt(agent, original_prompt)
    
    async def _perform_agent_retry(self, agent: Any, state: DeepAgentState, context: AgentExecutionContext) -> None:
        """Perform agent retry execution"""
        logger.info(f"Retrying {agent.__class__.__name__} with quality adjustments")
        await agent.execute(state, context.run_id, stream_updates=True)
    
    def _apply_prompt_adjustments(self,
                                agent: Any,
                                validation_result: ValidationResult) -> Optional[str]:
        """Apply prompt adjustments to agent"""
        if not self._should_apply_adjustments(validation_result):
            return None
        return self._modify_agent_prompt(agent, validation_result)
    
    def _should_apply_adjustments(self, validation_result: ValidationResult) -> bool:
        """Check if adjustments should be applied"""
        return bool(validation_result.retry_prompt_adjustments)
    
    def _modify_agent_prompt(self, agent: Any, validation_result: ValidationResult) -> Optional[str]:
        """Modify agent prompt with quality instructions"""
        original_prompt = getattr(agent, 'prompt_template', None)
        if not original_prompt:
            return None
        self._update_agent_prompt_template(agent, original_prompt, validation_result)
        return original_prompt
    
    def _update_agent_prompt_template(self, agent: Any, original_prompt: str, validation_result: ValidationResult) -> None:
        """Update agent prompt template with quality requirements"""
        quality_instructions = self._get_quality_instructions(validation_result)
        agent.prompt_template = f"{original_prompt}\n\nQUALITY REQUIREMENTS:\n{quality_instructions}"
    
    def _get_quality_instructions(self, validation_result: ValidationResult) -> str:
        """Get quality instructions from validation result"""
        adjustments = validation_result.retry_prompt_adjustments
        instructions = adjustments.get('additional_instructions', [])
        return "\n".join(instructions)
    
    def _restore_original_prompt(self, agent: Any, original_prompt: Optional[str]) -> None:
        """Restore original prompt template"""
        if original_prompt and hasattr(agent, 'prompt_template'):
            agent.prompt_template = original_prompt
    
    async def apply_fallback_response(self, context: AgentExecutionContext, agent_name: str, state: DeepAgentState, validation_result: ValidationResult) -> None:
        """Apply fallback response when quality is too low"""
        if not self.fallback_service:
            return
        await self._safe_apply_quality_fallback(context, agent_name, state, validation_result)
    
    async def _safe_apply_quality_fallback(self,
                                         context: AgentExecutionContext,
                                         agent_name: str,
                                         state: DeepAgentState,
                                         validation_result: ValidationResult) -> None:
        """Safely apply quality fallback with exception handling"""
        try:
            await self._generate_quality_fallback(context, agent_name, state, validation_result)
        except Exception as e:
            logger.error(f"Error applying fallback: {str(e)}")
    
    async def _generate_quality_fallback(self, context: AgentExecutionContext, agent_name: str, state: DeepAgentState, validation_result: ValidationResult) -> None:
        """Generate fallback for quality issues"""
        fallback_context = self._create_quality_fallback_context(agent_name, state, validation_result, context)
        fallback_response = await self._get_quality_fallback_response(fallback_context)
        self._apply_quality_fallback_response(state, agent_name, fallback_response)
    
    async def _get_quality_fallback_response(self, fallback_context) -> Dict[str, Any]:
        """Get quality fallback response from service"""
        return await self.fallback_service.generate_fallback(
            fallback_context,
            include_diagnostics=True,
            include_recovery=True
        )
    
    def _create_quality_fallback_context(self, agent_name: str, state: DeepAgentState, validation_result: ValidationResult, context: AgentExecutionContext) -> FallbackContext:
        """Create fallback context for quality issues"""
        return self._build_quality_fallback_context(agent_name, state, validation_result, context)
    
    def _build_quality_fallback_context(self, agent_name: str, state: DeepAgentState, validation_result: ValidationResult, context: AgentExecutionContext) -> FallbackContext:
        """Build fallback context with quality details"""
        basic_params = self._get_basic_quality_context_params(agent_name, state)
        quality_params = self._get_quality_context_params(validation_result, context)
        return FallbackContext(**basic_params, **quality_params)
    
    def _get_basic_quality_context_params(self, agent_name: str, state: DeepAgentState) -> Dict[str, Any]:
        """Get basic quality context parameters"""
        return {
            'agent_name': agent_name,
            'content_type': self._get_content_type_for_agent(agent_name),
            'failure_reason': FailureReason.LOW_QUALITY,
            'user_request': state.user_request,
        }
    
    def _get_quality_context_params(self, validation_result: ValidationResult, context: AgentExecutionContext) -> Dict[str, Any]:
        """Get quality-specific context parameters"""
        return {
            'attempted_action': f"Generate {context.metadata.get('agent_name', 'agent')} output",
            'quality_metrics': validation_result.metrics,
            'retry_count': context.retry_count
        }
    
    def _apply_quality_fallback_response(self,
                                       state: DeepAgentState,
                                       agent_name: str,
                                       fallback_response: Dict[str, Any]) -> None:
        """Apply quality fallback response to state"""
        self._replace_agent_output(state, agent_name, fallback_response['response'])
        self._mark_fallback_used(state, agent_name)
        self._update_fallback_stats_and_log(agent_name)
    
    def _update_fallback_stats_and_log(self, agent_name: str) -> None:
        """Update fallback statistics and log the operation"""
        self.fallback_stats['fallbacks_used'] += 1
        logger.info(f"Applied fallback response for {agent_name} due to low quality")
    
    def _replace_agent_output(self, state: DeepAgentState, agent_name: str, new_output: str) -> None:
        """Replace an agent's output in the state"""
        agent_update_map = self._get_agent_update_map()
        updater = agent_update_map.get(agent_name)
        
        if updater:
            updater(state, new_output)
    
    def _get_agent_update_map(self) -> Dict[str, callable]:
        """Get mapping of agent names to state update functions"""
        return self._create_agent_update_mappings()
    
    def _create_agent_update_mappings(self) -> Dict[str, callable]:
        """Create agent update function mappings"""
        mappings = self._get_basic_agent_mappings()
        mappings.update(self._get_extended_agent_mappings())
        return mappings
    
    def _get_basic_agent_mappings(self) -> Dict[str, callable]:
        """Get basic agent mappings"""
        return {
            'TriageSubAgent': lambda s, o: setattr(s, 'triage_result', {'summary': o, 'category': 'Fallback'}),
            'DataSubAgent': lambda s, o: setattr(s, 'data_result', {'data': o})
        }
    
    def _get_extended_agent_mappings(self) -> Dict[str, callable]:
        """Get extended agent mappings"""
        return {
            'OptimizationsCoreSubAgent': lambda s, o: setattr(s, 'optimizations_result', {'recommendations': o}),
            'ActionsToMeetGoalsSubAgent': lambda s, o: setattr(s, 'actions_result', {'actions': o}),
            'ReportingSubAgent': lambda s, o: setattr(s, 'report_result', {'report': o})
        }
    
    def _mark_fallback_used(self, state: DeepAgentState, agent_name: str) -> None:
        """Mark that fallback was used in state"""
        if not hasattr(state, 'fallbacks_used'):
            state.fallbacks_used = {}
        state.fallbacks_used[agent_name] = True
    
    def _get_content_type_for_agent(self, agent_name: str) -> ContentType:
        """Map agent name to content type"""
        mapping = self._create_content_type_mappings()
        return mapping.get(agent_name, ContentType.GENERAL)
    
    def _create_content_type_mappings(self) -> Dict[str, ContentType]:
        """Create content type mappings for agents"""
        mappings = self._get_basic_content_mappings()
        mappings.update(self._get_extended_content_mappings())
        return mappings
    
    def _get_basic_content_mappings(self) -> Dict[str, ContentType]:
        """Get basic content type mappings"""
        return {
            'TriageSubAgent': ContentType.TRIAGE,
            'DataSubAgent': ContentType.DATA_ANALYSIS
        }
    
    def _get_extended_content_mappings(self) -> Dict[str, ContentType]:
        """Get extended content type mappings"""
        return {
            'OptimizationsCoreSubAgent': ContentType.OPTIMIZATION,
            'ActionsToMeetGoalsSubAgent': ContentType.ACTION_PLAN,
            'ReportingSubAgent': ContentType.REPORT
        }
    
    def get_fallback_stats(self) -> Dict[str, int]:
        """Get fallback statistics"""
        return self.fallback_stats.copy()