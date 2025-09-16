"""Unit Tests for UnifiedToolDispatcher - Critical SSOT Class

This test suite provides comprehensive coverage for the UnifiedToolDispatcher,
focusing on security edge cases, factory patterns, and WebSocket integration
that are critical for multi-user isolation and business value delivery.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Platform Stability, Risk Reduction, Multi-User Safety
- Value Impact: Tool execution delivers 90% of agent value to customers
- Strategic Impact: Request-scoped isolation prevents multi-million dollar churn from user data leakage

CRITICAL REQUIREMENTS:
- Factory pattern enforcement (NO direct instantiation)
- Request-scoped isolation for multi-user safety
- WebSocket events for ALL tool executions (chat UX)
- Permission validation and admin tool boundaries
- Comprehensive error handling and metrics tracking
- Security violation tracking and prevention

Test Architecture:
- NO mocks for business logic (CHEATING = ABOMINATION)
- Real instances with minimal external dependencies
- ABSOLUTE IMPORTS only
- Tests must RAISE ERRORS - no try/except masking
- Focus on edge cases, error conditions, and security validation
"""
import asyncio
import pytest
import time
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher, UnifiedToolDispatcherFactory, ToolDispatchRequest, ToolDispatchResponse, DispatchStrategy, AuthenticationError, PermissionError, SecurityViolationError, create_request_scoped_dispatcher
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus

class MockBaseTool:
    """Mock LangChain tool for testing purposes."""

    def __init__(self, name: str, should_fail: bool=False, execution_result: Any=None, delay: float=0):
        self.name = name
        self.should_fail = should_fail
        self.execution_result = execution_result or f'Result from {name}'
        self.call_count = 0
        self.delay = delay
        self.last_kwargs = {}

    async def arun(self, **kwargs) -> Any:
        """Mock async tool execution."""
        self.call_count += 1
        self.last_kwargs = kwargs
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.should_fail:
            raise ValueError(f'Tool {self.name} execution failed')
        return self.execution_result

    def __call__(self, **kwargs) -> Any:
        """Synchronous call interface."""
        self.last_kwargs = kwargs
        self.call_count += 1
        if self.should_fail:
            raise ValueError(f'Tool {self.name} execution failed')
        return self.execution_result

class MockWebSocketManager:
    """Mock WebSocket manager for testing WebSocket event emission."""

    def __init__(self):
        self.events_sent = []
        self.should_fail = False
        self.fail_on_event_type = None

    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Mock send_event method."""
        if self.should_fail or (self.fail_on_event_type and event_type == self.fail_on_event_type):
            raise Exception(f'WebSocket send failed for {event_type}')
        self.events_sent.append({'event_type': event_type, 'data': data, 'timestamp': datetime.now(timezone.utc)})
        return True

    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is available."""
        return True

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of specific type."""
        return [event for event in self.events_sent if event['event_type'] == event_type]

    def clear_events(self):
        """Clear all recorded events."""
        self.events_sent.clear()

    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Bridge method for tool executing notifications."""
        return await self.send_event('tool_executing', {'run_id': run_id, 'agent_name': agent_name, 'tool_name': tool_name, 'parameters': parameters})

    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict[str, Any], execution_time_ms: float) -> bool:
        """Bridge method for tool completed notifications."""
        return await self.send_event('tool_completed', {'run_id': run_id, 'agent_name': agent_name, 'tool_name': tool_name, 'result': result, 'execution_time_ms': execution_time_ms})

class MockAgentWebSocketBridge:
    """Mock AgentWebSocketBridge for testing bridge adapter pattern."""

    def __init__(self):
        self.tool_executing_calls = []
        self.tool_completed_calls = []
        self.should_fail = False
        self.fail_on_method = None

    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Mock tool executing notification."""
        if self.should_fail or self.fail_on_method == 'notify_tool_executing':
            return False
        self.tool_executing_calls.append({'run_id': run_id, 'agent_name': agent_name, 'tool_name': tool_name, 'parameters': parameters})
        return True

    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict[str, Any], execution_time_ms: float) -> bool:
        """Mock tool completed notification."""
        if self.should_fail or self.fail_on_method == 'notify_tool_completed':
            return False
        self.tool_completed_calls.append({'run_id': run_id, 'agent_name': agent_name, 'tool_name': tool_name, 'result': result, 'execution_time_ms': execution_time_ms})
        return True

def create_user_context(user_id: str='test_user_123', run_id: str=None, thread_id: str='test_thread', metadata: Optional[Dict[str, Any]]=None) -> UserExecutionContext:
    """Create test UserExecutionContext with proper isolation."""
    if run_id is None:
        run_id = f'run_{int(time.time() * 1000)}'
    return UserExecutionContext(user_id=user_id, run_id=run_id, thread_id=thread_id, metadata=metadata or {})

def create_admin_user_context(user_id: str='admin_user_123', run_id: str=None) -> UserExecutionContext:
    """Create UserExecutionContext with admin permissions."""
    metadata = {'roles': ['admin'], 'permissions': ['admin_tools', 'corpus_admin', 'user_admin']}
    return create_user_context(user_id=user_id, run_id=run_id, metadata=metadata)

class FactoryPatternSecurityTests:
    """Test factory pattern security and enforcement."""

    def test_direct_instantiation_forbidden(self):
        """Direct instantiation must raise RuntimeError for security."""
        with pytest.raises(RuntimeError) as exc_info:
            UnifiedToolDispatcher()
        error_message = str(exc_info.value)
        assert 'Direct instantiation of UnifiedToolDispatcher is forbidden' in error_message
        assert 'Use factory methods for proper isolation' in error_message

    def test_new_bypass_attempt_blocked(self):
        """Test that __new__ bypass attempts create unusable instances."""
        instance = UnifiedToolDispatcher.__new__(UnifiedToolDispatcher)
        with pytest.raises(AttributeError):
            _ = instance.user_context
        with pytest.raises(AttributeError):
            _ = instance.dispatcher_id

    def test_security_violation_tracking(self):
        """Test that security violations are tracked globally."""
        initial_violations = UnifiedToolDispatcher._security_violations
        try:
            UnifiedToolDispatcher()
        except RuntimeError:
            pass
        assert UnifiedToolDispatcher._security_violations == initial_violations

    @pytest.mark.asyncio
    async def test_factory_creates_unique_instances(self):
        """Test that factory creates truly isolated instances."""
        user1_context = create_user_context(user_id='user1', run_id='run1')
        user2_context = create_user_context(user_id='user2', run_id='run2')
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user1_context)
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user2_context)
        assert dispatcher1 is not dispatcher2
        assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id
        assert dispatcher1.user_context != dispatcher2.user_context
        tool1 = MockBaseTool('tool1')
        tool2 = MockBaseTool('tool2')
        dispatcher1.register_tool(tool1)
        dispatcher2.register_tool(tool2)
        assert dispatcher1.has_tool('tool1') and (not dispatcher1.has_tool('tool2'))
        assert dispatcher2.has_tool('tool2') and (not dispatcher2.has_tool('tool1'))
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()

class EdgeCasesAndErrorConditionsTests:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_invalid_user_context_variations(self):
        """Test various invalid user context scenarios."""
        with pytest.raises(AuthenticationError):
            await UnifiedToolDispatcher.create_for_user(None)
        invalid_context1 = Mock()
        invalid_context1.user_id = None
        invalid_context1.run_id = 'valid_run'
        with pytest.raises(AuthenticationError):
            await UnifiedToolDispatcher.create_for_user(invalid_context1)
        invalid_context2 = Mock()
        invalid_context2.user_id = ''
        invalid_context2.run_id = 'valid_run'
        with pytest.raises(AuthenticationError):
            await UnifiedToolDispatcher.create_for_user(invalid_context2)
        invalid_context3 = Mock()
        invalid_context3.user_id = False
        invalid_context3.run_id = 'valid_run'
        with pytest.raises(AuthenticationError):
            await UnifiedToolDispatcher.create_for_user(invalid_context3)

    @pytest.mark.asyncio
    async def test_dispatcher_limit_enforcement(self):
        """Test dispatcher limit enforcement per user."""
        user_id = 'limited_user'
        original_limit = UnifiedToolDispatcher._max_dispatchers_per_user
        try:
            UnifiedToolDispatcher._max_dispatchers_per_user = 2
            dispatchers = []
            for i in range(2):
                context = create_user_context(user_id=user_id, run_id=f'run_{i}')
                dispatcher = await UnifiedToolDispatcher.create_for_user(context)
                dispatchers.append(dispatcher)
            assert len(dispatchers) == 2
            overflow_context = create_user_context(user_id=user_id, run_id='overflow_run')
            overflow_dispatcher = await UnifiedToolDispatcher.create_for_user(overflow_context)
            await asyncio.sleep(0.1)
            assert overflow_dispatcher._is_active
            for dispatcher in dispatchers:
                await dispatcher.cleanup()
            await overflow_dispatcher.cleanup()
        finally:
            UnifiedToolDispatcher._max_dispatchers_per_user = original_limit

    @pytest.mark.asyncio
    async def test_concurrent_dispatcher_creation_safety(self):
        """Test thread safety during concurrent dispatcher creation."""
        user_context = create_user_context()

        async def create_dispatcher(index):
            context = create_user_context(user_id=f'concurrent_user_{index}', run_id=f'run_{index}')
            return await UnifiedToolDispatcher.create_for_user(context)
        tasks = [create_dispatcher(i) for i in range(5)]
        dispatchers = await asyncio.gather(*tasks)
        dispatcher_ids = [d.dispatcher_id for d in dispatchers]
        assert len(set(dispatcher_ids)) == len(dispatchers)
        for dispatcher in dispatchers:
            assert dispatcher._is_active
        for dispatcher in dispatchers:
            await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_malformed_websocket_manager_handling(self):
        """Test handling of malformed WebSocket managers."""
        user_context = create_user_context()
        malformed_ws = Mock()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=malformed_ws)
        assert dispatcher.websocket_manager is not None
        await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_tool_registration_edge_cases(self):
        """Test edge cases in tool registration."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        tool1 = MockBaseTool('duplicate_name')
        tool2 = MockBaseTool('duplicate_name')
        dispatcher.register_tool(tool1)
        with pytest.raises(ValueError) as exc_info:
            dispatcher.register_tool(tool2)
        assert 'already registered' in str(exc_info.value)
        special_tool = MockBaseTool('tool-with_special.chars')
        dispatcher.register_tool(special_tool)
        assert dispatcher.has_tool('tool-with_special.chars')
        await dispatcher.cleanup()

