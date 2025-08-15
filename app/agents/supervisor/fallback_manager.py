"""Fallback and circuit breaker management."""

import time
from typing import Dict, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from app.agents.supervisor.websocket_notifier import WebSocketNotifier

from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult
)
from app.llm.fallback_handler import LLMFallbackHandler, FallbackConfig
from app.core.circuit_breaker import CircuitBreaker, CircuitConfig

logger = central_logger.get_logger(__name__)


class FallbackManager:
    """Manages fallback mechanisms and circuit breakers."""
    
    def __init__(self, websocket_notifier: 'WebSocketNotifier'):
        self.websocket_notifier = websocket_notifier
        self._init_fallback_mechanisms()
    
    async def execute_with_fallback(self, context: AgentExecutionContext,
                                   state: DeepAgentState,
                                   execute_func) -> AgentExecutionResult:
        """Execute with comprehensive fallback handling."""
        circuit_breaker = self._get_agent_circuit_breaker(context.agent_name)
        if circuit_breaker.is_open:
            return await self._handle_open_circuit_breaker(context, state)
        return await self._execute_with_fallback_handler(context, state, execute_func)
    
    async def _handle_open_circuit_breaker(self, context: AgentExecutionContext,
                                          state: DeepAgentState) -> AgentExecutionResult:
        """Handle open circuit breaker scenario."""
        logger.warning(f"Circuit breaker open for {context.agent_name}, using fallback")
        return await self._create_circuit_breaker_fallback(context, state)
    
    async def _execute_with_fallback_handler(self, context: AgentExecutionContext,
                                           state: DeepAgentState,
                                           execute_func) -> AgentExecutionResult:
        """Execute with fallback handler protection."""
        try:
            result = await self._execute_with_handler(context, state, execute_func)
            return self._process_fallback_result(result, context)
        except Exception as e:
            return await self._create_final_fallback(context, state, e)
    
    async def _execute_with_handler(self, context: AgentExecutionContext,
                                   state: DeepAgentState, execute_func):
        """Execute through fallback handler."""
        fallback_type = self._get_agent_fallback_type(context.agent_name)
        return await self.fallback_handler.execute_with_fallback(
            execute_func, f"execute_{context.agent_name}",
            context.agent_name, fallback_type
        )
    
    def _process_fallback_result(self, result, context: AgentExecutionContext):
        """Process fallback execution result."""
        if isinstance(result, AgentExecutionResult):
            return result
        return self._wrap_fallback_response(result, context)
    
    def _get_agent_fallback_type(self, agent_name: str) -> str:
        """Get appropriate fallback type for agent."""
        fallback_mapping = {
            "TriageSubAgent": "triage",
            "DataSubAgent": "data_analysis",
            "SupplyResearcherAgent": "data_analysis",
            "SyntheticDataGenerator": "data_analysis"
        }
        return fallback_mapping.get(agent_name, "general")
    
    def _wrap_fallback_response(self, fallback_data: dict,
                              context: AgentExecutionContext) -> AgentExecutionResult:
        """Wrap fallback response in AgentExecutionResult."""
        metadata = self._build_fallback_metadata(context.agent_name, fallback_data)
        return AgentExecutionResult(
            success=True, state=None, duration=0.1, metadata=metadata
        )
    
    def _build_fallback_metadata(self, agent_name: str, 
                                fallback_data: dict) -> Dict[str, any]:
        """Build fallback metadata."""
        return {
            "fallback_used": True, "agent_name": agent_name,
            "fallback_data": fallback_data
        }
    
    async def _create_circuit_breaker_fallback(self, context: AgentExecutionContext,
                                             state: DeepAgentState) -> AgentExecutionResult:
        """Create fallback when circuit breaker is open."""
        fallback_type = self._get_agent_fallback_type(context.agent_name)
        fallback_data = self.fallback_handler._create_fallback_response(fallback_type)
        await self.websocket_notifier.send_fallback_notification(context, "circuit_breaker")
        return self._build_circuit_breaker_result(context, state, fallback_data)
    
    def _build_circuit_breaker_result(self, context: AgentExecutionContext,
                                     state: DeepAgentState, 
                                     fallback_data: dict) -> AgentExecutionResult:
        """Build circuit breaker fallback result."""
        metadata = {
            "circuit_breaker_fallback": True, "agent_name": context.agent_name,
            "fallback_data": fallback_data
        }
        return AgentExecutionResult(
            success=True, state=state, duration=0.05, metadata=metadata
        )
    
    async def _create_final_fallback(self, context: AgentExecutionContext,
                                   state: DeepAgentState,
                                   error: Exception) -> AgentExecutionResult:
        """Create final fallback when all else fails."""
        logger.error(f"Final fallback for {context.agent_name}: {error}")
        fallback_data = self._build_final_fallback_data(context.agent_name, error)
        await self.websocket_notifier.send_fallback_notification(context, "final_fallback")
        return self._build_final_fallback_result(context, state, error, fallback_data)
    
    def _build_final_fallback_data(self, agent_name: str, error: Exception) -> dict:
        """Build final fallback data."""
        return {
            "message": f"Unable to complete {agent_name} operation",
            "status": "degraded", "error": str(error), "fallback_used": True
        }
    
    def _build_final_fallback_result(self, context: AgentExecutionContext,
                                    state: DeepAgentState, error: Exception,
                                    fallback_data: dict) -> AgentExecutionResult:
        """Build final fallback result."""
        metadata = {
            "final_fallback": True, "agent_name": context.agent_name,
            "fallback_data": fallback_data
        }
        return AgentExecutionResult(
            success=False, state=state, duration=0.01,
            error=str(error), metadata=metadata
        )
    
    async def create_fallback_result(self, context: AgentExecutionContext,
                                    state: DeepAgentState, error: Exception,
                                    start_time: float) -> AgentExecutionResult:
        """Create fallback result after retries exhausted."""
        fallback_type = self._get_agent_fallback_type(context.agent_name)
        fallback_data = self.fallback_handler._create_fallback_response(fallback_type, error)
        await self.websocket_notifier.send_fallback_notification(context, "retry_exhausted")
        return self._build_retry_exhausted_result(context, state, error, start_time, fallback_data)
    
    def _build_retry_exhausted_result(self, context: AgentExecutionContext,
                                     state: DeepAgentState, error: Exception,
                                     start_time: float, fallback_data: dict) -> AgentExecutionResult:
        """Build retry exhausted fallback result."""
        metadata = {
            "fallback_after_retry": True, "agent_name": context.agent_name,
            "original_error": str(error), "fallback_data": fallback_data
        }
        return AgentExecutionResult(
            success=True, state=state, duration=time.time() - start_time,
            metadata=metadata
        )
    
    def _init_fallback_mechanisms(self) -> None:
        """Initialize fallback mechanisms for graceful degradation."""
        fallback_config = self._create_fallback_config()
        self.fallback_handler = LLMFallbackHandler(fallback_config)
        self.agent_circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def _create_fallback_config(self) -> FallbackConfig:
        """Create fallback configuration."""
        return FallbackConfig(
            max_retries=2, base_delay=0.5,
            max_delay=10.0, timeout=30.0
        )
    
    def _get_agent_circuit_breaker(self, agent_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for agent."""
        if agent_name not in self.agent_circuit_breakers:
            self._create_agent_circuit_breaker(agent_name)
        return self.agent_circuit_breakers[agent_name]
    
    def _create_agent_circuit_breaker(self, agent_name: str) -> None:
        """Create circuit breaker for agent."""
        config = CircuitConfig(
            failure_threshold=3, recovery_timeout=60.0,
            name=f"agent_{agent_name}"
        )
        self.agent_circuit_breakers[agent_name] = CircuitBreaker(config)
    
    def get_fallback_health_status(self) -> Dict[str, any]:
        """Get health status of fallback mechanisms."""
        return {
            "fallback_handler": self.fallback_handler.get_health_status(),
            "circuit_breakers": {
                agent: cb.get_status()
                for agent, cb in self.agent_circuit_breakers.items()
            }
        }
    
    def reset_fallback_mechanisms(self) -> None:
        """Reset all fallback mechanisms."""
        self.fallback_handler.reset_circuit_breakers()
        for cb in self.agent_circuit_breakers.values():
            cb.reset()
        logger.info("All fallback mechanisms reset")