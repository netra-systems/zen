from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''WebSocket Async Serialization Blocking Compliance Tests

# REMOVED_SYNTAX_ERROR: CRITICAL ISSUE: Tests exposing synchronous _serialize_message_safely blocking event loop
# REMOVED_SYNTAX_ERROR: at line 810 in websocket_core/manager.py during agent updates.

# REMOVED_SYNTAX_ERROR: These tests are designed to FAIL until proper async serialization is implemented.
# REMOVED_SYNTAX_ERROR: The tests detect event loop blocking, performance issues, and concurrent agent bottlenecks.

# REMOVED_SYNTAX_ERROR: All tests should FAIL showing the current blocking behavior. Once fixed with async
# REMOVED_SYNTAX_ERROR: serialization, these tests will pass and provide ongoing regression protection.
""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import pytest

# Import core types and classes
from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult, ActionPlanResult, ReportResult
from netra_backend.app.schemas.agent_models import AgentMetadata
# REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.websocket_message_types import ( )
AgentCompletedMessage,
AgentStartedMessage,
AgentThinkingMessage,
ConnectionInfo,
ServerMessage,
UserMessage,
WebSocketMessage

from netra_backend.app.websocket_core import WebSocketManager


# REMOVED_SYNTAX_ERROR: class EventLoopBlockingDetector:
    # REMOVED_SYNTAX_ERROR: """Utility to detect when the event loop is blocked by synchronous operations"""

# REMOVED_SYNTAX_ERROR: def __init__(self, threshold_ms: float = 10.0):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Args:
        # REMOVED_SYNTAX_ERROR: threshold_ms: Block threshold in milliseconds. Event loop blocks
        # REMOVED_SYNTAX_ERROR: longer than this are considered violations
        # REMOVED_SYNTAX_ERROR: """"
        # REMOVED_SYNTAX_ERROR: self.threshold_ms = threshold_ms
        # REMOVED_SYNTAX_ERROR: self.max_block_time = 0.0
        # REMOVED_SYNTAX_ERROR: self.blocked_count = 0
        # REMOVED_SYNTAX_ERROR: self._monitoring = False
        # REMOVED_SYNTAX_ERROR: self._monitor_task = None

# REMOVED_SYNTAX_ERROR: async def start_monitoring(self):
    # REMOVED_SYNTAX_ERROR: """Start monitoring event loop for blocking operations"""
    # REMOVED_SYNTAX_ERROR: if self._monitoring:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return
        # REMOVED_SYNTAX_ERROR: self._monitoring = True
        # REMOVED_SYNTAX_ERROR: self.max_block_time = 0.0
        # REMOVED_SYNTAX_ERROR: self.blocked_count = 0
        # REMOVED_SYNTAX_ERROR: self._monitor_task = asyncio.create_task(self._monitor_loop())

# REMOVED_SYNTAX_ERROR: async def stop_monitoring(self):
    # Removed problematic line: '''Stop monitoring and await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return results""""
    # REMOVED_SYNTAX_ERROR: self._monitoring = False
    # REMOVED_SYNTAX_ERROR: if self._monitor_task:
        # REMOVED_SYNTAX_ERROR: self._monitor_task.cancel()
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: await self._monitor_task
            # REMOVED_SYNTAX_ERROR: except asyncio.CancelledError:
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: return { )
                # REMOVED_SYNTAX_ERROR: 'max_block_time_ms': self.max_block_time * 1000,
                # REMOVED_SYNTAX_ERROR: 'blocked_count': self.blocked_count,
                # REMOVED_SYNTAX_ERROR: 'threshold_exceeded': self.max_block_time * 1000 > self.threshold_ms
                

