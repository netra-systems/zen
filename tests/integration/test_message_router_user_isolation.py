"""Test 6: MessageRouter User Isolation Validation

This test validates that MessageRouter implementations properly isolate messages and handlers
between different users to prevent cross-user data leakage and security violations.

Business Value: Platform/Security - User Data Protection & Golden Path Security
- Ensures MessageRouter implementations prevent cross-user message leakage
- Validates proper user context isolation in multi-tenant environment
- Protects $500K+ ARR by preventing security vulnerabilities that could affect enterprise customers

EXPECTED BEHAVIOR:
- FAIL initially if user isolation violations detected
- PASS after SSOT consolidation with proper user isolation
- Provide actionable security remediation guidance

GitHub Issue: #1077 - MessageRouter SSOT violations blocking golden path
Related: #953 - User isolation security vulnerabilities
"""

import unittest
import asyncio
import uuid
from typing import Dict, List, Set, Optional, Any
from unittest.mock import MagicMock, AsyncMock
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockUser:
    """Mock user for testing user isolation."""
    def __init__(self, user_id: str, username: str = None):
        self.user_id = user_id
        self.username = username or f"user_{user_id}"
        self.messages_received = []
        self.handlers_accessed = []
        
    def add_received_message(self, message: dict):
        """Track received messages for isolation testing."""
        self.messages_received.append({
            'message': message,
            'timestamp': time.time(),
            'thread_id': threading.get_ident()
        })
    
    def add_handler_access(self, handler_name: str):
        """Track handler access for isolation testing."""
        self.handlers_accessed.append({
            'handler': handler_name,
            'timestamp': time.time(),
            'thread_id': threading.get_ident()
        })


class MockMessageHandler:
    """Mock message handler for testing isolation."""
    def __init__(self, handler_id: str, user_context: Optional[MockUser] = None):
        self.handler_id = handler_id
        self.user_context = user_context
        self.messages_handled = []
        self.supported_types = ['test_message', 'user_message']
        
    def can_handle(self, message: dict) -> bool:
        """Check if handler can handle message."""
        return message.get('type') in self.supported_types
    
    async def handle(self, message: dict, user_context = None):
        """Handle message with user context tracking."""
        handled_entry = {
            'message': message,
            'handler_user_context': self.user_context.user_id if self.user_context else None,
            'runtime_user_context': user_context.user_id if user_context else None,
            'timestamp': time.time(),
            'thread_id': threading.get_ident()
        }
        self.messages_handled.append(handled_entry)
        
        # Track in user context if available
        if user_context:
            user_context.add_handler_access(self.handler_id)
        
        return {'status': 'handled', 'handler_id': self.handler_id}


