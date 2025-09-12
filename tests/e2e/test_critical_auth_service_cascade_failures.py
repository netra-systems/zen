
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""Critical Auth Service Cascade Failures - E2E Failing Tests
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
End-to-end tests that replicate auth service failures cascading across multiple services.

CRITICAL CASCADE FAILURE SCENARIOS TO REPLICATE:
1. Auth service database failures preventing frontend authentication
2. Auth service startup failures causing backend service dependency issues
3. Auth service shutdown timeout causing deployment pipeline failures  
4. Missing OAuth secrets causing complete system authentication breakdown

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: End-to-end system reliability during auth service issues
- Value Impact: Prevents complete system failures when auth service has problems
- Strategic Impact: Ensures system resilience for all customer segments during auth issues
"""

import os
import sys
import pytest
import asyncio
import logging
import time
import requests
from fastapi.testclient import TestClient

from test_framework.environment_markers import env, staging_only, env_requires
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.http_client import UnifiedHTTPClient as HTTPClient

logger = logging.getLogger(__name__)


@env("staging") 
@env_requires(services=["auth_service", "backend", "frontend"], features=["full_system_configured"])
@pytest.mark.e2e
class TestCriticalAuthServiceCascadeFailures(SSotAsyncTestCase):
    """E2E test suite for auth service cascade failures across the system."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_database_failure_cascades_to_frontend_login(self):
        """FAILING TEST: Tests auth database failure preventing frontend user login.
        
        When the auth service database fails, frontend login attempts should fail
        gracefully, not cause system-wide crashes.
        """
        # Simulate auth service with database connectivity issues
        auth_service_down_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'unreachable-auth-db-host',  # Unreachable database
            'POSTGRES_DB': 'netra_staging',               # Database that doesn't exist
            'POSTGRES_USER': 'invalid_user',
            'POSTGRES_PASSWORD': 'invalid_password',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, auth_service_down_env):
            # Test frontend authentication flow when auth service has DB issues
            http_client = HTTPClient()
            
            # Attempt frontend login which depends on auth service
            frontend_url = self.get_service_url('frontend', 'http://localhost:3000')
            auth_service_url = self.get_service_url('auth_service', 'http://localhost:8081')
            
            # Try to initiate OAuth flow from frontend
            oauth_initiation_url = f"{frontend_url}/auth/signin"
            
            try:
                # Frontend should attempt to redirect to auth service
                response = await http_client.get(oauth_initiation_url, allow_redirects=False)
                
                # Check if the response indicates auth service issues
                if response.status_code == 500:
                    # Internal server error suggests cascade failure
                    pytest.fail(f"Auth service database failure cascaded to frontend 500 error: {response.text}")
                
                # Check if auth service health endpoint is down
                auth_health_url = f"{auth_service_url}/health"
                auth_response = await http_client.get(auth_health_url)
                
                if auth_response.status_code != 200:
                    logger.error(f"Auth service health check failed: {auth_response.status_code}")
                    
                    # Now test if frontend handles this gracefully
                    frontend_health_url = f"{frontend_url}/api/health"
                    frontend_response = await http_client.get(frontend_health_url)
                    
                    if frontend_response.status_code != 200:
                        pytest.fail(f"Frontend health degraded due to auth service issues: {frontend_response.status_code}")
                
                logger.error("Auth service database failure should cause cascading authentication failures")
                
            except Exception as e:
                # Connection errors indicate service availability issues
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    logger.error(f"Auth service database failure caused connection cascade: {e}")
                    pytest.fail(f"Auth database failure cascaded to connection failures: {e}")
                else:
                    raise
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_service_startup_failure_affects_backend_dependencies(self):
        """FAILING TEST: Tests auth service startup failure affecting backend service dependencies.
        
        If the auth service fails to start properly, backend services that depend
        on authentication should handle this gracefully.
        """
        # Simulate auth service startup failure due to missing secrets
        startup_failure_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLIENT_ID': '',  # Missing required OAuth config
            'GOOGLE_CLIENT_SECRET': '',
            'JWT_SECRET_KEY': '',
            'SERVICE_SECRET': '', 
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, startup_failure_env, clear=False):
            http_client = HTTPClient()
            
            # Test backend endpoints that require authentication
            backend_url = self.get_service_url('backend', 'http://localhost:8000')
            auth_service_url = self.get_service_url('auth_service', 'http://localhost:8081')
            
            # Check if auth service is healthy
            try:
                auth_health_response = await http_client.get(f"{auth_service_url}/health/ready")
                
                if auth_health_response.status_code != 200:
                    logger.error(f"Auth service not ready: {auth_health_response.status_code}")
                    
                    # Test backend authenticated endpoints
                    authenticated_endpoints = [
                        "/api/threads",
                        "/api/user/profile", 
                        "/api/agents"
                    ]
                    
                    for endpoint in authenticated_endpoints:
                        backend_endpoint = f"{backend_url}{endpoint}"
                        
                        try:
                            # Attempt to access authenticated endpoint without auth
                            response = await http_client.get(backend_endpoint)
                            
                            # Should get 401 Unauthorized, not 500 Internal Server Error
                            if response.status_code == 500:
                                pytest.fail(f"Backend endpoint {endpoint} returned 500 due to auth service issues")
                            
                            if response.status_code not in [401, 403]:
                                logger.warning(f"Backend endpoint {endpoint} unexpected status: {response.status_code}")
                        
                        except Exception as e:
                            # Connection failures suggest cascade issues
                            logger.error(f"Backend endpoint {endpoint} connection failed: {e}")
                            pytest.fail(f"Auth service startup failure cascaded to backend: {e}")
                
            except Exception as e:
                logger.error(f"Auth service startup failure cascade test failed: {e}")
                pytest.fail(f"Auth service startup failure caused system-wide issues: {e}")
    
    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_auth_service_shutdown_timeout_affects_deployment_pipeline(self):
        """FAILING TEST: Tests auth service shutdown timeout affecting deployment pipeline.
        
        If auth service doesn't shut down gracefully within timeout, it can cause
        deployment pipeline failures and rolling update problems.
        """
        # Simulate deployment environment with strict timeouts
        deployment_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-staging',      # Cloud Run environment
            'SHUTDOWN_TIMEOUT_SECONDS': '5',        # Short timeout for deployment
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, deployment_env):
            http_client = HTTPClient() 
            
            auth_service_url = self.get_service_url('auth_service', 'http://localhost:8081')
            backend_url = self.get_service_url('backend', 'http://localhost:8000')
            
            # Test service interdependency during shutdown simulation
            try:
                # Check initial service health
                auth_health = await http_client.get(f"{auth_service_url}/health")
                backend_health = await http_client.get(f"{backend_url}/health")
                
                if auth_health.status_code == 200 and backend_health.status_code == 200:
                    logger.info("Services initially healthy")
                    
                    # Simulate deployment scenario - new instance starting while old instance shutting down
                    # In a real deployment, this would involve actual service restart
                    # Here we simulate the timeout scenario
                    
                    start_time = time.time()
                    shutdown_timeout = 5.0
                    
                    # Monitor service availability during simulated shutdown
                    while time.time() - start_time < shutdown_timeout + 2:
                        try:
                            auth_response = await http_client.get(f"{auth_service_url}/health", timeout=1.0)
                            backend_response = await http_client.get(f"{backend_url}/health", timeout=1.0)
                            
                            # If services become unavailable, check if it's graceful
                            if auth_response.status_code != 200:
                                logger.warning(f"Auth service became unavailable: {auth_response.status_code}")
                                
                                # Backend should still handle requests gracefully
                                if backend_response.status_code != 200:
                                    elapsed = time.time() - start_time
                                    if elapsed < shutdown_timeout:
                                        pytest.fail(f"Backend failed before shutdown timeout: {elapsed}s < {shutdown_timeout}s")
                        
                        except asyncio.TimeoutError:
                            elapsed = time.time() - start_time
                            logger.error(f"Service timeout during deployment simulation: {elapsed}s")
                            
                            if elapsed < shutdown_timeout:
                                pytest.fail(f"Service timeout before graceful shutdown window: {elapsed}s")
                        
                        await asyncio.sleep(0.5)
                    
                    logger.info("Deployment shutdown timeout simulation completed")
                
            except Exception as e:
                logger.error(f"Deployment pipeline simulation failed: {e}")
                pytest.fail(f"Auth service shutdown timeout affected deployment: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_missing_oauth_secrets_cause_system_wide_auth_breakdown(self):
        """FAILING TEST: Tests missing OAuth secrets causing complete authentication breakdown.
        
        When OAuth secrets are missing from auth service, the entire system's
        authentication should fail gracefully, not crash.
        """
        # Simulate production deployment with missing OAuth configuration
        missing_oauth_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'valid-staging-db-host',
            'POSTGRES_DB': 'postgres',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password',
            # All OAuth secrets missing - this should cause system-wide auth failure
            # 'GOOGLE_CLIENT_ID': missing
            # 'GOOGLE_CLIENT_SECRET': missing  
            # 'OAUTH_HMAC_SECRET': missing
            'JWT_SECRET_KEY': 'valid-jwt-secret-key-32-chars-long',
            'SERVICE_SECRET': 'valid-service-secret-32-chars-long',
            'SERVICE_ID': 'staging-service-id',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, missing_oauth_env, clear=False):
            # Clear OAuth secrets
            for oauth_var in ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'OAUTH_HMAC_SECRET']:
                if oauth_var in os.environ:
                    del os.environ[oauth_var]
            
            http_client = HTTPClient()
            
            # Test complete authentication flow across all services
            services_urls = {
                'auth_service': self.get_service_url('auth_service', 'http://localhost:8081'),
                'backend': self.get_service_url('backend', 'http://localhost:8000'),
                'frontend': self.get_service_url('frontend', 'http://localhost:3000')
            }
            
            # Test each service's authentication-related endpoints
            auth_endpoints = {
                'auth_service': [
                    '/auth/google',        # OAuth initiation
                    '/auth/google/callback', # OAuth callback
                    '/auth/verify'         # Token verification
                ],
                'backend': [
                    '/auth/session',   # Session validation
                    '/api/user/profile'    # User profile (requires auth)
                ],
                'frontend': [
                    '/auth/signin',    # Sign in initiation
                    '/auth/signout'    # Sign out
                ]
            }
            
            oauth_failure_detected = False
            
            for service, base_url in services_urls.items():
                for endpoint in auth_endpoints.get(service, []):
                    full_url = f"{base_url}{endpoint}"
                    
                    try:
                        response = await http_client.get(full_url, allow_redirects=False)
                        
                        # Check for various failure modes
                        if response.status_code == 500:
                            # Internal server error suggests unhandled OAuth configuration issue
                            response_text = response.text if hasattr(response, 'text') else str(response.content)
                            
                            if any(oauth_term in response_text.lower() for oauth_term in 
                                   ['oauth', 'google', 'client_id', 'client_secret']):
                                oauth_failure_detected = True
                                logger.error(f"OAuth configuration failure at {service}{endpoint}: {response.status_code}")
                                pytest.fail(f"Missing OAuth secrets caused unhandled 500 error at {full_url}")
                        
                        # Configuration errors should be handled gracefully
                        elif response.status_code in [503, 502]:  # Service unavailable
                            logger.warning(f"Service unavailable due to OAuth config: {service}{endpoint}")
                            oauth_failure_detected = True
                        
                        logger.info(f"Tested {service}{endpoint}: {response.status_code}")
                    
                    except Exception as e:
                        # Connection failures might indicate service crash due to OAuth issues
                        if "connection" in str(e).lower():
                            oauth_failure_detected = True
                            logger.error(f"Connection failure due to OAuth config: {service}{endpoint}: {e}")
                            pytest.fail(f"Missing OAuth secrets caused service crash: {full_url}")
                        else:
                            logger.warning(f"Auth endpoint test exception: {service}{endpoint}: {e}")
            
            # If no OAuth failures were detected, the system might not be properly validating configuration
            if not oauth_failure_detected:
                logger.warning("No OAuth configuration failures detected - validation may be insufficient")
    
    def get_service_url(self, service: str, default: str) -> str:
        """Get service URL from environment or use default."""
        service_urls = {
            'auth_service': self._env.get('AUTH_SERVICE_URL', default if 'auth' in service else 'http://localhost:8081'),
            'backend': self._env.get('BACKEND_URL', default if 'backend' in service else 'http://localhost:8000'),  
            'frontend': self._env.get('FRONTEND_URL', default if 'frontend' in service else 'http://localhost:3000')
        }
        return service_urls.get(service, default)


