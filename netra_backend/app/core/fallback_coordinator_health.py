"""
Health monitoring and status management for fallback coordination.
"""

from typing import Dict, Any, List
from datetime import datetime, UTC

from app.logging_config import central_logger
from netra_backend.app.fallback_coordinator_models import (
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
        if agent_name not in self.coordinator.agent_statuses:
            return
        status = self.coordinator.agent_statuses[agent_name]
        self._update_success_status(status)
        self._record_circuit_breaker_success(agent_name, status)
    
    def _update_success_status(self, status: AgentFallbackStatus) -> None:
        """Update agent status for successful operation."""
        status.health_score = min(1.0, status.health_score + 0.1)
        status.fallback_active = False
    
    def _record_circuit_breaker_success(self, agent_name: str, status: AgentFallbackStatus) -> None:
        """Record success in circuit breaker and update status."""
        cb = self.coordinator.agent_circuit_breakers.get(agent_name)
        if cb:
            cb.record_success()
            status.circuit_breaker_open = cb.is_open()
    
    async def record_failure(self, agent_name: str, error: Exception) -> None:
        """Record failed operation for agent"""
        if agent_name not in self.coordinator.agent_statuses:
            return
        status = self.coordinator.agent_statuses[agent_name]
        self._update_failure_status(status)
        self._record_circuit_breaker_failure(agent_name, status)
    
    def _update_failure_status(self, status: AgentFallbackStatus) -> None:
        """Update agent status for failed operation."""
        status.recent_failures += 1
        status.last_failure_time = datetime.now(UTC)
        status.health_score = max(0.0, status.health_score - 0.2)
        status.fallback_active = True
    
    def _record_circuit_breaker_failure(self, agent_name: str, status: AgentFallbackStatus) -> None:
        """Record failure in circuit breaker and update status."""
        cb = self.coordinator.agent_circuit_breakers.get(agent_name)
        if cb:
            cb.record_failure("agent_failure")
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
        failing_agents = self._count_failing_agents()
        failure_rate = failing_agents / len(self.coordinator.agent_statuses)
        return failure_rate >= self.coordinator.emergency_mode_threshold
    
    def _count_failing_agents(self) -> int:
        """Count agents that are currently failing."""
        return sum(1 for status in self.coordinator.agent_statuses.values() 
                   if status.health_score < 0.3 or status.circuit_breaker_open)
    
    async def should_prevent_cascade(self, requesting_agent: str) -> bool:
        """Check if cascade prevention should be active"""
        if not self.coordinator.agent_statuses:
            return False
        fallback_agents = self._count_fallback_agents()
        if self._is_agent_already_in_fallback(requesting_agent):
            return False
        return fallback_agents >= self.coordinator.max_concurrent_fallbacks
    
    def _count_fallback_agents(self) -> int:
        """Count agents currently in fallback mode."""
        return sum(1 for status in self.coordinator.agent_statuses.values() 
                   if status.fallback_active)
    
    def _is_agent_already_in_fallback(self, agent_name: str) -> bool:
        """Check if agent is already in fallback mode."""
        current_status = self.coordinator.agent_statuses.get(agent_name)
        return current_status and current_status.fallback_active
    
    async def update_system_health(self) -> None:
        """Update overall system health status"""
        if not self.coordinator.agent_statuses:
            return
        metrics = self._calculate_system_metrics()
        status = await self._create_system_status(metrics)
        self._update_health_history(status)
        self._log_health_changes(status, metrics)
    
    def _calculate_system_metrics(self) -> Dict[str, Any]:
        """Calculate system health metrics."""
        total_agents = len(self.coordinator.agent_statuses)
        agents_in_fallback = [name for name, status in self.coordinator.agent_statuses.items() 
                            if status.fallback_active]
        fallback_rate = len(agents_in_fallback) / total_agents
        return {
            'total_agents': total_agents,
            'agents_in_fallback': agents_in_fallback,
            'fallback_rate': fallback_rate
        }
    
    async def _create_system_status(self, metrics: Dict[str, Any]) -> SystemFallbackStatus:
        """Create system fallback status record."""
        health_level = self._calculate_health_level(metrics['fallback_rate'])
        return SystemFallbackStatus(
            health_level=health_level,
            agents_in_fallback=metrics['agents_in_fallback'],
            total_agents=metrics['total_agents'],
            cascade_prevention_active=await self.should_prevent_cascade(""),
            emergency_mode_active=await self.is_emergency_mode_active(),
            last_health_check=datetime.now(UTC)
        )
    
    def _update_health_history(self, status: SystemFallbackStatus) -> None:
        """Update health history with new status."""
        self.system_health_history.append(status)
        if len(self.system_health_history) > self.max_health_history:
            self.system_health_history = self.system_health_history[-self.max_health_history:]
    
    def _log_health_changes(self, status: SystemFallbackStatus, metrics: Dict[str, Any]) -> None:
        """Log health changes if not healthy."""
        if status.health_level != SystemHealthLevel.HEALTHY:
            logger.warning(
                f"System health: {status.health_level.value} "
                f"({len(metrics['agents_in_fallback'])}/{metrics['total_agents']} agents in fallback)"
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
        return self._build_system_status_dict(latest_status)
    
    def _build_system_status_dict(self, latest_status) -> Dict[str, Any]:
        """Build system status dictionary from latest status."""
        basic_status = self._create_basic_status_dict(latest_status)
        basic_status["agent_details"] = self._create_agent_details_dict()
        return basic_status
    
    def _create_basic_status_dict(self, latest_status) -> Dict[str, Any]:
        """Create basic status dictionary."""
        return {
            "system_health": latest_status.health_level.value,
            "agents_in_fallback": latest_status.agents_in_fallback,
            "total_agents": latest_status.total_agents,
            "cascade_prevention_active": latest_status.cascade_prevention_active,
            "emergency_mode_active": latest_status.emergency_mode_active,
            "last_updated": latest_status.last_health_check.isoformat()
        }
    
    def _create_agent_details_dict(self) -> Dict[str, Dict[str, Any]]:
        """Create agent details dictionary."""
        return {
            name: self._create_agent_status_dict(status)
            for name, status in self.coordinator.agent_statuses.items()
        }
    
    def _create_agent_status_dict(self, status) -> Dict[str, Any]:
        """Create single agent status dictionary."""
        return {
            "health_score": status.health_score,
            "circuit_breaker_open": status.circuit_breaker_open,
            "fallback_active": status.fallback_active,
            "recent_failures": status.recent_failures
        }