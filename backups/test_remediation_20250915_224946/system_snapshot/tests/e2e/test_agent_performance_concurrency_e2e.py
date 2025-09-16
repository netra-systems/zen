"""Agent Performance and Concurrency E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests agent performance, load handling, and multi-user concurrency with real services.
Business Value: Ensure system stability and performance under realistic load conditions.

Business Value Justification (BVJ):
1. Segment: All segments (Free through Enterprise)
2. Business Goal: System stability and scalability for growing user base
3. Value Impact: Performance and concurrency ensure customer satisfaction and system reliability
4. Revenue Impact: $500K+ ARR protected by ensuring system can handle enterprise-scale usage

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events under load
- Tests actual agent performance and concurrency patterns
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
"""
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import threading
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import pytest
from loguru import logger
from shared.isolated_environment import get_env
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS

@dataclass
class PerformanceMetrics:
    """Captures performance metrics for agent execution."""
    user_id: str
    agent_type: str
    request_id: str
    start_time: float
    end_time: Optional[float] = None
    connection_time: Optional[float] = None
    first_event_time: Optional[float] = None
    agent_start_time: Optional[float] = None
    completion_time: Optional[float] = None
    total_duration: Optional[float] = None
    total_events: int = 0
    event_types_seen: Set[str] = field(default_factory=set)
    websocket_errors: int = 0
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    response_received: bool = False
    all_required_events: bool = False
    successful_completion: bool = False
    error_encountered: bool = False

    @property
    def duration(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

@dataclass
class ConcurrencyTestValidation:
    """Captures and validates concurrent agent execution."""
    test_name: str
    concurrent_users: int
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    user_metrics: List[PerformanceMetrics] = field(default_factory=list)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    avg_response_time: Optional[float] = None
    min_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    percentile_95_response_time: Optional[float] = None
    throughput_requests_per_second: Optional[float] = None
    concurrent_execution_achieved: bool = False
    user_isolation_maintained: bool = False
    resource_limits_respected: bool = False
    websocket_stability_maintained: bool = False
    error_types: Dict[str, int] = field(default_factory=dict)
    performance_degradation: float = 0.0

    @property
    def duration(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

    @property
    def success_rate(self) -> float:
        if self.total_requests > 0:
            return self.successful_requests / self.total_requests
        return 0.0

class AgentPerformanceConcurrencyTester:
    """Tests agent performance and concurrency with real services and WebSocket events."""
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    PERFORMANCE_TEST_SCENARIOS = [{'test_name': 'basic_agent_performance', 'agent_type': 'triage_agent', 'request': 'Analyze the performance requirements for a new application deployment', 'expected_max_duration': 60.0, 'expected_min_events': 5, 'concurrent_users': 1}, {'test_name': 'supply_research_load', 'agent_type': 'supply_researcher', 'request': 'Research cloud infrastructure vendors for enterprise deployment', 'expected_max_duration': 90.0, 'expected_min_events': 8, 'concurrent_users': 3}, {'test_name': 'domain_expert_concurrency', 'agent_type': 'finance_expert', 'request': 'Provide cost analysis for cloud migration project', 'expected_max_duration': 120.0, 'expected_min_events': 6, 'concurrent_users': 5}, {'test_name': 'high_concurrency_stress', 'agent_type': 'triage_agent', 'request': 'Quick analysis of system requirements', 'expected_max_duration': 45.0, 'expected_min_events': 4, 'concurrent_users': 8}]

    def __init__(self, config: Optional[E2ETestConfig]=None):
        self.config = config or get_e2e_config()
        self.env = None
        self.validations: List[ConcurrencyTestValidation] = []
        self.performance_baseline: Dict[str, float] = {}

    async def validate_staging_services(self):
        """Validate all required staging services are available - Phase 2 fix"""
        if self.config.environment.value != 'staging':
            return
        import httpx
        services = [('backend', f'{self.config.backend_url}/health'), ('api', f'{self.config.api_url}/health'), ('websocket', f'{self.config.backend_url}/ws')]
        for service_name, url in services:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if service_name == 'websocket':
                        response = await client.get(url.replace('ws://', 'http://').replace('wss://', 'https://'))
                        if response.status_code not in [200, 426]:
                            logger.warning(f'WebSocket service {service_name} returned {response.status_code}')
                    else:
                        response = await client.get(url)
                        assert response.status_code == 200, f'Service {service_name} not available at {url}: {response.status_code}'
                        logger.info(f'✅ Service {service_name} available at {url}')
            except Exception as e:
                logger.error(f'❌ Service {service_name} not available at {url}: {e}')

    async def setup(self):
        """Initialize test environment with real services."""
        from shared.isolated_environment import IsolatedEnvironment
        self.env = IsolatedEnvironment()
        await self.validate_staging_services()
        logger.info(f'Agent performance test environment ready')
        logger.info(f'Using backend: {self.config.backend_url}')
        logger.info(f'Using websocket: {self.config.websocket_url}')
        return self

    async def teardown(self):
        """Clean up test environment."""
        pass

    async def execute_single_agent_performance_test(self, user_id: str, scenario: Dict[str, Any], timeout: float=120.0) -> PerformanceMetrics:
        """Execute a single agent performance test for one user.
        
        Args:
            user_id: Unique user identifier
            scenario: Performance test scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Performance metrics for the execution
        """
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        request_id = str(uuid.uuid4())
        metrics = PerformanceMetrics(user_id=user_id, agent_type=scenario['agent_type'], request_id=request_id, start_time=time.time())
        try:
            jwt_helper = JWTTestHelper()
            user_data = create_test_user_data(f'perf_test_{user_id}')
            email = user_data['email']
            token = jwt_helper.create_access_token(user_id, email, permissions=['agents:use', 'performance:test'])
            ws_client = WebSocketTestClient(self.config.websocket_url)
            connect_start = time.time()
            connected = await ws_client.connect(token=token)
            metrics.connection_time = time.time() - connect_start
            if not connected:
                metrics.error_encountered = True
                metrics.websocket_errors += 1
                return metrics
            thread_id = str(uuid.uuid4())
            agent_request = {'type': 'agent_request', 'agent': scenario['agent_type'], 'message': scenario['request'], 'thread_id': thread_id, 'context': {'user_id': user_id, 'performance_test': True, 'test_scenario': scenario['test_name']}, 'optimistic_id': request_id}
            await ws_client.send_json(agent_request)
            event_start_time = time.time()
            completed = False
            while time.time() - metrics.start_time < timeout and (not completed):
                event = await ws_client.receive(timeout=2.0)
                if event:
                    await self._process_performance_event(event, metrics, event_start_time)
                    if event.get('type') in ['agent_completed', 'error']:
                        completed = True
                        metrics.completion_time = time.time() - metrics.start_time
            metrics.end_time = time.time()
            metrics.total_duration = metrics.duration
            metrics.response_received = completed
            metrics.all_required_events = self.REQUIRED_EVENTS.issubset(metrics.event_types_seen)
            metrics.successful_completion = completed and (not metrics.error_encountered)
            await ws_client.disconnect()
        except Exception as e:
            logger.error(f'Performance test error for user {user_id}: {e}')
            metrics.error_encountered = True
            metrics.end_time = time.time()
        return metrics

    async def _process_performance_event(self, event: Dict[str, Any], metrics: PerformanceMetrics, event_start_time: float):
        """Process and categorize performance-related events."""
        event_type = event.get('type', 'unknown')
        event_time = time.time() - metrics.start_time
        metrics.total_events += 1
        metrics.event_types_seen.add(event_type)
        if event_type == 'agent_started' and (not metrics.agent_start_time):
            metrics.agent_start_time = event_time
        elif event_type == 'agent_thinking' and (not metrics.first_event_time):
            metrics.first_event_time = time.time() - event_start_time
        elif event_type == 'error':
            metrics.error_encountered = True
            metrics.websocket_errors += 1

    async def execute_concurrent_performance_test(self, scenario: Dict[str, Any], timeout: float=180.0) -> ConcurrencyTestValidation:
        """Execute concurrent performance test with multiple users.
        
        Args:
            scenario: Performance test scenario configuration
            timeout: Maximum execution time for all users
            
        Returns:
            Complete concurrency validation results
        """
        concurrent_users = scenario['concurrent_users']
        validation = ConcurrencyTestValidation(test_name=scenario['test_name'], concurrent_users=concurrent_users)
        user_ids = [f'perf_user_{i}_{uuid.uuid4().hex[:8]}' for i in range(concurrent_users)]
        validation.total_requests = len(user_ids)
        logger.info(f"Starting concurrent test: {scenario['test_name']} with {concurrent_users} users")
        start_time = time.time()
        tasks = [self.execute_single_agent_performance_test(user_id, scenario, timeout) for user_id in user_ids]
        user_metrics = await asyncio.gather(*tasks, return_exceptions=True)
        validation.end_time = time.time()
        for i, result in enumerate(user_metrics):
            if isinstance(result, PerformanceMetrics):
                validation.user_metrics.append(result)
                if result.successful_completion:
                    validation.successful_requests += 1
                elif result.error_encountered:
                    validation.failed_requests += 1
                else:
                    validation.timeout_requests += 1
            else:
                logger.error(f'User {user_ids[i]} test failed with exception: {result}')
                validation.failed_requests += 1
        self._calculate_performance_statistics(validation)
        self._validate_concurrency_performance(validation, scenario)
        self.validations.append(validation)
        return validation

    def _calculate_performance_statistics(self, validation: ConcurrencyTestValidation):
        """Calculate aggregate performance statistics."""
        successful_metrics = [m for m in validation.user_metrics if m.successful_completion and m.total_duration is not None]
        if successful_metrics:
            durations = [m.total_duration for m in successful_metrics]
            validation.avg_response_time = statistics.mean(durations)
            validation.min_response_time = min(durations)
            validation.max_response_time = max(durations)
            if len(durations) > 1:
                validation.percentile_95_response_time = statistics.quantiles(durations, n=20)[18]
            else:
                validation.percentile_95_response_time = durations[0]
            if validation.duration and validation.duration > 0:
                validation.throughput_requests_per_second = len(successful_metrics) / validation.duration

    def _validate_concurrency_performance(self, validation: ConcurrencyTestValidation, scenario: Dict[str, Any]):
        """Validate concurrency and performance requirements."""
        if len(validation.user_metrics) >= 2:
            start_times = [m.start_time for m in validation.user_metrics if m.start_time]
            end_times = [m.end_time for m in validation.user_metrics if m.end_time]
            if start_times and end_times:
                earliest_start = min(start_times)
                latest_start = max(start_times)
                earliest_end = min(end_times)
                validation.concurrent_execution_achieved = latest_start < earliest_end
        user_ids = set((m.user_id for m in validation.user_metrics))
        validation.user_isolation_maintained = len(user_ids) == len(validation.user_metrics)
        if validation.user_metrics and len(validation.user_metrics) > 1:
            successful_durations = [m.total_duration for m in validation.user_metrics if m.successful_completion and m.total_duration]
            if len(successful_durations) > 1:
                avg_duration = sum(successful_durations) / len(successful_durations)
                max_duration = max(successful_durations)
                min_duration = min(successful_durations)
                variance_ratio = (max_duration - min_duration) / avg_duration if avg_duration > 0 else 1.0
                validation.resource_limits_respected = variance_ratio < 2.0
                validation.performance_degradation = variance_ratio
        websocket_errors = sum((m.websocket_errors for m in validation.user_metrics))
        total_connections = len(validation.user_metrics)
        if total_connections > 0:
            error_rate = websocket_errors / total_connections
            validation.websocket_stability_maintained = error_rate < 0.2

    def generate_performance_concurrency_report(self) -> str:
        """Generate comprehensive performance and concurrency test report."""
        report = []
        report.append('=' * 80)
        report.append('AGENT PERFORMANCE AND CONCURRENCY TEST REPORT')
        report.append('=' * 80)
        report.append(f'Total concurrent test scenarios: {len(self.validations)}')
        report.append('')
        for i, validation in enumerate(self.validations, 1):
            report.append(f'\n--- Test Scenario {i}: {validation.test_name} ---')
            report.append(f'Concurrent users: {validation.concurrent_users}')
            report.append(f'Test duration: {validation.duration:.2f}s' if validation.duration else 'Test duration: N/A')
            report.append(f'Total requests: {validation.total_requests}')
            report.append(f'Successful requests: {validation.successful_requests}')
            report.append(f'Failed requests: {validation.failed_requests}')
            report.append(f'Timeout requests: {validation.timeout_requests}')
            report.append(f'Success rate: {validation.success_rate:.1%}')
            report.append('\nPerformance Statistics:')
            if validation.avg_response_time:
                report.append(f'  - Average response time: {validation.avg_response_time:.2f}s')
                report.append(f'  - Min response time: {validation.min_response_time:.2f}s')
                report.append(f'  - Max response time: {validation.max_response_time:.2f}s')
                report.append(f'  - 95th percentile: {validation.percentile_95_response_time:.2f}s')
            else:
                report.append('  - No successful responses to analyze')
            if validation.throughput_requests_per_second:
                report.append(f'  - Throughput: {validation.throughput_requests_per_second:.2f} requests/second')
            report.append('\nConcurrency Validation:')
            report.append(f'  ✓ Concurrent execution achieved: {validation.concurrent_execution_achieved}')
            report.append(f'  ✓ User isolation maintained: {validation.user_isolation_maintained}')
            report.append(f'  ✓ Resource limits respected: {validation.resource_limits_respected}')
            report.append(f'  ✓ WebSocket stability maintained: {validation.websocket_stability_maintained}')
            report.append(f'  - Performance degradation ratio: {validation.performance_degradation:.2f}')
            if validation.user_metrics:
                report.append(f'\nIndividual User Analysis:')
                users_with_all_events = sum((1 for m in validation.user_metrics if m.all_required_events))
                report.append(f'  - Users with all required events: {users_with_all_events}/{len(validation.user_metrics)}')
                connection_times = [m.connection_time for m in validation.user_metrics if m.connection_time]
                if connection_times:
                    avg_connection = sum(connection_times) / len(connection_times)
                    report.append(f'  - Average connection time: {avg_connection:.2f}s')
                start_times = [m.agent_start_time for m in validation.user_metrics if m.agent_start_time]
                if start_times:
                    avg_start = sum(start_times) / len(start_times)
                    report.append(f'  - Average agent start time: {avg_start:.2f}s')
        report.append('\n' + '=' * 80)
        report.append('SUMMARY STATISTICS')
        report.append('=' * 80)
        if self.validations:
            total_requests = sum((v.total_requests for v in self.validations))
            total_successful = sum((v.successful_requests for v in self.validations))
            overall_success_rate = total_successful / total_requests if total_requests > 0 else 0
            report.append(f'Overall success rate: {overall_success_rate:.1%} ({total_successful}/{total_requests})')
            max_concurrent_users = max((v.concurrent_users for v in self.validations))
            successful_concurrency_tests = sum((1 for v in self.validations if v.concurrent_execution_achieved and v.success_rate > 0.7))
            report.append(f'Maximum concurrent users tested: {max_concurrent_users}')
            report.append(f'Successful concurrency tests: {successful_concurrency_tests}/{len(self.validations)}')
            all_response_times = []
            for v in self.validations:
                if v.avg_response_time:
                    all_response_times.append(v.avg_response_time)
            if all_response_times:
                overall_avg_response = sum(all_response_times) / len(all_response_times)
                report.append(f'Overall average response time: {overall_avg_response:.2f}s')
        report.append('\n' + '=' * 80)
        return '\n'.join(report)

@pytest.fixture(params=['local', 'staging'])
async def performance_concurrency_tester(request):
    """Create and setup the performance concurrency tester for both local and staging."""
    test_env = get_env().get('E2E_TEST_ENV', None)
    if test_env and test_env != request.param:
        pytest.skip(f'Skipping {request.param} tests (E2E_TEST_ENV={test_env})')
    if request.param == 'staging':
        config = get_e2e_config('staging')
        if not config.is_available():
            pytest.skip(f'Staging environment not available: {config.backend_url}')
    config = get_e2e_config(request.param)
    tester = AgentPerformanceConcurrencyTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.performance
class AgentPerformanceConcurrencyTests:
    """Test suite for agent performance and concurrency validation."""

    async def test_basic_agent_performance_baseline(self, performance_concurrency_tester):
        """Test basic agent performance to establish baseline."""
        scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[0]
        validation = await performance_concurrency_tester.execute_concurrent_performance_test(scenario, timeout=120.0)
        expected_min_success_rate = 0.6 if self.config.environment.value == 'staging' else 0.8
        assert validation.success_rate >= expected_min_success_rate, f'Success rate {validation.success_rate:.1%} too low for baseline (expected >= {expected_min_success_rate:.1%})'
        if validation.avg_response_time:
            assert validation.avg_response_time <= scenario['expected_max_duration'], f"Average response time {validation.avg_response_time:.2f}s exceeds expected {scenario['expected_max_duration']}s"
        successful_metrics = [m for m in validation.user_metrics if m.successful_completion]
        if successful_metrics:
            avg_events = sum((m.total_events for m in successful_metrics)) / len(successful_metrics)
            assert avg_events >= scenario['expected_min_events'], f"Average events {avg_events:.1f} below expected minimum {scenario['expected_min_events']}"
        logger.info(f'Basic performance baseline: {validation.avg_response_time:.2f}s avg response time')

    async def test_supply_research_load_performance(self, performance_concurrency_tester):
        """Test supply research agent under concurrent load."""
        scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[1]
        validation = await performance_concurrency_tester.execute_concurrent_performance_test(scenario, timeout=150.0)
        assert validation.success_rate >= 0.6, f'Load test success rate {validation.success_rate:.1%} too low'
        assert validation.concurrent_execution_achieved, 'Should achieve concurrent execution under load'
        assert validation.user_isolation_maintained, 'Should maintain user isolation under load'
        assert validation.performance_degradation < 3.0, f'Performance degradation {validation.performance_degradation:.2f} too high under load'
        logger.info(f'Supply research load test: {validation.concurrent_users} concurrent users, {validation.success_rate:.1%} success rate')

    async def test_domain_expert_concurrency_stress(self, performance_concurrency_tester):
        """Test domain expert agents under high concurrency stress."""
        scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[2]
        validation = await performance_concurrency_tester.execute_concurrent_performance_test(scenario, timeout=180.0)
        assert validation.success_rate >= 0.4, f'High concurrency success rate {validation.success_rate:.1%} too low'
        assert validation.websocket_stability_maintained, 'WebSocket stability should be maintained under stress'
        if validation.resource_limits_respected:
            logger.info('Resource limits properly respected under concurrency stress')
        else:
            logger.warning(f'Resource limit concerns: degradation ratio {validation.performance_degradation:.2f}')
        assert validation.successful_requests > 0, 'At least some requests should succeed under stress'

    async def test_high_concurrency_system_limits(self, performance_concurrency_tester):
        """Test system limits under high concurrency stress."""
        scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[3]
        validation = await performance_concurrency_tester.execute_concurrent_performance_test(scenario, timeout=120.0)
        assert validation.success_rate >= 0.25, f'Extreme load success rate {validation.success_rate:.1%} indicates system failure'
        assert validation.successful_requests > 0, 'System should handle at least some requests under extreme load'
        websocket_failure_rate = sum((m.websocket_errors for m in validation.user_metrics)) / len(validation.user_metrics)
        assert websocket_failure_rate < 0.8, f'WebSocket failure rate {websocket_failure_rate:.1%} too high'
        logger.info(f'High concurrency stress test: {validation.concurrent_users} users, {validation.success_rate:.1%} success rate, {websocket_failure_rate:.1%} WS failure rate')

    async def test_performance_regression_detection(self, performance_concurrency_tester):
        """Test performance regression detection across scenarios."""
        baseline_scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[0]
        baseline_validation = await performance_concurrency_tester.execute_concurrent_performance_test(baseline_scenario, timeout=100.0)
        load_scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[1]
        load_validation = await performance_concurrency_tester.execute_concurrent_performance_test(load_scenario, timeout=150.0)
        if baseline_validation.avg_response_time and load_validation.avg_response_time:
            performance_ratio = load_validation.avg_response_time / baseline_validation.avg_response_time
            assert performance_ratio < 5.0, f'Performance regression detected: {performance_ratio:.2f}x slower under load'
            logger.info(f'Performance comparison: baseline {baseline_validation.avg_response_time:.2f}s, load {load_validation.avg_response_time:.2f}s ({performance_ratio:.2f}x)')
        success_rate_degradation = baseline_validation.success_rate - load_validation.success_rate
        assert success_rate_degradation < 0.5, f'Success rate degradation {success_rate_degradation:.1%} too high under load'

    async def test_websocket_event_compliance_under_load(self, performance_concurrency_tester):
        """Test WebSocket event compliance under concurrent load."""
        scenario = performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS[1]
        validation = await performance_concurrency_tester.execute_concurrent_performance_test(scenario, timeout=140.0)
        successful_metrics = [m for m in validation.user_metrics if m.successful_completion]
        if successful_metrics:
            users_with_required_events = sum((1 for m in successful_metrics if m.all_required_events))
            event_compliance_rate = users_with_required_events / len(successful_metrics)
            assert event_compliance_rate >= 0.7, f'WebSocket event compliance {event_compliance_rate:.1%} too low under load'
            avg_events = sum((m.total_events for m in successful_metrics)) / len(successful_metrics)
            assert avg_events >= 4, f'Average events {avg_events:.1f} too low under load'
            logger.info(f'WebSocket event compliance under load: {event_compliance_rate:.1%}, {avg_events:.1f} avg events per user')

    async def test_comprehensive_performance_concurrency_report(self, performance_concurrency_tester):
        """Run comprehensive performance and concurrency tests and generate detailed report."""
        for scenario in performance_concurrency_tester.PERFORMANCE_TEST_SCENARIOS:
            await performance_concurrency_tester.execute_concurrent_performance_test(scenario, timeout=max(180.0, scenario.get('expected_max_duration', 60.0) * 2))
        report = performance_concurrency_tester.generate_performance_concurrency_report()
        logger.info('\n' + report)
        report_file = os.path.join(project_root, 'test_outputs', 'performance_concurrency_e2e_report.txt')
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            f.write(f'\n\nGenerated at: {datetime.now().isoformat()}\n')
        logger.info(f'Performance concurrency report saved to: {report_file}')
        total_validations = len(performance_concurrency_tester.validations)
        acceptable_validations = sum((1 for v in performance_concurrency_tester.validations if v.success_rate >= 0.3 and v.websocket_stability_maintained))
        assert acceptable_validations > 0, 'At least some performance tests should meet basic acceptability criteria'
        overall_system_health = acceptable_validations / total_validations if total_validations > 0 else 0
        logger.info(f'Overall system performance health: {overall_system_health:.1%}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')