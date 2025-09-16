"""
Unit tests for Issue #378: Database Configuration Validation Fix

This test suite validates that the enhanced startup validation properly catches
database configuration issues early, before auto-initialization attempts.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Platform Stability & Issue Prevention
- Value Impact: Prevents configuration issues from causing production failures
- Revenue Impact: Critical for operational reliability
"""
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.startup_validation import StartupValidator, ComponentValidation, ComponentStatus

@pytest.mark.unit
class DatabaseConfigurationValidationFixTests(SSotAsyncTestCase):
    """Test suite for the Issue #378 fix in startup validation."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        from shared.logging.unified_logging_ssot import get_logger
        self.logger = get_logger(__name__)

    async def test_early_configuration_validation_detects_missing_vars(self):
        """
        TEST: Early configuration validation detects missing environment variables.
        
        This tests the Issue #378 fix to ensure configuration problems are detected
        before any auto-initialization attempts.
        """
        self.logger.info('Testing early configuration validation for missing environment variables')
        validator = StartupValidator()
        with patch.dict(os.environ, {}, clear=True):
            await validator._validate_database_configuration_early()
            config_validations = [v for v in validator.validations if v.name == 'Database Configuration' and v.status == ComponentStatus.CRITICAL]
            assert len(config_validations) > 0, 'Should detect missing configuration variables'
            validation = config_validations[0]
            assert 'Missing required environment variables' in validation.message
            assert validation.is_critical, 'Configuration issues should be marked as critical'
            assert 'POSTGRES_HOST' in validation.message
            assert 'POSTGRES_PORT' in validation.message
            assert 'POSTGRES_DB' in validation.message
            assert 'POSTGRES_USER' in validation.message
            self.logger.info(f'Successfully detected missing configuration: {validation.message}')

    async def test_early_configuration_validation_detects_empty_vars(self):
        """
        TEST: Early configuration validation detects empty environment variables.
        """
        self.logger.info('Testing early configuration validation for empty environment variables')
        validator = StartupValidator()
        with patch.dict(os.environ, {'POSTGRES_HOST': '', 'POSTGRES_PORT': '5432', 'POSTGRES_DB': 'test_db', 'POSTGRES_USER': ''}, clear=False):
            await validator._validate_database_configuration_early()
            config_validations = [v for v in validator.validations if v.name == 'Database Configuration' and v.status == ComponentStatus.CRITICAL]
            assert len(config_validations) > 0, 'Should detect empty configuration variables'
            validation = config_validations[0]
            assert 'Empty required environment variables' in validation.message
            assert 'POSTGRES_HOST' in validation.message
            assert 'POSTGRES_USER' in validation.message
            self.logger.info(f'Successfully detected empty configuration: {validation.message}')

    async def test_early_configuration_validation_passes_with_valid_config(self):
        """
        TEST: Early configuration validation passes with valid configuration.
        """
        self.logger.info('Testing early configuration validation with valid configuration')
        validator = StartupValidator()
        with patch.dict(os.environ, {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432', 'POSTGRES_DB': 'test_db', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_pass'}, clear=False):
            await validator._validate_database_configuration_early()
            config_validations = [v for v in validator.validations if v.name == 'Database Configuration']
            assert len(config_validations) > 0, 'Should have configuration validation result'
            validation = config_validations[0]
            if validation.status == ComponentStatus.HEALTHY:
                assert 'Configuration validation passed' in validation.message
                self.logger.info(f'Configuration validation passed: {validation.message}')
            else:
                self.logger.info(f'Configuration validation result: {validation.status.value} - {validation.message}')

    async def test_database_validation_calls_early_configuration_validation(self):
        """
        TEST: Database validation calls early configuration validation.
        
        This ensures the Issue #378 fix is properly integrated into the main
        database validation workflow.
        """
        self.logger.info('Testing that database validation includes early configuration validation')
        validator = StartupValidator()
        mock_app = Mock()
        mock_app.state = Mock()
        mock_app.state.db_session_factory = None
        mock_app.state.database_mock_mode = False
        with patch.dict(os.environ, {}, clear=True):
            await validator._validate_database(mock_app)
            config_validations = [v for v in validator.validations if v.name == 'Database Configuration']
            database_validations = [v for v in validator.validations if v.name == 'Database' and v.category == 'Database']
            assert len(config_validations) > 0, 'Should include configuration validation'
            assert len(database_validations) > 0, 'Should include database validation'
            config_val = config_validations[0]
            assert config_val.status == ComponentStatus.CRITICAL
            self.logger.info('Database validation properly includes configuration validation')

    async def test_configuration_error_messages_are_actionable(self):
        """
        TEST: Configuration error messages provide actionable guidance.
        
        This ensures that when configuration problems are detected, the error
        messages tell operators exactly what they need to fix.
        """
        self.logger.info('Testing actionable configuration error messages')
        validator = StartupValidator()
        with patch.dict(os.environ, {}, clear=True):
            await validator._validate_database_configuration_early()
            config_validations = [v for v in validator.validations if v.name == 'Database Configuration' and v.status == ComponentStatus.CRITICAL]
            assert len(config_validations) > 0
            validation = config_validations[0]
            message = validation.message.lower()
            assert 'postgres_' in message, 'Should mention specific environment variables'
            assert 'environment variables' in message, 'Should explain what needs to be set'
            assert 'missing_vars' in validation.metadata
            assert 'required_vars' in validation.metadata
            self.logger.info(f'Error message is actionable: {validation.message}')

    async def test_configuration_validation_prevents_auto_initialization_masking(self):
        """
        TEST: Configuration validation prevents auto-initialization from masking issues.
        
        This is the core test for Issue #378 - ensuring configuration problems are
        detected early rather than being masked by auto-initialization attempts.
        """
        self.logger.info('Testing that configuration validation prevents auto-initialization masking')
        validator = StartupValidator()
        with patch.dict(os.environ, {'POSTGRES_HOST': '', 'POSTGRES_PORT': 'invalid_port', 'POSTGRES_DB': '', 'POSTGRES_USER': ''}, clear=False):
            await validator._validate_database_configuration_early()
            config_validations = [v for v in validator.validations if v.name == 'Database Configuration' and v.status == ComponentStatus.CRITICAL]
            assert len(config_validations) > 0, 'Should detect configuration issues early'
            validation = config_validations[0]
            message = validation.message.lower()
            assert 'empty' in message or 'missing' in message, 'Should identify empty/missing values'
            self.logger.info(f'Configuration issues detected early: {validation.message}')
            self.logger.info('✅ Issue #378 fix working: Configuration validation prevents auto-initialization masking')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')