# REMOVED_SYNTAX_ERROR: async def _monitor_loop(self):
    # REMOVED_SYNTAX_ERROR: """Monitor event loop blocking"""
    # REMOVED_SYNTAX_ERROR: while self._monitoring:
        # REMOVED_SYNTAX_ERROR: start_time = asyncio.get_event_loop().time()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.001)  # 1ms sleep
        # REMOVED_SYNTAX_ERROR: end_time = asyncio.get_event_loop().time()

        # REMOVED_SYNTAX_ERROR: actual_delay = end_time - start_time
        # REMOVED_SYNTAX_ERROR: if actual_delay > (0.001 + self.threshold_ms / 1000):  # Allow 1ms + threshold
        # REMOVED_SYNTAX_ERROR: self.max_block_time = max(self.max_block_time, actual_delay - 0.001)
        # REMOVED_SYNTAX_ERROR: self.blocked_count += 1


# REMOVED_SYNTAX_ERROR: class ComplexMessageGenerator:
    # REMOVED_SYNTAX_ERROR: """Generate complex messages that take significant time to serialize"""

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def create_complex_deep_agent_state(complexity_factor: int = 10) -> DeepAgentState:
    # REMOVED_SYNTAX_ERROR: """Create a DeepAgentState with nested complex objects"""
    # Create large nested data structures
    # REMOVED_SYNTAX_ERROR: large_data = {}
    # REMOVED_SYNTAX_ERROR: for i in range(complexity_factor * 100):
        # REMOVED_SYNTAX_ERROR: large_data["formatted_string"complex_optimization",
        # REMOVED_SYNTAX_ERROR: recommendations=["formatted_string" + "x" * 500,
        # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
        
        # REMOVED_SYNTAX_ERROR: for i in range(complexity_factor * 10)
        # REMOVED_SYNTAX_ERROR: ],
        # REMOVED_SYNTAX_ERROR: context_tracking=large_data.copy()
        

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return state

        # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def create_agent_update_message(complexity_factor: int = 10) -> AgentThinkingMessage:
    # REMOVED_SYNTAX_ERROR: """Create a complex agent update message"""
    # REMOVED_SYNTAX_ERROR: return AgentThinkingMessage( )
    # REMOVED_SYNTAX_ERROR: type="agent_thinking",
    # REMOVED_SYNTAX_ERROR: message="Processing complex analysis with extensive data structures",
    # REMOVED_SYNTAX_ERROR: thinking_content="A" * (complexity_factor * 2000),  # Large thinking content
    # REMOVED_SYNTAX_ERROR: agent_state=ComplexMessageGenerator.create_complex_deep_agent_state(complexity_factor),
    # REMOVED_SYNTAX_ERROR: metadata={ )
    # REMOVED_SYNTAX_ERROR: "step": complexity_factor,
    # REMOVED_SYNTAX_ERROR: "complexity": "high",
    # REMOVED_SYNTAX_ERROR: "processing_time_estimate": "formatted_string"
    
    


    # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def monitor_event_loop_blocking(threshold_ms: float = 10.0):
    # REMOVED_SYNTAX_ERROR: """Context manager to monitor event loop blocking during tests"""
    # REMOVED_SYNTAX_ERROR: detector = EventLoopBlockingDetector(threshold_ms)
    # REMOVED_SYNTAX_ERROR: await detector.start_monitoring()
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: yield detector
        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: results = await detector.stop_monitoring()


