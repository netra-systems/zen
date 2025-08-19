from sqlalchemy import text
from fastapi import APIRouter, HTTPException, Depends
from app.db.postgres import async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import central_logger
from app.services.database_env_service import DatabaseEnvironmentValidator
from app.services.schema_validation_service import SchemaValidationService
from app.config import settings
from app.dependencies import get_db_dependency

# Unified Health System imports
from app.core.health import (
    HealthInterface, HealthLevel, DatabaseHealthChecker, 
    DependencyHealthChecker, HealthResponseBuilder
)

import asyncio
from typing import Dict, Any

router = APIRouter()
logger = central_logger.get_logger(__name__)

# Initialize unified health interface
health_interface = HealthInterface("netra-ai-platform", "1.0.0")
response_builder = HealthResponseBuilder("netra-ai-platform", "1.0.0")

# Register health checkers
health_interface.register_checker(DatabaseHealthChecker("postgres"))
health_interface.register_checker(DatabaseHealthChecker("clickhouse"))
health_interface.register_checker(DatabaseHealthChecker("redis"))
health_interface.register_checker(DependencyHealthChecker("websocket"))
health_interface.register_checker(DependencyHealthChecker("llm"))

@router.get("/")
async def health() -> Dict[str, Any]:
    """
    Basic health check endpoint - returns healthy if the application is running.
    """
    return await health_interface.get_health_status(HealthLevel.BASIC)

@router.get("/live")
async def live() -> Dict[str, Any]:
    """
    Liveness probe to check if the application is running.
    """
    return response_builder.create_basic_response("healthy")

async def _check_postgres_connection(db: AsyncSession) -> None:
    """Check Postgres database connection."""
    import os
    database_url = os.getenv("DATABASE_URL", "")
    if "mock" not in database_url.lower():
        result = await db.execute(text("SELECT 1"))
        result.scalar_one_or_none()

async def _check_clickhouse_connection() -> None:
    """Check ClickHouse database connection."""
    import os
    if os.getenv('SKIP_CLICKHOUSE_INIT', 'false').lower() != 'true':
        await _perform_clickhouse_check()

async def _perform_clickhouse_check() -> None:
    """Perform the actual ClickHouse connection check."""
    try:
        from app.db.clickhouse import get_clickhouse_client
        async with get_clickhouse_client() as client:
            client.ping()
    except Exception as e:
        await _handle_clickhouse_error(e)

async def _handle_clickhouse_error(error: Exception) -> None:
    """Handle ClickHouse connection errors."""
    logger.warning(f"ClickHouse check failed (non-critical): {error}")
    if settings.environment == "staging":
        logger.info("Ignoring ClickHouse failure in staging environment")
    else:
        raise

async def _check_database_connection(db: AsyncSession) -> None:
    """Check database connection using dependency injection."""
    await _check_postgres_connection(db)
    await _check_clickhouse_connection()

async def _check_readiness_status(db: AsyncSession) -> Dict[str, Any]:
    """Check application readiness including database connectivity."""
    try:
        # First check database connectivity using dependency injection
        await _check_database_connection(db)
        
        # Then get overall health status
        health_status = await health_interface.get_health_status(HealthLevel.STANDARD)
        if health_status["status"] in ["healthy", "degraded"]:
            return {"status": "ready", "service": "netra-ai-platform", "details": health_status}
        raise HTTPException(status_code=503, detail="Service Unavailable")
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")

