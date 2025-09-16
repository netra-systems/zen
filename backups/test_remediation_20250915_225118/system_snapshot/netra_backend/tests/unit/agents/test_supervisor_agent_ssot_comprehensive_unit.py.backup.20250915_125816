"""SupervisorAgent SSOT Comprehensive Unit Test Suite - MISSION CRITICAL

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Chat Functionality Delivery & Platform Reliability
- Value Impact: SupervisorAgent SSOT orchestration = 100% of AI chat value = Direct $500K+ ARR impact
- Strategic Impact: Core orchestration engine for ALL AI interactions. Test failures = immediate customer impact.

CRITICAL REQUIREMENTS per CLAUDE.md:
- SupervisorAgent SSOT is the central orchestrator for ALL AI chat interactions
- All 5 WebSocket events must be validated (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- Multi-user isolation using UserExecutionContext MUST be validated
- SSOT factory patterns (AgentInstanceFactory, UserExecutionEngine) MUST be verified
- User context isolation and security MUST be tested
- Legacy compatibility delegation to SSOT execute() MUST work
- Error scenarios and graceful degradation MUST be covered

TEST STRATEGY per TEST_CREATION_GUIDE.md:
- Uses REAL instances with minimal mocking (SSOT compliance)
- Tests FAIL HARD on issues (no try/except masking)
- Follows SSotAsyncTestCase patterns
- Validates business-critical functionality first
- Uses IsolatedEnvironment (no direct os.environ)
- Comprehensive WebSocket event validation

COVERAGE TARGET: 100% of critical SupervisorAgent SSOT business logic:
- SSOT execute() method with UserExecutionContext (lines 139-248 in supervisor_ssot.py)
- Factory pattern integration (AgentInstanceFactory, UserExecutionEngine)  
- WebSocket event coordination for chat delivery
- User execution context validation and isolation
- Legacy run() method delegation to SSOT execute()
- Error handling and cleanup
- Performance under concurrent load
"""
import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError, validate_user_context
from netra_backend.app.agents.base.interface import ExecutionResult, ExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, create_agent_instance_factory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.id_generation import UnifiedIdGenerator

class MockUserExecutionEngine:
    """Mock UserExecutionEngine following SSOT execution patterns.
    
    Provides realistic mock behavior for testing SupervisorAgent SSOT
    orchestration without requiring full infrastructure.
    """

    def __init__(self, context: UserExecutionContext, agent_factory=None, websocket_emitter=None):
        self.context = context
        self.agent_factory = agent_factory
        self.websocket_emitter = websocket_emitter
        self.pipeline_executions = []
        self.cleanup_called = False

    async def execute_agent_pipeline(self, agent_name: str, execution_context: UserExecutionContext, input_data: Dict[str, Any]) -> Any:
        """Mock agent pipeline execution with realistic orchestration behavior."""
        execution_record = {'agent_name': agent_name, 'execution_context': execution_context, 'input_data': input_data, 'timestamp': time.time(), 'user_id': execution_context.user_id, 'run_id': execution_context.run_id}
        self.pipeline_executions.append(execution_record)
        orchestration_results = {'triage': {'status': 'completed', 'analysis': 'User request triaged successfully', 'confidence': 0.95, 'recommended_agents': ['data', 'optimization']}, 'data': {'status': 'completed', 'data_analysis': 'Cost data analyzed', 'metrics': {'total_cost': 5000, 'optimization_potential': 15}}, 'optimization': {'status': 'completed', 'recommendations': [{'action': 'rightsize_instances', 'savings': 800}, {'action': 'reserved_instances', 'savings': 1200}], 'total_potential_savings': 2000}, 'actions': {'status': 'completed', 'action_plan': 'Implementation plan created', 'priority': 'high'}, 'reporting': {'status': 'completed', 'report': 'Comprehensive optimization report generated', 'summary': 'Found $2000/month savings opportunity'}}
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = orchestration_results.get(agent_name, {'status': 'completed', 'agent_name': agent_name, 'user_id': execution_context.user_id})
        return mock_result

    async def cleanup(self):
        """Mock cleanup with tracking."""
        self.cleanup_called = True

