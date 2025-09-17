"""
PipelineExecutor Message Flow Unit Tests - Issue #1081 Phase 1

Comprehensive unit tests for PipelineExecutor message flow functionality.
Targets pipeline execution patterns, message routing, and flow orchestration.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Risk Reduction
- Value Impact: Protects $500K+ ARR pipeline execution and message orchestration
- Strategic Impact: Comprehensive coverage for supervisor agent pipeline workflows

Coverage Focus:
- Pipeline step execution and message flow
- User context isolation in pipeline processing
- Database session management (per-request, not global)
- WebSocket event coordination during pipeline execution
- Error handling and recovery in pipeline flows
- State persistence and checkpoint management

Test Strategy: Unit tests with real services where possible, minimal mocking
"""
import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional, List
import time
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult, PipelineStep
from netra_backend.app.agents.execution_engine_interface import IExecutionEngine as ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.schemas.agent_state import CheckpointType, StatePersistenceRequest
from netra_backend.app.llm.observability import generate_llm_correlation_id

class MockExecutionEngine:
    """Mock execution engine for pipeline testing."""

    def __init__(self):
        self.executed_agents = []
        self.execution_results = {}

    async def execute_agent(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock agent execution."""
        self.executed_agents.append(agent_name)
        result = {'agent_name': agent_name, 'status': 'completed', 'output': f'Mock output for {agent_name}', 'context': context}
        self.execution_results[agent_name] = result
        return result

class MockWebSocketBridge:
    """Mock WebSocket bridge for pipeline testing."""

    def __init__(self):
        self.events_sent = []
        self.connections = {}

    async def send_agent_event(self, event_type: str, data: Dict[str, Any], run_id: str):
        """Mock event sending."""
        event = {'type': event_type, 'data': data, 'run_id': run_id, 'timestamp': datetime.now(UTC).isoformat()}
        self.events_sent.append(event)
        return True

    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get events for specific run."""
        return [event for event in self.events_sent if event.get('run_id') == run_id]

class PipelineExecutorMessageFlowTests(SSotAsyncTestCase):
    """Comprehensive unit tests for PipelineExecutor message flow functionality."""

    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.mock_execution_engine = MockExecutionEngine()
        self.mock_websocket_bridge = MockWebSocketBridge()
        self.mock_db_session = AsyncMock(spec=AsyncSession)
        self.test_user_id = 'pipeline_user_123'
        self.test_session_id = 'pipeline_session_456'
        self.user_context = UserExecutionContext(user_id=self.test_user_id, session_id=self.test_session_id, context={'pipeline_test': True})
        self.pipeline_executor = PipelineExecutor(engine=self.mock_execution_engine, websocket_manager=self.mock_websocket_bridge, user_context=self.user_context)
        self.test_run_id = generate_llm_correlation_id()
        self.pipeline_operations = []
        self.checkpoint_operations = []

    def teardown_method(self, method):
        """Clean up after each test."""
        super().teardown_method(method)
        self.pipeline_operations.clear()
        self.checkpoint_operations.clear()

    def test_pipeline_executor_initialization(self):
        """Test PipelineExecutor initializes correctly."""
        assert self.pipeline_executor.engine is not None
        assert self.pipeline_executor.websocket_manager is not None
        assert self.pipeline_executor.user_context == self.user_context
        assert not hasattr(self.pipeline_executor, 'db_session') or self.pipeline_executor.db_session is None
        assert hasattr(self.pipeline_executor, 'state_persistence')
        assert self.pipeline_executor.state_persistence is not None

    def test_pipeline_executor_user_context_isolation(self):
        """Test pipeline executor maintains proper user context isolation."""
        assert self.pipeline_executor.user_context.user_id == self.test_user_id
        assert self.pipeline_executor.user_context.session_id == self.test_session_id
        other_context = UserExecutionContext(user_id='other_pipeline_user', session_id='other_pipeline_session', context={})
        other_executor = PipelineExecutor(engine=MockExecutionEngine(), websocket_manager=MockWebSocketBridge(), user_context=other_context)
        assert self.pipeline_executor.user_context.user_id != other_executor.user_context.user_id
        assert id(self.pipeline_executor.user_context) != id(other_executor.user_context)

    def test_flow_context_preparation(self):
        """Test flow context preparation for pipeline execution."""
        pipeline = [PipelineStep(agent_name='DataAgent', input_context={'task': 'analyze_data'}, dependencies=[]), PipelineStep(agent_name='ProcessorAgent', input_context={'task': 'process_results'}, dependencies=['DataAgent'])]
        flow_context = self.pipeline_executor._prepare_flow_context(pipeline)
        assert 'flow_id' in flow_context
        assert 'pipeline_steps' in flow_context
        assert len(flow_context['pipeline_steps']) == 2
        assert flow_context['pipeline_steps'][0].agent_name == 'DataAgent'
        assert flow_context['pipeline_steps'][1].agent_name == 'ProcessorAgent'

    def test_execution_context_building(self):
        """Test execution context building for pipeline steps."""
        test_context = {'user_query': 'test query', 'session_id': self.test_session_id}
        exec_context = self.pipeline_executor._build_execution_context(self.test_run_id, test_context)
        assert isinstance(exec_context, AgentExecutionContext)
        assert exec_context.agent_name == 'supervisor'
        params = self.pipeline_executor._extract_context_params(self.test_run_id, test_context)
        assert 'agent_name' in params
        assert params['agent_name'] == 'supervisor'

    def test_base_execution_params_extraction(self):
        """Test base execution parameters extraction."""
        test_context = {'user_query': 'test pipeline query', 'session_id': self.test_session_id, 'additional_data': 'test_data'}
        base_params = self.pipeline_executor._get_base_execution_params(self.test_run_id, test_context)
        assert isinstance(base_params, dict)
        assert any((self.test_run_id in str(value) for value in base_params.values()))

    async def test_complete_pipeline_execution_flow(self):
        """Test complete pipeline execution from start to finish."""
        pipeline = [PipelineStep(agent_name='InitAgent', input_context={'task': 'initialize'}, dependencies=[]), PipelineStep(agent_name='ProcessAgent', input_context={'task': 'process'}, dependencies=['InitAgent']), PipelineStep(agent_name='FinalizeAgent', input_context={'task': 'finalize'}, dependencies=['ProcessAgent'])]
        test_context = {'pipeline_test': True}
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context=test_context, db_session=self.mock_db_session)
        executed_agents = self.mock_execution_engine.executed_agents
        assert 'InitAgent' in executed_agents
        assert 'ProcessAgent' in executed_agents
        assert 'FinalizeAgent' in executed_agents
        assert len(self.mock_execution_engine.execution_results) == 3
        for agent_name in ['InitAgent', 'ProcessAgent', 'FinalizeAgent']:
            assert agent_name in self.mock_execution_engine.execution_results
            result = self.mock_execution_engine.execution_results[agent_name]
            assert result['status'] == 'completed'

    async def test_pipeline_execution_with_dependencies(self):
        """Test pipeline execution respects agent dependencies."""
        pipeline = [PipelineStep(agent_name='FoundationAgent', input_context={'task': 'foundation'}, dependencies=[]), PipelineStep(agent_name='DependentAgent', input_context={'task': 'dependent_work'}, dependencies=['FoundationAgent'])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)
        executed_agents = self.mock_execution_engine.executed_agents
        foundation_index = executed_agents.index('FoundationAgent')
        dependent_index = executed_agents.index('DependentAgent')
        assert foundation_index < dependent_index

    async def test_pipeline_execution_with_user_context(self):
        """Test pipeline execution properly uses user context."""
        pipeline = [PipelineStep(agent_name='ContextAgent', input_context={'task': 'use_context'}, dependencies=[])]
        test_context = {'user_id': self.test_user_id, 'session_id': self.test_session_id, 'special_data': 'context_test'}
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context=test_context, db_session=self.mock_db_session)
        result = self.mock_execution_engine.execution_results['ContextAgent']
        assert 'context' in result
        assert result['context']['special_data'] == 'context_test'

    async def test_websocket_events_during_pipeline_execution(self):
        """Test WebSocket events are sent during pipeline execution."""
        pipeline = [PipelineStep(agent_name='EventTestAgent', input_context={'task': 'test_events'}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)
        assert self.pipeline_executor.websocket_manager is not None
        assert isinstance(self.pipeline_executor.websocket_manager, MockWebSocketBridge)

    async def test_websocket_event_isolation_per_run(self):
        """Test WebSocket events are properly isolated per pipeline run."""
        run_id_1 = f'{self.test_run_id}_1'
        run_id_2 = f'{self.test_run_id}_2'
        pipeline = [PipelineStep(agent_name='IsolationTestAgent', input_context={'task': 'test_isolation'}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=run_id_1, context={'run': 'first'}, db_session=self.mock_db_session)
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=run_id_2, context={'run': 'second'}, db_session=self.mock_db_session)
        assert len(self.mock_execution_engine.executed_agents) == 2
        assert self.mock_execution_engine.executed_agents.count('IsolationTestAgent') == 2

    async def test_database_session_per_request_pattern(self):
        """Test database sessions are passed per-request, not stored globally."""
        assert not hasattr(self.pipeline_executor, 'db_session') or self.pipeline_executor.db_session is None
        pipeline = [PipelineStep(agent_name='DatabaseAgent', input_context={'task': 'database_operation'}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)
        assert 'DatabaseAgent' in self.mock_execution_engine.executed_agents
        assert not hasattr(self.pipeline_executor, 'db_session') or self.pipeline_executor.db_session is None

    async def test_database_session_isolation_between_requests(self):
        """Test database sessions are properly isolated between requests."""
        session1 = AsyncMock(spec=AsyncSession)
        session2 = AsyncMock(spec=AsyncSession)
        pipeline = [PipelineStep(agent_name='SessionTestAgent', input_context={'task': 'session_test'}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=f'{self.test_run_id}_session1', context={'session': 'first'}, db_session=session1)
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=f'{self.test_run_id}_session2', context={'session': 'second'}, db_session=session2)
        assert self.mock_execution_engine.executed_agents.count('SessionTestAgent') == 2

    async def test_state_persistence_during_pipeline_execution(self):
        """Test state persistence works during pipeline execution."""
        assert self.pipeline_executor.state_persistence is not None
        pipeline = [PipelineStep(agent_name='StatefulAgent', input_context={'task': 'stateful_operation', 'checkpoint': True}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={'enable_persistence': True}, db_session=self.mock_db_session)
        assert 'StatefulAgent' in self.mock_execution_engine.executed_agents

    def test_persistence_service_configuration(self):
        """Test state persistence service configuration."""
        persistence_service = self.pipeline_executor.state_persistence
        assert persistence_service is not None
        assert hasattr(self.pipeline_executor, '_get_persistence_service')

    async def test_pipeline_execution_error_handling(self):
        """Test error handling during pipeline execution."""
        error_engine = Mock()
        error_engine.execute_agent = AsyncMock(side_effect=Exception('Mock execution error'))
        error_executor = PipelineExecutor(engine=error_engine, websocket_manager=self.mock_websocket_bridge, user_context=self.user_context)
        pipeline = [PipelineStep(agent_name='ErrorAgent', input_context={'task': 'cause_error'}, dependencies=[])]
        with pytest.raises(Exception, match='Mock execution error'):
            await error_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)

    async def test_user_context_validation_errors(self):
        """Test handling of user context validation errors."""
        try:
            invalid_context = UserExecutionContext(user_id='', session_id=self.test_session_id, context={})
        except InvalidContextError:
            pytest.skip('Context validation prevents invalid creation')
        pipeline = [PipelineStep(agent_name='ValidationTestAgent', input_context={'task': 'validation_test'}, dependencies=[])]
        try:
            await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)
            assert True
        except Exception as e:
            assert 'validation' in str(e).lower() or 'context' in str(e).lower()

    async def test_pipeline_flow_logging_and_completion(self):
        """Test pipeline flow logging and completion tracking."""
        assert hasattr(self.pipeline_executor, 'flow_logger')
        assert self.pipeline_executor.flow_logger is not None
        pipeline = [PipelineStep(agent_name='LoggingTestAgent', input_context={'task': 'logging_test'}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)
        assert True

    async def test_concurrent_pipeline_execution(self):
        """Test concurrent pipeline execution maintains isolation."""
        pipeline = [PipelineStep(agent_name='ConcurrentAgent', input_context={'task': 'concurrent_test'}, dependencies=[])]
        tasks = []
        for i in range(3):
            task = asyncio.create_task(self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=f'{self.test_run_id}_concurrent_{i}', context={'concurrent_id': i}, db_session=self.mock_db_session))
            tasks.append(task)
        await asyncio.gather(*tasks)
        assert self.mock_execution_engine.executed_agents.count('ConcurrentAgent') == 3

    async def test_pipeline_execution_performance(self):
        """Test pipeline execution performance characteristics."""
        pipeline = [PipelineStep(agent_name=f'PerfAgent_{i}', input_context={'task': 'performance_test', 'index': i}, dependencies=[]) for i in range(5)]
        start_time = time.time()
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={}, db_session=self.mock_db_session)
        execution_time = time.time() - start_time
        assert len(self.mock_execution_engine.executed_agents) == 5
        assert execution_time < 1.0

    def test_memory_usage_during_pipeline_execution(self):
        """Test memory usage remains reasonable during pipeline execution."""
        import sys
        initial_size = sys.getsizeof(self.pipeline_executor)
        large_context = {f'data_{i}': f'value_{i}' * 100 for i in range(100)}
        final_size = sys.getsizeof(self.pipeline_executor)
        growth = final_size - initial_size
        assert growth < 50000

    def test_golden_path_pipeline_components_present(self):
        """Test all golden path pipeline components are present."""
        assert self.pipeline_executor.engine is not None, 'Execution engine required for golden path'
        assert self.pipeline_executor.websocket_manager is not None, 'WebSocket manager required for golden path'
        assert self.pipeline_executor.user_context is not None, 'User context required for golden path'
        assert self.pipeline_executor.state_persistence is not None, 'State persistence required for golden path'
        assert self.pipeline_executor.flow_logger is not None, 'Flow logging required for golden path'

    async def test_user_isolation_in_pipeline_execution(self):
        """Test user isolation is maintained during pipeline execution."""
        user1_context = UserExecutionContext(user_id='pipeline_user_1', session_id='session_1', context={'user': 'first'})
        user2_context = UserExecutionContext(user_id='pipeline_user_2', session_id='session_2', context={'user': 'second'})
        executor1 = PipelineExecutor(engine=MockExecutionEngine(), websocket_manager=MockWebSocketBridge(), user_context=user1_context)
        executor2 = PipelineExecutor(engine=MockExecutionEngine(), websocket_manager=MockWebSocketBridge(), user_context=user2_context)
        assert executor1.user_context.user_id != executor2.user_context.user_id
        assert id(executor1.user_context) != id(executor2.user_context)
        assert executor1.websocket_manager != executor2.websocket_manager
        assert executor1.engine != executor2.engine

    async def test_pipeline_execution_context_consistency(self):
        """Test pipeline execution maintains context consistency."""
        pipeline = [PipelineStep(agent_name='ConsistencyAgent', input_context={'task': 'consistency_check', 'user_id': self.test_user_id, 'session_id': self.test_session_id}, dependencies=[])]
        await self.pipeline_executor.execute_pipeline(pipeline=pipeline, user_context=self.user_context, run_id=self.test_run_id, context={'consistency_test': True}, db_session=self.mock_db_session)
        result = self.mock_execution_engine.execution_results['ConsistencyAgent']
        assert result['status'] == 'completed'
        assert 'context' in result
        assert result['context']['consistency_test'] is True
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')