@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db_dependency)) -> Dict[str, Any]:
    """Readiness probe to check if the application is ready to serve requests."""
    try:
        return await _check_readiness_status(db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")
    
def _build_database_environment_response(env_info: Dict, validation_result: Dict) -> Dict[str, Any]:
    """Build database environment response."""
    return {
        "environment": env_info["environment"], "database_name": validation_result["database_name"],
        "validation": {"valid": validation_result["valid"], "errors": validation_result["errors"], "warnings": validation_result["warnings"]},
        "debug_mode": env_info["debug"], "safe_database_name": DatabaseEnvironmentValidator.get_safe_database_name(env_info["environment"])
    }

@router.get("/database-env")
async def database_environment() -> Dict[str, Any]:
    """Check database environment configuration and validation status."""
    env_info = DatabaseEnvironmentValidator.get_environment_info()
    validation_result = DatabaseEnvironmentValidator.validate_database_url(env_info["database_url"], env_info["environment"])
    return _build_database_environment_response(env_info, validation_result)
    
async def _run_schema_validation() -> Dict[str, Any]:
    """Run schema validation with error handling."""
    try:
        return await SchemaValidationService.validate_schema(async_engine)
    except Exception as e:
        logger.error(f"Schema validation check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema-validation")
async def schema_validation() -> Dict[str, Any]:
    """Run and return comprehensive schema validation results."""
    return await _run_schema_validation()


# Agent monitoring imports (lazy loading)
def get_agent_metrics_collector():
    """Lazy import for agent metrics collector."""
    from app.services.metrics.agent_metrics import agent_metrics_collector
    return agent_metrics_collector

def get_enhanced_health_monitor():
    """Lazy import for enhanced health monitor."""
    from app.core.system_health_monitor import system_health_monitor
    return system_health_monitor

def get_alert_manager():
    """Lazy import for alert manager."""
    from app.monitoring.alert_manager import alert_manager
    return alert_manager


async def _get_agent_health_details() -> Dict[str, Any]:
    """Get agent health details with error handling."""
    try:
        health_monitor = get_enhanced_health_monitor()
        return await health_monitor.get_agent_health_details()
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def agent_health() -> Dict[str, Any]:
    """Get comprehensive agent health status and metrics."""
    return await _get_agent_health_details()


def _create_agent_metric_entry(agent_name: str, metrics) -> Dict[str, Any]:
    """Create individual agent metric entry."""
    return {
        "total_operations": metrics.total_operations, "success_rate": metrics.success_rate, "error_rate": metrics.error_rate,
        "avg_execution_time_ms": metrics.avg_execution_time_ms, "timeout_count": metrics.timeout_count,
        "validation_error_count": metrics.validation_error_count, "last_operation_time": metrics.last_operation_time
    }

def _build_agent_metrics_response(system_overview: Dict, all_metrics: Dict) -> Dict[str, Any]:
    """Build agent metrics response."""
    return {
        "system_overview": system_overview,
        "agent_metrics": {agent_name: _create_agent_metric_entry(agent_name, metrics) for agent_name, metrics in all_metrics.items()}
    }

async def _collect_agent_metrics_data() -> tuple[Dict, Dict]:
    """Collect agent metrics data from collector."""
    metrics_collector = get_agent_metrics_collector()
    system_overview = await metrics_collector.get_system_overview()
    all_metrics = metrics_collector.get_all_agent_metrics()
    return system_overview, all_metrics

async def _get_detailed_agent_metrics() -> Dict[str, Any]:
    """Get detailed agent metrics with error handling."""
    try:
        system_overview, all_metrics = await _collect_agent_metrics_data()
        return _build_agent_metrics_response(system_overview, all_metrics)
    except Exception as e:
        logger.error(f"Agent metrics check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/metrics")
async def agent_metrics() -> Dict[str, Any]:
    """Get detailed agent metrics and performance data."""
    return await _get_detailed_agent_metrics()


def _build_specific_agent_response(agent_name: str, agent_metrics, health_score: float, recent_operations) -> Dict[str, Any]:
    """Build specific agent health response."""
    return {
        "agent_name": agent_name, "health_score": health_score,
        "metrics": {"total_operations": agent_metrics.total_operations, "success_rate": agent_metrics.success_rate, "error_rate": agent_metrics.error_rate, "avg_execution_time_ms": agent_metrics.avg_execution_time_ms, "timeout_count": agent_metrics.timeout_count, "validation_error_count": agent_metrics.validation_error_count},
        "recent_operations_count": len(recent_operations), "last_operation_time": agent_metrics.last_operation_time
    }

async def _validate_agent_exists(metrics_collector, agent_name: str):
    """Validate that agent exists in metrics collector."""
    agent_metrics = metrics_collector.get_agent_metrics(agent_name)
    if not agent_metrics:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    return agent_metrics

async def _collect_specific_agent_data(agent_name: str) -> tuple:
    """Collect specific agent data from metrics collector."""
    metrics_collector = get_agent_metrics_collector()
    agent_metrics = await _validate_agent_exists(metrics_collector, agent_name)
    health_score = metrics_collector.get_health_score(agent_name)
    recent_operations = metrics_collector.get_recent_operations(agent_name, hours=1)
    return agent_metrics, health_score, recent_operations

async def _get_specific_agent_health_data(agent_name: str) -> Dict[str, Any]:
    """Get specific agent health data with validation."""
    try:
        return await _process_specific_agent_health_data(agent_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Specific agent health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_specific_agent_health_data(agent_name: str) -> Dict[str, Any]:
    """Process specific agent health data collection."""
    agent_metrics, health_score, recent_operations = await _collect_specific_agent_data(agent_name)
    return _build_specific_agent_response(agent_name, agent_metrics, health_score, recent_operations)

@router.get("/agents/{agent_name}")
async def specific_agent_health(agent_name: str) -> Dict[str, Any]:
    """Get health status for a specific agent."""
    return await _get_specific_agent_health_data(agent_name)


def _build_alert_response_item(alert) -> Dict[str, Any]:
    """Build individual alert response item."""
    return {"alert_id": alert.alert_id, "level": alert.level.value, "title": alert.title, "message": alert.message, "agent_name": alert.agent_name, "timestamp": alert.timestamp, "current_value": alert.current_value, "threshold_value": alert.threshold_value}

def _build_alerts_response(alert_summary, active_alerts) -> Dict[str, Any]:
    """Build system alerts response."""
    return {"alert_summary": alert_summary, "active_alerts": [_build_alert_response_item(alert) for alert in active_alerts[:10]]}

async def _collect_alerts_data() -> tuple:
    """Collect alerts data from alert manager."""
    alert_manager = get_alert_manager()
    active_alerts = alert_manager.get_active_alerts()
    alert_summary = alert_manager.get_alert_summary()
    return alert_summary, active_alerts

async def _get_system_alerts_data() -> Dict[str, Any]:
    """Get system alerts data with error handling."""
    try:
        alert_summary, active_alerts = await _collect_alerts_data()
        return _build_alerts_response(alert_summary, active_alerts)
    except Exception as e:
        logger.error(f"Alerts check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def system_alerts() -> Dict[str, Any]:
    """Get current system alerts and alert manager status."""
    return await _get_system_alerts_data()


async def _build_comprehensive_health_response() -> Dict[str, Any]:
    """Build comprehensive health response with enterprise data."""
    comprehensive_status = await health_interface.get_health_status(HealthLevel.COMPREHENSIVE)
    availability_percentage = _calculate_availability(comprehensive_status)
    return response_builder.create_enterprise_response(
        status=comprehensive_status["status"], uptime_seconds=comprehensive_status["uptime_seconds"],
        detailed_checks={}, metrics=comprehensive_status["metrics"], availability_percentage=availability_percentage
    )

async def _get_comprehensive_health_safe() -> Dict[str, Any]:
    """Get comprehensive health with error handling."""
    try:
        return await _build_comprehensive_health_response()
    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/comprehensive")
async def comprehensive_health() -> Dict[str, Any]:
    """Get comprehensive system health report including all components."""
    return await _get_comprehensive_health_safe()

def _count_successful_checks(checks: Dict) -> int:
    """Count successful health checks."""
    return sum(1 for check_result in checks.values() if check_result)

def _calculate_availability(health_status: Dict[str, Any]) -> float:
    """Calculate current availability percentage for Enterprise SLA."""
    if "checks" not in health_status or not health_status["checks"]:
        return 100.0
    checks = health_status["checks"]
    successful_checks = _count_successful_checks(checks)
    return (successful_checks / len(checks)) * 100.0

