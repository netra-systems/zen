"""WebSocket Message Ordering Under Concurrent Load Test

CRITICAL E2E Test: WebSocket Message Ordering Under Concurrent Load
Tests message ordering preservation with 100 concurrent WebSocket connections.

Business Value Justification (BVJ):
- Segment: Enterprise & Growth customers
- Business Goal: Data corruption prevention in multi-user scenarios  
- Value Impact: Prevents message ordering issues that affect AI pipeline integrity
- Revenue Impact: Critical for enterprise customers relying on message sequencing

Requirements:
1. Test message ordering with 100 concurrent WebSocket connections
2. Create 100 different test users
3. Send numbered messages concurrently from each connection
4. Verify message order preserved per connection
5. Check no message cross-contamination between users
6. Test burst messaging: 1000 messages in 1 second from single user

Validation criteria:
- Message order preserved under load
- No data leakage between connections
- System remains responsive
- Memory usage stays within limits
- Each user's messages isolated
"""

# Add parent directories to sys.path for imports
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from netra_backend.app.websocket.connection_manager import ModernModernConnectionManager as WebSocketManager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import asyncio
import psutil
import pytest
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

sys.path.insert(0, str(Path(__file__).parent.parent))

sys.path.insert(0, str(Path(__file__).parent))

from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.real_client_types import ClientConfig, ConnectionState
from tests.real_services_manager import (

    RealServicesManager as create_real_services_manager,

)
from tests.real_websocket_client import RealWebSocketClient


@dataclass

class ConcurrentLoadMetrics:

    """Metrics for concurrent load testing."""

    connection_count: int = 0

    successful_connections: int = 0

    messages_sent: int = 0

    messages_received: int = 0

    ordering_violations: int = 0

    cross_contamination_errors: int = 0

    memory_usage_mb: float = 0.0

    peak_memory_mb: float = 0.0

    test_duration_seconds: float = 0.0

    burst_completion_time: float = 0.0


@dataclass 

class UserConnection:

    """Represents a single user WebSocket connection."""

    user_id: str

    token: str

    client: Optional[RealWebSocketClient] = None

    sent_messages: List[Dict] = field(default_factory=list)

    received_messages: List[Dict] = field(default_factory=list)

    connected: bool = False

    message_sequence: int = 0


class ConcurrentWebSocketManager:

    """Manages 100 concurrent WebSocket connections for load testing."""
    

    def __init__(self):

        """Initialize concurrent connection manager."""

        self.jwt_helper = JWTTestHelper()

        self.ws_url = "ws://localhost:8000/ws"

        self.config = ClientConfig(timeout=5.0, max_retries=2)

        self.connections: Dict[str, UserConnection] = {}

        self.metrics = ConcurrentLoadMetrics()

        self.services_manager = None
        

    async def setup_services(self) -> None:

        """Setup real backend services."""

        self.services_manager = create_real_services_manager()

        await self.services_manager.start_all_services(skip_frontend=True)
    

    async def teardown_services(self) -> None:

        """Teardown services and cleanup."""

        if self.services_manager:

            await self.services_manager.stop_all_services()
    

    def create_test_users(self, count: int) -> List[UserConnection]:

        """Create test users with unique tokens."""

        users = []

        for i in range(count):

            user_id = f"test-user-{i:03d}-{uuid.uuid4().hex[:8]}"

            payload = self.jwt_helper.create_valid_payload()

            payload["sub"] = user_id

            payload["email"] = f"user{i}@netrasystems.ai"

            token = self.jwt_helper.create_token(payload)
            

            user = UserConnection(user_id=user_id, token=token)

            users.append(user)

            self.connections[user_id] = user

        return users
    

    async def establish_concurrent_connections(self, users: List[UserConnection]) -> int:

        """Establish WebSocket connections for all users concurrently."""

        connection_tasks = []
        

        for user in users:

            task = self._connect_single_user(user)

            connection_tasks.append(task)
        

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        successful_count = sum(1 for result in results if result is True)
        

        self.metrics.connection_count = len(users)

        self.metrics.successful_connections = successful_count

        return successful_count
    

    async def _connect_single_user(self, user: UserConnection) -> bool:

        """Connect single user to WebSocket."""

        try:

            user.client = RealWebSocketClient(self.ws_url, self.config)

            headers = {"Authorization": f"Bearer {user.token}"}

            success = await user.client.connect(headers)

            user.connected = success

            return success

        except Exception:

            user.connected = False

            return False


