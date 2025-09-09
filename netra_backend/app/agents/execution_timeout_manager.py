"""Agent Execution Timeout Manager for preventing pipeline blocking.

This module implements comprehensive timeout management and circuit breaker patterns
to prevent agent execution from hanging indefinitely and blocking user responses.

Business Value Justification:
- Segment: ALL segments (Free, Early, Mid, Enterprise)  
- Business Goal: Stability & User Experience
- Value Impact: Ensures users receive timely responses or clear error messages instead of indefinite waiting
- Strategic Impact: Enables 20K+ MRR chat functionality by preventing execution pipeline blocking

Key Features:
- Configurable timeouts for individual agent execution cycles
- Circuit breaker patterns for LLM API calls 
- Retry logic with exponential backoff
- Fallback response mechanisms when LLMs are unresponsive
- WebSocket event emission on failure/timeout
- Per-agent timeout configuration
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states for LLM integration resilience."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, block requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class TimeoutConfig:
    """Configuration for agent execution timeouts."""
    # Individual agent execution timeout
    agent_execution_timeout: float = 25.0  # Reduced from 30s for faster feedback
    
    # LLM API call timeout  
    llm_api_timeout: float = 15.0  # Individual LLM calls
    
    # Circuit breaker configuration
    failure_threshold: int = 3  # Open circuit after 3 failures
    recovery_timeout: float = 30.0  # Wait 30s before testing recovery
    success_threshold: int = 2  # Require 2 successes to close circuit
    
    # Retry configuration
    max_retries: int = 2
    retry_base_delay: float = 1.0  # Start with 1s delay
    retry_max_delay: float = 5.0   # Max 5s delay
    retry_exponential_base: float = 2.0  # Exponential backoff multiplier


class LLMCircuitBreaker:
    """Circuit breaker for LLM API calls to prevent cascade failures."""
    
    def __init__(self, config: TimeoutConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.next_attempt_time = 0.0
        
        logger.info(f"LLM Circuit Breaker initialized with {config.failure_threshold} failure threshold")
    
    async def call(self, func: Callable[[], T], operation_name: str = "llm_operation") -> T:
        """Execute a function with circuit breaker protection.
        
        Args:
            func: The async function to execute
            operation_name: Name of the operation for logging
            
        Returns:
            Result of the function execution
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            TimeoutError: When operation times out
            Exception: Original exception from the function
        """
        current_time = time.time()
        
        # Check circuit breaker state
        if self.state == CircuitBreakerState.OPEN:
            if current_time < self.next_attempt_time:
                logger.warning(f"🚫 Circuit breaker OPEN for {operation_name} - blocking request")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open for {operation_name}. "
                    f"Next attempt allowed in {self.next_attempt_time - current_time:.1f}s"
                )
            else:
                # Transition to half-open
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"🔄 Circuit breaker transition to HALF_OPEN for {operation_name}")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(func(), timeout=self.config.llm_api_timeout)
            
            # Success - update circuit breaker state
            await self._on_success(operation_name)
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ LLM operation {operation_name} timed out after {self.config.llm_api_timeout}s")
            await self._on_failure(operation_name, "timeout")
            raise TimeoutError(f"LLM operation {operation_name} timed out")
            
        except Exception as e:
            logger.error(f"❌ LLM operation {operation_name} failed: {e}")
            await self._on_failure(operation_name, str(e))
            raise
    
    async def _on_success(self, operation_name: str) -> None:
        """Handle successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            logger.debug(f"✅ Success {self.success_count}/{self.config.success_threshold} for {operation_name}")
            
            if self.success_count >= self.config.success_threshold:
                # Close the circuit
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"🔒 Circuit breaker CLOSED for {operation_name} - normal operation resumed")
        else:
            # Reset failure count on success in closed state
            self.failure_count = 0
    
    async def _on_failure(self, operation_name: str, error: str) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            # Open the circuit
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = self.last_failure_time + self.config.recovery_timeout
            logger.critical(
                f"🚨 Circuit breaker OPENED for {operation_name} after {self.failure_count} failures. "
                f"Next attempt in {self.config.recovery_timeout}s"
            )
        else:
            logger.warning(
                f"⚠️ Failure {self.failure_count}/{self.config.failure_threshold} for {operation_name}: {error}"
            )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    pass


