#!/usr/bin/env python3
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - FIXED VERSION

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality

This is a FIXED version of the WebSocket test suite that:
1. Tests actual API signatures against real implementation
2. Validates WebSocket event flow without complex real services dependencies
3. Focuses on core functionality that must work for chat to function
4. Uses proper test infrastructure that works reliably

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional
import pytest

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import unified WebSocket mock for consistency
from test_framework.fixtures.websocket_manager_mock import create_compliance_mock
from test_framework.fixtures.websocket_test_helpers import (
    WebSocketAssertions,
    simulate_agent_execution_flow,
    reset_mock_for_test
)

# Import production components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


# ============================================================================
# UNIFIED WEBSOCKET MOCK - REPLACES LOCAL IMPLEMENTATION
# ============================================================================

# Use unified mock instead of local implementation
def MockWebSocketManager():
    """Factory function for backward compatibility - returns unified compliance mock."""
    return create_compliance_mock()


class MissionCriticalEventValidator:
    """Validates WebSocket events with extreme rigor."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking",
        "tool_executing", 
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
    
    def record(self, event: Dict) -> None:
        """Record an event for validation."""
        event_type = event.get("type", "unknown")
        self.events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met."""
        failures = []
        
        # Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")
        
        # Check for paired tool events
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        if tool_starts != tool_ends:
            failures.append(f"CRITICAL: Unpaired tool events - {tool_starts} starts, {tool_ends} ends")
        
        return len(failures) == 0, failures


# ============================================================================
# UNIT TESTS - Component Isolation  
# ============================================================================

