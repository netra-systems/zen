#!/usr/bin/env python3
"""
System Health Validation Test Suite - Issue #817

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Stability - Ensure system readiness post-recovery
- Value Impact: Validate platform stability for $500K+ ARR protection
- Strategic Impact: Confirm deployment readiness and business confidence

This test validates that the test infrastructure can handle the restored files
and that the system maintains performance and stability after recovery.

CRITICAL REQUIREMENTS:
- NO DOCKER DEPENDENCIES (infrastructure validation only)
- Performance regression testing
- CI pipeline readiness validation
- System health metrics
"""

import os
import sys
import time
import psutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@dataclass
class SystemHealthMetrics:
    """System health metrics after recovery."""
    test_discovery_time: float
    test_discovery_success_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    test_collection_performance: Dict[str, float]
    infrastructure_readiness: bool
    ci_pipeline_ready: bool
    performance_regression_detected: bool


class SystemHealthValidator:
    """Validates system health and readiness post-recovery."""

    def __init__(self, project_root: str = None):
        """Initialize system health validator."""
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..')
        )
        self.test_directory = os.path.join(self.project_root, 'tests')

    def measure_test_discovery_performance(self) -> Dict[str, Any]:
        """Measure test discovery performance across different categories."""
        test_categories = {
            'unit': os.path.join(self.test_directory, 'unit'),
            'integration': os.path.join(self.test_directory, 'integration'),
            'e2e': os.path.join(self.test_directory, 'e2e'),
            'mission_critical': os.path.join(self.test_directory, 'mission_critical'),
        }

        performance_metrics = {}

        for category, path in test_categories.items():
            if not os.path.exists(path):
                performance_metrics[category] = {
                    'discovery_time': 0.0,
                    'tests_found': 0,
                    'success': False,
                    'error': 'Directory not found'
                }
                continue

            start_time = time.time()

            try:
                # Run pytest discovery on category
                cmd = [
                    sys.executable, '-m', 'pytest',
                    '--collect-only', '-q', '--tb=no',
                    path
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=self.project_root
                )

                discovery_time = time.time() - start_time
                success = result.returncode == 0

                # Count tests found
                tests_found = 0
                for line in result.stdout.split('\n'):
                    if '::test_' in line or '<Function test_' in line:
                        tests_found += 1

                performance_metrics[category] = {
                    'discovery_time': discovery_time,
                    'tests_found': tests_found,
                    'success': success,
                    'error': result.stderr if not success else None
                }

            except subprocess.TimeoutExpired:
                discovery_time = time.time() - start_time
                performance_metrics[category] = {
                    'discovery_time': discovery_time,
                    'tests_found': 0,
                    'success': False,
                    'error': 'Discovery timeout'
                }
            except Exception as e:
                discovery_time = time.time() - start_time
                performance_metrics[category] = {
                    'discovery_time': discovery_time,
                    'tests_found': 0,
                    'success': False,
                    'error': str(e)
                }

        return performance_metrics

    def measure_system_resources(self) -> Dict[str, float]:
        """Measure current system resource usage."""
        process = psutil.Process()

        # Get system metrics
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        cpu_percent = process.cpu_percent(interval=1.0)

        # System-wide metrics
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=1.0)

        return {
            'process_memory_mb': memory_mb,
            'process_cpu_percent': cpu_percent,
            'system_memory_percent': system_memory.percent,
            'system_cpu_percent': system_cpu,
            'available_memory_gb': system_memory.available / 1024 / 1024 / 1024
        }

    def validate_test_runner_infrastructure(self) -> Dict[str, Any]:
        """Validate the unified test runner infrastructure works."""
        test_runner_path = os.path.join(self.project_root, 'tests', 'unified_test_runner.py')

        if not os.path.exists(test_runner_path):
            return {
                'infrastructure_ready': False,
                'error': 'Unified test runner not found',
                'test_runner_functional': False
            }

        try:
            # Test the unified test runner help
            cmd = [
                sys.executable, test_runner_path, '--help'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )

            infrastructure_ready = result.returncode == 0
            help_output_valid = 'usage:' in result.stdout.lower() or '--category' in result.stdout

            return {
                'infrastructure_ready': infrastructure_ready,
                'test_runner_functional': help_output_valid,
                'help_output': result.stdout[:500],  # First 500 chars
                'error': result.stderr if not infrastructure_ready else None
            }

        except Exception as e:
            return {
                'infrastructure_ready': False,
                'test_runner_functional': False,
                'error': str(e)
            }

    def check_ci_pipeline_readiness(self) -> Dict[str, Any]:
        """Check if the system is ready for CI pipeline execution."""
        ci_indicators = []

        # Check for CI configuration files
        ci_files = [
            '.github/workflows',
            'pytest.ini',
            'pyproject.toml',
            'requirements.txt'
        ]

        for ci_file in ci_files:
            file_path = os.path.join(self.project_root, ci_file)
            exists = os.path.exists(file_path)
            ci_indicators.append({
                'file': ci_file,
                'exists': exists
            })

        # Test basic pytest execution
        try:
            cmd = [
                sys.executable, '-m', 'pytest',
                '--version'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root
            )

            pytest_available = result.returncode == 0

        except Exception:
            pytest_available = False

        # Calculate readiness score
        ci_files_present = sum(1 for indicator in ci_indicators if indicator['exists'])
        readiness_score = (ci_files_present / len(ci_files)) * 100

        return {
            'ci_pipeline_ready': readiness_score >= 75 and pytest_available,
            'readiness_score': readiness_score,
            'pytest_available': pytest_available,
            'ci_files_status': ci_indicators,
            'missing_files': [i['file'] for i in ci_indicators if not i['exists']]
        }

    def detect_performance_regression(self,
                                    baseline_discovery_time: float = 30.0,
                                    baseline_memory_mb: float = 500.0) -> Dict[str, Any]:
        """Detect performance regression compared to baseline."""

        # Measure current performance
        discovery_metrics = self.measure_test_discovery_performance()
        resource_metrics = self.measure_system_resources()

        # Calculate total discovery time
        total_discovery_time = sum(
            metrics.get('discovery_time', 0)
            for metrics in discovery_metrics.values()
        )

        current_memory = resource_metrics.get('process_memory_mb', 0)

        # Check for regressions
        discovery_regression = total_discovery_time > baseline_discovery_time * 1.5  # 50% threshold
        memory_regression = current_memory > baseline_memory_mb * 1.5  # 50% threshold

        performance_regression = discovery_regression or memory_regression

        return {
            'performance_regression_detected': performance_regression,
            'current_discovery_time': total_discovery_time,
            'baseline_discovery_time': baseline_discovery_time,
            'discovery_regression': discovery_regression,
            'current_memory_mb': current_memory,
            'baseline_memory_mb': baseline_memory_mb,
            'memory_regression': memory_regression,
            'regression_details': {
                'discovery_time_ratio': total_discovery_time / baseline_discovery_time,
                'memory_ratio': current_memory / baseline_memory_mb
            }
        }

    def validate_system_health(self) -> SystemHealthMetrics:
        """Comprehensive system health validation."""

        # Measure discovery performance
        discovery_metrics = self.measure_test_discovery_performance()

        # Calculate overall discovery success rate
        successful_categories = sum(
            1 for metrics in discovery_metrics.values()
            if metrics['success']
        )
        total_categories = len(discovery_metrics)
        discovery_success_rate = (successful_categories / total_categories) * 100 if total_categories > 0 else 0

        # Calculate total discovery time
        total_discovery_time = sum(
            metrics.get('discovery_time', 0)
            for metrics in discovery_metrics.values()
        )

        # Get resource metrics
        resource_metrics = self.measure_system_resources()

        # Validate infrastructure
        infrastructure_status = self.validate_test_runner_infrastructure()

        # Check CI readiness
        ci_status = self.check_ci_pipeline_readiness()

        # Check performance regression
        performance_status = self.detect_performance_regression()

        return SystemHealthMetrics(
            test_discovery_time=total_discovery_time,
            test_discovery_success_rate=discovery_success_rate,
            memory_usage_mb=resource_metrics.get('process_memory_mb', 0),
            cpu_usage_percent=resource_metrics.get('process_cpu_percent', 0),
            test_collection_performance={
                category: metrics.get('discovery_time', 0)
                for category, metrics in discovery_metrics.items()
            },
            infrastructure_readiness=infrastructure_status.get('infrastructure_ready', False),
            ci_pipeline_ready=ci_status.get('ci_pipeline_ready', False),
            performance_regression_detected=performance_status.get('performance_regression_detected', False)
        )


