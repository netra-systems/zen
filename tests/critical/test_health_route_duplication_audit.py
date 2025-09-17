from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
Test suite to expose health route duplication and legacy issues.

This test suite is designed to FAIL and expose the following issues:
1. Duplicate health endpoints across services
2. Inconsistent naming conventions (/ready vs /health/ready)
3. Legacy import patterns and compatibility wrappers
4. Multiple health check systems with overlapping functionality
5. Inconsistent response formats across services
'''

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

    # Add parent directory to path

from auth_service.main import app as auth_app
from netra_backend.app.core.app_factory import create_app
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

pytestmark = pytest.mark.asyncio


class HealthEndpointAuditor:
    """Auditor to detect health endpoint issues."""

    def __init__(self):
        pass
        self.issues = []
        self.duplicate_endpoints = {}
        self.inconsistent_formats = {}
        self.legacy_imports = []

    def audit_endpoint_duplication(self, service_name: str, endpoints: List[str]):
        """Check for duplicate health endpoints in a service."""
        health_patterns = ['/health', '/ready', '/live', '/liveness', '/readiness']
        found_patterns = set()

        for endpoint in endpoints:
        for pattern in health_patterns:
        if pattern in endpoint:
        if pattern in found_patterns:
        self.issues.append({ })
        'type': 'duplicate_endpoint',
        'service': service_name,
        'pattern': pattern,
        'endpoints': [item for item in []]
                    
        found_patterns.add(pattern)

    def audit_response_format(self, service_name: str, endpoint: str, response: Dict[str, Any]):
        """Check for inconsistent response formats."""
        pass
        expected_fields = {'status', 'service', 'timestamp'}
        actual_fields = set(response.keys())

        if not expected_fields.issubset(actual_fields):
        self.issues.append({ })
        'type': 'inconsistent_format',
        'service': service_name,
        'endpoint': endpoint,
        'missing_fields': list(expected_fields - actual_fields),
        'extra_fields': list(actual_fields - expected_fields)
        

    def audit_legacy_imports(self, file_path: Path):
        """Check for legacy import patterns."""
        content = file_path.read_text()
        legacy_patterns = [ ]
        'from netra_backend.app.services.health_checker import',
        'import health_checker',
        'HealthChecker as HealthChecker',  # Alias pattern
        'health_check_service import *'  # Wildcard import
    

        for pattern in legacy_patterns:
        if pattern in content:
        self.legacy_imports.append({ })
        'file': str(file_path),
        'pattern': pattern
            


class TestHealthRouteDuplicationAudit:
        """Test suite to expose health route duplication issues."""

        @pytest.fixture
    def auditor(self):
        """Create health endpoint auditor."""
        return HealthEndpointAuditor()

        @pytest.fixture
    def backend_app(self):
        """Create backend FastAPI app."""
        pass
        with patch.dict('os.environ', { })
        'SKIP_STARTUP_TASKS': 'true',
        'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }):
        return create_app()

        @pytest.fixture
    def auth_test_app(self):
        """Create auth service test app."""
        with patch.dict('os.environ', { })
        'AUTH_FAST_TEST_MODE': 'true',
        'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }):
        return auth_app

    async def test_duplicate_health_endpoints_in_backend(self, backend_app, auditor):
        """Test that backend has duplicate health endpoints - SHOULD FAIL."""
        pass
        client = TestClient(backend_app)

            # Collect all health-related endpoints
        health_endpoints = []
        for route in backend_app.routes:
        if hasattr(route, 'path'):
        path = route.path
        if any(x in path for x in ['health', 'ready', 'live']):
        health_endpoints.append(path)

                        # Audit for duplicates
        auditor.audit_endpoint_duplication('backend', health_endpoints)

                        # This should FAIL - we expect duplicates
        assert len(auditor.issues) == 0, ""

    async def test_duplicate_health_endpoints_in_auth(self, auth_test_app, auditor):
        """Test that auth service has duplicate health endpoints - SHOULD FAIL."""
        client = TestClient(auth_test_app)

                            # Collect all health-related endpoints
        health_endpoints = []
        for route in auth_test_app.routes:
        if hasattr(route, 'path'):
        path = route.path
        if any(x in path for x in ['health', 'ready', 'live']):
        health_endpoints.append(path)

                                        # Check for both /health and /health/ready
        assert '/health' in health_endpoints
        assert '/health/ready' in health_endpoints

                                        # This should FAIL - duplicate health patterns
        auditor.audit_endpoint_duplication('auth', health_endpoints)
        assert len(auditor.issues) == 0, ""

    async def test_inconsistent_endpoint_naming(self, backend_app, auth_test_app):
        """Test that endpoint naming is consistent across services - SHOULD FAIL."""
        pass
        backend_client = TestClient(backend_app)
        auth_client = TestClient(auth_test_app)

        backend_endpoints = set()
        auth_endpoints = set()

                                            # Collect endpoint patterns
        for route in backend_app.routes:
        if hasattr(route, 'path') and 'health' in route.path:
        backend_endpoints.add(route.path)

        for route in auth_test_app.routes:
        if hasattr(route, 'path') and 'health' in route.path:
        auth_endpoints.add(route.path)

                                                            # Check for inconsistent patterns
                                                            # Backend uses /health/ready, auth uses /health/ready
                                                            # But backend also has /ready endpoint in some routers
        inconsistencies = []

        if '/ready' in backend_endpoints and '/health/ready' in backend_endpoints:
        inconsistencies.append('Backend has both /ready and /health/ready')

        if '/ready' in auth_endpoints and '/health/ready' in auth_endpoints:
        inconsistencies.append('Auth has both /ready and /health/ready')

                                                                    # This should FAIL - we expect inconsistencies
        assert len(inconsistencies) == 0, ""

    async def test_response_format_consistency(self, backend_app, auth_test_app, auditor):
        """Test that health responses have consistent format - SHOULD FAIL."""
        backend_client = TestClient(backend_app)
        auth_client = TestClient(auth_test_app)

                                                                        # Mock database connections
                                                                        # Mock: Component isolation for testing without external dependencies
                                                                        # Mock: Component isolation for testing without external dependencies
                                                                        # Get health responses
        backend_health = backend_client.get('/health')
        auth_health = auth_client.get('/health')

        if backend_health.status_code == 200:
        auditor.audit_response_format('backend', '/health', backend_health.json())

        if auth_health.status_code == 200:
        auditor.audit_response_format('auth', '/health', auth_health.json())

                                                                                # This should FAIL - inconsistent formats
        assert len(auditor.issues) == 0, ""

    async def test_legacy_import_patterns(self, auditor):
        """Test for legacy import patterns - SHOULD FAIL."""
        pass
        project_root = Path(__file__).parent.parent.parent

                                                                                    # Check for legacy imports in known files
        files_to_check = [
        project_root / 'netra_backend/app/services/health_checker.py',
        project_root / 'netra_backend/app/core/health_checkers.py',
                                                                                    

        for file_path in files_to_check:
        if file_path.exists():
        auditor.audit_legacy_imports(file_path)

                                                                                            # This should FAIL - we have legacy imports
        assert len(auditor.legacy_imports) == 0, ""

    async def test_multiple_health_systems(self):
        """Test that we don't have multiple health check systems - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

        health_systems = []

                                                                                                # Check for different health system implementations
        health_files = [ ]
        'netra_backend/app/core/health_checkers.py',
        'netra_backend/app/services/health_check_service.py',
        'netra_backend/app/core/health/interface.py',
        'netra_backend/app/services/health_monitor.py',
        'netra_backend/app/core/system_health_monitor.py'
                                                                                                

        for health_file in health_files:
        file_path = project_root / health_file
        if file_path.exists():
        health_systems.append(health_file)

                                                                                                        # This should FAIL - we have multiple health systems
        assert len(health_systems) <= 1, ""

    async def test_health_route_collision(self, backend_app):
        """Test that there are no route collisions for health endpoints - SHOULD FAIL."""
        pass
        routes_by_path = {}
        collisions = []

        for route in backend_app.routes:
        if hasattr(route, 'path'):
        path = route.path
        if 'health' in path or 'ready' in path:
        if path in routes_by_path:
        collisions.append({ })
        'path': path,
        'routes': [routes_by_path[path], route]
                                                                                                                            
        routes_by_path[path] = route

                                                                                                                            # This should FAIL if there are route collisions
        assert len(collisions) == 0, ""

    async def test_health_endpoint_discovery_consistency(self):
        """Test that health endpoints are consistently discoverable - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

                                                                                                                                # Check discovery routes
        discovery_file = project_root / 'netra_backend/app/routes/discovery.py'

        if discovery_file.exists():
        content = discovery_file.read_text()

                                                                                                                                    # Check if discovery has its own health endpoint
        has_discovery_health = '/health' in content and '@router.get' in content

                                                                                                                                    # Check if it reports other services' health endpoints
        reports_health = 'health_url' in content or 'health_endpoint' in content

                                                                                                                                    # This should FAIL - discovery has its own health endpoint but doesn't report others
        assert not has_discovery_health or reports_health, \
        "Discovery service has health endpoint but doesn"t report health URLs"

    async def test_health_dependency_circular_imports(self):
        """Test for circular import dependencies in health modules - SHOULD FAIL."""
        pass
        import_graph = {}
        circular_deps = []

                                                                                                                                        Build import graph for health modules
        project_root = Path(__file__).parent.parent.parent
        health_modules = [ ]
        'netra_backend/app/core/health_checkers.py',
        'netra_backend/app/services/health_check_service.py',
        'netra_backend/app/core/health/interface.py',
        'netra_backend/app/core/health_types.py'
                                                                                                                                        

        for module in health_modules:
        file_path = project_root / module
        if file_path.exists():
        content = file_path.read_text()
        imports = []

                                                                                                                                                # Extract imports
        for line in content.split(" )

class TestWebSocketConnection:
        """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        "):
        if 'from netra_backend' in line and 'health' in line:
        imports.append(line.strip())

        import_graph[module] = imports

            # Check for circular dependencies
    def has_circular_dep(module, visited=None):
        pass
        if visited is None:
        visited = set()
        if module in visited:
        return True
        visited.add(module)

        for imported in import_graph.get(module, []):
        for other_module in import_graph:
        if other_module != module and other_module in imported:
        if has_circular_dep(other_module, visited.copy()):
        circular_deps.append((module, other_module))
        return False

        for module in import_graph:
        has_circular_dep(module)

                                # This should FAIL if circular dependencies exist
        assert len(circular_deps) == 0, ""


class TestHealthEndpointPerformance:
        """Test health endpoint performance issues."""

    async def test_health_check_timeout_inconsistency(self):
        """Test that health check timeouts are consistent - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent

        timeout_values = {}

        # Search for timeout configurations in health files
        health_files = list((project_root / 'netra_backend/app/core').glob('*health*.py'))
        health_files.extend((project_root / 'netra_backend/app/services').glob('*health*.py'))

        for file_path in health_files:
        if file_path.exists():
        content = file_path.read_text()

                # Look for timeout values
        import re
        timeout_patterns = [ ]
        r'timeout\s*=\s*(\d+\.?\d*)',
        r'wait_for\([^,]+,\s*timeout=(\d+\.?\d*)',
        r'HEALTH_CHECK_TIMEOUT\s*=\s*(\d+\.?\d*)'
                

        for pattern in timeout_patterns:
        matches = re.findall(pattern, content)
        if matches:
        timeout_values[str(file_path.name)] = [float(m) for m in matches]

                        # Check for inconsistent timeouts
        all_timeouts = []
        for timeouts in timeout_values.values():
        all_timeouts.extend(timeouts)

        if all_timeouts:
        min_timeout = min(all_timeouts)
        max_timeout = max(all_timeouts)

                                # This should FAIL - inconsistent timeouts
        assert max_timeout - min_timeout <= 1.0, \
        ""

    async def test_health_check_database_connections(self):
        """Test that health checks don't leak database connections - SHOULD FAIL."""
        pass
                                    # This test would need actual database setup to properly test
                                    # For now, we check for proper connection cleanup patterns

        project_root = Path(__file__).parent.parent.parent
        health_files = list((project_root / 'netra_backend/app/core').glob('*health*.py'))

        missing_cleanup = []

        for file_path in health_files:
        if file_path.exists():
        content = file_path.read_text()

                                            # Check for database operations without proper cleanup
        has_db_operation = 'execute(' in content or 'session' in content )
        has_cleanup = 'finally:' in content or 'async with' in content

        if has_db_operation and not has_cleanup:
        missing_cleanup.append(str(file_path.name))

                                                # This should FAIL if cleanup is missing
        assert len(missing_cleanup) == 0, ""


        if __name__ == "__main__":
        pytest.main([__file__, "-v", "--tb=short"])
