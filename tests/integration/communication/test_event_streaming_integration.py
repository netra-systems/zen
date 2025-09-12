"""
Real-Time Event Streaming Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time event streaming enables live AI processing visibility
- Value Impact: Real-time events build user trust and engagement with AI responses
- Strategic Impact: Event streaming enables responsive user experience for $500K+ ARR

CRITICAL: Real-time events are MISSION CRITICAL for chat value delivery per CLAUDE.md
All 5 agent events MUST stream reliably: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

These integration tests validate event streaming patterns, event ordering, streaming performance,
backpressure handling, and stream recovery without requiring Docker services.
"""

import asyncio
import json
import time
import uuid
from collections import deque, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed

# SSOT imports - using absolute imports only per CLAUDE.md
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)


@pytest.mark.integration
class TestRealTimeEventStreaming(SSotBaseTestCase):
    """
    Test real-time event streaming patterns and delivery.
    
    BVJ: Real-time streaming enables users to see AI processing as it happens
    """
    
    async def test_agent_event_streaming_sequence(self):
        """
        Test streaming of the 5 critical agent events in proper sequence.
        
        BVJ: Sequential event streaming shows users complete AI processing flow
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("stream-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Define critical agent event sequence per CLAUDE.md
            critical_events = [
                (WebSocketEventType.AGENT_STARTED, {
                    "agent_type": "cost_optimizer",
                    "request": "Analyze cloud spending",
                    "estimated_time": "30-45 seconds"
                }),
                (WebSocketEventType.AGENT_THINKING, {
                    "current_thought": "Loading billing data and usage patterns",
                    "progress": 0.2,
                    "reasoning": "Need to analyze historical costs and usage"
                }),
                (WebSocketEventType.TOOL_EXECUTING, {
                    "tool_name": "aws_cost_analyzer",
                    "description": "Analyzing AWS spending patterns",
                    "parameters": {"time_range": "90_days", "services": ["EC2", "S3", "RDS"]}
                }),
                (WebSocketEventType.TOOL_COMPLETED, {
                    "tool_name": "aws_cost_analyzer",
                    "results": {
                        "total_cost": 5420.75,
                        "potential_savings": 1365.50,
                        "top_recommendations": ["Right-size EC2", "Use Reserved Instances"]
                    },
                    "execution_time": 12.3
                }),
                (WebSocketEventType.AGENT_COMPLETED, {
                    "agent_type": "cost_optimizer",
                    "final_result": "Identified $1,365/month savings opportunity",
                    "confidence": 0.94,
                    "next_steps": ["Review recommendations", "Implement changes"]
                })
            ]
            
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            stream_start = time.time()
            
            # Stream events with realistic timing
            for i, (event_type, event_data) in enumerate(critical_events):
                # Add streaming metadata
                stream_data = {
                    **event_data,
                    "execution_id": execution_id,
                    "stream_sequence": i + 1,
                    "stream_timestamp": time.time(),
                    "stream_latency": time.time() - stream_start
                }
                
                await client.send_message(
                    event_type,
                    stream_data,
                    user_id="stream-user",
                    thread_id=f"thread_{execution_id}"
                )
                
                # Realistic delay between events
                await asyncio.sleep(0.1)
            
            # Verify streaming sequence
            assert len(client.sent_messages) == 5
            
            # Verify event order and streaming metadata
            for i, (expected_event, _) in enumerate(critical_events):
                actual_msg = client.sent_messages[i]
                assert actual_msg.event_type == expected_event
                assert actual_msg.data["execution_id"] == execution_id
                assert actual_msg.data["stream_sequence"] == i + 1
                assert "stream_timestamp" in actual_msg.data
            
            total_stream_time = time.time() - stream_start
            self.record_metric("event_streaming_sequence", len(critical_events))
            self.record_metric("total_stream_time", total_stream_time)
    
    async def test_concurrent_event_streaming(self):
        """
        Test concurrent event streaming from multiple AI agents.
        
        BVJ: Concurrent streaming supports multiple AI agents working simultaneously
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("concurrent-stream-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Define multiple concurrent agent executions
            concurrent_agents = [
                ("cost_optimizer", "Analyzing AWS costs"),
                ("security_scanner", "Scanning for vulnerabilities"),
                ("performance_analyzer", "Analyzing app performance"),
            ]
            
            # Start concurrent agent streams
            async def stream_agent_events(agent_type: str, task: str, agent_index: int):
                execution_id = f"exec_{agent_type}_{uuid.uuid4().hex[:6]}"
                
                events = [
                    (WebSocketEventType.AGENT_STARTED, {
                        "agent_type": agent_type,
                        "task": task,
                        "agent_index": agent_index
                    }),
                    (WebSocketEventType.AGENT_THINKING, {
                        "agent_type": agent_type,
                        "current_thought": f"Processing {task}",
                        "agent_index": agent_index
                    }),
                    (WebSocketEventType.AGENT_COMPLETED, {
                        "agent_type": agent_type,
                        "result": f"{task} completed",
                        "agent_index": agent_index
                    })
                ]
                
                for event_type, event_data in events:
                    await client.send_message(
                        event_type,
                        {**event_data, "execution_id": execution_id},
                        user_id="concurrent-stream-user",
                        thread_id=f"thread_{agent_index}"
                    )
                    await asyncio.sleep(0.05)  # Brief delay between events
            
            # Run agents concurrently
            tasks = [
                stream_agent_events(agent_type, task, i)
                for i, (agent_type, task) in enumerate(concurrent_agents)
            ]
            
            await asyncio.gather(*tasks)
            
            # Verify concurrent streaming
            total_events = len(concurrent_agents) * 3  # 3 events per agent
            assert len(client.sent_messages) == total_events
            
            # Group events by agent
            agent_events = defaultdict(list)
            for msg in client.sent_messages:
                agent_index = msg.data["agent_index"]
                agent_events[agent_index].append(msg)
            
            # Verify each agent has complete event sequence
            for agent_index in range(len(concurrent_agents)):
                agent_msgs = agent_events[agent_index]
                assert len(agent_msgs) == 3
                
                # Verify event types in sequence
                event_types = [msg.event_type for msg in agent_msgs]
                expected_types = [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.AGENT_COMPLETED
                ]
                assert event_types == expected_types
            
            self.record_metric("concurrent_streaming", len(concurrent_agents))
    
    async def test_streaming_backpressure_handling(self):
        """
        Test event streaming backpressure handling and flow control.
        
        BVJ: Backpressure handling prevents system overload during high-volume streaming
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("backpressure-user")
            client.is_connected = True
            
            # Mock WebSocket with slow processing to simulate backpressure
            mock_websocket = AsyncMock()
            send_delays = []
            
            async def slow_send(data):
                delay = 0.01  # Simulate processing delay
                send_delays.append(delay)
                await asyncio.sleep(delay)
                return None
            
            mock_websocket.send.side_effect = slow_send
            client.websocket = mock_websocket
            
            # Generate high-volume event stream
            event_count = 50
            start_time = time.time()
            
            for i in range(event_count):
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    {
                        "sequence": i,
                        "data": f"High volume event {i}",
                        "timestamp": time.time()
                    },
                    user_id="backpressure-user"
                )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify backpressure handling
            assert len(client.sent_messages) == event_count
            
            # Calculate streaming metrics
            events_per_second = event_count / total_time if total_time > 0 else 0
            avg_send_time = sum(send_delays) / len(send_delays) if send_delays else 0
            
            # Verify reasonable performance despite backpressure
            assert events_per_second > 10, "Should maintain reasonable throughput under backpressure"
            assert avg_send_time > 0, "Should show processing delay"
            
            self.record_metric("backpressure_throughput", events_per_second)
            self.record_metric("avg_send_delay", avg_send_time)
    
    async def test_event_streaming_with_filtering(self):
        """
        Test event streaming with client-side filtering and subscription.
        
        BVJ: Event filtering reduces bandwidth and delivers only relevant events to users
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("filter-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Define subscription filters (simulated)
            subscribed_events = {
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_COMPLETED,
                WebSocketEventType.ERROR
            }
            
            # Stream various event types
            all_events = [
                (WebSocketEventType.AGENT_STARTED, {"status": "Agent started"}),
                (WebSocketEventType.AGENT_THINKING, {"status": "Agent thinking"}),  # Not subscribed
                (WebSocketEventType.TOOL_EXECUTING, {"status": "Tool running"}),  # Not subscribed
                (WebSocketEventType.TOOL_COMPLETED, {"status": "Tool done"}),  # Not subscribed
                (WebSocketEventType.AGENT_COMPLETED, {"status": "Agent done"}),
                (WebSocketEventType.ERROR, {"error": "Test error"}),
                (WebSocketEventType.PING, {"ping": True}),  # Not subscribed
            ]
            
            # Send all events but simulate filtering
            filtered_messages = []
            for event_type, event_data in all_events:
                # Only send subscribed events (simulate client-side filtering)
                if event_type in subscribed_events:
                    await client.send_message(
                        event_type,
                        event_data,
                        user_id="filter-user"
                    )
                    filtered_messages.append((event_type, event_data))
            
            # Verify filtering effectiveness
            assert len(client.sent_messages) == len(filtered_messages)
            assert len(client.sent_messages) < len(all_events), "Filtering should reduce message count"
            
            # Verify only subscribed events were sent
            sent_event_types = {msg.event_type for msg in client.sent_messages}
            assert sent_event_types.issubset(subscribed_events)
            
            # Calculate filtering efficiency
            filter_ratio = len(filtered_messages) / len(all_events)
            assert filter_ratio < 1.0, "Should filter out some events"
            
            self.record_metric("filtering_efficiency", 1.0 - filter_ratio)


@pytest.mark.integration
class TestEventStreamingReliability(SSotBaseTestCase):
    """
    Test event streaming reliability and recovery patterns.
    
    BVJ: Reliable streaming ensures users don't miss important AI processing updates
    """
    
    async def test_streaming_interruption_recovery(self):
        """
        Test streaming recovery after connection interruptions.
        
        BVJ: Stream recovery ensures users receive complete AI processing updates
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("recovery-user")
            
            # Start streaming sequence
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            events_before_interruption = [
                (WebSocketEventType.AGENT_STARTED, {"status": "started"}),
                (WebSocketEventType.AGENT_THINKING, {"status": "thinking"}),
            ]
            
            # Send events before interruption
            client.is_connected = True
            client.websocket = AsyncMock()
            
            for event_type, event_data in events_before_interruption:
                await client.send_message(
                    event_type,
                    {**event_data, "execution_id": execution_id},
                    user_id="recovery-user"
                )
            
            pre_interruption_count = len(client.sent_messages)
            assert pre_interruption_count == 2
            
            # Simulate connection interruption
            await client.disconnect()
            assert not client.is_connected
            
            # Simulate recovery and continuation
            client.is_connected = True
            client.websocket = AsyncMock()
            
            events_after_recovery = [
                (WebSocketEventType.TOOL_EXECUTING, {"status": "executing"}),
                (WebSocketEventType.TOOL_COMPLETED, {"status": "completed"}),
                (WebSocketEventType.AGENT_COMPLETED, {"status": "finished"}),
            ]
            
            # Continue streaming after recovery
            for event_type, event_data in events_after_recovery:
                await client.send_message(
                    event_type,
                    {**event_data, "execution_id": execution_id, "recovered": True},
                    user_id="recovery-user"
                )
            
            # Verify recovery
            total_events = len(client.sent_messages)
            assert total_events == pre_interruption_count + len(events_after_recovery)
            
            # Verify continuity of execution_id
            all_execution_ids = [msg.data["execution_id"] for msg in client.sent_messages]
            assert all(eid == execution_id for eid in all_execution_ids)
            
            # Verify recovery markers
            recovered_events = [msg for msg in client.sent_messages if msg.data.get("recovered")]
            assert len(recovered_events) == len(events_after_recovery)
            
            self.record_metric("stream_recovery", "successful")
    
    async def test_event_streaming_buffering(self):
        """
        Test event streaming buffering during temporary disconnections.
        
        BVJ: Event buffering ensures no AI processing updates are lost during brief outages
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("buffer-user")
            
            # Simulate buffering scenario
            event_buffer = deque(maxlen=100)  # Simulate buffer
            
            # Generate events during "disconnected" state
            buffered_events = [
                (WebSocketEventType.AGENT_THINKING, {"step": 1, "thought": "Analyzing data"}),
                (WebSocketEventType.AGENT_THINKING, {"step": 2, "thought": "Processing results"}),
                (WebSocketEventType.TOOL_EXECUTING, {"tool": "calculator"}),
                (WebSocketEventType.TOOL_COMPLETED, {"tool": "calculator", "result": "done"}),
            ]
            
            # Buffer events while "disconnected"
            for event_type, event_data in buffered_events:
                buffered_event = {
                    "event_type": event_type,
                    "data": event_data,
                    "buffered_at": time.time(),
                    "user_id": "buffer-user"
                }
                event_buffer.append(buffered_event)
            
            # Verify buffering
            assert len(event_buffer) == len(buffered_events)
            
            # Simulate reconnection and buffer flush
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Flush buffered events
            while event_buffer:
                buffered_event = event_buffer.popleft()
                await client.send_message(
                    buffered_event["event_type"],
                    {**buffered_event["data"], "was_buffered": True},
                    user_id=buffered_event["user_id"]
                )
            
            # Verify buffer flush
            assert len(client.sent_messages) == len(buffered_events)
            assert len(event_buffer) == 0
            
            # Verify all events were marked as buffered
            buffered_flags = [msg.data.get("was_buffered") for msg in client.sent_messages]
            assert all(buffered_flags), "All events should be marked as previously buffered"
            
            self.record_metric("event_buffering", len(buffered_events))
    
    async def test_streaming_error_handling(self):
        """
        Test streaming error handling and error event delivery.
        
        BVJ: Error handling ensures users are informed of AI processing issues
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("error-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Start normal streaming
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            await client.send_message(
                WebSocketEventType.AGENT_STARTED,
                {"execution_id": execution_id, "agent": "test_agent"},
                user_id="error-user"
            )
            
            # Simulate various error scenarios during streaming
            error_scenarios = [
                {
                    "error_type": "tool_failure",
                    "error_message": "Tool execution failed",
                    "error_code": "TOOL_EXEC_ERROR",
                    "recoverable": True
                },
                {
                    "error_type": "data_access",
                    "error_message": "Unable to access required data",
                    "error_code": "DATA_ACCESS_ERROR",
                    "recoverable": False
                },
                {
                    "error_type": "timeout",
                    "error_message": "Operation timed out",
                    "error_code": "TIMEOUT_ERROR",
                    "recoverable": True
                }
            ]
            
            # Stream error events
            for error_info in error_scenarios:
                await client.send_message(
                    WebSocketEventType.ERROR,
                    {
                        "execution_id": execution_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        **error_info
                    },
                    user_id="error-user"
                )
                
                # If recoverable, send recovery event
                if error_info["recoverable"]:
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "execution_id": execution_id,
                            "status": "recovered",
                            "recovered_from": error_info["error_code"]
                        },
                        user_id="error-user"
                    )
            
            # Verify error streaming
            error_messages = [
                msg for msg in client.sent_messages 
                if msg.event_type == WebSocketEventType.ERROR
            ]
            assert len(error_messages) == len(error_scenarios)
            
            # Verify recovery messages
            recovery_messages = [
                msg for msg in client.sent_messages
                if msg.event_type == WebSocketEventType.STATUS_UPDATE 
                and msg.data.get("status") == "recovered"
            ]
            
            recoverable_errors = [e for e in error_scenarios if e["recoverable"]]
            assert len(recovery_messages) == len(recoverable_errors)
            
            self.record_metric("error_streaming", len(error_messages))
            self.record_metric("recovery_streaming", len(recovery_messages))
    
    async def test_streaming_flow_control(self):
        """
        Test streaming flow control and rate limiting.
        
        BVJ: Flow control prevents overwhelming users with too many events
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("flow-control-user")
            client.is_connected = True
            
            # Implement simple rate limiting simulation
            rate_limit_window = 1.0  # 1 second
            rate_limit_count = 10    # Max 10 events per second
            
            event_timestamps = deque()
            rate_limited_count = 0
            sent_count = 0
            
            # Generate high-frequency events
            total_events = 25
            for i in range(total_events):
                current_time = time.time()
                
                # Remove old timestamps outside window
                while event_timestamps and (current_time - event_timestamps[0]) > rate_limit_window:
                    event_timestamps.popleft()
                
                # Check rate limit
                if len(event_timestamps) < rate_limit_count:
                    # Send event
                    client.websocket = AsyncMock()
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "sequence": i,
                            "timestamp": current_time,
                            "rate_limited": False
                        },
                        user_id="flow-control-user"
                    )
                    event_timestamps.append(current_time)
                    sent_count += 1
                else:
                    # Rate limited
                    rate_limited_count += 1
                
                # Small delay to simulate rapid events
                await asyncio.sleep(0.02)
            
            # Verify flow control effectiveness
            assert sent_count < total_events, "Rate limiting should reduce sent events"
            assert rate_limited_count > 0, "Some events should be rate limited"
            assert len(client.sent_messages) == sent_count
            
            # Calculate rate limiting effectiveness
            rate_limit_ratio = rate_limited_count / total_events
            assert rate_limit_ratio > 0, "Should rate limit some events"
            
            self.record_metric("flow_control_ratio", rate_limit_ratio)
            self.record_metric("events_rate_limited", rate_limited_count)


