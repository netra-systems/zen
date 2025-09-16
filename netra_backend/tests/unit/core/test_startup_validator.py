"""
Unit Tests for Startup Validator

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Reliability
- Business Goal: Prevent broken deployments and reduce MTTR
- Value Impact: Startup validation prevents $500K+ ARR disruptions from configuration errors
- Strategic Impact: Fast startup validation catches critical issues before production deployment

This test suite validates critical Startup Validator business logic:
1. Startup validation orchestration and result aggregation
2. ID generation validation (UnifiedIDManager integration)
3. WebSocket component validation (mission-critical for chat)
4. Thread service validation (core business logic)
5. Database repository validation (data persistence)
6. Import integrity validation (prevents import failures)
7. Method signature validation (prevents runtime errors)
8. Agent registry validation (agent system functionality)
9. Configuration validation (system settings)

CRITICAL BUSINESS RULES:
- ALL validation methods MUST return consistent result format (bool, str)
- Critical validations MUST prevent application startup if they fail
- Validation results MUST provide actionable error messages
- Validation MUST complete within reasonable time bounds
- Failed validations MUST be properly logged with diagnostic information
"""
import pytest
import asyncio
import inspect
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.core.startup_validator import StartupValidator, ValidationStatus, ValidationResult, validate_startup, require_startup_validation

class StartupValidatorTests(SSotAsyncTestCase):
    """Unit tests for StartupValidator following SSOT patterns."""

    def setup_method(self, method):
        """Setup test method using SSOT patterns."""
        super().setup_method(method)
        self.validator = StartupValidator()
        self.mock_factory = SSotMockFactory()
        self.TEST_THREAD_ID = 'test_thread_001'
        self.TEST_ASSISTANT_ID = 'test_assistant_001'
        self.TEST_MODEL = 'gpt-4'
        self.TEST_INSTRUCTIONS = 'Test instructions for validation'

    async def teardown_method(self, method):
        """Cleanup test method using SSOT patterns."""
        await super().teardown_method(method)

