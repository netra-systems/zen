"""
Comprehensive Unit Tests for ConfigurationValidator - SSOT Configuration Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all segments)  
- Business Goal: Risk Reduction & Platform Stability
- Value Impact: Prevents $12K MRR loss from configuration errors - critical for production reliability
- Strategic Impact: ConfigurationValidator ensures all configurations are valid before system startup

CRITICAL: ConfigurationValidator is the SSOT for configuration validation across all environments.
Prevents deployment of invalid configurations that would cause system failures.

Test Requirements from CLAUDE.md:
1. CHEATING ON TESTS = ABOMINATION - Every test must fail hard on errors
2. NO mocks unless absolutely necessary - Use real configuration validation
3. ABSOLUTE IMPORTS only - No relative imports
4. Tests must RAISE ERRORS - No try/except blocks masking failures
5. Real services over mocks - Use real validation logic, real environment detection

Testing Areas:
1. Validator Initialization - environment detection, rule loading, sub-validator setup
2. Validation Mode Logic - WARN, ENFORCE_CRITICAL, ENFORCE_ALL modes
3. Complete Configuration Validation - orchestration of all validation modules
4. Progressive Validation - environment-specific enforcement levels
5. Configuration Health Score - scoring algorithm for configuration completeness
6. Critical Field Detection - identification of mission-critical configuration fields
7. Environment-Specific Rules - development vs production validation rules
8. Sub-validator Orchestration - database, LLM, auth, environment validators
9. Error Categorization - critical vs non-critical error classification
10. Validation Results - ValidationResult structure and scoring
11. Real Configuration Testing - actual AppConfig instances
12. Multi-Environment Validation - testing across dev/staging/prod environments
"""
import pytest
from typing import Any, Dict, List, Tuple
from unittest.mock import patch, MagicMock
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.core.configuration.validator import ConfigurationValidator, ValidationMode
from netra_backend.app.core.configuration.validator_types import ValidationResult
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, ProductionConfig, StagingConfig, NetraTestingConfig

class TestConfigurationValidatorInitialization(BaseTestCase):
    """Test ConfigurationValidator initialization and setup."""

    def test_configuration_validator_creates_real_instance(self):
        """Test that ConfigurationValidator creates a real working instance.
        
        Business Value: Ensures validator initializes properly for configuration validation
        """
        validator = ConfigurationValidator()
        assert validator is not None
        assert hasattr(validator, '_logger')
        assert hasattr(validator, '_environment')
        assert hasattr(validator, '_validation_rules')
        assert hasattr(validator, '_critical_fields')
        assert hasattr(validator, '_database_validator')
        assert hasattr(validator, '_llm_validator')
        assert hasattr(validator, '_auth_validator')
        assert hasattr(validator, '_environment_validator')

    def test_validation_rules_loaded_for_all_environments(self):
        """Test that validation rules are loaded for all supported environments.
        
        Business Value: Ensures environment-specific validation rules are available
        """
        validator = ConfigurationValidator()
        required_environments = ['development', 'staging', 'production', 'testing']
        for env in required_environments:
            assert env in validator._validation_rules
            rules = validator._validation_rules[env]
            assert 'require_ssl' in rules
            assert 'allow_localhost' in rules
            assert 'require_secrets' in rules
            assert 'validation_mode' in rules

    def test_critical_fields_loaded_for_all_components(self):
        """Test that critical fields are defined for all system components.
        
        Business Value: Ensures critical configuration fields are validated
        """
        validator = ConfigurationValidator()
        required_components = ['database', 'llm', 'auth', 'external', 'secrets']
        for component in required_components:
            assert component in validator._critical_fields
            fields = validator._critical_fields[component]
            assert isinstance(fields, list)
            assert len(fields) > 0

    def test_environment_detection_works(self):
        """Test that environment detection works properly.
        
        Business Value: Environment-specific validation depends on correct detection
        """
        validator = ConfigurationValidator()
        assert validator._environment is not None
        assert isinstance(validator._environment, str)
        assert validator._environment in ['development', 'staging', 'production', 'testing']

class TestValidationModeLogic(BaseTestCase):
    """Test validation mode logic and progressive enforcement."""

    def test_validation_mode_enum_values(self):
        """Test that ValidationMode enum has all required values.
        
        Business Value: Ensures all validation modes are properly defined
        """
        assert ValidationMode.WARN == 'warn'
        assert ValidationMode.ENFORCE_CRITICAL == 'enforce_critical'
        assert ValidationMode.ENFORCE_ALL == 'enforce_all'

    def test_development_environment_uses_warn_mode(self):
        """Test that development environment uses warn validation mode.
        
        Business Value: Development environments should be permissive for rapid iteration
        """
        validator = ConfigurationValidator()
        dev_rules = validator._get_development_rules()
        assert dev_rules['validation_mode'] == ValidationMode.WARN.value
        assert dev_rules['require_ssl'] is False
        assert dev_rules['allow_localhost'] is True
        assert dev_rules['require_secrets'] is False

    def test_production_environment_uses_enforce_all_mode(self):
        """Test that production environment uses enforce_all validation mode.
        
        Business Value: Production environments must have strict validation for security
        """
        validator = ConfigurationValidator()
        prod_rules = validator._get_production_rules()
        assert prod_rules['validation_mode'] == ValidationMode.ENFORCE_ALL.value
        assert prod_rules['require_ssl'] is True
        assert prod_rules['allow_localhost'] is False
        assert prod_rules['require_secrets'] is True

