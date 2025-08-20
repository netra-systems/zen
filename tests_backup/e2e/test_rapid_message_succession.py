"""
Test Suite 3: Rapid Message Succession (Idempotency/Ordering) - E2E Implementation

This comprehensive test suite validates message ordering guarantees, idempotency enforcement,
and state consistency when a single user sends messages in rapid succession to the Netra Apex
AI system. Tests focus on ensuring sequential processing, preventing duplicates, and maintaining
agent state integrity under high-frequency message bursts.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Platform Stability, User Experience, Risk Reduction
- Value Impact: Ensures consistent AI responses and prevents data corruption during peak usage
- Strategic/Revenue Impact: Critical for enterprise customer retention
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import random
import threading
import gc
import psutil
import os
import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict, deque
from dataclasses import dataclass, field

# WebSocket client imports
import websockets
import httpx

# Configure logging for rapid message testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
E2E_TEST_CONFIG = {
    "websocket_url": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8765"),  # Mock server port
    "backend_url": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
    "auth_service_url": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "skip_real_services": os.getenv("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_mode": os.getenv("RAPID_MESSAGE_TEST_MODE", "mock")  # mock or real
}

# Test configuration constants
RAPID_MESSAGE_TEST_CONFIG = {
    "max_burst_size": 50,
    "min_message_interval": 0.05,  # 50ms
    "burst_timeout": 30.0,
    "max_message_latency": 1.0,  # seconds
    "min_throughput": 10,  # messages/second
    "max_memory_growth": 50_000_000,  # 50MB
    "min_delivery_ratio": 0.95,  # 95%
    "queue_capacity_threshold": 500,
    "agent_state_sync_timeout": 5.0,
    "websocket_stability_duration": 30.0,
    "idempotency_window": 300,  # 5 minutes
}


@dataclass
class MessageSequenceEntry:
    """Tracking entry for message sequence validation."""
    sequence_id: int
    message_id: str
    content: str
    timestamp: float
    sent_time: Optional[float] = None
    received_time: Optional[float] = None
    processed_time: Optional[float] = None
    status: str = "pending"
    response_data: Optional[Dict] = None


@dataclass
class MessageBurstResult:
    """Result tracking for message burst operations."""
    total_sent: int = 0
    total_received: int = 0
    total_failed: int = 0
    total_duplicates: int = 0
    avg_latency: float = 0.0
    max_latency: float = 0.0
    sequence_violations: List[str] = field(default_factory=list)
    memory_growth: int = 0
    queue_overflows: int = 0


class MessageSequenceValidator:
    """Advanced message sequence integrity validator."""
    
    def __init__(self):
        self.expected_sequences = []
        self.received_sequences = []
        self.violations = []
        self.duplicate_tracker = set()
        
    def track_expected_sequence(self, sequence_id: int, message_id: str, content: str = ""):
        """Track expected message sequence."""
        entry = MessageSequenceEntry(
            sequence_id=sequence_id,
            message_id=message_id,
            content=content,
            timestamp=time.time()
        )
        self.expected_sequences.append(entry)
        return entry
    
    def track_received_sequence(self, sequence_id: int, message_id: str, response: Dict):
        """Track received message sequence."""
        entry = MessageSequenceEntry(
            sequence_id=sequence_id,
            message_id=message_id,
            content=response.get("content", ""),
            timestamp=time.time(),
            received_time=time.time(),
            response_data=response
        )
        self.received_sequences.append(entry)
        return entry
    
    def detect_duplicate_processing(self, message_id: str) -> bool:
        """Detect if message was already processed."""
        if message_id in self.duplicate_tracker:
            return True
        self.duplicate_tracker.add(message_id)
        return False
    
    def validate_sequence_integrity(self) -> Dict[str, Any]:
        """Comprehensive sequence integrity validation."""
        validation_result = {
            "total_expected": len(self.expected_sequences),
            "total_received": len(self.received_sequences),
            "missing_sequences": [],
            "duplicate_sequences": [],
            "out_of_order_sequences": [],
            "sequence_gaps": [],
            "violations": []
        }
        
        # Check for missing sequences
        expected_ids = {seq.sequence_id for seq in self.expected_sequences}
        received_ids = {seq.sequence_id for seq in self.received_sequences}
        
        validation_result["missing_sequences"] = list(expected_ids - received_ids)
        
        # Check for duplicates
        received_sequence_ids = [seq.sequence_id for seq in self.received_sequences]
        duplicates = [sid for sid in received_sequence_ids if received_sequence_ids.count(sid) > 1]
        validation_result["duplicate_sequences"] = list(set(duplicates))
        
        # Check for ordering violations
        sorted_received = sorted(self.received_sequences, key=lambda x: x.received_time or 0)
        sequence_order = [seq.sequence_id for seq in sorted_received]
        expected_order = sorted(sequence_order)
        
        if sequence_order != expected_order:
            validation_result["out_of_order_sequences"] = sequence_order
            validation_result["violations"].append("Message ordering violation detected")
        
        # Check for sequence gaps
        if expected_ids:
            min_seq = min(expected_ids)
            max_seq = max(expected_ids)
            expected_range = set(range(min_seq, max_seq + 1))
            gaps = expected_range - received_ids
            validation_result["sequence_gaps"] = list(gaps)
        
        # Compile violations
        if validation_result["missing_sequences"]:
            validation_result["violations"].append(f"Missing sequences: {validation_result['missing_sequences']}")
        
        if validation_result["duplicate_sequences"]:
            validation_result["violations"].append(f"Duplicate sequences: {validation_result['duplicate_sequences']}")
        
        if validation_result["sequence_gaps"]:
            validation_result["violations"].append(f"Sequence gaps: {validation_result['sequence_gaps']}")
        
        return validation_result
    
    def assert_no_sequence_violations(self):
        """Assert no sequence violations occurred."""
        validation_result = self.validate_sequence_integrity()
        violations = validation_result["violations"]
        
        assert len(violations) == 0, f"Sequence violations detected: {violations}"
        return validation_result


class MockWebSocketServer:
    """Mock WebSocket server for testing without real services."""
    
    def __init__(self, port=8765):
        self.port = port
        self.server = None
        self.clients = set()
        self.processed_messages = {}
        
    async def start(self):
        """Start mock WebSocket server."""
        self.server = await websockets.serve(
            self.handle_client,
            "localhost",
            self.port
        )
        logger.info(f"Mock WebSocket server started on ws://localhost:{self.port}")
        
    async def stop(self):
        """Stop mock WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
    async def handle_client(self, websocket):
        """Handle WebSocket client connections."""
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
    
    async def process_message(self, websocket, message):
        """Process incoming messages and send responses."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            # Simulate different message types
            if message_type == "user_message":
                await self.handle_user_message(websocket, data)
            elif message_type == "get_agent_state":
                await self.handle_agent_state_request(websocket, data)
            elif message_type == "get_queue_state":
                await self.handle_queue_state_request(websocket, data)
            elif message_type == "configure_agents":
                await self.handle_agent_configuration(websocket, data)
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))
    
    async def handle_user_message(self, websocket, data):
        """Simulate AI response to user messages with idempotency."""
        message_id = data.get("message_id")
        
        # Check for duplicate messages (idempotency)
        if message_id in self.processed_messages:
            duplicate_response = {
                "type": "duplicate_rejected",
                "message_id": message_id,
                "message": "Message already processed",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(duplicate_response))
            return
        
        # Mark as processed
        self.processed_messages[message_id] = data
        
        response = {
            "type": "ai_response",
            "message_id": message_id,
            "sequence_id": data.get("sequence_id"),
            "content": f"AI response to: {data.get('content', 'unknown')}",
            "timestamp": time.time()
        }
        
        # Add small delay to simulate processing
        await asyncio.sleep(0.1)
        await websocket.send(json.dumps(response))
    
    async def handle_agent_state_request(self, websocket, data):
        """Simulate agent state response."""
        state = {
            "type": "agent_state",
            "message_count": len(self.processed_messages),
            "conversation_context": {"topic": "sales_analysis"},
            "memory_usage": {"rss": psutil.Process().memory_info().rss},
            "corrupted": False,
            "processed_message_ids": list(self.processed_messages.keys()),
            "agents": {
                "data_sub_agent": {"messages_processed": 2, "shared_state": {"customer_data": "loaded"}},
                "analysis_sub_agent": {"messages_processed": 3, "shared_state": {"customer_segments": "analyzed"}},
                "reporting_sub_agent": {"messages_processed": 1, "shared_state": {"dashboard_export": "ready"}}
            },
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(state))
    
    async def handle_queue_state_request(self, websocket, data):
        """Simulate queue state response."""
        state = {
            "type": "queue_state",
            "queue_size": random.randint(0, 50),
            "max_capacity": 500,
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(state))
    
    async def handle_agent_configuration(self, websocket, data):
        """Handle agent configuration requests."""
        response = {
            "type": "agents_configured",
            "agents": data.get("agents", []),
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(response))


class RapidMessageSender:
    """Utility for controlled rapid message sending."""
    
    def __init__(self, websocket_uri: str, auth_token: str, max_rate_per_second: int = 50):
        self.websocket_uri = websocket_uri
        self.auth_token = auth_token
        self.max_rate_per_second = max_rate_per_second
        self.sent_messages = []
        self.connection = None
        
    async def connect(self):
        """Establish WebSocket connection."""
        try:
            # For mock server, don't use auth headers
            if "localhost:8765" in self.websocket_uri:
                self.connection = await websockets.connect(
                    self.websocket_uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
            else:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                self.connection = await websockets.connect(
                    self.websocket_uri,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise
    
    async def disconnect(self):
        """Close WebSocket connection."""
        if self.connection:
            await self.connection.close()
    
    async def send_rapid_burst(self, messages: List[Dict], burst_interval: float = 0.1) -> List[Dict]:
        """Send messages in rapid succession with controlled timing."""
        if not self.connection:
            await self.connect()
        
        tasks = []
        for i, message in enumerate(messages):
            delay = i * burst_interval
            task = asyncio.create_task(self._send_with_delay(message, delay))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _send_with_delay(self, message: Dict, delay: float) -> Dict:
        """Send message after specified delay."""
        await asyncio.sleep(delay)
        start_time = time.perf_counter()
        
        try:
            message_json = json.dumps(message)
            await self.connection.send(message_json)
            send_time = time.perf_counter() - start_time
            
            result = {
                "message": message,
                "send_time": send_time,
                "timestamp": time.time(),
                "status": "sent"
            }
            self.sent_messages.append(result)
            return result
            
        except Exception as e:
            result = {
                "message": message,
                "error": str(e),
                "timestamp": time.time(),
                "status": "failed"
            }
            self.sent_messages.append(result)
            return result
    
    async def receive_responses(self, expected_count: int, timeout: float = 30.0) -> List[Dict]:
        """Receive responses with timeout."""
        responses = []
        start_time = time.time()
        
        try:
            while len(responses) < expected_count and (time.time() - start_time) < timeout:
                try:
                    response = await asyncio.wait_for(
                        self.connection.recv(), 
                        timeout=min(5.0, timeout - (time.time() - start_time))
                    )
                    response_data = json.loads(response)
                    response_data["received_time"] = time.time()
                    responses.append(response_data)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Error receiving response: {e}")
                    break
        except Exception as e:
            logger.error(f"Error in receive_responses: {e}")
        
        return responses
    
    async def get_agent_state(self) -> Dict:
        """Get current agent state via WebSocket."""
        state_request = {
            "type": "get_agent_state",
            "timestamp": time.time()
        }
        
        await self.connection.send(json.dumps(state_request))
        
        # Wait for state response
        try:
            response = await asyncio.wait_for(self.connection.recv(), timeout=5.0)
            return json.loads(response)
        except asyncio.TimeoutError:
            return {"error": "Agent state request timeout"}
    
    async def monitor_connection_health(self, duration: float) -> Dict:
        """Monitor WebSocket connection health over time."""
        health_data = {
            "start_time": time.time(),
            "disconnections": 0,
            "reconnections": 0,
            "ping_failures": 0,
            "initial_memory_usage": {"rss": psutil.Process().memory_info().rss},
            "final_memory_usage": {},
            "connection_stable": True
        }
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                # Check connection state
                if self.connection.closed:
                    health_data["disconnections"] += 1
                    health_data["connection_stable"] = False
                    break
                
                # Test ping
                try:
                    pong = await self.connection.ping()
                    await asyncio.wait_for(pong, timeout=5.0)
                except asyncio.TimeoutError:
                    health_data["ping_failures"] += 1
                
                await asyncio.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.warning(f"Connection health check error: {e}")
                health_data["connection_stable"] = False
                break
        
        health_data["final_memory_usage"] = {"rss": psutil.Process().memory_info().rss}
        return health_data


class AgentStateMonitor:
    """Monitors agent state consistency during rapid messaging."""
    
    def __init__(self):
        self.state_snapshots = []
        self.consistency_violations = []
        
    async def capture_state_snapshot(self, label: str, sender: RapidMessageSender) -> Dict:
        """Capture current agent state."""
        state = await sender.get_agent_state()
        snapshot = {
            "label": label,
            "timestamp": time.time(),
            "state": state.copy() if isinstance(state, dict) else state,
            "memory_usage": {"rss": psutil.Process().memory_info().rss},
            "thread_count": threading.active_count()
        }
        
        self.state_snapshots.append(snapshot)
        return snapshot
    
    def validate_state_consistency(self) -> Dict[str, Any]:
        """Validate agent state remained consistent."""
        if len(self.state_snapshots) < 2:
            return {"error": "Insufficient snapshots for comparison"}
        
        validation_result = {
            "memory_growth": 0,
            "thread_growth": 0,
            "state_corruption_detected": False,
            "consistency_violations": [],
            "memory_leak_detected": False
        }
        
        # Check memory growth
        initial_memory = self.state_snapshots[0]["memory_usage"]["rss"]
        final_memory = self.state_snapshots[-1]["memory_usage"]["rss"]
        memory_growth = final_memory - initial_memory
        validation_result["memory_growth"] = memory_growth
        
        if memory_growth > RAPID_MESSAGE_TEST_CONFIG["max_memory_growth"]:
            validation_result["memory_leak_detected"] = True
            validation_result["consistency_violations"].append(
                f"Memory leak detected: {memory_growth:,} bytes growth"
            )
        
        # Check thread growth
        initial_threads = self.state_snapshots[0]["thread_count"]
        final_threads = self.state_snapshots[-1]["thread_count"]
        thread_growth = final_threads - initial_threads
        validation_result["thread_growth"] = thread_growth
        
        if thread_growth > 5:  # Allow some thread variance
            validation_result["consistency_violations"].append(
                f"Thread leak detected: {thread_growth} threads created"
            )
        
        # Check for state corruption
        for snapshot in self.state_snapshots:
            state = snapshot.get("state", {})
            if isinstance(state, dict) and state.get("corrupted", False):
                validation_result["state_corruption_detected"] = True
                validation_result["consistency_violations"].append(
                    f"State corruption detected at {snapshot['label']}"
                )
        
        return validation_result
    
    def assert_state_consistency(self):
        """Assert agent state consistency."""
        validation_result = self.validate_state_consistency()
        violations = validation_result.get("consistency_violations", [])
        
        assert len(violations) == 0, f"State consistency violations: {violations}"
        return validation_result


# Test Fixtures

@pytest.fixture
async def mock_websocket_server():
    """Mock WebSocket server fixture."""
    if E2E_TEST_CONFIG["test_mode"] != "mock":
        yield None
        return
        
    server = MockWebSocketServer()
    await server.start()
    
    yield server
    await server.stop()


@pytest.fixture
async def test_user_token():
    """Create test user and return auth token."""
    if E2E_TEST_CONFIG["test_mode"] == "real":
        # Use real authentication service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{E2E_TEST_CONFIG['auth_service_url']}/auth/test-user",
                    json={"email": f"test-{uuid.uuid4().hex[:8]}@example.com"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    token_data = response.json()
                    return {
                        "user_id": token_data["user_id"],
                        "token": token_data["token"],
                        "email": token_data["email"]
                    }
        except Exception as e:
            logger.warning(f"Real auth failed, using mock: {e}")
    
    # Fallback to mock authentication
    test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    return {
        "user_id": test_user_id,
        "token": f"mock-token-{uuid.uuid4().hex}",
        "email": f"{test_user_id}@example.com"
    }


@pytest.fixture
def message_sequence_validator():
    """Message sequence validator fixture."""
    validator = MessageSequenceValidator()
    yield validator
    # Cleanup is handled by validator internally


@pytest.fixture
def agent_state_monitor():
    """Agent state monitor fixture."""
    monitor = AgentStateMonitor()
    yield monitor
    # Validate consistency at end of test
    monitor.assert_state_consistency()


@pytest.fixture
async def rapid_message_sender(test_user_token, mock_websocket_server):
    """Rapid message sender fixture with automatic connection."""
    websocket_uri = E2E_TEST_CONFIG["websocket_url"]
    sender = RapidMessageSender(websocket_uri, test_user_token["token"])
    
    # Establish connection with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await sender.connect()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                pytest.skip(f"WebSocket connection failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1.0)
    
    yield sender
    
    # Cleanup with error handling
    try:
        await sender.disconnect()
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")


# Test Cases Implementation

class TestSequentialMessageProcessingRapidSuccession:
    """Test Case 1: Sequential Message Processing Under Rapid Succession"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sequential_message_processing_rapid_succession(
        self, rapid_message_sender, message_sequence_validator, agent_state_monitor
    ):
        """
        Scenario: Single user sends 20 messages within 2 seconds
        Expected: All messages processed in exact order, no duplicates or loss
        """
        await agent_state_monitor.capture_state_snapshot("test_start", rapid_message_sender)
        
        # Generate sequence of numbered messages
        message_count = 20
        messages = []
        
        for i in range(message_count):
            message = {
                "type": "user_message",
                "content": f"Message sequence {i:03d}: What is 2+2?",
                "sequence_id": i,
                "message_id": f"seq-msg-{i}",
                "timestamp": time.time(),
                "requires_processing": True
            }
            messages.append(message)
            message_sequence_validator.track_expected_sequence(i, message["message_id"], message["content"])
        
        # Send messages in rapid succession (100ms intervals)
        start_time = time.perf_counter()
        results = await rapid_message_sender.send_rapid_burst(messages, burst_interval=0.1)
        send_duration = time.perf_counter() - start_time
        
        # Collect responses
        responses = await rapid_message_sender.receive_responses(
            expected_count=message_count,
            timeout=30.0
        )
        
        # Track received sequences
        for response in responses:
            sequence_id = response.get("sequence_id")
            message_id = response.get("message_id", response.get("correlation_id"))
            if sequence_id is not None and message_id:
                message_sequence_validator.track_received_sequence(sequence_id, message_id, response)
        
        # Validation
        assert len(responses) == message_count, \
            f"Expected {message_count} responses, got {len(responses)}"
        
        # Validate sequence integrity
        sequence_validation = message_sequence_validator.validate_sequence_integrity()
        assert len(sequence_validation["violations"]) == 0, \
            f"Sequence violations detected: {sequence_validation['violations']}"
        
        # Verify no duplicates
        message_ids = [r.get("message_id", r.get("correlation_id")) for r in responses if r.get("message_id") or r.get("correlation_id")]
        unique_message_ids = set(message_ids)
        assert len(message_ids) == len(unique_message_ids), \
            f"Duplicate messages detected: {len(message_ids)} total, {len(unique_message_ids)} unique"
        
        # Verify timing performance
        assert send_duration < 5.0, f"Message sending took too long: {send_duration:.2f}s"
        
        await agent_state_monitor.capture_state_snapshot("test_end", rapid_message_sender)
        
        logger.info(f"Sequential processing test completed: {len(responses)} messages in {send_duration:.2f}s")


