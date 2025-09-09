from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

"""
Test suite to expose health route integration failures between services.

This test suite is designed to expose the following integration issues:
1. Cross-service health check dependencies that create circular references
2. Service discovery health endpoint mismatches leading to startup failures
3. WebSocket health check conflicts with HTTP health checks
4. Redis/database health check race conditions
5. Auth service health dependency circular references
6. Service port conflicts in health endpoint routing
7. Timeout cascading failures between health dependencies

Following CLAUDE.md principles:
- Tests use real services, not mocks
- Tests are designed to fail and expose integration issues
- Tests validate end-to-end health check flows
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import redis.asyncio as redis

from auth_service.main import app as auth_app
from netra_backend.app.core.app_factory import create_app
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

pytestmark = pytest.mark.asyncio


class HealthIntegrationFailureDetector:
    """Detector for health route integration failures across services."""

    def __init__(self):
        self.failures = []
        self.circular_deps = []
        self.port_conflicts = []
        self.timeout_cascades = []
        self.discovery_mismatches = []

    def add_failure(self, failure_type: str, service: str, details: Dict[str, Any]):
        """Add a detected integration failure."""
        self.failures.append({
            'type': failure_type,
            'service': service,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    def detect_circular_dependency(self, service_a: str, service_b: str, dependency_type: str):
        """Detect circular dependency between services."""
        self.circular_deps.append({
            'service_a': service_a,
            'service_b': service_b,
            'dependency_type': dependency_type
        })

    def detect_port_conflict(self, port: int, services: List[str]):
        """Detect port conflicts between services."""
        self.port_conflicts.append({
            'port': port,
            'conflicting_services': services
        })

    def detect_timeout_cascade(self, initiating_service: str, affected_services: List[str]):
        """Detect timeout cascading failures."""
        self.timeout_cascades.append({
            'initiating_service': initiating_service,
            'affected_services': affected_services
        })


class TestHealthRouteIntegrationFailures:
    """Test suite to expose health route integration failures."""

    @pytest.fixture
    def failure_detector(self):
        """Create failure detector."""
        return HealthIntegrationFailureDetector()

    @pytest.fixture
    def backend_app(self):
        """Create backend FastAPI app."""
        with patch.dict('os.environ', {
            'SKIP_STARTUP_TASKS': 'true',
            'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }):
            return create_app()

    @pytest.fixture
    def auth_test_app(self):
        """Create auth service test app."""
        with patch.dict('os.environ', {
            'AUTH_FAST_TEST_MODE': 'true',
            'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }):
            return auth_app

    async def test_cross_service_health_dependency_circular_reference(self, failure_detector):
        """Test that cross-service health checks create circular dependencies - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

        # Check if auth service health checks backend
        auth_main = project_root / 'auth_service/main.py'
        backend_health = project_root / 'netra_backend/app/routes/health.py'

        auth_checks_backend = False
        backend_checks_auth = False

        if auth_main.exists():
            auth_content = auth_main.read_text(encoding='utf-8')
            # Look for backend health URL references
            if 'netra_backend' in auth_content and 'health' in auth_content:
                auth_checks_backend = True

        if backend_health.exists():
            backend_content = backend_health.read_text(encoding='utf-8')
            # Look for auth service health references
            if 'auth_service' in backend_content or 'AUTH_SERVICE_URL' in backend_content:
                backend_checks_auth = True

        # Check for circular dependency
        if auth_checks_backend and backend_checks_auth:
            failure_detector.detect_circular_dependency(
                'auth_service', 'netra_backend', 'health_check'
            )

        # This should FAIL - we expect circular dependencies
        assert len(failure_detector.circular_deps) == 0, \
            f"Found circular health dependencies: {failure_detector.circular_deps}"

    async def test_service_discovery_health_endpoint_mismatch(self, failure_detector):
        """Test that service discovery has mismatched health endpoints - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

        # Check discovery service health endpoint
        discovery_file = project_root / 'netra_backend/app/routes/discovery.py'

        mismatches = []

        if discovery_file.exists():
            content = discovery_file.read_text(encoding='utf-8')

            # Discovery has its own /health endpoint
            has_own_health = '@app.get' in content and 'health' in content

            # But discovery doesn't report standardized health URLs for other services
            reports_standard_health = (
                'health_url' in content and
                '/health/ready' in content and
                'service_health_endpoints' in content
            )

            if has_own_health and not reports_standard_health:
                mismatches.append({
                    'issue': 'Discovery service has health endpoint but no standardized health URL reporting',
                    'service': 'discovery',
                    'endpoint': '/health'
                })

        for mismatch in mismatches:
            failure_detector.add_failure('discovery_mismatch', mismatch.get('service', 'unknown'), mismatch)

        # This should FAIL - we expect discovery mismatches
        assert len(mismatches) == 0, \
            f"Found service discovery health endpoint mismatches: {mismatches}"

    async def test_websocket_health_conflicts_with_http(self, backend_app, failure_detector):
        """Test that WebSocket and HTTP health checks conflict - SHOULD FAIL."""
        client = TestClient(backend_app)

        conflicts = []

        # Get all health endpoints
        health_endpoints = []
        for route in backend_app.routes:
            if hasattr(route, 'path') and 'health' in route.path:
                health_endpoints.append(route.path)

        # Check for WebSocket vs HTTP health endpoint conflicts
        ws_health_endpoints = [ep for ep in health_endpoints if 'ws' in ep.lower()]
        http_health_endpoints = [ep for ep in health_endpoints if 'ws' not in ep.lower()]

        # Test if WebSocket health uses different response format
        if ws_health_endpoints:
            try:
                ws_response = client.get(ws_health_endpoints[0])
                if ws_response.status_code == 200:
                    ws_data = ws_response.json()
                    ws_format = set(ws_data.keys())
                else:
                    ws_format = set()
            except:
                ws_format = set()
        else:
            ws_format = set()

        if http_health_endpoints:
            try:
                http_response = client.get(http_health_endpoints[0])
                if http_response.status_code == 200:
                    http_data = http_response.json()
                    http_format = set(http_data.keys())
                else:
                    http_format = set()
            except:
                http_format = set()
        else:
            http_format = set()

        # Check for format conflicts
        if ws_format and http_format:
            format_diff = ws_format.symmetric_difference(http_format)
            if format_diff:
                conflicts.append({
                    'type': 'response_format_conflict',
                    'ws_format': list(ws_format),
                    'http_format': list(http_format),
                    'differences': list(format_diff)
                })

        for conflict in conflicts:
            failure_detector.add_failure('websocket_conflict', 'websocket', conflict)

        # This should FAIL - we expect WebSocket/HTTP conflicts
        assert len(conflicts) == 0, \
            f"Found WebSocket/HTTP health check conflicts: {conflicts}"

    async def test_redis_database_health_race_conditions(self, failure_detector):
        """Test that Redis and database health checks have race conditions - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

        race_conditions = []

        # Check health route implementation
        health_file = project_root / 'netra_backend/app/routes/health.py'

        if health_file.exists():
            content = health_file.read_text(encoding='utf-8')

            # Look for Redis health checks without proper async/await handling
            has_redis_check = 'redis' in content.lower()
            has_database_check = 'postgres' in content or 'clickhouse' in content

            if has_redis_check and has_database_check:
                # Check if health checks run concurrently without coordination
                has_asyncio_gather = 'asyncio.gather' in content
                has_concurrent_checks = 'async def' in content and ('redis' in content and 'postgres' in content)

                if has_concurrent_checks and not has_asyncio_gather:
                    race_conditions.append({
                        'type': 'uncoordinated_concurrent_checks',
                        'checks': ['redis', 'postgres'],
                        'file': 'health.py'
                    })

                # Check for missing connection cleanup in health checks
                has_redis_cleanup = 'finally:' in content and 'redis' in content
                has_db_cleanup = 'async with' in content or ('try:' in content and 'finally:' in content)

                if has_redis_check and not has_redis_cleanup:
                    race_conditions.append({
                        'type': 'missing_redis_cleanup',
                        'risk': 'connection_leak'
                    })

        for race_condition in race_conditions:
            failure_detector.add_failure('race_condition', 'database', race_condition)

        # This should FAIL - we expect race conditions
        assert len(race_conditions) == 0, \
            f"Found Redis/database health check race conditions: {race_conditions}"

    async def test_service_startup_port_conflicts(self, failure_detector):
        """Test that services have port conflicts in health endpoint routing - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

        port_assignments = {}
        conflicts = []

        # Check service configuration files for hardcoded ports
        config_files = [
            project_root / 'netra_backend/app/main.py',
            project_root / 'auth_service/main.py',
            project_root / 'frontend/package.json'
        ]

        for config_file in config_files:
            if config_file.exists():
                content = config_file.read_text(encoding='utf-8')
                service_name = config_file.parent.name

                # Look for port configurations
                port_matches = re.findall(r'(?:port|PORT)[^\d]*(\d{4,5})', content)

                for port_str in port_matches:
                    port = int(port_str)
                    if port not in port_assignments:
                        port_assignments[port] = []
                    port_assignments[port].append(service_name)

        # Find conflicts
        for port, services in port_assignments.items():
            if len(services) > 1:
                conflicts.append({
                    'port': port,
                    'conflicting_services': services
                })
                failure_detector.detect_port_conflict(port, services)

        # This should FAIL - we expect port conflicts
        assert len(conflicts) == 0, \
            f"Found service port conflicts: {conflicts}"

    async def test_health_endpoint_authentication_conflicts(self, backend_app, auth_test_app, failure_detector):
        """Test that health endpoints have authentication conflicts - SHOULD FAIL."""
        backend_client = TestClient(backend_app)
        auth_client = TestClient(auth_test_app)

        auth_conflicts = []

        # Test backend health endpoints - should NOT require authentication
        backend_health_endpoints = ['/health', '/ready']

        for endpoint in backend_health_endpoints:
            try:
                # Test without auth token
                response = backend_client.get(endpoint)

                if response.status_code == 401:
                    auth_conflicts.append({
                        'service': 'backend',
                        'endpoint': endpoint,
                        'issue': 'health_endpoint_requires_authentication',
                        'status_code': response.status_code
                    })

                # Test with invalid auth token
                headers = {'Authorization': 'Bearer invalid_token'}
                response_with_auth = backend_client.get(endpoint, headers=headers)

                if response_with_auth.status_code != response.status_code:
                    auth_conflicts.append({
                        'service': 'backend',
                        'endpoint': endpoint,
                        'issue': 'health_endpoint_auth_inconsistency',
                        'no_auth_status': response.status_code,
                        'invalid_auth_status': response_with_auth.status_code
                    })

            except Exception as e:
                auth_conflicts.append({
                    'service': 'backend',
                    'endpoint': endpoint,
                    'issue': 'health_endpoint_exception',
                    'error': str(e)
                })

        for conflict in auth_conflicts:
            failure_detector.add_failure('auth_conflict', conflict['service'], conflict)

        # This should FAIL - we expect authentication conflicts
        assert len(auth_conflicts) == 0, \
            f"Found health endpoint authentication conflicts: {auth_conflicts}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])