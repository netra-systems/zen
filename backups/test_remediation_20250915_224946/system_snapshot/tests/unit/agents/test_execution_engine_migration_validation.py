"""Validation tests for execution engine migration to UserExecutionContext pattern.

This test suite validates that the migration from DeepAgentState to UserExecutionContext
preserves all business-critical functionality while improving security and isolation.

Business Impact: Ensures WebSocket events, agent execution, and user isolation work correctly.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine, ExecutionEngineFactory, AgentExecutionContext, AgentExecutionResult
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as SupervisorExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult as SupervisorAgentExecutionResult
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory as SupervisorExecutionEngineFactory, get_execution_engine_factory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.mcp_execution_engine import MCPEnhancedExecutionEngine, create_mcp_enhanced_engine

@pytest.mark.unit
class ExecutionEngineMigrationValidationTests:
    """Validate migration from DeepAgentState to UserExecutionContext."""

    @pytest.fixture
    def user_context(self):
        """Create a test UserExecutionContext using SSOT services implementation."""
        return UserExecutionContext(user_id='test_user_123', thread_id='thread_789', run_id='run_456', request_id='req_789')

    @pytest.fixture
    def mock_agent_registry(self):
        """Mock agent registry."""
        registry = Mock()
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value='test_result')
        registry.get_agent = Mock(return_value=mock_agent)
        return registry

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Mock WebSocket bridge."""
        bridge = AsyncMock()
        bridge.notify_agent_started = AsyncMock()
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_agent_error = AsyncMock()
        bridge.notify_agent_thinking = AsyncMock()
        return bridge

    @pytest.mark.asyncio
    async def test_consolidated_execution_engine_user_context_integration(self, user_context, mock_agent_registry, mock_websocket_bridge):
        """Test that ExecutionEngine properly integrates UserExecutionContext."""
        engine = UserExecutionEngine(registry=mock_agent_registry, websocket_bridge=mock_websocket_bridge, user_context=user_context)
        await engine.initialize()
        result = await engine.execute(agent_name='test_agent', task='test_task', user_context=user_context)
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.execution_time_ms is not None
        mock_websocket_bridge.notify_agent_started.assert_called()
        mock_websocket_bridge.notify_agent_completed.assert_called()
        await engine.cleanup()

    @pytest.mark.asyncio
    async def test_supervisor_execution_engine_user_context_delegation(self, user_context, mock_agent_registry, mock_websocket_bridge):
        """Test that supervisor ExecutionEngine properly delegates to UserExecutionEngine."""
        with patch('netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine._init_from_factory'):
            engine = SupervisorExecutionEngine._init_from_factory(registry=mock_agent_registry, websocket_bridge=mock_websocket_bridge, user_context=user_context)
            agent_context = Mock()
            agent_context.agent_name = 'test_agent'
            agent_context.run_id = 'test_run_123'
            agent_context.user_id = user_context.user_id
            agent_context.thread_id = user_context.thread_id
            agent_context.metadata = {}
            agent_context.retry_count = 0
            agent_context.max_retries = 3
            mock_user_engine = AsyncMock()
            mock_user_engine.execute_agent = AsyncMock(return_value=Mock(success=True))
            mock_user_engine.cleanup = AsyncMock()
            with patch.object(engine, 'create_user_engine', return_value=mock_user_engine):
                result = await engine.execute_agent(agent_context, user_context)
                mock_user_engine.execute_agent.assert_called_once()
                mock_user_engine.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_isolated_execution_engine_user_specific_state(self, user_context, mock_agent_registry):
        """Test that IsolatedExecutionEngine maintains user-specific state."""
        mock_websocket_emitter = AsyncMock()
        mock_websocket_emitter.notify_agent_started = AsyncMock()
        mock_websocket_emitter.notify_agent_completed = AsyncMock()
        mock_websocket_emitter.cleanup = AsyncMock()
        mock_factory = Mock()
        mock_factory.config.max_history_per_user = 100
        mock_factory.cleanup_context = AsyncMock()
        engine = IsolatedExecutionEngine(user_context=user_context, agent_registry=mock_agent_registry, websocket_emitter=mock_websocket_emitter, execution_semaphore=asyncio.Semaphore(5), execution_timeout=30.0, factory=mock_factory)
        assert engine.user_context == user_context
        assert engine.user_context.user_id == 'test_user_123'
        assert engine.user_context.request_id == 'req_456'
        status = engine.get_status()
        assert status['user_id'] == user_context.user_id
        assert status['request_id'] == user_context.request_id
        assert status['active_runs'] == []
        await engine.cleanup()
        mock_factory.cleanup_context.assert_called_once_with(user_context.request_id)

    @pytest.mark.asyncio
    async def test_mcp_execution_engine_user_context_integration(self, user_context, mock_agent_registry, mock_websocket_bridge):
        """Test that MCPEnhancedExecutionEngine properly handles UserExecutionContext."""
        engine = create_mcp_enhanced_engine(user_context=user_context, registry=mock_agent_registry, websocket_bridge=mock_websocket_bridge)
        agent_context = Mock()
        agent_context.agent_name = 'test_agent'
        agent_context.user_id = user_context.user_id
        agent_context.run_id = 'test_run_123'
        user_context.metadata['current_request'] = None
        with patch.object(SupervisorExecutionEngine, 'execute_agent') as mock_parent_execute:
            mock_parent_execute.return_value = AsyncMock()
            result = await engine.execute_agent(agent_context, user_context)
            mock_parent_execute.assert_called_once_with(agent_context, user_context)

    @pytest.mark.asyncio
    async def test_websocket_event_preservation(self, user_context, mock_agent_registry, mock_websocket_bridge):
        """Test that WebSocket events are preserved after migration."""
        engine = UserExecutionEngine(registry=mock_agent_registry, websocket_bridge=mock_websocket_bridge, user_context=user_context)
        await engine.initialize()
        await engine.execute(agent_name='test_agent', task='test_task', user_context=user_context)
        assert mock_websocket_bridge.notify_agent_started.called
        assert mock_websocket_bridge.notify_agent_completed.called
        start_call_args = mock_websocket_bridge.notify_agent_started.call_args
        assert len(start_call_args[0]) >= 2
        completion_call_args = mock_websocket_bridge.notify_agent_completed.call_args
        assert len(completion_call_args[0]) >= 2
        await engine.cleanup()

    def test_execution_result_migration(self, user_context):
        """Test that AgentExecutionResult properly handles UserExecutionContext."""
        consolidated_result = AgentExecutionResult(success=True, result='test_result', execution_time_ms=100.5, metadata={'user_isolated': True})
        assert consolidated_result.success is True
        assert consolidated_result.result == 'test_result'
        assert consolidated_result.execution_time_ms == 100.5
        assert consolidated_result.metadata['user_isolated'] is True
        supervisor_result = SupervisorAgentExecutionResult(success=True, user_context=user_context, duration=0.1005, metadata={'migration': 'completed'})
        assert supervisor_result.success is True
        assert supervisor_result.user_context == user_context
        assert supervisor_result.duration == 0.1005
        assert supervisor_result.metadata['migration'] == 'completed'

    @pytest.mark.asyncio
    async def test_user_isolation_boundaries(self, mock_agent_registry):
        """Test that different users have completely isolated execution contexts."""
        user1_context = UserExecutionContext(user_id='user_1', thread_id='thread_1', run_id='run_1', request_id='req_1')
        user2_context = UserExecutionContext(user_id='user_2', thread_id='thread_2', run_id='run_2', request_id='req_2')
        mock_websocket_emitter1 = AsyncMock()
        mock_websocket_emitter2 = AsyncMock()
        mock_factory = Mock()
        mock_factory.config.max_history_per_user = 100
        mock_factory.cleanup_context = AsyncMock()
        engine1 = IsolatedExecutionEngine(user_context=user1_context, agent_registry=mock_agent_registry, websocket_emitter=mock_websocket_emitter1, execution_semaphore=asyncio.Semaphore(5), execution_timeout=30.0, factory=mock_factory)
        engine2 = IsolatedExecutionEngine(user_context=user2_context, agent_registry=mock_agent_registry, websocket_emitter=mock_websocket_emitter2, execution_semaphore=asyncio.Semaphore(5), execution_timeout=30.0, factory=mock_factory)
        assert engine1.user_context.user_id != engine2.user_context.user_id
        assert engine1.user_context.request_id != engine2.user_context.request_id
        assert engine1.user_context.thread_id != engine2.user_context.thread_id
        assert engine1.user_context.agent_context is not engine2.user_context.agent_context
        assert engine1.user_context.audit_metadata is not engine2.user_context.audit_metadata
        assert engine1.websocket_emitter is not engine2.websocket_emitter
        await engine1.cleanup()
        await engine2.cleanup()

    @pytest.mark.asyncio
    async def test_factory_pattern_user_context_creation(self):
        """Test that factory properly creates user-isolated execution engines."""
        factory = SupervisorExecutionEngineFactory()
        mock_registry = Mock()
        mock_websocket_factory = AsyncMock()
        mock_websocket_factory.create_user_emitter = AsyncMock(return_value=AsyncMock())
        mock_db_pool = Mock()
        factory.configure(agent_registry=mock_registry, websocket_bridge_factory=mock_websocket_factory, db_connection_pool=mock_db_pool)
        user_context = UserExecutionContext(user_id='factory_test_user', thread_id='factory_thread_456', run_id='factory_run_789', request_id='factory_req_123')
        engine = await factory.create_execution_engine(user_context)
        assert isinstance(engine, IsolatedExecutionEngine)
        assert engine.user_context == user_context
        assert engine.user_context.user_id == 'factory_test_user'
        metrics = factory.get_factory_metrics()
        assert metrics['engines_created'] == 1
        assert metrics['engines_active'] == 1
        assert metrics['total_users'] == 1
        await engine.cleanup()

    def test_agent_execution_context_migration(self, user_context):
        """Test that AgentExecutionContext properly integrates UserExecutionContext."""
        context = AgentExecutionContext(agent_name='test_agent', task='test_task', user_id=user_context.user_id, request_id=user_context.request_id, thread_id=user_context.thread_id, user_context=user_context)
        assert context.agent_name == 'test_agent'
        assert context.task == 'test_task'
        assert context.user_id == user_context.user_id
        assert context.request_id == user_context.request_id
        assert context.thread_id == user_context.thread_id
        assert context.user_context == user_context
        assert isinstance(context.metadata, dict)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')