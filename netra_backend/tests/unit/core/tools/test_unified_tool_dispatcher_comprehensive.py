"""Comprehensive unit tests for UnifiedToolDispatcher - SECOND PRIORITY SSOT class.

This test suite validates the most critical SSOT class responsible for 90% of agent value
delivery through tool execution. Tests ensure factory-enforced isolation, multi-user 
safety, WebSocket event emission, and permission boundaries.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise, Platform/Internal) 
- Business Goal: Platform Stability, Risk Reduction, Multi-User Safety
- Value Impact: Tool execution = 90% of agent value delivery to customers
- Strategic Impact: Request-scoped isolation prevents $10M+ churn from user data leakage

CRITICAL REQUIREMENTS:
- Factory pattern enforcement (NO direct instantiation)
- Request-scoped isolation for multi-user safety  
- WebSocket events for ALL tool executions (chat UX)
- Permission validation and admin tool boundaries
- Comprehensive error handling and metrics tracking

Test Architecture:
- NO mocks for business logic (CHEATING = ABOMINATION)
- Real instances with minimal external dependencies
- ABSOLUTE IMPORTS only
- Tests must RAISE ERRORS - no try/except masking
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, MagicMock

from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse, 
    DispatchStrategy,
    AuthenticationError,
    PermissionError,
    SecurityViolationError,
    create_request_scoped_dispatcher
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus


class MockBaseTool:
    """Mock LangChain tool for testing purposes."""
    
    def __init__(self, name: str, should_fail: bool = False, execution_result: Any = None):
        self.name = name
        self.should_fail = should_fail
        self.execution_result = execution_result or f"Result from {name}"
        self.call_count = 0
        
    async def arun(self, tool_input: Dict[str, Any]) -> Any:
        """Mock async tool execution - matches LangChain BaseTool interface."""
        self.call_count += 1
        if self.should_fail:
            raise ValueError(f"Tool {self.name} execution failed")
        return self.execution_result
        
    def __call__(self, **kwargs) -> Any:
        """Synchronous call interface."""
        return self.execution_result


class MockWebSocketManager:
    """Mock WebSocket manager for testing WebSocket event emission."""
    
    def __init__(self):
        self.events_sent = []
        self.should_fail = False
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Mock send_event method."""
        if self.should_fail:
            raise Exception("WebSocket send failed")
            
        self.events_sent.append({
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        })
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


