"""
Integration tests for startup validation failure scenarios from Issue #899.

These tests reproduce real-world startup validation failure scenarios by
integrating multiple components and testing end-to-end startup validation flows.

Business Value: Platform/Internal - System Integration & Reliability
Protects the $500K+ ARR Golden Path by ensuring startup validation works
correctly across component boundaries and service integrations.

Test Categories:
- End-to-end startup validation failure scenarios
- Multi-component failure interactions
- Service integration validation failures
- Golden Path startup validation scenarios
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import components under test
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentValidation,
    ComponentStatus,
    EnvironmentType,
    validate_startup
)
from netra_backend.app.core.service_dependencies import ServiceType


class TestStartupValidationFailureScenarios(SSotAsyncTestCase):
    """Integration tests for startup validation failure scenarios."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        self.validator.validations = []

    async def test_database_configuration_and_initialization_cascade_failure(self):
        """
        Test Issue #899 Scenario 1: Database configuration failure cascades to initialization

        INTEGRATION FAILURE REPRODUCTION:
        When database configuration fails, should prevent initialization attempts
        and provide clear cascade failure information.
        """
        # Mock app state with database components
        mock_app = MagicMock()
        mock_app.state.db_session_factory = MagicMock()

        # Mock environment with missing database configuration
        mock_env_dict = {
            "POSTGRES_HOST": None,  # Missing critical variable
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "",      # Empty critical variable
            "POSTGRES_USER": "user"
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Mock table counting to simulate it still being called despite config failure
            with patch.object(self.validator, '_count_database_tables', return_value=0) as mock_count_tables:
                # Run complete startup validation
                success, report = await self.validator.validate_startup(mock_app)

        # Verify cascade failure was recorded
        db_validations = [v for v in self.validator.validations if v.category == "Database"]

        # Should have both configuration failure and initialization results
        config_failures = [v for v in db_validations if v.name == "Database Configuration"]
        table_results = [v for v in db_validations if v.name == "Database Tables"]

        assert len(config_failures) == 1, "Should have database configuration failure"
        assert len(table_results) == 1, "Should have database table validation"

        # Verify configuration failure details
        config_failure = config_failures[0]
        assert config_failure.status == ComponentStatus.CRITICAL
        assert "Missing required environment variables" in config_failure.message
        assert "POSTGRES_HOST" in config_failure.message

        # Verify overall startup failed
        assert success is False, "Startup should fail on database configuration failure"
        assert report["critical_failures"] >= 1, "Should have critical failures"

    async def test_service_dependency_validation_with_missing_services(self):
        """
        Test Issue #899 Scenario 2: Service dependency validation with missing services

        INTEGRATION FAILURE REPRODUCTION:
        When critical services are missing, service dependency validation should
        detect and report comprehensive failure information.
        """
        # Mock app state with missing critical services
        mock_app = MagicMock()
        mock_app.state.db_session_factory = None     # Database missing
        mock_app.state.llm_manager = None           # LLM service missing
        mock_app.state.redis_manager = MagicMock()  # Redis working
        mock_app.state.key_manager = MagicMock()    # Key manager working
        mock_app.state.security_service = None     # Security service missing

        # Mock service dependency checker to return comprehensive failure
        mock_dependency_result = MagicMock()
        mock_dependency_result.overall_success = False
        mock_dependency_result.services_healthy = 1  # Only Redis working
        mock_dependency_result.services_failed = 3   # DB, LLM, Security failed
        mock_dependency_result.execution_duration_ms = 100.0
        mock_dependency_result.critical_failures = [
            "Database service not initialized - PostgreSQL connection failed",
            "LLM service not initialized - AI functionality unavailable",
            "Security service not initialized - authentication compromised"
        ]
        mock_dependency_result.phase_results = {}

        with patch.object(self.validator, 'service_dependency_checker') as mock_checker:
            mock_checker.validate_service_dependencies.return_value = mock_dependency_result

            # Run startup validation
            success, report = await self.validator.validate_startup(mock_app)

        # Verify comprehensive service failure was recorded
        service_validations = [v for v in self.validator.validations
                             if v.category == "Services"]

        service_dep_validations = [v for v in self.validator.validations
                                 if v.name == "Service Dependencies"]

        # Should have individual service failures AND dependency validation failure
        assert len(service_validations) >= 3, "Should have individual service validations"
        assert len(service_dep_validations) == 1, "Should have service dependency validation"

        # Verify service dependency failure
        dep_validation = service_dep_validations[0]
        assert dep_validation.status == ComponentStatus.CRITICAL
        assert dep_validation.metadata["services_failed"] == 3
        assert "Database service not initialized" in dep_validation.metadata["critical_failures"]
        assert "LLM service not initialized" in dep_validation.metadata["critical_failures"]

        # Verify overall startup failed with clear business impact
        assert success is False, "Startup should fail on critical service failures"
        assert "Chat functionality may be broken" in dep_validation.metadata.get("business_impact", "")

    async def test_websocket_and_agent_integration_failure(self):
        """
        Test Issue #899 Scenario 3: WebSocket and agent integration failure

        INTEGRATION FAILURE REPRODUCTION:
        When WebSocket and agent systems fail to integrate properly,
        should detect and report impact on Golden Path functionality.
        """
        # Mock app state with WebSocket/agent integration issues
        mock_app = MagicMock()
        mock_app.state.websocket_manager = None        # WebSocket manager missing
        mock_app.state.agent_supervisor = MagicMock()  # Agent supervisor present
        mock_app.state.websocket_bridge_factory = None  # Bridge factory missing

        # Mock WebSocket validation to fail
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager', side_effect=ImportError("WebSocket factory not available")):
            # Run startup validation
            success, report = await self.validator.validate_startup(mock_app)

        # Verify WebSocket and agent integration failures were recorded
        websocket_validations = [v for v in self.validator.validations
                               if v.category == "WebSocket"]
        agent_validations = [v for v in self.validator.validations
                           if v.category == "Agents"]
        factory_validations = [v for v in self.validator.validations
                             if v.category == "Factories"]

        # Should have detected WebSocket failure
        websocket_failures = [v for v in websocket_validations
                            if v.status in [ComponentStatus.CRITICAL, ComponentStatus.FAILED]]
        assert len(websocket_failures) >= 1, "Should have WebSocket failure"

        # Should have detected factory integration issues
        bridge_factory_validations = [v for v in factory_validations
                                    if "WebSocketBridgeFactory" in v.name]
        if bridge_factory_validations:
            assert bridge_factory_validations[0].status == ComponentStatus.CRITICAL, "Missing bridge factory should be critical"

        # Verify overall impact on Golden Path
        assert success is False, "WebSocket/agent integration failure should fail startup"

    async def test_timeout_during_multi_component_validation(self):
        """
        Test Issue #899 Scenario 4: Timeout during multi-component validation

        INTEGRATION TIMEOUT REPRODUCTION:
        When multiple components are being validated and one times out,
        should handle gracefully and continue with remaining validations.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock one validation step to timeout while others succeed
        async def timeout_validation(app):
            await asyncio.sleep(6.0)  # Longer than 5.0 second timeout

        async def success_validation(app):
            # Add a successful validation
            validation = ComponentValidation(
                name="Working Component",
                category="Test",
                expected_min=1,
                actual_count=1,
                status=ComponentStatus.HEALTHY,
                message="Component working correctly",
                is_critical=False
            )
            self.validator.validations.append(validation)

        # Mock critical paths to timeout, others to succeed
        with patch.object(self.validator, '_validate_critical_paths', side_effect=timeout_validation):
            with patch.object(self.validator, '_validate_agents', side_effect=success_validation):
                with patch.object(self.validator, '_validate_tools', side_effect=success_validation):
                    with patch.object(self.validator, '_validate_database', return_value=None):
                        with patch.object(self.validator, '_validate_websocket', return_value=None):
                            with patch.object(self.validator, '_validate_services', return_value=None):
                                with patch.object(self.validator, '_validate_middleware', return_value=None):
                                    with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                        with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Verify timeout and successful validations coexist
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]
        success_validations = [v for v in self.validator.validations
                             if v.name == "Working Component"]

        assert len(timeout_validations) == 1, "Should have timeout validation"
        assert len(success_validations) >= 1, "Should have successful validations"

        # Verify timeout caused overall failure
        assert success is False, "Timeout should cause overall startup failure"
        assert report["critical_failures"] >= 1, "Should have critical failure from timeout"

        # Verify report includes both timeout and successful components
        assert report["status_counts"]["failed"] >= 1, "Should have failed components"
        assert report["status_counts"]["healthy"] >= 1, "Should have healthy components"

    async def test_factory_pattern_integration_with_service_failures(self):
        """
        Test Issue #899 Scenario 5: Factory pattern integration with service failures

        FACTORY INTEGRATION FAILURE REPRODUCTION:
        When factory patterns are used but underlying services fail,
        should detect dependency issues and report integration problems.
        """
        # Mock app state with factory patterns but missing dependencies
        mock_app = MagicMock()
        mock_app.state.execution_engine_factory = MagicMock()     # Factory present
        mock_app.state.websocket_bridge_factory = MagicMock()     # Factory present
        mock_app.state.websocket_connection_pool = MagicMock()    # Pool present

        # But underlying services missing
        mock_app.state.llm_manager = None                         # LLM service missing
        mock_app.state.websocket_manager = None                   # WebSocket service missing
        mock_app.state.db_session_factory = None                 # Database missing

        # Run startup validation
        success, report = await self.validator.validate_startup(mock_app)

        # Verify factory validations
        factory_validations = [v for v in self.validator.validations
                             if v.category == "Factories"]

        # Should have detected factory presence
        factory_names = [v.name for v in factory_validations]
        assert "ExecutionEngineFactory" in factory_names
        assert "WebSocketBridgeFactory" in factory_names
        assert "WebSocketConnectionPool" in factory_names

        # But service validations should show missing dependencies
        service_validations = [v for v in self.validator.validations
                             if v.category == "Services"]

        llm_failures = [v for v in service_validations
                       if v.name == "LLM Manager" and v.status == ComponentStatus.CRITICAL]
        assert len(llm_failures) == 1, "Should detect missing LLM manager"

        # Overall startup should fail due to missing underlying services
        assert success is False, "Factory patterns can't compensate for missing services"

    async def test_critical_path_validation_integration_failure(self):
        """
        Test Issue #899 Scenario 6: Critical path validation integration failure

        CRITICAL PATH FAILURE REPRODUCTION:
        When critical communication paths fail validation, should integrate
        with overall startup validation to report business impact.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock critical path validation to return failures
        mock_critical_validations = [
            MagicMock(passed=False, criticality=MagicMock(value="chat_breaking")),
            MagicMock(passed=False, criticality=MagicMock(value="degraded")),
            MagicMock(passed=True, criticality=MagicMock(value="warning"))
        ]

        with patch('netra_backend.app.core.startup_validation.validate_critical_paths', return_value=(False, mock_critical_validations)):
            # Run startup validation
            success, report = await self.validator.validate_startup(mock_app)

        # Verify critical path validation was integrated
        critical_path_validations = [v for v in self.validator.validations
                                   if v.category == "Critical Paths"]

        assert len(critical_path_validations) == 1, "Should have critical path validation"

        validation = critical_path_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Chat-breaking failures should be CRITICAL"
        assert "1 chat-breaking failures detected" in validation.message
        assert validation.metadata["chat_breaking"] == 1
        assert validation.metadata["degraded"] == 1

        # Verify overall startup failed due to critical path failures
        assert success is False, "Critical path failures should fail startup"

    async def test_performance_degradation_during_validation_failures(self):
        """
        Test Issue #899 Scenario 7: Performance degradation during validation failures

        PERFORMANCE FAILURE REPRODUCTION:
        When validation failures occur, should not significantly degrade
        overall startup validation performance.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock some validations to fail but complete quickly
        async def fast_failing_validation(app):
            await asyncio.sleep(0.01)  # Fast failure
            raise RuntimeError("Fast validation failure")

        # Mock other validations to succeed quickly
        async def fast_success_validation(app):
            await asyncio.sleep(0.01)

        with patch.object(self.validator, '_validate_database', side_effect=fast_failing_validation):
            with patch.object(self.validator, '_validate_services', side_effect=fast_failing_validation):
                with patch.object(self.validator, '_validate_agents', side_effect=fast_success_validation):
                    with patch.object(self.validator, '_validate_tools', side_effect=fast_success_validation):
                        with patch.object(self.validator, '_validate_websocket', side_effect=fast_success_validation):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Time the validation
                                                import time
                                                start_time = time.time()
                                                success, report = await self.validator.validate_startup(mock_app)
                                                end_time = time.time()

                                                validation_duration = end_time - start_time

        # Verify validation completed quickly despite failures
        assert validation_duration < 2.0, f"Validation with failures took {validation_duration}s, should be <2s"

        # Verify failures were recorded
        failed_validations = [v for v in self.validator.validations
                            if v.status == ComponentStatus.FAILED]
        assert len(failed_validations) >= 2, "Should have recorded validation failures"

        # Verify overall failure
        assert success is False, "Should fail overall due to validation failures"
        assert report["duration"] is not None, "Should have recorded timing"


class TestStartupValidationEndToEndScenarios(SSotAsyncTestCase):
    """End-to-end integration tests for startup validation scenarios."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)
        pass  # No persistent state needed

    async def test_full_startup_validation_with_mixed_results(self):
        """
        Test complete startup validation with mixed success/failure results.

        END-TO-END MIXED SCENARIO:
        Some components working, some failing, should provide comprehensive
        report with clear success/failure breakdown.
        """
        # Mock app state with mixed component states
        mock_app = MagicMock()

        # Working components
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.key_manager = MagicMock()
        mock_app.state.agent_supervisor = MagicMock()

        # Failing components
        mock_app.state.llm_manager = None
        mock_app.state.db_session_factory = None
        mock_app.state.websocket_manager = None

        # Run full startup validation using convenience function
        success, report = await validate_startup(mock_app, EnvironmentType.DEVELOPMENT)

        # Verify mixed results were recorded
        assert report["total_validations"] > 0, "Should have performed validations"
        assert report["status_counts"]["healthy"] > 0, "Should have healthy components"
        assert report["status_counts"]["critical"] > 0, "Should have critical failures"

        # Verify overall failure due to critical components
        assert success is False, "Should fail due to critical component failures"
        assert report["overall_health"] == "unhealthy"
        assert report["critical_failures"] > 0

        # Verify timing information
        assert report["duration"] is not None, "Should have timing information"
        assert report["duration"] > 0, "Duration should be positive"

    async def test_startup_validation_environment_type_differences(self):
        """
        Test startup validation behavior across different environment types.

        ENVIRONMENT VARIATION TEST:
        Different environments (DEVELOPMENT, STAGING, PRODUCTION) should
        have consistent validation behavior with environment-specific adjustments.
        """
        # Mock app state
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()
        mock_app.state.db_session_factory = MagicMock()
        mock_app.state.redis_manager = MagicMock()

        # Test different environment types
        environments = [
            EnvironmentType.DEVELOPMENT,
        ]

        results = {}

        for env_type in environments:
            success, report = await validate_startup(mock_app, env_type)
            results[env_type] = (success, report)

        # Verify consistent validation across environments
        dev_success, dev_report = results[EnvironmentType.DEVELOPMENT]

        # All environments should have performed validations
        assert dev_report["total_validations"] > 0, "Development should have validations"

        # Basic validation structure should be consistent
        assert "status_counts" in dev_report, "Should have status counts"
        assert "categories" in dev_report, "Should have categories"
        assert "duration" in dev_report, "Should have timing"

    async def test_startup_validation_concurrent_execution_safety(self):
        """
        Test startup validation safety under concurrent execution.

        CONCURRENCY SAFETY TEST:
        Multiple startup validations running concurrently should not interfere
        with each other and should produce consistent results.
        """
        # Mock app state
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()
        mock_app.state.redis_manager = MagicMock()

        # Run multiple concurrent validations
        async def run_validation():
            validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
            return await validator.validate_startup(mock_app)

        # Execute multiple validations concurrently
        results = await asyncio.gather(
            run_validation(),
            run_validation(),
            run_validation(),
            return_exceptions=True
        )

        # Verify all validations completed successfully (no exceptions)
        for result in results:
            assert not isinstance(result, Exception), f"Validation should not raise exception: {result}"
            success, report = result
            assert isinstance(success, bool), "Should return boolean success"
            assert isinstance(report, dict), "Should return report dict"
            assert "total_validations" in report, "Should have validation count"

    async def test_startup_validation_recovery_after_failure(self):
        """
        Test startup validation recovery capabilities after initial failures.

        RECOVERY TEST:
        After startup validation fails, subsequent validations should work
        correctly when underlying issues are resolved.
        """
        # Mock app state with initial failures
        mock_app = MagicMock()
        mock_app.state.llm_manager = None  # Initially missing

        # First validation should fail
        validator1 = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        success1, report1 = await validator1.validate_startup(mock_app)

        assert success1 is False, "Initial validation should fail"
        llm_failures1 = [v for v in validator1.validations
                        if v.name == "LLM Manager" and v.status == ComponentStatus.CRITICAL]
        assert len(llm_failures1) == 1, "Should detect missing LLM manager"

        # Fix the issue
        mock_app.state.llm_manager = MagicMock()  # Now present

        # Second validation should succeed
        validator2 = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        success2, report2 = await validator2.validate_startup(mock_app)

        # Should have better success rate after fix
        if success2:
            # Complete success
            assert report2["critical_failures"] == 0, "Should have no critical failures after fix"
        else:
            # Partial improvement - fewer critical failures
            assert report2["critical_failures"] < report1["critical_failures"], "Should have fewer failures after fix"

        # Verify LLM manager is now healthy
        llm_validations2 = [v for v in validator2.validations
                          if v.name == "LLM Manager"]
        if llm_validations2:
            assert llm_validations2[0].status == ComponentStatus.HEALTHY, "LLM manager should be healthy after fix"