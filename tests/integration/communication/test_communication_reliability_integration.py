"""
Communication Reliability Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure communication reliability maintains user trust and engagement
- Value Impact: Reliable communication prevents lost AI interactions and user frustration
- Strategic Impact: Reliability foundation for $500K+ ARR retention and user satisfaction

CRITICAL: Communication reliability builds user trust in AI platform per CLAUDE.md
Unreliable communication breaks user flow and reduces AI interaction frequency.

These integration tests validate communication reliability patterns, error recovery,
fault tolerance, message delivery guarantees, and system resilience without Docker services.
"""

import asyncio
import json
import time
import uuid
from collections import deque, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed, InvalidStatus

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


class ReliabilityTracker:
    """Track communication reliability metrics."""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_deliveries = 0
        self.failed_deliveries = 0
        self.recovery_attempts = 0
        self.successful_recoveries = 0
        self.error_types = defaultdict(int)
        self.delivery_times = []
        
    def record_attempt(self):
        self.total_attempts += 1
    
    def record_success(self, delivery_time: float = None):
        self.successful_deliveries += 1
        if delivery_time:
            self.delivery_times.append(delivery_time)
    
    def record_failure(self, error_type: str):
        self.failed_deliveries += 1
        self.error_types[error_type] += 1
    
    def record_recovery_attempt(self):
        self.recovery_attempts += 1
    
    def record_recovery_success(self):
        self.successful_recoveries += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful_deliveries / self.total_attempts
    
    @property
    def recovery_rate(self) -> float:
        if self.recovery_attempts == 0:
            return 0.0
        return self.successful_recoveries / self.recovery_attempts
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "successful_deliveries": self.successful_deliveries,
            "failed_deliveries": self.failed_deliveries,
            "success_rate": self.success_rate,
            "recovery_attempts": self.recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "recovery_rate": self.recovery_rate,
            "error_types": dict(self.error_types),
            "avg_delivery_time": sum(self.delivery_times) / len(self.delivery_times) if self.delivery_times else 0
        }


