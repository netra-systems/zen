"""
Comprehensive test suite for cross-service validators.

Tests all validator functionality and ensures proper validation of service boundaries.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any

from app.core.cross_service_validators import (
    CrossServiceValidatorFramework,
    ValidationReport,
    ValidationResult,
    ValidationStatus,
    ValidationSeverity,
    APIContractValidator,
    WebSocketContractValidator,
    UserDataConsistencyValidator,
    SessionStateValidator,
    MessageDeliveryValidator,
    LatencyValidator,
    ThroughputValidator,
    ResourceUsageValidator,
    TokenValidationValidator,
    PermissionEnforcementValidator,
    AuditTrailValidator,
    ServiceAuthValidator
)
from app.core.cross_service_validators.validation_orchestrator import (
    ValidationOrchestrator,
    ValidationReporter,
    ValidationScheduler
)


class TestValidatorFramework:
    """Test the core validator framework."""
    
    @pytest.fixture
    def framework(self):
        """Create test framework."""
        return CrossServiceValidatorFramework()
    
    @pytest.fixture
    def mock_validator(self):
        """Create mock validator."""
        class MockValidator:
            def __init__(self, name: str):
                self.name = name
            
            async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
                return [
                    ValidationResult(
                        validator_name=self.name,
                        check_name="test_check",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message="Test validation passed"
                    )
                ]
        
        return MockValidator("test_validator")
    
    def test_validator_registry(self, framework, mock_validator):
        """Test validator registry functionality."""
        # Register validator
        framework.registry.register(mock_validator, category="test")
        
        # Test retrieval
        retrieved = framework.registry.get_validator("test_validator")
        assert retrieved == mock_validator
        
        # Test category retrieval
        category_validators = framework.registry.get_validators_by_category("test")
        assert len(category_validators) == 1
        assert category_validators[0] == mock_validator
    
    @pytest.mark.asyncio
    async def test_validation_execution(self, framework, mock_validator):
        """Test validation execution."""
        framework.registry.register(mock_validator)
        
        report = await framework.run_validation(
            services=["test_service"],
            validator_names=["test_validator"]
        )
        
        assert isinstance(report, ValidationReport)
        assert report.total_checks == 1
        assert report.passed_checks == 1
        assert report.failed_checks == 0
        assert len(report.results) == 1
    
    def test_validation_result(self):
        """Test validation result creation."""
        result = ValidationResult(
            validator_name="test",
            check_name="check",
            status=ValidationStatus.PASSED,
            severity=ValidationSeverity.INFO,
            message="Test message"
        )
        
        assert result.validator_name == "test"
        assert result.status == ValidationStatus.PASSED
        assert result.severity == ValidationSeverity.INFO
    
    def test_validation_report(self):
        """Test validation report functionality."""
        report = ValidationReport(
            report_id="test-123",
            services_validated=["service1", "service2"],
            total_checks=0,
            execution_time_ms=100.0
        )
        
        # Test adding results
        result = ValidationResult(
            validator_name="test",
            check_name="check", 
            status=ValidationStatus.PASSED,
            severity=ValidationSeverity.INFO,
            message="Test"
        )
        
        report.add_result(result)
        
        assert report.total_checks == 1
        assert report.passed_checks == 1
        assert report.overall_status == ValidationStatus.PASSED


class TestContractValidators:
    """Test contract validators."""
    
    @pytest.fixture
    def api_validator(self):
        """Create API contract validator."""
        return APIContractValidator()
    
    @pytest.fixture
    def websocket_validator(self):
        """Create WebSocket contract validator."""
        return WebSocketContractValidator()
    
    @pytest.mark.asyncio
    async def test_api_contract_validation(self, api_validator):
        """Test API contract validation."""
        context = {
            "services": ["frontend", "backend"],
            "service_urls": {
                "frontend": "http://localhost:3000",
                "backend": "http://localhost:8000"
            }
        }
        
        results = await api_validator.validate(context)
        
        assert len(results) > 0
        assert all(isinstance(r, ValidationResult) for r in results)
    
    @pytest.mark.asyncio
    async def test_websocket_contract_validation(self, websocket_validator):
        """Test WebSocket contract validation."""
        context = {
            "services": ["frontend", "backend"]
        }
        
        results = await websocket_validator.validate(context)
        
        assert len(results) > 0
        # Should validate client and server message contracts
        check_names = [r.check_name for r in results]
        assert any("client_message" in name for name in check_names)
        assert any("server_message" in name for name in check_names)
    
    @pytest.mark.asyncio
    async def test_endpoint_validation_error_handling(self, api_validator):
        """Test endpoint validation error handling."""
        # Test with invalid context
        context = {"services": []}
        
        results = await api_validator.validate(context)
        
        # Should handle gracefully without throwing exceptions
        assert isinstance(results, list)


class TestDataConsistencyValidators:
    """Test data consistency validators."""
    
    @pytest.fixture
    def user_data_validator(self):
        """Create user data consistency validator."""
        return UserDataConsistencyValidator()
    
    @pytest.fixture
    def session_validator(self):
        """Create session state validator."""
        return SessionStateValidator()
    
    @pytest.fixture
    def message_validator(self):
        """Create message delivery validator."""
        return MessageDeliveryValidator()
    
    @pytest.mark.asyncio
    async def test_user_data_consistency(self, user_data_validator):
        """Test user data consistency validation."""
        context = {
            "services": ["auth", "backend"],
            "test_users": ["user-123", "user-456"]
        }
        
        results = await user_data_validator.validate(context)
        
        assert len(results) > 0
        # Should validate each test user
        user_checks = [r for r in results if "user_data_consistency" in r.check_name]
        assert len(user_checks) >= len(context["test_users"])
    
    @pytest.mark.asyncio
    async def test_session_state_validation(self, session_validator):
        """Test session state validation."""
        context = {
            "services": ["auth", "backend", "frontend"],
            "test_sessions": ["session-abc123"]
        }
        
        results = await session_validator.validate(context)
        
        assert len(results) > 0
        # Should validate session consistency and timeouts
        session_checks = [r for r in results if "session" in r.check_name]
        assert len(session_checks) > 0
    
    @pytest.mark.asyncio
    async def test_message_delivery_validation(self, message_validator):
        """Test message delivery validation."""
        context = {"services": ["frontend", "backend"]}
        
        results = await message_validator.validate(context)
        
        assert len(results) > 0
        # Should test ordering, confirmation, and duplicate detection
        check_names = [r.check_name for r in results]
        assert any("ordering" in name for name in check_names)
        assert any("confirmation" in name for name in check_names)
        assert any("duplicate" in name for name in check_names)


class TestPerformanceValidators:
    """Test performance validators."""
    
    @pytest.fixture
    def latency_validator(self):
        """Create latency validator."""
        config = {
            "latency_thresholds": {
                "api_call": 1000,
                "websocket_msg": 100,
                "auth_validation": 500
            }
        }
        return LatencyValidator(config)
    
    @pytest.fixture
    def throughput_validator(self):
        """Create throughput validator."""
        config = {
            "throughput_thresholds": {
                "api_requests": 100,
                "websocket_messages": 1000
            }
        }
        return ThroughputValidator(config)
    
    @pytest.fixture
    def resource_validator(self):
        """Create resource usage validator."""
        return ResourceUsageValidator()
    
    @pytest.mark.asyncio
    async def test_latency_validation(self, latency_validator):
        """Test latency validation."""
        context = {
            "services": ["frontend", "backend", "auth"],
            "service_urls": {
                "backend": "http://localhost:8000",
                "auth": "http://localhost:8001"
            }
        }
        
        results = await latency_validator.validate(context)
        
        assert len(results) > 0
        # Should test API, WebSocket, auth, and e2e latencies
        check_names = [r.check_name for r in results]
        assert any("api_" in name for name in check_names)
        assert any("websocket_" in name for name in check_names)
        assert any("auth_" in name for name in check_names)
    
    @pytest.mark.asyncio
    async def test_throughput_validation(self, throughput_validator):
        """Test throughput validation."""
        context = {"services": ["frontend", "backend", "auth"]}
        
        results = await throughput_validator.validate(context)
        
        assert len(results) > 0
        # Should test different throughput metrics
        throughput_checks = [r for r in results if "throughput" in r.check_name]
        assert len(throughput_checks) >= 3  # API, WebSocket, Auth
    
    @pytest.mark.asyncio
    async def test_resource_usage_validation(self, resource_validator):
        """Test resource usage validation."""
        context = {"services": ["frontend", "backend", "auth"]}
        
        results = await resource_validator.validate(context)
        
        assert len(results) > 0
        # Should check system and service resources
        check_names = [r.check_name for r in results]
        assert any("system_" in name for name in check_names)
        assert any("service_" in name for name in check_names)


class TestSecurityValidators:
    """Test security validators."""
    
    @pytest.fixture
    def token_validator(self):
        """Create token validation validator."""
        config = {
            "jwt_secret": "test-secret-key",
            "jwt_algorithm": "HS256"
        }
        return TokenValidationValidator(config)
    
    @pytest.fixture
    def permission_validator(self):
        """Create permission enforcement validator."""
        return PermissionEnforcementValidator()
    
    @pytest.fixture
    def audit_validator(self):
        """Create audit trail validator."""
        return AuditTrailValidator()
    
    @pytest.fixture
    def service_auth_validator(self):
        """Create service auth validator."""
        config = {
            "service_secrets": {
                "backend": "backend-secret",
                "frontend": "frontend-secret",
                "auth": "auth-secret"
            }
        }
        return ServiceAuthValidator(config)
    
    @pytest.mark.asyncio
    async def test_token_validation(self, token_validator):
        """Test token validation."""
        context = {"services": ["auth", "backend"]}
        
        results = await token_validator.validate(context)
        
        assert len(results) > 0
        # Should test consistency, expiration, tampering, and cross-service tokens
        check_names = [r.check_name for r in results]
        assert any("consistency" in name for name in check_names)
        assert any("expiration" in name for name in check_names)
        assert any("tampering" in name for name in check_names)
    
    @pytest.mark.asyncio
    async def test_permission_enforcement(self, permission_validator):
        """Test permission enforcement validation."""
        context = {"services": ["auth", "backend"]}
        
        results = await permission_validator.validate(context)
        
        assert len(results) > 0
        # Should test role-based, resource, inheritance, and escalation prevention
        check_names = [r.check_name for r in results]
        assert any("role_permissions" in name for name in check_names)
        assert any("resource_ownership" in name for name in check_names)
        assert any("privilege_escalation" in name for name in check_names)
    
    @pytest.mark.asyncio
    async def test_audit_trail_validation(self, audit_validator):
        """Test audit trail validation."""
        context = {"services": ["auth", "backend", "frontend"]}
        
        results = await audit_validator.validate(context)
        
        assert len(results) > 0
        # Should test completeness, integrity, and correlation
        check_names = [r.check_name for r in results]
        assert any("completeness" in name for name in check_names)
        assert any("integrity" in name for name in check_names)
        assert any("correlation" in name for name in check_names)
    
    @pytest.mark.asyncio
    async def test_service_authentication(self, service_auth_validator):
        """Test service authentication validation."""
        context = {"services": ["frontend", "backend", "auth"]}
        
        results = await service_auth_validator.validate(context)
        
        assert len(results) > 0
        # Should test service auth, authorization, and identity
        check_names = [r.check_name for r in results]
        assert any("service_auth" in name for name in check_names)
        assert any("service_permission" in name for name in check_names)
        assert any("service_identity" in name for name in check_names)


class TestValidationOrchestrator:
    """Test validation orchestrator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            "service_urls": {
                "frontend": "http://localhost:3000",
                "backend": "http://localhost:8000", 
                "auth": "http://localhost:8001"
            },
            "test_users": ["user-123", "user-456"],
            "test_sessions": ["session-abc123"],
            "latency_thresholds": {"api_call": 1000},
            "reporter": {"output_dir": "test_reports"}
        }
    
    @pytest.fixture
    def orchestrator(self, config):
        """Create test orchestrator."""
        return ValidationOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        # Should register all validators
        validator_names = orchestrator.framework.registry.list_validators()
        
        # Check that validators from all categories are registered
        assert any("api_contract" in name for name in validator_names)
        assert any("user_data" in name for name in validator_names)
        assert any("latency" in name for name in validator_names)
        assert any("token_validation" in name for name in validator_names)
    
    @pytest.mark.asyncio
    async def test_orchestrator_run_validation(self, orchestrator):
        """Test orchestrator validation execution."""
        services = ["frontend", "backend", "auth"]
        categories = ["contract", "security"]
        
        report = await orchestrator.run_validation(
            services=services,
            categories=categories,
            report_formats=["json"]
        )
        
        assert isinstance(report, ValidationReport)
        assert report.services_validated == services
        assert report.total_checks > 0
        assert report.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_orchestrator_specific_validators(self, orchestrator):
        """Test running specific validators."""
        services = ["frontend", "backend"]
        validator_names = ["api_contract_validator", "token_validation_validator"]
        
        report = await orchestrator.run_validation(
            services=services,
            validator_names=validator_names
        )
        
        assert isinstance(report, ValidationReport)
        # Should only run specified validators
        validator_names_in_results = [r.validator_name for r in report.results]
        assert all(name in ["api_contract_validator", "token_validation_validator"] 
                  for name in validator_names_in_results)


