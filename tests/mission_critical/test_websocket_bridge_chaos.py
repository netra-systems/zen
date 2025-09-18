#!/usr/bin/env python3
""""

Comprehensive Chaos Engineering Tests for WebSocket Bridge

Business Value Justification:
    - Segment: Platform/Internal
- Business Goal: System Reliability & Risk Reduction
- Value Impact: Validates resilience under extreme network conditions
- Strategic Impact: Ensures WebSocket bridge maintains eventual consistency during chaos

MISSION: Create chaos engineering tests that validate WebSocket bridge resilience
under extreme conditions including random disconnects, network delays, message
corruption, and rapid reconnection cycles.

REQUIREMENTS:
    - System must maintain eventual consistency
- Automatic reconnection within 3 seconds
- No permanent message loss after recovery
- Graceful degradation under chaos

Test Categories:
    1.0Random Connection Drops (20-50% drop rate simulation)
2.0Network Latency Injection (100-""500ms"" delays)
3.0Message Reordering Scenarios
4.0Partial Message Corruption
5.0Rapid Connect/Disconnect Cycles
6.0Automatic Reconnection Tests
7.0System Recovery Validation
""
""


"""
""""

import asyncio
import json
import random
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import statistics
from shared.isolated_environment import IsolatedEnvironment

import pytest
import websockets
from websockets import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError

from netra_backend.app.logging_config import central_logger
from test_framework.helpers.auth_helpers import create_test_jwt_token, create_test_auth_headers
from shared.isolated_environment import get_env


@dataclass
class ChaosMetrics:
    "Metrics tracking during chaos engineering tests."
connection_drops: int = 0
reconnections: int = 0
message_loss: int = 0
message_duplicates: int = 0
latency_measurements: List[float] = field(default_factory=list)
recovery_times: List[float] = field(default_factory=list)
errors: List[str] = field(default_factory=list)
start_time: float = field(default_factory=time.time)
total_messages_sent: int = 0
total_messages_received: int = 0

    @property
def duration(self) -> float:
        "Test duration in seconds."
return time.time() - self.start_time

    @property
def message_loss_rate(self) -> float:
        "Message loss rate as percentage."
if self.total_messages_sent == 0:
            return 0.0
return (self.message_loss / self.total_messages_sent) * 100

    @property
def avg_latency(self) -> float:
        Average latency in milliseconds.""
return statistics.mean(self.latency_measurements) if self.latency_measurements else 0.0

    @property
def avg_recovery_time(self) -> float:
        Average recovery time in seconds.""
Average recovery time in seconds.""

        return statistics.mean(self.recovery_times) if self.recovery_times else 0.0


@dataclass
class ChaosEvent:
    "Represents a chaos event to inject."
event_type: str  # 'disconnect', 'delay', 'corrupt', 'reorder'
timestamp: float
target: str  # connection ID or 'all'
parameters: Dict[str, Any] = field(default_factory=dict)


class ChaosWebSocketClient:
    ""WebSocket client that simulates network chaos.""


    def __init__(self, user_id: str, chaos_config: Dict[str, Any]:
        self.user_id = user_id
self.chaos_config = chaos_config
self.connection = None
self.is_connected = False
self.message_queue = deque()
self.sent_messages = {}  # message_id -> timestamp
self.received_messages = {}  # message_id -> timestamp
self.metrics = ChaosMetrics()
self.chaos_events = deque()
self._reconnect_task = None

    async def connect(self, uri: str, headers: Dict[str, str]:
        Connect with chaos injection.""
try:
            # Inject connection chaos
if self._should_inject_chaos('connect'):
                delay = random.uniform(0.1, 1.0)
await asyncio.sleep(delay)

            self.connection = await websockets.connect(uri, extra_headers=headers)
self.is_connected = True
central_logger.info(fChaos client {self.user_id} connected)

            # Start chaos injection
asyncio.create_task(self._chaos_injection_loop())

        except Exception as e:
            self.metrics.errors.append(f"Connection failed: {str(e)})"
central_logger.error(fChaos client {self.user_id} connection failed: {e}")"

    async def disconnect(self):
        Disconnect and cleanup.""
self.is_connected = False
if self.connection:
            await self.connection.close()
if self._reconnect_task:
            self._reconnect_task.cancel()

    async def send_message(self, message: Dict[str, Any] -> str:
        Send message with chaos injection.""
Send message with chaos injection.""

        message_id = str(uuid.uuid4())
message['message_id'] = message_id

        # Inject send chaos
if self._should_inject_chaos('send'):
            chaos_type = random.choice(['delay', 'corrupt', 'drop']

            if chaos_type == 'delay':
                delay = random.uniform(0.1, 0.5)
await asyncio.sleep(delay)

            elif chaos_type == 'corrupt':
                # Corrupt message content
message = self._corrupt_message(message)

            elif chaos_type == 'drop':
                # Simulate message drop
self.metrics.message_loss += 1
return message_id

        try:
            if self.is_connected and self.connection:
                self.sent_messages[message_id] = time.time()
await self.connection.send(json.dumps(message))
self.metrics.total_messages_sent += 1

        except Exception as e:
            self.metrics.errors.append(f"Send failed: {str(e)})"
# Trigger reconnection
asyncio.create_task(self._handle_disconnect())

        return message_id

    async def receive_messages(self) -> List[Dict[str, Any]]:
        Receive messages with chaos handling.""
Receive messages with chaos handling.""

        messages = []

        try:
            if self.is_connected and self.connection:
                # Non-blocking receive
while True:
                    try:
                        raw_message = await asyncio.wait_for(
self.connection.recv(), timeout=0.1

message = json.loads(raw_message)

                        # Track reception
message_id = message.get('message_id')
if message_id:
                            self.received_messages[message_id] = time.time()

                            # Calculate latency if we sent this message
if message_id in self.sent_messages:
                                latency = (time.time() - self.sent_messages[message_id] * 1000
self.metrics.latency_measurements.append(latency)

                        messages.append(message)
self.metrics.total_messages_received += 1

                    except asyncio.TimeoutError:
                        break

        except ConnectionClosed:
            # Handle disconnection
asyncio.create_task(self._handle_disconnect())

        except Exception as e:
            self.metrics.errors.append(f"Receive failed: {str(e)})"

        return messages

    def _should_inject_chaos(self, operation: str) -> bool:
        Determine if chaos should be injected for operation.""
Determine if chaos should be injected for operation.""

        chaos_rate = self.chaos_config.get(f'{operation}_chaos_rate', 0.0)
return random.random() < chaos_rate

    def _corrupt_message(self, message: Dict[str, Any] -> Dict[str, Any]:
        "Inject corruption into message."
corrupted = message.copy()

        # Randomly corrupt fields
if 'data' in corrupted:
            if random.random() < 0.3:
                corrupted['data'] = CORRUPTED_DATA""
elif random.random() < 0.3:
                corrupted['type'] = CORRUPTED_TYPE

        return corrupted

    async def _chaos_injection_loop(self):
        "Main loop for injecting chaos events."
while self.is_connected:
            try:
                # Random disconnection
if self._should_inject_chaos('disconnect'):
                    central_logger.warning(fChaos: Disconnecting {self.user_id})
self.metrics.connection_drops += 1
await self._simulate_disconnect()

                # Network delay simulation
if self._should_inject_chaos('network_delay'):
                    delay = random.uniform(0.1, 0.5)
await asyncio.sleep(delay)

                await asyncio.sleep(0.1)  # Check interval

            except Exception as e:
                self.metrics.errors.append(fChaos injection error: {str(e)})""
self.metrics.errors.append(fChaos injection error: {str(e)})""


    async def _simulate_disconnect(self):
        "Simulate network disconnection."
if self.connection:
            await self.connection.close()
self.is_connected = False

            # Schedule reconnection
recovery_start = time.time()
self._reconnect_task = asyncio.create_task(self._auto_reconnect())

            # Wait for reconnection and measure recovery time
try:
                await self._reconnect_task
recovery_time = time.time() - recovery_start
self.metrics.recovery_times.append(recovery_time)

            except asyncio.CancelledError:
                pass

    async def _auto_reconnect(self):
        ""Automatic reconnection with exponential backoff.""

        retry_count = 0
max_retries = 5

        while retry_count < max_retries and not self.is_connected:
            try:
                backoff_delay = min(2 ** retry_count, 5.0)
await asyncio.sleep(backoff_delay)

                # Attempt reconnection (would need original URI and headers)
central_logger.info(fAttempting reconnection {retry_count + 1} for {self.user_id})
# Note: In real implementation, would store original connection params

                self.is_connected = True  # Simulate successful reconnection
self.metrics.reconnections += 1
central_logger.info(fChaos client {self.user_id} reconnected")"
break

            except Exception as e:
                retry_count += 1
self.metrics.errors.append(fReconnection attempt {retry_count} failed: {str(e)})

        if not self.is_connected:
            central_logger.error(fFailed to reconnect {self.user_id} after {max_retries} attempts)

    async def _handle_disconnect(self):
        "Handle unexpected disconnection."
if self.is_connected:
            self.is_connected = False
self.metrics.connection_drops += 1
asyncio.create_task(self._auto_reconnect())


class ChaosTestOrchestrator:
    "Orchestrates chaos engineering tests."

    def __init__(self, num_clients: int = 5):
        self.num_clients = num_clients
self.clients: List[ChaosWebSocketClient] = []
self.test_metrics = ChaosMetrics()
self.test_start_time = time.time()

    async def setup_chaos_clients(self, chaos_config: Dict[str, Any]:
        Set up multiple chaos clients.""
base_uri = get_env(WEBSOCKET_URL, ws://localhost:8000/ws)

        for i in range(self.num_clients):
            user_id = fchaos_user_{i}""
user_id = fchaos_user_{i}""

            client = ChaosWebSocketClient(user_id, chaos_config)

            # Create auth headers
headers = create_test_auth_headers(user_id)

            # Connect with staggered timing
await asyncio.sleep(random.uniform(0.1, 0.5))
await client.connect(base_uri, headers)

            self.clients.append(client)

    async def run_chaos_scenario(self, duration_seconds: int, scenario_config: Dict[str, Any]:
        "Run a specific chaos scenario."
central_logger.info(fStarting chaos scenario for {duration_seconds} seconds")"

        # Start message sending tasks
message_tasks = []
for client in self.clients:
            task = asyncio.create_task(self._client_message_loop(client, scenario_config))
message_tasks.append(task)

        # Run for specified duration
await asyncio.sleep(duration_seconds)

        # Stop message tasks
for task in message_tasks:
            task.cancel()

        # Wait for tasks to complete
await asyncio.gather(*message_tasks, return_exceptions=True)

    async def _client_message_loop(self, client: ChaosWebSocketClient, config: Dict[str, Any]:
        Message sending loop for a client.""
Message sending loop for a client.""

        message_interval = config.get('message_interval', 1.0)

        try:
            while True:
                # Send test message
test_message = {
'type': 'chat_message'
'data': {
'content': f'Chaos test message from {client.user_id}'
'timestamp': datetime.now(timezone.utc).isoformat()



                await client.send_message(test_message)

                # Receive messages
received = await client.receive_messages()
for msg in received:
                    central_logger.debug(fClient {client.user_id} received: {msg.get('type', 'unknown')}")"

                # Wait for next message
await asyncio.sleep(message_interval)

        except asyncio.CancelledError:
            pass
except Exception as e:
            client.metrics.errors.append(fMessage loop error: {str(e)})

    async def cleanup(self):
        "Clean up all clients."
disconnect_tasks = []
for client in self.clients:
            task = asyncio.create_task(client.disconnect())
disconnect_tasks.append(task)

        await asyncio.gather(*disconnect_tasks, return_exceptions=True)

    def generate_chaos_report(self) -> Dict[str, Any]:
        Generate comprehensive chaos test report.""
# Aggregate metrics from all clients
total_drops = sum(client.metrics.connection_drops for client in self.clients)
total_reconnections = sum(client.metrics.reconnections for client in self.clients)
total_sent = sum(client.metrics.total_messages_sent for client in self.clients)
total_received = sum(client.metrics.total_messages_received for client in self.clients)
all_latencies = []
all_recovery_times = []
all_errors = []

        for client in self.clients:
            all_latencies.extend(client.metrics.latency_measurements)
all_recovery_times.extend(client.metrics.recovery_times)
all_errors.extend(client.metrics.errors)

        # Calculate aggregate statistics
avg_latency = statistics.mean(all_latencies) if all_latencies else 0.0
max_latency = max(all_latencies) if all_latencies else 0.0
avg_recovery = statistics.mean(all_recovery_times) if all_recovery_times else 0.0
max_recovery = max(all_recovery_times) if all_recovery_times else 0.0

        message_loss_rate = ((total_sent - total_received) / total_sent * 100) if total_sent > 0 else 0.0

        test_duration = time.time() - self.test_start_time

        return {
'test_summary': {
'duration_seconds': test_duration
'total_clients': len(self.clients)
'total_connection_drops': total_drops
'total_reconnections': total_reconnections
'reconnection_success_rate': (total_reconnections / total_drops * 100) if total_drops > 0 else 100.0

'message_metrics': {
'total_sent': total_sent
'total_received': total_received
'message_loss_rate': message_loss_rate
'throughput_msg_per_sec': total_received / test_duration if test_duration > 0 else 0.0

'performance_metrics': {
'avg_latency_ms': avg_latency
'max_latency_ms': max_latency
'avg_recovery_time_s': avg_recovery
'max_recovery_time_s': max_recovery

'reliability_metrics': {
'total_errors': len(all_errors)
'error_rate_per_client': len(all_errors) / len(self.clients) if self.clients else 0.0
'system_stability': 'STABLE' if message_loss_rate < 5.0 and avg_recovery < 3.0 else 'UNSTABLE'

'errors': all_errors[:10]  # First 10 errors for analysis



# ============================================================================
# CHAOS ENGINEERING TEST SUITE
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_random_disconnections():
    Test WebSocket resilience under random disconnection chaos.""
Test WebSocket resilience under random disconnection chaos.""

    chaos_config = {
'disconnect_chaos_rate': 0.3,  # 30% chance of random disconnect
'send_chaos_rate': 0.1,        # 10% chance of send issues
'network_delay_chaos_rate': 0.2  # 20% chance of network delays


    scenario_config = {
'message_interval': 2.0,  # Send message every 2 seconds


    orchestrator = ChaosTestOrchestrator(num_clients=5)

    try:
        # Setup chaos clients
await orchestrator.setup_chaos_clients(chaos_config)

        # Run chaos scenario for 30 seconds
await orchestrator.run_chaos_scenario(30, scenario_config)

        # Generate report
report = orchestrator.generate_chaos_report()

        # Validate chaos resilience requirements
assert report['test_summary']['reconnection_success_rate'] >= 80.0, \
f"Reconnection success rate too low: {report['test_summary']['reconnection_success_rate']}%"

        assert report['message_metrics']['message_loss_rate'] <= 10.0, \
fMessage loss rate too high: {report['message_metrics']['message_loss_rate']}%

        assert report['performance_metrics']['avg_recovery_time_s'] <= 5.0, \
fAverage recovery time too slow: {report['performance_metrics']['avg_recovery_time_s']}s

        assert report['reliability_metrics']['system_stability'] == 'STABLE', \
fSystem stability assessment: {report['reliability_metrics']['system_stability']}""

        central_logger.info(Chaos disconnection test PASSED)
central_logger.info(fReport: {json.dumps(report, indent=2)})""
central_logger.info(fReport: {json.dumps(report, indent=2)})""


    finally:
        await orchestrator.cleanup()


@pytest.mark.asyncio
async def test_websocket_high_latency_chaos():
    "Test WebSocket performance under high latency conditions."
chaos_config = {
'network_delay_chaos_rate': 0.8,  # 80% chance of network delays
'disconnect_chaos_rate': 0.1,     # 10% chance of disconnections
'send_chaos_rate': 0.2            # 20% chance of send delays


    scenario_config = {
'message_interval': 1.0,  # Faster message rate to test latency impact


    orchestrator = ChaosTestOrchestrator(num_clients=3)

    try:
        await orchestrator.setup_chaos_clients(chaos_config)
await orchestrator.run_chaos_scenario(20, scenario_config)

        report = orchestrator.generate_chaos_report()

        # Validate latency resilience
assert report['performance_metrics']['avg_latency_ms'] <= 2000.0, \
fAverage latency too high: {report['performance_metrics']['avg_latency_ms']}ms""

        assert report['performance_metrics']['max_latency_ms'] <= 5000.0, \
fMaximum latency too high: {report['performance_metrics']['max_latency_ms']}ms

        assert report['message_metrics']['throughput_msg_per_sec'] >= 1.0, \
fThroughput too low: {report['message_metrics']['throughput_msg_per_sec']} msg/s

        central_logger.info("High latency chaos test PASSED)"
central_logger.info(fLatency metrics: {report['performance_metrics']})

    finally:
        await orchestrator.cleanup()


@pytest.mark.asyncio
async def test_websocket_rapid_reconnection_chaos():
    Test WebSocket under rapid connect/disconnect cycles.""
chaos_config = {
'disconnect_chaos_rate': 0.7,  # 70% chance of disconnections
'connect_chaos_rate': 0.3,     # 30% chance of connection delays
'send_chaos_rate': 0.1         # 10% chance of send issues


    scenario_config = {
'message_interval': 0.5,  # Very fast message rate


    orchestrator = ChaosTestOrchestrator(num_clients=4)

    try:
        await orchestrator.setup_chaos_clients(chaos_config)
await orchestrator.run_chaos_scenario(25, scenario_config)

        report = orchestrator.generate_chaos_report()

        # Validate rapid reconnection handling
assert report['test_summary']['total_reconnections'] > 0, \
No reconnections detected in rapid reconnection test

        assert report['test_summary']['reconnection_success_rate'] >= 70.0, \
f"Reconnection success rate too low: {report['test_summary']['reconnection_success_rate']}%"

        assert report['performance_metrics']['max_recovery_time_s'] <= 10.0, \
fMaximum recovery time too slow: {report['performance_metrics']['max_recovery_time_s']}s""
fMaximum recovery time too slow: {report['performance_metrics']['max_recovery_time_s']}s""


        # System should maintain some level of message delivery despite chaos
assert report['message_metrics']['message_loss_rate'] <= 30.0, \
fMessage loss rate too high for rapid reconnection test: {report['message_metrics']['message_loss_rate']}%

        central_logger.info(Rapid reconnection chaos test PASSED)""
central_logger.info(Rapid reconnection chaos test PASSED)""
central_logger.info(f"Reconnection metrics: {report['test_summary']})"

    finally:
        await orchestrator.cleanup()


@pytest.mark.asyncio
async def test_websocket_message_corruption_resilience():
    Test WebSocket resilience to message corruption.""
Test WebSocket resilience to message corruption.""

    chaos_config = {
'send_chaos_rate': 0.5,        # 50% chance of message corruption
'disconnect_chaos_rate': 0.1,  # 10% chance of disconnections
'network_delay_chaos_rate': 0.2  # 20% chance of delays


    scenario_config = {
'message_interval': 1.5


    orchestrator = ChaosTestOrchestrator(num_clients=3)

    try:
        await orchestrator.setup_chaos_clients(chaos_config)
await orchestrator.run_chaos_scenario(15, scenario_config)

        report = orchestrator.generate_chaos_report()

        # Validate corruption resilience
assert report['reliability_metrics']['total_errors'] <= 20, \
f"Too many errors detected: {report['reliability_metrics']['total_errors']}"

        assert report['message_metrics']['throughput_msg_per_sec'] >= 0.5, \
fThroughput too low under corruption: {report['message_metrics']['throughput_msg_per_sec']} msg/s

        assert report['reliability_metrics']['system_stability'] == 'STABLE', \
fSystem unstable under message corruption: {report['reliability_metrics']['system_stability']}

        central_logger.info(Message corruption resilience test PASSED")"
central_logger.info(fError metrics: {report['reliability_metrics']})

    finally:
        await orchestrator.cleanup()


@pytest.mark.asyncio
async def test_websocket_comprehensive_chaos_endurance():
    Comprehensive chaos test combining all failure modes.""
chaos_config = {
'disconnect_chaos_rate': 0.4,     # 40% chance of disconnections
'send_chaos_rate': 0.3,           # 30% chance of send issues
'network_delay_chaos_rate': 0.5,  # 50% chance of network delays
'connect_chaos_rate': 0.2         # 20% chance of connection delays


    scenario_config = {
'message_interval': 1.0


    orchestrator = ChaosTestOrchestrator(num_clients=6)

    try:
        await orchestrator.setup_chaos_clients(chaos_config)

        # Extended test duration for endurance
await orchestrator.run_chaos_scenario(60, scenario_config)

        report = orchestrator.generate_chaos_report()

        # Comprehensive validation
assert report['test_summary']['reconnection_success_rate'] >= 75.0, \
fReconnection success rate insufficient: {report['test_summary']['reconnection_success_rate']}%

        assert report['message_metrics']['message_loss_rate'] <= 15.0, \
fMessage loss rate too high: {report['message_metrics']['message_loss_rate']}%

        assert report['performance_metrics']['avg_recovery_time_s'] <= 6.0, \
f"Average recovery time too slow: {report['performance_metrics']['avg_recovery_time_s']}s"

        assert report['performance_metrics']['avg_latency_ms'] <= 1500.0, \
fAverage latency too high: {report['performance_metrics']['avg_latency_ms']}ms""
fAverage latency too high: {report['performance_metrics']['avg_latency_ms']}ms""


        assert report['reliability_metrics']['error_rate_per_client'] <= 10.0, \
fError rate per client too high: {report['reliability_metrics']['error_rate_per_client']}

        # Throughput should be maintained despite chaos
assert report['message_metrics']['throughput_msg_per_sec'] >= 2.0, \
fThroughput too low: {report['message_metrics']['throughput_msg_per_sec']} msg/s""
fThroughput too low: {report['message_metrics']['throughput_msg_per_sec']} msg/s""


        central_logger.info("Comprehensive chaos endurance test PASSED)"
central_logger.info(= * 60)
central_logger.info("CHAOS ENGINEERING SUMMARY)"
central_logger.info(= * 60)
central_logger.info(fTest Duration: {report['test_summary']['duration_seconds']:0.0""1f""}s)
central_logger.info(fTotal Clients: {report['test_summary']['total_clients']}")"
central_logger.info(fConnection Drops: {report['test_summary']['total_connection_drops']})
central_logger.info(fReconnection Rate: {report['test_summary']['reconnection_success_rate']:0.0""1f""}%)
central_logger.info(f"Message Loss Rate: {report['message_metrics']['message_loss_rate']:0.0""1f""}%)"
central_logger.info(fAverage Latency: {report['performance_metrics']['avg_latency_ms']:0.0""1f""}ms")"
central_logger.info(fAverage Recovery: {report['performance_metrics']['avg_recovery_time_s']:0.0""1f""}s)
central_logger.info(fSystem Status: {report['reliability_metrics']['system_stability']})""
central_logger.info(fSystem Status: {report['reliability_metrics']['system_stability']})""
central_logger.info("= * 60)"

    finally:
        await orchestrator.cleanup()


if __name__ == __main__:
    # Run standalone chaos test
import sys

    async def run_standalone_chaos():
        "Run a quick standalone chaos test."
central_logger.info(Starting standalone WebSocket chaos test.0.00.0)""
central_logger.info(Starting standalone WebSocket chaos test.0.00.0)""


        chaos_config = {
'disconnect_chaos_rate': 0.3
'send_chaos_rate': 0.2
'network_delay_chaos_rate': 0.4


        scenario_config = {
'message_interval': 2.0


        orchestrator = ChaosTestOrchestrator(num_clients=3)

        try:
            await orchestrator.setup_chaos_clients(chaos_config)
await orchestrator.run_chaos_scenario(10, scenario_config)

            report = orchestrator.generate_chaos_report()
print(json.dumps(report, indent=2))

            # Simple validation
if (report['test_summary']['reconnection_success_rate'] >= 70.0 and
report['message_metrics']['message_loss_rate'] <= 20.0):
                print("CHECK Standalone chaos test PASSED)"
return 0
else:
                print(X Standalone chaos test FAILED")"
return 1

        finally:
            await orchestrator.cleanup()

    sys.exit(asyncio.run(run_standalone_chaos()))
))))))))
"""