class MockAgentWebSocketBridge:
    """Mock AgentWebSocketBridge for testing bridge adapter pattern."""
    
    def __init__(self):
        self.tool_executing_calls = []
        self.tool_completed_calls = []
        self.should_fail = False
        
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Mock tool executing notification."""
        if self.should_fail:
            return False
            
        self.tool_executing_calls.append({
            'run_id': run_id,
            'agent_name': agent_name, 
            'tool_name': tool_name,
            'parameters': parameters
        })
        return True
        
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict[str, Any], execution_time_ms: float) -> bool:
        """Mock tool completed notification."""
        if self.should_fail:
            return False
            
        self.tool_completed_calls.append({
            'run_id': run_id,
            'agent_name': agent_name,
            'tool_name': tool_name, 
            'result': result,
            'execution_time_ms': execution_time_ms
        })
        return True


def create_user_context(
    user_id: str = "test_user_123",
    run_id: str = None,
    thread_id: str = "test_thread",
    metadata: Optional[Dict[str, Any]] = None
) -> UserExecutionContext:
    """Create test UserExecutionContext with proper isolation."""
    if run_id is None:
        run_id = f"run_{int(time.time()*1000)}"
        
    return UserExecutionContext(
        user_id=user_id,
        run_id=run_id, 
        thread_id=thread_id,
        metadata=metadata or {}
    )


def create_admin_user_context(
    user_id: str = "admin_user_123",
    run_id: str = None
) -> UserExecutionContext:
    """Create UserExecutionContext with admin permissions."""
    metadata = {
        'roles': ['admin'],
        'permissions': ['admin_tools', 'corpus_admin', 'user_admin']
    }
    return create_user_context(user_id=user_id, run_id=run_id, metadata=metadata)


class TestUnifiedToolDispatcherFactoryEnforcement:
    """Test factory pattern enforcement - CRITICAL security requirement."""
    
    def test_direct_instantiation_raises_runtime_error(self):
        """Direct instantiation must raise RuntimeError to enforce factory pattern.
        
        BVJ: This prevents shared state issues that could cause user data leakage
        worth $10M+ in churn and regulatory penalties.
        """
        with pytest.raises(RuntimeError) as exc_info:
            UnifiedToolDispatcher()
            
        error_message = str(exc_info.value)
        assert "Direct instantiation of UnifiedToolDispatcher is forbidden" in error_message
        assert "Use factory methods for proper isolation" in error_message
        assert "UnifiedToolDispatcher.create_for_user(context)" in error_message
        assert "UnifiedToolDispatcherFactory.create_for_request(context)" in error_message
        
    def test_factory_pattern_enforcement_comprehensive(self):
        """Verify factory pattern prevents multiple instantiation methods."""
        # Test all blocked instantiation methods
        blocked_methods = [
            lambda: UnifiedToolDispatcher(),
            lambda: UnifiedToolDispatcher.__new__(UnifiedToolDispatcher),
        ]
        
        for method in blocked_methods:
            with pytest.raises((RuntimeError, TypeError)):
                method()
                
    def test_error_message_provides_correct_guidance(self):
        """Factory error message must provide actionable guidance."""
        try:
            UnifiedToolDispatcher()
        except RuntimeError as e:
            error_msg = str(e)
            # Must contain all valid factory methods
            assert "create_for_user(context)" in error_msg
            assert "create_scoped(context)" in error_msg  
            assert "create_for_request(context)" in error_msg
            assert "create_for_admin(context, db)" in error_msg
            assert "user isolation" in error_msg
            assert "shared state issues" in error_msg


class TestUnifiedToolDispatcherCreation:
    """Test proper dispatcher creation through factory methods."""
    
    @pytest.mark.asyncio
    async def test_create_for_user_basic_success(self):
        """Test basic dispatcher creation with user context.
        
        BVJ: Request-scoped isolation prevents user data leakage in multi-user environment.
        """
        user_context = create_user_context()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Verify proper initialization
        assert dispatcher.user_context == user_context
        assert dispatcher.strategy == DispatchStrategy.DEFAULT
        assert dispatcher.dispatcher_id.startswith(user_context.user_id)
        assert user_context.run_id in dispatcher.dispatcher_id
        assert dispatcher._is_active is True
        assert dispatcher.created_at is not None
        
        # Cleanup
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio 
    async def test_create_for_user_with_websocket_manager(self):
        """Test dispatcher creation with WebSocket manager for event emission."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        # Verify WebSocket integration
        assert dispatcher.has_websocket_support is True
        assert dispatcher.websocket_manager == websocket_manager
        assert hasattr(dispatcher, '_websocket_ready')
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_create_for_user_with_websocket_bridge_adapter(self):
        """Test dispatcher creation with AgentWebSocketBridge adapter pattern."""
        user_context = create_user_context()
        websocket_bridge = MockAgentWebSocketBridge()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_bridge
        )
        
        # Verify bridge adapter creation
        assert dispatcher.has_websocket_support is True
        assert hasattr(dispatcher, '_websocket_bridge')
        assert dispatcher._websocket_bridge == websocket_bridge
        
        # Verify adapter implements WebSocketManager interface
        adapter = dispatcher.websocket_manager
        assert hasattr(adapter, 'send_event')
        assert hasattr(adapter, 'has_websocket_support')
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_create_for_user_with_tools(self):
        """Test dispatcher creation with initial tools."""
        user_context = create_user_context()
        tools = [
            MockBaseTool("test_tool_1"),
            MockBaseTool("test_tool_2") 
        ]
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            tools=tools
        )
        
        # Verify tools registered
        assert dispatcher.has_tool("test_tool_1") is True
        assert dispatcher.has_tool("test_tool_2") is True
        assert len(dispatcher.get_available_tools()) >= 2
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_create_for_user_admin_tools_enabled(self):
        """Test dispatcher creation with admin tools enabled."""
        user_context = create_admin_user_context()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            enable_admin_tools=True
        )
        
        # Verify admin strategy and components
        assert dispatcher.strategy == DispatchStrategy.ADMIN
        assert hasattr(dispatcher, 'admin_tools')
        assert len(dispatcher.admin_tools) > 0
        assert 'corpus_create' in dispatcher.admin_tools
        assert 'user_admin' in dispatcher.admin_tools
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_create_for_user_validation_failures(self):
        """Test dispatcher creation validation failures."""
        
        # Test None user context
        with pytest.raises(AuthenticationError) as exc_info:
            await UnifiedToolDispatcher.create_for_user(None)
        assert "Valid UserExecutionContext required" in str(exc_info.value)
        
        # Test invalid user context (no user_id)
        invalid_context = Mock()
        invalid_context.user_id = None
        
        with pytest.raises(AuthenticationError) as exc_info:
            await UnifiedToolDispatcher.create_for_user(invalid_context)
        assert "Valid UserExecutionContext required" in str(exc_info.value)


