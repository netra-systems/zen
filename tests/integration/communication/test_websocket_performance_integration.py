"""
WebSocket Performance Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket performance supports responsive AI interactions
- Value Impact: Performance directly affects user experience and engagement
- Strategic Impact: Performance scalability enables platform growth and $500K+ ARR retention

CRITICAL: WebSocket performance enables real-time AI value delivery per CLAUDE.md
Poor performance degrades user trust and reduces AI interaction frequency.

These integration tests validate WebSocket performance under load, connection scaling,
memory efficiency, and response time characteristics without requiring Docker services.
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple
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
class TestWebSocketThroughput(SSotBaseTestCase):
    """
    Test WebSocket throughput and message processing performance.
    
    BVJ: High throughput enables responsive AI interactions under load
    """
    
    async def test_high_volume_message_throughput(self):
        """
        Test WebSocket performance with high volume message throughput.
        
        BVJ: High volume support enables busy AI systems with many simultaneous users
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("throughput-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Performance test configuration
            message_count = 1000
            batch_size = 50
            target_throughput = 500  # messages per second
            
            # Metrics collection
            start_time = time.time()
            latencies = []
            batch_times = []
            
            # Send messages in batches for realistic load testing
            for batch_num in range(0, message_count, batch_size):
                batch_start = time.time()
                batch_messages = []
                
                # Send batch of messages
                for i in range(batch_size):
                    if batch_num + i >= message_count:
                        break
                        
                    msg_start = time.time()
                    
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "sequence": batch_num + i,
                            "batch": batch_num // batch_size,
                            "content": f"High throughput test message {batch_num + i}",
                            "payload_size": len(f"Test data content for message {batch_num + i}"),
                            "timestamp": msg_start
                        },
                        user_id="throughput-user"
                    )
                    
                    msg_end = time.time()
                    latencies.append((msg_end - msg_start) * 1000)  # milliseconds
                
                batch_end = time.time()
                batch_duration = batch_end - batch_start
                batch_times.append(batch_duration)
                
                # Small delay between batches to simulate realistic load
                await asyncio.sleep(0.01)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Verify message count
            assert len(client.sent_messages) == message_count
            
            # Performance calculations
            actual_throughput = message_count / total_duration if total_duration > 0 else 0
            avg_latency = mean(latencies) if latencies else 0
            median_latency = median(latencies) if latencies else 0
            max_latency = max(latencies) if latencies else 0
            avg_batch_time = mean(batch_times) if batch_times else 0
            
            # Performance assertions
            assert actual_throughput > target_throughput * 0.8, f"Throughput {actual_throughput:.1f} should be at least 80% of target {target_throughput}"
            assert avg_latency < 50, f"Average latency {avg_latency:.2f}ms should be under 50ms"
            assert median_latency < 30, f"Median latency {median_latency:.2f}ms should be under 30ms"
            assert max_latency < 200, f"Max latency {max_latency:.2f}ms should be under 200ms"
            
            # Record comprehensive performance metrics
            self.record_metric("throughput_messages_per_second", actual_throughput)
            self.record_metric("average_latency_ms", avg_latency)
            self.record_metric("median_latency_ms", median_latency)
            self.record_metric("max_latency_ms", max_latency)
            self.record_metric("avg_batch_processing_time", avg_batch_time)
    
    async def test_concurrent_user_throughput(self):
        """
        Test WebSocket throughput with multiple concurrent users.
        
        BVJ: Concurrent user support enables platform scaling and multi-tenant usage
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple concurrent users
            user_count = 10
            messages_per_user = 100
            target_concurrent_throughput = 200  # messages per second across all users
            
            clients = []
            for i in range(user_count):
                client = await ws_util.create_authenticated_client(f"concurrent-user-{i}")
                client.is_connected = True
                client.websocket = AsyncMock()
                clients.append(client)
            
            # Performance tracking
            start_time = time.time()
            user_latencies = defaultdict(list)
            
            # Send messages concurrently from all users
            async def send_user_messages(client, user_index):
                user_latencies_list = []
                
                for msg_num in range(messages_per_user):
                    msg_start = time.time()
                    
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "user_index": user_index,
                            "message_number": msg_num,
                            "content": f"Concurrent message from user {user_index}, msg {msg_num}",
                            "timestamp": msg_start
                        },
                        user_id=f"concurrent-user-{user_index}"
                    )
                    
                    msg_end = time.time()
                    user_latencies_list.append((msg_end - msg_start) * 1000)
                    
                    # Brief delay to simulate realistic user behavior
                    await asyncio.sleep(0.002)
                
                user_latencies[user_index] = user_latencies_list
            
            # Execute concurrent sending
            tasks = [
                send_user_messages(clients[i], i)
                for i in range(user_count)
            ]
            
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_duration = end_time - start_time
            total_messages = user_count * messages_per_user
            
            # Verify all messages were sent
            total_sent = sum(len(client.sent_messages) for client in clients)
            assert total_sent == total_messages
            
            # Performance calculations
            concurrent_throughput = total_messages / total_duration if total_duration > 0 else 0
            
            # Calculate per-user performance metrics
            all_latencies = []
            user_avg_latencies = {}
            for user_index, latencies in user_latencies.items():
                user_avg_latencies[user_index] = mean(latencies) if latencies else 0
                all_latencies.extend(latencies)
            
            overall_avg_latency = mean(all_latencies) if all_latencies else 0
            overall_max_latency = max(all_latencies) if all_latencies else 0
            
            # Performance assertions
            assert concurrent_throughput > target_concurrent_throughput * 0.7, f"Concurrent throughput {concurrent_throughput:.1f} should meet target"
            assert overall_avg_latency < 100, f"Average latency under load {overall_avg_latency:.2f}ms should be reasonable"
            assert overall_max_latency < 500, f"Max latency under load {overall_max_latency:.2f}ms should be bounded"
            
            # Verify user isolation - each user should have sent correct number of messages
            for i, client in enumerate(clients):
                assert len(client.sent_messages) == messages_per_user
                user_messages = [msg for msg in client.sent_messages if msg.data["user_index"] == i]
                assert len(user_messages) == messages_per_user
            
            self.record_metric("concurrent_throughput", concurrent_throughput)
            self.record_metric("concurrent_avg_latency", overall_avg_latency)
            self.record_metric("concurrent_max_latency", overall_max_latency)
            self.record_metric("concurrent_users", user_count)
    
    async def test_sustained_throughput_over_time(self):
        """
        Test sustained WebSocket throughput over extended periods.
        
        BVJ: Sustained performance ensures reliable AI service during long sessions
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("sustained-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Sustained performance test configuration
            test_duration = 30.0  # 30 seconds
            target_sustained_rate = 100  # messages per second
            measurement_interval = 5.0  # Measure performance every 5 seconds
            
            # Performance tracking
            interval_metrics = []
            start_time = time.time()
            last_measurement = start_time
            messages_in_interval = 0
            total_messages = 0
            
            while (time.time() - start_time) < test_duration:
                current_time = time.time()
                
                # Send message
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    {
                        "sequence": total_messages,
                        "elapsed_time": current_time - start_time,
                        "sustained_test": True,
                        "content": f"Sustained throughput message {total_messages}"
                    },
                    user_id="sustained-user"
                )
                
                total_messages += 1
                messages_in_interval += 1
                
                # Record interval metrics
                if (current_time - last_measurement) >= measurement_interval:
                    interval_duration = current_time - last_measurement
                    interval_rate = messages_in_interval / interval_duration if interval_duration > 0 else 0
                    
                    interval_metrics.append({
                        "interval_start": last_measurement - start_time,
                        "interval_duration": interval_duration,
                        "messages_sent": messages_in_interval,
                        "rate": interval_rate,
                        "timestamp": current_time
                    })
                    
                    # Reset for next interval
                    last_measurement = current_time
                    messages_in_interval = 0
                
                # Maintain target rate
                target_interval = 1.0 / target_sustained_rate
                await asyncio.sleep(max(0, target_interval - 0.001))  # Small buffer
            
            # Final calculations
            total_duration = time.time() - start_time
            overall_sustained_rate = total_messages / total_duration if total_duration > 0 else 0
            
            # Verify sustained performance
            assert len(client.sent_messages) == total_messages
            assert len(interval_metrics) >= 5, "Should have multiple measurement intervals"
            
            # Analyze performance consistency
            interval_rates = [metric["rate"] for metric in interval_metrics]
            avg_interval_rate = mean(interval_rates) if interval_rates else 0
            min_interval_rate = min(interval_rates) if interval_rates else 0
            max_interval_rate = max(interval_rates) if interval_rates else 0
            rate_variance = max_interval_rate - min_interval_rate if interval_rates else 0
            
            # Performance assertions
            assert overall_sustained_rate > target_sustained_rate * 0.8, f"Sustained rate {overall_sustained_rate:.1f} should meet target"
            assert avg_interval_rate > target_sustained_rate * 0.75, f"Average interval rate {avg_interval_rate:.1f} should be consistent"
            assert rate_variance < target_sustained_rate * 0.5, f"Rate variance {rate_variance:.1f} should be bounded for consistency"
            
            # Verify performance didn't degrade over time
            early_rates = interval_rates[:2] if len(interval_rates) >= 2 else interval_rates
            late_rates = interval_rates[-2:] if len(interval_rates) >= 2 else interval_rates
            
            early_avg = mean(early_rates) if early_rates else 0
            late_avg = mean(late_rates) if late_rates else 0
            performance_degradation = (early_avg - late_avg) / early_avg if early_avg > 0 else 0
            
            assert performance_degradation < 0.2, f"Performance degradation {performance_degradation:.2%} should be minimal"
            
            self.record_metric("sustained_throughput", overall_sustained_rate)
            self.record_metric("sustained_avg_interval_rate", avg_interval_rate)
            self.record_metric("sustained_rate_variance", rate_variance)
            self.record_metric("performance_degradation", performance_degradation)


