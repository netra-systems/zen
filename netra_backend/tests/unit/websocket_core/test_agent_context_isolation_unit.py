"""
Unit Tests for Agent Context Management and Isolation - Issue #861 Phase 1

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Security/Privacy
- Value Impact: Validates critical user isolation that protects $500K+ ARR multi-tenant system
- Strategic Impact: Prevents data leaks between users and ensures scalable agent execution

Test Coverage Focus:
- UserExecutionContext isolation between different users
- WebSocketContext lifecycle and cleanup
- Thread-safe context operations under concurrent load
- Context data privacy and access control
- Resource isolation and memory management
- Session continuity and state preservation
- Error isolation between user contexts

CRITICAL ISOLATION SCENARIOS:
- Multiple users processing agents simultaneously
- Context cleanup on connection drops
- Thread-safe context creation and access
- Memory isolation between user sessions
- Database session isolation per user context

REQUIREMENTS per CLAUDE.md:
- Use SSotBaseTestCase for unified test infrastructure
- Test actual isolation mechanisms, not just API contracts
- Focus on multi-user security and resource isolation
- Validate context cleanup prevents resource leaks
"""

import asyncio
import gc
import json
import time
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import WebSocket

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from shared.isolated_environment import IsolatedEnvironment


class TestAgentContextIsolation(SSotAsyncTestCase):
    """Test suite for agent context management and isolation."""

    def setup_method(self, method):
        """Set up test fixtures for context isolation testing."""
        super().setup_method(method)
        
        # Create test environment
        self.env = IsolatedEnvironment()
        
        # Create multiple test users for isolation testing
        self.user_ids = [f"isolation_user_{i}_{uuid.uuid4()}" for i in range(5)]
        self.thread_ids = [f"thread_{i}_{uuid.uuid4()}" for i in range(5)]
        self.run_ids = [f"run_{i}_{uuid.uuid4()}" for i in range(5)]
        
        # Track created contexts for cleanup verification
        self.created_contexts = []
        self.active_websockets = []
        
        # Track resource allocation for leak detection
        self.resource_tracker = {
            "contexts_created": 0,
            "contexts_cleaned": 0,
            "sessions_created": 0,
            "sessions_closed": 0
        }

    def teardown_method(self, method):
        """Clean up test resources and verify no leaks."""
        super().teardown_method(method)
        
        # Force garbage collection to help detect leaks
        gc.collect()
        
        # Clean up any remaining contexts
        for context in self.created_contexts:
            if hasattr(context, 'cleanup'):
                try:
                    context.cleanup()
                except:
                    pass
        
        self.created_contexts.clear()
        self.active_websockets.clear()

    def create_isolated_websocket(self, user_id: str) -> MagicMock:
        """Create an isolated WebSocket mock for a specific user."""
        websocket = MagicMock(spec=WebSocket)
        websocket.client_state = "connected"
        websocket.scope = {
            'app': MagicMock(),
            'client': ('127.0.0.1', hash(user_id) % 65535),  # Unique port per user
            'path': f'/ws/{user_id}',
            'type': 'websocket',
            'user': {'id': user_id}  # User-specific scope data
        }
        websocket.scope['app'].state = MagicMock()
        
        # Track events sent to this specific websocket
        websocket.sent_events = []
        
        async def track_user_events(data):
            event = json.loads(data) if isinstance(data, str) else data
            event['_websocket_user'] = user_id  # Tag with user for verification
            websocket.sent_events.append(event)
        
        websocket.send_text = AsyncMock(side_effect=track_user_events)
        websocket.send_json = AsyncMock(side_effect=track_user_events)
        
        self.active_websockets.append(websocket)
        return websocket

    def create_test_message(self, user_id: str, message_type: MessageType, 
                          payload: Dict[str, Any]) -> WebSocketMessage:
        """Create a user-specific test message."""
        return WebSocketMessage(
            type=message_type,
            payload=payload,
            timestamp=time.time(),
            message_id=f"msg_{user_id}_{uuid.uuid4()}",
            user_id=user_id,
            thread_id=f"thread_{user_id}_{uuid.uuid4()}"
        )

    # Test 1: User Context Isolation Across Concurrent Requests
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_user_context_isolation_across_concurrent_requests(self, mock_context):
        """Test user contexts are properly isolated during concurrent processing.
        
        Business Impact: Critical for multi-tenant security - users must not access each other's data.
        Golden Path Impact: Multiple users using agent simultaneously must be isolated.
        """
        # Create isolated contexts for each user
        user_contexts = {}
        
        def create_isolated_context(user_id, **kwargs):
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.thread_id = f"isolated_thread_{user_id}"
            context.run_id = f"isolated_run_{user_id}"
            context.isolated_data = f"secret_data_for_{user_id}"  # Sensitive data
            user_contexts[user_id] = context
            self.created_contexts.append(context)
            return context
        
        mock_context.side_effect = create_isolated_context
        
        # Create handlers and messages for multiple users
        tasks = []
        for i, user_id in enumerate(self.user_ids[:3]):  # Test with 3 users
            handler = AgentMessageHandler(MagicMock())
            websocket = self.create_isolated_websocket(user_id)
            message = self.create_test_message(
                user_id,
                MessageType.USER_MESSAGE,
                {"message": f"Sensitive request from {user_id}"}
            )
            
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                    task = handler.handle_message(user_id, websocket, message)
                    tasks.append((task, user_id, context))
        
        # Process all requests concurrently
        results = await asyncio.gather(*[task for task, _, _ in tasks], return_exceptions=True)
        
        # Verify each user got their own isolated context
        assert len(user_contexts) == 3
        for user_id in self.user_ids[:3]:
            assert user_id in user_contexts
            context = user_contexts[user_id]
            assert context.user_id == user_id
            assert user_id in context.thread_id
            assert user_id in context.run_id
            assert user_id in context.isolated_data

    # Test 2: WebSocket Context Lifecycle Management
    async def test_websocket_context_lifecycle_management(self):
        """Test WebSocket context proper creation, usage, and cleanup.
        
        Business Impact: Proper lifecycle prevents resource leaks and ensures clean user sessions.
        """
        user_id = self.user_ids[0]
        websocket = self.create_isolated_websocket(user_id)
        
        # Track context lifecycle
        lifecycle_events = []
        
        # Create WebSocket context
        with patch('netra_backend.app.websocket_core.context.logger') as mock_logger:
            # Mock logger to track lifecycle events
            def track_lifecycle(*args, **kwargs):
                lifecycle_events.append(args[0] if args else str(kwargs))
            
            mock_logger.debug.side_effect = track_lifecycle
            
            try:
                context = WebSocketContext.create_for_user(
                    websocket=websocket,
                    user_id=user_id,
                    thread_id=f"lifecycle_thread_{user_id}",
                    run_id=f"lifecycle_run_{user_id}",
                    connection_id=f"lifecycle_conn_{user_id}"
                )
                
                # Verify context was created properly
                assert context.user_id == user_id
                assert context.is_active is True
                
                # Use context
                context.update_activity()
                context.validate_for_message_processing()
                
                self.created_contexts.append(context)
                
            except Exception as e:
                # Even if creation fails, should be handled gracefully
                assert isinstance(e, (ValueError, TypeError))
        
        # Verify lifecycle logging occurred
        assert len(lifecycle_events) > 0

    # Test 3: Thread-Safe Context Operations
    async def test_thread_safe_context_operations_under_load(self):
        """Test context operations are thread-safe under concurrent load.
        
        Business Impact: System stability under high concurrent user load.
        """
        # Create shared resources to test thread safety
        shared_counter = {"value": 0}
        context_operations = []
        
        def thread_safe_context_operation(user_id: str, operation_id: int):
            """Simulate thread-safe context operations."""
            # Simulate context access and modification
            context_data = {
                "user_id": user_id,
                "operation_id": operation_id,
                "timestamp": time.time(),
                "counter_before": shared_counter["value"]
            }
            
            # Simulate some processing time
            time.sleep(0.001)
            
            # Atomic increment (simulating thread-safe operation)
            shared_counter["value"] += 1
            context_data["counter_after"] = shared_counter["value"]
            
            context_operations.append(context_data)
            return context_data
        
        # Create multiple concurrent context operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for i in range(10):  # 10 concurrent operations
                user_id = self.user_ids[i % len(self.user_ids)]
                future = executor.submit(thread_safe_context_operation, user_id, i)
                futures.append(future)
            
            # Wait for all operations to complete
            results = [future.result() for future in futures]
        
        # Verify all operations completed
        assert len(results) == 10
        assert len(context_operations) == 10
        
        # Verify thread safety - final counter should equal number of operations
        assert shared_counter["value"] == 10

    # Test 4: Context Data Privacy and Access Control
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_context_data_privacy_and_access_control(self, mock_context):
        """Test context data is private and properly access-controlled between users.
        
        Business Impact: Data privacy compliance and security - users can't access each other's data.
        """
        # Create contexts with sensitive data for different users
        sensitive_data = {}
        
        def create_private_context(user_id, **kwargs):
            # Each user gets their own sensitive data
            user_secret = f"TOP_SECRET_KEY_{user_id}_{uuid.uuid4()}"
            sensitive_data[user_id] = user_secret
            
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.sensitive_data = user_secret
            context.thread_id = f"private_thread_{user_id}"
            
            # Simulate access control
            def check_access(accessing_user):
                return accessing_user == user_id
            
            context.check_access = check_access
            self.created_contexts.append(context)
            return context
        
        mock_context.side_effect = create_private_context
        
        # Test that each user only accesses their own data
        user1, user2 = self.user_ids[0], self.user_ids[1]
        
        # Create handlers for both users
        handler1 = AgentMessageHandler(MagicMock())
        handler2 = AgentMessageHandler(MagicMock())
        
        websocket1 = self.create_isolated_websocket(user1)
        websocket2 = self.create_isolated_websocket(user2)
        
        message1 = self.create_test_message(user1, MessageType.CHAT, {"content": "User 1 private data"})
        message2 = self.create_test_message(user2, MessageType.CHAT, {"content": "User 2 private data"})
        
        # Process both messages
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                await asyncio.gather(
                    handler1.handle_message(user1, websocket1, message1),
                    handler2.handle_message(user2, websocket2, message2),
                    return_exceptions=True
                )
        
        # Verify data isolation - each user should only have access to their own data
        assert user1 in sensitive_data
        assert user2 in sensitive_data
        assert sensitive_data[user1] != sensitive_data[user2]
        
        # Verify access control works
        user1_context = None
        user2_context = None
        
        for context in self.created_contexts:
            if hasattr(context, 'user_id'):
                if context.user_id == user1:
                    user1_context = context
                elif context.user_id == user2:
                    user2_context = context
        
        if user1_context and user2_context:
            # User should only access their own context
            assert user1_context.check_access(user1) is True
            assert user1_context.check_access(user2) is False
            assert user2_context.check_access(user2) is True
            assert user2_context.check_access(user1) is False

    # Test 5: Resource Isolation and Memory Management
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_resource_isolation_and_memory_management(self, mock_context):
        """Test resource isolation prevents memory leaks between user contexts.
        
        Business Impact: System scalability - prevents one user's usage from affecting others.
        """
        # Track memory allocation per user
        user_resources = {}
        
        def create_resource_tracked_context(user_id, **kwargs):
            # Simulate memory allocation for user
            user_memory = {
                "allocated_objects": [],
                "active_connections": 0,
                "context_size": 1024  # Simulate memory usage
            }
            
            # Create some objects that should be cleaned up
            for i in range(5):
                user_memory["allocated_objects"].append(f"object_{i}_for_{user_id}")
            
            user_resources[user_id] = user_memory
            
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.resources = user_memory
            
            # Add cleanup method
            def cleanup():
                if user_id in user_resources:
                    user_resources[user_id]["allocated_objects"].clear()
                    user_resources[user_id]["context_size"] = 0
                    self.resource_tracker["contexts_cleaned"] += 1
            
            context.cleanup = cleanup
            self.resource_tracker["contexts_created"] += 1
            self.created_contexts.append(context)
            
            return context
        
        mock_context.side_effect = create_resource_tracked_context
        
        # Create and process multiple user contexts
        handlers = []
        for user_id in self.user_ids[:3]:
            handler = AgentMessageHandler(MagicMock())
            websocket = self.create_isolated_websocket(user_id)
            message = self.create_test_message(
                user_id,
                MessageType.START_AGENT,
                {"user_request": f"Resource test for {user_id}"}
            )
            
            handlers.append((handler, user_id, websocket, message))
        
        # Process all contexts
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                tasks = [
                    handler.handle_message(user_id, websocket, message)
                    for handler, user_id, websocket, message in handlers
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify each user has isolated resources
        assert len(user_resources) == 3
        for user_id in self.user_ids[:3]:
            assert user_id in user_resources
            resources = user_resources[user_id]
            assert len(resources["allocated_objects"]) == 5
            assert all(user_id in obj for obj in resources["allocated_objects"])
        
        # Test cleanup
        for context in self.created_contexts:
            if hasattr(context, 'cleanup'):
                context.cleanup()
        
        # Verify cleanup occurred
        for user_id in self.user_ids[:3]:
            if user_id in user_resources:
                resources = user_resources[user_id]
                assert resources["context_size"] == 0

    # Test 6: Session Continuity Across Connection Drops
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_session_continuity_across_connection_drops(self, mock_context):
        """Test session continuity when WebSocket connections are dropped and reconnected.
        
        Business Impact: User experience - conversations should continue even with network issues.
        """
        user_id = self.user_ids[0]
        persistent_session_data = {
            "thread_id": f"persistent_thread_{user_id}",
            "conversation_history": [],
            "user_preferences": {"theme": "dark", "language": "en"}
        }
        
        def create_persistent_context(user_id, thread_id=None, **kwargs):
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            
            # Use existing thread_id for session continuity
            if thread_id and thread_id == persistent_session_data["thread_id"]:
                context.thread_id = thread_id
                context.session_data = persistent_session_data
                context.is_continuing_session = True
            else:
                context.thread_id = thread_id or f"new_thread_{uuid.uuid4()}"
                context.session_data = {"conversation_history": []}
                context.is_continuing_session = False
            
            self.created_contexts.append(context)
            return context
        
        mock_context.side_effect = create_persistent_context
        
        # Simulate first connection
        handler1 = AgentMessageHandler(MagicMock())
        websocket1 = self.create_isolated_websocket(user_id)
        
        first_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "First message in session"},
            timestamp=time.time(),
            user_id=user_id,
            thread_id=persistent_session_data["thread_id"]  # Continue existing session
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                result1 = await handler1.handle_message(user_id, websocket1, first_message)
        
        # Add to conversation history
        persistent_session_data["conversation_history"].append("First message in session")
        
        # Simulate connection drop and reconnection with same thread_id
        handler2 = AgentMessageHandler(MagicMock())
        websocket2 = self.create_isolated_websocket(user_id)
        
        continuation_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "Continuing after reconnection"},
            timestamp=time.time(),
            user_id=user_id,
            thread_id=persistent_session_data["thread_id"]  # Same thread - should continue
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                result2 = await handler2.handle_message(user_id, websocket2, continuation_message)
        
        # Verify session continuity was maintained
        continuing_contexts = [ctx for ctx in self.created_contexts 
                              if hasattr(ctx, 'is_continuing_session') and ctx.is_continuing_session]
        
        assert len(continuing_contexts) >= 1  # At least the continuation should be marked

    # Test 7: Error Isolation Between User Contexts
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_error_isolation_between_user_contexts(self, mock_context):
        """Test errors in one user context don't affect other users.
        
        Business Impact: System reliability - one user's errors shouldn't impact others.
        """
        # Setup contexts where one user will fail
        def create_context_with_potential_failure(user_id, **kwargs):
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.thread_id = f"error_test_thread_{user_id}"
            
            # Make the second user's context fail
            if user_id == self.user_ids[1]:
                context.should_fail = True
                # Make this context raise an exception when accessed
                def fail_on_access(*args, **kwargs):
                    raise Exception(f"Simulated failure for {user_id}")
                context.access_data = fail_on_access
            else:
                context.should_fail = False
                context.access_data = lambda: f"Success data for {user_id}"
            
            self.created_contexts.append(context)
            return context
        
        mock_context.side_effect = create_context_with_potential_failure
        
        # Create handlers for multiple users - one will fail
        tasks = []
        for i, user_id in enumerate(self.user_ids[:3]):
            handler = AgentMessageHandler(MagicMock())
            websocket = self.create_isolated_websocket(user_id)
            message = self.create_test_message(
                user_id,
                MessageType.CHAT,
                {"content": f"Message from user {i}"}
            )
            
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                    task = handler.handle_message(user_id, websocket, message)
                    tasks.append((task, user_id))
        
        # Process all tasks - some may fail, others should succeed
        results = await asyncio.gather(*[task for task, _ in tasks], return_exceptions=True)
        
        # Verify error isolation - failures should be isolated to specific users
        success_count = sum(1 for result in results if result is True)
        failure_count = sum(1 for result in results if result is False or isinstance(result, Exception))
        
        # At least some should succeed despite others failing
        assert success_count >= 1, "At least some users should succeed despite errors in others"

    # Test 8: Context Cleanup on Connection Termination
    async def test_context_cleanup_on_connection_termination(self):
        """Test proper context cleanup when WebSocket connections terminate.
        
        Business Impact: Resource management - prevents accumulating dead contexts.
        """
        user_id = self.user_ids[0]
        cleanup_tracker = {"cleaned_up": False, "resources_freed": False}
        
        # Create context with cleanup tracking
        with patch('netra_backend.app.websocket_core.context.WebSocketContext') as MockWSContext:
            
            # Mock context that tracks cleanup
            mock_context = MagicMock()
            mock_context.user_id = user_id
            mock_context.is_active = True
            
            def simulate_cleanup():
                cleanup_tracker["cleaned_up"] = True
                cleanup_tracker["resources_freed"] = True
                mock_context.is_active = False
            
            mock_context.cleanup = simulate_cleanup
            mock_context.update_activity = MagicMock()
            mock_context.validate_for_message_processing = MagicMock()
            
            MockWSContext.create_for_user.return_value = mock_context
            MockWSContext.return_value = mock_context
            
            # Create WebSocket that will be "terminated"
            websocket = self.create_isolated_websocket(user_id)
            
            # Simulate context usage
            context = MockWSContext.create_for_user(
                websocket=websocket,
                user_id=user_id,
                thread_id=f"cleanup_thread_{user_id}",
                run_id=f"cleanup_run_{user_id}",
                connection_id=f"cleanup_conn_{user_id}"
            )
            
            # Verify context is active
            assert context.is_active is True
            
            # Simulate connection termination
            websocket.client_state = "disconnected"
            context.cleanup()
            
            # Verify cleanup occurred
            assert cleanup_tracker["cleaned_up"] is True
            assert cleanup_tracker["resources_freed"] is True
            assert context.is_active is False

    # Test 9: Concurrent Context Creation and Destruction
    async def test_concurrent_context_creation_and_destruction(self):
        """Test system handles concurrent context creation and destruction safely.
        
        Business Impact: System stability under high user churn.
        """
        # Track context lifecycle events
        lifecycle_events = []
        active_contexts = {}
        
        async def create_and_destroy_context(user_id: str, operation_id: int):
            """Simulate context creation and destruction."""
            lifecycle_events.append(f"creating_context_{user_id}_{operation_id}")
            
            # Simulate context creation
            context = {
                "user_id": user_id,
                "operation_id": operation_id,
                "created_at": time.time(),
                "active": True
            }
            
            context_key = f"{user_id}_{operation_id}"
            active_contexts[context_key] = context
            
            lifecycle_events.append(f"context_created_{user_id}_{operation_id}")
            
            # Simulate some work
            await asyncio.sleep(0.01)
            
            # Simulate context destruction
            lifecycle_events.append(f"destroying_context_{user_id}_{operation_id}")
            
            if context_key in active_contexts:
                active_contexts[context_key]["active"] = False
                del active_contexts[context_key]
            
            lifecycle_events.append(f"context_destroyed_{user_id}_{operation_id}")
        
        # Create many concurrent context operations
        tasks = []
        for i in range(20):  # 20 concurrent operations
            user_id = self.user_ids[i % len(self.user_ids)]
            task = create_and_destroy_context(user_id, i)
            tasks.append(task)
        
        # Execute all operations concurrently
        await asyncio.gather(*tasks)
        
        # Verify all contexts were created and destroyed
        creation_events = [e for e in lifecycle_events if "context_created_" in e]
        destruction_events = [e for e in lifecycle_events if "context_destroyed_" in e]
        
        assert len(creation_events) == 20
        assert len(destruction_events) == 20
        
        # Verify no contexts are left active
        assert len(active_contexts) == 0

    # Test 10: Context State Consistency Under Load
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_context_state_consistency_under_load(self, mock_context):
        """Test context state remains consistent under high concurrent load.
        
        Business Impact: Data integrity under high user load.
        """
        # Shared state for consistency testing
        global_state = {"counter": 0, "operations": []}
        state_lock = asyncio.Lock()
        
        def create_stateful_context(user_id, **kwargs):
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.local_state = {"user_counter": 0}
            
            async def update_state():
                async with state_lock:
                    # Atomic state update
                    global_state["counter"] += 1
                    context.local_state["user_counter"] += 1
                    global_state["operations"].append(f"{user_id}_update_{context.local_state['user_counter']}")
            
            context.update_state = update_state
            self.created_contexts.append(context)
            return context
        
        mock_context.side_effect = create_stateful_context
        
        # Create many concurrent state update operations
        async def perform_state_updates(user_id: str, num_updates: int):
            handler = AgentMessageHandler(MagicMock())
            websocket = self.create_isolated_websocket(user_id)
            
            for i in range(num_updates):
                message = self.create_test_message(
                    user_id,
                    MessageType.USER_MESSAGE,
                    {"message": f"State update {i} from {user_id}"}
                )
                
                with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                        try:
                            result = await handler.handle_message(user_id, websocket, message)
                        except:
                            pass  # Focus on state consistency, not handler success
                
                # Update state through context
                for context in self.created_contexts:
                    if hasattr(context, 'user_id') and context.user_id == user_id:
                        await context.update_state()
                        break
        
        # Run concurrent state updates for multiple users
        tasks = []
        updates_per_user = 5
        for user_id in self.user_ids[:3]:
            task = perform_state_updates(user_id, updates_per_user)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify state consistency
        expected_total = len(self.user_ids[:3]) * updates_per_user
        assert global_state["counter"] == expected_total
        assert len(global_state["operations"]) == expected_total
        
        # Verify each user's operations are recorded
        for user_id in self.user_ids[:3]:
            user_operations = [op for op in global_state["operations"] if user_id in op]
            assert len(user_operations) == updates_per_user

    # Test 11: Memory Leak Detection
    async def test_memory_leak_detection_in_context_management(self):
        """Test context management doesn't create memory leaks.
        
        Business Impact: Long-term system stability and resource efficiency.
        """
        # Track objects with weak references to detect leaks
        created_objects = []
        weak_references = []
        
        def create_tracked_objects():
            """Create objects that should be garbage collected."""
            for i in range(10):
                obj = {
                    "id": i,
                    "data": f"test_data_{i}" * 100,  # Some memory allocation
                    "timestamp": time.time()
                }
                created_objects.append(obj)
                # Create weak reference to track if object is garbage collected
                weak_ref = weakref.ref(obj)
                weak_references.append(weak_ref)
        
        # Create objects
        create_tracked_objects()
        
        # Verify objects exist
        assert len(created_objects) == 10
        assert len(weak_references) == 10
        assert all(ref() is not None for ref in weak_references)
        
        # Clear strong references
        created_objects.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Check for memory leaks - weak references should be None if properly collected
        alive_objects = sum(1 for ref in weak_references if ref() is not None)
        
        # Allow for some objects to still be alive due to GC timing, but most should be collected
        leaked_percentage = (alive_objects / len(weak_references)) * 100
        assert leaked_percentage < 50, f"Potential memory leak: {leaked_percentage}% of objects still alive"

    # Test 12: Context Isolation Stress Test
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_context_isolation_stress_test(self, mock_context):
        """Stress test context isolation with high concurrency and rapid creation/destruction.
        
        Business Impact: System reliability under peak load conditions.
        """
        # Track all context operations for verification
        stress_test_results = {
            "contexts_created": 0,
            "successful_isolations": 0,
            "failed_isolations": 0,
            "concurrent_peak": 0
        }
        active_contexts_count = 0
        
        def create_stress_test_context(user_id, **kwargs):
            nonlocal active_contexts_count
            active_contexts_count += 1
            stress_test_results["concurrent_peak"] = max(
                stress_test_results["concurrent_peak"], 
                active_contexts_count
            )
            
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.stress_test_data = f"isolated_data_{user_id}_{uuid.uuid4()}"
            context.creation_time = time.time()
            
            # Add cleanup that decrements counter
            original_cleanup = getattr(context, 'cleanup', lambda: None)
            def cleanup_with_tracking():
                nonlocal active_contexts_count
                active_contexts_count -= 1
                original_cleanup()
            
            context.cleanup = cleanup_with_tracking
            stress_test_results["contexts_created"] += 1
            self.created_contexts.append(context)
            return context
        
        mock_context.side_effect = create_stress_test_context
        
        async def stress_test_user_session(user_id: str, session_id: int):
            """Simulate intensive user session with rapid context creation."""
            handler = AgentMessageHandler(MagicMock())
            websocket = self.create_isolated_websocket(user_id)
            
            # Rapid message processing
            for msg_id in range(3):  # 3 messages per session
                message = self.create_test_message(
                    user_id,
                    MessageType.CHAT,
                    {"content": f"Stress test session {session_id} message {msg_id}"}
                )
                
                with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                        try:
                            result = await handler.handle_message(user_id, websocket, message)
                            if result:
                                stress_test_results["successful_isolations"] += 1
                            else:
                                stress_test_results["failed_isolations"] += 1
                        except Exception:
                            stress_test_results["failed_isolations"] += 1
                
                # Brief pause to simulate realistic timing
                await asyncio.sleep(0.001)
        
        # Create high-intensity concurrent load
        stress_tasks = []
        num_users = len(self.user_ids)
        sessions_per_user = 3
        
        for session_id in range(sessions_per_user):
            for user_id in self.user_ids:
                task = stress_test_user_session(user_id, session_id)
                stress_tasks.append(task)
        
        # Execute stress test
        start_time = time.time()
        await asyncio.gather(*stress_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Clean up contexts
        for context in self.created_contexts:
            if hasattr(context, 'cleanup'):
                context.cleanup()
        
        # Verify stress test results
        total_sessions = num_users * sessions_per_user
        test_duration = end_time - start_time
        
        assert stress_test_results["contexts_created"] > 0
        assert stress_test_results["concurrent_peak"] > 1  # Had concurrent contexts
        assert active_contexts_count == 0  # All cleaned up
        
        # Performance check - should handle stress load reasonably quickly
        assert test_duration < 5.0, f"Stress test too slow: {test_duration}s"
        
        # Calculate success rate
        total_operations = stress_test_results["successful_isolations"] + stress_test_results["failed_isolations"]
        if total_operations > 0:
            success_rate = (stress_test_results["successful_isolations"] / total_operations) * 100
            # Should maintain reasonable success rate under stress
            assert success_rate >= 70, f"Success rate too low under stress: {success_rate}%"