class TestValidationReporter:
    """Test validation reporter."""
    
    @pytest.fixture
    def reporter(self):
        """Create test reporter."""
        config = {"output_dir": "test_reports"}
        return ValidationReporter(config)
    
    @pytest.fixture
    def sample_report(self):
        """Create sample validation report."""
        report = ValidationReport(
            report_id="test-report-123",
            services_validated=["frontend", "backend"],
            total_checks=3,
            execution_time_ms=150.5
        )
        
        # Add sample results
        results = [
            ValidationResult(
                validator_name="test_validator",
                check_name="test_check_1",
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message="Test passed",
                service_pair="frontend-backend"
            ),
            ValidationResult(
                validator_name="test_validator",
                check_name="test_check_2",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message="Test failed",
                service_pair="backend-auth"
            ),
            ValidationResult(
                validator_name="test_validator",
                check_name="test_check_3",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="Test warning",
                service_pair="frontend-backend"
            )
        ]
        
        for result in results:
            report.add_result(result)
        
        return report
    
    @pytest.mark.asyncio
    async def test_json_report_generation(self, reporter, sample_report):
        """Test JSON report generation."""
        report_path = await reporter.generate_detailed_report(sample_report, "json")
        
        assert report_path.endswith(".json")
        assert "test_reports" in report_path
        
        # Verify file exists and contains valid JSON
        import json
        from pathlib import Path
        
        path = Path(report_path)
        assert path.exists()
        
        with open(path) as f:
            report_data = json.load(f)
        
        assert report_data["report_id"] == "test-report-123"
        assert len(report_data["results"]) == 3
        
        # Cleanup
        path.unlink()
    
    @pytest.mark.asyncio
    async def test_html_report_generation(self, reporter, sample_report):
        """Test HTML report generation."""
        report_path = await reporter.generate_detailed_report(sample_report, "html")
        
        assert report_path.endswith(".html")
        
        # Verify file contains HTML content
        from pathlib import Path
        
        path = Path(report_path)
        assert path.exists()
        
        with open(path) as f:
            content = f.read()
        
        assert "<!DOCTYPE html>" in content
        assert "Cross-Service Validation Report" in content
        assert "test-report-123" in content
        
        # Cleanup
        path.unlink()
    
    @pytest.mark.asyncio
    async def test_markdown_report_generation(self, reporter, sample_report):
        """Test Markdown report generation."""
        report_path = await reporter.generate_detailed_report(sample_report, "markdown")
        
        assert report_path.endswith(".md")
        
        # Verify file contains Markdown content
        from pathlib import Path
        
        path = Path(report_path)
        assert path.exists()
        
        with open(path) as f:
            content = f.read()
        
        assert "# Cross-Service Validation Report" in content
        assert "test-report-123" in content
        assert "## Summary" in content
        
        # Cleanup
        path.unlink()


