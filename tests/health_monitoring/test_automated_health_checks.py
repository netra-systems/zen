"""
Test Suite for Automated Health Checks

Tests automated health checks with deployment integration including
pre-deployment validation, post-deployment verification, continuous monitoring,
and rollback triggers.
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.staging_health_checks import (
    AutomatedHealthChecker,
    HealthCheckMode,
    CheckResult
)


class TestAutomatedHealthChecker:
    """Test automated health checker initialization and configuration."""
    
    @pytest.fixture
    def health_checker(self):
        """Create automated health checker instance."""
        return AutomatedHealthChecker(
            backend_url="http://localhost:8000",
            config_path=None  # Use default config
        )
    
    def test_health_checker_initialization(self, health_checker):
        """Test health checker initialization with default config."""
        assert health_checker.backend_url == "http://localhost:8000"
        assert health_checker.config is not None
        assert "thresholds" in health_checker.config
        assert "deployment_checks" in health_checker.config
        assert "continuous_monitoring" in health_checker.config
        assert "rollback_triggers" in health_checker.config
    
    def test_health_checker_configuration_loading(self):
        """Test health checker configuration loading."""
        # Test with custom configuration
        custom_config = {
            "thresholds": {
                "overall_health_threshold": 0.9,
                "component_failure_threshold": 1
            }
        }
        
        config_path = "/tmp/test_health_config.json"
        with open(config_path, 'w') as f:
            json.dump(custom_config, f)
        
        try:
            checker = AutomatedHealthChecker(config_path=config_path)
            assert checker.config["thresholds"]["overall_health_threshold"] == 0.9
            assert checker.config["thresholds"]["component_failure_threshold"] == 1
        finally:
            os.remove(config_path)
    
    def test_health_checker_default_thresholds(self, health_checker):
        """Test default threshold configuration."""
        thresholds = health_checker.config["thresholds"]
        
        assert thresholds["overall_health_threshold"] == 0.8
        assert thresholds["component_failure_threshold"] == 2
        assert thresholds["response_time_threshold_ms"] == 1000
        assert thresholds["consecutive_failure_threshold"] == 3
        assert thresholds["rollback_threshold"] == 0.5


class TestPreDeploymentChecks:
    """Test pre-deployment validation checks."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for pre-deployment tests."""
        return AutomatedHealthChecker()
    
    @pytest.mark.asyncio
    async def test_pre_deployment_checks_success(self, health_checker):
        """Test successful pre-deployment checks."""
        # Mock all checks to pass
        with patch.object(health_checker, '_run_specific_check') as mock_check:
            mock_check.return_value = {
                "result": CheckResult.PASS,
                "message": "Check passed",
                "duration_seconds": 1.0
            }
            
            result, summary = await health_checker.run_pre_deployment_checks()
            
            assert result == CheckResult.PASS
            assert summary["deployment_approved"] is True
            assert summary["deployment_phase"] == "pre_deployment"
            assert summary["passed_checks"] == 5  # Number of pre-deployment checks
            assert summary["failed_checks"] == 0
    
    @pytest.mark.asyncio
    async def test_pre_deployment_checks_failure(self, health_checker):
        """Test pre-deployment checks with failures."""
        # Mock some checks to fail
        def mock_check_side_effect(check_name, mode):
            if check_name in ["websocket_health", "database_health"]:
                return {
                    "result": CheckResult.FAIL,
                    "message": f"{check_name} failed",
                    "duration_seconds": 1.0
                }
            else:
                return {
                    "result": CheckResult.PASS,
                    "message": "Check passed",
                    "duration_seconds": 1.0
                }
        
        with patch.object(health_checker, '_run_specific_check', side_effect=mock_check_side_effect):
            result, summary = await health_checker.run_pre_deployment_checks()
            
            assert result == CheckResult.FAIL
            assert summary["deployment_approved"] is False
            assert summary["failed_checks"] == 2
            assert summary["passed_checks"] == 3
    
    @pytest.mark.asyncio
    async def test_pre_deployment_checks_critical_failure(self, health_checker):
        """Test pre-deployment checks with critical failures."""
        # Mock critical failure
        with patch.object(health_checker, '_run_specific_check') as mock_check:
            mock_check.return_value = {
                "result": CheckResult.CRITICAL,
                "message": "Critical failure",
                "duration_seconds": 1.0
            }
            
            result, summary = await health_checker.run_pre_deployment_checks()
            
            assert result == CheckResult.FAIL
            assert summary["deployment_approved"] is False
    
    @pytest.mark.asyncio
    async def test_deployment_approval_evaluation(self, health_checker):
        """Test deployment approval evaluation logic."""
        # Test approval with all passing checks
        results_passing = {
            "check1": {"result": CheckResult.PASS},
            "check2": {"result": CheckResult.PASS},
            "check3": {"result": CheckResult.WARN}
        }
        
        approval = health_checker._evaluate_deployment_approval(results_passing)
        assert approval is True
        
        # Test rejection with critical failure
        results_critical = {
            "check1": {"result": CheckResult.PASS},
            "check2": {"result": CheckResult.CRITICAL},
            "check3": {"result": CheckResult.PASS}
        }
        
        approval = health_checker._evaluate_deployment_approval(results_critical)
        assert approval is False
        
        # Test rejection with too many failures
        results_many_failures = {
            "check1": {"result": CheckResult.FAIL},
            "check2": {"result": CheckResult.FAIL},
            "check3": {"result": CheckResult.FAIL}
        }
        
        approval = health_checker._evaluate_deployment_approval(results_many_failures)
        assert approval is False


