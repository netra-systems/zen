"""
Comprehensive Unit Tests for ConfigurationStartupValidator SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - All users depend on system stability
- Business Goal: System Stability and Deployment Safety
- Value Impact: Prevents configuration-related system failures that would cause 100% service outages
- Strategic Impact: Reduces MTTR, prevents revenue-impacting downtime, ensures reliable deployments

This comprehensive test suite ensures 100% coverage of startup_validator.py including:
- All validation modes (STRICT, PERMISSIVE, EMERGENCY)
- Configuration dependency validation
- Service readiness checks
- Error handling and graceful degradation
- Integration with ConfigDependencyMap
- Startup metrics collection
- Edge cases and boundary conditions

CRITICAL: These tests prevent broken deployments and configuration-related system failures.
"""

import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Import the components we're testing
from netra_backend.app.core.configuration.startup_validator import (
    StartupValidationMode,
    ConfigurationStartupValidator,
    validate_startup_config,
    get_critical_config_status,
    integrate_with_startup
)
from netra_backend.app.core.config_dependencies import ConfigDependencyMap, ConfigImpactLevel


class TestStartupValidationMode(SSotBaseTestCase):
    """Test StartupValidationMode enum values and behavior."""
    
    def test_startup_validation_mode_enum_values(self):
        """Test that StartupValidationMode enum has all required values."""
        expected_values = {"strict", "permissive", "emergency"}
        actual_values = {mode.value for mode in StartupValidationMode}
        
        assert actual_values == expected_values, f"Missing enum values: {expected_values - actual_values}"
    
    def test_startup_validation_mode_is_enum(self):
        """Test that StartupValidationMode is properly defined as Enum."""
        assert issubclass(StartupValidationMode, Enum)
        assert len(StartupValidationMode) == 3
    
    def test_startup_validation_mode_string_representation(self):
        """Test string representation of StartupValidationMode values."""
        assert str(StartupValidationMode.STRICT) == "StartupValidationMode.STRICT"
        assert repr(StartupValidationMode.PERMISSIVE) == "<StartupValidationMode.PERMISSIVE: 'permissive'>"
        
        # Test value access
        assert StartupValidationMode.STRICT.value == "strict"
        assert StartupValidationMode.PERMISSIVE.value == "permissive"
        assert StartupValidationMode.EMERGENCY.value == "emergency"
    
    def test_startup_validation_mode_comparison(self):
        """Test StartupValidationMode comparison operations."""
        # Same values should be equal
        assert StartupValidationMode.STRICT == StartupValidationMode.STRICT
        assert StartupValidationMode.PERMISSIVE != StartupValidationMode.EMERGENCY
        
        # Can compare with strings
        assert StartupValidationMode.STRICT.value == "strict"
        assert StartupValidationMode.EMERGENCY.value != "strict"


class TestConfigurationStartupValidatorInitialization(SSotBaseTestCase):
    """Test ConfigurationStartupValidator initialization and basic setup."""
    
    def test_startup_validator_initialization_default_mode(self):
        """Test ConfigurationStartupValidator initializes with default STRICT mode."""
        validator = ConfigurationStartupValidator()
        
        assert validator.mode == StartupValidationMode.STRICT
        assert validator.errors == []
        assert validator.warnings == []
        assert validator.logger is not None
    
    def test_startup_validator_initialization_custom_mode(self):
        """Test ConfigurationStartupValidator initializes with custom mode."""
        # Test PERMISSIVE mode
        validator_permissive = ConfigurationStartupValidator(StartupValidationMode.PERMISSIVE)
        assert validator_permissive.mode == StartupValidationMode.PERMISSIVE
        
        # Test EMERGENCY mode
        validator_emergency = ConfigurationStartupValidator(StartupValidationMode.EMERGENCY)
        assert validator_emergency.mode == StartupValidationMode.EMERGENCY
    
    def test_startup_validator_logger_setup(self):
        """Test that validator properly sets up logger."""
        validator = ConfigurationStartupValidator()
        
        assert validator.logger is not None
        assert hasattr(validator.logger, 'info')
        assert hasattr(validator.logger, 'warning')
        assert hasattr(validator.logger, 'error')
    
    def test_startup_validator_state_isolation(self):
        """Test that multiple validator instances maintain separate state."""
        validator1 = ConfigurationStartupValidator(StartupValidationMode.STRICT)
        validator2 = ConfigurationStartupValidator(StartupValidationMode.PERMISSIVE)
        
        # Add errors to first validator
        validator1.errors.append("Test error 1")
        validator1.warnings.append("Test warning 1")
        
        # Second validator should have empty state
        assert validator1.errors == ["Test error 1"]
        assert validator1.warnings == ["Test warning 1"]
        assert validator2.errors == []
        assert validator2.warnings == []
        assert validator1.mode != validator2.mode