class TestBurstMessageIdempotencyEnforcement:
    """Test Case 2: Burst Message Idempotency Enforcement"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_burst_message_idempotency_enforcement(
        self, rapid_message_sender, message_sequence_validator, agent_state_monitor
    ):
        """
        Scenario: User sends same message multiple times rapidly due to UI lag
        Expected: Only one processing per unique message, duplicates rejected gracefully
        """
        await agent_state_monitor.capture_state_snapshot("idempotency_test_start", rapid_message_sender)
        
        # Create base message with unique ID
        base_message = {
            "type": "user_message",
            "content": "Analyze the Q3 sales data trends",
            "message_id": f"unique-message-{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "requires_processing": True
        }
        
        message_sequence_validator.track_expected_sequence(0, base_message["message_id"], base_message["content"])
        
        # Send same message 10 times rapidly (simulating UI issues)
        duplicate_messages = []
        for i in range(10):
            message_copy = base_message.copy()
            message_copy["duplicate_attempt"] = i
            duplicate_messages.append(message_copy)
        
        # Send all duplicates with minimal delay variations
        start_time = time.perf_counter()
        results = await rapid_message_sender.send_rapid_burst(
            duplicate_messages, 
            burst_interval=random.uniform(0, 0.05)  # 0-50ms variations
        )
        
        # Collect responses with extended timeout for processing
        responses = await rapid_message_sender.receive_responses(
            expected_count=10,  # Allow for rejection messages
            timeout=15.0
        )
        
        # Analyze responses
        processed_responses = []
        duplicate_rejections = []
        
        for response in responses:
            response_type = response.get("type", "unknown")
            message_id = response.get("message_id", response.get("correlation_id"))
            
            if response_type in ["ai_response", "processed"] and message_id == base_message["message_id"]:
                processed_responses.append(response)
                message_sequence_validator.track_received_sequence(0, message_id, response)
            elif response_type in ["duplicate_rejected", "error"] and "duplicate" in response.get("message", "").lower():
                duplicate_rejections.append(response)
        
        # Validation: Only one should be processed
        assert len(processed_responses) <= 1, \
            f"Multiple messages processed: {len(processed_responses)} (expected: 0 or 1)"
        
        # Should have rejection messages for duplicates
        assert len(duplicate_rejections) >= 8, \
            f"Insufficient duplicate rejections: {len(duplicate_rejections)} (expected: ≥8)"
        
        # Verify no duplicate processing in agent state
        agent_state = await rapid_message_sender.get_agent_state()
        if isinstance(agent_state, dict):
            processed_message_ids = agent_state.get("processed_message_ids", [])
            if base_message["message_id"] in processed_message_ids:
                count = processed_message_ids.count(base_message["message_id"])
                assert count == 1, f"Message processed {count} times despite idempotency"
        
        await agent_state_monitor.capture_state_snapshot("idempotency_test_end", rapid_message_sender)
        
        logger.info(f"Idempotency test completed: {len(processed_responses)} processed, {len(duplicate_rejections)} rejected")


class TestQueueOverflowBackpressureHandling:
    """Test Case 3: Queue Overflow and Backpressure Handling"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_queue_overflow_backpressure_handling(
        self, rapid_message_sender, message_sequence_validator, agent_state_monitor
    ):
        """
        Scenario: User sends messages faster than system can process
        Expected: Graceful backpressure, message queuing, no loss of critical messages
        """
        await agent_state_monitor.capture_state_snapshot("queue_test_start", rapid_message_sender)
        
        # Test with high message volume to trigger queue limits
        message_count = RAPID_MESSAGE_TEST_CONFIG["queue_capacity_threshold"] + 50
        messages = []
        
        for i in range(message_count):
            priority = "high" if i % 10 == 0 else "normal"
            message = {
                "type": "user_message",
                "content": f"Process data batch {i}",
                "message_id": f"batch-{i}",
                "priority": priority,
                "timestamp": time.time(),
                "sequence_id": i
            }
            messages.append(message)
            message_sequence_validator.track_expected_sequence(i, message["message_id"])
        
        # Send messages as fast as possible
        start_time = time.perf_counter()
        results = await rapid_message_sender.send_rapid_burst(messages, burst_interval=0.01)  # 10ms intervals
        send_duration = time.perf_counter() - start_time
        
        # Monitor queue state during processing
        queue_monitoring_task = asyncio.create_task(
            self._monitor_queue_state(rapid_message_sender, duration=30.0)
        )
        
        # Collect responses with extended timeout
        responses = await rapid_message_sender.receive_responses(
            expected_count=min(message_count, RAPID_MESSAGE_TEST_CONFIG["queue_capacity_threshold"]),
            timeout=45.0
        )
        
        queue_states = await queue_monitoring_task
        
        # Analysis
        successful_sends = len([r for r in results if r.get("status") == "sent"])
        processed_responses = len([r for r in responses if r.get("type") in ["ai_response", "processed"]])
        queue_full_responses = len([r for r in responses if r.get("type") == "queue_full"])
        
        # Validation: Should handle backpressure gracefully
        assert queue_full_responses > 0 or processed_responses < message_count, \
            "No backpressure signals detected despite queue overflow"
        
        assert successful_sends > 0, "No messages successfully sent"
        
        # Verify high-priority message preservation
        high_priority_responses = [
            r for r in responses 
            if r.get("priority") == "high" and r.get("type") in ["ai_response", "processed"]
        ]
        
        high_priority_sent = len([m for m in messages if m["priority"] == "high"])
        if high_priority_sent > 0:
            preservation_ratio = len(high_priority_responses) / high_priority_sent
            assert preservation_ratio >= 0.8, \
                f"High priority preservation too low: {preservation_ratio:.2f}"
        
        # Verify queue management
        if queue_states:
            max_queue_size = max(state.get("queue_size", 0) for state in queue_states)
            assert max_queue_size <= RAPID_MESSAGE_TEST_CONFIG["queue_capacity_threshold"] * 1.1, \
                f"Queue capacity exceeded: {max_queue_size}"
        
        await agent_state_monitor.capture_state_snapshot("queue_test_end", rapid_message_sender)
        
        logger.info(f"Queue overflow test: {successful_sends} sent, {processed_responses} processed, {queue_full_responses} backpressure signals")
    
    async def _monitor_queue_state(self, sender: RapidMessageSender, duration: float) -> List[Dict]:
        """Monitor queue state over time."""
        states = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                # Request queue state
                state_request = {
                    "type": "get_queue_state",
                    "timestamp": time.time()
                }
                
                await sender.connection.send(json.dumps(state_request))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(sender.connection.recv(), timeout=2.0)
                    state_data = json.loads(response)
                    if state_data.get("type") == "queue_state":
                        states.append(state_data)
                except asyncio.TimeoutError:
                    pass
                
                await asyncio.sleep(1.0)  # Monitor every second
                
            except Exception as e:
                logger.warning(f"Queue monitoring error: {e}")
                break
        
        return states