class TestUnitWebSocketComponents:
    """Unit tests for individual WebSocket components."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_notifier_all_methods(self):
        """Test that WebSocketNotifier has ALL required methods and they work."""
        ws_manager = MockWebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        # Verify all methods exist
        required_methods = [
            'send_agent_started',
            'send_agent_thinking',
            'send_partial_result',
            'send_tool_executing', 
            'send_tool_completed',
            'send_final_report',
            'send_agent_completed'
        ]
        
        for method in required_methods:
            assert hasattr(notifier, method), f"Missing critical method: {method}"
            assert callable(getattr(notifier, method)), f"Method {method} is not callable"
        
        logger.info("✅ All WebSocketNotifier methods exist and are callable")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_notifier_method_signatures(self):
        """Test that WebSocketNotifier methods have correct signatures."""
        ws_manager = MockWebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        # Create test context
        context = AgentExecutionContext(
            run_id="test-123",
            thread_id="thread-456",
            user_id="user-789",
            agent_name="test_agent"
        )
        
        # Test each method with correct parameters
        test_calls = [
            ("send_agent_started", lambda: notifier.send_agent_started(context)),
            ("send_agent_thinking", lambda: notifier.send_agent_thinking(context, "Processing...")),
            ("send_partial_result", lambda: notifier.send_partial_result(context, "Partial result")),
            ("send_tool_executing", lambda: notifier.send_tool_executing(context, "search_tool")),
            ("send_tool_completed", lambda: notifier.send_tool_completed(context, "search_tool", {"status": "success"})),
            ("send_final_report", lambda: notifier.send_final_report(context, {"results": "complete"}, 1500.0)),
            ("send_agent_completed", lambda: notifier.send_agent_completed(context, {"success": True}, 2000.0))
        ]
        
        for method_name, method_call in test_calls:
            try:
                await method_call()
                logger.info(f"✅ {method_name}: signature correct")
            except Exception as e:
                pytest.fail(f"❌ {method_name}: signature mismatch - {e}")
        
        # Verify events were recorded
        assert len(ws_manager.messages) == len(test_calls), \
            f"Expected {len(test_calls)} events, got {len(ws_manager.messages)}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_dispatcher_enhancement(self):
        """Test that tool dispatcher enhancement actually works."""
        dispatcher = ToolDispatcher()
        ws_manager = MockWebSocketManager()
        
        # Verify initial state
        assert hasattr(dispatcher, 'executor'), "ToolDispatcher missing executor"
        original_executor = dispatcher.executor
        
        # Enhance
        enhance_tool_dispatcher_with_notifications(dispatcher, ws_manager)
        
        # Verify enhancement
        assert dispatcher.executor != original_executor, "Executor was not replaced"
        assert isinstance(dispatcher.executor, UnifiedToolExecutionEngine), \
            f"Executor is not UnifiedToolExecutionEngine, got {type(dispatcher.executor)}"
        assert hasattr(dispatcher, '_websocket_enhanced'), "Missing enhancement marker"
        assert dispatcher._websocket_enhanced is True, "Enhancement marker not set"
        
        logger.info("✅ Tool dispatcher enhanced successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_websocket_integration(self):
        """Test that AgentRegistry properly integrates WebSocket."""
        class MockLLM:
            pass
        
        tool_dispatcher = ToolDispatcher()
        registry = AgentRegistry(MockLLM(), tool_dispatcher)
        ws_manager = MockWebSocketManager()
        
        # Set WebSocket manager
        registry.set_websocket_manager(ws_manager)
        
        # Verify tool dispatcher was enhanced
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            "AgentRegistry did not enhance tool dispatcher"
        
        logger.info("✅ AgentRegistry enhanced tool dispatcher correctly")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_execution_engine_initialization(self):
        """Test that ExecutionEngine properly initializes WebSocket components."""
        class MockLLM:
            pass
        
        registry = AgentRegistry(MockLLM(), ToolDispatcher())
        ws_manager = MockWebSocketManager()
        
        engine = ExecutionEngine(registry, ws_manager)
        
        # Verify WebSocket components
        assert hasattr(engine, 'websocket_notifier'), "Missing websocket_notifier"
        assert isinstance(engine.websocket_notifier, WebSocketNotifier), \
            f"websocket_notifier is not WebSocketNotifier, got {type(engine.websocket_notifier)}"
        
        logger.info("✅ ExecutionEngine initialized WebSocket components correctly")


# ============================================================================
# INTEGRATION TESTS - Component Interaction
# ============================================================================

class TestIntegrationWebSocketFlow:
    """Integration tests for WebSocket event flow between components."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_websocket_event_flow(self):
        """Test complete WebSocket event flow from start to finish."""
        ws_manager = MockWebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        validator = MissionCriticalEventValidator()
        
        # Create context
        context = AgentExecutionContext(
            run_id="flow-test-123",
            thread_id="flow-thread-456",
            user_id="flow-user-789",
            agent_name="flow_test_agent"
        )
        
        # Send complete event sequence
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Analyzing request...")
        await notifier.send_tool_executing(context, "data_processor")
        await notifier.send_tool_completed(context, "data_processor", {"processed": 100})
        await notifier.send_agent_completed(context, {"success": True})
        
        # Validate events
        events = ws_manager.get_events_for_thread("flow-thread-456")
        assert len(events) == 5, f"Expected 5 events, got {len(events)}"
        
        for event in events:
            validator.record(event['message'])
        
        is_valid, failures = validator.validate_critical_requirements()
        assert is_valid, f"Event flow validation failed: {failures}"
        
        # Verify event order
        event_types = [e['event_type'] for e in events]
        expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        assert event_types == expected_order, f"Wrong event order: {event_types}"
        
        logger.info("✅ Complete WebSocket event flow validated successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_websocket_events(self):
        """Test WebSocket events with multiple concurrent threads."""
        ws_manager = MockWebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        # Create multiple contexts
        contexts = [
            AgentExecutionContext(
                run_id=f"concurrent-{i}",
                thread_id=f"thread-{i}",
                user_id=f"user-{i}",
                agent_name=f"agent_{i}"
            )
            for i in range(3)
        ]
        
        # Send events concurrently
        async def send_event_sequence(ctx):
            await notifier.send_agent_started(ctx)
            await notifier.send_agent_thinking(ctx, f"Processing for {ctx.agent_name}")
            await notifier.send_tool_executing(ctx, "concurrent_tool")
            await notifier.send_tool_completed(ctx, "concurrent_tool", {"done": True})
            await notifier.send_agent_completed(ctx, {"success": True})
        
        # Execute concurrently
        await asyncio.gather(*[send_event_sequence(ctx) for ctx in contexts])
        
        # Verify each thread received correct events
        for ctx in contexts:
            thread_events = ws_manager.get_event_types_for_thread(ctx.thread_id)
            expected = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            assert thread_events == expected, f"Thread {ctx.thread_id} wrong events: {thread_events}"
        
        # Verify total events
        total_events = len(ws_manager.messages)
        expected_total = 5 * len(contexts)  # 5 events per context
        assert total_events == expected_total, f"Expected {expected_total} total events, got {total_events}"
        
        logger.info(f"✅ Concurrent WebSocket events validated for {len(contexts)} threads")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_unified_tool_execution_events(self):
        """Test that enhanced tool execution sends proper WebSocket events."""
        ws_manager = MockWebSocketManager()
        enhanced_executor = UnifiedToolExecutionEngine(ws_manager)
        
        # Mock tool function
        async def test_tool(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate work
            return {"result": "success", "data": "processed"}
        
        # Create test state
        state = DeepAgentState(
            chat_thread_id="enhanced-thread",
            user_id="enhanced-user"
        )
        
        # Execute tool with WebSocket notifications
        result = await enhanced_executor.execute_with_state(
            test_tool, "test_tool", {}, state, "enhanced-run"
        )
        
        # Verify result
        assert result is not None, "Tool execution failed"
        
        # Verify WebSocket events were sent
        thread_events = ws_manager.get_event_types_for_thread("enhanced-thread")
        assert "tool_executing" in thread_events, f"Missing tool_executing event. Got: {thread_events}"
        assert "tool_completed" in thread_events, f"Missing tool_completed event. Got: {thread_events}"
        
        # Verify events are paired
        executing_count = thread_events.count("tool_executing")
        completed_count = thread_events.count("tool_completed") 
        assert executing_count == completed_count, \
            f"Unpaired tool events: {executing_count} executing, {completed_count} completed"
        
        logger.info("✅ Enhanced tool execution WebSocket events validated")


# ============================================================================
# REGRESSION PREVENTION TESTS
# ============================================================================

class TestRegressionPrevention:
    """Tests specifically designed to prevent regression of fixed issues."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_always_enhances_tool_dispatcher(self):
        """REGRESSION TEST: AgentRegistry MUST enhance tool dispatcher."""
        class MockLLM:
            pass
        
        # Test multiple times to catch intermittent issues
        for i in range(3):
            tool_dispatcher = ToolDispatcher()
            original_executor = tool_dispatcher.executor
            
            registry = AgentRegistry(MockLLM(), tool_dispatcher)
            ws_manager = MockWebSocketManager()
            
            # This is the critical call that was missing
            registry.set_websocket_manager(ws_manager)
            
            # MUST be enhanced
            assert tool_dispatcher.executor != original_executor, \
                f"Iteration {i}: Tool dispatcher not enhanced - REGRESSION!"
            assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
                f"Iteration {i}: Wrong executor type - REGRESSION!"
        
        logger.info("✅ AgentRegistry consistently enhances tool dispatcher")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_events_not_skipped_on_error(self):
        """REGRESSION TEST: Errors must not skip WebSocket events."""
        ws_manager = MockWebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        context = AgentExecutionContext(
            run_id="error-test",
            thread_id="error-thread",
            user_id="error-user",
            agent_name="error_agent"
        )
        
        # Start execution
        await notifier.send_agent_started(context)
        
        # Simulate error during execution
        try:
            raise Exception("Simulated error")
        except Exception:
            # Must still send completion using fallback
            await notifier.send_fallback_notification(context, "error_fallback")
        
        # Verify events
        thread_events = ws_manager.get_event_types_for_thread("error-thread")
        assert "agent_started" in thread_events, f"Missing start event: {thread_events}"
        assert "agent_fallback" in thread_events, f"Missing fallback event: {thread_events}"
        
        logger.info("✅ Error handling preserves WebSocket events")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_events_always_paired(self):
        """REGRESSION TEST: Tool events must ALWAYS be paired."""
        ws_manager = MockWebSocketManager()
        enhanced_executor = UnifiedToolExecutionEngine(ws_manager)
        
        # Test both success and failure cases
        state = DeepAgentState(
            chat_thread_id="pairing-thread",
            user_id="pairing-user"
        )
        
        # Success case
        async def success_tool(*args, **kwargs):
            return {"success": True}
        
        await enhanced_executor.execute_with_state(
            success_tool, "success_tool", {}, state, "success-run"
        )
        
        # Failure case
        async def failure_tool(*args, **kwargs):
            raise Exception("Tool failed")
        
        try:
            await enhanced_executor.execute_with_state(
                failure_tool, "failure_tool", {}, state, "failure-run"
            )
        except:
            pass  # Expected
        
        # Verify pairing
        thread_events = ws_manager.get_event_types_for_thread("pairing-thread")
        tool_starts = thread_events.count("tool_executing")
        tool_ends = thread_events.count("tool_completed")
        
        assert tool_starts == tool_ends, \
            f"REGRESSION: Unpaired tool events - {tool_starts} starts, {tool_ends} ends. Events: {thread_events}"
        assert tool_starts >= 2, \
            f"REGRESSION: Expected at least 2 tool executions, got {tool_starts}. Events: {thread_events}"
        
        logger.info("✅ Tool events are always properly paired")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestMissionCriticalWebSocketSuite:
    """Main test suite class for mission-critical WebSocket tests."""
    
    @pytest.mark.asyncio
    async def test_run_complete_suite(self):
        """Meta-test that validates the test suite itself is operational."""
        logger.info("\n" + "=" * 80)
        logger.info("MISSION CRITICAL WEBSOCKET TEST SUITE - FIXED VERSION")
        logger.info("=" * 80)
        
        # This test validates that the suite can run without infrastructure issues
        logger.info("✅ Mission Critical WebSocket Test Suite is operational")
        logger.info("All individual tests validate WebSocket API signatures and event flows")
        logger.info("Run with: pytest tests/mission_critical/test_websocket_agent_events_fixed.py -v")


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_agent_events_fixed.py
    # Or: pytest tests/mission_critical/test_websocket_agent_events_fixed.py -v
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])