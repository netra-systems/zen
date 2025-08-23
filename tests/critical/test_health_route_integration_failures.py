"""
Test suite to expose health route integration failures between services.

This test suite is designed to FAIL and expose the following integration issues:
1. Cross-service health check dependencies that create circular references
2. Service discovery health endpoint mismatches leading to startup failures  
3. WebSocket health check conflicts with HTTP health checks
4. Redis/database health check race conditions
5. Auth service health dependency circular references
6. Service port conflicts in health endpoint routing
7. Timeout cascading failures between health dependencies
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import redis.asyncio as redis

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auth_service.main import app as auth_app
from netra_backend.app.core.app_factory import create_app

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
            auth_content = auth_main.read_text()
            # Look for backend health URL references
            if 'netra_backend' in auth_content and 'health' in auth_content:
                auth_checks_backend = True
                
        if backend_health.exists():
            backend_content = backend_health.read_text()
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
            f"Circular health dependencies found: {failure_detector.circular_deps}"
    
    async def test_service_discovery_health_endpoint_mismatch(self, failure_detector):
        """Test that service discovery has mismatched health endpoints - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent
        
        # Check discovery service health endpoint
        discovery_file = project_root / 'netra_backend/app/routes/discovery.py'
        
        mismatches = []
        
        if discovery_file.exists():
            content = discovery_file.read_text()
            
            # Discovery has its own /health endpoint
            has_own_health = '@router.get("/health")' in content
            
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
        
        # Check if discovery reports inconsistent health endpoints
        dev_launcher = project_root / 'dev_launcher/startup_validator.py'
        if dev_launcher.exists():
            launcher_content = dev_launcher.read_text()
            
            # Check if launcher expects /health but discovery provides different format
            expects_health_ready = '/health/ready' in launcher_content
            expects_health = '"/health"' in launcher_content and 'auth' in launcher_content
            
            if expects_health_ready and expects_health:
                mismatches.append({
                    'issue': 'Dev launcher expects both /health and /health/ready inconsistently',
                    'component': 'dev_launcher'
                })
        
        for mismatch in mismatches:
            failure_detector.add_failure('discovery_mismatch', mismatch.get('service', 'unknown'), mismatch)
        
        # This should FAIL - we expect discovery mismatches
        assert len(mismatches) == 0, f"Discovery health endpoint mismatches: {mismatches}"
    
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
        ws_health_endpoints = [ep for ep in health_endpoints if 'ws' in ep]
        http_health_endpoints = [ep for ep in health_endpoints if 'ws' not in ep and 'health' in ep]
        
        # Test if WebSocket health uses different response format
        if ws_health_endpoints:
            try:
                ws_response = client.get(ws_health_endpoints[0])
                if ws_response.status_code == 200:
                    ws_data = ws_response.json()
                    ws_format = set(ws_data.keys())
            except:
                ws_format = set()
        else:
            ws_format = set()
            
        if http_health_endpoints:
            try:
                # Mock database dependencies to avoid connection errors
                with patch('netra_backend.app.dependencies.get_db_dependency'):
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
        
        # Check if WebSocket health endpoint uses different port expectations
        project_root = Path(__file__).parent.parent.parent
        ws_config_files = list(project_root.glob('**/websocket*.py'))
        
        for config_file in ws_config_files:
            if config_file.exists():
                content = config_file.read_text()
                if 'health' in content and 'port' in content:
                    # Look for hardcoded ports in WebSocket health
                    import re
                    port_matches = re.findall(r':(\d{4,5})/', content)
                    if port_matches:
                        conflicts.append({
                            'type': 'port_hardcoding',
                            'file': str(config_file),
                            'ports': port_matches
                        })
        
        for conflict in conflicts:
            failure_detector.add_failure('websocket_conflict', 'websocket', conflict)
        
        # This should FAIL - we expect WebSocket/HTTP conflicts
        assert len(conflicts) == 0, f"WebSocket/HTTP health conflicts: {conflicts}"
    
    async def test_redis_database_health_race_conditions(self, failure_detector):
        """Test that Redis and database health checks have race conditions - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent
        
        race_conditions = []
        
        # Check health route implementation
        health_file = project_root / 'netra_backend/app/routes/health.py'
        
        if health_file.exists():
            content = health_file.read_text()
            
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
        
        # Check for Redis timeout vs database timeout inconsistencies
        config_files = [
            project_root / 'netra_backend/app/core/configuration.py',
            project_root / 'netra_backend/app/db/postgres.py'
        ]
        
        timeouts = {}
        for config_file in config_files:
            if config_file.exists():
                content = config_file.read_text()
                
                # Look for timeout values
                import re
                redis_timeouts = re.findall(r'redis.*timeout[^\d]*(\d+\.?\d*)', content, re.IGNORECASE)
                db_timeouts = re.findall(r'database.*timeout[^\d]*(\d+\.?\d*)', content, re.IGNORECASE)
                
                if redis_timeouts:
                    timeouts['redis'] = [float(t) for t in redis_timeouts]
                if db_timeouts:
                    timeouts['database'] = [float(t) for t in db_timeouts]
        
        if 'redis' in timeouts and 'database' in timeouts:
            redis_max = max(timeouts['redis']) if timeouts['redis'] else 0
            db_max = max(timeouts['database']) if timeouts['database'] else 0
            
            # Race condition if timeouts are significantly different
            if abs(redis_max - db_max) > 5.0:
                race_conditions.append({
                    'type': 'timeout_mismatch',
                    'redis_timeout': redis_max,
                    'database_timeout': db_max,
                    'difference': abs(redis_max - db_max)
                })
        
        for race_condition in race_conditions:
            failure_detector.add_failure('race_condition', 'database', race_condition)
        
        # This should FAIL - we expect race conditions
        assert len(race_conditions) == 0, f"Redis/Database race conditions: {race_conditions}"
    
    async def test_auth_service_health_circular_references(self, auth_test_app, failure_detector):
        """Test that auth service has circular health check references - SHOULD FAIL."""
        client = TestClient(auth_test_app)
        
        circular_refs = []
        
        # Get auth service health endpoints
        auth_endpoints = []
        for route in auth_test_app.routes:
            if hasattr(route, 'path') and 'health' in route.path:
                auth_endpoints.append(route.path)
        
        project_root = Path(__file__).parent.parent.parent
        
        # Check if auth service health checks reference other services that check auth
        auth_main = project_root / 'auth_service/main.py'
        auth_routes = project_root / 'auth_service/auth_core/routes'
        
        services_referenced_by_auth = set()
        services_that_reference_auth = set()
        
        # Check what services auth references
        if auth_main.exists():
            content = auth_main.read_text()
            if 'netra_backend' in content:
                services_referenced_by_auth.add('netra_backend')
            if 'discovery' in content:
                services_referenced_by_auth.add('discovery')
        
        # Check auth route files
        if auth_routes.exists():
            for route_file in auth_routes.glob('*.py'):
                content = route_file.read_text()
                if 'netra_backend' in content or 'backend' in content:
                    services_referenced_by_auth.add('netra_backend')
        
        # Check what services reference auth in their health checks
        backend_files = [
            project_root / 'netra_backend/app/routes/health.py',
            project_root / 'netra_backend/app/main.py',
            project_root / 'netra_backend/app/core/health_checkers.py'
        ]
        
        for backend_file in backend_files:
            if backend_file.exists():
                content = backend_file.read_text()
                if 'auth' in content.lower() and 'service' in content:
                    services_that_reference_auth.add('netra_backend')
        
        # Find circular references
        circular_services = services_referenced_by_auth.intersection(services_that_reference_auth)
        
        for service in circular_services:
            circular_refs.append({
                'auth_references': service,
                'service_references_auth': True,
                'type': 'bidirectional_health_dependency'
            })
        
        # Check for auth token validation in health endpoints (another circular reference)
        for endpoint in auth_endpoints:
            try:
                # Mock auth dependencies to test the endpoint
                with patch('auth_service.auth_core.database.connection.auth_db'):
                    response = client.get(endpoint)
                    if response.status_code == 401:  # Requires authentication
                        circular_refs.append({
                            'endpoint': endpoint,
                            'type': 'health_endpoint_requires_auth',
                            'issue': 'Health endpoint requires auth token validation'
                        })
            except:
                pass
        
        for ref in circular_refs:
            failure_detector.add_failure('circular_reference', 'auth_service', ref)
        
        # This should FAIL - we expect circular references
        assert len(circular_refs) == 0, f"Auth service circular references: {circular_refs}"
    
    async def test_service_startup_port_conflicts(self, failure_detector):
        """Test that services have port conflicts in health endpoint routing - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent
        
        port_assignments = {}
        conflicts = []
        
        # Check dev launcher port assignments
        dev_launcher = project_root / 'dev_launcher/launcher.py'
        if dev_launcher.exists():
            content = dev_launcher.read_text()
            
            # Look for port assignments
            import re
            port_patterns = [
                r'backend.*port[^\d]*(\d+)',
                r'auth.*port[^\d]*(\d+)',
                r'frontend.*port[^\d]*(\d+)',
                r'port[^\d]*=\s*(\d+)'
            ]
            
            for pattern in port_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    port = int(match)
                    if port not in port_assignments:
                        port_assignments[port] = []
                    port_assignments[port].append('dev_launcher')
        
        # Check service configuration files for hardcoded ports
        config_files = [
            project_root / 'netra_backend/app/main.py',
            project_root / 'auth_service/main.py',
            project_root / 'frontend/package.json'
        ]
        
        for config_file in config_files:
            if config_file.exists():
                content = config_file.read_text()
                service_name = config_file.parent.name
                
                # Look for port configurations
                import re
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
        
        # Check for health endpoint specific port conflicts
        health_port_configs = []
        
        # Look for health-specific port configurations
        for root, dirs, files in project_root.walk():
            for file in files:
                if file.endswith('.py') and 'health' in file:
                    file_path = root / file
                    try:
                        content = file_path.read_text()
                        if 'port' in content and 'health' in content:
                            import re
                            health_ports = re.findall(r'health.*port[^\d]*(\d+)', content, re.IGNORECASE)
                            if health_ports:
                                health_port_configs.append({
                                    'file': str(file_path),
                                    'ports': [int(p) for p in health_ports]
                                })
                    except:
                        pass
        
        if health_port_configs:
            conflicts.append({
                'type': 'health_endpoint_port_configs',
                'configs': health_port_configs
            })
        
        # This should FAIL - we expect port conflicts
        assert len(conflicts) == 0, f"Service port conflicts: {conflicts}"
    
    async def test_health_check_timeout_cascade_failures(self, failure_detector):
        """Test that health check timeouts cause cascading failures - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent
        
        cascading_failures = []
        timeout_configs = {}
        
        # Analyze timeout configurations across services
        service_files = [
            ('netra_backend', project_root / 'netra_backend/app/routes/health.py'),
            ('auth_service', project_root / 'auth_service/main.py'),
            ('dev_launcher', project_root / 'dev_launcher/startup_validator.py')
        ]
        
        for service_name, service_file in service_files:
            if service_file.exists():
                content = service_file.read_text()
                
                # Extract timeout values
                import re
                timeout_patterns = [
                    r'timeout\s*=\s*(\d+\.?\d*)',
                    r'wait_for[^,]*timeout=(\d+\.?\d*)',
                    r'asyncio\.wait_for[^,]*timeout=(\d+\.?\d*)'
                ]
                
                service_timeouts = []
                for pattern in timeout_patterns:
                    matches = re.findall(pattern, content)
                    service_timeouts.extend([float(t) for t in matches])
                
                if service_timeouts:
                    timeout_configs[service_name] = {
                        'timeouts': service_timeouts,
                        'min_timeout': min(service_timeouts),
                        'max_timeout': max(service_timeouts),
                        'avg_timeout': sum(service_timeouts) / len(service_timeouts)
                    }
        
        # Check for cascading failure patterns
        if len(timeout_configs) >= 2:
            services = list(timeout_configs.keys())
            
            for i, service_a in enumerate(services):
                for service_b in services[i+1:]:
                    config_a = timeout_configs[service_a]
                    config_b = timeout_configs[service_b]
                    
                    # Check if service A's timeout is much shorter than service B's
                    # This could cause A to timeout while B is still processing
                    if config_a['max_timeout'] < config_b['min_timeout'] / 2:
                        cascading_failures.append({
                            'fast_service': service_a,
                            'slow_service': service_b,
                            'fast_timeout': config_a['max_timeout'],
                            'slow_timeout': config_b['min_timeout'],
                            'risk': 'fast_service_times_out_before_slow_service_completes'
                        })
                        
                        failure_detector.detect_timeout_cascade(service_a, [service_b])
        
        # Check for specific health check timeout cascades in startup sequence
        startup_files = [
            project_root / 'dev_launcher/launcher.py',
            project_root / 'dev_launcher/startup_validator.py'
        ]
        
        startup_cascade_risks = []
        for startup_file in startup_files:
            if startup_file.exists():
                content = startup_file.read_text()
                
                # Look for sequential health checks that might cascade
                if 'health/ready' in content and 'timeout' in content:
                    # Check if backend startup waits for auth, which waits for database
                    if 'backend' in content and 'auth' in content:
                        startup_cascade_risks.append({
                            'file': str(startup_file),
                            'risk': 'sequential_startup_health_checks_may_cascade',
                            'pattern': 'backend_waits_for_auth_waits_for_database'
                        })
        
        if startup_cascade_risks:
            cascading_failures.extend(startup_cascade_risks)
        
        # This should FAIL - we expect timeout cascades
        assert len(cascading_failures) == 0, f"Timeout cascade failures: {cascading_failures}"
    
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
                with patch('netra_backend.app.dependencies.get_db_dependency'):
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
        
        # Test auth service health endpoints
        auth_health_endpoints = ['/health', '/health/ready']
        
        for endpoint in auth_health_endpoints:
            try:
                # Test without auth token
                with patch('auth_service.auth_core.database.connection.auth_db'):
                    response = auth_client.get(endpoint)
                    
                    if response.status_code == 401:
                        auth_conflicts.append({
                            'service': 'auth',
                            'endpoint': endpoint,
                            'issue': 'health_endpoint_requires_authentication',
                            'status_code': response.status_code
                        })
                    
                    # Test if auth service health endpoint tries to validate its own tokens
                    if 'authorization' in response.headers.get('www-authenticate', '').lower():
                        auth_conflicts.append({
                            'service': 'auth',
                            'endpoint': endpoint,
                            'issue': 'auth_service_health_validates_own_tokens',
                            'headers': dict(response.headers)
                        })
            except Exception as e:
                auth_conflicts.append({
                    'service': 'auth',
                    'endpoint': endpoint,
                    'issue': 'health_endpoint_exception',
                    'error': str(e)
                })
        
        for conflict in auth_conflicts:
            failure_detector.add_failure('auth_conflict', conflict['service'], conflict)
        
        # This should FAIL - we expect authentication conflicts
        assert len(auth_conflicts) == 0, f"Health endpoint authentication conflicts: {auth_conflicts}"


class TestHealthRouteServiceDiscoveryFailures:
    """Test service discovery specific health route failures."""
    
    async def test_service_discovery_health_url_inconsistencies(self):
        """Test that service discovery reports inconsistent health URLs - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent
        
        inconsistencies = []
        
        # Check service discovery configuration
        discovery_files = [
            project_root / 'netra_backend/app/routes/discovery.py',
            project_root / 'dev_launcher/startup_validator.py',
            project_root / 'dev_launcher/service_startup.py'
        ]
        
        reported_health_urls = {}
        
        for discovery_file in discovery_files:
            if discovery_file.exists():
                content = discovery_file.read_text()
                file_name = discovery_file.name
                
                # Look for health URL patterns
                import re
                health_url_patterns = [
                    r'"([^"]*health[^"]*)"',
                    r"'([^']*health[^']*)'",
                    r'health_url[^"\']*["\']([^"\']*)["\']',
                    r'localhost:\d+(/[^"\']*health[^"\']*)'
                ]
                
                file_health_urls = set()
                for pattern in health_url_patterns:
                    matches = re.findall(pattern, content)
                    file_health_urls.update(matches)
                
                if file_health_urls:
                    reported_health_urls[file_name] = list(file_health_urls)
        
        # Check for inconsistencies between what different components expect
        if len(reported_health_urls) > 1:
            all_urls = set()
            for urls in reported_health_urls.values():
                all_urls.update(urls)
            
            # Check if different files expect different health endpoint formats
            for file_name, urls in reported_health_urls.items():
                for other_file, other_urls in reported_health_urls.items():
                    if file_name != other_file:
                        file_url_set = set(urls)
                        other_url_set = set(other_urls)
                        
                        # Check for conflicting expectations
                        if file_url_set and other_url_set and not file_url_set.intersection(other_url_set):
                            inconsistencies.append({
                                'file1': file_name,
                                'file2': other_file,
                                'file1_urls': list(file_url_set),
                                'file2_urls': list(other_url_set),
                                'type': 'no_common_health_urls'
                            })
        
        # Check for hardcoded vs dynamic health URL conflicts
        hardcoded_patterns = []
        dynamic_patterns = []
        
        for file_name, urls in reported_health_urls.items():
            for url in urls:
                if 'localhost' in url and re.search(r':\d{4,5}/', url):
                    hardcoded_patterns.append((file_name, url))
                elif '{' in url or 'port' in url or 'host' in url:
                    dynamic_patterns.append((file_name, url))
        
        if hardcoded_patterns and dynamic_patterns:
            inconsistencies.append({
                'type': 'mixed_hardcoded_dynamic_urls',
                'hardcoded': hardcoded_patterns,
                'dynamic': dynamic_patterns
            })
        
        # This should FAIL - we expect inconsistencies
        assert len(inconsistencies) == 0, f"Service discovery health URL inconsistencies: {inconsistencies}"
    
    async def test_health_endpoint_load_balancer_conflicts(self):
        """Test that health endpoints conflict with load balancer expectations - SHOULD FAIL."""
        project_root = Path(__file__).parent.parent.parent
        
        lb_conflicts = []
        
        # Check for load balancer or reverse proxy configurations
        config_files = [
            project_root / 'nginx.conf',
            project_root / 'docker-compose.yml',
            project_root / 'kubernetes',
            project_root / 'organized_root'
        ]
        
        lb_health_expectations = []
        
        for config_path in config_files:
            if config_path.exists():
                if config_path.is_file():
                    content = config_path.read_text()
                    # Look for health check configurations in load balancer configs
                    if 'health' in content:
                        import re
                        health_paths = re.findall(r'health[_-]?check[^"\']*["\']([^"\']*)["\']', content)
                        if health_paths:
                            lb_health_expectations.extend(health_paths)
                elif config_path.is_dir():
                    # Check kubernetes or deployment configs
                    for config_file in config_path.glob('**/*.yml'):
                        if config_file.exists():
                            content = config_file.read_text()
                            if 'healthcheck' in content or 'livenessProbe' in content:
                                import re
                                health_paths = re.findall(r'path:\s*([^\s]*health[^\s]*)', content)
                                if health_paths:
                                    lb_health_expectations.extend(health_paths)
        
        # Check if application health endpoints match load balancer expectations
        app_health_endpoints = []
        health_route_files = [
            project_root / 'netra_backend/app/routes/health.py',
            project_root / 'auth_service/main.py'
        ]
        
        for route_file in health_route_files:
            if route_file.exists():
                content = route_file.read_text()
                # Extract defined health endpoints
                import re
                endpoints = re.findall(r'@router\.get\(["\']([^"\']*health[^"\']*)["\']', content)
                endpoints.extend(re.findall(r'@app\.get\(["\']([^"\']*health[^"\']*)["\']', content))
                app_health_endpoints.extend(endpoints)
        
        # Find mismatches
        if lb_health_expectations and app_health_endpoints:
            lb_set = set(lb_health_expectations)
            app_set = set(app_health_endpoints)
            
            missing_from_app = lb_set - app_set
            extra_in_app = app_set - lb_set
            
            if missing_from_app:
                lb_conflicts.append({
                    'type': 'lb_expects_missing_endpoints',
                    'missing_endpoints': list(missing_from_app),
                    'lb_expectations': list(lb_set),
                    'app_provides': list(app_set)
                })
            
            if extra_in_app:
                lb_conflicts.append({
                    'type': 'app_provides_unexpected_endpoints',
                    'extra_endpoints': list(extra_in_app),
                    'lb_expectations': list(lb_set),
                    'app_provides': list(app_set)
                })
        
        # Check for path prefix conflicts (e.g., /api/health vs /health)
        prefixed_endpoints = [ep for ep in app_health_endpoints if '/' in ep[1:]]  # Has path segments
        root_endpoints = [ep for ep in app_health_endpoints if '/' not in ep[1:]]  # Root level
        
        if prefixed_endpoints and root_endpoints:
            lb_conflicts.append({
                'type': 'mixed_path_prefixes',
                'prefixed_endpoints': prefixed_endpoints,
                'root_endpoints': root_endpoints,
                'risk': 'load_balancer_routing_confusion'
            })
        
        # This should FAIL - we expect load balancer conflicts
        assert len(lb_conflicts) == 0, f"Load balancer health endpoint conflicts: {lb_conflicts}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])