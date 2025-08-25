import asyncio
import json
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.configuration import unified_config_manager

# Unified Health System imports
from netra_backend.app.core.health import (
    DatabaseHealthChecker,
    DependencyHealthChecker,
    HealthInterface,
    HealthLevel,
    HealthResponseBuilder,
)
from netra_backend.app.dependencies import get_db_dependency
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database_env_service import DatabaseEnvironmentValidator
from netra_backend.app.services.schema_validation_service import SchemaValidationService

router = APIRouter()
logger = central_logger.get_logger(__name__)

# Initialize unified health interface
health_interface = HealthInterface("netra-ai-platform", "1.0.0")
response_builder = HealthResponseBuilder("netra-ai-platform", "1.0.0")

# Register health checkers - using simple names for critical component matching
class SimpleNameDatabaseHealthChecker(DatabaseHealthChecker):
    """Database health checker with simple naming for critical component matching."""
    def __init__(self, db_type: str, timeout: float = 5.0):
        super().__init__(db_type, timeout)
        self.name = db_type  # Override to use simple name instead of "database_{db_type}"

health_interface.register_checker(SimpleNameDatabaseHealthChecker("postgres"))
health_interface.register_checker(SimpleNameDatabaseHealthChecker("clickhouse"))
health_interface.register_checker(SimpleNameDatabaseHealthChecker("redis"))
health_interface.register_checker(DependencyHealthChecker("websocket"))
health_interface.register_checker(DependencyHealthChecker("llm"))


def _create_error_response(status_code: int, response_data: Dict[str, Any]) -> Response:
    """Create a JSON error response with proper status code."""
    return Response(
        content=json.dumps(response_data),
        status_code=status_code,
        media_type="application/json"
    )

@router.get("/")
@router.options("/")
async def health(request: Request, response: Response) -> Dict[str, Any]:
    """
    Basic health check endpoint - returns healthy if the application is running.
    Checks startup state to ensure proper readiness signaling during cold starts.
    Supports API versioning through Accept-Version and API-Version headers.
    """
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return {"status": "ok", "message": "CORS preflight"}
    
    # Handle API versioning
    requested_version = request.headers.get("Accept-Version") or request.headers.get("API-Version", "current")
    response.headers["API-Version"] = requested_version
    # Check if application startup is complete
    app_state = getattr(request.app, 'state', None)
    if app_state:
        # Check startup completion status
        startup_complete = getattr(app_state, 'startup_complete', None)
        
        # Handle case where startup_complete is a MagicMock (test environment)
        if hasattr(startup_complete, '_mock_name'):
            startup_complete = None
        
        if startup_complete is False:
            # Startup in progress or failed
            startup_in_progress = getattr(app_state, 'startup_in_progress', False)
            startup_failed = getattr(app_state, 'startup_failed', False)
            startup_error = getattr(app_state, 'startup_error', None)
            
            # Handle MagicMock objects for test environment
            if hasattr(startup_in_progress, '_mock_name'):
                startup_in_progress = False
            if hasattr(startup_failed, '_mock_name'):
                startup_failed = False
            if hasattr(startup_error, '_mock_name'):
                startup_error = None
            
            if startup_failed:
                return _create_error_response(503, {
                    "status": "unhealthy",
                    "message": f"Startup failed: {startup_error}" if startup_error else "Startup failed",
                    "startup_failed": True
                })
            elif startup_in_progress:
                # Check for startup timeout
                startup_start_time = getattr(app_state, 'startup_start_time', None)
                
                # Handle MagicMock objects for test environment
                if hasattr(startup_start_time, '_mock_name'):
                    startup_start_time = None
                
                if startup_start_time and time.time() - startup_start_time > 300:  # 5 minutes
                    return _create_error_response(503, {
                        "status": "unhealthy",
                        "message": "Startup taking too long - possible timeout",
                        "startup_in_progress": True,
                        "startup_duration": time.time() - startup_start_time
                    })
                
                # Include progress information if available
                startup_phase = getattr(app_state, 'startup_phase', 'unknown')
                startup_progress = getattr(app_state, 'startup_progress', None)
                
                # Handle MagicMock objects for test environment
                if hasattr(startup_phase, '_mock_name'):
                    startup_phase = 'unknown'
                if hasattr(startup_progress, '_mock_name'):
                    startup_progress = None
                
                detail = {
                    "status": "unhealthy",
                    "message": "Startup in progress",
                    "startup_in_progress": True,
                    "details": {"phase": startup_phase}
                }
                if startup_progress is not None:
                    detail["details"]["progress"] = startup_progress
                
                return _create_error_response(503, detail)
            else:
                # startup_complete is False but not in progress - treat as not started
                return _create_error_response(503, {
                    "status": "unhealthy",
                    "message": "Startup not complete",
                    "startup_complete": False
                })
        elif startup_complete is None:
            # No startup state set - assume startup not complete
            return _create_error_response(503, {
                "status": "unhealthy",
                "message": "Startup state unknown",
                "startup_complete": None
            })
    
    # Startup is complete, proceed with normal health check
    health_status = await health_interface.get_health_status(HealthLevel.BASIC)
    
    # Add version-specific fields based on requested API version
    if requested_version in ["1.0", "2024-08-01"]:
        health_status["version_info"] = {
            "api_version": requested_version,
            "service_version": "1.0.0",
            "supported_versions": ["current", "1.0", "2024-08-01"]
        }
    
    return health_status


