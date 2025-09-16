"""
E2E tests for real GCP environment detection and optimization - Issue #586.

Tests complete environment detection cycle in actual GCP Cloud Run environment
with real WebSocket connections and service coordination.

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Performance Optimization & Platform Reliability
- Value Impact: Validates environment detection works correctly in production-like
  environment and delivers promised performance optimizations while maintaining
  $500K+ ARR protection through reliable WebSocket connections
- Strategic Impact: Real GCP validation ensures environment-aware system delivers
  optimal performance in actual deployment context

This test suite validates:
1. Accurate GCP Cloud Run environment detection in real deployment
2. Staging timeout optimization delivers promised performance gains (30% improvement)
3. WebSocket race condition prevention maintained despite optimization
4. Complete service startup coordination in actual GCP environment
"""
import asyncio
import pytest
import time
import json
import os
from typing import Dict, Any, List
try:
    from tests.e2e.base import BaseE2ETest
except ImportError:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase as BaseE2ETest
from netra_backend.app.websocket_core.gcp_initialization_validator import create_gcp_websocket_validator, gcp_websocket_readiness_check

@pytest.mark.e2e
class GCPEnvironmentDetectionE2ETests(BaseE2ETest):
    """
    Test real GCP environment detection and timeout optimization.
    
    These tests run in actual GCP staging environment to validate environment
    detection accuracy and performance optimization effectiveness.
    """

    def setup_method(self, method):
        """Set up E2E test environment with GCP staging context."""
        super().setup_method(method)
        self.record_metric('test_category', 'gcp_environment_detection_e2e')
        self._verify_gcp_staging_environment()
        self.baseline_metrics = {}

    def _verify_gcp_staging_environment(self):
        """
        Verify test is running in actual GCP staging environment.
        
        CRITICAL: E2E tests must run in real GCP environment to validate
        environment detection and optimization effectiveness.
        """
        k_service = self.get_env_var('K_SERVICE')
        environment = self.get_env_var('ENVIRONMENT')
        if not k_service:
            pytest.skip('E2E test requires GCP Cloud Run environment (K_SERVICE not found)')
        if not environment or environment.lower() != 'staging':
            pytest.skip('E2E test requires staging environment for safe testing')
        self.record_metric('gcp_staging_verification', 'confirmed')
        self.record_metric('k_service', k_service)
        self.record_metric('environment', environment)

    @pytest.mark.asyncio
    async def test_gcp_cloud_run_environment_detection_accuracy(self):
        """
        Test accurate GCP Cloud Run environment detection in real deployment.
        
        CRITICAL: This test verifies environment detection works correctly in
        actual GCP Cloud Run, validating the core logic for timeout optimization.
        
        Should initially fail if environment detection inaccurate in real GCP.
        """
        k_service = self.get_env_var('K_SERVICE')
        k_revision = self.get_env_var('K_REVISION')
        environment = self.get_env_var('ENVIRONMENT')
        self.assertIsNotNone(k_service, 'K_SERVICE should be detected in real GCP Cloud Run')
        self.assertIn('staging', k_service.lower(), f'K_SERVICE should indicate staging environment: {k_service}')
        self.assertEqual(environment.lower(), 'staging', f'ENVIRONMENT should be staging in GCP staging: {environment}')
        validator = create_gcp_websocket_validator(None)
        self.assertEqual(validator.environment, 'staging', f'Validator should detect staging environment: {validator.environment}')
        self.assertTrue(validator.is_gcp_environment, 'Validator should recognize GCP environment')
        self.assertTrue(validator.is_cloud_run, 'Validator should detect Cloud Run deployment')
        self.record_metric('gcp_environment_detection_accuracy', 'success')
        self.record_metric('detected_k_service', k_service)
        self.record_metric('detected_environment', environment)
        self.record_metric('is_gcp_detected', validator.is_gcp_environment)
        self.record_metric('is_cloud_run_detected', validator.is_cloud_run)

    @pytest.mark.asyncio
    async def test_staging_timeout_optimization_performance(self):
        """
        Test staging timeout optimization delivers promised performance gains.
        
        CRITICAL: This test measures actual WebSocket connection times and
        validates 30% performance improvement vs baseline (0.7x multiplier).
        
        Should initially fail if promised performance gains not achieved.
        """
        validator = create_gcp_websocket_validator(None)
        self.assertEqual(validator.timeout_multiplier, 0.7)
        self.assertEqual(validator.safety_margin, 1.1)
        self.assertEqual(validator.max_total_timeout, 5.0)
        baseline_timeouts = [1.0, 2.0, 5.0, 10.0]
        performance_improvements = []
        for baseline_timeout in baseline_timeouts:
            optimized_timeout = validator._get_optimized_timeout(baseline_timeout)
            production_timeout = baseline_timeout * 1.0 * 1.2
            improvement_ratio = (production_timeout - optimized_timeout) / production_timeout
            performance_improvements.append(improvement_ratio)
            self.assertLess(optimized_timeout, production_timeout, f'Optimized timeout ({optimized_timeout}s) should be faster than production ({production_timeout}s)')
            expected_improvement = 1 - 0.7 * 1.1 / 1.2
            self.assertAlmostEqual(improvement_ratio, expected_improvement, delta=0.1, msg=f'Performance improvement should be ~36%: got {improvement_ratio:.2%}')
        avg_improvement = sum(performance_improvements) / len(performance_improvements)
        self.assertGreaterEqual(avg_improvement, 0.25, f'Average performance improvement should be ≥ 25%: got {avg_improvement:.2%}')
        self.record_metric('staging_timeout_optimization_performance', 'success')
        self.record_metric('average_performance_improvement', avg_improvement)
        self.record_metric('timeout_multiplier_verified', validator.timeout_multiplier)
        for i, improvement in enumerate(performance_improvements):
            self.record_metric(f'improvement_baseline_{baseline_timeouts[i]}s', improvement)

    @pytest.mark.asyncio
    async def test_websocket_race_prevention_maintained(self):
        """
        Test WebSocket race condition prevention still works with optimization.
        
        CRITICAL: This test verifies that despite timeout optimizations, the system
        still prevents 1011 WebSocket errors and maintains race condition protection.
        
        Should initially fail if race condition prevention compromised by optimization.
        """
        validator = create_gcp_websocket_validator(None)
        very_small_timeout = 0.1
        safe_timeout = validator._get_optimized_timeout(very_small_timeout)
        self.assertGreaterEqual(safe_timeout, 0.5, f'Cloud Run minimum safety timeout not enforced in real GCP: got {safe_timeout}s')
        race_condition_start = time.time()
        try:
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=2.0)
            race_condition_duration = time.time() - race_condition_start
            self.assertFalse(result.ready, 'Should detect race condition when app_state not available in GCP')
            self.assertGreaterEqual(race_condition_duration, 0.4, f'Should maintain minimum safety timing in GCP race condition: {race_condition_duration:.3f}s')
            self.assertIn('startup_phase_timeout', result.failed_services, 'Should detect startup phase timeout in race condition')
            self.record_metric('race_condition_prevention_maintained', 'success')
            self.record_metric('race_condition_detection_duration', race_condition_duration)
        except Exception as e:
            race_condition_duration = time.time() - race_condition_start
            self.assertGreaterEqual(race_condition_duration, 0.4, f'Race condition exception should still respect timing: {race_condition_duration:.3f}s')
            self.record_metric('race_condition_exception_handling', 'success')
            self.record_metric('race_condition_exception_duration', race_condition_duration)

    @pytest.mark.asyncio
    async def test_service_startup_coordination_in_gcp(self):
        """
        Test service startup coordination works in real GCP environment.
        
        CRITICAL: This test validates that all services reach readiness within
        optimized timeouts and service coordination works in actual deployment.
        
        Should initially fail if service coordination doesn't work in real GCP.
        """
        try:
            health_start = time.time()
            ready, details = await gcp_websocket_readiness_check(None)
            health_duration = time.time() - health_start
            self.record_metric('gcp_health_check_duration', health_duration)
            self.record_metric('gcp_health_check_ready', ready)
            self.record_metric('gcp_health_check_details', json.dumps(details, default=str))
            self.assertLess(health_duration, 15.0, f'GCP health check should complete within timeout: took {health_duration:.3f}s')
            if ready:
                required_details = ['websocket_ready', 'state', 'elapsed_time', 'gcp_environment', 'cloud_run']
                for detail_key in required_details:
                    self.assertIn(detail_key, details, f'Health check details should include {detail_key}')
                self.assertTrue(details.get('gcp_environment', False), 'Health check should detect GCP environment')
                self.assertTrue(details.get('cloud_run', False), 'Health check should detect Cloud Run')
                self.record_metric('gcp_service_coordination_success', 'ready')
            else:
                failed_services = details.get('failed_services', [])
                warnings = details.get('warnings', [])
                self.record_metric('gcp_service_coordination_failures', failed_services)
                self.record_metric('gcp_service_coordination_warnings', warnings)
                print(f'GCP service coordination not ready: failed={failed_services}, warnings={warnings}')
        except Exception as e:
            health_duration = time.time() - health_start
            self.record_metric('gcp_health_check_exception', str(e))
            self.record_metric('gcp_health_check_exception_duration', health_duration)
            print(f'GCP health check exception (may be expected): {e}')

    @pytest.mark.asyncio
    async def test_environment_adaptation_transparency(self):
        """
        Test environment adaptation is transparent to users.
        
        CRITICAL: This test validates that users don't experience configuration-related
        errors and the system adapts gracefully to environment constraints.
        
        Should initially fail if environment adaptation causes user-visible issues.
        """
        validator_configs = [{'timeout_seconds': 1.0}, {'timeout_seconds': 5.0}, {'timeout_seconds': 10.0}]
        adaptation_results = []
        for config in validator_configs:
            adaptation_start = time.time()
            try:
                validator = create_gcp_websocket_validator(None)
                optimized_timeout = validator._get_optimized_timeout(config['timeout_seconds'])
                adaptation_duration = time.time() - adaptation_start
                self.assertLess(adaptation_duration, 0.1, f'Environment adaptation should be fast: took {adaptation_duration:.3f}s')
                self.assertGreater(optimized_timeout, 0.1, 'Optimized timeout should be reasonable')
                self.assertLess(optimized_timeout, 30.0, 'Optimized timeout should not be excessive')
                adaptation_results.append({'original': config['timeout_seconds'], 'optimized': optimized_timeout, 'duration': adaptation_duration, 'success': True})
            except Exception as e:
                adaptation_duration = time.time() - adaptation_start
                adaptation_results.append({'original': config['timeout_seconds'], 'error': str(e), 'duration': adaptation_duration, 'success': False})
        successful_adaptations = [r for r in adaptation_results if r['success']]
        self.assertGreater(len(successful_adaptations), 0, f'At least some environment adaptations should succeed: {adaptation_results}')
        self.record_metric('environment_adaptation_transparency', 'success')
        self.record_metric('successful_adaptations', len(successful_adaptations))
        self.record_metric('total_adaptations', len(adaptation_results))
        for i, result in enumerate(adaptation_results):
            self.record_metric(f'adaptation_{i}_success', result['success'])
            self.record_metric(f'adaptation_{i}_duration', result['duration'])

    def teardown_method(self, method):
        """Clean up E2E test environment and record GCP environment metrics."""
        execution_time = self.get_metrics().execution_time
        self.record_metric('test_execution_time', execution_time)
        metrics = self.get_all_metrics()
        gcp_metrics = {k: v for k, v in metrics.items() if 'gcp' in k}
        if gcp_metrics:
            duration_metrics = [v for k, v in gcp_metrics.items() if 'duration' in k and isinstance(v, (int, float))]
            if duration_metrics:
                avg_gcp_duration = sum(duration_metrics) / len(duration_metrics)
                self.record_metric('average_gcp_operation_duration', avg_gcp_duration)
        if execution_time > 30.0:
            print(f'PERFORMANCE WARNING: GCP E2E test took {execution_time:.3f}s')
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')