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
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter, WebSocketEmitterFactory, AuthenticationWebSocketEmitter, WebSocketEmitterPool
from netra_backend.app.services.user_execution_context import UserExecutionContext

@dataclass
class MockAgentResult:
    """Mock agent result for testing consumer integration."""
    success: bool
    data: Dict[str, Any]
    execution_time_ms: float = 1000.0
    error: Optional[str] = None

@pytest.mark.websocket
class LegacyAPICompatibilityTests(SSotAsyncTestCase):
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
        self.test_user_id = 'legacy_api_user'
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        self.emitter = UnifiedWebSocketEmitter(manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)

    async def test_legacy_notify_agent_started_compatibility(self):
        """Test legacy notify_agent_started method works."""
        await self.emitter.notify_agent_started(agent_name='LegacyAgent', metadata={'request_id': 'req_123', 'priority': 'high'}, context={'thread_id': 'thread_456'})
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        self.assertEqual(call_args[1]['event_type'], 'agent_started')
        self.assertEqual(call_args[1]['data']['agent_name'], 'LegacyAgent')
        self.assertIn('metadata', call_args[1]['data'])

    async def test_legacy_notify_agent_thinking_compatibility(self):
        """Test legacy notify_agent_thinking with various parameter combinations."""
        await self.emitter.notify_agent_thinking(agent_name='ThinkingAgent', reasoning="I need to analyze the user's request and determine the best approach")
        await self.emitter.notify_agent_thinking(agent_name='ThinkingAgent', thought='Processing user data...')
        await self.emitter.notify_agent_thinking(agent_name='ThinkingAgent', reasoning='Step 3: Analyzing results', step_number=3)
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 3)
        calls = self.mock_manager.emit_critical_event.call_args_list
        for call_args in calls:
            self.assertEqual(call_args[1]['event_type'], 'agent_thinking')

    async def test_legacy_notify_tool_methods_compatibility(self):
        """Test legacy tool notification methods."""
        await self.emitter.notify_tool_executing(tool_name='DataAnalyzer', metadata={'parameters': {'dataset': 'user_data.csv'}})
        await self.emitter.notify_tool_completed(tool_name='DataAnalyzer', metadata={'result': {'insights': ['trend1', 'trend2']}, 'duration_ms': 2500})
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)
        calls = self.mock_manager.emit_critical_event.call_args_list
        self.assertEqual(calls[0][1]['event_type'], 'tool_executing')
        self.assertEqual(calls[1][1]['event_type'], 'tool_completed')

    async def test_legacy_notify_agent_completed_compatibility(self):
        """Test legacy agent completion notification."""
        result_data = {'summary': 'Analysis completed successfully', 'recommendations': ['action1', 'action2'], 'confidence': 0.95}
        await self.emitter.notify_agent_completed(agent_name='AnalysisAgent', result=result_data, execution_time_ms=5000, metadata={'status': 'success', 'error_count': 0})
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        self.assertEqual(call_args[1]['event_type'], 'agent_completed')
        self.assertEqual(call_args[1]['data']['agent_name'], 'AnalysisAgent')
        self.assertIn('execution_time_ms', call_args[1]['data']['metadata'])
        metadata = call_args[1]['data']['metadata']
        self.assertIn('summary', metadata)
        self.assertIn('recommendations', metadata)

    async def test_legacy_generic_emit_compatibility(self):
        """Test legacy generic emit method routing."""
        await self.emitter.emit('agent_started', {'agent_name': 'GenericAgent'})
        await self.emitter.emit('agent_thinking', {'thought': 'Generic thinking'})
        await self.emitter.emit('tool_executing', {'tool': 'GenericTool'})
        await self.emitter.emit('tool_completed', {'tool': 'GenericTool', 'status': 'done'})
        await self.emitter.emit('agent_completed', {'agent_name': 'GenericAgent'})
        await self.emitter.emit('custom_progress', {'progress': 75, 'stage': 'analysis'})
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 6)
        calls = self.mock_manager.emit_critical_event.call_args_list
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed', 'custom_progress']
        for i, expected_event in enumerate(expected_events):
            self.assertEqual(calls[i][1]['event_type'], expected_event)

    async def test_legacy_error_and_progress_notifications(self):
        """Test legacy error and progress notification methods."""
        await self.emitter.notify_agent_error(error='Analysis failed: insufficient data', error_code='INSUFFICIENT_DATA', retry_suggested=True)
        await self.emitter.notify_progress_update(progress=45.5, message='Processing dataset...', stage='data_ingestion')
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)
        calls = self.mock_manager.emit_critical_event.call_args_list
        self.assertEqual(calls[0][1]['event_type'], 'agent_error')
        self.assertEqual(calls[1][1]['event_type'], 'progress_update')