class TestAgentStateConsistencyRapidUpdates:
    """Test Case 4: Agent State Consistency Under Rapid Updates"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_state_consistency_rapid_updates(
        self, rapid_message_sender, message_sequence_validator, agent_state_monitor
    ):
        """
        Scenario: Rapid messages that should build upon each other's context
        Expected: Agent state updates atomically, context remains coherent
        """
        await agent_state_monitor.capture_state_snapshot("consistency_test_start", rapid_message_sender)
        
        # Create interdependent message sequence
        conversation_sequence = [
            {"content": "Let's analyze sales data", "expected_context": "sales_analysis"},
            {"content": "Focus on Q3 2024", "expected_context": "sales_analysis_q3_2024"},
            {"content": "Compare with Q2", "expected_context": "sales_comparison_q2_q3"},
            {"content": "Show regional breakdown", "expected_context": "regional_sales_breakdown"},
            {"content": "Highlight top performers", "expected_context": "top_performers_regional"},
            {"content": "Export to spreadsheet", "expected_context": "export_sales_analysis"},
            {"content": "Schedule monthly update", "expected_context": "scheduled_sales_reports"},
            {"content": "Set alert thresholds", "expected_context": "sales_monitoring_alerts"},
            {"content": "Create dashboard view", "expected_context": "sales_dashboard_creation"},
            {"content": "Share with team", "expected_context": "team_collaboration_sales"}
        ]
        
        # Send messages with state monitoring
        messages = []
        state_snapshots = []
        
        for i, msg_data in enumerate(conversation_sequence):
            # Capture state before sending
            pre_state = await agent_state_monitor.capture_state_snapshot(f"pre_message_{i}", rapid_message_sender)
            
            message = {
                "type": "user_message",
                "content": msg_data["content"],
                "sequence_id": i,
                "message_id": f"context-msg-{i}",
                "timestamp": time.time(),
                "context_building": True
            }
            
            messages.append(message)
            message_sequence_validator.track_expected_sequence(i, message["message_id"])
        
        # Send all messages in rapid succession
        results = await rapid_message_sender.send_rapid_burst(messages, burst_interval=0.2)
        
        # Capture state after each expected processing
        for i in range(len(conversation_sequence)):
            await asyncio.sleep(1.0)  # Allow processing time
            await agent_state_monitor.capture_state_snapshot(f"post_message_{i}", rapid_message_sender)
        
        # Collect responses
        responses = await rapid_message_sender.receive_responses(
            expected_count=len(conversation_sequence),
            timeout=30.0
        )
        
        # Track received sequences
        for response in responses:
            sequence_id = response.get("sequence_id")
            message_id = response.get("message_id", response.get("correlation_id"))
            if sequence_id is not None and message_id:
                message_sequence_validator.track_received_sequence(sequence_id, message_id, response)
        
        # Validation
        assert len(responses) == len(conversation_sequence), \
            f"Expected {len(conversation_sequence)} responses, got {len(responses)}"
        
        # Verify sequence integrity
        sequence_validation = message_sequence_validator.validate_sequence_integrity()
        assert len(sequence_validation["violations"]) == 0, \
            f"Sequence violations: {sequence_validation['violations']}"
        
        # Verify context progression
        final_state = await rapid_message_sender.get_agent_state()
        if isinstance(final_state, dict):
            conversation_context = final_state.get("conversation_context", {})
            
            # Check if final context contains expected elements
            final_expected_context = conversation_sequence[-1]["expected_context"]
            context_str = str(conversation_context).lower()
            
            assert "sales" in context_str, "Sales context not preserved"
            assert "team" in context_str or "collaboration" in context_str, "Final context not reached"
            
            # Verify message count consistency
            expected_message_count = len(conversation_sequence)
            actual_message_count = final_state.get("message_count", 0)
            assert actual_message_count == expected_message_count, \
                f"Message count mismatch: {actual_message_count} != {expected_message_count}"
        
        await agent_state_monitor.capture_state_snapshot("consistency_test_end", rapid_message_sender)
        
        logger.info(f"Agent consistency test completed: {len(responses)} messages processed with context preservation")


class TestWebSocketStabilityMessageBursts:
    """Test Case 5: WebSocket Connection Stability Under Message Bursts"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_stability_message_bursts(
        self, rapid_message_sender, message_sequence_validator, agent_state_monitor
    ):
        """
        Scenario: Sustained high-frequency message sending over extended period
        Expected: WebSocket remains stable, no connection drops or message loss
        """
        await agent_state_monitor.capture_state_snapshot("stability_test_start", rapid_message_sender)
        
        # Configure burst testing parameters
        burst_duration = RAPID_MESSAGE_TEST_CONFIG["websocket_stability_duration"]
        messages_per_burst = 10
        burst_interval = 2.0  # 2 seconds between bursts
        bursts_count = int(burst_duration / burst_interval)
        
        message_metrics = {
            "sent": 0,
            "received": 0,
            "failed": 0,
            "timeouts": 0
        }
        
        # Start connection monitoring
        connection_monitor_task = asyncio.create_task(
            rapid_message_sender.monitor_connection_health(burst_duration + 10)
        )
        
        # Execute sustained bursts
        all_responses = []
        burst_results = []
        
        for burst_id in range(bursts_count):
            burst_messages = []
            for msg_id in range(messages_per_burst):
                message = {
                    "type": "user_message",
                    "content": f"Burst {burst_id} Message {msg_id}: Process data",
                    "burst_id": burst_id,
                    "message_id": f"burst-{burst_id}-msg-{msg_id}",
                    "timestamp": time.time()
                }
                burst_messages.append(message)
                message_sequence_validator.track_expected_sequence(
                    burst_id * messages_per_burst + msg_id, 
                    message["message_id"]
                )
            
            # Send burst
            start_time = time.perf_counter()
            results = await rapid_message_sender.send_rapid_burst(burst_messages, burst_interval=0.05)
            burst_duration_actual = time.perf_counter() - start_time
            
            # Count results
            successful_sends = len([r for r in results if r.get("status") == "sent"])
            failed_sends = len([r for r in results if r.get("status") == "failed"])
            
            message_metrics["sent"] += successful_sends
            message_metrics["failed"] += failed_sends
            
            burst_results.append({
                "burst_id": burst_id,
                "duration": burst_duration_actual,
                "sent": successful_sends,
                "failed": failed_sends
            })
            
            # Wait for burst interval
            await asyncio.sleep(burst_interval)
        
        # Collect all responses
        total_expected = bursts_count * messages_per_burst
        responses = await rapid_message_sender.receive_responses(
            expected_count=total_expected,
            timeout=burst_duration + 5
        )
        
        message_metrics["received"] = len(responses)
        
        # Track received sequences
        for response in responses:
            message_id = response.get("message_id", response.get("correlation_id"))
            if message_id:
                # Extract sequence from message ID
                try:
                    parts = message_id.split("-")
                    if len(parts) >= 4:  # burst-X-msg-Y format
                        burst_id = int(parts[1])
                        msg_id = int(parts[3])
                        sequence_id = burst_id * messages_per_burst + msg_id
                        message_sequence_validator.track_received_sequence(sequence_id, message_id, response)
                except (ValueError, IndexError):
                    pass
        
        # Stop connection monitoring
        connection_health = await connection_monitor_task
        
        # Validation
        
        # Verify connection stability
        assert connection_health["disconnections"] == 0, \
            f"WebSocket disconnected {connection_health['disconnections']} times"
        
        assert connection_health["connection_stable"], "WebSocket connection was unstable"
        
        # Verify message delivery ratio
        if message_metrics["sent"] > 0:
            delivery_ratio = message_metrics["received"] / message_metrics["sent"]
            assert delivery_ratio >= RAPID_MESSAGE_TEST_CONFIG["min_delivery_ratio"], \
                f"Delivery ratio too low: {delivery_ratio:.2f}"
        
        # Verify performance
        if burst_results:
            avg_burst_duration = sum(b["duration"] for b in burst_results) / len(burst_results)
            max_burst_duration = max(b["duration"] for b in burst_results)
            
            assert avg_burst_duration < 1.0, f"Average burst duration too high: {avg_burst_duration:.3f}s"
            assert max_burst_duration < 2.0, f"Maximum burst duration too high: {max_burst_duration:.3f}s"
        
        # Verify no excessive memory growth
        memory_growth = (
            connection_health["final_memory_usage"]["rss"] - 
            connection_health["initial_memory_usage"]["rss"]
        )
        memory_growth_mb = memory_growth / (1024 * 1024)
        
        assert memory_growth_mb < 100, f"Excessive memory growth: {memory_growth_mb:.1f}MB"
        
        # Verify sequence integrity
        sequence_validation = message_sequence_validator.validate_sequence_integrity()
        missing_ratio = len(sequence_validation["missing_sequences"]) / total_expected
        assert missing_ratio < 0.1, f"Too many missing messages: {missing_ratio:.2%}"
        
        await agent_state_monitor.capture_state_snapshot("stability_test_end", rapid_message_sender)
        
        logger.info(f"WebSocket stability test: {message_metrics['sent']} sent, {message_metrics['received']} received, {connection_health['disconnections']} disconnections")