class TestPostDeploymentVerification:
    """Test post-deployment verification checks."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for post-deployment tests."""
        return AutomatedHealthChecker()
    
    @pytest.mark.asyncio
    async def test_post_deployment_verification_success(self, health_checker):
        """Test successful post-deployment verification."""
        deployment_id = "test-deployment-123"
        
        # Mock all checks to pass
        with patch.object(health_checker, '_run_specific_check') as mock_check:
            mock_check.return_value = {
                "result": CheckResult.PASS,
                "message": "Check passed",
                "duration_seconds": 1.0
            }
            
            result, summary = await health_checker.run_post_deployment_verification(deployment_id)
            
            assert result == CheckResult.PASS
            assert summary["deployment_id"] == deployment_id
            assert summary["rollback_needed"] is False
            assert summary["deployment_phase"] == "post_deployment"
    
    @pytest.mark.asyncio
    async def test_post_deployment_verification_rollback_needed(self, health_checker):
        """Test post-deployment verification triggering rollback."""
        deployment_id = "test-deployment-456"
        
        # Mock critical failures that should trigger rollback
        def mock_check_side_effect(check_name, mode):
            if check_name in ["business_impact", "websocket_health"]:
                return {
                    "result": CheckResult.CRITICAL,
                    "message": f"Critical failure in {check_name}",
                    "business_impact_level": "critical",
                    "duration_seconds": 1.0
                }
            else:
                return {
                    "result": CheckResult.PASS,
                    "message": "Check passed",
                    "duration_seconds": 1.0
                }
        
        with patch.object(health_checker, '_run_specific_check', side_effect=mock_check_side_effect), \
             patch.object(health_checker, '_trigger_rollback') as mock_rollback:
            
            result, summary = await health_checker.run_post_deployment_verification(deployment_id)
            
            assert result == CheckResult.FAIL
            assert summary["rollback_needed"] is True
            mock_rollback.assert_called_once_with(deployment_id, summary["detailed_results"])
    
    @pytest.mark.asyncio
    async def test_rollback_evaluation_logic(self, health_checker):
        """Test rollback evaluation logic."""
        # Test rollback needed with critical failures
        results_critical = {
            "check1": {"result": CheckResult.CRITICAL},
            "check2": {"result": CheckResult.CRITICAL},
            "check3": {"result": CheckResult.CRITICAL}
        }
        
        rollback_needed = health_checker._evaluate_rollback_necessity(results_critical)
        assert rollback_needed is True
        
        # Test rollback needed with critical business impact
        results_business_impact = {
            "business_impact": {
                "result": CheckResult.FAIL,
                "business_impact_level": "critical"
            }
        }
        
        rollback_needed = health_checker._evaluate_rollback_necessity(results_business_impact)
        assert rollback_needed is True
        
        # Test no rollback needed
        results_healthy = {
            "check1": {"result": CheckResult.PASS},
            "check2": {"result": CheckResult.WARN},
            "check3": {"result": CheckResult.PASS}
        }
        
        rollback_needed = health_checker._evaluate_rollback_necessity(results_healthy)
        assert rollback_needed is False