class TestValidationScheduler:
    """Test validation scheduler."""
    
    @pytest.fixture
    def scheduler(self):
        """Create test scheduler."""
        config = {
            "schedule": {
                "critical_checks": {
                    "interval_minutes": 1,
                    "validators": ["token_validation"],
                    "services": ["auth", "backend"]
                }
            }
        }
        return ValidationScheduler(config)
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        orchestrator = Mock()
        orchestrator.run_validation = AsyncMock()
        orchestrator.run_validation.return_value = ValidationReport(
            report_id="scheduled-123",
            services_validated=["auth", "backend"],
            total_checks=1,
            execution_time_ms=50.0
        )
        return orchestrator
    
    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.config is not None
        assert scheduler.running_tasks == {}
    
    @pytest.mark.asyncio
    async def test_scheduled_validation(self, scheduler, mock_orchestrator):
        """Test scheduled validation execution."""
        # Create a short-lived scheduled validation
        schedule = {
            "name": "test_schedule",
            "interval_minutes": 0.01,  # Very short interval for testing
            "validators": ["token_validation"],
            "services": ["auth", "backend"]
        }
        
        # Start the scheduled validation
        task = asyncio.create_task(
            scheduler._run_scheduled_validation(schedule, mock_orchestrator)
        )
        
        # Let it run for a short time
        await asyncio.sleep(0.1)
        
        # Cancel the task
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify orchestrator was called
        mock_orchestrator.run_validation.assert_called()


