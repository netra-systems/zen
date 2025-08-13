# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-12T17:30:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Create unified supervisor entry point to fix broken imports
# Git: terra2 | bd8079c0 | modified
# Change: Feature | Scope: Component | Risk: Medium
# Session: supervisor-consolidation | Seq: 1
# Review: Pending | Score: 90
# ================================
"""
Unified Supervisor Agent Entry Point

This module provides the main entry point for the supervisor agent system,
consolidating multiple supervisor implementations with feature flags and
circuit breaker patterns for robust agent orchestration.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.ws_manager import WebSocketManager
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import time
from contextlib import asynccontextmanager

from app.logging_config import central_logger
# Avoid circular import - import moved to function body where needed
from app.agents.quality_supervisor import QualityEnhancedSupervisor
from app.agents.state import DeepAgentState
from app.schemas import SubAgentLifecycle
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher

logger = central_logger.get_logger(__name__)


class SupervisorMode(Enum):
    """Supervisor operation modes"""
    BASIC = "basic"
    QUALITY_ENHANCED = "quality_enhanced"
    ADMIN_ENABLED = "admin_enabled"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class SupervisorConfig:
    """Configuration for unified supervisor"""
    mode: SupervisorMode = SupervisorMode.BASIC
    enable_quality_gates: bool = False
    enable_admin_tools: bool = False
    enable_circuit_breaker: bool = True
    circuit_breaker_config: CircuitBreakerConfig = None
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    timeout: float = 300.0

    def __post_init__(self):
        if self.circuit_breaker_config is None:
            self.circuit_breaker_config = CircuitBreakerConfig()


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for agent failure handling"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        return False
    
    def record_success(self):
        """Record successful execution"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout


class SupervisorAgent:
    """Unified Supervisor Agent with configurable features and circuit breaker"""
    
    def __init__(self,
                 db_session: AsyncSession,
                 llm_manager: LLMManager = None,
                 websocket_manager: Optional['WebSocketManager'] = None,
                 tool_dispatcher: ToolDispatcher = None,
                 config: SupervisorConfig = None,
                 user_id: str = None,
                 thread_id: str = None):
        """
        Initialize unified supervisor agent
        
        Args:
            db_session: Database session
            llm_manager: LLM manager instance
            websocket_manager: WebSocket manager for real-time updates
            tool_dispatcher: Tool dispatcher for agent tools
            config: Supervisor configuration
            user_id: User ID for context
            thread_id: Thread ID for context
        """
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.config = config or SupervisorConfig()
        self.user_id = user_id
        self.thread_id = thread_id
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(self.config.circuit_breaker_config) if self.config.enable_circuit_breaker else None
        
        # Initialize the appropriate supervisor implementation
        self._supervisor_impl = self._create_supervisor_implementation()
        
        logger.info(f"Initialized unified supervisor with mode: {self.config.mode.value}")
    
    def _create_supervisor_implementation(self):
        """Create the appropriate supervisor implementation based on config"""
        from app.agents.supervisor_consolidated import SupervisorAgent as BaseSupervisorAgent
        
        if self.config.mode == SupervisorMode.QUALITY_ENHANCED or self.config.enable_quality_gates:
            return QualityEnhancedSupervisor(
                db_session=self.db_session,
                llm_manager=self.llm_manager,
                websocket_manager=self.websocket_manager,
                tool_dispatcher=self.tool_dispatcher,
                enable_quality_gates=self.config.enable_quality_gates,
                user_id=self.user_id,
                thread_id=self.thread_id
            )
        else:
            return BaseSupervisorAgent(
                db_session=self.db_session,
                llm_manager=self.llm_manager,
                websocket_manager=self.websocket_manager,
                tool_dispatcher=self.tool_dispatcher
            )
    
    @asynccontextmanager
    async def _circuit_breaker_context(self):
        """Context manager for circuit breaker execution"""
        if not self.circuit_breaker:
            yield
            return
        
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is open - supervisor unavailable")
        
        try:
            yield
            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Circuit breaker recorded failure: {e}")
            raise
    
    async def run(self,
                  user_request: str,
                  run_id: str,
                  stream_updates: bool = True) -> DeepAgentState:
        """
        Run the supervisor workflow with circuit breaker and retry logic
        
        Args:
            user_request: User's request/query
            run_id: Unique identifier for this run
            stream_updates: Whether to stream real-time updates
            
        Returns:
            DeepAgentState: Final state after execution
        """
        async with self._circuit_breaker_context():
            return await self._run_with_retries(user_request, run_id, stream_updates)
    
    async def _run_with_retries(self,
                                user_request: str,
                                run_id: str,
                                stream_updates: bool) -> DeepAgentState:
        """Run with exponential backoff retry logic"""
        last_exception = None
        delay = self.config.retry_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Set timeout for the execution
                return await asyncio.wait_for(
                    self._supervisor_impl.run(user_request, run_id, stream_updates),
                    timeout=self.config.timeout
                )
            except asyncio.TimeoutError:
                last_exception = RuntimeError(f"Supervisor execution timed out after {self.config.timeout}s")
                logger.error(f"Attempt {attempt + 1} timed out: {last_exception}")
            except Exception as e:
                last_exception = e
                logger.error(f"Attempt {attempt + 1} failed: {e}")
            
            # Don't retry on the last attempt
            if attempt < self.config.max_retries:
                logger.info(f"Retrying in {delay}s... (attempt {attempt + 2}/{self.config.max_retries + 1})")
                await asyncio.sleep(delay)
                
                if self.config.exponential_backoff:
                    delay *= 2
        
        # All retries failed
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Supervisor execution failed after all retries")
    
    def get_registered_agents(self) -> Dict[str, Any]:
        """Get registered agents from the implementation"""
        if hasattr(self._supervisor_impl, 'agents'):
            return self._supervisor_impl.agents
        return {}
    
    def register_agent(self, name: str, agent: 'BaseAgent') -> None:
        """Register an agent with the supervisor"""
        if hasattr(self._supervisor_impl, 'register_agent'):
            self._supervisor_impl.register_agent(name, agent)
    
    def set_state(self, state: SubAgentLifecycle) -> None:
        """Set supervisor state"""
        if hasattr(self._supervisor_impl, 'set_state'):
            self._supervisor_impl.set_state(state)
    
    @property
    def sub_agents(self) -> List[Any]:
        """Get sub-agents for backward compatibility"""
        if hasattr(self._supervisor_impl, 'sub_agents'):
            return self._supervisor_impl.sub_agents
        return []
    
    @property
    def circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        if not self.circuit_breaker:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": self.circuit_breaker.last_failure_time
        }


def create_supervisor(db_session: AsyncSession,
                      llm_manager: LLMManager = None,
                      websocket_manager: Optional['WebSocketManager'] = None,
                      tool_dispatcher: ToolDispatcher = None,
                      mode: SupervisorMode = SupervisorMode.BASIC,
                      enable_quality_gates: bool = False,
                      enable_admin_tools: bool = False,
                      user_id: str = None,
                      thread_id: str = None) -> SupervisorAgent:
    """
    Factory function to create a configured supervisor agent
    
    Args:
        db_session: Database session
        llm_manager: LLM manager instance
        websocket_manager: WebSocket manager
        tool_dispatcher: Tool dispatcher
        mode: Supervisor operation mode
        enable_quality_gates: Enable quality checking
        enable_admin_tools: Enable admin tools
        user_id: User ID for context
        thread_id: Thread ID for context
        
    Returns:
        Configured SupervisorAgent instance
    """
    config = SupervisorConfig(
        mode=mode,
        enable_quality_gates=enable_quality_gates,
        enable_admin_tools=enable_admin_tools
    )
    
    return SupervisorAgent(
        db_session=db_session,
        llm_manager=llm_manager,
        websocket_manager=websocket_manager,
        tool_dispatcher=tool_dispatcher,
        config=config,
        user_id=user_id,
        thread_id=thread_id
    )


# Export the main class for backward compatibility
__all__ = ["SupervisorAgent", "SupervisorMode", "SupervisorConfig", "create_supervisor"]