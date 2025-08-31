#!/usr/bin/env python
"""MISSION CRITICAL: Real-Time Chat Responsiveness Under Load Test Suite

Business Value: $500K+ ARR - Chat delivers 90% of user value
Priority: CRITICAL
Impact: Core User Experience

This test suite validates that chat remains responsive during peak usage scenarios
that beta users will experience. 

TEST COVERAGE:
1. Concurrent User Load Test - 5 simultaneous users, <2s response time
2. Agent Processing Backlog Test - Queue 10 requests, proper indicators
3. WebSocket Connection Recovery - Network disruption recovery

ACCEPTANCE CRITERIA:
✅ 5 concurrent users get responses within 2s
✅ All WebSocket events fire correctly under load  
✅ Zero message loss during normal operation
✅ Connection recovery works within 5s
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import random
from dataclasses import dataclass, field

# Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Real services infrastructure
from test_framework.real_services import get_real_services, RealServicesManager
from test_framework.environment_isolation import IsolatedEnvironment

# Import production components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.enhanced_tool_execution import (
    EnhancedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.schemas.websocket_models import WebSocketMessage


@dataclass
class LoadTestMetrics:
    """Comprehensive metrics for load testing."""
    concurrent_users: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    response_times: List[float] = field(default_factory=list)
    avg_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    events_received: Dict[str, int] = field(default_factory=dict)
    missing_events: List[str] = field(default_factory=list)
    message_loss_count: int = 0
    connection_drops: int = 0
    recovery_times: List[float] = field(default_factory=list)
    avg_recovery_time_ms: float = 0.0
    test_duration_seconds: float = 0.0
    error_rate: float = 0.0
    
    def calculate_percentiles(self):
        """Calculate response time percentiles."""
        if self.response_times:
            sorted_times = sorted(self.response_times)
            self.avg_response_time_ms = sum(sorted_times) / len(sorted_times) * 1000
            self.max_response_time_ms = max(sorted_times) * 1000
            self.min_response_time_ms = min(sorted_times) * 1000
            
            # Calculate percentiles
            n = len(sorted_times)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            self.p95_response_time_ms = sorted_times[min(p95_idx, n-1)] * 1000
            self.p99_response_time_ms = sorted_times[min(p99_idx, n-1)] * 1000
            
        if self.recovery_times:
            self.avg_recovery_time_ms = sum(self.recovery_times) / len(self.recovery_times) * 1000


class ChatResponsivenessTestClient:
    """Enhanced client for testing chat responsiveness under load."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, user_id: str, ws_manager: Optional[WebSocketManager] = None):
        self.user_id = user_id
        self.ws_manager = ws_manager
        self.websocket = None
        self.connected = False
        self.messages_sent = []
        self.messages_received = []
        self.events_received = []
        self.response_times = []
        self.last_message_time = None
        self.connection_drops = 0
        self.recovery_times = []
        self.event_tracker = {}
        
    async def connect(self, ws_url: str = "ws://localhost:8000/ws") -> bool:
        """Establish WebSocket connection with real services."""
        try:
            real_services = get_real_services()
            ws_client = real_services.create_websocket_client()
            
            # Connect with authentication
            headers = {"Authorization": f"Bearer test-token-{self.user_id}"}
            await ws_client.connect(f"chat/{self.user_id}", headers=headers)
            
            self.websocket = ws_client._websocket
            self.connected = True
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
        except Exception as e:
            logger.error(f"User {self.user_id} connection failed: {e}")
            return False
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            while self.connected and self.websocket:
                message = await self.websocket.recv()
                
                # Record timing
                if self.last_message_time:
                    response_time = time.time() - self.last_message_time
                    self.response_times.append(response_time)
                
                # Parse and track message
                try:
                    data = json.loads(message)
                    self.messages_received.append(data)
                    
                    # Track event types
                    event_type = data.get("type", "unknown")
                    self.events_received.append(event_type)
                    self.event_tracker[event_type] = self.event_tracker.get(event_type, 0) + 1
                    
                    logger.debug(f"User {self.user_id} received: {event_type}")
                except json.JSONDecodeError:
                    logger.error(f"User {self.user_id} received invalid JSON: {message}")
                    
        except Exception as e:
            logger.error(f"User {self.user_id} listen error: {e}")
            self.connected = False
    
    async def send_message(self, content: str) -> bool:
        """Send a chat message and record timing."""
        if not self.connected or not self.websocket:
            return False
            
        try:
            message = {
                "type": "chat_message",
                "content": content,
                "user_id": self.user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.last_message_time = time.time()
            await self.websocket.send(json.dumps(message))
            self.messages_sent.append(message)
            
            return True
        except Exception as e:
            logger.error(f"User {self.user_id} send error: {e}")
            return False
    
    async def simulate_network_disruption(self, duration_seconds: float = 2.0):
        """Simulate a network disruption and measure recovery."""
        if not self.websocket:
            return
            
        logger.info(f"User {self.user_id} simulating {duration_seconds}s network disruption")
        
        # Record disruption
        disruption_start = time.time()
        self.connection_drops += 1
        
        # Close connection
        await self.websocket.close()
        self.connected = False
        
        # Wait for disruption duration
        await asyncio.sleep(duration_seconds)
        
        # Attempt reconnection
        reconnect_start = time.time()
        success = await self.connect()
        
        if success:
            recovery_time = time.time() - reconnect_start
            self.recovery_times.append(recovery_time)
            logger.info(f"User {self.user_id} recovered in {recovery_time:.2f}s")
        else:
            logger.error(f"User {self.user_id} failed to recover")
            
        return success
    
    def validate_events(self) -> Tuple[bool, List[str]]:
        """Validate that all required events were received."""
        received_types = set(self.event_tracker.keys())
        missing = self.REQUIRED_EVENTS - received_types
        
        if missing:
            return False, list(missing)
        return True, []
    
    async def disconnect(self):
        """Clean disconnect."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False


class ChatLoadTestOrchestrator:
    """Orchestrates comprehensive load testing scenarios."""
    
    def __init__(self):
        self.real_services = None
        self.ws_manager = None
        self.agent_registry = None
        self.execution_engine = None
        self.supervisor_agent = None
        self.clients: List[ChatResponsivenessTestClient] = []
        self.metrics = LoadTestMetrics()
        
    async def setup(self):
        """Initialize all required services."""
        logger.info("Setting up real services for load testing")
        
        # Initialize real services
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Initialize agent components
        self.agent_registry = AgentRegistry()
        self.execution_engine = ExecutionEngine()
        
        # Set up WebSocket integration
        notifier = WebSocketNotifier(self.ws_manager)
        self.agent_registry.set_websocket_manager(self.ws_manager)
        self.execution_engine.set_notifier(notifier)
        
        # Initialize supervisor agent
        llm_manager = LLMManager()
        self.supervisor_agent = SupervisorAgent(
            llm_manager=llm_manager,
            registry=self.agent_registry,
            execution_engine=self.execution_engine
        )
        
        logger.info("Load test setup complete")
    
    async def teardown(self):
        """Clean up all resources."""
        # Disconnect all clients
        for client in self.clients:
            await client.disconnect()
        
        # Stop services
        if self.real_services:
            await self.real_services.close_all()
    
    async def test_concurrent_user_load(self, user_count: int = 5) -> LoadTestMetrics:
        """
        TEST 1.1: Concurrent User Load Test
        - 5 simultaneous users sending messages
        - Each user receives real-time updates within 2 seconds
        - WebSocket events flow correctly
        - No message loss or connection drops
        """
        logger.info(f"Starting concurrent user load test with {user_count} users")
        
        test_start = time.time()
        self.metrics = LoadTestMetrics(concurrent_users=user_count)
        
        # Create and connect users concurrently
        connect_tasks = []
        for i in range(user_count):
            client = ChatResponsivenessTestClient(f"user-{i:03d}", self.ws_manager)
            self.clients.append(client)
            connect_tasks.append(client.connect())
        
        # Wait for all connections
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        # Count successful connections
        self.metrics.successful_connections = sum(1 for r in connection_results if r is True)
        self.metrics.failed_connections = user_count - self.metrics.successful_connections
        
        if self.metrics.successful_connections == 0:
            logger.error("No users connected successfully!")
            return self.metrics
        
        logger.info(f"Connected {self.metrics.successful_connections}/{user_count} users")
        
        # Send messages from all users simultaneously
        message_tasks = []
        for client in self.clients:
            if client.connected:
                for msg_idx in range(3):  # Each user sends 3 messages
                    message = f"Test message {msg_idx} from {client.user_id}"
                    message_tasks.append(client.send_message(message))
                    await asyncio.sleep(0.1)  # Small delay between messages
        
        # Wait for all messages to be sent
        send_results = await asyncio.gather(*message_tasks, return_exceptions=True)
        self.metrics.messages_sent = sum(1 for r in send_results if r is True)
        
        # Wait for responses (max 5 seconds)
        await asyncio.sleep(5)
        
        # Collect metrics from all clients
        for client in self.clients:
            self.metrics.messages_received += len(client.messages_received)
            self.metrics.response_times.extend(client.response_times)
            
            # Track events
            for event_type, count in client.event_tracker.items():
                self.metrics.events_received[event_type] = \
                    self.metrics.events_received.get(event_type, 0) + count
            
            # Validate required events
            valid, missing = client.validate_events()
            if not valid:
                self.metrics.missing_events.extend(missing)
        
        # Calculate message loss
        expected_responses = self.metrics.messages_sent
        self.metrics.message_loss_count = max(0, expected_responses - self.metrics.messages_received)
        
        # Calculate metrics
        self.metrics.test_duration_seconds = time.time() - test_start
        self.metrics.calculate_percentiles()
        self.metrics.error_rate = self.metrics.failed_connections / user_count if user_count > 0 else 0
        
        # Log results
        self._log_test_results("Concurrent User Load Test")
        
        return self.metrics
    
    async def test_agent_processing_backlog(self, queue_size: int = 10) -> LoadTestMetrics:
        """
        TEST 1.2: Agent Processing Backlog Test
        - Queue 10 requests rapidly
        - Verify each user sees proper "processing" indicators
        - Ensure messages are processed in order
        - No user is left without feedback
        """
        logger.info(f"Starting agent processing backlog test with {queue_size} queued requests")
        
        test_start = time.time()
        self.metrics = LoadTestMetrics()
        
        # Create a single user for this test
        client = ChatResponsivenessTestClient("backlog-user", self.ws_manager)
        self.clients = [client]
        
        # Connect user
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect test user")
            return self.metrics
        
        self.metrics.successful_connections = 1
        
        # Rapidly send messages to create backlog
        logger.info(f"Sending {queue_size} rapid messages to create backlog")
        send_tasks = []
        for i in range(queue_size):
            message = f"Backlog message {i:02d} - Process this request"
            send_tasks.append(client.send_message(message))
            await asyncio.sleep(0.05)  # 50ms between messages
        
        # Wait for all messages to be sent
        send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
        self.metrics.messages_sent = sum(1 for r in send_results if r is True)
        
        # Monitor for processing indicators
        processing_events = ["agent_started", "agent_thinking", "tool_executing"]
        completion_events = ["tool_completed", "agent_completed"]
        
        # Wait for processing (max 30 seconds for backlog)
        max_wait = 30
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait:
            # Check if we've received processing indicators
            has_processing = any(
                client.event_tracker.get(event, 0) > 0 
                for event in processing_events
            )
            
            has_completion = any(
                client.event_tracker.get(event, 0) > 0
                for event in completion_events
            )
            
            if has_processing and has_completion:
                logger.info("Received both processing and completion indicators")
                break
                
            await asyncio.sleep(0.5)
        
        # Collect metrics
        self.metrics.messages_received = len(client.messages_received)
        self.metrics.response_times = client.response_times
        
        # Verify message ordering
        message_order_valid = self._verify_message_order(client.messages_received)
        
        # Track events
        self.metrics.events_received = dict(client.event_tracker)
        
        # Validate all messages got feedback
        messages_with_feedback = 0
        for msg in client.messages_sent:
            # Check if there's a corresponding response
            if any(r.get("correlation_id") == msg.get("timestamp") 
                   for r in client.messages_received):
                messages_with_feedback += 1
        
        # Calculate metrics
        self.metrics.test_duration_seconds = time.time() - test_start
        self.metrics.calculate_percentiles()
        
        # Log results
        logger.info(f"Backlog test results:")
        logger.info(f"  Messages sent: {self.metrics.messages_sent}")
        logger.info(f"  Messages received: {self.metrics.messages_received}")
        logger.info(f"  Messages with feedback: {messages_with_feedback}")
        logger.info(f"  Message order valid: {message_order_valid}")
        logger.info(f"  Events received: {self.metrics.events_received}")
        
        return self.metrics
    
    async def test_websocket_connection_recovery(self, disruption_count: int = 3) -> LoadTestMetrics:
        """
        TEST 1.3: WebSocket Connection Recovery
        - Simulate brief network disruption during active chat
        - Verify automatic reconnection and message replay
        - User sees seamless continuation
        """
        logger.info(f"Starting connection recovery test with {disruption_count} disruptions")
        
        test_start = time.time()
        self.metrics = LoadTestMetrics()
        
        # Create test users
        user_count = 3
        for i in range(user_count):
            client = ChatResponsivenessTestClient(f"recovery-user-{i}", self.ws_manager)
            self.clients.append(client)
        
        # Connect all users
        connect_tasks = [client.connect() for client in self.clients]
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        self.metrics.successful_connections = sum(1 for r in connection_results if r is True)
        
        if self.metrics.successful_connections == 0:
            logger.error("No users connected for recovery test")
            return self.metrics
        
        logger.info(f"Connected {self.metrics.successful_connections} users for recovery test")
        
        # Simulate disruptions and recovery
        for disruption_idx in range(disruption_count):
            logger.info(f"Disruption cycle {disruption_idx + 1}/{disruption_count}")
            
            # Send messages before disruption
            for client in self.clients:
                if client.connected:
                    await client.send_message(f"Pre-disruption message {disruption_idx}")
            
            await asyncio.sleep(1)
            
            # Simulate network disruption for all users
            disruption_tasks = []
            for client in self.clients:
                if client.connected:
                    disruption_duration = random.uniform(1.0, 3.0)  # 1-3 seconds
                    disruption_tasks.append(
                        client.simulate_network_disruption(disruption_duration)
                    )
            
            # Wait for all disruptions to complete
            recovery_results = await asyncio.gather(*disruption_tasks, return_exceptions=True)
            
            # Count successful recoveries
            successful_recoveries = sum(1 for r in recovery_results if r is True)
            logger.info(f"  Recovered: {successful_recoveries}/{len(self.clients)}")
            
            # Send messages after recovery
            for client in self.clients:
                if client.connected:
                    await client.send_message(f"Post-recovery message {disruption_idx}")
            
            await asyncio.sleep(2)
        
        # Collect metrics
        for client in self.clients:
            self.metrics.connection_drops += client.connection_drops
            self.metrics.recovery_times.extend(client.recovery_times)
            self.metrics.messages_sent += len(client.messages_sent)
            self.metrics.messages_received += len(client.messages_received)
        
        # Calculate recovery metrics
        self.metrics.test_duration_seconds = time.time() - test_start
        self.metrics.calculate_percentiles()
        
        if self.metrics.recovery_times:
            avg_recovery = sum(self.metrics.recovery_times) / len(self.metrics.recovery_times)
            max_recovery = max(self.metrics.recovery_times)
            
            logger.info(f"Recovery test results:")
            logger.info(f"  Total disruptions: {self.metrics.connection_drops}")
            logger.info(f"  Avg recovery time: {avg_recovery:.2f}s")
            logger.info(f"  Max recovery time: {max_recovery:.2f}s")
            logger.info(f"  Messages sent: {self.metrics.messages_sent}")
            logger.info(f"  Messages received: {self.metrics.messages_received}")
        
        return self.metrics
    
    def _verify_message_order(self, messages: List[Dict]) -> bool:
        """Verify messages are processed in order."""
        # Extract timestamps and check ordering
        timestamps = []
        for msg in messages:
            if "timestamp" in msg:
                timestamps.append(msg["timestamp"])
        
        # Check if timestamps are in order
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i-1]:
                return False
        return True
    
    def _log_test_results(self, test_name: str):
        """Log comprehensive test results."""
        logger.info(f"\n{'='*60}")
        logger.info(f"{test_name} Results")
        logger.info(f"{'='*60}")
        logger.info(f"Concurrent Users: {self.metrics.concurrent_users}")
        logger.info(f"Successful Connections: {self.metrics.successful_connections}")
        logger.info(f"Failed Connections: {self.metrics.failed_connections}")
        logger.info(f"Messages Sent: {self.metrics.messages_sent}")
        logger.info(f"Messages Received: {self.metrics.messages_received}")
        logger.info(f"Message Loss: {self.metrics.message_loss_count}")
        
        if self.metrics.response_times:
            logger.info(f"\nResponse Times:")
            logger.info(f"  Average: {self.metrics.avg_response_time_ms:.2f}ms")
            logger.info(f"  Min: {self.metrics.min_response_time_ms:.2f}ms")
            logger.info(f"  Max: {self.metrics.max_response_time_ms:.2f}ms")
            logger.info(f"  P95: {self.metrics.p95_response_time_ms:.2f}ms")
            logger.info(f"  P99: {self.metrics.p99_response_time_ms:.2f}ms")
        
        if self.metrics.events_received:
            logger.info(f"\nWebSocket Events:")
            for event_type, count in self.metrics.events_received.items():
                logger.info(f"  {event_type}: {count}")
        
        if self.metrics.missing_events:
            logger.info(f"\nMissing Required Events: {self.metrics.missing_events}")
        
        logger.info(f"\nTest Duration: {self.metrics.test_duration_seconds:.2f}s")
        logger.info(f"Error Rate: {self.metrics.error_rate:.2%}")
        logger.info(f"{'='*60}\n")


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(60)
async def test_concurrent_user_load():
    """
    CRITICAL TEST: 5 concurrent users must get responses within 2 seconds.
    
    Acceptance Criteria:
    ✅ 5 concurrent users connect successfully
    ✅ All users receive responses within 2 seconds
    ✅ All required WebSocket events are received
    ✅ Zero message loss
    """
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        # Run concurrent user load test
        metrics = await orchestrator.test_concurrent_user_load(user_count=5)
        
        # Assertions
        assert metrics.successful_connections >= 4, \
            f"Failed to connect enough users: {metrics.successful_connections}/5"
        
        assert metrics.avg_response_time_ms <= 2000, \
            f"Average response time too high: {metrics.avg_response_time_ms}ms > 2000ms"
        
        assert metrics.p95_response_time_ms <= 3000, \
            f"P95 response time too high: {metrics.p95_response_time_ms}ms > 3000ms"
        
        assert metrics.message_loss_count == 0, \
            f"Message loss detected: {metrics.message_loss_count} messages lost"
        
        # Verify all required events were received
        required_events = {"agent_started", "agent_thinking", "tool_executing", 
                          "tool_completed", "agent_completed"}
        missing_events = required_events - set(metrics.events_received.keys())
        assert not missing_events, \
            f"Missing required WebSocket events: {missing_events}"
        
        logger.info("✅ Concurrent user load test PASSED")
        
    finally:
        await orchestrator.teardown()


@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(60)
async def test_agent_processing_backlog():
    """
    CRITICAL TEST: System must handle message backlog with proper indicators.
    
    Acceptance Criteria:
    ✅ 10 queued messages are processed
    ✅ Processing indicators are shown
    ✅ Messages processed in order
    ✅ All messages receive feedback
    """
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        # Run backlog test
        metrics = await orchestrator.test_agent_processing_backlog(queue_size=10)
        
        # Assertions
        assert metrics.messages_sent == 10, \
            f"Failed to send all messages: {metrics.messages_sent}/10"
        
        assert metrics.messages_received > 0, \
            f"No responses received for backlog messages"
        
        # Verify processing indicators were shown
        processing_events = ["agent_started", "agent_thinking", "tool_executing"]
        has_processing = any(
            metrics.events_received.get(event, 0) > 0 
            for event in processing_events
        )
        assert has_processing, \
            f"No processing indicators received. Events: {metrics.events_received}"
        
        # Verify completion events
        completion_events = ["tool_completed", "agent_completed"]
        has_completion = any(
            metrics.events_received.get(event, 0) > 0
            for event in completion_events
        )
        assert has_completion, \
            f"No completion indicators received. Events: {metrics.events_received}"
        
        logger.info("✅ Agent processing backlog test PASSED")
        
    finally:
        await orchestrator.teardown()


@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(90)
async def test_websocket_connection_recovery():
    """
    CRITICAL TEST: Connection must recover within 5 seconds of disruption.
    
    Acceptance Criteria:
    ✅ Connections recover after disruption
    ✅ Recovery happens within 5 seconds
    ✅ Messages continue after recovery
    ✅ No data loss during recovery
    """
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        # Run recovery test
        metrics = await orchestrator.test_websocket_connection_recovery(disruption_count=3)
        
        # Assertions
        assert metrics.successful_connections > 0, \
            "No users connected for recovery test"
        
        assert len(metrics.recovery_times) > 0, \
            "No recovery times recorded"
        
        # All recoveries must be under 5 seconds
        max_recovery = max(metrics.recovery_times) if metrics.recovery_times else 0
        assert max_recovery <= 5.0, \
            f"Recovery took too long: {max_recovery:.2f}s > 5s"
        
        # Average recovery should be under 3 seconds
        avg_recovery = sum(metrics.recovery_times) / len(metrics.recovery_times) \
            if metrics.recovery_times else 0
        assert avg_recovery <= 3.0, \
            f"Average recovery too slow: {avg_recovery:.2f}s > 3s"
        
        # Messages should continue after recovery
        assert metrics.messages_received > 0, \
            "No messages received after recovery"
        
        logger.info("✅ WebSocket connection recovery test PASSED")
        
    finally:
        await orchestrator.teardown()


@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(120)
async def test_comprehensive_load_scenario():
    """
    COMPREHENSIVE TEST: All load scenarios combined.
    
    This test runs all three scenarios in sequence to validate
    the system under comprehensive load conditions.
    """
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        logger.info("="*80)
        logger.info("STARTING COMPREHENSIVE LOAD TEST SUITE")
        logger.info("="*80)
        
        all_passed = True
        
        # Test 1: Concurrent Users
        try:
            logger.info("\n[1/3] Running Concurrent User Load Test...")
            metrics1 = await orchestrator.test_concurrent_user_load(user_count=5)
            
            assert metrics1.successful_connections >= 4
            assert metrics1.avg_response_time_ms <= 2000
            assert metrics1.message_loss_count == 0
            
            logger.info("✅ Concurrent User Load Test PASSED")
        except AssertionError as e:
            logger.error(f"❌ Concurrent User Load Test FAILED: {e}")
            all_passed = False
        
        # Reset for next test
        await orchestrator.teardown()
        await orchestrator.setup()
        
        # Test 2: Agent Backlog
        try:
            logger.info("\n[2/3] Running Agent Processing Backlog Test...")
            metrics2 = await orchestrator.test_agent_processing_backlog(queue_size=10)
            
            assert metrics2.messages_sent == 10
            assert metrics2.messages_received > 0
            assert any(metrics2.events_received.get(e, 0) > 0 
                      for e in ["agent_started", "agent_thinking"])
            
            logger.info("✅ Agent Processing Backlog Test PASSED")
        except AssertionError as e:
            logger.error(f"❌ Agent Processing Backlog Test FAILED: {e}")
            all_passed = False
        
        # Reset for next test
        await orchestrator.teardown()
        await orchestrator.setup()
        
        # Test 3: Connection Recovery
        try:
            logger.info("\n[3/3] Running WebSocket Connection Recovery Test...")
            metrics3 = await orchestrator.test_websocket_connection_recovery(disruption_count=3)
            
            assert len(metrics3.recovery_times) > 0
            assert max(metrics3.recovery_times) <= 5.0
            assert metrics3.messages_received > 0
            
            logger.info("✅ WebSocket Connection Recovery Test PASSED")
        except AssertionError as e:
            logger.error(f"❌ WebSocket Connection Recovery Test FAILED: {e}")
            all_passed = False
        
        # Final summary
        logger.info("\n" + "="*80)
        if all_passed:
            logger.info("✅ COMPREHENSIVE LOAD TEST SUITE: ALL TESTS PASSED")
        else:
            logger.error("❌ COMPREHENSIVE LOAD TEST SUITE: SOME TESTS FAILED")
        logger.info("="*80)
        
        assert all_passed, "Not all load tests passed"
        
    finally:
        await orchestrator.teardown()


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(test_comprehensive_load_scenario())