class SystemHealthValidationTests:
    """Test cases for system health validation."""

    def setup_method(self):
        """Set up test environment."""
        self.env = IsolatedEnvironment()
        self.validator = SystemHealthValidator()

    @pytest.mark.unit
    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        assert self.validator.project_root is not None
        assert self.validator.test_directory.endswith('tests')
        assert os.path.exists(self.validator.test_directory)

    @pytest.mark.unit
    @pytest.mark.slow
    def test_test_discovery_performance(self):
        """Test discovery performance measurement."""
        metrics = self.validator.measure_test_discovery_performance()

        assert isinstance(metrics, dict)
        assert len(metrics) > 0

        print(f"\n=== TEST DISCOVERY PERFORMANCE ===")
        total_time = 0
        total_tests = 0

        for category, data in metrics.items():
            print(f"{category}:")
            print(f"  Discovery time: {data['discovery_time']:.2f}s")
            print(f"  Tests found: {data['tests_found']}")
            print(f"  Success: {data['success']}")
            if data.get('error'):
                print(f"  Error: {data['error']}")

            total_time += data.get('discovery_time', 0)
            total_tests += data.get('tests_found', 0)

        print(f"\nTotal discovery time: {total_time:.2f}s")
        print(f"Total tests discovered: {total_tests}")

        # Performance assertions
        assert total_time < 120, f"Discovery too slow: {total_time:.2f}s (max 120s)"
        assert total_tests > 0, "No tests discovered - system may be broken"

    @pytest.mark.unit
    def test_system_resource_measurement(self):
        """Test system resource measurement."""
        metrics = self.validator.measure_system_resources()

        assert isinstance(metrics, dict)
        required_keys = [
            'process_memory_mb',
            'process_cpu_percent',
            'system_memory_percent',
            'system_cpu_percent',
            'available_memory_gb'
        ]

        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"
            assert isinstance(metrics[key], (int, float)), f"Invalid metric type: {key}"

        print(f"\n=== SYSTEM RESOURCE METRICS ===")
        for key, value in metrics.items():
            if 'percent' in key:
                print(f"{key}: {value:.1f}%")
            elif 'mb' in key:
                print(f"{key}: {value:.1f} MB")
            elif 'gb' in key:
                print(f"{key}: {value:.2f} GB")
            else:
                print(f"{key}: {value}")

        # Resource health checks
        assert metrics['available_memory_gb'] > 1.0, (
            f"Low system memory: {metrics['available_memory_gb']:.2f} GB available"
        )

    @pytest.mark.unit
    def test_test_runner_infrastructure(self):
        """Test unified test runner infrastructure."""
        status = self.validator.validate_test_runner_infrastructure()

        assert isinstance(status, dict)
        assert 'infrastructure_ready' in status
        assert 'test_runner_functional' in status

        print(f"\n=== TEST RUNNER INFRASTRUCTURE ===")
        print(f"Infrastructure ready: {status['infrastructure_ready']}")
        print(f"Test runner functional: {status['test_runner_functional']}")

        if status.get('error'):
            print(f"Error: {status['error']}")

        if status.get('help_output'):
            print(f"Help output preview: {status['help_output'][:100]}...")

        # Infrastructure readiness assertions
        assert status['infrastructure_ready'], (
            f"Test runner infrastructure not ready: {status.get('error', 'Unknown error')}"
        )

    @pytest.mark.unit
    def test_ci_pipeline_readiness(self):
        """Test CI pipeline readiness."""
        status = self.validator.check_ci_pipeline_readiness()

        assert isinstance(status, dict)
        assert 'ci_pipeline_ready' in status
        assert 'readiness_score' in status
        assert 'pytest_available' in status

        print(f"\n=== CI PIPELINE READINESS ===")
        print(f"Pipeline ready: {status['ci_pipeline_ready']}")
        print(f"Readiness score: {status['readiness_score']:.1f}%")
        print(f"Pytest available: {status['pytest_available']}")

        if status.get('missing_files'):
            print(f"Missing files: {', '.join(status['missing_files'])}")

        print(f"CI files status:")
        for file_info in status.get('ci_files_status', []):
            print(f"  {file_info['file']}: {'✓' if file_info['exists'] else '✗'}")

        # CI readiness assertions
        assert status['pytest_available'], "Pytest not available - CI will fail"

    @pytest.mark.unit
    def test_performance_regression_detection(self):
        """Test performance regression detection."""
        regression_status = self.validator.detect_performance_regression()

        assert isinstance(regression_status, dict)
        assert 'performance_regression_detected' in regression_status

        print(f"\n=== PERFORMANCE REGRESSION DETECTION ===")
        print(f"Regression detected: {regression_status['performance_regression_detected']}")
        print(f"Current discovery time: {regression_status['current_discovery_time']:.2f}s")
        print(f"Baseline discovery time: {regression_status['baseline_discovery_time']:.2f}s")
        print(f"Discovery regression: {regression_status['discovery_regression']}")
        print(f"Current memory: {regression_status['current_memory_mb']:.1f} MB")
        print(f"Memory regression: {regression_status['memory_regression']}")

        regression_details = regression_status.get('regression_details', {})
        print(f"Discovery time ratio: {regression_details.get('discovery_time_ratio', 0):.2f}x")
        print(f"Memory ratio: {regression_details.get('memory_ratio', 0):.2f}x")

        # Performance regression warnings (not failures)
        if regression_status['performance_regression_detected']:
            print("\nWARNING: Performance regression detected!")
            print("This may indicate issues with the recovery process.")

    @pytest.mark.unit
    @pytest.mark.slow
    def test_comprehensive_system_health_validation(self):
        """Test comprehensive system health validation - MAIN TEST."""
        health_metrics = self.validator.validate_system_health()

        # Validate metrics structure
        assert isinstance(health_metrics.test_discovery_time, float)
        assert isinstance(health_metrics.test_discovery_success_rate, float)
        assert isinstance(health_metrics.memory_usage_mb, float)
        assert isinstance(health_metrics.cpu_usage_percent, float)
        assert isinstance(health_metrics.test_collection_performance, dict)
        assert isinstance(health_metrics.infrastructure_readiness, bool)
        assert isinstance(health_metrics.ci_pipeline_ready, bool)
        assert isinstance(health_metrics.performance_regression_detected, bool)

        # Log comprehensive health status
        print(f"\n=== COMPREHENSIVE SYSTEM HEALTH ===")
        print(f"Test discovery time: {health_metrics.test_discovery_time:.2f}s")
        print(f"Discovery success rate: {health_metrics.test_discovery_success_rate:.1f}%")
        print(f"Memory usage: {health_metrics.memory_usage_mb:.1f} MB")
        print(f"CPU usage: {health_metrics.cpu_usage_percent:.1f}%")
        print(f"Infrastructure ready: {health_metrics.infrastructure_readiness}")
        print(f"CI pipeline ready: {health_metrics.ci_pipeline_ready}")
        print(f"Performance regression: {health_metrics.performance_regression_detected}")

        print(f"\nCollection performance by category:")
        for category, time_taken in health_metrics.test_collection_performance.items():
            print(f"  {category}: {time_taken:.2f}s")

        # CRITICAL HEALTH ASSERTIONS
        assert health_metrics.test_discovery_success_rate >= 50, (
            f"Test discovery success rate too low: {health_metrics.test_discovery_success_rate:.1f}% "
            f"(minimum 50% required for basic functionality)"
        )

        assert health_metrics.infrastructure_readiness, (
            "Test infrastructure not ready! This blocks all testing capabilities."
        )

        assert not health_metrics.performance_regression_detected, (
            "Performance regression detected! This may indicate recovery issues."
        )

        assert health_metrics.test_discovery_time < 180, (
            f"Test discovery too slow: {health_metrics.test_discovery_time:.2f}s "
            f"(maximum 180s for reasonable developer experience)"
        )

        # Store health metrics for reporting
        self.system_health_metrics = health_metrics

    @pytest.mark.unit
    def test_deployment_readiness_assessment(self):
        """Assess overall deployment readiness post-recovery."""
        health_metrics = self.validator.validate_system_health()

        # Deployment readiness criteria
        readiness_criteria = {
            'discovery_success_rate': health_metrics.test_discovery_success_rate >= 70,
            'infrastructure_ready': health_metrics.infrastructure_readiness,
            'no_performance_regression': not health_metrics.performance_regression_detected,
            'reasonable_discovery_time': health_metrics.test_discovery_time < 120,
            'sufficient_memory': health_metrics.memory_usage_mb < 1000
        }

        passed_criteria = sum(readiness_criteria.values())
        total_criteria = len(readiness_criteria)
        readiness_score = (passed_criteria / total_criteria) * 100

        print(f"\n=== DEPLOYMENT READINESS ASSESSMENT ===")
        print(f"Overall readiness score: {readiness_score:.1f}%")
        print(f"Criteria passed: {passed_criteria}/{total_criteria}")

        print(f"\nReadiness criteria:")
        for criterion, passed in readiness_criteria.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {criterion}: {status}")

        deployment_ready = readiness_score >= 80

        print(f"\nDeployment recommendation: {'READY' if deployment_ready else 'NOT READY'}")

        if not deployment_ready:
            print("System requires additional recovery work before deployment.")

        # Store assessment
        self.deployment_readiness = {
            'ready': deployment_ready,
            'score': readiness_score,
            'criteria': readiness_criteria
        }

        # Deployment readiness assertion
        assert deployment_ready, (
            f"System not ready for deployment: {readiness_score:.1f}% readiness "
            f"(minimum 80% required)"
        )


if __name__ == "__main__":
    """Run system health validation directly."""
    validator = SystemHealthValidator()
    health_metrics = validator.validate_system_health()

    print("=== ISSUE #817 SYSTEM HEALTH ===")
    print(f"Discovery success: {health_metrics.test_discovery_success_rate:.1f}%")
    print(f"Infrastructure ready: {health_metrics.infrastructure_readiness}")
    print(f"Performance regression: {health_metrics.performance_regression_detected}")
    print(f"CI pipeline ready: {health_metrics.ci_pipeline_ready}")