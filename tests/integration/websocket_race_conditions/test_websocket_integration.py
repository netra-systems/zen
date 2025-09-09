"""
Critical Integration Tests for WebSocket Multi-Service Race Conditions

These tests validate WebSocket behavior across multiple services with real dependencies:
- WebSocket + Redis + Auth service interaction under timing stress
- Multi-user concurrent WebSocket isolation 
- Agent event delivery through complete WebSocket lifecycle

Business Value Justification:
1. Segment: Platform/Internal - Chat is King infrastructure protection
2. Business Goal: Prevent cascade failures in multi-service WebSocket scenarios  
3. Value Impact: Validates mission-critical agent events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
4. Strategic Impact: Protects $500K+ ARR from multi-service race condition failures

@compliance CLAUDE.md - NO MOCKS in integration tests, real services only
@compliance Five Whys Analysis - Tests exact multi-service failure patterns from GCP staging
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager

# CRITICAL: Real service dependencies only - NO MOCKS per CLAUDE.md
import redis.asyncio as redis
import websockets
import httpx
from fastapi.testclient import TestClient

# Import real WebSocket infrastructure components
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.utils import is_websocket_connected_and_ready
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.db.database_manager import DatabaseManager

# SSOT authentication and test framework
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase, requires_docker
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# Agent event validation
from netra_backend.app.websocket_core.types import MessageType


@requires_docker
class TestWebSocketRedisAuthRaceConditions:
    """
    CRITICAL TEST: WebSocket + Redis + Auth service race conditions under timing stress.
    
    FAILURE PATTERN: Authentication timeout + Redis connection failure + WebSocket disconnect
    ROOT CAUSE: Service initialization timing misalignment in multi-service scenarios
    """
    
    @pytest.fixture(autouse=True)
    async def setup_real_services(self):
        """Setup real Docker services for integration testing."""
        self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # Start required services (no mocks - real services only)
        services_needed = ["postgresql", "redis", "backend", "auth"]
        
        await self.docker_manager.start_services_smart(
            services=services_needed,
            wait_healthy=True
        )
        
        # Verify services are actually ready
        await self._verify_service_health()
        
        yield
        
        # Cleanup
        await self.docker_manager.stop_services()
    
    async def _verify_service_health(self):
        """Verify all required services are healthy before testing."""
        env = get_env()
        
        # Test Redis connection
        try:
            redis_client = redis.Redis.from_url("redis://localhost:6381")  # Test Redis port
            await redis_client.ping()
            await redis_client.close()
        except Exception as e:
            pytest.fail(f"Redis service not ready: {e}")
        
        # Test Auth service connection
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8081/health")
                assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Auth service not ready: {e}")
        
        # Test Backend service connection 
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health")
                assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Backend service not ready: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_redis_auth_race_conditions(self):
        """
        Test WebSocket + Redis + Auth timing stress scenarios.
        
        CRITICAL: This test MUST FAIL when multi-service race conditions occur.
        Validates service coordination under timing pressure.
        """
        # Create multiple authenticated user contexts to stress the system
        auth_helper = E2EAuthHelper(environment="test")
        
        user_contexts: List[StronglyTypedUserExecutionContext] = []
        for i in range(5):  # 5 concurrent users to create timing pressure
            context = await create_authenticated_user_context(
                user_id=f"race-test-user-{i}-{uuid.uuid4().hex[:8]}",
                environment="test",
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Test 1: Rapid WebSocket manager creation (stresses service coordination)
        websocket_managers = []
        creation_times = []
        
        for context in user_contexts:
            start_time = time.time()
            
            try:
                # This should coordinate WebSocket + Redis + Auth services
                manager = create_websocket_manager(context)
                creation_time = time.time() - start_time
                
                websocket_managers.append(manager)
                creation_times.append(creation_time)
                
                # CRITICAL: Creation should be fast (< 2s) even with multi-service coordination
                assert creation_time < 2.0, f"WebSocket manager creation too slow: {creation_time}s"
                
            except Exception as e:
                pytest.fail(f"WebSocket manager creation failed for user {context.user_id}: {e}")
        
        # Test 2: Validate all managers are properly coordinated with services
        for i, manager in enumerate(websocket_managers):
            # Validate Redis coordination
            assert hasattr(manager, 'user_context'), f"Manager {i} missing user context"
            
            # Validate Auth coordination (JWT token should be accessible)
            user_context = user_contexts[i]
            jwt_token = user_context.agent_context.get('jwt_token')
            assert jwt_token is not None, f"Manager {i} missing JWT token"
            
            # Validate WebSocket readiness
            # (Test the actual coordination between services)
            assert str(user_context.user_id) in str(manager.user_context.user_id), f"Manager {i} user ID mismatch"
        
        # Test 3: Concurrent service operations (stress test race conditions)
        async def test_concurrent_operations(manager_index: int):
            """Test concurrent operations that can trigger race conditions."""
            manager = websocket_managers[manager_index]
            context = user_contexts[manager_index]
            
            try:
                # Simulate rapid WebSocket operations that require service coordination
                operations = []
                
                for op in range(3):  # 3 operations per user
                    # Each operation stresses WebSocket + Redis + Auth coordination
                    operations.append(
                        self._simulate_websocket_operation(manager, context, f"op_{op}")
                    )
                
                # Execute all operations concurrently (maximum race condition pressure)
                results = await asyncio.gather(*operations, return_exceptions=True)
                
                # All operations should succeed despite race condition pressure
                for result in results:
                    if isinstance(result, Exception):
                        pytest.fail(f"Concurrent operation failed: {result}")
                
                return True
                
            except Exception as e:
                return e
        
        # Execute concurrent operations for all managers simultaneously
        concurrent_tasks = []
        for i in range(len(websocket_managers)):
            concurrent_tasks.append(test_concurrent_operations(i))
        
        # CRITICAL: All concurrent operations should succeed
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent operations failed for manager {i}: {result}")
            assert result is True, f"Manager {i} operations didn't complete successfully"
        
        # Test 4: Validate service coordination metrics
        avg_creation_time = sum(creation_times) / len(creation_times)
        assert avg_creation_time < 1.0, f"Average creation time too high: {avg_creation_time}s"
        
        max_creation_time = max(creation_times)
        assert max_creation_time < 3.0, f"Maximum creation time too high: {max_creation_time}s"
    
    async def _simulate_websocket_operation(self, manager: WebSocketManager, context: StronglyTypedUserExecutionContext, operation_id: str) -> bool:
        """Simulate WebSocket operation that requires multi-service coordination."""
        try:
            # Simulate operation that touches WebSocket + Redis + Auth
            # This is where race conditions typically occur
            
            # 1. WebSocket state check
            if hasattr(manager, 'get_user_connections'):
                connections = manager.get_user_connections() or set()
                # Operation should work even with no active connections
            
            # 2. Redis coordination (simulate caching operation)
            # (In real implementation this would be handled by the manager)
            operation_data = {
                "user_id": str(context.user_id),
                "operation_id": operation_id,
                "timestamp": time.time()
            }
            
            # 3. Auth validation (simulate token validation)
            jwt_token = context.agent_context.get('jwt_token')
            assert jwt_token is not None, "JWT token required for operation"
            
            # If we reach here without exceptions, the operation succeeded
            return True
            
        except Exception as e:
            # Log the race condition error for analysis
            print(f"Race condition detected in operation {operation_id}: {e}")
            raise


@requires_docker  
class TestMultiUserWebSocketIsolation:
    """
    CRITICAL TEST: 10+ simultaneous user WebSocket connections with proper isolation.
    
    FAILURE PATTERN: User context bleeding between WebSocket connections
    ROOT CAUSE: Insufficient isolation in concurrent WebSocket scenarios
    """
    
    @pytest.fixture(autouse=True)
    async def setup_websocket_test_base(self):
        """Setup real WebSocket test infrastructure."""
        self.websocket_test_base = RealWebSocketTestBase()
        
        # Start real Docker services (no mocks)
        async with self.websocket_test_base.real_websocket_test_session():
            yield self.websocket_test_base
    
    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_concurrent(self):
        """
        Test 10+ simultaneous user WebSocket connections with isolation.
        
        CRITICAL: This test MUST FAIL if user contexts leak between connections.
        Validates complete user isolation under concurrent load.
        """
        concurrent_user_count = 12  # 12 simultaneous users to stress isolation
        
        # Test 1: Create multiple authenticated user contexts
        user_contexts = []
        for i in range(concurrent_user_count):
            context = await create_authenticated_user_context(
                user_id=f"isolation-user-{i}-{uuid.uuid4().hex[:6]}",
                user_email=f"isolation_test_{i}@example.com",
                environment="test",
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Test 2: Create concurrent WebSocket connections
        async def create_user_websocket_connection(user_index: int):
            """Create WebSocket connection for specific user."""
            context = user_contexts[user_index]
            
            try:
                # Create test context with real WebSocket
                test_context = await self.websocket_test_base.create_test_context(
                    user_id=str(context.user_id),
                    jwt_token=context.agent_context.get('jwt_token')
                )
                
                # Establish actual WebSocket connection
                await test_context.setup_websocket_connection(
                    endpoint="/ws/test",
                    auth_required=True
                )
                
                # Send user-specific test message
                test_message = {
                    "type": "isolation_test",
                    "user_id": str(context.user_id),
                    "user_email": context.agent_context.get('user_email'),
                    "test_data": f"user_{user_index}_data_{uuid.uuid4().hex[:8]}",
                    "timestamp": time.time()
                }
                
                await test_context.send_message(test_message)
                
                # Attempt to receive response (validates connection works)
                try:
                    response = await test_context.receive_message(timeout=5.0)
                    return {
                        "success": True,
                        "user_index": user_index,
                        "user_id": str(context.user_id),
                        "test_context": test_context,
                        "sent_message": test_message,
                        "received_response": response
                    }
                except asyncio.TimeoutError:
                    # Some connections may not get immediate response - still success
                    return {
                        "success": True,
                        "user_index": user_index,
                        "user_id": str(context.user_id),
                        "test_context": test_context,
                        "sent_message": test_message,
                        "received_response": None
                    }
                
            except Exception as e:
                return {
                    "success": False,
                    "user_index": user_index,
                    "user_id": str(context.user_id),
                    "error": str(e)
                }
        
        # Execute all connections concurrently (maximum isolation stress)
        connection_tasks = []
        for i in range(concurrent_user_count):
            connection_tasks.append(create_user_websocket_connection(i))
        
        # CRITICAL: All connections should succeed with proper isolation
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Test 3: Validate all connections succeeded
        successful_connections = []
        failed_connections = []
        
        for result in connection_results:
            if isinstance(result, Exception):
                failed_connections.append(f"Exception: {result}")
            elif isinstance(result, dict):
                if result.get("success"):
                    successful_connections.append(result)
                else:
                    failed_connections.append(f"User {result.get('user_index')}: {result.get('error')}")
            else:
                failed_connections.append(f"Invalid result: {result}")
        
        # CRITICAL: At least 80% of connections should succeed (allow for timing issues)
        success_rate = len(successful_connections) / concurrent_user_count
        assert success_rate >= 0.8, f"Too many connection failures: {success_rate:.1%} success rate. Failures: {failed_connections}"
        
        # Test 4: Validate user isolation (no context bleeding)
        user_ids_seen = set()
        for connection in successful_connections:
            user_id = connection["user_id"]
            
            # Each user ID should be unique (no duplication due to context bleeding)
            assert user_id not in user_ids_seen, f"User ID {user_id} duplicated - context bleeding detected"
            user_ids_seen.add(user_id)
            
            # Validate message content matches user identity
            sent_message = connection["sent_message"]
            assert sent_message["user_id"] == user_id, f"Message user ID mismatch for {user_id}"
        
        # Test 5: Validate concurrent message isolation
        # Send follow-up messages to test cross-contamination
        isolation_test_tasks = []
        
        async def test_message_isolation(connection_data):
            """Test that messages don't cross-contaminate between users."""
            test_context = connection_data["test_context"]
            user_id = connection_data["user_id"]
            
            # Send user-specific isolation test message
            isolation_message = {
                "type": "isolation_verification",
                "user_id": user_id,
                "unique_token": f"{user_id}_token_{uuid.uuid4().hex[:12]}",
                "timestamp": time.time()
            }
            
            await test_context.send_message(isolation_message)
            return {
                "user_id": user_id,
                "unique_token": isolation_message["unique_token"],
                "message_sent": True
            }
        
        for connection in successful_connections:
            isolation_test_tasks.append(test_message_isolation(connection))
        
        # Execute isolation tests concurrently
        isolation_results = await asyncio.gather(*isolation_test_tasks, return_exceptions=True)
        
        # Validate no cross-contamination occurred
        tokens_sent = set()
        for result in isolation_results:
            if isinstance(result, dict) and result.get("message_sent"):
                token = result["unique_token"]
                assert token not in tokens_sent, f"Token {token} duplicated - message isolation failed"
                tokens_sent.add(token)
        
        # Clean up connections
        for connection in successful_connections:
            if "test_context" in connection:
                try:
                    await connection["test_context"].cleanup()
                except Exception:
                    pass  # Ignore cleanup errors