# Integration tests
class TestValidationIntegration:
    """Integration tests for the complete validation system."""
    
    @pytest.mark.asyncio
    async def test_full_validation_pipeline(self):
        """Test complete validation pipeline."""
        config = {
            "service_urls": {
                "frontend": "http://localhost:3000",
                "backend": "http://localhost:8000",
                "auth": "http://localhost:8001"
            },
            "test_users": ["integration-user-123"],
            "test_sessions": ["integration-session-abc"],
            "reporter": {"output_dir": "integration_test_reports"}
        }
        
        orchestrator = ValidationOrchestrator(config)
        
        # Run validation with multiple categories
        report = await orchestrator.run_validation(
            services=["frontend", "backend", "auth"],
            categories=["contract", "data_consistency", "performance", "security"],
            report_formats=["json", "markdown"]
        )
        
        # Verify comprehensive report
        assert isinstance(report, ValidationReport)
        assert len(report.services_validated) == 3
        assert report.total_checks > 10  # Should have many checks across categories
        assert report.execution_time_ms > 0
        
        # Verify results from different validator categories
        validator_names = [r.validator_name for r in report.results]
        assert any("contract" in name for name in validator_names)
        assert any("consistency" in name for name in validator_names)
        assert any("performance" in name or "latency" in name for name in validator_names)
        assert any("security" in name or "token" in name for name in validator_names)
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling in validation system."""
        # Test with invalid configuration
        config = {
            "service_urls": {},  # Empty URLs should not crash the system
            "invalid_config": "test"
        }
        
        orchestrator = ValidationOrchestrator(config)
        
        # Should handle gracefully without crashing
        report = await orchestrator.run_validation(
            services=["nonexistent_service"],
            categories=["contract"]
        )
        
        assert isinstance(report, ValidationReport)
        # Some validators may fail, but system should continue
        assert report.total_checks >= 0
    
    def test_validator_independence(self):
        """Test that validators are independent and don't interfere."""
        framework = CrossServiceValidatorFramework()
        
        # Register validators from different categories
        validators = [
            APIContractValidator(),
            UserDataConsistencyValidator(),
            LatencyValidator(),
            TokenValidationValidator()
        ]
        
        for validator in validators:
            framework.registry.register(validator)
        
        # Verify all are registered independently
        registered_names = framework.registry.list_validators()
        assert len(registered_names) == len(validators)
        
        # Each validator should be retrievable
        for validator in validators:
            retrieved = framework.registry.get_validator(validator.name)
            assert retrieved == validator


if __name__ == "__main__":
    pytest.main([__file__, "-v"])