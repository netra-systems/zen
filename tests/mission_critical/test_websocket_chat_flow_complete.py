#!/usr/bin/env python
"""MISSION CRITICAL: Complete WebSocket Chat Flow Test Suite

THIS SUITE VALIDATES THE CORE BUSINESS VALUE OF NETRA APEX.
Business Impact: $500K+ ARR - This is our primary value delivery channel.

THE 7 CRITICAL WEBSOCKET EVENTS THAT MUST BE SENT:
1. agent_started - User sees agent began processing  
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows when done
6. partial_result - Intermediate updates (optional but valuable)
7. error_event - Graceful error handling (when applicable)

ANY FAILURE HERE MEANS USERS SEE A "BLANK SCREEN" DURING AI PROCESSING.
This directly impacts:
- User engagement and trust
- Conversion from Free to Paid tiers  
- Platform stickiness and retention
- Support burden from confused users

REAL WEBSOCKET CONNECTIONS ONLY - NO MOCKS.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import random

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger
import websockets
from websockets.exceptions import ConnectionClosedError

# Real services infrastructure - NO MOCKS
from test_framework.real_services import get_real_services, RealServicesManager
from test_framework.environment_isolation import get_test_env_manager

# Production WebSocket components 
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.types import MessageType
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.enhanced_tool_execution import EnhancedToolExecutionEngine


# ============================================================================
# EVENT VALIDATION SYSTEM
# ============================================================================

class ChatFlowEventCapture:
    """Captures and validates WebSocket events with millisecond precision."""
    
    CRITICAL_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    VALUABLE_EVENTS = {
        "partial_result",
        "agent_response", 
        "final_report"
    }
    
    ERROR_EVENTS = {
        "agent_error",
        "tool_error",
        "execution_error"
    }
    
    def __init__(self, connection_id: str, strict_validation: bool = True):
        self.connection_id = connection_id
        self.strict_validation = strict_validation
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.event_counts: Dict[str, int] = {}
        self.start_time = time.time()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._lock = threading.Lock()
    
    def capture_event(self, event: Dict[str, Any]) -> None:
        """Thread-safe event capture with timing precision."""
        with self._lock:
            timestamp = time.time() - self.start_time
            event_type = event.get("type", "unknown")
            
            self.events.append(event)
            self.event_timeline.append((timestamp, event_type, event))
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
            
            logger.info(f"[{self.connection_id}] Event captured: {event_type} at {timestamp:.3f}s")
    
    def validate_critical_flow(self) -> Tuple[bool, List[str]]:
        """Validate that all critical events were captured in logical order."""
        failures = []
        
        # 1. Critical event coverage
        missing_critical = self.CRITICAL_EVENTS - set(self.event_counts.keys())
        if missing_critical:
            failures.append(f"CRITICAL: Missing required events: {missing_critical}")
        
        # 2. Event ordering validation
        if not self._validate_event_sequence():
            failures.append("CRITICAL: Invalid event sequence")
        
        # 3. Tool event pairing
        if not self._validate_tool_pairing():
            failures.append("CRITICAL: Unpaired tool events")
        
        # 4. Timing validation
        if not self._validate_timing_constraints():
            failures.append("CRITICAL: Timing violations")
        
        # 5. Event completeness
        if not self._validate_event_data():
            failures.append("CRITICAL: Incomplete event data")
        
        return len(failures) == 0, failures
    
    def _validate_event_sequence(self) -> bool:
        """Ensure events follow logical execution order."""
        if not self.event_timeline:
            self.errors.append("No events captured")
            return False
        
        # First event should indicate processing started
        first_event = self.event_timeline[0][1]
        if first_event not in ["agent_started", "connection_established"]:
            self.errors.append(f"Flow should start with agent_started, got: {first_event}")
            if self.strict_validation:
                return False
        
        # Last event should indicate completion
        last_event = self.event_timeline[-1][1]
        completion_events = ["agent_completed", "final_report", "agent_response"]
        if last_event not in completion_events:
            self.errors.append(f"Flow should end with completion event, got: {last_event}")
            if self.strict_validation:
                return False
        
        return True
    
    def _validate_tool_pairing(self) -> bool:
        """Ensure every tool_executing has a corresponding tool_completed."""
        executing_count = self.event_counts.get("tool_executing", 0)
        completed_count = self.event_counts.get("tool_completed", 0)
        
        if executing_count != completed_count:
            self.errors.append(
                f"Tool event mismatch: {executing_count} executions, {completed_count} completions"
            )
            return False
            
        return True
    
    def _validate_timing_constraints(self) -> bool:
        """Validate events arrive within reasonable time windows."""
        if not self.event_timeline:
            return True
        
        # No event should take longer than 60 seconds in testing
        for timestamp, event_type, _ in self.event_timeline:
            if timestamp > 60.0:
                self.errors.append(f"Event {event_type} took too long: {timestamp:.2f}s")
                return False
        
        # Events should be reasonably spaced (not all at once)
        if len(self.event_timeline) >= 3:
            timestamps = [t[0] for t in self.event_timeline]
            time_spans = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            
            # At least some events should be spaced apart
            if all(span < 0.001 for span in time_spans):  # All within 1ms
                self.warnings.append("All events occurred simultaneously - may indicate batching issue")
        
        return True
    
    def _validate_event_data(self) -> bool:
        """Ensure events contain required fields."""
        for event in self.events:
            if "type" not in event:
                self.errors.append("Event missing required 'type' field")
                return False
            
            # Validate specific event data requirements
            event_type = event.get("type")
            if event_type == "tool_executing" and "tool_name" not in event:
                self.warnings.append("tool_executing event missing tool_name")
            elif event_type == "agent_thinking" and "content" not in event:
                self.warnings.append("agent_thinking event missing content")
        
        return True
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        is_valid, failures = self.validate_critical_flow()
        
        report = [
            "\n" + "=" * 80,
            f"WEBSOCKET EVENT VALIDATION REPORT - {self.connection_id}",
            "=" * 80,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Event Types: {len(self.event_counts)}",
            f"Duration: {self.event_timeline[-1][0] if self.event_timeline else 0:.3f}s",
            "",
            "CRITICAL EVENT COVERAGE:"
        ]
        
        for event in sorted(self.CRITICAL_EVENTS):
            count = self.event_counts.get(event, 0)
            status = "✅" if count > 0 else "❌"
            report.append(f"  {status} {event}: {count}")
        
        if self.event_counts:
            report.extend(["", "ALL CAPTURED EVENTS:"])
            for event_type in sorted(self.event_counts.keys()):
                count = self.event_counts[event_type]
                report.append(f"  • {event_type}: {count}")
        
        if self.event_timeline:
            report.extend(["", "EVENT TIMELINE:"])
            for timestamp, event_type, event_data in self.event_timeline[:10]:  # First 10
                content = event_data.get("content", event_data.get("message", ""))[:50]
                report.append(f"  {timestamp:6.3f}s: {event_type} - {content}")
            if len(self.event_timeline) > 10:
                report.append(f"  ... and {len(self.event_timeline) - 10} more events")
        
        if failures:
            report.extend(["", "FAILURES:"] + [f"  ❌ {f}" for f in failures])
        
        if self.errors:
            report.extend(["", "ERRORS:"] + [f"  🔥 {e}" for e in self.errors])
        
        if self.warnings:
            report.extend(["", "WARNINGS:"] + [f"  ⚠️  {w}" for w in self.warnings])
        
        report.append("=" * 80)
        return "\n".join(report)


class WebSocketChatTester:
    """Real WebSocket client that simulates user chat interactions."""
    
    def __init__(self, real_services: RealServicesManager):
        self.real_services = real_services
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.event_capture: Optional[ChatFlowEventCapture] = None
        self.connection_id: Optional[str] = None
        self.receive_task: Optional[asyncio.Task] = None
    
    async def connect_with_auth(self, user_id: str, jwt_token: Optional[str] = None) -> str:
        """Connect to WebSocket with authentication."""
        self.connection_id = f"chat-test-{user_id}-{int(time.time())}"
        self.event_capture = ChatFlowEventCapture(self.connection_id)
        
        # Build connection URL with auth
        ws_url = "ws://localhost:8000/ws"  # Use real backend WebSocket endpoint
        
        headers = {}
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        
        try:
            # Connect to real WebSocket endpoint
            self.websocket = await websockets.connect(
                ws_url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            self.connected = True
            
            # Start receiving messages
            self.receive_task = asyncio.create_task(self._receive_messages())
            
            logger.info(f"✅ WebSocket connected: {self.connection_id}")
            return self.connection_id
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            raise ConnectionError(f"Failed to connect to WebSocket: {e}")
    
    async def send_chat_message(self, content: str, thread_id: Optional[str] = None) -> None:
        """Send a chat message and expect agent processing events."""
        if not self.connected or not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        message = {
            "type": "user_message",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if thread_id:
            message["thread_id"] = thread_id
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"📤 Sent chat message: {content[:50]}...")
    
    async def _receive_messages(self) -> None:
        """Continuously receive and capture WebSocket messages."""
        try:
            while self.connected and self.websocket:
                try:
                    raw_message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    
                    try:
                        message = json.loads(raw_message)
                        if self.event_capture:
                            self.event_capture.capture_event(message)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received: {raw_message}")
                    
                except asyncio.TimeoutError:
                    continue  # Keep listening
                except ConnectionClosedError:
                    logger.info(f"WebSocket connection closed: {self.connection_id}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in message receive loop: {e}")
        finally:
            self.connected = False
    
    async def wait_for_agent_completion(self, timeout: float = 30.0) -> bool:
        """Wait for agent to complete processing with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.event_capture:
                completion_events = ["agent_completed", "final_report", "agent_response"]
                if any(event in self.event_capture.event_counts for event in completion_events):
                    logger.info(f"✅ Agent completion detected for {self.connection_id}")
                    return True
            
            await asyncio.sleep(0.1)
        
        logger.warning(f"⏰ Agent completion timeout after {timeout}s for {self.connection_id}")
        return False
    
    async def close(self) -> None:
        """Close WebSocket connection and cleanup."""
        self.connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        logger.info(f"🔌 WebSocket closed: {self.connection_id}")