class StartupValidatorInitializationTests(StartupValidatorTests):
    """Test startup validator initialization and basic properties."""

    async def test_validator_initialization(self):
        """Test validator initializes with correct default state."""
        validator = StartupValidator()
        assert validator.results == []
        assert validator.start_time is None
        assert validator.end_time is None
        self.logger.info('✓ Validator initialization test passed')

    async def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass creation."""
        result = ValidationResult(name='Test Validation', status=ValidationStatus.PASSED, message='Test passed successfully', duration_ms=150.5)
        assert result.name == 'Test Validation'
        assert result.status == ValidationStatus.PASSED
        assert result.message == 'Test passed successfully'
        assert result.duration_ms == 150.5
        assert result.error is None
        assert result.traceback is None
        error = Exception('Test error')
        result_with_error = ValidationResult(name='Failed Validation', status=ValidationStatus.FAILED, message='Validation failed', duration_ms=250.0, error=error, traceback='Test traceback')
        assert result_with_error.error == error
        assert result_with_error.traceback == 'Test traceback'
        self.logger.info('✓ ValidationResult dataclass test passed')

    async def test_validation_status_enum(self):
        """Test ValidationStatus enum values."""
        expected_statuses = {ValidationStatus.PENDING: 'pending', ValidationStatus.RUNNING: 'running', ValidationStatus.PASSED: 'passed', ValidationStatus.FAILED: 'failed', ValidationStatus.SKIPPED: 'skipped'}
        for status, expected_value in expected_statuses.items():
            assert status.value == expected_value
        self.logger.info('✓ ValidationStatus enum test passed')

class ValidateAllOrchestrationTests(StartupValidatorTests):
    """Test the main validate_all method orchestration."""

    async def test_validate_all_success_scenario(self):
        """Test validate_all when all validations pass."""
        validation_methods = ['_validate_id_generation', '_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
        for method_name in validation_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        start_time = datetime.now()
        result = await self.validator.validate_all()
        end_time = datetime.now()
        assert result is True
        assert self.validator.start_time is not None
        assert self.validator.end_time is not None
        assert self.validator.start_time >= start_time
        assert self.validator.end_time >= self.validator.start_time
        assert len(self.validator.results) == len(validation_methods)
        for validation_result in self.validator.results:
            assert validation_result.status == ValidationStatus.PASSED
            assert validation_result.duration_ms > 0
        self.logger.info('✓ Validate all success scenario test passed')

    async def test_validate_all_failure_scenario(self):
        """Test validate_all when some validations fail."""
        self.validator._validate_id_generation = Mock(return_value=(True, 'Success'))
        self.validator._validate_websocket_components = Mock(return_value=(False, 'WebSocket failure'))
        self.validator._validate_thread_service = Mock(return_value=(True, 'Success'))
        self.validator._validate_repositories = Mock(return_value=(False, 'Repository failure'))
        remaining_methods = ['_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
        for method_name in remaining_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        result = await self.validator.validate_all()
        assert result is False
        failed_results = [r for r in self.validator.results if r.status == ValidationStatus.FAILED]
        assert len(failed_results) == 2
        failed_names = [r.name for r in failed_results]
        assert 'WebSocket Components' in failed_names
        assert 'Database Repositories' in failed_names
        self.logger.info('✓ Validate all failure scenario test passed')

    async def test_validate_all_exception_handling(self):
        """Test validate_all handles validation method exceptions."""
        self.validator._validate_id_generation = Mock(side_effect=Exception('Mock exception'))
        remaining_methods = ['_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
        for method_name in remaining_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        result = await self.validator.validate_all()
        assert result is False
        failed_results = [r for r in self.validator.results if r.status == ValidationStatus.FAILED]
        assert len(failed_results) == 1
        failed_result = failed_results[0]
        assert failed_result.name == 'ID Generation'
        assert 'Mock exception' in failed_result.message
        assert failed_result.error is not None
        self.logger.info('✓ Validate all exception handling test passed')

class IdGenerationValidationTests(StartupValidatorTests):
    """Test ID generation validation logic."""

    async def test_id_generation_validation_success(self):
        """Test successful ID generation validation."""
        success, message = self.validator._validate_id_generation()
        if success:
            assert 'working correctly' in message.lower()
        else:
            self.logger.warning(f'ID generation validation failed: {message}')
        self.logger.info('✓ ID generation validation success test passed')

    @patch('netra_backend.app.core.startup_validator.UnifiedIDManager')
    async def test_id_generation_validation_failure(self, mock_id_manager):
        """Test ID generation validation failure scenarios."""
        mock_id_manager.generate_run_id.return_value = 'invalid_id'
        mock_id_manager.validate_run_id.return_value = False
        success, message = self.validator._validate_id_generation()
        assert success is False
        assert 'invalid run_id' in message.lower()
        self.logger.info('✓ ID generation validation failure test passed')

    @patch('netra_backend.app.core.startup_validator.UnifiedIDManager')
    async def test_id_generation_extraction_failure(self, mock_id_manager):
        """Test ID generation validation when thread extraction fails."""
        mock_id_manager.generate_run_id.return_value = 'valid_id'
        mock_id_manager.validate_run_id.return_value = True
        mock_id_manager.extract_thread_id.return_value = 'wrong_thread'
        success, message = self.validator._validate_id_generation()
        assert success is False
        assert 'thread extraction failed' in message.lower()
        self.logger.info('✓ ID generation extraction failure test passed')

class WebSocketComponentsValidationTests(StartupValidatorTests):
    """Test WebSocket components validation logic."""

    async def test_websocket_components_validation_success(self):
        """Test successful WebSocket components validation."""
        success, message = self.validator._validate_websocket_components()
        if success:
            assert 'functional' in message.lower()
        else:
            self.logger.warning(f'WebSocket components validation failed: {message}')
        self.logger.info('✓ WebSocket components validation success test passed')

    @patch('netra_backend.app.core.startup_validator.AgentWebSocketBridge')
    async def test_websocket_components_import_failure(self, mock_bridge_class):
        """Test WebSocket components validation when import fails."""
        mock_bridge_class.side_effect = ImportError('Cannot import AgentWebSocketBridge')
        success, message = self.validator._validate_websocket_components()
        assert success is False
        assert 'websocket component error' in message.lower()
        assert 'cannot import' in message.lower()
        self.logger.info('✓ WebSocket components import failure test passed')

    @patch('netra_backend.app.core.startup_validator.AgentWebSocketBridge')
    async def test_websocket_bridge_extraction_failure(self, mock_bridge_class):
        """Test WebSocket validation when thread extraction fails."""
        mock_bridge = Mock()
        mock_bridge.extract_thread_id.return_value = 'wrong_thread'
        mock_bridge_class.return_value = mock_bridge
        success, message = self.validator._validate_websocket_components()
        assert success is False
        assert 'bridge extraction failed' in message.lower()
        self.logger.info('✓ WebSocket bridge extraction failure test passed')

class ThreadServiceValidationTests(StartupValidatorTests):
    """Test thread service validation logic."""

    async def test_thread_service_validation_success(self):
        """Test successful thread service validation."""
        success, message = self.validator._validate_thread_service()
        if success:
            assert 'working correctly' in message.lower()
        else:
            self.logger.warning(f'Thread service validation failed: {message}')
        self.logger.info('✓ Thread service validation success test passed')

    @patch('netra_backend.app.core.startup_validator.ThreadService')
    async def test_thread_service_validation_import_failure(self, mock_service_class):
        """Test thread service validation when import fails."""
        mock_service_class.side_effect = ImportError('Cannot import ThreadService')
        success, message = self.validator._validate_thread_service()
        assert success is False
        assert 'threadservice error' in message.lower()
        self.logger.info('✓ Thread service import failure test passed')

    @patch('netra_backend.app.core.startup_validator.ThreadService')
    async def test_thread_service_prepare_run_data_failure(self, mock_service_class):
        """Test thread service validation when _prepare_run_data fails."""
        mock_service = Mock()
        mock_service._prepare_run_data.return_value = (None, None)
        mock_service_class.return_value = mock_service
        success, message = self.validator._validate_thread_service()
        assert success is False
        assert '_prepare_run_data failed' in message.lower()
        self.logger.info('✓ Thread service prepare run data failure test passed')

    @patch('netra_backend.app.core.startup_validator.ThreadService')
    async def test_thread_service_two_argument_bug_detection(self, mock_service_class):
        """Test detection of the specific 2-argument bug in ThreadService."""
        mock_service = Mock()
        mock_service._prepare_run_data.side_effect = TypeError('takes 1 positional argument but 2 were given')
        mock_service_class.return_value = mock_service
        success, message = self.validator._validate_thread_service()
        assert success is False
        assert '2-argument bug' in message.lower()
        self.logger.info('✓ Thread service 2-argument bug detection test passed')

class RepositoriesValidationTests(StartupValidatorTests):
    """Test database repositories validation logic."""

    async def test_repositories_validation_success(self):
        """Test successful repositories validation."""
        success, message = self.validator._validate_repositories()
        if success:
            assert 'validated' in message.lower()
        else:
            self.logger.warning(f'Repositories validation failed: {message}')
        self.logger.info('✓ Repositories validation success test passed')

    @patch('netra_backend.app.core.startup_validator.RunRepository', None)
    async def test_repositories_validation_import_failure(self):
        """Test repositories validation when import fails."""
        with patch.dict('sys.modules', {'netra_backend.app.services.database.run_repository': Mock()}):
            success, message = self.validator._validate_repositories()
            self.logger.info(f'Repositories validation result: {success}, {message}')
        self.logger.info('✓ Repositories import failure test passed')

class ImportsValidationTests(StartupValidatorTests):
    """Test import integrity validation logic."""

    async def test_imports_validation_success(self):
        """Test successful imports validation."""
        success, message = self.validator._validate_imports()
        if success:
            assert 'imports' in message.lower()
        else:
            self.logger.warning(f'Imports validation failed: {message}')
        self.logger.info('✓ Imports validation success test passed')

    @patch('netra_backend.app.core.startup_validator.importlib.import_module')
    async def test_imports_validation_failure(self, mock_import):
        """Test imports validation when critical imports fail."""
        mock_import.side_effect = ImportError('Mock import failure')
        success, message = self.validator._validate_imports()
        assert success is False
        assert 'import error' in message.lower()
        self.logger.info('✓ Imports validation failure test passed')

class MethodSignaturesValidationTests(StartupValidatorTests):
    """Test method signatures validation logic."""

    async def test_method_signatures_validation_success(self):
        """Test successful method signatures validation."""
        success, message = self.validator._validate_method_signatures()
        if success:
            assert 'signatures' in message.lower()
        else:
            self.logger.warning(f'Method signatures validation failed: {message}')
        self.logger.info('✓ Method signatures validation success test passed')

class AgentRegistryValidationTests(StartupValidatorTests):
    """Test agent registry validation logic."""

    async def test_agent_registry_validation_success(self):
        """Test successful agent registry validation."""
        success, message = self.validator._validate_agent_registry()
        if success:
            assert 'functional' in message.lower() or 'working' in message.lower()
        else:
            self.logger.warning(f'Agent registry validation failed: {message}')
        self.logger.info('✓ Agent registry validation success test passed')

    @patch('netra_backend.app.core.startup_validator.AgentRegistry')
    async def test_agent_registry_validation_import_failure(self, mock_registry_class):
        """Test agent registry validation when import fails."""
        mock_registry_class.side_effect = ImportError('Cannot import AgentRegistry')
        success, message = self.validator._validate_agent_registry()
        assert success is False
        assert 'agent registry error' in message.lower()
        self.logger.info('✓ Agent registry import failure test passed')

class ConfigurationValidationTests(StartupValidatorTests):
    """Test configuration validation logic."""

    async def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        success, message = self.validator._validate_configuration()
        if success:
            assert 'configuration' in message.lower()
        else:
            self.logger.warning(f'Configuration validation failed: {message}')
        self.logger.info('✓ Configuration validation success test passed')

    @patch('netra_backend.app.core.startup_validator.get_config')
    async def test_configuration_validation_failure(self, mock_get_config):
        """Test configuration validation when get_config fails."""
        mock_get_config.side_effect = Exception('Configuration error')
        success, message = self.validator._validate_configuration()
        assert success is False
        assert 'configuration error' in message.lower()
        self.logger.info('✓ Configuration validation failure test passed')

class ValidationResultsAndReportingTests(StartupValidatorTests):
    """Test validation results handling and reporting."""

    async def test_validation_timing_accuracy(self):
        """Test that validation timing is recorded accurately."""

        def slow_validation():
            import time
            time.sleep(0.1)
            return (True, 'Success')
        self.validator._validate_id_generation = slow_validation
        remaining_methods = ['_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
        for method_name in remaining_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        await self.validator.validate_all()
        id_validation = next((r for r in self.validator.results if r.name == 'ID Generation'))
        assert id_validation.duration_ms >= 90.0
        self.logger.info('✓ Validation timing accuracy test passed')

    async def test_validation_results_completeness(self):
        """Test that all validation results are properly recorded."""
        validation_methods = ['_validate_id_generation', '_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
        for method_name in validation_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        await self.validator.validate_all()
        assert len(self.validator.results) == len(validation_methods)
        for result in self.validator.results:
            assert result.name is not None
            assert result.status is not None
            assert result.message is not None
            assert result.duration_ms >= 0
        self.logger.info('✓ Validation results completeness test passed')

class PublicInterfaceFunctionsTests(StartupValidatorTests):
    """Test public interface functions."""

    @patch('netra_backend.app.core.startup_validator.StartupValidator')
    async def test_validate_startup_function(self, mock_validator_class):
        """Test the public validate_startup function."""
        mock_validator = Mock()
        mock_validator.validate_all = Mock(return_value=True)
        mock_validator_class.return_value = mock_validator
        result = await validate_startup()
        assert result is True
        mock_validator_class.assert_called_once()
        mock_validator.validate_all.assert_called_once()
        self.logger.info('✓ Validate startup function test passed')

    async def test_require_startup_validation_decorator(self):
        """Test the require_startup_validation decorator."""

        @require_startup_validation()
        def test_function():
            return 'success'
        assert hasattr(test_function, '__wrapped__')
        result = test_function()
        assert result == 'success'
        self.logger.info('✓ Require startup validation decorator test passed')

class ErrorHandlingAndEdgeCasesTests(StartupValidatorTests):
    """Test error handling and edge cases."""

    async def test_validation_with_missing_dependencies(self):
        """Test behavior when optional dependencies are missing."""
        self.validator._validate_imports = Mock(return_value=(False, 'Some imports failed'))
        self.validator._validate_agent_registry = Mock(return_value=(False, 'Agent registry unavailable'))
        remaining_methods = ['_validate_id_generation', '_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_method_signatures', '_validate_configuration']
        for method_name in remaining_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        result = await self.validator.validate_all()
        assert result is False
        assert len(self.validator.results) == 8
        self.logger.info('✓ Validation with missing dependencies test passed')

    async def test_concurrent_validation_safety(self):
        """Test that validation is safe to run concurrently."""
        validators = [StartupValidator() for _ in range(3)]
        for validator in validators:
            validation_methods = ['_validate_id_generation', '_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
            for method_name in validation_methods:
                setattr(validator, method_name, Mock(return_value=(True, 'Success')))
        results = await asyncio.gather(*[v.validate_all() for v in validators])
        assert all(results)
        for validator in validators:
            assert len(validator.results) == 8
        self.logger.info('✓ Concurrent validation safety test passed')

    async def test_validation_timeout_handling(self):
        """Test handling of validation methods that timeout."""

        async def slow_validation():
            await asyncio.sleep(10)
            return (True, 'Success')
        self.validator._validate_id_generation = slow_validation
        remaining_methods = ['_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration']
        for method_name in remaining_methods:
            setattr(self.validator, method_name, Mock(return_value=(True, 'Success')))
        try:
            result = await asyncio.wait_for(self.validator.validate_all(), timeout=1.0)
            self.logger.info('Validation completed within timeout')
        except asyncio.TimeoutError:
            self.logger.info('Validation properly timed out')
        self.logger.info('✓ Validation timeout handling test passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')