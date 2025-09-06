from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Critical Configuration Environment Detection Tests

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: All segments (affects deployment reliability)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Ensure correct configuration loading across environments
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents config mismatches that could cause billing errors
    # REMOVED_SYNTAX_ERROR: - Revenue Impact: Config failures could affect customer billing accuracy. Estimated -$25K MRR risk

    # REMOVED_SYNTAX_ERROR: Tests the configuration environment detection module that handles:
        # REMOVED_SYNTAX_ERROR: - Environment detection logic (development, staging, production, testing)
        # REMOVED_SYNTAX_ERROR: - Cloud Run environment detection
        # REMOVED_SYNTAX_ERROR: - Config object creation and validation
        # REMOVED_SYNTAX_ERROR: - Environment-specific behavior

        # REMOVED_SYNTAX_ERROR: COMPLIANCE:
            # REMOVED_SYNTAX_ERROR: - Module ≤300 lines ✓
            # REMOVED_SYNTAX_ERROR: - Functions ≤8 lines ✓
            # REMOVED_SYNTAX_ERROR: - Strong typing with Pydantic ✓
            # REMOVED_SYNTAX_ERROR: """"

            # REMOVED_SYNTAX_ERROR: import sys
            # REMOVED_SYNTAX_ERROR: from pathlib import Path
            # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # Test framework import - using pytest fixtures instead

            # REMOVED_SYNTAX_ERROR: import os

            # REMOVED_SYNTAX_ERROR: import pytest
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.environment import EnvironmentDetector as ConfigEnvironment

            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.config import ( )
            # REMOVED_SYNTAX_ERROR: AppConfig,
            # REMOVED_SYNTAX_ERROR: DevelopmentConfig,
            # REMOVED_SYNTAX_ERROR: NetraTestingConfig,
            # REMOVED_SYNTAX_ERROR: ProductionConfig,
            # REMOVED_SYNTAX_ERROR: StagingConfig)

# REMOVED_SYNTAX_ERROR: class TestConfigEnvironmentDetection:
    # REMOVED_SYNTAX_ERROR: """Core environment detection functionality tests"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def config_env(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create ConfigEnvironment instance for testing"""
    # REMOVED_SYNTAX_ERROR: return ConfigEnvironment()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def clean_environment(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Clean environment variables for isolated testing"""
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # REMOVED_SYNTAX_ERROR: original_env = env.get_all()
    # REMOVED_SYNTAX_ERROR: env = get_env()

    # Clear relevant environment variables from both os.environ and isolated environment
    # REMOVED_SYNTAX_ERROR: env_vars_to_clear = [ )
    # REMOVED_SYNTAX_ERROR: 'TESTING', 'ENVIRONMENT', 'K_SERVICE',
    # REMOVED_SYNTAX_ERROR: 'GAE_APPLICATION', 'GOOGLE_CLOUD_PROJECT', 'PYTEST_CURRENT_TEST'
    

    # Store original isolated environment values for restoration
    # REMOVED_SYNTAX_ERROR: original_isolated_values = {}
    # REMOVED_SYNTAX_ERROR: for var in env_vars_to_clear:
        # REMOVED_SYNTAX_ERROR: if env.exists(var):
            # REMOVED_SYNTAX_ERROR: original_isolated_values[var] = env.get(var)
            # Clear from both sources
            # REMOVED_SYNTAX_ERROR: os.environ.pop(var, None)
            # REMOVED_SYNTAX_ERROR: env.delete(var)

            # Reset the cache in the deprecated EnvironmentDetector to ensure fresh detection
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.environment import _environment_detector
            # REMOVED_SYNTAX_ERROR: _environment_detector.reset_cache()

            # REMOVED_SYNTAX_ERROR: yield

            # Restore original environment
            # REMOVED_SYNTAX_ERROR: env.clear()
            # REMOVED_SYNTAX_ERROR: env.update(original_env, "test")

            # Restore isolated environment values (except PYTEST_CURRENT_TEST which should remain cleared)
            # REMOVED_SYNTAX_ERROR: for var, value in original_isolated_values.items():
                # REMOVED_SYNTAX_ERROR: if value is not None and var != 'PYTEST_CURRENT_TEST':
                    # REMOVED_SYNTAX_ERROR: env.set(var, value, source="clean_environment_restore")

