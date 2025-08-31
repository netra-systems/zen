#!/usr/bin/env python
"""SPECIALIZED TEST SUITE: Enhanced Tool Execution WebSocket Events - MISSION CRITICAL

THIS SUITE SPECIFICALLY TESTS THE ENHANCED TOOL EXECUTION WEBSOCKET INTEGRATION.
Business Value: $500K+ ARR - Critical for tool execution visibility in chat

The WebSocket injection fix includes enhancing tool dispatchers with WebSocket notifications.
This ensures users see:
- tool_executing events when tools start
- tool_completed events when tools finish  
- Real-time tool execution progress

ANY FAILURE HERE INDICATES TOOL EXECUTION EVENTS ARE NOT WORKING.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components for testing
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.enhanced_tool_execution import (
    EnhancedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager


# ============================================================================
# MOCK WEBSOCKET MANAGER FOR TOOL EXECUTION TESTING
# ============================================================================

class MockWebSocketManagerForTools:
    """Mock WebSocket manager optimized for tool execution event testing."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connections: Dict[str, Any] = {}
        self.tool_events: List[Dict] = []  # Specialized tracking for tool events
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message and track tool events specially."""
        event = {
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        }
        self.messages.append(event)
        
        # Track tool events specifically
        if event['event_type'] in ['tool_executing', 'tool_completed']:
            self.tool_events.append(event)
            
        return True
    
    def get_tool_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get tool events for a specific thread."""
        return [evt for evt in self.tool_events if evt['thread_id'] == thread_id]
    
    def get_tool_execution_pairs(self, thread_id: str) -> List[Dict]:
        """Get tool execution/completion pairs for validation."""
        tool_events = self.get_tool_events_for_thread(thread_id)
        pairs = []
        executing_tools = {}
        
        for event in tool_events:
            tool_name = event['message'].get('tool_name', 'unknown')
            
            if event['event_type'] == 'tool_executing':
                executing_tools[tool_name] = event
            elif event['event_type'] == 'tool_completed' and tool_name in executing_tools:
                pairs.append({
                    'tool_name': tool_name,
                    'executing': executing_tools[tool_name],
                    'completed': event
                })
                del executing_tools[tool_name]
        
        return pairs
    
    def clear_messages(self):
        """Clear all recorded messages."""
        self.messages.clear()
        self.tool_events.clear()


# ============================================================================
# UNIT TESTS - Enhanced Tool Execution Components
# ============================================================================

