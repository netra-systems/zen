"""
Health Check Endpoints for Database Connectivity
===============================================

Comprehensive health check endpoints for all database services:
- PostgreSQL connectivity and performance
- Redis connectivity and memory status  
- ClickHouse connectivity and query performance
- Overall system health aggregation

CRITICAL MISSION: Ensure staging database connectivity monitoring
- Real-time connection validation
- Performance metrics
- Error detection and alerting
- Business continuity assurance

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Early detection of infrastructure issues
- Value Impact: Prevents service outages and data loss
- Strategic Impact: Foundation for monitoring and alerting
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from netra_backend.app.core.config import get_config
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder
from netra_backend.app.db.database_manager import get_database_manager

logger = logging.getLogger(__name__)

# Health check router
health_router = APIRouter(prefix="/health", tags=["health"])


class DatabaseHealthStatus(BaseModel):
    """Database health status model."""
    service: str
    status: str  # healthy, degraded, failed, not_configured
    connected: bool
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    details: Dict[str, Any] = {}
    checked_at: datetime


class SystemHealthStatus(BaseModel):
    """Overall system health status model."""
    overall_status: str  # healthy, degraded, failed
    services: Dict[str, DatabaseHealthStatus]
    checked_at: datetime
    environment: str
    uptime_seconds: Optional[float] = None


class HealthCheckManager:
    """
    Centralized health check manager for all database services.
    
    Provides comprehensive health monitoring with caching, alerting,
    and performance tracking for production reliability.
    """
    
    def __init__(self):
        """Initialize health check manager."""
        self.config = get_config()
        self.env = get_env()
        self.environment = self.env.get_environment_name()
        
        # Health check caching
        self._cache: Dict[str, DatabaseHealthStatus] = {}
        self._cache_ttl = 30  # 30 seconds cache
        self._last_check: Dict[str, datetime] = {}
        
        # Performance tracking
        self._response_times: Dict[str, List[float]] = {
            'postgresql': [],
            'redis': [],
            'clickhouse': []
        }
        self._max_samples = 100  # Keep last 100 samples
        
        logger.info(f"HealthCheckManager initialized for {self.environment} environment")
    
    async def check_postgresql_health(self, force_check: bool = False) -> DatabaseHealthStatus:
        """Check PostgreSQL database health."""
        service_name = "postgresql"
        
        # Check cache first
        if not force_check and self._is_cached(service_name):
            return self._cache[service_name]
        
        start_time = time.time()
        health_status = DatabaseHealthStatus(
            service=service_name,
            status="unknown",
            connected=False,
            checked_at=datetime.utcnow()
        )
        
        try:
            # Get database manager
            db_manager = get_database_manager()
            
            # Test connection and basic query
            connection_start = time.time()
            health_result = await db_manager.health_check()
            response_time = (time.time() - connection_start) * 1000
            
            # Update metrics
            self._update_response_time(service_name, response_time)
            
            if health_result.get("status") == "healthy":
                health_status.status = "healthy"
                health_status.connected = True
                health_status.response_time_ms = round(response_time, 2)
                health_status.details = {
                    "engine": health_result.get("engine", "primary"),
                    "connection_pool": "active",
                    "avg_response_time": round(self._get_avg_response_time(service_name), 2)
                }
                
                # Check for performance degradation
                avg_response_time = self._get_avg_response_time(service_name)
                if avg_response_time > 1000:  # > 1 second
                    health_status.status = "degraded"
                    health_status.details["warning"] = f"High response time: {avg_response_time:.2f}ms"
                    
            else:
                health_status.status = "failed" 
                health_status.error = health_result.get("error", "Unknown database error")
                health_status.details = {"error_details": health_result}
                
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            health_status.status = "failed"
            health_status.error = str(e)
            health_status.details = {"exception_type": type(e).__name__}
        
        # Cache result
        self._cache[service_name] = health_status
        self._last_check[service_name] = datetime.utcnow()
        
        return health_status
    
    async def check_redis_health(self, force_check: bool = False) -> DatabaseHealthStatus:
        """Check Redis connectivity and performance."""
        service_name = "redis"
        
        # Check cache first
        if not force_check and self._is_cached(service_name):
            return self._cache[service_name]
        
        health_status = DatabaseHealthStatus(
            service=service_name,
            status="unknown",
            connected=False,
            checked_at=datetime.utcnow()
        )
        
        try:
            # Get Redis configuration
            redis_host = self.env.get("REDIS_HOST", "")
            redis_port = self.env.get("REDIS_PORT", "6379")
            redis_password = self.env.get("REDIS_PASSWORD", "")
            redis_db = self.env.get("REDIS_DB", "0")
            redis_url = self.env.get("REDIS_URL", "")
            
            if not redis_host and not redis_url:
                health_status.status = "not_configured"
                health_status.details = {"message": "Redis not configured"}
                return health_status
            
            # Test Redis connection
            try:
                import redis.asyncio as redis
                
                # Create Redis client
                if redis_url:
                    client = redis.from_url(redis_url, decode_responses=True)
                else:
                    client = await get_redis_client()  # MIGRATED: was redis.Redis(
                        host=redis_host,
                        port=int(redis_port),
                        password=redis_password if redis_password else None,
                        db=int(redis_db),
                        decode_responses=True
                    )
                
                connection_start = time.time()
                
                # Test ping and get info
                await asyncio.wait_for(client.ping(), timeout=5.0)
                info = await client.info()
                
                response_time = (time.time() - connection_start) * 1000
                self._update_response_time(service_name, response_time)
                
                await client.aclose()
                
                health_status.status = "healthy"
                health_status.connected = True
                health_status.response_time_ms = round(response_time, 2)
                health_status.details = {
                    "redis_version": info.get('redis_version', 'unknown'),
                    "memory_usage": info.get('used_memory_human', 'unknown'),
                    "connected_clients": info.get('connected_clients', 0),
                    "avg_response_time": round(self._get_avg_response_time(service_name), 2)
                }
                
                # Check memory usage
                used_memory = info.get('used_memory', 0)
                max_memory = info.get('maxmemory', 0)
                if max_memory > 0 and used_memory / max_memory > 0.8:
                    health_status.status = "degraded"
                    health_status.details["warning"] = "High memory usage"
                
            except ImportError:
                health_status.status = "failed"
                health_status.error = "redis-py package not available"
                health_status.details = {"dependency_missing": "redis[asyncio]"}
            
        except asyncio.TimeoutError:
            health_status.status = "failed"
            health_status.error = "Connection timeout (5s)"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status.status = "failed"
            health_status.error = str(e)
            health_status.details = {"exception_type": type(e).__name__}
        
        # Cache result
        self._cache[service_name] = health_status
        self._last_check[service_name] = datetime.utcnow()
        
        return health_status
    
    async def check_clickhouse_health(self, force_check: bool = False) -> DatabaseHealthStatus:
        """Check ClickHouse connectivity and query performance."""
        service_name = "clickhouse"
        
        # Check cache first
        if not force_check and self._is_cached(service_name):
            return self._cache[service_name]
        
        health_status = DatabaseHealthStatus(
            service=service_name,
            status="unknown",
            connected=False,
            checked_at=datetime.utcnow()
        )
        
        try:
            # Get ClickHouse configuration
            clickhouse_url = self.env.get("CLICKHOUSE_URL", "")
            clickhouse_host = self.env.get("CLICKHOUSE_HOST", "")
            clickhouse_required = self.env.get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
            
            if not clickhouse_host and not clickhouse_url:
                if clickhouse_required:
                    health_status.status = "failed"
                    health_status.error = "ClickHouse required but not configured"
                else:
                    health_status.status = "not_configured"
                    health_status.details = {"message": "ClickHouse not configured (optional)"}
                return health_status
            
            # Test ClickHouse connection
            try:
                import aiohttp
                
                # Build connection URL if not provided
                if not clickhouse_url:
                    clickhouse_port = self.env.get("CLICKHOUSE_PORT", "8123")
                    clickhouse_user = self.env.get("CLICKHOUSE_USER", "default")
                    clickhouse_password = self.env.get("CLICKHOUSE_PASSWORD", "")
                    clickhouse_secure = self.env.get("CLICKHOUSE_SECURE", "false").lower() == "true"
                    
                    protocol = "https" if clickhouse_secure else "http"
                    auth_part = f"{clickhouse_user}:{clickhouse_password}@" if clickhouse_password else f"{clickhouse_user}@"
                    clickhouse_url = f"{protocol}://{auth_part}{clickhouse_host}:{clickhouse_port}/"
                
                connection_start = time.time()
                
                async with aiohttp.ClientSession() as session:
                    # Test with simple query
                    query_url = clickhouse_url.rstrip('/') + "/?query=SELECT%20version()"
                    
                    async with session.get(query_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_time = (time.time() - connection_start) * 1000
                        self._update_response_time(service_name, response_time)
                        
                        if response.status == 200:
                            version_text = await response.text()
                            
                            health_status.status = "healthy"
                            health_status.connected = True
                            health_status.response_time_ms = round(response_time, 2)
                            health_status.details = {
                                "clickhouse_version": version_text.strip(),
                                "http_status": response.status,
                                "avg_response_time": round(self._get_avg_response_time(service_name), 2)
                            }
                            
                            # Check for performance degradation
                            if response_time > 5000:  # > 5 seconds
                                health_status.status = "degraded"
                                health_status.details["warning"] = f"High response time: {response_time:.2f}ms"
                        else:
                            error_text = await response.text()
                            health_status.status = "failed"
                            health_status.error = f"HTTP {response.status}: {error_text[:200]}"
                            health_status.details = {"http_status": response.status}
            
            except ImportError:
                health_status.status = "failed"
                health_status.error = "aiohttp package not available"
                health_status.details = {"dependency_missing": "aiohttp"}
            
        except asyncio.TimeoutError:
            health_status.status = "failed"
            health_status.error = "Connection timeout (10s)"
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            health_status.status = "failed"
            health_status.error = str(e)
            health_status.details = {"exception_type": type(e).__name__}
        
        # Cache result
        self._cache[service_name] = health_status
        self._last_check[service_name] = datetime.utcnow()
        
        return health_status
    
    async def check_overall_health(self, force_check: bool = False) -> SystemHealthStatus:
        """Check overall system health across all services."""
        # Run all health checks in parallel
        postgresql_task = asyncio.create_task(self.check_postgresql_health(force_check))
        redis_task = asyncio.create_task(self.check_redis_health(force_check))
        clickhouse_task = asyncio.create_task(self.check_clickhouse_health(force_check))
        
        # Wait for all checks to complete
        postgresql_health = await postgresql_task
        redis_health = await redis_task
        clickhouse_health = await clickhouse_task
        
        # Aggregate results
        services = {
            "postgresql": postgresql_health,
            "redis": redis_health,
            "clickhouse": clickhouse_health
        }
        
        # Determine overall status
        statuses = [health.status for health in services.values()]
        
        if "failed" in statuses:
            # Check if critical services are failing
            if postgresql_health.status == "failed":
                overall_status = "failed"  # PostgreSQL is critical
            elif redis_health.status == "failed" and self.env.get("REDIS_REQUIRED", "false").lower() == "true":
                overall_status = "failed"  # Redis is critical if required
            elif clickhouse_health.status == "failed" and self.env.get("CLICKHOUSE_REQUIRED", "false").lower() == "true":
                overall_status = "failed"  # ClickHouse is critical if required
            else:
                overall_status = "degraded"  # Non-critical service failures
        elif "degraded" in statuses:
            overall_status = "degraded"
        elif all(status in ["healthy", "not_configured"] for status in statuses):
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        return SystemHealthStatus(
            overall_status=overall_status,
            services=services,
            checked_at=datetime.utcnow(),
            environment=self.environment,
            uptime_seconds=None  # Could add application uptime tracking
        )
    
    def _is_cached(self, service_name: str) -> bool:
        """Check if service health is cached and still valid."""
        if service_name not in self._cache or service_name not in self._last_check:
            return False
        
        cache_age = (datetime.utcnow() - self._last_check[service_name]).total_seconds()
        return cache_age < self._cache_ttl
    
    def _update_response_time(self, service_name: str, response_time: float) -> None:
        """Update response time metrics for a service."""
        if service_name not in self._response_times:
            self._response_times[service_name] = []
        
        self._response_times[service_name].append(response_time)
        
        # Keep only recent samples
        if len(self._response_times[service_name]) > self._max_samples:
            self._response_times[service_name] = self._response_times[service_name][-self._max_samples:]
    
    def _get_avg_response_time(self, service_name: str) -> float:
        """Get average response time for a service."""
        if service_name not in self._response_times or not self._response_times[service_name]:
            return 0.0
        
        times = self._response_times[service_name]
        return sum(times) / len(times)
    
    def clear_cache(self) -> None:
        """Clear health check cache."""
        self._cache.clear()
        self._last_check.clear()
        logger.info("Health check cache cleared")


# Global health check manager
health_manager = HealthCheckManager()


# Health check endpoints
@health_router.get("/", response_model=SystemHealthStatus)
async def get_system_health(
    force: bool = Query(False, description="Force fresh health checks, bypass cache")
) -> SystemHealthStatus:
    """
    Get overall system health status.
    
    Returns comprehensive health information for all database services
    including response times, connection status, and performance metrics.
    """
    try:
        return await health_manager.check_overall_health(force_check=force)
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@health_router.get("/database", response_model=DatabaseHealthStatus)
async def get_database_health(
    force: bool = Query(False, description="Force fresh health check, bypass cache")
) -> DatabaseHealthStatus:
    """
    Get PostgreSQL database health status.
    
    Returns detailed information about database connectivity,
    response times, and any performance issues.
    """
    try:
        return await health_manager.check_postgresql_health(force_check=force)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")


@health_router.get("/redis", response_model=DatabaseHealthStatus)
async def get_redis_health(
    force: bool = Query(False, description="Force fresh health check, bypass cache")
) -> DatabaseHealthStatus:
    """
    Get Redis health status.
    
    Returns information about Redis connectivity, memory usage,
    and performance metrics.
    """
    try:
        return await health_manager.check_redis_health(force_check=force)
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Redis health check failed: {str(e)}")


@health_router.get("/clickhouse", response_model=DatabaseHealthStatus)
async def get_clickhouse_health(
    force: bool = Query(False, description="Force fresh health check, bypass cache")
) -> DatabaseHealthStatus:
    """
    Get ClickHouse health status.
    
    Returns information about ClickHouse connectivity,
    query performance, and service availability.
    """
    try:
        return await health_manager.check_clickhouse_health(force_check=force)
    except Exception as e:
        logger.error(f"ClickHouse health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"ClickHouse health check failed: {str(e)}")


@health_router.get("/config")
async def get_health_config() -> Dict[str, Any]:
    """
    Get health check configuration and diagnostics.
    
    Returns information about the health check system itself,
    cache status, and configuration details.
    """
    try:
        env_dict = health_manager.env.as_dict()
        
        # Build configuration summary (mask sensitive values)
        config_summary = {
            "environment": health_manager.environment,
            "cache_ttl_seconds": health_manager._cache_ttl,
            "max_response_time_samples": health_manager._max_samples,
            "services_configured": {
                "postgresql": bool(env_dict.get("POSTGRES_HOST")),
                "redis": bool(env_dict.get("REDIS_HOST") or env_dict.get("REDIS_URL")),
                "clickhouse": bool(env_dict.get("CLICKHOUSE_HOST") or env_dict.get("CLICKHOUSE_URL"))
            },
            "cache_status": {
                "cached_services": list(health_manager._cache.keys()),
                "last_check_times": {
                    service: time.isoformat() for service, time in health_manager._last_check.items()
                }
            },
            "performance_samples": {
                service: len(times) for service, times in health_manager._response_times.items()
            }
        }
        
        # Add database URL builder diagnostics
        try:
            url_builder = DatabaseURLBuilder(env_dict)
            config_summary["database_url_builder"] = {
                "environment": url_builder.environment,
                "has_cloud_sql": url_builder.cloud_sql.is_cloud_sql,
                "has_tcp_config": url_builder.tcp.has_config,
                "validation_status": url_builder.validate()[0]
            }
        except Exception as e:
            config_summary["database_url_builder_error"] = str(e)
        
        return config_summary
        
    except Exception as e:
        logger.error(f"Health config check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Config check failed: {str(e)}")


@health_router.post("/cache/clear")
async def clear_health_cache() -> Dict[str, str]:
    """
    Clear health check cache.
    
    Forces fresh health checks on next request.
    Useful for debugging or after configuration changes.
    """
    try:
        health_manager.clear_cache()
        return {"message": "Health check cache cleared successfully"}
    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


# Startup validation endpoint
@health_router.get("/startup")
async def startup_validation() -> Dict[str, Any]:
    """
    Comprehensive startup validation.
    
    Performs thorough health checks and configuration validation
    suitable for application startup verification.
    """
    try:
        # Force fresh checks for startup
        system_health = await health_manager.check_overall_health(force_check=True)
        
        # Additional startup-specific checks
        startup_result = {
            "system_health": system_health,
            "startup_time": datetime.utcnow().isoformat(),
            "critical_services_status": {},
            "startup_ready": False
        }
        
        # Check critical services
        postgresql_healthy = system_health.services["postgresql"].status in ["healthy", "degraded"]
        startup_result["critical_services_status"]["postgresql"] = postgresql_healthy
        
        redis_required = health_manager.env.get("REDIS_REQUIRED", "false").lower() == "true"
        if redis_required:
            redis_healthy = system_health.services["redis"].status in ["healthy", "degraded"]
            startup_result["critical_services_status"]["redis"] = redis_healthy
        else:
            startup_result["critical_services_status"]["redis"] = True  # Not required
        
        clickhouse_required = health_manager.env.get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
        if clickhouse_required:
            clickhouse_healthy = system_health.services["clickhouse"].status in ["healthy", "degraded"]
            startup_result["critical_services_status"]["clickhouse"] = clickhouse_healthy
        else:
            startup_result["critical_services_status"]["clickhouse"] = True  # Not required
        
        # Determine startup readiness
        startup_result["startup_ready"] = all(startup_result["critical_services_status"].values())
        
        return startup_result
        
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Startup validation failed: {str(e)}")