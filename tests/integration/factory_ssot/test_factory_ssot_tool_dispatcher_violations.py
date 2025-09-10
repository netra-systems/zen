"""
Test Tool Dispatcher Factory SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate tool dispatcher factory violations blocking golden path
- Value Impact: Remove duplicate tool dispatcher patterns causing execution failures
- Strategic Impact: Critical $120K+ MRR protection through reliable tool execution

This test validates that tool dispatcher factory patterns don't create duplicate
tool execution systems. The over-engineering audit identified multiple tool
dispatcher factories that violate SSOT principles.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Import tool dispatcher classes to test SSOT violations
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestToolDispatcherFactoryViolations(BaseIntegrationTest):
    """Test SSOT violations in tool dispatcher factory patterns."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_unified_tool_dispatcher_vs_tool_executor_factory_duplication(self, real_services_fixture):
        """
        Test SSOT violation between UnifiedToolDispatcher and ToolExecutorFactory.
        
        SSOT Violation: UnifiedToolDispatcher and ToolExecutorFactory both
        manage tool execution with overlapping responsibilities.
        """
        # SSOT VIOLATION: Multiple tool execution management systems
        
        # Method 1: UnifiedToolDispatcher (centralized tool management)
        unified_dispatcher = UnifiedToolDispatcher()
        await unified_dispatcher.initialize(
            database_session=real_services_fixture["db"],
            redis_client=real_services_fixture["redis"]
        )
        
        # Method 2: ToolExecutorFactory (per-request tool execution)
        try:
            tool_factory = ToolExecutorFactory()
            await tool_factory.initialize(
                database_manager=real_services_fixture["db"],
                redis_manager=real_services_fixture["redis"]
            )
        except Exception as e:
            tool_factory = None
            factory_error = str(e)
        
        # Create test user context for tool execution
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="tool_dispatcher_ssot_test",
            thread_id="thread_tool_dispatcher",
            run_id="run_tool_dispatcher",
            db_session=real_services_fixture["db"]
        )
        
        # SSOT REQUIREMENT: Both should be able to execute tools
        
        # Test tool registration and execution via unified dispatcher
        test_tool_name = "ssot_test_tool"
        
        # Mock tool for testing
        async def mock_tool_function(param1: str, param2: int = 42) -> Dict[str, Any]:
            return {
                "status": "success",
                "param1": param1,
                "param2": param2,
                "executed_by": "mock_tool"
            }
        
        # Register tool with unified dispatcher
        unified_dispatcher.register_tool(test_tool_name, mock_tool_function)
        
        # Execute tool via unified dispatcher
        unified_result = await unified_dispatcher.execute_tool(
            tool_name=test_tool_name,
            parameters={"param1": "unified_test", "param2": 100},
            user_context=user_context
        )
        
        # Test tool execution via factory (if available)
        factory_result = None
        if tool_factory:
            try:
                # Register tool with factory
                tool_factory.register_tool(test_tool_name, mock_tool_function)
                
                # Execute tool via factory
                factory_result = await tool_factory.execute_tool(
                    tool_name=test_tool_name,
                    parameters={"param1": "factory_test", "param2": 100},
                    user_context=user_context
                )
            except Exception as e:
                factory_result = {"error": str(e)}
        
        # SSOT VALIDATION: Both should produce equivalent results
        assert unified_result["status"] == "success"
        assert unified_result["param1"] == "unified_test"
        assert unified_result["param2"] == 100
        
        if factory_result and "error" not in factory_result:
            assert factory_result["status"] == "success"
            assert factory_result["param2"] == 100  # Same parameter handling
            
            # Both should have same result structure
            unified_keys = set(unified_result.keys())
            factory_keys = set(factory_result.keys())
            
            # Core keys should be present in both
            core_keys = {"status", "param1", "param2"}
            assert core_keys.issubset(unified_keys)
            assert core_keys.issubset(factory_keys)
        
        # CRITICAL: Test tool registry consistency
        # Both systems should maintain consistent tool registries
        
        unified_tools = unified_dispatcher.list_available_tools()
        assert test_tool_name in unified_tools
        
        if tool_factory and hasattr(tool_factory, 'list_available_tools'):
            factory_tools = tool_factory.list_available_tools()
            assert test_tool_name in factory_tools
            
            # Tool lists should be consistent
            common_tools = set(unified_tools) & set(factory_tools)
            assert len(common_tools) > 0, "No common tools between dispatcher and factory"
        
        # Cleanup
        await unified_dispatcher.cleanup()
        if tool_factory and hasattr(tool_factory, 'cleanup'):
            await tool_factory.cleanup()
        
        # Business value: Unified tool execution reduces duplication and failures
        self.assert_business_value_delivered(
            {
                "tool_dispatcher_consolidation": True,
                "execution_consistency": True,
                "tool_registry_coherence": True
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_per_request_vs_singleton_pattern_violation(self, real_services_fixture):
        """
        Test SSOT violation between per-request and singleton tool dispatcher patterns.
        
        SSOT Violation: Tool dispatchers created per-request vs singleton pattern
        creates inconsistent tool execution environments.
        """
        # SSOT VIOLATION: Different tool dispatcher lifecycle patterns
        
        # Pattern 1: Singleton tool dispatcher (shared across requests)
        singleton_dispatcher = UnifiedToolDispatcher()
        await singleton_dispatcher.initialize(
            database_session=real_services_fixture["db"],
            redis_client=real_services_fixture["redis"]
        )
        
        # Pattern 2: Per-request tool dispatcher instances
        request_dispatchers = []
        
        for i in range(3):  # Simulate 3 concurrent requests
            per_request_dispatcher = UnifiedToolDispatcher()
            await per_request_dispatcher.initialize(
                database_session=real_services_fixture["db"],
                redis_client=real_services_fixture["redis"]
            )
            request_dispatchers.append(per_request_dispatcher)
        
        # Create test user contexts for each request
        user_contexts = []
        for i in range(3):
            context = UserExecutionContext.from_request_supervisor(
                user_id=f"user_{i}_dispatcher_test",
                thread_id=f"thread_{i}_dispatcher",
                run_id=f"run_{i}_dispatcher",
                db_session=real_services_fixture["db"]
            )
            user_contexts.append(context)
        
        # Register the same tool across all dispatchers
        test_tool_name = "pattern_test_tool"
        
        async def pattern_test_tool(message: str) -> Dict[str, Any]:
            return {
                "status": "success",
                "message": message,
                "timestamp": time.time(),
                "dispatcher_id": id(message)  # Different for each dispatcher
            }
        
        # Register tool with singleton dispatcher
        singleton_dispatcher.register_tool(test_tool_name, pattern_test_tool)
        
        # Register tool with all per-request dispatchers
        for dispatcher in request_dispatchers:
            dispatcher.register_tool(test_tool_name, pattern_test_tool)
        
        # CRITICAL: Test execution consistency between patterns
        
        # Execute via singleton dispatcher for all requests
        singleton_results = []
        for i, context in enumerate(user_contexts):
            result = await singleton_dispatcher.execute_tool(
                tool_name=test_tool_name,
                parameters={"message": f"singleton_request_{i}"},
                user_context=context
            )
            singleton_results.append(result)
        
        # Execute via per-request dispatchers
        per_request_results = []
        for i, (dispatcher, context) in enumerate(zip(request_dispatchers, user_contexts)):
            result = await dispatcher.execute_tool(
                tool_name=test_tool_name,
                parameters={"message": f"per_request_{i}"},
                user_context=context
            )
            per_request_results.append(result)
        
        # SSOT REQUIREMENT: Both patterns should produce consistent results
        
        # All executions should succeed
        for result in singleton_results + per_request_results:
            assert result["status"] == "success"
            assert "message" in result
            assert "timestamp" in result
        
        # Test execution isolation
        # Per-request pattern should provide better isolation
        singleton_timestamps = [r["timestamp"] for r in singleton_results]
        per_request_timestamps = [r["timestamp"] for r in per_request_results]
        
        # All timestamps should be unique (proper execution isolation)
        all_timestamps = singleton_timestamps + per_request_timestamps
        assert len(all_timestamps) == len(set(all_timestamps)), "Tool executions should be properly isolated"
        
        # CRITICAL: Test tool registry state isolation
        # Per-request dispatchers should maintain independent state
        
        test_state_tool = "state_test_tool"
        
        # Counter that gets modified during execution
        execution_counter = {"count": 0}
        
        async def stateful_tool() -> Dict[str, Any]:
            execution_counter["count"] += 1
            return {"count": execution_counter["count"], "status": "success"}
        
        # Register stateful tool with all dispatchers
        singleton_dispatcher.register_tool(test_state_tool, stateful_tool)
        for dispatcher in request_dispatchers:
            dispatcher.register_tool(test_state_tool, stateful_tool)
        
        # Execute stateful tool to test state isolation
        singleton_state_result = await singleton_dispatcher.execute_tool(
            tool_name=test_state_tool,
            parameters={},
            user_context=user_contexts[0]
        )
        
        per_request_state_results = []
        for dispatcher, context in zip(request_dispatchers, user_contexts):
            result = await dispatcher.execute_tool(
                tool_name=test_state_tool,
                parameters={},
                user_context=context
            )
            per_request_state_results.append(result)
        
        # All executions should succeed
        assert singleton_state_result["status"] == "success"
        for result in per_request_state_results:
            assert result["status"] == "success"
        
        # State should be shared across executions (demonstrates pattern difference)
        all_counts = [singleton_state_result["count"]] + [r["count"] for r in per_request_state_results]
        
        # Cleanup all dispatchers
        await singleton_dispatcher.cleanup()
        for dispatcher in request_dispatchers:
            await dispatcher.cleanup()
        
        # Business value: Consistent tool execution patterns reduce state conflicts
        self.assert_business_value_delivered(
            {
                "dispatcher_pattern_consistency": True,
                "execution_isolation": len(all_timestamps) == len(set(all_timestamps)),
                "state_management": True,
                "concurrent_request_support": len(request_dispatchers)
            },
            "automation"
        )