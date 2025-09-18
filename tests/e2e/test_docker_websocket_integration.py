#!/usr/bin/env python
'''
'''
MISSION CRITICAL: Docker-WebSocket Integration E2E Tests

Business Value Justification (BVJ):
    - Segment: Platform/Internal - System Stability & User Experience
- Business Goal: Validate full-stack integration supporting chat business value ($"500K" plus ARR)
- Value Impact: Ensures Docker stability + WebSocket events = reliable AI chat interactions
- Strategic Impact: Comprehensive validation prevents system-wide failures affecting revenue

This test suite validates that Docker stability improvements and WebSocket bridge enhancements
work together in real-world scenarios to deliver substantive chat business value.

Test Scenarios:
    1. Full Agent Execution Flow - Docker services + WebSocket events + real agent tasks
2. Multi-User Concurrent Execution - 5 concurrent users with thread isolation validation
3. Failure Recovery Scenarios - Service restarts, disconnections, orchestrator failures
4. Performance Under Load - 10 agents, 100+ WebSocket events/sec, resource monitoring

CRITICAL: Uses real services only. NO MOCKS. Real Docker + Real WebSocket + Real Agents.
'''
'''

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import subprocess
import psutil
import websockets
from websockets import ConnectionClosedError
from shared.isolated_environment import IsolatedEnvironment

        # CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

            # Core system components
from test_framework.unified_docker_manager import get_default_manager, ServiceHealth, ContainerState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.orchestration.agent_execution_registry import get_agent_execution_registry
from tests.e2e.real_websocket_client import RealWebSocketClient, ConnectionState
from test_framework.http_client import UnifiedHTTPClient, ClientConfig
from shared.isolated_environment import get_env

            # Test utilities
from tests.e2e.real_services_health import ServiceHealthMonitor
from test_framework.docker_port_discovery import DockerPortDiscovery


class TestResult(Enum):
    """Test result states."""
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    ERROR = "error"


    @dataclass
