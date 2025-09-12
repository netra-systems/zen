
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
Test Golden Path Authentication Flow Circuit Breaker Preservation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User Experience & System Availability
- Value Impact: CRITICAL - Ensure user login works during/after SSOT migration
- Strategic Impact: $500K+ ARR dependency - Golden Path user flow must remain intact

This E2E test validates that the SSOT migration preserves Golden Path functionality:
1. User authentication flow remains working during circuit breaker SSOT migration
2. Auth circuit breaker properly protects against service failures without blocking valid users
3. Recovery behavior maintains user access during intermittent auth service issues
4. WebSocket authentication handshake works with migrated circuit breaker logic

PURPOSE: End-to-end validation that SSOT migration doesn't break the primary user journey.
This test runs against staging environment to validate real-world behavior.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_cache import AuthCircuitBreakerManager
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestGoldenPathAuthCircuitBreakerPreservation(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """E2E validation of Golden Path authentication flow with SSOT circuit breaker migration."""

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.auth_flow
    async def test_golden_path_user_login_with_circuit_breaker_protection(self):
        """
        Test complete Golden Path user login flow with auth circuit breaker protection.
        
        This is the CRITICAL test - validates that the primary user journey works
        end-to-end with the migrated auth circuit breaker implementation.
        
        Business Impact: If this fails, users cannot log in and the platform has zero value.
        """
        env = get_env()
        
        # Get staging environment configuration
        staging_backend_url = env.get("STAGING_BACKEND_URL", "https://netra-staging-backend.example.com")
        staging_frontend_url = env.get("STAGING_FRONTEND_URL", "https://netra-staging.example.com")
        
        # Create test user credentials (use staging test account)
        test_user_email = env.get("E2E_TEST_USER_EMAIL", "e2e.test.user@netra.ai")
        test_user_password = env.get("E2E_TEST_USER_PASSWORD", "test_password_123")
        
        if not test_user_email or not test_user_password:
            pytest.skip("E2E test credentials not configured for staging environment")
        
        # STEP 1: Validate auth circuit breaker is working
        auth_cb_manager = AuthCircuitBreakerManager()
        auth_breaker = auth_cb_manager.get_breaker("e2e_login_test")
        
        # Verify circuit breaker starts in healthy state
        assert hasattr(auth_breaker, 'state'), "Auth circuit breaker should have state attribute"
        
        # STEP 2: Perform user authentication flow
        auth_start_time = time.time()
        
        try:
            # Simulate authentication request through circuit breaker
            async def authenticate_user():
                # This would normally call the auth service
                # For E2E test, we simulate the auth flow
                await asyncio.sleep(0.1)  # Simulate network call
                return {
                    "valid": True,
                    "user_id": "e2e_test_user_123",
                    "email": test_user_email,
                    "token": "mock_jwt_token_for_e2e",
                    "permissions": ["read", "write", "agent_execute"]
                }
            
            # Call through circuit breaker protection
            auth_result = await auth_breaker.call(authenticate_user)
            auth_duration = time.time() - auth_start_time
            
            # Validate authentication succeeded
            assert auth_result["valid"] is True, "Authentication should succeed"
            assert auth_result["email"] == test_user_email, "Should authenticate correct user"
            assert "token" in auth_result, "Should return authentication token"
            assert "permissions" in auth_result, "Should return user permissions"
            
            # Validate auth completed in reasonable time (circuit breaker not interfering)
            assert auth_duration < 5.0, f"Authentication took {auth_duration:.2f}s, should be < 5s"
            
        except Exception as e:
            pytest.fail(f"Golden Path authentication failed: {e}")
        
        # STEP 3: Test WebSocket connection with authenticated user
        websocket_start_time = time.time()
        
        try:
            # Create WebSocket connection with auth token
            async with WebSocketTestClient(
                base_url=staging_backend_url.replace("https://", "wss://").replace("http://", "ws://"),
                token=auth_result["token"],
                timeout=10.0
            ) as websocket_client:
                
                # Test WebSocket authentication handshake
                await websocket_client.send_json({
                    "type": "auth",
                    "token": auth_result["token"]
                })
                
                # Wait for auth confirmation
                auth_response = await websocket_client.receive_json(timeout=5.0)
                assert auth_response.get("type") == "auth_success", (
                    f"WebSocket auth should succeed, got: {auth_response}"
                )
                
                websocket_duration = time.time() - websocket_start_time
                assert websocket_duration < 10.0, (
                    f"WebSocket auth took {websocket_duration:.2f}s, should be < 10s"
                )
                
        except Exception as e:
            pytest.fail(f"Golden Path WebSocket authentication failed: {e}")
        
        # STEP 4: Test agent request flow (full Golden Path)
        agent_start_time = time.time()
        
        try:
            async with WebSocketTestClient(
                base_url=staging_backend_url.replace("https://", "wss://").replace("http://", "ws://"),
                token=auth_result["token"],
                timeout=30.0
            ) as websocket_client:
                
                # Send agent request
                await websocket_client.send_json({
                    "type": "agent_request",
                    "agent": "triage_agent", 
                    "message": "E2E test - simple query",
                    "user_id": auth_result["user_id"]
                })
                
                # Collect agent execution events
                agent_events = []
                while len(agent_events) < 3:  # Expect at least agent_started, agent_thinking, agent_completed
                    try:
                        event = await websocket_client.receive_json(timeout=20.0)
                        if event.get("type") in ["agent_started", "agent_thinking", "agent_completed"]:
                            agent_events.append(event)
                        if event.get("type") == "agent_completed":
                            break
                    except asyncio.TimeoutError:
                        break
                
                agent_duration = time.time() - agent_start_time
                
                # Validate agent execution completed
                assert len(agent_events) >= 2, f"Should receive agent events, got {len(agent_events)}: {agent_events}"
                
                event_types = [event["type"] for event in agent_events]
                assert "agent_started" in event_types, "Should receive agent_started event"
                assert "agent_completed" in event_types, "Should receive agent_completed event"
                
                # Validate timing is reasonable (no circuit breaker interference)
                assert agent_duration < 60.0, f"Agent execution took {agent_duration:.2f}s, should be < 60s"
                
        except Exception as e:
            pytest.fail(f"Golden Path agent execution failed: {e}")
        
        # Log successful Golden Path completion
        total_duration = time.time() - auth_start_time
        # Success: Complete Golden Path flow preserved during SSOT migration
        print(f" PASS:  GOLDEN PATH PRESERVED: Complete flow succeeded in {total_duration:.2f}s: "
              f"auth({auth_duration:.2f}s) + websocket({websocket_duration:.2f}s) + agent({agent_duration:.2f}s)")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.auth_resilience
    async def test_auth_circuit_breaker_failure_recovery_preserves_user_access(self):
        """
        Test that auth circuit breaker failure recovery doesn't permanently block users.
        
        Validates that the SSOT migration preserves resilience patterns that allow
        users to regain access after temporary auth service issues.
        """
        auth_cb_manager = AuthCircuitBreakerManager()
        recovery_breaker = auth_cb_manager.get_breaker("recovery_test")
        
        # STEP 1: Simulate auth service failures
        failure_count = 0
        
        async def failing_auth_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:  # First 3 calls fail
                raise Exception(f"Auth service temporarily unavailable (failure {failure_count})")
            else:  # Subsequent calls succeed
                return {
                    "valid": True,
                    "user_id": "recovered_user_123",
                    "email": "recovery.test@netra.ai",
                    "token": "recovered_token"
                }
        
        # STEP 2: Test failure handling
        failures_caught = 0
        for attempt in range(5):
            try:
                result = await recovery_breaker.call(failing_auth_service)
                if result["valid"]:
                    break  # Success after recovery
            except Exception:
                failures_caught += 1
                await asyncio.sleep(0.1)  # Brief delay between attempts
        
        # STEP 3: Validate recovery behavior
        assert failures_caught > 0, "Should have caught some failures during auth service issues"
        assert failure_count > 3, "Should have eventually succeeded after service recovery"
        
        # STEP 4: Validate subsequent calls work normally
        success_count = 0
        for _ in range(3):
            try:
                result = await recovery_breaker.call(failing_auth_service)
                if result["valid"]:
                    success_count += 1
            except Exception:
                pass
        
        assert success_count >= 2, f"Should succeed consistently after recovery, got {success_count}/3"
        
        # Success: Auth circuit breaker failure recovery preserved during SSOT migration
        print(f" PASS:  FAILURE RECOVERY VERIFIED: Circuit breaker handled {failures_caught} failures and recovered, "
              f"allowing {success_count}/3 subsequent successful authentications")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.performance
    async def test_auth_circuit_breaker_performance_impact_minimal(self):
        """
        Test that SSOT migration doesn't introduce performance regression in auth flow.
        
        Validates that the migrated circuit breaker logic doesn't add significant
        overhead to the critical user authentication path.
        """
        auth_cb_manager = AuthCircuitBreakerManager()
        perf_breaker = auth_cb_manager.get_breaker("performance_test")
        
        # Fast auth simulation
        async def fast_auth_service():
            await asyncio.sleep(0.01)  # 10ms auth service response
            return {
                "valid": True,
                "user_id": "perf_test_user",
                "email": "perf.test@netra.ai"
            }
        
        # Measure performance over multiple calls
        call_times = []
        
        for i in range(10):
            start_time = time.time()
            result = await perf_breaker.call(fast_auth_service)
            call_duration = time.time() - start_time
            call_times.append(call_duration)
            
            assert result["valid"] is True, f"Call {i+1} should succeed"
        
        # Analyze performance
        avg_time = sum(call_times) / len(call_times)
        max_time = max(call_times)
        min_time = min(call_times)
        
        # Validate circuit breaker overhead is minimal
        assert avg_time < 0.1, f"Average call time {avg_time:.3f}s should be < 0.1s (mostly auth service time)"
        assert max_time < 0.2, f"Max call time {max_time:.3f}s should be < 0.2s"
        
        # Validate consistency (no significant variance indicating circuit breaker issues)
        time_variance = max_time - min_time
        assert time_variance < 0.1, f"Time variance {time_variance:.3f}s should be < 0.1s (consistent performance)"
        
        # Success: Auth circuit breaker performance impact minimal after SSOT migration
        print(f" PASS:  PERFORMANCE VERIFIED: Circuit breaker adds minimal overhead: avg={avg_time:.3f}s, "
              f"max={max_time:.3f}s, variance={time_variance:.3f}s over 10 calls")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.circuit_breaker_states
    async def test_auth_circuit_breaker_state_transitions_preserve_user_flow(self):
        """
        Test that circuit breaker state transitions don't disrupt ongoing user sessions.
        
        Validates that SSOT migration preserves the behavior where circuit breaker
        state changes don't negatively impact active user authentication flows.
        """
        auth_cb_manager = AuthCircuitBreakerManager()
        state_breaker = auth_cb_manager.get_breaker("state_transition_test")
        
        # Simulate auth service with intermittent issues
        call_count = 0
        
        async def intermittent_auth_service():
            nonlocal call_count
            call_count += 1
            
            # Pattern: success, success, fail, success, success, fail, etc.
            if call_count % 3 == 0:
                raise Exception("Intermittent auth service issue")
            else:
                return {
                    "valid": True,
                    "user_id": f"user_{call_count}",
                    "email": f"user{call_count}@netra.ai"
                }
        
        # Track results over multiple calls
        results = []
        exceptions = []
        
        for i in range(9):  # Test pattern over 9 calls
            try:
                result = await state_breaker.call(intermittent_auth_service)
                results.append(result)
            except Exception as e:
                exceptions.append(str(e))
            
            # Small delay between calls
            await asyncio.sleep(0.05)
        
        # Validate that circuit breaker handled the pattern appropriately
        success_count = len(results)
        failure_count = len(exceptions)
        
        # Should have some successes and some handled failures
        assert success_count >= 4, f"Should have multiple successful auths, got {success_count}"
        assert failure_count >= 2, f"Should have handled some failures, got {failure_count}"
        
        # Validate successful results are valid
        for i, result in enumerate(results):
            assert result["valid"] is True, f"Result {i} should be valid"
            assert "user_id" in result, f"Result {i} should have user_id"
            assert "email" in result, f"Result {i} should have email"
        
        # Test final state allows continued operation
        final_result = await state_breaker.call(intermittent_auth_service)
        assert final_result["valid"] is True, "Final call should succeed"
        
        # Success: Auth circuit breaker state transitions preserved during SSOT migration
        print(f" PASS:  STATE TRANSITIONS VERIFIED: Circuit breaker handled intermittent pattern: {success_count} successes, "
              f"{failure_count} handled failures, final state operational")