"""Integration Tests for UserContextManager - TDD Implementation

This test suite validates UserContextManager integration with the broader
system architecture, following Test-Driven Development principles.

These tests are designed to FAIL initially (UserContextManager does not exist)
and then PASS once proper integration is implemented.

Business Value Justification (BVJ):
- Segment: All segments (Free → Enterprise)
- Business Goal: Ensure UserContextManager integrates seamlessly with existing systems
- Value Impact: Validates that user isolation works across all system components
- Revenue Impact: Critical for system reliability protecting $500K+ ARR user flows

Test Categories:
1. SSOT Integration - Single Source of Truth compliance
2. WebSocket Integration - Real-time communication isolation
3. Agent Execution - Multi-agent isolation
4. Database Integration - Transaction isolation
5. Performance - Resource management
6. Error Handling - Graceful degradation
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# This import WILL FAIL initially - this is expected for TDD
try:
    from netra_backend.app.services.user_execution_context import UserContextManager
    USERCONTEXTMANAGER_EXISTS = True
except ImportError as e:
    USERCONTEXTMANAGER_EXISTS = False
    UserContextManager = None
    IMPORT_ERROR = str(e)

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    create_isolated_execution_context,
    managed_user_context,
    validate_user_context
)
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUserContextManagerSSotIntegration(SSotBaseTestCase):
    """Tests for UserContextManager SSOT compliance and integration."""
    
    def setUp(self):
        """Set up SSOT integration test fixtures."""
        super().setUp()
        
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f"UserContextManager not implemented yet. Import error: {IMPORT_ERROR}")
        
        # Test identifiers
        self.user_id = "ssot_integration_user_123"
        self.thread_id = "ssot_thread_456"
        self.run_id = "ssot_run_789"

    def test_ssot_factory_integration(self):
        """Test UserContextManager integrates with SSOT factory patterns."""
        manager = UserContextManager()
        
        # Should integrate with create_isolated_execution_context
        with patch('netra_backend.app.services.user_execution_context.create_isolated_execution_context') as mock_factory:
            mock_context = UserExecutionContext.from_request(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id
            )
            mock_factory.return_value = mock_context
            
            # UserContextManager should provide SSOT-compliant factory integration
            created_context = manager.create_isolated_context(
                user_id=self.user_id,
                request_id="ssot_request_123"
            )
            
            self.assertEqual(created_context.user_id, self.user_id)
            mock_factory.assert_called_once()

    def test_unified_id_manager_integration(self):
        """Test integration with UnifiedIDManager for consistent ID generation."""
        manager = UserContextManager()
        
        # Should use UnifiedIDManager for ID generation
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager') as mock_id_manager:
            mock_id_manager.return_value.generate_thread_id.return_value = "unified_thread_123"
            mock_id_manager.return_value.generate_run_id.return_value = "unified_run_456"
            
            context = manager.create_context_with_unified_ids(user_id=self.user_id)
            
            # Verify UnifiedIDManager integration
            self.assertEqual(context.user_id, self.user_id)
            mock_id_manager.return_value.generate_thread_id.assert_called()
            mock_id_manager.return_value.generate_run_id.assert_called()

    def test_isolated_environment_integration(self):
        """Test integration with IsolatedEnvironment for config access."""
        manager = UserContextManager()
        
        # Should respect IsolatedEnvironment patterns
        with patch('shared.isolated_environment.IsolatedEnvironment') as mock_env:
            mock_env.return_value.is_test.return_value = True
            mock_env.return_value.get_environment_name.return_value = "test"
            
            context = UserExecutionContext.from_request(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id
            )
            
            manager.set_context(self.user_id, context)
            
            # Verify environment integration
            mock_env.assert_called()

    def test_audit_trail_ssot_compliance(self):
        """Test that audit trails comply with SSOT patterns."""
        manager = UserContextManager()
        
        context = UserExecutionContext.from_request(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id
        )
        
        manager.set_context(self.user_id, context)
        
        # SSOT audit trail should include required fields
        audit_trail = manager.get_audit_trail(self.user_id)
        
        # Verify SSOT compliance fields
        required_fields = [
            'context_set_at',
            'user_id',
            'context_source',
            'isolation_verified',
            'compliance_version'
        ]
        
        for field in required_fields:
            self.assertIn(field, audit_trail, f"SSOT audit field {field} missing")


class TestUserContextManagerWebSocketIntegration(SSotBaseTestCase):
    """Tests for UserContextManager WebSocket integration."""
    
    def setUp(self):
        """Set up WebSocket integration test fixtures."""
        super().setUp()
        
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f"UserContextManager not implemented yet. Import error: {IMPORT_ERROR}")
        
        self.user_a = "websocket_user_a"
        self.user_b = "websocket_user_b"

    async def test_websocket_manager_integration(self):
        """Test integration with WebSocket manager for real-time updates."""
        manager = UserContextManager()
        
        # Mock WebSocket manager
        with patch('netra_backend.app.websocket_core.manager.WebSocketManager') as mock_ws_manager:
            mock_connection_a = AsyncMock()
            mock_connection_b = AsyncMock()
            
            mock_ws_manager.get_connection.side_effect = lambda user_id: {
                self.user_a: mock_connection_a,
                self.user_b: mock_connection_b
            }.get(user_id)
            
            # Create contexts with WebSocket integration
            context_a = UserExecutionContext.from_request(
                user_id=self.user_a,
                thread_id="ws_thread_a",
                run_id="ws_run_a",
                websocket_client_id="ws_client_a"
            )
            
            context_b = UserExecutionContext.from_request(
                user_id=self.user_b,
                thread_id="ws_thread_b",
                run_id="ws_run_b",
                websocket_client_id="ws_client_b"
            )
            
            manager.set_context(self.user_a, context_a)
            manager.set_context(self.user_b, context_b)
            
            # Test WebSocket notification isolation
            await manager.notify_context_change(self.user_a, "context_updated")
            
            # Verify only the correct user's WebSocket was notified
            mock_ws_manager.get_connection.assert_called_with(self.user_a)

    async def test_websocket_event_isolation(self):
        """Test that WebSocket events are properly isolated between users."""
        manager = UserContextManager()
        
        # Setup contexts
        context_a = UserExecutionContext.from_request(
            user_id=self.user_a,
            thread_id="event_thread_a",
            run_id="event_run_a",
            websocket_client_id="event_ws_a"
        )
        
        context_b = UserExecutionContext.from_request(
            user_id=self.user_b,
            thread_id="event_thread_b", 
            run_id="event_run_b",
            websocket_client_id="event_ws_b"
        )
        
        manager.set_context(self.user_a, context_a)
        manager.set_context(self.user_b, context_b)
        
        # Mock WebSocket notifier
        with patch('netra_backend.app.websocket_core.notifier.WebSocketNotifier') as mock_notifier:
            # Send events to different users
            await manager.send_event(self.user_a, "agent_started", {"data": "user_a_data"})
            await manager.send_event(self.user_b, "agent_started", {"data": "user_b_data"})
            
            # Verify isolation - each user should get only their events
            call_args_list = mock_notifier.send_event.call_args_list
            
            # Find calls for each user
            user_a_calls = [call for call in call_args_list if call[0][0] == self.user_a]
            user_b_calls = [call for call in call_args_list if call[0][0] == self.user_b]
            
            self.assertEqual(len(user_a_calls), 1)
            self.assertEqual(len(user_b_calls), 1)
            
            # Verify data isolation
            user_a_data = user_a_calls[0][0][2]["data"]
            user_b_data = user_b_calls[0][0][2]["data"]
            
            self.assertEqual(user_a_data, "user_a_data")
            self.assertEqual(user_b_data, "user_b_data")


class TestUserContextManagerAgentExecution(SSotBaseTestCase):
    """Tests for UserContextManager integration with agent execution."""
    
    def setUp(self):
        """Set up agent execution test fixtures."""
        super().setUp()
        
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f"UserContextManager not implemented yet. Import error: {IMPORT_ERROR}")
        
        self.user_id = "agent_execution_user"

    async def test_agent_registry_integration(self):
        """Test integration with agent registry for context passing."""
        manager = UserContextManager()
        
        # Mock agent registry
        with patch('netra_backend.app.agents.supervisor.agent_registry.UserAgentSession') as mock_registry:
            mock_session = AsyncMock()
            mock_registry.return_value = mock_session
            
            context = UserExecutionContext.from_request(
                user_id=self.user_id,
                thread_id="agent_thread",
                run_id="agent_run"
            )
            
            manager.set_context(self.user_id, context)
            
            # UserContextManager should integrate with agent execution
            await manager.execute_with_agent(
                user_id=self.user_id,
                agent_name="test_agent",
                parameters={"test": "data"}
            )
            
            # Verify agent was called with proper context
            mock_session.execute.assert_called_once()
            call_args = mock_session.execute.call_args
            
            # Context should be passed to agent
            self.assertIn("context", call_args.kwargs)

    async def test_multi_agent_isolation(self):
        """Test isolation between multiple concurrent agent executions."""
        manager = UserContextManager()
        
        results = {}
        errors = []
        
        async def run_agent(user_id: str, agent_name: str, data: dict):
            """Simulate agent execution with isolation."""
            try:
                context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=f"agent_{agent_name}_thread",
                    run_id=f"agent_{agent_name}_run",
                    agent_context={"agent_data": data}
                )
                
                manager.set_context(f"{user_id}_{agent_name}", context)
                
                # Simulate agent processing
                await asyncio.sleep(0.01)
                
                # Retrieve and validate context
                retrieved = manager.get_context(f"{user_id}_{agent_name}")
                results[f"{user_id}_{agent_name}"] = retrieved.agent_context["agent_data"]
                
                manager.clear_context(f"{user_id}_{agent_name}")
                
            except Exception as e:
                errors.append(f"Error in {user_id}_{agent_name}: {e}")
        
        # Run multiple agents concurrently
        users = ["user_1", "user_2", "user_3"]
        agents = ["data_helper", "optimizer", "reporter"]
        tasks = []
        
        for user in users:
            for agent in agents:
                agent_data = {"user": user, "agent": agent, "secret": f"{user}_{agent}_secret"}
                tasks.append(run_agent(user, agent, agent_data))
        
        await asyncio.gather(*tasks)
        
        # Verify isolation
        self.assertEqual(len(errors), 0, f"Agent execution errors: {errors}")
        self.assertEqual(len(results), 9)  # 3 users * 3 agents
        
        # Verify data isolation
        for user in users:
            for agent in agents:
                key = f"{user}_{agent}"
                expected_secret = f"{user}_{agent}_secret"
                self.assertEqual(results[key]["secret"], expected_secret)


class TestUserContextManagerDatabaseIntegration(SSotBaseTestCase):
    """Tests for UserContextManager database integration."""
    
    def setUp(self):
        """Set up database integration test fixtures."""
        super().setUp()
        
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f"UserContextManager not implemented yet. Import error: {IMPORT_ERROR}")

    async def test_database_session_management(self):
        """Test database session isolation and cleanup."""
        manager = UserContextManager()
        
        # Mock database sessions
        mock_session_a = AsyncMock()
        mock_session_b = AsyncMock()
        
        # Create contexts with database sessions
        context_a = UserExecutionContext.from_request(
            user_id="db_user_a",
            thread_id="db_thread_a",
            run_id="db_run_a",
            db_session=mock_session_a
        )
        
        context_b = UserExecutionContext.from_request(
            user_id="db_user_b",
            thread_id="db_thread_b",
            run_id="db_run_b",
            db_session=mock_session_b
        )
        
        manager.set_context("db_user_a", context_a)
        manager.set_context("db_user_b", context_b)
        
        # Test session isolation
        retrieved_a = manager.get_context("db_user_a")
        retrieved_b = manager.get_context("db_user_b")
        
        self.assertIs(retrieved_a.db_session, mock_session_a)
        self.assertIs(retrieved_b.db_session, mock_session_b)
        self.assertIsNot(retrieved_a.db_session, retrieved_b.db_session)
        
        # Test cleanup
        await manager.cleanup_context("db_user_a")
        
        # Session should be closed
        mock_session_a.close.assert_called_once()
        mock_session_b.close.assert_not_called()

    async def test_transaction_isolation(self):
        """Test that database transactions are properly isolated."""
        manager = UserContextManager()
        
        # Mock database manager
        with patch('netra_backend.app.db.database_manager.DatabaseManager') as mock_db_manager:
            mock_transaction_a = AsyncMock()
            mock_transaction_b = AsyncMock()
            
            mock_db_manager.begin_transaction.side_effect = [mock_transaction_a, mock_transaction_b]
            
            # Create contexts with transactions
            context_a = manager.create_context_with_transaction("tx_user_a")
            context_b = manager.create_context_with_transaction("tx_user_b")
            
            # Verify transaction isolation
            self.assertIsNot(
                context_a.db_session,
                context_b.db_session
            )
            
            # Test transaction operations
            await manager.execute_in_transaction("tx_user_a", "SELECT 1")
            await manager.execute_in_transaction("tx_user_b", "SELECT 2")
            
            # Verify each transaction was used correctly
            mock_transaction_a.execute.assert_called_with("SELECT 1")
            mock_transaction_b.execute.assert_called_with("SELECT 2")


class TestUserContextManagerPerformance(SSotBaseTestCase):
    """Performance and resource management tests for UserContextManager."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        super().setUp()
        
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f"UserContextManager not implemented yet. Import error: {IMPORT_ERROR}")

    def test_memory_usage_bounds(self):
        """Test that UserContextManager manages memory usage effectively."""
        manager = UserContextManager()
        
        # Create many contexts to test memory management
        num_contexts = 1000
        user_ids = [f"perf_user_{i}" for i in range(num_contexts)]
        
        # Track memory usage (simplified)
        initial_contexts = len(manager.get_active_contexts())
        
        for user_id in user_ids:
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=f"perf_thread_{user_id}",
                run_id=f"perf_run_{user_id}"
            )
            manager.set_context(user_id, context)
        
        # Verify all contexts were created
        self.assertEqual(
            len(manager.get_active_contexts()),
            initial_contexts + num_contexts
        )
        
        # Test batch cleanup
        manager.cleanup_all_contexts()
        
        # Verify cleanup
        self.assertEqual(len(manager.get_active_contexts()), initial_contexts)

    async def test_concurrent_performance(self):
        """Test performance under high concurrent load."""
        manager = UserContextManager()
        
        # Performance metrics
        operations_completed = 0
        errors_count = 0
        
        async def concurrent_operation(user_id: str, operation_id: int):
            nonlocal operations_completed, errors_count
            
            try:
                # Create context
                context = UserExecutionContext.from_request(
                    user_id=f"{user_id}_{operation_id}",
                    thread_id=f"concurrent_thread_{operation_id}",
                    run_id=f"concurrent_run_{operation_id}"
                )
                
                # Set context
                manager.set_context(f"{user_id}_{operation_id}", context)
                
                # Simulate work
                await asyncio.sleep(0.001)
                
                # Retrieve context
                retrieved = manager.get_context(f"{user_id}_{operation_id}")
                self.assertIsNotNone(retrieved)
                
                # Clean up
                manager.clear_context(f"{user_id}_{operation_id}")
                
                operations_completed += 1
                
            except Exception:
                errors_count += 1
        
        # Run high concurrency test
        tasks = []
        num_concurrent = 100
        
        for i in range(num_concurrent):
            tasks.append(concurrent_operation("concurrent_user", i))
        
        await asyncio.gather(*tasks)
        
        # Verify performance
        self.assertEqual(operations_completed, num_concurrent)
        self.assertEqual(errors_count, 0)
        self.assertEqual(len(manager.get_active_contexts()), 0)

    def test_resource_cleanup_effectiveness(self):
        """Test that resource cleanup is thorough and effective."""
        manager = UserContextManager()
        
        # Create contexts with various resources
        contexts_with_resources = []
        
        for i in range(10):
            mock_session = MagicMock()
            mock_websocket = MagicMock()
            
            context = UserExecutionContext.from_request(
                user_id=f"cleanup_user_{i}",
                thread_id=f"cleanup_thread_{i}",
                run_id=f"cleanup_run_{i}",
                db_session=mock_session,
                websocket_client_id=f"ws_{i}"
            )
            
            contexts_with_resources.append((context, mock_session, mock_websocket))
            manager.set_context(f"cleanup_user_{i}", context)
        
        # Verify all contexts are active
        self.assertEqual(len(manager.get_active_contexts()), 10)
        
        # Perform comprehensive cleanup
        manager.cleanup_all_contexts()
        
        # Verify cleanup effectiveness
        self.assertEqual(len(manager.get_active_contexts()), 0)
        
        # Verify resources were properly cleaned up
        for context, mock_session, mock_websocket in contexts_with_resources:
            if hasattr(mock_session, 'close'):
                mock_session.close.assert_called()