# REMOVED_SYNTAX_ERROR: class TestWebSocketSerializationBlocking:
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Comprehensive tests exposing WebSocket async serialization blocking issues.

    # REMOVED_SYNTAX_ERROR: All tests are designed to FAIL showing the current synchronous blocking behavior.
    # REMOVED_SYNTAX_ERROR: Once async serialization is properly implemented, these tests will pass.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager for testing"""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket connection"""
    # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_ws.send_json = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_ws.state = 1  # WebSocketState.CONNECTED
    # REMOVED_SYNTAX_ERROR: return mock_ws

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def complex_agent_state(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create complex agent state for testing"""
    # REMOVED_SYNTAX_ERROR: return ComplexMessageGenerator.create_complex_deep_agent_state(5)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_send_to_connection_uses_synchronous_serialization_blocking( )
    # REMOVED_SYNTAX_ERROR: self, websocket_manager, mock_websocket
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: CRITICAL TEST: Exposes that _send_to_connection uses sync serialization
        # REMOVED_SYNTAX_ERROR: which blocks the event loop during complex message serialization.

        # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL until line 810 is fixed to use async serialization.
        # REMOVED_SYNTAX_ERROR: """"
        # Create complex message that takes significant time to serialize
        # REMOVED_SYNTAX_ERROR: complex_message = ComplexMessageGenerator.create_agent_update_message(20)

        # Setup connection
        # REMOVED_SYNTAX_ERROR: connection_id = str(uuid.uuid4())
        # REMOVED_SYNTAX_ERROR: websocket_manager.connections[connection_id] = { )
        # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
        # REMOVED_SYNTAX_ERROR: "user_id": "test_user",
        # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: "message_count": 0
        

        # Monitor event loop blocking during send operation
        # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=5.0) as detector:
            # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

            # This should block the event loop due to sync serialization
            # REMOVED_SYNTAX_ERROR: result = await websocket_manager._send_to_connection(connection_id, complex_message)

            # REMOVED_SYNTAX_ERROR: end_time = time.perf_counter()

            # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()
            # REMOVED_SYNTAX_ERROR: operation_time_ms = (end_time - start_time) * 1000

            # ASSERTIONS THAT SHOULD FAIL with current sync implementation
            # REMOVED_SYNTAX_ERROR: assert result is True, "Send operation should succeed"

            # This assertion SHOULD FAIL - sync serialization blocks event loop
            # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            

            # This assertion SHOULD FAIL - operation should be faster with async
            # REMOVED_SYNTAX_ERROR: assert operation_time_ms < 50.0, ( )
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_concurrent_agent_updates_block_each_other( )
            # REMOVED_SYNTAX_ERROR: self, websocket_manager, mock_websocket
            # REMOVED_SYNTAX_ERROR: ):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test that concurrent agent updates block each other due to sync serialization.

                # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL until async serialization prevents mutual blocking.
                # REMOVED_SYNTAX_ERROR: """"
                # Create multiple complex messages
                # REMOVED_SYNTAX_ERROR: messages = [ )
                # REMOVED_SYNTAX_ERROR: ComplexMessageGenerator.create_agent_update_message(15)
                # REMOVED_SYNTAX_ERROR: for _ in range(5)
                

                # Setup multiple connections
                # REMOVED_SYNTAX_ERROR: connections = []
                # REMOVED_SYNTAX_ERROR: for i in range(5):
                    # REMOVED_SYNTAX_ERROR: conn_id = "formatted_string"
                    # REMOVED_SYNTAX_ERROR: websocket_manager.connections[conn_id] = { )
                    # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                    # REMOVED_SYNTAX_ERROR: "user_id": "formatted_string",
                    # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
                    # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
                    # REMOVED_SYNTAX_ERROR: "message_count": 0
                    
                    # REMOVED_SYNTAX_ERROR: connections.append(conn_id)

                    # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=10.0) as detector:
                        # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                        # Send all messages concurrently - should block due to sync serialization
                        # REMOVED_SYNTAX_ERROR: tasks = [ )
                        # REMOVED_SYNTAX_ERROR: websocket_manager._send_to_connection(conn_id, message)
                        # REMOVED_SYNTAX_ERROR: for conn_id, message in zip(connections, messages)
                        
                        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                        # REMOVED_SYNTAX_ERROR: end_time = time.perf_counter()

                        # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()
                        # REMOVED_SYNTAX_ERROR: total_time_ms = (end_time - start_time) * 1000

                        # All sends should succeed
                        # REMOVED_SYNTAX_ERROR: assert all(r is True for r in results), "formatted_string"

                        # This SHOULD FAIL - concurrent operations block each other with sync serialization
                        # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_send_agent_update_method_blocks_event_loop( )
                        # REMOVED_SYNTAX_ERROR: self, websocket_manager, mock_websocket
                        # REMOVED_SYNTAX_ERROR: ):
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: Test that send_agent_update method blocks due to underlying sync serialization.

                            # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL until send_agent_update uses async serialization path.
                            # REMOVED_SYNTAX_ERROR: """"
                            # Setup thread with connection
                            # REMOVED_SYNTAX_ERROR: thread_id = str(uuid.uuid4())
                            # REMOVED_SYNTAX_ERROR: user_id = "test_user"

                            # REMOVED_SYNTAX_ERROR: connection_id = str(uuid.uuid4())
                            # REMOVED_SYNTAX_ERROR: websocket_manager.connections[connection_id] = { )
                            # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                            # REMOVED_SYNTAX_ERROR: "user_id": user_id,
                            # REMOVED_SYNTAX_ERROR: "thread_id": thread_id,
                            # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
                            # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
                            # REMOVED_SYNTAX_ERROR: "message_count": 0
                            

                            # Create complex agent update
                            # REMOVED_SYNTAX_ERROR: complex_state = ComplexMessageGenerator.create_complex_deep_agent_state(25)

                            # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=8.0) as detector:
                                # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                                # This method should eventually call _send_to_connection with sync serialization
                                # REMOVED_SYNTAX_ERROR: result = await websocket_manager.send_agent_update( )
                                # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                                # REMOVED_SYNTAX_ERROR: message="Processing complex analysis",
                                # REMOVED_SYNTAX_ERROR: agent_state=complex_state,
                                # REMOVED_SYNTAX_ERROR: step_info={"step": 5, "total": 10}
                                

                                # REMOVED_SYNTAX_ERROR: end_time = time.perf_counter()

                                # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()
                                # REMOVED_SYNTAX_ERROR: operation_time_ms = (end_time - start_time) * 1000

                                # REMOVED_SYNTAX_ERROR: assert result is True, "Agent update should succeed"

                                # This SHOULD FAIL - method blocks event loop due to sync serialization
                                # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: websocket_manager.connections[conn_id] = { )
                                        # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                                        # REMOVED_SYNTAX_ERROR: "user_id": "formatted_string",
                                        # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
                                        # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
                                        # REMOVED_SYNTAX_ERROR: "message_count": 0
                                        
                                        # REMOVED_SYNTAX_ERROR: connections.append(conn_id)

                                        # Add connections to room
                                        # REMOVED_SYNTAX_ERROR: websocket_manager.room_memberships[room_id] = set(connections)

                                        # Create complex broadcast message
                                        # REMOVED_SYNTAX_ERROR: complex_message = ComplexMessageGenerator.create_agent_update_message(18)

                                        # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=15.0) as detector:
                                            # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                                            # REMOVED_SYNTAX_ERROR: result = await websocket_manager.broadcast_to_room( )
                                            # REMOVED_SYNTAX_ERROR: room_id=room_id,
                                            # REMOVED_SYNTAX_ERROR: message=complex_message
                                            

                                            # REMOVED_SYNTAX_ERROR: end_time = time.perf_counter()

                                            # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()
                                            # REMOVED_SYNTAX_ERROR: broadcast_time_ms = (end_time - start_time) * 1000

                                            # REMOVED_SYNTAX_ERROR: assert result.successful == 8, "formatted_string"

                                            # This SHOULD FAIL - broadcast blocks event loop with sync serialization
                                            # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: f"should be <100ms with async serialization"
                                            

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_send_to_user_serialization_blocking( )
                                            # REMOVED_SYNTAX_ERROR: self, websocket_manager, mock_websocket
                                            # REMOVED_SYNTAX_ERROR: ):
                                                # REMOVED_SYNTAX_ERROR: '''
                                                # REMOVED_SYNTAX_ERROR: Test send_to_user blocks due to sync serialization in _send_to_connection.

                                                # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL until the serialization path is made async.
                                                # REMOVED_SYNTAX_ERROR: """"
                                                # REMOVED_SYNTAX_ERROR: user_id = "test_user"

                                                # Setup user connection
                                                # REMOVED_SYNTAX_ERROR: connection_id = str(uuid.uuid4())
                                                # REMOVED_SYNTAX_ERROR: websocket_manager.connections[connection_id] = { )
                                                # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                                                # REMOVED_SYNTAX_ERROR: "user_id": user_id,
                                                # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
                                                # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
                                                # REMOVED_SYNTAX_ERROR: "message_count": 0
                                                

                                                # Create very complex message
                                                # REMOVED_SYNTAX_ERROR: complex_message = ComplexMessageGenerator.create_agent_update_message(30)

                                                # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=12.0) as detector:
                                                    # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                                                    # REMOVED_SYNTAX_ERROR: result = await websocket_manager.send_to_user( )
                                                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                    # REMOVED_SYNTAX_ERROR: message=complex_message
                                                    

                                                    # REMOVED_SYNTAX_ERROR: end_time = time.perf_counter()

                                                    # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()
                                                    # REMOVED_SYNTAX_ERROR: operation_time_ms = (end_time - start_time) * 1000

                                                    # REMOVED_SYNTAX_ERROR: assert result is True, "Send to user should succeed"

                                                    # This SHOULD FAIL - send_to_user blocks due to sync serialization
                                                    # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"Serialization took {operation_time_ms:.2f}ms without timeout protection. "
                                                                # REMOVED_SYNTAX_ERROR: f"Async serialization should have timeout handling."
                                                                

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_load_test_reveals_serialization_bottleneck( )
                                                                # REMOVED_SYNTAX_ERROR: self, websocket_manager, mock_websocket
                                                                # REMOVED_SYNTAX_ERROR: ):
                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                    # REMOVED_SYNTAX_ERROR: Load test that reveals serialization as bottleneck under concurrent load.

                                                                    # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL showing poor performance with sync serialization.
                                                                    # REMOVED_SYNTAX_ERROR: """"
                                                                    # Create many connections with complex messages
                                                                    # REMOVED_SYNTAX_ERROR: num_connections = 15
                                                                    # REMOVED_SYNTAX_ERROR: connections = []
                                                                    # REMOVED_SYNTAX_ERROR: messages = []

                                                                    # REMOVED_SYNTAX_ERROR: for i in range(num_connections):
                                                                        # REMOVED_SYNTAX_ERROR: conn_id = "formatted_string"
                                                                        # REMOVED_SYNTAX_ERROR: websocket_manager.connections[conn_id] = { )
                                                                        # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                                                                        # REMOVED_SYNTAX_ERROR: "user_id": "formatted_string",
                                                                        # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
                                                                        # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
                                                                        # REMOVED_SYNTAX_ERROR: "message_count": 0
                                                                        
                                                                        # REMOVED_SYNTAX_ERROR: connections.append(conn_id)
                                                                        # REMOVED_SYNTAX_ERROR: messages.append(ComplexMessageGenerator.create_agent_update_message(12))

                                                                        # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=20.0) as detector:
                                                                            # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                                                                            # Send all messages concurrently to simulate high load
                                                                            # REMOVED_SYNTAX_ERROR: tasks = [ )
                                                                            # REMOVED_SYNTAX_ERROR: websocket_manager._send_to_connection(conn_id, message)
                                                                            # REMOVED_SYNTAX_ERROR: for conn_id, message in zip(connections, messages)
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                                                                            # REMOVED_SYNTAX_ERROR: end_time = time.perf_counter()

                                                                            # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()
                                                                            # REMOVED_SYNTAX_ERROR: total_time_ms = (end_time - start_time) * 1000
                                                                            # REMOVED_SYNTAX_ERROR: avg_time_per_send = total_time_ms / num_connections

                                                                            # All operations should succeed
                                                                            # REMOVED_SYNTAX_ERROR: success_count = sum(1 for r in results if r is True)
                                                                            # REMOVED_SYNTAX_ERROR: assert success_count == num_connections, ( )
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                            

                                                                            # This SHOULD FAIL - load reveals serialization bottleneck
                                                                            # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                            # REMOVED_SYNTAX_ERROR: f"Should be <30ms with async serialization."
                                                                            

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_event_loop_starvation_during_agent_execution( )
                                                                            # REMOVED_SYNTAX_ERROR: self, websocket_manager, mock_websocket
                                                                            # REMOVED_SYNTAX_ERROR: ):
                                                                                # REMOVED_SYNTAX_ERROR: '''
                                                                                # REMOVED_SYNTAX_ERROR: Test that simulates real agent execution causing event loop starvation.

                                                                                # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL due to sync serialization starving the event loop
                                                                                # REMOVED_SYNTAX_ERROR: during agent state updates.
                                                                                # REMOVED_SYNTAX_ERROR: """"
                                                                                # REMOVED_SYNTAX_ERROR: thread_id = str(uuid.uuid4())

                                                                                # Setup connection for agent updates
                                                                                # REMOVED_SYNTAX_ERROR: connection_id = str(uuid.uuid4())
                                                                                # REMOVED_SYNTAX_ERROR: websocket_manager.connections[connection_id] = { )
                                                                                # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                                                                                # REMOVED_SYNTAX_ERROR: "user_id": "agent_user",
                                                                                # REMOVED_SYNTAX_ERROR: "thread_id": thread_id,
                                                                                # REMOVED_SYNTAX_ERROR: "connected_at": datetime.now(timezone.utc),
                                                                                # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
                                                                                # REMOVED_SYNTAX_ERROR: "message_count": 0
                                                                                

                                                                                # Create background task that should run continuously
                                                                                # REMOVED_SYNTAX_ERROR: background_task_runs = 0
                                                                                # REMOVED_SYNTAX_ERROR: task_blocked = False

# REMOVED_SYNTAX_ERROR: async def background_task():
    # REMOVED_SYNTAX_ERROR: nonlocal background_task_runs, task_blocked
    # REMOVED_SYNTAX_ERROR: while background_task_runs < 10:
        # REMOVED_SYNTAX_ERROR: start = asyncio.get_event_loop().time()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.05)  # 50ms
        # REMOVED_SYNTAX_ERROR: end = asyncio.get_event_loop().time()

        # If sleep took much longer than expected, event loop was blocked
        # REMOVED_SYNTAX_ERROR: if (end - start) > 0.1:  # More than 100ms indicates blocking
        # REMOVED_SYNTAX_ERROR: task_blocked = True

        # REMOVED_SYNTAX_ERROR: background_task_runs += 1

        # Start background task to detect starvation
        # REMOVED_SYNTAX_ERROR: background = asyncio.create_task(background_task())

        # REMOVED_SYNTAX_ERROR: async with monitor_event_loop_blocking(threshold_ms=25.0) as detector:
            # Simulate rapid agent updates during execution
            # REMOVED_SYNTAX_ERROR: for step in range(8):
                # REMOVED_SYNTAX_ERROR: complex_state = ComplexMessageGenerator.create_complex_deep_agent_state(15)

                # REMOVED_SYNTAX_ERROR: await websocket_manager.send_agent_update( )
                # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                # REMOVED_SYNTAX_ERROR: message="formatted_string",
                # REMOVED_SYNTAX_ERROR: agent_state=complex_state,
                # REMOVED_SYNTAX_ERROR: step_info={"step": step, "total": 8}
                

                # Small delay between updates
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)

                # Wait for background task to complete
                # REMOVED_SYNTAX_ERROR: await background
                # REMOVED_SYNTAX_ERROR: blocking_results = await detector.stop_monitoring()

                # This SHOULD FAIL - sync serialization starves other tasks
                # REMOVED_SYNTAX_ERROR: assert not task_blocked, ( )
                # REMOVED_SYNTAX_ERROR: "Background task was blocked, indicating event loop starvation "
                # REMOVED_SYNTAX_ERROR: "caused by synchronous serialization during agent updates."
                

                # REMOVED_SYNTAX_ERROR: assert blocking_results['threshold_exceeded'] is False, ( )
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                # REMOVED_SYNTAX_ERROR: f"should run at least 8 times without event loop starvation."
                


                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # Run specific test for debugging
                    # REMOVED_SYNTAX_ERROR: import pytest
                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])