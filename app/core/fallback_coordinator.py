"""
Centralized fallback coordinator for managing system-wide fallback strategies.

This module provides a centralized coordinator that manages fallback strategies
across all agents and services, preventing cascade failures and ensuring
graceful degradation of the entire system.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.logging_config import central_logger
from app.llm.fallback_handler import LLMFallbackHandler, FallbackConfig
from app.core.reliability import CircuitBreaker, CircuitBreakerConfig

logger = central_logger.get_logger(__name__)


class SystemHealthLevel(Enum):
    """System-wide health levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class AgentFallbackStatus:
    """Status of fallback mechanisms for an agent"""
    agent_name: str
    circuit_breaker_open: bool
    recent_failures: int
    fallback_active: bool
    last_failure_time: Optional[datetime]
    health_score: float


@dataclass
class SystemFallbackStatus:
    """Overall system fallback status"""
    health_level: SystemHealthLevel
    agents_in_fallback: List[str]
    total_agents: int
    cascade_prevention_active: bool
    emergency_mode_active: bool
    last_health_check: datetime


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
        
        # Monitoring
        self.system_health_history: List[SystemFallbackStatus] = []
        self.max_health_history = 100
        
        # Emergency fallback responses
        self._init_emergency_responses()
    
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
        if await self._is_emergency_mode_active():
            logger.warning(f"System in emergency mode, using emergency fallback for {agent_name}")
            return await self._execute_emergency_fallback(agent_name, operation_name, fallback_type)
        
        # Check if too many agents are in fallback mode
        if await self._should_prevent_cascade(agent_name):
            logger.warning(f"Cascade prevention active, limiting fallback for {agent_name}")
            return await self._execute_limited_fallback(agent_name, operation_name)
        
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
            await self._record_success(agent_name)
            return result
            
        except Exception as e:
            # Record failure and update status
            await self._record_failure(agent_name, e)
            
            # Check if circuit breaker should open
            await self._update_circuit_breaker_status(agent_name)
            
            # Update system health
            await self._update_system_health()
            
            raise e
    
    async def _record_success(self, agent_name: str) -> None:
        """Record successful operation for agent"""
        if agent_name in self.agent_statuses:
            status = self.agent_statuses[agent_name]
            status.health_score = min(1.0, status.health_score + 0.1)
            status.fallback_active = False
            
            # Record success in circuit breaker
            cb = self.agent_circuit_breakers.get(agent_name)
            if cb:
                cb.record_success()
                status.circuit_breaker_open = cb.is_open()
    
    async def _record_failure(self, agent_name: str, error: Exception) -> None:
        """Record failed operation for agent"""
        if agent_name in self.agent_statuses:
            status = self.agent_statuses[agent_name]
            status.recent_failures += 1
            status.last_failure_time = datetime.utcnow()
            status.health_score = max(0.0, status.health_score - 0.2)
            status.fallback_active = True
            
            # Record failure in circuit breaker
            cb = self.agent_circuit_breakers.get(agent_name)
            if cb:
                cb.record_failure()
                status.circuit_breaker_open = cb.is_open()
    
    async def _update_circuit_breaker_status(self, agent_name: str) -> None:
        """Update circuit breaker status for agent"""
        if agent_name in self.agent_statuses and agent_name in self.agent_circuit_breakers:
            cb = self.agent_circuit_breakers[agent_name]
            self.agent_statuses[agent_name].circuit_breaker_open = cb.is_open()
    
    async def _is_emergency_mode_active(self) -> bool:
        """Check if system should be in emergency mode"""
        if not self.agent_statuses:
            return False
        
        failing_agents = sum(1 for status in self.agent_statuses.values() 
                           if status.health_score < 0.3 or status.circuit_breaker_open)
        
        failure_rate = failing_agents / len(self.agent_statuses)
        return failure_rate >= self.emergency_mode_threshold
    
    async def _should_prevent_cascade(self, requesting_agent: str) -> bool:
        """Check if cascade prevention should be active"""
        if not self.agent_statuses:
            return False
        
        # Count agents currently in fallback mode
        fallback_agents = sum(1 for status in self.agent_statuses.values() 
                            if status.fallback_active)
        
        # Allow if under threshold or if this agent is already in fallback
        current_status = self.agent_statuses.get(requesting_agent)
        if current_status and current_status.fallback_active:
            return False
        
        return fallback_agents >= self.max_concurrent_fallbacks
    
    async def _execute_emergency_fallback(self, agent_name: str, operation_name: str, 
                                        fallback_type: str) -> Dict[str, Any]:
        """Execute emergency fallback when system is critical"""
        return self.emergency_responses.get(fallback_type, {
            "status": "emergency_fallback",
            "message": f"System is in emergency mode. {agent_name} operation {operation_name} unavailable.",
            "agent": agent_name,
            "operation": operation_name,
            "timestamp": datetime.utcnow().isoformat(),
            "fallback_type": "emergency"
        })
    
    async def _execute_limited_fallback(self, agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Execute limited fallback to prevent cascade"""
        return {
            "status": "cascade_prevention",
            "message": f"Limited fallback for {agent_name} to prevent system cascade failure",
            "agent": agent_name,
            "operation": operation_name,
            "timestamp": datetime.utcnow().isoformat(),
            "fallback_type": "cascade_prevention"
        }
    
    def _init_emergency_responses(self) -> None:
        """Initialize emergency response templates"""
        self.emergency_responses = {
            "triage": {
                "category": "System Maintenance",
                "confidence_score": 0.1,
                "priority": "low",
                "message": "System is temporarily unavailable for maintenance",
                "fallback_type": "emergency"
            },
            "data_analysis": {
                "analysis_type": "emergency_fallback",
                "insights": ["System temporarily unavailable"],
                "recommendations": ["Please try again later"],
                "data": {"available": False},
                "fallback_type": "emergency"
            },
            "general": {
                "message": "System is temporarily experiencing issues. Please try again later.",
                "status": "emergency_fallback",
                "fallback_type": "emergency"
            }
        }
    
    async def _update_system_health(self) -> None:
        """Update overall system health status"""
        if not self.agent_statuses:
            return
        
        # Calculate system metrics
        total_agents = len(self.agent_statuses)
        agents_in_fallback = [name for name, status in self.agent_statuses.items() 
                            if status.fallback_active]
        fallback_rate = len(agents_in_fallback) / total_agents
        
        # Determine health level
        if fallback_rate >= self.emergency_mode_threshold:
            health_level = SystemHealthLevel.EMERGENCY
        elif fallback_rate >= self.cascade_prevention_threshold:
            health_level = SystemHealthLevel.CRITICAL
        elif fallback_rate > 0.2:  # More than 20% in fallback
            health_level = SystemHealthLevel.DEGRADED
        else:
            health_level = SystemHealthLevel.HEALTHY
        
        # Create status record
        status = SystemFallbackStatus(
            health_level=health_level,
            agents_in_fallback=agents_in_fallback,
            total_agents=total_agents,
            cascade_prevention_active=await self._should_prevent_cascade(""),
            emergency_mode_active=await self._is_emergency_mode_active(),
            last_health_check=datetime.utcnow()
        )
        
        # Add to history
        self.system_health_history.append(status)
        if len(self.system_health_history) > self.max_health_history:
            self.system_health_history = self.system_health_history[-self.max_health_history:]
        
        # Log health changes
        if health_level != SystemHealthLevel.HEALTHY:
            logger.warning(
                f"System health: {health_level.value} "
                f"({len(agents_in_fallback)}/{total_agents} agents in fallback)"
            )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system fallback status"""
        if not self.system_health_history:
            return {"status": "no_data", "agents": {}}
        
        latest_status = self.system_health_history[-1]
        
        return {
            "system_health": latest_status.health_level.value,
            "agents_in_fallback": latest_status.agents_in_fallback,
            "total_agents": latest_status.total_agents,
            "cascade_prevention_active": latest_status.cascade_prevention_active,
            "emergency_mode_active": latest_status.emergency_mode_active,
            "last_updated": latest_status.last_health_check.isoformat(),
            "agent_details": {
                name: {
                    "health_score": status.health_score,
                    "circuit_breaker_open": status.circuit_breaker_open,
                    "fallback_active": status.fallback_active,
                    "recent_failures": status.recent_failures
                }
                for name, status in self.agent_statuses.items()
            }
        }
    
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
        
        self.system_health_history.clear()
        logger.info("Reset system-wide fallback status")


# Global coordinator instance
fallback_coordinator = FallbackCoordinator()