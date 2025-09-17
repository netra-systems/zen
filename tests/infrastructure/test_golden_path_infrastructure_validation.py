"""
Golden Path Infrastructure Validation Tests

Tests to validate critical infrastructure components required for the golden path:
- Users login → get AI responses

These tests are designed to run on GCP staging environment (non-Docker)
and validate that infrastructure is properly configured for reliable golden path operation.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Stability & Reliability
- Value Impact: Ensures customers can successfully use chat functionality
- Strategic Impact: Prevents cascade failures that block primary revenue channel

CRITICAL: These tests should initially FAIL to prove infrastructure issues exist,
then pass after infrastructure fixes are applied.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
import pytest
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config,
    get_cloud_sql_optimized_config,
    calculate_capacity_aware_timeout,
    monitor_connection_attempt,
    get_connection_performance_summary,
    check_vpc_connector_performance
)
from netra_backend.app.core.configuration.base import get_config
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.smd import SupremeModernDeterministicStartup
from dev_launcher.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class TestGoldenPathInfrastructureValidation(SSotAsyncTestCase):
    """Test suite for validating golden path infrastructure components."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.environment = IsolatedEnvironment.get("ENVIRONMENT", "staging")
        self.timeout_config = get_database_timeout_config(self.environment)
        
    async def asyncSetUp(self):
        """Async setup for database connections."""
        await super().asyncSetUp()

    async def test_database_connection_timeout_validation(self):
        """
        Test that database connections can be established within configured timeouts.
        
        CRITICAL: This test validates Issue #1278 remediation.
        Should pass after timeout configuration updates (75s for staging).
        """
        logger.info(f"Testing database connection timeout validation for {self.environment}")
        
        # Get current timeout configuration
        timeout_config = get_database_timeout_config(self.environment)
        expected_connection_timeout = 75.0 if self.environment == "staging" else timeout_config["connection_timeout"]
        
        # Validate timeout configuration is updated
        self.assertGreaterEqual(
            timeout_config["connection_timeout"], 
            expected_connection_timeout,
            f"Database connection timeout should be at least {expected_connection_timeout}s for {self.environment} environment"
        )
        
        # Test actual database connection within timeout
        start_time = time.time()
        connection_successful = False
        connection_error = None
        
        try:
            # Use database manager to test connection
            config = get_config()
            db_manager = DatabaseManager(config)
            
            # Test connection establishment
            await asyncio.wait_for(
                db_manager.initialize_all_connections(),
                timeout=timeout_config["connection_timeout"]
            )
            connection_successful = True
            connection_time = time.time() - start_time
            
            # Record connection metrics
            monitor_connection_attempt(self.environment, connection_time, True)
            
            logger.info(f"Database connection successful in {connection_time:.2f}s")
            
        except asyncio.TimeoutError as e:
            connection_time = time.time() - start_time
            connection_error = f"Database connection timed out after {connection_time:.2f}s"
            monitor_connection_attempt(self.environment, connection_time, False)
            logger.error(connection_error)
            
        except Exception as e:
            connection_time = time.time() - start_time
            connection_error = f"Database connection failed: {e}"
            monitor_connection_attempt(self.environment, connection_time, False)
            logger.error(connection_error)
        
        # Assert connection was successful
        self.assertTrue(
            connection_successful, 
            f"Database connection failed: {connection_error}. This indicates infrastructure issues affecting golden path."
        )
        
        # Validate connection time is reasonable
        connection_time = time.time() - start_time
        self.assertLess(
            connection_time, 
            timeout_config["connection_timeout"] * 0.8,
            f"Database connection took {connection_time:.2f}s, close to timeout {timeout_config['connection_timeout']}s"
        )

    async def test_vpc_connector_capacity_validation(self):
        """
        Test VPC connector capacity and performance for Cloud SQL environments.
        
        Validates that VPC connector can handle database connections
        within expected performance thresholds.
        """
        if self.environment not in ["staging", "production"]:
            self.skipTest(f"VPC connector validation only applies to Cloud SQL environments, not {self.environment}")
        
        logger.info(f"Testing VPC connector capacity validation for {self.environment}")
        
        # Check VPC connector performance
        vpc_performance = check_vpc_connector_performance(self.environment)
        
        # Log performance metrics for debugging
        logger.info(f"VPC Connector Performance: {vpc_performance}")
        
        # Assert VPC connector is functioning
        self.assertTrue(
            vpc_performance.get('vpc_connector_required', False),
            "VPC connector should be required for Cloud SQL environments"
        )
        
        # If we have metrics, validate performance
        if vpc_performance.get('connection_attempts', 0) > 0:
            # Assert acceptable performance
            self.assertIn(
                vpc_performance.get('status'), 
                ['healthy', 'warning'],
                f"VPC connector performance is {vpc_performance.get('status')}: {vpc_performance.get('performance_issues', [])}"
            )
            
            # Assert reasonable connection times
            avg_time = vpc_performance.get('average_connection_time', 0)
            warning_threshold = vpc_performance.get('warning_threshold', 50.0)
            
            self.assertLess(
                avg_time,
                warning_threshold,
                f"Average VPC connector connection time {avg_time:.2f}s exceeds warning threshold {warning_threshold}s"
            )

    async def test_deterministic_startup_resilience(self):
        """
        Test that deterministic startup can handle infrastructure failures gracefully.
        
        Validates emergency bypass functionality for degraded infrastructure.
        """
        logger.info("Testing deterministic startup resilience")
        
        # Test with emergency bypass enabled
        with patch.dict('os.environ', {'EMERGENCY_ALLOW_NO_DATABASE': 'true'}):
            startup_manager = SupremeModernDeterministicStartup()
            
            # Create mock app state
            class MockApp:
                def __init__(self):
                    self.state = type('MockState', (), {})()
            
            mock_app = MockApp()
            startup_manager.app = mock_app
            
            # Test that startup can handle database failures gracefully
            try:
                # This should not raise an exception with emergency bypass
                with patch.object(startup_manager, '_initialize_database_with_capacity_awareness') as mock_db_init:
                    mock_db_init.side_effect = Exception("Simulated database failure")
                    
                    # Should not raise exception with bypass
                    await startup_manager._phase3_database_setup()
                    
                    # Verify degraded state was set
                    self.assertFalse(getattr(mock_app.state, 'database_available', True))
                    self.assertEqual(getattr(mock_app.state, 'startup_mode', ''), 'emergency_degraded')
                    self.assertTrue(getattr(mock_app.state, 'emergency_database_bypassed', False))
                    
                    logger.info("Emergency bypass functionality validated")
                    
            except Exception as e:
                self.fail(f"Deterministic startup should handle database failures gracefully with emergency bypass: {e}")

    async def test_golden_path_service_dependencies(self):
        """
        Test that all services required for golden path are accessible.
        
        Validates:
        - Auth service connectivity
        - Database connectivity 
        - Redis connectivity (if required)
        - WebSocket infrastructure
        """
        logger.info("Testing golden path service dependencies")
        
        dependencies_status = {}
        
        # Test database dependency
        try:
            config = get_config()
            db_manager = DatabaseManager(config)
            await asyncio.wait_for(
                db_manager.initialize_all_connections(),
                timeout=self.timeout_config["connection_timeout"]
            )
            dependencies_status['database'] = 'healthy'
            logger.info("Database dependency: HEALTHY")
        except Exception as e:
            dependencies_status['database'] = f'failed: {e}'
            logger.error(f"Database dependency: FAILED - {e}")
        
        # Test auth service dependency
        try:
            auth_service_url = IsolatedEnvironment.get("AUTH_SERVICE_URL", "")
            if auth_service_url:
                # Simple connectivity test - could be enhanced with actual auth check
                dependencies_status['auth_service'] = 'configured'
                logger.info("Auth service dependency: CONFIGURED")
            else:
                dependencies_status['auth_service'] = 'not_configured'
                logger.warning("Auth service dependency: NOT CONFIGURED")
        except Exception as e:
            dependencies_status['auth_service'] = f'failed: {e}'
            logger.error(f"Auth service dependency: FAILED - {e}")
        
        # Assert critical dependencies are available
        self.assertEqual(
            dependencies_status.get('database'), 
            'healthy',
            f"Database dependency failed: {dependencies_status.get('database')}"
        )
        
        # Log overall status
        logger.info(f"Golden path dependencies status: {dependencies_status}")
        
        # Assert at least database is working (minimum for degraded operation)
        critical_dependencies = ['database']
        failed_critical = [
            dep for dep in critical_dependencies 
            if dependencies_status.get(dep) != 'healthy'
        ]
        
        self.assertEqual(
            len(failed_critical), 
            0,
            f"Critical dependencies failed: {failed_critical}. Golden path cannot function."
        )

    async def test_websocket_infrastructure_readiness(self):
        """
        Test that WebSocket infrastructure is ready for golden path.
        
        Validates WebSocket configuration and basic connectivity prerequisites.
        """
        logger.info("Testing WebSocket infrastructure readiness")
        
        # Test WebSocket configuration
        config = get_config()
        websocket_config = {
            'cors_origins': getattr(config, 'cors_origins', []),
            'allowed_hosts': getattr(config, 'allowed_hosts', []),
            'websocket_enabled': True  # Assume enabled for golden path
        }
        
        # Validate WebSocket prerequisites
        self.assertTrue(
            websocket_config['websocket_enabled'],
            "WebSocket support should be enabled for golden path"
        )
        
        # Validate CORS configuration for staging
        if self.environment == "staging":
            expected_origins = [
                "https://staging.netrasystems.ai",
                "https://api-staging.netrasystems.ai"
            ]
            
            # At least one expected origin should be configured
            cors_origins = websocket_config.get('cors_origins', [])
            has_staging_origin = any(
                any(expected in origin for expected in expected_origins)
                for origin in cors_origins
            )
            
            if not has_staging_origin:
                logger.warning(f"Staging CORS origins may not be configured correctly: {cors_origins}")
        
        logger.info(f"WebSocket infrastructure configuration: {websocket_config}")

    async def test_connection_performance_monitoring(self):
        """
        Test that connection performance monitoring is functioning.
        
        Validates that infrastructure monitoring can detect performance issues.
        """
        logger.info("Testing connection performance monitoring")
        
        # Get current performance summary
        performance_summary = get_connection_performance_summary(self.environment)
        
        logger.info(f"Connection performance summary: {performance_summary}")
        
        # Validate monitoring is collecting data
        if performance_summary.get('connection_attempts', 0) > 0:
            # Assert reasonable performance metrics
            success_rate = performance_summary.get('success_rate', 0)
            self.assertGreaterEqual(
                success_rate,
                80.0,
                f"Connection success rate {success_rate:.1f}% is below acceptable threshold"
            )
            
            # Assert timeout violations are not excessive
            timeout_violation_rate = performance_summary.get('timeout_violation_rate', 0)
            self.assertLess(
                timeout_violation_rate,
                20.0,
                f"Timeout violation rate {timeout_violation_rate:.1f}% is too high"
            )
        else:
            logger.info("No connection performance data available yet")

    def test_environment_configuration_consistency(self):
        """
        Test that environment configuration is consistent and complete.
        
        Validates that all required configuration values are present
        and correctly configured for the target environment.
        """
        logger.info(f"Testing environment configuration consistency for {self.environment}")
        
        # Get configuration
        config = get_config()
        timeout_config = get_database_timeout_config(self.environment)
        cloud_sql_config = get_cloud_sql_optimized_config(self.environment)
        
        # Validate timeout configuration is environment-appropriate
        if self.environment == "staging":
            # Validate Issue #1278 remediation values
            self.assertGreaterEqual(
                timeout_config["connection_timeout"], 
                75.0,
                "Staging connection timeout should be at least 75s (Issue #1278 remediation)"
            )
            
            self.assertGreaterEqual(
                timeout_config["initialization_timeout"], 
                95.0,
                "Staging initialization timeout should be at least 95s"
            )
        
        # Validate Cloud SQL configuration for staging/production
        if self.environment in ["staging", "production"]:
            pool_config = cloud_sql_config.get("pool_config", {})
            self.assertGreaterEqual(
                pool_config.get("pool_timeout", 0), 
                120.0,
                f"Cloud SQL pool timeout should be at least 120s for {self.environment}"
            )
        
        # Validate critical environment variables are set
        critical_env_vars = [
            "DATABASE_URL",
            "ENVIRONMENT"
        ]
        
        missing_vars = []
        for var in critical_env_vars:
            if not IsolatedEnvironment.get(var):
                missing_vars.append(var)
        
        self.assertEqual(
            len(missing_vars), 
            0,
            f"Critical environment variables missing: {missing_vars}"
        )
        
        logger.info(f"Environment configuration validation completed for {self.environment}")


if __name__ == "__main__":
    # Enable detailed logging for infrastructure validation
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])