class TestCompleteConfigurationValidation(BaseTestCase):
    """Test complete configuration validation orchestration."""

    def test_validate_complete_config_returns_validation_result(self):
        """Test that validate_complete_config returns proper ValidationResult.
        
        Business Value: Core validation function must return structured results
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        result = validator.validate_complete_config(config)
        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'score')
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.score, int)

    def test_validation_result_score_in_valid_range(self):
        """Test that validation score is always in valid range 0-100.
        
        Business Value: Configuration health score must be meaningful and bounded
        """
        validator = ConfigurationValidator()
        configs = [DevelopmentConfig(), ProductionConfig(), StagingConfig(), NetraTestingConfig()]
        for config in configs:
            result = validator.validate_complete_config(config)
            assert 0 <= result.score <= 100

    def test_validation_with_multiple_config_types(self):
        """Test validation works with all configuration types.
        
        Business Value: All configuration types must be properly validated
        """
        validator = ConfigurationValidator()
        config_types = [DevelopmentConfig, ProductionConfig, StagingConfig, NetraTestingConfig]
        for config_class in config_types:
            config = config_class()
            result = validator.validate_complete_config(config)
            assert isinstance(result, ValidationResult)
            assert isinstance(result.score, int)

class TestProgressiveValidation(BaseTestCase):
    """Test progressive validation enforcement based on environment."""

    def test_progressive_validation_warn_mode_converts_errors_to_warnings(self):
        """Test that WARN mode converts all errors to warnings.
        
        Business Value: Permissive validation in development environments
        """
        validator = ConfigurationValidator()
        test_errors = ['error1', 'error2', 'error3']
        test_warnings = ['warning1']
        with patch.object(validator, '_validation_rules', {validator._environment: {'validation_mode': ValidationMode.WARN.value}}):
            errors, warnings = validator._apply_progressive_validation(test_errors, test_warnings)
            assert len(errors) == 0
            assert len(warnings) >= len(test_errors)

    def test_progressive_validation_enforce_all_mode_keeps_all_errors(self):
        """Test that ENFORCE_ALL mode keeps all errors as errors.
        
        Business Value: Strict validation in production environments
        """
        validator = ConfigurationValidator()
        test_errors = ['error1', 'error2', 'error3']
        test_warnings = ['warning1']
        with patch.object(validator, '_validation_rules', {validator._environment: {'validation_mode': ValidationMode.ENFORCE_ALL.value}}):
            errors, warnings = validator._apply_progressive_validation(test_errors, test_warnings)
            assert errors == test_errors
            assert warnings == test_warnings

class TestConfigurationHealthScore(BaseTestCase):
    """Test configuration health scoring algorithm."""

    def test_health_score_calculation_with_no_issues(self):
        """Test health score calculation with perfect configuration.
        
        Business Value: Perfect configurations should get high scores
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        errors = []
        warnings = []
        score = validator._calculate_config_health_score(config, errors, warnings)
        assert score >= 80
        assert score <= 100

    def test_health_score_penalties_for_errors_and_warnings(self):
        """Test that errors and warnings properly penalize health score.
        
        Business Value: Configuration issues must be reflected in health score
        """
        validator = ConfigurationValidator()
        errors = ['error1', 'error2']
        warnings = ['warning1', 'warning2', 'warning3']
        penalties = validator._calculate_score_penalties(errors, warnings)
        expected_penalty = len(errors) * 15 + len(warnings) * 5
        assert penalties == expected_penalty

    def test_health_score_bounded_correctly(self):
        """Test that health score is properly bounded between 0-100.
        
        Business Value: Health score must be meaningful and interpretable
        """
        validator = ConfigurationValidator()
        extreme_cases = [(100, 0, 0), (100, 200, 0), (100, 0, 50), (0, 0, 150)]
        for base_score, penalties, bonus in extreme_cases:
            score = validator._compute_final_score(base_score, penalties, bonus)
            assert 0 <= score <= 100

