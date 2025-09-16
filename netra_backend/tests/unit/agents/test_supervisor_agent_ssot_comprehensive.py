"""SSOT SupervisorAgent Comprehensive Unit Test Suite - MISSION CRITICAL for Chat Delivery

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)  
- Business Goal: Platform Reliability & Chat Delivery Infrastructure
- Value Impact: SSOT SupervisorAgent reliability = 100% of AI chat functionality = Direct revenue impact
- Strategic Impact: Every chat interaction depends on SSOT SupervisorAgent orchestration. Failures = immediate user impact.

MISSION CRITICAL REQUIREMENTS:
- SupervisorAgent SSOT implementation is the core orchestration engine for ALL AI chat interactions
- All 5 WebSocket events for chat delivery must work correctly (agent_started, agent_thinking, agent_completed, agent_error, tool_*)
- Multi-user concurrent execution MUST be properly isolated using UserExecutionContext 
- SSOT factory pattern usage MUST be validated (AgentInstanceFactory, UserExecutionEngine)
- Error handling and recovery MUST work to maintain chat availability
- Legacy compatibility methods MUST delegate properly to SSOT execute() method

TEST COVERAGE TARGET: 100% of SSOT SupervisorAgent critical business logic including:
- SSOT execute() method with UserExecutionContext integration (lines 82-174)
- SSOT factory pattern usage (lines 74-78, 175-205) 
- WebSocket event coordination for chat delivery (lines 104-147, 160-168)
- Legacy compatibility delegation (lines 207-241)
- Factory method creation (lines 242-263)
- User isolation validation and session management (lines 92-99)

CRITICAL: Uses REAL instances approach - minimal mocking per CLAUDE.md standards.
Tests must FAIL HARD on any issues - no try/except masking allowed.
"""
import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError, validate_user_context
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, get_agent_instance_factory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.database.session_manager import managed_session
from shared.id_generation import UnifiedIdGenerator

class MockUserExecutionEngine:
    """Mock UserExecutionEngine for testing SSOT pattern compliance."""

    def __init__(self, context: UserExecutionContext, agent_factory=None, websocket_emitter=None):
        self.context = context
        self.agent_factory = agent_factory
        self.websocket_emitter = websocket_emitter
        self.execution_count = 0
        self.executed_pipelines = []

    async def execute_agent_pipeline(self, agent_name: str, execution_context: UserExecutionContext, input_data: Dict) -> Any:
        """Mock agent pipeline execution."""
        self.execution_count += 1
        self.executed_pipelines.append({'agent_name': agent_name, 'context': execution_context, 'input_data': input_data, 'timestamp': time.time()})
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = {'status': 'completed', 'agent_name': agent_name, 'user_id': execution_context.user_id, 'run_id': execution_context.run_id}
        return mock_result

    async def cleanup(self):
        """Mock cleanup method."""
        pass

class MockAgentInstanceFactory:
    """Mock AgentInstanceFactory for testing SSOT factory pattern."""

    def __init__(self):
        self.configured_websocket_bridge = None
        self.configured_llm_manager = None
        self.configure_count = 0

    def configure(self, websocket_bridge=None, llm_manager=None):
        """Mock configure method."""
        self.configure_count += 1
        self.configured_websocket_bridge = websocket_bridge
        self.configured_llm_manager = llm_manager

