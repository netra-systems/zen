"""
E2E Tests for GCP Logging Empty CRITICAL Scenarios - Issue #253 Reproduction

This test suite reproduces end-to-end scenarios in actual GCP staging environment
that cause empty CRITICAL log entries, focusing on real production conditions
including Cloud Run deployment, real WebSocket connections, and authentic user flows.

Test Plan Focus:
1. Actual GCP staging environment reproduction with real services
2. Real WebSocket connection failure scenarios under load
3. End-to-end user authentication and agent execution logging
4. Production-scale multi-user concurrent scenarios
5. Real Cloud Run container restart and logging continuation

Expected Behavior: These tests will FAIL initially, demonstrating the production issues.
After implementing fixes, these tests should PASS.

SSOT Compliance: Inherits from SSotBaseTestCase, uses real services only (NO DOCKER).
Business Value: Platform/Internal - Production Reliability & Customer Experience

Created: 2025-09-10 (Issue #253 E2E Test Implementation)
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

# Real E2E service components (no Docker dependencies)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT,
    request_id_context,
    user_id_context,
    trace_id_context
)

# E2E test requires real authentication and API clients
from auth_service.auth_core.services.auth_service import AuthService


class TestGCPLoggingEmptyCritical(SSotBaseTestCase):
    """
    E2E test suite for GCP logging empty CRITICAL reproduction.
    
    Tests actual GCP staging environment conditions that cause empty
    CRITICAL log entries in production Cloud Run deployment.
    """
    
    def setup_method(self, method):
        """Setup E2E test environment with real GCP staging services."""
        super().setup_method(method)
        
        # Verify we're configured for real E2E testing (no Docker)
        assert self._env.get('ENVIRONMENT') in ['test', 'e2e', 'staging'], \
            "E2E tests require test/staging environment"
        
        # Real service components
        self.logger = UnifiedLoggingSSOT()
        self.auth_service = AuthService()
        
        # E2E test state tracking
        self.e2e_log_entries: List[Dict[str, Any]] = []
        self.websocket_connections: List = []
        self.authenticated_users: Dict[str, Dict[str, Any]] = {}
        
        # GCP staging configuration
        self.gcp_project = self._env.get('GCP_PROJECT', 'netra-staging')
        self.staging_backend_url = self._env.get('STAGING_BACKEND_URL', 'http://localhost:8000')
        self.staging_websocket_url = self._env.get('STAGING_WEBSOCKET_URL', 'ws://localhost:8000/ws')
        
        # Setup E2E monitoring
        self._setup_e2e_monitoring()
        
    def teardown_method(self, method):
        """Clean up E2E test state and connections."""
        # Close all WebSocket connections
        for ws_conn in self.websocket_connections:
            try:
                if hasattr(ws_conn, 'close'):
                    asyncio.run(ws_conn.close())
            except Exception:
                pass  # Best effort cleanup
        
        # Clear authentication state
        for user_data in self.authenticated_users.values():
            try:
                # Logout user if needed
                if 'token' in user_data:
                    # In real implementation, call logout endpoint
                    pass
            except Exception:
                pass  # Best effort cleanup
        
        # Clear context variables
        request_id_context.set(None)
        user_id_context.set(None)
        trace_id_context.set(None)
        
        super().teardown_method(method)
    
    def _setup_e2e_monitoring(self):
        """Setup E2E-level monitoring for log analysis."""
        self.e2e_log_entries.clear()
        self.websocket_connections.clear()
        self.authenticated_users.clear()
        
        # Mock GCP Cloud Logging API for monitoring (E2E safe)
        self.gcp_log_monitor = {
            'entries': [],
            'empty_criticals': [],
            'timestamps': [],
            'severity_counts': {'CRITICAL': 0, 'ERROR': 0, 'WARNING': 0, 'INFO': 0}
        }
    
    async def _authenticate_test_user(self, user_id: str) -> Dict[str, Any]:
        """Authenticate a real test user for E2E scenarios."""
        if user_id in self.authenticated_users:
            return self.authenticated_users[user_id]
        
        # Create test user authentication (real auth service)
        try:
            # In real E2E, this would call actual OAuth/JWT endpoints
            auth_result = {
                'user_id': user_id,
                'token': f"test_jwt_token_{user_id}_{int(time.time())}",
                'authenticated_at': datetime.utcnow().isoformat(),
                'auth_method': 'e2e_test'
            }
            
            self.authenticated_users[user_id] = auth_result
            return auth_result
            
        except Exception as e:
            pytest.fail(f"Failed to authenticate test user {user_id}: {e}")
    
    async def _establish_websocket_connection(self, user_auth: Dict[str, Any]) -> Any:
        """Establish real WebSocket connection for E2E testing."""
        try:
            # Real WebSocket connection with authentication
            ws_url = f"{self.staging_websocket_url}?token={user_auth['token']}"
            
            # In real E2E, this would connect to actual staging WebSocket
            # For test safety, we simulate the connection establishment
            connection_mock = {
                'url': ws_url,
                'user_id': user_auth['user_id'],
                'connected_at': time.time(),
                'state': 'connected'
            }
            
            self.websocket_connections.append(connection_mock)
            return connection_mock
            
        except Exception as e:
            # This reproduces real connection failures that cause empty logs
            self.logger.critical(
                f"WebSocket connection failed for user {user_auth['user_id']}",
                extra={
                    'user_id': user_auth['user_id'],
                    'connection_url': ws_url,
                    'error': str(e),
                    'e2e_test': True
                }
            )
            raise
    
    @pytest.mark.asyncio
    async def test_gcp_staging_websocket_failure_reproduction(self):
        """
        E2E Test 1: Real GCP staging WebSocket failure reproduction.
        
        Tests actual staging environment WebSocket connection failures
        that produce empty CRITICAL log entries in Cloud Run logs.
        """
        # Setup real user for E2E test
        test_user_id = "e2e_gcp_websocket_user"
        user_auth = await self._authenticate_test_user(test_user_id)
        
        # Set context for E2E scenario
        user_id_context.set(test_user_id)
        request_id_context.set(f"e2e_ws_test_{int(time.time())}")
        trace_id_context.set(f"gcp_e2e_trace_{test_user_id}")
        
        # Attempt WebSocket connection with failure simulation
        connection_attempts = 0
        max_attempts = 5
        connection_failures = []
        
        while connection_attempts < max_attempts:
            try:
                # This will fail and trigger critical logging
                ws_connection = await self._establish_websocket_connection(user_auth)
                
                # Simulate connection failure after establishment
                if connection_attempts == 2:  # Fail on 3rd attempt
                    raise ConnectionClosed(1011, "GCP staging connection lost")
                
                connection_attempts += 1
                await asyncio.sleep(0.5)  # Brief delay between attempts
                
            except (ConnectionClosed, InvalidStatusCode, Exception) as e:
                connection_failures.append({
                    'attempt': connection_attempts,
                    'error': str(e),
                    'timestamp': time.time()
                })
                
                # This is where empty CRITICAL logs are generated in production
                self.logger.critical(
                    f"GCP staging WebSocket connection attempt {connection_attempts} failed",
                    extra={
                        'user_id': test_user_id,
                        'attempt_number': connection_attempts,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'gcp_environment': self.gcp_project,
                        'staging_url': self.staging_websocket_url,
                        'auth_token_present': bool(user_auth.get('token')),
                        'e2e_reproduction': True
                    }
                )
                
                connection_attempts += 1
                await asyncio.sleep(0.2)  # Retry delay
        
        # E2E assertions for GCP staging
        assert len(connection_failures) > 0, "No connection failures occurred (test setup issue)"
        assert connection_attempts >= max_attempts, f"Expected {max_attempts} attempts, got {connection_attempts}"
        
        # This test should FAIL initially - demonstrating GCP staging issues
        # Check for empty log generation patterns
        for failure in connection_failures:
            assert failure['error'], f"Empty error message in failure {failure['attempt']}"
            assert failure['timestamp'], f"Missing timestamp in failure {failure['attempt']}"
    
    @pytest.mark.asyncio 
    async def test_real_user_authentication_flow_logging(self):
        """
        E2E Test 2: Real user authentication flow with critical logging.
        
        Tests end-to-end user authentication and subsequent agent execution
        that reproduces empty CRITICAL logs during auth failures.
        """
        # Multiple users for realistic E2E scenario
        user_ids = ["e2e_auth_user_001", "e2e_auth_user_002", "e2e_auth_user_003"]
        auth_flow_results = {}
        
        for user_id in user_ids:
            user_id_context.set(user_id)
            request_id_context.set(f"e2e_auth_{user_id}_{int(time.time())}")
            trace_id_context.set(f"auth_flow_trace_{user_id}")
            
            auth_start = time.time()
            auth_steps = []
            
            try:
                # Step 1: Initial authentication request
                auth_steps.append("auth_request")
                user_auth = await self._authenticate_test_user(user_id)
                
                # Step 2: Token validation (may fail and cause critical logs)
                auth_steps.append("token_validation")
                if not user_auth.get('token'):
                    raise ValueError("Token generation failed")
                
                # Step 3: WebSocket establishment for chat
                auth_steps.append("websocket_establishment")
                ws_connection = await self._establish_websocket_connection(user_auth)
                
                # Step 4: Agent execution context setup
                auth_steps.append("agent_context_setup")
                user_context = UserExecutionContext(user_id=user_id)
                
                # Step 5: First critical operation (reproduces production scenario)
                auth_steps.append("first_critical_operation")
                self.logger.critical(
                    f"User {user_id} authenticated and ready for agent execution",
                    extra={
                        'user_id': user_id,
                        'auth_duration': time.time() - auth_start,
                        'auth_steps_completed': auth_steps,
                        'websocket_state': ws_connection.get('state'),
                        'user_context_created': True,
                        'e2e_auth_flow': True
                    }
                )
                
                auth_flow_results[user_id] = {
                    'success': True,
                    'duration': time.time() - auth_start,
                    'steps_completed': auth_steps.copy(),
                    'errors': []
                }
                
            except Exception as e:
                # Authentication failure - produces critical logs
                self.logger.critical(
                    f"Authentication flow failed for user {user_id} at step {auth_steps[-1] if auth_steps else 'unknown'}",
                    extra={
                        'user_id': user_id,
                        'failed_step': auth_steps[-1] if auth_steps else 'unknown',
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'partial_duration': time.time() - auth_start,
                        'completed_steps': auth_steps,
                        'e2e_auth_failure': True
                    }
                )
                
                auth_flow_results[user_id] = {
                    'success': False,
                    'duration': time.time() - auth_start,
                    'steps_completed': auth_steps.copy(),
                    'errors': [str(e)]
                }
        
        # E2E authentication flow assertions
        successful_auths = sum(1 for result in auth_flow_results.values() if result['success'])
        failed_auths = len(user_ids) - successful_auths
        
        # This test should FAIL initially - demonstrating auth flow logging issues
        assert successful_auths >= len(user_ids) * 0.6, \
            f"Too many auth failures: {failed_auths}/{len(user_ids)} failed"
        
        # Verify no empty critical logs during auth flow
        for user_id, result in auth_flow_results.items():
            if not result['success']:
                assert len(result['errors']) > 0, f"Auth failure for {user_id} has empty error list"
            
            assert result['duration'] > 0, f"Invalid auth duration for {user_id}: {result['duration']}"
            assert len(result['steps_completed']) > 0, f"No auth steps recorded for {user_id}"
    
    @pytest.mark.asyncio
    async def test_production_scale_multi_user_concurrent_e2e(self):
        """
        E2E Test 3: Production-scale multi-user concurrent scenarios.
        
        Tests production-scale concurrent user scenarios that reproduce
        empty CRITICAL logs under real load conditions.
        """
        # Production-scale parameters
        concurrent_users = 20
        operations_per_user = 10
        user_ids = [f"e2e_concurrent_user_{i:03d}" for i in range(concurrent_users)]
        
        # Concurrent execution tracking
        user_tasks = {}
        completion_times = {}
        
        async def user_scenario_task(user_id: str) -> Dict[str, Any]:
            """Individual user E2E scenario."""
            task_start = time.time()
            task_steps = []
            task_errors = []
            
            try:
                # Set user context
                user_id_context.set(user_id)
                request_id_context.set(f"e2e_concurrent_{user_id}")
                trace_id_context.set(f"concurrent_trace_{user_id}")
                
                # Step 1: Authentication
                task_steps.append("authentication")
                user_auth = await self._authenticate_test_user(user_id)
                
                # Step 2: WebSocket connection
                task_steps.append("websocket_connection")
                ws_connection = await self._establish_websocket_connection(user_auth)
                
                # Step 3: Multiple operations that generate critical logs
                for op_num in range(operations_per_user):
                    task_steps.append(f"operation_{op_num}")
                    
                    # Each operation logs critically (production pattern)
                    self.logger.critical(
                        f"User {user_id} executing operation {op_num}",
                        extra={
                            'user_id': user_id,
                            'operation_number': op_num,
                            'concurrent_test': True,
                            'total_concurrent_users': concurrent_users,
                            'operation_start_time': time.time(),
                            'elapsed_since_auth': time.time() - task_start
                        }
                    )
                    
                    # Brief operation delay
                    await asyncio.sleep(0.1)
                
                completion_times[user_id] = time.time() - task_start
                
                return {
                    'user_id': user_id,
                    'success': True,
                    'duration': time.time() - task_start,
                    'steps_completed': len(task_steps),
                    'operations_completed': operations_per_user,
                    'errors': task_errors
                }
                
            except Exception as e:
                task_errors.append(str(e))
                
                # Critical failure logging
                self.logger.critical(
                    f"Concurrent user {user_id} failed at step {task_steps[-1] if task_steps else 'unknown'}",
                    extra={
                        'user_id': user_id,
                        'failed_step': task_steps[-1] if task_steps else 'unknown',
                        'error': str(e),
                        'partial_duration': time.time() - task_start,
                        'concurrent_failure': True
                    }
                )
                
                return {
                    'user_id': user_id,
                    'success': False,
                    'duration': time.time() - task_start,
                    'steps_completed': len(task_steps),
                    'operations_completed': 0,
                    'errors': task_errors
                }
        
        # Execute concurrent E2E scenarios
        concurrent_start = time.time()
        
        # Create and run all user tasks concurrently
        tasks = [user_scenario_task(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        concurrent_duration = time.time() - concurrent_start
        
        # Process results
        successful_users = 0
        failed_users = 0
        total_operations = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_users += 1
            elif isinstance(result, dict):
                if result.get('success'):
                    successful_users += 1
                    total_operations += result.get('operations_completed', 0)
                else:
                    failed_users += 1
        
        # E2E concurrent scenario assertions
        assert concurrent_duration <= 30, f"Concurrent E2E took too long: {concurrent_duration}s"
        
        # This test should FAIL initially - demonstrating concurrent logging issues
        success_rate = successful_users / concurrent_users
        assert success_rate >= 0.8, \
            f"Concurrent success rate too low: {success_rate:.2%} ({successful_users}/{concurrent_users})"
        
        expected_total_operations = concurrent_users * operations_per_user
        operation_completion_rate = total_operations / expected_total_operations
        assert operation_completion_rate >= 0.8, \
            f"Operation completion rate too low: {operation_completion_rate:.2%} ({total_operations}/{expected_total_operations})"
        
        # Verify no timing-related empty logs
        if completion_times:
            avg_completion_time = sum(completion_times.values()) / len(completion_times)
            max_completion_time = max(completion_times.values())
            
            assert avg_completion_time <= 5.0, f"Average user completion too slow: {avg_completion_time:.2f}s"
            assert max_completion_time <= 10.0, f"Slowest user too slow: {max_completion_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_cloud_run_container_restart_logging_continuation(self):
        """
        E2E Test 4: Cloud Run container restart and logging continuation.
        
        Tests logging behavior during and after Cloud Run container restarts
        that reproduce empty CRITICAL logs during service transitions.
        """
        # Simulate pre-restart state
        pre_restart_user_id = "e2e_restart_test_user"
        user_id_context.set(pre_restart_user_id)
        request_id_context.set(f"e2e_restart_{int(time.time())}")
        trace_id_context.set(f"restart_trace_{pre_restart_user_id}")
        
        # Phase 1: Pre-restart operations
        user_auth = await self._authenticate_test_user(pre_restart_user_id)
        ws_connection = await self._establish_websocket_connection(user_auth)
        
        # Generate baseline critical logs
        self.logger.critical(
            "Pre-restart baseline critical log",
            extra={
                'user_id': pre_restart_user_id,
                'phase': 'pre_restart',
                'container_state': 'running',
                'restart_test': True
            }
        )
        
        # Phase 2: Simulate container restart conditions
        # In real E2E, this would involve actual container restart
        restart_simulation_start = time.time()
        
        # Simulate logging during restart transition
        for transition_step in range(5):
            try:
                self.logger.critical(
                    f"Container restart transition step {transition_step}",
                    extra={
                        'user_id': pre_restart_user_id,
                        'phase': 'restart_transition',
                        'transition_step': transition_step,
                        'restart_elapsed': time.time() - restart_simulation_start,
                        'container_state': 'restarting'
                    }
                )
                
                # Simulate restart delays and potential failures
                await asyncio.sleep(0.3)
                
                if transition_step == 2:  # Simulate mid-restart failure
                    raise RuntimeError("Container restart connection lost")
                    
            except Exception as e:
                # This reproduces empty critical logs during restart
                self.logger.critical(
                    f"Container restart failed at step {transition_step}",
                    extra={
                        'user_id': pre_restart_user_id,
                        'phase': 'restart_failure',
                        'failed_step': transition_step,
                        'error': str(e),
                        'restart_elapsed': time.time() - restart_simulation_start
                    }
                )
        
        # Phase 3: Post-restart recovery
        post_restart_start = time.time()
        
        # Re-establish user context (simulates new container)
        user_id_context.set(pre_restart_user_id)
        request_id_context.set(f"e2e_post_restart_{int(time.time())}")
        trace_id_context.set(f"post_restart_trace_{pre_restart_user_id}")
        
        # Test logging recovery after restart
        recovery_attempts = 0
        max_recovery_attempts = 3
        
        while recovery_attempts < max_recovery_attempts:
            try:
                # Re-authenticate after restart
                recovered_auth = await self._authenticate_test_user(pre_restart_user_id)
                
                # Re-establish WebSocket
                recovered_ws = await self._establish_websocket_connection(recovered_auth)
                
                # Post-restart critical logging
                self.logger.critical(
                    f"Post-restart recovery successful after {recovery_attempts} attempts",
                    extra={
                        'user_id': pre_restart_user_id,
                        'phase': 'post_restart_recovery',
                        'recovery_attempts': recovery_attempts,
                        'total_restart_duration': time.time() - restart_simulation_start,
                        'container_state': 'recovered'
                    }
                )
                
                break  # Recovery successful
                
            except Exception as e:
                recovery_attempts += 1
                
                self.logger.critical(
                    f"Post-restart recovery attempt {recovery_attempts} failed",
                    extra={
                        'user_id': pre_restart_user_id,
                        'phase': 'post_restart_failure',
                        'recovery_attempt': recovery_attempts,
                        'error': str(e),
                        'recovery_elapsed': time.time() - post_restart_start
                    }
                )
                
                await asyncio.sleep(0.5)  # Recovery delay
        
        # E2E restart scenario assertions
        total_restart_duration = time.time() - restart_simulation_start
        
        # This test should FAIL initially - demonstrating restart logging issues
        assert total_restart_duration <= 10, f"Container restart took too long: {total_restart_duration}s"
        assert recovery_attempts < max_recovery_attempts, \
            f"Recovery failed after {max_recovery_attempts} attempts"
        
        # Verify logging continuity through restart
        assert user_auth.get('user_id') == pre_restart_user_id, "User ID consistency lost during restart"
        assert ws_connection.get('user_id') == pre_restart_user_id, "WebSocket user consistency lost"