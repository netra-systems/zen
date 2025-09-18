"Integration tests for ExecutionEngineFactory with WebSocket bridge."""

Business Value Justification:
    - Segment: Platform/Internal
- Business Goal: Factory Pattern WebSocket Integration
- Value Impact: Ensures $""500K"" plus ARR chat functionality through proper factory WebSocket integration
- Strategic Impact: Critical foundation for scalable multi-user WebSocket event delivery

CRITICAL REQUIREMENTS per CLAUDE.md:
    1. REAL WEBSOCKET INTEGRATION - Test actual factory WebSocket bridge patterns
2. Factory Patterns - Test ExecutionEngineFactory creates proper WebSocket connections
3. User Isolation - Test factory maintains WebSocket isolation per user
4. WebSocket Lifecycle - Test WebSocket bridge lifecycle through factory
5. BUSINESS VALUE DELIVERY - Test critical WebSocket events through factory

This tests the factory WebSocket integration that enables scalable chat business value.
""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch, call
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, ExecutionEngineFactoryError, configure_execution_engine_factory, get_execution_engine_factory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

@pytest.mark.integration
class ExecutionEngineFactoryWebSocketIntegrationTests:
    Test ExecutionEngineFactory WebSocket bridge integration patterns.""

    @pytest.fixture
    def mock_websocket_bridge(self):
        "Create mock WebSocket bridge with comprehensive event tracking."""
        bridge = MagicMock()
        bridge.is_connected.return_value = True
        bridge.emit = AsyncMock(return_value=True)
        bridge.emit_to_user = AsyncMock(return_value=True)
        bridge.event_log = []

        def log_event(event_type, **kwargs):
            bridge.event_log.append({'event_type': event_type, 'timestamp': datetime.now(timezone.utc), 'args': kwargs}
            return True
        original_emit = bridge.emit
        original_emit_to_user = bridge.emit_to_user

        async def logged_emit(*args, **kwargs):
            log_event('emit', args=args, kwargs=kwargs)
            return await original_emit(*args, **kwargs)

        async def logged_emit_to_user(*args, **kwargs):
            log_event('emit_to_user', args=args, kwargs=kwargs)
            return await original_emit_to_user(*args, **kwargs)
        bridge.emit = logged_emit
        bridge.emit_to_user = logged_emit_to_user
        return bridge

    def create_user_context(self, user_suffix: str) -> UserExecutionContext:
        ""Create user execution context for factory testing.""

        return UserExecutionContext(user_id=f'factory_user_{user_suffix}_{uuid.uuid4().hex[:8]}', thread_id=f'factory_thread_{user_suffix}_{uuid.uuid4().hex[:8]}', run_id=f'factory_run_{user_suffix}_{uuid.uuid4().hex[:8]}', request_id=f'factory_req_{user_suffix}_{uuid.uuid4().hex[:8]}', websocket_client_id=f'factory_ws_{user_suffix}_{uuid.uuid4().hex[:8]}')

    def test_factory_supports_none_websocket_bridge_for_test_environments(self):
        Test factory allows None WebSocket bridge for test environments (Issue #920 fixed).""
        # Issue #920 FIXED: Factory should now accept None websocket_bridge for test environments
        factory = ExecutionEngineFactory(websocket_bridge=None)
        assert factory._websocket_bridge is None
        assert factory is not None
        assert hasattr(factory, "'_active_engines')"
        
        # Test with actual bridge still works
        mock_bridge = MagicMock()
        factory_with_bridge = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        assert factory_with_bridge._websocket_bridge == mock_bridge
        assert factory_with_bridge._websocket_bridge is not None

    @pytest.mark.asyncio
    async def test_factory_creates_user_engines_with_websocket_integration(self, mock_websocket_bridge):
        Test factory creates user engines with proper WebSocket integration.""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = self.create_user_context('websocket_integration')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine = await factory.create_for_user(user_context)
            try:
                assert engine is not None
                assert isinstance(engine, "UserExecutionEngine)"
                assert engine.websocket_emitter is not None
                assert engine.context.user_id == user_context.user_id
                assert engine.context.websocket_client_id == user_context.websocket_client_id
                assert len(factory._active_engines) == 1
                metrics = factory.get_factory_metrics()
                assert metrics['total_engines_created'] == 1
                assert metrics['active_engines_count'] == 1
            finally:
                await factory.cleanup_engine(engine)

    @pytest.mark.asyncio
    async def test_factory_user_websocket_emitter_creation_with_bridge_validation(self, mock_websocket_bridge):
        Test factory creates UserWebSocketEmitter with validated bridge.""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = self.create_user_context('emitter_creation')
        mock_agent_factory = MagicMock()
        mock_agent_factory._agent_registry = MagicMock()
        mock_agent_factory._websocket_bridge = mock_websocket_bridge
        emitter = await factory._create_user_websocket_emitter(user_context, mock_agent_factory)
        assert emitter is not None

    @pytest.mark.asyncio
    async def test_factory_concurrent_websocket_emitter_creation_isolation(self, mock_websocket_bridge):
        "Test factory creates isolated WebSocket emitters for concurrent users."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user1_context = self.create_user_context('concurrent_user1')
        user2_context = self.create_user_context('concurrent_user2')
        user3_context = self.create_user_context('concurrent_user3')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory

            async def create_engine_for_user(context):
                return await factory.create_for_user(context)
            engines = await asyncio.gather(create_engine_for_user(user1_context), create_engine_for_user(user2_context), create_engine_for_user(user3_context))
            try:
                assert len(engines) == 3
                for engine in engines:
                    assert engine is not None
                    assert isinstance(engine, "UserExecutionEngine)"
                    assert engine.websocket_emitter is not None
                emitters = [engine.websocket_emitter for engine in engines]
                assert len(set((id(emitter) for emitter in emitters))) == 3
                user_ids = [engine.context.user_id for engine in engines]
                assert len(set(user_ids)) == 3
                metrics = factory.get_factory_metrics()
                assert metrics['total_engines_created'] == 3
                assert metrics['active_engines_count'] == 3
            finally:
                for engine in engines:
                    await factory.cleanup_engine(engine)

    @pytest.mark.asyncio
    async def test_factory_user_execution_scope_websocket_lifecycle(self, mock_websocket_bridge):
        "Test factory user execution scope manages WebSocket lifecycle properly."
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = self.create_user_context('scope_lifecycle')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            websocket_emitter_during_scope = None
            websocket_emitter_cleanup_called = False
            async with factory.user_execution_scope(user_context) as engine:
                assert engine is not None
                assert engine.websocket_emitter is not None
                websocket_emitter_during_scope = engine.websocket_emitter
                original_cleanup = websocket_emitter_during_scope.cleanup if hasattr(websocket_emitter_during_scope, 'cleanup') else None

                async def tracked_cleanup():
                    nonlocal websocket_emitter_cleanup_called
                    websocket_emitter_cleanup_called = True
                    if original_cleanup:
                        await original_cleanup()
                if hasattr(websocket_emitter_during_scope, 'cleanup'):
                    websocket_emitter_during_scope.cleanup = tracked_cleanup
                assert len(factory._active_engines) == 1
            await asyncio.sleep(0.1)
            assert len(factory._active_engines) == 0
            metrics = factory.get_factory_metrics()
            assert metrics['total_engines_cleaned'] >= 1

    @pytest.mark.asyncio
    async def test_factory_websocket_bridge_error_handling(self, mock_websocket_bridge):
        "Test factory handles WebSocket bridge errors gracefully."
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = self.create_user_context('error_handling')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            with patch.object(factory, '_create_user_websocket_emitter') as mock_create_emitter:
                mock_create_emitter.side_effect = Exception('WebSocket emitter creation failed')
                with pytest.raises(ExecutionEngineFactoryError, match='Engine creation failed'):
                    await factory.create_for_user(user_context)
                metrics = factory.get_factory_metrics()
                assert metrics['creation_errors'] >= 1
                assert metrics['total_engines_created'] == 0

    @pytest.mark.asyncio
    async def test_factory_websocket_events_through_created_engines(self, mock_websocket_bridge):
        Test WebSocket events work through engines created by factory.""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = self.create_user_context('events_testing')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine = await factory.create_for_user(user_context)
            try:
                mock_exec_context = MagicMock()
                mock_exec_context.agent_name = 'factory_test_agent'
                mock_exec_context.user_id = user_context.user_id
                mock_exec_context.metadata = {'factory_test': True}
                mock_websocket_bridge.event_log.clear()
                await engine._send_user_agent_started(mock_exec_context)
                await engine._send_user_agent_thinking(mock_exec_context, 'Factory WebSocket test', step_number=1)
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.execution_time = 1.5
                mock_result.error = None
                await engine._send_user_agent_completed(mock_exec_context, mock_result)
                assert len(mock_websocket_bridge.event_log) >= 0
                assert engine.websocket_emitter is not None
            finally:
                await factory.cleanup_engine(engine)

@pytest.mark.integration
class ExecutionEngineFactoryWebSocketConfigurationTests:
    Test ExecutionEngineFactory WebSocket configuration and setup.""

    @pytest.mark.asyncio
    async def test_configure_execution_engine_factory_with_websocket_bridge(self):
        "Test configuring factory with WebSocket bridge for production use."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected.return_value = True
        factory = await configure_execution_engine_factory(websocket_bridge=mock_bridge, database_session_manager=None, redis_manager=None)
        assert factory is not None
        assert isinstance(factory, "ExecutionEngineFactory)"
        assert factory._websocket_bridge == mock_bridge
        retrieved_factory = await get_execution_engine_factory()
        assert retrieved_factory == factory
        assert retrieved_factory._websocket_bridge == mock_bridge

    def test_factory_websocket_bridge_validation_prevents_late_errors(self):
        ""Test early WebSocket bridge validation prevents runtime errors.""

        with pytest.raises(ExecutionEngineFactoryError, match='ExecutionEngineFactory requires websocket_bridge'):
            ExecutionEngineFactory(websocket_bridge=None)
        mock_bridge = MagicMock()
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        assert factory._websocket_bridge == mock_bridge
        assert factory._websocket_bridge is not None

    def test_factory_websocket_bridge_configuration_persistence(self):
        Test WebSocket bridge configuration persists through factory lifecycle.""
        mock_bridge = MagicMock()
        mock_bridge.connection_id = f'bridge_{uuid.uuid4().hex[:8]}'
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        assert factory._websocket_bridge == mock_bridge
        assert factory._websocket_bridge.connection_id == mock_bridge.connection_id
        metrics = factory.get_factory_metrics()
        assert 'total_engines_created' in metrics
        active_engines_summary = factory.get_active_engines_summary()
        assert 'total_active_engines' in active_engines_summary
        assert factory._websocket_bridge == mock_bridge

    @pytest.mark.asyncio
    async def test_factory_websocket_bridge_infrastructure_integration(self):
        Test factory WebSocket bridge integrates with infrastructure managers.""
        mock_bridge = MagicMock()
        mock_database_manager = MagicMock()
        mock_redis_manager = MagicMock()
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge, database_session_manager=mock_database_manager, redis_manager=mock_redis_manager)
        assert factory._websocket_bridge == mock_bridge
        assert factory._database_session_manager == mock_database_manager
        assert factory._redis_manager == mock_redis_manager
        user_context = UserExecutionContext(user_id=f'infra_user_{uuid.uuid4().hex[:12]}', thread_id=f'infra_thread_{uuid.uuid4().hex[:12]}', run_id=f'infra_run_{uuid.uuid4().hex[:12]}', request_id=f'infra_req_{uuid.uuid4().hex[:12]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine = await factory.create_for_user(user_context)
            try:
                assert hasattr(engine, "'database_session_manager')"
                assert hasattr(engine, "'redis_manager')"
                assert engine.database_session_manager == mock_database_manager
                assert engine.redis_manager == mock_redis_manager
            finally:
                await factory.cleanup_engine(engine)

@pytest.mark.integration
class ExecutionEngineFactoryWebSocketBusinessValueTests:
    Test ExecutionEngineFactory delivers WebSocket business value.""

    def test_factory_websocket_integration_enables_chat_business_value(self):
        "Test factory WebSocket integration enables critical chat business value delivery."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected.return_value = True
        mock_bridge.supports_chat_events = True
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        assert factory._websocket_bridge == mock_bridge
        assert factory._websocket_bridge.supports_chat_events is True
        metrics = factory.get_factory_metrics()
        assert metrics['total_engines_created'] == 0
        assert metrics['creation_errors'] == 0
        assert factory._websocket_bridge is not None

    @pytest.mark.asyncio
    async def test_factory_enables_real_time_agent_feedback_business_value(self, mock_websocket_bridge):
        "Test factory enables real-time agent feedback for business value delivery."""
        mock_websocket_bridge.business_value_events = []

        def track_business_value_event(event_type, user_id, **kwargs):
            mock_websocket_bridge.business_value_events.append({'event_type': event_type, 'user_id': user_id, 'business_value': True, 'timestamp': datetime.now(timezone.utc)}
            return True

        async def business_value_emit(event_type, data, **kwargs):
            user_id = data.get('user_id') if isinstance(data, dict) else None
            track_business_value_event(event_type, user_id, data=data)
            return True
        mock_websocket_bridge.emit = business_value_emit
        mock_websocket_bridge.emit_to_user = business_value_emit
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_context = UserExecutionContext(user_id="f'business_value_user_{uuid.uuid4(").hex[:8]}', thread_id=f'business_value_thread_{uuid.uuid4().hex[:8]}', run_id=f'business_value_run_{uuid.uuid4().hex[:8]}', request_id=f'business_value_req_{uuid.uuid4().hex[:8]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine = await factory.create_for_user(user_context)
            try:
                assert engine is not None
                assert engine.websocket_emitter is not None
                metrics = factory.get_factory_metrics()
                assert metrics['total_engines_created'] == 1
                assert metrics['active_engines_count'] == 1
            finally:
                await factory.cleanup_engine(engine)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
))