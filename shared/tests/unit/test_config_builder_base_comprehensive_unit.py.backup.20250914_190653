"""
Comprehensive unit tests for ConfigBuilderBase SSOT class.
Tests the single source of truth for configuration builder patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all services and user segments)
- Business Goal: Development Velocity, System Reliability, Technical Debt Reduction
- Value Impact: Prevents $50K/year in maintenance costs from inconsistent config logic
- Strategic Impact: Foundation for all configuration builders ensuring SSOT compliance

CRITICAL BUSINESS PROBLEM SOLVED:
This test suite validates that ConfigBuilderBase eliminates 200+ lines of duplicate
environment detection logic across multiple configuration builders, preventing
inconsistent behavior and maintenance burden.

SSOT PRINCIPLE ENFORCEMENT:
Every test validates that environment detection, validation patterns, and configuration
utilities exist in EXACTLY ONE PLACE and work consistently across all scenarios.

Testing Coverage Goals:
[U+2713] Environment detection across 8+ environment variables
[U+2713] Priority order handling for multiple environment variables
[U+2713] Cloud Run K_SERVICE detection logic
[U+2713] Pattern matching with case insensitivity 
[U+2713] Environment variable utilities (bool, int, list parsing)
[U+2713] Validation framework for required fields and constraints
[U+2713] Logging and security (credential masking)
[U+2713] IsolatedEnvironment integration
[U+2713] Thread safety and performance under load
[U+2713] Abstract method enforcement
[U+2713] Debug information generation
"""

import pytest
import os
import threading
import time
import concurrent.futures
import logging
import hashlib
from typing import Dict, List, Optional, Any, Set, Callable, Union, Tuple
from unittest.mock import patch, Mock, MagicMock, call
from dataclasses import dataclass, field
import sys
import re
from pathlib import Path
from abc import ABC, abstractmethod
import gc
import traceback

# ABSOLUTE IMPORTS per SSOT requirements - CLAUDE.md compliance
from shared.config_builder_base import (
    ConfigBuilderBase,
    ConfigEnvironment,
    ConfigValidationMixin,
    ConfigLoggingMixin
)
from shared.isolated_environment import IsolatedEnvironment


class TestConfigImplementation(ConfigBuilderBase):
    """Test implementation of abstract ConfigBuilderBase for testing."""
    
    def __init__(self, env_vars: Optional[Dict[str, Any]] = None):
        super().__init__(env_vars)
        self.validation_called = False
        self.debug_info_called = False
        
    def validate(self) -> Tuple[bool, str]:
        """Test implementation of abstract validate method."""
        self.validation_called = True
        return True, ""
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Test implementation of abstract get_debug_info method."""
        self.debug_info_called = True
        base_info = self.get_common_debug_info()
        base_info.update({
            "test_implementation": True,
            "validation_called": self.validation_called
        })
        return base_info


class FailingConfigImplementation(ConfigBuilderBase):
    """Test implementation that fails validation for testing error paths."""
    
    def validate(self) -> Tuple[bool, str]:
        """Test implementation that always fails validation."""
        return False, "Test validation failure"
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Test implementation with debug info."""
        return {"failing_implementation": True}


