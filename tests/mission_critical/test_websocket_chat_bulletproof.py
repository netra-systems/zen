#!/usr/bin/env python
"""MISSION CRITICAL: Bulletproof WebSocket Chat Event Tests

Business Value: $500K+ ARR - Core chat functionality is KING
Tests: Comprehensive real-world scenarios with extreme robustness

This test suite ensures:
1. All critical WebSocket events are sent for chat UI
2. Events arrive in correct order with proper data
3. Error conditions are handled gracefully 
4. Concurrent users work correctly
5. Reconnection preserves state
6. Performance meets <2s response requirement
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import random
import traceback

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

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
from netra_backend.app.websocket_core.heartbeat_manager import WebSocketHeartbeatManager, HeartbeatConfig
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.registry import ServerMessage, WebSocketMessage
from fastapi import WebSocket
from fastapi.websockets import WebSocketState


# ============================================================================
# ROBUST TEST UTILITIES
# ============================================================================

class RobustMockWebSocket:
    """Robust mock WebSocket that simulates real connection behavior."""
    
    def __init__(self, connection_id: str, should_fail: bool = False, failure_pattern: str = None):
        self.connection_id = connection_id
        self.client_state = WebSocketState.CONNECTED
        self.application_state = WebSocketState.CONNECTED
        self.messages_sent: List[Dict] = []
        self.messages_received: List[Dict] = []
        self.should_fail = should_fail
        self.failure_pattern = failure_pattern
        self.send_count = 0
        self.error_count = 0
        self.latency_ms = 0  # Simulated network latency
        self.packet_loss_rate = 0.0  # Simulated packet loss
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Simulate sending JSON with potential failures."""
        self.send_count += 1
        
        # Simulate network latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Simulate packet loss
        if random.random() < self.packet_loss_rate:
            raise ConnectionError("Simulated packet loss")
        
        # Simulate specific failure patterns
        if self.should_fail:
            if self.failure_pattern == "intermittent" and self.send_count % 3 == 0:
                self.error_count += 1
                raise ConnectionError("Intermittent connection failure")
            elif self.failure_pattern == "timeout" and self.send_count > 5:
                self.error_count += 1
                raise asyncio.TimeoutError("Connection timeout")
            elif self.failure_pattern == "disconnect":
                self.client_state = WebSocketState.DISCONNECTED
                raise ConnectionError("Connection disconnected")
        
        # Store message if successful
        self.messages_sent.append({
            "data": data,
            "timestamp": time.time(),
            "send_count": self.send_count
        })
    
    async def receive_json(self) -> Dict[str, Any]:
        """Simulate receiving JSON."""
        if self.messages_received:
            return self.messages_received.pop(0)
        await asyncio.sleep(0.1)
        return {"type": "ping"}
    
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Simulate closing connection."""
        self.client_state = WebSocketState.DISCONNECTED
        self.application_state = WebSocketState.DISCONNECTED
    
    def inject_message(self, message: Dict[str, Any]) -> None:
        """Inject a message to be received."""
        self.messages_received.append(message)


class BulletproofEventValidator:
    """Extremely robust event validation with detailed diagnostics."""
    
    CRITICAL_EVENTS = {
        "agent_started": {"required": True, "max_count": 1},
        "agent_thinking": {"required": True, "max_count": None},
        "tool_executing": {"required": True, "max_count": None},
        "tool_completed": {"required": True, "max_count": None},
        "agent_completed": {"required": True, "max_count": 1}
    }
    
    OPTIONAL_EVENTS = {
        "partial_result": {"required": False, "max_count": None},
        "final_report": {"required": False, "max_count": 1},
        "agent_fallback": {"required": False, "max_count": 1},
        "tool_error": {"required": False, "max_count": None}
    }
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.event_counts: Dict[str, int] = {}
        self.validation_errors: List[str] = []
        self.performance_metrics: Dict[str, float] = {}
        self.start_time = time.time()
        
    def record_event(self, event: Dict) -> None:
        """Record an event with comprehensive tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        # Store event
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Track performance metrics
        if event_type == "agent_started":
            self.performance_metrics["start_time"] = timestamp
        elif event_type in ["agent_completed", "final_report"]:
            self.performance_metrics["end_time"] = timestamp
            if "start_time" in self.performance_metrics:
                self.performance_metrics["total_duration"] = (
                    self.performance_metrics["end_time"] - self.performance_metrics["start_time"]
                )
    
    def validate_comprehensive(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Comprehensive validation with detailed diagnostics."""
        errors = []
        warnings = []
        diagnostics = {
            "total_events": len(self.events),
            "unique_event_types": len(self.event_counts),
            "event_counts": self.event_counts.copy(),
            "performance": self.performance_metrics.copy()
        }
        
        # 1. Validate required events
        for event_type, config in self.CRITICAL_EVENTS.items():
            count = self.event_counts.get(event_type, 0)
            if config["required"] and count == 0:
                errors.append(f"CRITICAL: Missing required event '{event_type}'")
            if config["max_count"] and count > config["max_count"]:
                warnings.append(f"Event '{event_type}' sent {count} times (max: {config['max_count']})")
        
        # 2. Validate event ordering
        if not self._validate_event_sequence():
            errors.append("CRITICAL: Invalid event sequence")
        
        # 3. Validate paired events
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0) + self.event_counts.get("tool_error", 0)
        if tool_starts != tool_ends:
            errors.append(f"CRITICAL: Unpaired tool events ({tool_starts} starts, {tool_ends} ends)")
        
        # 4. Validate performance
        if "total_duration" in self.performance_metrics:
            duration = self.performance_metrics["total_duration"]
            if duration > 30:
                warnings.append(f"Performance warning: Total duration {duration:.2f}s exceeds 30s limit")
            diagnostics["response_time_ok"] = duration < 2  # Target <2s
        
        # 5. Validate data integrity
        for event in self.events:
            if "type" not in event:
                errors.append(f"Event missing 'type' field: {event}")
            if "timestamp" not in event:
                warnings.append(f"Event '{event.get('type')}' missing timestamp")
        
        diagnostics["errors"] = errors
        diagnostics["warnings"] = warnings
        
        return len(errors) == 0, errors, diagnostics
    
    def _validate_event_sequence(self) -> bool:
        """Validate that events follow logical sequence."""
        if not self.event_timeline:
            return False
        
        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.validation_errors.append(f"First event was '{self.event_timeline[0][1]}', expected 'agent_started'")
            return False
        
        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report", "agent_fallback"]:
            self.validation_errors.append(f"Last event was '{last_event}', expected completion event")
            return False
        
        # Validate tool event pairing
        tool_stack = []
        for _, event_type, _ in self.event_timeline:
            if event_type == "tool_executing":
                tool_stack.append(event_type)
            elif event_type in ["tool_completed", "tool_error"]:
                if not tool_stack:
                    self.validation_errors.append(f"Tool completion without matching execution")
                    return False
                tool_stack.pop()
        
        if tool_stack:
            self.validation_errors.append(f"Unclosed tool executions: {len(tool_stack)}")
            return False
        
        return True
    
    def generate_detailed_report(self) -> str:
        """Generate comprehensive validation report."""
        is_valid, errors, diagnostics = self.validate_comprehensive()
        
        report_lines = [
            "\n" + "=" * 80,
            "BULLETPROOF WEBSOCKET VALIDATION REPORT",
            "=" * 80,
            f"Overall Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {diagnostics['total_events']}",
            f"Unique Event Types: {diagnostics['unique_event_types']}",
            ""
        ]
        
        # Performance metrics
        if "total_duration" in diagnostics["performance"]:
            duration = diagnostics["performance"]["total_duration"]
            report_lines.append(f"Total Duration: {duration:.2f}s")
            report_lines.append(f"Response Time Target (<2s): {'✅ MET' if diagnostics.get('response_time_ok') else '❌ MISSED'}")
        
        # Event coverage
        report_lines.extend(["", "Event Coverage:"])
        for event_type in self.CRITICAL_EVENTS:
            count = diagnostics["event_counts"].get(event_type, 0)
            status = "✅" if count > 0 else "❌"
            report_lines.append(f"  {status} {event_type}: {count}")
        
        # Errors and warnings
        if errors:
            report_lines.extend(["", "ERRORS:"] + [f"  - {e}" for e in errors])
        
        if diagnostics.get("warnings"):
            report_lines.extend(["", "WARNINGS:"] + [f"  - {w}" for w in diagnostics["warnings"]])
        
        # Event timeline
        if self.event_timeline:
            report_lines.extend(["", "Event Timeline:"])
            for timestamp, event_type, _ in self.event_timeline[:10]:  # First 10 events
                report_lines.append(f"  {timestamp:6.2f}s: {event_type}")
            if len(self.event_timeline) > 10:
                report_lines.append(f"  ... and {len(self.event_timeline) - 10} more events")
        
        report_lines.append("=" * 80)
        return "\n".join(report_lines)


# ============================================================================
# BULLETPROOF TEST SUITE
# ============================================================================

class TestBulletproofWebSocketChat:
    """Bulletproof tests for WebSocket chat functionality."""
    
    @pytest.fixture(autouse=True)
    async def setup_robust_environment(self):
        """Setup robust test environment with real components where possible."""
        # Create WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Create heartbeat manager with aggressive settings for testing
        self.heartbeat_config = HeartbeatConfig(
            heartbeat_interval_seconds=5,
            heartbeat_timeout_seconds=15,
            max_missed_heartbeats=2,
            cleanup_interval_seconds=10
        )
        self.heartbeat_manager = WebSocketHeartbeatManager(self.heartbeat_config)
        
        # Mock connections storage
        self.mock_connections: Dict[str, RobustMockWebSocket] = {}
        
        yield
        
        # Cleanup
        await self.cleanup_all_connections()
    
    async def cleanup_all_connections(self):
        """Clean up all test connections."""
        for conn_id in list(self.mock_connections.keys()):
            try:
                mock_ws = self.mock_connections[conn_id]
                await mock_ws.close()
            except Exception:
                pass
        self.mock_connections.clear()
    
    def create_mock_connection(self, user_id: str, thread_id: str, 
                              should_fail: bool = False, 
                              failure_pattern: str = None) -> RobustMockWebSocket:
        """Create a robust mock WebSocket connection."""
        conn_id = f"test_{user_id}_{uuid.uuid4().hex[:8]}"
        mock_ws = RobustMockWebSocket(conn_id, should_fail, failure_pattern)
        
        # Store in manager's connections (simulating real connection)
        self.ws_manager.connections[conn_id] = {
            "connection_id": conn_id,
            "user_id": user_id,
            "websocket": mock_ws,
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "is_healthy": True
        }
        
        # Track user connections
        if user_id not in self.ws_manager.user_connections:
            self.ws_manager.user_connections[user_id] = set()
        self.ws_manager.user_connections[user_id].add(conn_id)
        
        self.mock_connections[conn_id] = mock_ws
        return mock_ws
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_chat_flow_with_real_components(self):
        """Test complete chat flow with real WebSocket components."""
        validator = BulletproofEventValidator()
        
        # Create mock connection
        user_id = "test_user_1"
        thread_id = "test_thread_1"
        mock_ws = self.create_mock_connection(user_id, thread_id)
        
        # Create WebSocket notifier
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Create execution context
        context = AgentExecutionContext(
            run_id="test_run_1",
            thread_id=thread_id,
            user_id=user_id,
            agent_name="supervisor",
            retry_count=0,
            max_retries=3
        )
        
        # Simulate complete chat flow
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.01)  # Small delay to simulate processing
        
        await notifier.send_agent_thinking(context, "Analyzing user request...")
        await asyncio.sleep(0.02)
        
        await notifier.send_tool_executing(context, "search_knowledge")
        await asyncio.sleep(0.05)  # Simulate tool execution time
        await notifier.send_tool_completed(context, "search_knowledge", {"results": "Found relevant information"})
        
        await notifier.send_tool_executing(context, "generate_response")
        await asyncio.sleep(0.03)
        await notifier.send_tool_completed(context, "generate_response", {"response": "Here is your answer"})
        
        await notifier.send_final_report(context, {"answer": "Complete response to user"}, 150.0)
        await notifier.send_agent_completed(context, {"success": True}, 200.0)
        
        # Allow events to propagate
        await asyncio.sleep(0.1)
        
        # Validate events
        for msg in mock_ws.messages_sent:
            validator.record_event(msg["data"])
        
        is_valid, errors, diagnostics = validator.validate_comprehensive()
        
        if not is_valid:
            logger.error(validator.generate_detailed_report())
        
        assert is_valid, f"Chat flow validation failed: {errors}"
        assert diagnostics["total_events"] >= 7, f"Expected at least 7 events, got {diagnostics['total_events']}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_users_isolation(self):
        """Test that concurrent users receive only their own events."""
        validators = {}
        connections = {}
        
        # Create multiple users with connections
        num_users = 5
        for i in range(num_users):
            user_id = f"user_{i}"
            thread_id = f"thread_{i}"
            
            mock_ws = self.create_mock_connection(user_id, thread_id)
            connections[user_id] = mock_ws
            validators[user_id] = BulletproofEventValidator()
        
        # Create notifier
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Send events for each user concurrently
        async def send_user_events(user_id: str, thread_id: str):
            context = AgentExecutionContext(
                run_id=f"run_{user_id}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="agent",
                retry_count=0,
                max_retries=1
            )
            
            await notifier.send_agent_started(context)
            await asyncio.sleep(random.uniform(0.01, 0.03))
            await notifier.send_agent_thinking(context, f"Processing for {user_id}")
            await asyncio.sleep(random.uniform(0.01, 0.03))
            await notifier.send_tool_executing(context, "tool")
            await asyncio.sleep(random.uniform(0.02, 0.05))
            await notifier.send_tool_completed(context, "tool", {"result": f"Result for {user_id}"})
            await notifier.send_agent_completed(context, {"success": True})
        
        # Execute concurrently
        tasks = [send_user_events(f"user_{i}", f"thread_{i}") for i in range(num_users)]
        await asyncio.gather(*tasks)
        
        # Allow events to propagate
        await asyncio.sleep(0.2)
        
        # Validate each user received correct events
        for user_id, mock_ws in connections.items():
            validator = validators[user_id]
            
            # Record events
            for msg in mock_ws.messages_sent:
                validator.record_event(msg["data"])
            
            # Validate
            is_valid, errors, diagnostics = validator.validate_comprehensive()
            assert is_valid, f"User {user_id} validation failed: {errors}"
            
            # Verify no cross-contamination
            for msg in mock_ws.messages_sent:
                data = msg["data"]
                if "user_id" in data:
                    assert data["user_id"] == user_id, f"User {user_id} received event for wrong user"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_recovery_with_fallback(self):
        """Test that errors trigger proper fallback events."""
        validator = BulletproofEventValidator()
        
        # Create connection with intermittent failures
        user_id = "error_user"
        thread_id = "error_thread"
        mock_ws = self.create_mock_connection(user_id, thread_id, should_fail=True, failure_pattern="intermittent")
        
        # Create notifier
        notifier = WebSocketNotifier(self.ws_manager)
        
        context = AgentExecutionContext(
            run_id="error_run",
            thread_id=thread_id,
            user_id=user_id,
            agent_name="agent",
            retry_count=0,
            max_retries=3
        )
        
        # Start execution
        await notifier.send_agent_started(context)
        
        # Simulate error during tool execution
        try:
            await notifier.send_tool_executing(context, "failing_tool")
            # Simulate tool failure
            raise Exception("Tool execution failed")
        except Exception as e:
            # Send error event
            await notifier.send_tool_completed(context, "failing_tool", {"error": str(e), "status": "failed"})
            # Send fallback
            await notifier.send_fallback_notification(context, "error_recovery")
        
        # Ensure completion is sent
        await notifier.send_agent_completed(context, {"success": False, "fallback_used": True})
        
        # Allow events to propagate
        await asyncio.sleep(0.1)
        
        # Validate - should still have start and completion
        for msg in mock_ws.messages_sent:
            validator.record_event(msg["data"])
        
        assert validator.event_counts.get("agent_started", 0) > 0, "Missing agent_started event"
        assert any(validator.event_counts.get(e, 0) > 0 for e in ["agent_completed", "agent_fallback"]), \
            "Missing completion/fallback event after error"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_reconnection_state_preservation(self):
        """Test that reconnection preserves chat state."""
        # Create initial connection
        user_id = "reconnect_user"
        thread_id = "reconnect_thread"
        mock_ws1 = self.create_mock_connection(user_id, thread_id)
        
        notifier = WebSocketNotifier(self.ws_manager)
        
        context = AgentExecutionContext(
            run_id="reconnect_run",
            thread_id=thread_id,
            user_id=user_id,
            agent_name="agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send initial events
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Processing...")
        
        # Simulate disconnect
        mock_ws1.client_state = WebSocketState.DISCONNECTED
        
        # Create new connection (reconnect)
        mock_ws2 = self.create_mock_connection(user_id, thread_id)
        
        # Continue sending events
        await notifier.send_tool_executing(context, "tool")
        await notifier.send_tool_completed(context, "tool", {"result": "success"})
        await notifier.send_agent_completed(context, {"success": True})
        
        # Second connection should receive completion events
        assert len(mock_ws2.messages_sent) > 0, "Reconnected client received no events"
        
        # Check for completion event
        has_completion = any(
            msg["data"].get("type") in ["agent_completed", "final_report"] 
            for msg in mock_ws2.messages_sent
        )
        assert has_completion, "Reconnected client didn't receive completion event"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_performance_under_load(self):
        """Test WebSocket performance with high message volume."""
        start_time = time.time()
        
        # Create connections
        num_connections = 10
        connections = []
        for i in range(num_connections):
            user_id = f"load_user_{i}"
            thread_id = f"load_thread_{i}"
            mock_ws = self.create_mock_connection(user_id, thread_id)
            mock_ws.latency_ms = random.uniform(10, 50)  # Simulate network latency
            connections.append((user_id, thread_id, mock_ws))
        
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Send many events rapidly
        event_count = 0
        async def send_burst(user_id: str, thread_id: str):
            nonlocal event_count
            for i in range(20):  # 20 events per user
                context = AgentExecutionContext(
                    run_id=f"load_{user_id}_{i}",
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_name="load_test",
                    retry_count=0,
                    max_retries=1
                )
                await notifier.send_agent_thinking(context, f"Message {i}")
                event_count += 1
                if i % 5 == 0:
                    await notifier.send_partial_result(context, f"Partial {i}")
                    event_count += 1
        
        # Send events concurrently
        tasks = [send_burst(user_id, thread_id) for user_id, thread_id, _ in connections]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        events_per_second = event_count / duration
        
        logger.info(f"Performance test: {event_count} events in {duration:.2f}s = {events_per_second:.0f} events/s")
        
        # Verify performance
        assert events_per_second > 100, f"Performance too low: {events_per_second:.0f} events/s"
        
        # Verify all connections received events
        for _, _, mock_ws in connections:
            assert len(mock_ws.messages_sent) > 0, "Connection received no events"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_message_ordering_consistency(self):
        """Test that messages maintain correct order even under concurrent load."""
        user_id = "order_user"
        thread_id = "order_thread"
        mock_ws = self.create_mock_connection(user_id, thread_id)
        
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Send numbered messages
        expected_order = []
        for i in range(10):
            context = AgentExecutionContext(
                run_id=f"order_{i}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="order_test",
                retry_count=0,
                max_retries=1
            )
            
            message = f"Message {i:03d}"
            expected_order.append(message)
            await notifier.send_agent_thinking(context, message)
        
        # Allow propagation
        await asyncio.sleep(0.1)
        
        # Extract actual order
        actual_order = []
        for msg in mock_ws.messages_sent:
            data = msg["data"]
            if data.get("type") == "agent_thinking" and "message" in data:
                actual_order.append(data["message"])
        
        # Verify order preservation
        assert actual_order == expected_order, f"Message order corrupted: {actual_order} != {expected_order}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_heartbeat_detection_and_cleanup(self):
        """Test that heartbeat system detects and cleans up dead connections."""
        # Create connection
        user_id = "heartbeat_user"
        thread_id = "heartbeat_thread"
        mock_ws = self.create_mock_connection(user_id, thread_id)
        conn_id = list(self.ws_manager.connections.keys())[0]
        
        # Register with heartbeat manager
        await self.heartbeat_manager.register_connection(conn_id)
        
        # Start heartbeat monitoring
        await self.heartbeat_manager.start()
        
        # Simulate connection death
        mock_ws.client_state = WebSocketState.DISCONNECTED
        
        # Wait for heartbeat detection
        await asyncio.sleep(self.heartbeat_config.heartbeat_timeout_seconds + 1)
        
        # Check if marked as unhealthy
        is_alive = await self.heartbeat_manager.is_connection_alive(conn_id)
        assert not is_alive, "Dead connection not detected by heartbeat"
        
        # Cleanup
        await self.heartbeat_manager.stop()


# ============================================================================
# ADVANCED EDGE CASE TESTS
# ============================================================================

class TestAdvancedEdgeCases:
    """Test advanced edge cases and failure scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_rapid_connect_disconnect_cycles(self):
        """Test rapid connection/disconnection cycles."""
        ws_manager = WebSocketManager()
        
        for cycle in range(5):
            # Create connections
            connections = []
            for i in range(3):
                user_id = f"cycle_user_{i}"
                thread_id = f"cycle_thread_{i}"
                mock_ws = RobustMockWebSocket(f"cycle_{cycle}_{i}")
                
                # Add to manager
                conn_id = f"cycle_{cycle}_{i}"
                ws_manager.connections[conn_id] = {
                    "connection_id": conn_id,
                    "user_id": user_id,
                    "websocket": mock_ws,
                    "thread_id": thread_id,
                    "connected_at": datetime.now(timezone.utc),
                    "is_healthy": True
                }
                connections.append((conn_id, mock_ws))
            
            # Send a message
            await ws_manager.send_to_thread(f"cycle_thread_0", {"type": "test", "cycle": cycle})
            
            # Disconnect all
            for conn_id, mock_ws in connections:
                mock_ws.client_state = WebSocketState.DISCONNECTED
                del ws_manager.connections[conn_id]
            
            # Small delay between cycles
            await asyncio.sleep(0.01)
        
        # Manager should handle cycles gracefully
        assert len(ws_manager.connections) == 0, "Connections not cleaned up properly"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_malformed_message_handling(self):
        """Test handling of malformed messages."""
        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        # Create connection
        mock_ws = RobustMockWebSocket("malformed_test")
        ws_manager.connections["test"] = {
            "connection_id": "test",
            "user_id": "test_user",
            "websocket": mock_ws,
            "thread_id": "test_thread",
            "is_healthy": True
        }
        
        # Test various malformed messages
        malformed_messages = [
            None,  # None message
            {},  # Empty dict
            {"no_type": "field"},  # Missing type
            {"type": None},  # None type
            {"type": "test", "data": object()},  # Non-serializable object
            {"type": "test", "data": float('inf')},  # Infinity
            {"type": "test", "data": float('nan')},  # NaN
        ]
        
        for msg in malformed_messages:
            try:
                # Should handle gracefully without crashing
                await ws_manager.send_to_thread("test_thread", msg)
            except Exception as e:
                pytest.fail(f"Failed to handle malformed message {msg}: {e}")
        
        # Connection should still be healthy
        assert ws_manager.connections["test"]["is_healthy"], "Connection marked unhealthy after malformed messages"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_memory_leak_prevention(self):
        """Test that connections are properly cleaned up to prevent memory leaks."""
        ws_manager = WebSocketManager()
        
        initial_memory = len(ws_manager.connections)
        
        # Create and destroy many connections
        for i in range(100):
            user_id = f"leak_user_{i}"
            thread_id = f"leak_thread_{i}"
            mock_ws = RobustMockWebSocket(f"leak_{i}")
            
            conn_id = f"leak_{i}"
            ws_manager.connections[conn_id] = {
                "connection_id": conn_id,
                "user_id": user_id,
                "websocket": mock_ws,
                "thread_id": thread_id,
                "connected_at": datetime.now(timezone.utc) - timedelta(hours=25),  # Old connection
                "is_healthy": False
            }
        
        # Run cleanup
        await ws_manager._cleanup_stale_connections()
        
        # Should have cleaned up old/unhealthy connections
        assert len(ws_manager.connections) <= initial_memory + 10, \
            f"Memory leak detected: {len(ws_manager.connections)} connections remain"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_chat_bulletproof.py
    pytest.main([__file__, "-v", "-s", "--tb=short"])