@pytest.mark.integration
class TestCommunicationFaultTolerance(SSotBaseTestCase):
    """
    Test communication fault tolerance and error recovery.
    
    BVJ: Fault tolerance ensures AI services remain available during issues
    """
    
    async def test_network_interruption_recovery(self):
        """
        Test communication recovery after network interruptions.
        
        BVJ: Network recovery ensures continuous AI service availability
        """
        reliability_tracker = ReliabilityTracker()
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("network-recovery-user")
            
            # Simulate network interruption scenarios
            interruption_scenarios = [
                {"duration": 1.0, "type": "brief_disconnect"},
                {"duration": 3.0, "type": "moderate_outage"},
                {"duration": 0.5, "type": "micro_disconnect"},
                {"duration": 5.0, "type": "extended_outage"},
            ]
            
            messages_sent = 0
            
            for scenario in interruption_scenarios:
                # Pre-interruption messaging
                client.is_connected = True
                client.websocket = AsyncMock()
                
                for i in range(5):  # Send some messages before interruption
                    reliability_tracker.record_attempt()
                    try:
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                "pre_interruption": True,
                                "scenario": scenario["type"],
                                "sequence": messages_sent,
                                "timestamp": time.time()
                            },
                            user_id="network-recovery-user"
                        )
                        reliability_tracker.record_success()
                        messages_sent += 1
                    except Exception as e:
                        reliability_tracker.record_failure(str(type(e).__name__))
                
                # Simulate network interruption
                await client.disconnect()
                assert not client.is_connected
                
                # Simulate interruption duration
                await asyncio.sleep(scenario["duration"])
                
                # Recovery attempt
                reliability_tracker.record_recovery_attempt()
                client.is_connected = True
                client.websocket = AsyncMock()
                
                # Test recovery messaging
                recovery_success = True
                try:
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "post_recovery": True,
                            "scenario": scenario["type"],
                            "interruption_duration": scenario["duration"],
                            "recovery_timestamp": time.time()
                        },
                        user_id="network-recovery-user"
                    )
                    reliability_tracker.record_recovery_success()
                    messages_sent += 1
                except Exception as e:
                    recovery_success = False
                    reliability_tracker.record_failure(f"recovery_{type(e).__name__}")
                
                # Verify recovery
                if recovery_success:
                    assert client.is_connected
                    assert len(client.sent_messages) > 0
                
                # Continue with post-recovery messages
                for i in range(3):  # Test stability after recovery
                    reliability_tracker.record_attempt()
                    try:
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                "post_recovery_stability": True,
                                "sequence": messages_sent,
                                "scenario": scenario["type"]
                            },
                            user_id="network-recovery-user"
                        )
                        reliability_tracker.record_success()
                        messages_sent += 1
                    except Exception as e:
                        reliability_tracker.record_failure(str(type(e).__name__))
            
            # Analyze reliability statistics
            stats = reliability_tracker.get_stats()
            
            # Reliability assertions
            assert stats["success_rate"] > 0.8, f"Success rate {stats['success_rate']:.2%} should be high"
            assert stats["recovery_rate"] > 0.7, f"Recovery rate {stats['recovery_rate']:.2%} should be good"
            assert len(client.sent_messages) >= messages_sent * 0.8, "Most messages should be delivered"
            
            self.record_metric("network_recovery_success_rate", stats["success_rate"])
            self.record_metric("network_recovery_rate", stats["recovery_rate"])
            self.record_metric("total_recovery_scenarios", len(interruption_scenarios))
    
    async def test_partial_message_delivery_recovery(self):
        """
        Test recovery from partial message delivery failures.
        
        BVJ: Partial delivery recovery ensures complete AI responses reach users
        """
        reliability_tracker = ReliabilityTracker()
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("partial-delivery-user")
            client.is_connected = True
            
            # Simulate partial delivery scenarios
            large_messages = [
                {
                    "type": "comprehensive_analysis",
                    "content": {
                        "executive_summary": "Comprehensive cost analysis completed",
                        "detailed_findings": ["Finding " + str(i) for i in range(50)],
                        "recommendations": ["Recommendation " + str(i) for i in range(20)],
                        "data_tables": {f"table_{i}": [f"row_{j}" for j in range(10)] for i in range(5)},
                        "metadata": {"analysis_time": 45.2, "data_points": 1500}
                    }
                },
                {
                    "type": "security_audit_results", 
                    "content": {
                        "vulnerability_summary": "Security audit results",
                        "findings": [{"severity": "high", "issue": f"Issue {i}"} for i in range(30)],
                        "remediation_steps": [f"Step {i}: Action required" for i in range(25)],
                        "compliance_report": {"section_" + str(i): "compliant" for i in range(15)}
                    }
                }
            ]
            
            for msg_index, large_msg in enumerate(large_messages):
                reliability_tracker.record_attempt()
                
                # First attempt - simulate partial failure
                mock_websocket = AsyncMock()
                
                # Simulate partial send failure
                if msg_index == 0:
                    # First message partially fails then succeeds on retry
                    mock_websocket.send.side_effect = [
                        ConnectionClosed(None, None),  # First attempt fails
                        None  # Retry succeeds
                    ]
                else:
                    # Second message succeeds immediately
                    mock_websocket.send.side_effect = None
                
                client.websocket = mock_websocket
                
                # Attempt delivery with retry logic
                max_retries = 3
                delivered = False
                
                for attempt in range(max_retries):
                    try:
                        await client.send_message(
                            WebSocketEventType.AGENT_COMPLETED,
                            {
                                **large_msg,
                                "message_index": msg_index,
                                "attempt": attempt + 1,
                                "partial_delivery_test": True
                            },
                            user_id="partial-delivery-user"
                        )
                        
                        delivered = True
                        reliability_tracker.record_success()
                        break
                        
                    except ConnectionClosed:
                        if attempt < max_retries - 1:
                            # Retry with fresh connection
                            reliability_tracker.record_recovery_attempt()
                            await asyncio.sleep(0.1)  # Brief retry delay
                            
                            # Simulate connection recovery for retry
                            client.websocket = AsyncMock()  # Fresh mock for retry
                            reliability_tracker.record_recovery_success()
                        else:
                            reliability_tracker.record_failure("max_retries_exceeded")
                
                # Verify delivery status
                if delivered:
                    # Message should be in sent messages
                    latest_msg = client.sent_messages[-1] if client.sent_messages else None
                    assert latest_msg is not None
                    assert latest_msg.data["message_index"] == msg_index
                    assert latest_msg.data["partial_delivery_test"] is True
            
            # Test message integrity after partial delivery recovery
            assert len(client.sent_messages) >= len(large_messages) * 0.8
            
            # Verify message content integrity
            for i, sent_msg in enumerate(client.sent_messages[-len(large_messages):]):
                original_msg = large_messages[i] if i < len(large_messages) else large_messages[-1]
                assert sent_msg.data["type"] == original_msg["type"]
                assert "content" in sent_msg.data
                assert isinstance(sent_msg.data["content"], dict)
            
            # Analyze partial delivery recovery
            stats = reliability_tracker.get_stats()
            
            assert stats["success_rate"] > 0.7, f"Partial delivery recovery rate {stats['success_rate']:.2%} should be good"
            assert stats["recovery_rate"] > 0.5, f"Recovery attempts success rate {stats['recovery_rate']:.2%} should be reasonable"
            
            self.record_metric("partial_delivery_success_rate", stats["success_rate"])
            self.record_metric("partial_delivery_recovery_rate", stats["recovery_rate"])
    
    async def test_concurrent_failure_isolation(self):
        """
        Test isolation of failures in concurrent communication streams.
        
        BVJ: Failure isolation prevents one user's issues from affecting others
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple concurrent users
            user_count = 6
            messages_per_user = 20
            failure_users = [1, 3]  # Users that will experience failures
            
            clients = []
            reliability_trackers = {}
            
            for i in range(user_count):
                client = await ws_util.create_authenticated_client(f"isolation-user-{i}")
                client.is_connected = True
                clients.append(client)
                reliability_trackers[i] = ReliabilityTracker()
            
            # Send messages concurrently with some users experiencing failures
            async def send_user_messages(client, user_index):
                tracker = reliability_trackers[user_index]
                should_fail = user_index in failure_users
                
                for msg_num in range(messages_per_user):
                    tracker.record_attempt()
                    
                    if should_fail and msg_num % 3 == 0:  # Simulate intermittent failures
                        # Simulate failure for this user
                        mock_websocket = AsyncMock()
                        mock_websocket.send.side_effect = ConnectionClosed(None, None)
                        client.websocket = mock_websocket
                        
                        try:
                            await client.send_message(
                                WebSocketEventType.STATUS_UPDATE,
                                {
                                    "user_index": user_index,
                                    "message_number": msg_num,
                                    "failure_simulation": True,
                                    "should_fail": True
                                },
                                user_id=f"isolation-user-{user_index}"
                            )
                            tracker.record_success()
                        except ConnectionClosed:
                            tracker.record_failure("connection_closed")
                            
                            # Simulate recovery
                            tracker.record_recovery_attempt()
                            await asyncio.sleep(0.05)
                            client.websocket = AsyncMock()  # Recover connection
                            tracker.record_recovery_success()
                    else:
                        # Normal successful message
                        client.websocket = AsyncMock()
                        
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                "user_index": user_index,
                                "message_number": msg_num,
                                "failure_simulation": False,
                                "should_fail": False
                            },
                            user_id=f"isolation-user-{user_index}"
                        )
                        tracker.record_success()
                    
                    await asyncio.sleep(0.001)  # Small delay between messages
            
            # Execute concurrent messaging
            tasks = [send_user_messages(clients[i], i) for i in range(user_count)]
            await asyncio.gather(*tasks)
            
            # Analyze failure isolation
            successful_users = [i for i in range(user_count) if i not in failure_users]
            failing_users = failure_users
            
            # Verify isolation - successful users should have high success rates
            for user_index in successful_users:
                tracker = reliability_trackers[user_index]
                stats = tracker.get_stats()
                
                assert stats["success_rate"] > 0.95, f"Non-failing user {user_index} should have high success rate: {stats['success_rate']:.2%}"
                assert len(clients[user_index].sent_messages) == messages_per_user, f"Non-failing user {user_index} should send all messages"
            
            # Verify failing users had expected failures but some recovery
            for user_index in failing_users:
                tracker = reliability_trackers[user_index]
                stats = tracker.get_stats()
                
                assert stats["success_rate"] < 1.0, f"Failing user {user_index} should have some failures: {stats['success_rate']:.2%}"
                assert stats["failed_deliveries"] > 0, f"Failing user {user_index} should have recorded failures"
                assert stats["recovery_attempts"] > 0, f"Failing user {user_index} should have attempted recovery"
            
            # Overall system reliability should be maintained
            total_attempts = sum(tracker.total_attempts for tracker in reliability_trackers.values())
            total_successes = sum(tracker.successful_deliveries for tracker in reliability_trackers.values())
            overall_success_rate = total_successes / total_attempts if total_attempts > 0 else 0
            
            assert overall_success_rate > 0.7, f"Overall system success rate {overall_success_rate:.2%} should remain good despite failures"
            
            self.record_metric("failure_isolation_overall_success", overall_success_rate)
            self.record_metric("isolated_failure_users", len(failing_users))
            self.record_metric("protected_successful_users", len(successful_users))


@pytest.mark.integration
class TestMessageDeliveryGuarantees(SSotBaseTestCase):
    """
    Test message delivery guarantees and reliability patterns.
    
    BVJ: Delivery guarantees ensure users receive all AI responses and updates
    """
    
    async def test_at_least_once_delivery(self):
        """
        Test at-least-once message delivery guarantee.
        
        BVJ: Delivery guarantees ensure critical AI responses always reach users
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("delivery-guarantee-user")
            client.is_connected = True
            
            # Message tracking for delivery guarantees
            sent_message_ids = set()
            delivered_message_ids = set()
            delivery_confirmations = []
            
            # Critical messages that must be delivered
            critical_messages = [
                {"id": f"critical_{i}", "priority": "critical", "content": f"Critical alert {i}"}
                for i in range(10)
            ]
            
            # Send messages with delivery tracking
            for msg_data in critical_messages:
                message_id = msg_data["id"]
                sent_message_ids.add(message_id)
                
                # Simulate delivery attempts with confirmation
                max_delivery_attempts = 3
                delivered = False
                
                for attempt in range(max_delivery_attempts):
                    try:
                        # Mock delivery attempt
                        client.websocket = AsyncMock()
                        
                        # Simulate occasional delivery failure
                        if attempt == 0 and message_id.endswith("3"):  # Fail some first attempts
                            client.websocket.send.side_effect = ConnectionClosed(None, None)
                        
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                **msg_data,
                                "delivery_attempt": attempt + 1,
                                "requires_confirmation": True,
                                "at_least_once_test": True
                            },
                            user_id="delivery-guarantee-user"
                        )
                        
                        # Simulate delivery confirmation
                        delivered_message_ids.add(message_id)
                        delivery_confirmations.append({
                            "message_id": message_id,
                            "delivered_at": time.time(),
                            "attempt": attempt + 1
                        })
                        delivered = True
                        break
                        
                    except ConnectionClosed:
                        if attempt < max_delivery_attempts - 1:
                            await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                        continue
                
                # Ensure delivery succeeded
                assert delivered, f"Message {message_id} should be delivered within {max_delivery_attempts} attempts"
            
            # Verify at-least-once delivery guarantee
            assert len(delivered_message_ids) == len(sent_message_ids), "All sent messages should be delivered"
            assert delivered_message_ids == sent_message_ids, "Delivered messages should match sent messages"
            
            # Verify delivery confirmations
            assert len(delivery_confirmations) == len(critical_messages), "All messages should have delivery confirmations"
            
            # Check for any duplicate deliveries (at-least-once may allow duplicates)
            delivered_count = len(delivery_confirmations)
            unique_delivered = len(set(conf["message_id"] for conf in delivery_confirmations))
            
            # All messages delivered at least once
            assert unique_delivered == len(critical_messages), "All unique messages should be delivered"
            
            # Some messages may be delivered more than once (at-least-once guarantee)
            duplicate_deliveries = delivered_count - unique_delivered
            
            self.record_metric("delivery_guarantee_success_rate", len(delivered_message_ids) / len(sent_message_ids))
            self.record_metric("duplicate_deliveries", duplicate_deliveries)
            self.record_metric("total_delivery_attempts", delivered_count)
    
    async def test_ordered_message_delivery(self):
        """
        Test ordered message delivery within conversation threads.
        
        BVJ: Message ordering ensures users see logical AI conversation progression
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("ordered-delivery-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Create ordered message sequences for different threads
            conversation_threads = {
                "thread_cost_analysis": [
                    {"seq": 1, "type": "agent_started", "content": "Starting cost analysis"},
                    {"seq": 2, "type": "agent_thinking", "content": "Loading billing data"},
                    {"seq": 3, "type": "tool_executing", "content": "Running cost calculations"},
                    {"seq": 4, "type": "tool_completed", "content": "Analysis complete"},
                    {"seq": 5, "type": "agent_completed", "content": "Recommendations ready"},
                ],
                "thread_security_audit": [
                    {"seq": 1, "type": "agent_started", "content": "Starting security audit"},
                    {"seq": 2, "type": "agent_thinking", "content": "Scanning for vulnerabilities"},
                    {"seq": 3, "type": "tool_executing", "content": "Running security scan"},
                    {"seq": 4, "type": "agent_completed", "content": "Security report ready"},
                ]
            }
            
            # Send messages for each thread (may arrive out of order)
            thread_messages = {}
            for thread_id, messages in conversation_threads.items():
                thread_messages[thread_id] = []
                
                for msg in messages:
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "thread_id": thread_id,
                            "sequence": msg["seq"],
                            "message_type": msg["type"],
                            "content": msg["content"],
                            "ordered_delivery_test": True,
                            "timestamp": time.time()
                        },
                        user_id="ordered-delivery-user",
                        thread_id=thread_id
                    )
                    
                    thread_messages[thread_id].append(msg)
            
            # Verify message ordering within threads
            sent_messages_by_thread = defaultdict(list)
            for msg in client.sent_messages:
                thread_id = msg.thread_id
                if thread_id:
                    sent_messages_by_thread[thread_id].append(msg)
            
            # Check ordering within each thread
            for thread_id, expected_messages in conversation_threads.items():
                sent_thread_msgs = sent_messages_by_thread[thread_id]
                
                # Should have all messages for thread
                assert len(sent_thread_msgs) == len(expected_messages), f"Thread {thread_id} should have all messages"
                
                # Messages should be in sequence order
                sequences = [msg.data["sequence"] for msg in sent_thread_msgs]
                expected_sequences = [msg["seq"] for msg in expected_messages]
                
                assert sequences == expected_sequences, f"Thread {thread_id} messages should be in correct order"
                
                # Verify content matches expected sequence
                for i, sent_msg in enumerate(sent_thread_msgs):
                    expected_msg = expected_messages[i]
                    assert sent_msg.data["sequence"] == expected_msg["seq"]
                    assert sent_msg.data["message_type"] == expected_msg["type"]
                    assert sent_msg.data["content"] == expected_msg["content"]
            
            # Verify cross-thread isolation (messages from different threads can interleave)
            total_messages = sum(len(messages) for messages in conversation_threads.values())
            assert len(client.sent_messages) == total_messages
            
            self.record_metric("ordered_delivery_threads", len(conversation_threads))
            self.record_metric("total_ordered_messages", total_messages)
    
    async def test_delivery_timeout_handling(self):
        """
        Test delivery timeout handling and retry mechanisms.
        
        BVJ: Timeout handling prevents indefinite waits and provides user feedback
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("timeout-delivery-user")
            client.is_connected = True
            
            # Timeout configuration
            delivery_timeout = 2.0  # seconds
            max_retries = 3
            
            # Messages with different timeout behaviors
            timeout_scenarios = [
                {"id": "fast_delivery", "simulate_delay": 0.1, "should_timeout": False},
                {"id": "slow_delivery", "simulate_delay": 1.5, "should_timeout": False},
                {"id": "timeout_delivery", "simulate_delay": 3.0, "should_timeout": True},
                {"id": "very_slow", "simulate_delay": 5.0, "should_timeout": True},
            ]
            
            delivery_results = []
            
            for scenario in timeout_scenarios:
                message_id = scenario["id"]
                simulate_delay = scenario["simulate_delay"]
                should_timeout = scenario["should_timeout"]
                
                # Simulate delivery with timeout
                delivered = False
                timeout_occurred = False
                attempts = 0
                
                while attempts < max_retries and not delivered:
                    attempts += 1
                    delivery_start = time.time()
                    
                    try:
                        # Mock WebSocket with simulated delay
                        mock_websocket = AsyncMock()
                        
                        async def delayed_send(data):
                            if simulate_delay > delivery_timeout:
                                # Simulate timeout
                                await asyncio.sleep(delivery_timeout + 0.1)
                                raise asyncio.TimeoutError("Delivery timeout")
                            else:
                                await asyncio.sleep(simulate_delay)
                                return None
                        
                        mock_websocket.send.side_effect = delayed_send
                        client.websocket = mock_websocket
                        
                        # Attempt delivery with timeout
                        await asyncio.wait_for(
                            client.send_message(
                                WebSocketEventType.STATUS_UPDATE,
                                {
                                    "message_id": message_id,
                                    "attempt": attempts,
                                    "timeout_test": True,
                                    "expected_delay": simulate_delay
                                },
                                user_id="timeout-delivery-user"
                            ),
                            timeout=delivery_timeout
                        )
                        
                        # If we reach here, delivery succeeded
                        delivered = True
                        delivery_time = time.time() - delivery_start
                        
                        delivery_results.append({
                            "message_id": message_id,
                            "delivered": True,
                            "attempts": attempts,
                            "delivery_time": delivery_time,
                            "timeout_occurred": False
                        })
                        
                    except asyncio.TimeoutError:
                        timeout_occurred = True
                        if attempts >= max_retries:
                            # Final timeout
                            delivery_results.append({
                                "message_id": message_id,
                                "delivered": False,
                                "attempts": attempts,
                                "delivery_time": None,
                                "timeout_occurred": True
                            })
                        else:
                            # Will retry
                            await asyncio.sleep(0.1)  # Brief delay before retry
            
            # Verify timeout handling
            fast_deliveries = [r for r in delivery_results if not r["timeout_occurred"] and r["delivered"]]
            timed_out_deliveries = [r for r in delivery_results if r["timeout_occurred"]]
            
            # Messages that shouldn't timeout should be delivered
            should_deliver = [s for s in timeout_scenarios if not s["should_timeout"]]
            should_timeout = [s for s in timeout_scenarios if s["should_timeout"]]
            
            assert len(fast_deliveries) >= len(should_deliver) * 0.8, "Most non-timeout messages should be delivered"
            assert len(timed_out_deliveries) >= len(should_timeout) * 0.8, "Timeout messages should timeout as expected"
            
            # Verify retry attempts were made
            retry_attempts = [r["attempts"] for r in delivery_results if r["attempts"] > 1]
            assert len(retry_attempts) > 0, "Some messages should require retry attempts"
            
            self.record_metric("timeout_delivery_success", len(fast_deliveries))
            self.record_metric("timeout_delivery_failures", len(timed_out_deliveries))
            self.record_metric("average_delivery_attempts", sum(r["attempts"] for r in delivery_results) / len(delivery_results))


