
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

"""
Auth Service Down Critical Scenarios - Iteration 2 Audit Findings

This test file specifically focuses on scenarios where the Auth Service is completely
down, unreachable, or failing, which is a major contributor to the authentication
system failure identified in Iteration 2:

**CRITICAL AUTH SERVICE DOWN SCENARIOS:**
1. Auth Service completely unresponsive (no HTTP response)
2. Auth Service returning 500 Internal Server Error
3. Auth Service database connectivity lost
4. Auth Service container/process crashed
5. Auth Service overwhelmed with requests (503 Service Unavailable)
6. Auth Service network partitioned from other services
7. Auth Service SSL certificate expired
8. Auth Service OAuth provider connectivity lost
9. Auth Service Redis/cache layer down
10. Auth Service graceful shutdown not working

**EXPECTED TO FAIL**: These tests demonstrate what happens when Auth Service fails
and expose the lack of fallback mechanisms causing system-wide authentication breakdown

System Impact When Auth Service Down:
- Frontend cannot authenticate users (100% authentication failure)
- Backend cannot validate tokens (all requests rejected with 403)
- No fallback authentication mechanisms
- No cached authentication decisions
- No graceful degradation
- 6.2+ second timeouts waiting for unresponsive auth service

Root Causes (Auth Service Failures):
- Single point of failure with no redundancy
- No health checks or automatic recovery
- No caching layer for authentication decisions  
- No fallback to alternative authentication methods
- Dependencies on external services without circuit breakers
"""

import asyncio
import pytest
import ssl
import time
import psutil
import subprocess
import httpx
import redis
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from shared.isolated_environment import IsolatedEnvironment
from auth_service.main import app
from test_framework.base_integration_test import BaseIntegrationTest


