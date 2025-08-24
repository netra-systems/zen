"""Unit Tests for Staging Error Monitor - Deployment Safety Validation.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise
2. Business Goal: Reduce rollback time from 30min to 2min with automated error detection
3. Value Impact: Immediate post-deployment error detection prevents customer issues
4. Revenue Impact: +$20K MRR from enhanced deployment reliability

CRITICAL ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Comprehensive testing of deployment decision logic
- Error threshold validation and notification testing
- Console output formatting verification
"""

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

# Import the staging error monitor components
from netra_backend.app.schemas.monitoring_schemas import (
    ErrorResponse,
    ErrorSeverity,
    ErrorStatus,
    ErrorSummary,
    GCPError,
)
from scripts.staging_error_monitor import (
    ConsoleFormatter,
    DeploymentDecision,
    ErrorAnalyzer,
    ErrorThreshold,
    MonitorConfig,
    NotificationSender,
    StagingErrorMonitor,
    load_config_from_args,
    parse_deployment_time,
)

class TestErrorAnalyzer:
    """Test suite for ErrorAnalyzer deployment error analysis."""
    
    @pytest.fixture
    def deployment_time(self):
        """Create deployment time for testing."""
        return datetime.now(timezone.utc) - timedelta(minutes=5)
    
    @pytest.fixture
    def error_analyzer(self, deployment_time):
        """Create ErrorAnalyzer instance."""
        return ErrorAnalyzer(deployment_time)
    
    @pytest.fixture
    def sample_errors(self, deployment_time):
        """Create sample errors for testing."""
        return [
            self._create_test_error("pre-deploy-1", deployment_time - timedelta(minutes=10)),
            self._create_test_error("post-deploy-1", deployment_time + timedelta(minutes=2)),
            self._create_test_error("post-deploy-2", deployment_time + timedelta(minutes=3), ErrorSeverity.CRITICAL)
        ]

    def test_is_deployment_related_post_deployment_error(self, error_analyzer, deployment_time):
        """Test identification of post-deployment errors."""
        post_deploy_error = self._create_test_error("post-deploy", deployment_time + timedelta(minutes=1))
        
        result = error_analyzer.is_deployment_related(post_deploy_error)
        
        assert result is True

    def test_is_deployment_related_pre_deployment_error(self, error_analyzer, deployment_time):
        """Test identification of pre-deployment errors."""
        pre_deploy_error = self._create_test_error("pre-deploy", deployment_time - timedelta(minutes=1))
        
        result = error_analyzer.is_deployment_related(pre_deploy_error)
        
        assert result is False

    def test_categorize_errors_mixed_timing(self, error_analyzer, sample_errors):
        """Test error categorization by deployment timing."""
        result = error_analyzer.categorize_errors(sample_errors)
        
        assert len(result["deployment_related"]) == 2
        assert len(result["pre_existing"]) == 1
        assert "deployment_related" in result
        assert "pre_existing" in result

    def test_calculate_error_score_mixed_severities(self, error_analyzer):
        """Test error score calculation with mixed severities."""
        errors = [
            self._create_test_error("critical-1", datetime.now(timezone.utc), ErrorSeverity.CRITICAL),
            self._create_test_error("error-1", datetime.now(timezone.utc), ErrorSeverity.ERROR),
            self._create_test_error("error-2", datetime.now(timezone.utc), ErrorSeverity.ERROR)
        ]
        
        score = error_analyzer.calculate_error_score(errors)
        
        assert score == 20  # 1 critical (10) + 2 errors (5 each)

    def test_calculate_error_score_no_errors(self, error_analyzer):
        """Test error score calculation with empty error list."""
        score = error_analyzer.calculate_error_score([])
        
        assert score == 0

    # Helper method
    def _create_test_error(self, error_id: str, first_seen: datetime, severity: ErrorSeverity = ErrorSeverity.ERROR) -> GCPError:
        """Create test error with specified properties."""
        return GCPError(
            id=error_id,
            message=f"Test error {error_id}",
            service="netra-backend",
            severity=severity,
            first_seen=first_seen,
            last_seen=first_seen + timedelta(seconds=30)
        )

