"""
WebSocket User Isolation UUID Failure Unit Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose user isolation failures caused by uuid.uuid4() usage patterns.

Business Value Justification:
- Segment: Platform/Internal (Multi-user system integrity)
- Business Goal: User data isolation and security
- Value Impact: Prevents user data leakage and cross-contamination
- Strategic Impact: CRITICAL - User isolation failures = security vulnerabilities

Test Strategy:
1. FAIL INITIALLY - Tests expose isolation issues with uuid.uuid4() patterns
2. MIGRATE PHASE - Replace with UnifiedIdGenerator user-aware methods  
3. PASS FINALLY - Tests validate proper user isolation with consistent IDs

These tests validate that WebSocket user isolation works correctly with
UnifiedIdGenerator instead of random uuid.uuid4() patterns that can't
provide user context or proper isolation.
"""

import pytest
import uuid
import asyncio
import time
from typing import Dict, List, Set, Any, Optional
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

# Import WebSocket core modules for user isolation testing
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory  
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from netra_backend.app.websocket_core.context import WebSocketRequestContext
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager

# Import the SSOT UnifiedIdGenerator for proper user isolation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ConnectionID, ThreadID
from shared.session_management.user_session_manager import UnifiedUserSessionManager


class TestWebSocketUserIsolationUuidFailures:
    """
    Unit tests that EXPOSE user isolation failures caused by uuid.uuid4() usage.
    
    CRITICAL: These tests are DESIGNED TO FAIL initially to demonstrate
    how uuid.uuid4() patterns break user isolation in multi-user scenarios.
    """

    def test_connection_id_lacks_user_context_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose how uuid.uuid4() connection IDs lack user context.
        
        This test demonstrates that uuid.uuid4()-based connection IDs cannot
        provide user isolation or be traced back to specific users.
        """
        users = ["user_alice", "user_bob", "user_charlie"]
        connections_by_user = {}
        
        # Create connections for different users
        for user_id in users:
            user_connections = []
            for i in range(3):
                conn = ConnectionInfo(user_id=user_id)
                user_connections.append(conn)
            connections_by_user[user_id] = user_connections
            
        # FAILING ASSERTION: Connection IDs should contain user context
        for user_id, connections in connections_by_user.items():
            for conn in connections:
                # This will FAIL because uuid.uuid4() provides no user context
                assert user_id in conn.connection_id, \
                    f"Connection ID lacks user context: {conn.connection_id} for user {user_id}"
                    
                # This will FAIL because we expect user-aware ID format
                expected_pattern = f"ws_conn_{user_id}_"
                assert conn.connection_id.startswith(expected_pattern), \
                    f"Expected user-aware pattern '{expected_pattern}', got: {conn.connection_id}"
        
        # FAILING ASSERTION: Should be able to identify user from connection ID alone
        all_connections = []
        for connections in connections_by_user.values():
            all_connections.extend(connections)
            
        for conn in all_connections:
            # This will FAIL because uuid.uuid4() IDs can't be traced to users
            extracted_user = self._extract_user_from_connection_id(conn.connection_id)
            assert extracted_user == conn.user_id, \
                f"Cannot extract user from connection ID: {conn.connection_id}"

    def test_concurrent_user_connection_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose user isolation issues in concurrent scenarios.
        
        This test demonstrates that uuid.uuid4() patterns can cause user
        isolation failures when multiple users connect simultaneously.
        """
        factory = WebSocketManagerFactory()
        users = [f"concurrent_user_{i}" for i in range(10)]
        
        # Simulate concurrent user connections
        managers_by_user = {}
        
        def create_user_manager(user_id: str) -> UnifiedWebSocketManager:
            """Create WebSocket manager for user (simulates concurrent connection)."""
            mock_websocket = MagicMock()
            manager = factory.create_manager_for_user(user_id, mock_websocket)
            return manager
            
        # Create managers concurrently to stress-test isolation
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for user_id in users:
                future = executor.submit(create_user_manager, user_id)
                futures[future] = user_id
                
            for future in futures:
                user_id = futures[future]
                manager = future.result()
                managers_by_user[user_id] = manager
                
        # FAILING ASSERTION: Each manager should have user-traceable identifiers
        for user_id, manager in managers_by_user.items():
            manager_id = getattr(manager, '_manager_id', None) or \
                        getattr(manager, 'unique_suffix', None) or \
                        getattr(manager, '_internal_id', None)
                        
            if manager_id:
                # This will FAIL because uuid.uuid4() provides no user context
                assert user_id in manager_id, \
                    f"Manager ID lacks user context: {manager_id} for user {user_id}"
                    
                # This will FAIL because we expect user-aware manager IDs
                expected_pattern = f"mgr_{user_id[:8]}_"
                assert manager_id.startswith(expected_pattern), \
                    f"Expected user-aware manager pattern '{expected_pattern}', got: {manager_id}"
                    
        # FAILING ASSERTION: Should be able to isolate resources by user
        user_resource_map = {}
        for user_id, manager in managers_by_user.items():
            # Try to extract user-specific resources (this will fail with uuid.uuid4())
            resources = self._extract_user_resources_from_manager(manager)
            user_resource_map[user_id] = resources
            
            # This will FAIL because uuid.uuid4() prevents proper resource isolation
            assert len(resources) > 0, \
                f"Cannot identify user-specific resources for {user_id}"
                
            # This will FAIL because resources should contain user context
            for resource_id in resources:
                assert user_id[:8] in resource_id, \
                    f"Resource ID lacks user context: {resource_id} for user {user_id}"

    def test_websocket_context_user_leakage_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose user context leakage with uuid.uuid4() patterns.
        
        This test demonstrates that uuid.uuid4()-based context IDs can cause
        user data to leak between different user sessions.
        """
        users = ["sensitive_user_1", "sensitive_user_2", "sensitive_user_3"]
        contexts_by_user = {}
        
        # Create WebSocket contexts for different users with sensitive data
        for user_id in users:
            user_contexts = []
            for i in range(2):
                context = WebSocketRequestContext.create_for_user(
                    user_id=user_id,
                    thread_id=f"{user_id}_thread_{i}",
                    connection_info=None
                )
                # Add sensitive user data to context
                context.sensitive_data = {
                    "api_keys": [f"{user_id}_key_{j}" for j in range(3)],
                    "private_threads": [f"{user_id}_private_{j}" for j in range(2)]
                }
                user_contexts.append(context)
            contexts_by_user[user_id] = user_contexts
            
        # FAILING ASSERTION: Context IDs should prevent cross-user access
        all_contexts = []
        for contexts in contexts_by_user.values():
            all_contexts.extend(contexts)
            
        for context in all_contexts:
            # This will FAIL because uuid.uuid4() context IDs lack user binding
            assert context.user_id in context.run_id, \
                f"Context run_id lacks user binding: {context.run_id} for user {context.user_id}"
                
            # This will FAIL because we expect user-scoped context IDs
            expected_pattern = f"ctx_{context.user_id[:8]}_"
            assert context.run_id.startswith(expected_pattern), \
                f"Expected user-scoped pattern '{expected_pattern}', got: {context.run_id}"
                
        # FAILING ASSERTION: Should not be able to access other users' contexts
        for user_id, user_contexts in contexts_by_user.items():
            for context in user_contexts:
                # Simulate context lookup by ID (this should fail with uuid.uuid4())
                retrieved_context = self._lookup_context_by_id(context.run_id, all_contexts)
                
                if retrieved_context:
                    # This will FAIL because uuid.uuid4() IDs allow cross-user access
                    assert retrieved_context.user_id == user_id, \
                        f"Context ID {context.run_id} allows cross-user access: " \
                        f"expected {user_id}, got {retrieved_context.user_id}"

    def test_message_routing_user_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose message routing isolation issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() message IDs break message
        routing isolation between users in multi-user scenarios.
        """
        users = ["routing_user_a", "routing_user_b", "routing_user_c"]
        messages_by_user = {}
        
        # Create messages for different users
        for user_id in users:
            user_messages = []
            for msg_type in ["agent_started", "agent_thinking", "agent_completed"]:
                from netra_backend.app.websocket_core.types import generate_default_message
                
                message = generate_default_message(
                    message_type=msg_type,
                    user_id=user_id,
                    thread_id=f"{user_id}_thread",
                    data={"content": f"Private message for {user_id}"}
                )
                user_messages.append(message)
            messages_by_user[user_id] = user_messages
            
        # FAILING ASSERTION: Message IDs should contain user routing information
        for user_id, messages in messages_by_user.items():
            for msg in messages:
                # This will FAIL because uuid.uuid4() message IDs lack user context
                assert user_id[:8] in msg.message_id, \
                    f"Message ID lacks user context: {msg.message_id} for user {user_id}"
                    
                # This will FAIL because we expect user-aware message ID format
                expected_pattern = f"msg_{msg.type}_{user_id[:8]}_"
                assert msg.message_id.startswith(expected_pattern), \
                    f"Expected user-aware message pattern '{expected_pattern}', got: {msg.message_id}"
                    
        # FAILING ASSERTION: Message routing should be user-isolated
        all_messages = []
        for messages in messages_by_user.values():
            all_messages.extend(messages)
            
        for msg in all_messages:
            # Simulate message routing lookup (this should isolate by user)
            target_user = self._extract_user_from_message_id(msg.message_id)
            
            # This will FAIL because uuid.uuid4() prevents user extraction from message ID
            assert target_user == msg.user_id, \
                f"Cannot route message {msg.message_id} to correct user: " \
                f"expected {msg.user_id}, extracted {target_user}"

    def test_session_management_user_boundaries_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose user boundary violations in session management.
        
        This test demonstrates that uuid.uuid4() patterns break user session
        boundaries and allow unauthorized access to other users' data.
        """
        # Test with UnifiedUserSessionManager if available
        try:
            session_manager = UnifiedUserSessionManager()
        except:
            session_manager = UserSessionManager()
            
        users = ["session_user_1", "session_user_2", "session_user_3"]
        sessions_by_user = {}
        
        # Create sessions for different users
        for user_id in users:
            user_sessions = []
            for i in range(2):
                session_data = {
                    "user_id": user_id,
                    "thread_id": f"{user_id}_session_thread_{i}",
                    "private_data": f"confidential_data_for_{user_id}_{i}"
                }
                
                # Create session (this may use uuid.uuid4() internally)
                session = session_manager.create_session(user_id, session_data)
                user_sessions.append(session)
            sessions_by_user[user_id] = user_sessions
            
        # FAILING ASSERTION: Session IDs should enforce user boundaries
        for user_id, sessions in sessions_by_user.items():
            for session in sessions:
                session_id = getattr(session, 'session_id', None) or \
                           getattr(session, 'id', None) or \
                           getattr(session, '_id', None)
                           
                if session_id:
                    # This will FAIL because uuid.uuid4() session IDs lack user context
                    assert user_id[:8] in session_id, \
                        f"Session ID lacks user context: {session_id} for user {user_id}"
                        
                    # This will FAIL because we expect user-scoped session IDs
                    expected_pattern = f"session_{user_id[:8]}_"
                    assert session_id.startswith(expected_pattern), \
                        f"Expected user-scoped session pattern '{expected_pattern}', got: {session_id}"
                        
        # FAILING ASSERTION: Cross-user session access should be prevented
        all_sessions = []
        for sessions in sessions_by_user.values():
            all_sessions.extend(sessions)
            
        for user_id, user_sessions in sessions_by_user.items():
            for session in user_sessions:
                session_id = getattr(session, 'session_id', session.id if hasattr(session, 'id') else None)
                
                if session_id:
                    # Try to access session as different user (should fail)
                    other_users = [u for u in users if u != user_id]
                    for other_user in other_users:
                        # This will FAIL because uuid.uuid4() allows cross-user access
                        accessible = self._can_user_access_session(other_user, session_id, session_manager)
                        assert not accessible, \
                            f"User {other_user} can access {user_id}'s session {session_id}"

    def test_audit_trail_user_traceability_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose audit trail issues with uuid.uuid4() patterns.
        
        This test demonstrates that uuid.uuid4() IDs break audit trail
        user traceability required for compliance and debugging.
        """
        users = ["audit_user_alpha", "audit_user_beta", "audit_user_gamma"]
        audit_events = []
        
        # Generate audit events for different users
        for user_id in users:
            for action in ["websocket_connect", "message_send", "agent_execute"]:
                # Create audit event (simulating current uuid.uuid4() usage)
                event = {
                    "event_id": str(uuid.uuid4()),  # Current problematic pattern
                    "user_id": user_id,
                    "action": action,
                    "timestamp": time.time(),
                    "connection_id": f"conn_{uuid.uuid4().hex[:8]}",  # Also problematic
                    "session_context": {
                        "thread_id": str(uuid.uuid4()),  # Also problematic
                        "request_id": str(uuid.uuid4())  # Also problematic
                    }
                }
                audit_events.append(event)
                
        # FAILING ASSERTION: Audit event IDs should be user-traceable
        for event in audit_events:
            user_id = event["user_id"]
            
            # This will FAIL because uuid.uuid4() event IDs lack user context
            assert user_id[:8] in event["event_id"], \
                f"Audit event ID lacks user traceability: {event['event_id']} for user {user_id}"
                
            # This will FAIL because we expect user-aware audit event format
            expected_pattern = f"audit_{user_id[:8]}_"
            assert event["event_id"].startswith(expected_pattern), \
                f"Expected audit pattern '{expected_pattern}', got: {event['event_id']}"
                
            # This will FAIL because connection_id should also be user-traceable
            assert user_id[:8] in event["connection_id"], \
                f"Audit connection ID lacks user context: {event['connection_id']} for user {user_id}"
                
        # FAILING ASSERTION: Should be able to filter audit events by user efficiently
        for user_id in users:
            user_events = self._filter_audit_events_by_user(user_id, audit_events)
            
            # This will FAIL because uuid.uuid4() makes efficient user filtering impossible
            assert len(user_events) > 0, \
                f"Cannot efficiently filter audit events for user {user_id}"
                
            # Verify all returned events belong to the correct user
            for event in user_events:
                assert event["user_id"] == user_id, \
                    f"Audit filter returned wrong user event: {event['event_id']}"

    # Helper methods that simulate real-world operations
    
    def _extract_user_from_connection_id(self, connection_id: str) -> Optional[str]:
        """Extract user ID from connection ID (will fail with uuid.uuid4())."""
        try:
            # This is what SHOULD work with UnifiedIdGenerator format
            if connection_id.startswith("ws_conn_"):
                parts = connection_id.split("_")
                if len(parts) >= 3:
                    return parts[2]  # user part
            return None
        except:
            return None
            
    def _extract_user_resources_from_manager(self, manager) -> List[str]:
        """Extract user-specific resource IDs from manager (will fail with uuid.uuid4())."""
        resources = []
        try:
            # Look for any attributes that might contain resource IDs
            for attr_name in dir(manager):
                if not attr_name.startswith('_'):
                    attr_value = getattr(manager, attr_name, None)
                    if isinstance(attr_value, str) and len(attr_value) > 8:
                        resources.append(attr_value)
        except:
            pass
        return resources
        
    def _lookup_context_by_id(self, context_id: str, all_contexts: List) -> Optional[Any]:
        """Lookup context by ID (simulates context registry lookup)."""
        for context in all_contexts:
            if hasattr(context, 'run_id') and context.run_id == context_id:
                return context
        return None
        
    def _extract_user_from_message_id(self, message_id: str) -> Optional[str]:
        """Extract user ID from message ID (will fail with uuid.uuid4())."""
        try:
            # This is what SHOULD work with UnifiedIdGenerator format
            if "_" in message_id:
                parts = message_id.split("_")
                if len(parts) >= 3:
                    return parts[2]  # user part
            return None
        except:
            return None
            
    def _can_user_access_session(self, user_id: str, session_id: str, session_manager) -> bool:
        """Check if user can access session (simulates authorization check)."""
        try:
            # This simulates what happens in real session access
            session = session_manager.get_session_by_id(session_id)
            return session is not None
        except:
            # If session manager doesn't have this method, assume access is possible
            # (which demonstrates the security issue with uuid.uuid4())
            return True
            
    def _filter_audit_events_by_user(self, user_id: str, events: List[Dict]) -> List[Dict]:
        """Filter audit events by user (inefficient with uuid.uuid4() patterns)."""
        # With uuid.uuid4(), this requires full scan of all events
        user_events = []
        for event in events:
            if event.get("user_id") == user_id:
                user_events.append(event)
        return user_events

    @pytest.mark.security
    def test_user_isolation_security_requirements(self):
        """
        Test that validates critical user isolation security requirements.
        
        This test ensures that any ID generation solution meets security
        requirements for multi-user isolation in WebSocket communications.
        """
        # Define security test scenarios
        security_scenarios = [
            {
                "name": "Cross-user message interception",
                "users": ["victim_user", "attacker_user"],
                "test_type": "message_isolation"
            },
            {
                "name": "Session hijacking via ID prediction",
                "users": ["target_user", "malicious_user"],
                "test_type": "session_security" 
            },
            {
                "name": "Resource access escalation",
                "users": ["limited_user", "admin_user"],
                "test_type": "resource_isolation"
            }
        ]
        
        security_failures = []
        
        for scenario in security_scenarios:
            try:
                if scenario["test_type"] == "message_isolation":
                    failure = self._test_message_isolation_security(scenario["users"])
                elif scenario["test_type"] == "session_security":
                    failure = self._test_session_security(scenario["users"])
                elif scenario["test_type"] == "resource_isolation":
                    failure = self._test_resource_isolation_security(scenario["users"])
                else:
                    failure = f"Unknown test type: {scenario['test_type']}"
                    
                if failure:
                    security_failures.append(f"{scenario['name']}: {failure}")
                    
            except Exception as e:
                security_failures.append(f"{scenario['name']}: {str(e)}")
                
        # Report all security failures
        if security_failures:
            failure_report = "\n".join([f"  - {f}" for f in security_failures])
            pytest.fail(f"Security isolation failures detected:\n{failure_report}")
            
    def _test_message_isolation_security(self, users: List[str]) -> Optional[str]:
        """Test message isolation security between users."""
        if len(users) != 2:
            return "Invalid user count for message isolation test"
            
        user1, user2 = users
        
        # Create messages for user1
        from netra_backend.app.websocket_core.types import generate_default_message
        user1_message = generate_default_message(
            message_type="agent_completed",
            user_id=user1,
            thread_id=f"{user1}_private_thread",
            data={"sensitive": f"confidential_data_for_{user1}"}
        )
        
        # Check if user2 can access user1's message by ID prediction/guessing
        if not user1[:8] in user1_message.message_id:
            return f"Message ID lacks user isolation: {user1_message.message_id}"
            
        return None  # No security failure
        
    def _test_session_security(self, users: List[str]) -> Optional[str]:
        """Test session security between users.""" 
        if len(users) != 2:
            return "Invalid user count for session security test"
            
        target_user, malicious_user = users
        
        # Create context for target user
        context = WebSocketRequestContext.create_for_user(
            user_id=target_user,
            thread_id=f"{target_user}_secure_thread",
            connection_info=None
        )
        
        # Check if malicious user can predict/access target user's context
        if not target_user[:8] in context.run_id:
            return f"Context ID allows session prediction: {context.run_id}"
            
        return None  # No security failure
        
    def _test_resource_isolation_security(self, users: List[str]) -> Optional[str]:
        """Test resource isolation security between users."""
        if len(users) != 2:
            return "Invalid user count for resource isolation test"
            
        limited_user, admin_user = users
        
        # Create connections for both users
        limited_conn = ConnectionInfo(user_id=limited_user)
        admin_conn = ConnectionInfo(user_id=admin_user)
        
        # Check if connection IDs provide proper isolation
        if not limited_user[:8] in limited_conn.connection_id:
            return f"Limited user connection lacks isolation: {limited_conn.connection_id}"
            
        if not admin_user[:8] in admin_conn.connection_id:
            return f"Admin user connection lacks isolation: {admin_conn.connection_id}"
            
        return None  # No security failure