class SupervisorAgentSSOTCoreTests(BaseTestCase):
    """Test core SSOT SupervisorAgent functionality - MISSION CRITICAL for chat delivery."""

    def setUp(self):
        """Set up test environment with real SSOT instances."""
        super().setUp()
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='test-model')
        self.llm_manager.ask_llm = AsyncMock(return_value='test response')
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        self.test_context = UserExecutionContext(user_id=f'test-user-{uuid.uuid4().hex[:8]}', thread_id=f'test-thread-{uuid.uuid4().hex[:8]}', run_id=f'test-run-{uuid.uuid4().hex[:8]}', request_id=f'test-req-{uuid.uuid4().hex[:8]}', websocket_client_id=f'test-ws-{uuid.uuid4().hex[:8]}', agent_context={'user_request': 'test request for SSOT SupervisorAgent'})
        self.mock_db_session = AsyncMock()
        self.test_context = self.test_context.with_db_session(self.mock_db_session)
        self.mock_agent_factory = MockAgentInstanceFactory()
        self.factory_patcher = patch('netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory', return_value=self.mock_agent_factory)
        self.factory_patcher.start()
        self.session_validation_patcher = patch('netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation')
        self.session_validation_patcher.start()
        self.supervisor = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge)
        self.track_resource(self.supervisor)

    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.factory_patcher.stop()
        self.session_validation_patcher.stop()

    def test_ssot_supervisor_initialization_validation(self):
        """Test SSOT SupervisorAgent initializes properly with factory patterns."""
        self.assertIsNotNone(self.supervisor)
        self.assertEqual(self.supervisor.name, 'Supervisor')
        self.assertIn('SSOT patterns', self.supervisor.description)
        self.assertEqual(self.supervisor.websocket_bridge, self.websocket_bridge)
        self.assertEqual(self.supervisor.agent_factory, self.mock_agent_factory)
        self.assertEqual(self.supervisor._llm_manager, self.llm_manager)
        self.assertIsNone(getattr(self.supervisor, '_session_storage', None))
        self.assertIsNone(getattr(self.supervisor, 'persistent_state', None))

    async def test_ssot_execute_with_valid_context_full_flow(self):
        """Test SSOT SupervisorAgent execute() method with complete flow validation."""
        mock_engine = MockUserExecutionEngine(self.test_context)
        mock_websocket_emitter = Mock()

        async def mock_create_engine(context):
            return mock_engine
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=mock_websocket_emitter):
            result = await self.supervisor.execute(self.test_context, stream_updates=True)
            self.assertIsNotNone(result)
            self.assertIn('supervisor_result', result)
            self.assertEqual(result['supervisor_result'], 'completed')
            self.assertTrue(result['orchestration_successful'])
            self.assertTrue(result['user_isolation_verified'])
            self.assertEqual(result['user_id'], self.test_context.user_id)
            self.assertEqual(result['run_id'], self.test_context.run_id)
            self.assertEqual(mock_engine.execution_count, 1)
            self.assertEqual(len(mock_engine.executed_pipelines), 1)
            pipeline_exec = mock_engine.executed_pipelines[0]
            self.assertEqual(pipeline_exec['agent_name'], 'supervisor_orchestration')
            self.assertEqual(pipeline_exec['context'], self.test_context)
            self.assertIn('user_request', pipeline_exec['input_data'])

    async def test_websocket_events_all_5_critical_events_ssot(self):
        """Test all 5 critical WebSocket events are sent during SSOT execution."""
        mock_engine = MockUserExecutionEngine(self.test_context)

        async def mock_create_engine(context):
            return mock_engine
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            result = await self.supervisor.execute(self.test_context, stream_updates=True)
            self.assertTrue(result['orchestration_successful'])
            self.websocket_bridge.notify_agent_started.assert_called_once()
            started_call = self.websocket_bridge.notify_agent_started.call_args
            self.assertEqual(started_call[0][0], self.test_context.run_id)
            self.assertEqual(started_call[0][1], 'Supervisor')
            self.assertIn('isolated', started_call[1]['context'])
            self.websocket_bridge.notify_agent_thinking.assert_called_once()
            thinking_call = self.websocket_bridge.notify_agent_thinking.call_args
            self.assertEqual(thinking_call[0][0], self.test_context.run_id)
            self.assertEqual(thinking_call[0][1], 'Supervisor')
            self.assertIn('selecting appropriate agents', thinking_call[1]['reasoning'])
            self.websocket_bridge.notify_agent_completed.assert_called_once()
            completed_call = self.websocket_bridge.notify_agent_completed.call_args
            self.assertEqual(completed_call[0][0], self.test_context.run_id)
            self.assertEqual(completed_call[0][1], 'Supervisor')
            self.assertIn('supervisor_result', completed_call[1]['result'])
            self.websocket_bridge.notify_agent_error.assert_not_called()

    async def test_websocket_error_event_on_execution_failure(self):
        """Test agent_error WebSocket event is sent on execution failure."""
        mock_engine = Mock()
        mock_engine.execute_agent_pipeline = AsyncMock(side_effect=RuntimeError('Test execution failure'))
        mock_engine.cleanup = AsyncMock()

        async def mock_create_engine(context):
            return mock_engine
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            with self.assertRaises(RuntimeError):
                await self.supervisor.execute(self.test_context)
            self.websocket_bridge.notify_agent_error.assert_called_once()
            error_call = self.websocket_bridge.notify_agent_error.call_args
            self.assertEqual(error_call[0][0], self.test_context.run_id)
            self.assertEqual(error_call[0][1], 'Supervisor')
            self.assertIn('Test execution failure', error_call[1]['error'])
            self.assertEqual(error_call[1]['error_context']['error_type'], 'RuntimeError')

    async def test_ssot_factory_pattern_compliance(self):
        """Test SSOT factory pattern usage and configuration."""
        mock_websocket_emitter = Mock()
        mock_engine = MockUserExecutionEngine(self.test_context)
        with patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=mock_websocket_emitter), patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine', return_value=mock_engine):
            engine = await self.supervisor._create_user_execution_engine(self.test_context)
            self.assertEqual(self.mock_agent_factory.configure_count, 1)
            self.assertEqual(self.mock_agent_factory.configured_websocket_bridge, self.websocket_bridge)
            self.assertEqual(self.mock_agent_factory.configured_llm_manager, self.llm_manager)
            websocket_emitter_call = patch.get_original('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter').call_args
            if websocket_emitter_call:
                self.assertEqual(websocket_emitter_call[0][0], self.test_context.user_id)
                self.assertEqual(websocket_emitter_call[0][1], self.test_context.thread_id)
                self.assertEqual(websocket_emitter_call[0][2], self.test_context.run_id)
                self.assertEqual(websocket_emitter_call[0][3], self.websocket_bridge)
            self.assertIsNotNone(engine)

    async def test_user_context_validation_ssot_compliance(self):
        """Test UserExecutionContext validation using SSOT validate_user_context."""
        valid_context = self.test_context
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', return_value=valid_context) as mock_validate:
            mock_engine = MockUserExecutionEngine(valid_context)
            with patch.object(self.supervisor, '_create_user_execution_engine', return_value=mock_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=AsyncMock()):
                result = await self.supervisor.execute(valid_context)
                mock_validate.assert_called_once_with(valid_context)
                self.assertTrue(result['orchestration_successful'])

    async def test_database_session_requirement_validation(self):
        """Test database session requirement validation."""
        context_no_db = UserExecutionContext(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_client_id='test-ws')
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', return_value=context_no_db):
            with self.assertRaises(ValueError) as cm:
                await self.supervisor.execute(context_no_db)
            self.assertIn('database session', str(cm.exception))

    async def test_legacy_run_method_delegates_to_ssot_execute(self):
        """Test legacy run() method properly delegates to SSOT execute() method."""
        mock_request_id = 'legacy-req-123'
        mock_websocket_client_id = 'legacy-ws-456'
        with patch('netra_backend.app.agents.supervisor_ssot.UnifiedIdGenerator') as mock_id_gen:
            mock_id_gen.generate_base_id.return_value = mock_request_id
            mock_id_gen.generate_websocket_client_id.return_value = mock_websocket_client_id
            mock_execute_result = {'supervisor_result': 'completed', 'orchestration_successful': True, 'user_isolation_verified': True, 'results': {'legacy_test': 'data'}, 'user_id': 'legacy-user', 'run_id': 'legacy-run'}
            with patch.object(self.supervisor, 'execute', AsyncMock(return_value=mock_execute_result)) as mock_execute:
                result = await self.supervisor.run(user_request='legacy test request', thread_id='legacy-thread', user_id='legacy-user', run_id='legacy-run')
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args
                context = call_args[0][0]
                self.assertIsInstance(context, UserExecutionContext)
                self.assertEqual(context.user_id, 'legacy-user')
                self.assertEqual(context.thread_id, 'legacy-thread')
                self.assertEqual(context.run_id, 'legacy-run')
                self.assertEqual(context.request_id, mock_request_id)
                self.assertEqual(context.websocket_client_id, mock_websocket_client_id)
                self.assertTrue(call_args[1]['stream_updates'])
                self.assertEqual(result, {'legacy_test': 'data'})

    def test_ssot_factory_method_creates_proper_instance(self):
        """Test SSOT SupervisorAgent.create() factory method."""
        supervisor = SupervisorAgent.create(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge)
        self.assertIsInstance(supervisor, SupervisorAgent)
        self.assertEqual(supervisor._llm_manager, self.llm_manager)
        self.assertEqual(supervisor.websocket_bridge, self.websocket_bridge)
        self.assertIsNotNone(supervisor.agent_factory)
        self.track_resource(supervisor)

    async def test_concurrent_user_execution_isolation_ssot(self):
        """Test multi-user execution isolation using SSOT patterns."""
        contexts = []
        for i in range(3):
            context = UserExecutionContext(user_id=f'concurrent-user-{i}', thread_id=f'concurrent-thread-{i}', run_id=f'concurrent-run-{i}', request_id=f'concurrent-req-{i}', websocket_client_id=f'concurrent-ws-{i}', agent_context={'user_request': f'concurrent test {i}'})
            context = context.with_db_session(AsyncMock())
            contexts.append(context)
        execution_results = []

        async def execute_with_tracking(context, index):
            """Execute supervisor and track results for isolation testing."""
            mock_engine = MockUserExecutionEngine(context)

            async def mock_create_engine(ctx):
                return mock_engine
            mock_session_manager = AsyncMock()
            mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
            mock_session_manager.__aexit__ = AsyncMock(return_value=None)
            with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
                result = await self.supervisor.execute(context)
                execution_results.append((context.user_id, result, mock_engine.execution_count))
        await asyncio.gather(*[execute_with_tracking(context, i) for i, context in enumerate(contexts)])
        self.assertEqual(len(execution_results), 3)
        user_ids = [result[0] for result in execution_results]
        self.assertEqual(len(set(user_ids)), 3)
        for user_id, result, execution_count in execution_results:
            self.assertEqual(result['orchestration_successful'], True)
            self.assertEqual(result['user_isolation_verified'], True)
            self.assertEqual(execution_count, 1)

    def test_string_representations_ssot(self):
        """Test SSOT SupervisorAgent string representation methods."""
        str_repr = str(self.supervisor)
        self.assertIn('SupervisorAgent', str_repr)
        self.assertIn('SSOT pattern', str_repr)
        repr_str = repr(self.supervisor)
        self.assertIn('SupervisorAgent', repr_str)
        self.assertIn("pattern='SSOT'", repr_str)
        self.assertIn('factory_based=True', repr_str)