# Add separate endpoint for /health (without trailing slash) to handle direct requests
@router.get("", include_in_schema=False)  # This will match /health exactly
async def health_no_slash(request: Request, response: Response) -> Dict[str, Any]:
    """
    Health check endpoint without trailing slash - redirects to main health endpoint logic.
    """
    return await health(request, response)

@router.get("/live")
@router.options("/live")
async def live(request: Request) -> Dict[str, Any]:
    """
    Liveness probe to check if the application is running.
    """
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return {"status": "ok", "message": "CORS preflight"}
    
    return response_builder.create_basic_response("healthy")

async def _check_postgres_connection(db: AsyncSession) -> None:
    """Check Postgres database connection."""
    config = unified_config_manager.get_config()
    database_url = getattr(config, 'database_url', '')
    if "mock" not in database_url.lower():
        result = await db.execute(text("SELECT 1"))
        result.scalar_one_or_none()

async def _check_clickhouse_connection() -> None:
    """Check ClickHouse database connection (non-blocking for readiness)."""
    config = unified_config_manager.get_config()
    skip_clickhouse = getattr(config, 'skip_clickhouse_init', False)
    if skip_clickhouse:
        logger.debug("ClickHouse check skipped - skip_clickhouse_init=True")
        return
    
    # In development, make ClickHouse optional for readiness
    if config.environment in ["development", "staging"]:
        try:
            await asyncio.wait_for(_perform_clickhouse_check(), timeout=2.0)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"ClickHouse check failed (non-critical in {config.environment}): {e}")
            return  # Don't fail readiness for ClickHouse in development
    else:
        await _perform_clickhouse_check()

async def _perform_clickhouse_check() -> None:
    """Perform the actual ClickHouse connection check."""
    try:
        from netra_backend.app.services.clickhouse_service import clickhouse_service
        await clickhouse_service.execute_health_check()
    except Exception as e:
        await _handle_clickhouse_error(e)

async def _handle_clickhouse_error(error: Exception) -> None:
    """Handle ClickHouse connection errors."""
    logger.warning(f"ClickHouse check failed (non-critical): {error}")
    config = unified_config_manager.get_config()
    if config.environment in ["staging", "development"]:
        logger.info(f"Ignoring ClickHouse failure in {config.environment} environment")
    else:
        raise

async def _check_database_connection(db: AsyncSession) -> None:
    """Check database connection using dependency injection."""
    await _check_postgres_connection(db)
    await _check_clickhouse_connection()

