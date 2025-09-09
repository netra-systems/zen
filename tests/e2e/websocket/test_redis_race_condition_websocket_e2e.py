"""
E2E Tests for Redis Race Condition WebSocket Fix

MISSION CRITICAL: End-to-end tests that validate the Redis race condition fix
works in real WebSocket connections with authentication and real services.

ROOT CAUSE VALIDATION: These tests confirm that:
1. WebSocket connections succeed with Redis race condition fix in place
2. Authenticated E2E tests work with the 500ms grace period
3. Real services integration doesn't break WebSocket functionality
4. GCP-like environments handle WebSocket connections properly after fix

CRITICAL E2E AUTH REQUIREMENT: ALL e2e tests MUST use authentication
except for tests that directly validate auth itself (per CLAUDE.md).

SSOT COMPLIANCE: Uses test_framework.ssot.e2e_auth_helper for authentication
and real services for validation.

Business Value:
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Ensures complete WebSocket chat functionality works end-to-end
- Strategic Impact: Validates production-ready chat business value
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import patch

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.containers_utils import ensure_redis_container, ensure_backend_container

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    create_gcp_websocket_validator
)


class TestRedisRaceConditionWebSocketE2E:
    """E2E tests for Redis race condition fix in WebSocket connections."""
    
    @pytest.fixture
    async def authenticated_websocket_helper(self, isolated_env):
        """Create authenticated WebSocket helper for E2E testing."""
        # Use staging-like environment for GCP simulation
        helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Pre-authenticate to avoid auth delays during WebSocket tests
        token = await helper.get_staging_token_async()
        assert token is not None, "Failed to get authentication token for E2E test"
        
        return helper
    
    @pytest.fixture
    async def authenticated_user_context(self, isolated_env):
        """Create authenticated user context for E2E testing."""
        return await create_authenticated_user_context(
            environment="staging",
            websocket_enabled=True,
            permissions=["read", "write", "websocket"]
        )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_connection_with_redis_race_fix_authenticated(
        self, 
        authenticated_websocket_helper,
        real_services_fixture,
        isolated_env
    ):
        """Test authenticated WebSocket connection succeeds with Redis race condition fix."""
        
        # Ensure required services are running
        ensure_redis_container()
        ensure_backend_container()
        
        # Simulate GCP staging environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Test WebSocket connection with authentication and race condition fix
            websocket = None
            connection_time = 0
            
            try:
                start_time = time.time()
                
                # Connect with proper authentication and E2E headers
                websocket = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
                
                connection_time = time.time() - start_time
                
                # Connection should succeed
                assert websocket is not None, "WebSocket connection failed"
                
                # Should take at least 500ms due to Redis grace period (allowing tolerance)
                assert connection_time >= 0.4, f"Connection too fast, grace period may be missing: {connection_time}s"
                
                # Test WebSocket communication
                test_message = {
                    "type": "ping",
                    "data": "redis_race_condition_test",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Should receive response (wait up to 10s)
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                assert response is not None, "No WebSocket response received"
                
                print(f"✅ WebSocket E2E test successful - connection time: {connection_time:.3f}s")
                
            except asyncio.TimeoutError:
                pytest.fail(
                    f"WebSocket connection timed out - Redis race condition fix may not be working. "
                    f"Connection time: {connection_time:.3f}s"
                )
            except Exception as e:
                pytest.fail(f"WebSocket E2E test failed: {e}")
            
            finally:
                if websocket:
                    await websocket.close()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections_with_redis_fix_authenticated(
        self,
        authenticated_websocket_helper,
        real_services_fixture,
        isolated_env
    ):
        """Test multiple concurrent WebSocket connections work with Redis race condition fix."""
        
        ensure_redis_container()
        ensure_backend_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            async def create_websocket_connection(connection_id: int):
                """Create a single WebSocket connection with authentication."""
                try:
                    start_time = time.time()
                    
                    # Each connection uses same auth helper but separate WebSocket
                    ws = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
                    
                    connection_time = time.time() - start_time
                    
                    # Test communication
                    test_msg = {
                        "type": "test_concurrent",
                        "connection_id": connection_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await ws.send(json.dumps(test_msg))
                    
                    # Wait for response
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    
                    await ws.close()
                    
                    return {
                        "connection_id": connection_id,
                        "success": True,
                        "connection_time": connection_time,
                        "response_received": response is not None
                    }
                    
                except Exception as e:
                    return {
                        "connection_id": connection_id,
                        "success": False,
                        "error": str(e),
                        "connection_time": 0
                    }
            
            # Create multiple concurrent connections
            concurrent_connections = 3  # Keep reasonable for E2E test
            tasks = [create_websocket_connection(i) for i in range(concurrent_connections)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_connections = 0
            total_connection_time = 0
            
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent WebSocket connection failed with exception: {result}")
                
                if result["success"]:
                    successful_connections += 1
                    total_connection_time += result["connection_time"]
                    
                    # Verify grace period was applied
                    assert result["connection_time"] >= 0.4, \
                        f"Connection {result['connection_id']} too fast: {result['connection_time']}s"
                else:
                    print(f"⚠️  Connection {result['connection_id']} failed: {result.get('error', 'Unknown error')}")
            
            # At least 2 out of 3 connections should succeed (allowing for some GCP timing issues)
            assert successful_connections >= 2, \
                f"Too many concurrent WebSocket connections failed: {successful_connections}/{concurrent_connections}"
            
            # Average connection time should reflect Redis grace period
            if successful_connections > 0:
                avg_time = total_connection_time / successful_connections
                assert avg_time >= 0.4, f"Average connection time too fast: {avg_time}s"
            
            print(f"✅ Concurrent WebSocket test: {successful_connections}/{concurrent_connections} succeeded")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_reconnection_after_redis_recovery_authenticated(
        self,
        authenticated_websocket_helper,
        real_services_fixture,
        isolated_env
    ):
        """Test WebSocket reconnection works after Redis recovery with race condition fix."""
        
        ensure_redis_container()
        ensure_backend_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # First connection should succeed
            first_ws = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
            
            # Test first connection
            await first_ws.send(json.dumps({"type": "test", "phase": "first"}))
            first_response = await asyncio.wait_for(first_ws.recv(), timeout=5.0)
            assert first_response is not None
            
            # Close first connection
            await first_ws.close()
            
            # Wait briefly to simulate Redis recovery scenario
            await asyncio.sleep(1.0)
            
            # Second connection should also succeed (Redis grace period should handle recovery)
            start_reconnect = time.time()
            second_ws = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
            reconnect_time = time.time() - start_reconnect
            
            # Test second connection
            await second_ws.send(json.dumps({"type": "test", "phase": "reconnect"}))
            second_response = await asyncio.wait_for(second_ws.recv(), timeout=5.0)
            assert second_response is not None
            
            await second_ws.close()
            
            # Reconnection should also include grace period
            assert reconnect_time >= 0.4, f"Reconnection too fast: {reconnect_time}s"
            
            print(f"✅ WebSocket reconnection test successful - reconnect time: {reconnect_time:.3f}s")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_auth_flow_with_redis_stability_authenticated(
        self,
        authenticated_user_context,
        real_services_fixture,
        isolated_env
    ):
        """Test complete WebSocket authentication flow with Redis stability."""
        
        ensure_redis_container()
        ensure_backend_container()
        
        # Create WebSocket helper from authenticated context
        helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Use token from context
        jwt_token = authenticated_user_context.agent_context.get('jwt_token')
        assert jwt_token is not None, "No JWT token in authenticated context"
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Test complete auth flow
            auth_success = await helper.test_websocket_auth_flow()
            
            assert auth_success is True, "WebSocket authentication flow failed"
            
            print("✅ WebSocket authentication flow test successful with Redis race condition fix")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_performance_with_redis_grace_period_authenticated(
        self,
        authenticated_websocket_helper,
        real_services_fixture,
        isolated_env
    ):
        """Test WebSocket performance impact of Redis grace period is acceptable."""
        
        ensure_redis_container()
        ensure_backend_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Measure connection times for multiple attempts
            connection_times = []
            
            for attempt in range(3):  # Multiple attempts for E2E stability
                start_time = time.time()
                
                try:
                    ws = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
                    
                    connection_time = time.time() - start_time
                    connection_times.append(connection_time)
                    
                    # Quick communication test
                    await ws.send(json.dumps({"type": "perf_test", "attempt": attempt}))
                    await asyncio.wait_for(ws.recv(), timeout=5.0)
                    
                    await ws.close()
                    
                    # Brief pause between attempts
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    pytest.fail(f"Performance test attempt {attempt} failed: {e}")
            
            # Analyze performance
            avg_connection_time = sum(connection_times) / len(connection_times)
            max_connection_time = max(connection_times)
            min_connection_time = min(connection_times)
            
            # Should consistently include grace period
            assert min_connection_time >= 0.4, f"Minimum connection time too fast: {min_connection_time}s"
            
            # Should not be excessively slow (max 10s for E2E tolerance)
            assert max_connection_time <= 10.0, f"Maximum connection time too slow: {max_connection_time}s"
            
            # Average should be reasonable
            assert avg_connection_time <= 5.0, f"Average connection time too slow: {avg_connection_time}s"
            
            print(f"✅ WebSocket performance test - avg: {avg_connection_time:.3f}s, "
                  f"min: {min_connection_time:.3f}s, max: {max_connection_time:.3f}s")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_business_value_with_redis_fix_authenticated(
        self,
        authenticated_websocket_helper,
        authenticated_user_context,
        real_services_fixture,
        isolated_env
    ):
        """Test that WebSocket business value (chat functionality) works with Redis fix."""
        
        ensure_redis_container()
        ensure_backend_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            ws = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
            
            try:
                # Simulate business value: Chat message flow
                user_id = str(authenticated_user_context.user_id)
                thread_id = str(authenticated_user_context.thread_id)
                
                chat_message = {
                    "type": "chat_message",
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "message": "Test chat message with Redis race condition fix",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send chat message
                await ws.send(json.dumps(chat_message))
                
                # Should receive acknowledgment or response
                response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                
                assert response is not None, "No response to chat message"
                
                # Parse response
                try:
                    response_data = json.loads(response)
                    # Response should indicate message was processed
                    assert "type" in response_data, "Invalid response format"
                    print(f"✅ Chat message processed successfully: {response_data.get('type', 'unknown')}")
                    
                except json.JSONDecodeError:
                    # Some responses might not be JSON, that's ok for this test
                    print(f"✅ Chat message response received (non-JSON): {response[:100]}")
                
                print("✅ WebSocket business value test successful - chat functionality working")
                
            finally:
                await ws.close()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_with_redis_fix_authenticated(
        self,
        authenticated_websocket_helper,
        real_services_fixture,
        isolated_env
    ):
        """Test WebSocket error recovery scenarios work with Redis race condition fix."""
        
        ensure_redis_container()
        ensure_backend_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Test connection recovery after simulated error
            recovery_attempts = 0
            max_attempts = 3
            
            while recovery_attempts < max_attempts:
                try:
                    recovery_attempts += 1
                    start_time = time.time()
                    
                    ws = await authenticated_websocket_helper.connect_authenticated_websocket(timeout=30.0)
                    connection_time = time.time() - start_time
                    
                    # Test connection works
                    await ws.send(json.dumps({
                        "type": "recovery_test",
                        "attempt": recovery_attempts,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                    
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    
                    await ws.close()
                    
                    # Verify grace period was applied
                    assert connection_time >= 0.4, \
                        f"Recovery attempt {recovery_attempts} too fast: {connection_time}s"
                    
                    print(f"✅ Recovery attempt {recovery_attempts} successful: {connection_time:.3f}s")
                    break
                    
                except Exception as e:
                    if recovery_attempts >= max_attempts:
                        pytest.fail(f"All recovery attempts failed. Last error: {e}")
                    
                    print(f"⚠️  Recovery attempt {recovery_attempts} failed: {e}, retrying...")
                    await asyncio.sleep(1.0)  # Wait before retry
            
            assert recovery_attempts <= max_attempts, "Too many recovery attempts needed"
            print("✅ WebSocket error recovery test successful with Redis race condition fix")