class MessageOrderingValidator:

    """Validates message ordering and cross-contamination."""
    

    def __init__(self, manager: ConcurrentWebSocketManager):

        """Initialize ordering validator."""

        self.manager = manager

        self.ordering_violations: List[Dict] = []

        self.contamination_errors: List[Dict] = []
        

    async def send_numbered_messages_concurrent(self, message_count: int = 50) -> None:

        """Send numbered messages from all connected users concurrently."""

        send_tasks = []
        

        for user_id, user in self.manager.connections.items():

            if user.connected and user.client:

                task = self._send_numbered_messages_for_user(user, message_count)

                send_tasks.append(task)
        

        await asyncio.gather(*send_tasks, return_exceptions=True)
    

    async def _send_numbered_messages_for_user(self, user: UserConnection, count: int) -> None:

        """Send numbered messages for specific user."""

        for i in range(count):

            message = {

                "type": "test_message",

                "user_id": user.user_id,

                "sequence": i,

                "content": f"Message {i} from {user.user_id}",

                "timestamp": time.time()

            }
            

            success = await user.client.send(message)

            if success:

                user.sent_messages.append(message)

                user.message_sequence += 1

                self.manager.metrics.messages_sent += 1
    

    async def collect_all_responses(self, timeout: float = 10.0) -> None:

        """Collect responses from all connected users."""

        collection_tasks = []
        

        for user_id, user in self.manager.connections.items():

            if user.connected and user.client:

                task = self._collect_user_responses(user, timeout)

                collection_tasks.append(task)
        

        await asyncio.gather(*collection_tasks, return_exceptions=True)
    

    async def _collect_user_responses(self, user: UserConnection, timeout: float) -> None:

        """Collect responses for specific user."""

        start_time = time.time()

        expected_messages = len(user.sent_messages)
        

        while (time.time() - start_time) < timeout and len(user.received_messages) < expected_messages:

            try:

                response = await user.client.receive(timeout=1.0)

                if response:

                    user.received_messages.append(response)

                    self.manager.metrics.messages_received += 1

            except Exception:

                break
    

    def validate_message_ordering(self) -> Dict[str, Any]:

        """Validate message ordering for all users."""

        ordering_results = {}

        total_violations = 0
        

        for user_id, user in self.manager.connections.items():

            if not user.connected:

                continue
                

            violations = self._check_user_message_ordering(user)

            ordering_results[user_id] = {

                "sent_count": len(user.sent_messages),

                "received_count": len(user.received_messages),

                "ordering_violations": len(violations),

                "violations": violations

            }

            total_violations += len(violations)
        

        self.manager.metrics.ordering_violations = total_violations

        return ordering_results
    

    def _check_user_message_ordering(self, user: UserConnection) -> List[Dict]:

        """Check message ordering for specific user."""

        violations = []
        
        # Extract sequence numbers from received messages

        received_sequences = []

        for msg in user.received_messages:

            if isinstance(msg, dict) and "sequence" in msg:

                received_sequences.append(msg["sequence"])
        
        # Check for ordering violations

        for i in range(1, len(received_sequences)):

            current_seq = received_sequences[i]

            previous_seq = received_sequences[i-1]
            

            if current_seq < previous_seq:

                violation = {

                    "user_id": user.user_id,

                    "position": i,

                    "expected_min": previous_seq + 1,

                    "actual": current_seq,

                    "violation_type": "out_of_order"

                }

                violations.append(violation)

                self.ordering_violations.append(violation)
        

        return violations
    

    def validate_user_isolation(self) -> Dict[str, Any]:

        """Validate no cross-contamination between users."""

        isolation_results = {}

        total_contamination = 0
        

        for user_id, user in self.manager.connections.items():

            contamination = self._check_user_contamination(user)

            isolation_results[user_id] = {

                "contamination_count": len(contamination),

                "contaminated_messages": contamination

            }

            total_contamination += len(contamination)
        

        self.manager.metrics.cross_contamination_errors = total_contamination

        return isolation_results
    

    def _check_user_contamination(self, user: UserConnection) -> List[Dict]:

        """Check for message contamination for specific user."""

        contamination = []
        

        for msg in user.received_messages:

            if isinstance(msg, dict) and "user_id" in msg:

                msg_user_id = msg["user_id"]

                if msg_user_id != user.user_id:

                    contamination_error = {

                        "receiving_user": user.user_id,

                        "message_from": msg_user_id,

                        "message_content": msg.get("content", ""),

                        "contamination_type": "cross_user_leak"

                    }

                    contamination.append(contamination_error)

                    self.contamination_errors.append(contamination_error)
        

        return contamination


