"""
Comprehensive unit tests for Issue #1005 Database Timeout Handling Infrastructure.

Tests cover:
1. Enhanced timeout configuration with adaptive calculation
2. SMD bypass logic with intelligent failure type analysis
3. Database connection monitoring and performance analysis
4. Integration with existing timeout systems

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Staging Environment Stability & Golden Path Reliability
- Value Impact: Ensures timeout infrastructure works reliably across environments
- Strategic Impact: Prevents CI/CD failures and maintains customer confidence
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from netra_backend.app.core.database_timeout_config import (
    calculate_adaptive_timeout,
    get_adaptive_timeout_config,
    should_use_adaptive_timeouts,
    get_failure_type_analysis,
    ConnectionMetrics,
    DatabaseConnectionMonitor
)


class TestAdaptiveTimeoutCalculation(unittest.TestCase):
    """Test adaptive timeout calculation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_environments = ['development', 'test', 'staging', 'production']
        self.test_operation_types = ['initialization', 'table_setup', 'connection', 'pool', 'health_check']

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_adaptive_timeout_with_insufficient_data(self, mock_monitor):
        """Test adaptive timeout calculation with insufficient historical data."""
        # Mock insufficient data scenario
        mock_monitor.get_environment_metrics.return_value = None

        # Test each environment
        for environment in self.test_environments:
            for operation_type in self.test_operation_types:
                with self.subTest(environment=environment, operation_type=operation_type):
                    adaptive_timeout = calculate_adaptive_timeout(environment, operation_type)

                    # Should return a timeout value
                    self.assertIsInstance(adaptive_timeout, float)
                    self.assertGreater(adaptive_timeout, 0)

                    # Cloud SQL environments should have larger safety factors
                    if environment in ['staging', 'production']:
                        # Expect at least 20% increase for Cloud SQL
                        base_config = self._get_base_timeout(environment, operation_type)
                        self.assertGreaterEqual(adaptive_timeout, base_config * 1.1)

    def _get_base_timeout(self, environment: str, operation_type: str) -> float:
        """Helper to get base timeout for comparison."""
        from netra_backend.app.core.database_timeout_config import get_database_timeout_config
        config = get_database_timeout_config(environment)
        return config.get(f"{operation_type}_timeout", 30.0)

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_adaptive_timeout_with_performance_data(self, mock_monitor):
        """Test adaptive timeout calculation with historical performance data."""
        # Create mock metrics with performance data
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 20
        mock_metrics.get_average_connection_time.return_value = 5.0
        mock_metrics.get_recent_average_connection_time.return_value = 7.0  # Degrading performance
        mock_metrics.get_success_rate.return_value = 85.0  # Low success rate
        mock_metrics.get_timeout_violation_rate.return_value = 20.0  # High violation rate

        mock_monitor.get_environment_metrics.return_value = mock_metrics

        # Test staging environment with degrading performance
        adaptive_timeout = calculate_adaptive_timeout('staging', 'connection')

        # Should increase timeout significantly due to degradation + low success + violations
        base_timeout = self._get_base_timeout('staging', 'connection')
        self.assertGreater(adaptive_timeout, base_timeout * 1.5)  # At least 50% increase

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_adaptive_timeout_with_good_performance(self, mock_monitor):
        """Test adaptive timeout calculation with good performance data."""
        # Create mock metrics with good performance
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 50
        mock_metrics.get_average_connection_time.return_value = 3.0
        mock_metrics.get_recent_average_connection_time.return_value = 2.0  # Improving performance
        mock_metrics.get_success_rate.return_value = 99.0  # High success rate
        mock_metrics.get_timeout_violation_rate.return_value = 2.0  # Low violation rate

        mock_monitor.get_environment_metrics.return_value = mock_metrics

        # Test development environment with good performance
        adaptive_timeout = calculate_adaptive_timeout('development', 'connection')

        # Should potentially reduce timeout due to good performance
        base_timeout = self._get_base_timeout('development', 'connection')
        self.assertLessEqual(adaptive_timeout, base_timeout * 1.1)  # Should not increase much

    def test_adaptive_timeout_config_integration(self):
        """Test getting adaptive timeout configuration for all operation types."""
        for environment in self.test_environments:
            with self.subTest(environment=environment):
                adaptive_config = get_adaptive_timeout_config(environment)

                # Should have all required timeout types
                expected_keys = [
                    'initialization_timeout', 'table_setup_timeout', 'connection_timeout',
                    'pool_timeout', 'health_check_timeout'
                ]

                for key in expected_keys:
                    self.assertIn(key, adaptive_config)
                    self.assertIsInstance(adaptive_config[key], float)
                    self.assertGreater(adaptive_config[key], 0)

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_should_use_adaptive_timeouts(self, mock_monitor):
        """Test decision logic for when to use adaptive timeouts."""
        # Cloud SQL environments should always use adaptive timeouts
        self.assertTrue(should_use_adaptive_timeouts('staging'))
        self.assertTrue(should_use_adaptive_timeouts('production'))

        # Local environments depend on data availability
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 15  # Sufficient data
        mock_monitor.get_environment_metrics.return_value = mock_metrics

        self.assertTrue(should_use_adaptive_timeouts('development'))

        # Insufficient data
        mock_metrics.connection_attempts = 5  # Insufficient data
        self.assertFalse(should_use_adaptive_timeouts('development'))