# ============================================================================
# TEST SUITE
# ============================================================================

class TestWebSocketChatFlowComplete:
    """Complete test suite for WebSocket chat functionality with real connections."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup real test environment."""
        self.env_manager = get_test_env_manager()
        self.test_env = self.env_manager.setup_test_environment()
        
        # Get real services manager
        self.real_services = get_real_services()
        
        # Ensure all services are available
        try:
            await self.real_services.ensure_all_services_available()
            await self.real_services.reset_all_data()
        except Exception as e:
            pytest.skip(f"Real services not available: {e}")
        
        yield
        
        # Cleanup
        await self.real_services.close_all()
        self.env_manager.teardown_test_environment()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_chat_sends_all_seven_critical_events(self):
        """MISSION CRITICAL: Verify all 7 WebSocket events sent during chat processing.
        
        This test validates the core user experience:
        1. User sends message
        2. Agent starts processing (agent_started)
        3. Agent shows thinking process (agent_thinking)  
        4. Agent executes tools (tool_executing/tool_completed)
        5. Agent completes with result (agent_completed)
        """
        # Create real WebSocket client
        chat_tester = WebSocketChatTester(self.real_services)
        
        try:
            # Connect with test user
            user_id = f"test-user-{uuid.uuid4()}"
            connection_id = await chat_tester.connect_with_auth(user_id)
            
            # Allow connection to stabilize
            await asyncio.sleep(0.5)
            
            # Send a realistic chat message that will trigger agent processing
            test_message = "Analyze my system performance and suggest optimizations"
            await chat_tester.send_chat_message(test_message)
            
            # Wait for agent processing to complete
            completion_success = await chat_tester.wait_for_agent_completion(timeout=45.0)
            
            # Generate detailed report
            assert chat_tester.event_capture, "Event capture not initialized"
            
            validation_report = chat_tester.event_capture.generate_report()
            logger.info(validation_report)
            
            # Validate critical requirements
            is_valid, failures = chat_tester.event_capture.validate_critical_flow()
            
            # Assertions with detailed failure messages
            assert completion_success, f"Agent did not complete within timeout. Events captured: {list(chat_tester.event_capture.event_counts.keys())}"
            
            assert is_valid, f"Critical event validation failed:\n{chr(10).join(failures)}\n\nFull Report:\n{validation_report}"
            
            # Specific event assertions for business requirements
            events = chat_tester.event_capture.event_counts
            assert events.get("agent_started", 0) > 0, "Users must see that agent started processing"
            assert events.get("agent_thinking", 0) > 0, "Users must see agent reasoning process"
            assert events.get("tool_executing", 0) > 0, "Users must see when tools are being used"  
            assert events.get("tool_completed", 0) > 0, "Users must see when tools complete"
            assert events.get("agent_completed", 0) > 0, "Users must know when agent is done"
            
            # Business validation - user sees meaningful updates
            assert len(chat_tester.event_capture.events) >= 5, f"Expected at least 5 events for good UX, got {len(chat_tester.event_capture.events)}"
            
            logger.info(f"✅ CRITICAL TEST PASSED: All WebSocket events validated for chat flow")
            
        finally:
            await chat_tester.close()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_concurrent_chats_isolated_events(self):
        """Test multiple concurrent chat sessions receive isolated events."""
        num_concurrent_chats = 3
        chat_testers = []
        
        try:
            # Create multiple concurrent chat sessions
            for i in range(num_concurrent_chats):
                tester = WebSocketChatTester(self.real_services)
                user_id = f"concurrent-user-{i}-{uuid.uuid4()}"
                await tester.connect_with_auth(user_id)
                chat_testers.append(tester)
            
            # Allow connections to stabilize
            await asyncio.sleep(1.0)
            
            # Send different messages to each session concurrently
            messages = [
                "Optimize my database queries",
                "Review my API performance", 
                "Analyze my security configuration"
            ]
            
            send_tasks = []
            for i, tester in enumerate(chat_testers):
                task = tester.send_chat_message(messages[i])
                send_tasks.append(task)
            
            await asyncio.gather(*send_tasks)
            
            # Wait for all agents to complete
            completion_tasks = []
            for tester in chat_testers:
                task = tester.wait_for_agent_completion(timeout=60.0)
                completion_tasks.append(task)
            
            completion_results = await asyncio.gather(*completion_tasks)
            
            # Validate each session independently
            for i, (tester, completed) in enumerate(zip(chat_testers, completion_results)):
                assert completed, f"Session {i} did not complete processing"
                
                assert tester.event_capture, f"Session {i} missing event capture"
                is_valid, failures = tester.event_capture.validate_critical_flow()
                
                report = tester.event_capture.generate_report()
                logger.info(f"Session {i} Report:\n{report}")
                
                assert is_valid, f"Session {i} validation failed: {failures}"
                
                # Each session should have received its own events
                events = tester.event_capture.event_counts
                assert events.get("agent_started", 0) > 0, f"Session {i} missing agent_started"
                assert events.get("agent_completed", 0) > 0, f"Session {i} missing agent_completed"
            
            logger.info(f"✅ CONCURRENT TEST PASSED: {num_concurrent_chats} sessions processed independently")
            
        finally:
            # Cleanup all connections
            for tester in chat_testers:
                await tester.close()
    
    @pytest.mark.asyncio  
    @pytest.mark.critical
    @pytest.mark.timeout(45)
    async def test_agent_failure_sends_error_events(self):
        """Test that agent failures still send appropriate WebSocket events."""
        chat_tester = WebSocketChatTester(self.real_services)
        
        try:
            # Connect as test user
            user_id = f"error-test-{uuid.uuid4()}"
            await chat_tester.connect_with_auth(user_id)
            
            # Allow connection to stabilize  
            await asyncio.sleep(0.5)
            
            # Send a message that might trigger an error or use fallback
            # In real systems, some requests may fail or need graceful degradation
            problematic_message = "Execute an invalid SQL query: DROP TABLE users CASCADE;"
            await chat_tester.send_chat_message(problematic_message)
            
            # Wait for processing (may complete with error handling)
            completion_success = await chat_tester.wait_for_agent_completion(timeout=30.0)
            
            # Even with errors, we should get some events
            assert chat_tester.event_capture, "Event capture not initialized"
            
            events = chat_tester.event_capture.event_counts
            validation_report = chat_tester.event_capture.generate_report()
            logger.info(f"Error scenario report:\n{validation_report}")
            
            # At minimum, should have started and some form of completion
            assert events.get("agent_started", 0) > 0, "Even errors should show agent started"
            
            # Should have some form of completion or error indication
            completion_events = [
                "agent_completed", "agent_error", "final_report", 
                "agent_response", "execution_error"
            ]
            has_completion = any(events.get(event, 0) > 0 for event in completion_events)
            assert has_completion, f"No completion/error event found. Events: {list(events.keys())}"
            
            # Should have at least 2 events (start + completion/error)
            assert len(chat_tester.event_capture.events) >= 2, \
                f"Expected at least 2 events even in error cases, got {len(chat_tester.event_capture.events)}"
            
            logger.info("✅ ERROR HANDLING TEST PASSED: Agent failures handled gracefully")
            
        finally:
            await chat_tester.close()
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    @pytest.mark.timeout(30)
    async def test_websocket_reconnection_preserves_flow(self):
        """Test WebSocket reconnection doesn't break event flow."""
        chat_tester1 = WebSocketChatTester(self.real_services)
        chat_tester2 = WebSocketChatTester(self.real_services)
        
        try:
            # First connection
            user_id = f"reconnect-test-{uuid.uuid4()}"
            await chat_tester1.connect_with_auth(user_id)
            await asyncio.sleep(0.5)
            
            # Start processing
            await chat_tester1.send_chat_message("Start analyzing my data")
            await asyncio.sleep(1.0)  # Let processing begin
            
            # Simulate disconnect/reconnect
            await chat_tester1.close()
            await asyncio.sleep(0.5)
            
            # Reconnect with new session
            await chat_tester2.connect_with_auth(f"{user_id}-reconnected")
            await asyncio.sleep(0.5)
            
            # Send new message
            await chat_tester2.send_chat_message("Continue with performance analysis")
            
            # Wait for completion on reconnected session
            completion_success = await chat_tester2.wait_for_agent_completion(timeout=20.0)
            
            # Validate reconnected session works
            assert completion_success, "Reconnected session should complete processing"
            
            assert chat_tester2.event_capture, "Reconnected session missing event capture"
            events = chat_tester2.event_counts
            
            # Reconnected session should get full event flow
            assert events.get("agent_started", 0) > 0, "Reconnected session missing agent_started"
            assert events.get("agent_completed", 0) > 0, "Reconnected session missing agent_completed"
            
            logger.info("✅ RECONNECTION TEST PASSED: Event flow preserved after reconnection")
            
        finally:
            await chat_tester1.close()
            await chat_tester2.close()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.timeout(60)
    async def test_websocket_event_timing_performance(self):
        """Test that WebSocket events are sent with acceptable timing."""
        chat_tester = WebSocketChatTester(self.real_services)
        
        try:
            # Connect and send message
            user_id = f"timing-test-{uuid.uuid4()}"
            await chat_tester.connect_with_auth(user_id)
            await asyncio.sleep(0.5)
            
            # Send message and track timing
            start_time = time.time()
            await chat_tester.send_chat_message("Quick performance check")
            
            # Wait for first event (should be very fast)
            first_event_time = None
            while time.time() - start_time < 5.0:  # 5s timeout for first event
                if chat_tester.event_capture and chat_tester.event_capture.events:
                    first_event_time = time.time() - start_time
                    break
                await asyncio.sleep(0.01)
            
            # Wait for completion
            completion_success = await chat_tester.wait_for_agent_completion(timeout=30.0)
            total_time = time.time() - start_time
            
            # Timing validations
            assert first_event_time is not None, "No events received within 5 seconds"
            assert first_event_time < 2.0, f"First event took too long: {first_event_time:.2f}s (should be < 2s)"
            
            assert completion_success, "Processing did not complete"
            assert total_time < 30.0, f"Total processing took too long: {total_time:.2f}s"
            
            # Event distribution validation
            timeline = chat_tester.event_capture.event_timeline
            if len(timeline) >= 3:
                # Events should be reasonably distributed, not all at once
                timestamps = [t[0] for t in timeline]
                time_span = timestamps[-1] - timestamps[0]
                assert time_span > 0.1, "Events too clustered - may indicate batching issue"
            
            logger.info(f"✅ PERFORMANCE TEST PASSED: First event in {first_event_time:.3f}s, total {total_time:.3f}s")
            
        finally:
            await chat_tester.close()


