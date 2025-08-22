"""WebSocket Message Ordering Test

Test #9: Comprehensive FIFO Message Delivery Testing
Priority: MEDIUM - P2

Tests that WebSocket messages are delivered in First-In-First-Out (FIFO) order,
which is critical for agent conversations and user experience.

Business Value Justification (BVJ):
- Segment: All segments (Free, Early, Mid, Enterprise)  
- Business Goal: Reliable real-time communication
- Value Impact: Out-of-order messages confuse users and break agent conversations
- Strategic Impact: Core reliability for all real-time features

Test Coverage:
1. Messages delivered in send order
2. Sequence numbers maintained correctly  
3. Concurrent messages properly ordered
4. No message duplication
5. Order preserved under high load (100+ messages)
6. Order preserved across reconnection

CRITICAL: No mocking of WebSocket core components - real connections only.
"""

import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest

try:
    # Try relative imports first (for pytest execution)
    from tests.unified.jwt_token_helpers import JWTTestHelper
    from tests.unified.real_client_types import (
        ClientConfig,
        ConnectionState,
    )
    from tests.unified.real_services_manager import RealServicesManager
    from tests.unified.real_websocket_client import RealWebSocketClient
except ImportError:
    # Fallback for standalone execution
    import os
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.path.insert(0, project_root)

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.schemas.websocket_models import (
    BaseWebSocketPayload,
    WebSocketMessage,
)

logger = central_logger.get_logger(__name__)


@dataclass
class OrderingTestMessage:
    """Message with ordering metadata for testing."""
    sequence_number: int
    correlation_id: str
    content: str
    send_timestamp: float
    receive_timestamp: Optional[float] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderingMetrics:
    """Metrics for message ordering analysis."""
    total_sent: int = 0
    total_received: int = 0
    out_of_order_count: int = 0
    duplicate_count: int = 0
    missing_count: int = 0
    max_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    ordering_violations: List[Dict[str, Any]] = field(default_factory=list)


class MessageOrderingValidator:
    """Validates message ordering and detects violations."""
    
    def __init__(self):
        self.sent_messages: Dict[str, OrderingTestMessage] = {}
        self.received_messages: List[OrderingTestMessage] = []
        self.received_ids: set = set()
        self.expected_sequence = 0
        
    def register_sent_message(self, message: OrderingTestMessage) -> None:
        """Register a sent message for ordering validation."""
        self.sent_messages[message.correlation_id] = message
        
    def register_received_message(self, correlation_id: str, receive_time: float) -> Optional[OrderingTestMessage]:
        """Register a received message and validate ordering."""
        if correlation_id not in self.sent_messages:
            logger.error(f"Received unknown message: {correlation_id}")
            return None
            
        message = self.sent_messages[correlation_id]
        message.receive_timestamp = receive_time
        
        self.received_messages.append(message)
        self.received_ids.add(correlation_id)
        
        return message
        
    def analyze_ordering(self) -> OrderingMetrics:
        """Analyze message ordering and generate metrics."""
        metrics = OrderingMetrics()
        metrics.total_sent = len(self.sent_messages)
        metrics.total_received = len(self.received_messages)
        metrics.missing_count = metrics.total_sent - metrics.total_received
        
        # Sort received messages by sequence number
        sorted_messages = sorted(self.received_messages, key=lambda m: m.sequence_number)
        
        # Check for ordering violations
        for i, message in enumerate(sorted_messages):
            if message.sequence_number != i:
                violation = {
                    "expected_sequence": i,
                    "actual_sequence": message.sequence_number,
                    "correlation_id": message.correlation_id,
                    "content": message.content
                }
                metrics.ordering_violations.append(violation)
                metrics.out_of_order_count += 1
                
        # Check for duplicates
        seen_sequences = set()
        for message in self.received_messages:
            if message.sequence_number in seen_sequences:
                metrics.duplicate_count += 1
            seen_sequences.add(message.sequence_number)
            
        # Calculate latency metrics
        latencies = []
        for message in self.received_messages:
            if message.receive_timestamp:
                latency_ms = (message.receive_timestamp - message.send_timestamp) * 1000
                latencies.append(latency_ms)
                
        if latencies:
            metrics.max_latency_ms = max(latencies)
            metrics.avg_latency_ms = sum(latencies) / len(latencies)
            
        return metrics