@pytest.mark.websocket
class ConsumerIntegrationCompatibilityTests(SSotAsyncTestCase):
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
        self.test_user_id = 'consumer_integration_user'
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)

    async def test_agent_execution_pattern_compatibility(self):
        """Test typical agent execution pattern with SSOT emitter."""
        emitter = UnifiedWebSocketEmitter(manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)

        async def simulate_agent_execution(agent_name: str, request: str):
            await emitter.notify_agent_started(agent_name=agent_name, metadata={'request': request, 'start_time': time.time()})
            await emitter.notify_agent_thinking(agent_name=agent_name, reasoning=f'Analyzing request: {request}')
            await emitter.notify_tool_executing(tool_name='RequestAnalyzer', metadata={'input': request})
            await asyncio.sleep(0.01)
            await emitter.notify_tool_completed(tool_name='RequestAnalyzer', metadata={'analysis': 'completed', 'insights': ['insight1', 'insight2']})
            await emitter.notify_agent_completed(agent_name=agent_name, metadata={'status': 'success', 'result': 'Analysis complete'}, execution_time_ms=100)
        await simulate_agent_execution('AnalysisAgent', 'Analyze sales data')
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 5)
        calls = self.mock_manager.emit_critical_event.call_args_list
        expected_sequence = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for i, expected_event in enumerate(expected_sequence):
            self.assertEqual(calls[i][1]['event_type'], expected_event)

    async def test_bridge_pattern_compatibility(self):
        """Test agent-websocket bridge pattern compatibility."""
        bridge_emitter = WebSocketEmitterFactory.create_scoped_emitter(manager=self.mock_manager, context=self.test_context)
        await bridge_emitter.emit_agent_started({'agent_name': 'BridgeAgent', 'bridge_context': 'user_request_processing'})
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        self.assertEqual(call_args[1]['user_id'], self.test_user_id)
        self.assertEqual(call_args[1]['event_type'], 'agent_started')

    async def test_transparent_service_pattern_compatibility(self):
        """Test transparent service communication pattern."""
        from netra_backend.app.services.websocket.transparent_websocket_events import create_transparent_emitter
        with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create:
            mock_create.return_value = self.mock_manager
            transparent_emitter = await create_transparent_emitter(self.test_context)
            await transparent_emitter.notify_custom('service_status', {'service': 'DataProcessor', 'status': 'initializing', 'progress': 25})
            await transparent_emitter.notify_custom('service_status', {'service': 'DataProcessor', 'status': 'ready', 'progress': 100})
            self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)

    async def test_concurrent_consumer_compatibility(self):
        """Test concurrent consumer pattern compatibility."""
        emitter1 = WebSocketEmitterFactory.create_emitter(manager=self.mock_manager, user_id='concurrent_user_1', context=SSotMockFactory.create_mock_user_context(user_id='concurrent_user_1'))
        emitter2 = WebSocketEmitterFactory.create_emitter(manager=self.mock_manager, user_id='concurrent_user_2', context=SSotMockFactory.create_mock_user_context(user_id='concurrent_user_2'))

        async def consumer_operation(emitter, user_prefix):
            await emitter.notify_agent_started(agent_name=f'{user_prefix}Agent', metadata={'concurrent': True})
            await emitter.notify_agent_completed(agent_name=f'{user_prefix}Agent', metadata={'result': f'{user_prefix} completed'})
        await asyncio.gather(consumer_operation(emitter1, 'User1'), consumer_operation(emitter2, 'User2'))
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 4)
        calls = self.mock_manager.emit_critical_event.call_args_list
        user_ids = [call[1]['user_id'] for call in calls]
        self.assertIn('concurrent_user_1', user_ids)
        self.assertIn('concurrent_user_2', user_ids)