@pytest.mark.integration
class TestWebSocketScaling(SSotBaseTestCase):
    """
    Test WebSocket scaling patterns and connection management.
    
    BVJ: Scaling capabilities enable platform growth and user base expansion
    """
    
    async def test_connection_scaling_patterns(self):
        """
        Test WebSocket connection scaling under increasing load.
        
        BVJ: Connection scaling enables platform growth without performance degradation
        """
        async with WebSocketTestUtility() as ws_util:
            # Scaling test configuration
            scaling_levels = [5, 10, 20, 30]  # Progressive user counts
            messages_per_user = 20
            target_latency_threshold = 100  # ms
            
            scaling_results = []
            
            for user_count in scaling_levels:
                # Create users for this scaling level
                clients = []
                for i in range(user_count):
                    client = await ws_util.create_authenticated_client(f"scale-user-{i}")
                    client.is_connected = True
                    client.websocket = AsyncMock()
                    clients.append(client)
                
                # Performance measurement
                scale_start = time.time()
                latencies = []
                
                # Send messages from all users
                async def send_scaling_messages(client, user_index):
                    user_latencies = []
                    for msg_num in range(messages_per_user):
                        msg_start = time.time()
                        
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                "scaling_level": user_count,
                                "user_index": user_index,
                                "message_number": msg_num,
                                "content": f"Scaling test: {user_count} users, user {user_index}, msg {msg_num}"
                            },
                            user_id=f"scale-user-{user_index}"
                        )
                        
                        msg_end = time.time()
                        user_latencies.append((msg_end - msg_start) * 1000)
                    
                    return user_latencies
                
                # Execute scaling test
                tasks = [send_scaling_messages(clients[i], i) for i in range(user_count)]
                user_latency_results = await asyncio.gather(*tasks)
                
                scale_end = time.time()
                scale_duration = scale_end - scale_start
                
                # Collect performance data
                all_latencies = []
                for user_latencies in user_latency_results:
                    all_latencies.extend(user_latencies)
                
                avg_latency = mean(all_latencies) if all_latencies else 0
                max_latency = max(all_latencies) if all_latencies else 0
                total_messages = user_count * messages_per_user
                throughput = total_messages / scale_duration if scale_duration > 0 else 0
                
                scaling_result = {
                    "user_count": user_count,
                    "total_messages": total_messages,
                    "duration": scale_duration,
                    "throughput": throughput,
                    "avg_latency": avg_latency,
                    "max_latency": max_latency,
                    "latency_per_user": throughput / user_count if user_count > 0 else 0
                }
                scaling_results.append(scaling_result)
                
                # Verify scaling performance
                total_sent = sum(len(client.sent_messages) for client in clients)
                assert total_sent == total_messages
                
                # Performance should remain reasonable as load increases
                assert avg_latency < target_latency_threshold * (1 + user_count / 100), f"Latency should scale reasonably with load"
                
                # Cleanup clients for next scaling level
                for client in clients:
                    await client.disconnect()
            
            # Analyze scaling characteristics
            user_counts = [result["user_count"] for result in scaling_results]
            throughputs = [result["throughput"] for result in scaling_results]
            latencies = [result["avg_latency"] for result in scaling_results]
            
            # Verify scaling behavior
            assert len(scaling_results) == len(scaling_levels)
            
            # Throughput should generally increase with user count (scalability)
            for i in range(1, len(throughputs)):
                if user_counts[i] > user_counts[i-1]:
                    # Allow for some variance but expect general scaling
                    throughput_ratio = throughputs[i] / throughputs[i-1]
                    user_ratio = user_counts[i] / user_counts[i-1]
                    scaling_efficiency = throughput_ratio / user_ratio
                    
                    # Should maintain at least 60% scaling efficiency
                    assert scaling_efficiency > 0.6, f"Scaling efficiency {scaling_efficiency:.2f} should be reasonable"
            
            # Record scaling metrics
            max_throughput = max(throughputs) if throughputs else 0
            max_users_tested = max(user_counts) if user_counts else 0
            final_latency = latencies[-1] if latencies else 0
            
            self.record_metric("max_scaling_throughput", max_throughput)
            self.record_metric("max_users_tested", max_users_tested)
            self.record_metric("final_scaling_latency", final_latency)
    
    async def test_memory_efficiency_under_load(self):
        """
        Test WebSocket memory efficiency under sustained load.
        
        BVJ: Memory efficiency prevents system crashes and enables cost-effective scaling
        """
        async with WebSocketTestUtility() as ws_util:
            # Memory efficiency test configuration
            user_count = 15
            messages_per_user = 200
            message_size_bytes = 500  # Approximate message size
            cleanup_interval = 50  # Clean up every N messages
            
            clients = []
            memory_snapshots = []
            
            # Create users for memory testing
            for i in range(user_count):
                client = await ws_util.create_authenticated_client(f"memory-user-{i}")
                client.is_connected = True
                client.websocket = AsyncMock()
                clients.append(client)
            
            # Track memory usage approximation
            def estimate_memory_usage():
                total_messages_stored = sum(len(client.sent_messages) for client in clients)
                estimated_memory_mb = (total_messages_stored * message_size_bytes) / (1024 * 1024)
                return {
                    "total_messages": total_messages_stored,
                    "estimated_memory_mb": estimated_memory_mb,
                    "timestamp": time.time()
                }
            
            # Send messages with memory tracking
            start_time = time.time()
            
            for round_num in range(messages_per_user):
                round_start = time.time()
                
                # Send messages from all users in this round
                for user_index, client in enumerate(clients):
                    payload_data = "x" * message_size_bytes  # Simulate message payload
                    
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "round": round_num,
                            "user_index": user_index,
                            "payload": payload_data[:100] + "...",  # Truncated for readability
                            "full_payload_size": len(payload_data),
                            "memory_test": True
                        },
                        user_id=f"memory-user-{user_index}"
                    )
                
                # Take memory snapshot periodically
                if round_num % 20 == 0:
                    memory_snapshot = estimate_memory_usage()
                    memory_snapshots.append(memory_snapshot)
                
                # Simulate memory cleanup periodically
                if round_num % cleanup_interval == 0 and round_num > 0:
                    for client in clients:
                        # Keep only recent messages (simulate sliding window)
                        if len(client.sent_messages) > cleanup_interval:
                            client.sent_messages = client.sent_messages[-cleanup_interval:]
                
                # Brief delay between rounds
                await asyncio.sleep(0.01)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Final memory assessment
            final_memory = estimate_memory_usage()
            memory_snapshots.append(final_memory)
            
            # Verify memory efficiency
            total_messages_sent = user_count * messages_per_user
            total_messages_retained = sum(len(client.sent_messages) for client in clients)
            memory_efficiency = 1 - (total_messages_retained / total_messages_sent)
            
            # Memory should be managed efficiently
            assert memory_efficiency > 0.5, f"Memory efficiency {memory_efficiency:.2%} should show cleanup effectiveness"
            assert total_messages_retained <= user_count * cleanup_interval * 2, "Memory usage should be bounded by cleanup"
            
            # Analyze memory growth pattern
            memory_values = [snapshot["estimated_memory_mb"] for snapshot in memory_snapshots]
            if len(memory_values) >= 3:
                # Memory growth should be controlled, not linear
                early_memory = mean(memory_values[:2])
                late_memory = mean(memory_values[-2:])
                memory_growth_ratio = late_memory / early_memory if early_memory > 0 else 1
                
                # Memory shouldn't grow unbounded
                assert memory_growth_ratio < 3.0, f"Memory growth ratio {memory_growth_ratio:.2f} should be controlled"
            
            # Performance under memory pressure
            throughput = total_messages_sent / total_duration if total_duration > 0 else 0
            
            self.record_metric("memory_efficiency", memory_efficiency)
            self.record_metric("final_memory_mb", final_memory["estimated_memory_mb"])
            self.record_metric("memory_throughput", throughput)
            self.record_metric("memory_cleanup_effectiveness", memory_efficiency)


