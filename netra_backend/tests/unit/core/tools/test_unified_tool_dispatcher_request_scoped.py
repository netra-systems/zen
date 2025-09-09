"""Unit tests for UnifiedToolDispatcher request-scoped dispatching patterns.

These tests validate the factory-enforced request isolation patterns that ensure
proper user isolation and prevent shared state issues in multi-user scenarios.

Business Value: Platform/Internal - System Stability  
Ensures tool dispatching maintains proper user boundaries and request isolation.

Test Coverage:
- Factory pattern enforcement (no direct instantiation)
- Request-scoped dispatcher creation with user context
- User isolation boundaries and session cleanup
- WebSocket manager integration for events
- Tool registration and execution flow validation
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    DispatchStrategy,
    create_request_scoped_dispatcher,
    AuthenticationError,
    PermissionError,
    SecurityViolationError,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.unified_tool_registry.models import ToolExecutionResult
from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from langchain_core.tools import BaseTool


class MockWebSocketManager:
    """Mock WebSocket manager for testing WebSocket integration."""
    
    def __init__(self):
        self.events_sent = []
        self.connection_active = True
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Mock WebSocket event sending."""
        if not self.connection_active:
            return False
            
        event_record = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.events_sent.append(event_record)
        return True
        
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get events of specific type."""
        return [event for event in self.events_sent if event["event_type"] == event_type]
        
    def clear_events(self):
        """Clear all recorded events."""
        self.events_sent.clear()


class MockBusinessTool(BaseTool):
    """Mock business tool for testing tool execution."""
    
    name: str = "business_metrics_analyzer"
    description: str = "Analyzes business metrics and performance data"
    
    def __init__(self):
        super().__init__()
        self.execution_count = 0
        self.last_parameters = None
        
    def _run(self, query: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(query, **kwargs))
        
    async def _arun(self, query: str, **kwargs) -> str:
        """Asynchronous execution."""
        self.execution_count += 1
        self.last_parameters = {"query": query, **kwargs}
        
        # Simulate business analysis
        await asyncio.sleep(0.001)
        
        return f"Business analysis result for: {query}"


class TestUnifiedToolDispatcherRequestScoped(SSotAsyncTestCase):
    """Unit tests for request-scoped tool dispatcher patterns."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create test user contexts
        self.user1_context = UserExecutionContext(
            user_id="test_user_001",
            run_id=f"run_{int(time.time() * 1000)}",
            thread_id="thread_001",
            session_id="session_001",
            metadata={"plan_tier": "early", "roles": ["user"]}
        )
        
        self.user2_context = UserExecutionContext(
            user_id="test_user_002", 
            run_id=f"run_{int(time.time() * 1000) + 1}",
            thread_id="thread_002",
            session_id="session_002",
            metadata={"plan_tier": "mid", "roles": ["user"]}
        )
        
        self.admin_context = UserExecutionContext(
            user_id="admin_user_001",
            run_id=f"admin_run_{int(time.time() * 1000)}",
            thread_id="admin_thread_001", 
            session_id="admin_session_001",
            metadata={"plan_tier": "enterprise", "roles": ["admin", "user"]}
        )
        
        # Mock WebSocket manager
        self.websocket_manager = MockWebSocketManager()
        
        # Mock tools
        self.business_tool = MockBusinessTool()
        
    async def tearDown(self):
        """Clean up after tests."""
        # Clean up any active dispatchers
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user1_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user2_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.admin_context.user_id)
        
        await super().tearDown()
    
    # ===================== FACTORY PATTERN ENFORCEMENT =====================
    
    def test_direct_instantiation_forbidden(self):
        """Test that direct instantiation of UnifiedToolDispatcher is forbidden."""
        with self.assertRaises(RuntimeError) as context:
            dispatcher = UnifiedToolDispatcher()
            
        error_message = str(context.exception)
        self.assertIn("Direct instantiation of UnifiedToolDispatcher is forbidden", error_message)
        self.assertIn("Use factory methods for proper isolation", error_message)
        
    async def test_factory_creation_success(self):
        """Test successful factory creation with proper user context."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        # Verify dispatcher is properly initialized
        self.assertIsNotNone(dispatcher)
        self.assertEqual(dispatcher.user_context.user_id, self.user1_context.user_id)
        self.assertEqual(dispatcher.strategy, DispatchStrategy.DEFAULT)
        self.assertTrue(dispatcher._is_active)
        
        # Verify WebSocket integration
        self.assertTrue(dispatcher.has_websocket_support)
        self.assertIsNotNone(dispatcher.websocket_manager)
        
        # Verify tool registration
        self.assertTrue(dispatcher.has_tool("business_metrics_analyzer"))
        self.assertIn("business_metrics_analyzer", dispatcher.get_available_tools())
        
        await dispatcher.cleanup()
        
    async def test_factory_creation_without_context_fails(self):
        """Test that factory creation fails without valid user context."""
        with self.assertRaises(AuthenticationError) as context:
            dispatcher = await UnifiedToolDispatcher.create_for_user(
                user_context=None,
                websocket_bridge=self.websocket_manager
            )
            
        error_message = str(context.exception)
        self.assertIn("Valid UserExecutionContext required", error_message)
        
    async def test_factory_scoped_creation_with_cleanup(self):
        """Test scoped factory creation with automatic cleanup."""
        dispatcher_ref = None
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        ) as dispatcher:
            dispatcher_ref = dispatcher
            
            # Verify dispatcher is active within scope
            self.assertTrue(dispatcher._is_active)
            self.assertEqual(dispatcher.user_context.user_id, self.user1_context.user_id)
            
            # Test tool execution within scope
            result = await dispatcher.execute_tool(
                "business_metrics_analyzer",
                {"query": "Q4 revenue analysis"}
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.tool_name, "business_metrics_analyzer")
            self.assertIsNotNone(result.result)
        
        # Verify automatic cleanup occurred
        self.assertFalse(dispatcher_ref._is_active)
        
    # ===================== REQUEST-SCOPED ISOLATION =====================
        
    async def test_multiple_user_isolation(self):
        """Test that multiple users have isolated dispatcher instances."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        # Verify different instances
        self.assertNotEqual(dispatcher1.dispatcher_id, dispatcher2.dispatcher_id)
        self.assertEqual(dispatcher1.user_context.user_id, self.user1_context.user_id)
        self.assertEqual(dispatcher2.user_context.user_id, self.user2_context.user_id)
        
        # Test isolated tool execution
        result1 = await dispatcher1.execute_tool(
            "business_metrics_analyzer",
            {"query": "User1 analysis"}
        )
        
        result2 = await dispatcher2.execute_tool(
            "business_metrics_analyzer", 
            {"query": "User2 analysis"}
        )
        
        # Verify execution isolation
        self.assertEqual(result1.user_id, self.user1_context.user_id)
        self.assertEqual(result2.user_id, self.user2_context.user_id)
        self.assertNotEqual(result1.result, result2.result)
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
    async def test_concurrent_user_tool_execution(self):
        """Test concurrent tool execution by different users maintains isolation."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        # Execute tools concurrently
        task1 = asyncio.create_task(dispatcher1.execute_tool(
            "business_metrics_analyzer",
            {"query": "Concurrent user1 analysis"}
        ))
        
        task2 = asyncio.create_task(dispatcher2.execute_tool(
            "business_metrics_analyzer",
            {"query": "Concurrent user2 analysis"}  
        ))
        
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        
        # Verify both executions succeeded
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertNotIsInstance(result, Exception)
            self.assertTrue(result.success)
            
        # Verify user isolation maintained
        result1, result2 = results
        self.assertEqual(result1.user_id, self.user1_context.user_id)
        self.assertEqual(result2.user_id, self.user2_context.user_id)
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
    # ===================== WEBSOCKET INTEGRATION =====================
        
    async def test_websocket_event_emission_during_execution(self):
        """Test that WebSocket events are emitted during tool execution."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        # Clear any setup events
        self.websocket_manager.clear_events()
        
        # Execute tool to generate events
        result = await dispatcher.execute_tool(
            "business_metrics_analyzer",
            {"query": "WebSocket event test"}
        )
        
        self.assertTrue(result.success)
        
        # Verify WebSocket events were sent
        events = self.websocket_manager.events_sent
        self.assertGreater(len(events), 0)
        
        # Verify tool_executing event
        executing_events = self.websocket_manager.get_events_by_type("tool_executing")
        self.assertEqual(len(executing_events), 1)
        executing_event = executing_events[0]
        self.assertEqual(executing_event["data"]["tool_name"], "business_metrics_analyzer")
        self.assertEqual(executing_event["data"]["user_id"], self.user1_context.user_id)
        
        # Verify tool_completed event
        completed_events = self.websocket_manager.get_events_by_type("tool_completed")
        self.assertEqual(len(completed_events), 1)
        completed_event = completed_events[0]
        self.assertEqual(completed_event["data"]["tool_name"], "business_metrics_analyzer")
        self.assertEqual(completed_event["data"]["status"], "success")
        
        await dispatcher.cleanup()
        
    async def test_websocket_events_with_user_context_data(self):
        """Test WebSocket events include proper user context data."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        self.websocket_manager.clear_events()
        
        result = await dispatcher.execute_tool(
            "business_metrics_analyzer",
            {"query": "User context validation test"}
        )
        
        self.assertTrue(result.success)
        
        # Verify all events contain user context data
        for event in self.websocket_manager.events_sent:
            event_data = event["data"]
            self.assertEqual(event_data["user_id"], self.user1_context.user_id)
            self.assertEqual(event_data["run_id"], self.user1_context.run_id)
            self.assertEqual(event_data["thread_id"], self.user1_context.thread_id)
            self.assertIn("timestamp", event_data)
            
        await dispatcher.cleanup()
        
    # ===================== ADMIN DISPATCHER TESTING =====================
        
    async def test_admin_dispatcher_creation(self):
        """Test creation of admin dispatcher with elevated permissions."""
        # Mock admin user and database
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.is_admin = True
        
        admin_dispatcher = UnifiedToolDispatcherFactory.create_for_admin(
            user_context=self.admin_context,
            db=mock_db,
            user=mock_admin_user,
            websocket_manager=self.websocket_manager
        )
        
        # Verify admin configuration
        self.assertEqual(admin_dispatcher.strategy, DispatchStrategy.ADMIN)
        self.assertIsNotNone(admin_dispatcher.admin_tools)
        self.assertIn('corpus_create', admin_dispatcher.admin_tools)
        self.assertEqual(admin_dispatcher.db, mock_db)
        self.assertEqual(admin_dispatcher.user, mock_admin_user)
        
        await admin_dispatcher.cleanup()
        
    # ===================== METRICS AND MONITORING =====================
        
    async def test_dispatcher_metrics_tracking(self):
        """Test that dispatcher tracks execution metrics properly."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        initial_metrics = dispatcher.get_metrics()
        self.assertEqual(initial_metrics['tools_executed'], 0)
        self.assertEqual(initial_metrics['successful_executions'], 0)
        
        # Execute successful tool
        result = await dispatcher.execute_tool(
            "business_metrics_analyzer",
            {"query": "Metrics test"}
        )
        self.assertTrue(result.success)
        
        # Check updated metrics
        updated_metrics = dispatcher.get_metrics()
        self.assertEqual(updated_metrics['tools_executed'], 1)
        self.assertEqual(updated_metrics['successful_executions'], 1)
        self.assertEqual(updated_metrics['failed_executions'], 0)
        self.assertGreater(updated_metrics['total_execution_time_ms'], 0)
        
        await dispatcher.cleanup()
        
    async def test_dispatcher_cleanup_and_state_management(self):
        """Test proper cleanup and state management of dispatchers."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.business_tool]
        )
        
        # Verify dispatcher is active
        self.assertTrue(dispatcher._is_active)
        self.assertEqual(dispatcher.user_context.user_id, self.user1_context.user_id)
        
        # Cleanup dispatcher
        await dispatcher.cleanup()
        
        # Verify cleanup state
        self.assertFalse(dispatcher._is_active)
        
        # Verify operations fail after cleanup
        with self.assertRaises(RuntimeError) as context:
            await dispatcher.execute_tool("business_metrics_analyzer", {})
            
        self.assertIn("has been cleaned up", str(context.exception))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])