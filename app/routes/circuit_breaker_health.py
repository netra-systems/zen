"""Circuit breaker health and monitoring endpoints.

This module provides REST endpoints for monitoring circuit breaker
health, metrics, and state across the Netra platform.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, UTC

from app.services.circuit_breaker_monitor import (
    circuit_monitor, metrics_collector, get_circuit_health_dashboard
)
from app.core.circuit_breaker import circuit_registry
from app.llm.client import ResilientLLMClient
from app.db.client import db_client_manager
from app.services.external_api_client import http_client_manager
from app.logging_config import central_logger
from app.routes.utils.service_delegates import (
    delegate_circuit_dashboard, delegate_circuit_status, delegate_recent_events,
    delegate_recent_alerts, delegate_circuit_metrics, delegate_metrics_history
)
from app.routes.utils.response_builders import (
    build_circuit_response, build_service_health_response, build_timestamped_response
)
from app.routes.utils.validators import validate_circuit_exists
from app.routes.utils.circuit_helpers import (
    filter_llm_circuits, filter_database_circuits, filter_api_circuits,
    categorize_circuits, build_service_summary
)
from app.routes.utils.error_handlers import handle_circuit_breaker_error

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/circuit-breakers", tags=["Circuit Breaker Health"])


@router.get("/dashboard")
async def get_circuit_breaker_dashboard() -> Dict[str, Any]:
    """Get comprehensive circuit breaker dashboard."""
    return await delegate_circuit_dashboard()


@router.get("/status")
async def get_all_circuit_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers."""
    return await delegate_circuit_status()


async def _find_circuit_status(circuit_name: str) -> Dict[str, Any]:
    """Find specific circuit status."""
    all_status = await delegate_circuit_status()
    matched_name = validate_circuit_exists(all_status, circuit_name)
    return build_circuit_response(matched_name, all_status[matched_name])

@router.get("/status/{circuit_name}")
async def get_circuit_status(circuit_name: str) -> Dict[str, Any]:
    """Get status of specific circuit breaker."""
    try:
        return await _find_circuit_status(circuit_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        handle_circuit_breaker_error(e, "status")


@router.get("/events")
async def get_recent_events(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Get recent circuit breaker events."""
    return delegate_recent_events(limit)


@router.get("/alerts")
async def get_recent_alerts(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Get recent circuit breaker alerts."""
    return delegate_recent_alerts(limit)


@router.get("/metrics")
async def get_circuit_metrics(hours: int = Query(1, ge=1, le=168)) -> Dict[str, Dict[str, Any]]:
    """Get aggregated circuit breaker metrics."""
    return delegate_circuit_metrics(hours)


@router.get("/metrics/{circuit_name}")
async def get_circuit_metrics_history(
    circuit_name: str, 
    hours: int = Query(24, ge=1, le=168)
) -> List[Dict[str, Any]]:
    """Get metrics history for specific circuit."""
    return delegate_metrics_history(circuit_name, hours)


async def _get_llm_circuits() -> Dict[str, Any]:
    """Get LLM circuit status."""
    all_status = await delegate_circuit_status()
    return filter_llm_circuits(all_status)

@router.get("/health/llm")
async def get_llm_health() -> Dict[str, Any]:
    """Get LLM circuit breaker health."""
    try:
        llm_circuits = await _get_llm_circuits()
        return build_service_health_response("llm", llm_circuits)
    except Exception as e:
        handle_circuit_breaker_error(e, "LLM health")


async def _get_database_health_data() -> tuple[Dict, Dict[str, Any]]:
    """Get database health checks and circuits."""
    db_health = await db_client_manager.health_check_all()
    all_status = await delegate_circuit_status()
    return db_health, filter_database_circuits(all_status)

@router.get("/health/database")
async def get_database_health() -> Dict[str, Any]:
    """Get database circuit breaker health."""
    try:
        db_health, db_circuits = await _get_database_health_data()
        return build_service_health_response("database", db_circuits, db_health)
    except Exception as e:
        handle_circuit_breaker_error(e, "database health")


async def _get_external_api_health_data() -> tuple[Dict, Dict[str, Any]]:
    """Get external API health checks and circuits."""
    api_health = await http_client_manager.health_check_all()
    all_status = await delegate_circuit_status()
    return api_health, filter_api_circuits(all_status)

@router.get("/health/external-apis")
async def get_external_api_health() -> Dict[str, Any]:
    """Get external API circuit breaker health."""
    try:
        api_health, api_circuits = await _get_external_api_health_data()
        return build_service_health_response("external_apis", api_circuits, api_health)
    except Exception as e:
        handle_circuit_breaker_error(e, "external API health")


async def _build_health_summary_data() -> Dict[str, Any]:
    """Build health summary data."""
    summary = circuit_monitor.get_health_summary()
    all_status = await delegate_circuit_status()
    service_health = categorize_circuits(all_status)
    service_summary = build_service_summary(service_health)
    return {"overview": summary, "service_health": service_summary}

@router.get("/health/summary")
async def get_health_summary() -> Dict[str, Any]:
    """Get overall circuit breaker health summary."""
    try:
        summary_data = await _build_health_summary_data()
        return build_timestamped_response(summary_data)
    except Exception as e:
        handle_circuit_breaker_error(e, "health summary")


async def _execute_monitoring_start(interval_seconds: float) -> Dict[str, str]:
    """Execute monitoring start operation."""
    await circuit_monitor.start_monitoring(interval_seconds)
    return {
        "status": "started",
        "interval_seconds": str(interval_seconds),
        "message": "Circuit breaker monitoring started"
    }

@router.post("/monitoring/start")
async def start_monitoring(interval_seconds: float = Query(5.0, ge=1.0, le=60.0)) -> Dict[str, str]:
    """Start circuit breaker monitoring."""
    try:
        return await _execute_monitoring_start(interval_seconds)
    except Exception as e:
        handle_circuit_breaker_error(e, "start monitoring")


async def _execute_monitoring_stop() -> Dict[str, str]:
    """Execute monitoring stop operation."""
    await circuit_monitor.stop_monitoring()
    return {
        "status": "stopped",
        "message": "Circuit breaker monitoring stopped"
    }

@router.post("/monitoring/stop")
async def stop_monitoring() -> Dict[str, str]:
    """Stop circuit breaker monitoring."""
    try:
        return await _execute_monitoring_stop()
    except Exception as e:
        handle_circuit_breaker_error(e, "stop monitoring")