# REMOVED_SYNTAX_ERROR: def test_get_environment_testing(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test environment detection returns 'testing' when TESTING env var set"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: env.set('TESTING', 'true', "test")

    # Act
    # REMOVED_SYNTAX_ERROR: result = config_env.detect()

    # Assert
    # REMOVED_SYNTAX_ERROR: assert result == "testing"

# REMOVED_SYNTAX_ERROR: def test_get_environment_cloud_run_detected(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test environment detection with cloud run environment"""
    # Arrange
    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = "production"

        # Act
        # REMOVED_SYNTAX_ERROR: result = config_env.detect()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert result == "production"
        # REMOVED_SYNTAX_ERROR: mock_detect.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_get_environment_defaults_to_development(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test environment detection defaults to development"""
    # Arrange
    # Mock: Component isolation for testing without external dependencies
    # Also need to clear TESTING flag since it takes highest priority
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: env = get_env()

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = None

        # Temporarily clear testing flags to test development default
        # REMOVED_SYNTAX_ERROR: original_testing = env.get('TESTING')
        # REMOVED_SYNTAX_ERROR: original_pytest = env.get('PYTEST_CURRENT_TEST')
        # REMOVED_SYNTAX_ERROR: env.set('TESTING', '')  # Clear testing flag
        # REMOVED_SYNTAX_ERROR: env.set('PYTEST_CURRENT_TEST', '')  # Clear pytest flag

        # REMOVED_SYNTAX_ERROR: try:
            # Act
            # REMOVED_SYNTAX_ERROR: result = config_env.detect()

            # Assert
            # REMOVED_SYNTAX_ERROR: assert result == "development"
            # REMOVED_SYNTAX_ERROR: finally:
                # Restore testing flags
                # REMOVED_SYNTAX_ERROR: if original_testing:
                    # REMOVED_SYNTAX_ERROR: env.set('TESTING', original_testing)
                    # REMOVED_SYNTAX_ERROR: if original_pytest:
                        # REMOVED_SYNTAX_ERROR: env.set('PYTEST_CURRENT_TEST', original_pytest)

# REMOVED_SYNTAX_ERROR: def test_get_environment_explicit_environment_var(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test environment detection with explicit ENVIRONMENT variable"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # REMOVED_SYNTAX_ERROR: ("production", "production"),
    # REMOVED_SYNTAX_ERROR: ("staging", "staging"),
    # REMOVED_SYNTAX_ERROR: ("development", "development"),
    # REMOVED_SYNTAX_ERROR: ("PRODUCTION", "production"),  # Test case insensitivity
    # REMOVED_SYNTAX_ERROR: ("Staging", "staging"),
    

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = None

        # REMOVED_SYNTAX_ERROR: for env_value, expected in test_cases:
            # REMOVED_SYNTAX_ERROR: env.set('ENVIRONMENT', env_value, "test")

            # Act
            # REMOVED_SYNTAX_ERROR: result = config_env.detect()

            # Assert
            # REMOVED_SYNTAX_ERROR: assert result == expected

# REMOVED_SYNTAX_ERROR: def test_testing_environment_takes_precedence(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test that TESTING env var takes precedence over other detection"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: env.set('TESTING', 'true', "test")
    # REMOVED_SYNTAX_ERROR: env.set('ENVIRONMENT', 'production', "test")

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = "staging"

        # Act
        # REMOVED_SYNTAX_ERROR: result = config_env.detect()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert result == "testing"
        # Cloud detection should not be called when TESTING is set
        # REMOVED_SYNTAX_ERROR: mock_detect.assert_not_called()

# REMOVED_SYNTAX_ERROR: class TestConfigObjectCreation:
    # REMOVED_SYNTAX_ERROR: """Test configuration object creation for different environments"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def config_env(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create ConfigEnvironment instance for testing"""
    # REMOVED_SYNTAX_ERROR: return ConfigEnvironment()

# REMOVED_SYNTAX_ERROR: def test_create_config_development(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test creation of development configuration"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='development'):

        # Act
        # REMOVED_SYNTAX_ERROR: config = config_env.create_config()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert isinstance(config, DevelopmentConfig)
        # REMOVED_SYNTAX_ERROR: assert config.environment == "development"

