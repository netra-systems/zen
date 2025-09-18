"""
WebSocket Service Availability Manager - Issue #895 Implementation

This module provides comprehensive service availability detection and graceful degradation
for WebSocket connections to prevent 1011 errors when services are unavailable.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Reliability & User Experience
- Value Impact: Prevents WebSocket connection failures due to service unavailability
- Revenue Impact: Reduces user churn from connection failures, improves chat reliability

CRITICAL SERVICES MONITORED:
1. UnifiedAuthenticationService - Authentication for WebSocket connections
2. AgentWebSocketBridge - Agent communication channel
3. ThreadService - Message threading and persistence
4. Database connections (PostgreSQL/Redis) - Data persistence
5. Agent Supervisor - Agent orchestration

ISSUE #895 REQUIREMENTS:
- Health check mechanism for each service
- Circuit breaker pattern for failing services
- Graceful degradation when optional services are down
- Clear error messages for users when services are degraded
- Prevention of 1011 WebSocket errors
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from fastapi import FastAPI

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.config import get_config

logger = get_logger(__name__)


class ServiceType(Enum):
    """Types of services monitored for availability."""
    AUTHENTICATION = "authentication"
    AGENT_BRIDGE = "agent_bridge"
    THREAD_SERVICE = "thread_service"
    DATABASE_POSTGRES = "database_postgres"
    DATABASE_REDIS = "database_redis"
    AGENT_SUPERVISOR = "agent_supervisor"
    TOOL_CLASSES = "tool_classes"


class ServiceStatus(Enum):
    """Service availability status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealthInfo:
    """Health information for a service."""
    service_type: ServiceType
    status: ServiceStatus
    last_check: datetime
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    consecutive_failures: int = 0
    circuit_breaker_open: bool = False
    circuit_breaker_until: Optional[datetime] = None


@dataclass
class ServiceDependencyMap:
    """Maps service dependencies and criticality."""
    critical_services: Set[ServiceType] = field(default_factory=lambda: {
        ServiceType.AUTHENTICATION,
        ServiceType.DATABASE_POSTGRES
    })
    optional_services: Set[ServiceType] = field(default_factory=lambda: {
        ServiceType.AGENT_BRIDGE,
        ServiceType.THREAD_SERVICE,
        ServiceType.DATABASE_REDIS,
        ServiceType.AGENT_SUPERVISOR,
        ServiceType.TOOL_CLASSES
    })