class TestConsoleFormatter:
    """Test suite for ConsoleFormatter output generation."""
    
    @pytest.fixture
    def console_formatter(self):
        """Create ConsoleFormatter instance."""
        return ConsoleFormatter()
    
    @pytest.fixture
    def sample_response(self):
        """Create sample error response for formatting."""
        errors = [self._create_sample_error("error-1"), self._create_sample_error("error-2")]
        summary = ErrorSummary(
            total_errors=2,
            error_errors=2,
            time_range_start=datetime.now(timezone.utc) - timedelta(hours=1),
            time_range_end=datetime.now(timezone.utc)
        )
        return ErrorResponse(errors=errors, summary=summary)

    def test_format_error_summary_contains_header(self, console_formatter, sample_response):
        """Test error summary formatting includes proper header."""
        result = console_formatter.format_error_summary(sample_response, {})
        
        assert "STAGING ERROR MONITORING REPORT" in result
        assert "=" * 60 in result
        assert len(result.split('\n')) >= 3

    def test_format_error_details_limits_to_five_errors(self, console_formatter):
        """Test error details formatting limits to 5 errors."""
        errors = [self._create_sample_error(f"error-{i}") for i in range(10)]
        
        result = console_formatter.format_error_details(errors)
        
        assert len([line for line in result if line.strip().startswith("•")]) <= 5

    def test_format_error_details_includes_service_and_count(self, console_formatter):
        """Test error details include service and occurrence count."""
        errors = [self._create_sample_error("test-error")]
        
        result = console_formatter.format_error_details(errors)
        
        assert any("Service:" in line for line in result)
        assert any("Count:" in line for line in result)

    def test_format_recommendation_deployment_failure(self, console_formatter):
        """Test recommendation formatting for deployment failure."""
        result = console_formatter.format_recommendation(should_fail=True, score=25)
        
        assert "❌ DEPLOYMENT FAILURE RECOMMENDED" in result
        assert "Score: 25" in result

    def test_format_recommendation_deployment_healthy(self, console_formatter):
        """Test recommendation formatting for healthy deployment."""
        result = console_formatter.format_recommendation(should_fail=False, score=5)
        
        assert "✅ DEPLOYMENT HEALTHY" in result
        assert "Score: 5" in result

    # Helper method
    def _create_sample_error(self, error_id: str) -> GCPError:
        """Create sample error for testing."""
        return GCPError(
            id=error_id,
            message=f"Sample error message for {error_id}",
            service="netra-backend",
            severity=ErrorSeverity.ERROR,
            occurrences=3,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )

class TestDeploymentDecision:
    """Test suite for DeploymentDecision logic."""
    
    @pytest.fixture
    def error_threshold(self):
        """Create error threshold configuration."""
        return ErrorThreshold(
            critical_errors_max=0,
            error_errors_max=5,
            deployment_failure_threshold=15
        )
    
    @pytest.fixture
    def deployment_decision(self, error_threshold):
        """Create DeploymentDecision instance."""
        return DeploymentDecision(error_threshold)

    def test_should_fail_deployment_critical_errors_exceed_threshold(self, deployment_decision):
        """Test deployment failure due to critical errors."""
        analysis = {
            "deployment_related": [
                self._create_mock_error(ErrorSeverity.CRITICAL),
                self._create_mock_error(ErrorSeverity.ERROR)
            ],
            "error_score": 15
        }
        
        should_fail, reason = deployment_decision.should_fail_deployment(analysis)
        
        assert should_fail is True
        assert "Critical errors: 1 > 0" in reason

    def test_should_fail_deployment_error_score_exceeds_threshold(self, deployment_decision):
        """Test deployment failure due to high error score."""
        analysis = {
            "deployment_related": [
                self._create_mock_error(ErrorSeverity.ERROR),
                self._create_mock_error(ErrorSeverity.ERROR),
                self._create_mock_error(ErrorSeverity.ERROR),
                self._create_mock_error(ErrorSeverity.ERROR)
            ],
            "error_score": 20  # 4 errors * 5 points each
        }
        
        should_fail, reason = deployment_decision.should_fail_deployment(analysis)
        
        assert should_fail is True
        assert "Error score: 20 > 15" in reason

    def test_should_fail_deployment_within_acceptable_limits(self, deployment_decision):
        """Test deployment success with acceptable error levels."""
        analysis = {
            "deployment_related": [
                self._create_mock_error(ErrorSeverity.ERROR)
            ],
            "error_score": 5
        }
        
        should_fail, reason = deployment_decision.should_fail_deployment(analysis)
        
        assert should_fail is False
        assert "Error levels within acceptable limits" in reason

    # Helper method
    def _create_mock_error(self, severity: ErrorSeverity) -> Mock:
        """Create mock error with specified severity."""
        # Mock: Generic component isolation for controlled unit testing
        error = Mock()
        error.severity = severity
        return error

class TestNotificationSender:
    """Test suite for NotificationSender functionality."""
    
    @pytest.fixture
    def config_with_notifications(self):
        """Create config with notifications enabled."""
        return MonitorConfig(
            enable_notifications=True,
            notification_webhook="https://example.com/webhook"
        )
    
    @pytest.fixture
    def config_without_notifications(self):
        """Create config with notifications disabled."""
        return MonitorConfig(enable_notifications=False)

    @pytest.mark.asyncio
    async def test_send_notification_enabled_config(self, config_with_notifications):
        """Test notification sending with enabled configuration."""
        sender = NotificationSender(config_with_notifications)
        
        result = await sender.send_notification("Test message", is_critical=True)
        
        assert result is False  # Implementation returns False as placeholder

    @pytest.mark.asyncio
    async def test_send_notification_disabled_config(self, config_without_notifications):
        """Test notification sending with disabled configuration."""
        sender = NotificationSender(config_without_notifications)
        
        result = await sender.send_notification("Test message")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_no_webhook_config(self):
        """Test notification sending without webhook configuration."""
        config = MonitorConfig(enable_notifications=True, notification_webhook=None)
        sender = NotificationSender(config)
        
        result = await sender.send_notification("Test message")
        
        assert result is False

