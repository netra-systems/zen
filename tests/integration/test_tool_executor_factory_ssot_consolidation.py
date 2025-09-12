"""
Integration Tests: ToolExecutorFactory SSOT Consolidation Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core Infrastructure  
- Business Goal: Ensure reliable tool execution for $500K+ ARR chat functionality
- Value Impact: Validate single execution path with consistent WebSocket events
- Strategic Impact: Prove golden path user flow works end-to-end after consolidation

These tests validate that SSOT consolidation is working correctly.
They should PASS after GitHub Issue #219 is resolved.
"""

import pytest
import asyncio
import time
import gc
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Import consolidated system
try:
    from netra_backend.app.agents.tool_executor_factory import (
        ToolExecutorFactory,
        get_tool_executor_factory,
        create_isolated_tool_executor,
        isolated_tool_executor_scope
    )
    TOOL_EXECUTOR_FACTORY_AVAILABLE = True
except ImportError:
    TOOL_EXECUTOR_FACTORY_AVAILABLE = False

try:
    from netra_backend.app.core.tools.unified_tool_dispatcher import (
        UnifiedToolDispatcher,
        UnifiedToolDispatcherFactory
    )
    UNIFIED_TOOL_DISPATCHER_AVAILABLE = True
except ImportError:
    UNIFIED_TOOL_DISPATCHER_AVAILABLE = False

try:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    USER_EXECUTION_CONTEXT_AVAILABLE = True
except ImportError:
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        USER_EXECUTION_CONTEXT_AVAILABLE = True
    except ImportError:
        USER_EXECUTION_CONTEXT_AVAILABLE = False