async def _check_readiness_status(db: AsyncSession) -> Dict[str, Any]:
    """Check application readiness including core database connectivity."""
    try:
        # Run all checks concurrently with shorter timeouts for faster response
        postgres_task = asyncio.create_task(_check_postgres_connection(db))
        clickhouse_task = asyncio.create_task(_check_clickhouse_connection())
        health_task = asyncio.create_task(health_interface.get_health_status(HealthLevel.BASIC))
        
        # Wait for core PostgreSQL check (required)
        try:
            await asyncio.wait_for(postgres_task, timeout=3.0)  # Reduced from 5.0s
            postgres_status = "connected"
        except (asyncio.TimeoutError, Exception) as e:
            logger.error(f"PostgreSQL readiness check failed: {e}")
            raise HTTPException(status_code=503, detail="Core database unavailable")
        
        # Wait for other checks with shorter timeouts (optional)
        clickhouse_status = "unavailable"
        try:
            await asyncio.wait_for(clickhouse_task, timeout=2.0)  # Reduced from 3.0s
            clickhouse_status = "connected"
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"ClickHouse not available during readiness (non-critical): {e}")
        
        health_status = {}
        try:
            health_status = await asyncio.wait_for(health_task, timeout=1.5)  # Reduced from 2.0s
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"Health interface check failed (non-critical): {e}")
            health_status = {"status": "healthy", "message": "Basic health check bypassed"}
        
        # Return ready if core services are available
        return {
            "status": "ready", 
            "service": "netra-ai-platform", 
            "timestamp": time.time(),
            "core_db": postgres_status,
            "clickhouse_db": clickhouse_status,
            "details": health_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service readiness check failed")

@router.get("/ready")
@router.options("/ready")
async def ready(request: Request) -> Dict[str, Any]:
    """Readiness probe to check if the application is ready to serve requests."""
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return {"status": "ok", "message": "CORS preflight"}
    
    try:
        # Check startup state first - readiness requires startup completion
        app_state = getattr(request.app, 'state', None)
        if app_state:
            startup_complete = getattr(app_state, 'startup_complete', None)
            
            # Handle case where startup_complete is a MagicMock (test environment)
            if hasattr(startup_complete, '_mock_name'):
                startup_complete = None
            
            if startup_complete is False:
                # Not ready during startup
                startup_in_progress = getattr(app_state, 'startup_in_progress', False)
                
                # Handle MagicMock objects for test environment
                if hasattr(startup_in_progress, '_mock_name'):
                    startup_in_progress = False
                
                if startup_in_progress:
                    return _create_error_response(503, {
                        "status": "unhealthy",
                        "message": "Startup in progress - not ready",
                        "startup_in_progress": True
                    })
                else:
                    return _create_error_response(503, {
                        "status": "unhealthy",
                        "message": "Startup not complete - not ready",
                        "startup_complete": False
                    })
            elif startup_complete is None:
                return _create_error_response(503, {
                    "status": "unhealthy",
                    "message": "Startup state unknown - not ready",
                    "startup_complete": None
                })
        
        # Only try to get database dependency after startup state check passes
        try:
            # Use async for to properly handle session lifecycle
            async for db in get_db_dependency():
                try:
                    # Wrap the entire readiness check with timeout to prevent probe timeout
                    result = await asyncio.wait_for(_check_readiness_status(db), timeout=8.0)
                    return result
                except asyncio.TimeoutError:
                    logger.error("Readiness check exceeded 8 second timeout")
                    return _create_error_response(503, {
                        "status": "unhealthy",
                        "message": "Readiness check timeout",
                        "timeout_seconds": 8
                    })
                except Exception as check_error:
                    logger.error(f"Readiness check failed: {check_error}")
                    raise check_error
        except HTTPException:
            raise
        except Exception as db_error:
            logger.error(f"Database dependency failed during readiness: {db_error}")
            return _create_error_response(503, {
                "status": "unhealthy",
                "message": "Database dependency failed",
                "error": str(db_error)
            })
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
        # Initialize postgres through service pattern
        from netra_backend.app.db.postgres import initialize_postgres
        from netra_backend.app.db.postgres_core import async_engine
        from netra_backend.app.services.database_operations_service import (
            database_operations_service,
        )
        
        # Always get fresh reference to engine after ensuring initialization
        if async_engine is None:
            initialize_postgres()
            # Get fresh reference after initialization
            from netra_backend.app.db.postgres_core import async_engine as engine_ref
            if engine_ref is None:
                raise RuntimeError("Database engine not initialized after initialization")
            engine = engine_ref
        else:
            engine = async_engine
            
        return await SchemaValidationService.validate_schema(engine)
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
    from netra_backend.app.services.metrics.agent_metrics import agent_metrics_collector
    return agent_metrics_collector

def get_enhanced_health_monitor():
    """Lazy import for enhanced health monitor."""
    from netra_backend.app.core.system_health_monitor import system_health_monitor
    return system_health_monitor

def get_alert_manager():
    """Lazy import for alert manager."""
    from netra_backend.app.monitoring.alert_manager import alert_manager
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



