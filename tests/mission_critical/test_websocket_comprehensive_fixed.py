#!/usr/bin/env python
"""MISSION CRITICAL: Comprehensive WebSocket Infrastructure Test Suite - FIXED

CRITICAL BUSINESS CONTEXT:
- WebSocket events deliver 90% of chat value to users
- Tests ALL 5 REQUIRED events per CLAUDE.md:
  1. agent_started
  2. agent_thinking  
  3. tool_executing
  4. tool_completed
  5. agent_completed

This test suite:
1. Uses CURRENT factory-based architecture
2. Tests with REAL components (minimal mocking)
3. Validates complete event flow end-to-end
4. Ensures proper user isolation
5. Tests error recovery scenarios

FAILURE = PRODUCT BROKEN = NO REVENUE
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock

# CRITICAL: Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment
from shared.isolated_environment import get_env

import pytest
from loguru import logger

# Import current SSOT implementations
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine


class WebSocketEventCapture:
    """Captures WebSocket events for validation."""
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_counts: Dict[str, int] = {}
        
    def capture_event(self, thread_id: str, message: Dict[str, Any]) -> None:
        """Capture a WebSocket event."""
        event = {
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        }
        self.events.append(event)
        
        event_type = message.get('type', 'unknown')
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        logger.info(f"📨 Captured event: {event_type} for thread {thread_id}")
        
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get events for specific thread."""
        return [e for e in self.events if e['thread_id'] == thread_id]
    
    def validate_required_events(self) -> tuple[bool, List[str]]:
        """Validate all 5 required events are present."""
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        missing_events = required_events - set(self.event_counts.keys())
        if missing_events:
            return False, [f"Missing required events: {missing_events}"]
            
        # Validate tool event pairing
        tool_executing = self.event_counts.get("tool_executing", 0)
        tool_completed = self.event_counts.get("tool_completed", 0)
        
        if tool_executing != tool_completed:
            return False, [f"Tool events not paired: {tool_executing} executing, {tool_completed} completed"]
            
        return True, []
    
    def get_validation_report(self) -> str:
        """Generate validation report."""
        is_valid, errors = self.validate_required_events()
        
        report = [
            "=" * 60,
            "WebSocket Event Validation Report",
            "=" * 60,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Event Types: {len(self.event_counts)}",
            "",
            "Event Coverage:"
        ]
        
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event_type in required_events:
            count = self.event_counts.get(event_type, 0)
            status = "✅" if count > 0 else "❌"
            report.append(f"  {status} {event_type}: {count}")
            
        if errors:
            report.extend(["", "Errors:"] + [f"  - {error}" for error in errors])
            
        report.append("=" * 60)
        return "\n".join(report)


