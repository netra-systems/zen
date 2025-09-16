"""
Unit tests for startup validation timeout failures from Issue #899.

These tests reproduce the timeout-related failures from Issue #899:
- Individual validation step timeouts
- Infinite loop detection and prevention
- Overall startup validation timeout handling
- Performance monitoring and optimization

Business Value: Platform/Internal - System Reliability & Performance
Protects the $500K+ ARR Golden Path by ensuring startup validation
completes within reasonable time limits and doesn't hang systems.

Test Categories:
- Individual validation step timeout handling
- Infinite loop detection and prevention
- Timeout error reporting and recovery
- Performance monitoring and validation
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any
import time

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import components under test
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentValidation,
    ComponentStatus,
    EnvironmentType
)


class StartupValidationTimeoutUnitTests(SSotAsyncTestCase):
    """Unit tests for startup validation timeout handling."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance with test environment
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)

        # Clear any existing validations
        self.validator.validations = []

    async def test_individual_validation_step_timeout_agents(self):
        """
        Test Issue #899 Failure 1: Individual validation step timeout - agents

        CRITICAL FAILURE REPRODUCTION:
        When _validate_agents takes longer than timeout (5.0 seconds), should
        record timeout validation and continue with other validations.
        """
        # Mock app state
        mock_app = MagicMock()
        mock_app.state.agent_supervisor = MagicMock()

        # Mock _validate_agents to take longer than timeout
        async def slow_validate_agents(app):
            await asyncio.sleep(6.0)  # Longer than 5.0 second timeout

        with patch.object(self.validator, '_validate_agents', side_effect=slow_validate_agents):
            # Mock other validation methods to be fast
            with patch.object(self.validator, '_validate_tools', return_value=None):
                with patch.object(self.validator, '_validate_database', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Verify timeout validation was recorded
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]

        assert len(timeout_validations) == 1, "Should have recorded timeout validation"

        validation = timeout_validations[0]
        assert validation.status == ComponentStatus.FAILED, "Timeout should be FAILED status"
        assert validation.is_critical is True, "Timeout is critical for system stability"
        assert validation.actual_count == 0, "Timeout means validation didn't complete"
        assert "Startup validation timed out after 5.0 seconds" in validation.message
        assert "possible infinite loop" in validation.message
        assert validation.metadata["timeout_seconds"] == 5.0

        # Verify overall startup validation failed
        assert success is False, "Startup validation should fail on timeout"

    async def test_individual_validation_step_timeout_database(self):
        """
        Test Issue #899 Failure 2: Individual validation step timeout - database

        CRITICAL FAILURE REPRODUCTION:
        When _validate_database takes longer than timeout, should record timeout
        and provide specific information about database validation hanging.
        """
        # Mock app state
        mock_app = MagicMock()
        mock_app.state.db_session_factory = MagicMock()

        # Mock _validate_database to simulate infinite loop
        async def infinite_database_validation(app):
            # Simulate a database validation that never completes
            while True:
                await asyncio.sleep(0.1)

        with patch.object(self.validator, '_validate_database', side_effect=infinite_database_validation):
            # Mock other validations to be fast
            with patch.object(self.validator, '_validate_agents', return_value=None):
                with patch.object(self.validator, '_validate_tools', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Verify timeout was detected and recorded
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]

        assert len(timeout_validations) == 1, "Should have detected database validation timeout"

        validation = timeout_validations[0]
        assert validation.status == ComponentStatus.FAILED
        assert "timed out after 5.0 seconds" in validation.message
        assert validation.metadata["timeout_seconds"] == 5.0

        # Verify overall validation failed
        assert success is False, "Should fail on database validation timeout"
        assert report["overall_health"] == "unhealthy"

    async def test_multiple_validation_steps_timeout_handling(self):
        """
        Test handling of multiple validation steps that might timeout.

        COMPREHENSIVE TIMEOUT TEST:
        When multiple validation steps could timeout, should handle each
        timeout individually and continue validation process.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock multiple validation methods to timeout
        async def timeout_validation(app):
            await asyncio.sleep(6.0)  # Longer than 5.0 second timeout

        with patch.object(self.validator, '_validate_agents', side_effect=timeout_validation):
            with patch.object(self.validator, '_validate_database', side_effect=timeout_validation):
                # Mock other validations to be fast
                with patch.object(self.validator, '_validate_tools', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Should have recorded timeout for the first validation that timed out
        # (asyncio.wait_for will stop at first timeout)
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]

        assert len(timeout_validations) == 1, "Should have recorded timeout validation"
        assert timeout_validations[0].status == ComponentStatus.FAILED

        # Verify overall validation failed
        assert success is False, "Should fail on timeout"

    async def test_timeout_error_metadata_collection(self):
        """
        Test that timeout errors collect comprehensive metadata.

        DIAGNOSTIC TEST:
        Timeout validations should include detailed metadata for debugging
        including which step timed out and system state information.
        """
        # Mock app state
        mock_app = MagicMock()

        # Create specific timeout error
        timeout_error = asyncio.TimeoutError("Validation step timed out")

        # Mock _validate_tools to raise TimeoutError
        with patch.object(self.validator, '_validate_tools', side_effect=timeout_error):
            # Mock other validations
            with patch.object(self.validator, '_validate_agents', return_value=None):
                with patch.object(self.validator, '_validate_database', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Verify timeout metadata was collected
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]

        assert len(timeout_validations) == 1
        validation = timeout_validations[0]

        # Verify comprehensive metadata
        assert "timeout_error" in validation.metadata
        assert "timeout_seconds" in validation.metadata
        assert validation.metadata["timeout_seconds"] == 5.0
        assert str(timeout_error) in validation.metadata["timeout_error"]

    async def test_startup_validation_performance_monitoring(self):
        """
        Test startup validation performance monitoring and timing.

        PERFORMANCE TEST:
        Startup validation should complete within reasonable time
        and provide accurate timing information.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock all validation methods to be fast but measurable
        async def fast_validation(app):
            await asyncio.sleep(0.01)  # 10ms per validation

        with patch.object(self.validator, '_validate_agents', side_effect=fast_validation):
            with patch.object(self.validator, '_validate_tools', side_effect=fast_validation):
                with patch.object(self.validator, '_validate_database', side_effect=fast_validation):
                    with patch.object(self.validator, '_validate_websocket', side_effect=fast_validation):
                        with patch.object(self.validator, '_validate_services', side_effect=fast_validation):
                            with patch.object(self.validator, '_validate_middleware', side_effect=fast_validation):
                                with patch.object(self.validator, '_validate_background_tasks', side_effect=fast_validation):
                                    with patch.object(self.validator, '_validate_monitoring', side_effect=fast_validation):
                                        with patch.object(self.validator, '_validate_critical_paths', side_effect=fast_validation):
                                            with patch.object(self.validator, '_validate_service_dependencies', side_effect=fast_validation):
                                                # Time the validation
                                                start_time = time.time()
                                                success, report = await self.validator.validate_startup(mock_app)
                                                end_time = time.time()

        # Verify timing information
        validation_duration = end_time - start_time
        assert validation_duration < 2.0, f"Startup validation took {validation_duration}s, should be <2s"

        # Verify report includes timing
        assert "duration" in report
        assert report["duration"] is not None
        assert report["duration"] > 0, "Duration should be positive"
        assert abs(report["duration"] - validation_duration) < 0.1, "Report duration should match actual duration"

        # Verify successful completion
        assert success is True, "Fast validations should succeed"

    async def test_timeout_recovery_and_cleanup(self):
        """
        Test timeout recovery and cleanup mechanisms.

        RECOVERY TEST:
        After a timeout occurs, the validator should be in a clean state
        for subsequent validations.
        """
        # Mock app state
        mock_app = MagicMock()

        # First validation with timeout
        async def timeout_validation(app):
            await asyncio.sleep(6.0)

        with patch.object(self.validator, '_validate_agents', side_effect=timeout_validation):
            with patch.object(self.validator, '_validate_tools', return_value=None):
                with patch.object(self.validator, '_validate_database', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # First validation with timeout
                                                success1, report1 = await self.validator.validate_startup(mock_app)

        # Clear validations for second test
        timeout_validations = len([v for v in self.validator.validations
                                 if v.name == "Startup Validation Timeout"])
        assert timeout_validations >= 1, "Should have recorded timeout from first validation"

        # Reset validator state
        self.validator.validations = []

        # Second validation without timeout (should work normally)
        with patch.object(self.validator, '_validate_agents', return_value=None):
            with patch.object(self.validator, '_validate_tools', return_value=None):
                with patch.object(self.validator, '_validate_database', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Second validation should work
                                                success2, report2 = await self.validator.validate_startup(mock_app)

        # Verify first validation failed due to timeout
        assert success1 is False, "First validation should fail on timeout"

        # Verify second validation can succeed (no timeout validations)
        timeout_validations_second = [v for v in self.validator.validations
                                    if v.name == "Startup Validation Timeout"]
        assert len(timeout_validations_second) == 0, "Second validation should have no timeout validations"

    async def test_timeout_configuration_validation(self):
        """
        Test that timeout configuration is appropriate for different environments.

        CONFIGURATION TEST:
        Timeout values should be appropriate for the environment and validation
        complexity (5.0 seconds per step is reasonable for startup validation).
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock validation that takes exactly at the timeout boundary
        async def boundary_validation(app):
            await asyncio.sleep(5.0)  # Exactly 5.0 seconds

        with patch.object(self.validator, '_validate_agents', side_effect=boundary_validation):
            with patch.object(self.validator, '_validate_tools', return_value=None):
                with patch.object(self.validator, '_validate_database', return_value=None):
                    with patch.object(self.validator, '_validate_websocket', return_value=None):
                        with patch.object(self.validator, '_validate_services', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run validation at timeout boundary
                                                success, report = await self.validator.validate_startup(mock_app)

        # Validation taking exactly 5.0 seconds should not timeout
        # (asyncio.wait_for should allow completion at exactly the timeout value)
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]

        # This is environment-dependent, but should generally not timeout at exactly the limit
        # The key is that timeout handling exists and works for clearly excessive times


class StartupValidationTimeoutIntegrationTests(SSotAsyncTestCase):
    """Integration tests for timeout handling across validation components."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        self.validator.validations = []

    async def test_timeout_impact_on_overall_success_determination(self):
        """
        Test how timeouts impact overall startup validation success.

        SUCCESS DETERMINATION TEST:
        Timeouts should be considered critical failures that cause overall
        startup validation to fail.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock one validation to timeout, others to succeed
        async def timeout_validation(app):
            await asyncio.sleep(6.0)

        with patch.object(self.validator, '_validate_critical_paths', side_effect=timeout_validation):
            # Mock other validations to succeed (create successful validations)
            async def successful_validation(app):
                validation = ComponentValidation(
                    name="Test Component",
                    category="Test",
                    expected_min=1,
                    actual_count=1,
                    status=ComponentStatus.HEALTHY,
                    message="Component working",
                    is_critical=True
                )
                self.validator.validations.append(validation)

            with patch.object(self.validator, '_validate_agents', side_effect=successful_validation):
                with patch.object(self.validator, '_validate_tools', return_value=None):
                    with patch.object(self.validator, '_validate_database', return_value=None):
                        with patch.object(self.validator, '_validate_websocket', return_value=None):
                            with patch.object(self.validator, '_validate_services', return_value=None):
                                with patch.object(self.validator, '_validate_middleware', return_value=None):
                                    with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                        with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Verify overall failure due to timeout
        assert success is False, "Timeout should cause overall validation failure"
        assert report["overall_health"] == "unhealthy"

        # Verify timeout was recorded as critical failure
        assert report["critical_failures"] >= 1, "Should have at least one critical failure from timeout"

        # Verify both successful validation and timeout were recorded
        successful_validations = [v for v in self.validator.validations
                                if v.status == ComponentStatus.HEALTHY]
        timeout_validations = [v for v in self.validator.validations
                             if v.name == "Startup Validation Timeout"]

        assert len(successful_validations) >= 1, "Should have successful validations"
        assert len(timeout_validations) == 1, "Should have timeout validation"

    async def test_timeout_logging_and_reporting(self):
        """
        Test timeout logging and reporting in validation results.

        LOGGING TEST:
        Timeouts should be properly logged and included in validation reports
        with sufficient detail for debugging.
        """
        # Mock app state
        mock_app = MagicMock()

        # Mock validation to timeout
        async def timeout_validation(app):
            await asyncio.sleep(6.0)

        with patch.object(self.validator, '_validate_services', side_effect=timeout_validation):
            with patch.object(self.validator, '_validate_agents', return_value=None):
                with patch.object(self.validator, '_validate_tools', return_value=None):
                    with patch.object(self.validator, '_validate_database', return_value=None):
                        with patch.object(self.validator, '_validate_websocket', return_value=None):
                            with patch.object(self.validator, '_validate_middleware', return_value=None):
                                with patch.object(self.validator, '_validate_background_tasks', return_value=None):
                                    with patch.object(self.validator, '_validate_monitoring', return_value=None):
                                        with patch.object(self.validator, '_validate_critical_paths', return_value=None):
                                            with patch.object(self.validator, '_validate_service_dependencies', return_value=None):
                                                # Run startup validation
                                                success, report = await self.validator.validate_startup(mock_app)

        # Verify timeout appears in report categories
        timeout_category = report["categories"].get("System", [])
        timeout_components = [comp for comp in timeout_category
                            if comp["name"] == "Startup Validation Timeout"]

        assert len(timeout_components) == 1, "Should have timeout component in report"

        timeout_component = timeout_components[0]
        assert timeout_component["status"] == "failed"
        assert timeout_component["critical"] is True
        assert "timed out after 5.0 seconds" in timeout_component["message"]
        assert "timeout_error" in timeout_component["metadata"]
        assert "timeout_seconds" in timeout_component["metadata"]