@pytest.mark.integration
@pytest.mark.critical
class TestAuthServiceDownCriticalScenarios(BaseIntegrationTest):
    """Test critical scenarios when Auth Service is down or failing"""

    def setup_method(self):
        """Set up auth service failure test environment"""
        super().setup_method()
        self.auth_service_url = 'http://localhost:8080'
        self.auth_service_process = None
        self.mock_dependencies = {}
        
    def teardown_method(self):
        """Clean up auth service test environment"""
        # Ensure auth service is stopped
        if self.auth_service_process:
            try:
                self.auth_service_process.terminate()
                self.auth_service_process.wait(timeout=5)
            except:
                try:
                    self.auth_service_process.kill()
                except:
                    pass
        super().teardown_method()

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_completely_unresponsive_no_fallback(self):
        """
        EXPECTED TO FAIL - CRITICAL SERVICE DOWN ISSUE
        System should have fallback when Auth Service is completely unresponsive
        Root cause: No fallback mechanism when Auth Service doesn't respond at all
        """
        # Ensure auth service is not running
        await self._stop_auth_service_completely()
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            try:
                # Attempt authentication request that requires auth service
                response = await client.post(
                    f"{self.auth_service_url}/auth/validate",
                    json={'token': 'test-token-when-service-down'},
                    timeout=8.0  # Allow time to detect the observed 6.2+ second issue
                )
                
                # Should NOT reach here - auth service is down
                pytest.fail("Auth service responded when it should be down")
                
            except httpx.ConnectError:
                end_time = time.time()
                duration = end_time - start_time
                
                # Should fail quickly with fallback, not after 6+ seconds
                assert duration < 2.0, f"Auth service failure took {duration:.2f}s, should fail quickly with fallback"
                
                # Should have fallback mechanism that provides graceful degradation
                pytest.fail("No fallback mechanism when Auth Service completely unresponsive")
                
            except httpx.TimeoutException:
                end_time = time.time()
                duration = end_time - start_time
                
                # This indicates the 6.2+ second timeout issue
                pytest.fail(f"Auth service request timeout after {duration:.2f}s - no fallback mechanism implemented")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_returning_500_internal_server_error(self):
        """
        EXPECTED TO FAIL - CRITICAL SERVER ERROR ISSUE
        System should handle Auth Service 500 errors gracefully with retry/fallback
        Root cause: No error handling when Auth Service returns 500 errors
        """
        # Mock auth service to return 500 errors
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = httpx.Response(
                status_code=500,
                content=b'{"error": "Internal Server Error", "message": "Auth service database connection failed"}',
                headers={'content-type': 'application/json'},
                request=Mock()
            )
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{self.auth_service_url}/auth/validate",
                        json={'token': 'test-token-server-error'},
                        timeout=5.0
                    )
                    
                    # Should handle 500 error gracefully
                    if response.status_code == 500:
                        # Should have retry mechanism or fallback
                        pytest.fail("No fallback mechanism for Auth Service 500 errors")
                    elif response.status_code == 503:
                        # Acceptable: Service Unavailable with retry guidance
                        response_data = response.json()
                        assert 'retry_after' in response_data
                        assert 'fallback' in response_data.get('message', '').lower()
                    else:
                        # Should either succeed with fallback or provide proper error
                        assert response.status_code in [200, 503], f"Unexpected status code: {response.status_code}"
                        
                except httpx.TimeoutException:
                    pytest.fail("Auth Service 500 error handling timeout - no resilience mechanism")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_database_connectivity_lost(self):
        """
        EXPECTED TO FAIL - CRITICAL DATABASE CONNECTIVITY ISSUE
        Auth Service should handle database connectivity loss gracefully
        Root cause: Auth Service crashes or becomes unresponsive when database is unreachable
        """
        # Mock database connectivity failure
        with patch('asyncpg.connect') as mock_db_connect:
            mock_db_connect.side_effect = ConnectionError("Cannot connect to PostgreSQL database")
            
            # Mock Redis connectivity failure  
            with patch('redis.Redis.ping') as mock_redis_ping:
                mock_redis_ping.side_effect = redis.ConnectionError("Cannot connect to Redis")
                
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(
                            f"{self.auth_service_url}/api/health",
                            timeout=5.0
                        )
                        
                        # Should report database connectivity issues but remain responsive
                        if response.status_code == 200:
                            health_data = response.json()
                            assert health_data.get('database') == 'unhealthy'
                            assert 'degraded' in health_data.get('status', '').lower()
                        elif response.status_code == 503:
                            # Acceptable: Service degraded due to database issues
                            response_data = response.json()
                            assert 'database' in response_data.get('error', '').lower()
                        else:
                            pytest.fail(f"Auth Service should remain responsive with degraded database, got {response.status_code}")
                            
                    except httpx.ConnectError:
                        pytest.fail("Auth Service became completely unresponsive due to database connectivity loss")
                    except httpx.TimeoutException:
                        pytest.fail("Auth Service hanging due to database connectivity loss")

    @pytest.mark.critical
    def test_auth_service_container_process_crashed(self):
        """
        EXPECTED TO FAIL - CRITICAL PROCESS CRASH ISSUE
        System should detect and recover from Auth Service process crashes
        Root cause: No process monitoring or automatic restart when Auth Service crashes
        """
        # Simulate auth service process crash
        try:
            # Find auth service process (if running)
            auth_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('auth_service' in arg or 'auth-service' in arg for arg in cmdline):
                        auth_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Kill auth service processes to simulate crash
            for pid in auth_processes:
                try:
                    psutil.Process(pid).terminate()
                except psutil.NoSuchProcess:
                    pass
            
            time.sleep(2)  # Wait for crash detection
            
            # Should have automatic restart mechanism
            time.sleep(5)  # Wait for restart
            
            # Check if auth service automatically restarted
            restarted_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('auth_service' in arg or 'auth-service' in arg for arg in cmdline):
                        restarted_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Should have automatic restart mechanism
            assert len(restarted_processes) > 0, "Auth Service should automatically restart after crash"
            
            # New process IDs should be different (indicating restart)
            assert not any(pid in auth_processes for pid in restarted_processes), "Auth Service should be new process after restart"
            
        except Exception as e:
            pytest.fail(f"Auth Service crash recovery mechanism not implemented: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_overwhelmed_with_requests_503_no_circuit_breaker(self):
        """
        EXPECTED TO FAIL - CRITICAL OVERLOAD ISSUE
        Auth Service should handle request overload with proper rate limiting/circuit breaker
        Root cause: No circuit breaker or rate limiting when Auth Service is overwhelmed
        """
        # Simulate request overload
        concurrent_requests = 100
        overload_results = []
        
        async def make_auth_request(session: httpx.AsyncClient, request_id: int):
            try:
                start_time = time.time()
                response = await session.post(
                    f"{self.auth_service_url}/auth/validate",
                    json={'token': f'overload-test-token-{request_id}'},
                    timeout=3.0
                )
                end_time = time.time()
                duration = end_time - start_time
                
                return {
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'duration': duration,
                    'success': response.status_code in [200, 401, 503]  # 503 is acceptable for overload
                }
            except httpx.TimeoutException:
                return {'request_id': request_id, 'status_code': 'timeout', 'success': False}
            except Exception as e:
                return {'request_id': request_id, 'status_code': f'error: {str(e)}', 'success': False}
        
        async with httpx.AsyncClient() as client:
            # Send concurrent requests to simulate overload
            tasks = [make_auth_request(client, i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
            timeout_requests = sum(1 for r in results if isinstance(r, dict) and r.get('status_code') == 'timeout')
            error_requests = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, dict) and not r.get('success')))
            
            # Should handle overload gracefully with circuit breaker
            success_rate = successful_requests / concurrent_requests
            timeout_rate = timeout_requests / concurrent_requests
            
            # Should NOT have high timeout/error rate (indicates lack of circuit breaker)
            assert timeout_rate < 0.5, f"High timeout rate ({timeout_rate:.1%}) indicates no circuit breaker"
            assert success_rate > 0.3, f"Very low success rate ({success_rate:.1%}) indicates poor overload handling"
            
            # Should provide 503 responses with retry guidance for overload
            service_unavailable_responses = sum(1 for r in results if isinstance(r, dict) and r.get('status_code') == 503)
            if service_unavailable_responses == 0 and timeout_rate > 0.2:
                pytest.fail("No circuit breaker or rate limiting - requests timeout instead of proper 503 responses")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_network_partitioned_from_other_services(self):
        """
        EXPECTED TO FAIL - CRITICAL NETWORK PARTITION ISSUE
        System should detect and handle Auth Service network partition
        Root cause: No network partition detection or handling mechanisms
        """
        # Simulate network partition by blocking auth service traffic
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("Network unreachable - simulated partition")
            
            async with httpx.AsyncClient() as client:
                partition_start_time = time.time()
                
                try:
                    # Attempt multiple requests during network partition
                    for attempt in range(3):
                        response = await client.post(
                            f"{self.auth_service_url}/auth/validate",
                            json={'token': f'partition-test-token-{attempt}'},
                            timeout=2.0
                        )
                        
                        # Should detect partition and provide fallback
                        if response.status_code == 503:
                            response_data = response.json()
                            if 'partition' in response_data.get('message', '').lower():
                                break  # Partition detected
                        
                        await asyncio.sleep(1)  # Brief delay between attempts
                    
                    partition_end_time = time.time()
                    partition_duration = partition_end_time - partition_start_time
                    
                    # Should detect partition quickly, not hang
                    assert partition_duration < 5.0, f"Network partition detection took {partition_duration:.2f}s"
                    
                except httpx.ConnectError:
                    partition_end_time = time.time()
                    partition_duration = partition_end_time - partition_start_time
                    
                    # Should have network partition handling mechanism
                    pytest.fail(f"No network partition handling - connection failed after {partition_duration:.2f}s")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_ssl_certificate_expired(self):
        """
        EXPECTED TO FAIL - CRITICAL SSL CERT EXPIRY ISSUE
        System should handle Auth Service SSL certificate expiration gracefully
        Root cause: No SSL certificate monitoring or graceful handling of certificate expiry
        """
        # Mock SSL certificate expiry
        with patch('ssl.create_default_context') as mock_ssl_context:
            mock_ssl_context.side_effect = ssl.SSLError("certificate verify failed: certificate has expired")
            
            async with httpx.AsyncClient(verify=False) as client:  # Disable verification for test
                try:
                    response = await client.get(
                        f"{self.auth_service_url}/api/health",
                        timeout=5.0
                    )
                    
                    # Should detect SSL certificate issues
                    if response.status_code == 200:
                        health_data = response.json()
                        assert 'ssl' in health_data or 'certificate' in health_data
                        assert health_data.get('ssl_status') == 'expired' or health_data.get('ssl_status') == 'warning'
                    else:
                        # Should provide clear SSL error message
                        assert response.status_code == 503, f"Should return 503 for SSL certificate issues, got {response.status_code}"
                        
                except ssl.SSLError as e:
                    # Should handle SSL errors gracefully, not crash
                    pytest.fail(f"SSL certificate expiry not handled gracefully: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_oauth_provider_connectivity_lost(self):
        """
        EXPECTED TO FAIL - CRITICAL OAUTH PROVIDER ISSUE
        Auth Service should handle OAuth provider connectivity loss
        Root cause: No fallback when OAuth provider (Google, etc.) is unreachable
        """
        # Mock OAuth provider connectivity failure
        with patch('httpx.AsyncClient.post') as mock_oauth_post:
            mock_oauth_post.side_effect = httpx.ConnectError("Cannot connect to accounts.google.com")
            
            async with httpx.AsyncClient() as client:
                try:
                    # Attempt OAuth login when provider is unreachable
                    response = await client.get(
                        f"{self.auth_service_url}/auth/login?provider=google",
                        timeout=5.0
                    )
                    
                    # Should handle OAuth provider failure gracefully
                    if response.status_code == 503:
                        response_data = response.json()
                        assert 'oauth' in response_data.get('error', '').lower() or 'provider' in response_data.get('error', '').lower()
                        assert 'retry' in response_data or 'alternative' in response_data
                    elif response.status_code == 200:
                        # Should offer alternative authentication methods
                        response_data = response.json()
                        assert 'alternative_methods' in response_data or 'fallback' in response_data
                    else:
                        pytest.fail(f"OAuth provider connectivity loss not handled, got {response.status_code}")
                        
                except httpx.TimeoutException:
                    pytest.fail("OAuth provider connectivity loss causing Auth Service to hang")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_redis_cache_layer_down(self):
        """
        EXPECTED TO FAIL - CRITICAL CACHE LAYER ISSUE
        Auth Service should continue operating when Redis cache layer is down
        Root cause: Auth Service depends too heavily on Redis, fails when Redis is unavailable
        """
        # Mock Redis connectivity failure
        with patch('redis.Redis.ping') as mock_redis_ping:
            mock_redis_ping.side_effect = redis.ConnectionError("Connection refused to Redis server")
            
            # Mock Redis operations to fail
            with patch('redis.Redis.get') as mock_redis_get:
                mock_redis_get.side_effect = redis.ConnectionError("Redis connection lost")
                
                async with httpx.AsyncClient() as client:
                    try:
                        # Auth service should continue operating without cache
                        response = await client.post(
                            f"{self.auth_service_url}/auth/validate",
                            json={'token': 'test-token-no-redis'},
                            timeout=5.0
                        )
                        
                        # Should work without Redis (maybe slower but functional)
                        assert response.status_code in [200, 401], f"Auth Service should work without Redis, got {response.status_code}"
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            # Should indicate cache is unavailable but service works
                            assert response_data.get('cache_status') == 'unavailable' or 'cache' not in response_data
                            
                    except httpx.TimeoutException:
                        pytest.fail("Auth Service becomes unresponsive when Redis cache layer is down")
                    except httpx.ConnectError:
                        pytest.fail("Auth Service crashes when Redis cache layer is down")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_graceful_shutdown_not_working(self):
        """
        EXPECTED TO FAIL - CRITICAL GRACEFUL SHUTDOWN ISSUE
        Auth Service should shut down gracefully, finishing in-progress requests
        Root cause: No graceful shutdown mechanism, abrupt termination causing request failures
        """
        # Start auth service if not running
        await self._ensure_auth_service_running()
        
        async with httpx.AsyncClient() as client:
            # Start long-running request
            shutdown_test_task = asyncio.create_task(
                client.post(
                    f"{self.auth_service_url}/auth/validate",
                    json={'token': 'long-running-token-for-shutdown-test'},
                    timeout=10.0
                )
            )
            
            # Brief delay to ensure request is in progress
            await asyncio.sleep(0.5)
            
            # Initiate graceful shutdown
            shutdown_start_time = time.time()
            await self._graceful_shutdown_auth_service()
            
            try:
                # Request should complete successfully despite shutdown
                response = await shutdown_test_task
                shutdown_end_time = time.time()
                shutdown_duration = shutdown_end_time - shutdown_start_time
                
                # Should complete gracefully
                assert response.status_code in [200, 401], f"In-progress request failed during shutdown: {response.status_code}"
                assert shutdown_duration < 30.0, f"Graceful shutdown took too long: {shutdown_duration:.2f}s"
                
            except httpx.ConnectError:
                pytest.fail("In-progress request terminated abruptly - no graceful shutdown")
            except asyncio.CancelledError:
                pytest.fail("In-progress request cancelled - no graceful shutdown")

    # Helper methods for test setup
    
    async def _stop_auth_service_completely(self):
        """Stop auth service completely to simulate it being down"""
        try:
            # Kill any existing auth service processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('auth_service' in arg or 'auth-service' in arg for arg in cmdline):
                        psutil.Process(proc.info['pid']).kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
    
    async def _ensure_auth_service_running(self):
        """Ensure auth service is running for tests that require it"""
        # Check if auth service is already running
        auth_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('auth_service' in arg for arg in cmdline):
                    auth_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not auth_running:
            # Start auth service for test
            self.auth_service_process = subprocess.Popen(['python', '-m', 'auth_service.main'])
            await asyncio.sleep(2)  # Wait for startup
    
    async def _graceful_shutdown_auth_service(self):
        """Initiate graceful shutdown of auth service"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{self.auth_service_url}/api/admin/shutdown", timeout=2.0)
        except:
            # If graceful shutdown endpoint doesn't exist or fails, use SIGTERM
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('auth_service' in arg for arg in cmdline):
                        psutil.Process(proc.info['pid']).terminate()  # Graceful termination
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue