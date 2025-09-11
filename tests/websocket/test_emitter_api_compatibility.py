"""WebSocket Emitter API Compatibility Tests

MISSION CRITICAL: Test API compatibility for Issue #200 SSOT consolidation.
Validates that all existing consumer code can use the consolidated UnifiedWebSocketEmitter
without breaking changes, protecting the Golden Path user experience.

NON-DOCKER TESTS ONLY: These tests run without Docker orchestration requirements.

Test Strategy:
1. Legacy API Compatibility - Verify existing APIs still work
2. Consumer Integration - Test integration with agent code
3. Factory Compatibility - Validate factory methods work for consumers
4. Error Handling Compatibility - Ensure error paths work

Business Impact: Ensures consolidation doesn't break existing chat functionality.
"""

import asyncio
import pytest
import time
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from dataclasses import dataclass

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# SSOT imports
from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter,
    WebSocketEmitterFactory,
    AuthenticationWebSocketEmitter,
    WebSocketEmitterPool
)

# Consumer imports to test compatibility
from netra_backend.app.services.user_execution_context import UserExecutionContext


@dataclass
class MockAgentResult:
    """Mock agent result for testing consumer integration."""
    success: bool
    data: Dict[str, Any]
    execution_time_ms: float = 1000.0
    error: Optional[str] = None


