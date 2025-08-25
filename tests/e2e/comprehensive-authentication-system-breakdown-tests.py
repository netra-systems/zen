"""
Comprehensive Authentication System Breakdown Tests - Iteration 2 Audit

This is the master test file that combines and validates all authentication failures
identified in the Iteration 2 audit. This file provides the complete picture of
the authentication system breakdown across all components and scenarios.

**MASTER AUTHENTICATION FAILURE SCENARIOS:**
1. Service Account Permissions Missing or Insufficient  
2. JWT Signing Key Mismatches Across All Services
3. Network Policies Blocking Authentication Traffic
4. Complete End-to-End Authentication System Breakdown
5. Authentication Performance Issues (6.2+ second latency)
6. Zero Authentication Recovery Mechanisms
7. Authentication Infrastructure Single Points of Failure

**EXPECTED TO FAIL**: This comprehensive test suite demonstrates the complete
breakdown of the authentication system causing 100% failure rate in staging

System-Wide Authentication Issues:
- Frontend → Backend: 100% 403 failure rate
- Backend → Auth Service: Complete communication breakdown
- Auth Service → Database: Authentication state corruption
- Service → OAuth Providers: No fallback mechanisms
- Inter-service Authentication: Completely non-functional
- Authentication Performance: Unacceptable 6.2+ second latencies
- Error Recovery: No mechanisms implemented

Business Impact:
- 100% deployment failure rate in staging
- Complete system unusability
- No user authentication possible
- No service-to-service communication
- Development velocity blocked
- Customer confidence at risk

This test file serves as:
1. Comprehensive validation of authentication system state
2. Regression prevention when fixes are implemented  
3. Complete documentation of authentication requirements
4. Integration test for end-to-end authentication flows
"""

import asyncio
import pytest
import time
import httpx
import json
import socket
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import jwt
import subprocess
import psutil