class TestStagingErrorMonitor:
    """Test suite for StagingErrorMonitor main orchestrator."""
    
    @pytest.fixture
    def monitor_config(self):
        """Create monitor configuration for testing."""
        return MonitorConfig(
            project_id="test-project",
            service_filter="netra-backend",
            check_window_minutes=15
        )
    
    @pytest.fixture
    def staging_monitor(self, monitor_config):
        """Create StagingErrorMonitor instance."""
        return StagingErrorMonitor(monitor_config)

    @pytest.mark.asyncio
    async def test_check_deployment_errors_successful_flow(self, staging_monitor):
        """Test successful deployment error checking flow."""
        deployment_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        with patch.object(staging_monitor.error_service, 'fetch_errors', new_callable=AsyncMock) as mock_fetch:
            mock_response = self._create_mock_error_response()
            mock_fetch.return_value = mock_response
            
            result = await staging_monitor.check_deployment_errors(deployment_time)
            
            self._verify_analysis_result(result, mock_response)

    def test_parse_deployment_time_iso_format(self, staging_monitor):
        """Test deployment time parsing from ISO format."""
        iso_time = "2024-01-15T14:30:00Z"
        
        result = staging_monitor._parse_deployment_time(iso_time)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_format_console_output_complete_structure(self, staging_monitor):
        """Test complete console output formatting."""
        analysis = self._create_test_analysis()
        decision = (False, "All systems normal")
        
        result = staging_monitor.format_console_output(analysis, decision)
        
        assert "STAGING ERROR MONITORING REPORT" in result
        assert "✅ DEPLOYMENT HEALTHY" in result
        assert "Reason: All systems normal" in result

    @pytest.mark.asyncio
    async def test_run_error_check_success_flow(self, staging_monitor):
        """Test complete error check execution flow."""
        deployment_time_str = "2024-01-15T14:30:00Z"
        
        with patch.object(staging_monitor, 'initialize', new_callable=AsyncMock):
            with patch.object(staging_monitor, '_process_error_analysis', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = (self._create_test_analysis(), (False, "No issues"))
                
                exit_code = await staging_monitor.run_error_check(deployment_time_str)
                
                assert exit_code == 0

    @pytest.mark.asyncio
    async def test_run_error_check_deployment_failure(self, staging_monitor):
        """Test error check with deployment failure detected."""
        deployment_time_str = "2024-01-15T14:30:00Z"
        
        with patch.object(staging_monitor, 'initialize', new_callable=AsyncMock):
            with patch.object(staging_monitor, '_process_error_analysis', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = (self._create_test_analysis(), (True, "Critical errors detected"))
                
                exit_code = await staging_monitor.run_error_check(deployment_time_str)
                
                assert exit_code == 1

    @pytest.mark.asyncio
    async def test_run_error_check_exception_handling(self, staging_monitor):
        """Test error check exception handling."""
        deployment_time_str = "2024-01-15T14:30:00Z"
        
        with patch.object(staging_monitor, 'initialize', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("GCP connection failed")
            
            exit_code = await staging_monitor.run_error_check(deployment_time_str)
            
            assert exit_code == 2

    # Helper methods
    def _create_mock_error_response(self) -> ErrorResponse:
        """Create mock error response for testing."""
        errors = [GCPError(
            id="test-error",
            message="Test error",
            service="netra-backend",
            severity=ErrorSeverity.ERROR,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )]
        summary = ErrorSummary(
            total_errors=1,
            time_range_start=datetime.now(timezone.utc) - timedelta(hours=1),
            time_range_end=datetime.now(timezone.utc)
        )
        return ErrorResponse(errors=errors, summary=summary)

    def _verify_analysis_result(self, result: Dict[str, Any], expected_response: ErrorResponse):
        """Verify analysis result structure."""
        assert "deployment_related" in result
        assert "pre_existing" in result
        assert "error_score" in result
        assert "response" in result
        assert result["response"] == expected_response

    def _create_test_analysis(self) -> Dict[str, Any]:
        """Create test analysis data."""
        return {
            "deployment_related": [],
            "pre_existing": [],
            "error_score": 0,
            "response": self._create_mock_error_response()
        }

class TestConfigurationHelpers:
    """Test suite for configuration helper functions."""
    
    def test_load_config_from_args_project_id(self):
        """Test loading project ID from command line arguments."""
        args = ["--project-id", "custom-project", "--other-arg", "value"]
        
        config = load_config_from_args(args)
        
        assert config.project_id == "custom-project"

    def test_load_config_from_args_service_filter(self):
        """Test loading service filter from command line arguments."""
        args = ["--service", "custom-service", "--other-arg", "value"]
        
        config = load_config_from_args(args)
        
        assert config.service_filter == "custom-service"

    def test_parse_deployment_time_from_args(self):
        """Test parsing deployment time from command line arguments."""
        test_time = "2024-01-15T14:30:00Z"
        args = ["--deployment-time", test_time, "--other-arg", "value"]
        
        result = parse_deployment_time(args)
        
        assert result == test_time

    def test_parse_deployment_time_default_fallback(self):
        """Test deployment time parsing with default fallback."""
        args = ["--other-arg", "value"]
        
        result = parse_deployment_time(args)
        
        # Should return ISO format string (default behavior)
        assert isinstance(result, str)
        assert "T" in result  # ISO format contains T separator