class TestContinuousMonitoring:
    """Test continuous health monitoring functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for continuous monitoring tests."""
        checker = AutomatedHealthChecker()
        # Reduce interval for testing
        checker.continuous_check_interval = 1
        return checker
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring_startup(self, health_checker):
        """Test continuous monitoring startup and configuration."""
        assert health_checker.monitoring_active is False
        
        # Start monitoring in background task
        monitoring_task = asyncio.create_task(
            health_checker.start_continuous_monitoring()
        )
        
        # Give it time to start
        await asyncio.sleep(0.1)
        
        assert health_checker.monitoring_active is True
        
        # Stop monitoring
        health_checker.stop_continuous_monitoring()
        
        # Wait for task to complete
        await asyncio.sleep(0.1)
        monitoring_task.cancel()
        
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring_checks(self, health_checker):
        """Test continuous monitoring check execution."""
        # Mock check execution
        with patch.object(health_checker, '_run_specific_check') as mock_check:
            mock_check.return_value = {
                "result": CheckResult.PASS,
                "message": "Continuous check passed",
                "duration_seconds": 0.1
            }
            
            # Run a single continuous check cycle
            await health_checker._run_continuous_checks()
            
            # Verify checks were executed
            expected_checks = health_checker.config["continuous_monitoring"]["checks"]
            assert mock_check.call_count == len(expected_checks)
            
            # Verify results were stored
            assert len(health_checker.check_results) == len(expected_checks)
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring_critical_failure_detection(self, health_checker):
        """Test continuous monitoring critical failure detection."""
        # Mock critical failure
        def mock_check_side_effect(check_name, mode):
            if check_name == "critical_components":
                return {
                    "result": CheckResult.CRITICAL,
                    "message": "Critical component failure",
                    "duration_seconds": 0.1
                }
            else:
                return {
                    "result": CheckResult.PASS,
                    "message": "Check passed",
                    "duration_seconds": 0.1
                }
        
        with patch.object(health_checker, '_run_specific_check', side_effect=mock_check_side_effect), \
             patch.object(health_checker, '_send_alert_notification') as mock_alert:
            
            # Run continuous checks
            await health_checker._run_continuous_checks()
            
            # Verify critical failure was recorded
            assert len(health_checker.critical_failures) == 1
            assert health_checker.critical_failures[0]["check_name"] == "critical_components"
            
            # Verify alert was sent
            mock_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring_rollback_trigger(self, health_checker):
        """Test continuous monitoring rollback trigger."""
        # Add enough critical failures to trigger rollback
        for i in range(6):  # More than consecutive_failure_threshold
            health_checker.critical_failures.append({
                "check_name": f"check_{i}",
                "timestamp": time.time(),
                "result": CheckResult.CRITICAL
            })
        
        with patch.object(health_checker, '_trigger_emergency_rollback') as mock_rollback:
            
            # Check if rollback should be triggered
            should_rollback = health_checker._should_trigger_rollback()
            assert should_rollback is True
            
            # Simulate the rollback trigger
            await health_checker._trigger_emergency_rollback()
            
            assert health_checker.rollback_triggered is True
            assert health_checker.monitoring_active is False