class TestFailureTypeAnalysis(unittest.TestCase):
    """Test intelligent failure type analysis for SMD bypass logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_environments = ['development', 'test', 'staging', 'production']

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_failure_analysis_no_data(self, mock_monitor):
        """Test failure analysis with no historical data."""
        mock_monitor.get_environment_metrics.return_value = None

        for environment in self.test_environments:
            with self.subTest(environment=environment):
                analysis = get_failure_type_analysis(environment)

                self.assertEqual(analysis['environment'], environment)
                self.assertFalse(analysis['has_data'])
                self.assertEqual(analysis['bypass_recommendation'], 'conservative')
                self.assertIn('No historical data', analysis['reason'])

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_failure_analysis_critical_connection_failure(self, mock_monitor):
        """Test failure analysis with critical connection failures."""
        # Create mock metrics with critical connection failures
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 20
        mock_metrics.get_success_rate.return_value = 75.0  # Critical failure rate
        mock_metrics.get_timeout_violation_rate.return_value = 10.0
        mock_metrics.get_recent_average_connection_time.return_value = 5.0
        mock_metrics.get_average_connection_time.return_value = 5.0

        mock_monitor.get_environment_metrics.return_value = mock_metrics

        analysis = get_failure_type_analysis('staging')

        self.assertTrue(analysis['has_data'])
        self.assertEqual(analysis['failure_type'], 'connection_failure')
        self.assertEqual(analysis['severity'], 'critical')
        self.assertEqual(analysis['bypass_recommendation'], 'conditional')
        self.assertIn('Critical connection failure rate', analysis['reason'])

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_failure_analysis_timeout_violations(self, mock_monitor):
        """Test failure analysis with high timeout violations (infrastructure issue)."""
        # Create mock metrics with high timeout violations
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 30
        mock_metrics.get_success_rate.return_value = 92.0  # Good success rate
        mock_metrics.get_timeout_violation_rate.return_value = 30.0  # High timeout violations
        mock_metrics.get_recent_average_connection_time.return_value = 8.0
        mock_metrics.get_average_connection_time.return_value = 7.0

        mock_monitor.get_environment_metrics.return_value = mock_metrics

        analysis = get_failure_type_analysis('staging')

        self.assertEqual(analysis['failure_type'], 'timeout_failure')
        self.assertEqual(analysis['severity'], 'medium')
        self.assertEqual(analysis['bypass_recommendation'], 'permissive')
        self.assertIn('High timeout violation rate', analysis['reason'])
        self.assertIn('infrastructure issue', analysis['reason'])

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_failure_analysis_healthy_performance(self, mock_monitor):
        """Test failure analysis with healthy performance metrics."""
        # Create mock metrics with healthy performance
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 50
        mock_metrics.get_success_rate.return_value = 98.0  # Excellent success rate
        mock_metrics.get_timeout_violation_rate.return_value = 5.0  # Low violations
        mock_metrics.get_recent_average_connection_time.return_value = 3.0
        mock_metrics.get_average_connection_time.return_value = 3.2

        mock_monitor.get_environment_metrics.return_value = mock_metrics

        analysis = get_failure_type_analysis('production')

        self.assertEqual(analysis['failure_type'], 'none')
        self.assertEqual(analysis['severity'], 'low')
        self.assertEqual(analysis['bypass_recommendation'], 'strict')
        self.assertIn('Performance within acceptable bounds', analysis['reason'])

    @patch('netra_backend.app.core.database_timeout_config._connection_monitor')
    def test_failure_analysis_cloud_sql_adjustments(self, mock_monitor):
        """Test failure analysis with Cloud SQL environment adjustments."""
        # Create mock metrics with moderate timeout violations
        mock_metrics = Mock(spec=ConnectionMetrics)
        mock_metrics.connection_attempts = 25
        mock_metrics.get_success_rate.return_value = 95.0
        mock_metrics.get_timeout_violation_rate.return_value = 18.0  # Moderate violations
        mock_metrics.get_recent_average_connection_time.return_value = 6.0
        mock_metrics.get_average_connection_time.return_value = 5.5

        mock_monitor.get_environment_metrics.return_value = mock_metrics

        # Test staging (Cloud SQL environment)
        analysis = get_failure_type_analysis('staging')

        self.assertEqual(analysis['failure_type'], 'performance_degradation')
        self.assertEqual(analysis['bypass_recommendation'], 'permissive')
        self.assertIn('Cloud SQL infrastructure considerations', analysis['reason'])


class TestSMDBypassLogic(unittest.TestCase):
    """Test SMD bypass logic with intelligent failure analysis integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the StartupOrchestrator class
        from netra_backend.app.smd import StartupOrchestrator
        from fastapi import FastAPI

        app = FastAPI()
        self.orchestrator = StartupOrchestrator(app)

        # Mock logger to avoid actual logging during tests
        self.orchestrator.logger = Mock()

    def test_manual_bypass_override(self):
        """Test that manual bypass always takes precedence."""
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 5, True  # manual bypass = True
        )

        self.assertTrue(should_bypass)
        self.assertIn('manual override', reason)

    @patch('netra_backend.app.core.database_timeout_config.get_failure_type_analysis')
    def test_strict_bypass_recommendation(self, mock_get_analysis):
        """Test strict bypass recommendation (no bypass allowed)."""
        mock_get_analysis.return_value = {
            'bypass_recommendation': 'strict',
            'failure_type': 'connection_failure',
            'severity': 'critical',
            'reason': 'Genuine connection issues detected'
        }

        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 2, False
        )

        self.assertFalse(should_bypass)
        self.assertIn('Strict validation required', reason)

    @patch('netra_backend.app.core.database_timeout_config.get_failure_type_analysis')
    def test_permissive_bypass_recommendation(self, mock_get_analysis):
        """Test permissive bypass recommendation (infrastructure issues)."""
        mock_get_analysis.return_value = {
            'bypass_recommendation': 'permissive',
            'failure_type': 'timeout_failure',
            'severity': 'medium',
            'reason': 'High timeout violation rate: 25.0% (infrastructure issue)'
        }

        # Test with reasonable failure count
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 3, False
        )

        self.assertTrue(should_bypass)
        self.assertIn('Infrastructure-related bypass', reason)
        self.assertIn('timeout_failure', reason)

    @patch('netra_backend.app.core.database_timeout_config.get_failure_type_analysis')
    def test_permissive_bypass_too_many_failures(self, mock_get_analysis):
        """Test permissive bypass with too many failures."""
        mock_get_analysis.return_value = {
            'bypass_recommendation': 'permissive',
            'failure_type': 'timeout_failure',
            'severity': 'medium',
            'reason': 'Infrastructure timeout issues'
        }

        # Test with too many failures
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 8, False  # Too many failures
        )

        self.assertFalse(should_bypass)
        self.assertIn('Too many failures', reason)

    @patch('netra_backend.app.core.database_timeout_config.get_failure_type_analysis')
    def test_conditional_bypass_staging(self, mock_get_analysis):
        """Test conditional bypass logic for staging environment."""
        mock_get_analysis.return_value = {
            'bypass_recommendation': 'conditional',
            'failure_type': 'intermittent_failure',
            'severity': 'medium',
            'reason': 'Moderate connection failure rate: 88.0%'
        }

        # Test staging with acceptable failure count
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 2, False
        )

        self.assertTrue(should_bypass)
        self.assertIn('Staging conditional bypass', reason)

        # Test staging with too many failures
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 4, False
        )

        self.assertFalse(should_bypass)
        self.assertIn('Staging failure threshold exceeded', reason)

    @patch('netra_backend.app.core.database_timeout_config.get_failure_type_analysis')
    def test_conditional_bypass_production(self, mock_get_analysis):
        """Test conditional bypass logic for production environment (very strict)."""
        mock_get_analysis.return_value = {
            'bypass_recommendation': 'conditional',
            'failure_type': 'performance_degradation',
            'severity': 'low',
            'reason': 'Minor performance issues detected'
        }

        # Test production with single failure (acceptable)
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'production', 1, False
        )

        self.assertTrue(should_bypass)
        self.assertIn('Production conditional bypass', reason)

        # Test production with multiple failures (not acceptable)
        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'production', 2, False
        )

        self.assertFalse(should_bypass)
        self.assertIn('Production failure threshold exceeded', reason)

    @patch('netra_backend.app.core.database_timeout_config.get_failure_type_analysis')
    def test_fallback_to_basic_logic(self, mock_get_analysis):
        """Test fallback to basic logic when analysis fails."""
        # Mock analysis failure
        mock_get_analysis.side_effect = Exception("Analysis failed")

        should_bypass, reason = self.orchestrator._determine_intelligent_bypass(
            'staging', 2, False
        )

        # Should fall back to basic logic
        self.assertTrue(should_bypass)  # Staging with 2 failures should pass basic logic
        self.assertIn('basic logic', reason)

    def test_basic_bypass_logic_staging(self):
        """Test basic bypass logic for staging environment."""
        # Acceptable failures for staging
        should_bypass, reason = self.orchestrator._basic_bypass_logic('staging', 2)
        self.assertTrue(should_bypass)
        self.assertIn('staging environment with 2 minor failures', reason)

        # Too many failures for staging
        should_bypass, reason = self.orchestrator._basic_bypass_logic('staging', 3)
        self.assertFalse(should_bypass)
        self.assertIn('Too many critical failures', reason)

    def test_basic_bypass_logic_production(self):
        """Test basic bypass logic for production environment."""
        # Single acceptable failure for production
        should_bypass, reason = self.orchestrator._basic_bypass_logic('production', 1)
        self.assertTrue(should_bypass)
        self.assertIn('production environment with 1 acceptable failure', reason)

        # Multiple failures not acceptable for production
        should_bypass, reason = self.orchestrator._basic_bypass_logic('production', 2)
        self.assertFalse(should_bypass)
        self.assertIn('Too many critical failures', reason)

    def test_basic_bypass_logic_development(self):
        """Test basic bypass logic for development environment."""
        # Development can be more lenient
        should_bypass, reason = self.orchestrator._basic_bypass_logic('development', 3)
        self.assertTrue(should_bypass)
        self.assertIn('development environment with 3 acceptable failures', reason)

        # But not unlimited
        should_bypass, reason = self.orchestrator._basic_bypass_logic('development', 4)
        self.assertFalse(should_bypass)
        self.assertIn('Too many critical failures', reason)


