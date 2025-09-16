"""
Unit tests for LLM manager initialization failures in startup validation.

These tests reproduce the LLM manager initialization failures from Issue #899:
- LLM manager not initialized (None value)
- LLM service configuration errors
- Service dependency validation failures

Business Value: Platform/Internal - AI Service Reliability
Protects the $500K+ ARR Golden Path by ensuring LLM services are properly
initialized for AI agent functionality.

Test Categories:
- LLM manager initialization validation
- Service dependency checks
- Error handling for missing services
- Configuration validation for AI services
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Dict, Any

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import components under test
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentValidation,
    ComponentStatus,
    EnvironmentType
)
from netra_backend.app.core.service_dependencies import ServiceType


class LLMManagerInitializationUnitTests(SSotAsyncTestCase):
    """Unit tests for LLM manager initialization validation during startup."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance with test environment
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)

        # Clear any existing validations
        self.validator.validations = []

    async def test_llm_manager_not_initialized_critical_failure(self):
        """
        Test Issue #899 Failure 1: LLM Manager not initialized (None value)

        CRITICAL FAILURE REPRODUCTION:
        Expected behavior: When llm_manager is None or missing, should record
        CRITICAL failure as LLM services are required for AI agent functionality.
        """
        # Mock app state with missing/None LLM manager
        mock_app = MagicMock()
        mock_app.state.llm_manager = None

        # Add other required services to focus test on LLM manager
        mock_app.state.key_manager = MagicMock()
        mock_app.state.security_service = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.thread_service = MagicMock()
        mock_app.state.agent_service = MagicMock()

        # Run service validation
        await self.validator._validate_services(mock_app)

        # Verify LLM manager critical failure was recorded
        llm_validations = [v for v in self.validator.validations
                         if v.name == "LLM Manager"]

        assert len(llm_validations) == 1, "Should have recorded LLM manager validation"

        validation = llm_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Missing LLM manager should be CRITICAL"
        assert validation.is_critical is True, "LLM manager is critical for AI functionality"
        assert validation.actual_count == 0, "None LLM manager means 0 count"
        assert validation.expected_min == 1, "Should expect at least 1 LLM manager"
        assert "LLM Manager is None" in validation.message

    async def test_llm_manager_missing_from_app_state(self):
        """
        Test Issue #899 Failure 2: LLM Manager not found in app.state

        CRITICAL FAILURE REPRODUCTION:
        When app.state doesn't have llm_manager attribute at all,
        should record CRITICAL failure with appropriate message.
        """
        # Mock app state without llm_manager attribute
        mock_app = MagicMock()

        # Remove llm_manager attribute entirely
        if hasattr(mock_app.state, 'llm_manager'):
            delattr(mock_app.state, 'llm_manager')

        # Add other services
        mock_app.state.key_manager = MagicMock()
        mock_app.state.security_service = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.thread_service = MagicMock()
        mock_app.state.agent_service = MagicMock()

        # Run service validation
        await self.validator._validate_services(mock_app)

        # Verify LLM manager not found failure was recorded
        llm_validations = [v for v in self.validator.validations
                         if v.name == "LLM Manager"]

        assert len(llm_validations) == 1, "Should have recorded LLM manager validation"

        validation = llm_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Missing LLM manager should be CRITICAL"
        assert validation.is_critical is True, "LLM manager is critical for AI functionality"
        assert validation.actual_count == 0, "Missing manager means 0 count"
        assert "LLM Manager not found in app.state" in validation.message

    async def test_llm_manager_initialization_success(self):
        """
        Test successful LLM manager initialization validation.

        POSITIVE TEST CASE:
        When LLM manager is properly initialized, should record successful validation.
        """
        # Mock app state with initialized LLM manager
        mock_app = MagicMock()
        mock_llm_manager = MagicMock()
        mock_llm_manager.is_initialized = True
        mock_app.state.llm_manager = mock_llm_manager

        # Add other services
        mock_app.state.key_manager = MagicMock()
        mock_app.state.security_service = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.thread_service = MagicMock()
        mock_app.state.agent_service = MagicMock()

        # Run service validation
        await self.validator._validate_services(mock_app)

        # Verify successful LLM manager validation
        llm_validations = [v for v in self.validator.validations
                         if v.name == "LLM Manager"]

        assert len(llm_validations) == 1, "Should have recorded LLM manager validation"

        validation = llm_validations[0]
        assert validation.status == ComponentStatus.HEALTHY, "Initialized LLM manager should be HEALTHY"
        assert validation.is_critical is True, "LLM manager remains critical even when working"
        assert validation.actual_count == 1, "Initialized manager means 1 count"
        assert "LLM Manager initialized" in validation.message

    async def test_service_dependency_llm_service_validation(self):
        """
        Test LLM service validation through service dependency checker.

        INTEGRATION TEST:
        LLM services should be validated through the service dependency system
        to ensure proper Golden Path functionality.
        """
        # Mock app state with LLM manager
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()

        # Mock service dependency checker to return LLM service failure
        mock_dependency_result = MagicMock()
        mock_dependency_result.overall_success = False
        mock_dependency_result.services_healthy = 5
        mock_dependency_result.services_failed = 1
        mock_dependency_result.execution_duration_ms = 50.0
        mock_dependency_result.critical_failures = ["LLM service connection timeout"]

        with patch.object(self.validator, 'service_dependency_checker') as mock_checker:
            mock_checker.validate_service_dependencies.return_value = mock_dependency_result

            # Run service dependency validation
            await self.validator._validate_service_dependencies(mock_app)

        # Verify service dependency failure was recorded
        service_dep_validations = [v for v in self.validator.validations
                                 if v.name == "Service Dependencies"]

        assert len(service_dep_validations) == 1, "Should have recorded service dependency validation"

        validation = service_dep_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Service dependency failure should be CRITICAL"
        assert validation.is_critical is True, "Service dependencies are critical for business"
        assert "Service dependency validation FAILED" in validation.message
        assert "1 services failed" in validation.message
        assert validation.metadata["services_failed"] == 1
        assert "LLM service connection timeout" in validation.metadata["critical_failures"]

    async def test_llm_service_type_detection(self):
        """
        Test that LLM service type is correctly detected for validation.

        SERVICE DETECTION TEST:
        When llm_manager exists, ServiceType.LLM_SERVICE should be included
        in the services to check.
        """
        # Mock app state with LLM manager
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()

        # Mock successful dependency result
        mock_dependency_result = MagicMock()
        mock_dependency_result.overall_success = True
        mock_dependency_result.services_healthy = 1
        mock_dependency_result.services_failed = 0
        mock_dependency_result.execution_duration_ms = 25.0
        mock_dependency_result.critical_failures = []
        mock_dependency_result.phase_results = {}

        with patch.object(self.validator, 'service_dependency_checker') as mock_checker:
            mock_checker.validate_service_dependencies.return_value = mock_dependency_result

            # Run service dependency validation
            await self.validator._validate_service_dependencies(mock_app)

            # Verify LLM_SERVICE was included in services to check
            call_args = mock_checker.validate_service_dependencies.call_args
            services_to_check = call_args[1]['services_to_check']

            assert ServiceType.LLM_SERVICE in services_to_check, "Should include LLM_SERVICE when llm_manager exists"

    async def test_multiple_critical_services_failure_including_llm(self):
        """
        Test handling of multiple critical service failures including LLM.

        COMPREHENSIVE FAILURE TEST:
        When multiple critical services fail including LLM, should record
        all failures with appropriate criticality.
        """
        # Mock app state with multiple missing critical services
        mock_app = MagicMock()
        mock_app.state.llm_manager = None          # Missing LLM
        mock_app.state.key_manager = None          # Missing Key Manager
        mock_app.state.security_service = MagicMock()  # Working
        mock_app.state.redis_manager = MagicMock()     # Working
        mock_app.state.thread_service = None       # Missing Thread Service
        mock_app.state.agent_service = MagicMock()     # Working

        # Run service validation
        await self.validator._validate_services(mock_app)

        # Verify all critical failures were recorded
        critical_failures = [v for v in self.validator.validations
                           if v.is_critical and v.status == ComponentStatus.CRITICAL]

        # Should have at least LLM Manager, Key Manager, Thread Service failures
        critical_service_names = [v.name for v in critical_failures]

        assert "LLM Manager" in critical_service_names, "Should record LLM Manager failure"
        assert "Key Manager" in critical_service_names, "Should record Key Manager failure"
        assert "Thread Service" in critical_service_names, "Should record Thread Service failure"

        # Verify LLM Manager specifically
        llm_failures = [v for v in critical_failures if v.name == "LLM Manager"]
        assert len(llm_failures) == 1, "Should have exactly one LLM Manager failure"
        assert "LLM Manager is None" in llm_failures[0].message

    async def test_service_validation_exception_handling(self):
        """
        Test handling of exceptions during service validation.

        ROBUSTNESS TEST:
        Exceptions during service validation should be caught and recorded
        as failed validations without crashing startup.
        """
        # Mock app state that causes exception during access
        mock_app = MagicMock()

        # Mock property that raises exception when accessed
        type(mock_app.state).llm_manager = PropertyMock(side_effect=RuntimeError("Service access error"))

        # Run service validation
        await self.validator._validate_services(mock_app)

        # Verify exception was handled as failed validation
        llm_validations = [v for v in self.validator.validations
                         if "LLM" in v.name]

        # Should have recorded a failure due to the exception
        assert len(llm_validations) >= 1, "Should have recorded validation failure"

        # Find the validation that caught the exception
        error_validations = [v for v in llm_validations
                           if v.status == ComponentStatus.FAILED]

        if error_validations:
            validation = error_validations[0]
            assert "Service access error" in validation.message

    async def test_llm_manager_with_factory_patterns_validation(self):
        """
        Test LLM manager validation in context of factory patterns.

        FACTORY PATTERN TEST:
        LLM manager should work correctly with other factory-based services
        like ExecutionEngineFactory and WebSocketBridgeFactory.
        """
        # Mock app state with LLM manager and factory services
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()

        # Add factory pattern services
        mock_app.state.execution_engine_factory = MagicMock()
        mock_app.state.websocket_bridge_factory = MagicMock()
        mock_app.state.websocket_connection_pool = MagicMock()

        # Add other critical services
        mock_app.state.key_manager = MagicMock()
        mock_app.state.security_service = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.thread_service = MagicMock()
        mock_app.state.agent_service = MagicMock()

        # Run service validation
        await self.validator._validate_services(mock_app)

        # Verify LLM manager validation succeeded
        llm_validations = [v for v in self.validator.validations
                         if v.name == "LLM Manager"]

        assert len(llm_validations) == 1, "Should have validated LLM manager"
        assert llm_validations[0].status == ComponentStatus.HEALTHY

        # Verify factory services were also validated
        factory_validations = [v for v in self.validator.validations
                             if v.category == "Factories"]

        factory_names = [v.name for v in factory_validations]
        assert "ExecutionEngineFactory" in factory_names
        assert "WebSocketBridgeFactory" in factory_names
        assert "WebSocketConnectionPool" in factory_names

        # All should be healthy with proper LLM manager support
        healthy_factories = [v for v in factory_validations
                           if v.status == ComponentStatus.HEALTHY]
        assert len(healthy_factories) == len(factory_validations), "All factories should be healthy with LLM manager"


