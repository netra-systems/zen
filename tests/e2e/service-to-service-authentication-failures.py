"""
Service-to-Service Authentication Failures - Iteration 2 Audit Critical Issues

This test file focuses on the complete breakdown of service-to-service authentication
identified in the Iteration 2 audit across the entire Netra system:

**CRITICAL FINDINGS:**
1. Frontend [U+2194] Backend authentication completely non-functional (100% 403 rate)
2. Backend [U+2194] Auth Service communication failures
3. Auth Service [U+2194] Database authentication state corruption  
4. All service-to-service authentication taking 6.2+ seconds before failing
5. No authentication recovery between any services

**EXPECTED TO FAIL**: These tests replicate the complete service-to-service auth breakdown

Services Involved:
- Frontend Service (netra-frontend)
- Backend Service (netra-backend)  
- Auth Service (auth_service)
- Database Services (PostgreSQL, ClickHouse, Redis)

Root Causes (Service Integration):
- Service discovery failures between components
- Mutual TLS configuration missing or broken
- Service account credentials not shared between services
- JWT signing key synchronization failures across services
- Network policies blocking inter-service communication
- Service mesh authentication configuration errors
"""

import asyncio
import pytest
import httpx
import time
import json
import os
from fastapi import HTTPException, status
import jwt
from datetime import datetime, timedelta, timezone

from shared.isolated_environment import IsolatedEnvironment
from test_framework.base_e2e_test import BaseE2ETest
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


