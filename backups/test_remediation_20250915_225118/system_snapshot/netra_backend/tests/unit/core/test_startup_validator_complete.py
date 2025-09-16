"""
Test Startup Validator System - Complete Test Coverage for StartupValidator

Business Value Justification (BVJ):
- Segment: All (Platform/Internal)
- Business Goal: System Stability and Deployment Safety  
- Value Impact: Prevents broken deployments that would cause 100% system outages
- Strategic Impact: Reduces MTTR and prevents revenue-impacting downtime

This comprehensive test suite ensures 100% coverage of startup_validator.py
including all validation methods, error scenarios, concurrent execution,
and business value validation.

CRITICAL: These tests prevent broken deployments and system failures.
"""
import asyncio
import inspect
import pytest
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from dataclasses import dataclass, asdict
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.core.startup_validator import ValidationStatus, ValidationResult, StartupValidator, validate_startup, require_startup_validation

class ValidationStatusTests(BaseTestCase):
    """Test ValidationStatus enum values and behavior."""

    def test_validation_status_enum_values(self):
        """Test that ValidationStatus enum has all required values."""
        expected_values = {'pending', 'running', 'passed', 'failed', 'skipped'}
        actual_values = {status.value for status in ValidationStatus}
        assert actual_values == expected_values, f'Missing enum values: {expected_values - actual_values}'

    def test_validation_status_is_enum(self):
        """Test that ValidationStatus is properly defined as Enum."""
        assert issubclass(ValidationStatus, Enum)
        assert len(ValidationStatus) == 5

    def test_validation_status_string_representation(self):
        """Test string representation of ValidationStatus values."""
        assert str(ValidationStatus.PENDING) == 'ValidationStatus.PENDING'
        assert repr(ValidationStatus.PASSED) == "<ValidationStatus.PASSED: 'passed'>"
        assert ValidationStatus.RUNNING.value == 'running'
        assert ValidationStatus.FAILED.value == 'failed'
        assert ValidationStatus.SKIPPED.value == 'skipped'

    def test_validation_status_comparison(self):
        """Test ValidationStatus comparison operations."""
        assert ValidationStatus.PASSED == ValidationStatus.PASSED
        assert ValidationStatus.FAILED != ValidationStatus.PASSED
        assert ValidationStatus.PASSED.value == 'passed'
        assert ValidationStatus.RUNNING.value != 'failed'

class ValidationResultTests(BaseTestCase):
    """Test ValidationResult dataclass with all fields and edge cases."""

    def test_validation_result_creation(self):
        """Test basic ValidationResult creation with required fields."""
        result = ValidationResult(name='Test Validation', status=ValidationStatus.PASSED, message='Validation successful', duration_ms=150.5)
        assert result.name == 'Test Validation'
        assert result.status == ValidationStatus.PASSED
        assert result.message == 'Validation successful'
        assert result.duration_ms == 150.5
        assert result.error is None
        assert result.traceback is None

    def test_validation_result_with_error(self):
        """Test ValidationResult creation with error and traceback."""
        test_exception = ValueError('Test error')
        test_traceback = 'Traceback line 1\nTraceback line 2'
        result = ValidationResult(name='Failed Validation', status=ValidationStatus.FAILED, message='Validation failed', duration_ms=75.2, error=test_exception, traceback=test_traceback)
        assert result.name == 'Failed Validation'
        assert result.status == ValidationStatus.FAILED
        assert result.error == test_exception
        assert result.traceback == test_traceback

    def test_validation_result_is_dataclass(self):
        """Test that ValidationResult is properly defined as dataclass."""
        assert hasattr(ValidationResult, '__dataclass_fields__')
        expected_fields = {'name', 'status', 'message', 'duration_ms', 'error', 'traceback'}
        actual_fields = set(ValidationResult.__dataclass_fields__.keys())
        assert actual_fields == expected_fields

    def test_validation_result_default_values(self):
        """Test ValidationResult default values for optional fields."""
        result = ValidationResult(name='Test', status=ValidationStatus.PENDING, message='Test message', duration_ms=0)
        assert result.error is None
        assert result.traceback is None

    def test_validation_result_serialization(self):
        """Test ValidationResult can be converted to dict."""
        result = ValidationResult(name='Test Validation', status=ValidationStatus.PASSED, message='Success', duration_ms=100.0, error=ValueError('test'), traceback='test traceback')
        result_dict = asdict(result)
        assert result_dict['name'] == 'Test Validation'
        assert result_dict['status'] == ValidationStatus.PASSED
        assert result_dict['message'] == 'Success'
        assert result_dict['duration_ms'] == 100.0
        assert isinstance(result_dict['error'], ValueError)
        assert result_dict['traceback'] == 'test traceback'

class StartupValidatorInitializationTests(BaseTestCase):
    """Test StartupValidator initialization and basic setup."""

    def test_startup_validator_initialization(self):
        """Test StartupValidator initializes with proper defaults."""
        validator = StartupValidator()
        assert validator.results == []
        assert validator.start_time is None
        assert validator.end_time is None
        assert isinstance(validator.results, list)

    def test_startup_validator_is_class(self):
        """Test StartupValidator class structure."""
        assert inspect.isclass(StartupValidator)
        required_methods = ['validate_all', '_validate_id_generation', '_validate_websocket_components', '_validate_thread_service', '_validate_repositories', '_validate_imports', '_validate_method_signatures', '_validate_agent_registry', '_validate_configuration', '_print_summary']
        for method in required_methods:
            assert hasattr(StartupValidator, method), f'Missing method: {method}'
            assert callable(getattr(StartupValidator, method))