class AgentExecutionTimeoutManager:
    """Comprehensive timeout manager for agent execution pipeline."""
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self.circuit_breaker = LLMCircuitBreaker(self.config)
        self.active_executions: Dict[str, float] = {}  # Track execution start times
        
        logger.info(
            f"Agent Execution Timeout Manager initialized - "
            f"agent_timeout: {self.config.agent_execution_timeout}s, "
            f"llm_timeout: {self.config.llm_api_timeout}s"
        )
    
    async def execute_agent_with_timeout(
        self, 
        agent_func: Callable[[], T], 
        agent_name: str,
        run_id: str,
        websocket_manager: Optional[Any] = None
    ) -> T:
        """Execute agent with comprehensive timeout and error handling.
        
        Args:
            agent_func: The agent execution function
            agent_name: Name of the agent for logging and events
            run_id: Run ID for WebSocket events
            websocket_manager: Optional WebSocket manager for event emission
            
        Returns:
            Result of agent execution
            
        Raises:
            TimeoutError: When agent execution times out
            Exception: Original exception from agent execution
        """
        execution_id = f"{agent_name}_{run_id}_{int(time.time() * 1000)}"
        start_time = time.time()
        self.active_executions[execution_id] = start_time
        
        try:
            logger.info(f"🚀 Starting agent execution: {agent_name} (timeout: {self.config.agent_execution_timeout}s)")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                agent_func(), 
                timeout=self.config.agent_execution_timeout
            )
            
            duration = time.time() - start_time
            logger.info(f"✅ Agent {agent_name} completed successfully in {duration:.2f}s")
            
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(
                f"⏰ Agent {agent_name} execution timed out after {duration:.2f}s "
                f"(limit: {self.config.agent_execution_timeout}s)"
            )
            
            # Emit timeout event via WebSocket if available
            if websocket_manager:
                try:
                    await websocket_manager.notify_agent_error(
                        run_id=run_id,
                        agent_name=agent_name,
                        error=f"Agent execution timed out after {self.config.agent_execution_timeout}s",
                        error_context={
                            "error_type": "timeout",
                            "timeout_duration": self.config.agent_execution_timeout,
                            "actual_duration": duration
                        }
                    )
                    logger.info(f"📡 Emitted timeout error event for {agent_name}")
                except Exception as e:
                    logger.error(f"Failed to emit timeout error event: {e}")
            
            raise TimeoutError(
                f"Agent {agent_name} execution timed out after {self.config.agent_execution_timeout}s"
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Agent {agent_name} execution failed after {duration:.2f}s: {e}")
            
            # Emit error event via WebSocket if available
            if websocket_manager:
                try:
                    await websocket_manager.notify_agent_error(
                        run_id=run_id,
                        agent_name=agent_name,
                        error=str(e),
                        error_context={
                            "error_type": type(e).__name__,
                            "execution_duration": duration
                        }
                    )
                    logger.info(f"📡 Emitted execution error event for {agent_name}")
                except Exception as emit_error:
                    logger.error(f"Failed to emit execution error event: {emit_error}")
            
            raise
            
        finally:
            # Clean up tracking
            self.active_executions.pop(execution_id, None)
    
    async def execute_llm_with_circuit_breaker(
        self, 
        llm_func: Callable[[], T], 
        operation_name: str = "llm_request"
    ) -> T:
        """Execute LLM function with circuit breaker protection.
        
        Args:
            llm_func: The LLM function to execute
            operation_name: Name of the operation for logging
            
        Returns:
            Result of LLM execution
        """
        return await self.circuit_breaker.call(llm_func, operation_name)
    
    async def execute_with_retry(
        self, 
        func: Callable[[], T], 
        operation_name: str = "operation"
    ) -> T:
        """Execute function with exponential backoff retry logic.
        
        Args:
            func: The function to execute
            operation_name: Name of the operation for logging
            
        Returns:
            Result of function execution
        """
        last_exception = None
        delay = self.config.retry_base_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt}/{self.config.max_retries} for {operation_name}")
                
                return await func()
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    logger.warning(
                        f"⚠️ Attempt {attempt + 1} failed for {operation_name}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    
                    # Exponential backoff with max limit
                    delay = min(
                        delay * self.config.retry_exponential_base,
                        self.config.retry_max_delay
                    )
                else:
                    logger.error(f"❌ All {self.config.max_retries + 1} attempts failed for {operation_name}")
        
        # All retries failed
        raise last_exception
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get current execution statistics."""
        current_time = time.time()
        active_count = len(self.active_executions)
        
        # Calculate execution durations
        execution_durations = [
            current_time - start_time 
            for start_time in self.active_executions.values()
        ]
        
        stats = {
            "active_executions": active_count,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "config": {
                "agent_timeout": self.config.agent_execution_timeout,
                "llm_timeout": self.config.llm_api_timeout,
                "max_retries": self.config.max_retries
            }
        }
        
        if execution_durations:
            stats["execution_durations"] = {
                "min": min(execution_durations),
                "max": max(execution_durations),
                "avg": sum(execution_durations) / len(execution_durations)
            }
        
        return stats
    
    async def create_fallback_response(
        self, 
        agent_name: str, 
        error: Exception,
        run_id: str,
        websocket_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create fallback response when agent execution fails.
        
        Args:
            agent_name: Name of the failed agent
            error: The exception that caused failure
            run_id: Run ID for tracking
            websocket_manager: Optional WebSocket manager for events
            
        Returns:
            Fallback response dictionary
        """
        fallback_response = {
            "success": False,
            "agent_name": agent_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "fallback": True,
            "message": (
                f"I apologize, but I encountered an issue while processing your request with the {agent_name} agent. "
                f"Please try again in a moment. If the issue persists, please contact support."
            ),
            "run_id": run_id,
            "timestamp": time.time()
        }
        
        # Emit fallback notification via WebSocket if available
        if websocket_manager:
            try:
                await websocket_manager.notify_agent_completed(
                    run_id=run_id,
                    agent_name=agent_name,
                    result=fallback_response,
                    execution_time_ms=0
                )
                logger.info(f"📡 Emitted fallback completion event for {agent_name}")
            except Exception as e:
                logger.error(f"Failed to emit fallback completion event: {e}")
        
        return fallback_response


# Global timeout manager instance
_timeout_manager: Optional[AgentExecutionTimeoutManager] = None


def get_timeout_manager() -> AgentExecutionTimeoutManager:
    """Get or create the global timeout manager instance."""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = AgentExecutionTimeoutManager()
    return _timeout_manager


def configure_timeout_manager(config: TimeoutConfig) -> None:
    """Configure the global timeout manager with custom settings."""
    global _timeout_manager
    _timeout_manager = AgentExecutionTimeoutManager(config)
    logger.info("Global timeout manager configured with custom settings")