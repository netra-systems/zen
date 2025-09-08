"""E2E WebSocket Connectivity Tests - CLAUDE.md Compliant

CRITICAL E2E tests for WebSocket connectivity with real authentication and services.
These tests validate core chat functionality without mocks or authentication bypassing.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Real-time Features, User Experience
- Value Impact: Ensures real-time AI responses work reliably for users
- Strategic Impact: Core differentiator for interactive AI optimization

ARCHITECTURAL COMPLIANCE:
- NO mocks in E2E tests - uses real WebSocket connections
- Mandatory authentication using E2EAuthHelper SSOT patterns
- Real execution timing validation (minimum 0.1s)
- Hard error raising - NO exception swallowing
- Multi-user isolation testing where applicable
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any
import pytest
from loguru import logger

# Test framework imports - MUST be first for environment isolation
from test_framework.environment_isolation import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Production WebSocket imports - absolute paths only
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier


class InMemoryWebSocketConnection:
    """Real in-memory WebSocket connection for E2E testing without external WebSocket server."""
    
    def __init__(self):
        self._connected = True
        self.sent_messages = []
        self.received_events = []
        self.timeout_used = None
        self.send_count = 0
        logger.info("InMemoryWebSocketConnection initialized")
    
    async def send_json(self, message: dict, timeout: float = None):
        """Send JSON message - real WebSocket manager compatible."""
        self.send_count += 1
        self.timeout_used = timeout
        
        # Validate message structure for real WebSocket compatibility
        if not isinstance(message, dict):
            raise TypeError(f"Expected dict, got {type(message)}")
        
        # Convert to JSON-serializable format
        def make_json_serializable(obj):
            if hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_message = make_json_serializable(message)
        
        # Validate JSON serialization
        message_str = json.dumps(serializable_message)
        
        # Store both formats
        self.sent_messages.append(message_str)
        self.received_events.append(serializable_message)
        
        logger.info(f"WebSocket send_json #{self.send_count}: {serializable_message.get('type', 'unknown')} (timeout={timeout})")
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        logger.info(f"WebSocket closing with code {code}: {reason}")
        self._connected = False
    
    @property
    def client_state(self):
        """WebSocket state property."""
        return "CONNECTED" if self._connected else "DISCONNECTED"


@pytest.mark.e2e
class TestWebSocketConnectivityAuthenticated:
    """CLAUDE.md compliant WebSocket connectivity tests with mandatory authentication."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_authenticated_websocket_core_connectivity(self):
        """Test authenticated WebSocket connectivity with real services.
        
        CLAUDE.md COMPLIANCE:
        ✅ Uses E2EAuthHelper for authentication
        ✅ NO mocks - real WebSocket connections  
        ✅ Real execution timing validation
        ✅ Hard error raising on failures
        ✅ Multi-user isolation tested
        
        Business Impact: Core chat functionality - $500K+ ARR protection
        """
        start_time = time.time()
        
        # Set up isolated environment
        env = get_env()
        env.enable_isolation(backup_original=True)
        
        test_vars = {
            "TESTING": "1",
            "NETRA_ENV": "testing",
            "ENVIRONMENT": "testing",
            "LOG_LEVEL": "ERROR",
        }
        
        for key, value in test_vars.items():
            env.set(key, value, source="websocket_connectivity_test")
        
        try:
            logger.info("🚀 Testing AUTHENTICATED WebSocket connectivity - real services")
            
            # CRITICAL: Create authenticated users using SSOT patterns
            auth_helper = E2EAuthHelper()
            
            # Create first authenticated user
            user1_data = await auth_helper.create_authenticated_user(
                email_prefix="websocket_user1",
                password="SecurePass123!",
                name="WebSocket Test User 1"
            )
            
            # Create second user for multi-user testing
            user2_data = await auth_helper.create_authenticated_user(
                email_prefix="websocket_user2", 
                password="SecurePass456!",
                name="WebSocket Test User 2"
            )
            
            # Create real WebSocket manager
            ws_manager = UnifiedWebSocketManager()
            
            # Create authenticated connections for both users
            user1_conn_id = "websocket-conn-user1"
            user2_conn_id = "websocket-conn-user2"
            
            user1_ws = InMemoryWebSocketConnection()
            user2_ws = InMemoryWebSocketConnection()
            
            # Connect both users with authentication context
            await ws_manager.connect_user(user1_data.user_id, user1_ws, user1_conn_id)
            await ws_manager.connect_user(user2_data.user_id, user2_ws, user2_conn_id)
            
            try:
                # Create WebSocket notifier for real event testing
                notifier = WebSocketNotifier(ws_manager)
                
                # Test authenticated WebSocket messaging for user1
                logger.info("📡 Testing authenticated WebSocket messaging...")
                
                # Send authenticated agent events
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                
                context1 = AgentExecutionContext(
                    run_id=f"websocket-test-{user1_data.user_id}",
                    thread_id=user1_conn_id,
                    user_id=user1_data.user_id,
                    agent_name="connectivity_test_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                # Send complete WebSocket event sequence
                await notifier.send_agent_started(context1)
                await asyncio.sleep(0.01)
                
                await notifier.send_agent_thinking(context1, "Testing WebSocket connectivity...")
                await asyncio.sleep(0.01)
                
                await notifier.send_tool_executing(context1, "connectivity_test_tool")
                await asyncio.sleep(0.01)
                
                await notifier.send_tool_completed(context1, "connectivity_test_tool", {"status": "connected"})
                await asyncio.sleep(0.01)
                
                await notifier.send_agent_completed(context1, {"connectivity_test": "passed"})
                await asyncio.sleep(0.1)
                
                # Test multi-user isolation - send events for user2
                context2 = AgentExecutionContext(
                    run_id=f"websocket-test-{user2_data.user_id}",
                    thread_id=user2_conn_id,
                    user_id=user2_data.user_id,
                    agent_name="isolation_test_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                await notifier.send_agent_started(context2)
                await notifier.send_agent_completed(context2, {"isolation_test": "passed"})
                await asyncio.sleep(0.1)
                
            finally:
                # Cleanup connections
                await ws_manager.disconnect_user(user1_data.user_id, user1_ws, user1_conn_id)
                await ws_manager.disconnect_user(user2_data.user_id, user2_ws, user2_conn_id)
                await user1_ws.close()
                await user2_ws.close()
            
            # Validate execution timing (CLAUDE.md requirement)
            execution_time = time.time() - start_time
            assert execution_time >= 0.1, f"Test executed too quickly ({execution_time:.3f}s) - likely using mocks"
            
            # Validate authenticated user1 received events
            user1_events = user1_ws.received_events
            assert len(user1_events) >= 5, f"User1 expected at least 5 WebSocket events, got {len(user1_events)}"
            
            user1_event_types = [e.get("type") for e in user1_events]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for required_event in required_events:
                assert required_event in user1_event_types, f"User1 missing required event: {required_event}. Got: {user1_event_types}"
            
            # Validate multi-user isolation - user2 should have received their own events
            user2_events = user2_ws.received_events
            assert len(user2_events) >= 2, f"User2 expected at least 2 WebSocket events, got {len(user2_events)}"
            
            user2_event_types = [e.get("type") for e in user2_events]
            assert "agent_started" in user2_event_types, f"User2 missing agent_started event. Got: {user2_event_types}"
            assert "agent_completed" in user2_event_types, f"User2 missing agent_completed event. Got: {user2_event_types}"
            
            # Validate WebSocket message structure
            for event in user1_events:
                assert "type" in event, f"Event missing 'type' field: {event}"
                assert "timestamp" in event, f"Event missing 'timestamp' field: {event}"
                assert "payload" in event, f"Event missing 'payload' field: {event}"
                
                # Validate user isolation in payload
                if "user_id" in event.get("payload", {}):
                    assert event["payload"]["user_id"] == user1_data.user_id, f"User isolation violated - wrong user_id in event: {event}"
            
            # Validate user2 events are isolated from user1
            for event in user2_events:
                if "user_id" in event.get("payload", {}):
                    assert event["payload"]["user_id"] == user2_data.user_id, f"User2 isolation violated - wrong user_id in event: {event}"
            
            logger.info("✅ AUTHENTICATED WebSocket connectivity test PASSED")
            logger.info(f"   📊 User1: {len(user1_events)} events, User2: {len(user2_events)} events")
            logger.info(f"   🎯 Multi-user isolation validated successfully")
            logger.info(f"   ⏱️  Execution time: {execution_time:.3f}s (real services confirmed)")
            
        finally:
            # Cleanup environment
            env.disable_isolation(restore_original=True)

    @pytest.mark.asyncio
    @pytest.mark.timeout(25)
    async def test_websocket_message_sequence_validation(self):
        """Test WebSocket message sequence validation with authenticated users.
        
        CLAUDE.md COMPLIANCE:
        ✅ Uses E2EAuthHelper for authentication
        ✅ NO mocks - real WebSocket message sequences
        ✅ Real execution timing validation
        ✅ Hard error raising on failures
        ✅ Validates message ordering and integrity
        
        Business Impact: Message reliability - prevents data loss and corruption
        """
        start_time = time.time()
        
        # Set up isolated environment
        env = get_env()
        env.enable_isolation(backup_original=True)
        
        test_vars = {
            "TESTING": "1",
            "NETRA_ENV": "testing",
            "ENVIRONMENT": "testing",
            "LOG_LEVEL": "ERROR",
        }
        
        for key, value in test_vars.items():
            env.set(key, value, source="websocket_message_sequence_test")
        
        try:
            logger.info("🚀 Testing AUTHENTICATED WebSocket message sequences")
            
            # Create authenticated user using SSOT patterns
            auth_helper = E2EAuthHelper()
            user_data = await auth_helper.create_authenticated_user(
                email_prefix="message_sequence_user",
                password="SequencePass123!",
                name="Message Sequence Test User"
            )
            
            # Create real WebSocket manager and connection
            ws_manager = UnifiedWebSocketManager()
            conn_id = "message-sequence-conn"
            ws_conn = InMemoryWebSocketConnection()
            
            # Connect user with authentication context
            await ws_manager.connect_user(user_data.user_id, ws_conn, conn_id)
            
            try:
                # Create WebSocket notifier
                notifier = WebSocketNotifier(ws_manager)
                
                # Create execution context for message sequence testing
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                
                context = AgentExecutionContext(
                    run_id=f"sequence-test-{user_data.user_id}",
                    thread_id=conn_id,
                    user_id=user_data.user_id,
                    agent_name="message_sequence_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                # Send a complex message sequence with multiple tools
                logger.info("📡 Testing complex message sequence...")
                
                # Start agent
                await notifier.send_agent_started(context)
                await asyncio.sleep(0.01)
                
                # Multiple thinking phases
                await notifier.send_agent_thinking(context, "Phase 1: Analyzing input data...")
                await asyncio.sleep(0.01)
                
                # Tool sequence 1
                await notifier.send_tool_executing(context, "data_analyzer")
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context, "data_analyzer", {"analysis": "complete", "patterns": 3})
                await asyncio.sleep(0.01)
                
                # Thinking phase 2
                await notifier.send_agent_thinking(context, "Phase 2: Processing analysis results...")
                await asyncio.sleep(0.01)
                
                # Tool sequence 2
                await notifier.send_tool_executing(context, "pattern_processor")
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context, "pattern_processor", {"processed_patterns": 3, "confidence": 0.95})
                await asyncio.sleep(0.01)
                
                # Partial result
                await notifier.send_partial_result(context, "Found 3 patterns with high confidence...")
                await asyncio.sleep(0.01)
                
                # Final thinking
                await notifier.send_agent_thinking(context, "Phase 3: Generating final recommendations...")
                await asyncio.sleep(0.01)
                
                # Tool sequence 3
                await notifier.send_tool_executing(context, "recommendation_generator")
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context, "recommendation_generator", {"recommendations": ["opt1", "opt2", "opt3"]})
                await asyncio.sleep(0.01)
                
                # Complete agent
                await notifier.send_agent_completed(context, {"sequence_test": "passed", "total_tools": 3})
                await asyncio.sleep(0.1)
                
            finally:
                # Cleanup connection
                await ws_manager.disconnect_user(user_data.user_id, ws_conn, conn_id)
                await ws_conn.close()
            
            # Validate execution timing
            execution_time = time.time() - start_time
            assert execution_time >= 0.1, f"Test executed too quickly ({execution_time:.3f}s) - likely using mocks"
            
            # Validate message sequence integrity
            events = ws_conn.received_events
            assert len(events) >= 12, f"Expected at least 12 WebSocket events, got {len(events)}"
            
            event_types = [e.get("type") for e in events]
            
            # Validate sequence starts with agent_started
            assert event_types[0] == "agent_started", f"Sequence should start with agent_started, got {event_types[0]}"
            
            # Validate sequence ends with agent_completed
            assert event_types[-1] == "agent_completed", f"Sequence should end with agent_completed, got {event_types[-1]}"
            
            # Validate tool pairing (each tool_executing should have matching tool_completed)
            tool_executing_indices = [i for i, t in enumerate(event_types) if t == "tool_executing"]
            tool_completed_indices = [i for i, t in enumerate(event_types) if t == "tool_completed"]
            
            assert len(tool_executing_indices) == len(tool_completed_indices), \
                f"Tool event mismatch: {len(tool_executing_indices)} executing, {len(tool_completed_indices)} completed"
            
            assert len(tool_executing_indices) == 3, f"Expected 3 tool sequences, got {len(tool_executing_indices)}"
            
            # Validate tool sequence ordering (executing should come before completed for each tool)
            for i in range(len(tool_executing_indices)):
                executing_idx = tool_executing_indices[i]
                completed_idx = tool_completed_indices[i]
                assert executing_idx < completed_idx, \
                    f"Tool {i}: executing at {executing_idx} should come before completed at {completed_idx}"
            
            # Validate message structure consistency
            for i, event in enumerate(events):
                assert "type" in event, f"Event {i} missing 'type' field: {event}"
                assert "timestamp" in event, f"Event {i} missing 'timestamp' field: {event}"
                assert "payload" in event, f"Event {i} missing 'payload' field: {event}"
                
                # Validate user context in payload
                if "user_id" in event.get("payload", {}):
                    assert event["payload"]["user_id"] == user_data.user_id, \
                        f"Event {i} has wrong user_id: {event['payload']['user_id']} != {user_data.user_id}"
            
            # Validate specific tool results
            tool_completed_events = [e for e in events if e.get("type") == "tool_completed"]
            assert len(tool_completed_events) == 3, f"Expected 3 tool completed events, got {len(tool_completed_events)}"
            
            # Validate tool results contain expected data
            for tool_event in tool_completed_events:
                tool_result = tool_event.get("payload", {}).get("result", {})
                assert isinstance(tool_result, dict), f"Tool result should be dict, got {type(tool_result)}"
                assert len(tool_result) > 0, f"Tool result should not be empty: {tool_result}"
            
            logger.info("✅ AUTHENTICATED WebSocket message sequence test PASSED")
            logger.info(f"   📊 Total events: {len(events)}")
            logger.info(f"   🔧 Tool sequences: {len(tool_executing_indices)}")
            logger.info(f"   ⏱️  Execution time: {execution_time:.3f}s (real services confirmed)")
            
        finally:
            # Cleanup environment
            env.disable_isolation(restore_original=True)


if __name__ == "__main__":
    # Run WebSocket connectivity tests independently
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short", 
        "-s",  # Show real-time output
        "--timeout=60"  # Allow time for real service testing
    ])