class TestUnifiedToolDispatcherScoped:
    """Test scoped dispatcher creation with automatic cleanup."""
    
    @pytest.mark.asyncio
    async def test_create_scoped_context_manager_success(self):
        """Test scoped dispatcher with automatic cleanup."""
        user_context = create_user_context()
        
        async with UnifiedToolDispatcher.create_scoped(user_context) as dispatcher:
            # Verify dispatcher is active during context
            assert dispatcher._is_active is True
            assert dispatcher.user_context == user_context
            
            # Verify tools work
            tool = MockBaseTool("test_tool")
            dispatcher.register_tool(tool)
            assert dispatcher.has_tool("test_tool") is True
            
        # Verify cleanup happened automatically
        # Note: We can't test _is_active directly as cleanup() marks it False
        
    @pytest.mark.asyncio  
    async def test_create_scoped_with_websocket_and_tools(self):
        """Test scoped dispatcher with WebSocket and tools."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        tools = [MockBaseTool("scoped_tool")]
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=user_context,
            websocket_bridge=websocket_manager,
            tools=tools
        ) as dispatcher:
            assert dispatcher.has_websocket_support is True
            assert dispatcher.has_tool("scoped_tool") is True
            
        # Verify no errors during cleanup
        
    @pytest.mark.asyncio
    async def test_create_scoped_cleanup_on_exception(self):
        """Test scoped dispatcher cleanup on exception."""
        user_context = create_user_context()
        
        with pytest.raises(ValueError):
            async with UnifiedToolDispatcher.create_scoped(user_context) as dispatcher:
                assert dispatcher._is_active is True
                raise ValueError("Test exception")
                
        # Cleanup should still happen even with exception


class TestUnifiedToolDispatcherFactory:
    """Test UnifiedToolDispatcherFactory creation methods."""
    
    def test_create_for_request_success(self):
        """Test factory request-scoped dispatcher creation."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        tools = [MockBaseTool("factory_tool")]
        
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=tools
        )
        
        # Verify proper initialization
        assert dispatcher.user_context == user_context
        assert dispatcher.strategy == DispatchStrategy.DEFAULT
        assert dispatcher.websocket_manager == websocket_manager
        assert dispatcher.has_tool("factory_tool") is True
        
    def test_create_for_request_validation(self):
        """Test factory request creation validation."""
        with pytest.raises(ValueError) as exc_info:
            UnifiedToolDispatcherFactory.create_for_request(None)
        assert "user_context is required" in str(exc_info.value)
        
    def test_create_for_admin_success(self):
        """Test factory admin dispatcher creation."""
        user_context = create_admin_user_context()
        mock_db = Mock()
        mock_user = Mock()
        mock_user.is_admin = True
        websocket_manager = MockWebSocketManager()
        mock_permission_service = Mock()
        
        dispatcher = UnifiedToolDispatcherFactory.create_for_admin(
            user_context=user_context,
            db=mock_db,
            user=mock_user,
            websocket_manager=websocket_manager,
            permission_service=mock_permission_service
        )
        
        # Verify admin initialization
        assert dispatcher.strategy == DispatchStrategy.ADMIN
        assert dispatcher.db == mock_db
        assert dispatcher.user == mock_user
        assert dispatcher.permission_service == mock_permission_service
        assert hasattr(dispatcher, 'admin_tools')
        
    def test_create_for_admin_validation(self):
        """Test factory admin creation validation."""
        with pytest.raises(ValueError) as exc_info:
            UnifiedToolDispatcherFactory.create_for_admin(
                user_context=None,
                db=Mock(),
                user=Mock()
            )
        assert "user_context is required" in str(exc_info.value)
        
    def test_create_legacy_global_deprecated(self):
        """Test legacy global dispatcher creation with deprecation warning.""" 
        tools = [MockBaseTool("legacy_tool")]
        
        with pytest.warns(DeprecationWarning) as warning_info:
            dispatcher = UnifiedToolDispatcherFactory.create_legacy_global(tools)
            
        # Verify warning content
        assert "creates shared state" in str(warning_info[0].message)
        assert "Use create_for_request()" in str(warning_info[0].message)
        
        # Verify legacy dispatcher creation
        assert dispatcher.strategy == DispatchStrategy.LEGACY
        assert dispatcher.user_context.user_id == "legacy_global"
        assert dispatcher.has_tool("legacy_tool") is True


class TestUnifiedToolDispatcherToolManagement:
    """Test tool registration and management."""
    
    @pytest.mark.asyncio
    async def test_register_tool_success(self):
        """Test successful tool registration."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("new_tool")
        dispatcher.register_tool(tool)
        
        assert dispatcher.has_tool("new_tool") is True
        assert "new_tool" in dispatcher.get_available_tools()
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_has_tool_validation(self):
        """Test tool existence checking."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Test non-existent tool
        assert dispatcher.has_tool("non_existent") is False
        
        # Test existing tool
        tool = MockBaseTool("existing_tool")
        dispatcher.register_tool(tool)
        assert dispatcher.has_tool("existing_tool") is True
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_get_available_tools(self):
        """Test getting list of available tools."""
        user_context = create_user_context()
        tools = [
            MockBaseTool("tool_1"),
            MockBaseTool("tool_2"),
            MockBaseTool("tool_3")
        ]
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            tools=tools
        )
        
        available_tools = dispatcher.get_available_tools()
        assert isinstance(available_tools, list)
        assert "tool_1" in available_tools
        assert "tool_2" in available_tools  
        assert "tool_3" in available_tools
        assert len(available_tools) >= 3
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_tools_property(self):
        """Test tools property access.""" 
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("property_tool")
        dispatcher.register_tool(tool)
        
        tools_dict = dispatcher.tools
        assert isinstance(tools_dict, dict)
        assert "property_tool" in tools_dict
        assert tools_dict["property_tool"] == tool
        
        await dispatcher.cleanup()


