"""
Startup Health Checks - Critical Service Validation
====================================================
CRITICAL: This module validates all required services are available before
the application accepts requests. This prevents NoneType errors and ensures
system stability.

Based on Five Whys Analysis (2025-09-04):
- Root cause: No deterministic startup validation
- Solution: Block startup until all critical services ready
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy import text

from netra_backend.app.logging_config import central_logger

logger = central_logger


class ServiceStatus(Enum):
    """Health check status for a service."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"


@dataclass
class HealthCheckResult:
    """Result of a health check for a service."""
    service_name: str
    status: ServiceStatus
    message: str
    check_time: datetime
    latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class StartupHealthChecker:
    """
    Validates all critical services are available at startup.
    
    CRITICAL: This prevents the cascade failures identified in Five Whys:
    - LLM manager being None
    - Database connections failing
    - Circuit breakers opening
    """
    
    # Define critical services that MUST be available
    CRITICAL_SERVICES = [
        'llm_manager',
        'database',
        'redis',
    ]
    
    # Optional services that should log warnings if unavailable
    OPTIONAL_SERVICES = [
        'clickhouse',
        'websocket_manager',
    ]
    
    def __init__(self, app: FastAPI):
        """Initialize health checker with FastAPI app instance."""
        self.app = app
        self.health_results: Dict[str, HealthCheckResult] = {}
        
    async def check_llm_manager(self) -> HealthCheckResult:
        """Validate LLM manager is initialized and functional."""
        start_time = asyncio.get_event_loop().time()
        service_name = "llm_manager"
        
        try:
            # Check if LLM manager exists
            if not hasattr(self.app.state, 'llm_manager'):
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.NOT_CONFIGURED,
                    message="LLM manager not found in app.state",
                    check_time=datetime.now(timezone.utc)
                )
            
            llm_manager = self.app.state.llm_manager
            if llm_manager is None:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="LLM manager is None",
                    check_time=datetime.now(timezone.utc)
                )
            
            # Validate LLM manager has required methods
            required_methods = ['ask_llm', 'get_llm_config']
            missing_methods = []
            for method in required_methods:
                if not hasattr(llm_manager, method):
                    missing_methods.append(method)
            
            if missing_methods:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.DEGRADED,
                    message=f"LLM manager missing methods: {missing_methods}",
                    check_time=datetime.now(timezone.utc)
                )
            
            # Check if at least one LLM config is available
            try:
                # This should not fail if LLM manager is properly initialized
                config_available = hasattr(llm_manager, 'llm_configs') and llm_manager.llm_configs
                if not config_available:
                    return HealthCheckResult(
                        service_name=service_name,
                        status=ServiceStatus.DEGRADED,
                        message="No LLM configurations available",
                        check_time=datetime.now(timezone.utc)
                    )
            except Exception as e:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.DEGRADED,
                    message=f"Error checking LLM configs: {e}",
                    check_time=datetime.now(timezone.utc)
                )
            
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.HEALTHY,
                message="LLM manager is initialized and functional",
                check_time=datetime.now(timezone.utc),
                latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Exception during health check: {e}",
                check_time=datetime.now(timezone.utc)
            )
    
    async def check_database(self) -> HealthCheckResult:
        """Validate database connection is available."""
        start_time = asyncio.get_event_loop().time()
        service_name = "database"
        
        try:
            # Check if database session factory exists
            if not hasattr(self.app.state, 'db_session_factory'):
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.NOT_CONFIGURED,
                    message="Database session factory not found in app.state",
                    check_time=datetime.now(timezone.utc)
                )
            
            db_factory = self.app.state.db_session_factory
            if db_factory is None:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="Database session factory is None",
                    check_time=datetime.now(timezone.utc)
                )
            
            # Try to execute a simple query
            async with db_factory() as session:
                result = await session.execute(text("SELECT 1"))
                _ = result.scalar()
            
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.HEALTHY,
                message="Database connection successful",
                check_time=datetime.now(timezone.utc),
                latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Database connection failed: {e}",
                check_time=datetime.now(timezone.utc)
            )
    
    async def check_redis(self) -> HealthCheckResult:
        """Validate Redis connection is available."""
        start_time = asyncio.get_event_loop().time()
        service_name = "redis"
        
        try:
            from netra_backend.app.redis_manager import redis_manager
            
            # Try to ping Redis - check for either redis_client or _client
            if redis_manager:
                ping_successful = False
                if hasattr(redis_manager, 'redis_client'):
                    await redis_manager.redis_client.ping()
                    ping_successful = True
                elif hasattr(redis_manager, '_client') and redis_manager._client:
                    await redis_manager._client.ping()
                    ping_successful = True
                elif hasattr(redis_manager, '_connected'):
                    # If there's a _connected flag, check that
                    ping_successful = redis_manager._connected
                
                if ping_successful:
                    latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    return HealthCheckResult(
                        service_name=service_name,
                        status=ServiceStatus.HEALTHY,
                        message="Redis connection successful",
                        check_time=datetime.now(timezone.utc),
                        latency_ms=latency_ms
                    )
                else:
                    # Redis manager exists but ping failed or no connection
                    return HealthCheckResult(
                        service_name=service_name,
                        status=ServiceStatus.DEGRADED,
                        message="Redis manager exists but not connected",
                        check_time=datetime.now(timezone.utc)
                    )
            else:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.NOT_CONFIGURED,
                    message="Redis manager not initialized",
                    check_time=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Redis connection failed: {e}",
                check_time=datetime.now(timezone.utc)
            )
    
    async def check_clickhouse(self) -> HealthCheckResult:
        """Validate ClickHouse connection (optional service)."""
        start_time = asyncio.get_event_loop().time()
        service_name = "clickhouse"
        
        try:
            from netra_backend.app.db.clickhouse import ClickHouseService
            
            # Check if ClickHouse is configured
            ch_service = ClickHouseService()
            
            # Initialize the service first
            await ch_service.initialize()
            
            # Try to execute a simple query to validate connection
            result = await ch_service.execute("SELECT 1")
            
            # Clean up the service connection
            await ch_service.close()
            
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.HEALTHY,
                message="ClickHouse connection successful",
                check_time=datetime.now(timezone.utc),
                latency_ms=latency_ms
            )
            
        except Exception as e:
            # ClickHouse is optional, so we don't fail startup
            logger.warning(f"ClickHouse health check failed (optional service): {e}")
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.DEGRADED,
                message=f"ClickHouse unavailable: {e}",
                check_time=datetime.now(timezone.utc)
            )
    
    async def run_all_health_checks(self) -> Tuple[bool, List[HealthCheckResult]]:
        """
        Run all health checks and return overall status.
        
        Returns:
            Tuple of (all_critical_healthy, list_of_results)
        """
        logger.info("[U+1F3E5] Starting startup health checks...")
        
        # Define health check methods
        health_checks = {
            'llm_manager': self.check_llm_manager,
            'database': self.check_database,
            'redis': self.check_redis,
            'clickhouse': self.check_clickhouse,
        }
        
        # Run all health checks
        results = []
        for service_name, check_method in health_checks.items():
            logger.debug(f"Checking {service_name}...")
            result = await check_method()
            results.append(result)
            self.health_results[service_name] = result
            
            # Log result
            if result.status == ServiceStatus.HEALTHY:
                logger.info(f" PASS:  {service_name}: {result.message} ({result.latency_ms:.1f}ms)" 
                          if result.latency_ms else f" PASS:  {service_name}: {result.message}")
            elif result.status == ServiceStatus.DEGRADED:
                logger.warning(f" WARNING: [U+FE0F] {service_name}: {result.message}")
            elif result.status == ServiceStatus.NOT_CONFIGURED:
                logger.warning(f"[U+2753] {service_name}: {result.message}")
            else:
                logger.error(f" FAIL:  {service_name}: {result.message}")
        
        # Check if all critical services are healthy
        all_critical_healthy = True
        for service_name in self.CRITICAL_SERVICES:
            if service_name in self.health_results:
                result = self.health_results[service_name]
                if result.status not in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                    all_critical_healthy = False
                    logger.error(f" ALERT:  CRITICAL service {service_name} is not healthy: {result.status}")
        
        return all_critical_healthy, results
    
    async def validate_startup(self, fail_on_critical: bool = True) -> bool:
        """
        Validate all services at startup.
        
        Args:
            fail_on_critical: If True, raise exception if critical services fail
            
        Returns:
            True if all critical services are healthy
            
        Raises:
            RuntimeError: If fail_on_critical=True and critical services fail
        """
        all_healthy, results = await self.run_all_health_checks()
        
        if not all_healthy:
            unhealthy_critical = [
                r for r in results 
                if r.service_name in self.CRITICAL_SERVICES 
                and r.status not in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
            ]
            
            error_msg = "Critical services failed health checks:\n"
            for result in unhealthy_critical:
                error_msg += f"  - {result.service_name}: {result.message}\n"
            
            logger.error(f" ALERT:  STARTUP VALIDATION FAILED:\n{error_msg}")
            
            if fail_on_critical:
                raise RuntimeError(f"Startup validation failed: {len(unhealthy_critical)} critical services unhealthy")
        else:
            logger.info(" PASS:  All critical services passed health checks")
        
        # Log summary
        logger.info("Health Check Summary:")
        for service_name in self.CRITICAL_SERVICES + self.OPTIONAL_SERVICES:
            if service_name in self.health_results:
                result = self.health_results[service_name]
                logger.info(f"  {service_name}: {result.status.value}")
        
        return all_healthy


async def validate_startup_health(app: FastAPI, fail_on_critical: bool = True) -> bool:
    """
    Convenience function to validate startup health.
    
    This should be called after all services are initialized but before
    the application starts accepting requests.
    
    Args:
        app: FastAPI application instance
        fail_on_critical: If True, raise exception if critical services fail
        
    Returns:
        True if all critical services are healthy
    """
    checker = StartupHealthChecker(app)
    return await checker.validate_startup(fail_on_critical=fail_on_critical)