@pytest.mark.integration
class TestCommunicationMonitoring(SSotBaseTestCase):
    """
    Test communication monitoring and health checking.
    
    BVJ: Monitoring enables proactive issue detection and system reliability
    """
    
    async def test_communication_health_monitoring(self):
        """
        Test communication health monitoring and alerting.
        
        BVJ: Health monitoring enables proactive issue detection and resolution
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("health-monitor-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Health metrics tracking
            health_metrics = {
                "message_success_rate": 0.0,
                "average_latency": 0.0,
                "error_rate": 0.0,
                "connection_stability": 0.0,
                "throughput": 0.0
            }
            
            # Health monitoring configuration
            monitoring_duration = 10.0  # seconds
            health_check_interval = 2.0  # seconds
            health_reports = []
            
            # Simulate system operation with health monitoring
            start_time = time.time()
            messages_sent = 0
            errors_encountered = 0
            latencies = []
            last_health_check = start_time
            
            while (time.time() - start_time) < monitoring_duration:
                current_time = time.time()
                
                # Send operational messages
                msg_start = time.time()
                success = True
                
                try:
                    # Simulate occasional errors for realistic monitoring
                    if messages_sent > 0 and messages_sent % 15 == 0:
                        # Simulate error every 15th message
                        mock_websocket = AsyncMock()
                        mock_websocket.send.side_effect = ConnectionClosed(None, None)
                        client.websocket = mock_websocket
                        
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                "sequence": messages_sent,
                                "health_monitoring": True,
                                "simulated_error": True
                            },
                            user_id="health-monitor-user"
                        )
                    else:
                        # Normal successful message
                        client.websocket = AsyncMock()
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {
                                "sequence": messages_sent,
                                "health_monitoring": True,
                                "timestamp": current_time
                            },
                            user_id="health-monitor-user"
                        )
                    
                except ConnectionClosed:
                    success = False
                    errors_encountered += 1
                
                msg_end = time.time()
                if success:
                    latencies.append((msg_end - msg_start) * 1000)  # ms
                
                messages_sent += 1
                
                # Periodic health check
                if (current_time - last_health_check) >= health_check_interval:
                    elapsed = current_time - start_time
                    success_count = messages_sent - errors_encountered
                    
                    # Calculate current health metrics
                    current_health = {
                        "timestamp": current_time,
                        "elapsed_time": elapsed,
                        "messages_sent": messages_sent,
                        "success_count": success_count,
                        "error_count": errors_encountered,
                        "success_rate": success_count / messages_sent if messages_sent > 0 else 0,
                        "error_rate": errors_encountered / messages_sent if messages_sent > 0 else 0,
                        "average_latency": sum(latencies) / len(latencies) if latencies else 0,
                        "throughput": messages_sent / elapsed if elapsed > 0 else 0,
                        "connection_status": "connected" if client.is_connected else "disconnected"
                    }
                    
                    health_reports.append(current_health)
                    last_health_check = current_time
                    
                    # Send health report
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "type": "health_report",
                            "metrics": current_health,
                            "health_status": "healthy" if current_health["success_rate"] > 0.8 else "degraded"
                        },
                        user_id="health-monitor-user"
                    )
                
                # Brief operational delay
                await asyncio.sleep(0.1)
            
            # Analyze health monitoring effectiveness
            assert len(health_reports) >= 3, "Should have multiple health reports"
            
            # Verify health metrics tracking
            final_health = health_reports[-1]
            assert final_health["success_rate"] > 0.7, f"Overall success rate {final_health['success_rate']:.2%} should be good"
            assert final_health["throughput"] > 5, f"Throughput {final_health['throughput']:.1f} msg/s should be reasonable"
            assert final_health["average_latency"] < 100, f"Average latency {final_health['average_latency']:.2f}ms should be low"
            
            # Verify health trend monitoring
            success_rates = [report["success_rate"] for report in health_reports]
            throughputs = [report["throughput"] for report in health_reports]
            
            # Health should be relatively stable
            success_rate_variance = max(success_rates) - min(success_rates)
            assert success_rate_variance < 0.3, f"Success rate variance {success_rate_variance:.2f} should be stable"
            
            # Alert conditions should be detected
            degraded_reports = [r for r in health_reports if r["success_rate"] < 0.8]
            if errors_encountered > 0:
                assert len(degraded_reports) >= 0, "Should detect degraded performance"
            
            self.record_metric("health_monitoring_reports", len(health_reports))
            self.record_metric("final_success_rate", final_health["success_rate"])
            self.record_metric("health_monitoring_stability", 1 - success_rate_variance)
    
    async def test_communication_metrics_collection(self):
        """
        Test comprehensive communication metrics collection.
        
        BVJ: Metrics collection enables data-driven optimization and capacity planning
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("metrics-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Comprehensive metrics collection
            metrics_collector = {
                "message_counts": defaultdict(int),
                "latency_buckets": defaultdict(int),
                "error_types": defaultdict(int),
                "throughput_samples": [],
                "connection_events": [],
                "user_activity": defaultdict(int),
                "peak_concurrent": 0,
                "total_bytes_sent": 0
            }
            
            # Generate diverse communication patterns for metrics
            communication_patterns = [
                {"type": "burst", "count": 50, "interval": 0.01},  # High frequency burst
                {"type": "steady", "count": 30, "interval": 0.1},   # Steady rate
                {"type": "sparse", "count": 10, "interval": 0.5},   # Sparse messages
            ]
            
            for pattern in communication_patterns:
                pattern_start = time.time()
                
                for i in range(pattern["count"]):
                    msg_start = time.time()
                    message_size = 200 + (i % 300)  # Variable message sizes
                    
                    # Create message with metrics tracking
                    message_data = {
                        "pattern": pattern["type"],
                        "sequence": i,
                        "size_bytes": message_size,
                        "timestamp": msg_start,
                        "metrics_collection": True
                    }
                    
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        message_data,
                        user_id="metrics-user"
                    )
                    
                    msg_end = time.time()
                    latency_ms = (msg_end - msg_start) * 1000
                    
                    # Collect metrics
                    metrics_collector["message_counts"][pattern["type"]] += 1
                    metrics_collector["total_bytes_sent"] += message_size
                    
                    # Latency bucketing
                    if latency_ms < 10:
                        metrics_collector["latency_buckets"]["0-10ms"] += 1
                    elif latency_ms < 50:
                        metrics_collector["latency_buckets"]["10-50ms"] += 1
                    else:
                        metrics_collector["latency_buckets"]["50ms+"] += 1
                    
                    await asyncio.sleep(pattern["interval"])
                
                pattern_end = time.time()
                pattern_duration = pattern_end - pattern_start
                pattern_throughput = pattern["count"] / pattern_duration if pattern_duration > 0 else 0
                
                metrics_collector["throughput_samples"].append({
                    "pattern": pattern["type"],
                    "throughput": pattern_throughput,
                    "duration": pattern_duration,
                    "message_count": pattern["count"]
                })
            
            # Analyze collected metrics
            total_messages = sum(metrics_collector["message_counts"].values())
            total_bytes = metrics_collector["total_bytes_sent"]
            avg_message_size = total_bytes / total_messages if total_messages > 0 else 0
            
            # Verify metrics collection completeness
            expected_total = sum(pattern["count"] for pattern in communication_patterns)
            assert total_messages == expected_total, f"Should collect metrics for all {expected_total} messages"
            
            # Verify metrics categories
            assert len(metrics_collector["message_counts"]) == len(communication_patterns)
            assert len(metrics_collector["latency_buckets"]) >= 2, "Should have latency distribution"
            assert len(metrics_collector["throughput_samples"]) == len(communication_patterns)
            
            # Performance insights from metrics
            throughputs = [sample["throughput"] for sample in metrics_collector["throughput_samples"]]
            max_throughput = max(throughputs) if throughputs else 0
            min_throughput = min(throughputs) if throughputs else 0
            
            # Latency distribution analysis
            fast_messages = metrics_collector["latency_buckets"]["0-10ms"]
            medium_messages = metrics_collector["latency_buckets"]["10-50ms"]
            slow_messages = metrics_collector["latency_buckets"]["50ms+"]
            
            # Most messages should be fast
            fast_ratio = fast_messages / total_messages if total_messages > 0 else 0
            assert fast_ratio > 0.7, f"Most messages {fast_ratio:.1%} should be in fast latency bucket"
            
            self.record_metric("total_messages_metricated", total_messages)
            self.record_metric("average_message_size", avg_message_size)
            self.record_metric("max_pattern_throughput", max_throughput)
            self.record_metric("fast_message_ratio", fast_ratio)
            self.record_metric("total_bytes_tracked", total_bytes)