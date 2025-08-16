"""
Agent Health Checking Functionality

Extracted from system_health_monitor.py to maintain 300-line limit.
Provides specialized health checking for agent components.
"""

import time
from typing import Callable
from app.logging_config import central_logger
from .health_types import HealthCheckResult

logger = central_logger.get_logger(__name__)


def register_agent_checker(register_func: Callable) -> None:
    """Register agent health checker if available."""
    try:
        from app.services.metrics.agent_metrics import agent_metrics_collector
        register_func("agents", create_agent_checker())
    except ImportError:
        logger.debug("Agent metrics not available, skipping agent health checker")


def create_agent_checker() -> Callable:
    """Create agent health checker function."""
    async def check_agent_health() -> HealthCheckResult:
        start_time = time.time()
        try:
            from app.services.metrics.agent_metrics import agent_metrics_collector
            system_overview = await agent_metrics_collector.get_system_overview()
            error_rate = system_overview.get("system_error_rate", 0.0)
            active_agents = system_overview.get("active_agents", 0)
            unhealthy_agents = system_overview.get("unhealthy_agents", 0)
            
            if active_agents == 0:
                health_score = 1.0
            else:
                error_penalty = min(0.5, error_rate * 2)
                unhealthy_penalty = min(0.3, (unhealthy_agents / active_agents) * 0.5)
                health_score = max(0.0, 1.0 - error_penalty - unhealthy_penalty)
            
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component_name="agents", success=True, health_score=health_score,
                response_time_ms=response_time, metadata=system_overview
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component_name="agents", success=False, health_score=0.0,
                response_time_ms=response_time, error_message=str(e)
            )
    return check_agent_health


def calculate_health_status_from_score(health_score: float, thresholds: dict) -> str:
    """Calculate health status from health score using thresholds."""
    if health_score >= thresholds["healthy"]:
        return "HEALTHY"
    elif health_score >= thresholds["degraded"]:
        return "DEGRADED"
    elif health_score >= thresholds["unhealthy"]:
        return "UNHEALTHY"
    else:
        return "CRITICAL"


def determine_system_status(health_pct: float, critical_count: int) -> str:
    """Determine overall system status."""
    if critical_count > 0:
        return "critical"
    elif health_pct < 0.5:
        return "unhealthy"
    elif health_pct < 0.8:
        return "degraded"
    else:
        return "healthy"


def convert_legacy_result(component_name: str, legacy_result) -> HealthCheckResult:
    """Convert legacy health check result to new format."""
    if isinstance(legacy_result, dict):
        health_score = legacy_result.get("health_score", 1.0)
        metadata = legacy_result.get("metadata", {})
    elif isinstance(legacy_result, (int, float)):
        health_score = float(legacy_result)
        metadata = {}
    else:
        health_score = 1.0 if legacy_result else 0.0
        metadata = {}
    
    return HealthCheckResult(
        component_name=component_name, success=health_score > 0,
        health_score=health_score, response_time_ms=0.0, metadata=metadata
    )