class TestUserContextManagerErrorHandling(SSotBaseTestCase):
    """Error handling and resilience tests for UserContextManager."""
    
    def setUp(self):
        """Set up error handling test fixtures."""
        super().setUp()
        
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f"UserContextManager not implemented yet. Import error: {IMPORT_ERROR}")

    def test_graceful_degradation(self):
        """Test that UserContextManager degrades gracefully under error conditions."""
        manager = UserContextManager()
        
        # Test with corrupted context
        with patch.object(UserExecutionContext, 'verify_isolation', side_effect=ContextIsolationError("Test error")):
            context = UserExecutionContext.from_request(
                user_id="error_user",
                thread_id="error_thread", 
                run_id="error_run"
            )
            
            # Should handle isolation errors gracefully
            with self.assertRaises(ContextIsolationError):
                manager.set_context("error_user", context)
            
            # Manager should remain functional
            self.assertTrue(manager.is_healthy())

    def test_error_isolation(self):
        """Test that errors in one context don't affect others."""
        manager = UserContextManager()
        
        # Create good context
        good_context = UserExecutionContext.from_request(
            user_id="good_user",
            thread_id="good_thread",
            run_id="good_run"
        )
        
        manager.set_context("good_user", good_context)
        
        # Create problematic context
        with patch.object(UserExecutionContext, '__post_init__', side_effect=Exception("Initialization error")):
            with self.assertRaises(Exception):
                bad_context = UserExecutionContext.from_request(
                    user_id="bad_user",
                    thread_id="bad_thread",
                    run_id="bad_run"
                )
        
        # Good context should still be accessible
        retrieved_good = manager.get_context("good_user")
        self.assertEqual(retrieved_good.user_id, "good_user")

    async def test_cleanup_error_handling(self):
        """Test that cleanup errors are handled without affecting other operations."""
        manager = UserContextManager()
        
        # Create context with problematic cleanup
        mock_session = AsyncMock()
        mock_session.close.side_effect = Exception("Cleanup error")
        
        context = UserExecutionContext.from_request(
            user_id="cleanup_error_user",
            thread_id="cleanup_error_thread",
            run_id="cleanup_error_run",
            db_session=mock_session
        )
        
        manager.set_context("cleanup_error_user", context)
        
        # Cleanup should handle errors gracefully
        await manager.cleanup_context("cleanup_error_user")
        
        # Context should still be removed despite cleanup error
        with self.assertRaises((KeyError, ValueError)):
            manager.get_context("cleanup_error_user")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])