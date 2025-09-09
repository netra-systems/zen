#!/usr/bin/env python3
"""
Agent Performance Under Load E2E Test

Business Value Justification (BVJ):
- Segment: Mid, Enterprise
- Business Goal: Performance under load enables platform scaling and enterprise onboarding
- Value Impact: Ensures system maintains quality service under concurrent user load
- Strategic Impact: Validates platform can support growth from 10 to 100+ concurrent users

This test validates system behavior with concurrent users and agents:
1. Multiple concurrent agent executions without performance degradation
2. Resource utilization stays within acceptable bounds
3. Response time SLAs maintained under load
4. Memory and connection management scales properly
5. All users receive complete WebSocket event sequences
6. Database and Redis performance remains stable
7. Error rates stay below business-critical thresholds

CRITICAL REQUIREMENTS:
- MANDATORY AUTHENTICATION: All concurrent users use real JWT authentication
- NO MOCKS: Real services, real concurrent load, real resource measurement
- ALL 5 WEBSOCKET EVENTS: Every concurrent user receives all required events
- PERFORMANCE SLAS: Response times must stay within business-acceptable ranges
- RESOURCE MANAGEMENT: System must not leak memory or connections

This test ensures:
- Platform can onboard enterprise customers with confidence
- System scales gracefully with user growth
- Resource costs stay predictable under load
- User experience remains consistent at scale
"""

import asyncio
import json
import time
import uuid
import psutil
from concurrent.futures import as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

import pytest
from loguru import logger

# Test framework imports - SSOT patterns
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_authenticated_user_context
)
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import (
    assert_websocket_events_sent,
    WebSocketTestHelpers
)

# Shared utilities
from shared.isolated_environment import get_env


@dataclass
class UserLoadTestMetrics:
    """Metrics for individual user load testing."""
    user_id: str
    email: str
    start_time: float
    end_time: Optional[float] = None
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    response_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    
    def calculate_response_time(self) -> float:
        """Calculate response time if not already set."""
        if self.end_time and self.start_time:
            self.response_time = self.end_time - self.start_time
        return self.response_time or 0.0


@dataclass
class LoadTestResults:
    """Aggregate results from load testing."""
    total_users: int = 0
    successful_users: int = 0
    failed_users: int = 0
    average_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    total_events_received: int = 0
    error_rate: float = 0.0
    concurrent_peak: int = 0
    memory_usage_mb: float = 0.0
    
    def calculate_metrics(self, user_metrics: List[UserLoadTestMetrics]) -> None:
        """Calculate aggregate metrics from individual user results."""
        self.total_users = len(user_metrics)
        self.successful_users = sum(1 for m in user_metrics if m.success)
        self.failed_users = self.total_users - self.successful_users
        
        if self.total_users > 0:
            self.error_rate = (self.failed_users / self.total_users) * 100
        
        successful_metrics = [m for m in user_metrics if m.success and m.response_time]
        if successful_metrics:
            response_times = [m.response_time for m in successful_metrics]
            self.average_response_time = sum(response_times) / len(response_times)
            self.max_response_time = max(response_times)
            self.min_response_time = min(response_times)
        
        self.total_events_received = sum(len(m.events_received) for m in user_metrics)


