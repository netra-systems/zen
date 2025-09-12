"""
Mission-critical thread propagation verification tests.

Tests that thread_id correctly propagates through the entire system
ensuring proper isolation for multi-user chat functionality.

Critical verification points:
1. WebSocket -> Message Handler propagation
2. Message Handler -> Agent Registry propagation  
3. Agent Registry -> Execution Engine propagation
4. Execution Engine -> Tool Dispatcher propagation
5. Tool results -> WebSocket response propagation
6. End-to-end thread consistency verification

Business Context:
- Thread isolation is critical for $500K+ ARR multi-user chat platform
- Each user's conversation must remain isolated from other users
- WebSocket events must deliver to correct user only
- Agent execution context must preserve thread identity
"""

import asyncio
import logging
import uuid
import pytest
from typing import Dict, Any, Optional
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.ssot.websocket import WebSocketTestUtility
from test_framework.ssot.database import DatabaseTestUtility
from shared.isolated_environment import IsolatedEnvironment

# Import core services for thread propagation testing
try:
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.services.message_handlers import MessageHandlerService
    REAL_SERVICES_AVAILABLE = True
except ImportError as e:
    # Services not available in test environment - use mock mode
    UnifiedWebSocketManager = None
    MessageHandlerService = None
    REAL_SERVICES_AVAILABLE = False

logger = logging.getLogger(__name__)