@pytest.mark.e2e
@pytest.mark.critical
class TestServiceToServiceAuthenticationFailures(BaseE2ETest):
    """Test complete service-to-service authentication system breakdown"""

    def setup_method(self):
        """Set up cross-service test environment"""
        super().setup_method()
        self.services = {
            'frontend': 'http://localhost:3000',
            'backend': 'http://localhost:8000', 
            'auth_service': 'http://localhost:8080',
            'postgres': 'postgresql://localhost:5432',
            'clickhouse': 'http://localhost:8123',
            'redis': 'redis://localhost:6379'
        }
        self.service_tokens = {}
        self.start_time = time.time()

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_frontend_to_backend_authentication_complete_failure(self):
        """
        EXPECTED TO FAIL - CRITICAL CROSS-SERVICE ISSUE
        Frontend should authenticate with Backend but 100% failure rate with 403
        Root cause: Complete breakdown of frontend  ->  backend authentication
        """
        async with httpx.AsyncClient() as client:
            # Frontend trying to authenticate with Backend
            try:
                response = await client.get(
                    f"{self.services['backend']}/api/threads",
                    headers={
                        'Authorization': 'Bearer frontend-service-token',
                        'X-Service-Name': 'netra-frontend',
                        'X-Service-Version': '1.0.0',
                        'X-Request-ID': 'test-frontend-to-backend-001',
                        'Origin': self.services['frontend']
                    },
                    timeout=10.0
                )
                
                # Should authenticate successfully but will fail with 403
                assert response.status_code == 200
                assert response.headers.get('content-type') == 'application/json'
                
                data = response.json()
                assert isinstance(data, list)  # Should return threads list
                
                # Should NOT get authentication failure
                assert 'error' not in data
                assert 'Authentication failed' not in str(data)
                
            except httpx.ConnectError:
                pytest.fail("Backend service not reachable from Frontend")
            except httpx.TimeoutException:
                pytest.fail("Frontend  ->  Backend authentication timeout (> 10 seconds)")
            except Exception as e:
                pytest.fail(f"Frontend  ->  Backend authentication failed: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_backend_to_auth_service_communication_failure(self):
        """
        EXPECTED TO FAIL - CRITICAL AUTH SERVICE ISSUE
        Backend should communicate with Auth Service for token validation
        Root cause: Backend cannot reach Auth Service for authentication
        """
        async with httpx.AsyncClient() as client:
            # Backend trying to validate token with Auth Service
            try:
                response = await client.post(
                    f"{self.services['auth_service']}/auth/validate",
                    json={
                        'token': 'test-user-token-from-backend',
                        'requesting_service': 'netra-backend',
                        'validation_type': 'user_token'
                    },
                    headers={
                        'X-Service-Name': 'netra-backend',
                        'X-Service-Account': 'netra-backend@staging.iam.gserviceaccount.com',
                        'Content-Type': 'application/json'
                    },
                    timeout=5.0
                )
                
                # Should validate token successfully
                assert response.status_code == 200
                
                data = response.json()
                assert data.get('valid') is True
                assert 'user_id' in data
                
                # Should NOT get communication failure
                assert data.get('error') != 'Service communication failed'
                
            except httpx.ConnectError:
                pytest.fail("Auth Service not reachable from Backend")
            except httpx.TimeoutException:
                pytest.fail("Backend  ->  Auth Service communication timeout")
            except Exception as e:
                pytest.fail(f"Backend  ->  Auth Service communication failed: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_auth_service_to_database_authentication_state_corruption(self):
        """
        EXPECTED TO FAIL - CRITICAL DATABASE AUTH ISSUE  
        Auth Service should maintain consistent authentication state in database
        Root cause: Authentication state corruption between Auth Service and Database
        """
        # Test authentication state consistency across database operations
        test_user_id = "test-user-auth-state-001"
        
        async with httpx.AsyncClient() as client:
            # 1. Create user authentication state
            try:
                create_response = await client.post(
                    f"{self.services['auth_service']}/auth/users",
                    json={
                        'user_id': test_user_id,
                        'email': 'test-auth-state@example.com',
                        'auth_provider': 'google',
                        'auth_state': 'active'
                    },
                    headers={'Content-Type': 'application/json'},
                    timeout=5.0
                )
                
                assert create_response.status_code == 201
                
                # 2. Retrieve authentication state
                retrieve_response = await client.get(
                    f"{self.services['auth_service']}/auth/users/{test_user_id}/state",
                    timeout=5.0
                )
                
                assert retrieve_response.status_code == 200
                
                state_data = retrieve_response.json()
                assert state_data.get('user_id') == test_user_id
                assert state_data.get('auth_state') == 'active'
                
                # Should NOT have authentication state corruption
                assert state_data.get('error') != 'Authentication state corrupted'
                assert 'corrupted' not in str(state_data)
                
            except httpx.TimeoutException:
                pytest.fail("Auth Service  ->  Database operation timeout")
            except Exception as e:
                pytest.fail(f"Auth Service  ->  Database state corruption: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_all_service_authentication_latency_exceeds_6_seconds(self):
        """
        EXPECTED TO FAIL - CRITICAL LATENCY ISSUE
        All service-to-service authentication should complete quickly
        Root cause: Every service authentication attempt takes 6.2+ seconds
        """
        service_pairs = [
            ('frontend', 'backend', '/api/threads'),
            ('backend', 'auth_service', '/auth/validate'), 
            ('backend', 'backend', '/api/health'),  # Self-check
            ('frontend', 'auth_service', '/auth/config')
        ]
        
        latency_results = {}
        
        async with httpx.AsyncClient() as client:
            for source, target, endpoint in service_pairs:
                start_time = time.time()
                
                try:
                    response = await client.get(
                        f"{self.services[target]}{endpoint}",
                        headers={
                            'Authorization': 'Bearer service-to-service-token',
                            'X-Source-Service': source,
                            'X-Target-Service': target
                        },
                        timeout=8.0  # Allow up to 8 seconds to capture the 6.2+ issue
                    )
                    
                    end_time = time.time()
                    latency = end_time - start_time
                    latency_results[f"{source}_to_{target}"] = latency
                    
                    # Each authentication should complete within 2 seconds
                    assert latency < 2.0, f"{source}  ->  {target} took {latency:.2f}s (should be < 2.0s)"
                    
                except httpx.TimeoutException:
                    end_time = time.time()
                    latency = end_time - start_time
                    latency_results[f"{source}_to_{target}"] = latency
                    pytest.fail(f"{source}  ->  {target} authentication timeout after {latency:.2f}s")
                
                except Exception as e:
                    end_time = time.time() 
                    latency = end_time - start_time
                    latency_results[f"{source}_to_{target}"] = latency
                    pytest.fail(f"{source}  ->  {target} failed after {latency:.2f}s: {str(e)}")
        
        # Report latency issues for debugging
        slow_services = {k: v for k, v in latency_results.items() if v > 2.0}
        if slow_services:
            pytest.fail(f"Slow service authentications: {slow_services}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_service_discovery_authentication_failures(self):
        """
        EXPECTED TO FAIL - MEDIUM SERVICE DISCOVERY ISSUE
        Services should discover each other and authenticate automatically
        Root cause: Service discovery not providing authentication context
        """
        # Test service discovery with authentication
        async with httpx.AsyncClient() as client:
            try:
                # Frontend discovering Backend through service discovery
                discovery_response = await client.get(
                    f"{self.services['backend']}/api/discovery/services",
                    headers={
                        'X-Discovery-Request': 'netra-frontend',
                        'X-Service-Auth': 'discovery-token'
                    },
                    timeout=5.0
                )
                
                assert discovery_response.status_code == 200
                
                services = discovery_response.json()
                assert 'netra-backend' in services
                assert 'auth_endpoint' in services['netra-backend']
                
                # Should provide authentication information for service-to-service calls
                backend_info = services['netra-backend']
                assert 'auth_token' in backend_info or 'service_account' in backend_info
                
                # Should NOT get discovery authentication failure
                assert backend_info.get('error') != 'Service discovery authentication failed'
                
            except Exception as e:
                pytest.fail(f"Service discovery authentication failed: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_mutual_tls_configuration_missing_or_broken(self):
        """
        EXPECTED TO FAIL - CRITICAL MTLS ISSUE
        Services should use mutual TLS for secure communication
        Root cause: mTLS configuration missing or certificates invalid
        """
        # Test mTLS between services
        async with httpx.AsyncClient() as client:
            try:
                # Attempt secure service-to-service communication with mTLS
                response = await client.get(
                    f"{self.services['backend']}/api/secure/service-info",
                    headers={
                        'X-mTLS-Client': 'netra-frontend',
                        'X-Client-Certificate': 'test-client-cert-data'
                    },
                    timeout=5.0
                )
                
                # Should establish mTLS connection successfully  
                assert response.status_code == 200
                
                data = response.json()
                assert data.get('mtls_verified') is True
                assert data.get('client_service') == 'netra-frontend'
                
                # Should NOT get mTLS failure
                assert data.get('error') != 'mTLS verification failed'
                assert 'certificate' not in data.get('errors', [])
                
            except Exception as e:
                pytest.fail(f"mTLS configuration failure: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_service_account_credentials_not_shared_between_services(self):
        """
        EXPECTED TO FAIL - CRITICAL CREDENTIAL SHARING ISSUE
        Service account credentials should be accessible to all services
        Root cause: Service credentials not properly shared or accessible
        """
        service_account_tests = [
            ('frontend', 'netra-frontend@staging.iam.gserviceaccount.com'),
            ('backend', 'netra-backend@staging.iam.gserviceaccount.com'),
            ('auth_service', 'netra-auth@staging.iam.gserviceaccount.com')
        ]
        
        async with httpx.AsyncClient() as client:
            for service_name, expected_service_account in service_account_tests:
                try:
                    response = await client.get(
                        f"{self.services[service_name]}/api/service-account/info",
                        headers={'X-Internal-Request': 'true'},
                        timeout=5.0
                    )
                    
                    assert response.status_code == 200
                    
                    sa_info = response.json()
                    assert sa_info.get('service_account') == expected_service_account
                    assert sa_info.get('credentials_valid') is True
                    
                    # Should NOT have credential access issues
                    assert sa_info.get('error') != 'Service account credentials not accessible'
                    
                except Exception as e:
                    pytest.fail(f"Service account credentials not accessible for {service_name}: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_jwt_signing_key_synchronization_failures_across_services(self):
        """
        EXPECTED TO FAIL - CRITICAL JWT KEY SYNC ISSUE
        JWT signing keys should be synchronized across all services
        Root cause: Services using different or outdated JWT signing keys
        """
        # Test JWT key synchronization across services
        test_token_payload = {
            'sub': 'test-user-jwt-sync',
            'iat': datetime.now(timezone.utc).timestamp(),
            'exp': (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp(),
            'iss': 'netra-auth',
            'aud': 'netra-services'
        }
        
        # Generate token with current key
        test_token = jwt.encode(test_token_payload, 'test-signing-key', algorithm='HS256')
        
        services_to_test = ['backend', 'auth_service']
        
        async with httpx.AsyncClient() as client:
            for service in services_to_test:
                try:
                    response = await client.post(
                        f"{self.services[service]}/api/jwt/validate",
                        json={'token': test_token},
                        headers={'Content-Type': 'application/json'},
                        timeout=5.0
                    )
                    
                    assert response.status_code == 200
                    
                    validation_result = response.json()
                    assert validation_result.get('valid') is True
                    assert validation_result.get('payload', {}).get('sub') == 'test-user-jwt-sync'
                    
                    # Should NOT have key synchronization issues
                    assert validation_result.get('error') != 'JWT signature verification failed'
                    assert validation_result.get('error') != 'Unknown signing key'
                    
                except Exception as e:
                    pytest.fail(f"JWT key synchronization failure for {service}: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_authentication_recovery_between_services_non_existent(self):
        """
        EXPECTED TO FAIL - MEDIUM RECOVERY ISSUE
        Services should recover from temporary authentication failures
        Root cause: No authentication recovery mechanisms between services
        """
        # Test authentication recovery between Frontend and Backend
        recovery_attempt_count = 0
        
        async with httpx.AsyncClient() as client:
            # Simulate authentication recovery scenario
            for attempt in range(3):  # Try 3 times with recovery
                recovery_attempt_count += 1
                
                try:
                    response = await client.get(
                        f"{self.services['backend']}/api/threads",
                        headers={
                            'Authorization': f'Bearer recovery-token-attempt-{recovery_attempt_count}',
                            'X-Recovery-Attempt': str(recovery_attempt_count),
                            'X-Service-Name': 'netra-frontend'
                        },
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        # Authentication recovery succeeded
                        break
                    elif response.status_code == 401 and attempt < 2:
                        # Try recovery mechanism
                        await asyncio.sleep(1)  # Brief delay for recovery
                        continue
                    else:
                        # Recovery failed
                        data = response.json()
                        pytest.fail(f"Authentication recovery failed after {recovery_attempt_count} attempts: {data}")
                        
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(1)  # Brief delay for recovery
                        continue
                    else:
                        pytest.fail(f"No authentication recovery after {recovery_attempt_count} attempts: {str(e)}")
            
            # Should have succeeded with recovery mechanism
            assert recovery_attempt_count <= 3, "Should recover within 3 attempts"

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_network_policies_blocking_inter_service_communication(self):
        """
        EXPECTED TO FAIL - CRITICAL NETWORK POLICY ISSUE
        Network policies should allow authenticated inter-service communication
        Root cause: Network policies blocking service-to-service authentication traffic
        """
        # Test network policies for service communication
        service_communication_tests = [
            ('frontend', 'backend', 'HTTP'),
            ('backend', 'auth_service', 'HTTP'),
            ('backend', 'postgres', 'TCP'),
            ('auth_service', 'postgres', 'TCP')
        ]
        
        async with httpx.AsyncClient() as client:
            for source, target, protocol in service_communication_tests:
                try:
                    if protocol == 'HTTP':
                        response = await client.get(
                            f"{self.services[target]}/api/health",
                            headers={
                                'X-Source-Service': source,
                                'X-Network-Policy-Check': 'true'
                            },
                            timeout=5.0
                        )
                        
                        assert response.status_code == 200
                        
                        health_data = response.json()
                        assert health_data.get('status') == 'healthy'
                        
                        # Should NOT be blocked by network policies
                        assert health_data.get('error') != 'Network policy blocked'
                        assert 'blocked' not in health_data.get('message', '')
                    
                except httpx.ConnectError as e:
                    if 'Connection refused' in str(e) or 'blocked' in str(e):
                        pytest.fail(f"Network policy blocking {source}  ->  {target} communication: {str(e)}")
                    else:
                        pytest.fail(f"Network connectivity issue {source}  ->  {target}: {str(e)}")
                        
                except Exception as e:
                    pytest.fail(f"Service communication failure {source}  ->  {target}: {str(e)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_service_mesh_authentication_configuration_errors(self):
        """
        EXPECTED TO FAIL - CRITICAL SERVICE MESH ISSUE
        Service mesh should provide authentication between services
        Root cause: Service mesh authentication configuration missing or incorrect
        """
        async with httpx.AsyncClient() as client:
            try:
                # Test service mesh authentication configuration
                response = await client.get(
                    f"{self.services['backend']}/api/service-mesh/auth-config",
                    headers={
                        'X-Service-Mesh': 'istio',
                        'X-Auth-Check': 'service-mesh'
                    },
                    timeout=5.0
                )
                
                assert response.status_code == 200
                
                mesh_config = response.json()
                assert mesh_config.get('service_mesh_enabled') is True
                assert mesh_config.get('authentication_policy') == 'mutual_tls'
                assert 'certificates' in mesh_config
                
                # Should NOT have service mesh authentication errors
                assert mesh_config.get('error') != 'Service mesh authentication not configured'
                assert mesh_config.get('mtls_status') != 'failed'
                
            except Exception as e:
                pytest.fail(f"Service mesh authentication configuration error: {str(e)}")

    async def teardown_method(self):
        """Clean up after service-to-service authentication tests"""
        # Log test results for debugging
        end_time = time.time()
        test_duration = end_time - self.start_time
        print(f"Service-to-service authentication test duration: {test_duration:.2f} seconds")
        
        await super().teardown_method()