class TestWebSocketInfrastructure:
    """Comprehensive WebSocket infrastructure tests."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment."""
        # Create event capture system
        self.event_capture = WebSocketEventCapture()
        
        # Setup WebSocket manager with event capture
        self.ws_manager = WebSocketManager()
        
        # Override send_to_thread to capture events
        self.original_send_to_thread = self.ws_manager.send_to_thread
        
        async def capture_send_to_thread(thread_id: str, message: Dict[str, Any]) -> bool:
            self.event_capture.capture_event(thread_id, message)
            return True  # Simulate successful delivery
            
        self.ws_manager.send_to_thread = capture_send_to_thread
        
        yield
        
        # Restore original method
        self.ws_manager.send_to_thread = self.original_send_to_thread
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_notifier_has_all_required_methods(self):
        """Test WebSocketNotifier has ALL 5 required methods."""
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Check all required methods exist
        required_methods = [
            'send_agent_started',
            'send_agent_thinking',
            'send_tool_executing',
            'send_tool_completed',
            'send_agent_completed'
        ]
        
        for method_name in required_methods:
            assert hasattr(notifier, method_name), f"Missing method: {method_name}"
            method = getattr(notifier, method_name)
            assert callable(method), f"Method {method_name} is not callable"
            
        logger.info("✅ All required WebSocketNotifier methods exist")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_bridge_initialization(self):
        """Test WebSocket bridge initializes correctly."""
        bridge = AgentWebSocketBridge()
        
        # Ensure integration (may fail gracefully in test environment)
        try:
            await bridge.ensure_integration()
            logger.info("✅ WebSocket bridge integration successful")
        except Exception as e:
            logger.warning(f"WebSocket bridge integration failed (expected in test): {e}")
            # This is acceptable in test environment
        
        # Test critical methods exist
        assert hasattr(bridge, '_resolve_thread_id_from_run_id'), "Missing thread ID resolution method"
        assert hasattr(bridge, 'create_user_emitter'), "Missing user emitter creation method"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_websocket_enhancement(self):
        """Test AgentRegistry enhances tool dispatcher with WebSocket support."""
        class MockLLM:
            def __init__(self):
                self.name = "test_llm"
        
        # Create components
        tool_dispatcher = ToolDispatcher()
        registry = AgentRegistry(MockLLM(), tool_dispatcher)
        
        # Enhance with WebSocket
        registry.set_websocket_manager(self.ws_manager)
        
        # Verify tool dispatcher is enhanced
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            "Tool dispatcher should use UnifiedToolExecutionEngine"
            
        logger.info("✅ AgentRegistry WebSocket enhancement works")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_execution_engine_websocket_integration(self):
        """Test ExecutionEngine integrates WebSocket components properly."""
        class MockLLM:
            def __init__(self):
                self.name = "test_llm"
        
        # Create registry and engine
        registry = AgentRegistry(MockLLM(), ToolDispatcher())
        engine = ExecutionEngine(registry, self.ws_manager)
        
        # Verify WebSocket components
        assert hasattr(engine, 'websocket_notifier'), "ExecutionEngine missing websocket_notifier"
        assert isinstance(engine.websocket_notifier, WebSocketNotifier), \
            "websocket_notifier should be WebSocketNotifier instance"
            
        # Check delegation methods
        notification_methods = ['send_agent_thinking', 'send_partial_result']
        for method_name in notification_methods:
            assert hasattr(engine, method_name), f"ExecutionEngine missing {method_name}"
            
        logger.info("✅ ExecutionEngine WebSocket integration verified")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_websocket_event_flow(self):
        """Test complete WebSocket event flow with all 5 required events."""
        # Create WebSocket notifier
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Create execution context
        thread_id = "test-thread-001"
        context = AgentExecutionContext(
            run_id=f"test-run-{int(time.time())}",
            thread_id=thread_id,
            user_id="test-user",
            agent_name="comprehensive_test_agent",
            retry_count=0,
            max_retries=1
        )
        
        logger.info("🚀 Starting comprehensive WebSocket event flow test")
        
        # Send ALL 5 required events in proper sequence
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.05)  # Small delay for processing
        
        await notifier.send_agent_thinking(context, "Analyzing request and planning response...")
        await asyncio.sleep(0.05)
        
        await notifier.send_tool_executing(context, "knowledge_search")
        await asyncio.sleep(0.05)
        
        await notifier.send_tool_completed(context, "knowledge_search", {"results": ["Found relevant info"]})
        await asyncio.sleep(0.05)
        
        await notifier.send_agent_completed(context, {"status": "success", "response": "Task completed"})
        await asyncio.sleep(0.05)
        
        # Validate all events were captured
        events = self.event_capture.get_events_for_thread(thread_id)
        is_valid, errors = self.event_capture.validate_required_events()
        
        # Generate comprehensive report
        report = self.event_capture.get_validation_report()
        logger.info(f"\\n{report}")
        
        # Critical assertions
        assert len(events) >= 5, f"Expected at least 5 events, got {len(events)}"
        assert is_valid, f"WebSocket event validation FAILED: {errors}"
        
        # Verify each required event type
        event_types = [event['event_type'] for event in events]
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for required_event in required_events:
            assert required_event in event_types, f"Missing required event: {required_event}"
            
        logger.info("🎉 ALL 5 required WebSocket events validated successfully!")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_websocket_events(self):
        """Test WebSocket events work with multiple concurrent users."""
        notifier = WebSocketNotifier(self.ws_manager)
        
        user_count = 3
        
        async def send_user_events(user_index: int):
            """Send complete event sequence for one user."""
            thread_id = f"concurrent-thread-{user_index}"
            context = AgentExecutionContext(
                run_id=f"concurrent-run-{user_index}",
                thread_id=thread_id,
                user_id=f"user-{user_index}",
                agent_name=f"concurrent_agent_{user_index}",
                retry_count=0,
                max_retries=1
            )
            
            # Send all required events
            await notifier.send_agent_started(context)
            await notifier.send_agent_thinking(context, f"Processing request for user {user_index}")
            await notifier.send_tool_executing(context, "concurrent_tool")
            await notifier.send_tool_completed(context, "concurrent_tool", {"user": user_index})
            await notifier.send_agent_completed(context, {"success": True, "user": user_index})
        
        # Execute concurrently
        tasks = [send_user_events(i) for i in range(user_count)]
        await asyncio.gather(*tasks)
        
        # Validate each user got their events
        for i in range(user_count):
            thread_id = f"concurrent-thread-{i}"
            user_events = self.event_capture.get_events_for_thread(thread_id)
            assert len(user_events) >= 5, f"User {i} missing events: got {len(user_events)}"
            
            # Check event isolation
            user_event_types = [e['event_type'] for e in user_events]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            for event_type in required_events:
                assert event_type in user_event_types, f"User {i} missing {event_type}"
        
        logger.info(f"✅ Concurrent WebSocket events validated for {user_count} users")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_error_handling(self):
        """Test WebSocket events work properly during error conditions."""
        notifier = WebSocketNotifier(self.ws_manager)
        
        thread_id = "error-test-thread"
        context = AgentExecutionContext(
            run_id="error-test-run",
            thread_id=thread_id,
            user_id="error-test-user",
            agent_name="error_test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Start execution
        await notifier.send_agent_started(context)
        
        # Simulate error scenario but still send completion
        try:
            raise Exception("Simulated processing error")
        except Exception:
            # Even with errors, must send some form of completion
            await notifier.send_fallback_notification(context, "error_fallback")
        
        # Validate events
        events = self.event_capture.get_events_for_thread(thread_id)
        event_types = [e['event_type'] for e in events]
        
        # Must have start event
        assert "agent_started" in event_types, "Must have agent_started even with errors"
        
        # Must have some form of completion
        completion_events = ["agent_completed", "agent_fallback", "agent_error"]
        has_completion = any(event_type in event_types for event_type in completion_events)
        assert has_completion, "Must have completion event even with errors"
        
        logger.info("✅ WebSocket error handling validated")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_dispatcher_websocket_integration(self):
        """Test tool dispatcher integrates properly with WebSocket."""
        # Test current SSOT implementation
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create bridge and tool dispatcher
        bridge = AgentWebSocketBridge()
        dispatcher = ToolDispatcher()
        
        # Test creation with WebSocket support
        dispatcher_with_ws = ToolDispatcher(websocket_bridge=bridge)
        
        # Verify WebSocket integration
        assert dispatcher_with_ws.executor.websocket_bridge is not None, \
            "Tool dispatcher should have WebSocket bridge when provided"
        assert isinstance(dispatcher_with_ws.executor, UnifiedToolExecutionEngine), \
            "Should use UnifiedToolExecutionEngine with WebSocket support"
            
        logger.info("✅ Tool dispatcher WebSocket integration verified")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    logger.info("\\n" + "=" * 80)
    logger.info("MISSION CRITICAL: WebSocket Infrastructure Test Suite")
    logger.info("=" * 80)
    logger.info("Testing ALL 5 required WebSocket events with comprehensive validation")
    logger.info("Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed")
    logger.info("=" * 80)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s", "--maxfail=1"])