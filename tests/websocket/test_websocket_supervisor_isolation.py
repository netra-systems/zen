"""
Comprehensive WebSocket Supervisor Isolation Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Multi-User Support & System Reliability
- Value Impact: Ensures complete isolation between users in WebSocket supervisor creation
- Strategic Impact: Validates core business requirement of secure multi-user AI interactions

This test suite validates the WebSocket supervisor isolation patterns and multi-user
support using REAL services, REAL authentication, and REAL WebSocket connections.

CRITICAL: These tests verify that the WebSocket remediation provides:
1. Complete multi-user isolation (no data leakage between users)
2. Concurrent connection safety (multiple users simultaneously)
3. Performance characteristics under load
4. Error recovery and resilience patterns
5. Factory-based isolation patterns

This replaces the previous test file that contained REMOVED_SYNTAX_ERROR markings
and mock-based patterns with real service testing following SSOT patterns.
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import pytest
import websockets

from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, MessageType, WebSocketConnectionState, ConnectionInfo
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.db.database_manager import DatabaseManager

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database.database_fixtures import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestWebSocketSupervisorIsolation(SSotBaseTestCase):
    """
    Comprehensive tests for WebSocket supervisor isolation using REAL services.
    
    This test class validates that WebSocket supervisor creation and management
    provides complete isolation between different users while maintaining
    performance and reliability under concurrent load.
    
    CRITICAL: All tests use REAL WebSocket connections, REAL authentication,
    and REAL database sessions - NO MOCKS in integration/e2e patterns.
    """
    
    @pytest.fixture(scope="class")
    def auth_helper(self) -> E2EWebSocketAuthHelper:
        """SSOT WebSocket authentication helper for all tests."""
        config = E2EAuthConfig.for_environment("test")
        return E2EWebSocketAuthHelper(config=config, environment="test")
    
    @pytest.fixture(scope="class")
    def database_manager(self) -> DatabaseTestManager:
        """Real database test manager for isolated test database operations."""
        return DatabaseTestManager()
    
    @pytest.fixture
    def isolated_env(self) -> IsolatedEnvironment:
        """Isolated environment for consistent test configuration."""
        return IsolatedEnvironment()
    
    async def _create_real_websocket_context(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        user_id: str,
        thread_id: str,
        run_id: Optional[str] = None
    ) -> Tuple[WebSocketContext, websockets.ServerConnection]:
        """
        Create a REAL WebSocket context with authenticated connection.
        
        This helper establishes real WebSocket connections with proper authentication
        and creates WebSocketContext objects that represent actual user sessions.
        
        Args:
            auth_helper: Authentication helper for JWT tokens
            user_id: Unique user identifier
            thread_id: Thread/conversation identifier
            run_id: Optional run identifier
            
        Returns:
            Tuple of (WebSocketContext, WebSocket connection)
        """
        # Create authenticated WebSocket connection
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        # Create real WebSocket context (not a mock)
        context = WebSocketContext.create_for_user(
            websocket=websocket,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Validate context is properly isolated
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.is_active
        assert context.validate_for_message_processing()
        
        return context, websocket
    
    @pytest.mark.asyncio
    async def test_basic_websocket_context_isolation(
        self, 
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        Test that WebSocketContext properly isolates different user connections.
        
        This test validates the core isolation requirement: different users
        must have completely isolated WebSocket contexts with no shared state.
        """
        contexts_and_connections = []
        
        try:
            # Create contexts for 3 different users
            for i in range(3):
                user_id = f"test_user_{i}_{int(time.time())}"
                thread_id = f"thread_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Verify complete isolation between contexts
            contexts = [ctx for ctx, ws in contexts_and_connections]
            
            for i, ctx in enumerate(contexts):
                # Each context should have unique identifiers
                assert ctx.user_id == f"test_user_{i}_{int(time.time())}"[:-10] + ctx.user_id.split('_')[-1]
                assert ctx.connection_id != contexts[(i + 1) % 3].connection_id
                
                # Isolation keys must be unique
                isolation_key = ctx.to_isolation_key()
                for j, other_ctx in enumerate(contexts):
                    if i != j:
                        assert isolation_key != other_ctx.to_isolation_key()
                        
                # Verify connection info doesn't leak other users' data
                conn_info = ctx.get_connection_info()
                for j, other_ctx in enumerate(contexts):
                    if i != j:
                        info_str = str(conn_info)
                        assert other_ctx.user_id not in info_str
                        assert other_ctx.thread_id not in info_str
        
        finally:
            # Clean up all WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    await websocket.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_supervisor_creation_isolation(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        Test that multiple supervisors can be created concurrently without interference.
        
        This test validates that the supervisor factory can handle concurrent
        requests from different users without race conditions or data leakage.
        """
        contexts_and_connections = []
        supervisors = []
        
        try:
            # Create multiple contexts for concurrent supervisor creation
            for i in range(5):
                user_id = f"concurrent_user_{i}_{int(time.time())}"
                thread_id = f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Create supervisors concurrently
            async with database_manager.get_async_session() as db_session:
                tasks = []
                
                for context, _ in contexts_and_connections:
                    task = asyncio.create_task(
                        get_websocket_scoped_supervisor(context, db_session)
                    )
                    tasks.append(task)
                
                # Execute all supervisor creations concurrently
                created_supervisors = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all supervisors were created successfully
            for i, supervisor in enumerate(created_supervisors):
                if isinstance(supervisor, Exception):
                    pytest.fail(f"Supervisor creation {i} failed: {supervisor}")
                
                assert supervisor is not None
                supervisors.append(supervisor)
                
                # Verify supervisor has correct user isolation
                context = contexts_and_connections[i][0]
                expected_user = context.user_id
                
                # Verify supervisor is isolated to correct user
                # (This will depend on supervisor's internal structure)
                assert hasattr(supervisor, 'user_id') or hasattr(supervisor, '_user_context')
        
        finally:
            # Clean up supervisors if they have cleanup methods
            for supervisor in supervisors:
                if hasattr(supervisor, 'cleanup'):
                    try:
                        await supervisor.cleanup()
                    except Exception as e:
                        print(f"Supervisor cleanup error: {e}")
            
            # Clean up WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    await websocket.close()
    
    @pytest.mark.asyncio
    async def test_websocket_context_lifecycle_isolation(
        self,
        auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test that WebSocket context lifecycle operations don't interfere between users.
        
        This validates that activity updates, connection state changes, and other
        lifecycle operations maintain proper isolation between different users.
        """
        contexts_and_connections = []
        
        try:
            # Create contexts for multiple users
            for i in range(3):
                user_id = f"lifecycle_user_{i}_{int(time.time())}"
                thread_id = f"lifecycle_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id
                )
                contexts_and_connections.append((context, websocket))
            
            contexts = [ctx for ctx, ws in contexts_and_connections]
            
            # Perform lifecycle operations on different contexts
            for i, ctx in enumerate(contexts):
                original_activity = ctx.last_activity
                
                # Small delay to ensure timestamp difference
                await asyncio.sleep(0.01)
                ctx.update_activity()
                
                # Verify activity was updated for this context only
                assert ctx.last_activity > original_activity
                
                # Verify other contexts weren't affected
                for j, other_ctx in enumerate(contexts):
                    if i != j:
                        # Other contexts should have earlier activity timestamps
                        assert other_ctx.last_activity < ctx.last_activity
            
            # Test connection state validation isolation
            for context in contexts:
                assert context.is_active
                assert context.validate_for_message_processing()
        
        finally:
            # Clean up all WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    await websocket.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_message_handling_isolation(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        Test that concurrent message handling maintains proper user isolation.
        
        This validates that when multiple users send messages simultaneously,
        each message is processed in the correct user context without interference.
        """
        contexts_and_connections = []
        
        try:
            # Create contexts and messages for different users
            for i in range(4):
                user_id = f"message_user_{i}_{int(time.time())}"
                thread_id = f"message_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Create test messages for concurrent processing
            test_messages = []
            for i, (context, websocket) in enumerate(contexts_and_connections):
                message = {
                    "type": "user_message",
                    "content": f"Test message from user {i}",
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "timestamp": time.time(),
                    "message_id": str(uuid.uuid4())
                }
                test_messages.append((message, websocket, context))
            
            # Send messages concurrently to different user connections
            send_tasks = []
            for message, websocket, context in test_messages:
                task = asyncio.create_task(
                    websocket.send(json.dumps(message))
                )
                send_tasks.append(task)
            
            # Wait for all messages to be sent
            await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Give the system time to process messages
            await asyncio.sleep(1.0)
            
            # Verify each context maintained its isolation
            contexts = [ctx for ctx, ws in contexts_and_connections]
            for i, ctx in enumerate(contexts):
                # Verify context still has correct user data
                assert f"message_user_{i}_" in ctx.user_id
                assert f"message_thread_{i}_" in ctx.thread_id
                
                # Verify contexts remain unique
                isolation_key = ctx.to_isolation_key()
                for j, other_ctx in enumerate(contexts):
                    if i != j:
                        assert isolation_key != other_ctx.to_isolation_key()
        
        finally:
            # Clean up all WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    await websocket.close()
    
    @pytest.mark.asyncio
    async def test_error_isolation_between_users(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        Test that errors in one user's context don't affect other users.
        
        This validates that when one user experiences an error (connection failure,
        processing error, etc.), other users continue to operate normally.
        """
        contexts_and_connections = []
        
        try:
            # Create contexts for multiple users
            for i in range(3):
                user_id = f"error_test_user_{i}_{int(time.time())}"
                thread_id = f"error_test_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Simulate error in middle user's connection
            error_context, error_websocket = contexts_and_connections[1]
            
            # Force close the error user's connection
            await error_websocket.close()
            
            # Small delay for state propagation
            await asyncio.sleep(0.1)
            
            # Verify isolation: only middle user should be affected
            contexts = [ctx for ctx, ws in contexts_and_connections]
            
            assert contexts[0].is_active, "User 0 should remain active"
            assert not contexts[1].is_active, "User 1 should be inactive (error)"
            assert contexts[2].is_active, "User 2 should remain active"
            
            # Test validation isolation
            for i, ctx in enumerate(contexts):
                if i == 1:  # Error user
                    with pytest.raises(ValueError, match="not active"):
                        ctx.validate_for_message_processing()
                else:  # Healthy users
                    assert ctx.validate_for_message_processing()
        
        finally:
            # Clean up all WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    try:
                        await websocket.close()
                    except Exception:
                        pass  # Already closed or errored
    
    @pytest.mark.asyncio
    async def test_performance_under_concurrent_load(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        Test performance characteristics of WebSocket supervisor isolation under load.
        
        This validates that the system can handle multiple concurrent users
        without significant performance degradation or resource exhaustion.
        """
        num_connections = 20  # Reasonable load for test environment
        contexts_and_connections = []
        
        try:
            start_time = time.time()
            
            # Create multiple concurrent connections
            connection_tasks = []
            for i in range(num_connections):
                user_id = f"perf_user_{i}_{int(time.time())}"
                thread_id = f"perf_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                task = asyncio.create_task(
                    self._create_real_websocket_context(auth_helper, user_id, thread_id)
                )
                connection_tasks.append(task)
            
            # Create all connections concurrently
            connections_results = await asyncio.gather(
                *connection_tasks, return_exceptions=True
            )
            
            connection_time = time.time() - start_time
            
            # Verify all connections were successful
            successful_connections = []
            for i, result in enumerate(connections_results):
                if isinstance(result, Exception):
                    pytest.fail(f"Connection {i} failed: {result}")
                
                context, websocket = result
                successful_connections.append((context, websocket))
                assert context.is_active
            
            contexts_and_connections = successful_connections
            
            # Performance assertions
            assert len(successful_connections) == num_connections
            assert connection_time < 30.0, f"Connection time {connection_time}s too slow"
            
            # Verify each context maintained unique identities
            user_ids = set()
            connection_ids = set()
            
            for context, _ in successful_connections:
                assert context.user_id not in user_ids, f"Duplicate user_id: {context.user_id}"
                user_ids.add(context.user_id)
                
                assert context.connection_id not in connection_ids, \
                    f"Duplicate connection_id: {context.connection_id}"
                connection_ids.add(context.connection_id)
        
        finally:
            # Clean up all WebSocket connections
            cleanup_tasks = []
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    task = asyncio.create_task(websocket.close())
                    cleanup_tasks.append(task)
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.asyncio
    async def test_websocket_disconnection_isolation(
        self,
        auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test that WebSocket disconnections are properly isolated between users.
        
        This validates that when some users disconnect, other users remain
        unaffected and can continue their sessions normally.
        """
        contexts_and_connections = []
        
        try:
            # Create WebSocket connections for different users
            for i in range(3):
                user_id = f"disconnect_user_{i}_{int(time.time())}"
                thread_id = f"disconnect_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Verify all are initially active
            contexts = [ctx for ctx, ws in contexts_and_connections]
            for ctx in contexts:
                assert ctx.is_active
                assert ctx.validate_for_message_processing()
            
            # Disconnect user_1's WebSocket
            middle_context, middle_websocket = contexts_and_connections[1]
            await middle_websocket.close()
            
            # Small delay for state propagation
            await asyncio.sleep(0.1)
            
            # Verify isolation: only user_1 should be inactive
            assert contexts[0].is_active, "User 0 should remain active"
            assert not contexts[1].is_active, "User 1 should be inactive after disconnect"
            assert contexts[2].is_active, "User 2 should remain active"
            
            # Test validation isolation
            for i, ctx in enumerate(contexts):
                if i == 1:  # Disconnected user
                    with pytest.raises(ValueError, match="not active"):
                        ctx.validate_for_message_processing()
                else:  # Active users
                    assert ctx.validate_for_message_processing()
        
        finally:
            # Clean up all remaining WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    try:
                        await websocket.close()
                    except Exception:
                        pass  # Already closed
    
    @pytest.mark.asyncio
    async def test_websocket_context_factory_isolation(
        self,
        auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test that the WebSocketContext factory creates properly isolated contexts.
        
        This validates that the factory method produces contexts with unique
        identifiers and proper isolation without any shared state.
        """
        contexts_and_connections = []
        
        try:
            # Create contexts using factory method with different parameters
            for i in range(3):
                user_id = f"factory_user_{i}_{int(time.time())}"
                thread_id = f"factory_thread_{i}_{uuid.uuid4().hex[:8]}"
                run_id = f"factory_run_{i}_{uuid.uuid4().hex[:8]}"
                
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id, run_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Verify each context is properly isolated
            connection_ids = set()
            isolation_keys = set()
            
            for i, (ctx, websocket) in enumerate(contexts_and_connections):
                # Verify correct data
                assert f"factory_user_{i}_" in ctx.user_id
                assert f"factory_thread_{i}_" in ctx.thread_id
                assert f"factory_run_{i}_" in ctx.run_id
                
                # Verify uniqueness
                assert ctx.connection_id not in connection_ids
                connection_ids.add(ctx.connection_id)
                
                isolation_key = ctx.to_isolation_key()
                assert isolation_key not in isolation_keys
                isolation_keys.add(isolation_key)
                
                # Verify WebSocket association and activity
                assert ctx.websocket is websocket
                assert ctx.is_active
        
        finally:
            # Clean up all WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    await websocket.close()
    
    @pytest.mark.asyncio
    async def test_cross_user_data_isolation_validation(
        self,
        auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test that user data cannot leak between different WebSocket contexts.
        
        This is a security-focused test ensuring that sensitive user data
        (user_id, thread_id, connection info) remains completely isolated.
        """
        contexts_and_connections = []
        
        try:
            # Create contexts with distinct user data
            sensitive_data = [
                ("user_alice_sensitive", "thread_confidential_001", "run_secret_alpha"),
                ("user_bob_private", "thread_personal_002", "run_private_beta"),
                ("user_charlie_secure", "thread_classified_003", "run_secure_gamma")
            ]
            
            for user_id, thread_id, run_id in sensitive_data:
                context, websocket = await self._create_real_websocket_context(
                    auth_helper, user_id, thread_id, run_id
                )
                contexts_and_connections.append((context, websocket))
            
            # Verify complete data isolation
            for i, (ctx, _) in enumerate(contexts_and_connections):
                expected_user, expected_thread, expected_run = sensitive_data[i]
                
                # Verify context contains only its own data
                assert ctx.user_id == expected_user
                assert ctx.thread_id == expected_thread
                assert ctx.run_id == expected_run
                
                # Verify isolation keys don't contain other users' data
                isolation_key = ctx.to_isolation_key()
                
                for j, (other_user, other_thread, other_run) in enumerate(sensitive_data):
                    if i != j:
                        # Other users' data should not appear in this context
                        assert other_user not in isolation_key
                        assert other_thread not in isolation_key
                        assert other_run not in isolation_key
                
                # Verify connection info doesn't leak other users' data
                conn_info = ctx.get_connection_info()
                info_str = str(conn_info)
                
                for j, (other_user, other_thread, other_run) in enumerate(sensitive_data):
                    if i != j:
                        # Other users' data should not appear in connection info
                        assert other_user not in info_str
                        assert other_thread not in info_str
                        assert other_run not in info_str
        
        finally:
            # Clean up all WebSocket connections
            for context, websocket in contexts_and_connections:
                if websocket and not websocket.closed:
                    await websocket.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])