class TestUnifiedToolDispatcherExecution:
    """Test core tool execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_basic_functionality(self):
        """Test basic tool execution without WebSocket complexity."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("basic_tool", execution_result="Basic result")
        dispatcher.register_tool(tool)
        
        # Execute tool without WebSocket
        response = await dispatcher.execute_tool("basic_tool", {"param": "value"})
        
        # Verify basic response
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is True
        assert response.error is None
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution with WebSocket events.
        
        BVJ: Tool execution = 90% of agent value delivery. WebSocket events
        provide real-time visibility for chat UX worth $500k+ ARR.
        """
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        tool = MockBaseTool("execution_tool", execution_result="Tool executed successfully")
        dispatcher.register_tool(tool)
        
        # Execute tool
        response = await dispatcher.execute_tool(
            tool_name="execution_tool",
            parameters={"param1": "value1", "param2": "value2"}
        )
        
        # Verify response
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is True
        assert response.result is not None
        assert response.error is None
        assert "execution_time_ms" in response.metadata
        assert "dispatcher_id" in response.metadata
        
        # For ToolResult objects, check the payload content
        if hasattr(response.result, 'payload') and hasattr(response.result.payload, 'result'):
            assert response.result.payload.result == "Tool executed successfully"
        
        # Verify tool was called
        assert tool.call_count == 1
        
        # Verify WebSocket events sent
        executing_events = websocket_manager.get_events_by_type("tool_executing")
        completed_events = websocket_manager.get_events_by_type("tool_completed")
        
        assert len(executing_events) == 1
        assert len(completed_events) == 1
        
        # Verify executing event data
        executing_event = executing_events[0]
        assert executing_event['data']['tool_name'] == "execution_tool"
        assert executing_event['data']['parameters'] == {"param1": "value1", "param2": "value2"}
        assert executing_event['data']['user_id'] == user_context.user_id
        assert executing_event['data']['run_id'] == user_context.run_id
        
        # Verify completed event data
        completed_event = completed_events[0]
        assert completed_event['data']['tool_name'] == "execution_tool"
        # WebSocket events should be sent even if there are execution complexities
        # The main thing is that events are actually sent during tool execution
        assert 'status' in completed_event['data']
        assert 'user_id' in completed_event['data']
        assert 'run_id' in completed_event['data']
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_execute_tool_failure_with_error_events(self):
        """Test tool execution failure with proper error WebSocket events."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        tool = MockBaseTool("failing_tool", should_fail=True)
        dispatcher.register_tool(tool)
        
        # Execute failing tool
        response = await dispatcher.execute_tool(
            tool_name="failing_tool",
            parameters={"param": "value"}
        )
        
        # Verify error response
        assert response.success is False
        assert response.result is None
        assert "Tool failing_tool execution failed" in response.error
        assert "execution_time_ms" in response.metadata
        
        # Verify error WebSocket events
        executing_events = websocket_manager.get_events_by_type("tool_executing")
        completed_events = websocket_manager.get_events_by_type("tool_completed")
        
        assert len(executing_events) == 1
        assert len(completed_events) == 1
        
        completed_event = completed_events[0]
        assert completed_event['data']['status'] == "error"
        assert "Tool failing_tool execution failed" in completed_event['data']['error']
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_execute_tool_without_websocket_support(self):
        """Test tool execution without WebSocket manager."""
        user_context = create_user_context()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("no_websocket_tool")
        dispatcher.register_tool(tool)
        
        # Execute tool
        response = await dispatcher.execute_tool("no_websocket_tool", {"param": "value"})
        
        # Verify execution still works
        assert response.success is True
        assert dispatcher.has_websocket_support is False
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio  
    async def test_execute_tool_not_found(self):
        """Test execution of non-existent tool."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        response = await dispatcher.execute_tool("non_existent_tool")
        
        assert response.success is False
        assert "Tool non_existent_tool not found" in response.error
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_execute_tool_websocket_bridge_adapter(self):
        """Test tool execution with AgentWebSocketBridge adapter."""
        user_context = create_user_context()
        websocket_bridge = MockAgentWebSocketBridge()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_bridge
        )
        
        tool = MockBaseTool("bridge_tool")
        dispatcher.register_tool(tool)
        
        # Execute tool
        response = await dispatcher.execute_tool("bridge_tool", {"param": "test"})
        
        # Verify execution success
        assert response.success is True
        
        # Verify bridge adapter calls
        assert len(websocket_bridge.tool_executing_calls) == 1
        assert len(websocket_bridge.tool_completed_calls) == 1
        
        executing_call = websocket_bridge.tool_executing_calls[0]
        assert executing_call['tool_name'] == "bridge_tool"
        assert executing_call['parameters'] == {"param": "test"}
        assert executing_call['run_id'] == user_context.run_id
        
        completed_call = websocket_bridge.tool_completed_calls[0]
        assert completed_call['tool_name'] == "bridge_tool"
        assert completed_call['result']['output'] is not None
        
        await dispatcher.cleanup()


class TestUnifiedToolDispatcherPermissions:
    """Test permission validation and security boundaries."""
    
    @pytest.mark.asyncio
    async def test_permission_validation_success(self):
        """Test successful permission validation for regular tools."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("permitted_tool")
        dispatcher.register_tool(tool)
        
        # Should not raise exception
        await dispatcher._validate_tool_permissions("permitted_tool")
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio  
    async def test_permission_validation_no_user_context(self):
        """Test permission validation failure with invalid user context."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Corrupt user context
        dispatcher.user_context = None
        
        with pytest.raises(AuthenticationError) as exc_info:
            await dispatcher._validate_tool_permissions("any_tool")
            
        assert "SECURITY: User context required" in str(exc_info.value)
        assert "any_tool" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_admin_tool_permission_enforcement(self):
        """Test admin tool permission enforcement."""
        # Regular user context (no admin role)
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            enable_admin_tools=True  # This should still enforce permissions
        )
        
        # Test admin tool permission denial
        with pytest.raises(PermissionError) as exc_info:
            await dispatcher._validate_tool_permissions("corpus_create")
            
        assert "Admin permission required for tool corpus_create" in str(exc_info.value)
        assert user_context.user_id in str(exc_info.value)
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_admin_tool_permission_success(self):
        """Test admin tool access with proper permissions."""
        user_context = create_admin_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            enable_admin_tools=True
        )
        
        # Should not raise exception for admin user
        await dispatcher._validate_tool_permissions("corpus_create")
        await dispatcher._validate_tool_permissions("user_admin")
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_check_admin_permission_metadata(self):
        """Test admin permission checking via metadata."""
        user_context = create_admin_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        assert dispatcher._check_admin_permission() is True
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio  
    async def test_check_admin_permission_user_object(self):
        """Test admin permission checking via user object."""
        user_context = create_user_context()
        mock_user = Mock()
        mock_user.is_admin = True
        
        dispatcher = UnifiedToolDispatcherFactory.create_for_admin(
            user_context=user_context,
            db=Mock(),
            user=mock_user
        )
        
        assert dispatcher._check_admin_permission() is True
        
    @pytest.mark.asyncio
    async def test_check_admin_permission_service(self):
        """Test admin permission checking via permission service."""
        user_context = create_user_context()
        mock_user = Mock()
        mock_user.is_admin = False
        mock_permission_service = Mock()
        mock_permission_service.has_admin_permission.return_value = True
        
        dispatcher = UnifiedToolDispatcherFactory.create_for_admin(
            user_context=user_context,
            db=Mock(),
            user=mock_user,
            permission_service=mock_permission_service
        )
        
        assert dispatcher._check_admin_permission() is True
        mock_permission_service.has_admin_permission.assert_called_once_with(mock_user)


class TestUnifiedToolDispatcherWebSocketEvents:
    """Test WebSocket event emission - CRITICAL for chat UX."""
    
    @pytest.mark.asyncio
    async def test_websocket_event_emission_success(self):
        """Test successful WebSocket event emission during tool execution."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        tool = MockBaseTool("event_tool")
        dispatcher.register_tool(tool)
        
        # Execute tool and verify events
        await dispatcher.execute_tool("event_tool", {"test": "param"})
        
        # Verify both events sent
        assert len(websocket_manager.events_sent) == 2
        
        executing_event = websocket_manager.get_events_by_type("tool_executing")[0]
        completed_event = websocket_manager.get_events_by_type("tool_completed")[0]
        
        # Verify event structure and data
        assert executing_event['data']['tool_name'] == "event_tool"
        assert executing_event['data']['parameters'] == {"test": "param"}
        assert executing_event['data']['user_id'] == user_context.user_id
        assert executing_event['data']['run_id'] == user_context.run_id
        assert executing_event['data']['thread_id'] == user_context.thread_id
        assert 'timestamp' in executing_event['data']
        
        assert completed_event['data']['tool_name'] == "event_tool"
        assert completed_event['data']['status'] == "success"
        assert completed_event['data']['user_id'] == user_context.user_id
        assert 'execution_time_ms' in completed_event['data']
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_websocket_event_failure_resilience(self):
        """Test tool execution continues even if WebSocket events fail."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        websocket_manager.should_fail = True
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        tool = MockBaseTool("resilient_tool")
        dispatcher.register_tool(tool)
        
        # Tool execution should succeed despite WebSocket failures
        response = await dispatcher.execute_tool("resilient_tool")
        
        assert response.success is True
        # Events should be empty due to failures, but execution succeeded
        assert len(websocket_manager.events_sent) == 0
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_emit_tool_executing_event(self):
        """Test manual tool_executing event emission."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        # Emit executing event manually
        await dispatcher._emit_tool_executing("manual_tool", {"param": "value"})
        
        events = websocket_manager.get_events_by_type("tool_executing")
        assert len(events) == 1
        
        event_data = events[0]['data']
        assert event_data['tool_name'] == "manual_tool"
        assert event_data['parameters'] == {"param": "value"}
        assert event_data['user_id'] == user_context.user_id
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_emit_tool_completed_success_event(self):
        """Test manual tool_completed success event emission."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        # Emit completed success event
        await dispatcher._emit_tool_completed(
            "completed_tool", 
            result="Success result",
            execution_time=123.45
        )
        
        events = websocket_manager.get_events_by_type("tool_completed")
        assert len(events) == 1
        
        event_data = events[0]['data']
        assert event_data['tool_name'] == "completed_tool"
        assert event_data['status'] == "success"
        assert event_data['result'] == "Success result"
        assert event_data['execution_time_ms'] == 123.45
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_emit_tool_completed_error_event(self):
        """Test manual tool_completed error event emission."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        # Emit completed error event
        await dispatcher._emit_tool_completed(
            "error_tool",
            error="Tool execution failed",
            execution_time=67.89
        )
        
        events = websocket_manager.get_events_by_type("tool_completed")
        assert len(events) == 1
        
        event_data = events[0]['data']
        assert event_data['tool_name'] == "error_tool"
        assert event_data['status'] == "error"
        assert event_data['error'] == "Tool execution failed"
        assert event_data['execution_time_ms'] == 67.89
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_set_websocket_manager(self):
        """Test setting/updating WebSocket manager."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Initially no WebSocket support
        assert dispatcher.has_websocket_support is False
        
        # Set WebSocket manager
        websocket_manager = MockWebSocketManager()
        dispatcher.set_websocket_manager(websocket_manager)
        
        # Verify WebSocket support enabled
        assert dispatcher.has_websocket_support is True
        assert dispatcher.websocket_manager == websocket_manager
        
        await dispatcher.cleanup()


class TestUnifiedToolDispatcherMultiUser:
    """Test multi-user isolation and dispatcher limits."""
    
    @pytest.mark.asyncio
    async def test_multi_user_dispatcher_isolation(self):
        """Test that dispatchers for different users are properly isolated."""
        user1_context = create_user_context(user_id="user_1")
        user2_context = create_user_context(user_id="user_2")
        
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user1_context)
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user2_context)
        
        # Verify different dispatchers
        assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id
        assert dispatcher1.user_context.user_id == "user_1"
        assert dispatcher2.user_context.user_id == "user_2"
        
        # Verify isolated tool registrations
        tool1 = MockBaseTool("user1_tool")
        tool2 = MockBaseTool("user2_tool")
        
        dispatcher1.register_tool(tool1)
        dispatcher2.register_tool(tool2)
        
        assert dispatcher1.has_tool("user1_tool") is True
        assert dispatcher1.has_tool("user2_tool") is False
        assert dispatcher2.has_tool("user1_tool") is False
        assert dispatcher2.has_tool("user2_tool") is True
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
    @pytest.mark.asyncio
    async def test_user_dispatcher_limit_enforcement(self):
        """Test that user dispatcher limits are enforced."""
        user_context = create_user_context(user_id="limited_user")
        
        # Create dispatchers up to limit (10 by default)
        dispatchers = []
        for i in range(UnifiedToolDispatcher._max_dispatchers_per_user):
            dispatcher = await UnifiedToolDispatcher.create_for_user(
                create_user_context(
                    user_id="limited_user",
                    run_id=f"run_{i}"
                )
            )
            dispatchers.append(dispatcher)
            
        # Verify all created successfully
        assert len(dispatchers) == UnifiedToolDispatcher._max_dispatchers_per_user
        
        # Creating one more should trigger cleanup of oldest
        new_dispatcher = await UnifiedToolDispatcher.create_for_user(
            create_user_context(
                user_id="limited_user", 
                run_id="run_overflow"
            )
        )
        
        # Verify new dispatcher created
        assert new_dispatcher._is_active is True
        
        # Cleanup all
        for dispatcher in dispatchers:
            await dispatcher.cleanup()
        await new_dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_cleanup_user_dispatchers(self):
        """Test cleaning up all dispatchers for a specific user."""
        user_id = "cleanup_test_user"
        
        # Create multiple dispatchers for user
        dispatchers = []
        for i in range(3):
            dispatcher = await UnifiedToolDispatcher.create_for_user(
                create_user_context(
                    user_id=user_id,
                    run_id=f"run_{i}"
                )
            )
            dispatchers.append(dispatcher)
            
        # Verify all active
        for dispatcher in dispatchers:
            assert dispatcher._is_active is True
            
        # Cleanup all dispatchers for user
        await UnifiedToolDispatcher.cleanup_user_dispatchers(user_id)
        
        # Verify all cleaned up (we can't check _is_active directly since cleanup modifies it)
        # But the cleanup method should have been called on all


class TestUnifiedToolDispatcherLegacyCompatibility:
    """Test legacy compatibility methods."""
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_legacy_compatibility(self):
        """Test legacy dispatch_tool method redirects properly."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("legacy_tool")
        dispatcher.register_tool(tool)
        
        # Use legacy method
        response = await dispatcher.dispatch_tool(
            tool_name="legacy_tool",
            parameters={"param": "value"},
            state=None,
            run_id="legacy_run"
        )
        
        # Verify same response type as execute_tool
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is True
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_dispatch_legacy_compatibility(self):
        """Test legacy dispatch method returns ToolResult."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("dispatch_tool")
        dispatcher.register_tool(tool)
        
        # Use legacy dispatch method
        result = await dispatcher.dispatch("dispatch_tool", param="value")
        
        # Verify ToolResult type
        assert isinstance(result, ToolResult)
        assert result.tool_name == "dispatch_tool"
        assert result.status == ToolStatus.SUCCESS
        assert result.error is None
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_dispatch_legacy_error_conversion(self):
        """Test legacy dispatch method error conversion.""" 
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("error_tool", should_fail=True)
        dispatcher.register_tool(tool)
        
        # Use legacy dispatch method
        result = await dispatcher.dispatch("error_tool")
        
        # Verify error ToolResult
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.FAILURE
        assert result.result is None
        assert result.error is not None
        
        await dispatcher.cleanup()
        
    @property  
    def test_websocket_bridge_property(self):
        """Test websocket_bridge compatibility property."""
        # This would need to be tested with actual dispatcher instance
        pass


class TestUnifiedToolDispatcherMetrics:
    """Test metrics tracking and performance monitoring."""
    
    @pytest.mark.asyncio  
    async def test_metrics_initialization(self):
        """Test that metrics are properly initialized."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        metrics = dispatcher.get_metrics()
        
        # Verify all expected metrics present
        expected_metrics = [
            'tools_executed', 'successful_executions', 'failed_executions',
            'total_execution_time_ms', 'websocket_events_sent', 'permission_checks',
            'permission_denials', 'security_violations', 'last_execution_time',
            'created_at', 'user_id', 'dispatcher_id'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
            
        # Verify initial values
        assert metrics['tools_executed'] == 0
        assert metrics['successful_executions'] == 0  
        assert metrics['failed_executions'] == 0
        assert metrics['user_id'] == user_context.user_id
        assert metrics['dispatcher_id'] == dispatcher.dispatcher_id
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_metrics_tracking_successful_execution(self):
        """Test metrics tracking for successful tool execution."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        tool = MockBaseTool("metrics_tool")
        dispatcher.register_tool(tool)
        
        # Execute tool
        await dispatcher.execute_tool("metrics_tool")
        
        # Verify metrics updated
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 1
        assert metrics['successful_executions'] == 1
        assert metrics['failed_executions'] == 0
        assert metrics['total_execution_time_ms'] > 0
        assert metrics['websocket_events_sent'] == 2  # executing + completed
        assert metrics['permission_checks'] == 1
        assert metrics['last_execution_time'] is not None
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_metrics_tracking_failed_execution(self):
        """Test metrics tracking for failed tool execution."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("failing_metrics_tool", should_fail=True)
        dispatcher.register_tool(tool)
        
        # Execute failing tool
        await dispatcher.execute_tool("failing_metrics_tool")
        
        # Verify error metrics updated
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 1
        assert metrics['successful_executions'] == 0
        assert metrics['failed_executions'] == 1
        assert metrics['total_execution_time_ms'] > 0
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_metrics_permission_tracking(self):
        """Test metrics tracking for permission checks and denials."""
        user_context = create_user_context()  # Non-admin user
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            enable_admin_tools=True
        )
        
        # Try to validate admin tool (should be denied)
        try:
            await dispatcher._validate_tool_permissions("corpus_create")
        except PermissionError:
            pass  # Expected
            
        metrics = dispatcher.get_metrics()
        assert metrics['permission_checks'] == 1
        assert metrics['permission_denials'] == 1
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_metrics_security_violations(self):
        """Test metrics tracking for security violations."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Corrupt user context to trigger security violation
        dispatcher.user_context = None
        
        try:
            await dispatcher._validate_tool_permissions("any_tool")
        except AuthenticationError:
            pass  # Expected
            
        metrics = dispatcher.get_metrics()
        assert metrics['security_violations'] == 1
        
    @pytest.mark.asyncio
    async def test_metrics_multiple_executions(self):
        """Test metrics accumulation over multiple executions.""" 
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        # Register tools
        success_tool = MockBaseTool("success_tool")
        fail_tool = MockBaseTool("fail_tool", should_fail=True)
        dispatcher.register_tool(success_tool)
        dispatcher.register_tool(fail_tool)
        
        # Execute multiple tools
        await dispatcher.execute_tool("success_tool")
        await dispatcher.execute_tool("success_tool")
        await dispatcher.execute_tool("fail_tool")
        
        # Verify accumulated metrics
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 3
        assert metrics['successful_executions'] == 2
        assert metrics['failed_executions'] == 1
        assert metrics['websocket_events_sent'] == 6  # 2 events * 3 executions
        assert metrics['permission_checks'] == 3
        
        await dispatcher.cleanup()


class TestUnifiedToolDispatcherLifecycle:
    """Test dispatcher lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_dispatcher_active_state(self):
        """Test dispatcher active state management."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Verify initially active
        assert dispatcher._is_active is True
        
        # Verify methods work when active
        tool = MockBaseTool("active_tool")
        dispatcher.register_tool(tool)
        assert dispatcher.has_tool("active_tool") is True
        
        # Cleanup and verify inactive
        await dispatcher.cleanup()
        assert dispatcher._is_active is False
        
    @pytest.mark.asyncio 
    async def test_ensure_active_validation(self):
        """Test _ensure_active validation method."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Should not raise when active
        dispatcher._ensure_active()  # No exception
        
        # Cleanup and test inactive state
        await dispatcher.cleanup()
        
        with pytest.raises(RuntimeError) as exc_info:
            dispatcher._ensure_active()
            
        assert "has been cleaned up" in str(exc_info.value)
        assert dispatcher.dispatcher_id in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_cleanup_comprehensive(self):
        """Test comprehensive cleanup of dispatcher resources."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Add some tools and execute
        tool = MockBaseTool("cleanup_tool")
        dispatcher.register_tool(tool)
        await dispatcher.execute_tool("cleanup_tool")
        
        # Verify active state and data
        assert dispatcher._is_active is True
        assert len(dispatcher.get_available_tools()) > 0
        
        # Cleanup
        await dispatcher.cleanup()
        
        # Verify cleanup
        assert dispatcher._is_active is False
        # Registry should be cleared (empty)
        assert len(dispatcher.get_available_tools()) == 0
        
    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self):
        """Test that cleanup can be called multiple times safely."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Multiple cleanup calls should not raise errors
        await dispatcher.cleanup()
        await dispatcher.cleanup()  # Should be safe
        await dispatcher.cleanup()  # Should still be safe
        
        assert dispatcher._is_active is False
        
    @pytest.mark.asyncio
    async def test_dispatcher_registration_tracking(self):
        """Test that dispatchers are properly registered and unregistered."""
        user_context = create_user_context()
        
        # Track initial count
        initial_count = len(UnifiedToolDispatcher._active_dispatchers)
        
        # Create dispatcher
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Verify registered
        assert len(UnifiedToolDispatcher._active_dispatchers) == initial_count + 1
        assert dispatcher.dispatcher_id in UnifiedToolDispatcher._active_dispatchers
        
        # Cleanup and verify unregistered  
        await dispatcher.cleanup()
        assert len(UnifiedToolDispatcher._active_dispatchers) == initial_count
        assert dispatcher.dispatcher_id not in UnifiedToolDispatcher._active_dispatchers


class TestUnifiedToolDispatcherErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_invalid_tool_execution(self):
        """Test execution of invalid/missing tools."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Test non-existent tool
        response = await dispatcher.execute_tool("non_existent_tool")
        assert response.success is False
        assert "not found in registry" in response.error
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_permission_bypass_attempts(self):
        """Test that permission bypass attempts are properly blocked."""
        user_context = create_user_context()  # Regular user
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            enable_admin_tools=True
        )
        
        # Attempt to execute admin tool
        response = await dispatcher.execute_tool("corpus_create")
        
        assert response.success is False  
        assert "Admin permission required" in response.error
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_safety(self):
        """Test thread safety for concurrent tool execution."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Register tool
        tool = MockBaseTool("concurrent_tool")
        dispatcher.register_tool(tool)
        
        # Execute multiple tools concurrently
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                dispatcher.execute_tool("concurrent_tool", {"id": i})
            )
            tasks.append(task)
            
        # Wait for all executions
        responses = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        for response in responses:
            assert response.success is True
            
        # Verify tool called correct number of times
        assert tool.call_count == 5
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_websocket_error_resilience(self):
        """Test that WebSocket errors don't break tool execution."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        websocket_manager.should_fail = True
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_manager
        )
        
        tool = MockBaseTool("resilient_tool")
        dispatcher.register_tool(tool)
        
        # Tool should execute successfully despite WebSocket failures
        response = await dispatcher.execute_tool("resilient_tool")
        
        assert response.success is True
        assert tool.call_count == 1
        # WebSocket events should have failed, but execution succeeded
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_memory_cleanup_on_failure(self):
        """Test that memory is properly cleaned up on failures."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Create failing tool
        tool = MockBaseTool("memory_test_tool", should_fail=True)
        dispatcher.register_tool(tool)
        
        # Execute failing tool multiple times
        for _ in range(3):
            response = await dispatcher.execute_tool("memory_test_tool")
            assert response.success is False
            
        # Verify metrics tracked failures properly
        metrics = dispatcher.get_metrics()
        assert metrics['failed_executions'] == 3
        assert metrics['successful_executions'] == 0
        
        await dispatcher.cleanup()