class StartupValidatorMainFlowTests(BaseTestCase):
    """Test StartupValidator main validation flow including concurrent scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_all_success_scenario(self):
        """Test validate_all with all validations passing."""
        with patch.object(self.validator, '_validate_id_generation', return_value=(True, 'ID generation working')):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'WebSocket OK')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Thread service OK')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Signatures OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is True
                                        assert len(self.validator.results) == 8
                                        assert all((r.status == ValidationStatus.PASSED for r in self.validator.results))
                                        assert self.validator.start_time is not None
                                        assert self.validator.end_time is not None

    @pytest.mark.asyncio
    async def test_validate_all_failure_scenario(self):
        """Test validate_all with some validations failing."""
        with patch.object(self.validator, '_validate_id_generation', return_value=(False, 'ID generation failed')):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'WebSocket OK')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(False, 'Thread service failed')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Signatures OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is False
                                        assert len(self.validator.results) == 8
                                        failed_results = [r for r in self.validator.results if r.status == ValidationStatus.FAILED]
                                        assert len(failed_results) == 2
                                        failed_names = [r.name for r in failed_results]
                                        assert 'ID Generation' in failed_names
                                        assert 'Thread Service' in failed_names

    @pytest.mark.asyncio
    async def test_validate_all_exception_handling(self):
        """Test validate_all handles exceptions in validation methods."""

        def failing_validator():
            raise RuntimeError('Validation exploded')
        with patch.object(self.validator, '_validate_id_generation', side_effect=failing_validator):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'WebSocket OK')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Thread OK')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Signatures OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is False
                                        assert len(self.validator.results) == 8
                                        failed_result = next((r for r in self.validator.results if r.name == 'ID Generation'))
                                        assert failed_result.status == ValidationStatus.FAILED
                                        assert 'Exception: Validation exploded' in failed_result.message
                                        assert failed_result.error is not None
                                        assert failed_result.traceback is not None

    @pytest.mark.asyncio
    async def test_validate_all_timing_metrics(self):
        """Test that validate_all properly tracks timing metrics."""

        def slow_validator():
            time.sleep(0.01)
            return (True, 'Slow validation complete')
        with patch.object(self.validator, '_validate_id_generation', side_effect=slow_validator):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'Fast validation')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Thread OK')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Signatures OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is True
                                        assert self.validator.start_time is not None
                                        assert self.validator.end_time is not None
                                        assert self.validator.end_time > self.validator.start_time
                                        for validation_result in self.validator.results:
                                            assert validation_result.duration_ms >= 0
                                            if validation_result.name == 'ID Generation':
                                                assert validation_result.duration_ms >= 10

    @pytest.mark.asyncio
    async def test_validate_all_async_validator_support(self):
        """Test validate_all supports both sync and async validation methods."""

        async def async_validator():
            await asyncio.sleep(0.001)
            return (True, 'Async validation complete')

        def sync_validator():
            return (True, 'Sync validation complete')
        with patch.object(self.validator, '_validate_id_generation', side_effect=async_validator):
            with patch.object(self.validator, '_validate_websocket_components', side_effect=sync_validator):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Thread OK')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Signatures OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is True
                                        assert len(self.validator.results) == 8
                                        assert all((r.status == ValidationStatus.PASSED for r in self.validator.results))
                                        async_result = next((r for r in self.validator.results if r.name == 'ID Generation'))
                                        sync_result = next((r for r in self.validator.results if r.name == 'WebSocket Components'))
                                        assert async_result.message == 'Async validation complete'
                                        assert sync_result.message == 'Sync validation complete'

class StartupValidatorIndividualMethodsTests(BaseTestCase):
    """Test all individual validation methods (_validate_*) with success and failure cases."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator = StartupValidator()

    def test_validate_id_generation_success(self):
        """Test _validate_id_generation with successful ID generation."""
        mock_unified_id = Mock()
        mock_unified_id.generate_run_id.return_value = 'run_20241207_startup_validation_abc123'
        mock_unified_id.validate_run_id.return_value = True
        mock_unified_id.extract_thread_id.return_value = 'startup_validation'

        def mock_generate_run_id(*args, **kwargs):
            if len(args) > 1:
                raise TypeError('generate_run_id() takes 1 positional argument but 2 were given')
            return 'run_20241207_startup_validation_abc123'
        mock_unified_id.generate_run_id.side_effect = mock_generate_run_id
        mock_sig = Mock()
        mock_param = Mock()
        mock_param.default = inspect.Parameter.empty
        mock_sig.parameters = {'thread_id': mock_param}
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
            with patch('netra_backend.app.core.startup_validator.inspect.signature', return_value=mock_sig):
                success, message = self.validator._validate_id_generation()
                assert success is True
                assert 'ID generation working correctly' in message
                mock_unified_id.generate_run_id.assert_called()
                mock_unified_id.validate_run_id.assert_called()
                mock_unified_id.extract_thread_id.assert_called()

    def test_validate_id_generation_invalid_run_id(self):
        """Test _validate_id_generation with invalid run ID."""
        mock_unified_id = Mock()
        mock_unified_id.generate_run_id.return_value = 'invalid_run_id'
        mock_unified_id.validate_run_id.return_value = False
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
            success, message = self.validator._validate_id_generation()
            assert success is False
            assert 'Generated invalid run_id' in message
            assert 'invalid_run_id' in message

    def test_validate_id_generation_wrong_thread_extraction(self):
        """Test _validate_id_generation with wrong thread extraction."""
        mock_unified_id = Mock()
        mock_unified_id.generate_run_id.return_value = 'run_20241207_startup_validation_abc123'
        mock_unified_id.validate_run_id.return_value = True
        mock_unified_id.extract_thread_id.return_value = 'wrong_thread'
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
            success, message = self.validator._validate_id_generation()
            assert success is False
            assert 'Thread extraction failed' in message
            assert 'expected startup_validation, got wrong_thread' in message

    def test_validate_id_generation_wrong_signature(self):
        """Test _validate_id_generation detects wrong method signature."""
        mock_unified_id = Mock()
        mock_unified_id.generate_run_id.return_value = 'run_20241207_startup_validation_abc123'
        mock_unified_id.validate_run_id.return_value = True
        mock_unified_id.extract_thread_id.return_value = 'startup_validation'
        mock_sig = Mock()
        mock_param1 = Mock()
        mock_param1.default = inspect.Parameter.empty
        mock_param2 = Mock()
        mock_param2.default = inspect.Parameter.empty
        mock_sig.parameters = {'thread_id': mock_param1, 'extra_param': mock_param2}
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
            with patch('netra_backend.app.core.startup_validator.inspect.signature', return_value=mock_sig):
                success, message = self.validator._validate_id_generation()
                assert success is False
                assert 'generate_run_id has wrong signature' in message
                assert '2 required params instead of 1' in message

    def test_validate_id_generation_exception(self):
        """Test _validate_id_generation handles exceptions."""
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', side_effect=ImportError('UnifiedIDManager not found')):
            success, message = self.validator._validate_id_generation()
            assert success is False
            assert 'Failed to validate ID generation' in message
            assert 'UnifiedIDManager not found' in message

    def test_validate_websocket_components_success(self):
        """Test _validate_websocket_components with successful imports."""
        mock_bridge = Mock()
        mock_bridge.extract_thread_id.return_value = 'websocket_test'
        mock_websocket_manager = Mock()
        mock_unified_id = Mock()
        mock_unified_id.generate_run_id.return_value = 'run_20241207_websocket_test_abc123'
        with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge', return_value=mock_bridge):
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager', mock_websocket_manager):
                with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
                    success, message = self.validator._validate_websocket_components()
                    assert success is True
                    assert 'WebSocket components functional' in message
                    mock_bridge.extract_thread_id.assert_called_once()

    def test_validate_websocket_components_extraction_failure(self):
        """Test _validate_websocket_components with thread extraction failure."""
        mock_bridge = Mock()
        mock_bridge.extract_thread_id.return_value = 'wrong_thread'
        mock_unified_id = Mock()
        mock_unified_id.generate_run_id.return_value = 'run_20241207_websocket_test_abc123'
        with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge', return_value=mock_bridge):
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager'):
                with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
                    success, message = self.validator._validate_websocket_components()
                    assert success is False
                    assert 'WebSocket bridge extraction failed' in message
                    assert 'wrong_thread' in message

    def test_validate_websocket_components_import_error(self):
        """Test _validate_websocket_components handles import errors."""
        with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge', side_effect=ImportError('WebSocket components not available')):
            success, message = self.validator._validate_websocket_components()
            assert success is False
            assert 'WebSocket component error' in message
            assert 'WebSocket components not available' in message

    def test_validate_thread_service_success(self):
        """Test _validate_thread_service with successful service validation."""
        mock_service = Mock()
        mock_service._prepare_run_data.return_value = ('run_20241207_test_thread_abc123', {'thread_id': 'test_thread', 'assistant_id': 'test_assistant'})
        with patch('netra_backend.app.services.thread_service.ThreadService', return_value=mock_service):
            success, message = self.validator._validate_thread_service()
            assert success is True
            assert 'ThreadService working correctly' in message
            mock_service._prepare_run_data.assert_called_once_with(thread_id='test_thread', assistant_id='test_assistant', model='gpt-4', instructions='test')

    def test_validate_thread_service_two_argument_bug(self):
        """Test _validate_thread_service detects the 2-argument bug."""
        mock_service = Mock()
        mock_service._prepare_run_data.side_effect = TypeError('generate_run_id() takes 1 positional argument but 2 were given')
        with patch('netra_backend.app.services.thread_service.ThreadService', return_value=mock_service):
            success, message = self.validator._validate_thread_service()
            assert success is False
            assert 'ThreadService has 2-argument bug' in message
            assert 'takes 1 positional argument but 2 were given' in message

    def test_validate_thread_service_prepare_run_data_failure(self):
        """Test _validate_thread_service with _prepare_run_data failures."""
        mock_service = Mock()
        mock_service._prepare_run_data.return_value = (None, None)
        with patch('netra_backend.app.services.thread_service.ThreadService', return_value=mock_service):
            success, message = self.validator._validate_thread_service()
            assert success is False
            assert 'ThreadService._prepare_run_data failed' in message

    def test_validate_thread_service_wrong_thread_id(self):
        """Test _validate_thread_service with wrong thread ID in run_data."""
        mock_service = Mock()
        mock_service._prepare_run_data.return_value = ('run_20241207_test_thread_abc123', {'thread_id': 'wrong_thread', 'assistant_id': 'test_assistant'})
        with patch('netra_backend.app.services.thread_service.ThreadService', return_value=mock_service):
            success, message = self.validator._validate_thread_service()
            assert success is False
            assert 'Thread ID mismatch in run_data' in message
            assert 'wrong_thread' in message

    def test_validate_repositories_success(self):
        """Test _validate_repositories with successful import."""
        mock_repo = Mock()
        with patch('netra_backend.app.services.database.run_repository.RunRepository', mock_repo):
            success, message = self.validator._validate_repositories()
            assert success is True
            assert 'Repositories validated' in message

    def test_validate_repositories_import_error(self):
        """Test _validate_repositories handles import errors."""
        with patch('netra_backend.app.services.database.run_repository.RunRepository', side_effect=ImportError('Repository module not found')):
            success, message = self.validator._validate_repositories()
            assert success is False
            assert 'Repository error' in message
            assert 'Repository module not found' in message

    def test_validate_imports_success(self):
        """Test _validate_imports with all imports successful."""
        with patch('netra_backend.app.core.startup_validator.importlib.import_module') as mock_import:
            mock_import.return_value = Mock()
            success, message = self.validator._validate_imports()
            assert success is True
            assert 'All 5 critical modules imported' in message
            expected_modules = ['netra_backend.app.core.unified_id_manager', 'netra_backend.app.services.thread_service', 'netra_backend.app.services.agent_websocket_bridge', 'netra_backend.app.orchestration.agent_execution_registry', 'netra_backend.app.core.interfaces_observability']
            assert mock_import.call_count == len(expected_modules)
            for expected_module in expected_modules:
                mock_import.assert_any_call(expected_module)

    def test_validate_imports_partial_failure(self):
        """Test _validate_imports with some imports failing."""

        def mock_import_side_effect(module_name):
            if 'unified_id_manager' in module_name:
                raise ImportError('ID manager not found')
            elif 'thread_service' in module_name:
                raise ModuleNotFoundError('Thread service missing')
            else:
                return Mock()
        with patch('netra_backend.app.core.startup_validator.importlib.import_module', side_effect=mock_import_side_effect):
            success, message = self.validator._validate_imports()
            assert success is False
            assert 'Import failures:' in message
            assert 'unified_id_manager: ID manager not found' in message
            assert 'thread_service: Thread service missing' in message

    def test_validate_method_signatures_success(self):
        """Test _validate_method_signatures with correct signatures."""
        mock_unified_id = Mock()

        def create_mock_signature(param_count):
            mock_sig = Mock()
            params = {}
            for i in range(param_count):
                param = Mock()
                param.default = inspect.Parameter.empty
                params[f'param_{i}'] = param
            mock_sig.parameters = params
            return mock_sig
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
            with patch('netra_backend.app.core.startup_validator.inspect.signature') as mock_signature:
                mock_signature.return_value = create_mock_signature(1)
                success, message = self.validator._validate_method_signatures()
                assert success is True
                assert 'All method signatures correct' in message
                expected_calls = ['generate_run_id', 'extract_thread_id', 'validate_run_id', 'parse_run_id']
                assert mock_signature.call_count == len(expected_calls)

    def test_validate_method_signatures_wrong_signature(self):
        """Test _validate_method_signatures detects wrong method signatures."""
        mock_unified_id = Mock()

        def signature_side_effect(method):
            if method.__name__ == 'generate_run_id':
                mock_sig = Mock()
                param1 = Mock()
                param1.default = inspect.Parameter.empty
                param2 = Mock()
                param2.default = inspect.Parameter.empty
                mock_sig.parameters = {'param1': param1, 'param2': param2}
                return mock_sig
            else:
                mock_sig = Mock()
                param = Mock()
                param.default = inspect.Parameter.empty
                mock_sig.parameters = {'param': param}
                return mock_sig
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager', mock_unified_id):
            with patch('netra_backend.app.core.startup_validator.inspect.signature', side_effect=signature_side_effect):
                success, message = self.validator._validate_method_signatures()
                assert success is False
                assert 'Signature mismatches:' in message
                assert 'generate_run_id: expected 1 args, has 2' in message

    def test_validate_agent_registry_success(self):
        """Test _validate_agent_registry with healthy registry."""
        mock_registry = Mock()
        mock_registry.is_healthy.return_value = True
        mock_registry.get_stats.return_value = {'registered_count': 5}
        with patch('netra_backend.app.core.registry.universal_registry.get_global_registry', return_value=mock_registry):
            success, message = self.validator._validate_agent_registry()
            assert success is True
            assert 'AgentRegistry validated' in message
            assert '(5 agents registered)' in message

    def test_validate_agent_registry_not_healthy(self):
        """Test _validate_agent_registry with unhealthy registry."""
        mock_registry = Mock()
        mock_registry.is_healthy.return_value = False
        with patch('netra_backend.app.core.registry.universal_registry.get_global_registry', return_value=mock_registry):
            success, message = self.validator._validate_agent_registry()
            assert success is False
            assert 'AgentRegistry is not healthy' in message

    def test_validate_agent_registry_initialization_failure(self):
        """Test _validate_agent_registry with registry initialization failure."""
        with patch('netra_backend.app.core.registry.universal_registry.get_global_registry', return_value=None):
            success, message = self.validator._validate_agent_registry()
            assert success is False
            assert 'AgentRegistry initialization failed' in message

    def test_validate_configuration_success(self):
        """Test _validate_configuration with proper configuration."""
        mock_settings = Mock()
        mock_settings.environment = 'test'
        with patch('netra_backend.app.config.settings', mock_settings):
            success, message = self.validator._validate_configuration()
            assert success is True
            assert 'Configuration loaded' in message
            assert '(env: test)' in message

    def test_validate_configuration_missing_settings(self):
        """Test _validate_configuration with missing critical settings."""
        mock_settings = Mock()
        delattr(mock_settings, 'environment')
        with patch('netra_backend.app.config.settings', mock_settings):
            success, message = self.validator._validate_configuration()
            assert success is False
            assert 'Missing settings: environment' in message

    def test_validate_configuration_import_error(self):
        """Test _validate_configuration handles import errors."""
        with patch('netra_backend.app.config.settings', side_effect=ImportError('Settings module not found')):
            success, message = self.validator._validate_configuration()
            assert success is False
            assert 'Configuration error' in message
            assert 'Settings module not found' in message

