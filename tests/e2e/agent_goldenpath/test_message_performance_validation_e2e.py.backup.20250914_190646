"""
E2E Tests for Message Processing Performance Validation - Golden Path SLA Compliance

MISSION CRITICAL: Tests message processing performance and SLA compliance to validate
that the Golden Path agent workflow meets enterprise performance requirements.
These tests ensure system can handle production loads with acceptable response times.

Business Value Justification (BVJ):
- Segment: Enterprise Users (Performance SLA Requirements)
- Business Goal: Platform Reliability & Performance through SLA Compliance
- Value Impact: Validates performance standards critical for enterprise contracts and user satisfaction
- Strategic Impact: Poor performance = SLA violations = enterprise churn = $500K+ ARR loss

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- PERFORMANCE BENCHMARKING: Measure actual response times, throughput, and resource usage
- SLA VALIDATION: Test against realistic enterprise performance requirements
- LOAD TESTING: Validate performance under various load conditions
- BUSINESS CONTINUITY: Ensure performance degrades gracefully under stress

CRITICAL: These tests must measure actual performance with real timing validation.
No mocking of performance characteristics or skipping time measurements.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - Gap Area 4
Coverage Target: Message processing performance validation (identified gap)
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import statistics
from concurrent.futures import ThreadPoolExecutor

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.performance_validation
@pytest.mark.mission_critical
class TestMessagePerformanceValidationE2E(SSotAsyncTestCase):
    """
    E2E tests for validating message processing performance in staging GCP.

    Tests performance SLAs, response times, throughput, and system
    behavior under various load conditions.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment for performance testing."""

        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)

        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available")

        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")

        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper(
            base_url=cls.staging_config.urls.websocket_url,
            environment="staging"
        )

        # Define enterprise SLA requirements
        cls.ENTERPRISE_SLAS = {
            "simple_query_response_time": 15.0,  # seconds
            "complex_analysis_response_time": 90.0,  # seconds
            "first_event_latency": 5.0,  # seconds
            "event_delivery_reliability": 0.95,  # 95% event delivery
            "concurrent_user_degradation": 1.5,  # max 50% degradation under load
            "system_availability": 0.99  # 99% success rate
        }

        # Define the 5 critical events per CLAUDE.md
        cls.CRITICAL_EVENTS = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        cls.logger.info(f"Message performance validation E2E tests initialized for staging")

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Generate test-specific context
        self.performance_test_session = f"perf_test_{int(time.time())}"
        self.thread_id = f"perf_test_{self.performance_test_session}"
        self.run_id = f"run_{self.thread_id}"

        # Create JWT token for performance testing
        self.test_user_id = f"perf_test_user_{int(time.time())}"
        self.test_user_email = f"perf_test_{int(time.time())}@netra-testing.ai"

        self.access_token = self.__class__.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            exp_minutes=60
        )

        self.logger.info(f"Performance test setup - session: {self.performance_test_session}")

    async def _establish_websocket_connection(self, headers_override: Dict[str, str] = None) -> websockets.ServerConnection:
        """Establish WebSocket connection for performance testing."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False  # Staging environment
        ssl_context.verify_mode = ssl.CERT_NONE

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Environment": "staging",
            "X-Test-Suite": "message-performance-validation",
            "X-Session-Id": self.performance_test_session
        }

        if headers_override:
            headers.update(headers_override)

        websocket = await asyncio.wait_for(
            websockets.connect(
                self.__class__.staging_config.urls.websocket_url,
                additional_headers=headers,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            ),
            timeout=20.0
        )

        return websocket

    async def _measure_message_performance(self, agent_type: str, message: str,
                                         expected_complexity: str = "medium",
                                         timeout: float = 120.0) -> Dict[str, Any]:
        """Measure comprehensive message processing performance."""
        performance_metrics = {
            "start_time": time.time(),
            "connection_time": 0,
            "first_event_time": None,
            "agent_started_time": None,
            "agent_completed_time": None,
            "total_time": 0,
            "events": [],
            "event_timestamps": [],
            "critical_events_received": set(),
            "event_gaps": [],
            "success": False,
            "response_content": "",
            "error": None
        }

        try:
            # Measure connection establishment time
            connection_start = time.time()
            websocket = await self._establish_websocket_connection({
                "X-Performance-Test": "true",
                "X-Expected-Complexity": expected_complexity
            })
            performance_metrics["connection_time"] = time.time() - connection_start

            # Send request and start performance monitoring
            request_message = {
                "type": "agent_request",
                "agent": agent_type,
                "message": message,
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.test_user_id,
                "context": {
                    "performance_test": True,
                    "expected_complexity": expected_complexity,
                    "sla_validation": True
                }
            }

            message_sent_time = time.time()
            await websocket.send(json.dumps(request_message))

            # Collect events with precise timing
            last_event_time = message_sent_time

            while time.time() - message_sent_time < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event_received_time = time.time()
                    event = json.loads(event_data)

                    performance_metrics["events"].append(event)
                    performance_metrics["event_timestamps"].append(event_received_time)

                    # Calculate event gap
                    gap = event_received_time - last_event_time
                    performance_metrics["event_gaps"].append(gap)
                    last_event_time = event_received_time

                    event_type = event.get("type", "unknown")

                    # Track first event timing
                    if performance_metrics["first_event_time"] is None:
                        performance_metrics["first_event_time"] = event_received_time - message_sent_time

                    # Track critical event timings
                    if event_type in self.__class__.CRITICAL_EVENTS:
                        performance_metrics["critical_events_received"].add(event_type)

                        if event_type == "agent_started":
                            performance_metrics["agent_started_time"] = event_received_time - message_sent_time
                        elif event_type == "agent_completed":
                            performance_metrics["agent_completed_time"] = event_received_time - message_sent_time

                            # Extract response content
                            response_data = event.get("data", {})
                            result = response_data.get("result", {})
                            if isinstance(result, dict):
                                performance_metrics["response_content"] = result.get("response", str(result))
                            else:
                                performance_metrics["response_content"] = str(result)
                            break

                    # Check for errors
                    if event_type in ["error", "agent_error"]:
                        performance_metrics["error"] = str(event)
                        break

                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    performance_metrics["error"] = f"JSON decode error: {e}"
                    continue

            await websocket.close()

            performance_metrics["total_time"] = time.time() - performance_metrics["start_time"]
            performance_metrics["success"] = len(performance_metrics["response_content"]) > 0

            return performance_metrics

        except Exception as e:
            performance_metrics["total_time"] = time.time() - performance_metrics["start_time"]
            performance_metrics["error"] = str(e)
            return performance_metrics

    def _analyze_performance_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics against SLA requirements."""
        analysis = {
            "sla_compliance": {},
            "performance_grade": "A",  # A, B, C, D, F
            "critical_issues": [],
            "performance_summary": {}
        }

        slas = self.__class__.ENTERPRISE_SLAS

        # Check response time SLA
        if metrics.get("agent_completed_time"):
            response_time = metrics["agent_completed_time"]

            # Determine expected SLA based on message complexity
            if metrics.get("expected_complexity") == "simple":
                sla_limit = slas["simple_query_response_time"]
            else:
                sla_limit = slas["complex_analysis_response_time"]

            sla_met = response_time <= sla_limit
            analysis["sla_compliance"]["response_time"] = {
                "met": sla_met,
                "actual": response_time,
                "limit": sla_limit,
                "margin": sla_limit - response_time
            }

            if not sla_met:
                analysis["critical_issues"].append(f"Response time SLA violation: {response_time:.1f}s > {sla_limit}s")
                analysis["performance_grade"] = "F"

        # Check first event latency SLA
        if metrics.get("first_event_time"):
            first_event_latency = metrics["first_event_time"]
            sla_met = first_event_latency <= slas["first_event_latency"]

            analysis["sla_compliance"]["first_event_latency"] = {
                "met": sla_met,
                "actual": first_event_latency,
                "limit": slas["first_event_latency"],
                "margin": slas["first_event_latency"] - first_event_latency
            }

            if not sla_met:
                analysis["critical_issues"].append(f"First event latency SLA violation: {first_event_latency:.1f}s > {slas['first_event_latency']}s")
                if analysis["performance_grade"] not in ["F"]:
                    analysis["performance_grade"] = "D"

        # Check event delivery reliability
        critical_events_expected = len(self.__class__.CRITICAL_EVENTS)
        critical_events_received = len(metrics.get("critical_events_received", set()))
        event_reliability = critical_events_received / critical_events_expected if critical_events_expected > 0 else 0

        sla_met = event_reliability >= slas["event_delivery_reliability"]
        analysis["sla_compliance"]["event_reliability"] = {
            "met": sla_met,
            "actual": event_reliability,
            "limit": slas["event_delivery_reliability"],
            "received": critical_events_received,
            "expected": critical_events_expected
        }

        if not sla_met:
            analysis["critical_issues"].append(f"Event delivery reliability SLA violation: {event_reliability:.1%} < {slas['event_delivery_reliability']:.1%}")
            if analysis["performance_grade"] not in ["F", "D"]:
                analysis["performance_grade"] = "C"

        # Performance grading
        if len(analysis["critical_issues"]) == 0:
            if metrics.get("agent_completed_time", 0) < slas["simple_query_response_time"]:
                analysis["performance_grade"] = "A"
            else:
                analysis["performance_grade"] = "B"

        # Performance summary
        analysis["performance_summary"] = {
            "total_events": len(metrics.get("events", [])),
            "connection_time": metrics.get("connection_time", 0),
            "processing_time": metrics.get("agent_completed_time", 0),
            "avg_event_gap": statistics.mean(metrics.get("event_gaps", [0])) if metrics.get("event_gaps") else 0,
            "response_length": len(metrics.get("response_content", "")),
            "success": metrics.get("success", False)
        }

        return analysis

    async def test_simple_query_performance_sla(self):
        """
        Test simple query performance against enterprise SLA requirements.

        PERFORMANCE SLA: Simple queries should complete within 15 seconds
        with first event within 5 seconds and 95% event delivery reliability.

        Scenario:
        1. Send simple optimization query
        2. Measure response time, first event latency, event reliability
        3. Validate against enterprise SLA requirements
        4. Ensure performance meets business standards
        5. Grade overall performance quality

        DIFFICULTY: Medium (25 minutes)
        REAL SERVICES: Yes - Performance measurement in staging
        STATUS: Should PASS - Simple query SLAs are fundamental business requirements
        """
        self.logger.info("⚡ Testing simple query performance SLA compliance")

        simple_queries = [
            "What are the top 3 ways to reduce AI API costs?",
            "How can I optimize my OpenAI spending?",
            "What's the difference between GPT-4 and GPT-3.5 pricing?",
            "Should I use prompt caching to reduce costs?",
            "How do I calculate ROI on AI cost optimization?"
        ]

        performance_results = []

        for query in simple_queries:
            self.logger.info(f"Testing query: {query[:50]}...")

            metrics = await self._measure_message_performance(
                "triage_agent",  # Triage agent for simple queries
                query,
                expected_complexity="simple",
                timeout=30.0
            )

            analysis = self._analyze_performance_metrics(metrics)

            performance_results.append({
                "query": query,
                "metrics": metrics,
                "analysis": analysis
            })

            # Log individual result
            self.logger.info(f"   Response Time: {metrics.get('agent_completed_time', 0):.1f}s")
            self.logger.info(f"   First Event: {metrics.get('first_event_time', 0):.1f}s")
            self.logger.info(f"   Grade: {analysis['performance_grade']}")

        # Aggregate performance analysis
        successful_queries = [r for r in performance_results if r["metrics"]["success"]]
        response_times = [r["metrics"].get("agent_completed_time", float('inf')) for r in successful_queries]
        first_event_times = [r["metrics"].get("first_event_time", float('inf')) for r in successful_queries]
        performance_grades = [r["analysis"]["performance_grade"] for r in performance_results]

        self.logger.info(f"📊 Simple Query Performance Results:")
        self.logger.info(f"   Successful Queries: {len(successful_queries)}/{len(simple_queries)}")
        self.logger.info(f"   Avg Response Time: {statistics.mean(response_times):.1f}s")
        self.logger.info(f"   Max Response Time: {max(response_times):.1f}s")
        self.logger.info(f"   Avg First Event: {statistics.mean(first_event_times):.1f}s")
        self.logger.info(f"   Performance Grades: {performance_grades}")

        # Validate SLA compliance
        sla_violations = []
        for result in performance_results:
            analysis = result["analysis"]
            for issue in analysis["critical_issues"]:
                sla_violations.append(f"Query '{result['query'][:30]}...': {issue}")

        # All simple queries should succeed
        success_rate = len(successful_queries) / len(simple_queries)
        assert success_rate >= self.__class__.ENTERPRISE_SLAS["system_availability"], (
            f"Simple query success rate below SLA: {success_rate:.1%} "
            f"< {self.__class__.ENTERPRISE_SLAS['system_availability']:.1%}"
        )

        # Response times should meet SLA
        sla_compliant_responses = [
            t for t in response_times
            if t <= self.__class__.ENTERPRISE_SLAS["simple_query_response_time"]
        ]
        response_time_compliance = len(sla_compliant_responses) / len(response_times) if response_times else 0

        assert response_time_compliance >= 0.9, (
            f"Simple query response time SLA compliance too low: {response_time_compliance:.1%} (min 90%). "
            f"Max time: {max(response_times):.1f}s, "
            f"SLA limit: {self.__class__.ENTERPRISE_SLAS['simple_query_response_time']}s"
        )

        # First event latency should meet SLA
        sla_compliant_first_events = [
            t for t in first_event_times
            if t <= self.__class__.ENTERPRISE_SLAS["first_event_latency"]
        ]
        first_event_compliance = len(sla_compliant_first_events) / len(first_event_times) if first_event_times else 0

        assert first_event_compliance >= 0.8, (
            f"First event latency SLA compliance too low: {first_event_compliance:.1%} (min 80%). "
            f"Max first event time: {max(first_event_times):.1f}s, "
            f"SLA limit: {self.__class__.ENTERPRISE_SLAS['first_event_latency']}s"
        )

        # No critical performance failures
        failing_grades = [grade for grade in performance_grades if grade in ["F", "D"]]
        assert len(failing_grades) == 0, (
            f"No simple queries should have failing performance grades. "
            f"Failing grades: {failing_grades}, SLA violations: {sla_violations}"
        )

        self.logger.info("✅ Simple query performance SLA compliance validated")

    async def test_complex_analysis_performance_sla(self):
        """
        Test complex analysis performance against enterprise SLA requirements.

        PERFORMANCE SLA: Complex analysis should complete within 90 seconds
        with proper event delivery and maintained response quality.

        Scenario:
        1. Send complex optimization analysis requests
        2. Measure processing time and resource usage
        3. Validate against complex analysis SLA requirements
        4. Ensure quality is maintained under performance pressure
        5. Verify graceful performance scaling

        DIFFICULTY: High (35 minutes)
        REAL SERVICES: Yes - Complex processing performance in staging
        STATUS: Should PASS - Complex analysis SLAs critical for enterprise features
        """
        self.logger.info("🧠 Testing complex analysis performance SLA compliance")

        complex_analyses = [
            (
                "apex_optimizer_agent",
                "Provide comprehensive AI cost optimization analysis for a $500K/month AI spend "
                "across GPT-4, Claude, and custom models. Include market research, detailed ROI calculations, "
                "implementation timeline, and risk assessment for a Fortune 500 financial services company."
            ),
            (
                "supervisor_agent",
                "I need strategic guidance for scaling AI infrastructure from $50K to $500K monthly spend "
                "while maintaining 99.9% SLA compliance. Address technical architecture, cost optimization, "
                "team scaling, vendor management, and regulatory compliance requirements."
            ),
            (
                "data_helper_agent",
                "Analyze our AI usage data: 500M tokens/month across 12 different models, "
                "15 use cases, 3 geographic regions. Calculate optimal model mix, identify cost anomalies, "
                "project scaling scenarios, and recommend efficiency improvements with supporting metrics."
            )
        ]

        performance_results = []

        for agent_type, analysis_request in complex_analyses:
            self.logger.info(f"Testing complex analysis with {agent_type}...")

            metrics = await self._measure_message_performance(
                agent_type,
                analysis_request,
                expected_complexity="complex",
                timeout=150.0
            )

            analysis = self._analyze_performance_metrics(metrics)

            performance_results.append({
                "agent_type": agent_type,
                "metrics": metrics,
                "analysis": analysis
            })

            # Log individual result
            self.logger.info(f"   Response Time: {metrics.get('agent_completed_time', 0):.1f}s")
            self.logger.info(f"   Events: {len(metrics.get('events', []))}")
            self.logger.info(f"   Grade: {analysis['performance_grade']}")
            self.logger.info(f"   Response Length: {len(metrics.get('response_content', ''))} chars")

        # Aggregate complex analysis performance
        successful_analyses = [r for r in performance_results if r["metrics"]["success"]]
        response_times = [r["metrics"].get("agent_completed_time", float('inf')) for r in successful_analyses]
        response_qualities = [len(r["metrics"].get("response_content", "")) for r in successful_analyses]

        self.logger.info(f"📊 Complex Analysis Performance Results:")
        self.logger.info(f"   Successful Analyses: {len(successful_analyses)}/{len(complex_analyses)}")
        self.logger.info(f"   Avg Response Time: {statistics.mean(response_times):.1f}s")
        self.logger.info(f"   Max Response Time: {max(response_times):.1f}s")
        self.logger.info(f"   Avg Response Quality: {statistics.mean(response_qualities):.0f} chars")

        # Validate complex analysis SLA compliance

        # All complex analyses should succeed
        success_rate = len(successful_analyses) / len(complex_analyses)
        assert success_rate >= 0.9, (
            f"Complex analysis success rate below acceptable threshold: {success_rate:.1%} (min 90%)"
        )

        # Response times should meet complex analysis SLA
        sla_limit = self.__class__.ENTERPRISE_SLAS["complex_analysis_response_time"]
        sla_compliant_analyses = [t for t in response_times if t <= sla_limit]
        time_compliance = len(sla_compliant_analyses) / len(response_times) if response_times else 0

        assert time_compliance >= 0.8, (
            f"Complex analysis response time SLA compliance too low: {time_compliance:.1%} (min 80%). "
            f"Max time: {max(response_times):.1f}s, SLA limit: {sla_limit}s"
        )

        # Quality should be maintained under performance pressure
        min_quality_threshold = 200  # characters
        quality_compliant = [q for q in response_qualities if q >= min_quality_threshold]
        quality_compliance = len(quality_compliant) / len(response_qualities) if response_qualities else 0

        assert quality_compliance >= 0.9, (
            f"Response quality should be maintained under performance pressure: {quality_compliance:.1%} (min 90%). "
            f"Min response length: {min(response_qualities)} chars"
        )

        # Performance grades should be acceptable
        performance_grades = [r["analysis"]["performance_grade"] for r in performance_results]
        failing_grades = [grade for grade in performance_grades if grade == "F"]

        assert len(failing_grades) == 0, (
            f"No complex analyses should have failing performance grades. "
            f"Grades: {performance_grades}"
        )

        self.logger.info("✅ Complex analysis performance SLA compliance validated")

    async def test_concurrent_load_performance_degradation(self):
        """
        Test performance degradation under concurrent load conditions.

        PERFORMANCE SLA: System should maintain acceptable performance under
        concurrent load with no more than 50% degradation from baseline.

        Scenario:
        1. Establish baseline performance with single user
        2. Test performance with multiple concurrent users
        3. Measure performance degradation under load
        4. Validate degradation stays within acceptable limits
        5. Ensure system remains stable under concurrent pressure

        DIFFICULTY: Very High (40 minutes)
        REAL SERVICES: Yes - Concurrent load testing in staging
        STATUS: Should PASS - Concurrent performance critical for multi-user enterprise deployment
        """
        self.logger.info("🚀 Testing concurrent load performance degradation")

        # Step 1: Establish baseline performance
        baseline_request = (
            "I need AI cost optimization recommendations for my $25K/month spending "
            "across customer support, content generation, and data analysis use cases."
        )

        self.logger.info("Establishing baseline performance...")
        baseline_metrics = await self._measure_message_performance(
            "apex_optimizer_agent",
            baseline_request,
            expected_complexity="medium",
            timeout=90.0
        )

        baseline_time = baseline_metrics.get("agent_completed_time", 0)
        baseline_success = baseline_metrics.get("success", False)

        assert baseline_success, (
            f"Baseline performance test should succeed. Error: {baseline_metrics.get('error')}"
        )

        self.logger.info(f"Baseline Performance: {baseline_time:.1f}s")

        # Step 2: Test concurrent load performance
        concurrent_users = 4
        concurrent_requests = [
            f"Optimization request from concurrent user {i}: "
            f"Help reduce my AI costs for {['customer support', 'marketing', 'analytics', 'development'][i]} "
            f"with current spend of ${15000 + i * 5000}/month. User ID: CONCURRENT-{i}-{int(time.time())}"
            for i in range(concurrent_users)
        ]

        async def execute_concurrent_request(user_index: int, request: str) -> Dict[str, Any]:
            """Execute a single concurrent request with performance measurement."""
            return await self._measure_message_performance(
                "apex_optimizer_agent",
                request,
                expected_complexity="medium",
                timeout=120.0  # Slightly longer timeout for concurrent load
            )

        # Execute concurrent requests
        self.logger.info(f"Testing concurrent load with {concurrent_users} users...")
        concurrent_start = time.time()

        concurrent_tasks = [
            execute_concurrent_request(i, req)
            for i, req in enumerate(concurrent_requests)
        ]

        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_concurrent_time = time.time() - concurrent_start

        # Filter successful results
        successful_concurrent = [
            r for r in concurrent_results
            if isinstance(r, dict) and r.get("success")
        ]
        failed_concurrent = [
            r for r in concurrent_results
            if isinstance(r, dict) and not r.get("success")
        ]
        exception_concurrent = [
            r for r in concurrent_results
            if isinstance(r, Exception)
        ]

        concurrent_response_times = [
            r.get("agent_completed_time", 0) for r in successful_concurrent
        ]

        self.logger.info(f"📊 Concurrent Load Performance Results:")
        self.logger.info(f"   Concurrent Users: {concurrent_users}")
        self.logger.info(f"   Successful: {len(successful_concurrent)}")
        self.logger.info(f"   Failed: {len(failed_concurrent)}")
        self.logger.info(f"   Exceptions: {len(exception_concurrent)}")
        self.logger.info(f"   Total Execution: {total_concurrent_time:.1f}s")
        if concurrent_response_times:
            self.logger.info(f"   Avg Response Time: {statistics.mean(concurrent_response_times):.1f}s")
            self.logger.info(f"   Max Response Time: {max(concurrent_response_times):.1f}s")

        # Validate concurrent load performance

        # Minimum success rate under load
        success_rate = len(successful_concurrent) / concurrent_users
        assert success_rate >= 0.75, (
            f"Concurrent load success rate too low: {success_rate:.1%} (min 75%). "
            f"Failed: {len(failed_concurrent)}, Exceptions: {len(exception_concurrent)}"
        )

        # Performance degradation should be within acceptable limits
        if concurrent_response_times and baseline_time > 0:
            avg_concurrent_time = statistics.mean(concurrent_response_times)
            performance_degradation = (avg_concurrent_time - baseline_time) / baseline_time

            max_degradation = self.__class__.ENTERPRISE_SLAS["concurrent_user_degradation"]

            self.logger.info(f"📈 Performance Degradation Analysis:")
            self.logger.info(f"   Baseline: {baseline_time:.1f}s")
            self.logger.info(f"   Concurrent Avg: {avg_concurrent_time:.1f}s")
            self.logger.info(f"   Degradation: {performance_degradation:.1%}")
            self.logger.info(f"   SLA Limit: {max_degradation:.1%}")

            assert performance_degradation <= max_degradation, (
                f"Performance degradation exceeds SLA limit: {performance_degradation:.1%} > {max_degradation:.1%}. "
                f"Baseline: {baseline_time:.1f}s, Concurrent avg: {avg_concurrent_time:.1f}s"
            )

        # No critical system failures under load
        assert len(exception_concurrent) == 0, (
            f"Should not have system exceptions under concurrent load: {exception_concurrent}"
        )

        # Response times should still be reasonable under load
        if concurrent_response_times:
            max_concurrent_time = max(concurrent_response_times)
            reasonable_limit = self.__class__.ENTERPRISE_SLAS["complex_analysis_response_time"] * 1.5  # 50% buffer

            assert max_concurrent_time <= reasonable_limit, (
                f"Maximum concurrent response time exceeds reasonable limit: {max_concurrent_time:.1f}s > {reasonable_limit:.1f}s"
            )

        self.logger.info("✅ Concurrent load performance degradation validated")

    async def test_websocket_event_timing_precision(self):
        """
        Test WebSocket event timing precision and delivery consistency.

        PERFORMANCE SLA: WebSocket events should be delivered with consistent
        timing and minimal gaps to ensure smooth real-time user experience.

        Scenario:
        1. Monitor WebSocket event delivery timing patterns
        2. Measure inter-event gaps and consistency
        3. Validate event ordering and sequence integrity
        4. Ensure no abnormal delays or timing anomalies
        5. Verify real-time experience quality

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - WebSocket timing precision in staging
        STATUS: Should PASS - Event timing precision critical for real-time UX
        """
        self.logger.info("⏱️ Testing WebSocket event timing precision")

        timing_test_requests = [
            {
                "agent": "triage_agent",
                "message": "Quick timing test: What are 3 AI cost reduction strategies?",
                "expected_events": 4,  # Minimum expected events
                "complexity": "simple"
            },
            {
                "agent": "apex_optimizer_agent",
                "message": "Comprehensive timing test: Analyze AI cost optimization opportunities with calculations and recommendations.",
                "expected_events": 6,  # More events for complex processing
                "complexity": "complex"
            }
        ]

        timing_results = []

        for test_config in timing_test_requests:
            self.logger.info(f"Testing event timing for {test_config['complexity']} request...")

            metrics = await self._measure_message_performance(
                test_config["agent"],
                test_config["message"],
                expected_complexity=test_config["complexity"],
                timeout=90.0
            )

            # Analyze event timing patterns
            event_timestamps = metrics.get("event_timestamps", [])
            event_gaps = metrics.get("event_gaps", [])

            timing_analysis = {
                "test_config": test_config,
                "success": metrics.get("success", False),
                "total_events": len(metrics.get("events", [])),
                "event_gaps": event_gaps,
                "timing_consistency": {},
                "precision_issues": []
            }

            if len(event_gaps) > 1:
                # Analyze timing consistency
                avg_gap = statistics.mean(event_gaps)
                gap_std_dev = statistics.stdev(event_gaps) if len(event_gaps) > 1 else 0
                max_gap = max(event_gaps)
                min_gap = min(event_gaps)

                timing_analysis["timing_consistency"] = {
                    "avg_gap": avg_gap,
                    "std_dev": gap_std_dev,
                    "max_gap": max_gap,
                    "min_gap": min_gap,
                    "coefficient_of_variation": gap_std_dev / avg_gap if avg_gap > 0 else 0
                }

                # Check for timing anomalies
                if max_gap > 20.0:  # 20 second gap is abnormal
                    timing_analysis["precision_issues"].append(f"Abnormal event gap: {max_gap:.1f}s")

                if gap_std_dev > avg_gap:  # High variability
                    timing_analysis["precision_issues"].append(f"High timing variability: std_dev {gap_std_dev:.1f}s > avg {avg_gap:.1f}s")

            timing_results.append(timing_analysis)

            # Log individual timing analysis
            self.logger.info(f"   Events: {timing_analysis['total_events']}")
            self.logger.info(f"   Avg Gap: {timing_analysis['timing_consistency'].get('avg_gap', 0):.1f}s")
            self.logger.info(f"   Max Gap: {timing_analysis['timing_consistency'].get('max_gap', 0):.1f}s")
            self.logger.info(f"   Issues: {len(timing_analysis['precision_issues'])}")

        # Validate WebSocket event timing precision

        # All timing tests should succeed
        successful_tests = [r for r in timing_results if r["success"]]
        success_rate = len(successful_tests) / len(timing_test_requests)

        assert success_rate >= 0.9, (
            f"Event timing tests should have high success rate: {success_rate:.1%} (min 90%)"
        )

        # Event delivery should be reasonably consistent
        for result in successful_tests:
            consistency = result["timing_consistency"]

            # Maximum gap between events should be reasonable
            max_gap = consistency.get("max_gap", 0)
            assert max_gap <= 15.0, (
                f"Maximum event gap too large for {result['test_config']['complexity']} request: "
                f"{max_gap:.1f}s (max 15s)"
            )

            # Timing variability should be reasonable
            coefficient_of_variation = consistency.get("coefficient_of_variation", 0)
            assert coefficient_of_variation <= 2.0, (
                f"Event timing too inconsistent for {result['test_config']['complexity']} request: "
                f"CV {coefficient_of_variation:.1f} (max 2.0)"
            )

            # Should receive expected number of events
            total_events = result["total_events"]
            expected_events = result["test_config"]["expected_events"]

            assert total_events >= expected_events, (
                f"Should receive expected number of events: {total_events} < {expected_events} "
                f"for {result['test_config']['complexity']} request"
            )

        # No critical precision issues across all tests
        all_precision_issues = []
        for result in timing_results:
            all_precision_issues.extend(result["precision_issues"])

        assert len(all_precision_issues) == 0, (
            f"Should not have WebSocket timing precision issues: {all_precision_issues}"
        )

        self.logger.info(f"📊 Event Timing Precision Summary:")
        for result in timing_results:
            complexity = result["test_config"]["complexity"]
            consistency = result["timing_consistency"]
            self.logger.info(f"   {complexity.title()}: {consistency.get('avg_gap', 0):.1f}s avg, "
                          f"{consistency.get('max_gap', 0):.1f}s max, "
                          f"{result['total_events']} events")

        self.logger.info("✅ WebSocket event timing precision validated")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--performance-validation"
    ])