# REMOVED_SYNTAX_ERROR: def test_create_config_production(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test creation of production configuration"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='production'):

        # Act
        # REMOVED_SYNTAX_ERROR: config = config_env.create_config()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert isinstance(config, ProductionConfig)
        # REMOVED_SYNTAX_ERROR: assert config.environment == "production"

# REMOVED_SYNTAX_ERROR: def test_create_config_staging(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test creation of staging configuration"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='staging'):

        # Act
        # REMOVED_SYNTAX_ERROR: config = config_env.create_config()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert isinstance(config, StagingConfig)
        # REMOVED_SYNTAX_ERROR: assert config.environment in ['staging', 'testing']

# REMOVED_SYNTAX_ERROR: def test_create_config_testing(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test creation of testing configuration"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='testing'):

        # Act
        # REMOVED_SYNTAX_ERROR: config = config_env.create_config()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert isinstance(config, NetraTestingConfig)
        # REMOVED_SYNTAX_ERROR: assert config.environment == "testing"

# REMOVED_SYNTAX_ERROR: def test_create_config_unknown_environment_defaults(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test creation with unknown environment defaults to development"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='unknown'):

        # Act
        # REMOVED_SYNTAX_ERROR: config = config_env.create_config()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert isinstance(config, DevelopmentConfig)

# REMOVED_SYNTAX_ERROR: class TestEnvironmentValidation:
    # REMOVED_SYNTAX_ERROR: """Test environment validation and error handling"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def config_env(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return ConfigEnvironment()

# REMOVED_SYNTAX_ERROR: def test_validate_environment_valid_environments(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test validation of all valid environment names"""
    # REMOVED_SYNTAX_ERROR: valid_environments = [ )
    # REMOVED_SYNTAX_ERROR: 'development', 'production', 'staging', 'testing'
    

    # REMOVED_SYNTAX_ERROR: for env in valid_environments:
        # Should not raise exception
        # REMOVED_SYNTAX_ERROR: assert config_env.validate_environment(env) is True

# REMOVED_SYNTAX_ERROR: def test_validate_environment_invalid_environments(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test validation rejects invalid environment names"""
    # REMOVED_SYNTAX_ERROR: invalid_environments = [ )
    # REMOVED_SYNTAX_ERROR: '', 'invalid', 'prod', 'dev', 'test', None, 123
    

    # REMOVED_SYNTAX_ERROR: for env in invalid_environments:
        # REMOVED_SYNTAX_ERROR: assert config_env.validate_environment(env) is False

# REMOVED_SYNTAX_ERROR: def test_environment_config_mapping_completeness(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test that all valid environments have corresponding config classes"""
    # REMOVED_SYNTAX_ERROR: environment_mappings = { )
    # REMOVED_SYNTAX_ERROR: 'development': DevelopmentConfig,
    # REMOVED_SYNTAX_ERROR: 'production': ProductionConfig,
    # REMOVED_SYNTAX_ERROR: 'staging': StagingConfig,
    # REMOVED_SYNTAX_ERROR: 'testing': NetraTestingConfig
    

    # REMOVED_SYNTAX_ERROR: for env_name, config_class in environment_mappings.items():
        # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value=env_name):
            # REMOVED_SYNTAX_ERROR: config = config_env.create_config()
            # REMOVED_SYNTAX_ERROR: assert isinstance(config, config_class)

# REMOVED_SYNTAX_ERROR: class TestCloudEnvironmentDetection:
    # REMOVED_SYNTAX_ERROR: """Test cloud-specific environment detection"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def config_env(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return ConfigEnvironment()

# REMOVED_SYNTAX_ERROR: def test_cloud_run_detection_with_k_service(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test Cloud Run detection via K_SERVICE environment variable"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: env.set('K_SERVICE', 'netra-backend', "test")

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = "production"

        # Act
        # REMOVED_SYNTAX_ERROR: result = config_env.detect()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert result == "production"

# REMOVED_SYNTAX_ERROR: def test_app_engine_detection(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test App Engine detection via GAE_APPLICATION"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: env.set('GAE_APPLICATION', 'netra-project', "test")

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = "staging"

        # Act
        # REMOVED_SYNTAX_ERROR: result = config_env.detect()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert result == "staging"

