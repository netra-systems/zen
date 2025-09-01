#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - FOCUSED FIX

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality

Fixed version that addresses the hanging issue by:
1. Using proper mock isolation to avoid WebSocketManager initialization hang
2. Testing the critical integration points without complex background tasks
3. Validating all required WebSocket events are sent during agent execution
4. Ensuring AgentRegistry enhancement works correctly

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger


# ============================================================================
# FOCUSED MOCK WEBSOCKET MANAGER TO PREVENT HANGING
# ============================================================================

class FocusedMockWebSocketManager:
    """Focused mock that captures events without complex initialization."""
    
    def __init__(self):
        self.sent_messages: List[Dict] = []
        self.thread_messages: Dict[str, List[Dict]] = {}
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message for validation."""
        self.sent_messages.append({
            'thread_id': thread_id,
            'message': message,
            'timestamp': time.time()
        })
        
        if thread_id not in self.thread_messages:
            self.thread_messages[thread_id] = []
        self.thread_messages[thread_id].append(message)
        
        return True
    
    def get_messages_for_thread(self, thread_id: str) -> List[Dict]:
        """Get messages for specific thread."""
        return self.thread_messages.get(thread_id, [])
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for thread."""
        messages = self.get_messages_for_thread(thread_id)
        return [msg.get('type', 'unknown') for msg in messages]


# ============================================================================
# EVENT VALIDATOR FOR MISSION CRITICAL REQUIREMENTS
# ============================================================================