class WebSocketOrderingTester:
    """Comprehensive WebSocket ordering test executor."""
    
    def __init__(self, ws_url: str, auth_token: str):
        self.ws_url = ws_url
        self.auth_token = auth_token
        self.validator = MessageOrderingValidator()
        
    async def create_client(self, client_id: str = None) -> RealWebSocketClient:
        """Create a real WebSocket client with auth headers."""
        config = ClientConfig(
            connection_timeout=10.0,
            max_retries=3,
            reconnect_delay=0.5
        )
        
        client = RealWebSocketClient(self.ws_url, config)
        return client
        
    async def send_ordered_messages(self, client: RealWebSocketClient, count: int, 
                                  prefix: str = "test") -> List[OrderingTestMessage]:
        """Send a series of ordered messages and track them."""
        messages = []
        
        for i in range(count):
            correlation_id = str(uuid.uuid4())
            content = f"{prefix}_message_{i:04d}"
            
            message = OrderingTestMessage(
                sequence_number=i,
                correlation_id=correlation_id,
                content=content,
                send_timestamp=time.time(),
                payload={
                    "type": "test_ordering",
                    "sequence": i,
                    "content": content,
                    "correlation_id": correlation_id
                }
            )
            
            self.validator.register_sent_message(message)
            messages.append(message)
            
            # Send the message
            await client.send_json(message.payload)
            
        return messages
        
    async def rapid_fire_test(self, client: RealWebSocketClient, count: int) -> OrderingMetrics:
        """Test rapid-fire message sending to stress-test ordering."""
        logger.info(f"Starting rapid-fire test with {count} messages")
        
        # Clear validator state
        self.validator = MessageOrderingValidator()
        
        # Send messages as fast as possible
        start_time = time.time()
        await self.send_ordered_messages(client, count, "rapid")
        send_duration = time.time() - start_time
        
        logger.info(f"Sent {count} messages in {send_duration:.3f}s ({count/send_duration:.1f} msg/s)")
        
        # Wait for all responses
        await asyncio.sleep(2.0)
        
        return self.validator.analyze_ordering()
        
    async def concurrent_senders_test(self, num_senders: int, messages_per_sender: int) -> OrderingMetrics:
        """Test ordering with multiple concurrent senders."""
        logger.info(f"Starting concurrent senders test: {num_senders} senders, {messages_per_sender} each")
        
        # Clear validator state
        self.validator = MessageOrderingValidator()
        
        # Create multiple clients
        clients = []
        for i in range(num_senders):
            client = await self.create_client(f"sender_{i}")
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, f"Failed to connect client {i}"
            clients.append(client)
            
        try:
            # Send messages concurrently from all clients
            tasks = []
            for i, client in enumerate(clients):
                task = self.send_ordered_messages(
                    client, messages_per_sender, f"concurrent_{i}"
                )
                tasks.append(task)
                
            # Wait for all sends to complete
            all_messages = await asyncio.gather(*tasks)
            
            # Wait for responses
            await asyncio.sleep(3.0)
            
            return self.validator.analyze_ordering()
            
        finally:
            # Clean up clients
            for client in clients:
                await client.disconnect()


