"""Circuit breaker health and monitoring endpoints.

This module provides REST endpoints for monitoring circuit breaker
health, metrics, and state across the Netra platform.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from app.services.circuit_breaker_monitor import (
    circuit_monitor, metrics_collector, get_circuit_health_dashboard
)
from app.core.circuit_breaker import circuit_registry
from app.llm.client import ResilientLLMClient
from app.db.client import db_client_manager
from app.services.external_api_client import http_client_manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/circuit-breakers", tags=["Circuit Breaker Health"])


@router.get("/dashboard")
async def get_circuit_breaker_dashboard() -> Dict[str, Any]:
    """Get comprehensive circuit breaker dashboard."""
    try:
        return await get_circuit_health_dashboard()
    except Exception as e:
        logger.error(f"Failed to get circuit breaker dashboard: {e}")
        raise HTTPException(status_code=500, detail="Dashboard unavailable")


@router.get("/status")
async def get_all_circuit_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers."""
    try:
        return await circuit_registry.get_all_status()
    except Exception as e:
        logger.error(f"Failed to get circuit status: {e}")
        raise HTTPException(status_code=500, detail="Status unavailable")


@router.get("/status/{circuit_name}")
async def get_circuit_status(circuit_name: str) -> Dict[str, Any]:
    """Get status of specific circuit breaker."""
    try:
        all_status = await circuit_registry.get_all_status()
        
        # Search for circuit by name (exact match or partial)
        for name, status in all_status.items():
            if name == circuit_name or circuit_name in name:
                return {
                    "circuit_name": name,
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        raise HTTPException(
            status_code=404, 
            detail=f"Circuit breaker '{circuit_name}' not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get circuit status for {circuit_name}: {e}")
        raise HTTPException(status_code=500, detail="Status unavailable")


@router.get("/events")
async def get_recent_events(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Get recent circuit breaker events."""
    try:
        events = circuit_monitor.get_recent_events(limit)
        return [
            {
                "circuit_name": event.circuit_name,
                "old_state": event.old_state,
                "new_state": event.new_state,
                "timestamp": event.timestamp.isoformat(),
                "failure_count": event.failure_count,
                "success_rate": event.success_rate,
                "metadata": event.metadata
            }
            for event in events
        ]
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        raise HTTPException(status_code=500, detail="Events unavailable")


@router.get("/alerts")
async def get_recent_alerts(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Get recent circuit breaker alerts."""
    try:
        alerts = circuit_monitor.get_recent_alerts(limit)
        return [
            {
                "circuit_name": alert.circuit_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "state": alert.state,
                "metrics": alert.metrics
            }
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"Failed to get recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Alerts unavailable")


@router.get("/metrics")
async def get_circuit_metrics(hours: int = Query(1, ge=1, le=168)) -> Dict[str, Dict[str, Any]]:
    """Get aggregated circuit breaker metrics."""
    try:
        return metrics_collector.get_aggregated_metrics(hours)
    except Exception as e:
        logger.error(f"Failed to get circuit metrics: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")


@router.get("/metrics/{circuit_name}")
async def get_circuit_metrics_history(
    circuit_name: str, 
    hours: int = Query(24, ge=1, le=168)
) -> List[Dict[str, Any]]:
    """Get metrics history for specific circuit."""
    try:
        history = metrics_collector.get_metrics_history(circuit_name, hours)
        return [
            {
                "timestamp": metrics["timestamp"].isoformat(),
                "state": metrics["state"],
                "success_rate": metrics["success_rate"],
                "total_calls": metrics["total_calls"],
                "rejected_calls": metrics["rejected_calls"],
                "timeouts": metrics["timeouts"]
            }
            for metrics in history
        ]
    except Exception as e:
        logger.error(f"Failed to get metrics history for {circuit_name}: {e}")
        raise HTTPException(status_code=500, detail="Metrics history unavailable")


@router.get("/health/llm")
async def get_llm_health() -> Dict[str, Any]:
    """Get LLM circuit breaker health."""
    try:
        # This would require access to LLM client instances
        # For now, return general circuit status for LLM-related circuits
        all_status = await circuit_registry.get_all_status()
        llm_circuits = {
            name: status for name, status in all_status.items()
            if "llm" in name.lower()
        }
        
        return {
            "service": "llm",
            "circuits": llm_circuits,
            "overall_health": _assess_service_health(llm_circuits),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get LLM health: {e}")
        raise HTTPException(status_code=500, detail="LLM health unavailable")


@router.get("/health/database")
async def get_database_health() -> Dict[str, Any]:
    """Get database circuit breaker health."""
    try:
        db_health = await db_client_manager.health_check_all()
        all_status = await circuit_registry.get_all_status()
        db_circuits = {
            name: status for name, status in all_status.items()
            if any(db_type in name.lower() for db_type in ["postgres", "clickhouse", "db_"])
        }
        
        return {
            "service": "database",
            "health_checks": db_health,
            "circuits": db_circuits,
            "overall_health": _assess_service_health(db_circuits),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get database health: {e}")
        raise HTTPException(status_code=500, detail="Database health unavailable")


@router.get("/health/external-apis")
async def get_external_api_health() -> Dict[str, Any]:
    """Get external API circuit breaker health."""
    try:
        api_health = await http_client_manager.health_check_all()
        all_status = await circuit_registry.get_all_status()
        api_circuits = {
            name: status for name, status in all_status.items()
            if any(api_type in name.lower() for api_type in ["http_", "api", "google", "openai"])
        }
        
        return {
            "service": "external_apis",
            "health_checks": api_health,
            "circuits": api_circuits,
            "overall_health": _assess_service_health(api_circuits),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get external API health: {e}")
        raise HTTPException(status_code=500, detail="External API health unavailable")


@router.get("/health/summary")
async def get_health_summary() -> Dict[str, Any]:
    """Get overall circuit breaker health summary."""
    try:
        summary = circuit_monitor.get_health_summary()
        all_status = await circuit_registry.get_all_status()
        
        # Categorize circuits by service type
        service_health = {
            "llm": _filter_circuits(all_status, ["llm"]),
            "database": _filter_circuits(all_status, ["postgres", "clickhouse", "db_"]),
            "external_apis": _filter_circuits(all_status, ["http_", "api", "google", "openai"]),
            "other": {}
        }
        
        # Find uncategorized circuits
        categorized_names = set()
        for circuits in service_health.values():
            categorized_names.update(circuits.keys())
        
        service_health["other"] = {
            name: status for name, status in all_status.items()
            if name not in categorized_names
        }
        
        return {
            "overview": summary,
            "service_health": {
                service: {
                    "circuit_count": len(circuits),
                    "overall_health": _assess_service_health(circuits),
                    "circuits": circuits
                }
                for service, circuits in service_health.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get health summary: {e}")
        raise HTTPException(status_code=500, detail="Health summary unavailable")


@router.post("/monitoring/start")
async def start_monitoring(interval_seconds: float = Query(5.0, ge=1.0, le=60.0)) -> Dict[str, str]:
    """Start circuit breaker monitoring."""
    try:
        await circuit_monitor.start_monitoring(interval_seconds)
        return {
            "status": "started",
            "interval_seconds": str(interval_seconds),
            "message": "Circuit breaker monitoring started"
        }
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


@router.post("/monitoring/stop")
async def stop_monitoring() -> Dict[str, str]:
    """Stop circuit breaker monitoring."""
    try:
        await circuit_monitor.stop_monitoring()
        return {
            "status": "stopped",
            "message": "Circuit breaker monitoring stopped"
        }
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop monitoring")


def _filter_circuits(all_circuits: Dict[str, Dict[str, Any]], 
                    keywords: List[str]) -> Dict[str, Dict[str, Any]]:
    """Filter circuits by keywords."""
    return {
        name: status for name, status in all_circuits.items()
        if any(keyword in name.lower() for keyword in keywords)
    }


def _assess_service_health(circuits: Dict[str, Dict[str, Any]]) -> str:
    """Assess overall health of service circuits."""
    if not circuits:
        return "unknown"
    
    states = [status.get("health", "unknown") for status in circuits.values()]
    
    if all(state == "healthy" for state in states):
        return "healthy"
    elif any(state == "unhealthy" for state in states):
        return "unhealthy"
    elif any(state == "recovering" for state in states):
        return "recovering"
    else:
        return "degraded"