class TestLegacyAPICompatibility(SSotAsyncTestCase):
    """
    Test compatibility with legacy WebSocket emitter APIs.
    
    Validates that existing consumer code can use the SSOT emitter
    without modifications.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "legacy_api_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
    
    async def test_legacy_notify_agent_started_compatibility(self):
        """Test legacy notify_agent_started method works."""
        
        # Legacy API call pattern
        await self.emitter.notify_agent_started(
            agent_name="LegacyAgent",
            metadata={"request_id": "req_123", "priority": "high"},
            context={"thread_id": "thread_456"}
        )
        
        # Verify emission occurred
        self.mock_manager.emit_critical_event.assert_called_once()
        
        call_args = self.mock_manager.emit_critical_event.call_args
        self.assertEqual(call_args[1]['event_type'], 'agent_started')
        self.assertEqual(call_args[1]['data']['agent_name'], 'LegacyAgent')
        self.assertIn('metadata', call_args[1]['data'])
    
    async def test_legacy_notify_agent_thinking_compatibility(self):
        """Test legacy notify_agent_thinking with various parameter combinations."""
        
        # Test with reasoning parameter
        await self.emitter.notify_agent_thinking(
            agent_name="ThinkingAgent",
            reasoning="I need to analyze the user's request and determine the best approach"
        )
        
        # Test with thought parameter (legacy)
        await self.emitter.notify_agent_thinking(
            agent_name="ThinkingAgent",
            thought="Processing user data..."
        )
        
        # Test with step number
        await self.emitter.notify_agent_thinking(
            agent_name="ThinkingAgent",
            reasoning="Step 3: Analyzing results",
            step_number=3
        )
        
        # Verify all calls worked
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 3)
        
        # Check that all were agent_thinking events
        calls = self.mock_manager.emit_critical_event.call_args_list
        for call_args in calls:
            self.assertEqual(call_args[1]['event_type'], 'agent_thinking')
    
    async def test_legacy_notify_tool_methods_compatibility(self):
        """Test legacy tool notification methods."""
        
        # Tool executing
        await self.emitter.notify_tool_executing(
            tool_name="DataAnalyzer",
            metadata={"parameters": {"dataset": "user_data.csv"}}
        )
        
        # Tool completed
        await self.emitter.notify_tool_completed(
            tool_name="DataAnalyzer",
            metadata={"result": {"insights": ["trend1", "trend2"]}, "duration_ms": 2500}
        )
        
        # Verify both calls
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)
        
        calls = self.mock_manager.emit_critical_event.call_args_list
        self.assertEqual(calls[0][1]['event_type'], 'tool_executing')
        self.assertEqual(calls[1][1]['event_type'], 'tool_completed')
    
    async def test_legacy_notify_agent_completed_compatibility(self):
        """Test legacy agent completion notification."""
        
        # Legacy API with separate result parameter
        result_data = {
            "summary": "Analysis completed successfully",
            "recommendations": ["action1", "action2"],
            "confidence": 0.95
        }
        
        await self.emitter.notify_agent_completed(
            agent_name="AnalysisAgent",
            result=result_data,
            execution_time_ms=5000,
            metadata={"status": "success", "error_count": 0}
        )
        
        # Verify emission
        self.mock_manager.emit_critical_event.assert_called_once()
        
        call_args = self.mock_manager.emit_critical_event.call_args
        self.assertEqual(call_args[1]['event_type'], 'agent_completed')
        self.assertEqual(call_args[1]['data']['agent_name'], 'AnalysisAgent')
        self.assertIn('execution_time_ms', call_args[1]['data']['metadata'])
        
        # Result should be merged into metadata
        metadata = call_args[1]['data']['metadata']
        self.assertIn('summary', metadata)
        self.assertIn('recommendations', metadata)
    
    async def test_legacy_generic_emit_compatibility(self):
        """Test legacy generic emit method routing."""
        
        # Test critical event routing
        await self.emitter.emit('agent_started', {'agent_name': 'GenericAgent'})
        await self.emitter.emit('agent_thinking', {'thought': 'Generic thinking'})
        await self.emitter.emit('tool_executing', {'tool': 'GenericTool'})
        await self.emitter.emit('tool_completed', {'tool': 'GenericTool', 'status': 'done'})
        await self.emitter.emit('agent_completed', {'agent_name': 'GenericAgent'})
        
        # Test custom event routing
        await self.emitter.emit('custom_progress', {'progress': 75, 'stage': 'analysis'})
        
        # Verify all emissions
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 6)
        
        # Verify event types
        calls = self.mock_manager.emit_critical_event.call_args_list
        expected_events = [
            'agent_started', 'agent_thinking', 'tool_executing',
            'tool_completed', 'agent_completed', 'custom_progress'
        ]
        
        for i, expected_event in enumerate(expected_events):
            self.assertEqual(calls[i][1]['event_type'], expected_event)
    
    async def test_legacy_error_and_progress_notifications(self):
        """Test legacy error and progress notification methods."""
        
        # Error notification
        await self.emitter.notify_agent_error(
            error="Analysis failed: insufficient data",
            error_code="INSUFFICIENT_DATA",
            retry_suggested=True
        )
        
        # Progress notification
        await self.emitter.notify_progress_update(
            progress=45.5,
            message="Processing dataset...",
            stage="data_ingestion"
        )
        
        # Verify both calls
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)
        
        calls = self.mock_manager.emit_critical_event.call_args_list
        self.assertEqual(calls[0][1]['event_type'], 'agent_error')
        self.assertEqual(calls[1][1]['event_type'], 'progress_update')


class TestConsumerIntegrationCompatibility(SSotAsyncTestCase):
    """
    Test integration with actual consumer patterns.
    
    Validates that real agent and service patterns work with SSOT emitter.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "consumer_integration_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
    
    async def test_agent_execution_pattern_compatibility(self):
        """Test typical agent execution pattern with SSOT emitter."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Simulate typical agent execution flow
        async def simulate_agent_execution(agent_name: str, request: str):
            # Agent started
            await emitter.notify_agent_started(
                agent_name=agent_name,
                metadata={"request": request, "start_time": time.time()}
            )
            
            # Agent thinking
            await emitter.notify_agent_thinking(
                agent_name=agent_name,
                reasoning=f"Analyzing request: {request}"
            )
            
            # Tool execution
            await emitter.notify_tool_executing(
                tool_name="RequestAnalyzer",
                metadata={"input": request}
            )
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            await emitter.notify_tool_completed(
                tool_name="RequestAnalyzer",
                metadata={"analysis": "completed", "insights": ["insight1", "insight2"]}
            )
            
            # Agent completed
            await emitter.notify_agent_completed(
                agent_name=agent_name,
                metadata={"status": "success", "result": "Analysis complete"},
                execution_time_ms=100
            )
        
        # Execute simulation
        await simulate_agent_execution("AnalysisAgent", "Analyze sales data")
        
        # Verify complete execution flow
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 5)
        
        calls = self.mock_manager.emit_critical_event.call_args_list
        expected_sequence = [
            'agent_started', 'agent_thinking', 'tool_executing',
            'tool_completed', 'agent_completed'
        ]
        
        for i, expected_event in enumerate(expected_sequence):
            self.assertEqual(calls[i][1]['event_type'], expected_event)
    
    async def test_bridge_pattern_compatibility(self):
        """Test agent-websocket bridge pattern compatibility."""
        
        # Simulate bridge creating emitter for user context
        bridge_emitter = WebSocketEmitterFactory.create_scoped_emitter(
            manager=self.mock_manager,
            context=self.test_context
        )
        
        # Bridge would call methods like this
        await bridge_emitter.emit_agent_started({
            "agent_name": "BridgeAgent",
            "bridge_context": "user_request_processing"
        })
        
        # Verify bridge pattern works
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        self.assertEqual(call_args[1]['user_id'], self.test_user_id)
        self.assertEqual(call_args[1]['event_type'], 'agent_started')
    
    async def test_transparent_service_pattern_compatibility(self):
        """Test transparent service communication pattern."""
        
        from netra_backend.app.services.websocket.transparent_websocket_events import (
            create_transparent_emitter
        )
        
        # Mock websocket manager creation
        with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create:
            mock_create.return_value = self.mock_manager
            
            # Create transparent emitter as service would
            transparent_emitter = await create_transparent_emitter(self.test_context)
            
            # Service would emit status updates
            await transparent_emitter.notify_custom('service_status', {
                'service': 'DataProcessor',
                'status': 'initializing',
                'progress': 25
            })
            
            await transparent_emitter.notify_custom('service_status', {
                'service': 'DataProcessor',
                'status': 'ready',
                'progress': 100
            })
            
            # Verify transparent pattern works
            self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)
    
    async def test_concurrent_consumer_compatibility(self):
        """Test concurrent consumer pattern compatibility."""
        
        # Create multiple emitters for concurrent consumers
        emitter1 = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id="concurrent_user_1",
            context=SSotMockFactory.create_mock_user_context(user_id="concurrent_user_1")
        )
        
        emitter2 = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id="concurrent_user_2", 
            context=SSotMockFactory.create_mock_user_context(user_id="concurrent_user_2")
        )
        
        # Concurrent consumer operations
        async def consumer_operation(emitter, user_prefix):
            await emitter.notify_agent_started(
                agent_name=f"{user_prefix}Agent",
                metadata={"concurrent": True}
            )
            await emitter.notify_agent_completed(
                agent_name=f"{user_prefix}Agent",
                metadata={"result": f"{user_prefix} completed"}
            )
        
        # Execute concurrent operations
        await asyncio.gather(
            consumer_operation(emitter1, "User1"),
            consumer_operation(emitter2, "User2")
        )
        
        # Verify both consumers worked
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 4)
        
        # Verify user isolation
        calls = self.mock_manager.emit_critical_event.call_args_list
        user_ids = [call[1]['user_id'] for call in calls]
        self.assertIn("concurrent_user_1", user_ids)
        self.assertIn("concurrent_user_2", user_ids)


class TestFactoryCompatibility(SSotAsyncTestCase):
    """
    Test factory method compatibility for consumers.
    
    Validates that existing factory patterns work with SSOT consolidation.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "factory_compat_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
    
    def test_standard_factory_compatibility(self):
        """Test standard factory method works for consumers."""
        
        # Consumer creates emitter via factory
        emitter = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Verify factory produces working emitter
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        self.assertEqual(emitter.user_id, self.test_user_id)
        self.assertEqual(emitter.context, self.test_context)
        self.assertFalse(emitter.performance_mode)  # Default should be False
    
    def test_scoped_factory_compatibility(self):
        """Test scoped factory method for context-aware consumers."""
        
        # Consumer creates scoped emitter
        scoped_emitter = WebSocketEmitterFactory.create_scoped_emitter(
            manager=self.mock_manager,
            context=self.test_context
        )
        
        # Verify scoped factory works
        self.assertIsInstance(scoped_emitter, UnifiedWebSocketEmitter)
        self.assertEqual(scoped_emitter.user_id, self.test_user_id)
        self.assertEqual(scoped_emitter.context, self.test_context)
    
    def test_performance_factory_compatibility(self):
        """Test performance factory for high-throughput consumers."""
        
        # Consumer creates performance emitter
        perf_emitter = WebSocketEmitterFactory.create_performance_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Verify performance factory works
        self.assertIsInstance(perf_emitter, UnifiedWebSocketEmitter)
        self.assertTrue(perf_emitter.performance_mode)
    
    def test_auth_factory_compatibility(self):
        """Test auth factory for authentication consumers."""
        
        # Consumer creates auth emitter
        auth_emitter = WebSocketEmitterFactory.create_auth_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Verify auth factory works
        self.assertIsInstance(auth_emitter, AuthenticationWebSocketEmitter)
        self.assertIsInstance(auth_emitter, UnifiedWebSocketEmitter)
    
    def test_legacy_parameter_compatibility(self):
        """Test legacy parameter names work in factory."""
        
        # Test legacy websocket_manager parameter
        emitter = UnifiedWebSocketEmitter(
            websocket_manager=self.mock_manager,  # Legacy parameter name
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Verify legacy parameter works
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        self.assertEqual(emitter.manager, self.mock_manager)
        self.assertEqual(emitter.user_id, self.test_user_id)


class TestErrorHandlingCompatibility(SSotAsyncTestCase):
    """
    Test error handling compatibility for consumers.
    
    Validates that error scenarios work consistently with SSOT emitter.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "error_compat_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
    
    async def test_emission_failure_compatibility(self):
        """Test emission failure handling compatibility."""
        
        # Configure mock to fail
        self.mock_manager.emit_critical_event.side_effect = Exception("Network error")
        
        # Consumer should be able to handle emission failures
        try:
            await self.emitter.emit_agent_started({'agent_name': 'FailAgent'})
            # SSOT emitter should handle retries internally
        except Exception as e:
            # If exception bubbles up, it should be informative
            self.assertIn("Network error", str(e))
    
    async def test_connection_failure_compatibility(self):
        """Test connection failure handling compatibility."""
        
        # Configure connection as inactive
        self.mock_manager.is_connection_active.return_value = False
        self.mock_manager.get_connection_health.return_value = {
            'has_active_connections': False,
            'last_ping': None
        }
        
        # Consumer emission should handle dead connections gracefully
        result = await self.emitter.emit_agent_started({'agent_name': 'DeadConnAgent'})
        
        # Should not raise exception but return False
        self.assertFalse(result)
    
    async def test_invalid_context_compatibility(self):
        """Test invalid context handling compatibility."""
        
        # Create emitter with invalid context
        invalid_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=None  # Invalid context
        )
        
        # Should still work without context
        await invalid_emitter.emit_agent_started({'agent_name': 'NoContextAgent'})
        
        # Verify emission worked
        self.mock_manager.emit_critical_event.assert_called_once()
    
    def test_missing_parameters_compatibility(self):
        """Test missing parameter handling compatibility."""
        
        # Test missing manager parameter
        with self.assertRaises(ValueError) as context:
            UnifiedWebSocketEmitter(
                manager=None,
                user_id=self.test_user_id,
                context=self.test_context
            )
        
        self.assertIn("manager", str(context.exception))
        
        # Test missing user_id parameter
        with self.assertRaises(ValueError) as context:
            UnifiedWebSocketEmitter(
                manager=self.mock_manager,
                user_id=None,
                context=None
            )
        
        self.assertIn("user_id", str(context.exception))
    
    async def test_retry_exhaustion_compatibility(self):
        """Test retry exhaustion handling compatibility."""
        
        # Configure retries to always fail
        call_count = 0
        
        async def failing_emit(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception(f"Persistent failure {call_count}")
        
        self.mock_manager.emit_critical_event.side_effect = failing_emit
        
        # Consumer should handle retry exhaustion gracefully
        result = await self.emitter.emit_agent_started({'agent_name': 'RetryExhaustAgent'})
        
        # Should return False after retries exhausted
        self.assertFalse(result)
        
        # Should have attempted retries
        self.assertGreater(call_count, 1)


class TestPoolCompatibility(SSotAsyncTestCase):
    """
    Test WebSocket emitter pool compatibility.
    
    Validates that pool patterns work with SSOT consolidation.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.pool = WebSocketEmitterPool(manager=self.mock_manager, max_size=5)
    
    async def test_pool_acquire_release_compatibility(self):
        """Test pool acquire/release pattern compatibility."""
        
        test_user_id = "pool_user_1"
        test_context = SSotMockFactory.create_mock_user_context(user_id=test_user_id)
        
        # Consumer acquires emitter from pool
        emitter = await self.pool.acquire(
            user_id=test_user_id,
            context=test_context
        )
        
        # Verify emitter is SSOT type
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        
        # Consumer uses emitter
        await emitter.emit_agent_started({'agent_name': 'PoolAgent'})
        
        # Consumer releases emitter back to pool
        await self.pool.release(emitter)
        
        # Verify emission worked
        self.mock_manager.emit_critical_event.assert_called_once()
    
    async def test_pool_reuse_compatibility(self):
        """Test pool emitter reuse compatibility."""
        
        test_user_id = "pool_reuse_user"
        test_context = SSotMockFactory.create_mock_user_context(user_id=test_user_id)
        
        # First acquisition
        emitter1 = await self.pool.acquire(
            user_id=test_user_id,
            context=test_context
        )
        
        await self.pool.release(emitter1)
        
        # Second acquisition (should reuse)
        emitter2 = await self.pool.acquire(
            user_id=test_user_id,
            context=test_context
        )
        
        # Should be same instance (reused)
        self.assertIs(emitter1, emitter2)
        
        await self.pool.release(emitter2)
    
    async def test_pool_statistics_compatibility(self):
        """Test pool statistics compatibility."""
        
        # Get initial stats
        stats = self.pool.get_statistics()
        
        self.assertIn('pool_size', stats)
        self.assertIn('acquisitions', stats)
        self.assertIn('releases', stats)
        self.assertEqual(stats['pool_size'], 0)  # Empty pool
        
        # Acquire and check stats
        test_context = SSotMockFactory.create_mock_user_context(user_id="stats_user")
        emitter = await self.pool.acquire(user_id="stats_user", context=test_context)
        
        stats = self.pool.get_statistics()
        self.assertEqual(stats['pool_size'], 1)
        self.assertEqual(stats['acquisitions'], 1)
        
        await self.pool.release(emitter)
        
        stats = self.pool.get_statistics()
        self.assertEqual(stats['releases'], 1)


if __name__ == '__main__':
    # Run tests directly
    pytest.main([__file__, '-v', '--tb=short'])