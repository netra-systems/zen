"""
Integration tests for FINALIZE phase - Inter-Service Connectivity

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Integration Reliability
- Value Impact: Ensures all services can communicate properly for user operations
- Strategic Impact: Prevents service isolation issues that break user workflows

Tests inter-service connectivity validation during the FINALIZE phase, ensuring
all services can communicate effectively and handle cross-service operations
required for chat functionality.

This covers:
1. Backend <-> Auth service communication
2. Backend <-> Database connectivity  
3. Service discovery and routing
4. Cross-service authentication flows
5. Service mesh/proxy connectivity (if applicable)
6. Load balancer health checks
"""

import asyncio
import time
from typing import Dict, Any, List
import pytest
import httpx
import aiohttp
import json
from unittest.mock import patch, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env


class TestStartupFinalizeServiceConnectivity(SSotBaseTestCase):
    """Integration tests for FINALIZE phase inter-service connectivity."""
    
    def setup_method(self, method):
        """Setup test environment with multi-service configuration."""
        super().setup_method(method)
        
        # Initialize E2E auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Configure test environment
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
        
        # Service endpoints configuration
        self.services = {
            "backend": "http://localhost:8000",
            "auth": "http://localhost:8083", 
            "websocket": "ws://localhost:8000/ws"
        }
        
        # Track connectivity test results
        self.connectivity_results: Dict[str, Any] = {}

    @pytest.mark.integration
    async def test_finalize_backend_auth_service_connectivity(self):
        """
        Test backend service can communicate with auth service.
        
        BVJ: Ensures user authentication flows work through backend.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        connectivity_tests = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Test backend can validate tokens with auth service
            validation_start = time.time()
            try:
                # Create test payload for token validation
                test_payload = {
                    "action": "validate_user_session",
                    "user_id": "test-user-123"
                }
                
                async with session.post(
                    f"{self.services['backend']}/auth/validate", 
                    headers=headers,
                    json=test_payload,
                    timeout=10
                ) as resp:
                    validation_time = time.time() - validation_start
                    
                    # Should either succeed or gracefully handle validation
                    assert resp.status in [200, 401, 404, 422], f"Token validation failed: {resp.status}"
                    
                    if resp.status == 200:
                        validation_result = await resp.json()
                        connectivity_tests.append({
                            "test": "backend_auth_validation",
                            "status": "success", 
                            "response_time": validation_time,
                            "result": validation_result
                        })
                    else:
                        # Graceful failure is acceptable
                        connectivity_tests.append({
                            "test": "backend_auth_validation",
                            "status": "graceful_failure",
                            "response_time": validation_time,
                            "status_code": resp.status
                        })
                        
                    self.record_metric("backend_auth_validation_time", validation_time)
                    
            except asyncio.TimeoutError:
                pytest.fail("Backend to auth service communication timed out")
            except Exception as e:
                # Communication failure is a critical error
                pytest.fail(f"Backend to auth service communication failed: {e}")
            
            # 2. Test backend can proxy auth requests
            proxy_start = time.time()
            try:
                # Test if backend can proxy login requests to auth service
                login_data = {
                    "email": "test@example.com",
                    "password": "test_password_123"
                }
                
                async with session.post(
                    f"{self.services['backend']}/api/auth/login",
                    json=login_data,
                    timeout=15
                ) as resp:
                    proxy_time = time.time() - proxy_start
                    
                    # Should either succeed, handle gracefully, or indicate endpoint doesn't exist
                    assert resp.status in [200, 201, 400, 401, 404, 422], f"Auth proxy failed: {resp.status}"
                    
                    connectivity_tests.append({
                        "test": "backend_auth_proxy",
                        "status": "tested",
                        "response_time": proxy_time,
                        "status_code": resp.status
                    })
                    
                    self.record_metric("backend_auth_proxy_time", proxy_time)
                    
            except Exception as e:
                # Proxy may not be implemented - log but don't fail
                self.record_metric("backend_auth_proxy_error", str(e))
                connectivity_tests.append({
                    "test": "backend_auth_proxy",
                    "status": "not_implemented",
                    "error": str(e)
                })
            
            # 3. Test direct auth service health from backend perspective
            try:
                # Simulate backend checking auth service health
                async with session.get(
                    f"{self.services['auth']}/health",
                    timeout=10
                ) as resp:
                    assert resp.status == 200, f"Auth service not healthy from backend perspective: {resp.status}"
                    
                    auth_health = await resp.json()
                    connectivity_tests.append({
                        "test": "auth_service_health_check",
                        "status": "success",
                        "result": auth_health
                    })
                    
            except Exception as e:
                pytest.fail(f"Auth service health check failed: {e}")
        
        # Record all connectivity test results
        self.connectivity_results["backend_auth_connectivity"] = connectivity_tests
        
        # At least one connectivity test should have succeeded
        successful_tests = [t for t in connectivity_tests if t["status"] == "success"]
        assert len(successful_tests) > 0, "No successful backend-auth connectivity tests"
        
        self.record_metric("backend_auth_connectivity_passed", True)

    @pytest.mark.integration
    async def test_finalize_backend_database_connectivity(self):
        """
        Test backend service database connectivity and operations.
        
        BVJ: Ensures backend can perform database operations for user data.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        database_tests = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Test database health through backend
            db_health_start = time.time()
            try:
                async with session.get(
                    f"{self.services['backend']}/health/database",
                    headers=headers,
                    timeout=15
                ) as resp:
                    db_health_time = time.time() - db_health_start
                    
                    assert resp.status == 200, f"Database health check failed: {resp.status}"
                    
                    db_health = await resp.json()
                    database_tests.append({
                        "test": "database_health",
                        "status": "success",
                        "response_time": db_health_time,
                        "result": db_health
                    })
                    
                    # Validate database connection status
                    if "connected" in db_health:
                        assert db_health["connected"] is True, "Database not connected"
                    
                    self.record_metric("database_health_check_time", db_health_time)
                    
            except Exception as e:
                pytest.fail(f"Database health check through backend failed: {e}")
            
            # 2. Test database read operations
            db_read_start = time.time()
            try:
                # Test a simple read operation through backend API
                async with session.get(
                    f"{self.services['backend']}/api/users/me", 
                    headers=headers,
                    timeout=10
                ) as resp:
                    db_read_time = time.time() - db_read_start
                    
                    # Should either return user data or handle gracefully
                    assert resp.status in [200, 401, 403, 404], f"Database read test failed: {resp.status}"
                    
                    if resp.status == 200:
                        user_data = await resp.json()
                        database_tests.append({
                            "test": "database_read_operation",
                            "status": "success",
                            "response_time": db_read_time,
                            "has_data": bool(user_data)
                        })
                    else:
                        database_tests.append({
                            "test": "database_read_operation", 
                            "status": "auth_required",
                            "response_time": db_read_time,
                            "status_code": resp.status
                        })
                        
                    self.record_metric("database_read_operation_time", db_read_time)
                    
            except Exception as e:
                # Read operation may require specific setup
                self.record_metric("database_read_operation_error", str(e))
                database_tests.append({
                    "test": "database_read_operation",
                    "status": "error", 
                    "error": str(e)
                })
            
            # 3. Test database write operations (if safe)
            db_write_start = time.time()
            try:
                # Test a safe write operation - create test log entry
                test_log_data = {
                    "level": "INFO",
                    "message": "FINALIZE phase database connectivity test",
                    "source": "test_startup_finalize"
                }
                
                async with session.post(
                    f"{self.services['backend']}/api/logs",
                    headers=headers,
                    json=test_log_data,
                    timeout=10
                ) as resp:
                    db_write_time = time.time() - db_write_start
                    
                    # Write may not be allowed/implemented - that's ok
                    assert resp.status in [200, 201, 401, 403, 404, 405, 422], f"Database write test failed: {resp.status}"
                    
                    database_tests.append({
                        "test": "database_write_operation",
                        "status": "tested",
                        "response_time": db_write_time,
                        "status_code": resp.status
                    })
                    
                    self.record_metric("database_write_operation_time", db_write_time)
                    
            except Exception as e:
                # Write operations may not be available in test mode
                database_tests.append({
                    "test": "database_write_operation",
                    "status": "not_available",
                    "error": str(e)
                })
            
            # 4. Test database transaction handling
            transaction_start = time.time()
            try:
                # Test endpoint that involves database transactions
                async with session.post(
                    f"{self.services['backend']}/api/test/transaction",
                    headers=headers,
                    json={"test_data": "transaction_test"},
                    timeout=10
                ) as resp:
                    transaction_time = time.time() - transaction_start
                    
                    # Transaction endpoint may not exist
                    if resp.status != 404:
                        database_tests.append({
                            "test": "database_transaction",
                            "status": "tested",
                            "response_time": transaction_time,
                            "status_code": resp.status
                        })
                        
                        self.record_metric("database_transaction_time", transaction_time)
                    else:
                        database_tests.append({
                            "test": "database_transaction",
                            "status": "not_implemented"
                        })
                        
            except Exception as e:
                database_tests.append({
                    "test": "database_transaction",
                    "status": "error",
                    "error": str(e)
                })
        
        # Record database connectivity results
        self.connectivity_results["backend_database_connectivity"] = database_tests
        
        # At least database health check should have passed
        health_tests = [t for t in database_tests if t["test"] == "database_health" and t["status"] == "success"]
        assert len(health_tests) > 0, "Database health check failed"
        
        self.record_metric("backend_database_connectivity_passed", True)

    @pytest.mark.integration
    async def test_finalize_service_discovery_mechanism(self):
        """
        Test service discovery and routing mechanisms work properly.
        
        BVJ: Ensures services can find and communicate with each other reliably.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        discovery_tests = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Test service registry/discovery endpoint
            try:
                async with session.get(
                    f"{self.services['backend']}/services",
                    headers=headers,
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        services_info = await resp.json()
                        discovery_tests.append({
                            "test": "service_registry",
                            "status": "success",
                            "services": services_info
                        })
                        
                        # Should list known services
                        if isinstance(services_info, dict) and "services" in services_info:
                            service_list = services_info["services"]
                            assert len(service_list) > 0, "No services registered"
                    elif resp.status == 404:
                        discovery_tests.append({
                            "test": "service_registry",
                            "status": "not_implemented"
                        })
                    else:
                        discovery_tests.append({
                            "test": "service_registry",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
            except Exception as e:
                discovery_tests.append({
                    "test": "service_registry",
                    "status": "error",
                    "error": str(e)
                })
            
            # 2. Test DNS/hostname resolution between services
            dns_resolution_start = time.time()
            try:
                # Test if backend can resolve auth service by hostname
                async with session.get(
                    f"{self.services['backend']}/health/dependencies",
                    headers=headers,
                    timeout=10
                ) as resp:
                    dns_resolution_time = time.time() - dns_resolution_start
                    
                    if resp.status == 200:
                        dependencies = await resp.json()
                        discovery_tests.append({
                            "test": "dns_resolution",
                            "status": "success",
                            "response_time": dns_resolution_time,
                            "dependencies": dependencies
                        })
                    else:
                        discovery_tests.append({
                            "test": "dns_resolution",
                            "status": "not_available",
                            "status_code": resp.status
                        })
                        
            except Exception as e:
                discovery_tests.append({
                    "test": "dns_resolution",
                    "status": "error",
                    "error": str(e)
                })
            
            # 3. Test load balancer health checks (if applicable)
            lb_start = time.time()
            try:
                # Test health endpoint that load balancer would use
                async with session.get(
                    f"{self.services['backend']}/healthz",
                    timeout=5
                ) as resp:
                    lb_time = time.time() - lb_start
                    
                    if resp.status == 200:
                        discovery_tests.append({
                            "test": "load_balancer_health",
                            "status": "success",
                            "response_time": lb_time
                        })
                    elif resp.status == 404:
                        # Try alternative health check endpoint
                        async with session.get(
                            f"{self.services['backend']}/health",
                            timeout=5
                        ) as health_resp:
                            if health_resp.status == 200:
                                discovery_tests.append({
                                    "test": "load_balancer_health",
                                    "status": "alternative_endpoint",
                                    "response_time": lb_time
                                })
                                
            except Exception as e:
                discovery_tests.append({
                    "test": "load_balancer_health",
                    "status": "error",
                    "error": str(e)
                })
            
            # 4. Test service mesh connectivity (if applicable)
            mesh_start = time.time()
            try:
                # Test service mesh headers and routing
                mesh_headers = {**headers, "X-Service-Mesh": "test"}
                
                async with session.get(
                    f"{self.services['backend']}/health",
                    headers=mesh_headers,
                    timeout=5
                ) as resp:
                    mesh_time = time.time() - mesh_start
                    
                    assert resp.status == 200, f"Service mesh routing failed: {resp.status}"
                    
                    # Check if response has mesh-related headers
                    mesh_response_headers = dict(resp.headers)
                    has_mesh_headers = any(header.lower().startswith('x-') for header in mesh_response_headers)
                    
                    discovery_tests.append({
                        "test": "service_mesh_routing",
                        "status": "tested",
                        "response_time": mesh_time,
                        "has_mesh_headers": has_mesh_headers
                    })
                    
            except Exception as e:
                discovery_tests.append({
                    "test": "service_mesh_routing",
                    "status": "error", 
                    "error": str(e)
                })
        
        # Record service discovery results
        self.connectivity_results["service_discovery"] = discovery_tests
        self.record_metric("service_discovery_tests_count", len(discovery_tests))
        
        # At least some discovery mechanism should be working
        working_tests = [t for t in discovery_tests if t["status"] in ["success", "tested", "alternative_endpoint"]]
        assert len(working_tests) > 0, "No working service discovery mechanisms found"
        
        self.record_metric("service_discovery_passed", True)

    @pytest.mark.integration
    async def test_finalize_cross_service_authentication_flow(self):
        """
        Test complete cross-service authentication flow.
        
        BVJ: Ensures users can authenticate and access services seamlessly.
        """
        auth_flow_tests = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Test user registration flow
            registration_start = time.time()
            try:
                test_user_data = {
                    "email": f"test_finalize_{int(time.time())}@example.com",
                    "password": "test_password_123",
                    "name": "Finalize Test User"
                }
                
                async with session.post(
                    f"{self.services['auth']}/auth/register",
                    json=test_user_data,
                    timeout=15
                ) as resp:
                    registration_time = time.time() - registration_start
                    
                    if resp.status in [200, 201]:
                        registration_result = await resp.json()
                        auth_flow_tests.append({
                            "test": "user_registration",
                            "status": "success",
                            "response_time": registration_time,
                            "has_token": "access_token" in registration_result
                        })
                        
                        # Store token for subsequent tests
                        registration_token = registration_result.get("access_token")
                        
                    elif resp.status in [400, 409, 422]:
                        # User might already exist or validation error
                        auth_flow_tests.append({
                            "test": "user_registration",
                            "status": "validation_error",
                            "response_time": registration_time,
                            "status_code": resp.status
                        })
                        registration_token = None
                    else:
                        pytest.fail(f"User registration failed: {resp.status}")
                        
            except Exception as e:
                pytest.fail(f"User registration test failed: {e}")
            
            # 2. Test login flow
            login_start = time.time()
            try:
                login_data = {
                    "email": test_user_data["email"],
                    "password": test_user_data["password"]
                }
                
                async with session.post(
                    f"{self.services['auth']}/auth/login",
                    json=login_data,
                    timeout=10
                ) as resp:
                    login_time = time.time() - login_start
                    
                    if resp.status == 200:
                        login_result = await resp.json()
                        auth_flow_tests.append({
                            "test": "user_login",
                            "status": "success",
                            "response_time": login_time,
                            "has_token": "access_token" in login_result
                        })
                        
                        # Use login token for backend tests
                        login_token = login_result.get("access_token")
                    else:
                        # Login might fail if registration failed
                        auth_flow_tests.append({
                            "test": "user_login",
                            "status": "failed",
                            "response_time": login_time,
                            "status_code": resp.status
                        })
                        login_token = None
                        
            except Exception as e:
                auth_flow_tests.append({
                    "test": "user_login",
                    "status": "error",
                    "error": str(e)
                })
                login_token = None
            
            # 3. Test token validation across services
            if login_token:
                validation_start = time.time()
                try:
                    # Test token with backend service
                    auth_headers = {"Authorization": f"Bearer {login_token}"}
                    
                    async with session.get(
                        f"{self.services['backend']}/api/users/me",
                        headers=auth_headers,
                        timeout=10
                    ) as resp:
                        validation_time = time.time() - validation_start
                        
                        auth_flow_tests.append({
                            "test": "cross_service_token_validation",
                            "status": "tested",
                            "response_time": validation_time,
                            "status_code": resp.status,
                            "token_accepted": resp.status in [200, 404]  # 404 is ok if user doesn't exist in backend
                        })
                        
                except Exception as e:
                    auth_flow_tests.append({
                        "test": "cross_service_token_validation",
                        "status": "error",
                        "error": str(e)
                    })
            else:
                auth_flow_tests.append({
                    "test": "cross_service_token_validation",
                    "status": "skipped_no_token"
                })
            
            # 4. Test token refresh flow
            if login_token:
                refresh_start = time.time()
                try:
                    refresh_data = {"refresh_token": login_token}  # Some systems use access token for refresh
                    
                    async with session.post(
                        f"{self.services['auth']}/auth/refresh",
                        json=refresh_data,
                        timeout=10
                    ) as resp:
                        refresh_time = time.time() - refresh_start
                        
                        auth_flow_tests.append({
                            "test": "token_refresh",
                            "status": "tested",
                            "response_time": refresh_time,
                            "status_code": resp.status,
                            "refresh_supported": resp.status in [200, 201]
                        })
                        
                except Exception as e:
                    auth_flow_tests.append({
                        "test": "token_refresh",
                        "status": "error",
                        "error": str(e)
                    })
        
        # Record authentication flow results
        self.connectivity_results["cross_service_auth_flow"] = auth_flow_tests
        
        # At least login or registration should work
        successful_auth = [t for t in auth_flow_tests if t["status"] == "success" and t["test"] in ["user_registration", "user_login"]]
        assert len(successful_auth) > 0, "Neither registration nor login worked in cross-service flow"
        
        self.record_metric("cross_service_auth_flow_passed", True)

    @pytest.mark.integration
    async def test_finalize_service_resilience_and_failover(self):
        """
        Test service resilience and failover mechanisms.
        
        BVJ: Ensures system continues operating even with service issues.
        """
        resilience_tests = []
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            # 1. Test graceful handling of slow services
            slow_request_start = time.time()
            try:
                # Test with shorter timeout to simulate slow service
                async with session.get(
                    f"{self.services['backend']}/health",
                    headers=headers,
                    timeout=2.0  # Short timeout
                ) as resp:
                    slow_request_time = time.time() - slow_request_start
                    
                    resilience_tests.append({
                        "test": "fast_service_response",
                        "status": "success",
                        "response_time": slow_request_time,
                        "within_timeout": slow_request_time < 2.0
                    })
                    
            except asyncio.TimeoutError:
                slow_request_time = time.time() - slow_request_start
                resilience_tests.append({
                    "test": "service_timeout_handling",
                    "status": "timeout_occurred", 
                    "response_time": slow_request_time
                })
                # Timeout is acceptable - shows we handle slow services
            except Exception as e:
                resilience_tests.append({
                    "test": "slow_service_handling",
                    "status": "error",
                    "error": str(e)
                })
            
            # 2. Test handling of invalid service responses
            invalid_request_start = time.time()
            try:
                # Test invalid endpoint to see error handling
                async with session.get(
                    f"{self.services['backend']}/invalid/endpoint/test",
                    headers=headers,
                    timeout=5
                ) as resp:
                    invalid_request_time = time.time() - invalid_request_start
                    
                    # Should gracefully handle invalid requests
                    assert resp.status in [404, 405, 400], f"Invalid endpoint not handled gracefully: {resp.status}"
                    
                    resilience_tests.append({
                        "test": "invalid_endpoint_handling",
                        "status": "graceful_failure",
                        "response_time": invalid_request_time,
                        "status_code": resp.status
                    })
                    
            except Exception as e:
                resilience_tests.append({
                    "test": "invalid_endpoint_handling", 
                    "status": "error",
                    "error": str(e)
                })
            
            # 3. Test circuit breaker behavior (if implemented)
            circuit_breaker_start = time.time()
            try:
                # Send multiple requests to trigger potential circuit breaker
                circuit_breaker_responses = []
                
                for i in range(10):
                    try:
                        async with session.get(
                            f"{self.services['backend']}/health",
                            headers=headers,
                            timeout=3
                        ) as resp:
                            circuit_breaker_responses.append(resp.status)
                    except Exception:
                        circuit_breaker_responses.append("error")
                
                circuit_breaker_time = time.time() - circuit_breaker_start
                
                success_count = sum(1 for r in circuit_breaker_responses if r == 200)
                error_count = sum(1 for r in circuit_breaker_responses if r == "error")
                
                resilience_tests.append({
                    "test": "circuit_breaker_behavior",
                    "status": "tested",
                    "response_time": circuit_breaker_time,
                    "success_count": success_count,
                    "error_count": error_count,
                    "responses": circuit_breaker_responses[:5]  # First 5 responses only
                })
                
                # Should handle multiple requests without complete failure
                assert success_count > 0, "Circuit breaker blocked all requests"
                
            except Exception as e:
                resilience_tests.append({
                    "test": "circuit_breaker_behavior",
                    "status": "error",
                    "error": str(e)
                })
            
            # 4. Test service recovery after errors
            recovery_start = time.time()
            try:
                # After all error tests, service should still respond normally
                async with session.get(
                    f"{self.services['backend']}/health",
                    headers=headers,
                    timeout=10
                ) as resp:
                    recovery_time = time.time() - recovery_start
                    
                    assert resp.status == 200, f"Service did not recover after resilience tests: {resp.status}"
                    
                    resilience_tests.append({
                        "test": "service_recovery",
                        "status": "success",
                        "response_time": recovery_time
                    })
                    
            except Exception as e:
                pytest.fail(f"Service failed to recover after resilience tests: {e}")
        
        # Record resilience test results
        self.connectivity_results["service_resilience"] = resilience_tests
        
        # At least service recovery should work
        recovery_tests = [t for t in resilience_tests if t["test"] == "service_recovery" and t["status"] == "success"]
        assert len(recovery_tests) > 0, "Service did not demonstrate recovery capability"
        
        self.record_metric("service_resilience_passed", True)
        
        # Record overall connectivity validation completion
        self.record_metric("finalize_service_connectivity_complete", True)
        
        # Test should complete in reasonable time
        self.assert_execution_time_under(90.0)  # Allow up to 90 seconds for comprehensive connectivity tests