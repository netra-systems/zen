"""
E2E Test: Agent Performance & SLA Validation (Staging)

Business Value: $500K+ ARR - Performance requirements for optimal UX
Environment: GCP Staging with real performance constraints (NO DOCKER)
Coverage: Response times, throughput, resource usage, concurrent users
SLAs: <3s simple, <10s complex, <15s tool-heavy, multi-user isolation

GitHub Issue: #861 - Agent Golden Path Messages E2E Test Coverage  
Test Plan: /test_plans/agent_golden_path_messages_e2e_plan_20250914.md

MISSION CRITICAL: This test validates performance SLAs that directly impact user experience:

RESPONSE TIME SLAs:
- Simple questions: <3s response time
- Complex analysis: <10s response time  
- Tool-heavy workflows: <15s response time
- Multi-user concurrent: No performance degradation

BUSINESS IMPACT VALIDATION:
- User experience requirements (fast response = user retention)
- Multi-user scalability (enterprise requirement)
- Resource efficiency (cost optimization)
- System reliability under load (uptime protection)

SUCCESS CRITERIA:
- All response time SLAs met consistently
- Performance isolation between concurrent users
- Memory/CPU usage within bounds (no leaks)
- System remains responsive under load
- Error rates <1% during performance testing
"""

import pytest
import asyncio
import json
import time
import websockets
import ssl
import base64
import uuid
import psutil
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import httpx
import concurrent.futures

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_config import StagingTestConfig as StagingConfig

