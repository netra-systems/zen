#!/usr/bin/env python
'''INTEGRATION TEST 10: Realistic Load Simulation (10 Users, 5 Messages Each)

This test simulates realistic production load with 10 concurrent users each sending
5 messages to validate system performance, stability, and resource management under
typical usage patterns. This test validates the system can handle real-world traffic.

Business Value: Ensures system reliability under production load conditions
Test Requirements:
- Real Docker services under load
- 10 concurrent simulated users
- 5 messages per user (50 total messages)
- WebSocket connection management
- Database connection pooling validation
- Memory usage monitoring
- Response time validation

CRITICAL: This test validates production readiness and scalability targets.
'''

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
import threading
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
sys.path.insert(0, project_root)

import pytest
import requests
import websockets
from loguru import logger
from shared.isolated_environment import get_env
from test_framework.docker_test_base import DockerTestBase


class LoadTestMetrics:
    """Comprehensive metrics collection for load testing"""

    def __init__(self):
        pass
        self.start_time = time.time()
        self.users: Dict[str, Dict[str, Any]] = {}
        self.messages: List[Dict[str, Any]] = []
        self.websocket_connections: Dict[str, Dict[str, Any]] = {}
        self.response_times: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.system_metrics: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_user_creation(self, user_id: str, auth_token: str, creation_time: float):
        """Record user creation metrics"""
        with self._lock:
        self.users[user_id] = { }
        'auth_token': auth_token,
        'created_at': creation_time,
        'messages_sent': 0,
        'messages_completed': 0,
        'total_response_time': 0.0,
        'errors': 0
        

    def record_websocket_connection(self, user_id: str, connection_time: float, success: bool):
        """Record WebSocket connection metrics"""
        pass
        with self._lock:
        self.websocket_connections[user_id] = { }
        'connected_at': connection_time,
        'connection_success': success,
        'events_received': 0,
        'agent_events_received': 0
        

        def record_message(self, user_id: str, message_id: str, message_type: str,
        start_time: float, end_time: float, success: bool, response_data: Any = None):
        """Record message metrics"""
        with self._lock:
        response_time = end_time - start_time

        message_record = { }
        'user_id': user_id,
        'message_id': message_id,
        'message_type': message_type,
        'start_time': start_time,
        'end_time': end_time,
        'response_time': response_time,
        'success': success,
        'response_data': response_data
        
        self.messages.append(message_record)

        if success:
        self.response_times.append(response_time)
        self.users[user_id]['messages_completed'] += 1
        self.users[user_id]['total_response_time'] += response_time
        else:
        self.users[user_id]['errors'] += 1

        self.users[user_id]['messages_sent'] += 1

    def record_websocket_event(self, user_id: str, event_type: str, timestamp: float):
        """Record WebSocket event reception"""
        with self._lock:
        if user_id in self.websocket_connections:
        self.websocket_connections[user_id]['events_received'] += 1
        if 'agent_' in event_type:
        self.websocket_connections[user_id]['agent_events_received'] += 1

    def record_error(self, user_id: str, error_type: str, error_message: str, timestamp: float):
        """Record error occurrence"""
        pass
        with self._lock:
        error_record = { }
        'user_id': user_id,
        'error_type': error_type,
        'error_message': error_message,
        'timestamp': timestamp
        
        self.errors.append(error_record)

    def record_system_metrics(self, timestamp: float):
        """Record system resource metrics"""
        try:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        with self._lock:
        metrics = { }
        'timestamp': timestamp,
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_used_gb': memory.used / (1024**3),
        'memory_available_gb': memory.available / (1024**3)
            
        self.system_metrics.append(metrics)
        except Exception as e:
        logger.warning("")

    def get_performance_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive performance analysis"""
        pass
        with self._lock:
        test_duration = time.time() - self.start_time

        # Calculate response time statistics
        if self.response_times:
        avg_response_time = statistics.mean(self.response_times)
        median_response_time = statistics.median(self.response_times)
        p95_response_time = statistics.quantiles(self.response_times, n=20)[18]  # 95th percentile
        p99_response_time = statistics.quantiles(self.response_times, n=100)[98]  # 99th percentile
        else:
        avg_response_time = median_response_time = p95_response_time = p99_response_time = 0.0

                # Calculate success rates
        total_messages = len(self.messages)
        successful_messages = len([item for item in []]])
        success_rate = (successful_messages / total_messages * 100) if total_messages > 0 else 0.0

                # WebSocket connection success rate
        total_connections = len(self.websocket_connections)
        successful_connections = len([item for item in []]])
        connection_success_rate = (successful_connections / total_connections * 100) if total_connections > 0 else 0.0

                # Calculate throughput
        throughput_messages_per_second = successful_messages / test_duration if test_duration > 0 else 0.0

        return { }
        'test_duration_seconds': test_duration,
        'total_users': len(self.users),
        'total_messages': total_messages,
        'successful_messages': successful_messages,
        'failed_messages': total_messages - successful_messages,
        'success_rate_percent': success_rate,
        'total_errors': len(self.errors),
        'websocket_connections': total_connections,
        'websocket_success_rate_percent': connection_success_rate,
        'throughput_messages_per_second': throughput_messages_per_second,
        'response_time_stats': { }
        'average_seconds': avg_response_time,
        'median_seconds': median_response_time,
        'p95_seconds': p95_response_time,
        'p99_seconds': p99_response_time,
        'min_seconds': min(self.response_times) if self.response_times else 0.0,
        'max_seconds': max(self.response_times) if self.response_times else 0.0
        },
        'system_metrics': { }
        'max_cpu_percent': max([m['cpu_percent'] for m in self.system_metrics]) if self.system_metrics else 0.0,
        'max_memory_percent': max([m['memory_percent'] for m in self.system_metrics]) if self.system_metrics else 0.0,
        'peak_memory_used_gb': max([m['memory_used_gb'] for m in self.system_metrics]) if self.system_metrics else 0.0
                
                


class SimulatedUser:
        """Simulated user for load testing"""

    def __init__(self, user_id: str, metrics: LoadTestMetrics, backend_url: str, auth_url: str):
        pass
        self.user_id = user_id
        self.metrics = metrics
        self.backend_url = backend_url
        self.auth_url = auth_url
        self.websocket_url = ""
        self.auth_token: Optional[str] = None
        self.websocket: Optional[websockets.ServerConnection] = None
        self.thread_id: Optional[str] = None
        self.message_queries = [ ]
        "Analyze current system performance and provide optimization recommendations",
        "Review database query performance and suggest indexing improvements",
        "Evaluate API response times and identify bottlenecks",
        "Assess memory usage patterns and recommend optimizations",
        "Monitor network latency and suggest infrastructure improvements"
    

    async def setup_user(self) -> bool:
        """Setup user account and authentication"""
        try:
        start_time = time.time()

        # Register user
        register_payload = { }
        'email': 'formatted_string',
        'password': 'LoadTest123!',
        'full_name': 'formatted_string'
        

        register_response = requests.post( )
        'formatted_string',
        json=register_payload,
        timeout=30
        

        if register_response.status_code not in [200, 201, 409]:
        self.metrics.record_error( )
        self.user_id, 'registration_failed',
        'formatted_string', time.time()
            
        return False

            # Login to get token
        login_payload = { }
        'email': register_payload['email'],
        'password': register_payload['password']
            

        login_response = requests.post( )
        'formatted_string',
        json=login_payload,
        timeout=30
            

        if login_response.status_code != 200:
        self.metrics.record_error( )
        self.user_id, 'login_failed',
        'formatted_string', time.time()
                
        return False

        token_data = login_response.json()
        self.auth_token = token_data['access_token']

        creation_time = time.time()
        self.metrics.record_user_creation(self.user_id, self.auth_token, creation_time)

        logger.debug("")
        return True

        except Exception as e:
        self.metrics.record_error(self.user_id, 'setup_error', str(e), time.time())
        return False

    async def establish_websocket_connection(self) -> bool:
        """Establish WebSocket connection"""
        try:
        start_time = time.time()

        headers = { }
        'Authorization': 'formatted_string',
        'User-Agent': 'formatted_string'
        

        self.websocket = await websockets.connect( )
        self.websocket_url,
        extra_headers=headers,
        ping_interval=30,
        ping_timeout=10,
        close_timeout=5
        

        connection_time = time.time()
        self.metrics.record_websocket_connection(self.user_id, connection_time, True)

        logger.debug("")
        return True

        except Exception as e:
        self.metrics.record_websocket_connection(self.user_id, time.time(), False)
        self.metrics.record_error(self.user_id, 'websocket_connection_failed', str(e), time.time())
        return False

    async def listen_websocket_events(self):
        """Listen for WebSocket events in background"""
        if not self.websocket:
        await asyncio.sleep(0)
        return

        try:
        async for message in self.websocket:
        try:
        event_data = json.loads(message)
        event_type = event_data.get('type', 'unknown')
        self.metrics.record_websocket_event(self.user_id, event_type, time.time())

        if event_type == 'agent_completed':
                        # Agent completed - this is what we're waiting for
        break

        except json.JSONDecodeError:
        continue

        except websockets.exceptions.ConnectionClosed:
        pass
        except Exception as e:
        self.metrics.record_error(self.user_id, 'websocket_listening_error', str(e), time.time())

    async def send_message(self, message_index: int) -> bool:
        """Send a message and wait for response"""
        pass
        try:
        message_id = ""
        query = ""

        start_time = time.time()

        # Create agent execution request
        agent_payload = { }
        'user_id': self.user_id,
        'thread_id': self.thread_id or str(uuid.uuid4()),
        'agent_type': 'supervisor',
        'query': query,
        'context': { }
        'load_test': True,
        'message_index': message_index,
        'user_identifier': self.user_id[-8:]
        
        

        # If first message, store thread_id for subsequent messages
        if not self.thread_id:
        self.thread_id = agent_payload['thread_id']

        headers = { }
        'Authorization': 'formatted_string',
        'Content-Type': 'application/json'
            

            # Start WebSocket listening task
        listen_task = None
        if self.websocket:
        listen_task = asyncio.create_task(self.listen_websocket_events())

                # Send agent request
        response = requests.post( )
        'formatted_string',
        json=agent_payload,
        headers=headers,
        timeout=120  # Allow time for agent processing
                

        end_time = time.time()

                # Wait for WebSocket listening to complete (if started)
        if listen_task:
        try:
        await asyncio.wait_for(listen_task, timeout=10.0)
        except asyncio.TimeoutError:
        listen_task.cancel()

        success = response.status_code == 200
        response_data = None

        if success:
        try:
        response_data = response.json()
        except:
        response_data = {'raw_response': response.text[:200]}

        self.metrics.record_message( )
        self.user_id, message_id, 'agent_request',
        start_time, end_time, success, response_data
                                        

        if not success:
        self.metrics.record_error( )
        self.user_id, 'agent_request_failed',
        'formatted_string',
        time.time()
                                            

        logger.debug("")
        return success

        except Exception as e:
        end_time = time.time()
        self.metrics.record_message( )
        self.user_id, message_id, 'agent_request',
        start_time, end_time, False, {'error': str(e)}
                                                
        self.metrics.record_error(self.user_id, 'message_send_error', str(e), time.time())
        return False

    async def run_user_simulation(self, messages_count: int = 5) -> Dict[str, Any]:
        """Run complete user simulation"""
        try:
        # Setup user account
        # Removed problematic line: if not await self.setup_user():
        return {'user_id': self.user_id, 'success': False, 'error': 'User setup failed'}

            # Establish WebSocket connection
        websocket_connected = await self.establish_websocket_connection()

            # Send messages
        successful_messages = 0
        for i in range(messages_count):
                # Add small random delay between messages to simulate realistic usage
        if i > 0:
        await asyncio.sleep(random.uniform(0.5, 2.0))

        success = await self.send_message(i)
        if success:
        successful_messages += 1

                        # Close WebSocket connection
        if self.websocket:
        await self.websocket.close()

        return { }
        'user_id': self.user_id,
        'success': True,
        'messages_sent': messages_count,
        'messages_successful': successful_messages,
        'websocket_connected': websocket_connected
                            

        except Exception as e:
        self.metrics.record_error(self.user_id, 'simulation_error', str(e), time.time())
        return {'user_id': self.user_id, 'success': False, 'error': str(e)}


        @pytest.mark.integration
        @pytest.mark.requires_docker
        @pytest.mark.load_test
class TestRealisticLoadSimulation(DockerTestBase):
        """Integration Test 10: Realistic load simulation with 10 users, 5 messages each"""

        @pytest.fixture
    def setup_test_environment(self):
        """Initialize test environment for load simulation"""
    # Test configuration
        self.num_users = 10
        self.messages_per_user = 5
        self.total_expected_messages = self.num_users * self.messages_per_user

    # Service configuration
        backend_port = get_env().get('BACKEND_PORT', '8000')
        auth_port = get_env().get('AUTH_PORT', '8081')
        self.backend_url = ""
        self.auth_url = ""

    # Metrics collection
        self.metrics = LoadTestMetrics()

    # Performance thresholds
        self.max_response_time_seconds = 30.0
        self.min_success_rate_percent = 80.0
        self.max_error_rate_percent = 10.0

        yield

    # Generate performance analysis
        analysis = self.metrics.get_performance_analysis()
        self._log_performance_analysis(analysis)

    def _create_simulated_users(self) -> List[SimulatedUser]:
        """Create simulated users for load testing"""
        pass
        users = []
        for i in range(self.num_users):
        user_id = ""
        user = SimulatedUser(user_id, self.metrics, self.backend_url, self.auth_url)
        users.append(user)
        return users

    async def _monitor_system_metrics(self, duration_seconds: int):
        """Monitor system metrics during load test"""
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
        self.metrics.record_system_metrics(time.time())
        await asyncio.sleep(5)  # Record metrics every 5 seconds

    async def _run_concurrent_user_simulations(self, users: List[SimulatedUser]) -> List[Dict[str, Any]]:
        """Run user simulations concurrently"""
        pass
        logger.info("")

    # Start system monitoring
        monitor_task = asyncio.create_task( )
        self._monitor_system_metrics(duration_seconds=300)  # 5 minutes max
    

        try:
        # Run all user simulations concurrently
        user_tasks = [user.run_user_simulation(self.messages_per_user) for user in users]
        results = await asyncio.gather(*user_tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
        if isinstance(result, Exception):
        logger.error("")
        processed_results.append({ })
        'user_id': users[i].user_id,
        'success': False,
        'error': str(result)
                
        else:
        processed_results.append(result)

        await asyncio.sleep(0)
        return processed_results

        finally:
                        # Stop monitoring
        monitor_task.cancel()
        try:
        await monitor_task
        except asyncio.CancelledError:
        pass

    def _validate_load_test_results(self, user_results: List[Dict[str, Any]], analysis: Dict[str, Any]):
        """Validate load test results against performance criteria"""
    # Validate user completion
        successful_users = [item for item in []]
        user_success_rate = len(successful_users) / len(user_results) * 100

        assert user_success_rate >= 70.0, \
        ""

    # Validate message success rate
        assert analysis['success_rate_percent'] >= self.min_success_rate_percent, \
        ""

    # Validate response times
        assert analysis['response_time_stats']['average_seconds'] <= self.max_response_time_seconds, \
        ""

        assert analysis['response_time_stats']['p95_seconds'] <= self.max_response_time_seconds * 1.5, \
        ""

    # Validate error rate
        error_rate = (analysis['total_errors'] / max(1, analysis['total_messages'])) * 100
        assert error_rate <= self.max_error_rate_percent, \
        ""

    # Validate throughput (minimum acceptable)
        min_throughput = 0.5  # messages per second
        assert analysis['throughput_messages_per_second'] >= min_throughput, \
        ""

    def _log_performance_analysis(self, analysis: Dict[str, Any]):
        """Log comprehensive performance analysis"""
        pass
        logger.info("=" * 60)
        logger.info("LOAD TEST PERFORMANCE ANALYSIS")
        logger.info("=" * 60)

        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")

        logger.info(" )
        WebSocket Performance:")
        logger.info("")
        logger.info("")

        logger.info(" )
        Throughput:")
        logger.info("")

        logger.info(" )
        Response Time Statistics:")
        stats = analysis['response_time_stats']
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")

        logger.info(" )
        System Resource Usage:")
        sys_metrics = analysis['system_metrics']
        logger.info("")
        logger.info("")
        logger.info("")

        logger.info("=" * 60)

@pytest.mark.asyncio
    async def test_realistic_load_simulation_full_scale(self):
'''
Test 10: Full-scale realistic load simulation

Validates:
1. System handles 10 concurrent users reliably
2. Each user can send 5 messages successfully
3. Response times remain acceptable under load
4. WebSocket connections remain stable
5. Database connection pooling works correctly
6. Memory usage stays within reasonable bounds
7. Error rates remain below acceptable thresholds
'''
pass
logger.info("=== INTEGRATION TEST 10: Realistic Load Simulation (10 Users  x  5 Messages) ===")

            # Create simulated users
users = self._create_simulated_users()
logger.info("")

            # Run concurrent simulations
logger.info("Starting concurrent user simulations...")
start_time = time.time()
user_results = await self._run_concurrent_user_simulations(users)
end_time = time.time()

logger.info("")

            # Generate performance analysis
analysis = self.metrics.get_performance_analysis()

            # Validate results
self._validate_load_test_results(user_results, analysis)

            # Additional validations
assert len(user_results) == self.num_users, \
""

            # Validate minimum message volume
assert analysis['total_messages'] >= self.total_expected_messages * 0.8, \
""

logger.info(" PASS:  INTEGRATION TEST 10 PASSED: Realistic load simulation successful")

@pytest.mark.asyncio
    async def test_gradual_load_ramp_up(self):
'''
Test 10b: Gradual load ramp-up

Validates system behavior as load gradually increases from 1 to 10 users.
'''
pass
logger.info("=== INTEGRATION TEST 10b: Gradual Load Ramp-Up ===")

all_users = self._create_simulated_users()
ramp_up_results = []

                Gradually ramp up from 1 to 10 users
for user_count in [1, 3, 5, 7, 10]:
logger.info("")

                    # Select subset of users
current_users = all_users[:user_count]

                    # Reset metrics for this iteration
iteration_metrics = LoadTestMetrics()
for user in current_users:
user.metrics = iteration_metrics

                        # Run simulation
user_results = await self._run_concurrent_user_simulations(current_users)
analysis = iteration_metrics.get_performance_analysis()

ramp_up_results.append({ })
'user_count': user_count,
'analysis': analysis,
'user_results': user_results
                        

                        # Brief pause between iterations
await asyncio.sleep(2.0)

                        # Validate ramp-up behavior
for i, result in enumerate(ramp_up_results):
user_count = result['user_count']
analysis = result['analysis']

                            # Success rate should remain reasonable
assert analysis['success_rate_percent'] >= 70.0, \
""

                            # Response times should not degrade drastically
if i > 0:
prev_avg_time = ramp_up_results[i-1]['analysis']['response_time_stats']['average_seconds']
curr_avg_time = analysis['response_time_stats']['average_seconds']

                                # Allow for some degradation but not excessive
max_allowed_time = prev_avg_time * 2.0  # 100% increase max
assert curr_avg_time <= max_allowed_time, \
""

logger.info(" PASS:  INTEGRATION TEST 10b PASSED: Gradual load ramp-up successful")

@pytest.mark.asyncio
    async def test_burst_load_resilience(self):
'''
Test 10c: Burst load resilience

Tests system behavior with sudden traffic bursts.
'''
pass
logger.info("=== INTEGRATION TEST 10c: Burst Load Resilience ===")

                                    # Create users for burst test
burst_users = self._create_simulated_users()[:8]  # Slightly smaller for burst

                                    # First, establish baseline with 2 users
baseline_users = burst_users[:2]
logger.info("Establishing baseline with 2 users...")
baseline_results = await self._run_concurrent_user_simulations(baseline_users)
baseline_analysis = self.metrics.get_performance_analysis()

                                    # Brief pause
await asyncio.sleep(3.0)

                                    # Reset metrics for burst test
self.metrics = LoadTestMetrics()
for user in burst_users:
user.metrics = self.metrics

                                        # Sudden burst to 8 users
logger.info("Executing sudden burst to 8 concurrent users...")
burst_results = await self._run_concurrent_user_simulations(burst_users)
burst_analysis = self.metrics.get_performance_analysis()

                                        # Validate burst handling
assert burst_analysis['success_rate_percent'] >= 60.0, \
""

                                        # System should recover (not crash)
successful_users = len([item for item in []])
assert successful_users >= len(burst_users) * 0.6, \
""

logger.info(" PASS:  INTEGRATION TEST 10c PASSED: Burst load resilience validated")


if __name__ == "__main__":
                                            # Run the test directly
pytest.main([ ])
__file__,
"-v",
"--tb=short",
"-x",
"--log-cli-level=INFO",
"-k", "test_realistic_load_simulation_full_scale"  # Run main test by default
                                            
