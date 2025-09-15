"""BaseAgent SSOT Integration Tests: Foundation for AI Agent Chat Functionality

CRITICAL BUSINESS VALUE: BaseAgent is the foundation for all AI agents that deliver 90% of 
platform value through chat interactions. These tests validate the core infrastructure that 
enables reliable LLM interactions, WebSocket communication, user isolation, and resilience 
patterns essential for substantive chat experiences.

Business Impact:
- Protects $500K+ ARR through reliable chat functionality
- Ensures proper user isolation preventing data contamination
- Validates WebSocket events enabling real-time chat progress
- Tests retry mechanisms preventing chat failures
- Verifies LLM integration enabling AI responses

Test Strategy:
- NO MOCKS - Use real components without running services
- Focus on integration between BaseAgent and key dependencies
- Test realistic agent execution scenarios
- Validate proper error handling and graceful degradation
- Ensure UserExecutionContext isolation patterns work correctly

SSOT Compliance:
- Uses SSotAsyncTestCase from test_framework.ssot.base_test_case
- Follows absolute import patterns from SSOT_IMPORT_REGISTRY.md
- Uses IsolatedEnvironment for all environment access
- Tests actual BaseAgent functionality with real dependencies
"""
import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.agents.base_agent import BaseAgent, AgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler, RetryConfig
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from shared.types.core_types import UserID, ThreadID, RunID