class ServiceAvailabilityManager:
    """
    SSOT Service Availability Manager for WebSocket Infrastructure.

    Provides comprehensive health checking, circuit breaker functionality,
    and graceful degradation for WebSocket service dependencies.

    ISSUE #895 IMPLEMENTATION: Prevents 1011 errors by detecting service
    availability before WebSocket connection attempts.
    """

    def __init__(self, app: Optional[FastAPI] = None):
        """Initialize service availability manager.

        Args:
            app: FastAPI application instance for service access
        """
        self.app = app
        self.service_health: Dict[ServiceType, ServiceHealthInfo] = {}
        self.dependency_map = ServiceDependencyMap()
        self._last_global_check = datetime.now()
        self._health_check_interval = 30  # seconds
        self._circuit_breaker_timeout = 60  # seconds
        self._max_consecutive_failures = 3

        # Initialize health info for all services
        for service_type in ServiceType:
            self.service_health[service_type] = ServiceHealthInfo(
                service_type=service_type,
                status=ServiceStatus.UNKNOWN,
                last_check=datetime.now()
            )

    async def check_all_services(self) -> Dict[ServiceType, ServiceHealthInfo]:
        """
        Check health of all monitored services.

        Returns:
            Dictionary mapping service types to their health info
        """
        logger.info("Starting comprehensive service availability check")

        # Check each service type
        health_check_tasks = []
        for service_type in ServiceType:
            task = asyncio.create_task(
                self._check_service_health(service_type),
                name=f"health_check_{service_type.value}"
            )
            health_check_tasks.append(task)

        # Wait for all health checks to complete
        results = await asyncio.gather(*health_check_tasks, return_exceptions=True)

        # Process results and update health info
        for i, result in enumerate(results):
            service_type = list(ServiceType)[i]
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {service_type.value}: {result}")
                self._update_service_health(service_type, ServiceStatus.FAILED, str(result))
            else:
                status, error_msg, response_time = result
                self._update_service_health(service_type, status, error_msg, response_time)

        self._last_global_check = datetime.now()
        logger.info(f"Service availability check completed: {self._get_health_summary()}")

        return self.service_health.copy()

    async def _check_service_health(self, service_type: ServiceType) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """
        Check health of a specific service.

        Args:
            service_type: Type of service to check

        Returns:
            Tuple of (status, error_message, response_time_ms)
        """
        start_time = time.time()

        try:
            if service_type == ServiceType.AUTHENTICATION:
                return await self._check_authentication_service()
            elif service_type == ServiceType.AGENT_BRIDGE:
                return await self._check_agent_bridge_service()
            elif service_type == ServiceType.THREAD_SERVICE:
                return await self._check_thread_service()
            elif service_type == ServiceType.DATABASE_POSTGRES:
                return await self._check_postgres_database()
            elif service_type == ServiceType.DATABASE_REDIS:
                return await self._check_redis_database()
            elif service_type == ServiceType.AGENT_SUPERVISOR:
                return await self._check_agent_supervisor()
            elif service_type == ServiceType.TOOL_CLASSES:
                return await self._check_tool_classes()
            else:
                return ServiceStatus.UNKNOWN, f"Unknown service type: {service_type}", None

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Health check exception for {service_type.value}: {e}")
            return ServiceStatus.FAILED, str(e), response_time

    async def _check_authentication_service(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check UnifiedAuthenticationService availability."""
        start_time = time.time()

        try:
            from netra_backend.app.services.unified_authentication_service import get_unified_auth_service

            auth_service = get_unified_auth_service()
            if auth_service is None:
                return ServiceStatus.FAILED, "UnifiedAuthenticationService not available", None

            # Try to perform a lightweight health check
            # Note: We don't want to make actual auth calls that might have side effects
            if hasattr(auth_service, 'health_check'):
                await auth_service.health_check()

            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.HEALTHY, None, response_time

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"Authentication service error: {e}", response_time

    async def _check_agent_bridge_service(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check AgentWebSocketBridge availability."""
        start_time = time.time()

        try:
            if self.app and hasattr(self.app.state, 'agent_websocket_bridge'):
                bridge = self.app.state.agent_websocket_bridge
                if bridge is not None:
                    # Check if bridge has required methods
                    required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
                    missing_methods = [m for m in required_methods if not hasattr(bridge, m)]
                    if missing_methods:
                        return ServiceStatus.DEGRADED, f"AgentWebSocketBridge missing methods: {missing_methods}", None

                    response_time = (time.time() - start_time) * 1000
                    return ServiceStatus.HEALTHY, None, response_time

            # Try to import and check basic availability
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.DEGRADED, "AgentWebSocketBridge not initialized in app state", response_time

        except ImportError as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"AgentWebSocketBridge import failed: {e}", response_time
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"AgentWebSocketBridge error: {e}", response_time

    async def _check_thread_service(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check ThreadService availability."""
        start_time = time.time()

        try:
            from netra_backend.app.services.thread_service import ThreadService

            # Basic import success indicates service is available
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.HEALTHY, None, response_time

        except ImportError as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"ThreadService import failed: {e}", response_time
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"ThreadService error: {e}", response_time

    async def _check_postgres_database(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check PostgreSQL database connectivity."""
        start_time = time.time()

        try:
            from netra_backend.app.db.database_manager import DatabaseManager

            db_manager = DatabaseManager()
            if hasattr(db_manager, 'health_check'):
                await db_manager.health_check()
            elif hasattr(db_manager, 'get_postgres_pool'):
                # Try to get connection pool as health check
                pool = db_manager.get_postgres_pool()
                if pool is None:
                    return ServiceStatus.FAILED, "PostgreSQL connection pool not available", None

            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.HEALTHY, None, response_time

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"PostgreSQL database error: {e}", response_time

    async def _check_redis_database(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check Redis database connectivity."""
        start_time = time.time()

        try:
            from netra_backend.app.db.database_manager import DatabaseManager

            db_manager = DatabaseManager()
            if hasattr(db_manager, 'get_redis_client'):
                redis_client = db_manager.get_redis_client()
                if redis_client is None:
                    return ServiceStatus.FAILED, "Redis client not available", None

                # Try a simple ping
                if hasattr(redis_client, 'ping'):
                    await redis_client.ping()

            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.HEALTHY, None, response_time

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            # Redis is optional, so degraded rather than failed
            return ServiceStatus.DEGRADED, f"Redis database error: {e}", response_time

    async def _check_agent_supervisor(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check Agent Supervisor availability."""
        start_time = time.time()

        try:
            from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent

            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.HEALTHY, None, response_time

        except ImportError as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"SupervisorAgent import failed: {e}", response_time
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"SupervisorAgent error: {e}", response_time

    async def _check_tool_classes(self) -> Tuple[ServiceStatus, Optional[str], Optional[float]]:
        """Check Tool Classes availability."""
        start_time = time.time()

        try:
            from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher

            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.HEALTHY, None, response_time

        except ImportError as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"Tool classes import failed: {e}", response_time
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceStatus.FAILED, f"Tool classes error: {e}", response_time

    def _update_service_health(
        self,
        service_type: ServiceType,
        status: ServiceStatus,
        error_message: Optional[str] = None,
        response_time: Optional[float] = None
    ):
        """Update health information for a service."""
        health_info = self.service_health[service_type]

        # Update basic info
        health_info.status = status
        health_info.last_check = datetime.now()
        health_info.error_message = error_message
        health_info.response_time_ms = response_time

        # Update failure tracking
        if status == ServiceStatus.FAILED:
            health_info.consecutive_failures += 1
        else:
            health_info.consecutive_failures = 0

        # Circuit breaker logic
        if health_info.consecutive_failures >= self._max_consecutive_failures:
            health_info.circuit_breaker_open = True
            health_info.circuit_breaker_until = datetime.now() + timedelta(seconds=self._circuit_breaker_timeout)
            logger.warning(f"Circuit breaker opened for {service_type.value} after {health_info.consecutive_failures} failures")
        elif status == ServiceStatus.HEALTHY and health_info.circuit_breaker_open:
            if datetime.now() >= (health_info.circuit_breaker_until or datetime.now()):
                health_info.circuit_breaker_open = False
                health_info.circuit_breaker_until = None
                logger.info(f"Circuit breaker closed for {service_type.value} - service recovered")

    def is_service_available(self, service_type: ServiceType) -> bool:
        """
        Check if a service is currently available.

        Args:
            service_type: Type of service to check

        Returns:
            True if service is available (healthy or degraded), False if failed or circuit breaker open
        """
        health_info = self.service_health.get(service_type)
        if not health_info:
            return False

        # If circuit breaker is open, check if timeout has passed
        if health_info.circuit_breaker_open:
            if health_info.circuit_breaker_until and datetime.now() >= health_info.circuit_breaker_until:
                # Circuit breaker timeout passed, allow one test
                return True
            return False

        return health_info.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]

    def get_critical_services_status(self) -> Dict[ServiceType, bool]:
        """
        Get availability status of critical services.

        Returns:
            Dictionary mapping critical service types to their availability
        """
        return {
            service_type: self.is_service_available(service_type)
            for service_type in self.dependency_map.critical_services
        }

    def are_critical_services_available(self) -> bool:
        """
        Check if all critical services are available.

        Returns:
            True if all critical services are available, False otherwise
        """
        critical_status = self.get_critical_services_status()
        return all(critical_status.values())

    def get_degraded_services(self) -> List[ServiceType]:
        """
        Get list of services that are degraded but not failed.

        Returns:
            List of service types that are degraded
        """
        return [
            service_type for service_type, health_info in self.service_health.items()
            if health_info.status == ServiceStatus.DEGRADED
        ]

    def get_failed_services(self) -> List[ServiceType]:
        """
        Get list of services that have failed.

        Returns:
            List of service types that have failed
        """
        return [
            service_type for service_type, health_info in self.service_health.items()
            if health_info.status == ServiceStatus.FAILED
        ]

    def _get_health_summary(self) -> str:
        """Get a summary of service health status."""
        healthy = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.HEALTHY)
        degraded = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.DEGRADED)
        failed = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.FAILED)
        unknown = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.UNKNOWN)

        return f"Healthy: {healthy}, Degraded: {degraded}, Failed: {failed}, Unknown: {unknown}"

    def should_allow_websocket_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Determine if WebSocket connections should be allowed based on service availability.

        Returns:
            Tuple of (allow_connection, reason_if_denied)
        """
        # Check if critical services are available
        if not self.are_critical_services_available():
            failed_critical = [
                service_type.value for service_type in self.dependency_map.critical_services
                if not self.is_service_available(service_type)
            ]
            return False, f"Critical services unavailable: {', '.join(failed_critical)}"

        # Check for too many degraded services
        degraded = self.get_degraded_services()
        if len(degraded) >= 3:  # Arbitrary threshold
            return False, f"Too many degraded services: {', '.join(s.value for s in degraded)}"

        return True, None

    async def get_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report.

        Returns:
            Dictionary containing detailed health information
        """
        # Ensure we have recent health data
        if (datetime.now() - self._last_global_check).seconds > self._health_check_interval:
            await self.check_all_services()

        critical_status = self.get_critical_services_status()
        degraded_services = self.get_degraded_services()
        failed_services = self.get_failed_services()

        allow_connections, denial_reason = self.should_allow_websocket_connection()

        return {
            "overall_status": "healthy" if allow_connections else "degraded",
            "allow_websocket_connections": allow_connections,
            "denial_reason": denial_reason,
            "last_check": self._last_global_check.isoformat(),
            "critical_services": {
                service_type.value: {
                    "available": available,
                    "status": self.service_health[service_type].status.value,
                    "last_check": self.service_health[service_type].last_check.isoformat(),
                    "error": self.service_health[service_type].error_message,
                    "response_time_ms": self.service_health[service_type].response_time_ms,
                    "circuit_breaker_open": self.service_health[service_type].circuit_breaker_open
                }
                for service_type, available in critical_status.items()
            },
            "optional_services": {
                service_type.value: {
                    "available": self.is_service_available(service_type),
                    "status": self.service_health[service_type].status.value,
                    "last_check": self.service_health[service_type].last_check.isoformat(),
                    "error": self.service_health[service_type].error_message,
                    "response_time_ms": self.service_health[service_type].response_time_ms,
                    "circuit_breaker_open": self.service_health[service_type].circuit_breaker_open
                }
                for service_type in self.dependency_map.optional_services
            },
            "summary": {
                "total_services": len(ServiceType),
                "critical_services_count": len(self.dependency_map.critical_services),
                "optional_services_count": len(self.dependency_map.optional_services),
                "degraded_services": [s.value for s in degraded_services],
                "failed_services": [s.value for s in failed_services],
                "health_summary": self._get_health_summary()
            }
        }


# Global instance for easy access
_service_availability_manager: Optional[ServiceAvailabilityManager] = None


def get_service_availability_manager(app: Optional[FastAPI] = None) -> ServiceAvailabilityManager:
    """
    Get the global ServiceAvailabilityManager instance.

    Args:
        app: FastAPI application instance (used for initialization)

    Returns:
        ServiceAvailabilityManager instance
    """
    global _service_availability_manager

    if _service_availability_manager is None:
        _service_availability_manager = ServiceAvailabilityManager(app)
        logger.info("ServiceAvailabilityManager initialized")

    return _service_availability_manager


async def check_websocket_services_health(app: Optional[FastAPI] = None) -> Dict[str, Any]:
    """
    Convenience function to check WebSocket service health.

    Args:
        app: FastAPI application instance

    Returns:
        Health report dictionary
    """
    manager = get_service_availability_manager(app)
    return await manager.get_health_report()