class BurstMessageTester:

    """Tests burst messaging: 1000 messages in 1 second."""
    

    def __init__(self, manager: ConcurrentWebSocketManager):

        """Initialize burst message tester."""

        self.manager = manager

        self.burst_user: Optional[UserConnection] = None
        

    def setup_burst_test_user(self) -> UserConnection:

        """Setup dedicated user for burst testing."""

        user_id = f"burst-user-{uuid.uuid4().hex[:8]}"

        payload = self.manager.jwt_helper.create_valid_payload()

        payload["sub"] = user_id

        payload["email"] = f"burst@netrasystems.ai"

        token = self.manager.jwt_helper.create_token(payload)
        

        self.burst_user = UserConnection(user_id=user_id, token=token)

        self.manager.connections[user_id] = self.burst_user

        return self.burst_user
    

    async def execute_burst_test(self, message_count: int = 1000) -> Dict[str, Any]:

        """Execute burst message test: 1000 messages in 1 second."""

        if not self.burst_user:

            raise ValueError("Burst test user not setup")
        
        # Connect burst user

        self.burst_user.client = RealWebSocketClient(self.manager.ws_url, self.manager.config)

        headers = {"Authorization": f"Bearer {self.burst_user.token}"}

        connected = await self.burst_user.client.connect(headers)
        

        if not connected:

            return {"success": False, "error": "Failed to connect burst user"}
        
        # Execute burst sending

        start_time = time.time()

        await self._send_burst_messages(message_count)

        burst_time = time.time() - start_time
        

        self.manager.metrics.burst_completion_time = burst_time
        
        # Collect responses

        await self._collect_burst_responses(timeout=5.0)
        

        return {

            "success": True,

            "messages_sent": len(self.burst_user.sent_messages),

            "burst_time_seconds": burst_time,

            "messages_per_second": len(self.burst_user.sent_messages) / burst_time if burst_time > 0 else 0,

            "responses_received": len(self.burst_user.received_messages)

        }
    

    async def _send_burst_messages(self, count: int) -> None:

        """Send burst messages as fast as possible."""

        send_tasks = []
        

        for i in range(count):

            message = {

                "type": "burst_message",

                "user_id": self.burst_user.user_id,

                "sequence": i,

                "content": f"Burst message {i}",

                "timestamp": time.time()

            }
            

            task = self._send_single_burst_message(message)

            send_tasks.append(task)
        

        await asyncio.gather(*send_tasks, return_exceptions=True)
    

    async def _send_single_burst_message(self, message: Dict) -> None:

        """Send single burst message."""

        success = await self.burst_user.client.send(message)

        if success:

            self.burst_user.sent_messages.append(message)
    

    async def _collect_burst_responses(self, timeout: float) -> None:

        """Collect burst test responses."""

        start_time = time.time()
        

        while (time.time() - start_time) < timeout:

            try:

                response = await self.burst_user.client.receive(timeout=0.1)

                if response:

                    self.burst_user.received_messages.append(response)

            except Exception:

                break


class SystemResourceMonitor:

    """Monitors system resources during concurrent load test."""
    

    def __init__(self):

        """Initialize resource monitor."""

        self.initial_memory_mb = 0.0

        self.peak_memory_mb = 0.0

        self.monitoring = False

        self.monitor_task: Optional[asyncio.Task] = None
    

    def start_monitoring(self) -> None:

        """Start resource monitoring."""

        self.initial_memory_mb = self._get_memory_usage_mb()

        self.peak_memory_mb = self.initial_memory_mb

        self.monitoring = True

        self.monitor_task = asyncio.create_task(self._monitor_resources())
    

    async def stop_monitoring(self) -> Dict[str, float]:

        """Stop monitoring and return results."""

        self.monitoring = False

        if self.monitor_task:

            self.monitor_task.cancel()

            try:

                await self.monitor_task

            except asyncio.CancelledError:

                pass
        

        final_memory = self._get_memory_usage_mb()

        return {

            "initial_memory_mb": self.initial_memory_mb,

            "peak_memory_mb": self.peak_memory_mb,

            "final_memory_mb": final_memory,

            "memory_increase_mb": final_memory - self.initial_memory_mb

        }
    

    def _get_memory_usage_mb(self) -> float:

        """Get current memory usage in MB."""

        process = psutil.Process()

        return process.memory_info().rss / 1024 / 1024
    

    async def _monitor_resources(self) -> None:

        """Monitor system resources continuously."""

        while self.monitoring:

            current_memory = self._get_memory_usage_mb()

            self.peak_memory_mb = max(self.peak_memory_mb, current_memory)

            await asyncio.sleep(0.1)


@pytest.mark.asyncio

@pytest.mark.integration