class TestEnvironmentValidation:
    """Test environment validation functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for validation tests."""
        return AutomatedHealthChecker()
    
    @pytest.mark.asyncio
    async def test_validate_environment_success(self, health_checker):
        """Test successful environment validation."""
        # Mock all validation checks to pass
        with patch.object(health_checker, '_validate_environment_configuration') as mock_env_config, \
             patch.object(health_checker, '_validate_service_availability') as mock_services, \
             patch.object(health_checker, '_validate_resource_requirements') as mock_resources, \
             patch.object(health_checker, '_validate_network_connectivity') as mock_network, \
             patch.object(health_checker, '_validate_database_readiness') as mock_database:
            
            # Setup mock returns
            mock_env_config.return_value = {"result": CheckResult.PASS, "message": "Config valid"}
            mock_services.return_value = {"result": CheckResult.PASS, "message": "Services available"}
            mock_resources.return_value = {"result": CheckResult.PASS, "message": "Resources sufficient"}
            mock_network.return_value = {"result": CheckResult.PASS, "message": "Network healthy"}
            mock_database.return_value = {"result": CheckResult.PASS, "message": "Databases ready"}
            
            result, summary = await health_checker.validate_environment()
            
            assert result == CheckResult.PASS
            assert summary["environment_ready"] is True
            assert len(summary["validation_results"]) == 5
    
    @pytest.mark.asyncio
    async def test_validate_environment_configuration_check(self, health_checker):
        """Test environment configuration validation."""
        # Test valid configuration
        with patch('scripts.staging_health_checks.get_env') as mock_env:
            mock_env_instance = MagicMock()
            mock_env_instance.get.side_effect = lambda key: {
                "DATABASE_URL": "postgresql://user:pass@host:5432/db",
                "JWT_SECRET_KEY": "valid-secret-key-that-is-long-enough",
                "ENVIRONMENT": "staging"
            }.get(key)
            mock_env.return_value = mock_env_instance
            
            result = await health_checker._validate_environment_configuration()
            
            assert result["result"] == CheckResult.PASS
            assert result["message"] == "Environment configuration valid"
            assert len(result["missing_variables"]) == 0
            assert len(result["invalid_variables"]) == 0
        
        # Test missing configuration
        with patch('scripts.staging_health_checks.get_env') as mock_env:
            mock_env_instance = MagicMock()
            mock_env_instance.get.return_value = None
            mock_env.return_value = mock_env_instance
            
            result = await health_checker._validate_environment_configuration()
            
            assert result["result"] == CheckResult.FAIL
            assert len(result["missing_variables"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_service_availability_check(self, health_checker):
        """Test service availability validation."""
        # Mock HTTP client for service checks
        with patch('httpx.AsyncClient') as mock_client:
            # Setup successful HTTP responses
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await health_checker._validate_service_availability()
            
            assert result["result"] == CheckResult.PASS
            assert len(result["available_services"]) > 0
            assert len(result["unavailable_services"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_resource_requirements_check(self, health_checker):
        """Test resource requirements validation."""
        # Mock healthy resource metrics
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resources": {
                "cpu_usage_percent": 30.0,
                "memory_usage_percent": 50.0
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await health_checker._validate_resource_requirements()
            
            assert result["result"] == CheckResult.PASS
            assert "Sufficient resources available" in result["message"]


class TestSpecificHealthChecks:
    """Test specific health check implementations."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for specific check tests."""
        return AutomatedHealthChecker()
    
    @pytest.mark.asyncio
    async def test_websocket_health_check(self, health_checker):
        """Test WebSocket health check implementation."""
        # Mock successful WebSocket health response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "health_percentage": 100.0,
            "components_healthy": 3,
            "components_total": 3
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await health_checker._check_websocket_health(HealthCheckMode.PRE_DEPLOYMENT)
            
            assert result["result"] == CheckResult.PASS
            assert result["health_percentage"] == 100.0
            assert "WebSocket health excellent" in result["message"]
    
    @pytest.mark.asyncio
    async def test_database_health_check(self, health_checker):
        """Test database health check implementation."""
        # Mock successful database health response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "databases_healthy": 3,
            "databases_total": 3
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await health_checker._check_database_health(HealthCheckMode.PRE_DEPLOYMENT)
            
            assert result["result"] == CheckResult.PASS
            assert result["databases_healthy"] == 3
            assert result["databases_total"] == 3
            assert "All 3 databases healthy" in result["message"]
    
    @pytest.mark.asyncio
    async def test_service_health_check(self, health_checker):
        """Test service health check implementation."""
        # Mock successful service health response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "services_healthy": 2,
            "services_total": 2
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await health_checker._check_service_health(HealthCheckMode.PRE_DEPLOYMENT)
            
            assert result["result"] == CheckResult.PASS
            assert result["services_healthy"] == 2
            assert result["services_total"] == 2
            assert "All 2 services healthy" in result["message"]
    
    @pytest.mark.asyncio
    async def test_business_impact_check(self, health_checker):
        """Test business impact check implementation."""
        # Mock critical business impact response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "critical_analysis": {
                "business_impact_level": "critical"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await health_checker._check_business_impact(HealthCheckMode.POST_DEPLOYMENT)
            
            assert result["result"] == CheckResult.CRITICAL
            assert result["business_impact_level"] == "critical"
            assert "CRITICAL business impact detected" in result["message"]


class TestNotificationsAndAlerts:
    """Test notification and alert functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for notification tests."""
        config = {
            "notifications": {
                "webhook_urls": ["https://example.com/webhook"],
                "email_recipients": [],
                "slack_channels": []
            }
        }
        return AutomatedHealthChecker(config_path=None)
    
    @pytest.mark.asyncio
    async def test_send_alert_notification(self, health_checker):
        """Test alert notification sending."""
        check_name = "critical_components"
        result = {
            "result": CheckResult.CRITICAL,
            "message": "Critical component failure detected"
        }
        
        # Mock HTTP client for webhook
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.post.return_value = mock_response
            
            await health_checker._send_alert_notification(check_name, result)
            
            # Verify webhook was called
            mock_client.return_value.post.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_rollback_notification(self, health_checker):
        """Test rollback notification sending."""
        rollback_info = {
            "deployment_id": "test-deployment-789",
            "rollback_triggered_at": time.time(),
            "trigger_reason": "critical_health_check_failures"
        }
        
        # Mock HTTP client for webhook
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.post.return_value = mock_response
            
            await health_checker._send_rollback_notification(rollback_info)
            
            # Verify webhook was called
            mock_client.return_value.post.assert_called()


class TestHealthChecksIntegration:
    """Integration tests for automated health checks."""
    
    @pytest.mark.asyncio
    async def test_full_deployment_workflow(self):
        """Test complete deployment workflow with health checks."""
        health_checker = AutomatedHealthChecker()
        
        # Mock all HTTP responses as healthy
        def mock_http_response(status="healthy", **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "status": status,
                "health_percentage": 100.0,
                "databases_healthy": 3,
                "databases_total": 3,
                "services_healthy": 2,
                "services_total": 2,
                **kwargs
            }
            return response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_http_response()
            
            # Step 1: Pre-deployment checks
            pre_result, pre_summary = await health_checker.run_pre_deployment_checks()
            assert pre_result == CheckResult.PASS
            assert pre_summary["deployment_approved"] is True
            
            # Step 2: Post-deployment verification
            deployment_id = "integration-test-deployment"
            post_result, post_summary = await health_checker.run_post_deployment_verification(deployment_id)
            assert post_result == CheckResult.PASS
            assert post_summary["rollback_needed"] is False
            
            # Step 3: Environment validation
            env_result, env_summary = await health_checker.validate_environment()
            assert env_result == CheckResult.PASS
            assert env_summary["environment_ready"] is True
    
    @pytest.mark.asyncio
    async def test_failure_scenario_workflow(self):
        """Test deployment workflow with failures and rollback."""
        health_checker = AutomatedHealthChecker()
        
        # Mock HTTP responses with failures
        def mock_failing_response():
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "status": "unhealthy",
                "health_percentage": 20.0,
                "databases_healthy": 0,
                "databases_total": 3,
                "services_healthy": 0,
                "services_total": 2,
                "critical_analysis": {
                    "business_impact_level": "critical"
                }
            }
            return response
        
        with patch('httpx.AsyncClient') as mock_client, \
             patch.object(health_checker, '_trigger_rollback') as mock_rollback:
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_failing_response()
            
            # Step 1: Pre-deployment checks should fail
            pre_result, pre_summary = await health_checker.run_pre_deployment_checks()
            assert pre_result == CheckResult.FAIL
            assert pre_summary["deployment_approved"] is False
            
            # Step 2: Post-deployment verification should trigger rollback
            deployment_id = "failing-deployment"
            post_result, post_summary = await health_checker.run_post_deployment_verification(deployment_id)
            assert post_result == CheckResult.FAIL
            assert post_summary["rollback_needed"] is True
            
            # Verify rollback was triggered
            mock_rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])