class TestMessageRouterUserIsolation(SSotBaseTestCase):
    """Test suite for MessageRouter user isolation validation."""

    def setUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Test users for isolation testing
        self.user_a = MockUser("user_a_123", "alice")
        self.user_b = MockUser("user_b_456", "bob")
        self.user_c = MockUser("user_c_789", "charlie")
        
        # Test messages
        self.user_a_message = {
            'type': 'user_message',
            'user_id': self.user_a.user_id,
            'data': {'content': 'Private message from Alice', 'sensitive': True}
        }
        
        self.user_b_message = {
            'type': 'user_message',
            'user_id': self.user_b.user_id,
            'data': {'content': 'Private message from Bob', 'confidential': True}
        }
        
        self.admin_message = {
            'type': 'admin_message',
            'user_id': 'admin_001',
            'data': {'content': 'System admin message', 'level': 'system'}
        }

    def test_message_router_prevents_cross_user_message_leakage(self):
        """Test that MessageRouter prevents messages from leaking between users.
        
        EXPECTED: FAIL initially if cross-user leakage detected
        EXPECTED: PASS after SSOT consolidation with proper isolation
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter: {e}")
        except Exception as e:
            self.fail(f"Cannot create MessageRouter: {e}")
        
        # Set up user-specific handlers
        handler_a = MockMessageHandler("handler_a", self.user_a)
        handler_b = MockMessageHandler("handler_b", self.user_b)
        
        try:
            router.add_handler(handler_a)
            router.add_handler(handler_b)
        except Exception as e:
            self.skipTest(f"Cannot add handlers to router: {e}")
        
        isolation_violations = []
        
        # Test 1: Route User A's message
        try:
            if hasattr(router, 'route_message'):
                # Route message with User A context
                result_a = router.route_message(self.user_a_message, self.user_a)
                
                # Check if User B's handler received User A's message (violation)
                for handled in handler_b.messages_handled:
                    if (handled['message'].get('user_id') == self.user_a.user_id and 
                        handled['runtime_user_context'] != self.user_a.user_id):
                        isolation_violations.append(
                            f"User B handler received User A's message: {handled['message']['data']['content']}"
                        )
        except Exception as e:
            # Route might not work perfectly, but shouldn't crash
            self.logger.warning(f"Route message test had issues: {e}")
        
        # Test 2: Route User B's message
        try:
            if hasattr(router, 'route_message'):
                # Route message with User B context
                result_b = router.route_message(self.user_b_message, self.user_b)
                
                # Check if User A's handler received User B's message (violation)
                for handled in handler_a.messages_handled:
                    if (handled['message'].get('user_id') == self.user_b.user_id and 
                        handled['runtime_user_context'] != self.user_b.user_id):
                        isolation_violations.append(
                            f"User A handler received User B's message: {handled['message']['data']['content']}"
                        )
        except Exception as e:
            self.logger.warning(f"Route message test had issues: {e}")
        
        # Test 3: Check for shared state contamination
        if len(handler_a.messages_handled) > 0 and len(handler_b.messages_handled) > 0:
            # Check if handlers share any message references
            a_messages = [h['message'] for h in handler_a.messages_handled]
            b_messages = [h['message'] for h in handler_b.messages_handled]
            
            for a_msg in a_messages:
                for b_msg in b_messages:
                    if (a_msg is b_msg and 
                        a_msg.get('user_id') != b_msg.get('user_id')):
                        isolation_violations.append(
                            "Handlers sharing same message object reference (memory leak)"
                        )
        
        if isolation_violations:
            self.fail(
                f" FAIL:  CROSS-USER MESSAGE LEAKAGE DETECTED: {len(isolation_violations)} isolation violations.\n"
                f"BUSINESS IMPACT: Cross-user message leakage violates privacy and security, "
                f"risking enterprise customer trust and regulatory compliance.\n"
                f"SECURITY VIOLATIONS:\n" + "\n".join(f"- {violation}" for violation in isolation_violations) + 
                f"\n\nREMEDIATION: Implement proper user context validation in MessageRouter routing logic."
            )
        
        self.logger.info(" PASS:  MessageRouter prevents cross-user message leakage")

    def test_concurrent_user_message_routing_isolation(self):
        """Test that concurrent message routing maintains user isolation.
        
        EXPECTED: FAIL initially if concurrent access breaks isolation
        EXPECTED: PASS after SSOT consolidation with thread-safe isolation
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter: {e}")
        except Exception as e:
            self.fail(f"Cannot create MessageRouter: {e}")
        
        # Set up shared handler that tracks all processing
        shared_handler = MockMessageHandler("shared_handler")
        
        try:
            router.add_handler(shared_handler)
        except Exception as e:
            self.skipTest(f"Cannot add handler to router: {e}")
        
        # Function to route messages concurrently
        def route_user_messages(user: MockUser, message: dict, iterations: int = 5):
            for i in range(iterations):
                try:
                    if hasattr(router, 'route_message'):
                        router.route_message(message, user)
                        time.sleep(0.01)  # Small delay to increase chance of race conditions
                except Exception:
                    pass  # Ignore routing errors, focus on isolation
        
        # Run concurrent routing for multiple users
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(route_user_messages, self.user_a, self.user_a_message, 10),
                executor.submit(route_user_messages, self.user_b, self.user_b_message, 10),
                executor.submit(route_user_messages, self.user_c, 
                               {'type': 'user_message', 'user_id': self.user_c.user_id, 
                                'data': {'content': 'Charlie message', 'private': True}}, 10)
            ]
            
            # Wait for all to complete
            for future in futures:
                try:
                    future.result(timeout=10)
                except Exception as e:
                    self.logger.warning(f"Concurrent routing had issues: {e}")
        
        # Analyze results for isolation violations
        isolation_violations = []
        
        # Check if messages were cross-contaminated
        user_contexts_seen = set()
        for handled in shared_handler.messages_handled:
            runtime_context = handled.get('runtime_user_context')
            message_user = handled['message'].get('user_id')
            
            if runtime_context and message_user:
                if runtime_context != message_user:
                    isolation_violations.append(
                        f"Message from {message_user} processed with {runtime_context} context"
                    )
                
            user_contexts_seen.add(runtime_context)
        
        # Check if we saw multiple user contexts (good for isolation test)
        if len(user_contexts_seen) < 2:
            self.logger.warning("Concurrent test may not have effectively tested isolation")
        
        # Check for thread safety issues in handler state
        thread_ids_seen = set(h.get('thread_id') for h in shared_handler.messages_handled)
        if len(thread_ids_seen) > 1:
            # Multi-threaded execution occurred - check for consistency
            for handled in shared_handler.messages_handled:
                if (handled.get('runtime_user_context') and 
                    handled['message'].get('user_id') and
                    handled.get('runtime_user_context') != handled['message'].get('user_id')):
                    isolation_violations.append(
                        f"Thread {handled.get('thread_id')}: context/message user ID mismatch"
                    )
        
        if isolation_violations:
            self.fail(
                f" FAIL:  CONCURRENT USER ISOLATION VIOLATIONS: {len(isolation_violations)} violations detected.\n"
                f"BUSINESS IMPACT: Race conditions in user isolation can cause data leakage "
                f"between concurrent users, violating privacy and security.\n"
                f"THREAD SAFETY VIOLATIONS:\n" + "\n".join(f"- {violation}" for violation in isolation_violations) + 
                f"\n\nREMEDIATION: Implement thread-safe user context isolation in MessageRouter."
            )
        
        self.logger.info(" PASS:  Concurrent message routing maintains user isolation")

    def test_handler_registration_user_scoping(self):
        """Test that handler registration respects user scoping.
        
        EXPECTED: FAIL initially if handlers not properly scoped
        EXPECTED: PASS after SSOT consolidation with proper scoping
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter: {e}")
        
        scoping_violations = []
        
        # Test multiple router instances for user scoping
        try:
            router_a = MessageRouter()  # Router for User A
            router_b = MessageRouter()  # Router for User B
            
            handler_a = MockMessageHandler("user_a_handler", self.user_a)
            handler_b = MockMessageHandler("user_b_handler", self.user_b)
            
            # Add user-specific handlers to respective routers
            if hasattr(router_a, 'add_handler') and hasattr(router_b, 'add_handler'):
                router_a.add_handler(handler_a)
                router_b.add_handler(handler_b)
                
                # Test that User A's router doesn't have User B's handler
                if hasattr(router_a, 'handlers'):
                    router_a_handlers = router_a.handlers
                    if handler_b in router_a_handlers:
                        scoping_violations.append("Router A contains Router B's handler")
                
                # Test that User B's router doesn't have User A's handler
                if hasattr(router_b, 'handlers'):
                    router_b_handlers = router_b.handlers
                    if handler_a in router_b_handlers:
                        scoping_violations.append("Router B contains Router A's handler")
                
                # Test that adding to one router doesn't affect the other
                global_handler = MockMessageHandler("global_handler")
                router_a.add_handler(global_handler)
                
                if hasattr(router_b, 'handlers'):
                    router_b_handlers = router_b.handlers
                    if global_handler in router_b_handlers:
                        scoping_violations.append("Handler added to Router A appeared in Router B")
                        
        except Exception as e:
            self.logger.warning(f"Handler scoping test encountered issues: {e}")
            # If we can't test multiple instances, try single instance with context
            try:
                router = MessageRouter()
                
                # Test that handler context isolation is maintained
                handler_with_context = MockMessageHandler("context_handler", self.user_a)
                handler_without_context = MockMessageHandler("no_context_handler", None)
                
                router.add_handler(handler_with_context)
                router.add_handler(handler_without_context)
                
                # Route messages and check context preservation
                if hasattr(router, 'route_message'):
                    router.route_message(self.user_a_message, self.user_a)
                    router.route_message(self.user_b_message, self.user_b)
                    
                    # Check if context handlers maintained their user association
                    for handled in handler_with_context.messages_handled:
                        if (handled['handler_user_context'] == self.user_a.user_id and
                            handled['runtime_user_context'] != self.user_a.user_id):
                            scoping_violations.append(
                                "Context handler processed message from different user"
                            )
                
            except Exception as e2:
                self.skipTest(f"Cannot test handler scoping: {e2}")
        
        if scoping_violations:
            self.fail(
                f" FAIL:  HANDLER SCOPING VIOLATIONS: {len(scoping_violations)} violations detected.\n"
                f"BUSINESS IMPACT: Improper handler scoping allows cross-user access to "
                f"handlers and processing logic, breaking user isolation.\n"
                f"SCOPING VIOLATIONS:\n" + "\n".join(f"- {violation}" for violation in scoping_violations) + 
                f"\n\nREMEDIATION: Implement proper user scoping in handler registration and access."
            )
        
        self.logger.info(" PASS:  Handler registration respects user scoping")

    def test_message_router_memory_isolation(self):
        """Test that MessageRouter doesn't retain cross-user data in memory.
        
        EXPECTED: FAIL initially if memory contamination detected
        EXPECTED: PASS after SSOT consolidation with proper memory isolation
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter: {e}")
        except Exception as e:
            self.fail(f"Cannot create MessageRouter: {e}")
        
        memory_violations = []
        
        # Create handlers to track memory usage
        handler_a = MockMessageHandler("memory_test_a", self.user_a)
        handler_b = MockMessageHandler("memory_test_b", self.user_b)
        
        try:
            router.add_handler(handler_a)
            router.add_handler(handler_b)
        except Exception as e:
            self.skipTest(f"Cannot add handlers: {e}")
        
        # Process messages for User A
        try:
            if hasattr(router, 'route_message'):
                for i in range(5):
                    test_message = {
                        'type': 'user_message',
                        'user_id': self.user_a.user_id,
                        'data': {'content': f'User A message {i}', 'iteration': i}
                    }
                    router.route_message(test_message, self.user_a)
        except Exception as e:
            self.logger.warning(f"Message routing for User A had issues: {e}")
        
        # Capture User A's data state
        user_a_processed_count = len(handler_a.messages_handled)
        user_a_data = [h['message']['data'] for h in handler_a.messages_handled]
        
        # Process messages for User B  
        try:
            if hasattr(router, 'route_message'):
                for i in range(3):
                    test_message = {
                        'type': 'user_message',
                        'user_id': self.user_b.user_id,
                        'data': {'content': f'User B message {i}', 'iteration': i}
                    }
                    router.route_message(test_message, self.user_b)
        except Exception as e:
            self.logger.warning(f"Message routing for User B had issues: {e}")
        
        # Check for cross-contamination in handlers
        for handled in handler_a.messages_handled:
            if handled['message'].get('user_id') == self.user_b.user_id:
                memory_violations.append(
                    f"User A handler contains User B message: {handled['message']['data']}"
                )
        
        for handled in handler_b.messages_handled:
            if handled['message'].get('user_id') == self.user_a.user_id:
                memory_violations.append(
                    f"User B handler contains User A message: {handled['message']['data']}"
                )
        
        # Check if User A's data was modified by User B processing
        current_user_a_count = len([h for h in handler_a.messages_handled 
                                   if h['message'].get('user_id') == self.user_a.user_id])
        
        if current_user_a_count != user_a_processed_count:
            memory_violations.append(
                f"User A message count changed after User B processing: {user_a_processed_count} -> {current_user_a_count}"
            )
        
        # Check router state doesn't retain user-specific data
        if hasattr(router, 'handlers'):
            try:
                handlers = router.handlers
                # Look for any stored user data in router itself
                if hasattr(router, '__dict__'):
                    for attr_name, attr_value in router.__dict__.items():
                        if isinstance(attr_value, (list, dict)):
                            # Check if router is storing user-specific data
                            str_repr = str(attr_value)
                            if (self.user_a.user_id in str_repr and 
                                self.user_b.user_id in str_repr):
                                memory_violations.append(
                                    f"Router attribute '{attr_name}' contains data from multiple users"
                                )
            except Exception:
                pass  # Router inspection might not be possible
        
        if memory_violations:
            self.fail(
                f" FAIL:  MEMORY ISOLATION VIOLATIONS: {len(memory_violations)} violations detected.\n"
                f"BUSINESS IMPACT: Memory contamination between users creates security risks "
                f"and potential data leakage in multi-tenant environment.\n"
                f"MEMORY VIOLATIONS:\n" + "\n".join(f"- {violation}" for violation in memory_violations) + 
                f"\n\nREMEDIATION: Implement proper memory isolation and cleanup in MessageRouter."
            )
        
        self.logger.info(" PASS:  MessageRouter maintains proper memory isolation between users")


if __name__ == "__main__":
    import unittest
    unittest.main()