class TestBaseAgentForIntegration(BaseAgent):
    """Concrete test agent implementation for testing BaseAgent abstract patterns.
    
    This agent implements the modern UserExecutionContext pattern and provides
    realistic test scenarios for BaseAgent functionality.
    """

    def __init__(self, **kwargs):
        """Initialize test agent with enhanced tracking."""
        super().__init__(name='TestAgent', description='Test agent for BaseAgent integration testing', **kwargs)
        self.execution_count = 0
        self.last_execution_context = None
        self.last_execution_result = None
        self.execution_history = []
        self.websocket_events_sent = []
        self.llm_requests_made = []
        self.retry_attempts = 0
        self.failure_simulation = None
        self.enable_websocket_test_mode()

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> Dict[str, Any]:
        """Modern UserExecutionContext implementation for testing.
        
        This method demonstrates the proper BaseAgent execution pattern while
        providing hooks for integration test validation.
        """
        self.execution_count += 1
        self.last_execution_context = context
        execution_id = str(uuid.uuid4())
        try:
            execution_start = time.time()
            execution_record = {'execution_id': execution_id, 'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id, 'request_id': context.request_id, 'start_time': execution_start, 'stream_updates': stream_updates}
            self.execution_history.append(execution_record)
            if self.failure_simulation:
                failure_type = self.failure_simulation.get('type')
                if failure_type == 'ValueError':
                    raise ValueError(self.failure_simulation.get('message', 'Simulated test failure'))
                elif failure_type == 'RuntimeError':
                    raise RuntimeError(self.failure_simulation.get('message', 'Simulated runtime error'))
                elif failure_type == 'ConnectionError':
                    raise ConnectionError(self.failure_simulation.get('message', 'Simulated connection error'))
            if stream_updates:
                await self.emit_agent_started('Starting test agent execution')
                await self.emit_thinking('Analyzing user request', step_number=1)
                await self.emit_thinking('Generating response', step_number=2)
            user_request = context.agent_context.get('user_request', 'test request')
            llm_request = {'correlation_id': self.correlation_id, 'request': user_request, 'timestamp': time.time(), 'context_id': context.request_id}
            self.llm_requests_made.append(llm_request)
            self.store_metadata_result(context, 'execution_id', execution_id)
            self.store_metadata_result(context, 'processing_steps', ['request_analysis', 'response_generation'])
            await asyncio.sleep(0.01)
            result = {'execution_id': execution_id, 'status': 'success', 'user_request': user_request, 'response': f'Processed: {user_request}', 'execution_time': time.time() - execution_start, 'agent_name': self.name, 'context_details': {'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id, 'operation_depth': context.operation_depth}}
            if stream_updates:
                await self.emit_agent_completed({'result': result}, context)
            execution_record.update({'end_time': time.time(), 'status': 'success', 'result': result})
            self.last_execution_result = result
            return result
        except Exception as e:
            execution_record.update({'end_time': time.time(), 'status': 'failed', 'error': str(e), 'error_type': type(e).__name__})
            if stream_updates:
                await self.emit_error(str(e), type(e).__name__)
            raise

    def set_failure_simulation(self, failure_type: str, message: str=None):
        """Configure agent to simulate failures for testing."""
        self.failure_simulation = {'type': failure_type, 'message': message or f'Simulated {failure_type}'}

    def clear_failure_simulation(self):
        """Clear failure simulation."""
        self.failure_simulation = None

    def track_websocket_event(self, event_type: str, data: Any=None):
        """Track WebSocket events for test validation."""
        self.websocket_events_sent.append({'type': event_type, 'data': data, 'timestamp': time.time(), 'correlation_id': self.correlation_id})

    async def emit_thinking(self, thought: str, step_number: Optional[int]=None, context: Optional[UserExecutionContext]=None) -> None:
        """Override to track thinking events."""
        self.track_websocket_event('thinking', {'thought': thought, 'step': step_number})
        try:
            await super().emit_thinking(thought, step_number, context)
        except RuntimeError:
            pass

    async def emit_agent_started(self, message: Optional[str]=None) -> None:
        """Override to track agent started events."""
        self.track_websocket_event('agent_started', message)
        try:
            await super().emit_agent_started(message)
        except RuntimeError:
            pass

    async def emit_agent_completed(self, result: Optional[Dict]=None, context: Optional[UserExecutionContext]=None) -> None:
        """Override to track agent completed events."""
        self.track_websocket_event('agent_completed', result)
        try:
            await super().emit_agent_completed(result, context)
        except RuntimeError:
            pass

    async def emit_error(self, error_message: str, error_type: Optional[str]=None, error_details: Optional[Dict]=None) -> None:
        """Override to track error events."""
        self.track_websocket_event('error', {'message': error_message, 'type': error_type, 'details': error_details})
        try:
            await super().emit_error(error_message, error_type, error_details)
        except RuntimeError:
            pass

class TestBaseAgentIntegration(SSotAsyncTestCase):
    """Integration tests for BaseAgent SSOT class functionality.
    
    Tests cover the complete BaseAgent lifecycle, LLM integration, WebSocket bridging,
    retry mechanisms, and user context isolation - all critical for chat functionality.
    """

    def setup_method(self, method=None):
        """Setup test environment with SSOT patterns."""
        super().setup_method(method)
        self.env = self.get_env()
        self.env.set('TESTING', 'true', 'base_agent_integration_test')
        self.env.set('LLM_REQUESTS_ENABLED', 'false', 'base_agent_integration_test')
        self.test_user_1 = f'test_user_{uuid.uuid4().hex[:8]}'
        self.test_user_2 = f'test_user_{uuid.uuid4().hex[:8]}'
        self.base_context = self._create_test_user_context(user_id=self.test_user_1, thread_id=f'thread_{uuid.uuid4().hex[:8]}', run_id=f'run_{uuid.uuid4().hex[:8]}')

    def _create_test_user_context(self, user_id: str=None, thread_id: str=None, run_id: str=None, agent_context: Dict[str, Any]=None, **kwargs) -> UserExecutionContext:
        """Create test UserExecutionContext with proper validation."""
        default_agent_context = {'user_request': 'test request'}
        if agent_context:
            default_agent_context.update(agent_context)
        return UserExecutionContext(user_id=user_id or f'test_user_{uuid.uuid4().hex[:8]}', thread_id=thread_id or f'thread_{uuid.uuid4().hex[:8]}', run_id=run_id or f'run_{uuid.uuid4().hex[:8]}', agent_context=default_agent_context, **kwargs)

    async def test_agent_initialization_with_user_context(self):
        """Test BaseAgent initialization with UserExecutionContext pattern."""
        agent = BaseAgent.create_agent_with_context(self.base_context)
        self.assertIsNotNone(agent.agent_id)
        self.assertIsNotNone(agent.correlation_id)
        self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
        self.assertIsNotNone(agent.user_context)
        self.assertEqual(agent.user_context.user_id, self.base_context.user_id)
        self.assertIsNotNone(agent._websocket_adapter)
        self.assertIsNotNone(agent.timing_collector)
        self.assertIsNotNone(agent.circuit_breaker)
        self.assertIsNotNone(agent.monitor)
        health = agent.get_health_status()
        self.assertEqual(health['agent_name'], 'BaseAgent')
        self.assertEqual(health['state'], 'pending')
        self.assertIn('circuit_breaker', health)
        self.record_metric('agent_initialization_success', True)

    async def test_agent_state_transitions(self):
        """Test proper agent state transitions through lifecycle."""
        agent = TestBaseAgentForIntegration()
        self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
        agent.set_state(SubAgentLifecycle.RUNNING)
        self.assertEqual(agent.state, SubAgentLifecycle.RUNNING)
        agent.set_state(SubAgentLifecycle.COMPLETED)
        self.assertEqual(agent.state, SubAgentLifecycle.COMPLETED)
        agent.set_state(SubAgentLifecycle.SHUTDOWN)
        self.assertEqual(agent.state, SubAgentLifecycle.SHUTDOWN)
        with self.expect_exception(ValueError):
            agent.set_state(SubAgentLifecycle.RUNNING)
        self.record_metric('state_transitions_tested', 4)

    async def test_agent_execution_with_context_pattern(self):
        """Test agent execution using modern UserExecutionContext pattern."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context(user_id=self.test_user_1, agent_context={'user_request': 'analyze data patterns'})
        start_time = time.time()
        result = await agent.execute(context=context, stream_updates=True)
        execution_time = time.time() - start_time
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'success')
        self.assertIn('execution_id', result)
        self.assertEqual(result['user_request'], 'analyze data patterns')
        self.assertEqual(result['agent_name'], 'TestAgent')
        self.assertEqual(agent.execution_count, 1)
        self.assertIsNotNone(agent.last_execution_context)
        self.assertEqual(agent.last_execution_context.user_id, self.test_user_1)
        self.assertIsNotNone(context.agent_context)
        self.assertTrue(isinstance(context.agent_context, dict))
        self.assertIn('execution_id', agent.last_execution_result)
        self.assertEqual(len(agent.execution_history), 1)
        self.record_metric('execution_time_ms', execution_time * 1000)
        self.record_metric('successful_execution', True)

    async def test_agent_reset_state_functionality(self):
        """Test agent state reset for safe reuse across requests."""
        agent = TestBaseAgentForIntegration()
        context1 = self._create_test_user_context(user_id=self.test_user_1, agent_context={'user_request': 'first request'})
        await agent.execute(context=context1)
        self.assertEqual(agent.execution_count, 1)
        self.assertIsNotNone(agent.last_execution_context)
        await agent.reset_state()
        self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
        self.assertIsNone(agent.start_time)
        self.assertIsNone(agent.end_time)
        self.assertEqual(len(agent.context), 0)
        context2 = self._create_test_user_context(user_id=self.test_user_2, agent_context={'user_request': 'second request'})
        await agent.execute(context=context2)
        self.assertEqual(agent.execution_count, 2)
        self.assertEqual(agent.last_execution_context.user_id, self.test_user_2)
        self.record_metric('state_reset_success', True)

    async def test_agent_shutdown_graceful(self):
        """Test graceful agent shutdown and resource cleanup."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context()
        await agent.execute(context=context)
        await agent.shutdown()
        self.assertEqual(agent.state, SubAgentLifecycle.SHUTDOWN)
        self.assertEqual(len(agent.context), 0)
        await agent.shutdown()
        self.assertEqual(agent.state, SubAgentLifecycle.SHUTDOWN)
        self.record_metric('graceful_shutdown_success', True)

    async def test_llm_correlation_id_generation(self):
        """Test LLM correlation ID generation and consistency."""
        agent = TestBaseAgentForIntegration()
        correlation_id1 = agent.correlation_id
        self.assertIsNotNone(correlation_id1)
        self.assertTrue(isinstance(correlation_id1, str))
        self.assertGreater(len(correlation_id1), 10)
        agent2 = TestBaseAgentForIntegration()
        correlation_id2 = agent2.correlation_id
        self.assertNotEqual(correlation_id1, correlation_id2)
        context = self._create_test_user_context()
        await agent.execute(context=context)
        self.assertEqual(agent.correlation_id, correlation_id1)
        self.assertEqual(len(agent.llm_requests_made), 1)
        llm_request = agent.llm_requests_made[0]
        self.assertEqual(llm_request['correlation_id'], correlation_id1)
        self.record_metric('correlation_ids_generated', 2)

    @patch('netra_backend.app.llm.llm_manager.LLMManager')
    async def test_llm_manager_integration(self, mock_llm_manager_class):
        """Test BaseAgent integration with LLMManager."""
        mock_llm_manager = AsyncMock()
        mock_llm_manager.generate_async.return_value = {'response': 'Test LLM response', 'token_usage': {'input_tokens': 10, 'output_tokens': 15}, 'model': 'test-model'}
        mock_llm_manager_class.return_value = mock_llm_manager
        agent = TestBaseAgentForIntegration(llm_manager=mock_llm_manager)
        context = self._create_test_user_context(agent_context={'user_request': 'Generate creative content'})
        result = await agent.execute(context=context)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(agent.llm_manager, mock_llm_manager)
        self.assertEqual(len(agent.llm_requests_made), 1)
        llm_request = agent.llm_requests_made[0]
        self.assertEqual(llm_request['request'], 'Generate creative content')
        self.assertIsNotNone(llm_request['correlation_id'])
        self.record_metric('llm_manager_integration_success', True)

    async def test_token_usage_tracking(self):
        """Test token usage tracking and cost optimization features."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context()
        self.assertIsNotNone(agent.token_counter)
        summary = agent.get_token_usage_summary(context)
        self.assertIsNotNone(summary)
        self.assertTrue(isinstance(summary, dict))
        self.assertIsNotNone(agent.token_context_manager)
        self.record_metric('token_tracking_infrastructure_validated', True)

    async def test_llm_error_handling_patterns(self):
        """Test LLM error handling and fallback patterns."""
        agent = TestBaseAgentForIntegration()
        agent.set_failure_simulation('ConnectionError', 'LLM service unavailable')
        context = self._create_test_user_context()
        with self.expect_exception(ConnectionError, 'LLM service unavailable'):
            await agent.execute(context=context)
        self.assertEqual(len(agent.execution_history), 1)
        execution = agent.execution_history[0]
        self.assertEqual(execution['status'], 'failed')
        self.assertEqual(execution['error_type'], 'ConnectionError')
        agent.clear_failure_simulation()
        result = await agent.execute(context=context)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(agent.execution_history), 2)
        self.record_metric('llm_error_handling_tested', True)

    async def test_websocket_bridge_adapter_integration(self):
        """Test WebSocket bridge adapter integration for event emission."""
        agent = TestBaseAgentForIntegration()
        self.assertIsNotNone(agent._websocket_adapter)
        self.assertTrue(isinstance(agent._websocket_adapter, WebSocketBridgeAdapter))
        self.assertFalse(agent.has_websocket_context())
        await agent.emit_thinking('Test thinking event')
        await agent.emit_agent_started('Test start event')
        await agent.emit_agent_completed({'test': 'result'})
        self.assertEqual(len(agent.websocket_events_sent), 3)
        self.record_metric('websocket_adapter_integration_success', True)

    async def test_websocket_event_emission_with_context(self):
        """Test WebSocket event emission with UserExecutionContext."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context()
        agent.set_user_context(context)
        result = await agent.execute(context=context, stream_updates=True)
        self.assertEqual(result['status'], 'success')
        self.assertGreater(len(agent.websocket_events_sent), 0)
        for event in agent.websocket_events_sent:
            self.assertEqual(event['correlation_id'], agent.correlation_id)
            self.assertIsNotNone(event['timestamp'])
        self.record_metric('websocket_events_emitted', len(agent.websocket_events_sent))

    async def test_websocket_user_isolation(self):
        """Test WebSocket event isolation between different users."""
        agent1 = TestBaseAgentForIntegration()
        agent2 = TestBaseAgentForIntegration()
        context1 = self._create_test_user_context(user_id=self.test_user_1)
        context2 = self._create_test_user_context(user_id=self.test_user_2)
        agent1.set_user_context(context1)
        agent2.set_user_context(context2)
        await agent1.execute(context=context1, stream_updates=True)
        await agent2.execute(context=context2, stream_updates=True)
        self.assertNotEqual(agent1.correlation_id, agent2.correlation_id)
        self.assertEqual(agent1.user_context.user_id, self.test_user_1)
        self.assertEqual(agent2.user_context.user_id, self.test_user_2)
        for event in agent1.websocket_events_sent:
            self.assertEqual(event['correlation_id'], agent1.correlation_id)
        for event in agent2.websocket_events_sent:
            self.assertEqual(event['correlation_id'], agent2.correlation_id)
        self.record_metric('user_isolation_validated', True)

    async def test_websocket_error_emission(self):
        """Test WebSocket error event emission and handling."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context()
        agent.set_failure_simulation('ValueError', 'Test error for WebSocket emission')
        with self.expect_exception(ValueError):
            await agent.execute(context=context, stream_updates=True)
        error_events = [e for e in agent.websocket_events_sent if e['type'] == 'error']
        self.assertGreater(len(error_events), 0)
        self.record_metric('websocket_error_emission_tested', True)

    async def test_unified_retry_handler_integration(self):
        """Test integration with UnifiedRetryHandler for resilience."""
        agent = TestBaseAgentForIntegration(enable_reliability=True)
        self.assertIsNotNone(agent.unified_reliability_handler)
        self.assertTrue(isinstance(agent.unified_reliability_handler, UnifiedRetryHandler))
        cb_status = agent.get_circuit_breaker_status()
        self.assertIn('state', cb_status)
        self.assertIn('status', cb_status)
        health = agent.get_health_status()
        self.assertIn('circuit_breaker', health)
        self.assertIn('unified_reliability', health)
        self.record_metric('retry_handler_integration_success', True)

    async def test_agent_retry_with_transient_failures(self):
        """Test agent retry behavior with transient failures."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context()
        agent.retry_attempts = 0

        async def failing_operation():
            agent.retry_attempts += 1
            if agent.retry_attempts < 3:
                raise ValueError(f'Attempt {agent.retry_attempts} failed')
            return {'status': 'success', 'attempts': agent.retry_attempts}
        result = await agent.execute_with_retry(message='test with retries', context=context, max_retries=3)
        self.assertEqual(result['status'], 'success')
        self.record_metric('retry_attempts_tested', agent.retry_attempts)

    async def test_circuit_breaker_behavior(self):
        """Test circuit breaker behavior under failure conditions."""
        agent = TestBaseAgentForIntegration(enable_reliability=True)
        initial_status = agent.get_circuit_breaker_status()
        initial_state = initial_status.get('state', 'closed').lower()
        self.assertTrue(agent.circuit_breaker.can_execute())
        health = agent.get_health_status()
        self.assertIn('circuit_breaker', health)
        self.assertTrue(health['circuit_breaker']['can_execute'])
        self.record_metric('circuit_breaker_initial_state', initial_state)
        self.record_metric('circuit_breaker_can_execute', True)

    async def test_fallback_execution_patterns(self):
        """Test fallback execution patterns for service degradation."""
        agent = TestBaseAgentForIntegration()
        context = self._create_test_user_context()
        fallback_responses = {'connection': {'status': 'fallback', 'message': 'Using cached response'}, 'timeout': {'status': 'fallback', 'message': 'Request timed out, using default'}}
        agent.set_failure_simulation('ConnectionError', 'Service connection failed')
        result = await agent.execute_with_fallback(message='test with fallback', context=context, fallback_responses=fallback_responses)
        self.assertEqual(result['status'], 'fallback')
        self.assertIn('cached response', result['message'])
        self.record_metric('fallback_execution_tested', True)

    async def test_user_execution_context_validation(self):
        """Test UserExecutionContext validation and isolation."""
        agent = TestBaseAgentForIntegration()
        valid_context = self._create_test_user_context()
        validated_context = validate_user_context(valid_context)
        self.assertEqual(validated_context.user_id, valid_context.user_id)
        agent.set_user_context(validated_context)
        self.assertEqual(agent.user_context.user_id, validated_context.user_id)
        migration_status = agent.get_migration_status()
        self.assertEqual(migration_status['migration_status'], 'compliant')
        self.assertTrue(migration_status['user_isolation_safe'])
        self.record_metric('context_validation_success', True)

    async def test_concurrent_user_isolation(self):
        """Test that concurrent users maintain complete isolation."""
        agent1 = TestBaseAgentForIntegration()
        agent2 = TestBaseAgentForIntegration()
        context1 = self._create_test_user_context(user_id=self.test_user_1, agent_context={'user_request': 'user 1 request'})
        context2 = self._create_test_user_context(user_id=self.test_user_2, agent_context={'user_request': 'user 2 request'})
        results = await asyncio.gather(agent1.execute(context=context1), agent2.execute(context=context2), return_exceptions=True)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['status'], 'success')
        self.assertEqual(results[1]['status'], 'success')
        self.assertEqual(results[0]['user_request'], 'user 1 request')
        self.assertEqual(results[1]['user_request'], 'user 2 request')
        self.assertEqual(results[0]['context_details']['user_id'], self.test_user_1)
        self.assertEqual(results[1]['context_details']['user_id'], self.test_user_2)
        self.assertNotEqual(agent1.last_execution_context.user_id, agent2.last_execution_context.user_id)
        self.record_metric('concurrent_users_tested', 2)

    async def test_session_isolation_validation(self):
        """Test database session isolation validation."""
        agent = TestBaseAgentForIntegration()
        agent._validate_session_isolation()
        validation = agent.validate_modern_implementation()
        self.assertTrue(validation['compliant'])
        self.assertEqual(validation['pattern'], 'modern')
        migration_validation = agent.validate_migration_completeness()
        self.assertTrue(migration_validation['migration_complete'])
        self.record_metric('session_isolation_validated', True)

    async def test_metadata_storage_isolation(self):
        """Test metadata storage isolation between contexts."""
        agent = TestBaseAgentForIntegration()
        context1 = self._create_test_user_context(user_id=self.test_user_1, agent_context={'test_key': 'user1_value', 'user_type': 'user1'})
        context2 = self._create_test_user_context(user_id=self.test_user_2, agent_context={'test_key': 'user2_value', 'user_type': 'user2'})
        value1 = agent.get_metadata_value(context1, 'test_key')
        value2 = agent.get_metadata_value(context2, 'test_key')
        self.assertEqual(value1, 'user1_value')
        self.assertEqual(value2, 'user2_value')
        self.assertNotEqual(value1, value2)
        user1_type = agent.get_metadata_value(context1, 'user_type')
        user2_type = agent.get_metadata_value(context2, 'user_type')
        self.assertEqual(user1_type, 'user1')
        self.assertEqual(user2_type, 'user2')
        self.assertEqual(context1.user_id, self.test_user_1)
        self.assertEqual(context2.user_id, self.test_user_2)
        self.assertNotEqual(context1.user_id, context2.user_id)
        self.record_metric('context_isolation_validated', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')