class PerformanceMetrics:
    """Performance metrics for integration testing."""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Docker metrics
    docker_startup_time_ms: float = 0.0
    docker_health_check_time_ms: float = 0.0
    container_memory_usage_mb: float = 0.0
    container_cpu_usage_percent: float = 0.0

    # WebSocket metrics
    websocket_connection_time_ms: float = 0.0
    websocket_events_sent: int = 0
    websocket_events_received: int = 0
    websocket_event_delivery_rate: float = 0.0

    # Agent metrics
    agent_execution_time_ms: float = 0.0
    agent_response_time_ms: float = 0.0
    tools_executed: int = 0

    # System metrics
    thread_isolation_violations: int = 0
    memory_leaks_detected: int = 0
    error_count: int = 0
    recovery_attempts: int = 0

    def complete(self):
        """Mark metrics as complete."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()


        @dataclass
class TestExecutionContext:
        """Context for test execution with real services."""
        pass
        docker_manager: Any
        websocket_bridge: AgentWebSocketBridge
        agent_service: AgentService
        health_checker: ServiceHealthMonitor
        docker_ports: Dict[str, int]

    # Test state
        active_websocket_clients: List[RealWebSocketClient] = field(default_factory=list)
        active_agent_threads: Set[str] = field(default_factory=set)
        metrics_collection: List[PerformanceMetrics] = field(default_factory=list)


class DockerWebSocketIntegrationTests:
        '''
        '''
        Comprehensive E2E integration tests validating Docker and WebSocket systems
        working together to deliver business value through reliable AI chat interactions.
        '''
        '''

    def __init__(self):
        pass
        self.context: Optional[TestExecutionContext] = None
        self.test_results: Dict[str, TestResult] = {}
        self.performance_metrics: List[PerformanceMetrics] = []

    async def setup_test_environment(self) -> TestExecutionContext:
        '''
        '''
        Setup complete test environment with real Docker services and WebSocket integration.

        Business Value: Ensures test environment matches production for reliable validation.
        '''
        '''
        logger.info("[U+1F680] Setting up Docker-WebSocket integration test environment)"

    # Initialize Docker manager - this is the SSOT for Docker operations
        docker_manager = get_default_manager()

    # Start Docker environment with automatic conflict resolution
        logger.info("[U+1F4E6] Starting Docker services with UnifiedDockerManager)"
        env_name, ports = await asyncio.to_thread(docker_manager.acquire_environment)

    # Wait for services to be healthy - critical for reliable testing
        logger.info("[U+1F3E5] Waiting for service health validation)"
        await asyncio.to_thread(docker_manager.wait_for_services, timeout=120)

    # Check service health to validate all services are operational
        if hasattr(docker_manager, 'service_health') and docker_manager.service_health:
        for service_name, health in docker_manager.service_health.items():
        if not health.is_healthy:
        raise RuntimeError("")
        else:
                    # If no health data available, just log the health report
        health_report_str = docker_manager.get_health_report()
        logger.info("")

        logger.info(" PASS:  All Docker services are healthy and operational)"

                    # Initialize WebSocket bridge - SSOT for WebSocket-Agent integration
        websocket_bridge = AgentWebSocketBridge()
        await websocket_bridge.ensure_integration()

        bridge_status = await websocket_bridge.get_status()
        if bridge_status.get('state') != IntegrationState.ACTIVE.value:
        raise RuntimeError("WebSocket bridge integration failed to reach ACTIVE state)"

        logger.info(" PASS:  WebSocket-Agent bridge integration is ACTIVE)"

                        # Initialize agent service using the bridge
        agent_service = AgentService()
        await agent_service.initialize()

                        # Setup health checker for continuous monitoring
        health_checker = ServiceHealthMonitor()

                        # Create test execution context
        self.context = TestExecutionContext( )
        docker_manager=docker_manager,
        websocket_bridge=websocket_bridge,
        agent_service=agent_service,
        health_checker=health_checker,
        docker_ports=ports
                        

        logger.info(" TARGET:  Test environment setup complete - ready for integration testing)"
        return self.context

    async def cleanup_test_environment(self):
        '''
        '''
        Comprehensive cleanup of test environment.

        Business Value: Prevents resource leaks that could affect subsequent tests.
        '''
        '''
        pass
        if not self.context:
        await asyncio.sleep(0)
        return

        logger.info("[U+1F9F9] Starting comprehensive test environment cleanup)"

        # Cleanup active WebSocket connections
        for ws_client in self.context.active_websocket_clients:
        try:
        await ws_client.disconnect()
        except Exception as e:
        logger.warning("")

                    # Stop agent threads gracefully
        for thread_id in self.context.active_agent_threads.copy():
                        # Thread cleanup logic here
        pass

                        # Cleanup WebSocket bridge
        try:
        await self.context.websocket_bridge.cleanup()
        except Exception as e:
        logger.warning("")

                                # Release Docker environment
        try:
        env_name = getattr(self.context, 'env_name', 'test_env')
        self.context.docker_manager.release_environment(env_name)
        except Exception as e:
        logger.warning("")

        logger.info(" PASS:  Test environment cleanup complete)"

    async def test_full_agent_execution_flow(self) -> PerformanceMetrics:
        '''
        '''
        Test Scenario 1: Full Agent Execution Flow

        Business Value: Validates complete user journey from request to AI response.
        Validates: Docker services + WebSocket events + real agent execution

        Success Criteria:
        - Docker services remain stable during execution
        - All required WebSocket events are delivered (agent_started, agent_thinking,
        tool_executing, tool_completed, agent_completed)
        - Agent executes successfully and returns meaningful results
        - Response time < 10 seconds for simple tasks
        '''
        '''
        metrics = PerformanceMetrics( )
        test_name="full_agent_execution_flow,"
        start_time=datetime.now(timezone.utc)
                                                

        try:
        logger.info(" TARGET:  Test 1: Full Agent Execution Flow - Starting)"

                                                    # Create WebSocket client for event monitoring
        backend_port = self.context.docker_ports.get('backend', 8000)
        ws_url = ""

        ws_client = RealWebSocketClient(ws_url)
        self.context.active_websocket_clients.append(ws_client)

                                                    # Track WebSocket events received
        events_received = []

    def event_handler(message):
        pass
        if isinstance(message, dict):
        events_received.append(message)
        logger.info("")

        # Connect WebSocket and setup event handling
        connection_start = time.time()
        await ws_client.connect()
        await ws_client.setup_message_handler(event_handler)
        metrics.websocket_connection_time_ms = (time.time() - connection_start) * 1000

        if ws_client.connection_state != ConnectionState.CONNECTED:
        raise RuntimeError("Failed to establish WebSocket connection)"

        logger.info(" PASS:  WebSocket connection established)"

            # Execute agent task - use a simple task for reliable testing
        task_request = { }
        "agent_type": "system_info,"
        "task": "Get current system time and status,"
        "user_id": ","
        "session_id": ""
            

        agent_start = time.time()

            # Submit task through agent service
        result = await self.context.agent_service.execute_agent_task( )
        agent_type=task_request["agent_type],"
        task=task_request["task],"
        user_id=task_request["user_id],"
        session_id=task_request["session_id]"
            

        metrics.agent_execution_time_ms = (time.time() - agent_start) * 1000

            # Wait for WebSocket events to be delivered
        await asyncio.sleep(2.0)  # Allow time for event delivery

            # Validate WebSocket events
        event_types = [event.get('type') for event in events_received]
        required_events = ['agent_started', 'agent_completed']

        missing_events = [item for item in []]
        if missing_events:
        logger.error("")
        metrics.error_count += 1

        metrics.websocket_events_received = len(events_received)
        metrics.websocket_event_delivery_rate = len(events_received) / max(1, len(required_events))

                # Validate agent execution result
        if not result or not result.get('success'):
        logger.error("")
        metrics.error_count += 1
        else:
        logger.info(" PASS:  Agent execution completed successfully)"

                        # Validate response time requirement (< 10 seconds)
        if metrics.agent_execution_time_ms > 10000:
        logger.warning("")

                            # Validate Docker stability
        if hasattr(self.context.docker_manager, 'service_health') and self.context.docker_manager.service_health:
        unhealthy_services = [name for name, health in self.context.docker_manager.service_health.items() )
        if not health.is_healthy]
        if unhealthy_services:
        logger.error("")
        metrics.error_count += 1
        else:
        logger.info(" PASS:  Docker services remained stable during execution)"
        else:
        logger.info(" PASS:  Docker services stability check complete)"

        self.test_results["full_agent_execution_flow] = TestResult.PASS if metrics.error_count == 0 else TestResult.FAIL"

        except Exception as e:
        logger.error("")
        metrics.error_count += 1
        self.test_results["full_agent_execution_flow] = TestResult.ERROR"

        finally:
        metrics.complete()
        self.performance_metrics.append(metrics)
        logger.info("")

        return metrics

    async def test_multi_user_concurrent_execution(self) -> PerformanceMetrics:
        '''
        '''
        Test Scenario 2: Multi-User Concurrent Execution

        Business Value: Validates system can handle multiple users simultaneously.
        Simulates: 5 concurrent users running different agents with thread isolation.

        Success Criteria:
        - All 5 users can execute agents simultaneously
        - Thread isolation maintained (no data leakage between users)
        - WebSocket event routing works correctly per user
        - Docker resource usage remains within acceptable limits
        - 95%+ success rate for concurrent executions
        '''
        '''
        metrics = PerformanceMetrics( )
        test_name="multi_user_concurrent_execution,"
        start_time=datetime.now(timezone.utc)
                                                            

        try:
        logger.info(" TARGET:  Test 2: Multi-User Concurrent Execution - Starting)"

        concurrent_users = 5
        user_tasks = []

                                                                # Create tasks for concurrent users
        for user_idx in range(concurrent_users):
        user_id = ""
        session_id = ""

        task = { }
        "user_id": "user_id,"
        "session_id: session_id,"
        "agent_type": "system_info,"
        "task": ","
        "expected_unique_data": ""
                                                                    
        user_tasks.append(task)
        self.context.active_agent_threads.add("")

                                                                    # Execute all tasks concurrently
    async def execute_user_task(task_info):
        """Execute individual user task and validate isolation."""
        try:
        # Create WebSocket connection per user
        backend_port = self.context.docker_ports.get('backend', 8000)
        ws_url = ""

        user_ws_client = RealWebSocketClient(ws_url)
        await user_ws_client.connect()

        user_events = []
    def user_event_handler(message):
        if isinstance(message, dict):
        user_events.append(message)

        await user_ws_client.setup_message_handler(user_event_handler)

        # Execute agent task
        result = await self.context.agent_service.execute_agent_task( )
        agent_type=task_info["agent_type],"
        task=task_info["task],"
        user_id=task_info["user_id],"
        session_id=task_info["session_id]"
        

        Validate thread isolation - check no data from other users
        other_user_data = [t["expected_unique_data] for t in user_tasks )"
        if t["user_id"] != task_info["user_id]]"

        result_str = str(result)
        isolation_violations = sum(1 for data in other_user_data if data in result_str)

        await user_ws_client.disconnect()

        await asyncio.sleep(0)
        return { }
        "user_id": task_info["user_id],"
        "success: result and result.get('success', False),"
        "events_count: len(user_events),"
        "isolation_violations: isolation_violations,"
        "execution_time: time.time()"
        

        except Exception as e:
        logger.error("")
        return { }
        "user_id": task_info["user_id],"
        "success: False,"
        "error: str(e),"
        "isolation_violations: 0,"
        "execution_time: time.time()"
            

            # Run all user tasks concurrently
        concurrent_start = time.time()

        user_results = await asyncio.gather( )
        *[execute_user_task(task) for task in user_tasks],
        return_exceptions=True
            

        concurrent_duration = time.time() - concurrent_start
        metrics.agent_execution_time_ms = concurrent_duration * 1000

            # Analyze results
        successful_executions = sum(1 for r in user_results )
        if isinstance(r, dict) and r.get('success'))
        total_isolation_violations = sum(r.get('isolation_violations', 0) )
        for r in user_results if isinstance(r, dict))

        success_rate = successful_executions / concurrent_users
        metrics.thread_isolation_violations = total_isolation_violations

        logger.info("")
        logger.info("")
        logger.info("")

            # Validate success criteria
        if success_rate < 0.95:  # 95% success rate requirement
        logger.error("")
        metrics.error_count += 1

        if total_isolation_violations > 0:
        logger.error("")
        metrics.error_count += 1

                # Check if any services became unhealthy
        if hasattr(self.context.docker_manager, 'service_health') and self.context.docker_manager.service_health:
        unhealthy_services = [name for name, health in self.context.docker_manager.service_health.items() )
        if not health.is_healthy]
        if unhealthy_services:
        logger.error("")
        metrics.error_count += 1
        else:
        logger.info(" PASS:  All services remained healthy during concurrent execution)"
        else:
        logger.info(" PASS:  Service health check complete for concurrent execution)"

        self.test_results["multi_user_concurrent_execution] = TestResult.PASS if metrics.error_count == 0 else TestResult.FAIL"

        except Exception as e:
        logger.error("")
        metrics.error_count += 1
        self.test_results["multi_user_concurrent_execution] = TestResult.ERROR"

        finally:
        metrics.complete()
        self.performance_metrics.append(metrics)
        logger.info("")

        return metrics

    async def test_failure_recovery_scenarios(self) -> PerformanceMetrics:
        '''
        '''
        pass
        Test Scenario 3: Failure Recovery Scenarios

        Business Value: Validates system resilience and recovery capabilities.
        Tests: Docker service restarts, WebSocket disconnections, orchestrator failures.

        Success Criteria:
        - System recovers automatically from Docker service restarts
        - WebSocket reconnection works seamlessly
        - Orchestrator failures don"t crash the system"
        - Data consistency maintained during failures
        - Recovery time < 30 seconds for most scenarios
        '''
        '''
        metrics = PerformanceMetrics( )
        test_name="failure_recovery_scenarios,"
        start_time=datetime.now(timezone.utc)
                                                

        try:
        logger.info(" TARGET:  Test 3: Failure Recovery Scenarios - Starting)"

                                                    # Scenario 3.1: Docker service restart during execution
        logger.info(" CYCLE:  Testing Docker service restart recovery)"

                                                    # Start an agent task
        task_user_id = ""
        task_session_id = ""

                                                    # Execute task that should survive service restart
    async def long_running_task():
        pass
        await asyncio.sleep(0)
        return await self.context.agent_service.execute_agent_task( )
        agent_type="system_info,"
        task="Long running system analysis task,"
        user_id=task_user_id,
        session_id=task_session_id
    

    # Start the task
        task_future = asyncio.create_task(long_running_task())
        await asyncio.sleep(1.0)  # Let task start

    # Restart a Docker service (restart backend)
        restart_start = time.time()
        try:
        self.context.docker_manager.restart_service("backend)"
        await asyncio.to_thread(self.context.docker_manager.wait_for_services, timeout=60)
        restart_time = (time.time() - restart_start) * 1000
        metrics.docker_startup_time_ms = restart_time

        logger.info("")

        if restart_time > 30000:  # 30 second threshold
        logger.warning("")

        except Exception as e:
        logger.error("")
        metrics.error_count += 1
        metrics.recovery_attempts += 1

            # Check if task can complete after restart
        try:
        task_result = await asyncio.wait_for(task_future, timeout=30.0)
        if task_result and task_result.get('success'):
        logger.info(" PASS:  Agent task survived Docker service restart)"
        else:
        logger.error(" FAIL:  Agent task failed after Docker service restart)"
        metrics.error_count += 1
        except asyncio.TimeoutError:
        logger.error(" FAIL:  Agent task timed out after Docker service restart)"
        metrics.error_count += 1

                            # Scenario 3.2: WebSocket disconnection recovery
        logger.info(" CYCLE:  Testing WebSocket disconnection recovery)"

        backend_port = self.context.docker_ports.get('backend', 8000)
        ws_url = ""

        recovery_ws_client = RealWebSocketClient(ws_url)
        await recovery_ws_client.connect()

        if recovery_ws_client.connection_state == ConnectionState.CONNECTED:
                                # Simulate disconnection
        await recovery_ws_client.disconnect()
        await asyncio.sleep(1.0)

                                # Test reconnection
        reconnect_start = time.time()
        await recovery_ws_client.connect()
        reconnect_time = (time.time() - reconnect_start) * 1000

        if recovery_ws_client.connection_state == ConnectionState.CONNECTED:
        logger.info("")
        metrics.websocket_connection_time_ms = reconnect_time
        else:
        logger.error(" FAIL:  WebSocket reconnection failed)"
        metrics.error_count += 1

        await recovery_ws_client.disconnect()
        else:
        logger.error(" FAIL:  Initial WebSocket connection failed)"
        metrics.error_count += 1

                                            # Scenario 3.3: WebSocket bridge recovery
        logger.info(" CYCLE:  Testing WebSocket bridge recovery)"

        bridge_recovery_start = time.time()
        try:
                                                # Force bridge re-initialization
        await self.context.websocket_bridge.ensure_integration(force_reinit=True)

        bridge_status = await self.context.websocket_bridge.get_status()
        if bridge_status.get('state') == IntegrationState.ACTIVE.value:
        bridge_recovery_time = (time.time() - bridge_recovery_start) * 1000
        logger.info("")
        metrics.recovery_attempts += 1
        else:
        logger.error(" FAIL:  WebSocket bridge recovery failed)"
        metrics.error_count += 1
        metrics.recovery_attempts += 1

        except Exception as e:
        logger.error("")
        metrics.error_count += 1
        metrics.recovery_attempts += 1

                                                            # Final health validation
        if hasattr(self.context.docker_manager, 'service_health') and self.context.docker_manager.service_health:
        unhealthy_services = [name for name, health in self.context.docker_manager.service_health.items() )
        if not health.is_healthy]

        if unhealthy_services:
        logger.error("")
        metrics.error_count += 1
        else:
        logger.info(" PASS:  All services healthy after recovery tests)"
        else:
        logger.info(" PASS:  Service health validation complete after recovery tests)"

        self.test_results["failure_recovery_scenarios] = TestResult.PASS if metrics.error_count == 0 else TestResult.FAIL"

        except Exception as e:
        logger.error("")
        metrics.error_count += 1
        self.test_results["failure_recovery_scenarios] = TestResult.ERROR"

        finally:
        metrics.complete()
        self.performance_metrics.append(metrics)
        logger.info("")

        return metrics

    async def test_performance_under_load(self) -> PerformanceMetrics:
        '''
        '''
        Test Scenario 4: Performance Under Load

        Business Value: Validates system can handle production-level concurrent load.
        Simulates: 10 agents running simultaneously, 100+ WebSocket events/sec.

        Success Criteria:
        - 10 agents can run simultaneously without failures
        - WebSocket event delivery rate > 95% under load
        - Memory usage remains stable (no significant leaks)
        - CPU usage stays within reasonable limits
        - Average response time < 5 seconds per agent
        - Thread registry handles load without corruption
        '''
        '''
        metrics = PerformanceMetrics( )
        test_name="performance_under_load,"
        start_time=datetime.now(timezone.utc)
                                                                                            

        try:
        logger.info(" TARGET:  Test 4: Performance Under Load - Starting)"

        concurrent_agents = 10
        target_events_per_second = 100
        load_duration_seconds = 30

                                                                                                # Track system resources before load test
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        initial_cpu = process.cpu_percent()

        logger.info("")

                                                                                                # Create load test tasks
        load_tasks = []
        all_websocket_events = []

    async def load_test_agent(agent_idx: int):
        """Individual load test agent execution."""
        agent_user_id = ""
        agent_session_id = ""

    # Create WebSocket client for this agent
        backend_port = self.context.docker_ports.get('backend', 8000)
        ws_url = ""

        agent_ws_client = RealWebSocketClient(ws_url)
        agent_events = []

        try:
        await agent_ws_client.connect()

    def agent_event_handler(message):
        if isinstance(message, dict):
        agent_events.append({ })
        'agent_idx': agent_idx,
        'timestamp': time.time(),
        'event': message
        

        await agent_ws_client.setup_message_handler(agent_event_handler)

        # Execute multiple tasks per agent to generate load
        tasks_per_agent = 3
        agent_results = []

        for task_idx in range(tasks_per_agent):
        task_start = time.time()

        result = await self.context.agent_service.execute_agent_task( )
        agent_type="system_info,"
        task="",
        user_id=agent_user_id,
        session_id=""
            

        task_duration = (time.time() - task_start) * 1000
        agent_results.append({ })
        'success': result and result.get('success', False),
        'duration_ms': task_duration
            

            # Small delay to allow event processing
        await asyncio.sleep(0.1)

        await agent_ws_client.disconnect()

        await asyncio.sleep(0)
        return { }
        'agent_idx': agent_idx,
        'results': agent_results,
        'events': agent_events,
        'total_events': len(agent_events)
            

        except Exception as e:
        logger.error("")
        try:
        await agent_ws_client.disconnect()
        except:
        pass
        return { }
        'agent_idx': agent_idx,
        'error': str(e),
        'events': agent_events,
        'total_events': len(agent_events)
                        

                        # Execute load test
        logger.info("")
        load_start = time.time()

                        # Run all agents concurrently
        agent_results = await asyncio.gather( )
        *[load_test_agent(i) for i in range(concurrent_agents)],
        return_exceptions=True
                        

        load_duration = time.time() - load_start
        metrics.agent_execution_time_ms = load_duration * 1000

                        # Analyze results
        successful_agents = 0
        total_events = 0
        total_tasks = 0
        successful_tasks = 0
        response_times = []

        for result in agent_results:
        if isinstance(result, dict) and 'results' in result:
        agent_tasks = result['results']
        agent_success = all(task.get('success', False) for task in agent_tasks)

        if agent_success:
        successful_agents += 1

        total_tasks += len(agent_tasks)
        successful_tasks += sum(1 for task in agent_tasks if task.get('success', False))

                                    # Collect response times
        for task in agent_tasks:
        if 'duration_ms' in task:
        response_times.append(task['duration_ms'])

        total_events += result.get('total_events', 0)

                                            # Collect all events for rate calculation
        all_websocket_events.extend(result.get('events', []))

                                            # Calculate metrics
        agent_success_rate = successful_agents / concurrent_agents
        task_success_rate = successful_tasks / max(1, total_tasks)
        avg_response_time = statistics.mean(response_times) if response_times else 0

                                            # Calculate WebSocket event delivery rate
        expected_events = concurrent_agents * 3 * 5  # agents * tasks * approx events per task
        event_delivery_rate = total_events / max(1, expected_events)

        metrics.websocket_events_received = total_events
        metrics.websocket_event_delivery_rate = event_delivery_rate
        metrics.agent_response_time_ms = avg_response_time

                                            # Check system resources after load test
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        final_cpu = process.cpu_percent()
        memory_increase = final_memory - initial_memory

        metrics.container_memory_usage_mb = final_memory
        metrics.container_cpu_usage_percent = final_cpu

                                            # Log performance results
        logger.info(f" CHART:  Load Test Results:)"
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")
        logger.info("")

                                            # Validate success criteria
        if agent_success_rate < 0.90:  # 90% agent success rate
        logger.error("")
        metrics.error_count += 1

        if event_delivery_rate < 0.95:  # 95% event delivery rate
        logger.error("")
        metrics.error_count += 1

        if avg_response_time > 5000:  # 5 second response time threshold
        logger.error("")
        metrics.error_count += 1

        if memory_increase > 100:  # "100MB" memory leak threshold
        logger.warning("")
        metrics.memory_leaks_detected = 1

                                            # Final system health check
        if hasattr(self.context.docker_manager, 'service_health') and self.context.docker_manager.service_health:
        unhealthy_services = [name for name, health in self.context.docker_manager.service_health.items() )
        if not health.is_healthy]

        if unhealthy_services:
        logger.error("")
        metrics.error_count += 1
        else:
        logger.info(" PASS:  All services remained healthy during load test)"
        else:
        logger.info(" PASS:  Final system health check complete for load test)"

        self.test_results["performance_under_load] = TestResult.PASS if metrics.error_count == 0 else TestResult.FAIL"

        except Exception as e:
        logger.error("")
        metrics.error_count += 1
        self.test_results["performance_under_load] = TestResult.ERROR"

        finally:
        metrics.complete()
        self.performance_metrics.append(metrics)
        logger.info("")

        return metrics

    def generate_performance_report(self) -> Dict[str, Any]:
        '''
        '''
        pass
        Generate comprehensive performance metrics report.

        Business Value: Provides actionable insights for system optimization.
        '''
        '''
        if not self.performance_metrics:
        return {"error": "No performance metrics collected}"

        report = { }
        "test_execution_summary: { }"
        "total_tests: len(self.performance_metrics),"
        "passed_tests: sum(1 for r in self.test_results.values() if r == TestResult.PASS),"
        "failed_tests: sum(1 for r in self.test_results.values() if r == TestResult.FAIL),"
        "error_tests: sum(1 for r in self.test_results.values() if r == TestResult.ERROR),"
        "total_duration_seconds: sum(m.duration_seconds for m in self.performance_metrics)"
        },
        "individual_test_results: {m.test_name: self.test_results.get(m.test_name, TestResult.ERROR) )"
        for m in self.performance_metrics},
        "performance_metrics: { }"
        "docker_metrics: { }"
        "avg_startup_time_ms: statistics.mean([item for item in []]) if any(m.docker_startup_time_ms > 0 for m in self.performance_metrics) else 0,"
        "max_memory_usage_mb: max([item for item in []], default=0),"
        "avg_cpu_usage_percent: statistics.mean([item for item in []]) if any(m.container_cpu_usage_percent > 0 for m in self.performance_metrics) else 0"
        },
        "websocket_metrics: { }"
        "avg_connection_time_ms: statistics.mean([item for item in []]) if any(m.websocket_connection_time_ms > 0 for m in self.performance_metrics) else 0,"
        "total_events_received: sum(m.websocket_events_received for m in self.performance_metrics),"
        "avg_event_delivery_rate: statistics.mean([item for item in []]) if any(m.websocket_event_delivery_rate > 0 for m in self.performance_metrics) else 0"
        },
        "agent_metrics: { }"
        "avg_execution_time_ms: statistics.mean([item for item in []]) if any(m.agent_execution_time_ms > 0 for m in self.performance_metrics) else 0,"
        "avg_response_time_ms: statistics.mean([item for item in []]) if any(m.agent_response_time_ms > 0 for m in self.performance_metrics) else 0,"
        "total_tools_executed: sum(m.tools_executed for m in self.performance_metrics)"
        },
        "system_metrics: { }"
        "total_thread_isolation_violations: sum(m.thread_isolation_violations for m in self.performance_metrics),"
        "total_memory_leaks_detected: sum(m.memory_leaks_detected for m in self.performance_metrics),"
        "total_errors: sum(m.error_count for m in self.performance_metrics),"
        "total_recovery_attempts: sum(m.recovery_attempts for m in self.performance_metrics)"
        
        },
        "business_value_validation: { }"
        "chat_functionality_validated": self.test_results.get("full_agent_execution_flow) == TestResult.PASS,"
        "concurrent_user_support_validated": self.test_results.get("multi_user_concurrent_execution) == TestResult.PASS,"
        "system_resilience_validated": self.test_results.get("failure_recovery_scenarios) == TestResult.PASS,"
        "production_load_readiness": self.test_results.get("performance_under_load) == TestResult.PASS,"
        "overall_system_health: all(result == TestResult.PASS for result in self.test_results.values())"
        },
        "recommendations: self._generate_recommendations()"
        

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

    # Check for performance issues
        avg_response_time = statistics.mean([m.agent_response_time_ms for m in self.performance_metrics ))
        if m.agent_response_time_ms > 0]) if any(m.agent_response_time_ms > 0 for m in self.performance_metrics) else 0

        if avg_response_time > 3000:  # 3 second threshold
        recommendations.append("")

    # Check for WebSocket delivery issues
        avg_delivery_rate = statistics.mean([m.websocket_event_delivery_rate for m in self.performance_metrics ))
        if m.websocket_event_delivery_rate > 0]) if any(m.websocket_event_delivery_rate > 0 for m in self.performance_metrics) else 0

        if avg_delivery_rate < 0.98:  # 98% threshold
        recommendations.append("")

    # Check for memory leaks
        total_memory_leaks = sum(m.memory_leaks_detected for m in self.performance_metrics)
        if total_memory_leaks > 0:
        recommendations.append("Memory leak indicators detected - perform detailed memory profiling)"

        # Check for thread isolation violations
        total_violations = sum(m.thread_isolation_violations for m in self.performance_metrics)
        if total_violations > 0:
        recommendations.append("")

            # Check for failed tests
        failed_tests = [item for item in []]
        if failed_tests:
        recommendations.append("")

        if not recommendations:
        recommendations.append("All tests passed successfully - system is ready for production deployment)"

        return recommendations


@pytest.mark.asyncio
@pytest.mark.e2e
class TestDockerWebSocketIntegration:
    '''
    '''
    Pytest wrapper for comprehensive Docker-WebSocket integration tests.

    Business Value: Validates complete system integration supporting chat business value.
    '''
    '''

    async def test_comprehensive_integration_suite(self):
    '''
    '''
    Execute complete integration test suite validating Docker and WebSocket systems.

    This test is marked as mission-critical and must pass for deployment approval.
    '''
    '''
    pass
    integration_tests = DockerWebSocketIntegrationTests()

    try:
            # Setup test environment
    await integration_tests.setup_test_environment()

            # Execute all test scenarios
    test_results = []

            # Test 1: Full Agent Execution Flow
    result1 = await integration_tests.test_full_agent_execution_flow()
    test_results.append(result1)

            # Test 2: Multi-User Concurrent Execution
    result2 = await integration_tests.test_multi_user_concurrent_execution()
    test_results.append(result2)

            # Test 3: Failure Recovery Scenarios
    result3 = await integration_tests.test_failure_recovery_scenarios()
    test_results.append(result3)

            # Test 4: Performance Under Load
    result4 = await integration_tests.test_performance_under_load()
    test_results.append(result4)

            # Generate comprehensive report
    report = integration_tests.generate_performance_report()

            # Log final results
    logger.info("= * 80)"
    logger.info(" TARGET:  DOCKER-WEBSOCKET INTEGRATION TEST RESULTS)"
    logger.info("= * 80)"

    for test_name, result in integration_tests.test_results.items():
    status_emoji = " PASS: " if result == TestResult.PASS else " FAIL: "
    logger.info("")

    logger.info("")
    logger.info("")
    logger.info("")

                # Recommendations
    logger.info(" )"
    SEARCH:  RECOMMENDATIONS:")"
    for rec in report['recommendations']:
    logger.info("")

    logger.info("= * 80)"

                    # Assert all tests passed for pytest
    all_passed = all(result == TestResult.PASS for result in integration_tests.test_results.values())

    if not all_passed:
    failed_tests = [name for name, result in integration_tests.test_results.items() )
    if result != TestResult.PASS]
    pytest.fail("")

    await asyncio.sleep(0)
    return report

    finally:
                            # Always cleanup test environment
    await integration_tests.cleanup_test_environment()


    if __name__ == "__main__:"
    '''
    '''
    Direct execution support for integration testing.

    Usage:
    python tests/e2e/test_docker_websocket_integration.py
    '''
    '''
    async def main():
        """Main execution function for direct running."""
        integration_tests = DockerWebSocketIntegrationTests()

        try:
        print("[U+1F680] Starting Docker-WebSocket Integration Test Suite)"
        print("= * 60)"

        # Setup and run tests
        await integration_tests.setup_test_environment()

        # Execute all tests
        await integration_tests.test_full_agent_execution_flow()
        await integration_tests.test_multi_user_concurrent_execution()
        await integration_tests.test_failure_recovery_scenarios()
        await integration_tests.test_performance_under_load()

        # Generate and display report
        report = integration_tests.generate_performance_report()

        print("")
         + =" * 60)"
        print(" TARGET:  FINAL TEST RESULTS)"
        print("= * 60)"

        for test_name, result in integration_tests.test_results.items():
        status = "PASS  PASS: " if result == TestResult.PASS else ""
        print("")

        print("")

        if report['recommendations']:
        print("")
        SEARCH:  Recommendations:")"
        for rec in report['recommendations']:
        print("")

        except Exception as e:
        print("")
        raise
        finally:
        await integration_tests.cleanup_test_environment()

                            # Run the integration tests
        asyncio.run(main())
        pass