class TestConnectionMetrics(unittest.TestCase):
    """Test database connection metrics tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics = ConnectionMetrics()

    def test_connection_metrics_initialization(self):
        """Test connection metrics initialization."""
        self.assertEqual(self.metrics.connection_attempts, 0)
        self.assertEqual(self.metrics.successful_connections, 0)
        self.assertEqual(self.metrics.failed_connections, 0)
        self.assertEqual(self.metrics.timeout_violations, 0)
        self.assertIsNone(self.metrics.last_connection_time)

    def test_add_successful_connection(self):
        """Test adding successful connection attempt."""
        self.metrics.add_connection_attempt(2.5, True, 30.0)

        self.assertEqual(self.metrics.connection_attempts, 1)
        self.assertEqual(self.metrics.successful_connections, 1)
        self.assertEqual(self.metrics.failed_connections, 0)
        self.assertEqual(self.metrics.timeout_violations, 0)
        self.assertEqual(self.metrics.last_connection_time, 2.5)
        self.assertEqual(self.metrics.max_connection_time, 2.5)

    def test_add_failed_connection(self):
        """Test adding failed connection attempt."""
        self.metrics.add_connection_attempt(35.0, False, 30.0)  # Timeout violation

        self.assertEqual(self.metrics.connection_attempts, 1)
        self.assertEqual(self.metrics.successful_connections, 0)
        self.assertEqual(self.metrics.failed_connections, 1)
        self.assertEqual(self.metrics.timeout_violations, 1)  # Exceeded timeout threshold

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        # Add multiple attempts
        self.metrics.add_connection_attempt(2.0, True, 30.0)
        self.metrics.add_connection_attempt(3.0, True, 30.0)
        self.metrics.add_connection_attempt(35.0, False, 30.0)

        success_rate = self.metrics.get_success_rate()
        self.assertAlmostEqual(success_rate, 66.67, places=1)  # 2/3 = 66.67%

    def test_average_connection_time(self):
        """Test average connection time calculation."""
        self.metrics.add_connection_attempt(2.0, True, 30.0)
        self.metrics.add_connection_attempt(4.0, True, 30.0)
        self.metrics.add_connection_attempt(6.0, False, 30.0)

        avg_time = self.metrics.get_average_connection_time()
        self.assertAlmostEqual(avg_time, 4.0, places=1)  # (2+4+6)/3 = 4.0

    def test_recent_average_connection_time(self):
        """Test recent average connection time calculation."""
        # Add several attempts
        for i in range(10):
            self.metrics.add_connection_attempt(float(i + 1), True, 30.0)

        # Recent average with window size 5 should be average of last 5
        recent_avg = self.metrics.get_recent_average_connection_time(window_size=5)
        expected = (6 + 7 + 8 + 9 + 10) / 5  # Last 5 values
        self.assertAlmostEqual(recent_avg, expected, places=1)


class TestDatabaseConnectionMonitor(unittest.TestCase):
    """Test database connection monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = DatabaseConnectionMonitor()

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(len(self.monitor._metrics_by_environment), 0)
        self.assertEqual(len(self.monitor._alert_callbacks), 0)

    def test_record_connection_attempt(self):
        """Test recording connection attempts."""
        timeout_config = {'connection_timeout': 30.0}

        self.monitor.record_connection_attempt('staging', 5.0, True, timeout_config)

        metrics = self.monitor.get_environment_metrics('staging')
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.connection_attempts, 1)
        self.assertEqual(metrics.successful_connections, 1)

    def test_performance_summary(self):
        """Test getting performance summary."""
        timeout_config = {'connection_timeout': 30.0}

        # Add multiple attempts
        self.monitor.record_connection_attempt('staging', 5.0, True, timeout_config)
        self.monitor.record_connection_attempt('staging', 7.0, True, timeout_config)
        self.monitor.record_connection_attempt('staging', 35.0, False, timeout_config)

        summary = self.monitor.get_performance_summary('staging')

        self.assertEqual(summary['environment'], 'staging')
        self.assertEqual(summary['connection_attempts'], 3)
        self.assertAlmostEqual(summary['success_rate'], 66.67, places=1)
        self.assertIn('status', summary)

    def test_alert_callbacks(self):
        """Test alert callback registration and firing."""
        alert_callback = Mock()
        self.monitor.register_alert_callback(alert_callback)

        timeout_config = {'connection_timeout': 30.0}

        # Add a connection that should trigger alerts (high time)
        self.monitor.record_connection_attempt('staging', 29.0, True, timeout_config)  # 96% of timeout

        # Verify callback was called (should trigger critical alert)
        alert_callback.assert_called()


if __name__ == '__main__':
    unittest.main()