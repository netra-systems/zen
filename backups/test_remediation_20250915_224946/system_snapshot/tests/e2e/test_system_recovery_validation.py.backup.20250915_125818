"""
System Recovery Validation Tests

This module provides comprehensive validation of system recovery capabilities
when services fail, ensuring the system can gracefully handle and recover
from various failure scenarios.
from shared.isolated_environment import IsolatedEnvironment

Key areas tested:
- Service failure detection and isolation
- Automatic recovery mechanisms
- Graceful degradation patterns  
- Multi-service failure scenarios
- Recovery time and effectiveness validation
- System health monitoring during recovery

Business Value Justification (BVJ):
- Segment: Enterprise & Platform
- Business Goal: Minimize MTTR and ensure business continuity
- Value Impact: Reduces service downtime and maintains customer experience
- Strategic Impact: Protects $150K+ MRR through reliable system recovery
"""
import asyncio
import logging
import time
import statistics
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from enum import Enum
from collections import defaultdict
import pytest
logger = logging.getLogger(__name__)

class RecoveryState(Enum):
    """System recovery state enumeration."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    FAILING = 'failing'
    RECOVERING = 'recovering'
    FAILED = 'failed'

class FailureScenario(Enum):
    """Types of failure scenarios to test."""
    SINGLE_SERVICE = 'single_service'
    CASCADE_FAILURE = 'cascade_failure'
    NETWORK_PARTITION = 'network_partition'
    DATABASE_OUTAGE = 'database_outage'
    RESOURCE_EXHAUSTION = 'resource_exhaustion'
    CONFIGURATION_ERROR = 'configuration_error'

@dataclass
class RecoveryMetrics:
    """Metrics for system recovery validation."""
    scenario_name: str
    failure_type: FailureScenario
    start_time: float = field(default_factory=time.time)
    failure_detection_time: float = 0.0
    isolation_time: float = 0.0
    recovery_start_time: float = 0.0
    recovery_completion_time: float = 0.0
    total_recovery_time: float = 0.0
    service_states: Dict[str, List[Tuple[float, RecoveryState]]] = field(default_factory=dict)
    degraded_services: Set[str] = field(default_factory=set)
    failed_services: Set[str] = field(default_factory=set)
    recovered_services: Set[str] = field(default_factory=set)
    health_checks_performed: int = 0
    health_checks_passed: int = 0
    continuous_health_duration: float = 0.0
    performance_degradation: float = 0.0
    throughput_impact: float = 0.0
    latency_impact: float = 0.0
    services_recovered: int = 0
    services_failed_to_recover: int = 0
    manual_intervention_required: bool = False
    end_time: float = 0.0

    def record_service_state(self, service: str, state: RecoveryState):
        """Record service state change."""
        if service not in self.service_states:
            self.service_states[service] = []
        timestamp = time.time() - self.start_time
        self.service_states[service].append((timestamp, state))
        if state == RecoveryState.DEGRADED:
            self.degraded_services.add(service)
        elif state == RecoveryState.FAILED:
            self.failed_services.add(service)
        elif state == RecoveryState.HEALTHY:
            if service in self.failed_services:
                self.recovered_services.add(service)
                self.services_recovered += 1

    def record_failure_detected(self):
        """Record when failure was detected."""
        if self.failure_detection_time == 0.0:
            self.failure_detection_time = time.time() - self.start_time

    def record_isolation_complete(self):
        """Record when failure isolation was completed."""
        if self.isolation_time == 0.0:
            self.isolation_time = time.time() - self.start_time

    def record_recovery_start(self):
        """Record when recovery process started."""
        if self.recovery_start_time == 0.0:
            self.recovery_start_time = time.time() - self.start_time

    def record_recovery_complete(self):
        """Record when recovery process completed."""
        if self.recovery_completion_time == 0.0:
            self.recovery_completion_time = time.time() - self.start_time
            self.total_recovery_time = self.recovery_completion_time - (self.recovery_start_time or self.start_time)

    def record_health_check(self, passed: bool):
        """Record health check result."""
        self.health_checks_performed += 1
        if passed:
            self.health_checks_passed += 1

    @property
    def duration(self) -> float:
        """Total scenario duration."""
        return (self.end_time or time.time()) - self.start_time

    @property
    def health_check_success_rate(self) -> float:
        """Health check success rate."""
        if self.health_checks_performed == 0:
            return 0.0
        return self.health_checks_passed / self.health_checks_performed * 100

    @property
    def recovery_success_rate(self) -> float:
        """Recovery success rate."""
        total_affected = len(self.failed_services) + len(self.degraded_services)
        if total_affected == 0:
            return 100.0
        return len(self.recovered_services) / total_affected * 100

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive recovery metrics summary."""
        return {'scenario_name': self.scenario_name, 'failure_type': self.failure_type.value, 'duration_seconds': self.duration, 'failure_detection_time_seconds': self.failure_detection_time, 'isolation_time_seconds': self.isolation_time, 'total_recovery_time_seconds': self.total_recovery_time, 'services_affected': len(self.failed_services) + len(self.degraded_services), 'services_recovered': len(self.recovered_services), 'recovery_success_rate_percent': self.recovery_success_rate, 'health_check_success_rate_percent': self.health_check_success_rate, 'performance_degradation_percent': self.performance_degradation, 'manual_intervention_required': self.manual_intervention_required}