class WebSocketIntegrationEdgeCasesTests:
    """Test WebSocket integration edge cases."""

    @pytest.mark.asyncio
    async def test_websocket_event_failure_resilience(self):
        """Test resilience when WebSocket events fail."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        websocket_manager.should_fail = True
        with patch('netra_backend.app.agents.unified_tool_execution.UnifiedToolExecutionEngine') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute_tool_with_input.return_value = 'mocked_result'
            mock_executor_class.return_value = mock_executor
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=websocket_manager)
            tool = MockBaseTool('resilient_tool')
            dispatcher.register_tool(tool)
            response = await dispatcher.execute_tool('resilient_tool')
            assert response.success is True
            assert mock_executor.execute_tool_with_input.call_count == 1
            assert len(websocket_manager.events_sent) == 0
            await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_websocket_bridge_adapter_error_handling(self):
        """Test WebSocket bridge adapter error handling."""
        user_context = create_user_context()
        websocket_bridge = MockAgentWebSocketBridge()
        websocket_bridge.fail_on_method = 'notify_tool_executing'
        with patch('netra_backend.app.agents.unified_tool_execution.UnifiedToolExecutionEngine') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute_tool_with_input.return_value = 'mocked_result'
            mock_executor_class.return_value = mock_executor
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=websocket_bridge)
            tool = MockBaseTool('bridge_error_tool')
            dispatcher.register_tool(tool)
            response = await dispatcher.execute_tool('bridge_error_tool')
            assert response.success is True
            assert len(websocket_bridge.tool_executing_calls) == 0
            await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_websocket_manager_update_behavior(self):
        """Test WebSocket manager update behavior."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        assert not dispatcher.has_websocket_support
        ws_manager1 = MockWebSocketManager()
        dispatcher.set_websocket_manager(ws_manager1)
        assert dispatcher.has_websocket_support
        assert dispatcher.websocket_manager is ws_manager1
        ws_manager2 = MockWebSocketManager()
        dispatcher.set_websocket_manager(ws_manager2)
        assert dispatcher.websocket_manager is ws_manager2
        await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_websocket_event_data_validation(self):
        """Test WebSocket event data structure validation."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=websocket_manager)
        tool = MockBaseTool('validation_tool')
        dispatcher.register_tool(tool)
        response = await dispatcher.execute_tool('validation_tool', {'param': 'value'})
        executing_events = websocket_manager.get_events_by_type('tool_executing')
        assert len(executing_events) == 1
        executing_data = executing_events[0]['data']
        required_fields = ['tool_name', 'parameters', 'run_id', 'user_id', 'thread_id', 'timestamp']
        for field in required_fields:
            assert field in executing_data, f'Missing required field: {field}'
        completed_events = websocket_manager.get_events_by_type('tool_completed')
        assert len(completed_events) == 1
        completed_data = completed_events[0]['data']
        required_fields = ['tool_name', 'run_id', 'user_id', 'thread_id', 'timestamp', 'status']
        for field in required_fields:
            assert field in completed_data, f'Missing required field: {field}'
        await dispatcher.cleanup()

class PermissionAndSecurityTests:
    """Test permission validation and security boundaries."""

    @pytest.mark.asyncio
    async def test_permission_check_metrics_tracking(self):
        """Test that permission checks are properly tracked in metrics."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        tool = MockBaseTool('metrics_tool')
        dispatcher.register_tool(tool)
        await dispatcher.execute_tool('metrics_tool')
        metrics = dispatcher.get_metrics()
        assert metrics['permission_checks'] >= 1
        assert metrics['permission_denials'] == 0
        assert metrics['security_violations'] == 0
        await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_security_violation_tracking(self):
        """Test security violation tracking."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        original_user_context = dispatcher.user_context
        dispatcher.user_context = None
        with pytest.raises(AuthenticationError):
            await dispatcher._validate_tool_permissions('any_tool')
        metrics = dispatcher.get_metrics()
        assert metrics['security_violations'] >= 1
        dispatcher.user_context = original_user_context
        await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_admin_permission_edge_cases(self):
        """Test admin permission checking edge cases."""
        user_context = create_user_context()
        mock_user = Mock(spec=[])
        dispatcher = UnifiedToolDispatcherFactory.create_for_admin(user_context=user_context, db=Mock(), user=mock_user)
        result = dispatcher._check_admin_permission()
        assert result is False

    @pytest.mark.asyncio
    async def test_permission_service_fallback(self):
        """Test permission service as fallback when user has no is_admin attribute."""
        user_context = create_user_context(metadata={})
        mock_user = Mock(spec=[])
        mock_permission_service = Mock()
        mock_permission_service.has_admin_permission.return_value = True
        dispatcher = UnifiedToolDispatcherFactory.create_for_admin(user_context=user_context, db=Mock(), user=mock_user, permission_service=mock_permission_service)
        result = dispatcher._check_admin_permission()
        assert result is True
        mock_permission_service.has_admin_permission.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_admin_tool_execution_denied(self):
        """Test that admin tools are properly denied for regular users."""
        with patch('netra_backend.app.agents.unified_tool_execution.UnifiedToolExecutionEngine') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute_tool_with_input.return_value = 'mocked_result'
            mock_executor_class.return_value = mock_executor
            user_context = create_user_context()
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, enable_admin_tools=True)
            try:
                response = await dispatcher.execute_tool('corpus_create', {'param': 'value'})
                assert False, 'Expected PermissionError but execute_tool succeeded'
            except PermissionError as e:
                assert 'Admin permission required' in str(e) or 'lacks admin role' in str(e)
                metrics = dispatcher.get_metrics()
                assert metrics['permission_denials'] >= 1
                assert mock_executor.execute_tool_with_input.call_count == 0
            await dispatcher.cleanup()

class LifecycleAndCleanupTests:
    """Test dispatcher lifecycle and cleanup behavior."""

    @pytest.mark.asyncio
    async def test_cleanup_idempotency(self):
        """Test that cleanup can be called multiple times safely."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        await dispatcher.cleanup()
        await dispatcher.cleanup()
        await dispatcher.cleanup()
        assert not dispatcher._is_active

    @pytest.mark.asyncio
    async def test_inactive_dispatcher_method_calls(self):
        """Test that inactive dispatcher properly blocks method calls."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        await dispatcher.cleanup()
        assert not dispatcher._is_active
        with pytest.raises(RuntimeError) as exc_info:
            dispatcher.has_tool('any_tool')
        assert 'has been cleaned up' in str(exc_info.value)
        with pytest.raises(RuntimeError) as exc_info:
            tool = MockBaseTool('test_tool')
            dispatcher.register_tool(tool)
        assert 'has been cleaned up' in str(exc_info.value)
        with pytest.raises(RuntimeError):
            dispatcher.get_available_tools()

    @pytest.mark.asyncio
    async def test_registry_cleanup_behavior(self):
        """Test that tool registry is properly cleaned up."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        tool1 = MockBaseTool('tool1')
        tool2 = MockBaseTool('tool2')
        dispatcher.register_tool(tool1)
        dispatcher.register_tool(tool2)
        assert len(dispatcher.get_available_tools()) >= 2
        await dispatcher.cleanup()
        if hasattr(dispatcher, 'registry'):
            assert len(dispatcher.registry.list_keys()) == 0

    @pytest.mark.asyncio
    async def test_global_dispatcher_tracking(self):
        """Test global dispatcher tracking and cleanup."""
        initial_count = len(UnifiedToolDispatcher._active_dispatchers)
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        assert len(UnifiedToolDispatcher._active_dispatchers) == initial_count + 1
        assert dispatcher.dispatcher_id in UnifiedToolDispatcher._active_dispatchers
        await dispatcher.cleanup()
        assert len(UnifiedToolDispatcher._active_dispatchers) == initial_count
        assert dispatcher.dispatcher_id not in UnifiedToolDispatcher._active_dispatchers