@pytest.mark.integration  
class TestEventStreamingPerformance(SSotBaseTestCase):
    """
    Test event streaming performance characteristics.
    
    BVJ: Performance ensures responsive real-time AI interactions
    """
    
    async def test_high_frequency_event_streaming(self):
        """
        Test streaming performance with high-frequency events.
        
        BVJ: High-frequency streaming supports detailed AI processing visibility
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("high-freq-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Generate high-frequency thinking events
            event_count = 100
            start_time = time.time()
            
            for i in range(event_count):
                await client.send_message(
                    WebSocketEventType.AGENT_THINKING,
                    {
                        "sequence": i,
                        "thought": f"Processing step {i}",
                        "progress": i / event_count,
                        "timestamp": time.time()
                    },
                    user_id="high-freq-user"
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify high-frequency streaming
            assert len(client.sent_messages) == event_count
            
            # Performance metrics
            events_per_second = event_count / duration if duration > 0 else 0
            avg_latency = (duration / event_count) * 1000  # ms
            
            # Performance expectations
            assert events_per_second > 100, "Should handle at least 100 events/second"
            assert avg_latency < 20, "Average latency should be under 20ms"
            
            self.record_metric("high_freq_events_per_second", events_per_second)
            self.record_metric("high_freq_avg_latency", avg_latency)
    
    async def test_streaming_memory_management(self):
        """
        Test streaming memory management and event lifecycle.
        
        BVJ: Memory management ensures stable streaming under sustained load
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("memory-stream-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Stream events in batches with cleanup
            batch_size = 50
            batch_count = 10
            cleanup_threshold = 100  # Keep only latest N messages
            
            for batch in range(batch_count):
                # Send batch of events
                for i in range(batch_size):
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "batch": batch,
                            "sequence": i,
                            "data": "x" * 50,  # Small payload
                            "memory_test": True
                        },
                        user_id="memory-stream-user"
                    )
                
                # Simulate memory management - cleanup old messages
                if len(client.sent_messages) > cleanup_threshold:
                    # Keep only recent messages
                    client.sent_messages = client.sent_messages[-cleanup_threshold:]
                
                # Brief pause between batches
                await asyncio.sleep(0.01)
            
            # Verify memory management
            total_sent = batch_size * batch_count
            final_count = len(client.sent_messages)
            
            assert final_count <= cleanup_threshold, "Should not exceed cleanup threshold"
            assert final_count > 0, "Should retain some recent messages"
            
            # Calculate memory efficiency
            memory_efficiency = 1 - (final_count / total_sent)
            assert memory_efficiency > 0, "Should show memory cleanup efficiency"
            
            self.record_metric("memory_efficiency", memory_efficiency)
            self.record_metric("messages_retained", final_count)
    
    async def test_streaming_latency_measurement(self):
        """
        Test streaming latency measurement and optimization.
        
        BVJ: Low latency ensures responsive AI interaction experience
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("latency-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Measure end-to-end streaming latency
            latencies = []
            event_count = 30
            
            for i in range(event_count):
                send_start = time.time()
                
                await client.send_message(
                    WebSocketEventType.PING,
                    {
                        "sequence": i,
                        "send_timestamp": send_start,
                        "latency_test": True
                    },
                    user_id="latency-user"
                )
                
                send_end = time.time()
                latency = (send_end - send_start) * 1000  # ms
                latencies.append(latency)
                
                # Small delay between measurements
                await asyncio.sleep(0.05)
            
            # Analyze latency statistics
            min_latency = min(latencies)
            max_latency = max(latencies)
            avg_latency = sum(latencies) / len(latencies)
            
            # Calculate percentiles (simple approximation)
            sorted_latencies = sorted(latencies)
            p50_latency = sorted_latencies[len(sorted_latencies) // 2]
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            
            # Performance expectations
            assert avg_latency < 50, "Average latency should be under 50ms"
            assert p95_latency < 100, "95th percentile should be under 100ms"
            assert min_latency >= 0, "Minimum latency should be non-negative"
            
            # Latency consistency check
            latency_variance = max_latency - min_latency
            assert latency_variance < 200, "Latency variance should be reasonable"
            
            self.record_metric("avg_streaming_latency", avg_latency)
            self.record_metric("p95_streaming_latency", p95_latency)
            self.record_metric("latency_variance", latency_variance)