class TestWebSocketConcurrentOrdering:

    """WebSocket Message Ordering Under Concurrent Load Test."""
    

    async def test_websocket_concurrent_ordering_complete(self):

        """Complete test of WebSocket message ordering under concurrent load."""

        manager = ConcurrentWebSocketManager()

        resource_monitor = SystemResourceMonitor()
        

        try:

            start_time = time.time()
            
            # Setup services

            await manager.setup_services()
            
            # Start resource monitoring

            resource_monitor.start_monitoring()
            
            # Execute test phases

            await self._execute_concurrent_connections_test(manager)

            await self._execute_message_ordering_test(manager)

            await self._execute_burst_messaging_test(manager)
            
            # Stop monitoring and collect metrics

            resource_results = await resource_monitor.stop_monitoring()

            manager.metrics.test_duration_seconds = time.time() - start_time

            manager.metrics.memory_usage_mb = resource_results["final_memory_mb"]

            manager.metrics.peak_memory_mb = resource_results["peak_memory_mb"]
            
            # Validate results

            self._validate_test_results(manager)
            

        finally:

            await self._cleanup_all_connections(manager)

            await manager.teardown_services()
    

    async def _execute_concurrent_connections_test(self, manager: ConcurrentWebSocketManager) -> None:

        """Execute concurrent connections test phase."""

        users = manager.create_test_users(100)

        connected_count = await manager.establish_concurrent_connections(users)
        
        # Validate connection success rate

        success_rate = connected_count / 100

        assert success_rate >= 0.95, f"Connection success rate {success_rate:.2%} below 95%"

        assert connected_count >= 95, f"Only {connected_count}/100 connections successful"
    

    async def _execute_message_ordering_test(self, manager: ConcurrentWebSocketManager) -> None:

        """Execute message ordering test phase."""

        validator = MessageOrderingValidator(manager)
        
        # Send numbered messages concurrently

        await validator.send_numbered_messages_concurrent(message_count=50)
        
        # Collect responses

        await validator.collect_all_responses(timeout=10.0)
        
        # Validate ordering and isolation

        ordering_results = validator.validate_message_ordering()

        isolation_results = validator.validate_user_isolation()
        
        # Assert ordering preservation

        total_violations = sum(result["ordering_violations"] for result in ordering_results.values())

        assert total_violations == 0, f"Found {total_violations} message ordering violations"
        
        # Assert user isolation

        total_contamination = sum(result["contamination_count"] for result in isolation_results.values())

        assert total_contamination == 0, f"Found {total_contamination} cross-user message contamination errors"
    

    async def _execute_burst_messaging_test(self, manager: ConcurrentWebSocketManager) -> None:

        """Execute burst messaging test phase."""

        burst_tester = BurstMessageTester(manager)

        burst_user = burst_tester.setup_burst_test_user()
        
        # Execute burst test

        burst_results = await burst_tester.execute_burst_test(message_count=1000)
        
        # Validate burst performance

        assert burst_results["success"], "Burst test failed to execute"

        assert burst_results["burst_time_seconds"] <= 2.0, f"Burst took {burst_results['burst_time_seconds']:.2f}s, expected ≤2.0s"

        assert burst_results["messages_per_second"] >= 500, f"Burst rate {burst_results['messages_per_second']:.0f} msg/s below 500"
    

    def _validate_test_results(self, manager: ConcurrentWebSocketManager) -> None:

        """Validate overall test results."""

        metrics = manager.metrics
        
        # Connection success validation

        assert metrics.successful_connections >= 95, f"Only {metrics.successful_connections}/100 connections successful"
        
        # Message delivery validation

        assert metrics.messages_sent > 0, "No messages were sent"

        assert metrics.messages_received > 0, "No messages were received"
        
        # Ordering validation

        assert metrics.ordering_violations == 0, f"Found {metrics.ordering_violations} ordering violations"
        
        # Isolation validation

        assert metrics.cross_contamination_errors == 0, f"Found {metrics.cross_contamination_errors} contamination errors"
        
        # Performance validation

        assert metrics.test_duration_seconds < 60.0, f"Test took {metrics.test_duration_seconds:.1f}s, expected <60s"
        
        # Memory validation (should not exceed 1GB increase)

        memory_increase = metrics.peak_memory_mb - metrics.memory_usage_mb

        assert memory_increase < 1024, f"Memory increase {memory_increase:.1f}MB exceeds 1GB limit"
    

    async def _cleanup_all_connections(self, manager: ConcurrentWebSocketManager) -> None:

        """Cleanup all WebSocket connections."""

        cleanup_tasks = []
        

        for user in manager.connections.values():

            if user.client and user.connected:

                task = self._cleanup_single_connection(user)

                cleanup_tasks.append(task)
        

        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    

    async def _cleanup_single_connection(self, user: UserConnection) -> None:

        """Cleanup single WebSocket connection."""

        try:

            await user.client.close()

            user.connected = False

        except Exception:

            pass  # Best effort cleanup