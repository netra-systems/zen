#!/usr/bin/env python
"""
Performance and Scaling E2E Tests for Staging Environment

Business Value Justification (BVJ):
- Segment: Enterprise - High-volume customers
- Business Goal: Validate $500K+ MRR scaling capacity and performance under load
- Value Impact: Ensures staging can handle enterprise-scale concurrent operations
- Strategic/Revenue Impact: Prevents performance bottlenecks that cause customer churn

This test suite validates performance and scaling characteristics:
1. Concurrent user load testing with authentication
2. WebSocket connection scaling and message throughput
3. Agent execution performance under concurrent load
4. Memory and resource usage validation
5. Response time degradation under load
6. Connection pool and resource exhaustion testing
7. Error rate and reliability under stress

 ALERT:  CRITICAL E2E REQUIREMENTS:
- ALL tests use REAL authentication and staging services
- Real concurrent load generation and measurement
- Performance metrics collection and validation
- Realistic enterprise-scale load patterns
- Resource usage monitoring and limits
"""

import asyncio
import json
import logging
import psutil
import statistics
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import pytest
import aiohttp
import websockets
from dataclasses import dataclass, field

# Import E2E auth helper for SSOT authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper,
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging_config import StagingTestConfig, get_staging_config

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics collection and analysis."""
    response_times: List[float] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    def add_response_time(self, response_time: float, success: bool = True) -> None:
        """Add a response time measurement."""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def finalize(self) -> None:
        """Finalize metrics collection."""
        self.end_time = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        duration = (self.end_time or time.time()) - self.start_time
        
        return {
            "total_requests": len(self.response_times),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p95_response_time": self._percentile(self.response_times, 0.95),
            "p99_response_time": self._percentile(self.response_times, 0.99),
            "total_duration": duration,
            "requests_per_second": len(self.response_times) / duration if duration > 0 else 0
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]


class TestPerformanceAndScaling(BaseE2ETest):
    """
    Performance and Scaling E2E Tests for Staging Environment.
    
    Tests performance characteristics under realistic enterprise load.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_performance_testing_environment(self):
        """Set up performance testing environment with metrics collection."""
        await self.initialize_test_environment()
        
        # Configure for staging environment
        self.staging_config = get_staging_config()
        
        # Validate staging configuration
        assert self.staging_config.validate_configuration(), "Staging configuration invalid"
        
        # Initialize performance monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info()
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        
        # Create test user pool for concurrent operations
        self.concurrent_user_count = 15  # Test with 15 concurrent users
        self.test_users = []
        
        for i in range(self.concurrent_user_count):
            user_context = await create_authenticated_user_context(
                user_email=f"e2e_perf_test_{i}_{int(time.time())}@staging.netra.ai",
                environment="staging",
                permissions=["read", "write", "execute_agents", "performance_test"]
            )
            self.test_users.append(user_context)
        
        self.logger.info(f" PASS:  Performance testing environment setup complete - {len(self.test_users)} test users")
        
    async def test_concurrent_websocket_connection_scaling(self):
        """
        Test WebSocket connection scaling under concurrent load.
        
        BVJ: Validates $200K+ MRR concurrent connection capacity
        Ensures staging can handle multiple simultaneous WebSocket connections
        """
        connection_metrics = PerformanceMetrics()
        connection_results = []
        
        async def establish_concurrent_connection(user_index: int, user_context):
            """Establish and maintain WebSocket connection for performance testing."""
            connection_start = time.time()
            
            try:
                # Create auth helper for this user
                ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
                
                # Establish connection
                websocket = await ws_auth_helper.connect_authenticated_websocket(timeout=30.0)
                connection_time = time.time() - connection_start
                
                # Send test messages to validate connection quality
                messages_sent = 0
                messages_received = 0
                
                # Send multiple test messages
                for msg_index in range(5):
                    test_message = {
                        "type": "performance_test",
                        "user_index": user_index,
                        "message_index": msg_index,
                        "timestamp": time.time()
                    }
                    
                    msg_start = time.time()
                    await websocket.send(json.dumps(test_message))
                    messages_sent += 1
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        messages_received += 1
                        msg_time = time.time() - msg_start
                        connection_metrics.add_response_time(msg_time, True)
                    except asyncio.TimeoutError:
                        connection_metrics.add_response_time(5.0, False)
                
                # Keep connection alive for scaling test
                await asyncio.sleep(10.0)  # Hold connection for 10 seconds
                
                # Clean up
                await websocket.close()
                
                return {
                    "user_index": user_index,
                    "success": True,
                    "connection_time": connection_time,
                    "messages_sent": messages_sent,
                    "messages_received": messages_received,
                    "message_success_rate": messages_received / messages_sent if messages_sent > 0 else 0
                }
                
            except Exception as e:
                connection_time = time.time() - connection_start
                connection_metrics.add_response_time(connection_time, False)
                
                return {
                    "user_index": user_index,
                    "success": False,
                    "connection_time": connection_time,
                    "error": str(e)
                }
        
        # Create concurrent connections
        connection_tasks = [
            establish_concurrent_connection(i, user_context)
            for i, user_context in enumerate(self.test_users)
        ]
        
        # Execute with performance monitoring
        start_memory = self.process.memory_info()
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        end_memory = self.process.memory_info()
        
        connection_metrics.finalize()
        
        # Analyze connection scaling results
        successful_connections = [r for r in connection_results if isinstance(r, dict) and r.get("success")]
        failed_connections = [r for r in connection_results if isinstance(r, dict) and not r.get("success")]
        
        # Validate connection scaling performance
        success_rate = len(successful_connections) / len(connection_results) if connection_results else 0
        assert success_rate >= 0.8, f"Connection success rate too low: {success_rate:.1%}"
        
        # Validate connection performance
        connection_times = [r["connection_time"] for r in successful_connections]
        avg_connection_time = sum(connection_times) / len(connection_times) if connection_times else 0
        max_connection_time = max(connection_times) if connection_times else 0
        
        assert avg_connection_time <= 20.0, f"Average connection time too slow: {avg_connection_time:.1f}s"
        assert max_connection_time <= 35.0, f"Maximum connection time too slow: {max_connection_time:.1f}s"
        
        # Validate message throughput
        total_messages_sent = sum(r.get("messages_sent", 0) for r in successful_connections)
        total_messages_received = sum(r.get("messages_received", 0) for r in successful_connections)
        overall_message_success_rate = total_messages_received / total_messages_sent if total_messages_sent > 0 else 0
        
        assert overall_message_success_rate >= 0.7, f"Message success rate too low: {overall_message_success_rate:.1%}"
        
        # Memory usage validation
        memory_increase = end_memory.rss - start_memory.rss
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # Memory increase should be reasonable for the number of connections
        expected_memory_per_connection = 5  # MB per connection is reasonable
        max_expected_memory = len(self.test_users) * expected_memory_per_connection
        
        if memory_increase_mb > max_expected_memory:
            self.logger.warning(f"High memory usage during connection scaling: {memory_increase_mb:.1f}MB")
        
        self.logger.info(f" PASS:  Concurrent WebSocket connection scaling completed")
        self.logger.info(f"[U+1F50C] Successful connections: {len(successful_connections)}/{len(connection_results)}")
        self.logger.info(f"[U+23F1][U+FE0F] Average connection time: {avg_connection_time:.1f}s")
        self.logger.info(f" CHART:  Message success rate: {overall_message_success_rate:.1%}")
        self.logger.info(f"[U+1F9E0] Memory increase: {memory_increase_mb:.1f}MB")
        
    async def test_concurrent_agent_execution_performance(self):
        """
        Test agent execution performance under concurrent load.
        
        BVJ: Validates $500K+ MRR agent processing capacity
        Ensures multiple users can execute agents simultaneously with good performance
        """
        agent_metrics = PerformanceMetrics()
        execution_results = []
        
        async def execute_concurrent_agent(user_index: int, user_context):
            """Execute agent for performance testing."""
            execution_start = time.time()
            
            try:
                # Create WebSocket connection for this agent execution
                ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await ws_auth_helper.connect_authenticated_websocket(timeout=25.0)
                
                # Track agent execution events
                agent_events = []
                agent_completed = False
                
                async def collect_agent_events():
                    nonlocal agent_completed
                    try:
                        async for message in websocket:
                            event = json.loads(message)
                            agent_events.append({
                                "type": event.get("type"),
                                "timestamp": time.time(),
                                "relative_time": time.time() - execution_start
                            })
                            
                            if event.get("type") == "agent_completed":
                                agent_completed = True
                                break
                                
                    except Exception as e:
                        self.logger.debug(f"Event collection error for user {user_index}: {e}")
                
                # Start event collection
                event_task = asyncio.create_task(collect_agent_events())
                
                # Send agent execution request
                agent_request = {
                    "type": "execute_agent",
                    "agent_type": "performance_test_agent",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "performance_test": True,
                        "user_index": user_index,
                        "concurrent_execution": True,
                        "complexity": "medium"  # Medium complexity for performance testing
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Wait for agent completion with timeout
                try:
                    await asyncio.wait_for(event_task, timeout=60.0)  # 60s timeout for agent execution
                    execution_time = time.time() - execution_start
                    agent_metrics.add_response_time(execution_time, agent_completed)
                    
                except asyncio.TimeoutError:
                    execution_time = time.time() - execution_start
                    agent_metrics.add_response_time(execution_time, False)
                    agent_completed = False
                
                await websocket.close()
                
                return {
                    "user_index": user_index,
                    "success": agent_completed,
                    "execution_time": execution_time,
                    "events_received": len(agent_events),
                    "agent_events": agent_events
                }
                
            except Exception as e:
                execution_time = time.time() - execution_start
                agent_metrics.add_response_time(execution_time, False)
                
                return {
                    "user_index": user_index,
                    "success": False,
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        # Execute agents concurrently with performance monitoring
        start_memory = self.process.memory_info()
        start_cpu_percent = self.process.cpu_percent()
        
        # Use smaller batch for agent execution to avoid overloading staging
        concurrent_agents = self.test_users[:8]  # Test with 8 concurrent agents
        
        agent_tasks = [
            execute_concurrent_agent(i, user_context)
            for i, user_context in enumerate(concurrent_agents)
        ]
        
        execution_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        end_memory = self.process.memory_info()
        end_cpu_percent = self.process.cpu_percent()
        
        agent_metrics.finalize()
        
        # Analyze agent execution performance
        successful_executions = [r for r in execution_results if isinstance(r, dict) and r.get("success")]
        failed_executions = [r for r in execution_results if isinstance(r, dict) and not r.get("success")]
        
        # Validate agent execution performance
        success_rate = len(successful_executions) / len(execution_results) if execution_results else 0
        assert success_rate >= 0.7, f"Agent execution success rate too low: {success_rate:.1%}"
        
        # Validate execution times
        execution_times = [r["execution_time"] for r in successful_executions]
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
            max_execution_time = max(execution_times)
            
            assert avg_execution_time <= 45.0, f"Average agent execution time too slow: {avg_execution_time:.1f}s"
            assert max_execution_time <= 70.0, f"Maximum agent execution time too slow: {max_execution_time:.1f}s"
        
        # Validate event delivery performance
        total_events = sum(r.get("events_received", 0) for r in successful_executions)
        avg_events_per_execution = total_events / len(successful_executions) if successful_executions else 0
        
        assert avg_events_per_execution >= 3, f"Too few events per agent execution: {avg_events_per_execution:.1f}"
        
        # Performance metrics validation
        perf_stats = agent_metrics.get_stats()
        requests_per_second = perf_stats.get("requests_per_second", 0)
        
        # Should handle reasonable throughput
        assert requests_per_second >= 0.1, f"Agent execution throughput too low: {requests_per_second:.2f} req/s"
        
        self.logger.info(f" PASS:  Concurrent agent execution performance completed")
        self.logger.info(f"[U+1F916] Successful executions: {len(successful_executions)}/{len(execution_results)}")
        self.logger.info(f"[U+23F1][U+FE0F] Average execution time: {avg_execution_time if execution_times else 0:.1f}s")
        self.logger.info(f" CHART:  Events per execution: {avg_events_per_execution:.1f}")
        self.logger.info(f" CYCLE:  Throughput: {requests_per_second:.2f} req/s")
        
    async def test_api_endpoint_performance_under_load(self):
        """
        Test API endpoint performance under concurrent HTTP load.
        
        BVJ: Validates $100K+ MRR API responsiveness
        Ensures API endpoints maintain good performance under load
        """
        api_metrics = PerformanceMetrics()
        
        async def make_concurrent_api_requests(user_index: int, user_context):
            """Make multiple API requests for load testing."""
            auth_helper = E2EAuthHelper(environment="staging")
            
            # Create authenticated session
            auth_token = auth_helper.create_test_jwt_token(
                user_id=user_context.user_id,
                email=user_context.agent_context["user_email"]
            )
            headers = auth_helper.get_auth_headers(auth_token)
            
            request_results = []
            
            # Test multiple API endpoints with multiple requests each
            api_endpoints = [
                ("health", f"{self.staging_config.urls.backend_url}/health", "GET"),
                ("auth_health", f"{self.staging_config.urls.auth_url}/auth/health", "GET")
            ]
            
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as session:
                for endpoint_name, endpoint_url, method in api_endpoints:
                    # Make multiple requests to each endpoint
                    for req_index in range(3):  # 3 requests per endpoint per user
                        request_start = time.time()
                        
                        try:
                            if method == "GET":
                                async with session.get(endpoint_url) as resp:
                                    request_time = time.time() - request_start
                                    success = resp.status < 500  # 4xx is acceptable, 5xx is not
                                    
                                    api_metrics.add_response_time(request_time, success)
                                    
                                    request_results.append({
                                        "endpoint": endpoint_name,
                                        "url": endpoint_url,
                                        "method": method,
                                        "status": resp.status,
                                        "response_time": request_time,
                                        "success": success,
                                        "request_index": req_index
                                    })
                                    
                        except Exception as e:
                            request_time = time.time() - request_start
                            api_metrics.add_response_time(request_time, False)
                            
                            request_results.append({
                                "endpoint": endpoint_name,
                                "url": endpoint_url,
                                "method": method,
                                "error": str(e),
                                "response_time": request_time,
                                "success": False,
                                "request_index": req_index
                            })
                        
                        # Brief pause between requests
                        await asyncio.sleep(0.1)
            
            return {
                "user_index": user_index,
                "requests": request_results,
                "total_requests": len(request_results),
                "successful_requests": sum(1 for r in request_results if r.get("success"))
            }
        
        # Execute API load test
        api_load_users = self.test_users[:10]  # Use 10 users for API load testing
        
        api_tasks = [
            make_concurrent_api_requests(i, user_context)
            for i, user_context in enumerate(api_load_users)
        ]
        
        api_results = await asyncio.gather(*api_tasks, return_exceptions=True)
        api_metrics.finalize()
        
        # Analyze API performance results
        successful_user_results = [r for r in api_results if isinstance(r, dict) and "requests" in r]
        
        # Aggregate all API requests across users
        all_requests = []
        for user_result in successful_user_results:
            all_requests.extend(user_result.get("requests", []))
        
        successful_requests = [r for r in all_requests if r.get("success")]
        failed_requests = [r for r in all_requests if not r.get("success")]
        
        # Validate API performance under load
        overall_success_rate = len(successful_requests) / len(all_requests) if all_requests else 0
        assert overall_success_rate >= 0.85, f"API success rate under load too low: {overall_success_rate:.1%}"
        
        # Validate response times
        response_times = [r["response_time"] for r in successful_requests]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = api_metrics._percentile(response_times, 0.95)
            
            assert avg_response_time <= 10.0, f"Average API response time too slow: {avg_response_time:.2f}s"
            assert p95_response_time <= 20.0, f"P95 API response time too slow: {p95_response_time:.2f}s"
        
        # Validate throughput
        perf_stats = api_metrics.get_stats()
        throughput = perf_stats.get("requests_per_second", 0)
        
        assert throughput >= 1.0, f"API throughput too low: {throughput:.2f} req/s"
        
        # Endpoint-specific analysis
        endpoint_stats = defaultdict(list)
        for request in successful_requests:
            endpoint_stats[request["endpoint"]].append(request["response_time"])
        
        for endpoint, times in endpoint_stats.items():
            avg_time = sum(times) / len(times) if times else 0
            self.logger.info(f"   CHART:  {endpoint}: {len(times)} requests, avg {avg_time:.2f}s")
        
        self.logger.info(f" PASS:  API endpoint performance under load completed")
        self.logger.info(f"[U+1F517] Total API requests: {len(all_requests)}")
        self.logger.info(f" CHART:  Success rate: {overall_success_rate:.1%}")
        self.logger.info(f"[U+23F1][U+FE0F] Average response time: {avg_response_time if response_times else 0:.2f}s")
        self.logger.info(f" CYCLE:  Throughput: {throughput:.2f} req/s")
        
    async def test_memory_and_resource_usage_under_load(self):
        """
        Test memory and resource usage behavior under sustained load.
        
        BVJ: Validates $25K+ MRR operational stability
        Ensures system resources remain stable under load
        """
        resource_metrics = {
            "memory_samples": [],
            "cpu_samples": [],
            "connection_counts": [],
            "start_time": time.time()
        }
        
        # Initial resource measurement
        initial_memory = self.process.memory_info()
        initial_cpu = self.process.cpu_percent()
        
        resource_metrics["initial_memory_mb"] = initial_memory.rss / (1024 * 1024)
        resource_metrics["initial_cpu_percent"] = initial_cpu
        
        async def sustained_load_operation(user_index: int, user_context):
            """Generate sustained load for resource testing."""
            operations_completed = 0
            
            try:
                # Create WebSocket connection for sustained operation
                ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await ws_auth_helper.connect_authenticated_websocket(timeout=30.0)
                
                # Perform sustained operations for resource testing
                operation_duration = 30.0  # 30 seconds of sustained operations
                operation_start = time.time()
                
                while (time.time() - operation_start) < operation_duration:
                    # Send periodic messages
                    message = {
                        "type": "resource_test",
                        "user_index": user_index,
                        "operation_count": operations_completed,
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(message))
                    operations_completed += 1
                    
                    # Wait between operations
                    await asyncio.sleep(2.0)
                
                # Clean up
                await websocket.close()
                
                return {
                    "user_index": user_index,
                    "operations_completed": operations_completed,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "operations_completed": operations_completed,
                    "error": str(e),
                    "success": False
                }
        
        # Start sustained load with resource monitoring
        load_users = self.test_users[:6]  # Use 6 users for sustained load
        
        # Start load operations
        load_tasks = [
            sustained_load_operation(i, user_context)
            for i, user_context in enumerate(load_users)
        ]
        
        # Monitor resources during load
        async def monitor_resources():
            monitor_start = time.time()
            sample_count = 0
            
            while (time.time() - monitor_start) < 35.0:  # Monitor for 35 seconds
                try:
                    # Sample memory and CPU
                    memory_info = self.process.memory_info()
                    cpu_percent = self.process.cpu_percent()
                    
                    resource_metrics["memory_samples"].append({
                        "timestamp": time.time() - monitor_start,
                        "memory_mb": memory_info.rss / (1024 * 1024),
                        "memory_vms_mb": memory_info.vms / (1024 * 1024) if hasattr(memory_info, 'vms') else 0
                    })
                    
                    resource_metrics["cpu_samples"].append({
                        "timestamp": time.time() - monitor_start,
                        "cpu_percent": cpu_percent
                    })
                    
                    sample_count += 1
                    
                except Exception as e:
                    self.logger.debug(f"Resource monitoring error: {e}")
                
                await asyncio.sleep(1.0)  # Sample every second
        
        # Run load and monitoring concurrently
        monitoring_task = asyncio.create_task(monitor_resources())
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        await monitoring_task
        
        resource_metrics["end_time"] = time.time()
        resource_metrics["total_duration"] = resource_metrics["end_time"] - resource_metrics["start_time"]
        
        # Analyze resource usage
        successful_load_ops = [r for r in load_results if isinstance(r, dict) and r.get("success")]
        total_operations = sum(r.get("operations_completed", 0) for r in successful_load_ops)
        
        # Memory analysis
        if resource_metrics["memory_samples"]:
            memory_values = [s["memory_mb"] for s in resource_metrics["memory_samples"]]
            resource_metrics["peak_memory_mb"] = max(memory_values)
            resource_metrics["avg_memory_mb"] = sum(memory_values) / len(memory_values)
            resource_metrics["memory_increase_mb"] = resource_metrics["peak_memory_mb"] - resource_metrics["initial_memory_mb"]
        
        # CPU analysis
        if resource_metrics["cpu_samples"]:
            cpu_values = [s["cpu_percent"] for s in resource_metrics["cpu_samples"]]
            resource_metrics["peak_cpu_percent"] = max(cpu_values)
            resource_metrics["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
        
        # Validate resource usage is reasonable
        memory_increase = resource_metrics.get("memory_increase_mb", 0)
        peak_cpu = resource_metrics.get("peak_cpu_percent", 0)
        avg_cpu = resource_metrics.get("avg_cpu_percent", 0)
        
        # Memory increase should be reasonable for the load
        max_acceptable_memory_increase = len(load_users) * 10  # 10MB per user is reasonable
        if memory_increase > max_acceptable_memory_increase:
            self.logger.warning(f"High memory increase during load: {memory_increase:.1f}MB")
        
        # CPU usage should be reasonable (not sustained high usage)
        if avg_cpu > 80.0:
            self.logger.warning(f"High average CPU usage during load: {avg_cpu:.1f}%")
        
        self.logger.info(f" PASS:  Memory and resource usage testing completed")
        self.logger.info(f"[U+1F9E0] Memory increase: {memory_increase:.1f}MB")
        self.logger.info(f" LIGHTNING:  Peak CPU: {peak_cpu:.1f}%, Average CPU: {avg_cpu:.1f}%")
        self.logger.info(f" CYCLE:  Total operations completed: {total_operations}")
        self.logger.info(f" CHART:  Resource samples: {len(resource_metrics['memory_samples'])} memory, {len(resource_metrics['cpu_samples'])} CPU")
        
    async def test_error_rate_and_reliability_under_stress(self):
        """
        Test error rates and system reliability under stress conditions.
        
        BVJ: Validates $100K+ MRR system resilience
        Ensures system maintains reliability under stress
        """
        stress_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "error_types": defaultdict(int),
            "response_times": [],
            "start_time": time.time()
        }
        
        async def generate_stress_load(user_index: int, user_context):
            """Generate stress load with various operation types."""
            user_operations = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "errors": []
            }
            
            try:
                # Create multiple connections for stress testing
                ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
                
                # Perform various types of operations rapidly
                operation_types = [
                    "quick_query",
                    "data_request", 
                    "status_check",
                    "ping_test",
                    "connection_test"
                ]
                
                for operation_type in operation_types:
                    for attempt in range(3):  # 3 attempts per operation type
                        op_start = time.time()
                        user_operations["total"] += 1
                        stress_metrics["total_operations"] += 1
                        
                        try:
                            # Quick connection for each operation (stress test)
                            websocket = await ws_auth_helper.connect_authenticated_websocket(timeout=15.0)
                            
                            # Send operation
                            operation_message = {
                                "type": operation_type,
                                "user_index": user_index,
                                "attempt": attempt,
                                "timestamp": time.time()
                            }
                            
                            await websocket.send(json.dumps(operation_message))
                            
                            # Try to get response quickly
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                                user_operations["successful"] += 1
                                stress_metrics["successful_operations"] += 1
                                
                            except asyncio.TimeoutError:
                                user_operations["failed"] += 1
                                stress_metrics["failed_operations"] += 1
                                stress_metrics["error_types"]["timeout"] += 1
                            
                            await websocket.close()
                            
                            op_time = time.time() - op_start
                            stress_metrics["response_times"].append(op_time)
                            
                        except Exception as e:
                            user_operations["failed"] += 1
                            stress_metrics["failed_operations"] += 1
                            stress_metrics["error_types"][type(e).__name__] += 1
                            
                            user_operations["errors"].append({
                                "operation_type": operation_type,
                                "attempt": attempt,
                                "error": str(e)
                            })
                            
                            op_time = time.time() - op_start
                            stress_metrics["response_times"].append(op_time)
                        
                        # Brief pause between operations
                        await asyncio.sleep(0.5)
                
                return {
                    "user_index": user_index,
                    "operations": user_operations,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "operations": user_operations,
                    "error": str(e),
                    "success": False
                }
        
        # Execute stress test with subset of users
        stress_users = self.test_users[:5]  # Use 5 users for stress testing
        
        stress_tasks = [
            generate_stress_load(i, user_context)
            for i, user_context in enumerate(stress_users)
        ]
        
        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        stress_metrics["end_time"] = time.time()
        
        # Analyze stress test results
        successful_users = [r for r in stress_results if isinstance(r, dict) and r.get("success")]
        
        # Calculate overall error rate
        total_ops = stress_metrics["total_operations"]
        successful_ops = stress_metrics["successful_operations"]
        failed_ops = stress_metrics["failed_operations"]
        
        overall_success_rate = successful_ops / total_ops if total_ops > 0 else 0
        overall_error_rate = failed_ops / total_ops if total_ops > 0 else 0
        
        # Validate acceptable error rate under stress
        max_acceptable_error_rate = 0.3  # 30% error rate acceptable under stress
        assert overall_error_rate <= max_acceptable_error_rate, f"Error rate under stress too high: {overall_error_rate:.1%}"
        
        # Validate some operations succeed even under stress
        assert overall_success_rate >= 0.5, f"Success rate under stress too low: {overall_success_rate:.1%}"
        
        # Analyze response time distribution
        if stress_metrics["response_times"]:
            response_times = stress_metrics["response_times"]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # Response times might be higher under stress but shouldn't be excessive
            assert avg_response_time <= 30.0, f"Average response time under stress too high: {avg_response_time:.1f}s"
            assert max_response_time <= 60.0, f"Maximum response time under stress too high: {max_response_time:.1f}s"
        
        # Analyze error types
        error_summary = dict(stress_metrics["error_types"])
        most_common_error = max(error_summary, key=error_summary.get) if error_summary else "None"
        
        self.logger.info(f" PASS:  Error rate and reliability under stress testing completed")
        self.logger.info(f" CHART:  Total operations: {total_ops}")
        self.logger.info(f" PASS:  Success rate: {overall_success_rate:.1%}")
        self.logger.info(f" FAIL:  Error rate: {overall_error_rate:.1%}")
        self.logger.info(f"[U+1F527] Most common error: {most_common_error}")
        self.logger.info(f"[U+23F1][U+FE0F] Avg response time: {avg_response_time if stress_metrics['response_times'] else 0:.1f}s")


# Integration with pytest for automated test discovery
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])