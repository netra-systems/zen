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

from app.agents.supervisor.execution_context import AgentExecutionContext
from app.agents.state import DeepAgentState
from app.services.fallback_response_service import (
    FallbackResponseService, FallbackContext, FailureReason
)
from app.services.quality_gate_service import ValidationResult, ContentType
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class QualityFallbackManager:
    """Manages quality-based fallback responses with 8-line function limit"""
    
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
        
        try:
            await self._generate_error_fallback(context, error, agent_name)
        except Exception as e:
            logger.error(f"Error generating fallback: {str(e)}")
    
    async def _generate_error_fallback(self,
                                     context: AgentExecutionContext,
                                     error: Exception,
                                     agent_name: str) -> None:
        """Generate fallback for error conditions"""
        fallback_context = self._create_error_fallback_context(
            context, error, agent_name
        )
        
        fallback_response = await self.fallback_service.generate_fallback(
            fallback_context,
            include_diagnostics=True,
            include_recovery=True
        )
        
        self._store_error_fallback(context, fallback_response, agent_name)
    
    def _create_error_fallback_context(self,
                                     context: AgentExecutionContext,
                                     error: Exception,
                                     agent_name: str) -> FallbackContext:
        """Create fallback context for error conditions"""
        return FallbackContext(
            agent_name=agent_name,
            content_type=self._get_content_type_for_agent(agent_name),
            failure_reason=FailureReason.LLM_ERROR,
            user_request=context.metadata.get('user_request', ''),
            attempted_action=f"Execute {agent_name}",
            error_details=str(error),
            retry_count=context.retry_count
        )
    
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
        try:
            self._increment_retry_stats()
            agent = self._get_agent(agents, agent_name)
            
            if agent:
                await self._execute_retry_with_adjustments(
                    agent, validation_result, state, context
                )
        except Exception as e:
            logger.error(f"Error in quality retry: {str(e)}")
    
    def _increment_retry_stats(self) -> None:
        """Increment retry statistics"""
        self.fallback_stats['retries_attempted'] += 1
    
    def _get_agent(self, agents: Dict[str, Any], agent_name: str) -> Optional[Any]:
        """Get agent from agents dictionary"""
        return agents.get(agent_name)
    
    async def _execute_retry_with_adjustments(self,
                                            agent: Any,
                                            validation_result: ValidationResult,
                                            state: DeepAgentState,
                                            context: AgentExecutionContext) -> None:
        """Execute retry with quality adjustments"""
        original_prompt = self._apply_prompt_adjustments(agent, validation_result)
        
        logger.info(f"Retrying {agent.__class__.__name__} with quality adjustments")
        
        await agent.execute(state, context.run_id, stream_updates=True)
        
        self._restore_original_prompt(agent, original_prompt)
    
    def _apply_prompt_adjustments(self,
                                agent: Any,
                                validation_result: ValidationResult) -> Optional[str]:
        """Apply prompt adjustments to agent"""
        if not validation_result.retry_prompt_adjustments:
            return None
        
        original_prompt = getattr(agent, 'prompt_template', None)
        if not original_prompt:
            return None
        
        quality_instructions = self._get_quality_instructions(validation_result)
        agent.prompt_template = f"{original_prompt}\n\nQUALITY REQUIREMENTS:\n{quality_instructions}"
        
        return original_prompt
    
    def _get_quality_instructions(self, validation_result: ValidationResult) -> str:
        """Get quality instructions from validation result"""
        adjustments = validation_result.retry_prompt_adjustments
        instructions = adjustments.get('additional_instructions', [])
        return "\n".join(instructions)
    
    def _restore_original_prompt(self, agent: Any, original_prompt: Optional[str]) -> None:
        """Restore original prompt template"""
        if original_prompt and hasattr(agent, 'prompt_template'):
            agent.prompt_template = original_prompt
    
    async def apply_fallback_response(self,
                                    context: AgentExecutionContext,
                                    agent_name: str,
                                    state: DeepAgentState,
                                    validation_result: ValidationResult) -> None:
        """Apply fallback response when quality is too low"""
        if not self.fallback_service:
            return
        
        try:
            await self._generate_quality_fallback(
                context, agent_name, state, validation_result
            )
        except Exception as e:
            logger.error(f"Error applying fallback: {str(e)}")
    
    async def _generate_quality_fallback(self,
                                       context: AgentExecutionContext,
                                       agent_name: str,
                                       state: DeepAgentState,
                                       validation_result: ValidationResult) -> None:
        """Generate fallback for quality issues"""
        fallback_context = self._create_quality_fallback_context(
            agent_name, state, validation_result, context
        )
        
        fallback_response = await self.fallback_service.generate_fallback(
            fallback_context,
            include_diagnostics=True,
            include_recovery=True
        )
        
        self._apply_quality_fallback_response(state, agent_name, fallback_response)
    
    def _create_quality_fallback_context(self,
                                       agent_name: str,
                                       state: DeepAgentState,
                                       validation_result: ValidationResult,
                                       context: AgentExecutionContext) -> FallbackContext:
        """Create fallback context for quality issues"""
        return FallbackContext(
            agent_name=agent_name,
            content_type=self._get_content_type_for_agent(agent_name),
            failure_reason=FailureReason.LOW_QUALITY,
            user_request=state.user_request,
            attempted_action=f"Generate {agent_name} output",
            quality_metrics=validation_result.metrics,
            retry_count=context.retry_count
        )
    
    def _apply_quality_fallback_response(self,
                                       state: DeepAgentState,
                                       agent_name: str,
                                       fallback_response: Dict[str, Any]) -> None:
        """Apply quality fallback response to state"""
        self._replace_agent_output(state, agent_name, fallback_response['response'])
        self._mark_fallback_used(state, agent_name)
        
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
        return {
            'TriageSubAgent': lambda s, o: setattr(s, 'triage_result', {'summary': o, 'category': 'Fallback'}),
            'DataSubAgent': lambda s, o: setattr(s, 'data_result', {'data': o}),
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
        mapping = {
            'TriageSubAgent': ContentType.TRIAGE,
            'DataSubAgent': ContentType.DATA_ANALYSIS,
            'OptimizationsCoreSubAgent': ContentType.OPTIMIZATION,
            'ActionsToMeetGoalsSubAgent': ContentType.ACTION_PLAN,
            'ReportingSubAgent': ContentType.REPORT
        }
        return mapping.get(agent_name, ContentType.GENERAL)
    
    def get_fallback_stats(self) -> Dict[str, int]:
        """Get fallback statistics"""
        return self.fallback_stats.copy()