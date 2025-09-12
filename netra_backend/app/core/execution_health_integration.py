"""Integration module for execution tracking health checks.

Bridges the gap between AgentExecutionTracker and UnifiedHealthService.
Ensures health checks accurately reflect agent execution state.

Business Value: Prevents false-positive health checks when agents are dead.
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timezone, timedelta

from netra_backend.app.core.agent_execution_tracker import (
    get_execution_tracker,
    ExecutionState
)
from netra_backend.app.core.health_types import (
    HealthCheckConfig,
    HealthCheckResult,
    HealthStatus,
    CheckType
)
from netra_backend.app.services.unified_health_service import UnifiedHealthService
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionHealthIntegration:
    """Integrates execution tracking with health monitoring."""
    
    def __init__(self, health_service: Optional[UnifiedHealthService] = None):
        self.execution_tracker = get_execution_tracker()
        self.health_service = health_service
        self._registered = False
        
    async def register_health_checks(self) -> None:
        """Register execution tracking health checks with unified health service."""
        if not self.health_service:
            logger.warning("No health service available for registration")
            return
            
        if self._registered:
            logger.debug("Execution health checks already registered")
            return
            
        # Register agent execution health check
        await self.health_service.register_check(
            HealthCheckConfig(
                name="agent_execution",
                check_type=CheckType.READINESS,
                check_function=self.check_agent_execution_health,
                timeout_seconds=5,
                critical=True
            )
        )
        
        # Register execution timeout check
        await self.health_service.register_check(
            HealthCheckConfig(
                name="execution_timeouts",
                check_type=CheckType.READINESS,
                check_function=self.check_execution_timeouts,
                timeout_seconds=5,
                critical=False
            )
        )
        
        # Register execution capacity check
        await self.health_service.register_check(
            HealthCheckConfig(
                name="execution_capacity",
                check_type=CheckType.READINESS,
                check_function=self.check_execution_capacity,
                timeout_seconds=5,
                critical=False
            )
        )
        
        self._registered = True
        logger.info("Registered execution tracking health checks")
        
    async def check_agent_execution_health(self) -> Dict[str, Any]:
        """Check health of agent execution system.
        
        This is the CRITICAL check that catches agent death.
        """
        try:
            # Get all active executions
            active_executions = self.execution_tracker.get_active_executions()
            
            # Check for dead agents
            dead_agents = []
            stuck_agents = []
            healthy_agents = []
            
            for execution in active_executions:
                if execution.is_dead():
                    dead_agents.append({
                        'agent': execution.agent_name,
                        'execution_id': execution.execution_id,
                        'time_since_heartbeat': execution.time_since_heartbeat.total_seconds()
                    })
                elif execution.is_timed_out():
                    stuck_agents.append({
                        'agent': execution.agent_name,
                        'execution_id': execution.execution_id,
                        'duration': execution.duration.total_seconds() if execution.duration else 0
                    })
                else:
                    healthy_agents.append(execution.agent_name)
            
            # Determine health status
            if dead_agents:
                return {
                    'status': HealthStatus.UNHEALTHY.value,
                    'message': f"Found {len(dead_agents)} dead agents",
                    'dead_agents': dead_agents,
                    'details': {
                        'total_active': len(active_executions),
                        'dead': len(dead_agents),
                        'stuck': len(stuck_agents),
                        'healthy': len(healthy_agents)
                    }
                }
            elif stuck_agents:
                return {
                    'status': HealthStatus.DEGRADED.value,
                    'message': f"Found {len(stuck_agents)} stuck agents",
                    'stuck_agents': stuck_agents,
                    'details': {
                        'total_active': len(active_executions),
                        'stuck': len(stuck_agents),
                        'healthy': len(healthy_agents)
                    }
                }
            else:
                return {
                    'status': HealthStatus.HEALTHY.value,
                    'message': f"{len(healthy_agents)} agents executing normally",
                    'details': {
                        'total_active': len(active_executions),
                        'healthy': len(healthy_agents)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error checking agent execution health: {e}")
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'message': f"Health check failed: {str(e)}"
            }
            
    async def check_execution_timeouts(self) -> Dict[str, Any]:
        """Check for execution timeout trends."""
        try:
            stats = self.execution_tracker.get_statistics()
            timeout_rate = stats.get('timeout_rate', 0)
            recent_timeouts = stats.get('recent_timeout_count', 0)
            
            if timeout_rate > 0.5:  # More than 50% timeout rate
                return {
                    'status': HealthStatus.UNHEALTHY.value,
                    'message': f"High timeout rate: {timeout_rate:.1%}",
                    'details': {
                        'timeout_rate': timeout_rate,
                        'recent_timeouts': recent_timeouts
                    }
                }
            elif timeout_rate > 0.2:  # More than 20% timeout rate
                return {
                    'status': HealthStatus.DEGRADED.value,
                    'message': f"Elevated timeout rate: {timeout_rate:.1%}",
                    'details': {
                        'timeout_rate': timeout_rate,
                        'recent_timeouts': recent_timeouts
                    }
                }
            else:
                return {
                    'status': HealthStatus.HEALTHY.value,
                    'message': f"Normal timeout rate: {timeout_rate:.1%}",
                    'details': {
                        'timeout_rate': timeout_rate,
                        'recent_timeouts': recent_timeouts
                    }
                }
                
        except Exception as e:
            logger.error(f"Error checking execution timeouts: {e}")
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': f"Check failed: {str(e)}"
            }
            
    async def check_execution_capacity(self) -> Dict[str, Any]:
        """Check available execution capacity."""
        try:
            stats = self.execution_tracker.get_statistics()
            active_count = stats.get('active_execution_count', 0)
            max_capacity = 100  # Configurable max executions
            
            usage_percent = (active_count / max_capacity) * 100
            
            if usage_percent > 90:
                return {
                    'status': HealthStatus.UNHEALTHY.value,
                    'message': f"Near capacity: {usage_percent:.0f}% used",
                    'details': {
                        'active_executions': active_count,
                        'max_capacity': max_capacity,
                        'available': max_capacity - active_count
                    }
                }
            elif usage_percent > 70:
                return {
                    'status': HealthStatus.DEGRADED.value,
                    'message': f"High usage: {usage_percent:.0f}% used",
                    'details': {
                        'active_executions': active_count,
                        'max_capacity': max_capacity,
                        'available': max_capacity - active_count
                    }
                }
            else:
                return {
                    'status': HealthStatus.HEALTHY.value,
                    'message': f"Normal usage: {usage_percent:.0f}% used",
                    'details': {
                        'active_executions': active_count,
                        'max_capacity': max_capacity,
                        'available': max_capacity - active_count
                    }
                }
                
        except Exception as e:
            logger.error(f"Error checking execution capacity: {e}")
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': f"Check failed: {str(e)}"
            }


async def setup_execution_health_monitoring(health_service: UnifiedHealthService) -> None:
    """Setup execution health monitoring integration.
    
    Call this during application startup to ensure health checks
    accurately reflect agent execution state.
    """
    integration = ExecutionHealthIntegration(health_service)
    await integration.register_health_checks()
    logger.info(" PASS:  Execution health monitoring setup complete")