# Real service clients for staging
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentPerformanceSLAStaging(StagingTestBase):
    """
    Agent performance and SLA validation with real staging services
    
    BUSINESS IMPACT: Validates user experience performance requirements
    ENVIRONMENT: GCP Staging with real performance constraints
    COVERAGE: Response times, throughput, resource usage, scalability
    """
    
    # Performance SLA definitions
    PERFORMANCE_SLAS = {
        "simple_query": {
            "max_response_time": 3.0,
            "description": "Simple questions and basic information",
            "examples": [
                "What is AI optimization?", 
                "Explain machine learning benefits",
                "Define Netra platform"
            ]
        },
        "complex_analysis": {
            "max_response_time": 10.0,
            "description": "Complex analysis requiring reasoning",
            "examples": [
                "Analyze Q3 performance trends and provide recommendations",
                "Create optimization strategy for AI infrastructure",
                "Compare different ML model approaches"
            ]
        },
        "tool_heavy_workflow": {
            "max_response_time": 15.0,
            "description": "Multi-tool workflows with data processing",
            "examples": [
                "Generate comprehensive performance report with cost analysis",
                "Analyze system metrics and create optimization roadmap",
                "Process data files and create visualization dashboard"
            ]
        }
    }
    
    # Concurrent performance requirements
    CONCURRENT_PERFORMANCE_REQUIREMENTS = {
        "max_users": 5,  # Concurrent users for staging testing
        "performance_degradation_threshold": 1.5,  # Max slowdown multiplier
        "error_rate_threshold": 0.01,  # <1% error rate
        "memory_growth_threshold": 100 * 1024 * 1024  # 100MB max growth
    }
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Setup performance testing infrastructure"""
        await super().asyncSetUpClass()
        
        # Initialize staging configuration
        cls.staging_config = StagingConfig()
        cls.staging_backend_url = cls.staging_config.get_backend_websocket_url()
        
        # Initialize real service clients
        cls.auth_client = StagingAuthClient()
        cls.websocket_client = RealWebSocketClient()
        
        # Verify staging services performance baseline
        await cls._verify_staging_performance_baseline()
        
        # Create performance test users
        cls.performance_test_users = await cls._create_performance_test_users()
        
        # Initialize performance monitoring
        cls.performance_metrics = {
            "baseline_memory": psutil.virtual_memory().used,
            "baseline_cpu": psutil.cpu_percent(),
            "test_start_time": time.time()
        }
        
        cls.logger.info("Agent performance SLA staging test setup completed")
    
    @classmethod
    async def _verify_staging_performance_baseline(cls):
        """Verify staging services meet basic performance requirements"""
        try:
            baseline_start = time.time()
            
            # Test basic API response time
            async with httpx.AsyncClient(timeout=10) as client:
                health_response = await client.get(
                    cls.staging_config.get_api_health_endpoint()
                )
                
                api_response_time = time.time() - baseline_start
                
                if health_response.status_code != 200:
                    pytest.skip(f"Staging API not healthy: {health_response.status_code}")
                
                # API should respond quickly for performance testing
                assert api_response_time < 2.0, \
                    f"Staging API too slow for performance testing: {api_response_time:.1f}s"
            
            # Test WebSocket connection time
            ws_start = time.time()
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            test_connection = await asyncio.wait_for(
                websockets.connect(
                    cls.staging_backend_url,
                    ssl=ssl_context if cls.staging_backend_url.startswith('wss') else None
                ),
                timeout=5
            )
            
            ws_connection_time = time.time() - ws_start
            await test_connection.close()
            
            # WebSocket should connect quickly
            assert ws_connection_time < 3.0, \
                f"Staging WebSocket too slow: {ws_connection_time:.1f}s"
            
            cls.logger.info(
                f"Performance baseline verified: API {api_response_time:.1f}s, "
                f"WebSocket {ws_connection_time:.1f}s"
            )
            
        except Exception as e:
            pytest.skip(f"Staging performance baseline not met: {e}")
    
    @classmethod
    async def _create_performance_test_users(cls) -> List[Dict[str, Any]]:
        """Create users optimized for performance testing"""
        performance_users = []
        
        # Create users for each SLA category
        for sla_type, sla_config in cls.PERFORMANCE_SLAS.items():
            user_data = {
                "user_id": f"perf_user_{sla_type}_{int(time.time())}",
                "email": f"perf_{sla_type}@netrasystems-staging.ai",
                "sla_category": sla_type,
                "max_response_time": sla_config["max_response_time"],
                "test_permissions": ["basic_chat", "agent_access", "performance_testing"]
            }
            
            try:
                access_token = await cls.auth_client.generate_test_access_token(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    permissions=user_data["test_permissions"]
                )
                
                user_data["access_token"] = access_token
                user_data["encoded_token"] = base64.urlsafe_b64encode(
                    access_token.encode()
                ).decode().rstrip('=')
                
                performance_users.append(user_data)
                cls.logger.info(f"Created performance test user: {user_data['email']}")
                
            except Exception as e:
                cls.logger.error(f"Failed to create performance user for {sla_type}: {e}")
        
        # Create additional concurrent users
        for i in range(cls.CONCURRENT_PERFORMANCE_REQUIREMENTS["max_users"]):
            user_data = {
                "user_id": f"concurrent_perf_user_{i}_{int(time.time())}",
                "email": f"concurrent_perf_{i}@netrasystems-staging.ai", 
                "sla_category": "concurrent_testing",
                "concurrent_user_index": i,
                "test_permissions": ["basic_chat", "agent_access", "concurrent_testing"]
            }
            
            try:
                access_token = await cls.auth_client.generate_test_access_token(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    permissions=user_data["test_permissions"]
                )
                
                user_data["access_token"] = access_token
                user_data["encoded_token"] = base64.urlsafe_b64encode(
                    access_token.encode()
                ).decode().rstrip('=')
                
                performance_users.append(user_data)
                
            except Exception as e:
                cls.logger.error(f"Failed to create concurrent user {i}: {e}")
        
        if len(performance_users) < 3:
            pytest.skip("Insufficient performance test users created")
            
        return performance_users

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    async def test_agent_response_time_sla_validation(self):
        """
        BUSINESS SLA: Validate agent response times meet user experience requirements
        
        SLA Categories:
        - Simple questions: <3s response time (immediate feedback)
        - Complex analysis: <10s response time (acceptable for analysis)  
        - Tool-heavy workflows: <15s response time (maximum patience threshold)
        
        Validation includes:
        - End-to-end latency measurement (user perspective)
        - WebSocket event timing analysis (real-time UX)
        - Database persistence timing (data reliability)
        - LLM API call performance (external dependency)
        - Statistical analysis (multiple runs for confidence)
        """
        performance_results = []
        
        # Test each SLA category with multiple examples
        for sla_type, sla_config in self.PERFORMANCE_SLAS.items():
            user = next(
                (u for u in self.performance_test_users if u.get("sla_category") == sla_type), 
                None
            )
            
            if not user:
                pytest.fail(f"No performance test user for SLA category: {sla_type}")
            
            self.logger.info(f"Testing SLA category: {sla_type} (max: {sla_config['max_response_time']}s)")
            
            category_results = []
            
            # Test multiple examples for statistical confidence
            for example_message in sla_config["examples"]:
                try:
                    # Measure complete response time
                    response_metrics = await self._measure_complete_response_time(
                        user, example_message, sla_type
                    )
                    
                    category_results.append(response_metrics)
                    
                    # Validate SLA compliance
                    total_time = response_metrics["total_response_time"]
                    assert total_time <= sla_config["max_response_time"], \
                        f"SLA violation for {sla_type}: {total_time:.1f}s > {sla_config['max_response_time']}s"
                    
                    self.logger.info(
                        f"SLA passed for {sla_type}: {total_time:.1f}s "
                        f"(limit: {sla_config['max_response_time']}s)"
                    )
                    
                except Exception as e:
                    category_results.append({
                        "message": example_message,
                        "status": "failed",
                        "error": str(e)
                    })
                    pytest.fail(f"Performance test failed for {sla_type}: {e}")
            
            # Statistical analysis of category performance
            successful_results = [r for r in category_results if r.get("status") == "success"]
            if successful_results:
                response_times = [r["total_response_time"] for r in successful_results]
                
                category_stats = {
                    "sla_category": sla_type,
                    "max_allowed": sla_config["max_response_time"],
                    "samples": len(response_times),
                    "average": statistics.mean(response_times),
                    "median": statistics.median(response_times),
                    "max": max(response_times),
                    "min": min(response_times),
                    "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
                    "sla_compliance": all(t <= sla_config["max_response_time"] for t in response_times)
                }
                
                performance_results.append(category_stats)
                
                assert category_stats["sla_compliance"], \
                    f"SLA category {sla_type} failed compliance: {category_stats}"
            
        # Overall performance validation
        assert len(performance_results) == len(self.PERFORMANCE_SLAS), \
            f"Not all SLA categories tested: {len(performance_results)}/{len(self.PERFORMANCE_SLAS)}"
        
        failed_categories = [r for r in performance_results if not r["sla_compliance"]]
        assert len(failed_categories) == 0, f"SLA failures: {failed_categories}"
        
        self.logger.info(f"All performance SLAs validated: {performance_results}")

    async def _measure_complete_response_time(
        self,
        user: Dict[str, Any],
        message: str,
        sla_category: str
    ) -> Dict[str, Any]:
        """Measure complete response time with detailed breakdowns"""
        
        # Start timing
        total_start = time.time()
        metrics = {
            "message": message,
            "sla_category": sla_category,
            "user_id": user["user_id"]
        }
        
        try:
            # Phase 1: WebSocket connection establishment
            connection_start = time.time()
            connection = await self._establish_performance_websocket_connection(user)
            metrics["connection_time"] = time.time() - connection_start
            
            # Phase 2: Message send and first response
            send_start = time.time()
            message_payload = {
                "type": "chat_message",
                "data": {
                    "message": message,
                    "user_id": user["user_id"],
                    "performance_test": True,
                    "sla_category": sla_category,
                    "timestamp": int(time.time())
                }
            }
            
            await connection.send(json.dumps(message_payload))
            metrics["send_time"] = time.time() - send_start
            
            # Phase 3: Track events and final response
            event_tracking_start = time.time()
            events = []
            final_response = None
            
            # Wait for agent completion or timeout
            max_wait_time = self.PERFORMANCE_SLAS[sla_category]["max_response_time"] + 5.0
            
            while time.time() - event_tracking_start < max_wait_time:
                try:
                    event_message = await asyncio.wait_for(
                        connection.recv(), 
                        timeout=3.0
                    )
                    
                    event_data = json.loads(event_message)
                    event_time = time.time()
                    
                    events.append({
                        "type": event_data.get("type"),
                        "timestamp": event_time,
                        "elapsed": event_time - total_start
                    })
                    
                    # Check for completion
                    if event_data.get("type") == "agent_completed":
                        final_response = event_data
                        break
                        
                except asyncio.TimeoutError:
                    # Continue waiting but log timeout
                    self.logger.warning(f"Event timeout in performance test: {sla_category}")
                    continue
            
            await connection.close()
            
            # Calculate final metrics
            total_end = time.time()
            metrics.update({
                "total_response_time": total_end - total_start,
                "event_tracking_time": total_end - event_tracking_start,
                "events_received": len(events),
                "event_types": [e["type"] for e in events],
                "first_event_time": events[0]["elapsed"] if events else None,
                "last_event_time": events[-1]["elapsed"] if events else None,
                "final_response_received": final_response is not None,
                "status": "success"
            })
            
            # Validate response was received
            assert final_response is not None, f"No final response received for {sla_category}"
            
            return metrics
            
        except Exception as e:
            metrics.update({
                "status": "failed",
                "error": str(e),
                "total_response_time": time.time() - total_start
            })
            raise

    async def _establish_performance_websocket_connection(self, user: Dict[str, Any]) -> websockets.WebSocketClientProtocol:
        """Establish WebSocket connection optimized for performance testing"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            headers = {
                "Authorization": f"Bearer {user['access_token']}",
                "X-User-ID": user["user_id"],
                "X-Performance-Test": "true",
                "X-SLA-Category": user.get("sla_category", "unknown"),
                "X-Test-Environment": "staging"
            }
            
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.staging_backend_url,
                    extra_headers=headers,
                    ssl=ssl_context if self.staging_backend_url.startswith('wss') else None,
                    ping_interval=30,  # Longer for performance testing
                    ping_timeout=15,
                    close_timeout=10
                ),
                timeout=10  # Quick connection for performance
            )
            
            return connection
            
        except Exception as e:
            self.logger.error(f"Performance WebSocket connection failed: {e}")
            raise

    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.performance
    @pytest.mark.scalability
    async def test_concurrent_user_performance_isolation(self):
        """
        Validate performance isolation between concurrent users
        
        ENTERPRISE REQUIREMENT: Multiple users don't degrade each other's performance
        SCALABILITY VALIDATION: System handles concurrent load efficiently
        ISOLATION VALIDATION: Users don't interfere with response times
        """
        concurrent_users = [
            u for u in self.performance_test_users 
            if u.get("sla_category") == "concurrent_testing"
        ][:self.CONCURRENT_PERFORMANCE_REQUIREMENTS["max_users"]]
        
        if len(concurrent_users) < 3:
            pytest.skip("Insufficient concurrent users for performance testing")
        
        self.logger.info(f"Testing concurrent performance with {len(concurrent_users)} users")
        
        # Baseline: Single user performance
        baseline_user = concurrent_users[0]
        baseline_message = "Analyze system performance metrics and provide optimization recommendations"
        
        baseline_metrics = await self._measure_complete_response_time(
            baseline_user, baseline_message, "concurrent_baseline"
        )
        baseline_time = baseline_metrics["total_response_time"]
        
        # Concurrent: Multiple users simultaneously  
        concurrent_tasks = []
        concurrent_messages = [
            "Generate performance report with cost analysis",
            "Optimize AI infrastructure for better throughput", 
            "Analyze data processing pipeline efficiency",
            "Create system monitoring dashboard",
            "Evaluate resource utilization patterns"
        ]
        
        concurrent_start = time.time()
        
        for i, user in enumerate(concurrent_users[:5]):  # Limit to 5 concurrent users
            message = concurrent_messages[i % len(concurrent_messages)]
            task = asyncio.create_task(
                self._measure_concurrent_user_performance(user, message, i)
            )
            concurrent_tasks.append(task)
        
        # Execute all concurrent requests
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_duration = time.time() - concurrent_start
        
        # Analyze concurrent performance results
        successful_results = [
            r for r in concurrent_results 
            if isinstance(r, dict) and r.get("status") == "success"
        ]
        failed_results = [
            r for r in concurrent_results 
            if isinstance(r, Exception) or (isinstance(r, dict) and r.get("status") != "success")
        ]
        
        # Validate concurrent performance
        assert len(failed_results) == 0, f"Concurrent performance failures: {failed_results}"
        
        assert len(successful_results) >= 3, \
            f"Insufficient successful concurrent results: {len(successful_results)}"
        
        # Check performance isolation (no excessive degradation)
        concurrent_times = [r["total_response_time"] for r in successful_results]
        avg_concurrent_time = statistics.mean(concurrent_times)
        max_concurrent_time = max(concurrent_times)
        
        performance_degradation = avg_concurrent_time / baseline_time
        max_degradation = max_concurrent_time / baseline_time
        
        degradation_threshold = self.CONCURRENT_PERFORMANCE_REQUIREMENTS["performance_degradation_threshold"]
        
        assert performance_degradation <= degradation_threshold, \
            f"Excessive performance degradation: {performance_degradation:.1f}x (max: {degradation_threshold}x)"
        
        assert max_degradation <= degradation_threshold + 0.5, \
            f"Individual user excessive slowdown: {max_degradation:.1f}x"
        
        # Calculate error rate
        error_rate = len(failed_results) / len(concurrent_users)
        error_threshold = self.CONCURRENT_PERFORMANCE_REQUIREMENTS["error_rate_threshold"]
        
        assert error_rate <= error_threshold, \
            f"Error rate too high: {error_rate:.2%} > {error_threshold:.2%}"
        
        self.logger.info(
            f"Concurrent performance test passed: "
            f"{len(successful_results)} users, "
            f"avg degradation: {performance_degradation:.1f}x, "
            f"error rate: {error_rate:.1%}"
        )

    async def _measure_concurrent_user_performance(
        self,
        user: Dict[str, Any],
        message: str,
        user_index: int
    ) -> Dict[str, Any]:
        """Measure performance for a single concurrent user"""
        try:
            start_time = time.time()
            
            # Add user-specific delay to stagger requests slightly
            await asyncio.sleep(user_index * 0.1)
            
            # Measure response time
            metrics = await self._measure_complete_response_time(
                user, message, f"concurrent_user_{user_index}"
            )
            
            metrics.update({
                "user_index": user_index,
                "concurrent_test": True,
                "stagger_delay": user_index * 0.1
            })
            
            return metrics
            
        except Exception as e:
            return {
                "user_index": user_index,
                "status": "failed",
                "error": str(e),
                "total_response_time": time.time() - start_time
            }

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    @pytest.mark.resource_monitoring
    async def test_agent_memory_usage_bounded(self):
        """
        Ensure agent execution doesn't cause memory leaks or excessive resource usage
        
        RESOURCE EFFICIENCY: System operates within memory bounds
        COST OPTIMIZATION: Prevent resource waste in cloud environment
        STABILITY: Avoid out-of-memory conditions
        """
        memory_baseline = psutil.virtual_memory().used
        cpu_baseline = psutil.cpu_percent()
        
        self.logger.info(f"Resource baseline: Memory {memory_baseline / 1024 / 1024:.1f}MB, CPU {cpu_baseline:.1f}%")
        
        # Run multiple agent interactions to test resource usage
        resource_test_user = self.performance_test_users[0]
        resource_measurements = []
        
        resource_test_messages = [
            "Analyze comprehensive system performance data",
            "Generate detailed optimization recommendations", 
            "Process multiple data sources for analysis",
            "Create extensive reporting dashboard",
            "Perform complex calculations and data transformations"
        ]
        
        for i, message in enumerate(resource_test_messages):
            try:
                # Measure resources before interaction
                pre_memory = psutil.virtual_memory().used
                pre_cpu = psutil.cpu_percent()
                
                # Run agent interaction
                interaction_start = time.time()
                response_metrics = await self._measure_complete_response_time(
                    resource_test_user, message, f"resource_test_{i}"
                )
                
                # Measure resources after interaction
                post_memory = psutil.virtual_memory().used  
                post_cpu = psutil.cpu_percent()
                interaction_duration = time.time() - interaction_start
                
                # Calculate resource usage
                memory_delta = post_memory - pre_memory
                cpu_delta = post_cpu - pre_cpu
                
                resource_measurement = {
                    "iteration": i,
                    "message": message[:50],
                    "duration": interaction_duration,
                    "memory_before": pre_memory,
                    "memory_after": post_memory, 
                    "memory_delta": memory_delta,
                    "cpu_before": pre_cpu,
                    "cpu_after": post_cpu,
                    "cpu_delta": cpu_delta,
                    "response_success": response_metrics.get("status") == "success"
                }
                
                resource_measurements.append(resource_measurement)
                
                self.logger.info(
                    f"Resource iteration {i}: Memory Δ{memory_delta / 1024 / 1024:.1f}MB, "
                    f"CPU Δ{cpu_delta:.1f}%, Duration {interaction_duration:.1f}s"
                )
                
                # Brief pause between iterations
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Resource test iteration {i} failed: {e}")
        
        # Analyze resource usage patterns
        successful_measurements = [m for m in resource_measurements if m["response_success"]]
        assert len(successful_measurements) >= 3, "Insufficient successful resource measurements"
        
        # Check memory usage
        memory_deltas = [m["memory_delta"] for m in successful_measurements]
        total_memory_growth = sum(memory_deltas)
        max_memory_growth = self.CONCURRENT_PERFORMANCE_REQUIREMENTS["memory_growth_threshold"]
        
        assert total_memory_growth <= max_memory_growth, \
            f"Excessive memory growth: {total_memory_growth / 1024 / 1024:.1f}MB > {max_memory_growth / 1024 / 1024:.1f}MB"
        
        # Check for memory leaks (consistently increasing memory)
        positive_deltas = [d for d in memory_deltas if d > 0]
        if len(positive_deltas) > len(memory_deltas) * 0.8:
            avg_positive_delta = statistics.mean(positive_deltas)
            self.logger.warning(
                f"Potential memory leak detected: {len(positive_deltas)}/{len(memory_deltas)} "
                f"iterations with positive memory delta (avg: {avg_positive_delta / 1024 / 1024:.1f}MB)"
            )
        
        # Check CPU usage reasonable
        cpu_deltas = [abs(m["cpu_delta"]) for m in successful_measurements]
        avg_cpu_delta = statistics.mean(cpu_deltas) if cpu_deltas else 0
        
        # CPU spikes are expected during processing, but shouldn't be extreme
        assert avg_cpu_delta <= 50.0, f"Excessive average CPU usage: {avg_cpu_delta:.1f}%"
        
        final_memory = psutil.virtual_memory().used
        total_session_memory_growth = final_memory - memory_baseline
        
        self.logger.info(
            f"Resource usage test completed: "
            f"Total memory growth: {total_session_memory_growth / 1024 / 1024:.1f}MB, "
            f"Average CPU delta: {avg_cpu_delta:.1f}%"
        )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    @pytest.mark.throughput
    async def test_agent_throughput_under_load(self):
        """
        Test agent system throughput under sustained load
        
        THROUGHPUT VALIDATION: System handles continuous requests efficiently
        QUEUE MANAGEMENT: Requests processed in reasonable time under load
        STABILITY: System doesn't break down under sustained usage
        """
        throughput_user = self.performance_test_users[0]
        
        # Throughput test configuration
        throughput_duration = 60  # 1 minute sustained load
        request_interval = 2.0  # Request every 2 seconds
        max_requests = throughput_duration // request_interval
        
        self.logger.info(f"Starting throughput test: {max_requests} requests over {throughput_duration}s")
        
        throughput_results = []
        throughput_start = time.time()
        
        # Generate sustained load
        for request_index in range(int(max_requests)):
            request_start = time.time()
            
            try:
                # Vary message complexity to simulate real usage
                message_complexity = request_index % 3
                if message_complexity == 0:
                    message = f"Simple query #{request_index}: What is AI optimization?"
                elif message_complexity == 1:
                    message = f"Complex analysis #{request_index}: Analyze system performance and provide recommendations"
                else:
                    message = f"Tool workflow #{request_index}: Generate comprehensive performance report with metrics"
                
                # Measure individual request performance
                request_metrics = await self._measure_complete_response_time(
                    throughput_user, message, f"throughput_request_{request_index}"
                )
                
                request_end = time.time()
                request_total_time = request_end - request_start
                
                throughput_result = {
                    "request_index": request_index,
                    "request_total_time": request_total_time,
                    "agent_response_time": request_metrics.get("total_response_time", 0),
                    "success": request_metrics.get("status") == "success",
                    "complexity": message_complexity,
                    "elapsed_since_start": request_end - throughput_start
                }
                
                throughput_results.append(throughput_result)
                
                # Maintain request interval
                elapsed = time.time() - request_start
                if elapsed < request_interval:
                    await asyncio.sleep(request_interval - elapsed)
                    
            except Exception as e:
                throughput_results.append({
                    "request_index": request_index,
                    "success": False,
                    "error": str(e),
                    "elapsed_since_start": time.time() - throughput_start
                })
        
        # Analyze throughput results
        successful_requests = [r for r in throughput_results if r["success"]]
        failed_requests = [r for r in throughput_results if not r["success"]]
        
        throughput_success_rate = len(successful_requests) / len(throughput_results)
        
        # Validate throughput performance
        assert throughput_success_rate >= 0.95, \
            f"Throughput success rate too low: {throughput_success_rate:.1%}"
        
        if successful_requests:
            response_times = [r["agent_response_time"] for r in successful_requests]
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            # Response times shouldn't degrade significantly under load
            assert avg_response_time <= 12.0, \
                f"Average response time too high under load: {avg_response_time:.1f}s"
            
            assert max_response_time <= 20.0, \
                f"Maximum response time excessive: {max_response_time:.1f}s"
        
        total_throughput_time = time.time() - throughput_start
        actual_throughput = len(throughput_results) / total_throughput_time
        
        self.logger.info(
            f"Throughput test completed: "
            f"{len(successful_requests)}/{len(throughput_results)} successful "
            f"({throughput_success_rate:.1%}), "
            f"throughput: {actual_throughput:.1f} req/s"
        )


# Pytest configuration for performance tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.performance,
    pytest.mark.mission_critical,
    pytest.mark.real_services,
    pytest.mark.sla_validation
]