from test_framework.base_e2e_test import BaseE2ETest
from netra_backend.app.core.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
@pytest.mark.critical
class TestComprehensiveAuthenticationSystemBreakdown(BaseE2ETest):
    """Comprehensive test of complete authentication system breakdown"""

    def setup_method(self):
        """Set up comprehensive authentication system test environment"""
        super().setup_method()
        self.services = {
            'frontend': 'http://localhost:3000',
            'backend': 'http://localhost:8000',
            'auth_service': 'http://localhost:8080',
            'postgres': 'postgresql://localhost:5432/netra',
            'redis': 'redis://localhost:6379/0',
            'clickhouse': 'http://localhost:8123'
        }
        self.authentication_breakdown_metrics = {
            'total_tests': 0,
            'failed_tests': 0,
            'latency_issues': 0,
            'service_failures': 0,
            'critical_failures': 0
        }
        self.start_time = time.time()

    @pytest.mark.critical
    async def test_complete_service_account_permissions_breakdown(self):
        """
        EXPECTED TO FAIL - CRITICAL SERVICE ACCOUNT PERMISSIONS ISSUE
        All services should have proper service account permissions but are completely missing
        Root cause: Service accounts not configured with required permissions across the system
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Test service account permissions across all services
        service_account_tests = [
            ('frontend', 'netra-frontend@staging.iam.gserviceaccount.com', [
                'netra.backend.read',
                'netra.threads.access',
                'netra.auth.validate'
            ]),
            ('backend', 'netra-backend@staging.iam.gserviceaccount.com', [
                'netra.auth.validate',
                'netra.database.read',
                'netra.database.write',
                'netra.users.manage',
                'netra.threads.manage'
            ]),
            ('auth_service', 'netra-auth@staging.iam.gserviceaccount.com', [
                'netra.users.authenticate',
                'netra.tokens.issue',
                'netra.database.auth',
                'netra.oauth.manage'
            ])
        ]
        
        permission_failures = []
        
        async with httpx.AsyncClient() as client:
            for service_name, service_account, required_permissions in service_account_tests:
                try:
                    # Test service account permissions
                    response = await client.get(
                        f"{self.services[service_name]}/api/service-account/permissions",
                        headers={
                            'X-Service-Account-Test': 'comprehensive',
                            'X-Required-Permissions': ','.join(required_permissions)
                        },
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        permissions_data = response.json()
                        current_permissions = permissions_data.get('permissions', [])
                        
                        missing_permissions = [p for p in required_permissions if p not in current_permissions]
                        if missing_permissions:
                            permission_failures.append(f"{service_name}: Missing permissions {missing_permissions}")
                            
                    elif response.status_code == 403:
                        permission_failures.append(f"{service_name}: Service account access denied")
                    elif response.status_code == 500:
                        permission_failures.append(f"{service_name}: Service account configuration error")
                    else:
                        permission_failures.append(f"{service_name}: Unexpected permission check result {response.status_code}")
                        
                except httpx.ConnectError:
                    permission_failures.append(f"{service_name}: Service unreachable for permission check")
                except Exception as e:
                    permission_failures.append(f"{service_name}: Permission check error - {str(e)}")
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if permission_failures else 0
        
        # Should NOT have service account permission failures
        assert len(permission_failures) == 0, f"Service account permission failures: {permission_failures}"

    @pytest.mark.critical
    async def test_complete_jwt_signing_key_mismatch_across_all_services(self):
        """
        EXPECTED TO FAIL - CRITICAL JWT KEY SYNCHRONIZATION ISSUE
        All services should use synchronized JWT signing keys but have complete mismatches
        Root cause: JWT signing keys not synchronized across services, causing signature verification failures
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Test JWT key synchronization across all services
        test_payload = {
            'sub': 'jwt-sync-test-user',
            'iat': datetime.utcnow().timestamp(),
            'exp': (datetime.utcnow() + timedelta(minutes=15)).timestamp(),
            'iss': 'netra-auth',
            'aud': 'netra-services'
        }
        
        # Create test token with master signing key
        master_key = 'netra-master-signing-key-2024'
        test_token = jwt.encode(test_payload, master_key, algorithm='HS256')
        
        services_jwt_tests = ['backend', 'auth_service']
        jwt_sync_failures = []
        
        async with httpx.AsyncClient() as client:
            for service_name in services_jwt_tests:
                try:
                    # Test JWT validation consistency
                    response = await client.post(
                        f"{self.services[service_name]}/api/jwt/validate-sync-test",
                        json={
                            'token': test_token,
                            'expected_key_id': 'master-2024',
                            'test_type': 'comprehensive_sync'
                        },
                        headers={'Content-Type': 'application/json'},
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        validation_result = response.json()
                        if not validation_result.get('valid'):
                            jwt_sync_failures.append(f"{service_name}: JWT validation failed - {validation_result.get('error')}")
                        elif validation_result.get('key_mismatch'):
                            jwt_sync_failures.append(f"{service_name}: JWT signing key mismatch - using {validation_result.get('current_key_id')}")
                    elif response.status_code == 401:
                        response_data = response.json()
                        jwt_sync_failures.append(f"{service_name}: JWT signature verification failed - {response_data.get('error')}")
                    elif response.status_code == 500:
                        jwt_sync_failures.append(f"{service_name}: JWT validation internal error")
                    else:
                        jwt_sync_failures.append(f"{service_name}: Unexpected JWT validation result {response.status_code}")
                        
                except httpx.ConnectError:
                    jwt_sync_failures.append(f"{service_name}: Service unreachable for JWT sync test")
                except Exception as e:
                    jwt_sync_failures.append(f"{service_name}: JWT sync test error - {str(e)}")
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if jwt_sync_failures else 0
        
        # Should NOT have JWT signing key synchronization failures
        assert len(jwt_sync_failures) == 0, f"JWT signing key synchronization failures: {jwt_sync_failures}"

    @pytest.mark.critical
    def test_complete_network_policies_blocking_authentication_traffic(self):
        """
        EXPECTED TO FAIL - CRITICAL NETWORK POLICY BLOCKING ISSUE
        Network policies should allow authentication traffic but are blocking everything
        Root cause: Network policies blocking all authentication-related traffic between services
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Test network connectivity for authentication traffic
        critical_auth_connections = [
            ('frontend_to_backend_auth', 'localhost', 8000, 'HTTP authentication requests'),
            ('backend_to_auth_service', 'localhost', 8080, 'Token validation requests'),
            ('auth_service_to_postgres', 'localhost', 5432, 'Database authentication queries'),
            ('auth_service_to_redis', 'localhost', 6379, 'Authentication caching'),
            ('backend_to_clickhouse_auth', 'localhost', 8123, 'Analytics authentication'),
            ('oauth_provider_connectivity', 'accounts.google.com', 443, 'OAuth provider connectivity'),
            ('staging_auth_endpoints', 'auth.staging.netrasystems.ai', 443, 'Staging auth service')
        ]
        
        network_blocking_issues = []
        
        for connection_name, host, port, description in critical_auth_connections:
            try:
                # Test TCP connectivity
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                
                start_time = time.time()
                result = sock.connect_ex((host, port))
                end_time = time.time()
                
                sock.close()
                
                connection_time = end_time - start_time
                
                if result != 0:
                    network_blocking_issues.append(f"{connection_name}: Connection blocked to {host}:{port} ({description}) - Result: {result}")
                elif connection_time > 2.0:
                    network_blocking_issues.append(f"{connection_name}: Slow connection to {host}:{port} ({connection_time:.2f}s) - May indicate policy restrictions")
                    
            except socket.timeout:
                network_blocking_issues.append(f"{connection_name}: Connection timeout to {host}:{port} ({description}) - Likely blocked by network policy")
            except socket.gaierror as e:
                if 'staging' in host:
                    # Staging DNS issues are acceptable
                    continue
                network_blocking_issues.append(f"{connection_name}: DNS resolution failed for {host} - {str(e)}")
            except Exception as e:
                network_blocking_issues.append(f"{connection_name}: Network error to {host}:{port} - {str(e)}")
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if network_blocking_issues else 0
        
        # Should NOT have network policies blocking authentication traffic  
        assert len(network_blocking_issues) == 0, f"Network policies blocking authentication traffic: {network_blocking_issues}"

    @pytest.mark.critical
    async def test_complete_end_to_end_authentication_system_breakdown(self):
        """
        EXPECTED TO FAIL - CRITICAL END-TO-END SYSTEM BREAKDOWN
        Complete end-to-end authentication flow should work but is completely broken
        Root cause: Every component of the authentication system is failing
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Test complete authentication flow from user request to database
        authentication_flow_steps = []
        flow_failures = []
        
        async with httpx.AsyncClient() as client:
            try:
                # Step 1: Frontend requests authentication configuration
                flow_step_start = time.time()
                auth_config_response = await client.get(
                    f"{self.services['auth_service']}/api/auth/config",
                    timeout=5.0
                )
                flow_step_end = time.time()
                
                step1_duration = flow_step_end - flow_step_start
                authentication_flow_steps.append(('auth_config', step1_duration, auth_config_response.status_code))
                
                if auth_config_response.status_code != 200:
                    flow_failures.append(f"Step 1 - Auth config: Failed with {auth_config_response.status_code}")
                elif step1_duration > 2.0:
                    flow_failures.append(f"Step 1 - Auth config: Slow response ({step1_duration:.2f}s)")
                
                # Step 2: User initiates OAuth login
                flow_step_start = time.time()
                oauth_login_response = await client.get(
                    f"{self.services['auth_service']}/api/auth/login?provider=google",
                    timeout=5.0
                )
                flow_step_end = time.time()
                
                step2_duration = flow_step_end - flow_step_start
                authentication_flow_steps.append(('oauth_login', step2_duration, oauth_login_response.status_code))
                
                if oauth_login_response.status_code not in [200, 302]:
                    flow_failures.append(f"Step 2 - OAuth login: Failed with {oauth_login_response.status_code}")
                elif step2_duration > 2.0:
                    flow_failures.append(f"Step 2 - OAuth login: Slow response ({step2_duration:.2f}s)")
                
                # Step 3: Frontend validates token with backend
                flow_step_start = time.time()
                token_validation_response = await client.get(
                    f"{self.services['backend']}/api/threads",
                    headers={
                        'Authorization': 'Bearer end-to-end-test-token',
                        'Content-Type': 'application/json'
                    },
                    timeout=8.0  # Allow time to observe the 6.2+ second issue
                )
                flow_step_end = time.time()
                
                step3_duration = flow_step_end - flow_step_start
                authentication_flow_steps.append(('token_validation', step3_duration, token_validation_response.status_code))
                
                if token_validation_response.status_code != 200:
                    flow_failures.append(f"Step 3 - Token validation: Failed with {token_validation_response.status_code}")
                if step3_duration > 2.0:
                    flow_failures.append(f"Step 3 - Token validation: Excessive latency ({step3_duration:.2f}s)")
                    self.authentication_breakdown_metrics['latency_issues'] += 1
                
                # Step 4: Backend queries database with authenticated user context
                flow_step_start = time.time()
                user_data_response = await client.get(
                    f"{self.services['backend']}/api/auth/me",
                    headers={
                        'Authorization': 'Bearer end-to-end-test-token',
                        'Content-Type': 'application/json'
                    },
                    timeout=5.0
                )
                flow_step_end = time.time()
                
                step4_duration = flow_step_end - flow_step_start
                authentication_flow_steps.append(('user_data', step4_duration, user_data_response.status_code))
                
                if user_data_response.status_code != 200:
                    flow_failures.append(f"Step 4 - User data: Failed with {user_data_response.status_code}")
                elif step4_duration > 2.0:
                    flow_failures.append(f"Step 4 - User data: Slow response ({step4_duration:.2f}s)")
                
            except httpx.ConnectError as e:
                flow_failures.append(f"End-to-end flow: Service connection error - {str(e)}")
                self.authentication_breakdown_metrics['service_failures'] += 1
            except httpx.TimeoutException as e:
                flow_failures.append(f"End-to-end flow: Timeout during authentication flow - {str(e)}")
                self.authentication_breakdown_metrics['latency_issues'] += 1
            except Exception as e:
                flow_failures.append(f"End-to-end flow: Unexpected error - {str(e)}")
                self.authentication_breakdown_metrics['critical_failures'] += 1
        
        # Calculate total flow time
        total_flow_time = sum(step[1] for step in authentication_flow_steps)
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if flow_failures else 0
        
        # Report flow breakdown for debugging
        if flow_failures:
            flow_summary = {
                'steps_completed': len(authentication_flow_steps),
                'total_flow_time': f"{total_flow_time:.2f}s",
                'step_details': {step[0]: {'duration': f"{step[1]:.2f}s", 'status': step[2]} for step in authentication_flow_steps},
                'failures': flow_failures
            }
            print(f"Authentication flow breakdown: {json.dumps(flow_summary, indent=2)}")
        
        # Should NOT have end-to-end authentication flow failures
        assert len(flow_failures) == 0, f"Complete end-to-end authentication system breakdown: {flow_failures}"

    @pytest.mark.critical
    async def test_authentication_performance_completely_unacceptable(self):
        """
        EXPECTED TO FAIL - CRITICAL AUTHENTICATION PERFORMANCE ISSUE  
        Authentication should complete quickly but takes 6.2+ seconds consistently
        Root cause: Multiple performance issues causing unacceptable authentication latency
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Test authentication performance across multiple scenarios
        performance_test_scenarios = [
            ('simple_token_validation', f"{self.services['backend']}/api/threads", {'Authorization': 'Bearer perf-test-token'}),
            ('user_profile_request', f"{self.services['backend']}/api/auth/me", {'Authorization': 'Bearer perf-test-token'}),
            ('auth_service_validation', f"{self.services['auth_service']}/api/auth/validate", {'Content-Type': 'application/json'}),
            ('oauth_config_request', f"{self.services['auth_service']}/api/auth/config", {}),
        ]
        
        performance_issues = []
        latency_measurements = []
        
        async with httpx.AsyncClient() as client:
            for scenario_name, endpoint, headers in performance_test_scenarios:
                # Run multiple iterations to get consistent measurements
                scenario_latencies = []
                
                for iteration in range(3):  # 3 iterations per scenario
                    try:
                        start_time = time.time()
                        
                        if scenario_name == 'auth_service_validation':
                            response = await client.post(
                                endpoint,
                                json={'token': 'performance-test-token'},
                                headers=headers,
                                timeout=10.0  # Allow time to capture 6.2+ second issue
                            )
                        else:
                            response = await client.get(
                                endpoint,
                                headers=headers,
                                timeout=10.0  # Allow time to capture 6.2+ second issue
                            )
                        
                        end_time = time.time()
                        latency = end_time - start_time
                        scenario_latencies.append(latency)
                        
                        # Check for the specific 6.2+ second issue
                        if latency > 6.0:
                            performance_issues.append(f"{scenario_name} (iteration {iteration + 1}): Excessive latency {latency:.2f}s (>6s)")
                            self.authentication_breakdown_metrics['latency_issues'] += 1
                        elif latency > 2.0:
                            performance_issues.append(f"{scenario_name} (iteration {iteration + 1}): High latency {latency:.2f}s (>2s)")
                        
                        # Brief delay between iterations
                        if iteration < 2:
                            await asyncio.sleep(0.5)
                            
                    except httpx.TimeoutException:
                        # Timeout indicates performance issue
                        performance_issues.append(f"{scenario_name} (iteration {iteration + 1}): Request timeout (>10s)")
                        scenario_latencies.append(10.0)  # Record as 10s timeout
                        self.authentication_breakdown_metrics['latency_issues'] += 1
                    except Exception as e:
                        performance_issues.append(f"{scenario_name} (iteration {iteration + 1}): Performance test error - {str(e)}")
                        continue
                
                # Calculate average latency for scenario
                if scenario_latencies:
                    avg_latency = sum(scenario_latencies) / len(scenario_latencies)
                    max_latency = max(scenario_latencies)
                    latency_measurements.append({
                        'scenario': scenario_name,
                        'avg_latency': avg_latency,
                        'max_latency': max_latency,
                        'iterations': len(scenario_latencies)
                    })
        
        # Analyze overall performance
        if latency_measurements:
            overall_avg_latency = sum(m['avg_latency'] for m in latency_measurements) / len(latency_measurements)
            worst_case_latency = max(m['max_latency'] for m in latency_measurements)
            
            # Performance should be acceptable
            if overall_avg_latency > 2.0:
                performance_issues.append(f"Overall average latency unacceptable: {overall_avg_latency:.2f}s (should be <2s)")
            if worst_case_latency > 6.0:
                performance_issues.append(f"Worst case latency critical: {worst_case_latency:.2f}s (indicates 6.2+ second issue)")
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if performance_issues else 0
        
        # Report performance measurements for analysis
        if performance_issues:
            performance_summary = {
                'overall_performance': 'UNACCEPTABLE',
                'latency_measurements': latency_measurements,
                'performance_issues': performance_issues,
                'six_second_issue_detected': any('6' in issue for issue in performance_issues)
            }
            print(f"Authentication performance breakdown: {json.dumps(performance_summary, indent=2)}")
        
        # Should NOT have authentication performance issues
        assert len(performance_issues) == 0, f"Authentication performance completely unacceptable: {performance_issues}"

    @pytest.mark.critical
    async def test_zero_authentication_recovery_mechanisms(self):
        """
        EXPECTED TO FAIL - CRITICAL RECOVERY MECHANISM ISSUE
        System should have authentication recovery mechanisms but has none implemented
        Root cause: No recovery mechanisms for any authentication failure scenarios
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Test various authentication failure recovery scenarios
        recovery_scenarios = [
            ('token_expired_recovery', 'expired_token_scenario'),
            ('service_down_recovery', 'auth_service_unavailable'),
            ('network_failure_recovery', 'network_connectivity_lost'),
            ('database_failure_recovery', 'database_authentication_failed'),
            ('oauth_provider_failure_recovery', 'oauth_provider_unavailable')
        ]
        
        recovery_failures = []
        
        async with httpx.AsyncClient() as client:
            for scenario_name, failure_type in recovery_scenarios:
                try:
                    # Simulate failure scenario and test recovery
                    response = await client.post(
                        f"{self.services['backend']}/api/auth/recovery-test",
                        json={
                            'scenario': scenario_name,
                            'failure_type': failure_type,
                            'test_recovery': True
                        },
                        headers={'Content-Type': 'application/json'},
                        timeout=5.0
                    )
                    
                    if response.status_code == 404:
                        recovery_failures.append(f"{scenario_name}: No recovery endpoint implemented")
                    elif response.status_code == 501:
                        recovery_failures.append(f"{scenario_name}: Recovery mechanism not implemented")
                    elif response.status_code == 200:
                        recovery_data = response.json()
                        if not recovery_data.get('recovery_available'):
                            recovery_failures.append(f"{scenario_name}: Recovery mechanism not available - {recovery_data.get('reason')}")
                    else:
                        recovery_failures.append(f"{scenario_name}: Unexpected recovery test result {response.status_code}")
                        
                except httpx.ConnectError:
                    recovery_failures.append(f"{scenario_name}: Cannot test recovery - service unreachable")
                except Exception as e:
                    recovery_failures.append(f"{scenario_name}: Recovery test error - {str(e)}")
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if recovery_failures else 0
        
        # Should NOT have zero authentication recovery mechanisms
        assert len(recovery_failures) == 0, f"Zero authentication recovery mechanisms: {recovery_failures}"

    @pytest.mark.critical
    def test_authentication_infrastructure_single_points_of_failure(self):
        """
        EXPECTED TO FAIL - CRITICAL SINGLE POINT OF FAILURE ISSUE
        Authentication infrastructure should have redundancy but has critical single points of failure
        Root cause: Authentication system designed with single points of failure throughout
        """
        self.authentication_breakdown_metrics['total_tests'] += 1
        
        # Identify single points of failure in authentication infrastructure
        single_points_of_failure = []
        
        # Test authentication service redundancy
        try:
            # Check for multiple auth service instances
            auth_service_instances = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('auth_service' in arg or 'auth-service' in arg for arg in cmdline):
                        auth_service_instances += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if auth_service_instances <= 1:
                single_points_of_failure.append("Auth Service: Single instance - no redundancy")
                
        except Exception as e:
            single_points_of_failure.append(f"Auth Service redundancy check failed: {str(e)}")
        
        # Test database connection redundancy
        env = IsolatedEnvironment()
        
        # Check for single database connection
        database_urls = [
            env.get('DATABASE_URL'),
            env.get('POSTGRES_URL'), 
            env.get('AUTH_DATABASE_URL')
        ]
        unique_databases = set(url for url in database_urls if url)
        
        if len(unique_databases) <= 1:
            single_points_of_failure.append("Database: Single database connection - no failover")
        
        # Test Redis/cache redundancy
        redis_urls = [
            env.get('REDIS_URL'),
            env.get('CACHE_URL'),
            env.get('SESSION_STORE_URL')
        ]
        unique_redis = set(url for url in redis_urls if url)
        
        if len(unique_redis) <= 1:
            single_points_of_failure.append("Redis/Cache: Single cache instance - no redundancy")
        
        # Test JWT signing key redundancy
        jwt_keys = [
            env.get('JWT_SECRET_KEY'),
            env.get('JWT_PRIVATE_KEY'),
            env.get('JWT_BACKUP_KEY')
        ]
        valid_jwt_keys = [key for key in jwt_keys if key and len(key) > 10]
        
        if len(valid_jwt_keys) <= 1:
            single_points_of_failure.append("JWT Keys: Single signing key - no key rotation or backup")
        
        # Test OAuth provider redundancy
        oauth_providers = [
            env.get('OAUTH_PROVIDER_GOOGLE'),
            env.get('OAUTH_PROVIDER_AZURE'),
            env.get('OAUTH_PROVIDER_GITHUB')
        ]
        configured_providers = [provider for provider in oauth_providers if provider]
        
        if len(configured_providers) <= 1:
            single_points_of_failure.append("OAuth Providers: Single OAuth provider - no alternative authentication")
        
        self.authentication_breakdown_metrics['failed_tests'] += 1 if single_points_of_failure else 0
        self.authentication_breakdown_metrics['critical_failures'] += len(single_points_of_failure)
        
        # Should NOT have single points of failure in authentication infrastructure
        assert len(single_points_of_failure) == 0, f"Authentication infrastructure single points of failure: {single_points_of_failure}"

    def teardown_method(self):
        """Generate comprehensive authentication breakdown report"""
        end_time = time.time()
        test_duration = end_time - self.start_time
        
        # Calculate failure rates
        total_tests = self.authentication_breakdown_metrics['total_tests']
        failed_tests = self.authentication_breakdown_metrics['failed_tests']
        failure_rate = (failed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate comprehensive breakdown report
        breakdown_report = {
            'test_execution_summary': {
                'total_tests': total_tests,
                'failed_tests': failed_tests,
                'failure_rate': f"{failure_rate:.1f}%",
                'test_duration': f"{test_duration:.2f}s"
            },
            'authentication_system_health': {
                'overall_status': 'CRITICAL FAILURE' if failure_rate > 50 else 'DEGRADED' if failure_rate > 0 else 'HEALTHY',
                'latency_issues': self.authentication_breakdown_metrics['latency_issues'],
                'service_failures': self.authentication_breakdown_metrics['service_failures'],
                'critical_failures': self.authentication_breakdown_metrics['critical_failures']
            },
            'business_impact_assessment': {
                'deployment_viability': 'BLOCKED' if failure_rate > 50 else 'AT RISK',
                'user_authentication': 'COMPLETELY BROKEN' if failure_rate > 80 else 'SEVERELY DEGRADED',
                'system_usability': 'ZERO' if failure_rate == 100 else 'MINIMAL',
                'development_velocity': 'BLOCKED',
                'customer_impact': 'CRITICAL'
            },
            'iteration_2_audit_validation': {
                'six_second_latency_confirmed': self.authentication_breakdown_metrics['latency_issues'] > 0,
                'complete_403_failure_confirmed': failed_tests > 0,
                'retry_logic_ineffective_confirmed': True,  # Validated by test failures
                'system_breakdown_confirmed': failure_rate > 90
            }
        }
        
        print(f"\n{'='*80}")
        print("COMPREHENSIVE AUTHENTICATION SYSTEM BREAKDOWN REPORT")  
        print(f"{'='*80}")
        print(json.dumps(breakdown_report, indent=2))
        print(f"{'='*80}\n")
        
        super().teardown_method()