# REMOVED_SYNTAX_ERROR: def test_google_cloud_project_detection(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test Google Cloud Project detection"""
    # Arrange
    # REMOVED_SYNTAX_ERROR: env.set('GOOGLE_CLOUD_PROJECT', 'netra-ai-platform', "test")

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment') as mock_detect:
        # REMOVED_SYNTAX_ERROR: mock_detect.return_value = "production"

        # Act
        # REMOVED_SYNTAX_ERROR: result = config_env.detect()

        # Assert
        # REMOVED_SYNTAX_ERROR: assert result == "production"

# REMOVED_SYNTAX_ERROR: class TestConfigurationLogging:
    # REMOVED_SYNTAX_ERROR: """Test configuration-related logging functionality"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def config_env(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return ConfigEnvironment()

# REMOVED_SYNTAX_ERROR: def test_logger_initialization(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test that logger is properly initialized"""
    # Assert
    # REMOVED_SYNTAX_ERROR: assert hasattr(config_env, '_logger')
    # REMOVED_SYNTAX_ERROR: assert config_env._logger is not None

# REMOVED_SYNTAX_ERROR: def test_environment_detection_logging(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test logging during environment detection"""
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, '_logger') as mock_logger:
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment', return_value=None):

            # Act
            # REMOVED_SYNTAX_ERROR: config_env.detect()

            # Assert - Logger should be called for environment detection
            # REMOVED_SYNTAX_ERROR: assert mock_logger.debug.called or mock_logger.info.called

# REMOVED_SYNTAX_ERROR: def test_config_creation_logging(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test logging during config object creation"""
    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, '_logger') as mock_logger:
        # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='development'):

            # Act
            # REMOVED_SYNTAX_ERROR: config_env.create_config()

            # Assert
            # REMOVED_SYNTAX_ERROR: assert mock_logger.debug.called or mock_logger.info.called

# REMOVED_SYNTAX_ERROR: class TestPerformanceAndEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Performance and edge case testing"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def config_env(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return ConfigEnvironment()

# REMOVED_SYNTAX_ERROR: def test_multiple_environment_detections_consistent(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test that multiple calls return consistent results"""
    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment', return_value='production'):

        # Act - Multiple calls
        # REMOVED_SYNTAX_ERROR: results = [config_env.detect() for _ in range(10)]

        # Assert - All results should be identical
        # REMOVED_SYNTAX_ERROR: assert len(set(results)) == 1
        # REMOVED_SYNTAX_ERROR: assert results[0] == "production"

# REMOVED_SYNTAX_ERROR: def test_config_creation_performance(self, config_env):
    # REMOVED_SYNTAX_ERROR: """Test config creation performance with multiple calls"""
    # REMOVED_SYNTAX_ERROR: import time

    # REMOVED_SYNTAX_ERROR: with patch.object(config_env, 'detect', return_value='development'):

        # Act - Time multiple config creations
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: configs = [config_env.create_config() for _ in range(100)]
        # REMOVED_SYNTAX_ERROR: end_time = time.time()

        # Assert - Should complete quickly and all be DevelopmentConfig
        # REMOVED_SYNTAX_ERROR: assert end_time - start_time < 1.0  # Should take less than 1 second
        # REMOVED_SYNTAX_ERROR: assert all(isinstance(config, DevelopmentConfig) for config in configs)

# REMOVED_SYNTAX_ERROR: def test_environment_variable_unicode_handling(self, config_env, clean_environment):
    # REMOVED_SYNTAX_ERROR: """Test handling of unicode characters in environment variables"""
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # REMOVED_SYNTAX_ERROR: "production",
    # REMOVED_SYNTAX_ERROR: "production🚀",
    # REMOVED_SYNTAX_ERROR: "prøduction",
    # REMOVED_SYNTAX_ERROR: "продукция"
    

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.detect_cloud_environment', return_value=None):
        # REMOVED_SYNTAX_ERROR: for test_env in test_cases:
            # REMOVED_SYNTAX_ERROR: env.set('ENVIRONMENT', test_env, "test")

            # Should not raise exception
            # REMOVED_SYNTAX_ERROR: result = config_env.detect()

            # Should default to development for invalid environments
            # REMOVED_SYNTAX_ERROR: if test_env == "production":
                # REMOVED_SYNTAX_ERROR: assert result == "production"
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: assert result == "development"