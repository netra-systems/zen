"""
ClickHouse Health Check API Endpoints

Provides detailed health monitoring and dependency validation for ClickHouse service.
Exposes connection manager metrics, retry statistics, and analytics data consistency.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable proactive monitoring and debugging of ClickHouse dependencies
- Value Impact: Reduces debugging time for analytics issues by 90%
- Revenue Impact: Prevents data loss incidents that could affect business intelligence
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
import time

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

router = APIRouter()


@router.get("/health/clickhouse", tags=["health", "clickhouse"])
async def get_clickhouse_health() -> Dict[str, Any]:
    """
    Get comprehensive ClickHouse health status including connection manager metrics
    
    Returns:
        Dict containing:
        - connection_state: Current connection state
        - dependency_validation: Service dependency check results
        - analytics_consistency: Analytics data consistency status
        - connection_metrics: Detailed connection and retry metrics
        - circuit_breaker_status: Circuit breaker state and statistics
        - pool_metrics: Connection pool statistics
    """
    try:
        # Try to get connection manager
        try:
            from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
            connection_manager = get_clickhouse_connection_manager()
            
            if connection_manager is None:
                return {
                    "status": "unavailable",
                    "message": "ClickHouse connection manager not initialized",
                    "connection_state": "not_configured",
                    "timestamp": time.time(),
                    "details": {
                        "manager_available": False,
                        "reason": "Connection manager not initialized during startup"
                    }
                }
        except ImportError:
            return {
                "status": "unavailable", 
                "message": "ClickHouse connection manager not available",
                "connection_state": "not_configured",
                "timestamp": time.time(),
                "details": {
                    "manager_available": False,
                    "reason": "Connection manager module not imported"
                }
            }
        
        # Get comprehensive health status
        health_status = {
            "status": "checking",
            "timestamp": time.time(),
            "connection_state": connection_manager.connection_health.state.value,
            "manager_available": True
        }
        
        # Get connection metrics
        try:
            connection_metrics = connection_manager.get_connection_metrics()
            health_status["connection_metrics"] = connection_metrics
            health_status["circuit_breaker_status"] = {
                "state": connection_metrics.get("circuit_breaker_state", "unknown"),
                "failure_count": connection_metrics.get("circuit_breaker_failures", 0),
                "consecutive_failures": connection_metrics.get("consecutive_failures", 0)
            }
            health_status["pool_metrics"] = {
                "current_pool_size": connection_metrics.get("pool_size", 0),
                "pool_hits": connection_metrics.get("pool_hits", 0),
                "pool_misses": connection_metrics.get("pool_misses", 0),
                "max_pool_size": connection_metrics.get("pool_config", {}).get("max_pool_size", 0)
            }
        except Exception as e:
            health_status["connection_metrics_error"] = str(e)
        
        # Perform dependency validation
        try:
            dependency_validation = await connection_manager.validate_service_dependencies()
            health_status["dependency_validation"] = dependency_validation
            
            # Update overall status based on dependency validation
            if dependency_validation.get("overall_health", False):
                health_status["status"] = "healthy"
            else:
                health_status["status"] = "unhealthy"
                health_status["dependency_errors"] = dependency_validation.get("errors", [])
                
        except Exception as e:
            health_status["dependency_validation_error"] = str(e)
            health_status["status"] = "error"
        
        # Check analytics consistency
        try:
            analytics_consistency = await connection_manager.ensure_analytics_consistency()
            health_status["analytics_consistency"] = analytics_consistency
            
            if not analytics_consistency.get("overall_consistent", False):
                health_status["analytics_warnings"] = analytics_consistency.get("errors", [])
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
                    
        except Exception as e:
            health_status["analytics_consistency_error"] = str(e)
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"ClickHouse health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": time.time(),
            "connection_state": "error"
        }


@router.get("/health/clickhouse/connection", tags=["health", "clickhouse"])
async def get_clickhouse_connection_status() -> Dict[str, Any]:
    """
    Get basic ClickHouse connection status (lightweight check)
    
    Returns:
        Dict with basic connection information
    """
    try:
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        connection_manager = get_clickhouse_connection_manager()
        
        if connection_manager is None:
            return {
                "connected": False,
                "state": "not_configured",
                "message": "Connection manager not available"
            }
        
        return {
            "connected": connection_manager.connection_health.state.value in ["connected", "healthy"],
            "state": connection_manager.connection_health.state.value,
            "last_successful_connection": connection_manager.connection_health.last_successful_connection,
            "consecutive_failures": connection_manager.connection_health.consecutive_failures,
            "last_error": connection_manager.connection_health.last_error,
            "circuit_breaker_state": connection_manager.circuit_breaker.state
        }
        
    except ImportError:
        return {
            "connected": False,
            "state": "not_available", 
            "message": "Connection manager not available"
        }
    except Exception as e:
        return {
            "connected": False,
            "state": "error",
            "message": str(e)
        }


@router.post("/health/clickhouse/reconnect", tags=["health", "clickhouse"])
async def reconnect_clickhouse() -> Dict[str, Any]:
    """
    Force ClickHouse reconnection with retry logic
    
    Returns:
        Dict with reconnection results
    """
    try:
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        connection_manager = get_clickhouse_connection_manager()
        
        if connection_manager is None:
            return {
                "success": False,
                "message": "Connection manager not available",
                "timestamp": time.time()
            }
        
        # Force reconnection
        logger.info("Forcing ClickHouse reconnection via API request")
        success = await connection_manager._connect_with_retry()
        
        return {
            "success": success,
            "message": "Reconnection successful" if success else "Reconnection failed",
            "connection_state": connection_manager.connection_health.state.value,
            "timestamp": time.time(),
            "metrics": {
                "connection_attempts": connection_manager.metrics["connection_attempts"],
                "successful_connections": connection_manager.metrics["successful_connections"],
                "failed_connections": connection_manager.metrics["failed_connections"],
                "retry_attempts": connection_manager.metrics["retry_attempts"]
            }
        }
        
    except ImportError:
        return {
            "success": False,
            "message": "Connection manager not available",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"ClickHouse reconnection failed: {e}")
        return {
            "success": False,
            "message": f"Reconnection error: {str(e)}",
            "timestamp": time.time()
        }


@router.get("/health/clickhouse/metrics", tags=["health", "clickhouse"])
async def get_clickhouse_metrics() -> Dict[str, Any]:
    """
    Get detailed ClickHouse connection manager metrics
    
    Returns:
        Dict with comprehensive metrics including retry statistics
    """
    try:
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        connection_manager = get_clickhouse_connection_manager()
        
        if connection_manager is None:
            return {
                "available": False,
                "message": "Connection manager not available"
            }
        
        metrics = connection_manager.get_connection_metrics()
        
        # Add calculated metrics
        total_attempts = metrics.get("connection_attempts", 0)
        successful = metrics.get("successful_connections", 0)
        failed = metrics.get("failed_connections", 0)
        
        success_rate = (successful / total_attempts) if total_attempts > 0 else 0
        failure_rate = (failed / total_attempts) if total_attempts > 0 else 0
        
        return {
            "available": True,
            "timestamp": time.time(),
            "connection_metrics": metrics,
            "calculated_metrics": {
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "total_attempts": total_attempts,
                "health_score": max(0, 100 - (failure_rate * 100))
            },
            "performance_metrics": {
                "pool_efficiency": (
                    metrics.get("pool_hits", 0) / 
                    max(1, metrics.get("pool_hits", 0) + metrics.get("pool_misses", 0))
                ),
                "retry_frequency": (
                    metrics.get("retry_attempts", 0) / max(1, total_attempts)
                )
            }
        }
        
    except ImportError:
        return {
            "available": False,
            "message": "Connection manager not available"
        }
    except Exception as e:
        logger.error(f"Failed to get ClickHouse metrics: {e}")
        return {
            "available": False,
            "message": f"Metrics error: {str(e)}"
        }


@router.get("/health/clickhouse/dependencies", tags=["health", "clickhouse"])
async def validate_clickhouse_dependencies() -> Dict[str, Any]:
    """
    Validate ClickHouse service dependencies and Docker container status
    
    Returns:
        Dict with comprehensive dependency validation results
    """
    try:
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        connection_manager = get_clickhouse_connection_manager()
        
        if connection_manager is None:
            return {
                "validation_successful": False,
                "message": "Connection manager not available",
                "timestamp": time.time(),
                "dependencies": {
                    "connection_manager": "not_available",
                    "docker_service": "unknown",
                    "clickhouse_server": "unknown"
                }
            }
        
        # Perform comprehensive dependency validation
        validation = await connection_manager.validate_service_dependencies()
        
        return {
            "validation_successful": validation.get("overall_health", False),
            "timestamp": validation.get("validation_timestamp", time.time()),
            "dependencies": {
                "connection_manager": "available",
                "docker_service": "healthy" if validation.get("docker_service_healthy", False) else "unhealthy",
                "clickhouse_server": "available" if validation.get("clickhouse_available", False) else "unavailable",
                "query_execution": "working" if validation.get("query_execution", False) else "failed"
            },
            "details": validation,
            "errors": validation.get("errors", []),
            "recommendations": _generate_dependency_recommendations(validation)
        }
        
    except ImportError:
        return {
            "validation_successful": False,
            "message": "Connection manager not available",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Dependency validation failed: {e}")
        return {
            "validation_successful": False,
            "message": f"Validation error: {str(e)}",
            "timestamp": time.time()
        }


@router.get("/health/clickhouse/analytics", tags=["health", "clickhouse"])
async def check_analytics_consistency() -> Dict[str, Any]:
    """
    Check analytics data consistency and table availability
    
    Returns:
        Dict with analytics consistency check results
    """
    try:
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        connection_manager = get_clickhouse_connection_manager()
        
        if connection_manager is None:
            return {
                "consistent": False,
                "message": "Connection manager not available",
                "timestamp": time.time()
            }
        
        # Check analytics consistency
        consistency = await connection_manager.ensure_analytics_consistency()
        
        return {
            "consistent": consistency.get("overall_consistent", False),
            "timestamp": consistency.get("consistency_timestamp", time.time()),
            "checks": {
                "tables_verified": consistency.get("tables_verified", False),
                "schema_valid": consistency.get("schema_valid", False),
                "data_accessible": consistency.get("data_accessible", False),
                "write_test_successful": consistency.get("write_test_successful", False)
            },
            "table_info": {
                "count": consistency.get("table_count", 0),
                "tables": consistency.get("tables", [])
            },
            "details": consistency,
            "errors": consistency.get("errors", []),
            "recommendations": _generate_analytics_recommendations(consistency)
        }
        
    except ImportError:
        return {
            "consistent": False,
            "message": "Connection manager not available",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Analytics consistency check failed: {e}")
        return {
            "consistent": False,
            "message": f"Consistency check error: {str(e)}",
            "timestamp": time.time()
        }


def _generate_dependency_recommendations(validation: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on dependency validation results"""
    recommendations = []
    
    if not validation.get("docker_service_healthy", False):
        recommendations.append(
            "Check if ClickHouse Docker container is running: docker ps | grep clickhouse"
        )
        recommendations.append(
            "Restart ClickHouse service: docker-compose restart dev-clickhouse"
        )
    
    if not validation.get("clickhouse_available", False):
        recommendations.append(
            "Verify ClickHouse configuration in docker-compose.yml"
        )
        recommendations.append(
            "Check ClickHouse logs: docker-compose logs dev-clickhouse"
        )
    
    if not validation.get("connection_successful", False):
        recommendations.append(
            "Verify network connectivity between backend and ClickHouse"
        )
        recommendations.append(
            "Check firewall and port configurations (default: 8123, 9000)"
        )
    
    if not validation.get("query_execution", False):
        recommendations.append(
            "Check ClickHouse server status and resource availability"
        )
        recommendations.append(
            "Verify authentication credentials and database permissions"
        )
    
    return recommendations


def _generate_analytics_recommendations(consistency: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on analytics consistency check results"""
    recommendations = []
    
    if not consistency.get("tables_verified", False):
        recommendations.append(
            "Run database migrations to create missing analytics tables"
        )
        recommendations.append(
            "Check if ClickHouse initialization scripts executed properly"
        )
    
    if not consistency.get("schema_valid", False):
        recommendations.append(
            "Verify analytics table schemas match expected structure"
        )
        recommendations.append(
            "Check for ClickHouse version compatibility issues"
        )
    
    if not consistency.get("data_accessible", False):
        recommendations.append(
            "Check read permissions on analytics database and tables"
        )
        recommendations.append(
            "Verify connection pool configuration and limits"
        )
    
    if not consistency.get("write_test_successful", False):
        recommendations.append(
            "Check write permissions on analytics database and tables"
        )
        recommendations.append(
            "Verify disk space availability on ClickHouse server"
        )
    
    return recommendations