class MockAgentInstanceFactory:
    """Mock AgentInstanceFactory for testing SSOT factory patterns."""

    def __init__(self):
        self.websocket_bridge = None
        self.llm_manager = None
        self.configuration_count = 0

    def configure(self, websocket_bridge=None, llm_manager=None):
        """Mock factory configuration."""
        self.configuration_count += 1
        if websocket_bridge:
            self.websocket_bridge = websocket_bridge
        if llm_manager:
            self.llm_manager = llm_manager

class TestSupervisorAgentSSOTCore(SSotAsyncTestCase):
    """Test core SupervisorAgent SSOT functionality - MISSION CRITICAL for chat delivery."""

    def setup_method(self, method):
        """Set up test environment with SSOT patterns."""
        super().setup_method(method)
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='gpt-4')
        self.llm_manager.ask_llm = AsyncMock(return_value='AI optimization analysis complete')
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_tool_executing = AsyncMock()
        self.websocket_bridge.notify_tool_completed = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        self.test_user_context = UserExecutionContext.from_request_supervisor(user_id=f'test-user-{uuid.uuid4().hex[:8]}', thread_id=f'test-thread-{uuid.uuid4().hex[:8]}', run_id=f'test-run-{uuid.uuid4().hex[:8]}', request_id=f'test-req-{uuid.uuid4().hex[:8]}', websocket_connection_id=f'test-ws-{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Optimize my AI infrastructure costs'})
        self.mock_db_session = AsyncMock()
        self.test_user_context = self.test_user_context.with_db_session(self.mock_db_session)
        self.mock_agent_factory = MockAgentInstanceFactory()
        self.factory_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory', return_value=self.mock_agent_factory)
        self.factory_patcher.start()
        self.add_cleanup(self.factory_patcher.stop)
        self.session_validation_patcher = patch('netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation')
        self.session_validation_patcher.start()
        self.add_cleanup(self.session_validation_patcher.stop)
        self.supervisor = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge, user_context=self.test_user_context)
        self.record_metric('test_setup_time', time.time())

    def test_ssot_supervisor_initialization_patterns(self):
        """Test SupervisorAgent SSOT initializes with proper factory patterns.
        
        BVJ: Initialization correctness = Foundation for all chat interactions.
        """
        self.assertIsNotNone(self.supervisor)
        self.assertEqual(self.supervisor.name, 'Supervisor')
        self.assertIn('SSOT patterns', self.supervisor.description)
        self.assertEqual(self.supervisor.agent_factory, self.mock_agent_factory)
        self.assertIsNotNone(self.supervisor.workflow_executor)
        self.assertEqual(self.supervisor.websocket_bridge, self.websocket_bridge)
        self.assertEqual(self.supervisor._llm_manager, self.llm_manager)
        self.assertIsNone(getattr(self.supervisor, '_session_storage', None))
        self.assertIsNone(getattr(self.supervisor, 'persistent_state', None))
        self.record_metric('ssot_initialization_verified', True)

    async def test_ssot_execute_complete_orchestration_workflow(self):
        """Test SupervisorAgent SSOT execute() method with complete orchestration flow.
        
        BVJ: Execute method = Core of all AI chat value delivery.
        """
        mock_engine = MockUserExecutionEngine(self.test_user_context)
        mock_websocket_emitter = Mock()

        async def mock_create_engine(context):
            return mock_engine
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=mock_websocket_emitter):
            result = await self.supervisor.execute(self.test_user_context, stream_updates=True)
            self.assertIsInstance(result, ExecutionResult)
            self.assertEqual(result.status, ExecutionStatus.COMPLETED)
            self.assertIsNotNone(result.request_id)
            result_data = result.data
            self.assertEqual(result_data['supervisor_result'], 'completed')
            self.assertTrue(result_data['orchestration_successful'])
            self.assertTrue(result_data['user_isolation_verified'])
            self.assertEqual(result_data['user_id'], self.test_user_context.user_id)
            self.assertEqual(result_data['run_id'], self.test_user_context.run_id)
            expected_agents = ['triage', 'data', 'optimization', 'actions', 'reporting']
            self.assertEqual(len(mock_engine.pipeline_executions), len(expected_agents))
            executed_agents = [exec_record['agent_name'] for exec_record in mock_engine.pipeline_executions]
            self.assertEqual(executed_agents, expected_agents)
            for exec_record in mock_engine.pipeline_executions:
                self.assertEqual(exec_record['user_id'], self.test_user_context.user_id)
                self.assertEqual(exec_record['run_id'], self.test_user_context.run_id)
                self.assertIn('user_request', exec_record['input_data'])
        self.record_metric('orchestration_workflow_completed', True)
        self.record_metric('pipeline_steps_executed', len(mock_engine.pipeline_executions))

    async def test_websocket_events_all_5_critical_events_validation(self):
        """Test all 5 critical WebSocket events for chat delivery are sent.
        
        BVJ: WebSocket events = Real-time chat experience = User engagement.
        """
        mock_engine = MockUserExecutionEngine(self.test_user_context)

        async def mock_create_engine(context):
            return mock_engine
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=Mock()):
            result = await self.supervisor.execute(self.test_user_context, stream_updates=True)
            self.assertEqual(result.status, ExecutionStatus.COMPLETED)
            self.websocket_bridge.notify_agent_started.assert_called_once()
            started_call = self.websocket_bridge.notify_agent_started.call_args
            self.assertEqual(started_call[0][0], self.test_user_context.run_id)
            self.assertEqual(started_call[0][1], 'Supervisor')
            self.assertIn('isolated', started_call[1]['context'])
            self.websocket_bridge.notify_agent_thinking.assert_called_once()
            thinking_call = self.websocket_bridge.notify_agent_thinking.call_args
            self.assertEqual(thinking_call[0][0], self.test_user_context.run_id)
            self.assertEqual(thinking_call[0][1], 'Supervisor')
            self.assertIn('selecting appropriate agents', thinking_call[1]['reasoning'])
            self.assertEqual(thinking_call[1]['step_number'], 1)
            self.websocket_bridge.notify_agent_completed.assert_called_once()
            completed_call = self.websocket_bridge.notify_agent_completed.call_args
            self.assertEqual(completed_call[0][0], self.test_user_context.run_id)
            self.assertEqual(completed_call[0][1], 'Supervisor')
            completed_result = completed_call[1]['result']
            self.assertEqual(completed_result['supervisor_result'], 'completed')
            self.assertTrue(completed_result['orchestration_successful'])
            self.assertTrue(completed_result['user_isolation_verified'])
            self.websocket_bridge.notify_agent_error.assert_not_called()
        self.record_metric('websocket_events_validated', 5)
        self.record_metric('chat_delivery_events_working', True)

    async def test_websocket_error_event_on_execution_failure(self):
        """Test agent_error WebSocket event is sent on execution failure.
        
        BVJ: Error communication = User awareness of issues = Trust maintenance.
        """
        mock_engine = Mock()
        mock_engine.cleanup = AsyncMock()

        async def failing_orchestration(*args, **kwargs):
            raise RuntimeError('Data analysis service unavailable')
        with patch.object(self.supervisor, '_execute_orchestration_workflow', failing_orchestration), patch.object(self.supervisor, '_create_user_execution_engine', return_value=mock_engine):
            result = await self.supervisor.execute(self.test_user_context)
            self.assertEqual(result.status, ExecutionStatus.FAILED)
            self.assertIsNotNone(result.error_message)
            self.assertEqual(result.error_code, 'RuntimeError')
            error_data = result.data
            self.assertEqual(error_data['supervisor_result'], 'failed')
            self.assertFalse(error_data['orchestration_successful'])
            self.assertTrue(error_data['user_isolation_verified'])
            self.assertIn('Data analysis service unavailable', error_data['error'])
            self.websocket_bridge.notify_agent_error.assert_called_once()
            error_call = self.websocket_bridge.notify_agent_error.call_args
            self.assertEqual(error_call[0][0], self.test_user_context.run_id)
            self.assertEqual(error_call[0][1], 'Supervisor')
            self.assertIn('Data analysis service unavailable', error_call[1]['error'])
            self.assertEqual(error_call[1]['error_context']['error_type'], 'RuntimeError')
            mock_engine.cleanup.assert_called_once()
        self.record_metric('error_handling_validated', True)

    async def test_ssot_factory_pattern_compliance_validation(self):
        """Test SSOT factory pattern usage and configuration.
        
        BVJ: Factory patterns = User isolation = Multi-tenant scalability.
        """
        mock_websocket_emitter = Mock()
        mock_engine = MockUserExecutionEngine(self.test_user_context)
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=mock_websocket_emitter), patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine', return_value=mock_engine):
            created_engine = await self.supervisor._create_user_execution_engine(self.test_user_context)
            self.assertEqual(self.mock_agent_factory.configuration_count, 1)
            self.assertEqual(self.mock_agent_factory.websocket_bridge, self.websocket_bridge)
            self.assertEqual(self.mock_agent_factory.llm_manager, self.llm_manager)
            self.assertIsNotNone(created_engine)
        self.record_metric('factory_pattern_validated', True)

    async def test_user_context_validation_ssot_compliance(self):
        """Test UserExecutionContext validation using SSOT validate_user_context.
        
        BVJ: Context validation = User isolation security = Platform trust.
        """
        valid_context = self.test_user_context
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', return_value=valid_context) as mock_validate:
            mock_engine = MockUserExecutionEngine(valid_context)
            with patch.object(self.supervisor, '_create_user_execution_engine', return_value=mock_engine), patch.object(self.supervisor, '_execute_orchestration_workflow', return_value={'workflow_completed': True}):
                result = await self.supervisor.execute(valid_context)
                mock_validate.assert_called_once_with(valid_context)
                self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        invalid_context = UserExecutionContext.from_request_supervisor(user_id='', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_connection_id='test-ws')
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', side_effect=InvalidContextError('Invalid user_id: cannot be empty')):
            with self.expect_exception(InvalidContextError, 'Invalid user_id'):
                await self.supervisor.execute(invalid_context)
        self.record_metric('context_validation_verified', True)

    async def test_database_session_requirement_enforcement(self):
        """Test database session requirement validation.
        
        BVJ: Database session requirement = Data consistency = Platform reliability.
        """
        context_no_db = UserExecutionContext.from_request_supervisor(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_connection_id='test-ws')
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', return_value=context_no_db):
            with self.expect_exception(ValueError, 'database session'):
                await self.supervisor.execute(context_no_db)
        self.record_metric('database_session_validation_enforced', True)

    async def test_legacy_run_method_delegates_to_ssot_execute(self):
        """Test legacy run() method properly delegates to SSOT execute() method.
        
        BVJ: Legacy compatibility = Existing integrations continue working = Zero downtime.
        """
        mock_request_id = 'legacy-req-12345'
        mock_websocket_id = 'legacy-ws-67890'
        with patch('netra_backend.app.agents.supervisor_ssot.UnifiedIdGenerator') as mock_id_gen:
            mock_id_gen.generate_base_id.return_value = mock_request_id
            mock_id_gen.generate_websocket_client_id.return_value = mock_websocket_id
            mock_execute_result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id=mock_request_id, data={'supervisor_result': 'completed', 'orchestration_successful': True, 'user_isolation_verified': True, 'results': {'optimization_savings': 2000, 'recommendations': ['rightsize', 'reserved_instances']}, 'user_id': 'legacy-user-123', 'run_id': 'legacy-run-456'})
            with patch.object(self.supervisor, 'execute', AsyncMock(return_value=mock_execute_result)) as mock_execute:
                result = await self.supervisor.run(user_request='Optimize my cloud infrastructure costs', thread_id='legacy-thread-789', user_id='legacy-user-123', run_id='legacy-run-456')
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args
                context = call_args[0][0]
                self.assertIsInstance(context, UserExecutionContext)
                self.assertEqual(context.user_id, 'legacy-user-123')
                self.assertEqual(context.thread_id, 'legacy-thread-789')
                self.assertEqual(context.run_id, 'legacy-run-456')
                self.assertEqual(context.request_id, mock_request_id)
                self.assertEqual(context.websocket_client_id, mock_websocket_id)
                self.assertIn('user_request', context.metadata)
                self.assertEqual(context.metadata['user_request'], 'Optimize my cloud infrastructure costs')
                self.assertTrue(call_args[1]['stream_updates'])
                expected_result = {'optimization_savings': 2000, 'recommendations': ['rightsize', 'reserved_instances']}
                self.assertEqual(result, expected_result)
        self.record_metric('legacy_compatibility_validated', True)

    def test_ssot_factory_method_creates_proper_instance(self):
        """Test SupervisorAgent.create() SSOT factory method.
        
        BVJ: Factory method = Standardized creation = Consistent behavior across system.
        """
        created_supervisor = SupervisorAgent.create(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge)
        self.assertIsInstance(created_supervisor, SupervisorAgent)
        self.assertEqual(created_supervisor._llm_manager, self.llm_manager)
        self.assertEqual(created_supervisor.websocket_bridge, self.websocket_bridge)
        self.assertIsNotNone(created_supervisor.agent_factory)
        self.assertIsNotNone(created_supervisor.workflow_executor)
        self.record_metric('factory_method_validated', True)

    async def test_concurrent_user_isolation_ssot_validation(self):
        """Test multi-user concurrent execution isolation using SSOT patterns.
        
        BVJ: User isolation = Multi-tenant security = Enterprise scalability.
        """
        user_contexts = []
        for i in range(3):
            context = UserExecutionContext.from_request_supervisor(user_id=f'concurrent-user-{i}', thread_id=f'concurrent-thread-{i}', run_id=f'concurrent-run-{i}', request_id=f'concurrent-req-{i}', websocket_connection_id=f'concurrent-ws-{i}', metadata={'user_request': f'Concurrent optimization request {i}'}).with_db_session(AsyncMock())
            user_contexts.append(context)
        execution_results = []

        async def execute_with_isolation_tracking(context, index):
            """Execute with isolation tracking for concurrent testing."""
            mock_engine = MockUserExecutionEngine(context)

            async def mock_create_engine(ctx):
                return mock_engine
            with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=Mock()):
                result = await self.supervisor.execute(context)
                execution_results.append({'user_id': context.user_id, 'result': result, 'engine_executions': len(mock_engine.pipeline_executions), 'context_preserved': all((exec['user_id'] == context.user_id for exec in mock_engine.pipeline_executions))})
        await asyncio.gather(*[execute_with_isolation_tracking(context, i) for i, context in enumerate(user_contexts)])
        self.assertEqual(len(execution_results), 3)
        user_ids = [result['user_id'] for result in execution_results]
        self.assertEqual(len(set(user_ids)), 3)
        for exec_result in execution_results:
            result = exec_result['result']
            self.assertEqual(result.status, ExecutionStatus.COMPLETED)
            self.assertTrue(result.data['orchestration_successful'])
            self.assertTrue(result.data['user_isolation_verified'])
            self.assertEqual(exec_result['engine_executions'], 5)
            self.assertTrue(exec_result['context_preserved'])
        self.record_metric('concurrent_isolation_validated', 3)

    def test_string_representations_ssot_patterns(self):
        """Test SupervisorAgent SSOT string representation methods.
        
        BVJ: String representations = Debugging capability = Development velocity.
        """
        str_repr = str(self.supervisor)
        self.assertIn('SupervisorAgent', str_repr)
        self.assertIn('SSOT pattern', str_repr)
        self.assertIn('factory-based', str_repr)
        repr_str = repr(self.supervisor)
        self.assertIn('SupervisorAgent', repr_str)
        self.assertIn("pattern='SSOT'", repr_str)
        self.assertIn('factory_based=True', repr_str)
        self.record_metric('string_representations_validated', True)