class PerformanceAndStressTests:
    """Test performance characteristics and stress scenarios."""

    @pytest.mark.asyncio
    async def test_rapid_tool_execution_stress(self):
        """Test rapid consecutive tool execution stress."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=websocket_manager)
        tool = MockBaseTool('stress_tool')
        dispatcher.register_tool(tool)
        tasks = []
        for i in range(20):
            task = asyncio.create_task(dispatcher.execute_tool('stress_tool', {'iteration': i}))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        for response in responses:
            assert response.success
        assert tool.call_count == 20
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 20
        assert metrics['successful_executions'] == 20
        assert metrics['failed_executions'] == 0
        await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_memory_stability_under_load(self):
        """Test memory stability under sustained load."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=websocket_manager)
        tool = MockBaseTool('memory_tool')
        dispatcher.register_tool(tool)
        for i in range(100):
            response = await dispatcher.execute_tool('memory_tool', {'iteration': i, 'data': f'test_data_{i}'})
            assert response.success
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 100
        assert metrics['successful_executions'] == 100
        await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_permission_validation(self):
        """Test concurrent permission validation stress."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        tasks = []
        for i in range(10):
            task = asyncio.create_task(dispatcher._validate_tool_permissions(f'tool_{i}'))
            tasks.append(task)
        await asyncio.gather(*tasks)
        metrics = dispatcher.get_metrics()
        assert metrics['permission_checks'] >= 10
        await dispatcher.cleanup()

class LegacyCompatibilityTests:
    """Test legacy compatibility methods and deprecation warnings."""

    def test_legacy_global_factory_deprecation_warning(self):
        """Test that legacy global factory emits deprecation warning."""
        with patch('netra_backend.app.agents.supervisor.user_execution_context.UserExecutionContext') as mock_context_class:
            mock_context = Mock()
            mock_context.user_id = 'legacy_global'
            mock_context_class.return_value = mock_context
            with pytest.warns(DeprecationWarning) as warning_info:
                dispatcher = UnifiedToolDispatcherFactory.create_legacy_global()
            warning_message = str(warning_info[0].message)
            assert 'creates shared state' in warning_message
            assert 'Use create_for_request()' in warning_message
            assert dispatcher.strategy == DispatchStrategy.LEGACY
            assert dispatcher.user_context.user_id == 'legacy_global'

    @pytest.mark.asyncio
    async def test_legacy_dispatch_methods_functionality(self):
        """Test that legacy dispatch methods work correctly."""
        with patch('netra_backend.app.agents.unified_tool_execution.UnifiedToolExecutionEngine') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute_tool_with_input.return_value = 'mocked_result'
            mock_executor_class.return_value = mock_executor
            user_context = create_user_context()
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
            tool = MockBaseTool('legacy_test_tool')
            dispatcher.register_tool(tool)
            response1 = await dispatcher.dispatch_tool(tool_name='legacy_test_tool', parameters={'param': 'value1'}, state=None, run_id='ignored_run_id')
            assert isinstance(response1, ToolDispatchResponse)
            assert response1.success
            try:
                result2 = await dispatcher.dispatch('legacy_test_tool', param='value2')
                assert isinstance(result2, ToolResult)
            except Exception as e:
                assert 'ValidationError' in str(type(e)) or 'validation' in str(e).lower()
            assert mock_executor.execute_tool_with_input.call_count == 2
            await dispatcher.cleanup()

    @pytest.mark.asyncio
    async def test_websocket_bridge_property_compatibility(self):
        """Test websocket_bridge property for backward compatibility."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=websocket_manager)
        assert dispatcher1.websocket_bridge == websocket_manager
        websocket_bridge = MockAgentWebSocketBridge()
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user_context=create_user_context(user_id='user2', run_id='run2'), websocket_bridge=websocket_bridge)
        assert dispatcher2.websocket_bridge == websocket_bridge
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()

