# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:44.451152+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to supervisor agents
# Git: v6 | 2c55fb99 | dirty (24 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: 8743fc1b-f4dd-445e-b9cf-aa1c8ccb4103 | Seq: 2
# Review: Pending | Score: 85
# ================================
"""Quality-Enhanced Supervisor Agent

This module wraps the supervisor with quality gates to prevent AI slop
and ensure high-quality outputs from all agents.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio

from app.logging_config import central_logger
from app.agents.supervisor_consolidated import SupervisorAgent, AgentExecutionContext
from app.agents.state import DeepAgentState
from app.services.quality_gate_service import (
    QualityGateService, ContentType, QualityMetrics, ValidationResult
)
from app.services.fallback_response_service import (
    FallbackResponseService, FallbackContext, FailureReason
)
from app.services.quality_monitoring_service import QualityMonitoringService
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher

logger = central_logger.get_logger(__name__)


class QualityEnhancedSupervisor(SupervisorAgent):
    """Supervisor with integrated quality gates and monitoring"""
    
    def __init__(self,
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: Any,
                 tool_dispatcher: ToolDispatcher,
                 enable_quality_gates: bool = True,
                 strict_mode: bool = False):
        """
        Initialize quality-enhanced supervisor
        
        Args:
            enable_quality_gates: Whether to enable quality validation
            strict_mode: If True, apply stricter quality thresholds
        """
        super().__init__(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Quality services
        self.quality_gate_service = QualityGateService() if enable_quality_gates else None
        self.fallback_service = FallbackResponseService() if enable_quality_gates else None
        self.monitoring_service = QualityMonitoringService() if enable_quality_gates else None
        
        self.enable_quality_gates = enable_quality_gates
        self.strict_mode = strict_mode
        
        # Quality statistics
        self.quality_stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'retried': 0,
            'fallbacks_used': 0
        }
        
        # Register quality hooks
        if enable_quality_gates:
            self._register_quality_hooks()
            asyncio.create_task(self._start_monitoring())
        
        logger.info(f"Quality-Enhanced Supervisor initialized (quality_gates={'enabled' if enable_quality_gates else 'disabled'})")
    
    def _register_quality_hooks(self):
        """Register quality validation hooks"""
        # Add quality validation after each agent
        self.hooks["after_agent"].append(self._quality_validation_hook)
        
        # Add quality monitoring hook
        self.hooks["after_agent"].append(self._quality_monitoring_hook)
        
        # Add fallback generation on error
        self.hooks["on_error"].append(self._fallback_generation_hook)
        
        # Add quality-based retry decision
        self.hooks["on_retry"].append(self._quality_retry_hook)
    
    async def _start_monitoring(self):
        """Start the quality monitoring service"""
        if self.monitoring_service:
            await self.monitoring_service.start_monitoring(interval_seconds=30)
    
    async def _quality_validation_hook(self, 
                                      context: AgentExecutionContext,
                                      agent_name: str,
                                      state: DeepAgentState):
        """Validate agent output quality"""
        if not self.quality_gate_service:
            return
        
        try:
            # Get the agent's output from state
            agent_output = self._extract_agent_output(state, agent_name)
            if not agent_output:
                return
            
            # Determine content type based on agent
            content_type = self._get_content_type_for_agent(agent_name)
            
            # Validate the output
            validation_result = await self.quality_gate_service.validate_content(
                content=agent_output,
                content_type=content_type,
                context={
                    'user_request': state.user_request,
                    'agent_name': agent_name,
                    'run_id': context.run_id
                },
                strict_mode=self.strict_mode
            )
            
            # Update statistics
            self.quality_stats['total_validations'] += 1
            
            # Handle validation result
            if not validation_result.passed:
                self.quality_stats['failed'] += 1
                logger.warning(
                    f"Quality validation failed for {agent_name}: "
                    f"Score={validation_result.metrics.overall_score:.2f}, "
                    f"Issues={validation_result.metrics.issues}"
                )
                
                # Decide on action based on quality score
                if validation_result.retry_suggested:
                    # Retry with adjusted prompts
                    await self._retry_with_quality_adjustments(
                        context, agent_name, state, validation_result
                    )
                else:
                    # Use fallback response
                    await self._apply_fallback_response(
                        context, agent_name, state, validation_result
                    )
            else:
                self.quality_stats['passed'] += 1
                logger.info(
                    f"Quality validation passed for {agent_name}: "
                    f"Score={validation_result.metrics.overall_score:.2f}"
                )
            
            # Store validation metrics in state for tracking
            if not hasattr(state, 'quality_metrics'):
                state.quality_metrics = {}
            state.quality_metrics[agent_name] = validation_result.metrics
            
        except Exception as e:
            logger.error(f"Error in quality validation hook: {str(e)}")
    
    async def _quality_monitoring_hook(self,
                                      context: AgentExecutionContext,
                                      agent_name: str,
                                      state: DeepAgentState):
        """Record quality metrics for monitoring"""
        if not self.monitoring_service or not hasattr(state, 'quality_metrics'):
            return
        
        try:
            metrics = state.quality_metrics.get(agent_name)
            if metrics:
                await self.monitoring_service.record_quality_event(
                    agent_name=agent_name,
                    content_type=self._get_content_type_for_agent(agent_name),
                    metrics=metrics,
                    user_id=context.user_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id
                )
        except Exception as e:
            logger.error(f"Error in quality monitoring hook: {str(e)}")
    
    async def _fallback_generation_hook(self,
                                       context: AgentExecutionContext,
                                       error: Exception,
                                       agent_name: str):
        """Generate fallback response on error"""
        if not self.fallback_service:
            return
        
        try:
            fallback_context = FallbackContext(
                agent_name=agent_name,
                content_type=self._get_content_type_for_agent(agent_name),
                failure_reason=FailureReason.LLM_ERROR,
                user_request=context.metadata.get('user_request', ''),
                attempted_action=f"Execute {agent_name}",
                error_details=str(error),
                retry_count=context.retry_count
            )
            
            fallback_response = await self.fallback_service.generate_fallback(
                fallback_context,
                include_diagnostics=True,
                include_recovery=True
            )
            
            # Store fallback in context for use
            context.metadata['fallback_response'] = fallback_response
            self.quality_stats['fallbacks_used'] += 1
            
            logger.info(f"Generated fallback response for {agent_name} error")
            
        except Exception as e:
            logger.error(f"Error generating fallback: {str(e)}")
    
    async def _quality_retry_hook(self,
                                 context: AgentExecutionContext,
                                 agent_name: str,
                                 retry_count: int) -> bool:
        """Decide whether to retry based on quality metrics"""
        if not hasattr(context, 'metadata') or 'quality_validation' not in context.metadata:
            return retry_count < context.max_retries
        
        validation_result = context.metadata['quality_validation']
        
        # Don't retry if quality is extremely poor
        if validation_result.metrics.overall_score < 0.2:
            logger.info(f"Skipping retry for {agent_name} due to very low quality score")
            return False
        
        # Allow retry if suggested and under limit
        return validation_result.retry_suggested and retry_count < context.max_retries
    
    async def _retry_with_quality_adjustments(self,
                                             context: AgentExecutionContext,
                                             agent_name: str,
                                             state: DeepAgentState,
                                             validation_result: ValidationResult):
        """Retry agent execution with quality-based prompt adjustments"""
        try:
            self.quality_stats['retried'] += 1
            
            # Get the agent
            agent = self.agents.get(agent_name)
            if not agent:
                return
            
            # Apply prompt adjustments
            if validation_result.retry_prompt_adjustments:
                original_prompt = agent.prompt_template if hasattr(agent, 'prompt_template') else None
                
                # Add quality instructions to prompt
                quality_instructions = "\n".join(
                    validation_result.retry_prompt_adjustments.get('additional_instructions', [])
                )
                
                if quality_instructions and hasattr(agent, 'prompt_template'):
                    agent.prompt_template = f"{original_prompt}\n\nQUALITY REQUIREMENTS:\n{quality_instructions}"
                
                # Adjust LLM parameters
                if 'temperature' in validation_result.retry_prompt_adjustments:
                    # Would need to pass this to LLM manager
                    pass
            
            # Retry execution
            logger.info(f"Retrying {agent_name} with quality adjustments")
            
            # Execute agent again
            await agent.execute(state, context.run_id, stream_updates=True)
            
            # Restore original prompt if modified
            if hasattr(agent, 'prompt_template') and original_prompt:
                agent.prompt_template = original_prompt
                
        except Exception as e:
            logger.error(f"Error in quality retry: {str(e)}")
    
    async def _apply_fallback_response(self,
                                      context: AgentExecutionContext,
                                      agent_name: str,
                                      state: DeepAgentState,
                                      validation_result: ValidationResult):
        """Apply fallback response when quality is too low"""
        if not self.fallback_service:
            return
        
        try:
            fallback_context = FallbackContext(
                agent_name=agent_name,
                content_type=self._get_content_type_for_agent(agent_name),
                failure_reason=FailureReason.LOW_QUALITY,
                user_request=state.user_request,
                attempted_action=f"Generate {agent_name} output",
                quality_metrics=validation_result.metrics,
                retry_count=context.retry_count
            )
            
            fallback_response = await self.fallback_service.generate_fallback(
                fallback_context,
                include_diagnostics=True,
                include_recovery=True
            )
            
            # Replace agent output with fallback
            self._replace_agent_output(state, agent_name, fallback_response['response'])
            
            # Mark in state that fallback was used
            if not hasattr(state, 'fallbacks_used'):
                state.fallbacks_used = {}
            state.fallbacks_used[agent_name] = True
            
            self.quality_stats['fallbacks_used'] += 1
            
            logger.info(f"Applied fallback response for {agent_name} due to low quality")
            
        except Exception as e:
            logger.error(f"Error applying fallback: {str(e)}")
    
    def _extract_agent_output(self, state: DeepAgentState, agent_name: str) -> Optional[str]:
        """Extract the output from an agent's execution"""
        # Map agent names to their state attributes
        agent_output_map = {
            'TriageSubAgent': lambda s: s.triage_result.get('summary', '') if hasattr(s, 'triage_result') else None,
            'DataSubAgent': lambda s: s.data_result.get('data', '') if hasattr(s, 'data_result') else None,
            'OptimizationsCoreSubAgent': lambda s: s.optimizations_result.get('recommendations', '') if hasattr(s, 'optimizations_result') else None,
            'ActionsToMeetGoalsSubAgent': lambda s: s.actions_result.get('actions', '') if hasattr(s, 'actions_result') else None,
            'ReportingSubAgent': lambda s: s.report_result.get('report', '') if hasattr(s, 'report_result') else None
        }
        
        extractor = agent_output_map.get(agent_name)
        if extractor:
            output = extractor(state)
            if output:
                # Convert to string if needed
                return str(output) if not isinstance(output, str) else output
        
        return None
    
    def _replace_agent_output(self, state: DeepAgentState, agent_name: str, new_output: str):
        """Replace an agent's output in the state"""
        # Map agent names to their state update functions
        agent_update_map = {
            'TriageSubAgent': lambda s, o: setattr(s, 'triage_result', {'summary': o, 'category': 'Fallback'}),
            'DataSubAgent': lambda s, o: setattr(s, 'data_result', {'data': o}),
            'OptimizationsCoreSubAgent': lambda s, o: setattr(s, 'optimizations_result', {'recommendations': o}),
            'ActionsToMeetGoalsSubAgent': lambda s, o: setattr(s, 'actions_result', {'actions': o}),
            'ReportingSubAgent': lambda s, o: setattr(s, 'report_result', {'report': o})
        }
        
        updater = agent_update_map.get(agent_name)
        if updater:
            updater(state, new_output)
    
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
    
    async def get_quality_dashboard(self) -> Dict[str, Any]:
        """Get quality dashboard data"""
        dashboard_data = {
            'quality_stats': self.quality_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.monitoring_service:
            monitoring_data = await self.monitoring_service.get_dashboard_data()
            dashboard_data.update(monitoring_data)
        
        return dashboard_data
    
    async def get_agent_quality_report(self, agent_name: str, period_hours: int = 24) -> Dict[str, Any]:
        """Get quality report for a specific agent"""
        if self.monitoring_service:
            return await self.monitoring_service.get_agent_report(agent_name, period_hours)
        return {'error': 'Quality monitoring not enabled'}
    
    async def shutdown(self):
        """Shutdown the supervisor and quality services"""
        if self.monitoring_service:
            await self.monitoring_service.stop_monitoring()
        
        logger.info(f"Quality stats at shutdown: {self.quality_stats}")
        await super().shutdown()