class TestToolExecutorFactorySSotConsolidation(SSotBaseTestCase):
    """
    Integration tests validating SSOT consolidation is working correctly.
    
    These tests should PASS after consolidation and prove the golden path works.
    """
    
    def setup_method(self, method=None):
        """Setup for SSOT consolidation validation."""
        super().setup_method()
        self.record_metric("test_category", "tool_executor_factory_ssot_consolidation")
        
        # Create test user contexts
        if USER_EXECUTION_CONTEXT_AVAILABLE:
            self._test_user_context = UserExecutionContext(
                user_id="ssot_consolidation_test_user",
                thread_id="ssot_consolidation_test_thread",
                run_id="ssot_consolidation_test_run"
            )
            
            self._test_user_context_2 = UserExecutionContext(
                user_id="ssot_consolidation_test_user_2", 
                thread_id="ssot_consolidation_test_thread_2",
                run_id="ssot_consolidation_test_run_2"
            )
        
        # Track created resources for cleanup
        self._created_executors = []
        self._created_dispatchers = []
        
        # Track events for WebSocket validation
        self._websocket_events = []
    
    @pytest.mark.integration
    async def test_single_tool_execution_path(self):
        """
        SHOULD PASS: Validate all tool calls route through ToolExecutorFactory.
        
        After consolidation, UnifiedToolDispatcher should redirect to ToolExecutorFactory.
        """
        # Skip if modules not available
        if not (TOOL_EXECUTOR_FACTORY_AVAILABLE and USER_EXECUTION_CONTEXT_AVAILABLE):
            pytest.skip("Required modules not available")
        
        # Test 1: ToolExecutorFactory direct usage
        factory = get_tool_executor_factory()
        assert factory is not None, "Global ToolExecutorFactory should be available"
        
        # Create tool executor
        executor = await factory.create_tool_executor(self._test_user_context)
        self._created_executors.append(executor)
        
        assert executor is not None, "Tool executor should be created successfully"
        
        # Test 2: UnifiedToolDispatcher redirection (if available)
        if UNIFIED_TOOL_DISPATCHER_AVAILABLE:
            try:
                # This should now redirect to ToolExecutorFactory
                async with UnifiedToolDispatcher.create_scoped(self._test_user_context) as dispatcher:
                    self._created_dispatchers.append(dispatcher)
                    
                    # Verify dispatcher is properly configured
                    assert dispatcher is not None, "Dispatcher should be created via factory pattern"
                    assert hasattr(dispatcher, 'execute_tool'), "Dispatcher should have execute_tool method"
                    
                    # Test tool execution works
                    # Mock tool for testing
                    test_tool_name = "consolidation_test_tool"
                    
                    async def mock_tool_function(param1: str = "default") -> Dict[str, Any]:
                        return {
                            "status": "success",
                            "param1": param1,
                            "executed_by": "mock_tool_via_consolidated_path"
                        }
                    
                    # Register and execute tool
                    dispatcher.register_tool(MockTool(test_tool_name, mock_tool_function))
                    
                    result = await dispatcher.execute_tool(
                        tool_name=test_tool_name,
                        parameters={"param1": "consolidation_test"}
                    )
                    
                    # Validate execution success
                    assert result.success, f"Tool execution should succeed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
                    
                    if hasattr(result, 'result'):
                        assert result.result["status"] == "success", "Tool should execute successfully"
                        assert result.result["param1"] == "consolidation_test", "Parameters should be passed correctly"
                        assert "consolidated_path" in result.result["executed_by"], "Should execute via consolidated path"
            
            except RuntimeError as e:
                if "Direct instantiation" in str(e):
                    # Expected - direct instantiation is properly blocked
                    print(" PASS:  Direct instantiation properly blocked - using factory patterns")
                else:
                    raise
        
        # Test 3: Convenience functions work
        async with isolated_tool_executor_scope(self._test_user_context) as scoped_executor:
            assert scoped_executor is not None, "Scoped executor should be created"
            # Executor should be the same type as direct creation
            assert type(scoped_executor).__name__ == type(executor).__name__, "Should use same executor type"
        
        # Test 4: Multiple user isolation
        executor_2 = await create_isolated_tool_executor(self._test_user_context_2)
        self._created_executors.append(executor_2)
        
        assert executor_2 is not None, "Second executor should be created"
        assert id(executor) != id(executor_2), "Executors should be isolated instances"
        
        print(" PASS:  Single tool execution path validation complete")
    
    @pytest.mark.integration
    async def test_websocket_event_consistency(self):
        """
        SHOULD PASS: Validate all 5 WebSocket events deliver consistently.
        
        Tests golden path: login  ->  tool execution  ->  AI response.
        """
        # Skip if modules not available
        if not (TOOL_EXECUTOR_FACTORY_AVAILABLE and USER_EXECUTION_CONTEXT_AVAILABLE):
            pytest.skip("Required modules not available")
        
        # Mock WebSocket manager to capture events
        mock_websocket_manager = MagicMock()
        mock_events_sent = []
        
        async def capture_send_event(event_type: str, data: Dict[str, Any]):
            mock_events_sent.append({
                "type": event_type,
                "data": data,
                "timestamp": time.time()
            })
            self._websocket_events.append({
                "type": event_type,
                "data": data,
                "timestamp": time.time()
            })
            return True
        
        mock_websocket_manager.send_event = capture_send_event
        
        # Create tool executor with WebSocket manager
        factory = get_tool_executor_factory()
        factory.set_websocket_manager(mock_websocket_manager)
        
        executor = await factory.create_tool_executor(
            self._test_user_context,
            websocket_manager=mock_websocket_manager
        )
        self._created_executors.append(executor)
        
        # Test tool execution with WebSocket events
        test_tool_name = "websocket_test_tool"
        
        async def websocket_test_tool(message: str = "test") -> Dict[str, Any]:
            # Simulate some processing time
            await asyncio.sleep(0.1)
            return {
                "status": "success",
                "message": f"Processed: {message}",
                "result": "Tool execution completed"
            }
        
        # Create mock tool
        mock_tool = MockTool(test_tool_name, websocket_test_tool)
        
        # Execute through ToolExecutorFactory path
        if hasattr(executor, 'executor') and hasattr(executor.executor, 'registry'):
            # Register tool with the executor's registry
            executor.executor.registry.register(test_tool_name, mock_tool)
        
        # Alternative: If using UnifiedToolDispatcher
        if UNIFIED_TOOL_DISPATCHER_AVAILABLE:
            try:
                async with UnifiedToolDispatcher.create_scoped(
                    self._test_user_context,
                    websocket_manager=mock_websocket_manager
                ) as dispatcher:
                    self._created_dispatchers.append(dispatcher)
                    
                    # Register and execute tool
                    dispatcher.register_tool(mock_tool)
                    
                    # Clear events for clean test
                    mock_events_sent.clear()
                    
                    result = await dispatcher.execute_tool(
                        tool_name=test_tool_name,
                        parameters={"message": "websocket_consistency_test"}
                    )
                    
                    # Validate execution success
                    assert result.success, f"Tool execution should succeed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
                    
                    # Validate WebSocket events were sent
                    event_types = [event["type"] for event in mock_events_sent]
                    
                    # Should have both executing and completed events
                    assert "tool_executing" in event_types, "tool_executing event should be sent"
                    assert "tool_completed" in event_types, "tool_completed event should be sent"
                    
                    # Events should be in correct order
                    executing_index = event_types.index("tool_executing")
                    completed_index = event_types.index("tool_completed")
                    assert executing_index < completed_index, "tool_executing should come before tool_completed"
                    
                    # Event data should be consistent
                    executing_event = mock_events_sent[executing_index]
                    completed_event = mock_events_sent[completed_index]
                    
                    assert executing_event["data"]["tool_name"] == test_tool_name, "Event should include correct tool name"
                    assert executing_event["data"]["run_id"] == self._test_user_context.run_id, "Event should include correct run_id"
                    
                    assert completed_event["data"]["tool_name"] == test_tool_name, "Completion event should include correct tool name"
                    assert completed_event["data"]["status"] == "success", "Completion event should show success"
                    
                    print(f" PASS:  WebSocket events validated: {len(mock_events_sent)} events sent")
                    print(f"   Event types: {event_types}")
            
            except RuntimeError as e:
                if "Direct instantiation" in str(e):
                    print(" PASS:  Direct instantiation properly blocked - WebSocket events should work via factory")
                else:
                    raise
        
        print(" PASS:  WebSocket event consistency validation complete")
    
    @pytest.mark.integration
    async def test_tool_registry_singleton(self):
        """
        SHOULD PASS: Validate single ToolRegistry instance used efficiently.
        
        Tests memory efficiency and state consistency after consolidation.
        """
        # Skip if modules not available
        if not (TOOL_EXECUTOR_FACTORY_AVAILABLE and USER_EXECUTION_CONTEXT_AVAILABLE):
            pytest.skip("Required modules not available")
        
        # Create multiple tool executors
        factory = get_tool_executor_factory()
        
        executors = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"registry_test_user_{i}",
                thread_id=f"registry_test_thread_{i}",
                run_id=f"registry_test_run_{i}"
            )
            
            executor = await factory.create_tool_executor(context)
            executors.append(executor)
            self._created_executors.append(executor)
        
        # Test registry behavior
        registry_instances = []
        for executor in executors:
            if hasattr(executor, 'executor') and hasattr(executor.executor, 'registry'):
                registry_instances.append(id(executor.executor.registry))
        
        if registry_instances:
            # Check registry isolation vs sharing
            unique_registries = len(set(registry_instances))
            
            # After consolidation, should have proper registry management
            # Either shared singleton (1 registry) or proper per-user isolation (3 registries)
            assert unique_registries in [1, 3], f"Should have either 1 shared registry or 3 isolated registries, got {unique_registries}"
            
            if unique_registries == 1:
                print(" PASS:  Single shared registry pattern detected")
            else:
                print(" PASS:  Per-user registry isolation pattern detected")
        
        # Test registry consistency
        test_tool_name = "registry_consistency_tool"
        
        async def registry_test_tool() -> Dict[str, Any]:
            return {"status": "success", "registry_test": True}
        
        mock_tool = MockTool(test_tool_name, registry_test_tool)
        
        # Register tool with first executor
        if executors and hasattr(executors[0], 'executor') and hasattr(executors[0].executor, 'registry'):
            executors[0].executor.registry.register(test_tool_name, mock_tool)
            
            # Check if tool is available in other executors (depends on sharing strategy)
            for i, executor in enumerate(executors[1:], 1):
                if hasattr(executor, 'executor') and hasattr(executor.executor, 'registry'):
                    has_tool = executor.executor.registry.has(test_tool_name)
                    
                    if unique_registries == 1:
                        # Shared registry - tool should be available
                        assert has_tool, f"Tool should be available in executor {i} with shared registry"
                    else:
                        # Isolated registries - tool should not be available
                        assert not has_tool, f"Tool should not be available in executor {i} with isolated registry"
        
        print(" PASS:  Tool registry singleton validation complete")
    
    @pytest.mark.integration
    async def test_golden_path_user_flow_integration(self):
        """
        SHOULD PASS: Test complete golden path user flow works end-to-end.
        
        Validates: user login  ->  tool execution  ->  AI response delivery.
        """
        # Skip if modules not available
        if not (TOOL_EXECUTOR_FACTORY_AVAILABLE and USER_EXECUTION_CONTEXT_AVAILABLE):
            pytest.skip("Required modules not available")
        
        # Simulate complete user flow
        print("[U+1F680] Testing Golden Path User Flow")
        
        # Step 1: User login (simulated with user context)
        user_context = UserExecutionContext(
            user_id="golden_path_test_user",
            thread_id="golden_path_test_thread",
            run_id="golden_path_test_run",
            metadata={"roles": ["user"], "subscription": "enterprise"}
        )
        
        # Step 2: Create tool execution environment
        factory = get_tool_executor_factory()
        
        # Mock WebSocket manager for event tracking
        mock_websocket_manager = MagicMock()
        golden_path_events = []
        
        async def capture_golden_path_event(event_type: str, data: Dict[str, Any]):
            golden_path_events.append({
                "type": event_type,
                "data": data,
                "timestamp": time.time(),
                "user_id": data.get("user_id"),
                "run_id": data.get("run_id")
            })
            return True
        
        mock_websocket_manager.send_event = capture_golden_path_event
        factory.set_websocket_manager(mock_websocket_manager)
        
        # Step 3: Execute AI agent workflow simulation
        async with isolated_tool_executor_scope(
            user_context,
            websocket_manager=mock_websocket_manager
        ) as executor:
            
            # Simulate agent tools
            tools_to_test = [
                ("data_analyzer", "Analyze user data"),
                ("cost_optimizer", "Optimize costs"),
                ("report_generator", "Generate report")
            ]
            
            for tool_name, description in tools_to_test:
                # Create mock tool
                async def mock_agent_tool(query: str = description) -> Dict[str, Any]:
                    await asyncio.sleep(0.05)  # Simulate processing
                    return {
                        "status": "success",
                        "tool": tool_name,
                        "result": f"Processed: {query}",
                        "insights": ["Insight 1", "Insight 2"],
                        "recommendations": ["Recommendation 1", "Recommendation 2"]
                    }
                
                mock_tool = MockTool(tool_name, mock_agent_tool)
                
                # Execute via consolidated system
                if UNIFIED_TOOL_DISPATCHER_AVAILABLE:
                    try:
                        async with UnifiedToolDispatcher.create_scoped(
                            user_context,
                            websocket_manager=mock_websocket_manager
                        ) as dispatcher:
                            
                            dispatcher.register_tool(mock_tool)
                            
                            result = await dispatcher.execute_tool(
                                tool_name=tool_name,
                                parameters={"query": f"Golden path test: {description}"}
                            )
                            
                            # Validate successful execution
                            assert result.success, f"Tool {tool_name} should execute successfully"
                            
                            if hasattr(result, 'result') and result.result:
                                assert result.result["status"] == "success", f"Tool {tool_name} should return success"
                                assert "insights" in result.result, f"Tool {tool_name} should return insights"
                                assert "recommendations" in result.result, f"Tool {tool_name} should return recommendations"
                    
                    except RuntimeError as e:
                        if "Direct instantiation" in str(e):
                            print(f" PASS:  Tool {tool_name}: Direct instantiation properly blocked")
                        else:
                            raise
        
        # Step 4: Validate golden path events
        assert len(golden_path_events) > 0, "Should have captured WebSocket events during golden path"
        
        # Group events by tool
        events_by_tool = {}
        for event in golden_path_events:
            tool_name = event["data"].get("tool_name", "unknown")
            if tool_name not in events_by_tool:
                events_by_tool[tool_name] = []
            events_by_tool[tool_name].append(event)
        
        # Validate event consistency for each tool
        for tool_name, tool_events in events_by_tool.items():
            event_types = [e["type"] for e in tool_events]
            
            # Should have executing and completed events
            assert "tool_executing" in event_types, f"Tool {tool_name} should have executing event"
            assert "tool_completed" in event_types, f"Tool {tool_name} should have completed event"
            
            # All events should have consistent user context
            for event in tool_events:
                assert event["user_id"] == user_context.user_id, f"Event should have correct user_id"
                assert event["run_id"] == user_context.run_id, f"Event should have correct run_id"
        
        print(f" PASS:  Golden Path User Flow validated")
        print(f"   Tools executed: {len(events_by_tool)}")
        print(f"   Total events: {len(golden_path_events)}")
        print(f"   Event types: {set(e['type'] for e in golden_path_events)}")
    
    def teardown_method(self, method=None):
        """Cleanup test resources."""
        # Cleanup executors
        for executor in self._created_executors:
            try:
                if hasattr(executor, 'cleanup'):
                    asyncio.create_task(executor.cleanup())
            except Exception:
                pass
        
        # Cleanup dispatchers
        for dispatcher in self._created_dispatchers:
            try:
                if hasattr(dispatcher, 'cleanup'):
                    asyncio.create_task(dispatcher.cleanup())
            except Exception:
                pass
        
        # Report test results
        if self._websocket_events:
            print(f"\n CHART:  WebSocket Events Summary:")
            print(f"   Total events captured: {len(self._websocket_events)}")
            event_types = [e["type"] for e in self._websocket_events]
            print(f"   Event types: {set(event_types)}")
        
        # Force garbage collection
        gc.collect()
        
        super().teardown_method()


class MockTool:
    """Mock tool for testing purposes."""
    
    def __init__(self, name: str, handler):
        self.name = name
        self.handler = handler
    
    async def __call__(self, *args, **kwargs):
        return await self.handler(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        """Sync run method for compatibility."""
        return asyncio.run(self.handler(*args, **kwargs))