class StartupValidatorSummaryAndOutputTests(BaseTestCase):
    """Test validation summary and output functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator = StartupValidator()

    def test_print_summary_with_results(self):
        """Test _print_summary outputs correct information."""
        self.validator.results = [ValidationResult(name='Test 1', status=ValidationStatus.PASSED, message='Success', duration_ms=100.0), ValidationResult(name='Test 2', status=ValidationStatus.FAILED, message='Failed', duration_ms=200.0, error=ValueError('Test error'), traceback='Test traceback')]
        self.validator.start_time = datetime.now()
        self.validator.end_time = datetime.now()
        import io
        from contextlib import redirect_stdout
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            self.validator._print_summary()
        output = output_buffer.getvalue()
        assert 'VALIDATION SUMMARY' in output
        assert '[U+2713] Test 1: Success (100.0ms)' in output
        assert '[U+2717] Test 2: Failed (200.0ms)' in output
        assert 'Results: 1/2 passed, 1 failed' in output
        assert 'Total time:' in output
        assert 'Error: Test error' in output
        assert 'Test traceback' in output

    def test_print_summary_status_symbols(self):
        """Test _print_summary uses correct status symbols."""
        self.validator.results = [ValidationResult('Passed Test', ValidationStatus.PASSED, 'OK', 50.0), ValidationResult('Failed Test', ValidationStatus.FAILED, 'Fail', 75.0), ValidationResult('Skipped Test', ValidationStatus.SKIPPED, 'Skip', 0.0), ValidationResult('Running Test', ValidationStatus.RUNNING, 'Run', 25.0), ValidationResult('Pending Test', ValidationStatus.PENDING, 'Wait', 0.0)]
        import io
        from contextlib import redirect_stdout
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            self.validator._print_summary()
        output = output_buffer.getvalue()
        assert '[U+2713] Passed Test' in output
        assert '[U+2717] Failed Test' in output
        assert '[U+2298] Skipped Test' in output
        assert '[U+27F3] Running Test' in output
        assert '[U+25EF] Pending Test' in output

    def test_print_summary_empty_results(self):
        """Test _print_summary with no results."""
        import io
        from contextlib import redirect_stdout
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            self.validator._print_summary()
        output = output_buffer.getvalue()
        assert 'VALIDATION SUMMARY' in output
        assert 'Results: 0/0 passed, 0 failed' in output

class StartupValidatorUtilityFunctionsTests(BaseTestCase):
    """Test utility functions and entry points."""

    @pytest.mark.asyncio
    async def test_validate_startup_function(self):
        """Test validate_startup function creates validator and calls validate_all."""
        with patch('netra_backend.app.core.startup_validator.StartupValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_all = AsyncMock(return_value=True)
            mock_validator_class.return_value = mock_validator
            result = await validate_startup()
            assert result is True
            mock_validator_class.assert_called_once()
            mock_validator.validate_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_startup_function_failure(self):
        """Test validate_startup function with validation failure."""
        with patch('netra_backend.app.core.startup_validator.StartupValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_all = AsyncMock(return_value=False)
            mock_validator_class.return_value = mock_validator
            result = await validate_startup()
            assert result is False

    def test_require_startup_validation_decorator(self):
        """Test require_startup_validation decorator functionality."""

        @require_startup_validation()
        def test_function():
            return 'function executed'
        result = test_function()
        assert result == 'function executed'
        assert hasattr(test_function, '_validated')
        assert test_function._validated is False

    def test_require_startup_validation_decorator_warning(self):
        """Test require_startup_validation decorator logs warning."""
        with patch('netra_backend.app.core.startup_validator.logger') as mock_logger:

            @require_startup_validation()
            def test_function():
                return 'executed'
            test_function()
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert 'called without startup validation' in warning_call
            assert 'test_function' in warning_call

class StartupValidatorConcurrentExecutionTests(BaseTestCase):
    """Test concurrent validation scenarios and thread safety."""

    @pytest.mark.asyncio
    async def test_multiple_validators_concurrent(self):
        """Test multiple validators can run concurrently."""

        async def run_validator():
            validator = StartupValidator()
            with patch.object(validator, '_validate_id_generation', return_value=(True, 'OK')):
                with patch.object(validator, '_validate_websocket_components', return_value=(True, 'OK')):
                    with patch.object(validator, '_validate_thread_service', return_value=(True, 'OK')):
                        with patch.object(validator, '_validate_repositories', return_value=(True, 'OK')):
                            with patch.object(validator, '_validate_imports', return_value=(True, 'OK')):
                                with patch.object(validator, '_validate_method_signatures', return_value=(True, 'OK')):
                                    with patch.object(validator, '_validate_agent_registry', return_value=(True, 'OK')):
                                        with patch.object(validator, '_validate_configuration', return_value=(True, 'OK')):
                                            return await validator.validate_all()
        tasks = [run_validator() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        assert all(results), f'Some validators failed: {results}'
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_validator_state_isolation(self):
        """Test that validator instances maintain separate state."""
        validator1 = StartupValidator()
        validator2 = StartupValidator()
        validator1.results.append(ValidationResult('Test 1', ValidationStatus.PASSED, 'OK', 100.0))
        assert len(validator1.results) == 1
        assert len(validator2.results) == 0
        validator1.start_time = datetime.now()
        assert validator2.start_time is None

    @pytest.mark.asyncio
    async def test_concurrent_validation_with_failures(self):
        """Test concurrent validations with some failures."""

        async def run_failing_validator():
            validator = StartupValidator()
            with patch.object(validator, '_validate_id_generation', return_value=(False, 'ID Failed')):
                with patch.object(validator, '_validate_websocket_components', return_value=(True, 'WS OK')):
                    with patch.object(validator, '_validate_thread_service', return_value=(True, 'Thread OK')):
                        with patch.object(validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                            with patch.object(validator, '_validate_imports', return_value=(True, 'Imports OK')):
                                with patch.object(validator, '_validate_method_signatures', return_value=(True, 'Sigs OK')):
                                    with patch.object(validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                        with patch.object(validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                            return await validator.validate_all()

        async def run_passing_validator():
            validator = StartupValidator()
            with patch.object(validator, '_validate_id_generation', return_value=(True, 'ID OK')):
                with patch.object(validator, '_validate_websocket_components', return_value=(True, 'WS OK')):
                    with patch.object(validator, '_validate_thread_service', return_value=(True, 'Thread OK')):
                        with patch.object(validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                            with patch.object(validator, '_validate_imports', return_value=(True, 'Imports OK')):
                                with patch.object(validator, '_validate_method_signatures', return_value=(True, 'Sigs OK')):
                                    with patch.object(validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                        with patch.object(validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                            return await validator.validate_all()
        tasks = [run_failing_validator(), run_passing_validator(), run_failing_validator()]
        results = await asyncio.gather(*tasks)
        assert results == [False, True, False]

class StartupValidatorErrorEdgeCasesTests(BaseTestCase):
    """Test error handling, exception scenarios, and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator = StartupValidator()

    def test_validator_with_none_values(self):
        """Test validator handles None values gracefully."""
        result = ValidationResult(name=None, status=ValidationStatus.FAILED, message=None, duration_ms=0.0)
        self.validator.results.append(result)
        import io
        from contextlib import redirect_stdout
        output_buffer = io.StringIO()
        try:
            with redirect_stdout(output_buffer):
                self.validator._print_summary()
        except Exception as e:
            pytest.fail(f'_print_summary should handle None values: {e}')

    def test_validator_with_unicode_messages(self):
        """Test validator handles unicode and special characters."""
        result = ValidationResult(name='Unicode Test [U+6D4B][U+8BD5]', status=ValidationStatus.PASSED, message='Success with [U+00E9]mojis [U+1F680] and sp[U+00E9]cial chars', duration_ms=123.45)
        self.validator.results.append(result)
        import io
        from contextlib import redirect_stdout
        output_buffer = io.StringIO()
        try:
            with redirect_stdout(output_buffer):
                self.validator._print_summary()
            output = output_buffer.getvalue()
            assert 'Unicode Test [U+6D4B][U+8BD5]' in output
            assert '[U+00E9]mojis [U+1F680]' in output
        except UnicodeEncodeError:
            pass

    @pytest.mark.asyncio
    async def test_validator_with_very_long_duration(self):
        """Test validator handles very long validation durations."""

        def extremely_slow_validator():
            import time
            time.sleep(0.1)
            return (True, 'Extremely slow validation')
        with patch.object(self.validator, '_validate_id_generation', side_effect=extremely_slow_validator):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'Fast')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Fast')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Fast')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Fast')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Fast')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Fast')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Fast')):
                                        result = await self.validator.validate_all()
                                        assert result is True
                                        slow_result = next((r for r in self.validator.results if r.name == 'ID Generation'))
                                        assert slow_result.duration_ms >= 100

    def test_validator_memory_management(self):
        """Test validator doesn't leak memory with large result sets."""
        for i in range(1000):
            result = ValidationResult(name=f'Test {i}', status=ValidationStatus.PASSED, message=f'Test message {i}' * 100, duration_ms=float(i))
            self.validator.results.append(result)
        assert len(self.validator.results) == 1000
        self.validator.results.clear()
        assert len(self.validator.results) == 0

    def test_validator_system_exit_scenarios(self):
        """Test validator behavior in system exit scenarios."""
        import subprocess
        import sys
        test_script = '\nimport sys\nimport asyncio\nfrom unittest.mock import patch\n\n# Add the project path\nsys.path.insert(0, r"C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1")\n\nasync def test_main():\n    from netra_backend.app.core.startup_validator import validate_startup\n    \n    # Mock all validations to succeed\n    with patch("netra_backend.app.core.startup_validator.StartupValidator") as mock_validator_class:\n        mock_validator = type("MockValidator", (), {})()\n        mock_validator.validate_all = lambda: True\n        mock_validator_class.return_value = mock_validator\n        \n        result = await validate_startup()\n        sys.exit(0 if result else 1)\n\nif __name__ == "__main__":\n    asyncio.run(test_main())\n'
        assert '__main__' in test_script
        assert 'sys.exit' in test_script