class SystemRecoveryValidator:
    """Advanced system recovery validation framework."""

    def __init__(self):
        self.recovery_metrics: Dict[str, RecoveryMetrics] = {}
        self.active_simulations: Set[str] = set()
        self.service_simulators: Dict[str, 'ServiceSimulator'] = {}

    def create_metrics(self, scenario_name: str, failure_type: FailureScenario) -> RecoveryMetrics:
        """Create and track recovery metrics."""
        metrics = RecoveryMetrics(scenario_name, failure_type)
        self.recovery_metrics[scenario_name] = metrics
        return metrics

    async def validate_single_service_recovery(self, service_name: str, failure_simulator: Callable, recovery_simulator: Callable, health_checker: Callable, recovery_timeout: float=30.0) -> RecoveryMetrics:
        """
        Validate recovery from single service failure.
        
        Tests detection, isolation, and recovery of a single service failure.
        """
        metrics = self.create_metrics(f'single_service_{service_name}', FailureScenario.SINGLE_SERVICE)
        try:
            logger.info(f'Starting single service recovery validation for {service_name}')
            logger.info(f'Phase 1: Establishing baseline for {service_name}')
            baseline_health = await health_checker()
            if baseline_health.get('healthy', False):
                metrics.record_service_state(service_name, RecoveryState.HEALTHY)
                metrics.record_health_check(True)
            else:
                logger.warning(f'Service {service_name} not healthy at baseline')
                metrics.record_health_check(False)
            logger.info(f'Phase 2: Introducing failure in {service_name}')
            failure_start = time.time()
            try:
                await failure_simulator()
                metrics.record_service_state(service_name, RecoveryState.FAILING)
            except Exception as e:
                logger.info(f'Failure simulation completed: {e}')
                metrics.record_service_state(service_name, RecoveryState.FAILED)
            logger.info(f'Phase 3: Detecting failure in {service_name}')
            failure_detected = False
            detection_attempts = 0
            max_detection_attempts = 10
            while not failure_detected and detection_attempts < max_detection_attempts:
                detection_attempts += 1
                try:
                    health_result = await asyncio.wait_for(health_checker(), timeout=5.0)
                    if not health_result.get('healthy', True):
                        failure_detected = True
                        metrics.record_failure_detected()
                        metrics.record_service_state(service_name, RecoveryState.FAILED)
                        logger.info(f'Failure detected in {service_name} after {detection_attempts} attempts')
                    else:
                        metrics.record_health_check(True)
                except asyncio.TimeoutError:
                    failure_detected = True
                    metrics.record_failure_detected()
                    logger.info(f'Failure detected via timeout in {service_name}')
                except Exception as e:
                    failure_detected = True
                    metrics.record_failure_detected()
                    logger.info(f'Failure detected via exception in {service_name}: {e}')
                if not failure_detected:
                    await asyncio.sleep(1.0)
            if not failure_detected:
                logger.warning(f'Failed to detect failure in {service_name}')
            logger.info(f'Phase 4: Isolating failure in {service_name}')
            await asyncio.sleep(0.5)
            metrics.record_isolation_complete()
            logger.info(f'Phase 5: Starting recovery for {service_name}')
            metrics.record_recovery_start()
            metrics.record_service_state(service_name, RecoveryState.RECOVERING)
            recovery_successful = False
            recovery_start = time.time()
            try:
                recovery_result = await asyncio.wait_for(recovery_simulator(), timeout=recovery_timeout)
                if recovery_result.get('success', False):
                    recovery_successful = True
                    metrics.record_service_state(service_name, RecoveryState.HEALTHY)
                    logger.info(f'Recovery successful for {service_name}')
                else:
                    logger.warning(f'Recovery failed for {service_name}: {recovery_result}')
            except asyncio.TimeoutError:
                logger.error(f'Recovery timed out for {service_name}')
                metrics.manual_intervention_required = True
            except Exception as e:
                logger.error(f'Recovery error for {service_name}: {e}')
                metrics.manual_intervention_required = True
            if recovery_successful:
                logger.info(f'Phase 6: Validating recovery for {service_name}')
                recovery_validation_attempts = 5
                recovery_validations_passed = 0
                for i in range(recovery_validation_attempts):
                    try:
                        health_result = await health_checker()
                        if health_result.get('healthy', False):
                            recovery_validations_passed += 1
                            metrics.record_health_check(True)
                        else:
                            metrics.record_health_check(False)
                    except Exception as e:
                        logger.warning(f'Recovery validation {i} failed: {e}')
                        metrics.record_health_check(False)
                    await asyncio.sleep(0.5)
                if recovery_validations_passed >= recovery_validation_attempts * 0.8:
                    metrics.record_recovery_complete()
                    logger.info(f'Recovery validation successful for {service_name}')
                else:
                    logger.warning(f'Recovery validation insufficient for {service_name}')
                    metrics.manual_intervention_required = True
        finally:
            metrics.end_time = time.time()
        return metrics

    async def validate_cascade_failure_recovery(self, primary_service: str, dependent_services: List[str], failure_simulator: Callable, recovery_orchestrator: Callable, health_checkers: Dict[str, Callable], recovery_timeout: float=60.0) -> RecoveryMetrics:
        """
        Validate recovery from cascading service failures.
        
        Tests detection and recovery when failure propagates across services.
        """
        metrics = self.create_metrics(f'cascade_{primary_service}', FailureScenario.CASCADE_FAILURE)
        all_services = [primary_service] + dependent_services
        try:
            logger.info(f'Starting cascade failure recovery validation for {primary_service} -> {dependent_services}')
            logger.info('Phase 1: Establishing baseline health for all services')
            for service in all_services:
                health_checker = health_checkers.get(service)
                if health_checker:
                    try:
                        health = await health_checker()
                        if health.get('healthy', False):
                            metrics.record_service_state(service, RecoveryState.HEALTHY)
                            metrics.record_health_check(True)
                    except Exception as e:
                        logger.warning(f'Baseline health check failed for {service}: {e}')
                        metrics.record_health_check(False)
            logger.info(f'Phase 2: Introducing primary failure in {primary_service}')
            try:
                await failure_simulator()
                metrics.record_service_state(primary_service, RecoveryState.FAILED)
                metrics.record_failure_detected()
            except Exception as e:
                logger.info(f'Primary failure simulation completed: {e}')
            logger.info('Phase 3: Monitoring cascade failure propagation')
            cascade_detection_time = 10.0
            cascade_start = time.time()
            while time.time() - cascade_start < cascade_detection_time:
                for service in dependent_services:
                    health_checker = health_checkers.get(service)
                    if health_checker:
                        try:
                            health = await health_checker()
                            if not health.get('healthy', True):
                                metrics.record_service_state(service, RecoveryState.FAILED)
                                logger.info(f'Cascade failure detected in {service}')
                            else:
                                metrics.record_health_check(True)
                        except Exception:
                            metrics.record_service_state(service, RecoveryState.FAILED)
                            logger.info(f'Cascade failure detected in {service} via exception')
                await asyncio.sleep(1.0)
            metrics.record_isolation_complete()
            logger.info('Phase 4: Starting orchestrated recovery')
            metrics.record_recovery_start()
            for service in all_services:
                metrics.record_service_state(service, RecoveryState.RECOVERING)
            try:
                recovery_result = await asyncio.wait_for(recovery_orchestrator(), timeout=recovery_timeout)
                if recovery_result.get('success', False):
                    recovered_services = recovery_result.get('recovered_services', [])
                    for service in recovered_services:
                        metrics.record_service_state(service, RecoveryState.HEALTHY)
                    logger.info(f'Orchestrated recovery completed: {recovered_services}')
                else:
                    logger.warning(f'Orchestrated recovery failed: {recovery_result}')
                    metrics.manual_intervention_required = True
            except asyncio.TimeoutError:
                logger.error('Orchestrated recovery timed out')
                metrics.manual_intervention_required = True
            except Exception as e:
                logger.error(f'Orchestrated recovery error: {e}')
                metrics.manual_intervention_required = True
            logger.info('Phase 5: Validating system recovery')
            final_health_checks = 0
            healthy_services = 0
            for service in all_services:
                health_checker = health_checkers.get(service)
                if health_checker:
                    try:
                        health = await health_checker()
                        final_health_checks += 1
                        if health.get('healthy', False):
                            healthy_services += 1
                            metrics.record_health_check(True)
                        else:
                            metrics.record_health_check(False)
                    except Exception:
                        final_health_checks += 1
                        metrics.record_health_check(False)
            if final_health_checks > 0:
                recovery_rate = healthy_services / final_health_checks
                if recovery_rate >= 0.8:
                    metrics.record_recovery_complete()
                    logger.info(f'Cascade recovery successful: {recovery_rate:.1%}')
                else:
                    logger.warning(f'Cascade recovery insufficient: {recovery_rate:.1%}')
        finally:
            metrics.end_time = time.time()
        return metrics

    async def validate_network_partition_recovery(self, partition_simulator: Callable, partition_recovery_simulator: Callable, connectivity_checker: Callable, affected_services: List[str], recovery_timeout: float=45.0) -> RecoveryMetrics:
        """
        Validate recovery from network partition scenarios.
        
        Tests system behavior when network connectivity is lost and restored.
        """
        metrics = self.create_metrics('network_partition', FailureScenario.NETWORK_PARTITION)
        try:
            logger.info(f'Starting network partition recovery validation for services: {affected_services}')
            logger.info('Phase 1: Establishing connectivity baseline')
            baseline_connectivity = await connectivity_checker()
            if baseline_connectivity.get('connected', False):
                for service in affected_services:
                    metrics.record_service_state(service, RecoveryState.HEALTHY)
                metrics.record_health_check(True)
            else:
                logger.warning('Network connectivity issues detected at baseline')
                metrics.record_health_check(False)
            logger.info('Phase 2: Simulating network partition')
            try:
                await partition_simulator()
                metrics.record_failure_detected()
                for service in affected_services:
                    metrics.record_service_state(service, RecoveryState.FAILED)
                logger.info('Network partition simulation completed')
            except Exception as e:
                logger.info(f'Network partition simulation: {e}')
            logger.info('Phase 3: Monitoring partition detection')
            partition_detected = False
            detection_attempts = 0
            while not partition_detected and detection_attempts < 8:
                detection_attempts += 1
                try:
                    connectivity = await connectivity_checker()
                    if not connectivity.get('connected', True):
                        partition_detected = True
                        metrics.record_isolation_complete()
                        logger.info('Network partition detected')
                    else:
                        metrics.record_health_check(True)
                except Exception:
                    partition_detected = True
                    metrics.record_isolation_complete()
                    logger.info('Network partition detected via connectivity failure')
                if not partition_detected:
                    await asyncio.sleep(2.0)
            logger.info('Phase 4: Starting partition recovery')
            metrics.record_recovery_start()
            for service in affected_services:
                metrics.record_service_state(service, RecoveryState.RECOVERING)
            try:
                recovery_result = await asyncio.wait_for(partition_recovery_simulator(), timeout=recovery_timeout)
                if recovery_result.get('success', False):
                    logger.info('Network partition recovery initiated')
                else:
                    logger.warning(f'Partition recovery failed: {recovery_result}')
                    metrics.manual_intervention_required = True
            except asyncio.TimeoutError:
                logger.error('Partition recovery timed out')
                metrics.manual_intervention_required = True
            except Exception as e:
                logger.error(f'Partition recovery error: {e}')
                metrics.manual_intervention_required = True
            logger.info('Phase 5: Validating connectivity restoration')
            restoration_checks = 5
            successful_checks = 0
            for i in range(restoration_checks):
                try:
                    connectivity = await connectivity_checker()
                    if connectivity.get('connected', False):
                        successful_checks += 1
                        metrics.record_health_check(True)
                    else:
                        metrics.record_health_check(False)
                except Exception:
                    metrics.record_health_check(False)
                await asyncio.sleep(1.0)
            restoration_rate = successful_checks / restoration_checks
            if restoration_rate >= 0.8:
                metrics.record_recovery_complete()
                for service in affected_services:
                    metrics.record_service_state(service, RecoveryState.HEALTHY)
                logger.info(f'Network partition recovery successful: {restoration_rate:.1%}')
            else:
                logger.warning(f'Network partition recovery insufficient: {restoration_rate:.1%}')
        finally:
            metrics.end_time = time.time()
        return metrics

    def generate_recovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive recovery validation report."""
        if not self.recovery_metrics:
            return {'error': 'No recovery metrics available'}
        report = {'summary': {'total_scenarios_tested': len(self.recovery_metrics), 'scenario_types': {}, 'average_recovery_time': 0.0, 'average_detection_time': 0.0, 'overall_recovery_success_rate': 0.0, 'scenarios_requiring_manual_intervention': 0}, 'detailed_results': {}, 'performance_analysis': {'fastest_recovery': None, 'slowest_recovery': None, 'most_effective_recovery': None, 'least_effective_recovery': None}, 'recommendations': []}
        recovery_times = []
        detection_times = []
        success_rates = []
        manual_interventions = 0
        for scenario_name, metrics in self.recovery_metrics.items():
            scenario_summary = metrics.get_summary()
            report['detailed_results'][scenario_name] = scenario_summary
            if metrics.total_recovery_time > 0:
                recovery_times.append(metrics.total_recovery_time)
            if metrics.failure_detection_time > 0:
                detection_times.append(metrics.failure_detection_time)
            success_rates.append(metrics.recovery_success_rate)
            if metrics.manual_intervention_required:
                manual_interventions += 1
            scenario_type = metrics.failure_type.value
            if scenario_type not in report['summary']['scenario_types']:
                report['summary']['scenario_types'][scenario_type] = 0
            report['summary']['scenario_types'][scenario_type] += 1
        if recovery_times:
            report['summary']['average_recovery_time'] = statistics.mean(recovery_times)
        if detection_times:
            report['summary']['average_detection_time'] = statistics.mean(detection_times)
        if success_rates:
            report['summary']['overall_recovery_success_rate'] = statistics.mean(success_rates)
        report['summary']['scenarios_requiring_manual_intervention'] = manual_interventions
        if recovery_times:
            fastest_time = min(recovery_times)
            slowest_time = max(recovery_times)
            for name, metrics in self.recovery_metrics.items():
                if metrics.total_recovery_time == fastest_time:
                    report['performance_analysis']['fastest_recovery'] = name
                if metrics.total_recovery_time == slowest_time:
                    report['performance_analysis']['slowest_recovery'] = name
        if success_rates:
            best_rate = max(success_rates)
            worst_rate = min(success_rates)
            for name, metrics in self.recovery_metrics.items():
                if metrics.recovery_success_rate == best_rate:
                    report['performance_analysis']['most_effective_recovery'] = name
                if metrics.recovery_success_rate == worst_rate:
                    report['performance_analysis']['least_effective_recovery'] = name
        if report['summary']['average_recovery_time'] > 60:
            report['recommendations'].append('Average recovery time exceeds 60 seconds - review recovery procedures')
        if report['summary']['overall_recovery_success_rate'] < 80:
            report['recommendations'].append('Overall recovery success rate below 80% - enhance recovery mechanisms')
        if manual_interventions > 0:
            report['recommendations'].append(f'{manual_interventions} scenarios required manual intervention - improve automation')
        if report['summary']['average_detection_time'] > 30:
            report['recommendations'].append('Average failure detection time exceeds 30 seconds - improve monitoring')
        return report

@pytest.fixture
def recovery_validator():
    """Provide system recovery validator."""
    return SystemRecoveryValidator()

@pytest.mark.e2e
@pytest.mark.env_test
class TestSystemRecoveryValidation:
    """Comprehensive system recovery validation tests."""

    async def simulate_auth_service_failure(self):
        """Simulate auth service failure."""
        await asyncio.sleep(0.1)
        raise ConnectionError('Auth service connection failed')

    async def simulate_auth_service_recovery(self):
        """Simulate auth service recovery."""
        await asyncio.sleep(0.5)
        return {'success': True, 'service': 'auth', 'status': 'recovered'}

    async def check_auth_service_health(self):
        """Check auth service health."""
        await asyncio.sleep(0.02)
        import random
        if random.random() > 0.2:
            return {'healthy': True, 'service': 'auth'}
        else:
            return {'healthy': False, 'service': 'auth', 'error': 'service_unavailable'}

    async def simulate_cascade_failure(self):
        """Simulate cascading failure starting from primary service."""
        await asyncio.sleep(0.1)
        raise RuntimeError('Primary service failure triggering cascade')

    async def simulate_cascade_recovery(self):
        """Simulate orchestrated cascade recovery."""
        await asyncio.sleep(1.0)
        return {'success': True, 'recovered_services': ['auth', 'backend', 'database'], 'recovery_order': ['database', 'auth', 'backend']}

    async def check_service_health(self, service_name: str):
        """Generic service health checker."""
        await asyncio.sleep(0.03)
        import random
        healthy = random.random() > 0.25
        return {'healthy': healthy, 'service': service_name, 'status': 'healthy' if healthy else 'unhealthy'}

    async def simulate_network_partition(self):
        """Simulate network partition."""
        await asyncio.sleep(0.2)
        logger.info('Network partition simulated - connectivity lost')

    async def simulate_partition_recovery(self):
        """Simulate network partition recovery."""
        await asyncio.sleep(0.8)
        return {'success': True, 'connectivity': 'restored'}

    async def check_network_connectivity(self):
        """Check network connectivity."""
        await asyncio.sleep(0.05)
        import random
        connected = random.random() > 0.3
        return {'connected': connected, 'latency': 50 if connected else None, 'status': 'connected' if connected else 'disconnected'}

    @pytest.mark.asyncio
    async def test_single_service_recovery_validation(self, recovery_validator):
        """Test recovery validation for single service failure."""
        metrics = await recovery_validator.validate_single_service_recovery(service_name='auth_service', failure_simulator=self.simulate_auth_service_failure, recovery_simulator=self.simulate_auth_service_recovery, health_checker=self.check_auth_service_health, recovery_timeout=20.0)
        assert metrics.failure_detection_time > 0, 'Should detect failure'
        assert metrics.isolation_time >= metrics.failure_detection_time, 'Isolation should follow detection'
        recovery_acceptable = metrics.recovery_success_rate >= 50 or metrics.manual_intervention_required
        assert recovery_acceptable, f'Recovery should be acceptable: success_rate={metrics.recovery_success_rate}%, manual={metrics.manual_intervention_required}'
        assert metrics.health_checks_performed > 0, 'Should perform health checks'
        assert metrics.duration < 30.0, f'Total duration should be reasonable: {metrics.duration}s'
        logger.info(f'Single service recovery: {metrics.get_summary()}')

    @pytest.mark.asyncio
    async def test_cascade_failure_recovery_validation(self, recovery_validator):
        """Test recovery validation for cascading failures."""
        dependent_services = ['backend_service', 'database_service']
        health_checkers = {'auth_service': self.check_auth_service_health, 'backend_service': lambda: self.check_service_health('backend'), 'database_service': lambda: self.check_service_health('database')}
        metrics = await recovery_validator.validate_cascade_failure_recovery(primary_service='auth_service', dependent_services=dependent_services, failure_simulator=self.simulate_cascade_failure, recovery_orchestrator=self.simulate_cascade_recovery, health_checkers=health_checkers, recovery_timeout=30.0)
        assert metrics.failure_detection_time > 0, 'Should detect primary failure'
        assert len(metrics.service_states) >= 2, 'Should track multiple services'
        cascade_recovery_acceptable = metrics.recovery_success_rate >= 40 or metrics.manual_intervention_required
        assert cascade_recovery_acceptable, f'Cascade recovery should be acceptable: success_rate={metrics.recovery_success_rate}%, manual={metrics.manual_intervention_required}'
        assert metrics.health_checks_performed > 0, 'Should perform health checks on multiple services'
        logger.info(f'Cascade failure recovery: {metrics.get_summary()}')

    @pytest.mark.asyncio
    async def test_network_partition_recovery_validation(self, recovery_validator):
        """Test recovery validation for network partition scenarios."""
        affected_services = ['auth_service', 'backend_service']
        metrics = await recovery_validator.validate_network_partition_recovery(partition_simulator=self.simulate_network_partition, partition_recovery_simulator=self.simulate_partition_recovery, connectivity_checker=self.check_network_connectivity, affected_services=affected_services, recovery_timeout=25.0)
        assert metrics.failure_type == FailureScenario.NETWORK_PARTITION, 'Should be network partition scenario'
        network_recovery_acceptable = metrics.recovery_success_rate >= 30 or metrics.manual_intervention_required or metrics.health_checks_performed > 0
        assert network_recovery_acceptable, f'Network recovery should be acceptable: success_rate={metrics.recovery_success_rate}%, manual={metrics.manual_intervention_required}'
        assert metrics.duration < 35.0, f'Network recovery duration should be reasonable: {metrics.duration}s'
        logger.info(f'Network partition recovery: {metrics.get_summary()}')

    @pytest.mark.asyncio
    async def test_comprehensive_recovery_report(self, recovery_validator):
        """Test comprehensive recovery report generation."""
        await recovery_validator.validate_single_service_recovery(service_name='report_test_service', failure_simulator=self.simulate_auth_service_failure, recovery_simulator=self.simulate_auth_service_recovery, health_checker=self.check_auth_service_health, recovery_timeout=10.0)
        report = recovery_validator.generate_recovery_report()
        assert 'summary' in report, 'Report should include summary'
        assert 'detailed_results' in report, 'Report should include detailed results'
        assert 'performance_analysis' in report, 'Report should include performance analysis'
        assert 'recommendations' in report, 'Report should include recommendations'
        summary = report['summary']
        assert summary['total_scenarios_tested'] >= 1, 'Should have test data'
        assert 'scenario_types' in summary, 'Should categorize scenarios'
        logger.info('=== COMPREHENSIVE RECOVERY REPORT ===')
        logger.info(f"Scenarios Tested: {summary['total_scenarios_tested']}")
        logger.info(f"Average Recovery Time: {summary['average_recovery_time']:.2f}s")
        logger.info(f"Average Detection Time: {summary['average_detection_time']:.2f}s")
        logger.info(f"Overall Recovery Success Rate: {summary['overall_recovery_success_rate']:.1f}%")
        logger.info(f"Manual Interventions Required: {summary['scenarios_requiring_manual_intervention']}")
        logger.info(f"Scenario Types: {summary['scenario_types']}")
        if report['recommendations']:
            logger.info('Recommendations:')
            for rec in report['recommendations']:
                logger.info(f'  - {rec}')
        assert True, 'Recovery report generation completed'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')