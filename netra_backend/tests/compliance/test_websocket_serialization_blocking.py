"""WebSocket Async Serialization Blocking Compliance Tests

CRITICAL ISSUE: Tests exposing synchronous _serialize_message_safely blocking event loop 
at line 810 in websocket_core/manager.py during agent updates.

These tests are designed to FAIL until proper async serialization is implemented.
The tests detect event loop blocking, performance issues, and concurrent agent bottlenecks.

All tests should FAIL showing the current blocking behavior. Once fixed with async
serialization, these tests will pass and provide ongoing regression protection.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
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
from netra_backend.app.schemas.websocket_message_types import (
    AgentCompletedMessage,
    AgentStartedMessage, 
    AgentThinkingMessage,
    ConnectionInfo,
    ServerMessage,
    UserMessage,
    WebSocketMessage
)
from netra_backend.app.websocket_core import WebSocketManager


class EventLoopBlockingDetector:
    """Utility to detect when the event loop is blocked by synchronous operations"""
    
    def __init__(self, threshold_ms: float = 10.0):
        """
        Args:
            threshold_ms: Block threshold in milliseconds. Event loop blocks 
                         longer than this are considered violations
        """
    pass
        self.threshold_ms = threshold_ms
        self.max_block_time = 0.0
        self.blocked_count = 0
        self._monitoring = False
        self._monitor_task = None
        
    async def start_monitoring(self):
        """Start monitoring event loop for blocking operations"""
        if self._monitoring:
            await asyncio.sleep(0)
    return
        self._monitoring = True
        self.max_block_time = 0.0
        self.blocked_count = 0
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop_monitoring(self):
        """Stop monitoring and await asyncio.sleep(0)
    return results"""
    pass
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        return {
            'max_block_time_ms': self.max_block_time * 1000,
            'blocked_count': self.blocked_count,
            'threshold_exceeded': self.max_block_time * 1000 > self.threshold_ms
        }
        
    async def _monitor_loop(self):
        """Monitor event loop blocking"""
        while self._monitoring:
            start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.001)  # 1ms sleep
            end_time = asyncio.get_event_loop().time()
            
            actual_delay = end_time - start_time
            if actual_delay > (0.001 + self.threshold_ms / 1000):  # Allow 1ms + threshold
                self.max_block_time = max(self.max_block_time, actual_delay - 0.001)
                self.blocked_count += 1


class ComplexMessageGenerator:
    """Generate complex messages that take significant time to serialize"""
    
    @staticmethod
    def create_complex_deep_agent_state(complexity_factor: int = 10) -> DeepAgentState:
        """Create a DeepAgentState with nested complex objects"""
        # Create large nested data structures
        large_data = {}
        for i in range(complexity_factor * 100):
            large_data[f"key_{i}"] = {
                "nested_data": [f"item_{j}" for j in range(50)],
                "timestamp": datetime.now(timezone.utc),
                "uuid": str(uuid.uuid4()),
                "metadata": {"depth": i, "complexity": complexity_factor}
            }
            
        # Create complex sub-results
        optimizations = OptimizationsResult(
            optimization_type="complex_optimization",
            recommendations=[f"recommendation_{i}" for i in range(complexity_factor * 20)],
            cost_savings=float(complexity_factor * 1000),
            performance_improvement=float(complexity_factor * 5),
            confidence_score=0.95
        )
        
        action_plan = ActionPlanResult(
            action_plan_summary="Complex multi-step plan with extensive details",
            actions=[{"step": i, "details": f"action_{i}"} for i in range(complexity_factor * 15)],
            execution_timeline=[{"phase": i, "duration": f"{i}h"} for i in range(complexity_factor * 8)]
        )
        
        report = ReportResult(
            report_type="comprehensive_analysis",
            content="A" * (complexity_factor * 1000),  # Large text content
            generated_at=datetime.now(timezone.utc)
        )
        
        # Create the complex state
        state = DeepAgentState(
            user_request="Complex analysis request requiring extensive processing",
            chat_thread_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            agent_input=large_data,
            optimizations_result=optimizations,
            action_plan_result=action_plan,
            report_result=report,
            step_count=complexity_factor * 50,
            messages=[
                {
                    "role": "assistant", 
                    "content": f"Message {i}: " + "x" * 500,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                for i in range(complexity_factor * 10)
            ],
            context_tracking=large_data.copy()
        )
        
        await asyncio.sleep(0)
    return state
        
    @staticmethod
    def create_agent_update_message(complexity_factor: int = 10) -> AgentThinkingMessage:
        """Create a complex agent update message"""
        return AgentThinkingMessage(
            type="agent_thinking",
            message="Processing complex analysis with extensive data structures",
            thinking_content="A" * (complexity_factor * 2000),  # Large thinking content
            agent_state=ComplexMessageGenerator.create_complex_deep_agent_state(complexity_factor),
            metadata={
                "step": complexity_factor,
                "complexity": "high",
                "processing_time_estimate": f"{complexity_factor}s"
            }
        )


@asynccontextmanager
async def monitor_event_loop_blocking(threshold_ms: float = 10.0):
    """Context manager to monitor event loop blocking during tests"""
    detector = EventLoopBlockingDetector(threshold_ms)
    await detector.start_monitoring()
    try:
        yield detector
    finally:
        results = await detector.stop_monitoring()


class TestWebSocketSerializationBlocking:
    """
    pass
    Comprehensive tests exposing WebSocket async serialization blocking issues.
    
    All tests are designed to FAIL showing the current synchronous blocking behavior.
    Once async serialization is properly implemented, these tests will pass.
    """
    
    @pytest.fixture
    def websocket_manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create WebSocket manager for testing"""
    pass
        await asyncio.sleep(0)
    return WebSocketManager()
        
    @pytest.fixture
 def real_websocket():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket connection"""
        mock_ws = AsyncNone  # TODO: Use real service instance
    pass
        mock_ws.send_json = AsyncNone  # TODO: Use real service instance
        mock_ws.state = 1  # WebSocketState.CONNECTED
        return mock_ws
        
    @pytest.fixture
    def complex_agent_state(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create complex agent state for testing"""
    pass
        return ComplexMessageGenerator.create_complex_deep_agent_state(5)
    
    @pytest.mark.asyncio
    async def test_send_to_connection_uses_synchronous_serialization_blocking(
        self, websocket_manager, mock_websocket
    ):
        """
        CRITICAL TEST: Exposes that _send_to_connection uses sync serialization 
        which blocks the event loop during complex message serialization.
        
        This test SHOULD FAIL until line 810 is fixed to use async serialization.
        """
        # Create complex message that takes significant time to serialize
        complex_message = ComplexMessageGenerator.create_agent_update_message(20)
        
        # Setup connection
        connection_id = str(uuid.uuid4())
        websocket_manager.connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": "test_user",
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Monitor event loop blocking during send operation
        async with monitor_event_loop_blocking(threshold_ms=5.0) as detector:
            start_time = time.perf_counter()
            
            # This should block the event loop due to sync serialization
            result = await websocket_manager._send_to_connection(connection_id, complex_message)
            
            end_time = time.perf_counter()
            
        blocking_results = await detector.stop_monitoring()
        operation_time_ms = (end_time - start_time) * 1000
        
        # ASSERTIONS THAT SHOULD FAIL with current sync implementation
        assert result is True, "Send operation should succeed"
        
        # This assertion SHOULD FAIL - sync serialization blocks event loop
        assert blocking_results['threshold_exceeded'] is False, (
            f"Event loop blocked for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 5.0ms). This indicates synchronous serialization is blocking. "
            f"Operation took {operation_time_ms:.2f}ms total."
        )
        
        # This assertion SHOULD FAIL - operation should be faster with async
        assert operation_time_ms < 50.0, (
            f"Serialization took {operation_time_ms:.2f}ms, should be <50ms with async serialization"
        )
        
    @pytest.mark.asyncio
    async def test_concurrent_agent_updates_block_each_other(
        self, websocket_manager, mock_websocket
    ):
        """
        Test that concurrent agent updates block each other due to sync serialization.
        
        This test SHOULD FAIL until async serialization prevents mutual blocking.
        """
        # Create multiple complex messages
        messages = [
            ComplexMessageGenerator.create_agent_update_message(15)
            for _ in range(5)
        ]
        
        # Setup multiple connections
        connections = []
        for i in range(5):
            conn_id = f"test_connection_{i}"
            websocket_manager.connections[conn_id] = {
                "websocket": mock_websocket,
                "user_id": f"test_user_{i}",
                "connected_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc), 
                "message_count": 0
            }
            connections.append(conn_id)
            
        async with monitor_event_loop_blocking(threshold_ms=10.0) as detector:
            start_time = time.perf_counter()
            
            # Send all messages concurrently - should block due to sync serialization
            tasks = [
                websocket_manager._send_to_connection(conn_id, message)
                for conn_id, message in zip(connections, messages)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.perf_counter()
            
        blocking_results = await detector.stop_monitoring()
        total_time_ms = (end_time - start_time) * 1000
        
        # All sends should succeed
        assert all(r is True for r in results), f"Some sends failed: {results}"
        
        # This SHOULD FAIL - concurrent operations block each other with sync serialization  
        assert blocking_results['threshold_exceeded'] is False, (
            f"Concurrent operations blocked event loop for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 10.0ms). This indicates serializations are blocking each other."
        )
        
        # With async serialization, concurrent sends should be much faster
        assert total_time_ms < 200.0, (
            f"Concurrent sends took {total_time_ms:.2f}ms, should be <200ms with async serialization"
        )
        
    @pytest.mark.asyncio
    async def test_send_agent_update_method_blocks_event_loop(
        self, websocket_manager, mock_websocket
    ):
        """
        Test that send_agent_update method blocks due to underlying sync serialization.
        
        This test SHOULD FAIL until send_agent_update uses async serialization path.
        """
        # Setup thread with connection
        thread_id = str(uuid.uuid4())
        user_id = "test_user"
        
        connection_id = str(uuid.uuid4())
        websocket_manager.connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": user_id,
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Create complex agent update
        complex_state = ComplexMessageGenerator.create_complex_deep_agent_state(25)
        
        async with monitor_event_loop_blocking(threshold_ms=8.0) as detector:
            start_time = time.perf_counter()
            
            # This method should eventually call _send_to_connection with sync serialization
            result = await websocket_manager.send_agent_update(
                thread_id=thread_id,
                message="Processing complex analysis",
                agent_state=complex_state,
                step_info={"step": 5, "total": 10}
            )
            
            end_time = time.perf_counter()
            
        blocking_results = await detector.stop_monitoring()
        operation_time_ms = (end_time - start_time) * 1000
        
        assert result is True, "Agent update should succeed"
        
        # This SHOULD FAIL - method blocks event loop due to sync serialization
        assert blocking_results['threshold_exceeded'] is False, (
            f"send_agent_update blocked event loop for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 8.0ms). Agent updates should use async serialization."
        )
        
    @pytest.mark.asyncio 
    async def test_broadcast_to_room_serialization_performance(
        self, websocket_manager, mock_websocket
    ):
        """
        Test broadcast_to_room performance with complex messages.
        
        This test SHOULD FAIL due to sync serialization bottlenecks in broadcasts.
        """
        room_id = "test_room"
        
        # Setup room with multiple connections
        connections = []
        for i in range(8):
            conn_id = f"room_connection_{i}"
            websocket_manager.connections[conn_id] = {
                "websocket": mock_websocket,
                "user_id": f"user_{i}",
                "connected_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "message_count": 0
            }
            connections.append(conn_id)
            
        # Add connections to room
        websocket_manager.room_memberships[room_id] = set(connections)
        
        # Create complex broadcast message
        complex_message = ComplexMessageGenerator.create_agent_update_message(18)
        
        async with monitor_event_loop_blocking(threshold_ms=15.0) as detector:
            start_time = time.perf_counter()
            
            result = await websocket_manager.broadcast_to_room(
                room_id=room_id,
                message=complex_message
            )
            
            end_time = time.perf_counter()
            
        blocking_results = await detector.stop_monitoring()
        broadcast_time_ms = (end_time - start_time) * 1000
        
        assert result.successful == 8, f"Expected 8 successful broadcasts, got {result.successful}"
        
        # This SHOULD FAIL - broadcast blocks event loop with sync serialization
        assert blocking_results['threshold_exceeded'] is False, (
            f"Broadcast blocked event loop for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 15.0ms). Broadcasts should serialize once with async then send to all."
        )
        
        # With async serialization, broadcast should serialize once then send quickly
        assert broadcast_time_ms < 100.0, (
            f"Broadcast took {broadcast_time_ms:.2f}ms for 8 connections, "
            f"should be <100ms with async serialization"
        )
        
    @pytest.mark.asyncio
    async def test_send_to_user_serialization_blocking(
        self, websocket_manager, mock_websocket  
    ):
        """
        Test send_to_user blocks due to sync serialization in _send_to_connection.
        
        This test SHOULD FAIL until the serialization path is made async.
        """
        user_id = "test_user"
        
        # Setup user connection
        connection_id = str(uuid.uuid4())
        websocket_manager.connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Create very complex message
        complex_message = ComplexMessageGenerator.create_agent_update_message(30)
        
        async with monitor_event_loop_blocking(threshold_ms=12.0) as detector:
            start_time = time.perf_counter()
            
            result = await websocket_manager.send_to_user(
                user_id=user_id,
                message=complex_message
            )
            
            end_time = time.perf_counter()
            
        blocking_results = await detector.stop_monitoring()  
        operation_time_ms = (end_time - start_time) * 1000
        
        assert result is True, "Send to user should succeed"
        
        # This SHOULD FAIL - send_to_user blocks due to sync serialization
        assert blocking_results['threshold_exceeded'] is False, (
            f"send_to_user blocked event loop for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 12.0ms). User messages should use async serialization."
        )
        
    @pytest.mark.asyncio
    async def test_serialization_timeout_handling_not_implemented(
        self, websocket_manager, mock_websocket
    ):
        """
        Test that extremely complex messages don't have timeout protection.
        
        This test SHOULD FAIL until async serialization with timeout is implemented.
        """
        # Create extremely complex message that would take very long to serialize
        extremely_complex_state = ComplexMessageGenerator.create_complex_deep_agent_state(50)
        message = AgentThinkingMessage(
            type="agent_thinking",
            message="Extremely complex processing", 
            thinking_content="X" * 50000,  # Very large content
            agent_state=extremely_complex_state
        )
        
        connection_id = str(uuid.uuid4())
        websocket_manager.connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": "test_user",
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Test should timeout quickly with async serialization, but doesn't with sync
        start_time = time.perf_counter()
        
        try:
            result = await asyncio.wait_for(
                websocket_manager._send_to_connection(connection_id, message),
                timeout=2.0  # 2 second timeout
            )
        except asyncio.TimeoutError:
            # This is actually what we want - the sync serialization takes too long
            result = False
            
        end_time = time.perf_counter()
        operation_time_ms = (end_time - start_time) * 1000
        
        # This SHOULD FAIL - sync serialization has no timeout protection
        assert operation_time_ms < 1000.0, (
            f"Serialization took {operation_time_ms:.2f}ms without timeout protection. "
            f"Async serialization should have timeout handling."
        )
        
    @pytest.mark.asyncio
    async def test_load_test_reveals_serialization_bottleneck(
        self, websocket_manager, mock_websocket
    ):
        """
        Load test that reveals serialization as bottleneck under concurrent load.
        
        This test SHOULD FAIL showing poor performance with sync serialization.
        """
        # Create many connections with complex messages
        num_connections = 15
        connections = []
        messages = []
        
        for i in range(num_connections):
            conn_id = f"load_test_conn_{i}"
            websocket_manager.connections[conn_id] = {
                "websocket": mock_websocket,
                "user_id": f"load_user_{i}",
                "connected_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "message_count": 0
            }
            connections.append(conn_id)
            messages.append(ComplexMessageGenerator.create_agent_update_message(12))
            
        async with monitor_event_loop_blocking(threshold_ms=20.0) as detector:
            start_time = time.perf_counter()
            
            # Send all messages concurrently to simulate high load
            tasks = [
                websocket_manager._send_to_connection(conn_id, message)
                for conn_id, message in zip(connections, messages)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.perf_counter()
            
        blocking_results = await detector.stop_monitoring()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_send = total_time_ms / num_connections
        
        # All operations should succeed
        success_count = sum(1 for r in results if r is True)
        assert success_count == num_connections, (
            f"Only {success_count}/{num_connections} sends succeeded under load"
        )
        
        # This SHOULD FAIL - load reveals serialization bottleneck
        assert blocking_results['threshold_exceeded'] is False, (
            f"Load test blocked event loop for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 20.0ms). Serialization is the bottleneck under concurrent load."
        )
        
        # With async serialization, should handle load efficiently
        assert avg_time_per_send < 30.0, (
            f"Average time per send: {avg_time_per_send:.2f}ms under load. "
            f"Should be <30ms with async serialization."
        )
        
    @pytest.mark.asyncio
    async def test_event_loop_starvation_during_agent_execution(
        self, websocket_manager, mock_websocket
    ):
        """
        Test that simulates real agent execution causing event loop starvation.
        
        This test SHOULD FAIL due to sync serialization starving the event loop 
        during agent state updates.
        """
        thread_id = str(uuid.uuid4())
        
        # Setup connection for agent updates
        connection_id = str(uuid.uuid4())
        websocket_manager.connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": "agent_user",
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Create background task that should run continuously
        background_task_runs = 0
        task_blocked = False
        
        async def background_task():
    pass
            nonlocal background_task_runs, task_blocked
            while background_task_runs < 10:
                start = asyncio.get_event_loop().time()
                await asyncio.sleep(0.05)  # 50ms
                end = asyncio.get_event_loop().time()
                
                # If sleep took much longer than expected, event loop was blocked
                if (end - start) > 0.1:  # More than 100ms indicates blocking
                    task_blocked = True
                    
                background_task_runs += 1
                
        # Start background task to detect starvation
        background = asyncio.create_task(background_task())
        
        async with monitor_event_loop_blocking(threshold_ms=25.0) as detector:
            # Simulate rapid agent updates during execution
            for step in range(8):
                complex_state = ComplexMessageGenerator.create_complex_deep_agent_state(15)
                
                await websocket_manager.send_agent_update(
                    thread_id=thread_id,
                    message=f"Agent processing step {step}",
                    agent_state=complex_state,
                    step_info={"step": step, "total": 8}
                )
                
                # Small delay between updates
                await asyncio.sleep(0.01)
                
        # Wait for background task to complete
        await background
        blocking_results = await detector.stop_monitoring()
        
        # This SHOULD FAIL - sync serialization starves other tasks
        assert not task_blocked, (
            "Background task was blocked, indicating event loop starvation "
            "caused by synchronous serialization during agent updates."
        )
        
        assert blocking_results['threshold_exceeded'] is False, (
            f"Agent updates blocked event loop for {blocking_results['max_block_time_ms']:.2f}ms "
            f"(threshold: 25.0ms). This starves other async operations."
        )
        
        assert background_task_runs >= 8, (
            f"Background task only ran {background_task_runs} times, "
            f"should run at least 8 times without event loop starvation."
        )


if __name__ == "__main__":
    # Run specific test for debugging
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])