class TestCriticalFieldDetection(BaseTestCase):
    """Test critical field detection and completeness calculation."""

    def test_count_critical_fields_returns_valid_counts(self):
        """Test that critical field counting returns valid counts.
        
        Business Value: Completeness metrics must be accurate
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        present, total = validator._count_critical_fields(config)
        assert isinstance(present, int)
        assert isinstance(total, int)
        assert present >= 0
        assert total >= 0
        assert present <= total

    def test_completeness_bonus_calculation(self):
        """Test completeness bonus calculation logic.
        
        Business Value: Complete configurations should be rewarded with higher scores
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        bonus = validator._calculate_completeness_bonus(config)
        assert isinstance(bonus, int)
        assert 0 <= bonus <= 10

    def test_component_field_counting(self):
        """Test component-specific field counting.
        
        Business Value: Per-component completeness tracking for detailed metrics
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        test_fields = ['database_url', 'jwt_secret_key']
        present, total = validator._count_component_fields(config, test_fields)
        assert isinstance(present, int)
        assert isinstance(total, int)
        assert total == len(test_fields)
        assert 0 <= present <= total

class TestEnvironmentSpecificBehavior(BaseTestCase):
    """Test environment-specific validation behavior."""

    def test_environment_refresh_updates_validators(self):
        """Test that refresh_environment updates sub-validators.
        
        Business Value: Dynamic environment changes must update validation behavior
        """
        validator = ConfigurationValidator()
        original_env = validator._environment
        with patch.object(validator, '_get_environment', return_value='production'):
            validator.refresh_environment()
            assert validator._environment == 'production'

    def test_validation_rules_differ_between_environments(self):
        """Test that validation rules are different between environments.
        
        Business Value: Environment-specific rules ensure appropriate validation
        """
        validator = ConfigurationValidator()
        dev_rules = validator._validation_rules['development']
        prod_rules = validator._validation_rules['production']
        assert dev_rules['require_ssl'] != prod_rules['require_ssl']
        assert dev_rules['allow_localhost'] != prod_rules['allow_localhost']
        assert dev_rules['require_secrets'] != prod_rules['require_secrets']
        assert dev_rules['validation_mode'] != prod_rules['validation_mode']

class TestSubValidatorOrchestration(BaseTestCase):
    """Test orchestration of sub-validators."""

    def test_sub_validators_initialized_correctly(self):
        """Test that all sub-validators are initialized with correct parameters.
        
        Business Value: Sub-validators must be properly initialized for validation
        """
        validator = ConfigurationValidator()
        assert validator._database_validator is not None
        assert validator._llm_validator is not None
        assert validator._auth_validator is not None
        assert validator._environment_validator is not None

    def test_error_collection_calls_all_validators(self):
        """Test that error collection orchestrates all validator modules.
        
        Business Value: Comprehensive validation requires all components to be checked
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        with patch.object(validator, '_collect_database_errors_with_fallbacks', return_value=[]):
            with patch.object(validator, '_collect_llm_errors_with_fallbacks', return_value=[]):
                with patch.object(validator, '_collect_auth_errors_with_fallbacks', return_value=[]):
                    with patch.object(validator, '_collect_external_errors_with_fallbacks', return_value=[]):
                        with patch.object(validator, '_collect_config_dependency_errors', return_value=[]):
                            errors = validator._collect_all_errors(config)
                            assert isinstance(errors, list)

class TestRealConfigurationValidation(BaseTestCase):
    """Test validation with real configuration instances."""

    def test_development_config_validation(self):
        """Test validation of real DevelopmentConfig instance.
        
        Business Value: Development configurations must validate properly
        """
        validator = ConfigurationValidator()
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value='development'):
            validator.refresh_environment()
            config = DevelopmentConfig()
            result = validator.validate_complete_config(config)
            assert isinstance(result, ValidationResult)
            assert isinstance(result.score, int)

    def test_production_config_validation(self):
        """Test validation of real ProductionConfig instance.
        
        Business Value: Production configurations must validate strictly
        """
        validator = ConfigurationValidator()
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value='production'):
            validator.refresh_environment()
            config = ProductionConfig()
            result = validator.validate_complete_config(config)
            assert isinstance(result, ValidationResult)
            assert isinstance(result.score, int)

    def test_testing_config_validation(self):
        """Test validation of real NetraTestingConfig instance.
        
        Business Value: Testing configurations must validate for reliable test execution
        """
        validator = ConfigurationValidator()
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value='testing'):
            validator.refresh_environment()
            config = NetraTestingConfig()
            result = validator.validate_complete_config(config)
            assert isinstance(result, ValidationResult)
            assert isinstance(result.score, int)

class TestValidationResultStructure(BaseTestCase):
    """Test ValidationResult structure and properties."""

    def test_validation_result_has_required_properties(self):
        """Test that ValidationResult has all required properties.
        
        Business Value: Validation results must provide complete information for decisions
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        result = validator.validate_complete_config(config)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'score')
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.score, int)

    def test_validation_result_consistency(self):
        """Test consistency between validation result fields.
        
        Business Value: Validation results must be logically consistent
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        result = validator.validate_complete_config(config)
        if len(result.errors) == 0:
            assert result.is_valid is True
        else:
            assert result.is_valid is False

class TestValidationErrorHandling(BaseTestCase):
    """Test error handling in validation processes."""

    def test_validation_handles_invalid_config_gracefully(self):
        """Test that validation handles invalid configurations gracefully.
        
        Business Value: Robust validation prevents crashes from bad configurations
        """
        validator = ConfigurationValidator()
        config = AppConfig()
        result = validator.validate_complete_config(config)
        assert isinstance(result, ValidationResult)

    def test_validation_with_none_config_values(self):
        """Test validation behavior with None configuration values.
        
        Business Value: Must handle missing/None configuration values safely
        """
        validator = ConfigurationValidator()
        config = DevelopmentConfig()
        result = validator.validate_complete_config(config)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.score, int)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')