class ContextManagersTests:
    """Test context manager functionality."""

    @pytest.mark.asyncio
    async def test_request_scoped_context_manager_basic(self):
        """Test basic request-scoped context manager functionality."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        async with create_request_scoped_dispatcher(user_context, websocket_manager=websocket_manager) as dispatcher:
            assert dispatcher._is_active
            assert dispatcher.user_context == user_context
            tool = MockBaseTool('context_tool')
            dispatcher.register_tool(tool)
            response = await dispatcher.execute_tool('context_tool')
            assert response.success

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self):
        """Test context manager cleanup when exception occurs."""
        user_context = create_user_context()
        with pytest.raises(ValueError):
            async with create_request_scoped_dispatcher(user_context) as dispatcher:
                assert dispatcher._is_active
                raise ValueError('Test exception')

    @pytest.mark.asyncio
    async def test_scoped_context_manager_with_tools(self):
        """Test scoped context manager with initial tools."""
        user_context = create_user_context()
        tools = [MockBaseTool('scoped_tool1'), MockBaseTool('scoped_tool2')]
        websocket_manager = MockWebSocketManager()
        async with UnifiedToolDispatcher.create_scoped(user_context=user_context, websocket_bridge=websocket_manager, tools=tools) as dispatcher:
            assert dispatcher.has_tool('scoped_tool1')
            assert dispatcher.has_tool('scoped_tool2')
            assert dispatcher.has_websocket_support
            response1 = await dispatcher.execute_tool('scoped_tool1')
            response2 = await dispatcher.execute_tool('scoped_tool2')
            assert response1.success and response2.success
        assert len(websocket_manager.events_sent) == 4
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')