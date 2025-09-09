"""Integration tests for tool execution user context isolation.

These tests validate that tool execution maintains strict user boundaries 
during concurrent operations and prevents cross-user data leakage.

Business Value: Platform/Internal - Security & Data Privacy
Ensures multi-user tool execution maintains isolation and prevents data breaches.

Test Coverage:
- Concurrent tool execution by different users
- User context boundary enforcement  
- Session isolation during tool operations
- WebSocket event isolation per user
- Tool state isolation and cleanup
- Error boundary isolation
"""

import asyncio
import pytest
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    create_request_scoped_dispatcher,
)
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from langchain_core.tools import BaseTool


class UserIsolationWebSocketManager:
    """Mock WebSocket manager that tracks events per user for isolation testing."""
    
    def __init__(self):
        self.user_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.connection_states: Dict[str, bool] = defaultdict(lambda: True)
        self.cross_user_violations: List[Dict[str, Any]] = []
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send event and track user isolation."""
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")
        
        if not user_id:
            # Log potential isolation violation
            self.cross_user_violations.append({
                "violation_type": "missing_user_id",
                "event_type": event_type,
                "data": data,
                "timestamp": time.time()
            })
            return False
            
        if not self.connection_states[user_id]:
            return False
            
        event_record = {
            "event_type": event_type,
            "data": data.copy(),
            "timestamp": time.time(),
            "user_id": user_id,
            "thread_id": thread_id
        }
        
        self.user_events[user_id].append(event_record)
        return True
        
    def get_user_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events for specific user."""
        return self.user_events[user_id]
        
    def get_cross_user_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events that may have leaked from other users."""
        cross_user_events = []
        for other_user_id, events in self.user_events.items():
            if other_user_id != user_id:
                for event in events:
                    # Check if event contains data from the target user
                    if event["data"].get("user_id") == user_id:
                        cross_user_events.append({
                            "source_user": other_user_id,
                            "target_user": user_id,
                            "event": event
                        })
        return cross_user_events
        
    def disconnect_user(self, user_id: str):
        """Simulate user disconnection."""
        self.connection_states[user_id] = False
        
    def clear_events(self):
        """Clear all tracked events."""
        self.user_events.clear()
        self.cross_user_violations.clear()


class IsolatedUserTool(BaseTool):
    """Tool that tracks user-specific execution state for isolation testing."""
    
    name = "user_state_tool"
    description = "Tool that maintains user-specific state"
    
    def __init__(self):
        super().__init__()
        self.user_executions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.user_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.execution_count = 0
        self.cross_user_access_attempts = []
        
    def _run(self, operation: str, user_data: str = None, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(operation, user_data, **kwargs))
        
    async def _arun(self, operation: str, user_data: str = None, **kwargs) -> str:
        """Asynchronous execution with user state tracking."""
        self.execution_count += 1
        
        # Get context to determine user
        context = kwargs.get('context')
        user_id = context.user_id if context else "unknown"
        
        # Record execution
        execution_record = {
            "operation": operation,
            "user_data": user_data,
            "timestamp": time.time(),
            "execution_id": self.execution_count,
            "thread_id": context.thread_id if context else None
        }
        
        self.user_executions[user_id].append(execution_record)
        
        # Simulate user-specific data operation
        if operation == "store_data":
            self.user_data[user_id][f"data_{len(self.user_data[user_id])}"] = user_data
            result = f"Stored data for user {user_id}: {user_data}"
            
        elif operation == "get_data":
            user_stored_data = self.user_data[user_id]
            result = f"User {user_id} data: {list(user_stored_data.values())}"
            
        elif operation == "cross_user_access":
            # This operation intentionally tries to access other user's data (for testing)
            target_user = user_data
            if target_user in self.user_data and target_user != user_id:
                self.cross_user_access_attempts.append({
                    "accessing_user": user_id,
                    "target_user": target_user,
                    "timestamp": time.time()
                })
                result = f"ERROR: Cross-user access blocked for user {user_id} -> {target_user}"
            else:
                result = f"No cross-user access attempted by {user_id}"
                
        else:
            result = f"Unknown operation '{operation}' for user {user_id}"
            
        # Add small delay to simulate real work
        await asyncio.sleep(0.001)
        
        return result
        
    def get_user_execution_count(self, user_id: str) -> int:
        """Get execution count for specific user."""
        return len(self.user_executions[user_id])
        
    def has_cross_user_violations(self) -> bool:
        """Check if any cross-user access attempts occurred."""
        return len(self.cross_user_access_attempts) > 0


class TestToolExecutionUserContextIsolation(SSotAsyncTestCase):
    """Integration tests for user context isolation in tool execution."""
    
    def setUp(self):
        """Set up test environment with multiple user contexts."""
        super().setUp()
        
        # Create distinct user contexts
        self.user1_context = UserExecutionContext(
            user_id="isolation_user_001",
            run_id=f"run_001_{int(time.time() * 1000)}",
            thread_id="thread_001_isolation",
            session_id="session_001_isolation",
            metadata={"plan_tier": "early", "roles": ["user"], "tenant": "company_a"}
        )
        
        self.user2_context = UserExecutionContext(
            user_id="isolation_user_002", 
            run_id=f"run_002_{int(time.time() * 1000)}",
            thread_id="thread_002_isolation",
            session_id="session_002_isolation",
            metadata={"plan_tier": "mid", "roles": ["user"], "tenant": "company_b"}
        )
        
        self.user3_context = UserExecutionContext(
            user_id="isolation_user_003",
            run_id=f"run_003_{int(time.time() * 1000)}",
            thread_id="thread_003_isolation", 
            session_id="session_003_isolation",
            metadata={"plan_tier": "enterprise", "roles": ["admin", "user"], "tenant": "company_c"}
        )
        
        # Create isolation tracking WebSocket manager
        self.websocket_manager = UserIsolationWebSocketManager()
        
        # Create user-specific tool for testing isolation
        self.isolation_tool = IsolatedUserTool()
        
    async def tearDown(self):
        """Clean up user dispatchers."""
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user1_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user2_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user3_context.user_id)
        
        await super().tearDown()
        
    # ===================== USER ISOLATION TESTS =====================
        
    async def test_concurrent_user_tool_execution_isolation(self):
        """Test that concurrent tool execution by different users maintains isolation."""
        # Create user-specific dispatchers
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        dispatcher3 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user3_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        # Execute tools concurrently with user-specific data
        tasks = [
            dispatcher1.execute_tool("user_state_tool", {
                "operation": "store_data",
                "user_data": "sensitive_user1_data"
            }),
            dispatcher2.execute_tool("user_state_tool", {
                "operation": "store_data", 
                "user_data": "confidential_user2_info"
            }),
            dispatcher3.execute_tool("user_state_tool", {
                "operation": "store_data",
                "user_data": "admin_user3_secrets"
            })
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions succeeded
        for result in results:
            self.assertNotIsInstance(result, Exception)
            self.assertTrue(result.success)
            
        # Verify user-specific execution counts
        self.assertEqual(self.isolation_tool.get_user_execution_count(self.user1_context.user_id), 1)
        self.assertEqual(self.isolation_tool.get_user_execution_count(self.user2_context.user_id), 1)
        self.assertEqual(self.isolation_tool.get_user_execution_count(self.user3_context.user_id), 1)
        
        # Verify no cross-user access violations
        self.assertFalse(self.isolation_tool.has_cross_user_violations())
        
        # Verify user data isolation
        self.assertIn("sensitive_user1_data", results[0].result)
        self.assertIn("confidential_user2_info", results[1].result)
        self.assertIn("admin_user3_secrets", results[2].result)
        
        # Ensure no user can see other user's data
        self.assertNotIn("confidential_user2_info", results[0].result)
        self.assertNotIn("admin_user3_secrets", results[0].result)
        self.assertNotIn("sensitive_user1_data", results[1].result)
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        await dispatcher3.cleanup()
        
    async def test_websocket_event_user_isolation(self):
        """Test that WebSocket events are properly isolated per user."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        # Clear any setup events
        self.websocket_manager.clear_events()
        
        # Execute tools for different users
        await dispatcher1.execute_tool("user_state_tool", {
            "operation": "get_data"
        })
        
        await dispatcher2.execute_tool("user_state_tool", {
            "operation": "get_data"
        })
        
        # Verify events are properly isolated
        user1_events = self.websocket_manager.get_user_events(self.user1_context.user_id)
        user2_events = self.websocket_manager.get_user_events(self.user2_context.user_id)
        
        # Each user should have their own events
        self.assertGreater(len(user1_events), 0)
        self.assertGreater(len(user2_events), 0)
        
        # Verify no cross-user event leakage
        user1_cross_events = self.websocket_manager.get_cross_user_events(self.user1_context.user_id)
        user2_cross_events = self.websocket_manager.get_cross_user_events(self.user2_context.user_id)
        
        self.assertEqual(len(user1_cross_events), 0, "User 1 should not receive User 2's events")
        self.assertEqual(len(user2_cross_events), 0, "User 2 should not receive User 1's events")
        
        # Verify no isolation violations were detected
        self.assertEqual(len(self.websocket_manager.cross_user_violations), 0)
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
    async def test_user_session_boundary_enforcement(self):
        """Test that user session boundaries are properly enforced."""
        # Create dispatcher with specific session context
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        # Execute tool with session-specific operation
        result = await dispatcher.execute_tool("user_state_tool", {
            "operation": "store_data",
            "user_data": f"session_data_{self.user1_context.session_id}"
        })
        
        self.assertTrue(result.success)
        
        # Verify session context is maintained in tool execution
        user_executions = self.isolation_tool.user_executions[self.user1_context.user_id]
        self.assertEqual(len(user_executions), 1)
        
        execution_record = user_executions[0]
        self.assertIn(self.user1_context.session_id, execution_record["user_data"])
        
        await dispatcher.cleanup()
        
    async def test_error_boundary_isolation(self):
        """Test that errors in one user's tools don't affect other users."""
        # Create mock failing tool for one user
        class FailingTool(BaseTool):
            name = "failing_tool"
            description = "Tool that always fails"
            
            def _run(self, **kwargs):
                return asyncio.run(self._arun(**kwargs))
                
            async def _arun(self, **kwargs):
                raise RuntimeError("Simulated tool failure")
        
        failing_tool = FailingTool()
        
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[failing_tool]  # User 1 gets failing tool
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]  # User 2 gets working tool
        )
        
        # Execute tools concurrently - one should fail, one should succeed
        task1 = asyncio.create_task(dispatcher1.execute_tool("failing_tool", {}))
        task2 = asyncio.create_task(dispatcher2.execute_tool("user_state_tool", {
            "operation": "store_data",
            "user_data": "successful_execution_despite_other_user_error"
        }))
        
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        
        # Verify user 1's tool failed
        result1 = results[0]
        self.assertFalse(result1.success)
        self.assertIn("Simulated tool failure", result1.error)
        
        # Verify user 2's tool succeeded despite user 1's failure
        result2 = results[1]
        self.assertTrue(result2.success)
        self.assertIn("successful_execution_despite_other_user_error", result2.result)
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
    # ===================== LOAD TESTING FOR ISOLATION =====================
        
    async def test_high_concurrency_user_isolation(self):
        """Test user isolation under high concurrency load."""
        num_users = 10
        operations_per_user = 5
        
        # Create multiple user contexts and dispatchers
        user_contexts = []
        dispatchers = []
        
        for i in range(num_users):
            context = UserExecutionContext(
                user_id=f"load_user_{i:03d}",
                run_id=f"load_run_{i:03d}_{int(time.time() * 1000)}",
                thread_id=f"load_thread_{i:03d}",
                session_id=f"load_session_{i:03d}",
                metadata={"load_test": True, "user_index": i}
            )
            user_contexts.append(context)
            
            dispatcher = await UnifiedToolDispatcher.create_for_user(
                user_context=context,
                websocket_bridge=self.websocket_manager,
                tools=[self.isolation_tool]
            )
            dispatchers.append(dispatcher)
        
        # Create concurrent tasks for all users
        all_tasks = []
        for i, dispatcher in enumerate(dispatchers):
            for op_num in range(operations_per_user):
                task = dispatcher.execute_tool("user_state_tool", {
                    "operation": "store_data",
                    "user_data": f"user_{i}_operation_{op_num}_data"
                })
                all_tasks.append((i, op_num, task))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[task for _, _, task in all_tasks], return_exceptions=True)
        
        # Verify all operations succeeded
        success_count = 0
        for result in results:
            if not isinstance(result, Exception) and result.success:
                success_count += 1
                
        expected_operations = num_users * operations_per_user
        self.assertEqual(success_count, expected_operations, 
                        f"Expected {expected_operations} successful operations, got {success_count}")
        
        # Verify each user has correct execution count
        for i, context in enumerate(user_contexts):
            user_execution_count = self.isolation_tool.get_user_execution_count(context.user_id)
            self.assertEqual(user_execution_count, operations_per_user,
                           f"User {i} should have {operations_per_user} executions, got {user_execution_count}")
        
        # Verify no cross-user violations
        self.assertFalse(self.isolation_tool.has_cross_user_violations())
        
        # Cleanup all dispatchers
        for dispatcher in dispatchers:
            await dispatcher.cleanup()
            
    async def test_user_disconnect_isolation(self):
        """Test that user disconnection doesn't affect other users' tool execution."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.isolation_tool]
        )
        
        # Execute tool for user 1
        result1 = await dispatcher1.execute_tool("user_state_tool", {
            "operation": "store_data",
            "user_data": "before_disconnect"
        })
        self.assertTrue(result1.success)
        
        # Simulate user 1 disconnection
        self.websocket_manager.disconnect_user(self.user1_context.user_id)
        
        # User 2 should still be able to execute tools
        result2 = await dispatcher2.execute_tool("user_state_tool", {
            "operation": "store_data",
            "user_data": "after_user1_disconnect"
        })
        self.assertTrue(result2.success)
        
        # User 1's subsequent tool execution should handle disconnection gracefully
        result1_after = await dispatcher1.execute_tool("user_state_tool", {
            "operation": "get_data"
        })
        # Tool execution should still work, but WebSocket events may fail
        self.assertTrue(result1_after.success)
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])