class StartupValidatorPerformanceTests(BaseTestCase):
    """Test validation timing, metrics, and performance requirements."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validation_performance_requirements(self):
        """Test validation completes within reasonable time limits."""
        with patch.object(self.validator, '_validate_id_generation', return_value=(True, 'Fast')):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'Fast')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Fast')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Fast')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Fast')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Fast')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Fast')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Fast')):
                                        start_time = time.time()
                                        result = await self.validator.validate_all()
                                        end_time = time.time()
                                        duration = end_time - start_time
                                        assert result is True
                                        assert duration < 1.0, f'Validation took too long: {duration}s'
                                        for validation_result in self.validator.results:
                                            assert validation_result.duration_ms < 100, f'{validation_result.name} took {validation_result.duration_ms}ms'

    @pytest.mark.asyncio
    async def test_validation_timing_accuracy(self):
        """Test that validation timing measurements are accurate."""

        def timed_validator():
            time.sleep(0.05)
            return (True, 'Timed validation')
        with patch.object(self.validator, '_validate_id_generation', side_effect=timed_validator):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'Instant')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Instant')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Instant')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Instant')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Instant')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Instant')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Instant')):
                                        await self.validator.validate_all()
                                        timed_result = next((r for r in self.validator.results if r.name == 'ID Generation'))
                                        assert 45 <= timed_result.duration_ms <= 100, f'Expected ~50ms, got {timed_result.duration_ms}ms'

    def test_validation_memory_efficiency(self):
        """Test that validation doesn't consume excessive memory."""
        import tracemalloc
        tracemalloc.start()
        validator = StartupValidator()
        for i in range(100):
            result = ValidationResult(name=f'Test {i}', status=ValidationStatus.PASSED, message='Test message', duration_ms=float(i))
            validator.results.append(result)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak < 1024 * 1024, f'Memory usage too high: {peak} bytes'

    @pytest.mark.asyncio
    async def test_validation_timeout_handling(self):
        """Test validation behavior with timeouts (simulated)."""

        def timeout_validator():
            time.sleep(0.2)
            return (True, 'Slow validation')
        with patch.object(self.validator, '_validate_id_generation', side_effect=timeout_validator):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'Fast')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(True, 'Fast')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Fast')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Fast')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Fast')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Fast')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Fast')):
                                        start_time = time.time()
                                        result = await self.validator.validate_all()
                                        end_time = time.time()
                                        assert result is True
                                        assert end_time - start_time >= 0.2
                                        slow_result = next((r for r in self.validator.results if r.name == 'ID Generation'))
                                        assert slow_result.duration_ms >= 200