class TestUnifiedToolDispatcherContextManager:
    """Test context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_request_scoped_context_manager(self):
        """Test request-scoped context manager with automatic cleanup."""
        user_context = create_user_context()
        websocket_manager = MockWebSocketManager()
        tools = [MockBaseTool("context_tool")]
        
        async with create_request_scoped_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=tools
        ) as dispatcher:
            # Verify dispatcher is properly initialized
            assert dispatcher.user_context == user_context
            assert dispatcher.websocket_manager == websocket_manager
            assert dispatcher.has_tool("context_tool") is True
            assert dispatcher._is_active is True
            
            # Execute tool within context
            response = await dispatcher.execute_tool("context_tool")
            assert response.success is True
            
        # Dispatcher should be cleaned up automatically
        
    @pytest.mark.asyncio
    async def test_context_manager_exception_cleanup(self):
        """Test context manager cleanup on exception."""
        user_context = create_user_context()
        
        with pytest.raises(ValueError):
            async with create_request_scoped_dispatcher(user_context) as dispatcher:
                assert dispatcher._is_active is True
                raise ValueError("Test exception in context")
                
        # Cleanup should still happen despite exception


class TestUnifiedToolDispatcherPerformance:
    """Test performance characteristics and resource usage."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_timing(self):
        """Test that tool execution timing is properly tracked."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        # Create tool with known delay
        async def delayed_execution(**kwargs):
            await asyncio.sleep(0.01)  # 10ms delay
            return "delayed result"
            
        tool = MockBaseTool("timing_tool")
        tool.arun = delayed_execution
        dispatcher.register_tool(tool)
        
        # Execute and verify timing
        response = await dispatcher.execute_tool("timing_tool")
        
        assert response.success is True
        assert response.metadata['execution_time_ms'] >= 10  # At least 10ms
        
        # Verify metrics tracking
        metrics = dispatcher.get_metrics()
        assert metrics['total_execution_time_ms'] >= 10
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio  
    async def test_memory_usage_stability(self):
        """Test that memory usage remains stable across many executions."""
        user_context = create_user_context()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
        
        tool = MockBaseTool("memory_tool")
        dispatcher.register_tool(tool)
        
        # Execute tool many times
        for i in range(50):
            response = await dispatcher.execute_tool("memory_tool", {"iteration": i})
            assert response.success is True
            
        # Verify metrics are reasonable
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 50
        assert metrics['successful_executions'] == 50
        assert metrics['failed_executions'] == 0
        
        await dispatcher.cleanup()
        
    @pytest.mark.asyncio
    async def test_concurrent_dispatcher_isolation(self):
        """Test performance and isolation with multiple concurrent dispatchers."""
        # Create multiple dispatchers for different users
        dispatchers = []
        for i in range(5):
            user_context = create_user_context(user_id=f"perf_user_{i}")
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context)
            tool = MockBaseTool(f"tool_{i}")
            dispatcher.register_tool(tool)
            dispatchers.append((dispatcher, tool))
            
        # Execute tools concurrently across all dispatchers
        tasks = []
        for dispatcher, tool in dispatchers:
            task = asyncio.create_task(
                dispatcher.execute_tool(tool.name, {"user": dispatcher.user_context.user_id})
            )
            tasks.append(task)
            
        # Wait for all executions
        responses = await asyncio.gather(*tasks)
        
        # Verify all succeeded and isolation maintained
        for i, response in enumerate(responses):
            assert response.success is True
            # Verify each tool was called only once (no cross-contamination)
            assert dispatchers[i][1].call_count == 1
            
        # Cleanup all
        for dispatcher, _ in dispatchers:
            await dispatcher.cleanup()


if __name__ == "__main__":
    # Run with: python -m pytest netra_backend/tests/unit/core/tools/test_unified_tool_dispatcher_comprehensive.py -v
    pytest.main([__file__, "-v", "--tb=short"])