"""
Health monitoring and status management for fallback coordination.
"""

from typing import Dict, Any, List
from datetime import datetime

from app.logging_config import central_logger
from .fallback_coordinator_models import (
    SystemHealthLevel, AgentFallbackStatus, SystemFallbackStatus
)

logger = central_logger.get_logger(__name__)


class HealthMonitor:
    """Monitors system health and manages health status"""
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.system_health_history: List[SystemFallbackStatus] = []
        self.max_health_history = 100
    
    async def record_success(self, agent_name: str) -> None:
        """Record successful operation for agent"""
        if agent_name in self.coordinator.agent_statuses:
            status = self.coordinator.agent_statuses[agent_name]
            status.health_score = min(1.0, status.health_score + 0.1)
            status.fallback_active = False
            
            # Record success in circuit breaker
            cb = self.coordinator.agent_circuit_breakers.get(agent_name)
            if cb:
                cb.record_success()
                status.circuit_breaker_open = cb.is_open()
    
    async def record_failure(self, agent_name: str, error: Exception) -> None:
        """Record failed operation for agent"""
        if agent_name in self.coordinator.agent_statuses:
            status = self.coordinator.agent_statuses[agent_name]
            status.recent_failures += 1
            status.last_failure_time = datetime.utcnow()
            status.health_score = max(0.0, status.health_score - 0.2)
            status.fallback_active = True
            
            # Record failure in circuit breaker
            cb = self.coordinator.agent_circuit_breakers.get(agent_name)
            if cb:
                cb.record_failure()
                status.circuit_breaker_open = cb.is_open()
    
    async def update_circuit_breaker_status(self, agent_name: str) -> None:
        """Update circuit breaker status for agent"""
        if (agent_name in self.coordinator.agent_statuses and 
            agent_name in self.coordinator.agent_circuit_breakers):
            cb = self.coordinator.agent_circuit_breakers[agent_name]
            self.coordinator.agent_statuses[agent_name].circuit_breaker_open = cb.is_open()
    
    async def is_emergency_mode_active(self) -> bool:
        """Check if system should be in emergency mode"""
        if not self.coordinator.agent_statuses:
            return False
        
        failing_agents = sum(1 for status in self.coordinator.agent_statuses.values() 
                           if status.health_score < 0.3 or status.circuit_breaker_open)
        
        failure_rate = failing_agents / len(self.coordinator.agent_statuses)
        return failure_rate >= self.coordinator.emergency_mode_threshold
    
    async def should_prevent_cascade(self, requesting_agent: str) -> bool:
        """Check if cascade prevention should be active"""
        if not self.coordinator.agent_statuses:
            return False
        
        # Count agents currently in fallback mode
        fallback_agents = sum(1 for status in self.coordinator.agent_statuses.values() 
                            if status.fallback_active)
        
        # Allow if under threshold or if this agent is already in fallback
        current_status = self.coordinator.agent_statuses.get(requesting_agent)
        if current_status and current_status.fallback_active:
            return False
        
        return fallback_agents >= self.coordinator.max_concurrent_fallbacks
    
    async def update_system_health(self) -> None:
        """Update overall system health status"""
        if not self.coordinator.agent_statuses:
            return
        
        # Calculate system metrics
        total_agents = len(self.coordinator.agent_statuses)
        agents_in_fallback = [name for name, status in self.coordinator.agent_statuses.items() 
                            if status.fallback_active]
        fallback_rate = len(agents_in_fallback) / total_agents
        
        # Determine health level
        health_level = self._calculate_health_level(fallback_rate)
        
        # Create status record
        status = SystemFallbackStatus(
            health_level=health_level,
            agents_in_fallback=agents_in_fallback,
            total_agents=total_agents,
            cascade_prevention_active=await self.should_prevent_cascade(""),
            emergency_mode_active=await self.is_emergency_mode_active(),
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
    
    def _calculate_health_level(self, fallback_rate: float) -> SystemHealthLevel:
        """Calculate system health level based on fallback rate"""
        if fallback_rate >= self.coordinator.emergency_mode_threshold:
            return SystemHealthLevel.EMERGENCY
        elif fallback_rate >= self.coordinator.cascade_prevention_threshold:
            return SystemHealthLevel.CRITICAL
        elif fallback_rate > 0.2:  # More than 20% in fallback
            return SystemHealthLevel.DEGRADED
        else:
            return SystemHealthLevel.HEALTHY
    
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
                for name, status in self.coordinator.agent_statuses.items()
            }
        }