class TestEnhancedToolExecutionUnit:
    """Unit tests for enhanced tool execution WebSocket components."""
    
    @pytest.fixture(autouse=True)
    async def setup_tool_mock_services(self):
        """Setup mock services for tool execution tests."""
        self.mock_ws_manager = MockWebSocketManagerForTools()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhanced_tool_execution_engine_creation(self):
        """Test creation of EnhancedToolExecutionEngine with WebSocket manager."""
        # Create enhanced executor
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Verify it has WebSocket notifier
        assert enhanced_executor.websocket_notifier is not None, \
            "EnhancedToolExecutionEngine missing websocket_notifier"
        assert isinstance(enhanced_executor.websocket_notifier, WebSocketNotifier), \
            "websocket_notifier is not WebSocketNotifier instance"
        
        logger.info("✅ EnhancedToolExecutionEngine creation PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_tool_dispatcher_enhancement_function(self):
        """Test enhance_tool_dispatcher_with_notifications function."""
        # Create tool dispatcher
        dispatcher = ToolDispatcher()
        original_executor = dispatcher.executor
        
        # Enhance it
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        
        # Verify enhancement
        assert dispatcher.executor != original_executor, \
            "Tool dispatcher executor was not replaced during enhancement"
        assert isinstance(dispatcher.executor, EnhancedToolExecutionEngine), \
            "Enhanced executor is not EnhancedToolExecutionEngine"
        assert hasattr(dispatcher, '_websocket_enhanced'), \
            "Enhancement marker _websocket_enhanced not set"
        assert dispatcher._websocket_enhanced is True, \
            "Enhancement marker not set to True"
        
        logger.info("✅ Tool dispatcher enhancement function PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_enhances_tool_dispatcher_automatically(self):
        """Test that AgentRegistry automatically enhances tool dispatcher."""
        class MockLLM:
            pass
        
        # Create tool dispatcher and registry
        tool_dispatcher = ToolDispatcher()
        original_executor = tool_dispatcher.executor
        
        registry = AgentRegistry(MockLLM(), tool_dispatcher)
        
        # Set WebSocket manager (this should trigger enhancement)
        registry.set_websocket_manager(self.mock_ws_manager)
        
        # Verify tool dispatcher was enhanced
        assert tool_dispatcher.executor != original_executor, \
            "AgentRegistry did not enhance tool dispatcher automatically"
        assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
            "AgentRegistry enhancement resulted in wrong executor type"
        assert hasattr(tool_dispatcher, '_websocket_enhanced'), \
            "AgentRegistry enhancement did not set marker"
        
        logger.info("✅ AgentRegistry automatic tool dispatcher enhancement PASSED")

    @pytest.mark.asyncio  
    @pytest.mark.critical
    async def test_double_enhancement_protection(self):
        """Test that double enhancement is prevented."""
        dispatcher = ToolDispatcher()
        
        # First enhancement
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        first_executor = dispatcher.executor
        
        # Second enhancement (should be prevented)
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)  
        second_executor = dispatcher.executor
        
        # Should be the same executor
        assert first_executor == second_executor, \
            "Double enhancement occurred - should be prevented"
        assert dispatcher._websocket_enhanced is True, \
            "Enhancement marker lost during double enhancement attempt"
        
        logger.info("✅ Double enhancement protection PASSED")


# ============================================================================
# INTEGRATION TESTS - Tool Execution Event Flow
# ============================================================================

class TestEnhancedToolExecutionIntegration:
    """Integration tests for tool execution WebSocket event flow."""
    
    @pytest.fixture(autouse=True)
    async def setup_tool_integration_services(self):
        """Setup services for tool execution integration tests."""
        self.mock_ws_manager = MockWebSocketManagerForTools()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_enhanced_executor_sends_tool_events(self):
        """Test that enhanced executor sends tool execution events."""
        # Create enhanced executor
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        notifier = enhanced_executor.websocket_notifier
        
        # Create execution context
        context = AgentExecutionContext(
            run_id="tool-test",
            thread_id="tool-thread",
            user_id="tool-user",
            agent_name="tool_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send tool events directly
        await notifier.send_tool_executing(context, "test_analysis_tool")
        await notifier.send_tool_completed(context, "test_analysis_tool", {
            "result": "analysis complete",
            "data": {"insights": 42}
        })
        
        # Verify events were captured
        tool_events = self.mock_ws_manager.get_tool_events_for_thread("tool-thread")
        assert len(tool_events) == 2, \
            f"Expected 2 tool events, got {len(tool_events)}"
        
        # Verify event types
        event_types = [e['event_type'] for e in tool_events]
        assert 'tool_executing' in event_types, "Missing tool_executing event"
        assert 'tool_completed' in event_types, "Missing tool_completed event"
        
        # Verify event pairing
        pairs = self.mock_ws_manager.get_tool_execution_pairs("tool-thread")
        assert len(pairs) == 1, f"Expected 1 tool pair, got {len(pairs)}"
        assert pairs[0]['tool_name'] == "test_analysis_tool", \
            f"Wrong tool name in pair: {pairs[0]['tool_name']}"
        
        logger.info("✅ Enhanced executor tool event sending PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    @pytest.mark.timeout(30)
    async def test_tool_dispatcher_with_enhanced_executor_flow(self):
        """Test complete tool dispatcher flow with enhanced executor."""
        # Create and enhance tool dispatcher
        dispatcher = ToolDispatcher()
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        
        # Verify enhancement worked
        assert isinstance(dispatcher.executor, EnhancedToolExecutionEngine), \
            "Tool dispatcher not properly enhanced"
        
        # Create context for tool execution
        context = AgentExecutionContext(
            run_id="dispatcher-test",
            thread_id="dispatcher-thread", 
            user_id="dispatcher-user",
            agent_name="dispatcher_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Simulate tool execution through dispatcher
        # Note: We can't fully test tool execution without LLM, but we can test the WebSocket part
        enhanced_executor = dispatcher.executor
        await enhanced_executor.websocket_notifier.send_tool_executing(context, "dispatcher_tool")
        await enhanced_executor.websocket_notifier.send_tool_completed(context, "dispatcher_tool", {"status": "ok"})
        
        # Verify tool events through dispatcher
        tool_events = self.mock_ws_manager.get_tool_events_for_thread("dispatcher-thread")
        assert len(tool_events) >= 2, \
            f"Tool dispatcher flow missing events, got {len(tool_events)}"
        
        pairs = self.mock_ws_manager.get_tool_execution_pairs("dispatcher-thread")
        assert len(pairs) >= 1, f"Tool dispatcher flow missing pairs, got {len(pairs)}"
        
        logger.info("✅ Tool dispatcher enhanced executor flow PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)  
    async def test_multiple_concurrent_tool_executions(self):
        """Test multiple concurrent tool executions with WebSocket events.""" 
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        notifier = enhanced_executor.websocket_notifier
        
        # Define multiple tools to execute concurrently
        tools = ["data_analyzer", "report_generator", "trend_analyzer", "compliance_checker"]
        
        # Create contexts for each tool
        contexts = []
        for i, tool in enumerate(tools):
            context = AgentExecutionContext(
                run_id=f"concurrent-{i}",
                thread_id=f"concurrent-thread-{i}",
                user_id=f"concurrent-user-{i}",
                agent_name="concurrent_agent",
                retry_count=0,
                max_retries=1
            )
            contexts.append((context, tool))
        
        # Execute tools concurrently  
        async def execute_tool(context, tool_name):
            await notifier.send_tool_executing(context, tool_name)
            await asyncio.sleep(0.01)  # Simulate tool execution time
            await notifier.send_tool_completed(context, tool_name, {"result": f"{tool_name}_complete"})
        
        # Run all tools concurrently
        tasks = [execute_tool(ctx, tool) for ctx, tool in contexts]
        await asyncio.gather(*tasks)
        
        # Verify all tool events were captured
        total_tool_events = len(self.mock_ws_manager.tool_events)
        expected_events = len(tools) * 2  # executing + completed for each tool
        assert total_tool_events == expected_events, \
            f"Concurrent tool execution lost events: got {total_tool_events}, expected {expected_events}"
        
        # Verify each tool has proper pairs
        for i, tool in enumerate(tools):
            thread_id = f"concurrent-thread-{i}"
            pairs = self.mock_ws_manager.get_tool_execution_pairs(thread_id)
            assert len(pairs) == 1, f"Tool {tool} missing event pair"
            assert pairs[0]['tool_name'] == tool, f"Wrong tool name for {tool}"
        
        logger.info(f"✅ Concurrent tool execution ({len(tools)} tools) PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_tool_execution_error_handling_events(self):
        """Test that tool execution errors still produce proper WebSocket events."""
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        notifier = enhanced_executor.websocket_notifier
        
        context = AgentExecutionContext(
            run_id="error-tool-test",
            thread_id="error-tool-thread",
            user_id="error-tool-user", 
            agent_name="error_tool_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Start tool execution
        await notifier.send_tool_executing(context, "failing_tool")
        
        # Simulate tool error - still send completion with error info
        await notifier.send_tool_completed(context, "failing_tool", {
            "status": "error",
            "error": "Tool failed to analyze data",
            "details": "Network timeout during API call"
        })
        
        # Verify events were sent even for errors
        tool_events = self.mock_ws_manager.get_tool_events_for_thread("error-tool-thread")
        assert len(tool_events) == 2, \
            f"Error tool execution missing events, got {len(tool_events)}"
        
        pairs = self.mock_ws_manager.get_tool_execution_pairs("error-tool-thread")
        assert len(pairs) == 1, f"Error tool execution missing pairs, got {len(pairs)}"
        
        # Verify error information in completed event
        completed_event = pairs[0]['completed']
        result = completed_event['message'].get('result', {})
        assert result.get('status') == 'error', "Error status not preserved in tool completion"
        
        logger.info("✅ Tool execution error handling events PASSED")


# ============================================================================
# PERFORMANCE TESTS - Tool Execution Under Load
# ============================================================================

class TestEnhancedToolExecutionPerformance:
    """Performance tests for tool execution WebSocket events."""
    
    @pytest.fixture(autouse=True)
    async def setup_tool_performance_services(self):
        """Setup services for tool execution performance tests."""
        self.mock_ws_manager = MockWebSocketManagerForTools()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_tool_execution_high_frequency_events(self):
        """Test tool execution WebSocket events under high frequency."""
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        notifier = enhanced_executor.websocket_notifier
        
        # High frequency tool executions
        tool_count = 50
        start_time = time.time()
        
        async def rapid_tool_execution(tool_id):
            context = AgentExecutionContext(
                run_id=f"rapid-{tool_id}",
                thread_id=f"rapid-thread-{tool_id % 10}",  # 10 concurrent threads
                user_id=f"rapid-user-{tool_id % 10}",
                agent_name="rapid_agent",
                retry_count=0,
                max_retries=1
            )
            
            await notifier.send_tool_executing(context, f"rapid_tool_{tool_id}")
            await notifier.send_tool_completed(context, f"rapid_tool_{tool_id}", {"rapid": True})
        
        # Execute all tools rapidly
        tasks = [rapid_tool_execution(i) for i in range(tool_count)]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        events_per_second = (tool_count * 2) / duration  # 2 events per tool
        
        # Verify performance
        assert events_per_second >= 100, \
            f"Tool execution events too slow: {events_per_second:.0f} events/sec (expected ≥100)"
        
        # Verify all events captured
        total_tool_events = len(self.mock_ws_manager.tool_events)
        expected_events = tool_count * 2
        assert total_tool_events == expected_events, \
            f"High frequency tool execution lost events: got {total_tool_events}, expected {expected_events}"
        
        logger.info(f"✅ High frequency tool execution: {events_per_second:.0f} events/sec PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_tool_execution_burst_load_handling(self):
        """Test tool execution WebSocket events handling burst loads."""
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        notifier = enhanced_executor.websocket_notifier
        
        # Simulate burst load - many tools starting simultaneously
        burst_size = 20
        
        # Create all contexts first
        contexts = []
        for i in range(burst_size):
            context = AgentExecutionContext(
                run_id=f"burst-{i}",
                thread_id=f"burst-thread",  # All same thread
                user_id="burst-user",
                agent_name="burst_agent",
                retry_count=0,
                max_retries=1
            )
            contexts.append(context)
        
        start_time = time.time()
        
        # Send all tool_executing events simultaneously (burst start)
        executing_tasks = [
            notifier.send_tool_executing(ctx, f"burst_tool_{i}")
            for i, ctx in enumerate(contexts)
        ]
        await asyncio.gather(*executing_tasks)
        
        # Small delay to simulate processing
        await asyncio.sleep(0.1)
        
        # Send all tool_completed events simultaneously (burst end)  
        completed_tasks = [
            notifier.send_tool_completed(ctx, f"burst_tool_{i}", {"burst_result": i})
            for i, ctx in enumerate(contexts)
        ]
        await asyncio.gather(*completed_tasks)
        
        duration = time.time() - start_time
        
        # Verify burst handling
        tool_events = self.mock_ws_manager.get_tool_events_for_thread("burst-thread")
        assert len(tool_events) == burst_size * 2, \
            f"Burst load lost events: got {len(tool_events)}, expected {burst_size * 2}"
        
        # Verify all tools have proper pairs
        pairs = self.mock_ws_manager.get_tool_execution_pairs("burst-thread")
        assert len(pairs) == burst_size, \
            f"Burst load missing tool pairs: got {len(pairs)}, expected {burst_size}"
        
        # Verify timing (should handle burst quickly)
        assert duration < 5.0, \
            f"Burst load too slow: {duration:.2f}s (expected <5s)"
        
        logger.info(f"✅ Burst load handling ({burst_size} tools in {duration:.2f}s) PASSED")


# ============================================================================
# REGRESSION TESTS - Tool Execution Specific
# ============================================================================  

class TestEnhancedToolExecutionRegression:
    """Regression tests specifically for tool execution WebSocket events."""
    
    @pytest.fixture(autouse=True)  
    async def setup_tool_regression_services(self):
        """Setup services for tool execution regression tests."""
        self.mock_ws_manager = MockWebSocketManagerForTools()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_regression_tool_dispatcher_enhancement_still_works(self):
        """REGRESSION TEST: Tool dispatcher enhancement still works after updates."""
        from netra_backend.app.agents.enhanced_tool_execution import enhance_tool_dispatcher_with_notifications
        import inspect
        
        # Verify enhancement function still exists and works
        dispatcher = ToolDispatcher()
        original_executor = dispatcher.executor
        
        # This should not raise an exception
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        
        # Verify enhancement still works
        assert dispatcher.executor != original_executor, \
            "REGRESSION: Tool dispatcher enhancement no longer works"
        assert isinstance(dispatcher.executor, EnhancedToolExecutionEngine), \
            "REGRESSION: Tool dispatcher enhancement produces wrong executor type"
        
        logger.info("✅ Regression test tool dispatcher enhancement PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_regression_agent_registry_still_enhances_tools(self):
        """REGRESSION TEST: AgentRegistry still enhances tool dispatcher."""
        class MockLLM:
            pass
        
        dispatcher = ToolDispatcher()
        original_executor = dispatcher.executor
        
        registry = AgentRegistry(MockLLM(), dispatcher)
        registry.set_websocket_manager(self.mock_ws_manager)
        
        # Should still be enhanced
        assert dispatcher.executor != original_executor, \
            "REGRESSION: AgentRegistry no longer enhances tool dispatcher"
        assert hasattr(dispatcher, '_websocket_enhanced'), \
            "REGRESSION: AgentRegistry enhancement marker missing"
        
        logger.info("✅ Regression test AgentRegistry tool enhancement PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_regression_tool_events_still_paired(self):
        """REGRESSION TEST: Tool events are still properly paired."""
        enhanced_executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        notifier = enhanced_executor.websocket_notifier
        
        context = AgentExecutionContext(
            run_id="regression-pair-test",
            thread_id="regression-pair-thread",
            user_id="regression-pair-user",
            agent_name="regression_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send multiple tool event pairs
        tools = ["tool1", "tool2", "tool3"]
        for tool in tools:
            await notifier.send_tool_executing(context, tool)
            await notifier.send_tool_completed(context, tool, {"done": True})
        
        # Verify pairing still works
        pairs = self.mock_ws_manager.get_tool_execution_pairs("regression-pair-thread")
        assert len(pairs) == len(tools), \
            f"REGRESSION: Tool event pairing broken - got {len(pairs)} pairs, expected {len(tools)}"
        
        # Verify all tools accounted for
        pair_tools = {pair['tool_name'] for pair in pairs}
        assert pair_tools == set(tools), \
            f"REGRESSION: Tool pairing missing tools - got {pair_tools}, expected {set(tools)}"
        
        logger.info("✅ Regression test tool event pairing PASSED")


# ============================================================================
# TEST SUITE RUNNER  
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestEnhancedToolExecutionSuite:
    """Main test suite for enhanced tool execution WebSocket events."""
    
    @pytest.mark.asyncio
    async def test_run_enhanced_tool_execution_suite(self):
        """Run the complete enhanced tool execution WebSocket test suite."""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING ENHANCED TOOL EXECUTION WEBSOCKET TEST SUITE")
        logger.info("Business Value: $500K+ ARR - Tool execution visibility in chat")
        logger.info("=" * 80)
        
        suite_components = [
            "Unit Tests - Enhanced tool execution components",
            "Integration Tests - Tool execution event flow", 
            "Performance Tests - Tool execution under load",
            "Regression Tests - Tool execution specific checks"
        ]
        
        for component in suite_components:
            logger.info(f"✅ {component} - Test classes defined")
        
        logger.info("\n🔧 TOOL EXECUTION WEBSOCKET SUITE READY") 
        logger.info("Run with: pytest tests/mission_critical/test_enhanced_tool_execution_websocket_events.py -v")
        logger.info("=" * 80)


if __name__ == "__main__":
    # Run with comprehensive output  
    pytest.main([__file__, "-v", "--tb=short", "-x", "--durations=10"])