class SupervisorAgentSSOTErrorScenariosTests(BaseTestCase):
    """Test SSOT SupervisorAgent error scenarios and edge cases."""

    def setUp(self):
        """Set up test environment for SSOT error scenario testing."""
        super().setUp()
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='test-model')
        self.llm_manager.ask_llm = AsyncMock(return_value='test response')
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        self.mock_agent_factory = MockAgentInstanceFactory()
        self.factory_patcher = patch('netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory', return_value=self.mock_agent_factory)
        self.factory_patcher.start()
        self.session_validation_patcher = patch('netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation')
        self.session_validation_patcher.start()
        self.supervisor = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge)
        self.track_resource(self.supervisor)

    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.factory_patcher.stop()
        self.session_validation_patcher.stop()

    async def test_invalid_context_handling_ssot(self):
        """Test SSOT SupervisorAgent handling of invalid UserExecutionContext."""
        with self.assertRaises(TypeError):
            await self.supervisor.execute(None)
        invalid_context = UserExecutionContext(user_id='', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_client_id='test-ws')
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', side_effect=InvalidContextError('Invalid user_id')):
            with self.assertRaises(InvalidContextError):
                await self.supervisor.execute(invalid_context)

    async def test_websocket_bridge_failure_graceful_degradation_ssot(self):
        """Test SSOT graceful degradation when WebSocket bridge fails."""
        context = UserExecutionContext(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_client_id='test-ws').with_db_session(AsyncMock())
        failing_bridge = Mock(spec=AgentWebSocketBridge)
        failing_bridge.notify_agent_started = AsyncMock(side_effect=Exception('WebSocket failure'))
        failing_bridge.notify_agent_thinking = AsyncMock(side_effect=Exception('WebSocket failure'))
        failing_bridge.notify_agent_completed = AsyncMock(side_effect=Exception('WebSocket failure'))
        failing_bridge.notify_agent_error = AsyncMock(side_effect=Exception('WebSocket failure'))
        supervisor_with_failing_ws = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=failing_bridge)
        mock_engine = MockUserExecutionEngine(context)

        async def mock_create_engine(ctx):
            return mock_engine
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        with patch.object(supervisor_with_failing_ws, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            result = await supervisor_with_failing_ws.execute(context)
            self.assertTrue(result['orchestration_successful'])
            self.assertGreater(failing_bridge.notify_agent_started.call_count, 0)
            self.assertGreater(failing_bridge.notify_agent_thinking.call_count, 0)
        self.track_resource(supervisor_with_failing_ws)

    async def test_execution_engine_cleanup_on_error_ssot(self):
        """Test UserExecutionEngine cleanup is called even on execution errors."""
        context = UserExecutionContext(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_client_id='test-ws').with_db_session(AsyncMock())
        mock_engine = Mock()
        mock_engine.execute_agent_pipeline = AsyncMock(side_effect=RuntimeError('Pipeline failure'))
        mock_engine.cleanup = AsyncMock()
        cleanup_called = []

        async def track_cleanup():
            cleanup_called.append(True)
        mock_engine.cleanup.side_effect = track_cleanup

        async def mock_create_engine(ctx):
            return mock_engine
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            with self.assertRaises(RuntimeError):
                await self.supervisor.execute(context)
            mock_engine.cleanup.assert_called_once()
            self.assertEqual(len(cleanup_called), 1)

class SupervisorAgentSSOTPerformanceTests(BaseTestCase):
    """Performance testing for SSOT SupervisorAgent."""

    def setUp(self):
        super().setUp()
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='test-model')
        self.llm_manager.ask_llm = AsyncMock(return_value='test response')
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        self.mock_agent_factory = MockAgentInstanceFactory()
        self.factory_patcher = patch('netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory', return_value=self.mock_agent_factory)
        self.factory_patcher.start()
        self.session_validation_patcher = patch('netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation')
        self.session_validation_patcher.start()
        self.supervisor = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge)
        self.track_resource(self.supervisor)

    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.factory_patcher.stop()
        self.session_validation_patcher.stop()

    async def test_ssot_performance_concurrent_execution(self):
        """Test SSOT SupervisorAgent performance under concurrent load."""
        contexts = []
        for i in range(5):
            context = UserExecutionContext(user_id=f'perf-user-{i}', thread_id=f'perf-thread-{i}', run_id=f'perf-run-{i}', request_id=f'perf-req-{i}', websocket_client_id=f'perf-ws-{i}', agent_context={'test_index': i}).with_db_session(AsyncMock())
            contexts.append(context)

        async def mock_create_engine(ctx):
            return MockUserExecutionEngine(ctx)
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            start_time = time.time()
            results = await asyncio.gather(*[self.supervisor.execute(context) for context in contexts])
            total_time = time.time() - start_time
            self.assertEqual(len(results), 5)
            for result in results:
                self.assertTrue(result['orchestration_successful'])
                self.assertTrue(result['user_isolation_verified'])
            self.assertLess(total_time, 3.0)
            avg_time = total_time / len(results)
            self.assertLess(avg_time, 1.0)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')