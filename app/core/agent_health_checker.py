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
            return await _perform_agent_health_check(start_time)
        except Exception as e:
            return _create_agent_health_error_result(start_time, e)
    return check_agent_health


async def _perform_agent_health_check(start_time: float) -> HealthCheckResult:
    """Perform agent health check and return result."""
    from app.services.metrics.agent_metrics import agent_metrics_collector
    system_overview = await agent_metrics_collector.get_system_overview()
    health_score = _calculate_agent_health_score(system_overview)
    response_time = (time.time() - start_time) * 1000
    return _create_agent_health_success_result(health_score, response_time, system_overview)


def _calculate_agent_health_score(system_overview: dict) -> float:
    """Calculate health score based on system overview metrics."""
    error_rate = system_overview.get("system_error_rate", 0.0)
    active_agents = system_overview.get("active_agents", 0)
    unhealthy_agents = system_overview.get("unhealthy_agents", 0)
    if active_agents == 0:
        return 1.0
    return _compute_health_score_with_penalties(error_rate, unhealthy_agents, active_agents)


def _compute_health_score_with_penalties(error_rate: float, unhealthy_agents: int, active_agents: int) -> float:
    """Compute health score with error and unhealthy agent penalties."""
    error_penalty = min(0.5, error_rate * 2)
    unhealthy_penalty = min(0.3, (unhealthy_agents / active_agents) * 0.5)
    return max(0.0, 1.0 - error_penalty - unhealthy_penalty)


def _create_agent_health_success_result(health_score: float, response_time: float, metadata: dict) -> HealthCheckResult:
    """Create successful agent health check result."""
    return HealthCheckResult(
        component_name="agents", success=True, health_score=health_score,
        response_time_ms=response_time, metadata=metadata
    )


def _create_agent_health_error_result(start_time: float, error: Exception) -> HealthCheckResult:
    """Create error agent health check result."""
    response_time = (time.time() - start_time) * 1000
    return HealthCheckResult(
        component_name="agents", success=False, health_score=0.0,
        response_time_ms=response_time, error_message=str(error)
    )


def calculate_health_status_from_score(health_score: float, thresholds: dict) -> str:
    """Calculate health status from health score using thresholds."""
    if health_score >= thresholds["healthy"]:
        return "HEALTHY"
    elif health_score >= thresholds["degraded"]:
        return "DEGRADED"
    return "UNHEALTHY" if health_score >= thresholds["unhealthy"] else "CRITICAL"


def determine_system_status(health_pct: float, critical_count: int) -> str:
    """Determine overall system status."""
    if critical_count > 0:
        return "critical"
    if health_pct < 0.5:
        return "unhealthy"
    return "degraded" if health_pct < 0.8 else "healthy"


def convert_legacy_result(component_name: str, legacy_result) -> HealthCheckResult:
    """Convert legacy health check result to new format."""
    health_score, metadata = _extract_legacy_data(legacy_result)
    return HealthCheckResult(
        component_name=component_name, success=health_score > 0,
        health_score=health_score, response_time_ms=0.0, metadata=metadata
    )

def _extract_legacy_data(legacy_result) -> tuple[float, dict]:
    """Extract health score and metadata from legacy result."""
    if isinstance(legacy_result, dict):
        return legacy_result.get("health_score", 1.0), legacy_result.get("metadata", {})
    elif isinstance(legacy_result, (int, float)):
        return float(legacy_result), {}
    else:
        return 1.0 if legacy_result else 0.0, {}