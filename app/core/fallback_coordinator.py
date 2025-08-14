"""
Centralized fallback coordinator for managing system-wide fallback strategies.

This module provides a centralized coordinator that manages fallback strategies
across all agents and services, preventing cascade failures and ensuring
graceful degradation of the entire system.
"""

from typing import Dict, Optional, Any, Callable
from datetime import datetime

from app.logging_config import central_logger
from app.llm.fallback_handler import LLMFallbackHandler, FallbackConfig
from app.core.reliability import CircuitBreaker, CircuitBreakerConfig
from .fallback_coordinator_models import AgentFallbackStatus
from .fallback_coordinator_health import HealthMonitor
from .fallback_coordinator_emergency import EmergencyFallbackManager

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
        self.emergency_manager = EmergencyFallbackManager()
    
    def register_agent(self, agent_name: str, 
                      fallback_config: Optional[FallbackConfig] = None) -> LLMFallbackHandler:
        """Register an agent with the fallback coordinator"""
        if agent_name in self.agent_handlers:
            logger.warning(f"Agent {agent_name} already registered, returning existing handler")
            return self.agent_handlers[agent_name]
        
        # Create fallback handler
        config = fallback_config or self._get_default_fallback_config()
        handler = LLMFallbackHandler(config)
        self.agent_handlers[agent_name] = handler
        
        # Create circuit breaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
            name=f"coordinator_{agent_name}"
        )
        circuit_breaker = CircuitBreaker(cb_config)
        self.agent_circuit_breakers[agent_name] = circuit_breaker
        
        # Initialize status
        self.agent_statuses[agent_name] = AgentFallbackStatus(
            agent_name=agent_name,
            circuit_breaker_open=False,
            recent_failures=0,
            fallback_active=False,
            last_failure_time=None,
            health_score=1.0
        )
        
        logger.info(f"Registered agent {agent_name} with fallback coordinator")
        return handler
    
    def _get_default_fallback_config(self) -> FallbackConfig:
        """Get default fallback configuration"""
        return FallbackConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=15.0,
            timeout=30.0,
            use_circuit_breaker=True
        )
    
    async def execute_with_coordination(
        self,
        agent_name: str,
        operation: Callable,
        operation_name: str,
        fallback_type: str = "general"
    ) -> Any:
        """Execute operation with coordinated fallback handling"""
        
        # Check if system is in emergency mode
        if await self.health_monitor.is_emergency_mode_active():
            logger.warning(f"System in emergency mode, using emergency fallback for {agent_name}")
            return await self.emergency_manager.execute_emergency_fallback(
                agent_name, operation_name, fallback_type
            )
        
        # Check if too many agents are in fallback mode
        if await self.health_monitor.should_prevent_cascade(agent_name):
            logger.warning(f"Cascade prevention active, limiting fallback for {agent_name}")
            return await self.emergency_manager.execute_limited_fallback(agent_name, operation_name)
        
        # Get agent's fallback handler
        handler = self.agent_handlers.get(agent_name)
        if not handler:
            logger.error(f"No fallback handler registered for agent {agent_name}")
            raise ValueError(f"Agent {agent_name} not registered with fallback coordinator")
        
        # Execute with coordination
        try:
            result = await handler.execute_with_fallback(
                operation,
                operation_name,
                agent_name,
                fallback_type
            )
            
            # Record successful operation
            await self.health_monitor.record_success(agent_name)
            return result
            
        except Exception as e:
            # Record failure and update status
            await self.health_monitor.record_failure(agent_name, e)
            
            # Check if circuit breaker should open
            await self.health_monitor.update_circuit_breaker_status(agent_name)
            
            # Update system health
            await self.health_monitor.update_system_health()
            
            raise e
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system fallback status"""
        return self.health_monitor.get_system_status()
    
    async def reset_agent_status(self, agent_name: str) -> bool:
        """Reset status for a specific agent"""
        if agent_name not in self.agent_statuses:
            return False
        
        # Reset circuit breaker
        cb = self.agent_circuit_breakers.get(agent_name)
        if cb:
            cb.reset()
        
        # Reset handler
        handler = self.agent_handlers.get(agent_name)
        if handler:
            handler.reset_circuit_breakers()
        
        # Reset status
        self.agent_statuses[agent_name] = AgentFallbackStatus(
            agent_name=agent_name,
            circuit_breaker_open=False,
            recent_failures=0,
            fallback_active=False,
            last_failure_time=None,
            health_score=1.0
        )
        
        logger.info(f"Reset fallback status for agent {agent_name}")
        return True
    
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