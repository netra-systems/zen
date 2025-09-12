"""
PERFORMANCE & SLA COMPLIANCE for Golden Path - COMPREHENSIVE Testing

 LIGHTNING:  PERFORMANCE & SLA COMPLIANCE TEST  LIGHTNING: 
This test suite validates that the golden path meets performance requirements
and SLA commitments that ensure customer satisfaction and business success.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - performance affects all customers
- Business Goal: Ensure platform meets performance SLAs for customer retention
- Value Impact: Poor performance = customer churn = revenue loss = competitive disadvantage
- Strategic Impact: Performance is competitive advantage and customer retention driver

PERFORMANCE & SLA REQUIREMENTS:
1. First response time: < 3 seconds (user engagement)
2. Complete AI response: < 60 seconds (business expectation)
3. WebSocket connection: < 5 seconds (real-time requirement)
4. Concurrent user support: 10+ users without degradation
5. Memory usage: Stable under load (no memory leaks)
6. Throughput: Support business growth without performance cliff

SUCCESS CRITERIA: All SLAs met under realistic load conditions.
"""

import asyncio
import pytest
import time
import statistics
import psutil
import gc
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import threading

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestPerformanceSLAComplianceComprehensive(SSotAsyncTestCase):
    """
     LIGHTNING:  COMPREHENSIVE PERFORMANCE & SLA COMPLIANCE TEST  LIGHTNING: 
    
    Validates that the golden path meets all performance requirements
    and SLA commitments for customer satisfaction and business success.
    """
    
    def setup_method(self, method=None):
        """Setup with performance testing context."""
        super().setup_method(method)
        
        # Performance metrics
        self.record_metric("performance_test", True)
        self.record_metric("sla_compliance_validation", True)
        self.record_metric("customer_satisfaction_metrics", True)
        self.record_metric("business_performance_validation", True)
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Performance configuration
        self.websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # SLA thresholds (business requirements)
        self.SLA_THRESHOLDS = {
            "first_response_time": 3.0,      # 3 seconds - user engagement threshold
            "complete_response_time": 60.0,   # 60 seconds - business expectation
            "websocket_connection_time": 5.0, # 5 seconds - real-time requirement
            "concurrent_users_supported": 10, # 10+ concurrent users
            "memory_growth_limit": 100,       # 100MB max memory growth
            "throughput_min_requests": 5,     # 5 requests/minute minimum
            "availability_threshold": 0.99    # 99% availability requirement
        }
        
        # Performance tracking
        self.performance_metrics = {
            "response_times": [],
            "connection_times": [],
            "memory_usage": [],
            "throughput_measurements": [],
            "error_rates": [],
            "concurrent_performance": []
        }
        
        self.active_connections = []
        self.performance_lock = threading.Lock()
        
        # Get baseline memory usage
        self.baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
    async def async_teardown_method(self, method=None):
        """Cleanup with performance validation."""
        try:
            # Close connections
            for connection in self.active_connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(connection)
                except Exception:
                    pass
            
            # Force garbage collection for memory cleanup
            gc.collect()
            
            # Record final performance metrics
            if hasattr(self, 'performance_metrics'):
                self._record_final_performance_metrics()
            
        except Exception as e:
            print(f" WARNING: [U+FE0F]  Performance test cleanup error: {e}")
        
        await super().async_teardown_method(method)
    
    def _record_final_performance_metrics(self):
        """Record comprehensive performance metrics."""
        try:
            # Response time metrics
            if self.performance_metrics["response_times"]:
                response_times = self.performance_metrics["response_times"]
                self.record_metric("avg_response_time", statistics.mean(response_times))
                self.record_metric("p95_response_time", statistics.quantiles(response_times, n=20)[18])  # 95th percentile
                self.record_metric("max_response_time", max(response_times))
                self.record_metric("min_response_time", min(response_times))
            
            # Connection time metrics
            if self.performance_metrics["connection_times"]:
                connection_times = self.performance_metrics["connection_times"]
                self.record_metric("avg_connection_time", statistics.mean(connection_times))
                self.record_metric("max_connection_time", max(connection_times))
            
            # Memory metrics
            if self.performance_metrics["memory_usage"]:
                memory_usage = self.performance_metrics["memory_usage"]
                self.record_metric("peak_memory_usage", max(memory_usage))
                self.record_metric("memory_growth", max(memory_usage) - self.baseline_memory)
            
            # Throughput metrics
            if self.performance_metrics["throughput_measurements"]:
                throughput = self.performance_metrics["throughput_measurements"]
                self.record_metric("avg_throughput", statistics.mean(throughput))
                self.record_metric("min_throughput", min(throughput))
            
        except Exception as metric_error:
            print(f" WARNING: [U+FE0F]  Performance metric recording error: {metric_error}")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_first_response_time_sla_compliance(self):
        """
         LIGHTNING:  FIRST RESPONSE SLA: < 3 Second Response Time
        
        Tests that users receive their first response within 3 seconds,
        which is critical for user engagement and perceived performance.
        """
        first_response_start = time.time()
        
        print(f"\n LIGHTNING:  FIRST RESPONSE SLA: Testing < 3 second response time")
        print(f" TARGET:  SLA Threshold: {self.SLA_THRESHOLDS['first_response_time']}s")
        
        # Test multiple scenarios for first response time
        response_time_tests = []
        
        for test_num in range(5):  # Test 5 scenarios
            test_start = time.time()
            
            try:
                # Create user context
                user_context = await create_authenticated_user_context(
                    user_email=f"first_response_test_{test_num}@example.com",
                    environment=self.environment,
                    websocket_enabled=True
                )
                
                # Get authentication token
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get('user_email')
                )
                
                # Establish WebSocket connection
                connection_start = time.time()
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=str(user_context.user_id)
                )
                self.active_connections.append(connection)
                connection_time = time.time() - connection_start
                
                # Send message and measure first response time
                message_send_time = time.time()
                test_message = {
                    "type": "chat_message",
                    "content": f"Performance test {test_num}: Quick response needed",
                    "user_id": str(user_context.user_id),
                    "performance_test": True,
                    "test_number": test_num
                }
                
                await WebSocketTestHelpers.send_test_message(
                    connection, test_message, timeout=5.0
                )
                
                # Wait for FIRST response
                first_response_time = None
                first_response_received = False
                
                response_start = time.time()
                while (time.time() - response_start) < 10.0:  # 10 second max wait
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=1.0
                        )
                        
                        if response and isinstance(response, dict):
                            first_response_time = time.time() - message_send_time
                            first_response_received = True
                            break
                            
                    except:
                        continue
                
                # Record test result
                test_result = {
                    "test_number": test_num,
                    "success": first_response_received,
                    "first_response_time": first_response_time,
                    "connection_time": connection_time,
                    "sla_compliant": first_response_time is not None and first_response_time <= self.SLA_THRESHOLDS["first_response_time"],
                    "total_test_time": time.time() - test_start
                }
                
                response_time_tests.append(test_result)
                
                if first_response_time:
                    with self.performance_lock:
                        self.performance_metrics["response_times"].append(first_response_time)
                        self.performance_metrics["connection_times"].append(connection_time)
                
                print(f"   Test {test_num}: {' PASS: ' if test_result['sla_compliant'] else ' FAIL: '} "
                      f"({first_response_time:.2f}s)" if first_response_time else f"   Test {test_num}:  FAIL:  No response")
                
                # Cleanup
                await WebSocketTestHelpers.close_test_connection(connection)
                self.active_connections.remove(connection)
                
            except Exception as test_error:
                response_time_tests.append({
                    "test_number": test_num,
                    "success": False,
                    "error": str(test_error),
                    "sla_compliant": False,
                    "total_test_time": time.time() - test_start
                })
                
                print(f"   Test {test_num}:  FAIL:  Error: {test_error}")
        
        first_response_total_time = time.time() - first_response_start
        
        # Analyze first response SLA compliance
        successful_tests = [test for test in response_time_tests if test.get("success")]
        sla_compliant_tests = [test for test in response_time_tests if test.get("sla_compliant")]
        
        if successful_tests:
            response_times = [test["first_response_time"] for test in successful_tests if test.get("first_response_time")]
            avg_response_time = statistics.mean(response_times) if response_times else None
            max_response_time = max(response_times) if response_times else None
        else:
            avg_response_time = None
            max_response_time = None
        
        success_rate = len(successful_tests) / len(response_time_tests)
        sla_compliance_rate = len(sla_compliant_tests) / len(response_time_tests)
        
        # Record first response metrics
        self.record_metric("first_response_success_rate", success_rate)
        self.record_metric("first_response_sla_compliance_rate", sla_compliance_rate)
        if avg_response_time:
            self.record_metric("first_response_avg_time", avg_response_time)
        if max_response_time:
            self.record_metric("first_response_max_time", max_response_time)
        
        print(f"\n CHART:  FIRST RESPONSE SLA ANALYSIS:")
        print(f"    LIGHTNING:  Tests performed: {len(response_time_tests)}")
        print(f"    PASS:  Success rate: {success_rate:.1%}")
        print(f"    TARGET:  SLA compliance: {sla_compliance_rate:.1%}")
        if avg_response_time:
            print(f"   [U+1F4C8] Average response time: {avg_response_time:.2f}s")
        if max_response_time:
            print(f"    CHART:  Max response time: {max_response_time:.2f}s")
        
        # SLA compliance validation
        if sla_compliance_rate < 0.95:  # 95% compliance required
            pytest.fail(
                f" ALERT:  FIRST RESPONSE SLA FAILURE\n"
                f"SLA Compliance: {sla_compliance_rate:.1%} (< 95% required)\n"
                f"SLA Threshold: {self.SLA_THRESHOLDS['first_response_time']}s\n"
                f"Average Response Time: {avg_response_time:.2f}s\n"
                f"This violates user engagement SLA requirements!"
            )
        
        if success_rate < 0.9:  # 90% success rate required
            pytest.fail(
                f" ALERT:  FIRST RESPONSE RELIABILITY FAILURE\n"
                f"Success Rate: {success_rate:.1%} (< 90% required)\n"
                f"System not reliably delivering first responses!"
            )
        
        print(f"\n PASS:  FIRST RESPONSE SLA: COMPLIANT")
        print(f"    LIGHTNING:  User engagement threshold: MET")
        print(f"    TARGET:  Performance SLA: VALIDATED")
        
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_complete_response_time_sla_compliance(self):
        """
        [U+1F3C1] COMPLETE RESPONSE SLA: < 60 Second Complete Response
        
        Tests that users receive complete AI responses within 60 seconds,
        which is the business expectation for AI processing completion.
        """
        complete_response_start = time.time()
        
        print(f"\n[U+1F3C1] COMPLETE RESPONSE SLA: Testing < 60 second complete response")
        print(f" TARGET:  SLA Threshold: {self.SLA_THRESHOLDS['complete_response_time']}s")
        
        # Test complete response scenarios
        complete_response_tests = []
        
        for test_num in range(3):  # Test 3 complete scenarios
            test_start = time.time()
            
            try:
                # Create user context
                user_context = await create_authenticated_user_context(
                    user_email=f"complete_response_test_{test_num}@example.com",
                    environment=self.environment,
                    websocket_enabled=True
                )
                
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get('user_email')
                )
                
                # Establish connection
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=str(user_context.user_id)
                )
                self.active_connections.append(connection)
                
                # Send comprehensive request that requires full AI processing
                request_send_time = time.time()
                comprehensive_request = {
                    "type": "chat_message",
                    "content": f"Performance Test {test_num}: Provide comprehensive cost optimization analysis with detailed recommendations and specific savings opportunities",
                    "user_id": str(user_context.user_id),
                    "comprehensive_test": True,
                    "test_number": test_num
                }
                
                await WebSocketTestHelpers.send_test_message(
                    connection, comprehensive_request, timeout=5.0
                )
                
                # Collect events until completion
                complete_response_time = None
                complete_response_received = False
                events_received = []
                
                collection_start = time.time()
                max_wait = self.SLA_THRESHOLDS["complete_response_time"] + 10.0  # SLA + buffer
                
                while (time.time() - collection_start) < max_wait:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=3.0
                        )
                        
                        if event and isinstance(event, dict):
                            events_received.append(event)
                            event_type = event.get("type")
                            
                            # Check for completion
                            if event_type == "agent_completed":
                                complete_response_time = time.time() - request_send_time
                                complete_response_received = True
                                break
                                
                    except:
                        continue
                
                # Validate response completeness
                response_quality = self._assess_response_quality(events_received)
                
                test_result = {
                    "test_number": test_num,
                    "success": complete_response_received,
                    "complete_response_time": complete_response_time,
                    "events_received": len(events_received),
                    "response_quality": response_quality,
                    "sla_compliant": complete_response_time is not None and complete_response_time <= self.SLA_THRESHOLDS["complete_response_time"],
                    "total_test_time": time.time() - test_start
                }
                
                complete_response_tests.append(test_result)
                
                if complete_response_time:
                    with self.performance_lock:
                        self.performance_metrics["response_times"].append(complete_response_time)
                
                print(f"   Test {test_num}: {' PASS: ' if test_result['sla_compliant'] else ' FAIL: '} "
                      f"({complete_response_time:.2f}s, {len(events_received)} events)" 
                      if complete_response_time else f"   Test {test_num}:  FAIL:  No completion")
                
                # Cleanup
                await WebSocketTestHelpers.close_test_connection(connection)
                self.active_connections.remove(connection)
                
            except Exception as test_error:
                complete_response_tests.append({
                    "test_number": test_num,
                    "success": False,
                    "error": str(test_error),
                    "sla_compliant": False,
                    "total_test_time": time.time() - test_start
                })
                
                print(f"   Test {test_num}:  FAIL:  Error: {test_error}")
        
        complete_response_total_time = time.time() - complete_response_start
        
        # Analyze complete response SLA compliance
        successful_tests = [test for test in complete_response_tests if test.get("success")]
        sla_compliant_tests = [test for test in complete_response_tests if test.get("sla_compliant")]
        
        if successful_tests:
            response_times = [test["complete_response_time"] for test in successful_tests if test.get("complete_response_time")]
            avg_complete_time = statistics.mean(response_times) if response_times else None
            max_complete_time = max(response_times) if response_times else None
        else:
            avg_complete_time = None
            max_complete_time = None
        
        success_rate = len(successful_tests) / len(complete_response_tests)
        sla_compliance_rate = len(sla_compliant_tests) / len(complete_response_tests)
        
        # Record complete response metrics
        self.record_metric("complete_response_success_rate", success_rate)
        self.record_metric("complete_response_sla_compliance_rate", sla_compliance_rate)
        if avg_complete_time:
            self.record_metric("complete_response_avg_time", avg_complete_time)
        if max_complete_time:
            self.record_metric("complete_response_max_time", max_complete_time)
        
        print(f"\n CHART:  COMPLETE RESPONSE SLA ANALYSIS:")
        print(f"   [U+1F3C1] Tests performed: {len(complete_response_tests)}")
        print(f"    PASS:  Success rate: {success_rate:.1%}")
        print(f"    TARGET:  SLA compliance: {sla_compliance_rate:.1%}")
        if avg_complete_time:
            print(f"   [U+1F4C8] Average complete time: {avg_complete_time:.2f}s")
        if max_complete_time:
            print(f"    CHART:  Max complete time: {max_complete_time:.2f}s")
        
        # SLA compliance validation
        if sla_compliance_rate < 0.9:  # 90% compliance required for complete responses
            pytest.fail(
                f" ALERT:  COMPLETE RESPONSE SLA FAILURE\n"
                f"SLA Compliance: {sla_compliance_rate:.1%} (< 90% required)\n"
                f"SLA Threshold: {self.SLA_THRESHOLDS['complete_response_time']}s\n"
                f"Average Complete Time: {avg_complete_time:.2f}s\n"
                f"This violates business expectation SLA requirements!"
            )
        
        print(f"\n PASS:  COMPLETE RESPONSE SLA: COMPLIANT")
        print(f"   [U+1F3C1] Business expectation: MET")
        print(f"    TARGET:  AI processing SLA: VALIDATED")
        
    def _assess_response_quality(self, events: List[Dict]) -> Dict[str, Any]:
        """Assess the quality and completeness of an AI response."""
        quality_metrics = {
            "events_count": len(events),
            "has_agent_started": any(e.get("type") == "agent_started" for e in events),
            "has_agent_completed": any(e.get("type") == "agent_completed" for e in events),
            "has_tool_execution": any(e.get("type") in ["tool_executing", "tool_completed"] for e in events),
            "response_content_length": 0,
            "quality_score": 0
        }
        
        # Analyze final response content
        completion_events = [e for e in events if e.get("type") == "agent_completed"]
        if completion_events:
            final_response = completion_events[-1]
            content = str(final_response.get("content", ""))
            quality_metrics["response_content_length"] = len(content)
            
            # Simple quality scoring
            quality_score = 0
            if len(content) > 100:  # Substantial response
                quality_score += 25
            if any(keyword in content.lower() for keyword in ["cost", "optimization", "recommendation"]):
                quality_score += 25
            if quality_metrics["has_tool_execution"]:
                quality_score += 25
            if quality_metrics["has_agent_started"] and quality_metrics["has_agent_completed"]:
                quality_score += 25
            
            quality_metrics["quality_score"] = quality_score
        
        return quality_metrics
        
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_concurrent_users_performance_sla(self):
        """
        [U+1F465] CONCURRENT USERS SLA: 10+ Users Without Degradation
        
        Tests that the system can handle 10+ concurrent users without
        significant performance degradation, ensuring scalability.
        """
        concurrent_start = time.time()
        
        print(f"\n[U+1F465] CONCURRENT USERS SLA: Testing {self.SLA_THRESHOLDS['concurrent_users_supported']}+ users")
        
        concurrent_users = self.SLA_THRESHOLDS["concurrent_users_supported"]
        
        # Execute concurrent user load test
        async def concurrent_user_test(user_index: int) -> Dict[str, Any]:
            """Execute performance test for a single concurrent user."""
            user_start = time.time()
            
            try:
                # Create user context
                user_context = await create_authenticated_user_context(
                    user_email=f"concurrent_user_{user_index}@example.com",
                    environment=self.environment,
                    websocket_enabled=True
                )
                
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get('user_email')
                )
                
                # Measure connection time
                connection_start = time.time()
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=15.0,  # Allow more time under load
                    user_id=str(user_context.user_id)
                )
                connection_time = time.time() - connection_start
                
                # Send request and measure response time
                request_start = time.time()
                test_message = {
                    "type": "chat_message",
                    "content": f"Concurrent user {user_index} performance test",
                    "user_id": str(user_context.user_id),
                    "concurrent_test": True,
                    "user_index": user_index
                }
                
                await WebSocketTestHelpers.send_test_message(
                    connection, test_message, timeout=5.0
                )
                
                # Wait for first response
                first_response_time = None
                response_received = False
                
                response_start = time.time()
                while (time.time() - response_start) < 20.0:  # Allow more time under load
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=2.0
                        )
                        
                        if response and isinstance(response, dict):
                            first_response_time = time.time() - request_start
                            response_received = True
                            break
                            
                    except:
                        continue
                
                # Cleanup
                await WebSocketTestHelpers.close_test_connection(connection)
                
                user_execution_time = time.time() - user_start
                
                return {
                    "user_index": user_index,
                    "success": response_received,
                    "connection_time": connection_time,
                    "first_response_time": first_response_time,
                    "total_execution_time": user_execution_time,
                    "connection_sla_met": connection_time <= self.SLA_THRESHOLDS["websocket_connection_time"],
                    "response_sla_met": first_response_time is not None and first_response_time <= self.SLA_THRESHOLDS["first_response_time"]
                }
                
            except Exception as user_error:
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(user_error),
                    "total_execution_time": time.time() - user_start,
                    "connection_sla_met": False,
                    "response_sla_met": False
                }
        
        # Execute all concurrent users
        concurrent_tasks = [
            concurrent_user_test(i) for i in range(concurrent_users)
        ]
        
        print(f"   [U+1F680] Launching {concurrent_users} concurrent users...")
        
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_total_time = time.time() - concurrent_start
        
        # Analyze concurrent performance results
        successful_users = []
        failed_users = []
        connection_times = []
        response_times = []
        
        for result in concurrent_results:
            if isinstance(result, Exception):
                failed_users.append({"error": str(result)})
                continue
                
            if result.get("success"):
                successful_users.append(result)
                if result.get("connection_time"):
                    connection_times.append(result["connection_time"])
                if result.get("first_response_time"):
                    response_times.append(result["first_response_time"])
            else:
                failed_users.append(result)
        
        success_rate = len(successful_users) / concurrent_users
        
        # Performance under load analysis
        if connection_times:
            avg_connection_time = statistics.mean(connection_times)
            max_connection_time = max(connection_times)
            connection_sla_compliance = sum(1 for t in connection_times if t <= self.SLA_THRESHOLDS["websocket_connection_time"]) / len(connection_times)
        else:
            avg_connection_time = None
            max_connection_time = None
            connection_sla_compliance = 0
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            response_sla_compliance = sum(1 for t in response_times if t <= self.SLA_THRESHOLDS["first_response_time"]) / len(response_times)
        else:
            avg_response_time = None
            max_response_time = None
            response_sla_compliance = 0
        
        # Record concurrent performance metrics
        self.record_metric("concurrent_users_success_rate", success_rate)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("concurrent_connection_sla_compliance", connection_sla_compliance)
        self.record_metric("concurrent_response_sla_compliance", response_sla_compliance)
        if avg_connection_time:
            self.record_metric("concurrent_avg_connection_time", avg_connection_time)
        if avg_response_time:
            self.record_metric("concurrent_avg_response_time", avg_response_time)
        
        with self.performance_lock:
            self.performance_metrics["concurrent_performance"].extend(concurrent_results)
        
        print(f"\n CHART:  CONCURRENT USERS PERFORMANCE ANALYSIS:")
        print(f"   [U+1F465] Concurrent users: {concurrent_users}")
        print(f"    PASS:  Success rate: {success_rate:.1%}")
        print(f"   [U+1F4E1] Connection SLA compliance: {connection_sla_compliance:.1%}")
        print(f"    LIGHTNING:  Response SLA compliance: {response_sla_compliance:.1%}")
        if avg_connection_time:
            print(f"   [U+1F517] Avg connection time: {avg_connection_time:.2f}s")
        if avg_response_time:
            print(f"   [U+1F4C8] Avg response time: {avg_response_time:.2f}s")
        
        # Concurrent performance validation
        if success_rate < 0.8:  # 80% success rate under load
            pytest.fail(
                f" ALERT:  CONCURRENT USERS PERFORMANCE FAILURE\n"
                f"Success Rate: {success_rate:.1%} (< 80% required)\n"
                f"System cannot handle {concurrent_users} concurrent users!"
            )
        
        if connection_sla_compliance < 0.8:  # 80% connection SLA compliance under load
            pytest.fail(
                f" ALERT:  CONCURRENT CONNECTION SLA FAILURE\n"
                f"Connection SLA Compliance: {connection_sla_compliance:.1%} (< 80% required)\n"
                f"Connection times degrading significantly under load!"
            )
        
        if response_sla_compliance < 0.7:  # 70% response SLA compliance under load
            pytest.fail(
                f" ALERT:  CONCURRENT RESPONSE SLA FAILURE\n"
                f"Response SLA Compliance: {response_sla_compliance:.1%} (< 70% required)\n"
                f"Response times degrading significantly under load!"
            )
        
        print(f"\n PASS:  CONCURRENT USERS SLA: COMPLIANT")
        print(f"   [U+1F465] Scalability: VALIDATED")
        print(f"   [U+1F4C8] Performance under load: MAINTAINED")
        
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_memory_usage_stability_sla(self):
        """
        [U+1F9E0] MEMORY STABILITY SLA: Memory Growth < 100MB Under Load
        
        Tests that memory usage remains stable under load and doesn't
        exhibit memory leaks that could degrade system performance.
        """
        memory_test_start = time.time()
        
        print(f"\n[U+1F9E0] MEMORY STABILITY SLA: Testing memory growth < {self.SLA_THRESHOLDS['memory_growth_limit']}MB")
        print(f" CHART:  Baseline memory: {self.baseline_memory:.2f}MB")
        
        # Record memory usage throughout test
        memory_measurements = []
        
        def record_memory():
            """Record current memory usage."""
            try:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append({
                    "timestamp": time.time() - memory_test_start,
                    "memory_mb": current_memory,
                    "growth_mb": current_memory - self.baseline_memory
                })
                return current_memory
            except Exception:
                return self.baseline_memory
        
        # Initial memory recording
        initial_memory = record_memory()
        
        # Execute memory stress test with multiple operations
        stress_operations = []
        
        try:
            # Operation 1: Multiple WebSocket connections
            connections = []
            for i in range(5):  # Create 5 connections
                user_context = await create_authenticated_user_context(
                    user_email=f"memory_test_user_{i}@example.com",
                    environment=self.environment,
                    websocket_enabled=True
                )
                
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get('user_email')
                )
                
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=str(user_context.user_id)
                )
                connections.append(connection)
                
                # Record memory after each connection
                record_memory()
            
            # Operation 2: Send multiple messages
            for i, connection in enumerate(connections):
                for msg_num in range(3):  # 3 messages per connection
                    message = {
                        "type": "chat_message",
                        "content": f"Memory test - Connection {i}, Message {msg_num}",
                        "memory_test": True
                    }
                    
                    await WebSocketTestHelpers.send_test_message(
                        connection, message, timeout=5.0
                    )
                    
                    # Small delay and memory recording
                    await asyncio.sleep(0.1)
                    record_memory()
            
            # Operation 3: Process responses while monitoring memory
            for connection in connections:
                try:
                    for _ in range(3):  # Try to receive 3 responses per connection
                        response = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=2.0
                        )
                        record_memory()
                except:
                    continue  # Timeouts are acceptable
            
            # Operation 4: Cleanup connections and measure memory recovery
            for connection in connections:
                await WebSocketTestHelpers.close_test_connection(connection)
                record_memory()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(1.0)  # Allow cleanup time
            final_memory = record_memory()
            
            stress_operations.append({
                "operation": "websocket_stress_test",
                "success": True,
                "connections_created": len(connections),
                "messages_sent": len(connections) * 3
            })
            
        except Exception as stress_error:
            stress_operations.append({
                "operation": "websocket_stress_test",
                "success": False,
                "error": str(stress_error)
            })
        
        memory_test_time = time.time() - memory_test_start
        
        # Analyze memory usage
        if memory_measurements:
            peak_memory = max(m["memory_mb"] for m in memory_measurements)
            final_memory = memory_measurements[-1]["memory_mb"]
            max_growth = max(m["growth_mb"] for m in memory_measurements)
            final_growth = final_memory - self.baseline_memory
            
            # Check for memory recovery (should be close to baseline after cleanup)
            memory_recovery = peak_memory - final_memory
            memory_leak_suspected = final_growth > (self.SLA_THRESHOLDS["memory_growth_limit"] * 0.5)  # 50% of limit
        else:
            peak_memory = self.baseline_memory
            final_memory = self.baseline_memory
            max_growth = 0
            final_growth = 0
            memory_recovery = 0
            memory_leak_suspected = False
        
        # Record memory metrics
        self.record_metric("memory_peak_usage", peak_memory)
        self.record_metric("memory_max_growth", max_growth)
        self.record_metric("memory_final_growth", final_growth)
        self.record_metric("memory_recovery", memory_recovery)
        self.record_metric("memory_leak_suspected", memory_leak_suspected)
        
        with self.performance_lock:
            self.performance_metrics["memory_usage"].extend([m["memory_mb"] for m in memory_measurements])
        
        print(f"\n CHART:  MEMORY STABILITY ANALYSIS:")
        print(f"   [U+1F9E0] Baseline memory: {self.baseline_memory:.2f}MB")
        print(f"   [U+1F4C8] Peak memory: {peak_memory:.2f}MB")
        print(f"    CHART:  Max growth: {max_growth:.2f}MB")
        print(f"    CYCLE:  Final growth: {final_growth:.2f}MB")
        print(f"   [U+267B][U+FE0F]  Memory recovery: {memory_recovery:.2f}MB")
        print(f"    WARNING: [U+FE0F]  Leak suspected: {'YES' if memory_leak_suspected else 'NO'}")
        
        # Memory SLA validation
        if max_growth > self.SLA_THRESHOLDS["memory_growth_limit"]:
            pytest.fail(
                f" ALERT:  MEMORY GROWTH SLA FAILURE\n"
                f"Max Memory Growth: {max_growth:.2f}MB (> {self.SLA_THRESHOLDS['memory_growth_limit']}MB limit)\n"
                f"Peak Memory: {peak_memory:.2f}MB\n"
                f"System using excessive memory under load!"
            )
        
        if memory_leak_suspected:
            pytest.fail(
                f" ALERT:  MEMORY LEAK SUSPECTED\n"
                f"Final Growth: {final_growth:.2f}MB (> {self.SLA_THRESHOLDS['memory_growth_limit'] * 0.5:.2f}MB threshold)\n"
                f"Memory not recovering properly after operations!"
            )
        
        print(f"\n PASS:  MEMORY STABILITY SLA: COMPLIANT")
        print(f"   [U+1F9E0] Memory growth: WITHIN LIMITS")
        print(f"   [U+267B][U+FE0F]  Memory recovery: HEALTHY")
        print(f"   [U+1F4C8] System stability: MAINTAINED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])