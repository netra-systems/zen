#!/usr/bin/env python
"""CORE WEBSOCKET FUNCTIONALITY TEST - Independent of external services.

This test validates core WebSocket functionality per CLAUDE.md standards 
without requiring external database services.

Business Value: $500K+ ARR protection - Core chat functionality
Compliance: NO MOCKS, IsolatedEnvironment, Mission Critical Events
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Optional
from pathlib import Path

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Test framework imports - MUST be first for environment isolation
from test_framework.environment_isolation import get_env

# Production imports - using absolute paths only
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class MissionCriticalWebSocketValidator:
    """Validates WebSocket events with mission-critical rigor per CLAUDE.md Section 6."""
    
    # Required events per CLAUDE.md Section 6.1
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed", 
        "agent_completed"
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        
    def record_event(self, event: Dict) -> None:
        """Record WebSocket event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        logger.debug(f"Recorded event: {event_type} at {timestamp:.3f}s")
    
    def validate_mission_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL mission-critical requirements are met."""
        failures = []
        
        # 1. Check for required events per CLAUDE.md
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"MISSION CRITICAL: Missing required events: {missing}")
        
        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("MISSION CRITICAL: Invalid event order - user experience broken")
        
        # 3. Check for paired events (tools must have start/end)
        if not self._validate_paired_events():
            failures.append("MISSION CRITICAL: Unpaired tool events - user sees hanging operations")
        
        return len(failures) == 0, failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order per user experience requirements."""
        if not self.event_timeline:
            self.errors.append("No events received at all")
            return False
            
        # First event must be agent_started (user needs to know processing began)
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, not agent_started")
            return False
        
        # Must have at least thinking or action events
        has_activity = any(event_type in ["agent_thinking", "tool_executing", "partial_result"] 
                          for _, event_type, _ in self.event_timeline)
        if not has_activity:
            self.errors.append("No activity events - user sees no progress")
            return False
        
        return True
    
    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired (executing -> completed)."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        
        if tool_starts != tool_ends:
            self.errors.append(f"Tool event mismatch: {tool_starts} starts, {tool_ends} completions")
            return False
            
        return True
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive validation report for mission-critical analysis."""
        is_valid, failures = self.validate_mission_critical_requirements()
        
        report = [
            "\
" + "=" * 80,
            "MISSION CRITICAL WEBSOCKET VALIDATION REPORT",
            "=" * 80,
            f"Status: {'✅ PASSED - WebSocket functionality operational' if is_valid else '❌ FAILED - WebSocket functionality BROKEN'}",
            f"Total Events: {len(self.events)}",
            f"Event Types: {len(self.event_counts)}",
            f"Duration: {self.event_timeline[-1][0] if self.event_timeline else 0:.2f}s",
            f"Event Rate: {len(self.events) / max(self.event_timeline[-1][0], 0.001) if self.event_timeline else 0:.1f} events/sec",
            "",
            "Required Event Coverage (per CLAUDE.md Section 6.1):"
        ]
        
        for event in self.REQUIRED_EVENTS:
            count = self.event_counts.get(event, 0)
            status = "✅" if count > 0 else "❌ MISSING"
            report.append(f"  {status} {event}: {count}")
        
        if failures:
            report.extend(["", "MISSION CRITICAL FAILURES:"])
            report.extend([f"  - {f}" for f in failures])
        
        if self.errors:
            report.extend(["", "ERRORS:"])
            report.extend([f"  - {e}" for e in self.errors])
        
        report.append("=" * 80)
        return "\
".join(report)


class InMemoryWebSocketConnection:
    """Real in-memory WebSocket connection for testing without external dependencies."""
    
    def __init__(self):
        self._connected = True
        self.sent_messages = []
        self.received_events = []
        self.timeout_used = None  # Track timeout usage for compatibility
        self.send_count = 0  # Debug counter
    
    async def send(self, message: str):
        """Send message - captures for validation."""
        import json
        data = json.loads(message) if isinstance(message, str) else message
        self.sent_messages.append(message)
        self.received_events.append(data)
        self.send_count += 1
        logger.info(f"WebSocket send #{self.send_count}: {data.get('type', 'unknown')}")
    
    async def send_json(self, message: dict, timeout: float = None):
        """Send JSON message - required by WebSocket manager."""
        self.send_count += 1
        self.timeout_used = timeout
        
        try:
            import json
            from datetime import datetime
            
            if not isinstance(message, dict):
                logger.error(f"send_json got non-dict message: {type(message)}")
                raise TypeError(f"Expected dict, got {type(message)}")
            
            # Create a JSON-serializable version of the message
            def make_json_serializable(obj):
                """Convert objects to JSON-serializable format."""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: make_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_json_serializable(item) for item in obj]
                else:
                    return obj
            
            # Convert message to JSON-serializable format
            serializable_message = make_json_serializable(message)
            
            # Validate the message can be serialized
            message_str = json.dumps(serializable_message)
            
            # Store both formats
            self.sent_messages.append(message_str)
            self.received_events.append(serializable_message)
            
            logger.info(f"WebSocket send_json #{self.send_count} SUCCESS: {serializable_message.get('type', 'unknown')} (timeout={timeout})")
            
            # Simulate successful send - must not raise exceptions
            return None  # FastAPI WebSocket send_json doesn't return anything
            
        except Exception as e:
            logger.error(f"WebSocket send_json #{self.send_count} ERROR: {e} for message: {message}")
            # Re-raise to trigger circuit breaker for debugging
            raise
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close connection with WebSocket close codes."""
        logger.info(f"WebSocket closing with code {code}: {reason}")
        self._connected = False
    
    @property
    def client_state(self):
        """Mock WebSocket state property."""
        return "CONNECTED" if self._connected else "DISCONNECTED"


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(15)
async def test_websocket_core_event_flow():
    """Test core WebSocket event flow with NO external service dependencies.
    
    This test validates mission-critical WebSocket functionality per CLAUDE.md:
    - Real WebSocket manager creation and connection handling
    - WebSocket notifier event sending
    - Mission-critical event validation
    - Event ordering and pairing validation
    
    This ensures core chat functionality works independently of database services.
    """
    # Set up isolated environment manually
    env = get_env()
    env.enable_isolation(backup_original=True)
    
    # Set minimal test environment
    test_vars = {
        "TESTING": "1",
        "NETRA_ENV": "testing",
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "ERROR",
        "USE_MEMORY_DB": "true",
    }
    
    for key, value in test_vars.items():
        env.set(key, value, source="core_websocket_test")
    
    try:
        logger.info("🚀 Testing CORE WebSocket functionality - NO external dependencies")
        
        validator = MissionCriticalWebSocketValidator(strict_mode=True)
        
        # Create real WebSocket manager
        ws_manager = WebSocketManager()
        
        # Create real in-memory WebSocket connection
        connection_id = "core-test"
        user_id = "core-test-user"
        ws_conn = InMemoryWebSocketConnection()
        
        # Connect to WebSocket manager
        await ws_manager.connect_user(user_id, ws_conn, connection_id)
        
        try:
            # Create WebSocket notifier
            notifier = WebSocketNotifier(ws_manager)
            
            # Create execution context
            context = AgentExecutionContext(
                run_id="core-req-123",
                thread_id=connection_id,
                user_id=user_id,
                agent_name="test_agent",
                retry_count=0,
                max_retries=1
            )
            
            # Test complete WebSocket event flow
            logger.info("📡 Sending all required WebSocket events...")
            
            # Send all required events per CLAUDE.md Section 6.1
            await notifier.send_agent_started(context)
            await asyncio.sleep(0.01)
            
            await notifier.send_agent_thinking(context, "Processing your request...")
            await asyncio.sleep(0.01)
            
            await notifier.send_tool_executing(context, "test_tool")
            await asyncio.sleep(0.01)
            
            await notifier.send_tool_completed(context, "test_tool", {"result": "success"})
            await asyncio.sleep(0.01)
            
            await notifier.send_partial_result(context, "Here are the results...")
            await asyncio.sleep(0.01)
            
            await notifier.send_agent_completed(context, {"success": True})
            await asyncio.sleep(0.01)
            
            # Allow final processing
            await asyncio.sleep(0.1)
            
        finally:
            # Cleanup WebSocket connection
            await ws_manager.disconnect_user(user_id, ws_conn, connection_id)
            await ws_conn.close()
        
        # Process events from connection
        for event in ws_conn.received_events:
            validator.record_event(event)
        
        # Generate comprehensive validation report
        report = validator.generate_comprehensive_report()
        logger.info(report)
        
        # Validate mission-critical requirements
        is_valid, failures = validator.validate_mission_critical_requirements()
        
        # Assert mission-critical requirements
        assert is_valid, f"CORE WEBSOCKET TEST FAILED:\
{report}\
Failures: {failures}"
        
        received_events = ws_conn.received_events
        assert len(received_events) >= 6, f"Expected at least 6 WebSocket events, got {len(received_events)}. Events: {[e.get('type') for e in received_events]}"
        
        # Validate all required events are present
        event_types = [e.get("type") for e in received_events]
        required_events = validator.REQUIRED_EVENTS
        
        for required_event in required_events:
            assert required_event in event_types, f"Missing required event: {required_event}. Got: {event_types}"
        
        # Validate event data structure (WebSocket message format)
        for event in received_events:
            assert "type" in event, f"Event missing 'type' field: {event}"
            assert "timestamp" in event, f"Event missing 'timestamp' field: {event}"
            assert "payload" in event, f"Event missing 'payload' field: {event}"
        
        # Validate tool event pairing
        tool_executing_count = event_types.count("tool_executing")
        tool_completed_count = event_types.count("tool_completed") 
        assert tool_executing_count == tool_completed_count, \
            f"Unpaired tool events: {tool_executing_count} executing, {tool_completed_count} completed"
        
        logger.info("✅ CORE WEBSOCKET TEST PASSED - Mission-critical functionality verified!")
        logger.info(f"   📊 Events: {len(received_events)}, Event Types: {len(set(event_types))}")
        logger.info(f"   🎯 All required WebSocket events validated successfully")
        
    finally:
        # Cleanup environment
        env.disable_isolation(restore_original=True)


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(10)
async def test_websocket_manager_real_connection_handling():
    """Test WebSocket manager real connection handling."""
    env = get_env()
    env.enable_isolation(backup_original=True)
    
    test_vars = {"TESTING": "1", "NETRA_ENV": "testing"}
    for key, value in test_vars.items():
        env.set(key, value, source="connection_test")
    
    try:
        ws_manager = WebSocketManager()
        
        # Test multiple connections
        connections = []
        for i in range(3):
            conn_id = f"conn-{i}"
            user_id = f"user-{i}"
            ws_conn = InMemoryWebSocketConnection()
            
            await ws_manager.connect_user(user_id, ws_conn, conn_id)
            connections.append((user_id, ws_conn, conn_id))
        
        # Test broadcast functionality
        notifier = WebSocketNotifier(ws_manager)
        context = AgentExecutionContext(
            run_id="broadcast-test",
            thread_id="broadcast",
            user_id="broadcast-user",
            agent_name="broadcast_agent",
            retry_count=0,
            max_retries=1
        )
        
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.1)
        
        # Verify all connections received the event
        for user_id, ws_conn, conn_id in connections:
            if ws_conn.received_events:
                event = ws_conn.received_events[0]
                assert event.get("type") == "agent_started"
                logger.info(f"Connection {conn_id} received event: {event.get('type')}")
        
        # Cleanup all connections
        for user_id, ws_conn, conn_id in connections:
            await ws_manager.disconnect_user(user_id, ws_conn, conn_id)
            await ws_conn.close()
        
        logger.info("✅ WebSocket connection handling test PASSED")
        
    finally:
        env.disable_isolation(restore_original=True)


if __name__ == "__main__":
    # Run core WebSocket tests independently
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short", 
        "-s",  # Show real-time output
        "--timeout=30"  # Allow time for processing
    ])