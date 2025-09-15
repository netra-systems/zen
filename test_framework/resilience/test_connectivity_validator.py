"""
Test Connectivity Validator for Issue #1278

Provides pre-test connectivity validation and health checks to determine
infrastructure availability before running test suites. Enables graceful
degradation when staging environment is unreachable.

Business Value: Platform/Internal - Test Infrastructure Resilience
Prevents test failures due to infrastructure issues and enables development
to continue during staging outages.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import socket
import ssl
import httpx
import redis
import asyncpg
from contextlib import asynccontextmanager

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class ConnectivityStatus(Enum):
    """Infrastructure connectivity status."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    """Types of services to validate."""
    DATABASE = "database"
    REDIS = "redis"
    CLICKHOUSE = "clickhouse"
    BACKEND_API = "backend_api"
    AUTH_SERVICE = "auth_service"
    WEBSOCKET = "websocket"
    LLM_SERVICE = "llm_service"


@dataclass
class ConnectivityResult:
    """Result of a connectivity check."""
    service_type: ServiceType
    status: ConnectivityStatus
    response_time: float = 0.0
    error_message: Optional[str] = None
    endpoint: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.status == ConnectivityStatus.AVAILABLE

    @property
    def is_degraded(self) -> bool:
        """Check if service is degraded but usable."""
        return self.status == ConnectivityStatus.DEGRADED


@dataclass
class InfrastructureHealth:
    """Overall infrastructure health assessment."""
    results: Dict[ServiceType, ConnectivityResult] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def overall_status(self) -> ConnectivityStatus:
        """Determine overall infrastructure status."""
        if not self.results:
            return ConnectivityStatus.UNKNOWN

        statuses = [result.status for result in self.results.values()]

        if all(status == ConnectivityStatus.AVAILABLE for status in statuses):
            return ConnectivityStatus.AVAILABLE
        elif any(status == ConnectivityStatus.UNAVAILABLE for status in statuses):
            # If critical services are down, overall is unavailable
            critical_services = {ServiceType.DATABASE, ServiceType.BACKEND_API}
            critical_down = any(
                self.results.get(service, ConnectivityResult(service, ConnectivityStatus.UNAVAILABLE)).status == ConnectivityStatus.UNAVAILABLE
                for service in critical_services
            )
            return ConnectivityStatus.UNAVAILABLE if critical_down else ConnectivityStatus.DEGRADED
        else:
            return ConnectivityStatus.DEGRADED

    @property
    def is_staging_available(self) -> bool:
        """Check if staging environment is available."""
        critical_services = {ServiceType.DATABASE, ServiceType.BACKEND_API}
        return all(
            self.results.get(service, ConnectivityResult(service, ConnectivityStatus.UNAVAILABLE)).is_healthy
            for service in critical_services
        )

    @property
    def should_skip_tests(self) -> bool:
        """Determine if tests should be skipped due to infrastructure issues."""
        return self.overall_status == ConnectivityStatus.UNAVAILABLE

    @property
    def should_use_fallback(self) -> bool:
        """Determine if fallback configurations should be used."""
        return self.overall_status in {ConnectivityStatus.DEGRADED, ConnectivityStatus.UNAVAILABLE}

    def get_healthy_services(self) -> List[ServiceType]:
        """Get list of healthy services."""
        return [
            service_type for service_type, result in self.results.items()
            if result.is_healthy
        ]

    def get_degraded_services(self) -> List[ServiceType]:
        """Get list of degraded services."""
        return [
            service_type for service_type, result in self.results.items()
            if result.is_degraded
        ]

    def get_unavailable_services(self) -> List[ServiceType]:
        """Get list of unavailable services."""
        return [
            service_type for service_type, result in self.results.items()
            if result.status == ConnectivityStatus.UNAVAILABLE
        ]


class TestConnectivityValidator:
    """
    Validates infrastructure connectivity before running tests.

    Provides pre-test health checks and enables graceful degradation
    when infrastructure components are unavailable.
    """

    def __init__(self, env: Optional[IsolatedEnvironment] = None):
        """Initialize connectivity validator."""
        self.env = env or get_env()
        self.timeout = float(self.env.get("INFRASTRUCTURE_HEALTH_CHECK_TIMEOUT", "5"))
        self.staging_timeout = float(self.env.get("STAGING_CONNECTION_TIMEOUT", "10"))

    async def validate_database_connectivity(self) -> ConnectivityResult:
        """Validate database connectivity."""
        start_time = time.time()

        # Try staging database first
        staging_host = self.env.get("STAGING_POSTGRES_HOST")
        if staging_host:
            try:
                conn = await asyncio.wait_for(
                    asyncpg.connect(
                        host=staging_host,
                        port=int(self.env.get("STAGING_POSTGRES_PORT", "5432")),
                        database=self.env.get("STAGING_POSTGRES_DB", "netra_staging"),
                        user=self.env.get("STAGING_POSTGRES_USER", "postgres"),
                        password=self.env.get("STAGING_POSTGRES_PASSWORD", "staging_password")
                    ),
                    timeout=self.staging_timeout
                )
                await conn.close()
                response_time = time.time() - start_time

                return ConnectivityResult(
                    service_type=ServiceType.DATABASE,
                    status=ConnectivityStatus.AVAILABLE,
                    response_time=response_time,
                    endpoint=f"{staging_host}:5432"
                )
            except Exception as e:
                logger.warning(f"Staging database unavailable: {e}")

        # Try local fallback database
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=self.env.get("POSTGRES_HOST", "localhost"),
                    port=int(self.env.get("POSTGRES_PORT", "5435")),
                    database=self.env.get("POSTGRES_DB", "test_db"),
                    user=self.env.get("POSTGRES_USER", "test_user"),
                    password=self.env.get("POSTGRES_PASSWORD", "test_password")
                ),
                timeout=self.timeout
            )
            await conn.close()
            response_time = time.time() - start_time

            return ConnectivityResult(
                service_type=ServiceType.DATABASE,
                status=ConnectivityStatus.DEGRADED,  # Local fallback is degraded mode
                response_time=response_time,
                endpoint="localhost:5435"
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectivityResult(
                service_type=ServiceType.DATABASE,
                status=ConnectivityStatus.UNAVAILABLE,
                response_time=response_time,
                error_message=str(e),
                endpoint="localhost:5435"
            )

    async def validate_redis_connectivity(self) -> ConnectivityResult:
        """Validate Redis connectivity."""
        start_time = time.time()

        try:
            redis_url = self.env.get("REDIS_URL", "redis://localhost:6382/0")
            r = redis.from_url(redis_url, socket_timeout=self.timeout)
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, r.ping),
                timeout=self.timeout
            )
            response_time = time.time() - start_time

            return ConnectivityResult(
                service_type=ServiceType.REDIS,
                status=ConnectivityStatus.AVAILABLE,
                response_time=response_time,
                endpoint=redis_url
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectivityResult(
                service_type=ServiceType.REDIS,
                status=ConnectivityStatus.UNAVAILABLE,
                response_time=response_time,
                error_message=str(e),
                endpoint=self.env.get("REDIS_URL", "redis://localhost:6382/0")
            )

    async def validate_backend_api_connectivity(self) -> ConnectivityResult:
        """Validate backend API connectivity."""
        start_time = time.time()

        # Try staging backend first
        staging_url = self.env.get("STAGING_BACKEND_URL")
        if staging_url:
            try:
                async with httpx.AsyncClient(timeout=self.staging_timeout) as client:
                    response = await client.get(f"{staging_url}/health")
                    response_time = time.time() - start_time

                    if response.status_code == 200:
                        return ConnectivityResult(
                            service_type=ServiceType.BACKEND_API,
                            status=ConnectivityStatus.AVAILABLE,
                            response_time=response_time,
                            endpoint=staging_url
                        )
                    else:
                        return ConnectivityResult(
                            service_type=ServiceType.BACKEND_API,
                            status=ConnectivityStatus.DEGRADED,
                            response_time=response_time,
                            error_message=f"HTTP {response.status_code}",
                            endpoint=staging_url
                        )
            except Exception as e:
                logger.warning(f"Staging backend API unavailable: {e}")

        # No local fallback for backend API
        response_time = time.time() - start_time
        return ConnectivityResult(
            service_type=ServiceType.BACKEND_API,
            status=ConnectivityStatus.UNAVAILABLE,
            response_time=response_time,
            error_message="No backend API available",
            endpoint=staging_url or "unknown"
        )

    async def validate_auth_service_connectivity(self) -> ConnectivityResult:
        """Validate auth service connectivity."""
        start_time = time.time()

        try:
            auth_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8083")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{auth_url}/health")
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ConnectivityResult(
                        service_type=ServiceType.AUTH_SERVICE,
                        status=ConnectivityStatus.AVAILABLE,
                        response_time=response_time,
                        endpoint=auth_url
                    )
                else:
                    return ConnectivityResult(
                        service_type=ServiceType.AUTH_SERVICE,
                        status=ConnectivityStatus.DEGRADED,
                        response_time=response_time,
                        error_message=f"HTTP {response.status_code}",
                        endpoint=auth_url
                    )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectivityResult(
                service_type=ServiceType.AUTH_SERVICE,
                status=ConnectivityStatus.UNAVAILABLE,
                response_time=response_time,
                error_message=str(e),
                endpoint=self.env.get("AUTH_SERVICE_URL", "http://localhost:8083")
            )

    async def validate_websocket_connectivity(self) -> ConnectivityResult:
        """Validate WebSocket connectivity."""
        start_time = time.time()

        # Try staging WebSocket first
        staging_ws_url = self.env.get("STAGING_WEBSOCKET_URL")
        if staging_ws_url:
            try:
                import websockets

                async with asyncio.wait_for(
                    websockets.connect(staging_ws_url),
                    timeout=self.staging_timeout
                ) as ws:
                    # Send a simple ping
                    await ws.send('{"type": "ping"}')
                    response = await asyncio.wait_for(ws.recv(), timeout=5)

                    response_time = time.time() - start_time
                    return ConnectivityResult(
                        service_type=ServiceType.WEBSOCKET,
                        status=ConnectivityStatus.AVAILABLE,
                        response_time=response_time,
                        endpoint=staging_ws_url
                    )
            except Exception as e:
                logger.warning(f"Staging WebSocket unavailable: {e}")

        # No WebSocket available
        response_time = time.time() - start_time
        return ConnectivityResult(
            service_type=ServiceType.WEBSOCKET,
            status=ConnectivityStatus.UNAVAILABLE,
            response_time=response_time,
            error_message="No WebSocket service available",
            endpoint=staging_ws_url or "unknown"
        )

    async def validate_clickhouse_connectivity(self) -> ConnectivityResult:
        """Validate ClickHouse connectivity."""
        start_time = time.time()

        try:
            clickhouse_host = self.env.get("CLICKHOUSE_HOST", "localhost")
            clickhouse_port = int(self.env.get("CLICKHOUSE_HTTP_PORT", "8126"))

            # Simple TCP connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((clickhouse_host, clickhouse_port))
            sock.close()

            response_time = time.time() - start_time

            if result == 0:
                return ConnectivityResult(
                    service_type=ServiceType.CLICKHOUSE,
                    status=ConnectivityStatus.AVAILABLE,
                    response_time=response_time,
                    endpoint=f"{clickhouse_host}:{clickhouse_port}"
                )
            else:
                return ConnectivityResult(
                    service_type=ServiceType.CLICKHOUSE,
                    status=ConnectivityStatus.UNAVAILABLE,
                    response_time=response_time,
                    error_message="Connection refused",
                    endpoint=f"{clickhouse_host}:{clickhouse_port}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectivityResult(
                service_type=ServiceType.CLICKHOUSE,
                status=ConnectivityStatus.UNAVAILABLE,
                response_time=response_time,
                error_message=str(e),
                endpoint=f"{clickhouse_host}:{clickhouse_port}"
            )

    async def validate_all_services(self) -> InfrastructureHealth:
        """Validate all infrastructure services."""
        logger.info("Starting infrastructure connectivity validation...")

        validation_tasks = {
            ServiceType.DATABASE: self.validate_database_connectivity(),
            ServiceType.REDIS: self.validate_redis_connectivity(),
            ServiceType.BACKEND_API: self.validate_backend_api_connectivity(),
            ServiceType.AUTH_SERVICE: self.validate_auth_service_connectivity(),
            ServiceType.WEBSOCKET: self.validate_websocket_connectivity(),
            ServiceType.CLICKHOUSE: self.validate_clickhouse_connectivity(),
        }

        results = {}
        for service_type, task in validation_tasks.items():
            try:
                result = await task
                results[service_type] = result
                logger.info(f"Service {service_type.value}: {result.status.value} ({result.response_time:.3f}s)")
            except Exception as e:
                results[service_type] = ConnectivityResult(
                    service_type=service_type,
                    status=ConnectivityStatus.UNAVAILABLE,
                    error_message=str(e)
                )
                logger.error(f"Service {service_type.value}: validation failed - {e}")

        health = InfrastructureHealth(results=results)
        logger.info(f"Infrastructure health assessment complete: {health.overall_status.value}")

        return health

    async def validate_quick_health_check(self) -> InfrastructureHealth:
        """Quick health check for critical services only."""
        logger.info("Running quick infrastructure health check...")

        # Only check critical services for speed
        critical_tasks = {
            ServiceType.DATABASE: self.validate_database_connectivity(),
            ServiceType.BACKEND_API: self.validate_backend_api_connectivity(),
        }

        results = {}
        for service_type, task in critical_tasks.items():
            try:
                result = await task
                results[service_type] = result
            except Exception as e:
                results[service_type] = ConnectivityResult(
                    service_type=service_type,
                    status=ConnectivityStatus.UNAVAILABLE,
                    error_message=str(e)
                )

        health = InfrastructureHealth(results=results)
        logger.info(f"Quick health check complete: {health.overall_status.value}")

        return health

    def should_skip_tests(self, health: InfrastructureHealth) -> Tuple[bool, str]:
        """Determine if tests should be skipped based on infrastructure health."""
        if self.env.get("TEST_SKIP_ON_INFRASTRUCTURE_FAILURE", "true").lower() == "true":
            if health.should_skip_tests:
                unavailable_services = health.get_unavailable_services()
                reason = f"Critical infrastructure unavailable: {[s.value for s in unavailable_services]}"
                return True, reason

        return False, ""

    def get_fallback_configuration(self, health: InfrastructureHealth) -> Dict[str, str]:
        """Get fallback configuration based on infrastructure health."""
        fallback_config = {}

        if health.should_use_fallback:
            # Enable fallback modes
            fallback_config.update({
                "INFRASTRUCTURE_DEGRADED_MODE": "true",
                "CONNECTIVITY_RESILIENCE_ENABLED": "true",
                "TEST_GRACEFUL_DEGRADATION": "true"
            })

            # Service-specific fallbacks
            unavailable_services = health.get_unavailable_services()

            if ServiceType.DATABASE in unavailable_services:
                fallback_config["DATABASE_MODE"] = "local"
                logger.warning("Falling back to local database due to staging unavailability")

            if ServiceType.REDIS in unavailable_services:
                fallback_config["REDIS_MODE"] = "local"
                logger.warning("Falling back to local Redis due to unavailability")

            if ServiceType.BACKEND_API in unavailable_services:
                fallback_config["BACKEND_MOCK_MODE"] = "true"
                logger.warning("Enabling backend mock mode due to API unavailability")

            if ServiceType.WEBSOCKET in unavailable_services:
                fallback_config["WEBSOCKET_MOCK_MODE"] = "true"
                logger.warning("Enabling WebSocket mock mode due to service unavailability")

        return fallback_config


# Convenience functions for test integration
async def validate_infrastructure_health(env: Optional[IsolatedEnvironment] = None) -> InfrastructureHealth:
    """Validate infrastructure health (convenience function)."""
    validator = TestConnectivityValidator(env)
    return await validator.validate_all_services()


async def validate_critical_services(env: Optional[IsolatedEnvironment] = None) -> InfrastructureHealth:
    """Quick validation of critical services only (convenience function)."""
    validator = TestConnectivityValidator(env)
    return await validator.validate_quick_health_check()


def should_skip_test_due_to_infrastructure(health: InfrastructureHealth, env: Optional[IsolatedEnvironment] = None) -> Tuple[bool, str]:
    """Determine if test should be skipped due to infrastructure issues (convenience function)."""
    validator = TestConnectivityValidator(env)
    return validator.should_skip_tests(health)


def get_resilient_test_configuration(health: InfrastructureHealth, env: Optional[IsolatedEnvironment] = None) -> Dict[str, str]:
    """Get resilient test configuration based on infrastructure health (convenience function)."""
    validator = TestConnectivityValidator(env)
    return validator.get_fallback_configuration(health)