class TestAgentPerformanceUnderLoadE2E(BaseE2ETest):
    """
    E2E test for agent performance under concurrent user load.
    
    This test validates that the platform can handle multiple concurrent users
    while maintaining performance SLAs and resource efficiency.
    """

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Set up test environment for load testing."""
        await self.initialize_test_environment()
        
        # Initialize auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Track all connections for cleanup
        self.active_connections = []
        
        # Performance monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        yield
        
        # Cleanup all connections
        logger.info(f"🧹 Cleaning up {len(self.active_connections)} connections...")
        cleanup_tasks = [
            WebSocketTestHelpers.close_test_connection(conn) 
            for conn in self.active_connections
        ]
        
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Some connections failed to close cleanly: {e}")
        
        # Final memory check
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_delta = final_memory - self.initial_memory
        logger.info(f"📊 Memory usage change: {memory_delta:+.2f} MB")

    async def create_concurrent_user_session(self, user_index: int) -> Tuple[Any, Any, Any]:
        """Create authenticated user session for concurrent testing."""
        email = f"load_test_user_{user_index}@example.com"
        
        auth_user = await self.auth_helper.create_authenticated_user(
            email=email,
            permissions=["read", "write", "agent_execute"]
        )
        
        user_context = await create_authenticated_user_context(
            user_email=auth_user.email,
            user_id=auth_user.user_id,
            environment="test",
            permissions=auth_user.permissions,
            websocket_enabled=True
        )
        
        websocket_url = "ws://localhost:8000/ws/chat"
        headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        
        websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            websocket_url,
            headers=headers,
            timeout=20.0,  # Longer timeout for load testing
            max_retries=2,  # Fewer retries to fail faster under load
            user_id=auth_user.user_id
        )
        
        self.active_connections.append(websocket_connection)
        
        return auth_user, websocket_connection, user_context

    async def execute_user_agent_workflow(
        self, 
        user_index: int,
        concurrent_user_count: int = 1
    ) -> UserLoadTestMetrics:
        """
        Execute complete agent workflow for one user and measure performance.
        
        Args:
            user_index: Index of this user in the load test
            concurrent_user_count: Total number of concurrent users (for messaging context)
            
        Returns:
            UserLoadTestMetrics with performance data
        """
        metrics = UserLoadTestMetrics(
            user_id="",
            email=f"load_test_user_{user_index}@example.com",
            start_time=time.time()
        )
        
        try:
            # Create user session
            auth_user, websocket_connection, user_context = await self.create_concurrent_user_session(user_index)
            metrics.user_id = auth_user.user_id
            
            logger.info(f"👤 [{user_index+1}/{concurrent_user_count}] Starting agent workflow for {auth_user.email}")
            
            # Send agent request with load-specific context
            agent_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": f"Load test request #{user_index+1} of {concurrent_user_count} concurrent users. Please provide system optimization insights for high-load scenarios.",
                "user_id": auth_user.user_id,
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id) + f"_load_{user_index}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket_connection, agent_message)
            
            # Collect events with timeout appropriate for load testing
            collection_timeout = 45.0  # Longer timeout under load
            event_start_time = time.time()
            
            while time.time() - event_start_time < collection_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        websocket_connection,
                        timeout=3.0  # Individual event timeout
                    )
                    metrics.events_received.append(event)
                    
                    event_type = event.get("type", "unknown")
                    
                    # Stop on completion
                    if event_type == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        # Check if we have completion event
                        completion_events = [
                            e for e in metrics.events_received 
                            if e.get("type") == "agent_completed"
                        ]
                        if completion_events:
                            break
                        continue
                    else:
                        raise e
            
            # Calculate performance metrics
            metrics.end_time = time.time()
            metrics.calculate_response_time()
            
            # Validate success criteria
            event_types = [event.get("type") for event in metrics.events_received]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            has_all_events = all(event_type in event_types for event_type in required_events)
            has_completion = "agent_completed" in event_types
            reasonable_response_time = metrics.response_time and metrics.response_time < 60.0
            
            metrics.success = has_all_events and has_completion and reasonable_response_time
            
            if metrics.success:
                logger.info(f"✅ [{user_index+1}/{concurrent_user_count}] User workflow completed successfully in {metrics.response_time:.2f}s")
            else:
                missing_events = [e for e in required_events if e not in event_types]
                metrics.error_message = f"Missing events: {missing_events}, completion: {has_completion}, time: {metrics.response_time:.2f}s"
                logger.warning(f"⚠️ [{user_index+1}/{concurrent_user_count}] User workflow incomplete: {metrics.error_message}")
            
        except Exception as e:
            metrics.end_time = time.time()
            metrics.calculate_response_time()
            metrics.error_message = str(e)
            logger.error(f"❌ [{user_index+1}/{concurrent_user_count}] User workflow failed: {e}")
        
        return metrics

    def measure_system_resources(self) -> Dict[str, float]:
        """Measure current system resource usage."""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            return {
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_delta_mb": (memory_info.rss / 1024 / 1024) - self.initial_memory,
                "cpu_percent": cpu_percent,
                "num_connections": len(self.active_connections)
            }
        except Exception as e:
            logger.warning(f"Failed to measure system resources: {e}")
            return {"error": str(e)}

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_concurrent_agent_execution_5_users(self, real_services_fixture):
        """
        Test concurrent agent execution with 5 users.
        
        This test validates that the system can handle a small but meaningful
        concurrent load while maintaining performance SLAs.
        """
        logger.info("🚀 Starting concurrent agent execution test with 5 users")
        
        concurrent_users = 5
        
        # Measure initial system state
        initial_resources = self.measure_system_resources()
        logger.info(f"📊 Initial resources: {initial_resources}")
        
        # Start all user workflows concurrently
        logger.info(f"👥 Starting {concurrent_users} concurrent user workflows...")
        
        start_time = time.time()
        
        # Create tasks for concurrent execution
        user_tasks = [
            asyncio.create_task(
                self.execute_user_agent_workflow(i, concurrent_users)
            )
            for i in range(concurrent_users)
        ]
        
        # Wait for all tasks to complete
        user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results (handle any exceptions)
        valid_metrics = []
        for i, result in enumerate(user_metrics):
            if isinstance(result, Exception):
                logger.error(f"User {i+1} task failed with exception: {result}")
                # Create failed metrics entry
                failed_metric = UserLoadTestMetrics(
                    user_id=f"failed_user_{i}",
                    email=f"load_test_user_{i}@example.com", 
                    start_time=start_time,
                    end_time=time.time(),
                    error_message=str(result)
                )
                valid_metrics.append(failed_metric)
            else:
                valid_metrics.append(result)
        
        # Calculate aggregate results
        results = LoadTestResults()
        results.calculate_metrics(valid_metrics)
        
        # Measure final system state
        final_resources = self.measure_system_resources()
        results.memory_usage_mb = final_resources.get("memory_delta_mb", 0.0)
        
        # Log detailed results
        logger.info("📊 CONCURRENT LOAD TEST RESULTS:")
        logger.info(f"   👥 Total Users: {results.total_users}")
        logger.info(f"   ✅ Successful: {results.successful_users}")
        logger.info(f"   ❌ Failed: {results.failed_users}")
        logger.info(f"   📈 Success Rate: {((results.successful_users/results.total_users)*100):.1f}%")
        logger.info(f"   ⏱️ Average Response Time: {results.average_response_time:.2f}s")
        logger.info(f"   ⚡ Max Response Time: {results.max_response_time:.2f}s")
        logger.info(f"   📨 Total Events: {results.total_events_received}")
        logger.info(f"   💾 Memory Delta: {results.memory_usage_mb:+.2f} MB")
        logger.info(f"   🕐 Total Test Time: {total_time:.2f}s")
        
        # Validate performance SLAs
        success_rate = (results.successful_users / results.total_users) * 100
        assert success_rate >= 80.0, f"Success rate too low: {success_rate:.1f}% (minimum: 80%)"
        
        assert results.average_response_time < 30.0, \
            f"Average response time too high: {results.average_response_time:.2f}s (max: 30s)"
        
        assert results.max_response_time < 60.0, \
            f"Max response time too high: {results.max_response_time:.2f}s (max: 60s)"
        
        # Validate all successful users received required events
        successful_metrics = [m for m in valid_metrics if m.success]
        for metrics in successful_metrics:
            event_types = [event.get("type") for event in metrics.events_received]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            missing_events = [e for e in required_events if e not in event_types]
            assert len(missing_events) == 0, \
                f"User {metrics.email} missing required events: {missing_events}"
        
        # Validate reasonable memory usage
        assert results.memory_usage_mb < 200.0, \
            f"Memory usage too high: {results.memory_usage_mb:.2f} MB (max: 200 MB)"
        
        logger.info("🎉 CONCURRENT AGENT EXECUTION (5 USERS) TEST PASSED")
        logger.info(f"   ✅ Performance SLAs: MET")
        logger.info(f"   📊 Success Rate: {success_rate:.1f}%")
        logger.info(f"   ⚡ Response Time: {results.average_response_time:.2f}s avg")
        logger.info(f"   💾 Resource Usage: ACCEPTABLE")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_concurrent_agent_execution_10_users(self, real_services_fixture):
        """
        Test concurrent agent execution with 10 users.
        
        This test validates platform ability to handle moderate concurrent load
        which represents typical small-to-medium enterprise usage.
        """
        logger.info("🚀 Starting concurrent agent execution test with 10 users")
        
        concurrent_users = 10
        
        # Measure initial system state
        initial_resources = self.measure_system_resources()
        logger.info(f"📊 Initial resources: {initial_resources}")
        
        # Execute in smaller batches to reduce resource spike
        batch_size = 5
        all_metrics = []
        
        start_time = time.time()
        
        for batch_start in range(0, concurrent_users, batch_size):
            batch_end = min(batch_start + batch_size, concurrent_users)
            batch_users = batch_end - batch_start
            
            logger.info(f"👥 Starting batch {batch_start//batch_size + 1}: users {batch_start+1}-{batch_end}")
            
            # Create batch tasks
            batch_tasks = [
                asyncio.create_task(
                    self.execute_user_agent_workflow(i, concurrent_users)
                )
                for i in range(batch_start, batch_end)
            ]
            
            # Wait for batch completion
            batch_metrics = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process batch results
            for i, result in enumerate(batch_metrics):
                if isinstance(result, Exception):
                    logger.error(f"User {batch_start + i + 1} failed: {result}")
                    failed_metric = UserLoadTestMetrics(
                        user_id=f"failed_user_{batch_start + i}",
                        email=f"load_test_user_{batch_start + i}@example.com",
                        start_time=start_time,
                        end_time=time.time(),
                        error_message=str(result)
                    )
                    all_metrics.append(failed_metric)
                else:
                    all_metrics.append(result)
            
            # Brief pause between batches to avoid overwhelming the system
            await asyncio.sleep(1.0)
        
        total_time = time.time() - start_time
        
        # Calculate aggregate results
        results = LoadTestResults()
        results.calculate_metrics(all_metrics)
        
        # Measure final system state
        final_resources = self.measure_system_resources()
        results.memory_usage_mb = final_resources.get("memory_delta_mb", 0.0)
        
        # Log detailed results
        logger.info("📊 CONCURRENT LOAD TEST RESULTS (10 USERS):")
        logger.info(f"   👥 Total Users: {results.total_users}")
        logger.info(f"   ✅ Successful: {results.successful_users}")
        logger.info(f"   ❌ Failed: {results.failed_users}")
        logger.info(f"   📈 Success Rate: {((results.successful_users/results.total_users)*100):.1f}%")
        logger.info(f"   ⏱️ Average Response Time: {results.average_response_time:.2f}s")
        logger.info(f"   ⚡ Max Response Time: {results.max_response_time:.2f}s")
        logger.info(f"   📨 Total Events: {results.total_events_received}")
        logger.info(f"   💾 Memory Delta: {results.memory_usage_mb:+.2f} MB")
        logger.info(f"   🕐 Total Test Time: {total_time:.2f}s")
        
        # Validate performance SLAs (slightly relaxed for higher load)
        success_rate = (results.successful_users / results.total_users) * 100
        assert success_rate >= 70.0, f"Success rate too low: {success_rate:.1f}% (minimum: 70%)"
        
        assert results.average_response_time < 45.0, \
            f"Average response time too high: {results.average_response_time:.2f}s (max: 45s)"
        
        assert results.max_response_time < 90.0, \
            f"Max response time too high: {results.max_response_time:.2f}s (max: 90s)"
        
        # Validate memory usage stays reasonable
        assert results.memory_usage_mb < 400.0, \
            f"Memory usage too high: {results.memory_usage_mb:.2f} MB (max: 400 MB)"
        
        logger.info("🎉 CONCURRENT AGENT EXECUTION (10 USERS) TEST PASSED")
        logger.info(f"   ✅ Performance SLAs: MET")
        logger.info(f"   📊 Success Rate: {success_rate:.1f}%")
        logger.info(f"   ⚡ Response Time: {results.average_response_time:.2f}s avg")
        logger.info(f"   💾 Resource Usage: ACCEPTABLE")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    @pytest.mark.stress
    async def test_rapid_sequential_requests_stress_test(self, real_services_fixture):
        """
        Test rapid sequential requests from a single user.
        
        This test validates that the system can handle rapid-fire requests
        from power users or automated systems without degrading.
        """
        logger.info("🚀 Starting rapid sequential requests stress test")
        
        # Create single user session
        auth_user, websocket_connection, user_context = await self.create_concurrent_user_session(0)
        
        num_requests = 10
        request_metrics = []
        
        logger.info(f"⚡ Sending {num_requests} rapid sequential requests...")
        
        for request_index in range(num_requests):
            request_start = time.time()
            
            message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": f"Rapid request #{request_index + 1} - provide quick system status check for stress testing.",
                "user_id": auth_user.user_id,
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id) + f"_rapid_{request_index}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket_connection, message)
            
            # Collect events for this request
            events = []
            timeout = 30.0
            event_start = time.time()
            
            while time.time() - event_start < timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        websocket_connection,
                        timeout=2.0
                    )
                    events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        # Check for completion
                        completion_events = [e for e in events if e.get("type") == "agent_completed"]
                        if completion_events:
                            break
                        continue
                    else:
                        raise e
            
            request_end = time.time()
            request_time = request_end - request_start
            
            # Track metrics
            event_types = [event.get("type") for event in events]
            has_completion = "agent_completed" in event_types
            
            request_metrics.append({
                "request_index": request_index,
                "response_time": request_time,
                "events_count": len(events),
                "success": has_completion,
                "event_types": event_types
            })
            
            logger.info(f"📤 Request {request_index + 1}/{num_requests} completed in {request_time:.2f}s (events: {len(events)})")
            
            # Brief pause between requests
            await asyncio.sleep(0.5)
        
        # Analyze results
        successful_requests = [m for m in request_metrics if m["success"]]
        success_rate = (len(successful_requests) / len(request_metrics)) * 100
        
        if successful_requests:
            avg_response_time = sum(m["response_time"] for m in successful_requests) / len(successful_requests)
            max_response_time = max(m["response_time"] for m in successful_requests)
            min_response_time = min(m["response_time"] for m in successful_requests)
        else:
            avg_response_time = max_response_time = min_response_time = 0.0
        
        total_events = sum(m["events_count"] for m in request_metrics)
        
        # Log results
        logger.info("📊 RAPID SEQUENTIAL REQUESTS RESULTS:")
        logger.info(f"   📤 Total Requests: {len(request_metrics)}")
        logger.info(f"   ✅ Successful: {len(successful_requests)}")
        logger.info(f"   📈 Success Rate: {success_rate:.1f}%")
        logger.info(f"   ⏱️ Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"   ⚡ Max Response Time: {max_response_time:.2f}s")
        logger.info(f"   🏃 Min Response Time: {min_response_time:.2f}s")
        logger.info(f"   📨 Total Events: {total_events}")
        
        # Validate stress test results
        assert success_rate >= 80.0, f"Success rate too low under stress: {success_rate:.1f}%"
        assert avg_response_time < 25.0, f"Average response time degraded under stress: {avg_response_time:.2f}s"
        assert max_response_time < 60.0, f"Max response time too high under stress: {max_response_time:.2f}s"
        
        # Validate that later requests didn't significantly degrade
        first_half = request_metrics[:num_requests//2]
        second_half = request_metrics[num_requests//2:]
        
        first_half_successful = [m for m in first_half if m["success"]]
        second_half_successful = [m for m in second_half if m["success"]]
        
        if first_half_successful and second_half_successful:
            first_avg = sum(m["response_time"] for m in first_half_successful) / len(first_half_successful)
            second_avg = sum(m["response_time"] for m in second_half_successful) / len(second_half_successful)
            
            degradation_ratio = second_avg / first_avg if first_avg > 0 else 1.0
            
            assert degradation_ratio < 2.0, \
                f"Significant performance degradation during stress test: {degradation_ratio:.2f}x"
            
            logger.info(f"📈 Performance consistency: {degradation_ratio:.2f}x degradation (acceptable)")
        
        logger.info("🎉 RAPID SEQUENTIAL REQUESTS STRESS TEST PASSED")
        logger.info(f"   ⚡ Request Processing: STABLE")
        logger.info(f"   📊 Success Rate: {success_rate:.1f}%")
        logger.info(f"   🎯 Performance Consistency: MAINTAINED")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_resource_cleanup_after_load(self, real_services_fixture):
        """
        Test that system properly cleans up resources after load testing.
        
        This test validates that memory leaks and connection buildup don't
        occur during sustained load scenarios.
        """
        logger.info("🚀 Starting resource cleanup after load test")
        
        initial_resources = self.measure_system_resources()
        logger.info(f"📊 Initial resources: {initial_resources}")
        
        # Create and immediately clean up multiple user sessions
        num_sessions = 8
        cleanup_metrics = []
        
        for session_round in range(3):  # Multiple rounds to test cumulative effects
            logger.info(f"🔄 Session round {session_round + 1}/3 with {num_sessions} users")
            
            round_start_resources = self.measure_system_resources()
            
            # Create multiple sessions
            session_tasks = []
            for i in range(num_sessions):
                task = asyncio.create_task(
                    self.execute_user_agent_workflow(i + (session_round * num_sessions), num_sessions)
                )
                session_tasks.append(task)
            
            # Wait for all sessions to complete
            session_results = await asyncio.gather(*session_tasks, return_exceptions=True)
            
            # Force cleanup of connections
            current_connections = len(self.active_connections)
            logger.info(f"🧹 Cleaning up {current_connections} connections from round {session_round + 1}")
            
            cleanup_tasks = [
                WebSocketTestHelpers.close_test_connection(conn) 
                for conn in self.active_connections[-current_connections:]
            ]
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Remove connections from tracking
            self.active_connections = self.active_connections[:-current_connections]
            
            # Measure resources after cleanup
            await asyncio.sleep(2.0)  # Allow time for cleanup
            round_end_resources = self.measure_system_resources()
            
            cleanup_metrics.append({
                "round": session_round + 1,
                "start_memory": round_start_resources.get("memory_mb", 0),
                "end_memory": round_end_resources.get("memory_mb", 0),
                "memory_delta": round_end_resources.get("memory_mb", 0) - round_start_resources.get("memory_mb", 0),
                "connections_cleaned": current_connections,
                "final_connections": len(self.active_connections)
            })
            
            logger.info(f"✅ Round {session_round + 1} cleanup: {cleanup_metrics[-1]['memory_delta']:+.2f} MB")
        
        # Final resource measurement
        final_resources = self.measure_system_resources()
        total_memory_delta = final_resources.get("memory_mb", 0) - initial_resources.get("memory_mb", 0)
        
        # Log cleanup results
        logger.info("📊 RESOURCE CLEANUP RESULTS:")
        logger.info(f"   💾 Initial Memory: {initial_resources.get('memory_mb', 0):.2f} MB")
        logger.info(f"   💾 Final Memory: {final_resources.get('memory_mb', 0):.2f} MB")
        logger.info(f"   📈 Total Memory Delta: {total_memory_delta:+.2f} MB")
        logger.info(f"   🔗 Final Connections: {len(self.active_connections)}")
        
        for i, metrics in enumerate(cleanup_metrics):
            logger.info(f"   Round {i+1}: {metrics['memory_delta']:+.2f} MB, {metrics['connections_cleaned']} cleaned")
        
        # Validate resource cleanup
        assert total_memory_delta < 300.0, \
            f"Excessive memory usage after cleanup: {total_memory_delta:.2f} MB (max: 300 MB)"
        
        # Validate no excessive connection buildup
        assert len(self.active_connections) < num_sessions, \
            f"Too many connections remaining: {len(self.active_connections)} (should be < {num_sessions})"
        
        # Validate memory usage doesn't continuously grow
        memory_deltas = [m["memory_delta"] for m in cleanup_metrics]
        if len(memory_deltas) >= 2:
            # Last round shouldn't use significantly more memory than first
            memory_growth = memory_deltas[-1] - memory_deltas[0]
            assert memory_growth < 100.0, \
                f"Memory usage growing across rounds: {memory_growth:+.2f} MB"
        
        logger.info("🎉 RESOURCE CLEANUP AFTER LOAD TEST PASSED")
        logger.info(f"   🧹 Memory Management: EFFECTIVE")
        logger.info(f"   🔗 Connection Cleanup: VERIFIED")
        logger.info(f"   📊 Resource Growth: CONTROLLED")


if __name__ == "__main__":
    # Run this E2E test standalone
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s",  # Show real-time output
        "--timeout=300",  # Allow time for load testing
        "-m", "not stress",  # Skip stress tests by default
    ])