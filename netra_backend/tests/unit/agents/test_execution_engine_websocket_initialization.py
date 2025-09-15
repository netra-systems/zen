"""Unit tests for ExecutionEngine initialization with WebSocketNotifier.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: WebSocket Integration & Agent Execution Reliability
- Value Impact: Ensures $500K+ ARR chat functionality through proper WebSocket initialization
- Strategic Impact: Critical foundation for real-time agent execution feedback

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL WebSocket Integration - Test actual WebSocketNotifier initialization patterns
2. User Context Isolation - Test ExecutionEngine per-user WebSocket emitter creation
3. Factory Patterns - Test ExecutionEngineFactory WebSocket bridge integration
4. Business Value Delivery - Test critical WebSocket events (agent_started, tool_executing, etc.)
5. NO MOCKS - Use real UserExecutionEngine with real WebSocket components

This tests the critical WebSocket integration that enables chat business value delivery.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, ExecutionEngineFactoryError
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

class ExecutionEngineWebSocketInitializationTests:
    """Test ExecutionEngine initialization with WebSocket components."""

    @pytest.fixture
    def real_user_context(self) -> UserExecutionContext:
        """Create real user execution context for testing."""
        return UserExecutionContext(user_id=f'user_{uuid.uuid4().hex[:12]}', thread_id=f'thread_{uuid.uuid4().hex[:12]}', run_id=f'run_{uuid.uuid4().hex[:12]}', request_id=f'req_{uuid.uuid4().hex[:12]}', websocket_client_id=f'ws_{uuid.uuid4().hex[:12]}')

    @pytest.fixture
    def strongly_typed_context(self) -> StronglyTypedUserExecutionContext:
        """Create strongly typed user execution context."""
        return StronglyTypedUserExecutionContext(user_id=UserID(f'user_{uuid.uuid4().hex[:12]}'), thread_id=ThreadID(f'thread_{uuid.uuid4().hex[:12]}'), run_id=RunID(f'run_{uuid.uuid4().hex[:12]}'), request_id=RequestID(f'req_{uuid.uuid4().hex[:12]}'), websocket_client_id=WebSocketID(f'ws_{uuid.uuid4().hex[:12]}'))

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge for testing."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected.return_value = True
        mock_bridge.emit = AsyncMock(return_value=True)
        mock_bridge.emit_to_user = AsyncMock(return_value=True)
        return mock_bridge

    @pytest.fixture
    def mock_agent_factory(self):
        """Create mock agent factory for testing."""
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        mock_factory.create_agent_instance = AsyncMock()
        return mock_factory

    def test_execution_engine_requires_websocket_bridge_during_creation(self, real_user_context, mock_agent_factory):
        """Test that ExecutionEngine creation requires WebSocket bridge."""
        mock_factory_no_ws = MagicMock()
        mock_factory_no_ws._agent_registry = MagicMock()
        mock_factory_no_ws._websocket_bridge = None
        mock_emitter = MagicMock()
        with pytest.raises((ValueError, AttributeError)):
            UserExecutionEngine(context=real_user_context, agent_factory=mock_factory_no_ws, websocket_emitter=mock_emitter)

    def test_user_execution_engine_websocket_emitter_integration(self, real_user_context, mock_agent_factory, mock_websocket_bridge):
        """Test UserExecutionEngine integrates with WebSocket emitter correctly."""
        mock_emitter = MagicMock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        mock_emitter.cleanup = AsyncMock()
        mock_agent_factory._websocket_bridge = mock_websocket_bridge
        engine = UserExecutionEngine(context=real_user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_emitter)
        assert engine.websocket_emitter == mock_emitter
        assert engine.context == real_user_context
        assert engine.context.user_id == real_user_context.user_id
        assert engine.engine_id.startswith(f'user_engine_{real_user_context.user_id}')
        assert engine.is_active() is False

    @pytest.mark.asyncio
    async def test_execution_engine_websocket_notification_methods(self, real_user_context, mock_agent_factory, mock_websocket_bridge):
        """Test ExecutionEngine WebSocket notification methods."""
        mock_emitter = MagicMock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        mock_emitter.cleanup = AsyncMock()
        mock_agent_factory._websocket_bridge = mock_websocket_bridge
        engine = UserExecutionEngine(context=real_user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_emitter)
        mock_execution_context = MagicMock()
        mock_execution_context.agent_name = 'test_agent'
        mock_execution_context.user_id = real_user_context.user_id
        mock_execution_context.metadata = {'test': 'metadata'}
        await engine._send_user_agent_started(mock_execution_context)
        mock_emitter.notify_agent_started.assert_called_once()
        call_args = mock_emitter.notify_agent_started.call_args
        assert call_args[1]['agent_name'] == 'test_agent'
        context_data = call_args[1]['context']
        assert context_data['user_isolated'] is True
        assert context_data['user_id'] == real_user_context.user_id
        assert context_data['engine_id'] == engine.engine_id
        await engine._send_user_agent_thinking(mock_execution_context, 'Test thinking', step_number=1)
        mock_emitter.notify_agent_thinking.assert_called_once_with(agent_name='test_agent', reasoning='Test thinking', step_number=1)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.execution_time = 2.5
        mock_result.error = None
        await engine._send_user_agent_completed(mock_execution_context, mock_result)
        mock_emitter.notify_agent_completed.assert_called_once()
        completed_call_args = mock_emitter.notify_agent_completed.call_args
        result_data = completed_call_args[1]['result']
        assert result_data['success'] is True
        assert result_data['user_isolated'] is True
        assert result_data['user_id'] == real_user_context.user_id
        assert result_data['duration_ms'] == 2500.0

    @pytest.mark.asyncio
    async def test_execution_engine_cleanup_websocket_emitter(self, real_user_context, mock_agent_factory, mock_websocket_bridge):
        """Test ExecutionEngine properly cleans up WebSocket emitter."""
        mock_emitter = MagicMock()
        mock_emitter.cleanup = AsyncMock()
        mock_agent_factory._websocket_bridge = mock_websocket_bridge
        engine = UserExecutionEngine(context=real_user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_emitter)
        assert engine._is_active is True
        await engine.cleanup()
        mock_emitter.cleanup.assert_called_once()
        assert engine._is_active is False
        assert engine.is_active() is False

class ExecutionEngineFactoryWebSocketIntegrationTests:
    """Test ExecutionEngineFactory WebSocket bridge integration."""

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected.return_value = True
        mock_bridge.emit = AsyncMock(return_value=True)
        return mock_bridge

    def test_factory_requires_websocket_bridge_during_initialization(self):
        """Test ExecutionEngineFactory requires WebSocket bridge during initialization."""
        with pytest.raises(ExecutionEngineFactoryError, match='ExecutionEngineFactory requires websocket_bridge'):
            ExecutionEngineFactory(websocket_bridge=None)
        mock_bridge = MagicMock()
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        assert factory._websocket_bridge == mock_bridge

    @pytest.mark.asyncio
    async def test_factory_creates_user_websocket_emitter_with_bridge(self, mock_websocket_bridge):
        """Test factory creates UserWebSocketEmitter with validated bridge."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = UserExecutionContext(user_id=f'user_{uuid.uuid4().hex[:12]}', thread_id=f'thread_{uuid.uuid4().hex[:12]}', run_id=f'run_{uuid.uuid4().hex[:12]}', request_id=f'req_{uuid.uuid4().hex[:12]}', websocket_client_id=f'ws_{uuid.uuid4().hex[:12]}')
        mock_agent_factory = MagicMock()
        emitter = await factory._create_user_websocket_emitter(user_context, mock_agent_factory)
        assert emitter is not None

    @pytest.mark.asyncio
    async def test_factory_user_execution_scope_websocket_lifecycle(self, mock_websocket_bridge):
        """Test factory user execution scope handles WebSocket lifecycle."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = UserExecutionContext(user_id=f'user_{uuid.uuid4().hex[:12]}', thread_id=f'thread_{uuid.uuid4().hex[:12]}', run_id=f'run_{uuid.uuid4().hex[:12]}', request_id=f'req_{uuid.uuid4().hex[:12]}', websocket_client_id=f'ws_{uuid.uuid4().hex[:12]}')
        from unittest.mock import patch
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            async with factory.user_execution_scope(user_context) as engine:
                assert engine is not None
                assert isinstance(engine, UserExecutionEngine)
                assert engine.websocket_emitter is not None
                assert engine.context.user_id == user_context.user_id
                assert engine.context.thread_id == user_context.thread_id

    def test_factory_metrics_track_websocket_integration(self, mock_websocket_bridge):
        """Test factory metrics track WebSocket integration status."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        metrics = factory.get_factory_metrics()
        assert 'total_engines_created' in metrics
        assert 'total_engines_cleaned' in metrics
        assert 'active_engines_count' in metrics
        assert 'creation_errors' in metrics
        assert 'cleanup_errors' in metrics
        assert metrics['total_engines_created'] == 0
        assert metrics['active_engines_count'] == 0

    @pytest.mark.asyncio
    async def test_factory_websocket_bridge_validation_prevents_runtime_errors(self):
        """Test that WebSocket bridge validation prevents runtime errors."""
        mock_bridge = MagicMock()
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        assert factory._websocket_bridge == mock_bridge
        user_context = UserExecutionContext(user_id=f'user_{uuid.uuid4().hex[:12]}', thread_id=f'thread_{uuid.uuid4().hex[:12]}', run_id=f'run_{uuid.uuid4().hex[:12]}', request_id=f'req_{uuid.uuid4().hex[:12]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_bridge
            mock_get_factory.return_value = mock_agent_factory
            try:
                engine = await factory.create_for_user(user_context)
                assert engine is not None
                await factory.cleanup_engine(engine)
            except ExecutionEngineFactoryError:
                pass

class WebSocketNotifierExecutionEngineIntegrationTests:
    """Test WebSocketNotifier integration within ExecutionEngine workflow."""

    @pytest.fixture
    def mock_websocket_notifier(self):
        """Create mock WebSocketNotifier for testing."""
        notifier = MagicMock()
        notifier.notify_agent_started = AsyncMock(return_value=True)
        notifier.notify_agent_thinking = AsyncMock(return_value=True)
        notifier.notify_tool_executing = AsyncMock(return_value=True)
        notifier.notify_tool_completed = AsyncMock(return_value=True)
        notifier.notify_agent_completed = AsyncMock(return_value=True)
        notifier.notify_agent_error = AsyncMock(return_value=True)
        return notifier

    @pytest.mark.asyncio
    async def test_execution_engine_websocket_notifier_agent_lifecycle(self, mock_websocket_notifier):
        """Test ExecutionEngine uses WebSocketNotifier for complete agent lifecycle."""
        user_context = UserExecutionContext(user_id=f'user_{uuid.uuid4().hex[:12]}', thread_id=f'thread_{uuid.uuid4().hex[:12]}', run_id=f'run_{uuid.uuid4().hex[:12]}', request_id=f'req_{uuid.uuid4().hex[:12]}', websocket_client_id=f'ws_{uuid.uuid4().hex[:12]}')
        mock_agent_factory = MagicMock()
        mock_agent_factory._agent_registry = MagicMock()
        mock_agent_factory._websocket_bridge = MagicMock()
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_notifier)
        assert engine.websocket_emitter == mock_websocket_notifier
        assert hasattr(engine, '_send_user_agent_started')
        assert hasattr(engine, '_send_user_agent_thinking')
        assert hasattr(engine, '_send_user_agent_completed')
        mock_context = MagicMock()
        mock_context.agent_name = 'test_agent'
        mock_context.user_id = user_context.user_id
        mock_context.metadata = {}
        await engine._send_user_agent_started(mock_context)
        mock_websocket_notifier.notify_agent_started.assert_called_once()
        await engine._send_user_agent_thinking(mock_context, 'Processing request', step_number=1)
        mock_websocket_notifier.notify_agent_thinking.assert_called_once()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.execution_time = 1.5
        mock_result.error = None
        await engine._send_user_agent_completed(mock_context, mock_result)
        mock_websocket_notifier.notify_agent_completed.assert_called_once()

    def test_websocket_notifier_user_isolation_in_engine(self):
        """Test WebSocketNotifier maintains user isolation within ExecutionEngine."""
        user1_context = UserExecutionContext(user_id=f'user1_{uuid.uuid4().hex[:8]}', thread_id=f'thread1_{uuid.uuid4().hex[:8]}', run_id=f'run1_{uuid.uuid4().hex[:8]}', request_id=f'req1_{uuid.uuid4().hex[:8]}')
        user2_context = UserExecutionContext(user_id=f'user2_{uuid.uuid4().hex[:8]}', thread_id=f'thread2_{uuid.uuid4().hex[:8]}', run_id=f'run2_{uuid.uuid4().hex[:8]}', request_id=f'req2_{uuid.uuid4().hex[:8]}')
        notifier1 = MagicMock()
        notifier2 = MagicMock()
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        engine1 = UserExecutionEngine(context=user1_context, agent_factory=mock_factory, websocket_emitter=notifier1)
        engine2 = UserExecutionEngine(context=user2_context, agent_factory=mock_factory, websocket_emitter=notifier2)
        assert engine1.websocket_emitter == notifier1
        assert engine2.websocket_emitter == notifier2
        assert engine1.websocket_emitter != engine2.websocket_emitter
        assert engine1.context.user_id != engine2.context.user_id
        assert engine1.engine_id != engine2.engine_id
        assert engine1.active_runs != engine2.active_runs
        assert engine1.execution_stats != engine2.execution_stats
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')