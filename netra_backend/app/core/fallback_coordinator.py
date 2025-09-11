"""
Centralized fallback coordinator for managing system-wide fallback strategies.

This module provides a centralized coordinator that manages fallback strategies
across all agents and services, preventing cascade failures and ensuring
graceful degradation of the entire system.
"""

from datetime import datetime
from typing import Any, Callable, Dict, Optional

# Emergency fallback manager implementation would go here
# from netra_backend.app.core.fallback_coordinator_emergency import EmergencyFallbackManager
from netra_backend.app.core.fallback_coordinator_health import HealthMonitor
from netra_backend.app.core.fallback_coordinator_models import AgentFallbackStatus
from netra_backend.app.core.reliability import CircuitBreaker, CircuitBreakerConfig
from netra_backend.app.llm.fallback_handler import FallbackConfig, LLMFallbackHandler
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FallbackCoordinator:
    """Coordinates fallback strategies across the entire system"""
    
    def __init__(self):
        self.agent_handlers: Dict[str, LLMFallbackHandler] = {}
        self.agent_circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.agent_statuses: Dict[str, AgentFallbackStatus] = {}
        
        # System-wide settings
        self.max_concurrent_fallbacks = 3  # Max agents in fallback mode simultaneously
        self.cascade_prevention_threshold = 0.5  # 50% of agents failing triggers prevention
        self.emergency_mode_threshold = 0.7  # 70% of agents failing triggers emergency
        
        # Initialize sub-managers
        self.health_monitor = HealthMonitor(self)
        # Emergency manager would be initialized here
        # self.emergency_manager = EmergencyFallbackManager()
        self.emergency_manager = None
    
    def register_agent(self, agent_name: str, 
                      fallback_config: Optional[FallbackConfig] = None) -> LLMFallbackHandler:
        """Register an agent with the fallback coordinator"""
        existing_handler = self._check_existing_agent(agent_name)
        if existing_handler:
            return existing_handler
        handler = self._create_agent_handler(agent_name, fallback_config)
        self._setup_agent_circuit_breaker(agent_name)
        self._initialize_agent_status(agent_name)
        logger.info(f"Registered agent {agent_name} with fallback coordinator")
        return handler

    def _check_existing_agent(self, agent_name: str) -> Optional[LLMFallbackHandler]:
        """Check if agent is already registered and return existing handler."""
        if agent_name in self.agent_handlers:
            logger.warning(f"Agent {agent_name} already registered, returning existing handler")
            return self.agent_handlers[agent_name]
        return None

    def _create_agent_handler(self, agent_name: str, 
                             fallback_config: Optional[FallbackConfig]) -> LLMFallbackHandler:
        """Create and store fallback handler for agent."""
        config = fallback_config or self._get_default_fallback_config()
        handler = LLMFallbackHandler(config)
        self.agent_handlers[agent_name] = handler
        return handler

    def _setup_agent_circuit_breaker(self, agent_name: str) -> None:
        """Setup circuit breaker for agent."""
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
            name=f"coordinator_{agent_name}"
        )
        circuit_breaker = CircuitBreaker(cb_config)
        self.agent_circuit_breakers[agent_name] = circuit_breaker

    def _initialize_agent_status(self, agent_name: str) -> None:
        """Initialize status tracking for agent."""
        self.agent_statuses[agent_name] = AgentFallbackStatus(
            agent_name=agent_name,
            circuit_breaker_open=False,
            recent_failures=0,
            fallback_active=False,
            last_failure_time=None,
            health_score=1.0
        )
    
    def _get_default_fallback_config(self) -> FallbackConfig:
        """Get default fallback configuration"""
        return FallbackConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=15.0,
            timeout=30.0,
            use_circuit_breaker=True
        )
    
    async def _check_emergency_mode(self, agent_name: str, operation_name: str, fallback_type: str) -> Any:
        """Check if system is in emergency mode and handle accordingly."""
        if await self.health_monitor.is_emergency_mode_active():
            logger.warning(f"System in emergency mode, using emergency fallback for {agent_name}")
            return await self.emergency_manager.execute_emergency_fallback(
                agent_name, operation_name, fallback_type
            )
        return None

    async def _check_cascade_prevention(self, agent_name: str, operation_name: str) -> Any:
        """Check if cascade prevention should be applied."""
        if await self.health_monitor.should_prevent_cascade(agent_name):
            logger.warning(f"Cascade prevention active, limiting fallback for {agent_name}")
            return await self.emergency_manager.execute_limited_fallback(agent_name, operation_name)
        return None

    def _validate_agent_handler(self, agent_name: str):
        """Validate that agent has a registered handler."""
        handler = self.agent_handlers.get(agent_name)
        if not handler:
            logger.error(f"No fallback handler registered for agent {agent_name}")
            raise ValueError(f"Agent {agent_name} not registered with fallback coordinator")
        return handler

    async def _execute_operation_with_handler(self, handler, operation, operation_name, agent_name, fallback_type):
        """Execute operation using the fallback handler."""
        return await handler.execute_with_fallback(
            operation, operation_name, agent_name, fallback_type
        )

    async def _handle_operation_success(self, agent_name: str, result: Any) -> Any:
        """Handle successful operation execution."""
        await self.health_monitor.record_success(agent_name)
        return result

    async def _handle_operation_failure(self, agent_name: str, exception: Exception) -> None:
        """Handle operation failure and update monitoring."""
        await self.health_monitor.record_failure(agent_name, exception)
        await self.health_monitor.update_circuit_breaker_status(agent_name)
        await self.health_monitor.update_system_health()

    async def _execute_with_error_handling(self, handler, operation, operation_name, agent_name, fallback_type) -> Any:
        """Execute operation with error handling and monitoring updates."""
        try:
            result = await self._execute_operation_with_handler(handler, operation, operation_name, agent_name, fallback_type)
            return await self._handle_operation_success(agent_name, result)
        except Exception as e:
            await self._handle_operation_failure(agent_name, e)
            raise e

    async def execute_with_coordination(
        self, agent_name: str, operation: Callable, operation_name: str, fallback_type: str = "general"
    ) -> Any:
        """Execute operation with coordinated fallback handling"""
        emergency_result = await self._check_emergency_mode(agent_name, operation_name, fallback_type)
        if emergency_result is not None:
            return emergency_result
        cascade_result = await self._check_cascade_prevention(agent_name, operation_name)
        if cascade_result is not None:
            return cascade_result
        handler = self._validate_agent_handler(agent_name)
        return await self._execute_with_error_handling(handler, operation, operation_name, agent_name, fallback_type)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system fallback status"""
        return self.health_monitor.get_system_status()
    
    async def reset_agent_status(self, agent_name: str) -> bool:
        """Reset status for a specific agent"""
        if agent_name not in self.agent_statuses:
            return False
        self._reset_agent_components(agent_name)
        self._reset_agent_status_data(agent_name)
        logger.info(f"Reset fallback status for agent {agent_name}")
        return True
    
    def _reset_agent_components(self, agent_name: str) -> None:
        """Reset circuit breaker and handler for agent."""
        self._reset_agent_circuit_breaker(agent_name)
        self._reset_agent_handler(agent_name)
    
    def _reset_agent_circuit_breaker(self, agent_name: str) -> None:
        """Reset circuit breaker for agent."""
        cb = self.agent_circuit_breakers.get(agent_name)
        if cb:
            cb.reset()
    
    def _reset_agent_handler(self, agent_name: str) -> None:
        """Reset handler for agent."""
        handler = self.agent_handlers.get(agent_name)
        if handler:
            handler.reset_circuit_breakers()
    
    def _reset_agent_status_data(self, agent_name: str) -> None:
        """Reset status data for agent."""
        self.agent_statuses[agent_name] = self._create_fresh_agent_status(agent_name)
    
    def _create_fresh_agent_status(self, agent_name: str) -> AgentFallbackStatus:
        """Create fresh agent status instance."""
        return AgentFallbackStatus(
            agent_name=agent_name,
            circuit_breaker_open=False,
            recent_failures=0,
            fallback_active=False,
            last_failure_time=None,
            health_score=1.0
        )
    
    async def reset_system_status(self) -> None:
        """Reset entire system fallback status"""
        for agent_name in list(self.agent_statuses.keys()):
            await self.reset_agent_status(agent_name)
        
        self.health_monitor.system_health_history.clear()
        logger.info("Reset system-wide fallback status")
    
    def get_agent_handler(self, agent_name: str) -> Optional[LLMFallbackHandler]:
        """Get fallback handler for an agent"""
        return self.agent_handlers.get(agent_name)
    
    def get_registered_agents(self) -> list[str]:
        """Get list of registered agent names"""
        return list(self.agent_handlers.keys())
    
    def is_agent_registered(self, agent_name: str) -> bool:
        """Check if agent is registered"""
        return agent_name in self.agent_handlers


# Global coordinator instance
fallback_coordinator = FallbackCoordinator()