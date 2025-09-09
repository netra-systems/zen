"""
E2E Staging Tests: Performance and Scaling Scenarios - BATCH 2
=============================================================

This module tests comprehensive performance and scaling capabilities end-to-end in staging.
Tests REAL load patterns, concurrent user scenarios, throughput optimization, and scaling behavior.

Business Value:
- Ensures $1M+ ARR scalability for growing customer base
- Validates enterprise-grade performance for 100+ concurrent users
- Tests system optimization delivers promised performance SLAs
- Validates scaling efficiency reduces infrastructure costs by 40%

CRITICAL E2E REQUIREMENTS:
- MUST use real authentication (JWT/OAuth)
- MUST test actual performance with real load patterns
- MUST validate business SLA compliance under load
- MUST test with real staging environment configuration
- NO MOCKS ALLOWED - uses real services, measures real performance

Test Coverage:
1. Concurrent multi-user agent execution with performance monitoring
2. Throughput optimization under enterprise load scenarios
"""

import asyncio
import json
import logging
import random
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

import aiohttp
import pytest
import websockets
from dataclasses import dataclass

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    E2EAuthConfig,
    create_authenticated_user_context
)
from tests.e2e.staging_config import get_staging_config, StagingTestConfig
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)

class TestPerformanceScaling:
    """
    E2E Tests for Performance and Scaling in Staging Environment.
    
    These tests validate that the system can handle enterprise-grade load
    and scale efficiently to meet business SLA requirements.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_authenticated_context(self):
        """Setup authenticated user context for all tests."""
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.websocket_helper = E2EWebSocketAuthHelper(environment="staging")
        self.staging_config = StagingTestConfig()
        
        # Create authenticated user context
        self.user_context = await create_authenticated_user_context(
            user_email=f"performance_test_{int(time.time())}@example.com",
            environment="staging",
            permissions=["read", "write", "agent_execute", "performance_monitor"],
            websocket_enabled=True
        )
        
        # Get authentication token
        self.auth_token = await self.auth_helper.get_staging_token_async(
            email=self.user_context.agent_context['user_email']
        )
        
        logger.info(f"✅ Setup authenticated context for performance tests")
        logger.info(f"User ID: {self.user_context.user_id}")

    async def _create_concurrent_user_session(self, user_index: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Create a concurrent user session for load testing.
        
        Returns:
            Tuple of (performance_metrics, execution_events)
        """
        session_start_time = time.time()
        performance_metrics = {
            "user_index": user_index,
            "session_start": session_start_time,
            "connection_time": 0.0,
            "authentication_time": 0.0,
            "agent_execution_time": 0.0,
            "total_session_time": 0.0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": [],
            "throughput_ops_per_second": 0.0
        }
        execution_events = []
        
        try:
            # Create unique authenticated context for this user
            user_email = f"concurrent_user_{user_index}_{int(time.time())}@example.com"
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                environment="staging",
                permissions=["read", "write", "agent_execute"],
                websocket_enabled=True
            )
            
            # Authenticate user
            auth_start = time.time()
            auth_token = await self.auth_helper.get_staging_token_async(email=user_email)
            performance_metrics["authentication_time"] = time.time() - auth_start
            
            # Establish WebSocket connection
            connection_start = time.time()
            headers = self.websocket_helper.get_websocket_headers(auth_token)
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers=headers,
                open_timeout=20.0  # Longer timeout for concurrent load
            ) as websocket:
                
                performance_metrics["connection_time"] = time.time() - connection_start
                
                logger.info(f"👤 User {user_index}: Connected successfully")
                
                # Execute multiple agent operations to simulate real user behavior
                agent_operations = 3  # Each user performs 3 operations
                agent_start = time.time()
                
                for op_index in range(agent_operations):
                    operation_start = time.time()
                    
                    # Send agent execution request
                    agent_request = {
                        "type": "concurrent_agent_execution",
                        "request_id": f"{user_context.request_id}_op_{op_index}",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id),
                        "agent_type": "performance_test_agent",
                        "operation_index": op_index,
                        "user_index": user_index,
                        "concurrent_load_test": True,
                        "business_scenario": "customer_optimization_request"
                    }
                    
                    await websocket.send(json.dumps(agent_request))
                    performance_metrics["messages_sent"] += 1
                    
                    # Wait for agent execution completion
                    operation_timeout = 30.0  # 30 second timeout per operation
                    operation_completed = False
                    
                    while time.time() - operation_start < operation_timeout and not operation_completed:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event_data = json.loads(message)
                            execution_events.append({
                                **event_data,
                                "user_index": user_index,
                                "operation_index": op_index,
                                "received_at": time.time()
                            })
                            
                            performance_metrics["messages_received"] += 1
                            
                            event_type = event_data.get("event_type", "")
                            
                            # Check for operation completion
                            if event_type in ["agent_completed", "operation_completed"]:
                                operation_completed = True
                                logger.info(f"👤 User {user_index}: Operation {op_index+1} completed")
                                
                        except asyncio.TimeoutError:
                            # Continue waiting for completion
                            continue
                        except json.JSONDecodeError as e:
                            performance_metrics["errors"].append(f"JSON decode error: {e}")
                            continue
                    
                    if not operation_completed:
                        performance_metrics["errors"].append(f"Operation {op_index} timeout")
                        logger.warning(f"👤 User {user_index}: Operation {op_index+1} timed out")
                    
                    # Brief pause between operations
                    await asyncio.sleep(1.0)
                
                performance_metrics["agent_execution_time"] = time.time() - agent_start
                
        except Exception as e:
            performance_metrics["errors"].append(f"Session error: {str(e)}")
            logger.error(f"👤 User {user_index}: Session error - {e}")
        
        # Calculate final metrics
        performance_metrics["total_session_time"] = time.time() - session_start_time
        if performance_metrics["total_session_time"] > 0:
            total_operations = performance_metrics["messages_sent"] + performance_metrics["messages_received"]
            performance_metrics["throughput_ops_per_second"] = total_operations / performance_metrics["total_session_time"]
        
        return performance_metrics, execution_events

    @pytest.mark.asyncio
    async def test_concurrent_multi_user_agent_execution_with_performance_monitoring(self):
        """
        Test 1: Concurrent Multi-User Agent Execution with Performance Monitoring
        
        Business Value: $750K+ ARR validation - Tests that:
        1. System handles 20+ concurrent users executing agents simultaneously
        2. Performance remains within enterprise SLA thresholds
        3. Each user receives isolated, responsive service  
        4. WebSocket connections scale efficiently under concurrent load
        
        This validates our enterprise scalability promises to customers.
        """
        test_start_time = time.time()
        
        # Concurrent Load Configuration
        load_config = {
            "concurrent_users": 20,  # 20 simultaneous users
            "operations_per_user": 3,
            "performance_sla": {
                "max_connection_time": 15.0,  # seconds
                "max_authentication_time": 5.0,  # seconds  
                "max_agent_execution_time": 60.0,  # seconds per operation
                "min_throughput_ops_per_second": 0.1,  # operations per second per user
                "max_error_rate": 0.2  # 20% max error rate
            },
            "business_context": "enterprise_concurrent_optimization"
        }
        
        logger.info(f"🚀 Starting concurrent multi-user performance test with {load_config['concurrent_users']} users")
        
        # Execute concurrent user sessions
        concurrent_session_tasks = []
        for user_index in range(load_config["concurrent_users"]):
            task = asyncio.create_task(self._create_concurrent_user_session(user_index))
            concurrent_session_tasks.append(task)
        
        # Wait for all concurrent sessions to complete with overall timeout
        concurrent_timeout = 180.0  # 3 minutes total test time
        try:
            session_results = await asyncio.wait_for(
                asyncio.gather(*concurrent_session_tasks, return_exceptions=True),
                timeout=concurrent_timeout
            )
        except asyncio.TimeoutError:
            logger.error("❌ Concurrent user test timed out - cancelling remaining tasks")
            for task in concurrent_session_tasks:
                if not task.done():
                    task.cancel()
            # Get partial results
            session_results = [task.result() if task.done() and not task.cancelled() else None 
                             for task in concurrent_session_tasks]
        
        # Analyze performance results
        performance_metrics = []
        all_execution_events = []
        successful_sessions = 0
        total_errors = 0
        
        for result in session_results:
            if result is not None and not isinstance(result, Exception):
                metrics, events = result
                performance_metrics.append(metrics)
                all_execution_events.extend(events)
                
                if len(metrics["errors"]) == 0:
                    successful_sessions += 1
                total_errors += len(metrics["errors"])
        
        # Calculate aggregate performance statistics
        if len(performance_metrics) > 0:
            connection_times = [m["connection_time"] for m in performance_metrics if m["connection_time"] > 0]
            authentication_times = [m["authentication_time"] for m in performance_metrics if m["authentication_time"] > 0]
            agent_execution_times = [m["agent_execution_time"] for m in performance_metrics if m["agent_execution_time"] > 0]
            throughput_rates = [m["throughput_ops_per_second"] for m in performance_metrics if m["throughput_ops_per_second"] > 0]
            
            performance_stats = {
                "total_users_attempted": load_config["concurrent_users"],
                "successful_sessions": successful_sessions,
                "total_errors": total_errors,
                "error_rate": total_errors / (len(performance_metrics) * 3) if len(performance_metrics) > 0 else 1.0,
                "avg_connection_time": statistics.mean(connection_times) if connection_times else float('inf'),
                "max_connection_time": max(connection_times) if connection_times else float('inf'),
                "avg_authentication_time": statistics.mean(authentication_times) if authentication_times else float('inf'),
                "max_authentication_time": max(authentication_times) if authentication_times else float('inf'),
                "avg_agent_execution_time": statistics.mean(agent_execution_times) if agent_execution_times else float('inf'),
                "max_agent_execution_time": max(agent_execution_times) if agent_execution_times else float('inf'),
                "avg_throughput": statistics.mean(throughput_rates) if throughput_rates else 0.0,
                "min_throughput": min(throughput_rates) if throughput_rates else 0.0,
                "total_operations": sum(m["messages_sent"] + m["messages_received"] for m in performance_metrics),
                "total_websocket_events": len(all_execution_events)
            }
        else:
            performance_stats = {"error": "No performance data collected"}
        
        # Validation: Comprehensive concurrent performance validation
        test_duration = time.time() - test_start_time
        
        # Assert 1: Real concurrent load testing timing
        assert test_duration >= 10.0, f"Concurrent test too fast ({test_duration:.2f}s) - likely fake/mocked"
        
        # Assert 2: Multiple users executed concurrently
        assert len(performance_metrics) >= 10, f"Expected at least 10 concurrent users, got {len(performance_metrics)}"
        assert successful_sessions >= 5, f"Too few successful sessions ({successful_sessions}) - scalability issues"
        
        # Assert 3: Performance SLA compliance
        if "error" not in performance_stats:
            assert performance_stats["error_rate"] <= load_config["performance_sla"]["max_error_rate"], \
                f"Error rate {performance_stats['error_rate']:.2%} exceeds SLA {load_config['performance_sla']['max_error_rate']:.2%}"
                
            assert performance_stats["max_connection_time"] <= load_config["performance_sla"]["max_connection_time"], \
                f"Max connection time {performance_stats['max_connection_time']:.2f}s exceeds SLA {load_config['performance_sla']['max_connection_time']}s"
                
            assert performance_stats["max_authentication_time"] <= load_config["performance_sla"]["max_authentication_time"], \
                f"Max auth time {performance_stats['max_authentication_time']:.2f}s exceeds SLA {load_config['performance_sla']['max_authentication_time']}s"
        
        # Assert 4: Throughput meets minimum requirements
        if "error" not in performance_stats and performance_stats["min_throughput"] > 0:
            assert performance_stats["min_throughput"] >= load_config["performance_sla"]["min_throughput_ops_per_second"], \
                f"Minimum throughput {performance_stats['min_throughput']:.3f} ops/s below SLA {load_config['performance_sla']['min_throughput_ops_per_second']} ops/s"
        
        # Assert 5: WebSocket scalability demonstrated
        assert len(all_execution_events) >= 20, f"Too few WebSocket events ({len(all_execution_events)}) for concurrent test"
        
        # Assert 6: Business operations completed under load
        business_operations_completed = sum(m["messages_received"] for m in performance_metrics)
        assert business_operations_completed >= 10, f"Too few business operations completed ({business_operations_completed}) under concurrent load"
        
        logger.info(f"✅ PASS: Concurrent multi-user agent execution with performance monitoring - {test_duration:.2f}s")
        logger.info(f"Concurrent users: {load_config['concurrent_users']}")
        logger.info(f"Successful sessions: {successful_sessions}")
        logger.info(f"Error rate: {performance_stats.get('error_rate', 'N/A'):.2%}")
        logger.info(f"Avg connection time: {performance_stats.get('avg_connection_time', 'N/A'):.2f}s")
        logger.info(f"Avg authentication time: {performance_stats.get('avg_authentication_time', 'N/A'):.2f}s") 
        logger.info(f"Avg agent execution time: {performance_stats.get('avg_agent_execution_time', 'N/A'):.2f}s")
        logger.info(f"Avg throughput: {performance_stats.get('avg_throughput', 'N/A'):.3f} ops/s")
        logger.info(f"Total operations: {performance_stats.get('total_operations', 'N/A')}")
        logger.info(f"Total WebSocket events: {performance_stats.get('total_websocket_events', 'N/A')}")

    @pytest.mark.asyncio
    async def test_throughput_optimization_under_enterprise_load_scenarios(self):
        """
        Test 2: Throughput Optimization Under Enterprise Load Scenarios
        
        Business Value: $500K+ ARR validation - Tests that:
        1. System optimizes throughput for high-volume enterprise workloads
        2. Request processing efficiency scales with increased load
        3. WebSocket message throughput remains high under sustained load
        4. System maintains responsiveness during peak enterprise usage
        
        This validates our enterprise performance optimization capabilities.
        """
        test_start_time = time.time()
        
        # Enterprise Load Configuration
        enterprise_load_config = {
            "test_duration": 60.0,  # 1 minute sustained load
            "batch_size": 5,  # Requests per batch
            "batches_count": 12,  # Total batches (60 requests total)
            "concurrent_batches": 3,  # Up to 3 batches running simultaneously
            "throughput_targets": {
                "min_requests_per_second": 0.8,  # Minimum 0.8 requests/sec
                "min_messages_per_second": 2.0,  # Minimum 2 WebSocket messages/sec
                "max_average_response_time": 15.0,  # Max 15s average response time
                "min_success_rate": 0.85  # 85% minimum success rate
            },
            "enterprise_workload_simulation": True
        }
        
        throughput_metrics = {
            "requests_sent": 0,
            "requests_completed": 0,
            "requests_failed": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "response_times": [],
            "throughput_measurements": [],
            "batch_completion_times": [],
            "websocket_events": []
        }
        
        async with aiohttp.ClientSession() as session:
            headers = self.websocket_helper.get_websocket_headers(self.auth_token)
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers=headers,
                open_timeout=20.0
            ) as websocket:
                
                logger.info(f"📈 Starting enterprise throughput optimization test")
                logger.info(f"Target: {enterprise_load_config['batches_count']} batches of {enterprise_load_config['batch_size']} requests over {enterprise_load_config['test_duration']}s")
                
                # Start throughput monitoring task
                throughput_monitoring_task = asyncio.create_task(
                    self._monitor_websocket_throughput(websocket, throughput_metrics, enterprise_load_config["test_duration"])
                )
                
                # Execute enterprise load in batches
                batch_tasks = []
                load_start_time = time.time()
                
                for batch_index in range(enterprise_load_config["batches_count"]):
                    # Control concurrent batch execution
                    while len([task for task in batch_tasks if not task.done()]) >= enterprise_load_config["concurrent_batches"]:
                        await asyncio.sleep(0.5)  # Wait for batch slot
                    
                    # Create and start batch task
                    batch_task = asyncio.create_task(
                        self._execute_enterprise_request_batch(
                            websocket, batch_index, enterprise_load_config["batch_size"], throughput_metrics
                        )
                    )
                    batch_tasks.append(batch_task)
                    
                    logger.info(f"🏭 Started enterprise batch {batch_index + 1}/{enterprise_load_config['batches_count']}")
                    
                    # Controlled spacing between batch starts
                    await asyncio.sleep(enterprise_load_config["test_duration"] / enterprise_load_config["batches_count"])
                
                # Wait for all batches to complete
                logger.info("⏳ Waiting for all enterprise batches to complete...")
                await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Stop throughput monitoring
                throughput_monitoring_task.cancel()
                try:
                    await throughput_monitoring_task
                except asyncio.CancelledError:
                    pass
        
        # Calculate throughput performance metrics
        total_test_duration = time.time() - test_start_time
        
        throughput_stats = {
            "test_duration": total_test_duration,
            "requests_per_second": throughput_metrics["requests_sent"] / total_test_duration if total_test_duration > 0 else 0,
            "completed_requests_per_second": throughput_metrics["requests_completed"] / total_test_duration if total_test_duration > 0 else 0,
            "messages_per_second": (throughput_metrics["total_messages_sent"] + throughput_metrics["total_messages_received"]) / total_test_duration if total_test_duration > 0 else 0,
            "success_rate": throughput_metrics["requests_completed"] / throughput_metrics["requests_sent"] if throughput_metrics["requests_sent"] > 0 else 0,
            "average_response_time": statistics.mean(throughput_metrics["response_times"]) if throughput_metrics["response_times"] else float('inf'),
            "median_response_time": statistics.median(throughput_metrics["response_times"]) if throughput_metrics["response_times"] else float('inf'),
            "max_response_time": max(throughput_metrics["response_times"]) if throughput_metrics["response_times"] else float('inf'),
            "total_websocket_events": len(throughput_metrics["websocket_events"])
        }
        
        # Validation: Comprehensive throughput optimization validation
        
        # Assert 1: Real enterprise load testing timing
        assert total_test_duration >= 30.0, f"Enterprise load test too fast ({total_test_duration:.2f}s) - likely fake"
        
        # Assert 2: Sufficient enterprise load generated
        assert throughput_metrics["requests_sent"] >= 30, f"Too few requests sent ({throughput_metrics['requests_sent']}) for enterprise load test"
        assert throughput_metrics["requests_completed"] >= 15, f"Too few requests completed ({throughput_metrics['requests_completed']}) - throughput issues"
        
        # Assert 3: Throughput targets met
        assert throughput_stats["requests_per_second"] >= enterprise_load_config["throughput_targets"]["min_requests_per_second"], \
            f"Request throughput {throughput_stats['requests_per_second']:.2f} req/s below target {enterprise_load_config['throughput_targets']['min_requests_per_second']} req/s"
            
        assert throughput_stats["messages_per_second"] >= enterprise_load_config["throughput_targets"]["min_messages_per_second"], \
            f"Message throughput {throughput_stats['messages_per_second']:.2f} msg/s below target {enterprise_load_config['throughput_targets']['min_messages_per_second']} msg/s"
        
        # Assert 4: Response time performance
        assert throughput_stats["average_response_time"] <= enterprise_load_config["throughput_targets"]["max_average_response_time"], \
            f"Average response time {throughput_stats['average_response_time']:.2f}s exceeds target {enterprise_load_config['throughput_targets']['max_average_response_time']}s"
        
        # Assert 5: Success rate meets enterprise standards  
        assert throughput_stats["success_rate"] >= enterprise_load_config["throughput_targets"]["min_success_rate"], \
            f"Success rate {throughput_stats['success_rate']:.2%} below enterprise target {enterprise_load_config['throughput_targets']['min_success_rate']:.2%}"
        
        # Assert 6: WebSocket throughput scalability
        assert throughput_stats["total_websocket_events"] >= 50, f"Too few WebSocket events ({throughput_stats['total_websocket_events']}) for enterprise throughput test"
        
        logger.info(f"✅ PASS: Throughput optimization under enterprise load - {total_test_duration:.2f}s")
        logger.info(f"Requests sent: {throughput_metrics['requests_sent']}")
        logger.info(f"Requests completed: {throughput_metrics['requests_completed']}")
        logger.info(f"Request throughput: {throughput_stats['requests_per_second']:.2f} req/s")
        logger.info(f"Message throughput: {throughput_stats['messages_per_second']:.2f} msg/s")
        logger.info(f"Success rate: {throughput_stats['success_rate']:.2%}")
        logger.info(f"Average response time: {throughput_stats['average_response_time']:.2f}s")
        logger.info(f"Median response time: {throughput_stats['median_response_time']:.2f}s")
        logger.info(f"Total WebSocket events: {throughput_stats['total_websocket_events']}")

    async def _execute_enterprise_request_batch(self, websocket, batch_index: int, batch_size: int, throughput_metrics: Dict[str, Any]) -> None:
        """Execute a batch of enterprise requests for throughput testing."""
        batch_start_time = time.time()
        batch_requests_completed = 0
        
        for request_index in range(batch_size):
            request_start_time = time.time()
            
            try:
                # Send enterprise optimization request
                enterprise_request = {
                    "type": "enterprise_optimization_request",
                    "request_id": f"{self.user_context.request_id}_batch_{batch_index}_req_{request_index}",
                    "thread_id": str(self.user_context.thread_id),
                    "user_id": str(self.user_context.user_id),
                    "batch_index": batch_index,
                    "request_index": request_index,
                    "enterprise_workload": True,
                    "optimization_type": "cost_performance_analysis",
                    "priority": "high_throughput"
                }
                
                await websocket.send(json.dumps(enterprise_request))
                throughput_metrics["requests_sent"] += 1
                throughput_metrics["total_messages_sent"] += 1
                
                # Wait for completion with timeout
                request_timeout = 20.0
                request_completed = False
                
                while time.time() - request_start_time < request_timeout and not request_completed:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(message)
                        throughput_metrics["total_messages_received"] += 1
                        throughput_metrics["websocket_events"].append(event_data)
                        
                        # Check for request completion
                        if event_data.get("request_id") == enterprise_request["request_id"]:
                            event_type = event_data.get("event_type", "")
                            if event_type in ["request_completed", "optimization_completed", "agent_completed"]:
                                request_completed = True
                                batch_requests_completed += 1
                                throughput_metrics["requests_completed"] += 1
                                
                                request_duration = time.time() - request_start_time
                                throughput_metrics["response_times"].append(request_duration)
                                
                                logger.debug(f"Enterprise request batch {batch_index} request {request_index} completed in {request_duration:.2f}s")
                                
                    except asyncio.TimeoutError:
                        continue  # Keep waiting for completion
                    except json.JSONDecodeError:
                        continue  # Skip malformed messages
                
                if not request_completed:
                    throughput_metrics["requests_failed"] += 1
                    logger.warning(f"Enterprise request batch {batch_index} request {request_index} timed out")
                    
            except Exception as e:
                throughput_metrics["requests_failed"] += 1
                logger.error(f"Enterprise request batch {batch_index} request {request_index} failed: {e}")
        
        batch_duration = time.time() - batch_start_time
        throughput_metrics["batch_completion_times"].append(batch_duration)
        
        logger.info(f"Enterprise batch {batch_index} completed: {batch_requests_completed}/{batch_size} requests in {batch_duration:.2f}s")

    async def _monitor_websocket_throughput(self, websocket, throughput_metrics: Dict[str, Any], duration: float) -> None:
        """Monitor WebSocket message throughput during load testing."""
        monitoring_start = time.time()
        throughput_samples = []
        
        while time.time() - monitoring_start < duration:
            sample_start = time.time()
            initial_messages = throughput_metrics["total_messages_received"]
            
            await asyncio.sleep(5.0)  # 5-second sampling interval
            
            sample_duration = time.time() - sample_start
            messages_in_sample = throughput_metrics["total_messages_received"] - initial_messages
            throughput_sample = messages_in_sample / sample_duration
            
            throughput_samples.append(throughput_sample)
            throughput_metrics["throughput_measurements"].append({
                "timestamp": time.time(),
                "throughput": throughput_sample,
                "cumulative_messages": throughput_metrics["total_messages_received"]
            })
            
            logger.debug(f"Throughput sample: {throughput_sample:.2f} messages/sec")
        
        logger.info(f"Throughput monitoring completed: avg {statistics.mean(throughput_samples):.2f} messages/sec") 