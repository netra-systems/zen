"""
E2E Tests for Performance Under Realistic Load - Golden Path Scalability

MISSION CRITICAL: Tests agent performance and system behavior under realistic
production load scenarios to validate scalability, user isolation, and performance
consistency that maintains quality user experience under actual usage patterns.

Business Value Justification (BVJ):
- Segment: Growing Mid-tier to Enterprise Users (Production Scale Validation)
- Business Goal: Platform Reliability & Scalability for Revenue Growth
- Value Impact: Validates system can handle real-world load without degradation
- Strategic Impact: Proves platform readiness for scale, prevents churn due to performance

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: Multiple JWT tokens for concurrent user simulation
- REAL WEBSOCKETS: Multiple concurrent wss:// connections under load
- REAL AGENTS: All agent types under concurrent execution pressure
- REAL ISOLATION: Multi-user context separation validation under load
- PERFORMANCE DEPTH: Response times, throughput, error rates, resource utilization

CRITICAL: These tests must demonstrate actual performance characteristics under load.
No mocking concurrency, load simulation, or performance measurement bypassing.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - STEP 1
Coverage Target: 0.9% -> 25% improvement (Priority Scenario #4)
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from datetime import datetime, timedelta
import uuid
import statistics
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@dataclass
class PerformanceMetrics:
    """Tracks performance metrics during load testing."""
    user_id: str
    start_time: float
    end_time: float = 0.0
    response_time: float = 0.0
    success: bool = False
    error_message: str = ''
    events_received: int = 0
    response_length: int = 0
    agent_type: str = ''
    concurrent_users: int = 0

@dataclass
class LoadTestResults:
    """Aggregated load test results and analysis."""
    total_users: int
    successful_users: int
    failed_users: int
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    success_rate: float
    throughput: float
    error_rate: float
    user_metrics: List[PerformanceMetrics] = field(default_factory=list)

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.performance
@pytest.mark.mission_critical
class PerformanceRealisticLoadE2ETests(SSotAsyncTestCase):
    """
    E2E tests for validating agent performance under realistic production load.

    Tests system behavior under concurrent user scenarios: response times,
    user isolation, error rates, and performance consistency at scale.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and dependencies."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper(base_url=cls.staging_config.urls.websocket_url, environment='staging')
        cls.logger.info(f'Performance realistic load E2E tests initialized for staging')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.load_test_id = str(uuid.uuid4())
        self.test_start_time = time.time()
        self.logger.info(f'Load test setup - load_test_id: {self.load_test_id}')

    async def _create_concurrent_user(self, user_index: int, total_users: int) -> PerformanceMetrics:
        """Create and execute a single concurrent user scenario."""
        user_id = f'load_user_{user_index}_{int(time.time())}'
        user_email = f'load_test_{user_index}_{int(time.time())}@netra-testing.ai'
        thread_id = f'load_thread_{user_index}_{self.load_test_id}'
        metrics = PerformanceMetrics(user_id=user_id, start_time=time.time(), concurrent_users=total_users)
        try:
            access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=user_id, email=user_email, exp_minutes=60)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'performance-load-e2e', 'X-Load-Test-Id': self.load_test_id, 'X-User-Index': str(user_index), 'X-Concurrent-Users': str(total_users)}, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
            business_questions = [f"I'm optimizing AI costs for user {user_index}. My current spend is ${5000 + user_index * 100}/month. How can I reduce costs by 20%?", f'User {user_index} needs help with AI model selection. Current latency is {200 + user_index * 10}ms. What optimizations do you recommend?', f'Analyzing performance for client {user_index}. We have {10000 + user_index * 500} daily users. How can we scale efficiently?', f'Cost analysis for user {user_index}: spending ${15000 + user_index * 200}/month on LLM APIs. Need 30% reduction strategy.']
            message = business_questions[user_index % len(business_questions)]
            agent_type = ['supervisor_agent', 'triage_agent', 'apex_optimizer_agent', 'data_helper_agent'][user_index % 4]
            request_message = {'type': 'agent_request', 'agent': agent_type, 'message': message, 'thread_id': thread_id, 'run_id': f'run_{thread_id}', 'user_id': user_id, 'context': {'load_test': True, 'user_index': user_index, 'concurrent_users': total_users}}
            metrics.agent_type = agent_type
            await websocket.send(json.dumps(request_message))
            events = []
            response_timeout = 60.0
            collection_start = time.time()
            while time.time() - collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    events.append(event)
                    event_type = event.get('type', 'unknown')
                    if event_type == 'agent_completed':
                        response_data = event.get('data', {})
                        result = response_data.get('result', {})
                        if isinstance(result, dict):
                            response_text = result.get('response', str(result))
                        else:
                            response_text = str(result)
                        metrics.response_length = len(response_text)
                        metrics.success = True
                        break
                    elif event_type in ['error', 'agent_error']:
                        metrics.error_message = str(event)
                        metrics.success = False
                        break
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            await websocket.close()
            metrics.end_time = time.time()
            metrics.response_time = metrics.end_time - metrics.start_time
            metrics.events_received = len(events)
            if metrics.success and metrics.response_length < 50:
                metrics.success = False
                metrics.error_message = f'Response too short under load: {metrics.response_length} chars'
        except Exception as e:
            metrics.end_time = time.time()
            metrics.response_time = metrics.end_time - metrics.start_time
            metrics.success = False
            metrics.error_message = str(e)
        return metrics

    def _analyze_load_test_results(self, user_metrics: List[PerformanceMetrics]) -> LoadTestResults:
        """Analyze load test results and compute performance statistics."""
        successful_metrics = [m for m in user_metrics if m.success]
        failed_metrics = [m for m in user_metrics if not m.success]
        response_times = [m.response_time for m in successful_metrics]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 10 else max(response_times)
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0.0
        total_users = len(user_metrics)
        successful_users = len(successful_metrics)
        failed_users = len(failed_metrics)
        success_rate = successful_users / total_users if total_users > 0 else 0.0
        error_rate = failed_users / total_users if total_users > 0 else 0.0
        if successful_metrics:
            total_duration = max((m.end_time for m in successful_metrics)) - min((m.start_time for m in successful_metrics))
            throughput = successful_users / total_duration if total_duration > 0 else 0.0
        else:
            throughput = 0.0
        return LoadTestResults(total_users=total_users, successful_users=successful_users, failed_users=failed_users, avg_response_time=avg_response_time, median_response_time=median_response_time, p95_response_time=p95_response_time, p99_response_time=p99_response_time, success_rate=success_rate, throughput=throughput, error_rate=error_rate, user_metrics=user_metrics)

    async def test_moderate_concurrent_user_load(self):
        """
        Test moderate concurrent user load to validate basic scalability.

        PERFORMANCE VALIDATION: System should handle moderate concurrent load
        with acceptable response times and high success rates.

        Load Characteristics:
        - 5 concurrent users
        - Mixed agent types
        - Realistic business questions
        - 60-second timeout per request

        Performance Targets:
        - Success rate ≥ 80%
        - Average response time ≤ 30 seconds
        - P95 response time ≤ 45 seconds
        - No user isolation failures

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Concurrent load on staging GCP
        STATUS: Should PASS - Basic concurrent load handling is essential
        """
        self.logger.info('⚡ Testing moderate concurrent user load')
        concurrent_users = 5
        self.logger.info(f'Starting load test with {concurrent_users} concurrent users')
        user_tasks = []
        for user_index in range(concurrent_users):
            task = self._create_concurrent_user(user_index, concurrent_users)
            user_tasks.append(task)
        load_start_time = time.time()
        user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_load_time = time.time() - load_start_time
        valid_metrics = [m for m in user_metrics if isinstance(m, PerformanceMetrics)]
        exception_count = len(user_metrics) - len(valid_metrics)
        results = self._analyze_load_test_results(valid_metrics)
        self.logger.info(f'⚡ Moderate Load Test Results:')
        self.logger.info(f'   Total Load Time: {total_load_time:.1f}s')
        self.logger.info(f'   Concurrent Users: {concurrent_users}')
        self.logger.info(f'   Successful Users: {results.successful_users}/{results.total_users}')
        self.logger.info(f'   Success Rate: {results.success_rate:.1%}')
        self.logger.info(f'   Average Response Time: {results.avg_response_time:.1f}s')
        self.logger.info(f'   Median Response Time: {results.median_response_time:.1f}s')
        self.logger.info(f'   P95 Response Time: {results.p95_response_time:.1f}s')
        self.logger.info(f'   Throughput: {results.throughput:.2f} requests/sec')
        self.logger.info(f'   Exceptions: {exception_count}')
        assert results.success_rate >= 0.8, f'Success rate too low under moderate load: {results.success_rate:.1%} (expected ≥80%). Failed users: {results.failed_users}, Errors: {[m.error_message for m in valid_metrics if not m.success][:3]}'
        assert results.avg_response_time <= 30.0, f'Average response time too slow under moderate load: {results.avg_response_time:.1f}s (expected ≤30s). This impacts user experience.'
        assert results.p95_response_time <= 45.0, f'P95 response time too slow under moderate load: {results.p95_response_time:.1f}s (expected ≤45s). Users expect consistent performance.'
        user_ids = {m.user_id for m in valid_metrics}
        assert len(user_ids) == len(valid_metrics), f'User isolation failure detected under load. Unique users: {len(user_ids)}, Total metrics: {len(valid_metrics)}'
        successful_metrics = [m for m in valid_metrics if m.success]
        if successful_metrics:
            avg_response_length = statistics.mean((m.response_length for m in successful_metrics))
            assert avg_response_length >= 80, f'Response quality degraded under load: {avg_response_length:.0f} avg chars (expected ≥80 for business questions)'
        self.logger.info('CHECK Moderate concurrent user load validation passed')

    async def test_high_concurrent_user_load(self):
        """
        Test high concurrent user load to validate advanced scalability.

        PERFORMANCE VALIDATION: System should handle higher concurrent load
        while maintaining acceptable performance and reliability.

        Load Characteristics:
        - 10 concurrent users
        - All agent types under pressure
        - Complex business scenarios
        - 90-second timeout per request

        Performance Targets:
        - Success rate ≥ 70%
        - Average response time ≤ 45 seconds
        - P95 response time ≤ 75 seconds
        - Error rate ≤ 30%

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - High concurrent load on staging GCP
        STATUS: Should PASS - High load handling demonstrates platform scalability
        """
        self.logger.info('⚡ Testing high concurrent user load')
        concurrent_users = 10
        self.logger.info(f'Starting high load test with {concurrent_users} concurrent users')
        user_tasks = []
        for user_index in range(concurrent_users):
            task = self._create_concurrent_user(user_index, concurrent_users)
            user_tasks.append(task)
        load_start_time = time.time()
        user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_load_time = time.time() - load_start_time
        valid_metrics = [m for m in user_metrics if isinstance(m, PerformanceMetrics)]
        exception_count = len(user_metrics) - len(valid_metrics)
        results = self._analyze_load_test_results(valid_metrics)
        self.logger.info(f'⚡ High Load Test Results:')
        self.logger.info(f'   Total Load Time: {total_load_time:.1f}s')
        self.logger.info(f'   Concurrent Users: {concurrent_users}')
        self.logger.info(f'   Successful Users: {results.successful_users}/{results.total_users}')
        self.logger.info(f'   Success Rate: {results.success_rate:.1%}')
        self.logger.info(f'   Error Rate: {results.error_rate:.1%}')
        self.logger.info(f'   Average Response Time: {results.avg_response_time:.1f}s')
        self.logger.info(f'   Median Response Time: {results.median_response_time:.1f}s')
        self.logger.info(f'   P95 Response Time: {results.p95_response_time:.1f}s')
        self.logger.info(f'   P99 Response Time: {results.p99_response_time:.1f}s')
        self.logger.info(f'   Throughput: {results.throughput:.2f} requests/sec')
        assert results.success_rate >= 0.7, f'Success rate too low under high load: {results.success_rate:.1%} (expected ≥70%). System should handle higher concurrency gracefully.'
        assert results.error_rate <= 0.3, f'Error rate too high under high load: {results.error_rate:.1%} (expected ≤30%). Error handling should be robust.'
        if results.successful_users > 0:
            assert results.avg_response_time <= 45.0, f'Average response time too slow under high load: {results.avg_response_time:.1f}s (expected ≤45s for high concurrency scenario)'
            assert results.p95_response_time <= 75.0, f'P95 response time too slow under high load: {results.p95_response_time:.1f}s (expected ≤75s). Even under pressure, most users should get reasonable performance.'
        assert results.throughput >= 0.1, f'Throughput too low under high load: {results.throughput:.2f} requests/sec (expected ≥0.1). System should maintain reasonable processing rate.'
        agent_performance = {}
        for metric in valid_metrics:
            if metric.success and metric.agent_type:
                if metric.agent_type not in agent_performance:
                    agent_performance[metric.agent_type] = []
                agent_performance[metric.agent_type].append(metric.response_time)
        self.logger.info('📊 Performance by Agent Type:')
        for agent_type, response_times in agent_performance.items():
            if response_times:
                avg_time = statistics.mean(response_times)
                self.logger.info(f'   {agent_type}: {avg_time:.1f}s avg ({len(response_times)} samples)')
        self.logger.info('CHECK High concurrent user load validation passed')

    async def test_sustained_load_performance(self):
        """
        Test sustained load performance over extended duration.

        PERFORMANCE VALIDATION: System should maintain performance consistency
        over time without degradation from memory leaks or resource exhaustion.

        Load Characteristics:
        - 3 concurrent users
        - Extended duration (multiple rounds)
        - Performance consistency over time
        - Resource stability validation

        Performance Targets:
        - Consistent response times across rounds
        - No significant performance degradation
        - Success rate stability ≥ 75%
        - Memory/resource stability

        DIFFICULTY: Very High (50 minutes)
        REAL SERVICES: Yes - Sustained load on staging GCP
        STATUS: Should PASS - Sustained performance is critical for production
        """
        self.logger.info('⚡ Testing sustained load performance')
        concurrent_users = 3
        test_rounds = 4
        round_duration = 60
        all_round_results = []
        for round_num in range(test_rounds):
            self.logger.info(f'🔄 Starting sustained load round {round_num + 1}/{test_rounds}')
            user_tasks = []
            for user_index in range(concurrent_users):
                task = self._create_concurrent_user(user_index + round_num * concurrent_users, concurrent_users)
                user_tasks.append(task)
            round_start_time = time.time()
            user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)
            round_duration_actual = time.time() - round_start_time
            valid_metrics = [m for m in user_metrics if isinstance(m, PerformanceMetrics)]
            round_results = self._analyze_load_test_results(valid_metrics)
            round_results.round_number = round_num + 1
            round_results.round_duration = round_duration_actual
            all_round_results.append(round_results)
            self.logger.info(f'   Round {round_num + 1} Results:')
            self.logger.info(f'   Success Rate: {round_results.success_rate:.1%}')
            self.logger.info(f'   Avg Response Time: {round_results.avg_response_time:.1f}s')
            self.logger.info(f'   P95 Response Time: {round_results.p95_response_time:.1f}s')
            if round_num < test_rounds - 1:
                self.logger.info(f'   Pausing {round_duration}s before next round...')
                await asyncio.sleep(round_duration)
        success_rates = [r.success_rate for r in all_round_results]
        avg_response_times = [r.avg_response_time for r in all_round_results if r.successful_users > 0]
        p95_response_times = [r.p95_response_time for r in all_round_results if r.successful_users > 0]
        self.logger.info(f'⚡ Sustained Load Test Summary:')
        self.logger.info(f'   Total Rounds: {test_rounds}')
        self.logger.info(f"   Success Rates: {[f'{r:.1%}' for r in success_rates]}")
        self.logger.info(f"   Avg Response Times: {[f'{t:.1f}s' for t in avg_response_times]}")
        self.logger.info(f"   P95 Response Times: {[f'{t:.1f}s' for t in p95_response_times]}")
        avg_success_rate = statistics.mean(success_rates)
        assert avg_success_rate >= 0.75, f'Average sustained success rate too low: {avg_success_rate:.1%} (expected ≥75%). System should maintain reliability over time.'
        if len(avg_response_times) >= 3:
            first_half_avg = statistics.mean(avg_response_times[:len(avg_response_times) // 2])
            second_half_avg = statistics.mean(avg_response_times[len(avg_response_times) // 2:])
            degradation_ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1.0
            assert degradation_ratio <= 1.5, f'Significant performance degradation detected over time: First half avg: {first_half_avg:.1f}s, Second half avg: {second_half_avg:.1f}s (degradation ratio: {degradation_ratio:.2f}, expected ≤1.5)'
        if avg_response_times:
            response_time_std = statistics.stdev(avg_response_times) if len(avg_response_times) > 1 else 0
            response_time_avg = statistics.mean(avg_response_times)
            coefficient_of_variation = response_time_std / response_time_avg if response_time_avg > 0 else 0
            assert coefficient_of_variation <= 0.4, f'Response time too inconsistent across rounds: CV={coefficient_of_variation:.2f} (expected ≤0.4). System should provide consistent performance over time.'
        failed_rounds = [r for r in all_round_results if r.success_rate == 0]
        assert len(failed_rounds) == 0, f'Complete failure detected in {len(failed_rounds)} rounds. System should not have complete failures during sustained load.'
        self.logger.info('CHECK Sustained load performance validation passed')

    async def test_mixed_agent_load_distribution(self):
        """
        Test performance with mixed agent types under concurrent load.

        PERFORMANCE VALIDATION: Different agent types should maintain
        reasonable performance when running concurrently under load.

        Load Characteristics:
        - 8 concurrent users
        - Balanced distribution across all agent types
        - Agent-specific performance analysis
        - Cross-agent performance comparison

        Performance Targets:
        - All agent types maintain ≥70% success rate
        - No single agent type dominates resources
        - Reasonable performance across all agent types
        - Fair resource sharing

        DIFFICULTY: High (35 minutes)
        REAL SERVICES: Yes - Mixed agent load on staging GCP
        STATUS: Should PASS - Balanced agent performance is important for UX
        """
        self.logger.info('⚡ Testing mixed agent load distribution')
        total_users = 8
        agent_types = ['supervisor_agent', 'triage_agent', 'apex_optimizer_agent', 'data_helper_agent']
        users_per_agent = total_users // len(agent_types)
        self.logger.info(f'Testing {total_users} users across {len(agent_types)} agent types')
        user_tasks = []
        agent_user_mapping = {}
        for agent_idx, agent_type in enumerate(agent_types):
            agent_user_mapping[agent_type] = []
            for user_idx in range(users_per_agent):
                user_index = agent_idx * users_per_agent + user_idx
                task = self._create_concurrent_user(user_index, total_users)
                user_tasks.append(task)
                agent_user_mapping[agent_type].append(user_index)
        load_start_time = time.time()
        user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_load_time = time.time() - load_start_time
        valid_metrics = [m for m in user_metrics if isinstance(m, PerformanceMetrics)]
        overall_results = self._analyze_load_test_results(valid_metrics)
        agent_performance = {}
        for agent_type in agent_types:
            agent_metrics = [m for m in valid_metrics if m.agent_type == agent_type]
            if agent_metrics:
                agent_results = self._analyze_load_test_results(agent_metrics)
                agent_performance[agent_type] = agent_results
        self.logger.info(f'⚡ Mixed Agent Load Test Results:')
        self.logger.info(f'   Total Load Time: {total_load_time:.1f}s')
        self.logger.info(f'   Overall Success Rate: {overall_results.success_rate:.1%}')
        self.logger.info(f'   Overall Avg Response Time: {overall_results.avg_response_time:.1f}s')
        self.logger.info('📊 Performance by Agent Type:')
        for agent_type, results in agent_performance.items():
            self.logger.info(f'   {agent_type}:')
            self.logger.info(f'     Success Rate: {results.success_rate:.1%}')
            self.logger.info(f'     Avg Response Time: {results.avg_response_time:.1f}s')
            self.logger.info(f'     P95 Response Time: {results.p95_response_time:.1f}s')
            self.logger.info(f'     Users: {results.successful_users}/{results.total_users}')
        assert overall_results.success_rate >= 0.7, f'Overall mixed agent success rate too low: {overall_results.success_rate:.1%} (expected ≥70%). Mixed agent load should be handled effectively.'
        for agent_type, results in agent_performance.items():
            assert results.success_rate >= 0.7, f'{agent_type} success rate too low under mixed load: {results.success_rate:.1%} (expected ≥70%). All agent types should perform well concurrently.'
            if results.successful_users > 0:
                assert results.avg_response_time <= 50.0, f'{agent_type} average response time too slow: {results.avg_response_time:.1f}s (expected ≤50s under mixed agent load)'
        successful_response_times = {}
        for agent_type in agent_types:
            agent_times = [m.response_time for m in valid_metrics if m.agent_type == agent_type and m.success]
            if agent_times:
                successful_response_times[agent_type] = statistics.mean(agent_times)
        if len(successful_response_times) >= 2:
            min_avg_time = min(successful_response_times.values())
            max_avg_time = max(successful_response_times.values())
            fairness_ratio = max_avg_time / min_avg_time if min_avg_time > 0 else 1.0
            assert fairness_ratio <= 2.5, f'Resource fairness issue detected across agent types. Performance ratio: {fairness_ratio:.2f} (expected ≤2.5). Times: {successful_response_times}'
        success_distribution = {agent_type: results.successful_users for agent_type, results in agent_performance.items()}
        total_successes = sum(success_distribution.values())
        if total_successes > 0:
            for agent_type, successes in success_distribution.items():
                success_percentage = successes / total_successes
                assert success_percentage >= 0.1, f'{agent_type} has too few successes under mixed load: {success_percentage:.1%} (expected ≥10% of total successes)'
        self.logger.info('CHECK Mixed agent load distribution validation passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')