@pytest.mark.websocket
class FactoryCompatibilityTests(SSotAsyncTestCase):
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
        self.test_user_id = 'factory_compat_user'
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)

    def test_standard_factory_compatibility(self):
        """Test standard factory method works for consumers."""
        emitter = WebSocketEmitterFactory.create_emitter(manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        self.assertEqual(emitter.user_id, self.test_user_id)
        self.assertEqual(emitter.context, self.test_context)
        self.assertFalse(emitter.performance_mode)

    def test_scoped_factory_compatibility(self):
        """Test scoped factory method for context-aware consumers."""
        scoped_emitter = WebSocketEmitterFactory.create_scoped_emitter(manager=self.mock_manager, context=self.test_context)
        self.assertIsInstance(scoped_emitter, UnifiedWebSocketEmitter)
        self.assertEqual(scoped_emitter.user_id, self.test_user_id)
        self.assertEqual(scoped_emitter.context, self.test_context)

    def test_performance_factory_compatibility(self):
        """Test performance factory for high-throughput consumers."""
        perf_emitter = WebSocketEmitterFactory.create_performance_emitter(manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)
        self.assertIsInstance(perf_emitter, UnifiedWebSocketEmitter)
        self.assertTrue(perf_emitter.performance_mode)

    def test_auth_factory_compatibility(self):
        """Test auth factory for authentication consumers."""
        auth_emitter = WebSocketEmitterFactory.create_auth_emitter(manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)
        self.assertIsInstance(auth_emitter, AuthenticationWebSocketEmitter)
        self.assertIsInstance(auth_emitter, UnifiedWebSocketEmitter)

    def test_legacy_parameter_compatibility(self):
        """Test legacy parameter names work in factory."""
        emitter = UnifiedWebSocketEmitter(websocket_manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        self.assertEqual(emitter.manager, self.mock_manager)
        self.assertEqual(emitter.user_id, self.test_user_id)

@pytest.mark.websocket
class ErrorHandlingCompatibilityTests(SSotAsyncTestCase):
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
        self.test_user_id = 'error_compat_user'
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        self.emitter = UnifiedWebSocketEmitter(manager=self.mock_manager, user_id=self.test_user_id, context=self.test_context)

    async def test_emission_failure_compatibility(self):
        """Test emission failure handling compatibility."""
        self.mock_manager.emit_critical_event.side_effect = Exception('Network error')
        try:
            await self.emitter.emit_agent_started({'agent_name': 'FailAgent'})
        except Exception as e:
            self.assertIn('Network error', str(e))

    async def test_connection_failure_compatibility(self):
        """Test connection failure handling compatibility."""
        self.mock_manager.is_connection_active.return_value = False
        self.mock_manager.get_connection_health.return_value = {'has_active_connections': False, 'last_ping': None}
        result = await self.emitter.emit_agent_started({'agent_name': 'DeadConnAgent'})
        self.assertFalse(result)

    async def test_invalid_context_compatibility(self):
        """Test invalid context handling compatibility."""
        invalid_emitter = UnifiedWebSocketEmitter(manager=self.mock_manager, user_id=self.test_user_id, context=None)
        await invalid_emitter.emit_agent_started({'agent_name': 'NoContextAgent'})
        self.mock_manager.emit_critical_event.assert_called_once()

    def test_missing_parameters_compatibility(self):
        """Test missing parameter handling compatibility."""
        with self.assertRaises(ValueError) as context:
            UnifiedWebSocketEmitter(manager=None, user_id=self.test_user_id, context=self.test_context)
        self.assertIn('manager', str(context.exception))
        with self.assertRaises(ValueError) as context:
            UnifiedWebSocketEmitter(manager=self.mock_manager, user_id=None, context=None)
        self.assertIn('user_id', str(context.exception))

    async def test_retry_exhaustion_compatibility(self):
        """Test retry exhaustion handling compatibility."""
        call_count = 0

        async def failing_emit(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception(f'Persistent failure {call_count}')
        self.mock_manager.emit_critical_event.side_effect = failing_emit
        result = await self.emitter.emit_agent_started({'agent_name': 'RetryExhaustAgent'})
        self.assertFalse(result)
        self.assertGreater(call_count, 1)

@pytest.mark.websocket
class PoolCompatibilityTests(SSotAsyncTestCase):
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
        test_user_id = 'pool_user_1'
        test_context = SSotMockFactory.create_mock_user_context(user_id=test_user_id)
        emitter = await self.pool.acquire(user_id=test_user_id, context=test_context)
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        await emitter.emit_agent_started({'agent_name': 'PoolAgent'})
        await self.pool.release(emitter)
        self.mock_manager.emit_critical_event.assert_called_once()

    async def test_pool_reuse_compatibility(self):
        """Test pool emitter reuse compatibility."""
        test_user_id = 'pool_reuse_user'
        test_context = SSotMockFactory.create_mock_user_context(user_id=test_user_id)
        emitter1 = await self.pool.acquire(user_id=test_user_id, context=test_context)
        await self.pool.release(emitter1)
        emitter2 = await self.pool.acquire(user_id=test_user_id, context=test_context)
        self.assertIs(emitter1, emitter2)
        await self.pool.release(emitter2)

    async def test_pool_statistics_compatibility(self):
        """Test pool statistics compatibility."""
        stats = self.pool.get_statistics()
        self.assertIn('pool_size', stats)
        self.assertIn('acquisitions', stats)
        self.assertIn('releases', stats)
        self.assertEqual(stats['pool_size'], 0)
        test_context = SSotMockFactory.create_mock_user_context(user_id='stats_user')
        emitter = await self.pool.acquire(user_id='stats_user', context=test_context)
        stats = self.pool.get_statistics()
        self.assertEqual(stats['pool_size'], 1)
        self.assertEqual(stats['acquisitions'], 1)
        await self.pool.release(emitter)
        stats = self.pool.get_statistics()
        self.assertEqual(stats['releases'], 1)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')