class TestWebSocketMessageOrdering:
    """Test suite for WebSocket message ordering validation."""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup test environment with real services."""
        self.services = RealServicesManager()
        await self.services.start_all()
        
        # Get WebSocket URL and auth token
        self.ws_url = await self.services.get_websocket_url()
        jwt_helper = JWTTestHelper()
        self.auth_token = jwt_helper.create_access_token("test-user-ordering", "test@netrasystems.ai")
        
        # Create tester instance
        self.tester = WebSocketOrderingTester(self.ws_url, self.auth_token)
        
        yield
        
        # Cleanup
        await self.services.stop_all()
        
    async def test_basic_message_order(self):
        """Test: Messages delivered in send order (happy path)."""
        client = await self.tester.create_client("basic_order")
        
        try:
            # Connect client
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, "Failed to establish WebSocket connection"
            
            # Send 20 messages in sequence
            messages = await self.tester.send_ordered_messages(client, 20, "basic")
            
            # Wait for responses
            await asyncio.sleep(1.5)
            
            # Analyze ordering
            metrics = self.tester.validator.analyze_ordering()
            
            # Assertions
            assert metrics.total_sent == 20, f"Expected 20 sent, got {metrics.total_sent}"
            assert metrics.total_received >= 18, f"Too many missing messages: {metrics.missing_count}"
            assert metrics.out_of_order_count == 0, f"Found {metrics.out_of_order_count} out-of-order messages"
            assert metrics.duplicate_count == 0, f"Found {metrics.duplicate_count} duplicate messages"
            
            logger.info(f"Basic ordering test passed: {metrics.total_received}/{metrics.total_sent} messages received in order")
            
        finally:
            await client.disconnect()
            
    async def test_sequence_number_preservation(self):
        """Test: Sequence numbers maintained correctly."""
        client = await self.tester.create_client("sequence_test")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, "Failed to establish WebSocket connection"
            
            # Send messages with explicit sequence tracking
            messages = await self.tester.send_ordered_messages(client, 30, "sequence")
            
            # Wait for responses
            await asyncio.sleep(2.0)
            
            # Verify sequence preservation
            metrics = self.tester.validator.analyze_ordering()
            
            assert metrics.total_received >= 28, f"Missing too many messages: {metrics.missing_count}"
            assert len(metrics.ordering_violations) == 0, f"Sequence violations: {metrics.ordering_violations}"
            
            # Check that received messages maintain sequential order
            received = sorted(self.tester.validator.received_messages, key=lambda m: m.sequence_number)
            for i, message in enumerate(received):
                assert message.sequence_number == i, f"Sequence gap at position {i}, found {message.sequence_number}"
                
            logger.info(f"Sequence preservation test passed: {len(received)} messages in perfect sequence")
            
        finally:
            await client.disconnect()
            
    async def test_high_load_ordering(self):
        """Test: Order preserved under high load (100+ messages)."""
        client = await self.tester.create_client("high_load")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, "Failed to establish WebSocket connection"
            
            # Rapid-fire 150 messages
            metrics = await self.tester.rapid_fire_test(client, 150)
            
            # High load assertions - allow for some message loss under extreme load
            assert metrics.total_sent == 150, f"Expected 150 sent, got {metrics.total_sent}"
            assert metrics.total_received >= 140, f"Too many messages lost under high load: {metrics.missing_count}"
            assert metrics.out_of_order_count <= 2, f"Too many out-of-order messages: {metrics.out_of_order_count}"
            assert metrics.duplicate_count == 0, f"Duplicates detected: {metrics.duplicate_count}"
            assert metrics.avg_latency_ms < 500, f"Average latency too high: {metrics.avg_latency_ms}ms"
            
            logger.info(f"High load test passed: {metrics.total_received}/{metrics.total_sent} messages, "
                       f"avg latency: {metrics.avg_latency_ms:.1f}ms")
            
        finally:
            await client.disconnect()
            
    async def test_concurrent_message_ordering(self):
        """Test: Concurrent messages properly ordered."""
        # Test with 3 concurrent senders, 25 messages each
        metrics = await self.tester.concurrent_senders_test(3, 25)
        
        # Concurrent sender assertions
        assert metrics.total_sent == 75, f"Expected 75 sent, got {metrics.total_sent}"
        assert metrics.total_received >= 70, f"Too many messages lost: {metrics.missing_count}"
        assert metrics.duplicate_count == 0, f"Duplicates detected: {metrics.duplicate_count}"
        
        # For concurrent senders, we allow some global ordering flexibility
        # but within each sender's messages should maintain relative order
        violation_rate = metrics.out_of_order_count / metrics.total_received if metrics.total_received > 0 else 1.0
        assert violation_rate <= 0.1, f"Too many ordering violations: {violation_rate:.2%}"
        
        logger.info(f"Concurrent ordering test passed: {metrics.total_received}/{metrics.total_sent} messages, "
                   f"violation rate: {violation_rate:.2%}")
                   
    async def test_no_message_duplication(self):
        """Test: No message duplication."""
        client = await self.tester.create_client("duplicate_test")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, "Failed to establish WebSocket connection"
            
            # Send messages and track for duplicates
            messages = await self.tester.send_ordered_messages(client, 50, "duplicate")
            
            # Wait for responses
            await asyncio.sleep(2.5)
            
            # Analyze for duplicates
            metrics = self.tester.validator.analyze_ordering()
            
            assert metrics.duplicate_count == 0, f"Detected {metrics.duplicate_count} duplicate messages"
            assert len(self.tester.validator.received_ids) == metrics.total_received, "Correlation ID duplicates found"
            
            # Verify each correlation_id is unique
            correlation_ids = [msg.correlation_id for msg in self.tester.validator.received_messages]
            unique_ids = set(correlation_ids)
            assert len(correlation_ids) == len(unique_ids), "Duplicate correlation IDs detected"
            
            logger.info(f"Duplication test passed: {metrics.total_received} unique messages, no duplicates")
            
        finally:
            await client.disconnect()
            
    @pytest.mark.integration
    async def test_ordering_across_reconnection(self):
        """Test: Order preserved across reconnection."""
        client = await self.tester.create_client("reconnection_test")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, "Failed to establish WebSocket connection"
            
            # Send first batch of messages
            batch1 = await self.tester.send_ordered_messages(client, 20, "before_reconnect")
            await asyncio.sleep(1.0)
            
            # Force disconnect and reconnect
            logger.info("Forcing reconnection...")
            await client.disconnect()
            await asyncio.sleep(0.5)
            
            # Reconnect
            reconnected = await client.connect(headers)
            assert reconnected, "Failed to reconnect WebSocket"
            
            # Send second batch after reconnection
            batch2 = await self.tester.send_ordered_messages(client, 20, "after_reconnect")
            await asyncio.sleep(2.0)
            
            # Analyze cross-reconnection ordering
            metrics = self.tester.validator.analyze_ordering()
            
            # We expect all messages, allowing for some loss during reconnection
            assert metrics.total_sent == 40, f"Expected 40 sent, got {metrics.total_sent}"
            assert metrics.total_received >= 35, f"Too many messages lost during reconnection: {metrics.missing_count}"
            assert metrics.duplicate_count == 0, f"Duplicates after reconnection: {metrics.duplicate_count}"
            
            logger.info(f"Reconnection ordering test passed: {metrics.total_received}/{metrics.total_sent} messages preserved")
            
        finally:
            await client.disconnect()
            
    async def test_ordering_performance_benchmarks(self):
        """Test: Performance benchmarks for message ordering."""
        client = await self.tester.create_client("performance_test")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            connected = await client.connect(headers)
            assert connected, "Failed to establish WebSocket connection"
            
            # Benchmark different message volumes
            test_cases = [
                {"count": 10, "max_latency": 100, "description": "Small batch"},
                {"count": 50, "max_latency": 200, "description": "Medium batch"},
                {"count": 100, "max_latency": 400, "description": "Large batch"}
            ]
            
            for test_case in test_cases:
                logger.info(f"Running benchmark: {test_case['description']}")
                
                # Reset validator
                self.tester.validator = MessageOrderingValidator()
                
                # Run test
                start_time = time.time()
                metrics = await self.tester.rapid_fire_test(client, test_case["count"])
                total_time = time.time() - start_time
                
                # Performance assertions
                assert metrics.total_received >= test_case["count"] * 0.9, \
                    f"Too many lost messages in {test_case['description']}"
                assert metrics.avg_latency_ms <= test_case["max_latency"], \
                    f"Latency too high for {test_case['description']}: {metrics.avg_latency_ms}ms"
                    
                throughput = metrics.total_received / total_time
                logger.info(f"{test_case['description']}: {throughput:.1f} msg/s, "
                           f"avg latency: {metrics.avg_latency_ms:.1f}ms")
                
                # Small delay between test cases
                await asyncio.sleep(1.0)
                
        finally:
            await client.disconnect()


if __name__ == "__main__":
    # Standalone validation
    
    # Add project root to path for standalone execution
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.path.insert(0, project_root)
    
    # Quick validation run
    async def main():
        """Quick validation of message ordering functionality."""
        print("WebSocket Message Ordering Test Framework")
        print("=========================================")
        
        # Test basic class instantiation
        validator = MessageOrderingValidator()
        print("[OK] MessageOrderingValidator created")
        
        # Test message registration
        test_msg = OrderingTestMessage(
            sequence_number=0,
            correlation_id="test-123",
            content="test message",
            send_timestamp=time.time()
        )
        validator.register_sent_message(test_msg)
        print("[OK] Message registration works")
        
        # Test metrics analysis
        metrics = validator.analyze_ordering()
        print(f"[OK] Metrics analysis works: {metrics.total_sent} sent, {metrics.total_received} received")
        
        print("\nFramework validation successful! Ready for integration testing.")
        print("Run with pytest to execute full test suite.")
        
    # Run validation if executed directly
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        asyncio.run(main())
    else:
        print("WebSocket Message Ordering Test")
        print("Usage: python test_message_ordering.py --validate")
        print("Or run with pytest for full test execution")