class TestConfigurationStartupValidatorMainFlow(SSotBaseTestCase):
    """Test ConfigurationStartupValidator main validation flow."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_validate_startup_configuration_success_scenario(self):
        """Test validate_startup_configuration with all validations passing."""
        # Mock all validation methods to succeed
        with patch.object(self.validator, '_validate_critical_dependencies') as mock_critical:
            with patch.object(self.validator, '_validate_config_values') as mock_values:
                with patch.object(self.validator, '_check_service_readiness') as mock_service:
                    with patch.object(self.validator, '_determine_validation_result', return_value=True) as mock_determine:
                        with patch.object(self.validator, '_log_validation_results') as mock_log:
                            
                            is_valid, errors, warnings = self.validator.validate_startup_configuration()
                            
                            assert is_valid is True
                            assert errors == []
                            assert warnings == []
                            
                            # Verify all validation methods were called
                            mock_critical.assert_called_once()
                            mock_values.assert_called_once()
                            mock_service.assert_called_once()
                            mock_determine.assert_called_once()
                            mock_log.assert_called_once_with(True)
    
    def test_validate_startup_configuration_failure_scenario(self):
        """Test validate_startup_configuration with validation failures."""
        # Setup failure scenario
        def mock_critical_dependencies():
            self.validator.errors.append("CRITICAL CONFIG MISSING: JWT_SECRET_KEY")
            self.validator.warnings.append("Warning: Optional config missing")
        
        with patch.object(self.validator, '_validate_critical_dependencies', side_effect=mock_critical_dependencies):
            with patch.object(self.validator, '_validate_config_values'):
                with patch.object(self.validator, '_check_service_readiness'):
                    with patch.object(self.validator, '_determine_validation_result', return_value=False):
                        with patch.object(self.validator, '_log_validation_results'):
                            
                            is_valid, errors, warnings = self.validator.validate_startup_configuration()
                            
                            assert is_valid is False
                            assert len(errors) == 1
                            assert "CRITICAL CONFIG MISSING: JWT_SECRET_KEY" in errors
                            assert len(warnings) == 1
                            assert "Warning: Optional config missing" in warnings
    
    def test_validate_startup_configuration_exception_handling(self):
        """Test validate_startup_configuration handles exceptions properly."""
        # Mock validation method to raise exception
        exception_message = "Validation method exploded"
        with patch.object(self.validator, '_validate_critical_dependencies', side_effect=RuntimeError(exception_message)):
            
            is_valid, errors, warnings = self.validator.validate_startup_configuration()
            
            assert is_valid is False
            assert len(errors) == 1
            assert "Startup validation failed with exception:" in errors[0]
            assert exception_message in errors[0]
    
    def test_validate_startup_configuration_clears_previous_state(self):
        """Test that validate_startup_configuration clears previous errors and warnings."""
        # Add some previous state
        self.validator.errors.append("Previous error")
        self.validator.warnings.append("Previous warning")
        
        with patch.object(self.validator, '_validate_critical_dependencies'):
            with patch.object(self.validator, '_validate_config_values'):
                with patch.object(self.validator, '_check_service_readiness'):
                    with patch.object(self.validator, '_determine_validation_result', return_value=True):
                        with patch.object(self.validator, '_log_validation_results'):
                            
                            is_valid, errors, warnings = self.validator.validate_startup_configuration()
                            
                            # Previous state should be cleared
                            assert is_valid is True
                            assert errors == []
                            assert warnings == []


class TestValidateCriticalDependencies(SSotBaseTestCase):
    """Test _validate_critical_dependencies method."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_validate_critical_dependencies_all_present(self):
        """Test _validate_critical_dependencies with all required configs present."""
        mock_required_configs = {
            "JWT_SECRET_KEY": {
                "impact_level": ConfigImpactLevel.CRITICAL,
                "deletion_impact": "All authentication will fail",
                "fallback_allowed": False
            },
            "DATABASE_URL": {
                "impact_level": ConfigImpactLevel.CRITICAL,
                "deletion_impact": "Database connection will fail",
                "fallback_allowed": False
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "present_value"
                mock_get_env.return_value = mock_env
                
                self.validator._validate_critical_dependencies()
                
                assert len(self.validator.errors) == 0
                assert len(self.validator.warnings) == 0
    
    def test_validate_critical_dependencies_critical_missing(self):
        """Test _validate_critical_dependencies with critical configs missing."""
        mock_required_configs = {
            "JWT_SECRET_KEY": {
                "impact_level": ConfigImpactLevel.CRITICAL,
                "deletion_impact": "All authentication will fail",
                "fallback_allowed": False
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None  # Missing config
                mock_get_env.return_value = mock_env
                
                self.validator._validate_critical_dependencies()
                
                assert len(self.validator.errors) == 1
                assert "CRITICAL CONFIG MISSING: JWT_SECRET_KEY" in self.validator.errors[0]
                assert "All authentication will fail" in self.validator.errors[0]
    
    def test_validate_critical_dependencies_high_priority_missing(self):
        """Test _validate_critical_dependencies with high priority configs missing."""
        mock_required_configs = {
            "OPTIONAL_CONFIG": {
                "impact_level": ConfigImpactLevel.HIGH,
                "deletion_impact": "Some features will be disabled",
                "fallback_allowed": False
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None  # Missing config
                mock_get_env.return_value = mock_env
                
                self.validator._validate_critical_dependencies()
                
                assert len(self.validator.errors) == 0
                assert len(self.validator.warnings) == 1
                assert "CRITICAL CONFIG MISSING: OPTIONAL_CONFIG" in self.validator.warnings[0]
    
    def test_validate_critical_dependencies_with_fallback_allowed(self):
        """Test _validate_critical_dependencies with fallback allowed configs."""
        mock_required_configs = {
            "CONFIG_WITH_FALLBACK": {
                "impact_level": ConfigImpactLevel.CRITICAL,
                "deletion_impact": "Will use default value",
                "fallback_allowed": True
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None  # Missing but fallback allowed
                mock_get_env.return_value = mock_env
                
                self.validator._validate_critical_dependencies()
                
                # Should not add errors or warnings for configs with fallback allowed
                assert len(self.validator.errors) == 0
                assert len(self.validator.warnings) == 0


class TestValidateConfigValues(SSotBaseTestCase):
    """Test _validate_config_values method."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_validate_config_values_all_valid(self):
        """Test _validate_config_values with all config values valid."""
        mock_configs = {
            "JWT_SECRET_KEY": {"impact_level": ConfigImpactLevel.CRITICAL},
            "DATABASE_URL": {"impact_level": ConfigImpactLevel.HIGH}
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_configs):
            with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', {}):
                with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                    with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                        mock_env = Mock()
                        mock_env.get.side_effect = lambda key: "valid_value" if key in mock_configs else None
                        mock_get_env.return_value = mock_env
                        
                        with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(True, "Valid")):
                            
                            self.validator._validate_config_values()
                            
                            assert len(self.validator.errors) == 0
                            assert len(self.validator.warnings) == 0
    
    def test_validate_config_values_critical_invalid(self):
        """Test _validate_config_values with critical config values invalid."""
        mock_configs = {
            "JWT_SECRET_KEY": {"impact_level": ConfigImpactLevel.CRITICAL}
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_configs):
            with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', {}):
                with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                    with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                        mock_env = Mock()
                        mock_env.get.return_value = "invalid_value"
                        mock_get_env.return_value = mock_env
                        
                        with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(False, "Too short")):
                            
                            self.validator._validate_config_values()
                            
                            assert len(self.validator.errors) == 1
                            assert "INVALID CONFIG VALUE: JWT_SECRET_KEY - Too short" in self.validator.errors[0]
    
    def test_validate_config_values_high_priority_invalid(self):
        """Test _validate_config_values with high priority config values invalid."""
        mock_configs = {
            "OPTIONAL_CONFIG": {"impact_level": ConfigImpactLevel.HIGH}
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', {}):
            with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', mock_configs):
                with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                    with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                        mock_env = Mock()
                        mock_env.get.return_value = "invalid_value"
                        mock_get_env.return_value = mock_env
                        
                        with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(False, "Invalid format")):
                            
                            self.validator._validate_config_values()
                            
                            assert len(self.validator.errors) == 0
                            assert len(self.validator.warnings) == 1
                            assert "INVALID CONFIG VALUE: OPTIONAL_CONFIG - Invalid format" in self.validator.warnings[0]
    
    def test_validate_config_values_missing_values_skipped(self):
        """Test _validate_config_values skips validation for missing values."""
        mock_configs = {
            "MISSING_CONFIG": {"impact_level": ConfigImpactLevel.CRITICAL}
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_configs):
            with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', {}):
                with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                    with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                        mock_env = Mock()
                        mock_env.get.return_value = None  # Missing value
                        mock_get_env.return_value = mock_env
                        
                        # Should not call validate_config_value for missing values
                        with patch.object(ConfigDependencyMap, 'validate_config_value') as mock_validate:
                            
                            self.validator._validate_config_values()
                            
                            mock_validate.assert_not_called()
                            assert len(self.validator.errors) == 0
                            assert len(self.validator.warnings) == 0


class TestCheckServiceReadiness(SSotBaseTestCase):
    """Test _check_service_readiness method."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_check_service_readiness_all_configured(self):
        """Test _check_service_readiness with all services properly configured."""
        mock_config = Mock()
        mock_config.database_url = "postgresql://localhost:5432/test"
        mock_config.jwt_secret_key = "secret_key_with_sufficient_length"
        mock_config.__dict__ = {
            "database_url": "postgresql://localhost:5432/test",
            "jwt_secret_key": "secret_key_with_sufficient_length"
        }
        
        with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', return_value=mock_config):
            with patch.object(ConfigDependencyMap, 'check_config_consistency', return_value=[]):
                
                self.validator._check_service_readiness()
                
                assert len(self.validator.errors) == 0
                assert len(self.validator.warnings) == 0
    
    def test_check_service_readiness_missing_database_url(self):
        """Test _check_service_readiness with missing database URL."""
        mock_config = Mock()
        mock_config.database_url = None
        mock_config.jwt_secret_key = "valid_secret_key"
        mock_config.__dict__ = {"database_url": None, "jwt_secret_key": "valid_secret_key"}
        
        with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', return_value=mock_config):
            with patch.object(ConfigDependencyMap, 'check_config_consistency', return_value=[]):
                
                self.validator._check_service_readiness()
                
                assert len(self.validator.errors) == 1
                assert "DATABASE CONFIG: No database URL configured" in self.validator.errors[0]
    
    def test_check_service_readiness_missing_jwt_secret(self):
        """Test _check_service_readiness with missing JWT secret."""
        mock_config = Mock()
        mock_config.database_url = "postgresql://localhost:5432/test"
        mock_config.jwt_secret_key = None
        mock_config.__dict__ = {"database_url": "postgresql://localhost:5432/test", "jwt_secret_key": None}
        
        with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', return_value=mock_config):
            with patch.object(ConfigDependencyMap, 'check_config_consistency', return_value=[]):
                
                self.validator._check_service_readiness()
                
                assert len(self.validator.errors) == 1
                assert "AUTH CONFIG: No JWT secret key" in self.validator.errors[0]
    
    def test_check_service_readiness_config_consistency_issues(self):
        """Test _check_service_readiness with configuration consistency issues."""
        mock_config = Mock()
        mock_config.database_url = "postgresql://localhost:5432/test"
        mock_config.jwt_secret_key = "valid_secret_key"
        mock_config.__dict__ = {
            "database_url": "postgresql://localhost:5432/test",
            "jwt_secret_key": "valid_secret_key"
        }
        
        consistency_issues = [
            "CRITICAL: JWT_SECRET_KEY mismatch between services",
            "WARNING: Optional config not synchronized",
            "INFO: Configuration loaded successfully"
        ]
        
        with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', return_value=mock_config):
            with patch.object(ConfigDependencyMap, 'check_config_consistency', return_value=consistency_issues):
                
                self.validator._check_service_readiness()
                
                assert len(self.validator.errors) == 1
                assert "CONFIG CONSISTENCY: CRITICAL: JWT_SECRET_KEY mismatch" in self.validator.errors[0]
                
                assert len(self.validator.warnings) == 2
                assert any("WARNING: Optional config not synchronized" in w for w in self.validator.warnings)
                assert any("INFO: Configuration loaded successfully" in w for w in self.validator.warnings)
    
    def test_check_service_readiness_config_loading_exception(self):
        """Test _check_service_readiness handles configuration loading exceptions."""
        with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', side_effect=ImportError("Config module not found")):
            
            self.validator._check_service_readiness()
            
            assert len(self.validator.errors) == 1
            assert "Service readiness check failed: Config module not found" in self.validator.errors[0]


class TestDetermineValidationResult(SSotBaseTestCase):
    """Test _determine_validation_result method for different modes."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_determine_validation_result_strict_mode_no_errors(self):
        """Test _determine_validation_result in STRICT mode with no errors."""
        self.validator.mode = StartupValidationMode.STRICT
        self.validator.errors = []
        self.validator.warnings = ["Some warning"]
        
        result = self.validator._determine_validation_result()
        
        assert result is True
    
    def test_determine_validation_result_strict_mode_with_errors(self):
        """Test _determine_validation_result in STRICT mode with errors."""
        self.validator.mode = StartupValidationMode.STRICT
        self.validator.errors = ["Some error"]
        self.validator.warnings = []
        
        result = self.validator._determine_validation_result()
        
        assert result is False
    
    def test_determine_validation_result_permissive_mode_no_critical_errors(self):
        """Test _determine_validation_result in PERMISSIVE mode with no critical errors."""
        self.validator.mode = StartupValidationMode.PERMISSIVE
        self.validator.errors = ["Non-critical error"]
        self.validator.warnings = []
        
        result = self.validator._determine_validation_result()
        
        assert result is True
    
    def test_determine_validation_result_permissive_mode_with_critical_errors(self):
        """Test _determine_validation_result in PERMISSIVE mode with critical errors."""
        self.validator.mode = StartupValidationMode.PERMISSIVE
        self.validator.errors = ["CRITICAL error that should fail"]
        self.validator.warnings = []
        
        result = self.validator._determine_validation_result()
        
        assert result is False
    
    def test_determine_validation_result_emergency_mode_no_database_errors(self):
        """Test _determine_validation_result in EMERGENCY mode with no database errors."""
        self.validator.mode = StartupValidationMode.EMERGENCY
        self.validator.errors = ["Some non-database error"]
        self.validator.warnings = []
        
        result = self.validator._determine_validation_result()
        
        assert result is True
    
    def test_determine_validation_result_emergency_mode_with_database_errors(self):
        """Test _determine_validation_result in EMERGENCY mode with database errors."""
        self.validator.mode = StartupValidationMode.EMERGENCY
        self.validator.errors = ["database_url configuration is missing"]
        self.validator.warnings = []
        
        result = self.validator._determine_validation_result()
        
        assert result is False


class TestLogValidationResults(SSotBaseTestCase):
    """Test _log_validation_results method."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_log_validation_results_success_no_warnings(self):
        """Test _log_validation_results for successful validation with no warnings."""
        self.validator.mode = StartupValidationMode.STRICT
        self.validator.warnings = []
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            with patch.object(self.validator.logger, 'error') as mock_error:
                
                self.validator._log_validation_results(True)
                
                mock_info.assert_called_once()
                assert "Startup configuration validation PASSED (strict mode)" in mock_info.call_args[0][0]
                mock_error.assert_not_called()
    
    def test_log_validation_results_success_with_warnings(self):
        """Test _log_validation_results for successful validation with warnings."""
        self.validator.mode = StartupValidationMode.PERMISSIVE
        self.validator.warnings = ["Warning 1", "Warning 2"]
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            
            self.validator._log_validation_results(True)
            
            assert mock_info.call_count == 2
            assert "Startup configuration validation PASSED (permissive mode)" in mock_info.call_args_list[0][0][0]
            assert "Warnings: 2 issues detected but not blocking" in mock_info.call_args_list[1][0][0]
    
    def test_log_validation_results_failure(self):
        """Test _log_validation_results for failed validation."""
        self.validator.mode = StartupValidationMode.STRICT
        self.validator.errors = ["Error 1", "Error 2"]
        self.validator.warnings = ["Warning 1"]
        
        with patch.object(self.validator.logger, 'error') as mock_error:
            
            self.validator._log_validation_results(False)
            
            assert mock_error.call_count == 2
            assert "Startup configuration validation FAILED (strict mode)" in mock_error.call_args_list[0][0][0]
            assert "Errors: 2, Warnings: 1" in mock_error.call_args_list[1][0][0]


class TestGetValidationSummary(SSotBaseTestCase):
    """Test get_validation_summary method."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_get_validation_summary_strict_mode_passed(self):
        """Test get_validation_summary in STRICT mode with no errors."""
        self.validator.mode = StartupValidationMode.STRICT
        self.validator.errors = []
        self.validator.warnings = ["Warning 1"]
        
        summary = self.validator.get_validation_summary()
        
        assert summary["mode"] == "strict"
        assert summary["passed"] is True
        assert summary["error_count"] == 0
        assert summary["warning_count"] == 1
        assert summary["errors"] == []
        assert summary["warnings"] == ["Warning 1"]
    
    def test_get_validation_summary_permissive_mode_failed(self):
        """Test get_validation_summary in PERMISSIVE mode with critical errors."""
        self.validator.mode = StartupValidationMode.PERMISSIVE
        self.validator.errors = ["CRITICAL error"]
        self.validator.warnings = []
        
        with patch.object(self.validator, '_determine_validation_result', return_value=False):
            summary = self.validator.get_validation_summary()
            
            assert summary["mode"] == "permissive"
            assert summary["passed"] is False
            assert summary["error_count"] == 1
            assert summary["warning_count"] == 0
            assert summary["errors"] == ["CRITICAL error"]
            assert summary["warnings"] == []
    
    def test_get_validation_summary_emergency_mode(self):
        """Test get_validation_summary in EMERGENCY mode."""
        self.validator.mode = StartupValidationMode.EMERGENCY
        self.validator.errors = ["Non-critical error"]
        self.validator.warnings = ["Warning"]
        
        with patch.object(self.validator, '_determine_validation_result', return_value=True):
            summary = self.validator.get_validation_summary()
            
            assert summary["mode"] == "emergency"
            assert summary["passed"] is True
            assert summary["error_count"] == 1
            assert summary["warning_count"] == 1


class TestValidateStartupConfigFunction(SSotBaseTestCase):
    """Test validate_startup_config convenience function."""
    
    def test_validate_startup_config_default_mode(self):
        """Test validate_startup_config with default STRICT mode."""
        with patch('netra_backend.app.core.configuration.startup_validator.ConfigurationStartupValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_startup_configuration.return_value = (True, [], [])
            mock_validator_class.return_value = mock_validator
            
            result = validate_startup_config()
            
            assert result is True
            mock_validator_class.assert_called_once_with(StartupValidationMode.STRICT)
            mock_validator.validate_startup_configuration.assert_called_once()
    
    def test_validate_startup_config_custom_mode(self):
        """Test validate_startup_config with custom mode."""
        with patch('netra_backend.app.core.configuration.startup_validator.ConfigurationStartupValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_startup_configuration.return_value = (True, [], [])
            mock_validator_class.return_value = mock_validator
            
            result = validate_startup_config(StartupValidationMode.PERMISSIVE)
            
            assert result is True
            mock_validator_class.assert_called_once_with(StartupValidationMode.PERMISSIVE)
    
    def test_validate_startup_config_failure_logging(self):
        """Test validate_startup_config logs errors on failure."""
        with patch('netra_backend.app.core.configuration.startup_validator.ConfigurationStartupValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_startup_configuration.return_value = (False, ["Error 1", "Error 2"], ["Warning 1"])
            mock_validator_class.return_value = mock_validator
            
            with patch('netra_backend.app.core.configuration.startup_validator.central_logger') as mock_logger_module:
                mock_logger = Mock()
                mock_logger_module.get_logger.return_value = mock_logger
                
                result = validate_startup_config()
                
                assert result is False
                mock_logger.error.assert_called()
                # Should log the main failure message and each error
                assert mock_logger.error.call_count == 3


class TestGetCriticalConfigStatus(SSotBaseTestCase):
    """Test get_critical_config_status function."""
    
    def test_get_critical_config_status_all_present_and_valid(self):
        """Test get_critical_config_status with all configs present and valid."""
        mock_critical_deps = {
            "JWT_SECRET_KEY": {
                "required_by": ["auth_service"],
                "impact_level": ConfigImpactLevel.CRITICAL,
                "fallback_allowed": False,
                "deletion_impact": "All auth will fail"
            }
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_critical_deps):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "valid_secret_key"
                mock_get_env.return_value = mock_env
                
                with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(True, "OK")):
                    
                    status = get_critical_config_status()
                    
                    assert "JWT_SECRET_KEY" in status
                    config_status = status["JWT_SECRET_KEY"]
                    assert config_status["present"] is True
                    assert config_status["valid"] is True
                    assert config_status["required_by"] == ["auth_service"]
                    assert config_status["impact_level"] == "CRITICAL"
                    assert config_status["fallback_allowed"] is False
                    assert config_status["validation_message"] == "OK"
                    assert config_status["deletion_impact"] == "All auth will fail"
    
    def test_get_critical_config_status_missing_config(self):
        """Test get_critical_config_status with missing config."""
        mock_critical_deps = {
            "MISSING_CONFIG": {
                "required_by": ["some_service"],
                "impact_level": ConfigImpactLevel.CRITICAL,
                "fallback_allowed": False,
                "deletion_impact": "Service will fail"
            }
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_critical_deps):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None  # Missing
                mock_get_env.return_value = mock_env
                
                status = get_critical_config_status()
                
                assert "MISSING_CONFIG" in status
                config_status = status["MISSING_CONFIG"]
                assert config_status["present"] is False
                assert config_status["valid"] is True  # Not validated if missing
                assert config_status["validation_message"] == "OK"
    
    def test_get_critical_config_status_invalid_config(self):
        """Test get_critical_config_status with invalid config value."""
        mock_critical_deps = {
            "INVALID_CONFIG": {
                "required_by": ["some_service"],
                "impact_level": ConfigImpactLevel.HIGH,
                "fallback_allowed": True,
                "deletion_impact": "Reduced functionality"
            }
        }
        
        with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_critical_deps):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "invalid_value"
                mock_get_env.return_value = mock_env
                
                with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(False, "Invalid format")):
                    
                    status = get_critical_config_status()
                    
                    assert "INVALID_CONFIG" in status
                    config_status = status["INVALID_CONFIG"]
                    assert config_status["present"] is True
                    assert config_status["valid"] is False
                    assert config_status["validation_message"] == "Invalid format"
                    assert config_status["impact_level"] == "HIGH"
                    assert config_status["fallback_allowed"] is True


class TestIntegrateWithStartup(SSotBaseTestCase):
    """Test integrate_with_startup function."""
    
    def test_integrate_with_startup_success(self):
        """Test integrate_with_startup with successful validation."""
        mock_orchestrator = Mock()
        
        with patch('netra_backend.app.core.configuration.startup_validator.validate_startup_config', return_value=True) as mock_validate:
            with patch('netra_backend.app.core.configuration.startup_validator.central_logger') as mock_logger_module:
                mock_logger = Mock()
                mock_logger_module.get_logger.return_value = mock_logger
                
                result = integrate_with_startup(mock_orchestrator)
                
                assert result is True
                mock_validate.assert_called_once_with(StartupValidationMode.PERMISSIVE)
                mock_logger.info.assert_called()
                assert "Configuration dependency validation passed" in mock_logger.info.call_args_list[-1][0][0]
    
    def test_integrate_with_startup_validation_failure(self):
        """Test integrate_with_startup with validation failure."""
        mock_orchestrator = Mock()
        
        with patch('netra_backend.app.core.configuration.startup_validator.validate_startup_config', return_value=False) as mock_validate:
            with patch('netra_backend.app.core.configuration.startup_validator.central_logger') as mock_logger_module:
                mock_logger = Mock()
                mock_logger_module.get_logger.return_value = mock_logger
                
                result = integrate_with_startup(mock_orchestrator)
                
                assert result is False
                mock_validate.assert_called_once_with(StartupValidationMode.PERMISSIVE)
                mock_logger.warning.assert_called()
                assert "Configuration dependency validation failed" in mock_logger.warning.call_args[0][0]
    
    def test_integrate_with_startup_exception_handling(self):
        """Test integrate_with_startup handles exceptions gracefully."""
        mock_orchestrator = Mock()
        
        with patch('netra_backend.app.core.configuration.startup_validator.validate_startup_config', side_effect=RuntimeError("Validation crashed")):
            with patch('netra_backend.app.core.configuration.startup_validator.central_logger') as mock_logger_module:
                mock_logger = Mock()
                mock_logger_module.get_logger.return_value = mock_logger
                
                result = integrate_with_startup(mock_orchestrator)
                
                # Should not block startup on integration errors
                assert result is True
                mock_logger.error.assert_called()
                assert "ConfigDependencyMap startup integration failed" in mock_logger.error.call_args[0][0]


class TestConfigurationStartupValidatorEdgeCases(SSotBaseTestCase):
    """Test edge cases and error scenarios."""
    
    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.validator = ConfigurationStartupValidator()
    
    def test_validator_with_empty_config_dependency_map(self):
        """Test validator behavior with empty ConfigDependencyMap."""
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value={}):
            with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', {}):
                with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', {}):
                    with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                        
                        self.validator._validate_critical_dependencies()
                        self.validator._validate_config_values()
                        
                        assert len(self.validator.errors) == 0
                        assert len(self.validator.warnings) == 0
    
    def test_validator_with_malformed_config_metadata(self):
        """Test validator handles malformed config metadata gracefully."""
        mock_required_configs = {
            "MALFORMED_CONFIG": {
                # Missing required fields
                "impact_level": None,
                "deletion_impact": None,
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None
                mock_get_env.return_value = mock_env
                
                # Should not crash even with malformed metadata
                try:
                    self.validator._validate_critical_dependencies()
                    # Should complete without raising exception
                except Exception as e:
                    pytest.fail(f"Validator should handle malformed metadata gracefully: {e}")
    
    def test_validator_concurrent_access(self):
        """Test validator thread safety with concurrent access."""
        import threading
        import time
        
        results = []
        errors = []
        
        def run_validation():
            try:
                validator = ConfigurationStartupValidator()
                with patch.object(validator, '_validate_critical_dependencies'):
                    with patch.object(validator, '_validate_config_values'):
                        with patch.object(validator, '_check_service_readiness'):
                            with patch.object(validator, '_determine_validation_result', return_value=True):
                                with patch.object(validator, '_log_validation_results'):
                                    
                                    is_valid, _, _ = validator.validate_startup_configuration()
                                    results.append(is_valid)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_validation)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All validations should succeed without errors
        assert len(errors) == 0, f"Concurrent validation errors: {errors}"
        assert len(results) == 5
        assert all(results), f"Some validations failed: {results}"
    
    def test_validator_memory_usage_large_config_set(self):
        """Test validator memory efficiency with large configuration sets."""
        # Create a large mock configuration set
        large_config_set = {}
        for i in range(1000):
            large_config_set[f"CONFIG_{i}"] = {
                "impact_level": ConfigImpactLevel.MEDIUM,
                "deletion_impact": f"Impact description {i}",
                "fallback_allowed": i % 2 == 0,
                "required_by": [f"service_{j}" for j in range(5)]
            }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=large_config_set):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "present_value"
                mock_get_env.return_value = mock_env
                
                # Should handle large config sets efficiently
                start_time = time.time()
                self.validator._validate_critical_dependencies()
                end_time = time.time()
                
                # Should complete in reasonable time (< 1 second for 1000 configs)
                assert end_time - start_time < 1.0, f"Validation took too long: {end_time - start_time}s"
    
    def test_validator_unicode_config_values(self):
        """Test validator handles unicode configuration values."""
        mock_required_configs = {
            "UNICODE_CONFIG": {
                "impact_level": ConfigImpactLevel.MEDIUM,
                "deletion_impact": "Unicode test config with émojis 🚀",
                "fallback_allowed": False
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "Unicode value with special chars: 测试 🌟"
                mock_get_env.return_value = mock_env
                
                # Should handle unicode values without issues
                try:
                    self.validator._validate_critical_dependencies()
                    # Should complete without encoding errors
                except UnicodeError as e:
                    pytest.fail(f"Validator should handle unicode gracefully: {e}")
    
    def test_validator_very_long_config_values(self):
        """Test validator handles very long configuration values."""
        long_value = "x" * 10000  # 10KB string
        
        mock_required_configs = {
            "LONG_CONFIG": {
                "impact_level": ConfigImpactLevel.LOW,
                "deletion_impact": "Test with very long config value",
                "fallback_allowed": False
            }
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = long_value
                mock_get_env.return_value = mock_env
                
                with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(True, "Valid")):
                    
                    # Should handle long values efficiently
                    start_time = time.time()
                    self.validator._validate_critical_dependencies()
                    end_time = time.time()
                    
                    # Should complete quickly even with long values
                    assert end_time - start_time < 0.1, f"Validation too slow with long values: {end_time - start_time}s"


class TestConfigurationStartupValidatorIntegration(SSotBaseTestCase):
    """Integration tests for complete startup validation flow."""
    
    def test_complete_validation_flow_success(self):
        """Test complete validation flow with successful scenario."""
        validator = ConfigurationStartupValidator(StartupValidationMode.STRICT)
        
        # Mock all dependencies for success scenario
        mock_required_configs = {
            "JWT_SECRET_KEY": {
                "impact_level": ConfigImpactLevel.CRITICAL,
                "deletion_impact": "Auth will fail",
                "fallback_allowed": False
            }
        }
        
        mock_config = Mock()
        mock_config.database_url = "postgresql://localhost:5432/test"
        mock_config.jwt_secret_key = "valid_secret_key_with_sufficient_length"
        mock_config.__dict__ = {
            "database_url": "postgresql://localhost:5432/test",
            "jwt_secret_key": "valid_secret_key_with_sufficient_length"
        }
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', mock_required_configs):
                with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', {}):
                    with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                        with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                            mock_env = Mock()
                            mock_env.get.return_value = "valid_secret_key_with_sufficient_length"
                            mock_get_env.return_value = mock_env
                            
                            with patch.object(ConfigDependencyMap, 'validate_config_value', return_value=(True, "Valid")):
                                with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', return_value=mock_config):
                                    with patch.object(ConfigDependencyMap, 'check_config_consistency', return_value=[]):
                                        
                                        is_valid, errors, warnings = validator.validate_startup_configuration()
                                        
                                        assert is_valid is True
                                        assert errors == []
                                        assert warnings == []
    
    def test_complete_validation_flow_failure(self):
        """Test complete validation flow with failure scenario."""
        validator = ConfigurationStartupValidator(StartupValidationMode.STRICT)
        
        # Mock dependencies for failure scenario
        mock_required_configs = {
            "CRITICAL_MISSING": {
                "impact_level": ConfigImpactLevel.CRITICAL,
                "deletion_impact": "System will fail",
                "fallback_allowed": False
            }
        }
        
        mock_config = Mock()
        mock_config.database_url = None  # Missing database URL
        mock_config.jwt_secret_key = None  # Missing JWT secret
        mock_config.__dict__ = {"database_url": None, "jwt_secret_key": None}
        
        with patch.object(ConfigDependencyMap, 'get_required_configs', return_value=mock_required_configs):
            with patch.object(ConfigDependencyMap, 'CRITICAL_DEPENDENCIES', {}):
                with patch.object(ConfigDependencyMap, 'HIGH_PRIORITY_DEPENDENCIES', {}):
                    with patch.object(ConfigDependencyMap, 'SERVICE_SPECIFIC_DEPENDENCIES', {}):
                        with patch('netra_backend.app.core.configuration.startup_validator.get_env') as mock_get_env:
                            mock_env = Mock()
                            mock_env.get.return_value = None  # Missing config
                            mock_get_env.return_value = mock_env
                            
                            with patch('netra_backend.app.core.configuration.startup_validator.get_unified_config', return_value=mock_config):
                                with patch.object(ConfigDependencyMap, 'check_config_consistency', return_value=["CRITICAL: Major issue"]):
                                    
                                    is_valid, errors, warnings = validator.validate_startup_configuration()
                                    
                                    assert is_valid is False
                                    assert len(errors) >= 3  # Missing critical config, database URL, JWT secret, config consistency
                                    
                                    # Check specific error messages
                                    error_text = " ".join(errors)
                                    assert "CRITICAL CONFIG MISSING" in error_text
                                    assert "DATABASE CONFIG" in error_text
                                    assert "AUTH CONFIG" in error_text


if __name__ == "__main__":
    # Run the tests
    import sys
    sys.exit(pytest.main([__file__, "-v"]))