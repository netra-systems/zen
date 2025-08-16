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
from app.agents.supervisor_circuit_breaker import CircuitBreaker
from app.schemas.core_models import CircuitBreakerConfig

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
            return await self._try_execute_with_processing(context, state, execute_func)
        except Exception as e:
            return await self._create_final_fallback(context, state, e)
    
    async def _try_execute_with_processing(self, context: AgentExecutionContext,
                                          state: DeepAgentState, execute_func) -> AgentExecutionResult:
        """Try execution with result processing."""
        result = await self._execute_with_handler(context, state, execute_func)
        return self._process_fallback_result(result, context)
    
    async def _execute_with_handler(self, context: AgentExecutionContext,
                                   state: DeepAgentState, execute_func):
        """Execute through fallback handler."""
        circuit_breaker = self._get_agent_circuit_breaker(context.agent_name)
        try:
            return await self._execute_and_record_result(context, execute_func, circuit_breaker)
        except Exception as e:
            return self._handle_execution_error(circuit_breaker, e)
    
    def _handle_execution_error(self, circuit_breaker, error: Exception):
        """Handle execution error by recording failure and re-raising."""
        circuit_breaker.record_failure(type(error).__name__)
        raise error
    
    async def _execute_and_record_result(self, context: AgentExecutionContext,
                                       execute_func, circuit_breaker):
        """Execute with fallback and record circuit breaker result."""
        fallback_type = self._get_agent_fallback_type(context.agent_name)
        result = await self._call_fallback_handler(execute_func, context, fallback_type)
        self._record_circuit_breaker_result(result, circuit_breaker)
        return result
    
    async def _call_fallback_handler(self, execute_func, context: AgentExecutionContext,
                                   fallback_type: str):
        """Call fallback handler with execution parameters."""
        return await self.fallback_handler.execute_with_fallback(
            execute_func, f"execute_{context.agent_name}",
            context.agent_name, fallback_type)
    
    def _record_circuit_breaker_result(self, result, circuit_breaker) -> None:
        """Record success or failure on circuit breaker based on result."""
        if hasattr(result, 'success') and result.success:
            circuit_breaker.record_success()
        else:
            circuit_breaker.record_failure("execution_failure")
    
    def _process_fallback_result(self, result, context: AgentExecutionContext):
        """Process fallback execution result."""
        if isinstance(result, AgentExecutionResult):
            return result
        return self._wrap_fallback_response(result, context)
    
    def _get_agent_fallback_type(self, agent_name: str) -> str:
        """Get appropriate fallback type for agent."""
        fallback_mapping = self._create_fallback_mapping()
        return fallback_mapping.get(agent_name, "general")
    
    def _create_fallback_mapping(self) -> dict:
        """Create agent fallback type mapping."""
        return {
            "TriageSubAgent": "triage",
            "DataSubAgent": "data_analysis",
            "SupplyResearcherAgent": "data_analysis",
            "SyntheticDataGenerator": "data_analysis"
        }
    
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
        metadata = self._create_circuit_breaker_metadata(context.agent_name, fallback_data)
        return AgentExecutionResult(
            success=True, state=state, duration=0.05, metadata=metadata)
    
    def _create_circuit_breaker_metadata(self, agent_name: str, 
                                        fallback_data: dict) -> dict:
        """Create circuit breaker metadata."""
        return {
            "circuit_breaker_fallback": True, "agent_name": agent_name,
            "fallback_data": fallback_data
        }
    
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
        metadata = self._create_final_fallback_metadata(context.agent_name, fallback_data)
        return AgentExecutionResult(
            success=False, state=state, duration=0.01,
            error=str(error), metadata=metadata)
    
    def _create_final_fallback_metadata(self, agent_name: str, 
                                       fallback_data: dict) -> dict:
        """Create final fallback metadata."""
        return {
            "final_fallback": True, "agent_name": agent_name,
            "fallback_data": fallback_data
        }
    
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
        metadata = self._create_retry_exhausted_metadata(
            context.agent_name, error, fallback_data)
        duration = time.time() - start_time
        return AgentExecutionResult(success=True, state=state, duration=duration, metadata=metadata)
    
    def _create_retry_exhausted_metadata(self, agent_name: str, error: Exception,
                                        fallback_data: dict) -> dict:
        """Create retry exhausted metadata."""
        return {
            "fallback_after_retry": True, "agent_name": agent_name,
            "original_error": str(error), "fallback_data": fallback_data
        }
    
    def _init_fallback_mechanisms(self) -> None:
        """Initialize fallback mechanisms for graceful degradation."""
        fallback_config = self._create_fallback_config()
        self.fallback_handler = LLMFallbackHandler(fallback_config)
        # Circuit breakers are now managed by the global registry
    
    def _create_fallback_config(self) -> FallbackConfig:
        """Create fallback configuration."""
        return FallbackConfig(
            max_retries=2, base_delay=0.5,
            max_delay=10.0, timeout=30.0
        )
    
    async def _get_agent_circuit_breaker(self, agent_name: str):
        """Get or create circuit breaker for agent."""
        timeout = self._get_circuit_breaker_timeout()
        threshold = self._get_circuit_breaker_threshold()
        config = self._build_circuit_breaker_config(agent_name, threshold, timeout)
        return await circuit_registry.get_circuit(f"agent_{agent_name}", config)
    
    
    def _get_circuit_breaker_timeout(self) -> float:
        """Get circuit breaker timeout based on environment."""
        import os
        return 0.1 if os.getenv('PYTEST_CURRENT_TEST') else 60.0
    
    def _get_circuit_breaker_threshold(self) -> int:
        """Get circuit breaker threshold based on environment."""
        import os
        return 2 if os.getenv('PYTEST_CURRENT_TEST') else 3
    
    def _build_circuit_breaker_config(self, agent_name: str, threshold: int, 
                                     timeout: float) -> CircuitBreakerConfig:
        """Build circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=threshold, recovery_timeout=timeout,
            name=f"agent_{agent_name}")
    
    def get_fallback_health_status(self) -> Dict[str, any]:
        """Get health status of fallback mechanisms."""
        handler_status = self.fallback_handler.get_health_status()
        breaker_status = self._get_circuit_breaker_status()
        return {"fallback_handler": handler_status, "circuit_breakers": breaker_status}
    
    def _get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status for all agents."""
        return {
            agent: cb.get_status()
            for agent, cb in self.agent_circuit_breakers.items()
        }
    
    def reset_fallback_mechanisms(self) -> None:
        """Reset all fallback mechanisms."""
        self.fallback_handler.reset_circuit_breakers()
        for cb in self.agent_circuit_breakers.values():
            cb.reset()
        logger.info("All fallback mechanisms reset")