class TestCrossAgentStateSynchronization:
    """Test Case 6: Cross-Agent State Synchronization During Rapid Messages"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_agent_state_synchronization(
        self, rapid_message_sender, message_sequence_validator, agent_state_monitor
    ):
        """
        Scenario: Rapid messages requiring coordination between multiple sub-agents
        Expected: All sub-agents maintain consistent shared state, no race conditions
        """
        await agent_state_monitor.capture_state_snapshot("sync_test_start", rapid_message_sender)
        
        # Enable multi-agent mode
        agent_config = {
            "type": "configure_agents",
            "agents": ["data_sub_agent", "analysis_sub_agent", "reporting_sub_agent"],
            "timestamp": time.time()
        }
        
        await rapid_message_sender.connection.send(json.dumps(agent_config))
        await asyncio.sleep(2.0)  # Allow configuration time
        
        # Create messages requiring cross-agent coordination
        coordination_messages = [
            {
                "content": "Load customer database",
                "target_agents": ["data_sub_agent"],
                "shared_state_key": "customer_data"
            },
            {
                "content": "Analyze customer segments",
                "target_agents": ["data_sub_agent", "analysis_sub_agent"],
                "shared_state_key": "customer_segments"
            },
            {
                "content": "Calculate segment metrics",
                "target_agents": ["analysis_sub_agent"],
                "shared_state_key": "segment_metrics"
            },
            {
                "content": "Generate segment report",
                "target_agents": ["analysis_sub_agent", "reporting_sub_agent"],
                "shared_state_key": "segment_report"
            },
            {
                "content": "Export to dashboard",
                "target_agents": ["reporting_sub_agent"],
                "shared_state_key": "dashboard_export"
            }
        ]
        
        # Send coordination messages
        messages = []
        for i, msg_data in enumerate(coordination_messages):
            message = {
                "type": "user_message",
                "content": msg_data["content"],
                "sequence_id": i,
                "message_id": f"coord-msg-{i}",
                "coordination_required": True,
                "target_agents": msg_data["target_agents"],
                "shared_state_key": msg_data["shared_state_key"],
                "timestamp": time.time()
            }
            messages.append(message)
            message_sequence_validator.track_expected_sequence(i, message["message_id"])
        
        # Send in rapid succession
        results = await rapid_message_sender.send_rapid_burst(messages, burst_interval=0.1)
        
        # Monitor agent states during processing
        agent_state_timeline = []
        for i in range(len(coordination_messages) + 2):  # Extra snapshots
            await asyncio.sleep(1.0)
            snapshot = await agent_state_monitor.capture_state_snapshot(f"coord_state_{i}", rapid_message_sender)
            agent_state_timeline.append(snapshot)
        
        # Collect responses
        responses = await rapid_message_sender.receive_responses(
            expected_count=len(coordination_messages),
            timeout=20.0
        )
        
        # Track received sequences
        for response in responses:
            sequence_id = response.get("sequence_id")
            message_id = response.get("message_id", response.get("correlation_id"))
            if sequence_id is not None and message_id:
                message_sequence_validator.track_received_sequence(sequence_id, message_id, response)
        
        # Validation
        assert len(responses) == len(coordination_messages), \
            f"Expected {len(coordination_messages)} responses, got {len(responses)}"
        
        # Verify sequence integrity
        sequence_validation = message_sequence_validator.validate_sequence_integrity()
        assert len(sequence_validation["violations"]) == 0, \
            f"Coordination sequence violations: {sequence_validation['violations']}"
        
        # Verify cross-agent state synchronization
        final_state = await rapid_message_sender.get_agent_state()
        if isinstance(final_state, dict):
            agents_state = final_state.get("agents", {})
            
            # Check that all target agents processed their messages
            for i, msg_data in enumerate(coordination_messages):
                shared_key = msg_data["shared_state_key"]
                target_agents = msg_data["target_agents"]
                
                # Verify agents have consistent shared state
                shared_values = []
                for agent_name in target_agents:
                    if agent_name in agents_state:
                        agent_state = agents_state[agent_name]
                        shared_state = agent_state.get("shared_state", {})
                        if shared_key in shared_state:
                            shared_values.append(shared_state[shared_key])
                
                # All agents should have same shared state value
                if len(shared_values) > 1:
                    assert all(v == shared_values[0] for v in shared_values), \
                        f"Inconsistent shared state for {shared_key}: {shared_values}"
            
            # Verify no agent state corruption
            for agent_name, agent_state in agents_state.items():
                assert not agent_state.get("corrupted", False), \
                    f"Agent {agent_name} state corrupted during coordination"
                
                # Check message processing counts
                processed_count = agent_state.get("messages_processed", 0)
                expected_count = len([
                    msg for msg in coordination_messages 
                    if agent_name in msg["target_agents"]
                ])
                
                if expected_count > 0:  # Only check if agent should have processed messages
                    assert processed_count == expected_count, \
                        f"Agent {agent_name} processed {processed_count}, expected {expected_count}"
        
        await agent_state_monitor.capture_state_snapshot("sync_test_end", rapid_message_sender)
        
        logger.info(f"Cross-agent synchronization test completed: {len(responses)} coordinated messages processed")


# Performance Benchmark Test

@pytest.mark.asyncio
@pytest.mark.performance
async def test_rapid_message_suite_performance_benchmark(rapid_message_sender):
    """
    Performance benchmark for rapid message succession capabilities.
    Provides baseline metrics for regression testing.
    """
    benchmark_results = {
        "start_time": time.time(),
        "message_throughput": {},
        "latency_metrics": {},
        "memory_usage": {},
        "connection_stability": {}
    }
    
    # Benchmark message throughput
    throughput_messages = []
    for i in range(100):
        message = {
            "type": "user_message",
            "content": f"Throughput test message {i}",
            "message_id": f"throughput-{i}",
            "timestamp": time.time()
        }
        throughput_messages.append(message)
    
    # Measure sending throughput
    start_time = time.perf_counter()
    results = await rapid_message_sender.send_rapid_burst(throughput_messages, burst_interval=0.01)
    send_duration = time.perf_counter() - start_time
    
    # Measure response latency
    responses = await rapid_message_sender.receive_responses(
        expected_count=100,
        timeout=30.0
    )
    
    total_duration = time.perf_counter() - start_time
    
    # Calculate metrics
    messages_per_second = len(throughput_messages) / send_duration
    response_ratio = len(responses) / len(throughput_messages)
    
    benchmark_results["message_throughput"] = {
        "messages_sent": len(throughput_messages),
        "send_duration": send_duration,
        "messages_per_second": messages_per_second,
        "responses_received": len(responses),
        "response_ratio": response_ratio,
        "total_duration": total_duration
    }
    
    # Latency analysis
    if responses:
        latencies = []
        for response in responses:
            send_time = response.get("timestamp", 0)
            receive_time = response.get("received_time", 0)
            if send_time and receive_time:
                latency = receive_time - send_time
                latencies.append(latency)
        
        if latencies:
            benchmark_results["latency_metrics"] = {
                "count": len(latencies),
                "avg_latency": sum(latencies) / len(latencies),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "p95_latency": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies)
            }
    
    # Memory usage
    memory_info = psutil.Process().memory_info()
    benchmark_results["memory_usage"] = {
        "rss_mb": memory_info.rss / (1024 * 1024),
        "vms_mb": memory_info.vms / (1024 * 1024)
    }
    
    benchmark_results["total_benchmark_duration"] = time.time() - benchmark_results["start_time"]
    
    # Performance assertions
    assert messages_per_second >= RAPID_MESSAGE_TEST_CONFIG["min_throughput"], \
        f"Throughput below threshold: {messages_per_second:.1f} < {RAPID_MESSAGE_TEST_CONFIG['min_throughput']}"
    
    if benchmark_results.get("latency_metrics", {}).get("avg_latency"):
        avg_latency = benchmark_results["latency_metrics"]["avg_latency"]
        assert avg_latency <= RAPID_MESSAGE_TEST_CONFIG["max_message_latency"], \
            f"Average latency too high: {avg_latency:.3f}s > {RAPID_MESSAGE_TEST_CONFIG['max_message_latency']}s"
    
    logger.info(f"Rapid message benchmark completed: {json.dumps(benchmark_results, indent=2)}")
    
    return benchmark_results


if __name__ == "__main__":
    # Allow running individual test cases for debugging
    pytest.main([__file__, "-v", "--tb=short"])