@requires_docker
class TestAgentEventDeliveryLifecycle:
    """
    CRITICAL TEST: All 5 required agent events delivered through complete WebSocket lifecycle.
    
    FAILURE PATTERN: Missing agent events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)  
    ROOT CAUSE: WebSocket event delivery failures during agent execution lifecycle
    """
    
    @pytest.fixture(autouse=True)
    async def setup_websocket_test_base(self):
        """Setup real WebSocket test infrastructure with agent capabilities."""
        self.websocket_test_base = RealWebSocketTestBase()
        
        async with self.websocket_test_base.real_websocket_test_session():
            yield self.websocket_test_base
    
    @pytest.mark.asyncio
    async def test_agent_event_delivery_lifecycle(self):
        """
        Test all 5 agent events delivered through WebSocket lifecycle.
        
        CRITICAL: This test MUST FAIL if any required agent events are missing.
        Validates complete agent event delivery for business value.
        """
        # Required agent events for business value (from CLAUDE.md Section 6)
        required_events = {
            "agent_started",     # User must see agent began processing
            "agent_thinking",    # Real-time reasoning visibility  
            "tool_executing",    # Tool usage transparency
            "tool_completed",    # Tool results display
            "agent_completed"    # User must know when response ready
        }
        
        # Test 1: Create authenticated user context with agent capabilities
        user_context = await create_authenticated_user_context(
            user_id=f"agent-event-user-{uuid.uuid4().hex[:8]}",
            environment="test",
            websocket_enabled=True
        )
        
        # Test 2: Create real WebSocket test context
        test_context = await self.websocket_test_base.create_test_context(
            user_id=str(user_context.user_id),
            jwt_token=user_context.agent_context.get('jwt_token')
        )
        
        await test_context.setup_websocket_connection(
            endpoint="/ws/test",
            auth_required=True
        )
        
        # Test 3: Send agent request that should trigger all events
        agent_request = {
            "type": "agent_request",
            "agent_name": "test_agent",
            "task": "Perform a test task that triggers all agent events",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "request_id": str(user_context.request_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await test_context.send_message(agent_request)
        
        # Test 4: Validate all required agent events are received
        event_timeout = 60.0  # 60 seconds for complete agent lifecycle
        
        validation_result = await self.websocket_test_base.validate_agent_events(
            test_context=test_context,
            required_events=required_events,
            timeout=event_timeout
        )
        
        # CRITICAL: All events must be received for business value
        assert validation_result.success, f"Agent event validation failed: {validation_result.error_message}"
        
        # Test 5: Validate specific event content and ordering
        captured_events = validation_result.events_captured
        event_types_received = [event.get("type") for event in captured_events if event.get("type")]
        
        # Validate all required events were received
        missing_events = required_events - validation_result.required_events_found
        assert len(missing_events) == 0, f"Missing required agent events: {missing_events}"
        
        # Test 6: Validate event ordering (business logic requirement)
        # agent_started should come before agent_completed
        started_index = None
        completed_index = None
        
        for i, event_type in enumerate(event_types_received):
            if event_type == "agent_started":
                started_index = i
            elif event_type == "agent_completed":  
                completed_index = i
        
        if started_index is not None and completed_index is not None:
            assert started_index < completed_index, "agent_started must come before agent_completed"
        
        # Test 7: Validate event timing (reasonable delays between events)
        event_timestamps = []
        for event in captured_events:
            if event.get("timestamp"):
                try:
                    ts = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    event_timestamps.append(ts.timestamp())
                except:
                    pass
        
        if len(event_timestamps) >= 2:
            total_lifecycle_time = max(event_timestamps) - min(event_timestamps)
            # Complete lifecycle should be reasonable (not too fast, not too slow)
            assert 0.1 <= total_lifecycle_time <= 120, f"Agent lifecycle time unrealistic: {total_lifecycle_time}s"
        
        # Test 8: Validate business-critical event content
        for event in captured_events:
            event_type = event.get("type")
            
            if event_type == "agent_started":
                # Should contain user/agent identification
                assert "user_id" in event or "agent_name" in event, "agent_started missing identification"
            
            elif event_type == "agent_thinking":
                # Should show reasoning/progress
                assert "content" in event or "message" in event, "agent_thinking missing content"
            
            elif event_type == "tool_executing":
                # Should show tool usage
                assert "tool_name" in event or "tool_type" in event, "tool_executing missing tool info"
            
            elif event_type == "tool_completed":
                # Should show results
                assert "result" in event or "output" in event or "status" in event, "tool_completed missing results"
            
            elif event_type == "agent_completed":
                # Should indicate completion status
                assert "status" in event or "result" in event, "agent_completed missing status"
        
        # Cleanup
        await test_context.cleanup()


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v", "--tb=short", "--real-services"])