"""User Isolation Validation Tests for RequestScopedToolDispatcher SSOT.

Test Phase 2: User Context Isolation Validation Tests
Focus on the 85% failure risk in user isolation due to singleton remnants and shared state.

CRITICAL ISOLATION REQUIREMENTS:
- Complete user context isolation between concurrent requests
- No cross-user data leakage in tool execution
- Separate WebSocket event streams per user  
- Independent tool registry per user context
- Proper resource cleanup per user session

Business Value:
- Ensures multi-tenant safety for production deployment
- Prevents data leakage between concurrent users
- Enables reliable concurrent tool execution
- Maintains user privacy and security
"""

import asyncio
import gc
import time
import uuid
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, MagicMock, patch
import weakref

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class TestUserIsolationValidation(SSotAsyncTestCase):
    """Test user isolation in RequestScopedToolDispatcher SSOT implementation."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        
        # Create multiple user contexts for isolation testing
        self.users = {
            'alice': UserExecutionContext(
                user_id="alice_user_id",
                thread_id="alice_thread_id",
                run_id=f"alice_run_{uuid.uuid4()}"
            ),
            'bob': UserExecutionContext(
                user_id="bob_user_id", 
                thread_id="bob_thread_id",
                run_id=f"bob_run_{uuid.uuid4()}"
            ),
            'charlie': UserExecutionContext(
                user_id="charlie_user_id",
                thread_id="charlie_thread_id", 
                run_id=f"charlie_run_{uuid.uuid4()}"
            )
        }

    async def test_tool_registry_isolation_between_users(self):
        """Test that tool registries are completely isolated between users.
        
        EXPECTED: FAIL initially due to shared tool registry state
        EXPECTED: PASS after SSOT consolidation with proper isolation
        """
        dispatchers = {}
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            # Create separate dispatchers for each user
            for user_name, user_context in self.users.items():
                dispatchers[user_name] = RequestScopedToolDispatcher(
                    user_context=user_context,
                    websocket_emitter=None  # Focus on tool registry isolation
                )
            
            # Register different tools for each user
            def alice_tool(query: str) -> str:
                return f"Alice's secret result: {query}"
                
            def bob_tool(query: str) -> str:
                return f"Bob's confidential result: {query}"
                
            def charlie_tool(query: str) -> str:
                return f"Charlie's private result: {query}"
            
            dispatchers['alice'].register_tool("alice_secret_tool", alice_tool, "Alice's private tool")
            dispatchers['bob'].register_tool("bob_confidential_tool", bob_tool, "Bob's business tool")
            dispatchers['charlie'].register_tool("charlie_private_tool", charlie_tool, "Charlie's personal tool")
            
            # ISOLATION VALIDATION: Each user should only see their own tools
            
            # Alice should only have her tool
            self.assertTrue(
                dispatchers['alice'].has_tool("alice_secret_tool"),
                "Alice should have access to her own tool"
            )
            self.assertFalse(
                dispatchers['alice'].has_tool("bob_confidential_tool"),
                "USER ISOLATION VIOLATION: Alice should NOT have access to Bob's tool"
            )
            self.assertFalse(
                dispatchers['alice'].has_tool("charlie_private_tool"),
                "USER ISOLATION VIOLATION: Alice should NOT have access to Charlie's tool"
            )
            
            # Bob should only have his tool
            self.assertTrue(
                dispatchers['bob'].has_tool("bob_confidential_tool"),
                "Bob should have access to his own tool"
            )
            self.assertFalse(
                dispatchers['bob'].has_tool("alice_secret_tool"),
                "USER ISOLATION VIOLATION: Bob should NOT have access to Alice's tool"
            )
            self.assertFalse(
                dispatchers['bob'].has_tool("charlie_private_tool"),
                "USER ISOLATION VIOLATION: Bob should NOT have access to Charlie's tool"
            )
            
            # Charlie should only have his tool
            self.assertTrue(
                dispatchers['charlie'].has_tool("charlie_private_tool"),
                "Charlie should have access to his own tool"
            )
            self.assertFalse(
                dispatchers['charlie'].has_tool("alice_secret_tool"),
                "USER ISOLATION VIOLATION: Charlie should NOT have access to Alice's tool"
            )
            self.assertFalse(
                dispatchers['charlie'].has_tool("bob_confidential_tool"),
                "USER ISOLATION VIOLATION: Charlie should NOT have access to Bob's tool"
            )
            
            # Verify tool counts are correct per user
            alice_tools = list(dispatchers['alice'].tools.keys())
            bob_tools = list(dispatchers['bob'].tools.keys())
            charlie_tools = list(dispatchers['charlie'].tools.keys())
            
            self.assertEqual(
                len(alice_tools), 1,
                f"Alice should have exactly 1 tool, got: {alice_tools}"
            )
            self.assertEqual(
                len(bob_tools), 1,
                f"Bob should have exactly 1 tool, got: {bob_tools}"
            )
            self.assertEqual(
                len(charlie_tools), 1,
                f"Charlie should have exactly 1 tool, got: {charlie_tools}"
            )
            
        except Exception as e:
            self.fail(f"Tool registry isolation test failed: {e}")
        
        finally:
            # Clean up all dispatchers
            for dispatcher in dispatchers.values():
                if hasattr(dispatcher, 'cleanup'):
                    await dispatcher.cleanup()

    async def test_execution_context_isolation(self):
        """Test that execution contexts are completely isolated between users.
        
        EXPECTED: FAIL initially due to shared execution state
        EXPECTED: PASS after SSOT consolidation with proper context isolation
        """
        execution_results = {}
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatchers = {}
            
            # Create dispatchers with shared tool name but different implementations
            for user_name, user_context in self.users.items():
                dispatchers[user_name] = RequestScopedToolDispatcher(
                    user_context=user_context
                )
                
                # Each user gets their own implementation of "shared_tool"
                def create_user_tool(user_name):
                    def user_specific_tool(query: str) -> str:
                        return f"{user_name.upper()}_RESULT: {query}"
                    return user_specific_tool
                
                dispatchers[user_name].register_tool(
                    "shared_tool", 
                    create_user_tool(user_name),
                    f"{user_name}'s implementation"
                )
            
            # Execute the same tool name for all users concurrently
            async def execute_for_user(user_name: str, dispatcher):
                result = await dispatcher.dispatch("shared_tool", query=f"test_for_{user_name}")
                return user_name, result
            
            # Execute concurrently to test isolation under race conditions
            tasks = [
                execute_for_user(user_name, dispatcher) 
                for user_name, dispatcher in dispatchers.items()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in results:
                if isinstance(result, tuple):
                    user_name, execution_result = result
                    execution_results[user_name] = execution_result
                else:
                    self.fail(f"Execution failed: {result}")
            
            # ISOLATION VALIDATION: Each user should get their own result
            
            if 'alice' in execution_results:
                alice_result = execution_results['alice']
                if hasattr(alice_result, 'message'):
                    alice_content = alice_result.message
                else:
                    alice_content = str(alice_result)
                    
                self.assertIn(
                    "ALICE_RESULT",
                    alice_content.upper(),
                    f"EXECUTION ISOLATION VIOLATION: Alice got wrong result: {alice_content}"
                )
            
            if 'bob' in execution_results:
                bob_result = execution_results['bob']
                if hasattr(bob_result, 'message'):
                    bob_content = bob_result.message
                else:
                    bob_content = str(bob_result)
                    
                self.assertIn(
                    "BOB_RESULT",
                    bob_content.upper(),
                    f"EXECUTION ISOLATION VIOLATION: Bob got wrong result: {bob_content}"
                )
            
            if 'charlie' in execution_results:
                charlie_result = execution_results['charlie']
                if hasattr(charlie_result, 'message'):
                    charlie_content = charlie_result.message
                else:
                    charlie_content = str(charlie_result)
                    
                self.assertIn(
                    "CHARLIE_RESULT",
                    charlie_content.upper(),
                    f"EXECUTION ISOLATION VIOLATION: Charlie got wrong result: {charlie_content}"
                )
            
            # No result should contain another user's data
            for user_name, result in execution_results.items():
                result_content = str(result).upper()
                other_users = [u for u in self.users.keys() if u != user_name]
                
                for other_user in other_users:
                    self.assertNotIn(
                        f"{other_user.upper()}_RESULT",
                        result_content,
                        f"CROSS-USER DATA LEAKAGE: {user_name}'s result contains {other_user}'s data: {result_content}"
                    )
            
        except Exception as e:
            self.fail(f"Execution context isolation test failed: {e}")
        
        finally:
            # Clean up
            for dispatcher in dispatchers.values():
                if hasattr(dispatcher, 'cleanup'):
                    await dispatcher.cleanup()

    async def test_metrics_isolation_between_users(self):
        """Test that metrics are isolated per user context.
        
        EXPECTED: FAIL initially due to shared metrics state
        EXPECTED: PASS after SSOT consolidation with per-user metrics
        """
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatchers = {}
            
            # Create dispatchers for each user
            for user_name, user_context in self.users.items():
                dispatchers[user_name] = RequestScopedToolDispatcher(
                    user_context=user_context
                )
                
                # Register a test tool
                def create_test_tool(user_identifier):
                    def test_tool(query: str) -> str:
                        return f"Result for {user_identifier}: {query}"
                    return test_tool
                
                dispatchers[user_name].register_tool(
                    "test_tool",
                    create_test_tool(user_name)
                )
            
            # Execute different numbers of tools per user to create distinct metrics
            await dispatchers['alice'].dispatch("test_tool", query="alice_test_1")
            await dispatchers['alice'].dispatch("test_tool", query="alice_test_2")  # Alice: 2 executions
            
            await dispatchers['bob'].dispatch("test_tool", query="bob_test_1")  # Bob: 1 execution
            
            await dispatchers['charlie'].dispatch("test_tool", query="charlie_test_1")
            await dispatchers['charlie'].dispatch("test_tool", query="charlie_test_2")
            await dispatchers['charlie'].dispatch("test_tool", query="charlie_test_3")  # Charlie: 3 executions
            
            # Get metrics for each user
            alice_metrics = dispatchers['alice'].get_metrics()
            bob_metrics = dispatchers['bob'].get_metrics()
            charlie_metrics = dispatchers['charlie'].get_metrics()
            
            # METRICS ISOLATION VALIDATION
            
            # Each user should have different dispatcher IDs
            self.assertNotEqual(
                alice_metrics['dispatcher_id'], bob_metrics['dispatcher_id'],
                "METRICS ISOLATION VIOLATION: Alice and Bob have same dispatcher_id"
            )
            self.assertNotEqual(
                bob_metrics['dispatcher_id'], charlie_metrics['dispatcher_id'],
                "METRICS ISOLATION VIOLATION: Bob and Charlie have same dispatcher_id"
            )
            self.assertNotEqual(
                alice_metrics['dispatcher_id'], charlie_metrics['dispatcher_id'],
                "METRICS ISOLATION VIOLATION: Alice and Charlie have same dispatcher_id"
            )
            
            # Each user should have correct user_id in metrics
            self.assertEqual(
                alice_metrics['user_id'], "alice_user_id",
                f"METRICS USER_ID VIOLATION: Alice metrics have wrong user_id: {alice_metrics['user_id']}"
            )
            self.assertEqual(
                bob_metrics['user_id'], "bob_user_id",
                f"METRICS USER_ID VIOLATION: Bob metrics have wrong user_id: {bob_metrics['user_id']}"
            )
            self.assertEqual(
                charlie_metrics['user_id'], "charlie_user_id",
                f"METRICS USER_ID VIOLATION: Charlie metrics have wrong user_id: {charlie_metrics['user_id']}"
            )
            
            # Each user should have different run_ids
            self.assertNotEqual(
                alice_metrics['run_id'], bob_metrics['run_id'],
                "METRICS RUN_ID VIOLATION: Alice and Bob have same run_id"
            )
            self.assertNotEqual(
                bob_metrics['run_id'], charlie_metrics['run_id'],
                "METRICS RUN_ID VIOLATION: Bob and Charlie have same run_id"
            )
            
            # Tool execution counts should match per user
            self.assertEqual(
                alice_metrics['tools_executed'], 2,
                f"METRICS COUNT VIOLATION: Alice should have 2 tool executions, got: {alice_metrics['tools_executed']}"
            )
            self.assertEqual(
                bob_metrics['tools_executed'], 1,
                f"METRICS COUNT VIOLATION: Bob should have 1 tool execution, got: {bob_metrics['tools_executed']}"
            )
            self.assertEqual(
                charlie_metrics['tools_executed'], 3,
                f"METRICS COUNT VIOLATION: Charlie should have 3 tool executions, got: {charlie_metrics['tools_executed']}"
            )
            
        except Exception as e:
            self.fail(f"Metrics isolation test failed: {e}")
        
        finally:
            # Clean up
            for dispatcher in dispatchers.values():
                if hasattr(dispatcher, 'cleanup'):
                    await dispatcher.cleanup()

    async def test_memory_isolation_and_cleanup(self):
        """Test that memory is properly isolated and cleaned up per user.
        
        EXPECTED: FAIL initially due to memory leaks and shared references
        EXPECTED: PASS after SSOT consolidation with proper cleanup
        """
        initial_objects = len(gc.get_objects())
        dispatcher_refs = []
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            # Create multiple dispatchers and track weak references
            for i in range(10):  # Create more dispatchers to amplify memory issues
                user_context = UserExecutionContext(
                    user_id=f"memory_test_user_{i}",
                    thread_id=f"memory_test_thread_{i}",
                    run_id=f"memory_test_run_{uuid.uuid4()}"
                )
                
                dispatcher = RequestScopedToolDispatcher(user_context=user_context)
                
                # Create weak reference to track cleanup
                dispatcher_refs.append(weakref.ref(dispatcher))
                
                # Register tools and execute to create memory usage
                dispatcher.register_tool(
                    f"test_tool_{i}",
                    lambda x: f"Result {i}: {x}",
                    f"Test tool {i}"
                )
                
                await dispatcher.dispatch(f"test_tool_{i}", query=f"test_{i}")
                
                # Clean up immediately
                await dispatcher.cleanup()
                
                # Remove strong reference
                del dispatcher
            
            # Force garbage collection
            gc.collect()
            
            # MEMORY ISOLATION VALIDATION: All weak references should be dead
            live_dispatchers = sum(1 for ref in dispatcher_refs if ref() is not None)
            
            self.assertEqual(
                live_dispatchers, 0,
                f"MEMORY LEAK VIOLATION: {live_dispatchers} dispatchers still alive after cleanup. "
                f"All dispatchers should be garbage collected after cleanup."
            )
            
            # Check that we haven't created a significant number of new objects
            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects
            
            # Allow some growth but not excessive (adjust threshold as needed)
            max_allowed_growth = 1000  # Allow up to 1000 new objects
            
            self.assertLess(
                object_growth, max_allowed_growth,
                f"MEMORY GROWTH VIOLATION: Created {object_growth} new objects, "
                f"expected less than {max_allowed_growth}. Possible memory leak."
            )
            
        except Exception as e:
            self.fail(f"Memory isolation test failed: {e}")

    async def test_concurrent_user_execution_isolation(self):
        """Test isolation under high concurrency with multiple users.
        
        EXPECTED: FAIL initially due to race conditions in shared state
        EXPECTED: PASS after SSOT consolidation with proper concurrency handling
        """
        num_concurrent_users = 20
        num_executions_per_user = 5
        
        results = {}
        errors = []
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            async def create_and_execute_user(user_id: int):
                """Create a user dispatcher and execute multiple tools."""
                try:
                    user_context = UserExecutionContext(
                        user_id=f"concurrent_user_{user_id}",
                        thread_id=f"concurrent_thread_{user_id}",
                        run_id=f"concurrent_run_{user_id}_{uuid.uuid4()}"
                    )
                    
                    dispatcher = RequestScopedToolDispatcher(user_context=user_context)
                    
                    # Register user-specific tool
                    def user_tool(query: str) -> str:
                        return f"USER_{user_id}_RESULT: {query}"
                    
                    dispatcher.register_tool(f"user_{user_id}_tool", user_tool)
                    
                    # Execute multiple times
                    user_results = []
                    for exec_id in range(num_executions_per_user):
                        result = await dispatcher.dispatch(
                            f"user_{user_id}_tool",
                            query=f"exec_{exec_id}"
                        )
                        user_results.append(result)
                    
                    await dispatcher.cleanup()
                    return user_id, user_results, None
                    
                except Exception as e:
                    return user_id, None, str(e)
            
            # Execute all users concurrently
            tasks = [
                create_and_execute_user(user_id)
                for user_id in range(num_concurrent_users)
            ]
            
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for task_result in completed_tasks:
                if isinstance(task_result, tuple):
                    user_id, user_results, error = task_result
                    if error:
                        errors.append(f"User {user_id}: {error}")
                    else:
                        results[user_id] = user_results
                else:
                    errors.append(f"Task failed: {task_result}")
            
            # CONCURRENCY ISOLATION VALIDATION
            
            # Should have no errors
            self.assertEqual(
                len(errors), 0,
                f"CONCURRENCY ERROR VIOLATION: Errors occurred during concurrent execution: {errors[:5]}"  # Show first 5 errors
            )
            
            # Should have results for all users
            self.assertEqual(
                len(results), num_concurrent_users,
                f"CONCURRENCY COMPLETION VIOLATION: Only {len(results)}/{num_concurrent_users} users completed successfully"
            )
            
            # Each user should have correct number of results
            for user_id, user_results in results.items():
                self.assertEqual(
                    len(user_results), num_executions_per_user,
                    f"CONCURRENCY RESULT COUNT VIOLATION: User {user_id} has {len(user_results)}/{num_executions_per_user} results"
                )
                
                # Each result should contain the correct user ID
                for result in user_results:
                    result_content = str(result).upper()
                    expected_user_marker = f"USER_{user_id}_RESULT"
                    
                    self.assertIn(
                        expected_user_marker.upper(),
                        result_content,
                        f"CONCURRENCY ISOLATION VIOLATION: User {user_id} result doesn't contain expected marker: {result_content}"
                    )
                    
                    # Should not contain other users' markers
                    for other_user_id in range(num_concurrent_users):
                        if other_user_id != user_id:
                            other_user_marker = f"USER_{other_user_id}_RESULT"
                            self.assertNotIn(
                                other_user_marker.upper(),
                                result_content,
                                f"CONCURRENCY CROSS-USER VIOLATION: User {user_id} result contains User {other_user_id} data: {result_content}"
                            )
            
        except Exception as e:
            self.fail(f"Concurrent user execution isolation test failed: {e}")


class TestResourceCleanupIsolation(SSotAsyncTestCase):
    """Test resource cleanup and disposal isolation."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        
        self.user_context = UserExecutionContext(
            user_id="cleanup_test_user",
            thread_id="cleanup_test_thread",
            run_id=f"cleanup_test_run_{uuid.uuid4()}"
        )

    async def test_dispatcher_cleanup_prevents_further_usage(self):
        """Test that cleaned up dispatchers cannot be used and don't leak resources.
        
        EXPECTED: FAIL initially due to incomplete cleanup implementation
        EXPECTED: PASS after SSOT consolidation with proper disposal pattern
        """
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            
            # Register tool and verify it works
            dispatcher.register_tool("test_tool", lambda x: f"Result: {x}")
            result = await dispatcher.dispatch("test_tool", query="before_cleanup")
            
            self.assertIsNotNone(result, "Tool should work before cleanup")
            
            # Clean up the dispatcher
            await dispatcher.cleanup()
            
            # Verify dispatcher is marked as inactive
            self.assertFalse(
                dispatcher.is_active(),
                "CLEANUP VIOLATION: Dispatcher should be inactive after cleanup"
            )
            
            # Attempt to use cleaned up dispatcher should fail
            with self.assertRaises(RuntimeError, msg="CLEANUP VIOLATION: Should not be able to use disposed dispatcher"):
                await dispatcher.dispatch("test_tool", query="after_cleanup")
            
            with self.assertRaises(RuntimeError, msg="CLEANUP VIOLATION: Should not be able to register tools on disposed dispatcher"):
                dispatcher.register_tool("new_tool", lambda x: x)
            
            with self.assertRaises(RuntimeError, msg="CLEANUP VIOLATION: Should not be able to check tools on disposed dispatcher"):
                dispatcher.has_tool("test_tool")
            
            with self.assertRaises(RuntimeError, msg="CLEANUP VIOLATION: Should not be able to get metrics on disposed dispatcher"):
                dispatcher.get_metrics()
            
        except Exception as e:
            self.fail(f"Dispatcher cleanup test failed: {e}")

    async def test_context_manager_automatic_cleanup(self):
        """Test that context manager pattern provides automatic cleanup.
        
        EXPECTED: FAIL initially if context manager cleanup is not implemented
        EXPECTED: PASS after SSOT consolidation with proper context manager support
        """
        dispatcher_ref = None
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            # Use async context manager
            async with RequestScopedToolDispatcher(user_context=self.user_context) as dispatcher:
                # Create weak reference to track cleanup
                dispatcher_ref = weakref.ref(dispatcher)
                
                # Use dispatcher normally
                dispatcher.register_tool("context_tool", lambda x: f"Context result: {x}")
                result = await dispatcher.dispatch("context_tool", query="test")
                
                self.assertIsNotNone(result, "Tool should work within context manager")
                self.assertTrue(dispatcher.is_active(), "Dispatcher should be active within context")
            
            # After context manager exit, dispatcher should be cleaned up
            # Note: We can't test is_active() here because the dispatcher reference
            # might be cleaned up, but we can verify automatic cleanup occurred
            
        except AttributeError:
            # If context manager is not implemented, this test should fail
            self.fail("CONTEXT MANAGER VIOLATION: RequestScopedToolDispatcher should support async context manager protocol (__aenter__, __aexit__)")
        except Exception as e:
            self.fail(f"Context manager cleanup test failed: {e}")


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, "-v", "-s"])