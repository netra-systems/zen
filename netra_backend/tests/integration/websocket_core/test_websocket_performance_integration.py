#!/usr/bin/env python
"""
Integration Tests for WebSocket Performance and Concurrency

MISSION CRITICAL: WebSocket performance tests for multi-user chat scalability.
Tests real WebSocket performance under concurrent load for business scalability.

Business Value: $500K+ ARR - Multi-user chat scalability validation
- Tests concurrent WebSocket connections and event delivery
- Validates performance under realistic user loads
- Ensures system can handle multiple simultaneous chat sessions
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType as TestEventType

# Import production WebSocket components - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
async def performance_websocket_utility():
    """Create WebSocket test utility optimized for performance testing."""
    async with WebSocketTestUtility() as ws_util:
        yield ws_util


@pytest.fixture
async def performance_websocket_manager():
    """Create WebSocket manager for performance testing."""
    manager = UnifiedWebSocketManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.mark.integration
@pytest.mark.performance
class TestWebSocketConcurrentPerformance:
    """Integration tests for WebSocket concurrent performance."""
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections_performance(self, performance_websocket_utility, performance_websocket_manager):
        """
        Test concurrent WebSocket connections performance.
        
        CRITICAL: System must handle multiple concurrent chat users.
        Performance degradation affects user experience and business value.
        """
        # Arrange
        user_count = 10  # Realistic concurrent user load
        bridge = AgentWebSocketBridge(performance_websocket_manager)
        
        # Create user contexts
        user_contexts = []
        for i in range(user_count):
            context = UserExecutionContext(
                user_id=UserID(f"perf_user_{i}_{uuid.uuid4().hex[:6]}"),
                thread_id=ThreadID(f"perf_thread_{i}_{uuid.uuid4().hex[:6]}"),
                request_id=RequestID(f"perf_request_{i}_{uuid.uuid4().hex[:6]}")
            )
            user_contexts.append(context)
        
        # Act - Create concurrent WebSocket connections
        start_time = time.time()
        
        clients = []
        connect_tasks = []
        
        for context in user_contexts:
            client = await performance_websocket_utility.create_test_client(context.user_id)
            clients.append(client)
            
            # Create connection task
            connect_task = asyncio.create_task(client.connect(timeout=30.0))
            connect_tasks.append(connect_task)
        
        # Wait for all connections
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        connection_time = time.time() - start_time
        
        # Register all connections with manager
        for i, (client, context) in enumerate(zip(clients, user_contexts)):
            if connection_results[i] is True:  # Successful connection
                await performance_websocket_manager.register_user_connection(
                    context.user_id,
                    client.websocket
                )
        
        # Assert connection performance
        successful_connections = sum(1 for result in connection_results if result is True)
        assert successful_connections >= user_count * 0.8, f"At least 80% connections must succeed, got {successful_connections}/{user_count}"
        assert connection_time < 30.0, f"Connection time {connection_time:.2f}s exceeds limit"
        
        # Test concurrent event delivery
        event_start_time = time.time()
        
        # Send agent_started events to all users concurrently
        event_tasks = []
        for context in user_contexts:
            event_task = asyncio.create_task(
                bridge.emit_event(
                    context=context,
                    event_type="agent_started",
                    event_data={
                        "agent": f"perf_agent_{context.user_id}",
                        "status": "starting",
                        "timestamp": datetime.now().isoformat(),
                        "performance_test": True
                    }
                )
            )
            event_tasks.append(event_task)
        
        # Wait for all events to be sent
        event_results = await asyncio.gather(*event_tasks, return_exceptions=True)
        event_delivery_time = time.time() - event_start_time
        
        # Assert event delivery performance
        successful_events = sum(1 for result in event_results if result is True)
        assert successful_events >= user_count * 0.9, f"At least 90% events must be delivered, got {successful_events}/{user_count}"
        assert event_delivery_time < 10.0, f"Event delivery time {event_delivery_time:.2f}s exceeds limit"
        
        # Cleanup
        cleanup_tasks = [client.disconnect() for client in clients]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Performance metrics
        performance_metrics = {
            "total_users": user_count,
            "successful_connections": successful_connections,
            "connection_time": connection_time,
            "successful_events": successful_events,
            "event_delivery_time": event_delivery_time,
            "avg_connection_time": connection_time / user_count,
            "events_per_second": successful_events / event_delivery_time if event_delivery_time > 0 else 0
        }
        
        print(f"Performance Metrics: {performance_metrics}")
        
        # Business-critical performance assertions
        assert performance_metrics["events_per_second"] >= 50, "Must handle at least 50 events/second"
        assert performance_metrics["avg_connection_time"] < 3.0, "Average connection time must be under 3 seconds"
    
    @pytest.mark.asyncio
    async def test_high_frequency_event_delivery_performance(self, performance_websocket_utility, performance_websocket_manager):
        """
        Test high-frequency WebSocket event delivery performance.
        
        CRITICAL: System must handle rapid agent event sequences.
        Agent workflows generate multiple events quickly during execution.
        """
        # Arrange
        bridge = AgentWebSocketBridge(performance_websocket_manager)
        user_context = UserExecutionContext(
            user_id=UserID(f"freq_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"freq_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"freq_request_{uuid.uuid4().hex[:8]}")
        )
        
        async with performance_websocket_utility.connected_client(user_context.user_id) as client:
            # Register connection
            await performance_websocket_manager.register_user_connection(
                user_context.user_id,
                client.websocket
            )
            
            # Act - Send high-frequency events
            event_count = 50  # 50 rapid events to simulate intensive agent workflow
            events_to_send = []
            
            # Create diverse event sequence
            for i in range(event_count):
                event_type = ["agent_thinking", "tool_executing", "tool_completed"][i % 3]
                event_data = {
                    "sequence_number": i,
                    "timestamp": datetime.now().isoformat(),
                    "high_frequency_test": True
                }
                
                if event_type == "agent_thinking":
                    event_data.update({
                        "agent": "high_freq_agent",
                        "progress": f"Processing step {i+1}/{event_count}",
                        "stage": f"step_{i}"
                    })
                elif event_type == "tool_executing":
                    event_data.update({
                        "tool": f"tool_{i}",
                        "status": "executing",
                        "args": {"step": i}
                    })
                else:  # tool_completed
                    event_data.update({
                        "tool": f"tool_{i}",
                        "result": {"step_result": f"result_{i}"},
                        "status": "completed"
                    })
                
                events_to_send.append((event_type, event_data))
            
            # Send events as fast as possible
            start_time = time.time()
            
            send_tasks = []
            for event_type, event_data in events_to_send:
                task = asyncio.create_task(
                    bridge.emit_event(
                        context=user_context,
                        event_type=event_type,
                        event_data=event_data
                    )
                )
                send_tasks.append(task)
            
            # Wait for all events to be sent
            send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
            send_time = time.time() - start_time
            
            # Wait for events to be received
            await asyncio.sleep(2.0)  # Allow time for WebSocket delivery
            
            # Assert sending performance
            successful_sends = sum(1 for result in send_results if result is True)
            assert successful_sends >= event_count * 0.95, f"At least 95% events must send successfully, got {successful_sends}/{event_count}"
            
            # Verify reception (sample check)
            received_messages = client.received_messages
            assert len(received_messages) >= event_count * 0.8, f"Must receive at least 80% of events, got {len(received_messages)}/{event_count}"
            
            # Performance metrics
            events_per_second = event_count / send_time if send_time > 0 else 0
            avg_event_time = send_time / event_count if event_count > 0 else 0
            
            performance_results = {
                "total_events": event_count,
                "successful_sends": successful_sends,
                "send_time": send_time,
                "events_per_second": events_per_second,
                "avg_event_time_ms": avg_event_time * 1000,
                "received_events": len(received_messages)
            }
            
            print(f"High-Frequency Performance: {performance_results}")
            
            # Business-critical performance assertions
            assert events_per_second >= 25, f"Must handle at least 25 events/second, got {events_per_second:.1f}"
            assert avg_event_time < 0.1, f"Average event time must be under 100ms, got {avg_event_time*1000:.1f}ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_multi_user_event_streams(self, performance_websocket_utility, performance_websocket_manager):
        """
        Test concurrent multi-user event streams performance.
        
        CRITICAL: System must handle multiple users with active agent workflows.
        Real business scenario has multiple concurrent chat sessions.
        """
        # Arrange
        user_count = 5  # Concurrent active users
        events_per_user = 10  # Events in each user's workflow
        bridge = AgentWebSocketBridge(performance_websocket_manager)
        
        # Create user contexts and clients
        user_data = []
        for i in range(user_count):
            context = UserExecutionContext(
                user_id=UserID(f"stream_user_{i}_{uuid.uuid4().hex[:6]}"),
                thread_id=ThreadID(f"stream_thread_{i}_{uuid.uuid4().hex[:6]}"),
                request_id=RequestID(f"stream_request_{i}_{uuid.uuid4().hex[:6]}")
            )
            user_data.append({"context": context, "client": None})
        
        # Connect all users
        connect_tasks = []
        for user in user_data:
            client = await performance_websocket_utility.create_test_client(user["context"].user_id)
            user["client"] = client
            connect_tasks.append(client.connect(timeout=30.0))
        
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        # Register successful connections
        for i, user in enumerate(user_data):
            if connection_results[i] is True and user["client"]:
                await performance_websocket_manager.register_user_connection(
                    user["context"].user_id,
                    user["client"].websocket
                )
        
        # Act - Generate concurrent event streams
        async def generate_user_event_stream(user_info):
            """Generate event stream for a single user."""
            context = user_info["context"]
            stream_results = []
            
            for event_num in range(events_per_user):
                # Simulate agent workflow events
                event_sequence = [
                    ("agent_thinking", {
                        "agent": f"agent_{context.user_id}",
                        "progress": f"Processing user request step {event_num+1}",
                        "stage": f"step_{event_num}"
                    }),
                    ("tool_executing", {
                        "tool": f"tool_{event_num}",
                        "status": "executing",
                        "description": f"Executing tool for step {event_num+1}"
                    }),
                    ("tool_completed", {
                        "tool": f"tool_{event_num}",
                        "result": {"step": event_num+1, "status": "success"},
                        "status": "completed"
                    })
                ]
                
                # Send event sequence
                for event_type, event_data in event_sequence:
                    event_data["timestamp"] = datetime.now().isoformat()
                    event_data["user_stream_test"] = True
                    
                    result = await bridge.emit_event(
                        context=context,
                        event_type=event_type,
                        event_data=event_data
                    )
                    stream_results.append(result)
                    
                    # Small delay between events to simulate realistic timing
                    await asyncio.sleep(0.05)
            
            return stream_results
        
        # Generate concurrent streams
        start_time = time.time()
        
        stream_tasks = [
            asyncio.create_task(generate_user_event_stream(user))
            for user in user_data
            if user["client"] and user["client"].is_connected
        ]
        
        stream_results = await asyncio.gather(*stream_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        total_events_sent = 0
        successful_events = 0
        
        for result in stream_results:
            if isinstance(result, list):
                total_events_sent += len(result)
                successful_events += sum(1 for r in result if r is True)
        
        # Wait for message delivery
        await asyncio.sleep(3.0)
        
        # Count received messages across all clients
        total_received = 0
        for user in user_data:
            if user["client"] and hasattr(user["client"], "received_messages"):
                total_received += len(user["client"].received_messages)
        
        # Performance metrics
        concurrent_performance = {
            "concurrent_users": len(stream_tasks),
            "events_per_user": events_per_user * 3,  # 3 events per step
            "total_events_sent": total_events_sent,
            "successful_events": successful_events,
            "total_received": total_received,
            "execution_time": total_time,
            "events_per_second": total_events_sent / total_time if total_time > 0 else 0,
            "success_rate": successful_events / total_events_sent if total_events_sent > 0 else 0
        }
        
        print(f"Concurrent Multi-User Performance: {concurrent_performance}")
        
        # Assert performance requirements
        assert concurrent_performance["success_rate"] >= 0.9, f"Must have 90%+ success rate, got {concurrent_performance['success_rate']:.2%}"
        assert concurrent_performance["events_per_second"] >= 20, f"Must handle 20+ events/second, got {concurrent_performance['events_per_second']:.1f}"
        assert total_time < 60.0, f"Total execution time must be under 60s, got {total_time:.1f}s"
        
        # Cleanup
        cleanup_tasks = []
        for user in user_data:
            if user["client"]:
                cleanup_tasks.append(user["client"].disconnect())
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


@pytest.mark.integration
@pytest.mark.performance
class TestWebSocketStressAndResilience:
    """Integration tests for WebSocket stress testing and resilience."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_resilience_under_load(self, performance_websocket_utility, performance_websocket_manager):
        """
        Test WebSocket connection resilience under load conditions.
        
        CRITICAL: System must maintain stability under stress conditions.
        Connection failures must not cascade or crash the system.
        """
        # Arrange
        bridge = AgentWebSocketBridge(performance_websocket_manager)
        resilience_user_count = 8
        
        # Create user contexts
        user_contexts = []
        for i in range(resilience_user_count):
            context = UserExecutionContext(
                user_id=UserID(f"resilience_user_{i}_{uuid.uuid4().hex[:6]}"),
                thread_id=ThreadID(f"resilience_thread_{i}_{uuid.uuid4().hex[:6]}"),
                request_id=RequestID(f"resilience_request_{i}_{uuid.uuid4().hex[:6]}")
            )
            user_contexts.append(context)
        
        # Act - Stress test with connection cycling
        stress_results = {
            "connection_cycles": 0,
            "successful_connections": 0,
            "successful_events": 0,
            "connection_failures": 0,
            "event_failures": 0
        }
        
        for cycle in range(3):  # 3 connection cycles
            stress_results["connection_cycles"] += 1
            
            # Connect all users
            clients = []
            for context in user_contexts:
                try:
                    client = await performance_websocket_utility.create_test_client(context.user_id)
                    connected = await client.connect(timeout=10.0)
                    
                    if connected:
                        await performance_websocket_manager.register_user_connection(
                            context.user_id,
                            client.websocket
                        )
                        clients.append((client, context))
                        stress_results["successful_connections"] += 1
                    else:
                        stress_results["connection_failures"] += 1
                        
                except Exception:
                    stress_results["connection_failures"] += 1
            
            # Send events under stress
            for client, context in clients:
                try:
                    result = await bridge.emit_event(
                        context=context,
                        event_type="agent_started",
                        event_data={
                            "agent": f"stress_agent_{cycle}",
                            "status": "starting",
                            "cycle": cycle,
                            "stress_test": True,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    if result:
                        stress_results["successful_events"] += 1
                    else:
                        stress_results["event_failures"] += 1
                        
                except Exception:
                    stress_results["event_failures"] += 1
            
            # Disconnect all clients (stress condition)
            for client, _ in clients:
                try:
                    await client.disconnect()
                except Exception:
                    pass  # Expected during stress testing
            
            # Brief recovery period
            await asyncio.sleep(1.0)
        
        # Assert resilience requirements
        total_connections_attempted = resilience_user_count * stress_results["connection_cycles"]
        connection_success_rate = stress_results["successful_connections"] / total_connections_attempted if total_connections_attempted > 0 else 0
        
        total_events_attempted = stress_results["successful_events"] + stress_results["event_failures"]
        event_success_rate = stress_results["successful_events"] / total_events_attempted if total_events_attempted > 0 else 0
        
        print(f"Stress Test Results: {stress_results}")
        print(f"Connection Success Rate: {connection_success_rate:.2%}")
        print(f"Event Success Rate: {event_success_rate:.2%}")
        
        # Business-critical resilience assertions
        assert connection_success_rate >= 0.7, f"Must maintain 70%+ connection success under stress, got {connection_success_rate:.2%}"
        assert event_success_rate >= 0.8, f"Must maintain 80%+ event success under stress, got {event_success_rate:.2%}"
        assert stress_results["successful_events"] > 0, "Must successfully deliver some events under stress"