class LLMManagerServiceIntegrationUnitTests(SSotAsyncTestCase):
    """Unit tests for LLM manager integration with service dependencies."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        self.validator.validations = []

    async def test_llm_service_golden_path_validation(self):
        """
        Test LLM service validation in Golden Path context.

        GOLDEN PATH TEST:
        LLM services should be validated as part of Golden Path to ensure
        chat functionality works for the $500K+ ARR business value.
        """
        # Mock app state with LLM manager
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()

        # Mock successful Golden Path validation including LLM
        mock_dependency_result = MagicMock()
        mock_dependency_result.overall_success = True
        mock_dependency_result.services_healthy = 6
        mock_dependency_result.services_failed = 0
        mock_dependency_result.execution_duration_ms = 100.0
        mock_dependency_result.critical_failures = []
        mock_dependency_result.phase_results = {
            "golden_path": {"status": "success", "llm_service": "validated"}
        }

        with patch.object(self.validator, 'service_dependency_checker') as mock_checker:
            mock_checker.validate_service_dependencies.return_value = mock_dependency_result

            # Run service dependency validation with Golden Path
            await self.validator._validate_service_dependencies(mock_app)

            # Verify Golden Path was included
            call_args = mock_checker.validate_service_dependencies.call_args
            assert call_args[1]['include_golden_path'] is True, "Should include Golden Path validation"

        # Verify successful validation
        service_dep_validations = [v for v in self.validator.validations
                                 if v.name == "Service Dependencies"]

        assert len(service_dep_validations) == 1
        validation = service_dep_validations[0]
        assert validation.status == ComponentStatus.HEALTHY
        assert validation.metadata["golden_path_validated"] is True
        assert "6/6 services healthy" in validation.message

    async def test_no_services_found_for_llm_validation(self):
        """
        Test handling when no services are found for validation.

        EDGE CASE TEST:
        When app.state has no services at all, should record appropriate warning.
        """
        # Mock app state with no services
        mock_app = MagicMock()
        # Remove all service attributes
        for attr in ['llm_manager', 'db_session_factory', 'redis_manager',
                     'key_manager', 'security_service', 'agent_supervisor',
                     'websocket_manager', 'agent_websocket_bridge']:
            if hasattr(mock_app.state, attr):
                delattr(mock_app.state, attr)

        # Run service dependency validation
        await self.validator._validate_service_dependencies(mock_app)

        # Verify no services warning was recorded
        service_dep_validations = [v for v in self.validator.validations
                                 if v.name == "Service Dependencies"]

        assert len(service_dep_validations) == 1
        validation = service_dep_validations[0]
        assert validation.status == ComponentStatus.WARNING
        assert validation.is_critical is False
        assert "No services found for dependency validation" in validation.message

    async def test_service_dependency_checker_fallback_mode(self):
        """
        Test LLM service validation with fallback service dependency checker.

        FALLBACK TEST:
        When ServiceDependencyChecker initialization fails, should use fallback
        but still validate LLM services with appropriate warnings.
        """
        # Mock app state with LLM manager
        mock_app = MagicMock()
        mock_app.state.llm_manager = MagicMock()

        # Mock validator with fallback service dependency checker
        fallback_result = MagicMock()
        fallback_result.overall_success = True
        fallback_result.services_healthy = 6
        fallback_result.services_failed = 0
        fallback_result.execution_duration_ms = 1.0
        fallback_result.critical_failures = ["ServiceDependencyChecker not fully initialized - using fallback mode"]
        fallback_result.service_results = []
        fallback_result.phase_results = {}

        with patch.object(self.validator, 'service_dependency_checker') as mock_checker:
            mock_checker.validate_service_dependencies.return_value = fallback_result

            # Run service dependency validation
            await self.validator._validate_service_dependencies(mock_app)

        # Verify fallback mode was handled appropriately
        service_dep_validations = [v for v in self.validator.validations
                                 if v.name == "Service Dependencies"]

        assert len(service_dep_validations) == 1
        validation = service_dep_validations[0]
        # Should still be healthy but with critical failures indicating fallback mode
        assert validation.status == ComponentStatus.HEALTHY
        assert "ServiceDependencyChecker not fully initialized" in validation.metadata["critical_failures"][0]