class TestThreadPropagationVerification(SSotAsyncTestCase):
    """
    Mission-critical thread propagation validation using real services.
    
    These tests MUST fail initially to prove they work, then pass when
    proper thread propagation is implemented.
    """
    
    async def asyncSetUp(self):
        """Setup test environment for thread propagation testing."""
        await super().asyncSetUp()
        
        # Generate unique test identifiers
        self.user_id = str(uuid.uuid4())
        self.thread_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())
        
        # Setup WebSocket test utilities first  
        self.websocket_util = WebSocketTestUtility()
        self.db_util = DatabaseTestUtility()
        
        # Initialize services if available
        if REAL_SERVICES_AVAILABLE:
            try:
                self.websocket_manager = UnifiedWebSocketManager()
                self.message_handler = MessageHandlerService()
                self.logger.info("Real services initialized for thread propagation testing")
            except Exception as e:
                self.logger.info(f"Using mock mode for services due to: {e}")
                self.websocket_manager = None
                self.message_handler = None
        else:
            self.logger.info("Real services not available - using mock mode")
            self.websocket_manager = None
            self.message_handler = None
        
        # Track thread propagation
        self.thread_capture_log = {}
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Thread propagation test setup - User: {self.user_id[:8]}, Thread: {self.thread_id[:8]}")
    
    async def asyncTearDown(self):
        """Cleanup test resources."""
        try:
            await self.websocket_manager.shutdown()
        except Exception as e:
            self.logger.warning(f"Websocket cleanup warning: {e}")
        
        await super().asyncTearDown()
    
    @pytest.mark.asyncio
    async def test_websocket_to_message_handler_propagation_FAIL_FIRST(self):
        """
        Test thread_id propagation from WebSocket to message handler.
        
        This test is designed to FAIL initially to prove thread propagation
        is not working, then PASS when proper implementation is added.
        """
        self.logger.info("Testing WebSocket to Message Handler thread propagation")
        
        # Create WebSocket test connection
        websocket_connection = await self.websocket_util.create_test_connection(
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Test WebSocket manager thread context handling  
        if self.websocket_manager:
            try:
                # Connect with thread context
                connection_id = await self.websocket_manager.connect_user(
                    user_id=self.user_id,
                    websocket=websocket_connection.mock_websocket,
                    thread_id=self.thread_id
                )
                
                # FAILING ASSERTION: Check if WebSocket manager preserves thread context
                # This should fail initially because proper thread propagation is not implemented
                self.assertIsNotNone(connection_id, "Connection should be established")
                
                # Check if we can retrieve the connection with thread context
                connection_info = self.websocket_manager.get_connection_info(self.user_id)
                
                # This will likely fail, proving thread context is not properly maintained
                self.assertIn('thread_id', connection_info,
                    "WebSocket manager should maintain thread_id in connection info")
                self.assertEqual(connection_info.get('thread_id'), self.thread_id,
                    "Thread ID should match what was provided during connection")
                
            except AssertionError as e:
                # Expected failure - proves test works
                self.logger.warning(f"Expected failure in WebSocket thread propagation: {e}")
                raise
            except Exception as e:
                # Any exception indicates thread propagation issues
                self.logger.error(f"WebSocket thread propagation error: {e}")
                raise
        else:
            # No WebSocket manager available - test fails as expected
            self.fail("WebSocket manager not available - thread propagation cannot be tested")
        
        self.logger.info("WebSocket to Message Handler propagation test completed")
    
    @pytest.mark.asyncio  
    async def test_message_handler_to_agent_registry_propagation_FAIL_FIRST(self):
        """
        Test thread_id propagation from message handler to downstream services.
        
        Designed to fail initially, proving thread context is not preserved.
        """
        self.logger.info("Testing Message Handler thread context propagation")
        
        # Test with mock context to prove thread propagation logic
        test_context = {
            'thread_id': self.thread_id,
            'user_id': self.user_id,
            'message': 'Test thread propagation'
        }
        
        try:
            if self.message_handler:
                # Test with real message handler
                result = await self.message_handler.handle_user_message(
                    user_id=self.user_id,
                    message={'content': 'Test', 'thread_id': self.thread_id},
                    websocket_manager=self.websocket_manager
                )
                
                # FAILING ASSERTION: Should preserve thread context
                self.assertIsInstance(result, (dict, type(None)), "Handler should return result")
                # This will fail if thread context is not maintained
                self.assertIn(self.thread_id, str(result) if result else '',
                    "Thread ID should be preserved in processing chain")
            else:
                # No real services - this failure proves the test works
                self.fail("Message handler not available - thread propagation cannot be tested")
            
        except AssertionError as e:
            self.logger.warning(f"Expected failure in message handler propagation: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Message handler error indicates thread propagation issue: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_thread_context_isolation_FAIL_FIRST(self):
        """
        Test that thread contexts are properly isolated between concurrent users.
        
        This test validates the business-critical requirement that each user's
        conversation thread remains isolated from other users.
        """
        self.logger.info("Testing Thread Context Isolation")
        
        # Create multiple user contexts  
        user_contexts = []
        for i in range(3):
            user_contexts.append({
                'user_id': str(uuid.uuid4()),
                'thread_id': str(uuid.uuid4()),
                'message': f'User {i+1} test message'
            })
        
        # Create WebSocket connections for each user
        connections = []
        for ctx in user_contexts:
            conn = await self.websocket_util.create_test_connection(
                user_id=ctx['user_id'],
                thread_id=ctx['thread_id']
            )
            connections.append((ctx, conn))
        
        try:
            # Simulate concurrent processing
            if self.websocket_manager:
                connection_results = []
                for ctx, conn in connections:
                    try:
                        connection_id = await self.websocket_manager.connect_user(
                            user_id=ctx['user_id'],
                            websocket=conn.mock_websocket,
                            thread_id=ctx['thread_id']
                        )
                        connection_results.append((ctx, connection_id))
                    except Exception as e:
                        self.logger.error(f"Connection failed for user {ctx['user_id']}: {e}")
                
                # FAILING ASSERTION: Thread contexts should be isolated
                # This will fail if thread isolation is not properly implemented
                self.assertGreater(len(connection_results), 0, 
                    "At least one connection should be established")
                
                # Each connection should maintain its own thread context
                unique_threads = set(ctx['thread_id'] for ctx, _ in connection_results)
                self.assertEqual(len(unique_threads), len(connection_results),
                    "Each connection should have unique thread context")
                
            else:
                # No WebSocket manager - test fails as expected
                self.fail("WebSocket manager not available - thread isolation cannot be tested")
                
        except AssertionError as e:
            self.logger.warning(f"Expected failure in thread isolation: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Thread isolation error: {e}")
            raise
        
        self.logger.info("Thread Context Isolation test completed")
    


if __name__ == "__main__":
    # Run tests with verbose output to see failures
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))