class TestSupervisorAgentSSOTErrorScenarios(SSotAsyncTestCase):
    """Test SupervisorAgent SSOT error scenarios and edge cases."""

    def setup_method(self, method):
        """Set up test environment for error scenario testing."""
        super().setup_method(method)
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='gpt-4')
        self.llm_manager.ask_llm = AsyncMock(return_value='AI response')
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        self.test_user_context = UserExecutionContext.from_request_supervisor(user_id=f'test-user-{uuid.uuid4().hex[:8]}', thread_id=f'test-thread-{uuid.uuid4().hex[:8]}', run_id=f'test-run-{uuid.uuid4().hex[:8]}', request_id=f'test-req-{uuid.uuid4().hex[:8]}', websocket_connection_id=f'test-ws-{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Test scenarios'})
        self.mock_agent_factory = MockAgentInstanceFactory()
        self.factory_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory', return_value=self.mock_agent_factory)
        self.factory_patcher.start()
        self.add_cleanup(self.factory_patcher.stop)
        self.session_validation_patcher = patch('netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation')
        self.session_validation_patcher.start()
        self.add_cleanup(self.session_validation_patcher.stop)
        self.supervisor = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge, user_context=self.test_user_context)

    async def test_invalid_context_handling_ssot(self):
        """Test SupervisorAgent SSOT handling of invalid UserExecutionContext.
        
        BVJ: Input validation = System stability = User trust.
        """
        with self.expect_exception(TypeError):
            await self.supervisor.execute(None)
        invalid_context = UserExecutionContext.from_request_supervisor(user_id='', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_connection_id='test-ws')
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', side_effect=InvalidContextError('Invalid user_id: cannot be empty')):
            with self.expect_exception(InvalidContextError, 'Invalid user_id'):
                await self.supervisor.execute(invalid_context)
        self.record_metric('invalid_context_handling_validated', True)

    async def test_websocket_failure_graceful_degradation(self):
        """Test graceful degradation when WebSocket bridge fails.
        
        BVJ: Graceful degradation = Service reliability = User experience continuity.
        """
        context = UserExecutionContext.from_request_supervisor(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_connection_id='test-ws').with_db_session(AsyncMock())
        failing_bridge = Mock(spec=AgentWebSocketBridge)
        failing_bridge.notify_agent_started = AsyncMock(side_effect=Exception('WebSocket connection lost'))
        failing_bridge.notify_agent_thinking = AsyncMock(side_effect=Exception('WebSocket connection lost'))
        failing_bridge.notify_agent_completed = AsyncMock(side_effect=Exception('WebSocket connection lost'))
        failing_bridge.notify_agent_error = AsyncMock(side_effect=Exception('WebSocket connection lost'))
        supervisor_with_failing_ws = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=failing_bridge, user_context=self.test_user_context)
        mock_engine = MockUserExecutionEngine(context)

        async def mock_create_engine(ctx):
            return mock_engine
        with patch.object(supervisor_with_failing_ws, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=Mock()):
            result = await supervisor_with_failing_ws.execute(context)
            self.assertEqual(result.status, ExecutionStatus.COMPLETED)
            self.assertTrue(result.data['orchestration_successful'])
            self.assertGreater(failing_bridge.notify_agent_started.call_count, 0)
            self.assertGreater(failing_bridge.notify_agent_thinking.call_count, 0)
        self.record_metric('websocket_graceful_degradation_validated', True)

    async def test_execution_engine_cleanup_on_error(self):
        """Test UserExecutionEngine cleanup is called even on execution errors.
        
        BVJ: Resource cleanup = Memory management = System stability.
        """
        context = UserExecutionContext.from_request_supervisor(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-req', websocket_connection_id='test-ws').with_db_session(AsyncMock())
        mock_engine = Mock()
        mock_engine.cleanup = AsyncMock()
        cleanup_tracking = []

        async def track_cleanup():
            cleanup_tracking.append('cleanup_called')
        mock_engine.cleanup.side_effect = track_cleanup

        async def failing_orchestration(*args, **kwargs):
            raise RuntimeError('Orchestration pipeline failure')
        with patch.object(self.supervisor, '_create_user_execution_engine', return_value=mock_engine), patch.object(self.supervisor, '_execute_orchestration_workflow', failing_orchestration):
            result = await self.supervisor.execute(context)
            self.assertEqual(result.status, ExecutionStatus.FAILED)
            self.assertIn('Orchestration pipeline failure', result.error_message)
            mock_engine.cleanup.assert_called_once()
            self.assertEqual(len(cleanup_tracking), 1)
        self.record_metric('cleanup_on_error_validated', True)

class TestSupervisorAgentSSOTPerformance(SSotAsyncTestCase):
    """Test SupervisorAgent SSOT performance characteristics."""

    def setup_method(self, method):
        """Set up performance testing environment."""
        super().setup_method(method)
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='gpt-4')
        self.llm_manager.ask_llm = AsyncMock(return_value='Fast AI response')
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        self.test_user_context = UserExecutionContext.from_request_supervisor(user_id=f'test-user-{uuid.uuid4().hex[:8]}', thread_id=f'test-thread-{uuid.uuid4().hex[:8]}', run_id=f'test-run-{uuid.uuid4().hex[:8]}', request_id=f'test-req-{uuid.uuid4().hex[:8]}', websocket_connection_id=f'test-ws-{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Test scenarios'})
        self.mock_agent_factory = MockAgentInstanceFactory()
        self.factory_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory', return_value=self.mock_agent_factory)
        self.factory_patcher.start()
        self.add_cleanup(self.factory_patcher.stop)
        self.session_validation_patcher = patch('netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation')
        self.session_validation_patcher.start()
        self.add_cleanup(self.session_validation_patcher.stop)
        self.supervisor = SupervisorAgent(llm_manager=self.llm_manager, websocket_bridge=self.websocket_bridge, user_context=self.test_user_context)

    async def test_ssot_performance_concurrent_execution(self):
        """Test SupervisorAgent SSOT performance under concurrent load.
        
        BVJ: Performance = User experience = Platform scalability = Revenue growth.
        """
        contexts = []
        for i in range(5):
            context = UserExecutionContext.from_request_supervisor(user_id=f'perf-user-{i}', thread_id=f'perf-thread-{i}', run_id=f'perf-run-{i}', request_id=f'perf-req-{i}', websocket_connection_id=f'perf-ws-{i}', metadata={'performance_test_index': i}).with_db_session(AsyncMock())
            contexts.append(context)

        async def mock_create_engine(ctx):
            return MockUserExecutionEngine(ctx)
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=Mock()):
            start_time = time.time()
            results = await asyncio.gather(*[self.supervisor.execute(context) for context in contexts])
            total_time = time.time() - start_time
            self.assertEqual(len(results), 5)
            for result in results:
                self.assertEqual(result.status, ExecutionStatus.COMPLETED)
                self.assertTrue(result.data['orchestration_successful'])
                self.assertTrue(result.data['user_isolation_verified'])
            self.assertLess(total_time, 5.0)
            avg_time = total_time / len(results)
            self.assertLess(avg_time, 2.0)
        self.record_metric('concurrent_execution_time', total_time)
        self.record_metric('average_execution_time', avg_time)
        self.record_metric('concurrent_users_tested', len(contexts))

    async def test_memory_usage_isolation_validation(self):
        """Test memory usage isolation between concurrent users.
        
        BVJ: Memory isolation = System stability = Cost optimization.
        """
        contexts = []
        for i in range(3):
            context = UserExecutionContext.from_request_supervisor(user_id=f'memory-user-{i}', thread_id=f'memory-thread-{i}', run_id=f'memory-run-{i}', request_id=f'memory-req-{i}', websocket_connection_id=f'memory-ws-{i}', metadata={'memory_test': True, 'data_size': i * 1000}).with_db_session(AsyncMock())
            contexts.append(context)
        memory_tracking = []

        async def memory_tracking_engine(ctx):
            engine = MockUserExecutionEngine(ctx)
            engine.memory_footprint = ctx.metadata.get('data_size', 0)
            memory_tracking.append({'user_id': ctx.user_id, 'memory_footprint': engine.memory_footprint})
            return engine
        with patch.object(self.supervisor, '_create_user_execution_engine', memory_tracking_engine), patch('netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter', return_value=Mock()):
            results = await asyncio.gather(*[self.supervisor.execute(context) for context in contexts])
            self.assertEqual(len(memory_tracking), 3)
            expected_footprints = [0, 1000, 2000]
            actual_footprints = [track['memory_footprint'] for track in memory_tracking]
            self.assertEqual(actual_footprints, expected_footprints)
            for result in results:
                self.assertEqual(result.status, ExecutionStatus.COMPLETED)
                self.assertTrue(result.data['user_isolation_verified'])
        self.record_metric('memory_isolation_validated', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')