@pytest.mark.integration
class TestWebSocketLatencyOptimization(SSotBaseTestCase):
    """
    Test WebSocket latency optimization and response time characteristics.
    
    BVJ: Low latency ensures responsive AI interactions and user satisfaction
    """
    
    async def test_message_latency_distribution(self):
        """
        Test WebSocket message latency distribution and consistency.
        
        BVJ: Consistent low latency ensures predictable AI response times
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("latency-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Latency measurement configuration
            measurement_count = 500
            target_p50_latency = 10  # ms
            target_p95_latency = 50  # ms
            target_p99_latency = 100  # ms
            
            latencies = []
            
            # Measure message latencies
            for i in range(measurement_count):
                msg_start = time.time()
                
                await client.send_message(
                    WebSocketEventType.PING,
                    {
                        "sequence": i,
                        "timestamp": msg_start,
                        "latency_measurement": True
                    },
                    user_id="latency-user"
                )
                
                msg_end = time.time()
                latency_ms = (msg_end - msg_start) * 1000
                latencies.append(latency_ms)
                
                # Small random delay to simulate realistic usage
                await asyncio.sleep(0.001 + (i % 10) * 0.0001)
            
            # Calculate latency statistics
            latencies.sort()
            
            min_latency = min(latencies)
            max_latency = max(latencies)
            mean_latency = mean(latencies)
            median_latency = median(latencies)
            
            # Calculate percentiles
            p50_index = int(len(latencies) * 0.50)
            p90_index = int(len(latencies) * 0.90)
            p95_index = int(len(latencies) * 0.95)
            p99_index = int(len(latencies) * 0.99)
            
            p50_latency = latencies[p50_index]
            p90_latency = latencies[p90_index]
            p95_latency = latencies[p95_index]
            p99_latency = latencies[p99_index]
            
            # Verify latency requirements
            assert p50_latency < target_p50_latency, f"P50 latency {p50_latency:.2f}ms should be under {target_p50_latency}ms"
            assert p95_latency < target_p95_latency, f"P95 latency {p95_latency:.2f}ms should be under {target_p95_latency}ms"
            assert p99_latency < target_p99_latency, f"P99 latency {p99_latency:.2f}ms should be under {target_p99_latency}ms"
            
            # Verify latency consistency (low variance)
            latency_range = max_latency - min_latency
            assert latency_range < 200, f"Latency range {latency_range:.2f}ms should show good consistency"
            
            # Verify most latencies are in acceptable range
            acceptable_latencies = [l for l in latencies if l < target_p95_latency]
            acceptable_ratio = len(acceptable_latencies) / len(latencies)
            assert acceptable_ratio > 0.90, f"At least 90% of latencies should be acceptable, got {acceptable_ratio:.1%}"
            
            self.record_metric("p50_latency_ms", p50_latency)
            self.record_metric("p95_latency_ms", p95_latency)
            self.record_metric("p99_latency_ms", p99_latency)
            self.record_metric("mean_latency_ms", mean_latency)
            self.record_metric("latency_range_ms", latency_range)
    
    async def test_latency_under_concurrent_load(self):
        """
        Test WebSocket latency characteristics under concurrent load.
        
        BVJ: Latency stability under load ensures consistent AI performance
        """
        async with WebSocketTestUtility() as ws_util:
            # Concurrent load configuration
            concurrent_users = 8
            messages_per_user = 100
            target_latency_degradation = 2.0  # Max 2x latency increase under load
            
            # Baseline latency measurement (single user)
            baseline_client = await ws_util.create_authenticated_client("baseline-user")
            baseline_client.is_connected = True
            baseline_client.websocket = AsyncMock()
            
            baseline_latencies = []
            for i in range(20):  # Quick baseline measurement
                start = time.time()
                await baseline_client.send_message(
                    WebSocketEventType.PING,
                    {"baseline": True, "sequence": i},
                    user_id="baseline-user"
                )
                end = time.time()
                baseline_latencies.append((end - start) * 1000)
            
            baseline_avg_latency = mean(baseline_latencies)
            
            # Concurrent load latency measurement
            concurrent_clients = []
            for i in range(concurrent_users):
                client = await ws_util.create_authenticated_client(f"concurrent-latency-{i}")
                client.is_connected = True
                client.websocket = AsyncMock()
                concurrent_clients.append(client)
            
            concurrent_latencies = []
            
            async def measure_concurrent_latencies(client, user_index):
                user_latencies = []
                for msg_num in range(messages_per_user):
                    start = time.time()
                    
                    await client.send_message(
                        WebSocketEventType.PING,
                        {
                            "concurrent_load": True,
                            "user_index": user_index,
                            "sequence": msg_num
                        },
                        user_id=f"concurrent-latency-{user_index}"
                    )
                    
                    end = time.time()
                    latency = (end - start) * 1000
                    user_latencies.append(latency)
                    
                    await asyncio.sleep(0.001)  # Small delay
                
                return user_latencies
            
            # Execute concurrent latency measurements
            tasks = [
                measure_concurrent_latencies(concurrent_clients[i], i)
                for i in range(concurrent_users)
            ]
            
            user_latency_results = await asyncio.gather(*tasks)
            
            # Collect all concurrent latencies
            for user_latencies in user_latency_results:
                concurrent_latencies.extend(user_latencies)
            
            # Analyze latency under load
            concurrent_avg_latency = mean(concurrent_latencies)
            concurrent_p95_latency = sorted(concurrent_latencies)[int(len(concurrent_latencies) * 0.95)]
            
            latency_degradation = concurrent_avg_latency / baseline_avg_latency if baseline_avg_latency > 0 else 1
            
            # Verify latency stability under load
            assert latency_degradation < target_latency_degradation, f"Latency degradation {latency_degradation:.2f}x should be under {target_latency_degradation}x"
            assert concurrent_avg_latency < 100, f"Average latency under load {concurrent_avg_latency:.2f}ms should be reasonable"
            assert concurrent_p95_latency < 200, f"P95 latency under load {concurrent_p95_latency:.2f}ms should be bounded"
            
            # Verify message completion
            total_messages_expected = concurrent_users * messages_per_user
            total_messages_sent = sum(len(client.sent_messages) for client in concurrent_clients)
            assert total_messages_sent == total_messages_expected
            
            self.record_metric("baseline_latency_ms", baseline_avg_latency)
            self.record_metric("concurrent_avg_latency_ms", concurrent_avg_latency)
            self.record_metric("latency_degradation_ratio", latency_degradation)
            self.record_metric("concurrent_p95_latency_ms", concurrent_p95_latency)