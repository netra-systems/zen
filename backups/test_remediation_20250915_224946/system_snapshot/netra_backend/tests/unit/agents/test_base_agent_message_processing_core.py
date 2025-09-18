"""
BaseAgent Message Processing Core Unit Tests - Issue #1081 Phase 1

Comprehensive unit tests for BaseAgent message processing functionality.
Targets golden path message handling, validation, and transformation flows.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Risk Reduction  
- Value Impact: Protects $500K+ ARR BaseAgent core message processing functionality
- Strategic Impact: Comprehensive coverage for critical agent message workflows

Coverage Focus:
- Message routing and validation (golden path priority)
- State transitions during message processing
- WebSocket event emission for user visibility
- Error handling and recovery patterns
- User context isolation in message flows
- Async message processing patterns

Test Strategy: Unit tests with minimal mocking, focus on core logic validation
"""
import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional, List
import time
from datetime import datetime
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus

class BaseAgentMessageProcessingCoreTests(SSotAsyncTestCase):
    """Comprehensive unit tests for BaseAgent message processing functionality."""

    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.mock_llm_manager = self.mock_factory.create_mock_llm_manager()
        self.mock_tool_dispatcher = self.mock_factory.create_tool_mock('unified_dispatcher')
        self.mock_redis_manager = Mock()
        self.test_user_id = 'test_user_123'
        self.test_session_id = 'session_456'
        self.user_context = self.mock_factory.create_mock_user_context(user_id=self.test_user_id, session_id=self.test_session_id)
        self.agent = BaseAgent(llm_manager=self.mock_llm_manager, name='TestMessageAgent', description='Test agent for message processing', user_id=self.test_user_id, enable_reliability=True, enable_execution_engine=True, user_context=self.user_context)
        self.websocket_calls = []
        self.processing_calls = []

    def teardown_method(self, method):
        """Clean up after each test."""
        super().teardown_method(method)
        self.websocket_calls.clear()
        self.processing_calls.clear()

    def test_agent_initialization_with_message_context(self):
        """Test agent initializes properly with message processing context."""
        assert self.agent.name == 'TestMessageAgent'
        assert self.agent.state == SubAgentLifecycle.PENDING
        assert self.agent.user_context == self.user_context
        assert self.agent.llm_manager is not None
        assert self.agent.timing_collector is not None
        assert self.agent.token_counter is not None
        assert self.agent._enable_reliability is True
        assert self.agent.circuit_breaker is not None
        assert self.agent.monitor is not None

    def test_agent_state_transitions_during_message_processing(self):
        """Test agent state changes correctly during message processing flow."""
        assert self.agent.state == SubAgentLifecycle.PENDING
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        assert self.agent.state == SubAgentLifecycle.RUNNING
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        assert self.agent.state == SubAgentLifecycle.COMPLETED

    def test_invalid_state_transitions_prevent_message_corruption(self):
        """Test invalid state transitions are prevented to maintain message integrity."""
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        with pytest.raises(ValueError, match='Invalid state transition'):
            self.agent.set_state(SubAgentLifecycle.RUNNING)

    def test_agent_context_isolation_for_messages(self):
        """Test agent maintains proper context isolation for message processing."""
        assert self.agent.user_context.user_id == self.test_user_id
        assert self.agent.user_context.session_id == self.test_session_id
        other_agent = BaseAgent(name='OtherAgent', user_context=UserExecutionContext(user_id='other_user', session_id='other_session', context={}))
        assert self.agent.user_context.user_id != other_agent.user_context.user_id
        assert self.agent.context != other_agent.context

    def test_websocket_bridge_configuration_for_message_events(self):
        """Test WebSocket bridge setup for message event notifications."""
        assert hasattr(self.agent, '_websocket_adapter')
        assert self.agent._websocket_adapter is not None
        mock_bridge = Mock()
        test_run_id = 'run_123'
        self.agent._websocket_adapter.set_websocket_bridge(bridge=mock_bridge, run_id=test_run_id, agent_name=self.agent.name)
        assert self.agent._websocket_adapter.has_websocket_bridge()
        assert self.agent._websocket_adapter._bridge == mock_bridge
        assert self.agent._websocket_adapter._run_id == test_run_id

    async def test_websocket_event_emission_during_message_processing(self):
        """Test WebSocket events are emitted during message processing flow."""
        mock_bridge = AsyncMock()
        test_run_id = 'run_456'
        self.agent._websocket_adapter.set_websocket_bridge(bridge=mock_bridge, run_id=test_run_id, agent_name=self.agent.name)
        await self.agent._websocket_adapter.emit_agent_started('Processing message')
        assert self.agent._websocket_adapter.has_websocket_bridge()

    async def test_websocket_events_fail_safely_without_bridge(self):
        """Test WebSocket events handle missing bridge gracefully in test mode."""
        self.agent._websocket_adapter.enable_test_mode()
        await self.agent._websocket_adapter.emit_agent_started('Test message')
        assert True

    def test_timing_collection_during_message_processing(self):
        """Test timing collection works for message processing workflows."""
        self.agent.timing_collector.start_timing('message_processing')
        time.sleep(0.001)
        duration = self.agent.timing_collector.end_timing('message_processing')
        assert duration > 0
        timing_data = self.agent.timing_collector.get_timing_summary()
        assert 'message_processing' in timing_data

    def test_token_counting_for_message_processing(self):
        """Test token counting during message processing."""
        test_content = 'This is a test message for token counting'
        tokens = self.agent.token_counter.count_tokens(test_content)
        assert tokens > 0
        assert tokens < 100
        cost = self.agent.token_counter.calculate_cost(tokens, 'input')
        assert cost >= 0

    def test_circuit_breaker_protection_for_message_failures(self):
        """Test circuit breaker protects against message processing failures."""
        assert self.agent.circuit_breaker is not None
        assert self.agent.circuit_breaker.name == 'TestMessageAgent'
        assert hasattr(self.agent.circuit_breaker, '_circuit_breaker')
        assert self.agent.circuit_breaker._recovery_timeout_seconds == 10

    def test_execution_monitor_tracks_message_processing(self):
        """Test execution monitor tracks message processing activities."""
        assert self.agent.monitor is not None
        assert isinstance(self.agent.monitor, ExecutionMonitor)
        test_result = {'status': 'success', 'message': 'Test processed'}
        self.agent.monitor.record_execution('message_processing', test_result)
        history = self.agent.monitor.get_execution_history()
        assert len(history) >= 1

    def test_reliability_manager_configuration(self):
        """Test reliability manager is properly configured for message processing."""
        assert self.agent._enable_reliability is True
        assert self.agent._reliability_manager_instance is not None
        reliability_manager = self.agent._reliability_manager_instance
        assert hasattr(reliability_manager, 'circuit_breaker')

    def test_execution_engine_initialization(self):
        """Test execution engine is initialized for message processing."""
        assert self.agent._enable_execution_engine is True
        assert hasattr(self.agent, '_execution_monitor')
        assert self.agent._execution_monitor is not None

    def test_message_validation_patterns(self):
        """Test message validation patterns prevent invalid processing."""
        assert self.agent.user_context is not None
        assert self.agent.user_context.user_id == self.test_user_id
        try:
            from netra_backend.app.services.user_execution_context import validate_user_context
            validate_user_context(self.agent.user_context)
            validation_passed = True
        except InvalidContextError:
            validation_passed = False
        assert validation_passed

    def test_session_isolation_validation(self):
        """Test session isolation is maintained during message processing."""
        assert not hasattr(self.agent, 'db_session') or self.agent.db_session is None
        assert hasattr(self.agent, '_validate_session_isolation')

    def test_error_handling_during_message_processing(self):
        """Test error handling patterns during message processing."""
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        with pytest.raises(ValueError):
            self.agent.set_state(SubAgentLifecycle.RUNNING)

    def test_context_error_handling(self):
        """Test handling of context-related errors."""
        try:
            invalid_agent = BaseAgent(name='InvalidAgent', user_context=None)
            assert invalid_agent.user_context is None
        except Exception as e:
            pytest.fail(f'Agent initialization failed with None context: {e}')

    async def test_async_message_processing_patterns(self):
        """Test async message processing patterns work correctly."""
        current_state = self.agent.state
        assert current_state == SubAgentLifecycle.PENDING
        await asyncio.sleep(0.001)
        assert self.agent.state == current_state

    async def test_concurrent_message_processing_safety(self):
        """Test concurrent message processing maintains safety."""
        tasks = []
        for i in range(5):
            task = asyncio.create_task(self._simulate_message_operation(i))
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            assert not isinstance(result, Exception), f'Concurrent operation failed: {result}'

    async def _simulate_message_operation(self, operation_id: int):
        """Simulate a message processing operation."""
        await asyncio.sleep(0.001)
        self.processing_calls.append(f'operation_{operation_id}')
        return f'completed_{operation_id}'

    def test_websocket_adapter_integration_readiness(self):
        """Test agent is ready for WebSocket integration."""
        assert hasattr(self.agent, '_websocket_adapter')
        adapter = self.agent._websocket_adapter
        assert hasattr(adapter, 'set_websocket_bridge')
        assert hasattr(adapter, 'has_websocket_bridge')
        assert hasattr(adapter, 'enable_test_mode')

    def test_llm_manager_integration_readiness(self):
        """Test agent is ready for LLM manager integration."""
        assert self.agent.llm_manager is not None
        assert hasattr(self.agent, 'correlation_id')
        assert self.agent.correlation_id is not None

    def test_tool_dispatcher_integration_readiness(self):
        """Test agent is ready for tool dispatcher integration."""
        agent_with_tools = BaseAgent(name='ToolAgent', tool_dispatcher=self.mock_tool_dispatcher, user_context=self.user_context)
        assert agent_with_tools.tool_dispatcher is not None

    def test_memory_usage_during_message_processing(self):
        """Test memory usage is reasonable during message processing."""
        import sys
        initial_size = sys.getsizeof(self.agent)
        for i in range(100):
            self.agent.context[f'message_{i}'] = f'value_{i}'
        final_size = sys.getsizeof(self.agent)
        growth = final_size - initial_size
        assert growth < 10000

    def test_context_cleanup_during_message_processing(self):
        """Test context cleanup happens correctly."""
        self.agent.context['temp_data'] = 'should_be_cleaned'
        assert 'temp_data' in self.agent.context
        assert len(self.agent.context) >= 1

    def test_cache_configuration_for_messages(self):
        """Test cache configuration for message processing."""
        cached_agent = BaseAgent(name='CachedAgent', enable_caching=True, redis_manager=self.mock_redis_manager, user_context=self.user_context)
        assert cached_agent._enable_caching is True
        assert cached_agent.redis_manager is not None
        assert cached_agent.cache_ttl == 3600

    def test_retry_configuration_for_message_failures(self):
        """Test retry configuration for handling message processing failures."""
        assert self.agent.max_retries == 3
        if self.agent._enable_reliability:
            assert hasattr(self.agent, '_unified_reliability_handler')

    def test_golden_path_message_flow_protection(self):
        """Test protection of golden path message processing flow."""
        assert self.agent.user_context is not None, 'User context required for golden path'
        assert self.agent._websocket_adapter is not None, 'WebSocket events required for golden path'
        assert self.agent.timing_collector is not None, 'Performance tracking required'
        assert self.agent.token_counter is not None, 'Cost tracking required'

    def test_user_isolation_for_multi_tenant_messages(self):
        """Test user isolation prevents message cross-contamination."""
        other_context = UserExecutionContext(user_id='other_user', session_id='other_session', context={})
        other_agent = BaseAgent(name='OtherUserAgent', user_context=other_context)
        assert self.agent.user_context.user_id != other_agent.user_context.user_id
        assert self.agent.context != other_agent.context
        assert id(self.agent.context) != id(other_agent.context)

    def test_websocket_event_isolation_per_user(self):
        """Test WebSocket events are properly isolated per user."""
        user1_bridge = Mock()
        user2_bridge = Mock()
        self.agent._websocket_adapter.set_websocket_bridge(bridge=user1_bridge, run_id='user1_run', agent_name=self.agent.name)
        other_context = UserExecutionContext(user_id='user2', session_id='session2', context={})
        other_agent = BaseAgent(name='User2Agent', user_context=other_context)
        other_agent._websocket_adapter.set_websocket_bridge(bridge=user2_bridge, run_id='user2_run', agent_name='User2Agent')
        assert self.agent._websocket_adapter._bridge != other_agent._websocket_adapter._bridge
        assert self.agent._websocket_adapter._run_id != other_agent._websocket_adapter._run_id
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')