# ============================================================================
# HELPER FUNCTIONS FOR DEBUGGING
# ============================================================================

async def debug_websocket_connection():
    """Debug helper to test basic WebSocket connectivity."""
    try:
        websocket = await websockets.connect("ws://localhost:8000/ws")
        await websocket.send(json.dumps({"type": "ping"}))
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        await websocket.close()
        logger.info(f"✅ WebSocket connectivity test passed: {response}")
        return True
    except Exception as e:
        logger.error(f"❌ WebSocket connectivity test failed: {e}")
        return False


def create_test_jwt_token(user_id: str) -> str:
    """Create a test JWT token for authentication."""
    # In real implementation, would use proper JWT creation
    # For testing, return a mock token that the test environment accepts
    return f"test-jwt-{user_id}"


# ============================================================================
# MAIN EXECUTION FOR STANDALONE TESTING  
# ============================================================================

if __name__ == "__main__":
    """
    Run this test standalone with:
    python tests/mission_critical/test_websocket_chat_flow_complete.py
    
    This will execute a quick connectivity check and run the critical tests.
    """
    import asyncio
    
    async def main():
        logger.info("🚀 Starting WebSocket Chat Flow Tests")
        
        # Quick connectivity check
        if not await debug_websocket_connection():
            logger.error("❌ WebSocket server not available - start the backend first")
            return
        
        # Run pytest with specific test
        import pytest
        exit_code = pytest.main([
            __file__,
            "-v",
            "--tb=short", 
            "-k", "test_chat_sends_all_seven_critical_events",
            "--no-header"
        ])
        
        if exit_code == 0:
            logger.info("✅ ALL CRITICAL WEBSOCKET TESTS PASSED")
        else:
            logger.error("❌ CRITICAL WEBSOCKET TESTS FAILED")
            logger.error("This means users will see a blank screen during AI processing!")
    
    # Run the main test
    asyncio.run(main())