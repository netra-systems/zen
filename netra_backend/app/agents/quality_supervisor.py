# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Refactor to  <= 300 lines, functions  <= 8 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 9
# Review: Pending | Score: 90
# ================================

"""
Quality-Enhanced Supervisor Agent

This module wraps the supervisor with quality gates to prevent AI slop
and ensure high-quality outputs from all agents. All functions  <= 8 lines.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.quality_fallback import QualityFallbackManager
from netra_backend.app.agents.quality_hooks import QualityHooksManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.fallback_response_service import FallbackResponseService
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import (
    QualityMonitoringService,
)

logger = central_logger.get_logger(__name__)


class QualityEnhancedSupervisor:
    """Supervisor with integrated quality gates and monitoring"""
    
    def __init__(self,
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: 'WebSocketManager',
                 tool_dispatcher: UnifiedToolDispatcher,
                 enable_quality_gates: bool = True,
                 strict_mode: bool = False):
        """Initialize quality-enhanced supervisor with modular components"""
        super().__init__(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        self.enable_quality_gates = enable_quality_gates
        self.strict_mode = strict_mode
        
        self._initialize_quality_services()
        self._initialize_managers()
        self._register_hooks_if_enabled()
    
    def _initialize_quality_services(self) -> None:
        """Initialize quality services"""
        if self.enable_quality_gates:
            self.quality_gate_service = QualityGateService()
            self.fallback_service = FallbackResponseService()
            self.monitoring_service = QualityMonitoringService()
        else:
            self.quality_gate_service = None
            self.fallback_service = None
            self.monitoring_service = None
    
    def _initialize_managers(self) -> None:
        """Initialize quality management components"""
        self.hooks_manager = QualityHooksManager(
            self.quality_gate_service,
            self.monitoring_service,
            self.strict_mode
        )
        self.fallback_manager = QualityFallbackManager(self.fallback_service)
    
    def _register_hooks_if_enabled(self) -> None:
        """Register quality hooks if quality gates are enabled"""
        if self.enable_quality_gates:
            self._register_quality_hooks()
            asyncio.create_task(self._start_monitoring())
        
        self._log_initialization()
    
    def _register_quality_hooks(self) -> None:
        """Register quality validation hooks"""
        self.hooks["after_agent"].append(self._quality_validation_hook)
        self.hooks["after_agent"].append(self._quality_monitoring_hook)
        self.hooks["on_error"].append(self._fallback_generation_hook)
        self.hooks["on_retry"].append(self._quality_retry_hook)
    
    def _log_initialization(self) -> None:
        """Log supervisor initialization"""
        status = 'enabled' if self.enable_quality_gates else 'disabled'
        logger.info(f"Quality-Enhanced Supervisor initialized (quality_gates={status})")
    
    async def _start_monitoring(self) -> None:
        """Start the quality monitoring service"""
        if self.monitoring_service:
            await self.monitoring_service.start_monitoring(interval_seconds=30)
    
    async def _quality_validation_hook(self, 
                                     context: AgentExecutionContext,
                                     agent_name: str,
                                     state: DeepAgentState) -> None:
        """Hook for quality validation"""
        await self.hooks_manager.quality_validation_hook(context, agent_name, state)
        await self._handle_validation_result(context, agent_name, state)
    
    async def _handle_validation_result(self,
                                      context: AgentExecutionContext,
                                      agent_name: str,
                                      state: DeepAgentState) -> None:
        """Handle quality validation results"""
        if not self._has_quality_metrics(state, agent_name):
            return
        
        validation_result = self._get_validation_result(state, agent_name)
        if not validation_result.passed:
            await self._handle_failed_validation(
                context, agent_name, state, validation_result
            )
    
    def _has_quality_metrics(self, state: DeepAgentState, agent_name: str) -> bool:
        """Check if quality metrics exist"""
        return (
            hasattr(state, 'quality_metrics') and
            state.quality_metrics.get(agent_name) is not None
        )
    
    def _get_validation_result(self, state: DeepAgentState, agent_name: str) -> Any:
        """Get validation result from state"""
        # This would need to be implemented based on how validation results are stored
        return state.quality_metrics.get(agent_name)
    
    async def _handle_failed_validation(self,
                                      context: AgentExecutionContext,
                                      agent_name: str,
                                      state: DeepAgentState,
                                      validation_result: Any) -> None:
        """Handle failed quality validation"""
        if validation_result.retry_suggested:
            await self.fallback_manager.retry_with_quality_adjustments(
                context, agent_name, state, validation_result, self.agents
            )
        else:
            await self.fallback_manager.apply_fallback_response(
                context, agent_name, state, validation_result
            )
    
    async def _quality_monitoring_hook(self,
                                     context: AgentExecutionContext,
                                     agent_name: str,
                                     state: DeepAgentState) -> None:
        """Hook for quality monitoring"""
        await self.hooks_manager.quality_monitoring_hook(context, agent_name, state)
    
    async def _fallback_generation_hook(self,
                                      context: AgentExecutionContext,
                                      error: Exception,
                                      agent_name: str) -> None:
        """Hook for fallback generation on error"""
        await self.fallback_manager.fallback_generation_hook(context, error, agent_name)
    
    async def _quality_retry_hook(self,
                                context: AgentExecutionContext,
                                agent_name: str,
                                retry_count: int) -> bool:
        """Hook for quality-based retry decisions"""
        return await self.hooks_manager.quality_retry_hook(context, agent_name, retry_count)
    
    async def get_quality_dashboard(self) -> Dict[str, Any]:
        """Get quality dashboard data"""
        dashboard_data = {
            'quality_stats': self._get_combined_stats(),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        if self.monitoring_service:
            monitoring_data = await self.monitoring_service.get_dashboard_data()
            dashboard_data.update(monitoring_data)
        
        return dashboard_data
    
    def _get_combined_stats(self) -> Dict[str, Any]:
        """Get combined statistics from all managers"""
        stats = {}
        stats.update(self.hooks_manager.get_quality_stats())
        stats.update(self.fallback_manager.get_fallback_stats())
        return stats
    
    async def get_agent_quality_report(self, agent_name: str, period_hours: int = 24) -> Dict[str, Any]:
        """Get quality report for a specific agent"""
        if self.monitoring_service:
            return await self.monitoring_service.get_agent_report(agent_name, period_hours)
        return {'error': 'Quality monitoring not enabled'}
    
    def get_quality_stats_summary(self) -> Dict[str, Any]:
        """Get summary of quality statistics"""
        return {
            'hooks_stats': self.hooks_manager.get_quality_stats(),
            'fallback_stats': self.fallback_manager.get_fallback_stats(),
            'quality_gates_enabled': self.enable_quality_gates,
            'strict_mode': self.strict_mode
        }
    
    async def shutdown(self) -> None:
        """Shutdown the supervisor and quality services"""
        if self.monitoring_service:
            await self.monitoring_service.stop_monitoring()
        
        final_stats = self._get_combined_stats()
        logger.info(f"Quality stats at shutdown: {final_stats}")
        
        await super().shutdown()
    
    def enable_strict_mode(self) -> None:
        """Enable strict quality mode"""
        self.strict_mode = True
        if self.hooks_manager:
            self.hooks_manager.strict_mode = True
    
    def disable_strict_mode(self) -> None:
        """Disable strict quality mode"""
        self.strict_mode = False
        if self.hooks_manager:
            self.hooks_manager.strict_mode = False
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current quality configuration"""
        return {
            'quality_gates_enabled': self.enable_quality_gates,
            'strict_mode': self.strict_mode,
            'services_available': {
                'quality_gate_service': self.quality_gate_service is not None,
                'fallback_service': self.fallback_service is not None,
                'monitoring_service': self.monitoring_service is not None
            }
        }