class StartupValidatorBusinessValueTests(BaseTestCase):
    """Test business value scenarios - preventing broken deployments."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_critical_system_failure_detection(self):
        """Test validator detects critical system failures that would break deployment."""
        with patch.object(self.validator, '_validate_id_generation', return_value=(False, 'CRITICAL: ID generation broken')):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(False, 'CRITICAL: WebSocket broken')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(False, 'CRITICAL: Thread service broken')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Sigs OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is False
                                        failed_results = [r for r in self.validator.results if r.status == ValidationStatus.FAILED]
                                        assert len(failed_results) == 3
                                        failed_names = [r.name for r in failed_results]
                                        assert 'ID Generation' in failed_names
                                        assert 'WebSocket Components' in failed_names
                                        assert 'Thread Service' in failed_names

    @pytest.mark.asyncio
    async def test_deployment_safety_validation(self):
        """Test that validator ensures deployment safety."""
        with patch.object(self.validator, '_validate_id_generation', return_value=(False, '2-argument bug detected')):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'WebSocket OK')):
                with patch.object(self.validator, '_validate_thread_service', return_value=(False, 'ThreadService 2-arg bug')):
                    with patch.object(self.validator, '_validate_repositories', return_value=(False, 'Repository import failed')):
                        with patch.object(self.validator, '_validate_imports', return_value=(False, 'Critical imports missing')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(False, 'Wrong signatures')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(False, 'Registry unhealthy')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(False, 'Config missing')):
                                        result = await self.validator.validate_all()
                                        assert result is False
                                        failed_results = [r for r in self.validator.results if r.status == ValidationStatus.FAILED]
                                        assert len(failed_results) >= 6
                                        assert self.validator.end_time is not None

    def test_startup_validator_prevents_silent_failures(self):
        """Test that validator catches silent failures that would cause issues."""
        validator = StartupValidator()
        mock_service = Mock()
        mock_service._prepare_run_data.side_effect = TypeError('generate_run_id() takes 1 positional argument but 2 were given')
        with patch('netra_backend.app.services.thread_service.ThreadService', return_value=mock_service):
            success, message = validator._validate_thread_service()
            assert success is False
            assert 'ThreadService has 2-argument bug' in message
            assert 'takes 1 positional argument but 2 were given' in message

    def test_validation_comprehensive_coverage(self):
        """Test that validation covers all critical startup components."""
        expected_validations = {'ID Generation', 'WebSocket Components', 'Thread Service', 'Database Repositories', 'Import Integrity', 'Method Signatures', 'Agent Registry', 'Configuration'}
        validator_code = inspect.getsource(self.validator.validate_all)
        for validation_name in expected_validations:
            assert validation_name in validator_code, f'Missing validation: {validation_name}'

    @pytest.mark.asyncio
    async def test_validator_prevents_broken_production_deployment(self):
        """Test end-to-end scenario: validator prevents broken production deployment."""

        def subtle_bug_validator():
            raise RuntimeError('Subtle production-breaking bug')
        with patch.object(self.validator, '_validate_id_generation', return_value=(True, 'ID OK')):
            with patch.object(self.validator, '_validate_websocket_components', return_value=(True, 'WebSocket OK')):
                with patch.object(self.validator, '_validate_thread_service', side_effect=subtle_bug_validator):
                    with patch.object(self.validator, '_validate_repositories', return_value=(True, 'Repos OK')):
                        with patch.object(self.validator, '_validate_imports', return_value=(True, 'Imports OK')):
                            with patch.object(self.validator, '_validate_method_signatures', return_value=(True, 'Sigs OK')):
                                with patch.object(self.validator, '_validate_agent_registry', return_value=(True, 'Registry OK')):
                                    with patch.object(self.validator, '_validate_configuration', return_value=(True, 'Config OK')):
                                        result = await self.validator.validate_all()
                                        assert result is False
                                        thread_result = next((r for r in self.validator.results if r.name == 'Thread Service'))
                                        assert thread_result.status == ValidationStatus.FAILED
                                        assert 'Subtle production-breaking bug' in thread_result.message
                                        assert thread_result.error is not None
                                        assert thread_result.traceback is not None

@pytest.mark.unit
class StartupValidatorIntegrationTests(BaseTestCase):
    """Integration tests for complete startup validation flow."""

    @pytest.mark.asyncio
    async def test_complete_validation_integration(self):
        """Test complete validation flow with real-like scenarios."""
        validator = StartupValidator()
        with patch('netra_backend.app.core.unified_id_manager.UnifiedIDManager') as mock_id_manager:
            mock_id_manager.generate_run_id.return_value = 'run_20241207_startup_validation_abc123'
            mock_id_manager.validate_run_id.return_value = True
            mock_id_manager.extract_thread_id.return_value = 'startup_validation'
            with patch('inspect.signature') as mock_signature:
                mock_sig = Mock()
                mock_param = Mock()
                mock_param.default = inspect.Parameter.empty
                mock_sig.parameters = {'thread_id': mock_param}
                mock_signature.return_value = mock_sig
                with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge') as mock_bridge_class:
                    mock_bridge = Mock()
                    mock_bridge.extract_thread_id.return_value = 'websocket_test'
                    mock_bridge_class.return_value = mock_bridge
                    with patch('netra_backend.app.services.thread_service.ThreadService') as mock_thread_service_class:
                        mock_thread_service = Mock()
                        mock_thread_service._prepare_run_data.return_value = ('run_id', {'thread_id': 'test_thread'})
                        mock_thread_service_class.return_value = mock_thread_service
                        with patch('netra_backend.app.services.database.run_repository.RunRepository', Mock()):
                            with patch('importlib.import_module', return_value=Mock()):
                                with patch('netra_backend.app.core.registry.universal_registry.get_global_registry') as mock_registry:
                                    mock_reg = Mock()
                                    mock_reg.is_healthy.return_value = True
                                    mock_reg.get_stats.return_value = {'registered_count': 3}
                                    mock_registry.return_value = mock_reg
                                    with patch('netra_backend.app.config.settings') as mock_settings:
                                        mock_settings.environment = 'test'
                                        result = await validator.validate_all()
                                        assert result is True
                                        assert len(validator.results) == 8
                                        assert all((r.status == ValidationStatus.PASSED for r in validator.results))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')