from sqlalchemy import text
from fastapi import APIRouter, HTTPException
from app.db.postgres import get_async_db as get_db, async_engine
from app.logging_config import central_logger
from app.services.database_env_service import DatabaseEnvironmentValidator
from app.services.schema_validation_service import SchemaValidationService
from app.config import settings

import asyncio
from typing import Dict, Any

router = APIRouter()
logger = central_logger.get_logger(__name__)

@router.get("/")
async def health() -> Dict[str, str]:
    """
    Basic health check endpoint - returns healthy if the application is running.
    """
    return {"status": "healthy"}

@router.get("/live")
async def live() -> Dict[str, str]:
    """
    Liveness probe to check if the application is running.
    """
    return {"status": "ok"}

@router.get("/ready")
async def ready() -> Dict[str, str]:
    """
    Readiness probe to check if the application is ready to serve requests.
    """
    import os
    
    try:
        # Skip database check if in mock mode
        database_url = os.getenv("DATABASE_URL", "")
        if "mock" not in database_url.lower():
            # Check Postgres connection
            async with get_db() as db:
                result = await db.execute(text("SELECT 1"))
                result.scalar_one_or_none()

        # Check ClickHouse connection only if not explicitly skipped
        if os.getenv('SKIP_CLICKHOUSE_INIT', 'false').lower() != 'true':
            try:
                from app.db.clickhouse import get_clickhouse_client
                async with get_clickhouse_client() as client:
                    client.ping()
            except Exception as e:
                logger.warning(f"ClickHouse check failed (non-critical): {e}")
                # Don't fail readiness if ClickHouse is not available in staging
                if settings.environment == "staging":
                    logger.info("Ignoring ClickHouse failure in staging environment")
                else:
                    raise

        # If all checks pass, return a success response
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")
    
@router.get("/database-env")
async def database_environment() -> Dict[str, Any]:
    """
    Check database environment configuration and validation status.
    """
    env_info = DatabaseEnvironmentValidator.get_environment_info()
    validation_result = DatabaseEnvironmentValidator.validate_database_url(
        env_info["database_url"], 
        env_info["environment"]
    )
    
    return {
        "environment": env_info["environment"],
        "database_name": validation_result["database_name"],
        "validation": {
            "valid": validation_result["valid"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"]
        },
        "debug_mode": env_info["debug"],
        "safe_database_name": DatabaseEnvironmentValidator.get_safe_database_name(env_info["environment"])
    }
    
@router.get("/schema-validation")
async def schema_validation() -> Dict[str, Any]:
    """
    Run and return comprehensive schema validation results.
    """
    try:
        results = await SchemaValidationService.validate_schema(async_engine)
        return results
    except Exception as e:
        logger.error(f"Schema validation check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent monitoring imports (lazy loading)
def get_agent_metrics_collector():
    """Lazy import for agent metrics collector."""
    from app.services.metrics.agent_metrics import agent_metrics_collector
    return agent_metrics_collector

def get_enhanced_health_monitor():
    """Lazy import for enhanced health monitor."""
    from app.core.system_health_monitor_enhanced import enhanced_system_health_monitor
    return enhanced_system_health_monitor

def get_alert_manager():
    """Lazy import for alert manager."""
    from app.monitoring.alert_manager import alert_manager
    return alert_manager


@router.get("/agents")
async def agent_health() -> Dict[str, Any]:
    """
    Get comprehensive agent health status and metrics.
    """
    try:
        health_monitor = get_enhanced_health_monitor()
        return await health_monitor.get_agent_health_details()
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/metrics")
async def agent_metrics() -> Dict[str, Any]:
    """
    Get detailed agent metrics and performance data.
    """
    try:
        metrics_collector = get_agent_metrics_collector()
        system_overview = await metrics_collector.get_system_overview()
        all_metrics = metrics_collector.get_all_agent_metrics()
        
        return {
            "system_overview": system_overview,
            "agent_metrics": {
                agent_name: {
                    "total_operations": metrics.total_operations,
                    "success_rate": metrics.success_rate,
                    "error_rate": metrics.error_rate,
                    "avg_execution_time_ms": metrics.avg_execution_time_ms,
                    "timeout_count": metrics.timeout_count,
                    "validation_error_count": metrics.validation_error_count,
                    "last_operation_time": metrics.last_operation_time
                }
                for agent_name, metrics in all_metrics.items()
            }
        }
    except Exception as e:
        logger.error(f"Agent metrics check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_name}")
async def specific_agent_health(agent_name: str) -> Dict[str, Any]:
    """
    Get health status for a specific agent.
    """
    try:
        metrics_collector = get_agent_metrics_collector()
        agent_metrics = metrics_collector.get_agent_metrics(agent_name)
        
        if not agent_metrics:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        health_score = metrics_collector.get_health_score(agent_name)
        recent_operations = metrics_collector.get_recent_operations(agent_name, hours=1)
        
        return {
            "agent_name": agent_name,
            "health_score": health_score,
            "metrics": {
                "total_operations": agent_metrics.total_operations,
                "success_rate": agent_metrics.success_rate,
                "error_rate": agent_metrics.error_rate,
                "avg_execution_time_ms": agent_metrics.avg_execution_time_ms,
                "timeout_count": agent_metrics.timeout_count,
                "validation_error_count": agent_metrics.validation_error_count
            },
            "recent_operations_count": len(recent_operations),
            "last_operation_time": agent_metrics.last_operation_time
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Specific agent health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def system_alerts() -> Dict[str, Any]:
    """
    Get current system alerts and alert manager status.
    """
    try:
        alert_manager = get_alert_manager()
        active_alerts = alert_manager.get_active_alerts()
        alert_summary = alert_manager.get_alert_summary()
        
        return {
            "alert_summary": alert_summary,
            "active_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "agent_name": alert.agent_name,
                    "timestamp": alert.timestamp,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value
                }
                for alert in active_alerts[:10]  # Limit to 10 most recent
            ]
        }
    except Exception as e:
        logger.error(f"Alerts check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/comprehensive")
async def comprehensive_health() -> Dict[str, Any]:
    """
    Get comprehensive system health report including all components.
    """
    try:
        health_monitor = get_enhanced_health_monitor()
        return await health_monitor.get_comprehensive_health_report()
    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