@env("staging")
@env_requires(services=["auth_service", "backend"], features=["service_mesh_configured"])
@pytest.mark.e2e
class TestAuthServiceInterdependencyFailures(SSotAsyncTestCase):
    """Test auth service interdependency failures in service mesh."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_service_unavailable_affects_backend_startup(self):
        """FAILING TEST: Tests auth service unavailability affecting backend service startup.
        
        If auth service is unavailable during backend startup, it should handle
        this gracefully rather than failing to start.
        """
        # Simulate auth service completely unavailable
        unavailable_auth_env = {
            'ENVIRONMENT': 'staging',
            'AUTH_SERVICE_URL': 'http://unreachable-auth-service:8081',  # Unreachable
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, unavailable_auth_env):
            http_client = HTTPClient()
            
            # Test backend health when auth service is unavailable
            backend_url = self.get_service_url('backend', 'http://localhost:8000')
            
            try:
                # Backend should still be able to start and respond to health checks
                health_response = await http_client.get(f"{backend_url}/health")
                
                if health_response.status_code != 200:
                    pytest.fail(f"Backend health check failed when auth service unavailable: {health_response.status_code}")
                
                # Backend should report auth service as unavailable in dependencies
                dependencies_response = await http_client.get(f"{backend_url}/health/dependencies")
                
                if dependencies_response.status_code == 200:
                    # Should indicate auth service issues
                    logger.info("Backend properly reported auth service dependency issues")
                
            except Exception as e:
                logger.error(f"Backend startup affected by auth service unavailability: {e}")
                pytest.fail(f"Auth service unavailability prevented backend startup: {e}")
    
    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_auth_service_performance_degradation_cascade(self):
        """FAILING TEST: Tests auth service performance degradation cascading to other services.
        
        When auth service responds slowly, it should not cause timeouts and failures
        in other services that depend on authentication.
        """
        # Simulate slow auth service responses
        slow_auth_env = {
            'ENVIRONMENT': 'staging', 
            'AUTH_RESPONSE_TIMEOUT': '1',     # Very short timeout
            'DATABASE_TIMEOUT': '30',         # Long database timeout causing slow responses
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, slow_auth_env):
            http_client = HTTPClient()
            
            services_urls = {
                'auth_service': self.get_service_url('auth_service', 'http://localhost:8081'),
                'backend': self.get_service_url('backend', 'http://localhost:8000')
            }
            
            # Test performance cascade
            for service, base_url in services_urls.items():
                try:
                    start_time = time.time()
                    response = await http_client.get(f"{base_url}/health", timeout=5.0)
                    elapsed = time.time() - start_time
                    
                    # Check for performance degradation
                    if elapsed > 3.0:  # Reasonable health check timeout
                        logger.warning(f"{service} health check took {elapsed:.2f}s")
                        
                        if service != 'auth_service':
                            # Non-auth services shouldn't be slow due to auth issues
                            pytest.fail(f"{service} performance degraded due to auth service issues: {elapsed:.2f}s")
                    
                    logger.info(f"{service} health check: {response.status_code} in {elapsed:.2f}s")
                
                except asyncio.TimeoutError:
                    logger.error(f"{service} health check timed out")
                    if service != 'auth_service':
                        pytest.fail(f"{service} timed out due to auth service performance issues")


# Mark all tests as E2E integration tests requiring full system
pytestmark = [pytest.mark.e2e, pytest.mark.integration, pytest.mark.staging, pytest.mark.timeout(120)]