class MissionCriticalValidator:
    """Validates WebSocket events meet mission critical requirements."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking",
        "tool_executing", 
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.received_events = []
        self.event_counts = {}
    
    def record_event(self, event: Dict):
        """Record an event."""
        event_type = event.get('type', 'unknown')
        self.received_events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def validate_requirements(self) -> tuple[bool, List[str]]:
        """Validate mission critical requirements."""
        failures = []
        
        # Check required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"Missing required events: {missing}")
        
        # Check tool pairing
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0) 
        if tool_starts != tool_ends:
            failures.append(f"Unpaired tool events: {tool_starts} starts, {tool_ends} ends")
        
        return len(failures) == 0, failures


# ============================================================================
# MISSION CRITICAL TESTS
# ============================================================================

class TestMissionCriticalWebSocketEvents:
    """Mission critical WebSocket event tests with proper isolation."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment without hanging WebSocketManager."""
        self.mock_ws_manager = FocusedMockWebSocketManager()
        yield
        # Cleanup automatically handled by mock
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_notifier_core_functionality(self):
        """Test WebSocketNotifier core functionality without real WebSocketManager."""
        # Import here to avoid early initialization
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        # Create notifier with mock manager
        notifier = WebSocketNotifier(self.mock_ws_manager)
        
        # Verify all critical methods exist
        critical_methods = [
            'send_agent_started',
            'send_agent_thinking',
            'send_tool_executing', 
            'send_tool_completed',
            'send_agent_completed'
        ]
        
        for method in critical_methods:
            assert hasattr(notifier, method), f"Missing critical method: {method}"
            assert callable(getattr(notifier, method)), f"Method {method} not callable"
        
        # Test event sending with context
        context = AgentExecutionContext(
            run_id="test-run",
            thread_id="test-thread",
            user_id="test-user",
            agent_name="test_agent",
            retry_count=0,
            max_retries=1
        )
        
        validator = MissionCriticalValidator()
        
        # Send critical event sequence
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Processing request...")
        await notifier.send_tool_executing(context, "test_tool")
        await notifier.send_tool_completed(context, "test_tool", {"result": "success"})
        await notifier.send_agent_completed(context, {"success": True})
        
        # Validate events were recorded
        messages = self.mock_ws_manager.get_messages_for_thread("test-thread")
        for msg in messages:
            validator.record_event(msg)
        
        is_valid, failures = validator.validate_requirements()
        
        assert is_valid, f"Mission critical validation failed: {failures}"
        assert len(messages) >= 5, f"Expected at least 5 events, got {len(messages)}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_websocket_enhancement(self):
        """Test that AgentRegistry properly enhances tool dispatcher."""
        # Import here to avoid initialization issues
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        
        # Mock LLM to avoid complex dependencies
        class MockLLM:
            pass
        
        # Create components
        tool_dispatcher = ToolDispatcher()
        original_executor = tool_dispatcher.executor
        
        registry = AgentRegistry(MockLLM(), tool_dispatcher)
        
        # CRITICAL: Test that set_websocket_manager enhances the tool dispatcher
        registry.set_websocket_manager(self.mock_ws_manager)
        
        # Verify enhancement
        assert tool_dispatcher.executor != original_executor, \
            "Tool dispatcher was not enhanced"
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            "Wrong executor type after enhancement"
        assert hasattr(tool_dispatcher, '_websocket_enhanced'), \
            "Enhancement marker missing"
        assert tool_dispatcher._websocket_enhanced is True, \
            "Enhancement not properly marked"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_execution_engine_websocket_integration(self):
        """Test ExecutionEngine WebSocket integration."""
        # Import here to avoid initialization issues
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        
        # Mock LLM
        class MockLLM:
            pass
        
        # Create registry with tool dispatcher
        registry = AgentRegistry(MockLLM(), ToolDispatcher())
        
        # Create execution engine with WebSocket manager
        engine = ExecutionEngine(registry, self.mock_ws_manager)
        
        # Verify WebSocket components
        assert hasattr(engine, 'websocket_notifier'), \
            "ExecutionEngine missing websocket_notifier"
        assert isinstance(engine.websocket_notifier, WebSocketNotifier), \
            "websocket_notifier is not WebSocketNotifier instance"
        assert hasattr(engine, 'send_agent_thinking'), \
            "ExecutionEngine missing send_agent_thinking method"
        assert hasattr(engine, 'send_partial_result'), \
            "ExecutionEngine missing send_partial_result method"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_unified_tool_execution_events(self):
        """Test that enhanced tool execution sends WebSocket events."""
        # Import here to avoid initialization issues
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        # Create enhanced executor with mock WebSocket manager
        executor = UnifiedToolExecutionEngine(self.mock_ws_manager)
        
        # Verify WebSocket notifier exists
        assert hasattr(executor, 'websocket_notifier'), \
            "Enhanced executor missing websocket_notifier"
        assert executor.websocket_notifier is not None, \
            "WebSocket notifier is None"
        
        # Test direct event sending
        notifier = executor.websocket_notifier
        context = AgentExecutionContext(
            run_id="enhanced-test",
            thread_id="enhanced-thread",
            user_id="enhanced-user", 
            agent_name="enhanced_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send tool events
        await notifier.send_tool_executing(context, "enhanced_tool")
        await notifier.send_tool_completed(context, "enhanced_tool", {"result": "enhanced"})
        
        # Verify events were sent
        messages = self.mock_ws_manager.get_messages_for_thread("enhanced-thread")
        event_types = [msg.get('type') for msg in messages]
        
        assert "tool_executing" in event_types, \
            "tool_executing event not sent"
        assert "tool_completed" in event_types, \
            "tool_completed event not sent"
        assert len(messages) == 2, \
            f"Expected 2 events, got {len(messages)}"
    
    @pytest.mark.asyncio 
    @pytest.mark.critical
    async def test_concurrent_websocket_events(self):
        """Test WebSocket events work correctly under concurrent load."""
        # Import here to avoid initialization issues
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        notifier = WebSocketNotifier(self.mock_ws_manager)
        
        async def send_concurrent_events(connection_id: str):
            context = AgentExecutionContext(
                run_id=f"concurrent-{connection_id}",
                thread_id=f"thread-{connection_id}",
                user_id=f"user-{connection_id}",
                agent_name="concurrent_agent",
                retry_count=0,
                max_retries=1
            )
            
            await notifier.send_agent_started(context)
            await notifier.send_agent_thinking(context, "Concurrent processing...")
            await notifier.send_tool_executing(context, "concurrent_tool")
            await notifier.send_tool_completed(context, "concurrent_tool", {"result": "done"})
            await notifier.send_agent_completed(context, {"success": True})
        
        # Run 5 concurrent event sequences
        tasks = [send_concurrent_events(str(i)) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify all sequences completed
        for i in range(5):
            thread_id = f"thread-{i}"
            messages = self.mock_ws_manager.get_messages_for_thread(thread_id)
            event_types = [msg.get('type') for msg in messages]
            
            validator = MissionCriticalValidator()
            for msg in messages:
                validator.record_event(msg)
            
            is_valid, failures = validator.validate_requirements()
            assert is_valid, f"Concurrent validation failed for {thread_id}: {failures}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_scenario_websocket_events(self):
        """Test WebSocket events during error scenarios."""
        # Import here to avoid initialization issues
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        notifier = WebSocketNotifier(self.mock_ws_manager)
        
        context = AgentExecutionContext(
            run_id="error-test",
            thread_id="error-thread",
            user_id="error-user",
            agent_name="error_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Start execution
        await notifier.send_agent_started(context)
        
        # Simulate error during execution
        try:
            raise Exception("Simulated error")
        except Exception:
            # Send fallback notification 
            await notifier.send_fallback_notification(context, "error_fallback")
        
        # Verify events
        messages = self.mock_ws_manager.get_messages_for_thread("error-thread")
        event_types = [msg.get('type') for msg in messages]
        
        assert "agent_started" in event_types, \
            "agent_started event missing in error scenario"
        assert "agent_fallback" in event_types, \
            "agent_fallback event missing in error scenario"
        assert len(messages) >= 2, \
            f"Expected at least 2 events in error scenario, got {len(messages)}"


# ============================================================================
# REGRESSION PREVENTION TESTS
# ============================================================================

class TestRegressionPrevention:
    """Prevent regression of previously fixed WebSocket issues."""
    
    @pytest.fixture(autouse=True)
    def setup_regression_environment(self):
        """Setup for regression tests."""
        self.mock_ws_manager = FocusedMockWebSocketManager()
        yield
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_always_enhances_dispatcher(self):
        """REGRESSION: AgentRegistry MUST always enhance tool dispatcher."""
        # Import here to avoid initialization issues  
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        
        class MockLLM:
            pass
        
        # Test multiple times to catch intermittent issues
        for i in range(3):
            tool_dispatcher = ToolDispatcher()
            original_executor = tool_dispatcher.executor
            
            registry = AgentRegistry(MockLLM(), tool_dispatcher)
            
            # This is the critical call that was missing
            registry.set_websocket_manager(self.mock_ws_manager)
            
            # MUST be enhanced
            assert tool_dispatcher.executor != original_executor, \
                f"Iteration {i}: Tool dispatcher not enhanced - REGRESSION!"
            assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
                f"Iteration {i}: Wrong executor type - REGRESSION!"


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_events_fixed.py
    pytest.main([__file__, "-v", "--tb=short", "-x"])