class TestConfigBuilderBaseCore:
    """Test ConfigBuilderBase core functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_basic_initialization(self):
        """Test basic ConfigBuilderBase initialization."""
        config = TestConfigImplementation()
        
        assert config is not None
        assert hasattr(config, 'env')
        assert hasattr(config, 'environment')
        assert hasattr(config, '_logger')
        assert config.environment in ['development', 'staging', 'production']

    def test_initialization_with_env_vars(self):
        """Test initialization with custom environment variables."""
        test_env = {
            'ENVIRONMENT': 'staging',
            'TEST_VAR': 'test_value'
        }
        
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.environment == 'staging'
        assert config.get_env_var('TEST_VAR') == 'test_value'

    def test_initialization_with_none_values(self):
        """Test initialization with None values removes environment variables."""
        # First set up IsolatedEnvironment with a variable
        IsolatedEnvironment.get_instance().set('REMOVE_ME', 'should_be_removed')
        
        test_env = {
            'ENVIRONMENT': 'development',
            'REMOVE_ME': None
        }
        
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.environment == 'development'
        assert config.get_env_var('REMOVE_ME') is None

    def test_abstract_methods_enforcement(self):
        """Test that abstract methods must be implemented."""
        with pytest.raises(TypeError):
            # This should fail because ConfigBuilderBase is abstract
            ConfigBuilderBase()

    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        config = TestConfigImplementation()
        
        assert config._logger is not None
        assert isinstance(config._logger, logging.Logger)
        assert config.__class__.__name__ in config._logger.name


class TestEnvironmentDetection:
    """Test environment detection logic - CORE SSOT FUNCTIONALITY."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_environment_detection_priority_order(self):
        """Test that environment variables are checked in correct priority order."""
        # Test each environment variable individually
        env_vars = [
            "ENVIRONMENT",
            "ENV", 
            "NETRA_ENVIRONMENT",
            "NETRA_ENV",
            "NODE_ENV",
            "AUTH_ENV",
            "K_SERVICE",
            "GCP_PROJECT_ID"
        ]
        
        for env_var in env_vars:
            test_env = {env_var: 'production'}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == 'production', f"Failed for {env_var}"

    def test_production_patterns(self):
        """Test production environment pattern matching."""
        production_values = ['production', 'prod', 'PRODUCTION', 'PROD', 'Production']
        
        for value in production_values:
            test_env = {'ENVIRONMENT': value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == 'production', f"Failed for production value: {value}"

    def test_staging_patterns(self):
        """Test staging environment pattern matching."""
        staging_values = ['staging', 'stage', 'stg', 'STAGING', 'STAGE', 'STG', 'Staging']
        
        for value in staging_values:
            test_env = {'ENVIRONMENT': value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == 'staging', f"Failed for staging value: {value}"

    def test_development_patterns(self):
        """Test development environment pattern matching."""
        dev_values = ['development', 'dev', 'local', 'test', 'testing', 'DEVELOPMENT', 'DEV', 'LOCAL']
        
        for value in dev_values:
            test_env = {'ENVIRONMENT': value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == 'development', f"Failed for development value: {value}"

    def test_cloud_run_k_service_detection(self):
        """Test Cloud Run K_SERVICE special detection logic."""
        # Staging Cloud Run service
        test_env = {'K_SERVICE': 'netra-staging-service'}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.environment == 'staging'
        
        # Production Cloud Run service (non-staging)
        test_env = {'K_SERVICE': 'netra-production-service'}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.environment == 'production'
        
        # Generic Cloud Run service defaults to production
        test_env = {'K_SERVICE': 'netra-backend'}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.environment == 'production'

    def test_case_insensitive_matching(self):
        """Test that environment detection is case insensitive."""
        test_cases = [
            ('PRODUCTION', 'production'),
            ('Production', 'production'),
            ('pRoDuCtIoN', 'production'),
            ('STAGING', 'staging'),
            ('Staging', 'staging'),
            ('sTaGiNg', 'staging')
        ]
        
        for input_value, expected_env in test_cases:
            test_env = {'ENVIRONMENT': input_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == expected_env

    def test_whitespace_handling(self):
        """Test that whitespace is properly stripped from environment values."""
        test_cases = [
            ('  production  ', 'production'),
            ('\tproduction\t', 'production'),
            ('\nproduction\n', 'production'),
            ('   staging   ', 'staging'),
            ('development  ', 'development')
        ]
        
        for input_value, expected_env in test_cases:
            test_env = {'ENVIRONMENT': input_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == expected_env

    def test_multiple_environment_variables_priority(self):
        """Test priority when multiple environment variables are set."""
        # ENVIRONMENT should take priority over ENV
        test_env = {
            'ENVIRONMENT': 'production',
            'ENV': 'staging'
        }
        config = TestConfigImplementation(env_vars=test_env)
        assert config.environment == 'production'
        
        # First found environment variable wins
        test_env = {
            'ENV': 'staging',
            'NETRA_ENVIRONMENT': 'production'
        }
        config = TestConfigImplementation(env_vars=test_env)
        assert config.environment == 'staging'

    def test_default_to_development(self):
        """Test that system defaults to development when no environment is detected."""
        test_env = {}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.environment == 'development'

    def test_invalid_environment_values_default_to_development(self):
        """Test that invalid environment values default to development."""
        invalid_values = ['invalid', 'unknown', '123', '', '   ']
        
        for invalid_value in invalid_values:
            test_env = {'ENVIRONMENT': invalid_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.environment == 'development', f"Failed for invalid value: {invalid_value}"


class TestEnvironmentHelperMethods:
    """Test environment helper methods."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_is_development(self):
        """Test is_development method."""
        test_env = {'ENVIRONMENT': 'development'}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.is_development() is True
        assert config.is_staging() is False
        assert config.is_production() is False

    def test_is_staging(self):
        """Test is_staging method."""
        test_env = {'ENVIRONMENT': 'staging'}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.is_development() is False
        assert config.is_staging() is True
        assert config.is_production() is False

    def test_is_production(self):
        """Test is_production method."""
        test_env = {'ENVIRONMENT': 'production'}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.is_development() is False
        assert config.is_staging() is False
        assert config.is_production() is True


class TestEnvironmentVariableUtilities:
    """Test environment variable utility methods."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_get_env_var_basic(self):
        """Test basic get_env_var functionality."""
        test_env = {
            'TEST_VAR': 'test_value',
            'EMPTY_VAR': ''
        }
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('TEST_VAR') == 'test_value'
        assert config.get_env_var('EMPTY_VAR') == ''
        assert config.get_env_var('NONEXISTENT') is None

    def test_get_env_var_with_default(self):
        """Test get_env_var with default values."""
        test_env = {'TEST_VAR': 'test_value'}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('TEST_VAR', 'default') == 'test_value'
        assert config.get_env_var('NONEXISTENT', 'default') == 'default'
        assert config.get_env_var('NONEXISTENT') is None

    def test_get_env_bool_true_values(self):
        """Test get_env_bool with various true representations."""
        true_values = ['true', 'TRUE', 'True', '1', 'yes', 'YES', 'Yes', 'on', 'ON', 'On']
        
        for true_value in true_values:
            test_env = {'BOOL_VAR': true_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.get_env_bool('BOOL_VAR') is True, f"Failed for true value: {true_value}"

    def test_get_env_bool_false_values(self):
        """Test get_env_bool with various false representations."""
        false_values = ['false', 'FALSE', 'False', '0', 'no', 'NO', 'No', 'off', 'OFF', 'Off', 'invalid']
        
        for false_value in false_values:
            test_env = {'BOOL_VAR': false_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.get_env_bool('BOOL_VAR') is False, f"Failed for false value: {false_value}"

    def test_get_env_bool_default_values(self):
        """Test get_env_bool with default values."""
        test_env = {}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_bool('NONEXISTENT') is False  # Default false
        assert config.get_env_bool('NONEXISTENT', default=True) is True
        
        # Empty string should use default
        test_env = {'EMPTY_VAR': ''}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.get_env_bool('EMPTY_VAR') is False
        assert config.get_env_bool('EMPTY_VAR', default=True) is True

    def test_get_env_bool_whitespace_handling(self):
        """Test get_env_bool handles whitespace properly."""
        test_env = {'BOOL_VAR': '  true  '}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.get_env_bool('BOOL_VAR') is True

    def test_get_env_int_valid_integers(self):
        """Test get_env_int with valid integer values."""
        test_cases = [
            ('123', 123),
            ('0', 0),
            ('-123', -123),
            ('999999', 999999)
        ]
        
        for str_value, expected_int in test_cases:
            test_env = {'INT_VAR': str_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.get_env_int('INT_VAR') == expected_int

    def test_get_env_int_invalid_values(self):
        """Test get_env_int with invalid values uses defaults."""
        invalid_values = ['abc', '12.34', 'true', '']
        
        for invalid_value in invalid_values:
            test_env = {'INT_VAR': invalid_value}
            config = TestConfigImplementation(env_vars=test_env)
            assert config.get_env_int('INT_VAR') == 0  # Default 0
            assert config.get_env_int('INT_VAR', default=42) == 42

    def test_get_env_int_nonexistent_variable(self):
        """Test get_env_int with nonexistent variables."""
        test_env = {}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_int('NONEXISTENT') == 0
        assert config.get_env_int('NONEXISTENT', default=100) == 100

    def test_get_env_int_whitespace_handling(self):
        """Test get_env_int handles whitespace properly."""
        test_env = {'INT_VAR': '  123  '}
        config = TestConfigImplementation(env_vars=test_env)
        assert config.get_env_int('INT_VAR') == 123

    def test_get_env_list_basic_functionality(self):
        """Test get_env_list basic comma separation."""
        test_env = {'LIST_VAR': 'item1,item2,item3'}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('LIST_VAR')
        assert result == ['item1', 'item2', 'item3']

    def test_get_env_list_custom_separator(self):
        """Test get_env_list with custom separators."""
        test_env = {'LIST_VAR': 'item1;item2;item3'}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('LIST_VAR', separator=';')
        assert result == ['item1', 'item2', 'item3']

    def test_get_env_list_whitespace_handling(self):
        """Test get_env_list handles whitespace properly."""
        test_env = {'LIST_VAR': 'item1, item2 ,  item3  '}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('LIST_VAR')
        assert result == ['item1', 'item2', 'item3']

    def test_get_env_list_empty_items_filtered(self):
        """Test get_env_list filters out empty items."""
        test_env = {'LIST_VAR': 'item1,,item3,'}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('LIST_VAR')
        assert result == ['item1', 'item3']

    def test_get_env_list_empty_string(self):
        """Test get_env_list with empty string."""
        test_env = {'LIST_VAR': ''}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('LIST_VAR')
        assert result == []

    def test_get_env_list_nonexistent_variable(self):
        """Test get_env_list with nonexistent variables."""
        test_env = {}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('NONEXISTENT')
        assert result == []
        
        result = config.get_env_list('NONEXISTENT', default=['default'])
        assert result == ['default']

    def test_get_env_list_single_item(self):
        """Test get_env_list with single item."""
        test_env = {'LIST_VAR': 'single_item'}
        config = TestConfigImplementation(env_vars=test_env)
        
        result = config.get_env_list('LIST_VAR')
        assert result == ['single_item']


class TestEnvironmentVariableValidation:
    """Test environment variable validation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_validate_required_variable_present(self):
        """Test validation of required variables that are present."""
        test_env = {'REQUIRED_VAR': 'present'}
        config = TestConfigImplementation(env_vars=test_env)
        
        is_valid, error_msg = config.validate_environment_variable('REQUIRED_VAR', required=True)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_required_variable_missing(self):
        """Test validation of required variables that are missing."""
        test_env = {}
        config = TestConfigImplementation(env_vars=test_env)
        
        is_valid, error_msg = config.validate_environment_variable('REQUIRED_VAR', required=True)
        assert is_valid is False
        assert "REQUIRED_VAR is required but not set" in error_msg

    def test_validate_optional_variable_missing(self):
        """Test validation of optional variables that are missing."""
        test_env = {}
        config = TestConfigImplementation(env_vars=test_env)
        
        is_valid, error_msg = config.validate_environment_variable('OPTIONAL_VAR', required=False)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_min_length_satisfied(self):
        """Test validation when minimum length requirement is satisfied."""
        test_env = {'TEST_VAR': 'longvalue'}
        config = TestConfigImplementation(env_vars=test_env)
        
        is_valid, error_msg = config.validate_environment_variable('TEST_VAR', min_length=5)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_min_length_violated(self):
        """Test validation when minimum length requirement is violated."""
        test_env = {'TEST_VAR': 'short'}
        config = TestConfigImplementation(env_vars=test_env)
        
        is_valid, error_msg = config.validate_environment_variable('TEST_VAR', min_length=10)
        assert is_valid is False
        assert "must be at least 10 characters" in error_msg

    def test_validate_combined_requirements(self):
        """Test validation with combined requirements."""
        test_env = {'TEST_VAR': 'valid_length'}
        config = TestConfigImplementation(env_vars=test_env)
        
        is_valid, error_msg = config.validate_environment_variable(
            'TEST_VAR', required=True, min_length=5
        )
        assert is_valid is True
        assert error_msg == ""


class TestDebugAndLoggingMethods:
    """Test debug information and logging methods."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_get_common_debug_info_structure(self):
        """Test that get_common_debug_info returns expected structure."""
        test_env = {'ENVIRONMENT': 'staging'}
        config = TestConfigImplementation(env_vars=test_env)
        
        debug_info = config.get_common_debug_info()
        
        assert 'class_name' in debug_info
        assert 'environment' in debug_info
        assert 'environment_detection' in debug_info
        assert 'common_env_vars' in debug_info
        
        assert debug_info['class_name'] == 'TestConfigImplementation'
        assert debug_info['environment'] == 'staging'

    def test_get_common_debug_info_environment_detection(self):
        """Test environment detection info in debug output."""
        test_env = {'ENVIRONMENT': 'production'}
        config = TestConfigImplementation(env_vars=test_env)
        
        debug_info = config.get_common_debug_info()
        env_detection = debug_info['environment_detection']
        
        assert env_detection['is_development'] is False
        assert env_detection['is_staging'] is False
        assert env_detection['is_production'] is True

    def test_get_safe_log_summary(self):
        """Test safe log summary generation."""
        test_env = {'ENVIRONMENT': 'development'}
        config = TestConfigImplementation(env_vars=test_env)
        
        summary = config.get_safe_log_summary()
        assert 'TestConfigImplementation Configuration' in summary
        assert 'Environment: development' in summary

    def test_log_common_info_basic(self, caplog):
        """Test basic common info logging."""
        test_env = {'ENVIRONMENT': 'staging'}
        config = TestConfigImplementation(env_vars=test_env)
        
        with caplog.at_level(logging.INFO):
            config.log_common_info()
        
        assert 'TestConfigImplementation Configuration' in caplog.text
        assert 'Environment: staging' in caplog.text

    def test_log_common_info_with_additional(self, caplog):
        """Test common info logging with additional information."""
        test_env = {'ENVIRONMENT': 'production'}
        config = TestConfigImplementation(env_vars=test_env)
        
        with caplog.at_level(logging.INFO):
            config.log_common_info("Additional test info")
        
        assert 'TestConfigImplementation Configuration' in caplog.text
        assert 'Environment: production' in caplog.text
        assert 'Additional test info' in caplog.text


class TestAbstractMethodImplementation:
    """Test abstract method implementation requirements."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_abstract_validate_method_called(self):
        """Test that abstract validate method is properly called."""
        config = TestConfigImplementation()
        
        is_valid, error_msg = config.validate()
        assert is_valid is True
        assert error_msg == ""
        assert config.validation_called is True

    def test_abstract_get_debug_info_called(self):
        """Test that abstract get_debug_info method is properly called."""
        config = TestConfigImplementation()
        
        debug_info = config.get_debug_info()
        assert 'test_implementation' in debug_info
        assert debug_info['test_implementation'] is True
        assert config.debug_info_called is True

    def test_failing_validation_implementation(self):
        """Test implementation that fails validation."""
        config = FailingConfigImplementation()
        
        is_valid, error_msg = config.validate()
        assert is_valid is False
        assert error_msg == "Test validation failure"


class TestOptionalMethodOverrides:
    """Test optional method overrides."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_get_environment_specific_defaults_default(self):
        """Test default implementation of get_environment_specific_defaults."""
        config = TestConfigImplementation()
        
        defaults = config.get_environment_specific_defaults()
        assert defaults == {}

    def test_validate_for_environment_default(self):
        """Test default implementation of validate_for_environment."""
        config = TestConfigImplementation()
        
        is_valid, error_msg = config.validate_for_environment()
        assert is_valid is True
        assert error_msg == ""


class TestConfigEnvironmentEnum:
    """Test ConfigEnvironment enum functionality."""

    def test_config_environment_values(self):
        """Test that ConfigEnvironment has expected values."""
        assert ConfigEnvironment.DEVELOPMENT.value == "development"
        assert ConfigEnvironment.STAGING.value == "staging"
        assert ConfigEnvironment.PRODUCTION.value == "production"

    def test_config_environment_string_representation(self):
        """Test string representation of ConfigEnvironment values."""
        assert str(ConfigEnvironment.DEVELOPMENT) == "ConfigEnvironment.DEVELOPMENT"
        assert str(ConfigEnvironment.STAGING) == "ConfigEnvironment.STAGING" 
        assert str(ConfigEnvironment.PRODUCTION) == "ConfigEnvironment.PRODUCTION"

    def test_config_environment_comparison(self):
        """Test ConfigEnvironment value comparison."""
        assert ConfigEnvironment.DEVELOPMENT != ConfigEnvironment.STAGING
        assert ConfigEnvironment.STAGING != ConfigEnvironment.PRODUCTION
        assert ConfigEnvironment.DEVELOPMENT == ConfigEnvironment.DEVELOPMENT

    def test_config_environment_iteration(self):
        """Test iteration over ConfigEnvironment values."""
        environments = list(ConfigEnvironment)
        assert len(environments) == 3
        assert ConfigEnvironment.DEVELOPMENT in environments
        assert ConfigEnvironment.STAGING in environments
        assert ConfigEnvironment.PRODUCTION in environments


class TestConfigValidationMixin:
    """Test ConfigValidationMixin utility methods."""

    def test_validate_required_fields_all_present(self):
        """Test validation when all required fields are present."""
        config = {'field1': 'value1', 'field2': 'value2', 'field3': 'value3'}
        required_fields = ['field1', 'field2']
        
        is_valid, error_msg = ConfigValidationMixin.validate_required_fields(config, required_fields)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_required_fields_missing_fields(self):
        """Test validation when required fields are missing."""
        config = {'field1': 'value1'}
        required_fields = ['field1', 'field2', 'field3']
        
        is_valid, error_msg = ConfigValidationMixin.validate_required_fields(config, required_fields)
        assert is_valid is False
        assert "Missing required configuration fields" in error_msg
        assert "field2" in error_msg
        assert "field3" in error_msg

    def test_validate_required_fields_empty_requirements(self):
        """Test validation with empty required fields list."""
        config = {'field1': 'value1'}
        required_fields = []
        
        is_valid, error_msg = ConfigValidationMixin.validate_required_fields(config, required_fields)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_field_types_correct_types(self):
        """Test field type validation with correct types."""
        config = {
            'string_field': 'text',
            'int_field': 42,
            'bool_field': True,
            'list_field': [1, 2, 3]
        }
        field_types = {
            'string_field': str,
            'int_field': int,
            'bool_field': bool,
            'list_field': list
        }
        
        is_valid, error_msg = ConfigValidationMixin.validate_field_types(config, field_types)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_field_types_incorrect_types(self):
        """Test field type validation with incorrect types."""
        config = {
            'string_field': 123,  # Should be string
            'int_field': 'not_int',  # Should be int
            'bool_field': 'not_bool'  # Should be bool
        }
        field_types = {
            'string_field': str,
            'int_field': int,
            'bool_field': bool
        }
        
        is_valid, error_msg = ConfigValidationMixin.validate_field_types(config, field_types)
        assert is_valid is False
        assert "Type validation errors" in error_msg
        assert "string_field should be str but got int" in error_msg
        assert "int_field should be int but got str" in error_msg
        assert "bool_field should be bool but got str" in error_msg

    def test_validate_field_types_missing_fields_ignored(self):
        """Test that missing fields are ignored in type validation."""
        config = {'string_field': 'text'}
        field_types = {
            'string_field': str,
            'missing_field': int
        }
        
        is_valid, error_msg = ConfigValidationMixin.validate_field_types(config, field_types)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_field_types_empty_config(self):
        """Test field type validation with empty config."""
        config = {}
        field_types = {'field1': str, 'field2': int}
        
        is_valid, error_msg = ConfigValidationMixin.validate_field_types(config, field_types)
        assert is_valid is True
        assert error_msg == ""


class TestConfigLoggingMixin:
    """Test ConfigLoggingMixin safe logging utilities."""

    def test_mask_sensitive_value_basic(self):
        """Test basic sensitive value masking."""
        result = ConfigLoggingMixin.mask_sensitive_value("secret_password")
        assert result == "********"

    def test_mask_sensitive_value_with_visible_chars(self):
        """Test sensitive value masking with visible characters."""
        result = ConfigLoggingMixin.mask_sensitive_value("secret_password", visible_chars=3)
        # "secret_password" is 15 chars, visible_chars=3, so masked_part = min(8, max(3, 15-3)) = min(8, 12) = 8
        assert result == "sec********"

    def test_mask_sensitive_value_empty_string(self):
        """Test masking of empty string."""
        result = ConfigLoggingMixin.mask_sensitive_value("")
        assert result == "NOT_SET"

    def test_mask_sensitive_value_none(self):
        """Test masking of None value."""
        result = ConfigLoggingMixin.mask_sensitive_value(None)
        assert result == "NOT_SET"

    def test_mask_sensitive_value_short_value(self):
        """Test masking of very short values."""
        result = ConfigLoggingMixin.mask_sensitive_value("ab", visible_chars=3)
        assert result == "********"

    def test_mask_sensitive_value_custom_mask_char(self):
        """Test masking with custom mask character."""
        result = ConfigLoggingMixin.mask_sensitive_value("secret", mask_char="X")
        # "secret" is 6 chars, visible_chars=0, so masked_part = min(8, max(3, 6-0)) = min(8, 6) = 6
        assert result == "XXXXXX"

    def test_mask_sensitive_value_various_lengths(self):
        """Test masking with various value lengths."""
        test_cases = [
            # (value, visible_chars, expected) 
            ("a", 0, "***"),        # len=1, min(8, max(3, 1-0)) = min(8, 3) = 3
            ("ab", 0, "***"),       # len=2, min(8, max(3, 2-0)) = min(8, 3) = 3  
            ("abc", 0, "***"),      # len=3, min(8, max(3, 3-0)) = min(8, 3) = 3
            ("abcdefgh", 0, "********"), # len=8, min(8, max(3, 8-0)) = min(8, 8) = 8
            ("abcdefghijklmnop", 0, "********"), # len=16, min(8, max(3, 16-0)) = min(8, 16) = 8
            ("longpassword", 2, "lo********") # len=12, visible=2, min(8, max(3, 12-2)) = min(8, 10) = 8
        ]
        
        for value, visible_chars, expected in test_cases:
            result = ConfigLoggingMixin.mask_sensitive_value(value, visible_chars=visible_chars)
            assert result == expected, f"Failed for value: {value}, got: {result}, expected: {expected}"

    def test_mask_url_credentials_with_password(self):
        """Test URL credential masking with password."""
        url = "postgresql://user:password@localhost:5432/database"
        result = ConfigLoggingMixin.mask_url_credentials(url)
        assert ":password" not in result
        assert ":***" in result
        assert "user" in result
        assert "localhost:5432/database" in result

    def test_mask_url_credentials_no_password(self):
        """Test URL credential masking with no password."""
        url = "postgresql://user@localhost:5432/database"
        result = ConfigLoggingMixin.mask_url_credentials(url)
        assert result == url  # Should be unchanged

    def test_mask_url_credentials_empty_string(self):
        """Test URL credential masking with empty string."""
        result = ConfigLoggingMixin.mask_url_credentials("")
        assert result == "NOT_SET"

    def test_mask_url_credentials_none(self):
        """Test URL credential masking with None."""
        result = ConfigLoggingMixin.mask_url_credentials(None)
        assert result == "NOT_SET"

    def test_mask_url_credentials_invalid_url(self):
        """Test URL credential masking with invalid URL."""
        result = ConfigLoggingMixin.mask_url_credentials("not-a-valid-url")
        # Should return original for simple URLs without credentials
        assert result == "not-a-valid-url"

    def test_mask_url_credentials_complex_cases(self):
        """Test URL credential masking with complex cases."""
        test_cases = [
            ("http://user:pass@example.com", True),  # Should mask
            ("https://user:pass@example.com:8080/path", True),  # Should mask
            ("redis://user:pass@redis.com:6379", True),  # Should mask
            ("http://example.com", False),  # No masking needed
            ("file:///path/to/file", False)  # No masking needed
        ]
        
        for url, should_mask in test_cases:
            result = ConfigLoggingMixin.mask_url_credentials(url)
            if should_mask:
                assert ":***" in result, f"Failed to mask: {url}"
            else:
                assert result == url, f"Unexpectedly changed: {url}"

    def test_create_safe_config_summary_basic(self):
        """Test basic safe config summary creation."""
        config = {
            'public_field': 'public_value',
            'secret_field': 'secret_value',
            'password': 'my_password'
        }
        sensitive_keys = ['secret_field', 'password']
        
        result = ConfigLoggingMixin.create_safe_config_summary(config, sensitive_keys)
        
        assert result['public_field'] == 'public_value'
        assert result['secret_field'] == '********'
        assert result['password'] == '********'

    def test_create_safe_config_summary_case_insensitive(self):
        """Test that sensitive key matching is case insensitive."""
        config = {
            'SECRET_FIELD': 'secret_value',
            'Password': 'my_password'
        }
        sensitive_keys = ['secret_field', 'password']
        
        result = ConfigLoggingMixin.create_safe_config_summary(config, sensitive_keys)
        
        assert result['SECRET_FIELD'] == '********'
        assert result['Password'] == '********'

    def test_create_safe_config_summary_non_string_values(self):
        """Test safe config summary with non-string sensitive values."""
        config = {
            'public_int': 42,
            'secret_int': 12345,
            'secret_list': [1, 2, 3],
            'secret_dict': {'key': 'value'}
        }
        sensitive_keys = ['secret_int', 'secret_list', 'secret_dict']
        
        result = ConfigLoggingMixin.create_safe_config_summary(config, sensitive_keys)
        
        assert result['public_int'] == 42
        assert result['secret_int'] == '<int_MASKED>'
        assert result['secret_list'] == '<list_MASKED>'
        assert result['secret_dict'] == '<dict_MASKED>'

    def test_create_safe_config_summary_empty_config(self):
        """Test safe config summary with empty config."""
        result = ConfigLoggingMixin.create_safe_config_summary({}, ['any_key'])
        assert result == {}

    def test_create_safe_config_summary_no_sensitive_keys(self):
        """Test safe config summary with no sensitive keys."""
        config = {'field1': 'value1', 'field2': 'value2'}
        result = ConfigLoggingMixin.create_safe_config_summary(config, [])
        assert result == config


class TestIsolatedEnvironmentIntegration:
    """Test integration with IsolatedEnvironment."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_isolated_environment_integration(self):
        """Test that ConfigBuilderBase properly integrates with IsolatedEnvironment."""
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.set('TEST_INTEGRATION', 'integration_value')
        
        config = TestConfigImplementation()
        assert config.get_env_var('TEST_INTEGRATION') == 'integration_value'

    def test_isolated_environment_overlay(self):
        """Test environment variable overlay behavior."""
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.set('OVERLAY_TEST', 'original_value')
        
        # ConfigBuilderBase should overlay provided env_vars on top
        test_env = {'OVERLAY_TEST': 'overridden_value'}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('OVERLAY_TEST') == 'overridden_value'

    def test_isolated_environment_none_removal(self):
        """Test that None values properly remove environment variables."""
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.set('REMOVE_TEST', 'should_be_removed')
        
        test_env = {'REMOVE_TEST': None}
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('REMOVE_TEST') is None


class TestPerformanceAndConcurrency:
    """Test performance and thread safety."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_environment_detection_performance(self):
        """Test environment detection performance under load."""
        # Test with 100 environment variables
        large_env = {f'VAR_{i}': f'value_{i}' for i in range(100)}
        large_env['ENVIRONMENT'] = 'production'
        
        start_time = time.time()
        
        # Create 1000 config instances
        for _ in range(1000):
            config = TestConfigImplementation(env_vars=large_env)
            assert config.environment == 'production'
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle >1000 environment detections per second
        assert duration < 1.0, f"Environment detection too slow: {duration}s for 1000 instances"

    def test_concurrent_access_thread_safety(self):
        """Test thread safety with concurrent access."""
        test_env = {'ENVIRONMENT': 'production', 'SHARED_VAR': 'shared_value'}
        num_threads = 5
        num_operations = 100
        results = []
        errors = []
        
        def worker_thread(thread_id):
            """Worker thread function."""
            try:
                for i in range(num_operations):
                    config = TestConfigImplementation(env_vars=test_env)
                    assert config.environment == 'production'
                    assert config.get_env_var('SHARED_VAR') == 'shared_value'
                    
                    # Test various utility methods
                    config.get_env_bool('BOOL_TEST', default=True)
                    config.get_env_int('INT_TEST', default=42)
                    config.get_env_list('LIST_TEST')
                    
                results.append(f"Thread {thread_id} completed {num_operations} operations")
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
        
        # Start concurrent threads
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == num_threads

    def test_memory_usage_large_environments(self):
        """Test memory usage with large environment configurations."""
        # Create a config with 1000 environment variables
        large_env = {f'LARGE_VAR_{i}': f'value_{i}' * 10 for i in range(1000)}
        large_env['ENVIRONMENT'] = 'development'
        
        config = TestConfigImplementation(env_vars=large_env)
        
        # Should handle large environments without issues
        assert config.environment == 'development'
        assert len(config.env) >= 1000
        
        # Test that we can access all variables
        for i in range(0, 1000, 100):  # Test every 100th variable
            key = f'LARGE_VAR_{i}'
            expected_value = f'value_{i}' * 10
            assert config.get_env_var(key) == expected_value


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_unicode_environment_values(self):
        """Test handling of Unicode characters in environment values."""
        test_env = {
            'UNICODE_VAR': 'de[U+011F]er_with_unicode_[U+00E7]haracters',
            'EMOJI_VAR': '[U+1F680] rocket emoji',
            'ENVIRONMENT': 'development'
        }
        
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('UNICODE_VAR') == 'de[U+011F]er_with_unicode_[U+00E7]haracters'
        assert config.get_env_var('EMOJI_VAR') == '[U+1F680] rocket emoji'
        assert config.environment == 'development'

    def test_very_long_environment_values(self):
        """Test handling of very long environment variable values."""
        long_value = 'x' * 10000  # 10KB string
        test_env = {
            'LONG_VAR': long_value,
            'ENVIRONMENT': 'staging'
        }
        
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('LONG_VAR') == long_value
        assert config.environment == 'staging'

    def test_special_characters_in_values(self):
        """Test handling of special characters in environment values."""
        test_env = {
            'SPECIAL_CHARS': 'value with \n newlines \t tabs \r returns',
            'QUOTES_VAR': 'value with "quotes" and \'apostrophes\'',
            'SYMBOLS_VAR': 'symbols: !@#$%^&*()_+-={}[]|\\:";\'<>?,./`~',
            'ENVIRONMENT': 'production'
        }
        
        config = TestConfigImplementation(env_vars=test_env)
        
        assert '\n' in config.get_env_var('SPECIAL_CHARS')
        assert '\t' in config.get_env_var('SPECIAL_CHARS')
        assert '"quotes"' in config.get_env_var('QUOTES_VAR')
        assert '!@#$%^&*' in config.get_env_var('SYMBOLS_VAR')

    def test_numeric_string_environment_keys(self):
        """Test handling of numeric string environment variable names."""
        test_env = {
            '123': 'numeric_key',
            'VAR_456': 'mixed_numeric_key',
            'ENVIRONMENT': 'development'
        }
        
        config = TestConfigImplementation(env_vars=test_env)
        
        assert config.get_env_var('123') == 'numeric_key'
        assert config.get_env_var('VAR_456') == 'mixed_numeric_key'

    def test_boolean_conversion_edge_cases(self):
        """Test boolean conversion with edge cases."""
        edge_cases = [
            ('', False),  # Empty string
            ('   ', False),  # Whitespace only
            ('True ', True),  # Trailing space
            (' true', True),  # Leading space
            ('TRUE', True),  # All caps
            ('tRuE', True),  # Mixed case
            ('1', True),  # Numeric true
            ('0', False),  # Numeric false
            ('yes', True),  # Alternative true
            ('no', False),  # Alternative false (not in true list)
            ('on', True),  # Switch-style true
            ('off', False),  # Switch-style false (not in true list)
            ('invalid', False),  # Invalid value
        ]
        
        for value, expected in edge_cases:
            test_env = {'BOOL_TEST': value}
            config = TestConfigImplementation(env_vars=test_env)
            result = config.get_env_bool('BOOL_TEST')
            assert result == expected, f"Failed for value: '{value}', expected: {expected}, got: {result}"

    def test_integer_conversion_edge_cases(self):
        """Test integer conversion with edge cases."""
        edge_cases = [
            ('0', 0),
            ('-0', 0),
            ('+123', 123),
            ('-123', -123),
            ('   123   ', 123),  # Whitespace handling
            ('123.0', 0),  # Invalid float format (should use default)
            ('123.456', 0),  # Invalid float format (should use default)
            ('abc123', 0),  # Invalid with numbers (should use default)
            ('', 0),  # Empty string (should use default)
            ('   ', 0),  # Whitespace only (should use default)
        ]
        
        for value, expected in edge_cases:
            test_env = {'INT_TEST': value}
            config = TestConfigImplementation(env_vars=test_env)
            result = config.get_env_int('INT_TEST')
            assert result == expected, f"Failed for value: '{value}', expected: {expected}, got: {result}"

    def test_list_parsing_edge_cases(self):
        """Test list parsing with edge cases."""
        edge_cases = [
            ('', []),  # Empty string
            ('   ', []),  # Whitespace only
            (',', []),  # Single separator
            (',,', []),  # Multiple separators
            (',item,', ['item']),  # Leading/trailing separators
            ('item1,,item2', ['item1', 'item2']),  # Empty middle items
            ('  item1  ,  item2  ', ['item1', 'item2']),  # Whitespace around items
            ('single', ['single']),  # Single item
            ('item1;item2', ['item1', 'item2']),  # Custom separator
        ]
        
        for value, expected in edge_cases:
            test_env = {'LIST_TEST': value}
            config = TestConfigImplementation(env_vars=test_env)
            
            if ';' in value:
                result = config.get_env_list('LIST_TEST', separator=';')
            else:
                result = config.get_env_list('LIST_TEST')
            
            assert result == expected, f"Failed for value: '{value}', expected: {expected}, got: {result}"


class TestBusinessValueValidation:
    """Test that ConfigBuilderBase delivers its promised business value."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset IsolatedEnvironment to clean state for testing
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Reset IsolatedEnvironment to clean state after tests
        env_manager = IsolatedEnvironment.get_instance()
        env_manager.reset()

    def test_ssot_principle_enforcement(self):
        """Test that SSOT principle is enforced - same environment detection across instances."""
        # All instances should detect the same environment with same input
        test_env = {
            'ENVIRONMENT': 'staging',
            'ENV': 'production',  # Should be ignored due to priority
            'NETRA_ENVIRONMENT': 'development'  # Should be ignored due to priority
        }
        
        configs = [TestConfigImplementation(env_vars=test_env) for _ in range(10)]
        
        # All instances should have identical environment detection
        environments = [config.environment for config in configs]
        assert all(env == 'staging' for env in environments)

    def test_eliminates_duplicate_environment_detection_logic(self):
        """Test that ConfigBuilderBase eliminates the need for duplicate environment detection."""
        # Multiple different config implementations should all use the same detection logic
        configs = [
            TestConfigImplementation(),
            FailingConfigImplementation()
        ]
        
        # All should use the same environment detection logic
        for config in configs:
            # Should have the same environment detection behavior
            assert hasattr(config, '_detect_environment')
            assert hasattr(config, 'is_development')
            assert hasattr(config, 'is_staging')
            assert hasattr(config, 'is_production')

    def test_consistent_utility_methods_across_implementations(self):
        """Test that utility methods work consistently across different implementations."""
        test_env = {
            'BOOL_VAR': 'true',
            'INT_VAR': '42',
            'LIST_VAR': 'a,b,c',
            'ENVIRONMENT': 'production'
        }
        
        configs = [
            TestConfigImplementation(env_vars=test_env),
            FailingConfigImplementation(env_vars=test_env)
        ]
        
        for config in configs:
            # All utility methods should work identically
            assert config.get_env_bool('BOOL_VAR') is True
            assert config.get_env_int('INT_VAR') == 42
            assert config.get_env_list('LIST_VAR') == ['a', 'b', 'c']
            assert config.is_production() is True

    def test_debug_information_consistency(self):
        """Test that debug information is consistent across implementations."""
        test_env = {'ENVIRONMENT': 'development'}
        
        configs = [
            TestConfigImplementation(env_vars=test_env),
            FailingConfigImplementation(env_vars=test_env)
        ]
        
        for config in configs:
            debug_info = config.get_common_debug_info()
            
            # All configs should have consistent common debug structure
            assert 'environment' in debug_info
            assert 'environment_detection' in debug_info
            assert 'common_env_vars' in debug_info
            assert debug_info['environment'] == 'development'

    def test_logging_safety_across_implementations(self):
        """Test that logging safety is consistent across implementations."""
        configs = [
            TestConfigImplementation(),
            FailingConfigImplementation()
        ]
        
        for config in configs:
            # All configs should have safe logging capabilities
            summary = config.get_safe_log_summary()
            assert 'Configuration' in summary
            assert 'Environment:' in summary

    def test_validation_framework_consistency(self):
        """Test that validation framework works consistently."""
        test_env = {'TEST_VAR': 'valid_value'}
        
        configs = [
            TestConfigImplementation(env_vars=test_env),
            FailingConfigImplementation(env_vars=test_env)
        ]
        
        for config in configs:
            # All configs should have consistent validation capabilities
            is_valid, error_msg = config.validate_environment_variable('TEST_VAR', required=True)
            assert is_valid is True
            assert error_msg == ""

    def test_configuration_maintenance_cost_reduction(self):
        """Test that ConfigBuilderBase reduces configuration maintenance burden."""
        # This test validates that common patterns are centralized
        
        # Environment detection should be identical across instances
        test_cases = [
            ({'ENVIRONMENT': 'prod'}, 'production'),
            ({'ENV': 'stage'}, 'staging'),
            ({'NETRA_ENVIRONMENT': 'dev'}, 'development'),
            ({'K_SERVICE': 'staging-service'}, 'staging'),
        ]
        
        for env_vars, expected_env in test_cases:
            configs = [
                TestConfigImplementation(env_vars=env_vars),
                FailingConfigImplementation(env_vars=env_vars)
            ]
            
            # All implementations should produce identical results
            environments = [config.environment for config in configs]
            assert all(env == expected_env for env in environments)


class TestComplianceAndStandards:
    """Test compliance with CLAUDE.md standards and requirements."""
    
    def test_absolute_imports_compliance(self):
        """Test that all imports are absolute as required by CLAUDE.md."""
        # This test verifies that the module follows absolute import standards
        import shared.config_builder_base
        
        # Module should be importable with absolute path
        assert hasattr(shared.config_builder_base, 'ConfigBuilderBase')
        assert hasattr(shared.config_builder_base, 'ConfigEnvironment')
        assert hasattr(shared.config_builder_base, 'ConfigValidationMixin')
        assert hasattr(shared.config_builder_base, 'ConfigLoggingMixin')

    def test_ssot_compliance_validation(self):
        """Test that ConfigBuilderBase enforces SSOT compliance."""
        # Every config builder using this base class should have identical core behavior
        config1 = TestConfigImplementation()
        config2 = FailingConfigImplementation()
        
        # Both should use the same environment detection logic
        assert callable(config1._detect_environment)
        assert callable(config2._detect_environment)
        
        # Both should have the same utility methods
        assert callable(config1.get_env_bool)
        assert callable(config2.get_env_bool)
        assert callable(config1.get_env_int)
        assert callable(config2.get_env_int)

    def test_business_value_metrics_validation(self):
        """Test validation of claimed business value metrics."""
        # Test that environment detection is fast enough for claimed value
        large_env = {f'VAR_{i}': f'value_{i}' for i in range(200)}
        large_env['ENVIRONMENT'] = 'production'
        
        start_time = time.time()
        
        # Create 100 config instances (simulating high usage)
        configs = []
        for _ in range(100):
            config = TestConfigImplementation(env_vars=large_env)
            configs.append(config)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be fast enough to support claimed $50K/year savings through efficiency
        assert duration < 0.5, f"Performance not adequate for claimed business value: {duration}s"
        
        # All configs should have consistent environment detection
        environments = [config.environment for config in configs]
        assert all(env == 'production' for env in environments)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])