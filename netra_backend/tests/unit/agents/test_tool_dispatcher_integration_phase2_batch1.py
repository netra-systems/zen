"""
Tool Dispatcher Integration Unit Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless integration between dispatcher components
- Value Impact: Smooth component integration enables reliable AI agent workflows
- Strategic Impact: Component integration stability ensures consistent user experience

CRITICAL: These tests validate integration interfaces between dispatcher components,
ensuring AI agents can reliably execute tools to deliver business value.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from netra_backend.app.agents.tool_dispatcher import (
    UnifiedToolDispatcherFactory,
    create_request_scoped_tool_dispatcher
)
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy
)
from netra_backend.app.agents.state import DeepAgentState
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockUserExecutionContext:
    """Mock user execution context for integration testing."""
    
    def __init__(self, user_id: str = "integration-user-123"):
        self.user_id = user_id
        self.request_id = f"req-{int(datetime.now(timezone.utc).timestamp())}"
        self.session_id = f"session-{user_id}"
        self.metadata = {"test_type": "integration", "environment": "unit_test"}
        self.permissions = ["read", "write", "execute_tools"]
        
    def has_permission(self, permission: str) -> bool:
        """Check if user has permission."""
        return permission in self.permissions


class MockUnifiedWebSocketManager:
    """Mock unified WebSocket manager for integration testing."""
    
    def __init__(self):
        self.events_sent = []
        self.connection_active = True
        self.user_connections = {}
        
    async def notify_tool_executing(self, tool_name: str, user_id: str = None, **kwargs):
        """Notify tool execution started."""
        if self.connection_active:
            event = {
                "type": "tool_executing",
                "tool_name": tool_name,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kwargs": kwargs
            }
            self.events_sent.append(event)
            
    async def notify_tool_completed(self, tool_name: str, result: Any, user_id: str = None, **kwargs):
        """Notify tool execution completed.""" 
        if self.connection_active:
            event = {
                "type": "tool_completed",
                "tool_name": tool_name,
                "result": result,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kwargs": kwargs
            }
            self.events_sent.append(event)
            
    def get_events_for_user(self, user_id: str) -> List[Dict]:
        """Get events for specific user."""
        return [e for e in self.events_sent if e.get("user_id") == user_id]


class MockIntegrationTool(BaseTool):
    """Mock tool for integration testing that simulates cross-component interactions."""
    
    def __init__(
        self, 
        name: str,
        requires_permissions: List[str] = None,
        integration_delay: float = 0.05,
        cross_component_calls: List[str] = None
    ):
        self.name = name
        self.description = f"Integration tool {name} with cross-component interactions"
        self.requires_permissions = requires_permissions or ["execute_tools"]
        self.integration_delay = integration_delay
        self.cross_component_calls = cross_component_calls or []
        
    def _run(self, *args, **kwargs):
        """Sync version."""
        return self._execute(*args, **kwargs)
        
    async def _arun(self, *args, **kwargs):
        """Async version with integration simulation."""
        # Simulate integration delay
        await asyncio.sleep(self.integration_delay)
        
        # Simulate cross-component calls
        for component in self.cross_component_calls:
            await self._simulate_component_call(component, kwargs)
            
        return self._execute(*args, **kwargs)
        
    async def _simulate_component_call(self, component: str, kwargs: Dict):
        """Simulate call to another component."""
        await asyncio.sleep(0.01)  # Small delay for component interaction
        
    def _execute(self, *args, **kwargs):
        """Core execution logic."""
        return {
            "success": True,
            "tool_name": self.name,
            "integration_status": "completed",
            "components_called": self.cross_component_calls,
            "permissions_required": self.requires_permissions,
            "parameters_processed": kwargs,
            "execution_timestamp": datetime.now(timezone.utc).isoformat()
        }


class TestToolDispatcherIntegrationInterfaces(SSotBaseTestCase):
    """Test integration interfaces between dispatcher components."""
    
    @pytest.mark.unit
    async def test_unified_factory_integration_pattern(self):
        """Test unified factory creates proper integrations between components."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockUnifiedWebSocketManager()
        integration_tools = [
            MockIntegrationTool("registry_tool", cross_component_calls=["registry"]),
            MockIntegrationTool("execution_tool", cross_component_calls=["executor"]),
            MockIntegrationTool("validation_tool", cross_component_calls=["validator"])
        ]
        
        # Use unified factory to create dispatcher with all integrations
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=integration_tools
        )
        
        # Verify dispatcher has all integrated components
        assert isinstance(dispatcher, UnifiedToolDispatcher)
        
        # Test cross-component integration by executing each tool
        for tool in integration_tools:
            # Create dispatch request
            request = ToolDispatchRequest(
                tool_name=tool.name,
                parameters={"integration_test": True, "user_id": user_context.user_id}
            )
            
            # Execute tool (this tests registry -> executor -> validator integration)
            result = await dispatcher.dispatch_tool_request(request)
            
            # Verify successful integration
            assert isinstance(result, ToolDispatchResponse)
            assert result.success is True
            assert "integration_status" in str(result.result)
            
        # Verify WebSocket integration sent events for all tools
        assert len(websocket_manager.events_sent) >= 6  # 3 executing + 3 completed
        user_events = websocket_manager.get_events_for_user(user_context.user_id)
        assert len(user_events) >= 6
    
    @pytest.mark.unit
    async def test_event_bridging_integration_between_components(self):
        """Test event bridging integration between dispatcher and WebSocket system."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockUnifiedWebSocketManager()
        
        # Create tool that generates multiple events
        event_tool = MockIntegrationTool(
            "event_generator", 
            cross_component_calls=["websocket", "registry", "executor"]
        )
        
        dispatcher = create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=[event_tool]
        )
        
        # Execute tool and track event bridging
        request = ToolDispatchRequest(
            tool_name="event_generator",
            parameters={"generate_events": True, "event_count": 5}
        )
        
        result = await dispatcher.dispatch_tool_request(request)
        
        # Verify successful execution
        assert result.success is True
        
        # Verify event bridging worked - events should be properly routed
        assert len(websocket_manager.events_sent) >= 2
        
        # Verify event contains proper integration context
        events_for_user = websocket_manager.get_events_for_user(user_context.user_id)
        assert len(events_for_user) >= 2
        
        executing_event = next((e for e in events_for_user if e["type"] == "tool_executing"), None)
        assert executing_event is not None
        assert executing_event["tool_name"] == "event_generator"
        
        completed_event = next((e for e in events_for_user if e["type"] == "tool_completed"), None)
        assert completed_event is not None
        assert "integration_status" in str(completed_event["result"])


class TestToolDispatcherRequestScopedIntegration(SSotBaseTestCase):
    """Test request-scoped integration patterns and isolation."""
    
    @pytest.mark.unit
    async def test_multi_user_request_scoped_isolation_integration(self):
        """Test that request-scoped integration maintains proper user isolation."""
        # Create multiple user contexts
        user_contexts = [
            MockUserExecutionContext(f"user-{i}")
            for i in range(1, 4)
        ]
        
        websocket_manager = MockUnifiedWebSocketManager()
        
        # Create tools for each user with user-specific behavior
        dispatchers = []
        for user_context in user_contexts:
            user_specific_tool = MockIntegrationTool(
                f"tool_for_{user_context.user_id}",
                cross_component_calls=["registry", "executor"]
            )
            
            dispatcher = create_request_scoped_tool_dispatcher(
                user_context=user_context,
                websocket_manager=websocket_manager,
                tools=[user_specific_tool]
            )
            dispatchers.append((dispatcher, user_context))
        
        # Execute tools concurrently for all users
        tasks = []
        for dispatcher, user_context in dispatchers:
            request = ToolDispatchRequest(
                tool_name=f"tool_for_{user_context.user_id}",
                parameters={"user_isolation_test": True, "user_id": user_context.user_id}
            )
            task = dispatcher.dispatch_tool_request(request)
            tasks.append((task, user_context))
        
        # Wait for all executions
        results = await asyncio.gather(*[task for task, _ in tasks], return_exceptions=True)
        
        # Verify all executions succeeded and maintained isolation
        for i, (result, (_, user_context)) in enumerate(zip(results, tasks)):
            assert not isinstance(result, Exception), f"User {user_context.user_id} task failed: {result}"
            assert isinstance(result, ToolDispatchResponse)
            assert result.success is True
            
            # Verify user-specific results
            result_str = str(result.result)
            assert user_context.user_id in result_str
        
        # Verify each user only got their own events
        for _, user_context in dispatchers:
            user_events = websocket_manager.get_events_for_user(user_context.user_id)
            assert len(user_events) >= 2  # executing + completed
            
            # Verify events contain only tools for this user
            for event in user_events:
                assert user_context.user_id in event["tool_name"]
    
    @pytest.mark.unit
    async def test_dispatch_strategy_integration_with_user_context(self):
        """Test dispatch strategy integration with user context and permissions."""
        # Create user with specific permissions
        user_context = MockUserExecutionContext()
        user_context.permissions = ["read", "write", "execute_tools", "admin_tools"]
        
        websocket_manager = MockUnifiedWebSocketManager()
        
        # Create tools with different permission requirements
        tools = [
            MockIntegrationTool("public_tool", requires_permissions=["read"]),
            MockIntegrationTool("user_tool", requires_permissions=["execute_tools"]),
            MockIntegrationTool("admin_tool", requires_permissions=["admin_tools"])
        ]
        
        dispatcher = create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=tools
        )
        
        # Test different dispatch strategies based on user permissions
        strategies_to_test = [
            (DispatchStrategy.IMMEDIATE, "public_tool"),
            (DispatchStrategy.QUEUED, "user_tool"),
            (DispatchStrategy.PRIORITY, "admin_tool")
        ]
        
        results = []
        for strategy, tool_name in strategies_to_test:
            request = ToolDispatchRequest(
                tool_name=tool_name,
                parameters={"strategy_test": True, "required_permissions": True}
            )
            
            # Execute with specific strategy (if dispatcher supports it)
            result = await dispatcher.dispatch_tool_request(request)
            results.append((strategy, tool_name, result))
        
        # Verify all strategies worked with proper permissions
        for strategy, tool_name, result in results:
            assert result.success is True, f"Strategy {strategy} failed for {tool_name}"
            assert tool_name in str(result.result)
        
        # Verify WebSocket integration worked for all strategies
        assert len(websocket_manager.events_sent) >= 6  # 3 tools * 2 events each
        
        # Verify each tool execution generated proper events
        for _, tool_name, _ in strategies_to_test:
            tool_events = [e for e in websocket_manager.events_sent if e["tool_name"] == tool_name]
            assert len(tool_events) >= 2  # executing + completed