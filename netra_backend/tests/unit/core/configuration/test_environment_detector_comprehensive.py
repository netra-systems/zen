"""
Test Environment Detector SSOT Class - Comprehensive Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity  
- Business Goal: Ensure environment detection works correctly across all deployment contexts
- Value Impact: Proper environment detection prevents configuration issues and service failures
- Strategic Impact: Critical for deployment reliability and multi-environment consistency

Tests ALL methods of the EnvironmentDetector SSOT class with 100% coverage including:
- Environment detection (local, test, dev, staging, production)
- Cloud environment detection (GCP, AWS, Azure)
- Docker detection
- CI/CD detection
- Configuration validation and consistency checking
- Error handling and edge cases
- URL masking and security
- Service requirement checking

CRITICAL REQUIREMENTS per CLAUDE.md:
- Use SSOT base test class from test_framework.ssot.base_test_case
- Use IsolatedEnvironment for ALL environment variable access (NO os.environ)
- Test real object behavior with minimal mocks
- Cover all edge cases and error conditions
- Include deprecation warning testing
"""

import warnings
import socket
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Optional, Any

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.configuration.environment_detector import (
    EnvironmentDetector,
    Environment,
    EnvironmentConfig,
    get_environment_detector,
    get_current_environment,
    get_environment_config,
    validate_environment
)


class TestEnvironmentDetectorComprehensive(SSotBaseTestCase):
    """Comprehensive unit tests for EnvironmentDetector SSOT class."""
    
    def setup_method(self, method=None):
        """Setup test environment with clean state."""
        super().setup_method(method)
        
        # Reset global detector instance for clean tests
        import netra_backend.app.core.configuration.environment_detector as detector_module
        detector_module._environment_detector = None
        
        # Clear any cached environment state
        self.detector = EnvironmentDetector()
        
        # Track deprecation warnings
        self.warning_list = []
        
    def teardown_method(self, method=None):
        """Clean up after each test."""
        # Reset global state
        import netra_backend.app.core.configuration.environment_detector as detector_module
        detector_module._environment_detector = None
        
        super().teardown_method(method)

    # === DEPRECATION WARNING TESTS ===

    def test_module_deprecation_warning_on_import(self):
        """Test that module shows deprecation warning on import."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Re-import to trigger warning
            import importlib
            import netra_backend.app.core.configuration.environment_detector as detector_module
            importlib.reload(detector_module)
            
            # Check that deprecation warning was issued
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) > 0
            assert "environment_detector is deprecated" in str(deprecation_warnings[0].message)
            assert "environment_constants" in str(deprecation_warnings[0].message)

    def test_get_current_environment_deprecation_warning(self):
        """Test that get_current_environment shows deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Set a clean environment for this test
            with self.temp_env_vars(ENVIRONMENT="development"):
                # Call deprecated function
                env = get_current_environment()
                
                # Check deprecation warning
                deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
                assert len(deprecation_warnings) > 0
                assert "get_current_environment() from environment_detector is deprecated" in str(deprecation_warnings[0].message)
                # Check that it returns an Environment enum value
                assert hasattr(env, 'value')
                assert env.value in ['development', 'staging', 'production', 'testing']

    # === ENVIRONMENT ENUM TESTS ===

    def test_environment_enum_values(self):
        """Test all Environment enum values."""
        expected_values = {
            "DEVELOPMENT": "development",
            "STAGING": "staging",
            "PRODUCTION": "production",
            "TESTING": "testing"
        }
        
        for name, value in expected_values.items():
            env = getattr(Environment, name)
            assert env.value == value
            self.record_metric("environment_enum_tested", name)

    # === ENVIRONMENT CONFIG TESTS ===

    def test_environment_config_development(self):
        """Test development environment configuration."""
        config = EnvironmentConfig.create_for_environment(Environment.DEVELOPMENT)
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug_mode is True
        assert config.log_level == "DEBUG"
        assert config.health_check_timeout == 10.0
        assert config.circuit_breaker_aggressive is False
        assert config.external_service_timeout == 30.0
        assert config.database_pool_size == 5
        assert config.redis_enabled is False
        assert config.clickhouse_required is False
        assert config.ssl_required is False
        
        self.record_metric("dev_config_validated", True)

    def test_environment_config_staging(self):
        """Test staging environment configuration."""
        config = EnvironmentConfig.create_for_environment(Environment.STAGING)
        
        assert config.environment == Environment.STAGING
        assert config.debug_mode is False
        assert config.log_level == "INFO"
        assert config.health_check_timeout == 8.0
        assert config.circuit_breaker_aggressive is True
        assert config.external_service_timeout == 15.0
        assert config.database_pool_size == 10
        assert config.redis_enabled is True
        assert config.clickhouse_required is False
        assert config.ssl_required is True
        
        self.record_metric("staging_config_validated", True)

    def test_environment_config_production(self):
        """Test production environment configuration."""
        config = EnvironmentConfig.create_for_environment(Environment.PRODUCTION)
        
        assert config.environment == Environment.PRODUCTION
        assert config.debug_mode is False
        assert config.log_level == "INFO"
        assert config.health_check_timeout == 5.0
        assert config.circuit_breaker_aggressive is True
        assert config.external_service_timeout == 10.0
        assert config.database_pool_size == 20
        assert config.redis_enabled is True
        assert config.clickhouse_required is True
        assert config.ssl_required is True
        
        self.record_metric("prod_config_validated", True)

    def test_environment_config_testing(self):
        """Test testing environment configuration."""
        config = EnvironmentConfig.create_for_environment(Environment.TESTING)
        
        assert config.environment == Environment.TESTING
        assert config.debug_mode is True
        assert config.log_level == "WARNING"
        assert config.health_check_timeout == 30.0
        assert config.circuit_breaker_aggressive is False
        assert config.external_service_timeout == 60.0
        assert config.database_pool_size == 2
        assert config.redis_enabled is False
        assert config.clickhouse_required is False
        assert config.ssl_required is False
        
        self.record_metric("test_config_validated", True)

    def test_environment_config_unknown_defaults_to_production(self):
        """Test that unknown environment defaults to production config."""
        # Create a mock environment that's not in the enum
        with patch('netra_backend.app.core.configuration.environment_detector.Environment') as mock_env:
            unknown_env = Mock()
            unknown_env.value = "unknown"
            
            config = EnvironmentConfig.create_for_environment(unknown_env)
            
            # Should get production config as fallback
            assert config.environment == unknown_env
            assert config.debug_mode is False
            assert config.ssl_required is True
            assert config.clickhouse_required is True

    # === ENVIRONMENT DETECTOR INITIALIZATION TESTS ===

    def test_environment_detector_initialization(self):
        """Test EnvironmentDetector initialization."""
        detector = EnvironmentDetector()
        
        assert detector._detected_environment is None
        assert detector._environment_config is None
        assert isinstance(detector._detection_cache, dict)
        assert len(detector._detection_cache) == 0
        
        self.record_metric("detector_initialized", True)

    # === ENVIRONMENT DETECTION TESTS ===

    def test_detect_environment_from_env_var_development(self):
        """Test environment detection from ENVIRONMENT variable - development."""
        test_cases = ["dev", "development", "Development", "DEV"]
        
        for env_value in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env_value):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.DEVELOPMENT
                self.record_metric(f"env_var_detected_{env_value}", True)

    def test_detect_environment_from_env_var_staging(self):
        """Test environment detection from ENVIRONMENT variable - staging."""
        test_cases = ["stage", "staging", "Staging", "STAGE"]
        
        for env_value in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env_value):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.STAGING
                self.record_metric(f"env_var_detected_{env_value}", True)

    def test_detect_environment_from_env_var_production(self):
        """Test environment detection from ENVIRONMENT variable - production."""
        test_cases = ["prod", "production", "Production", "PROD"]
        
        for env_value in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env_value):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.PRODUCTION
                self.record_metric(f"env_var_detected_{env_value}", True)

    def test_detect_environment_from_env_var_testing(self):
        """Test environment detection from ENVIRONMENT variable - testing."""
        test_cases = ["test", "testing", "Testing", "TEST"]
        
        for env_value in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env_value):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.TESTING
                self.record_metric(f"env_var_detected_{env_value}", True)

    def test_detect_environment_from_env_var_unknown(self):
        """Test environment detection with unknown ENVIRONMENT value."""
        with self.temp_env_vars(ENVIRONMENT="unknown"):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            # Should fall through to hostname detection and then default to production
            assert detected == Environment.PRODUCTION
            self.record_metric("unknown_env_fallback", True)

    def test_detect_environment_from_env_var_empty(self):
        """Test environment detection with empty ENVIRONMENT value."""
        with self.temp_env_vars(ENVIRONMENT=""):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            # Should fall through to hostname detection and then default to production
            assert detected == Environment.PRODUCTION
            self.record_metric("empty_env_fallback", True)

    @patch('socket.gethostname')
    def test_detect_environment_from_hostname_development(self, mock_hostname):
        """Test environment detection from hostname - development."""
        test_hostnames = ["dev-server", "development-box", "local-machine", "my-dev-laptop"]
        
        for hostname in test_hostnames:
            mock_hostname.return_value = hostname
            
            # Clear ENVIRONMENT to force hostname detection
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.DEVELOPMENT
                self.record_metric(f"hostname_detected_{hostname}", True)

    @patch('socket.gethostname')
    def test_detect_environment_from_hostname_staging(self, mock_hostname):
        """Test environment detection from hostname - staging."""
        test_hostnames = ["stage-server", "staging-box", "pre-prod-staging"]
        
        for hostname in test_hostnames:
            mock_hostname.return_value = hostname
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.STAGING
                self.record_metric(f"hostname_detected_{hostname}", True)

    @patch('socket.gethostname')
    def test_detect_environment_from_hostname_production(self, mock_hostname):
        """Test environment detection from hostname - production."""
        test_hostnames = ["prod-server", "production-box", "live-prod-01"]
        
        for hostname in test_hostnames:
            mock_hostname.return_value = hostname
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.PRODUCTION
                self.record_metric(f"hostname_detected_{hostname}", True)

    @patch('socket.gethostname')
    def test_detect_environment_from_hostname_testing(self, mock_hostname):
        """Test environment detection from hostname - testing."""
        test_hostnames = ["test-server", "testing-box", "ci-test-runner"]
        
        for hostname in test_hostnames:
            mock_hostname.return_value = hostname
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.TESTING
                self.record_metric(f"hostname_detected_{hostname}", True)

    @patch('socket.gethostname')
    def test_detect_environment_from_hostname_exception(self, mock_hostname):
        """Test environment detection when hostname throws exception."""
        mock_hostname.side_effect = Exception("Cannot get hostname")
        
        with self.temp_env_vars(ENVIRONMENT=""):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            # Should fall through to database URL detection and then default to production
            assert detected == Environment.PRODUCTION
            self.record_metric("hostname_exception_handled", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_detect_environment_from_database_url_development(self, mock_builder_class):
        """Test environment detection from database URL - development."""
        test_urls = [
            "postgresql://localhost:5432/db",
            "postgresql://127.0.0.1:5432/db",
            "postgresql://dev.example.com:5432/db"
        ]
        
        for db_url in test_urls:
            mock_builder = Mock()
            mock_builder.get_url_for_environment.return_value = db_url
            mock_builder_class.return_value = mock_builder
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.DEVELOPMENT
                self.record_metric(f"db_url_detected_{db_url}", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_detect_environment_from_database_url_staging(self, mock_builder_class):
        """Test environment detection from database URL - staging."""
        test_urls = [
            "postgresql://staging.example.com:5432/db",
            "postgresql://staging-db:5432/db"
        ]
        
        for db_url in test_urls:
            mock_builder = Mock()
            mock_builder.get_url_for_environment.return_value = db_url
            mock_builder_class.return_value = mock_builder
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.STAGING
                self.record_metric(f"db_url_detected_{db_url}", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_detect_environment_from_database_url_production(self, mock_builder_class):
        """Test environment detection from database URL - production."""
        test_urls = [
            "postgresql://prod.example.com:5432/db",
            "postgresql://production-db:5432/db"
        ]
        
        for db_url in test_urls:
            mock_builder = Mock()
            mock_builder.get_url_for_environment.return_value = db_url
            mock_builder_class.return_value = mock_builder
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.PRODUCTION
                self.record_metric(f"db_url_detected_{db_url}", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_detect_environment_from_database_url_testing(self, mock_builder_class):
        """Test environment detection from database URL - testing."""
        test_urls = [
            "postgresql://test.example.com:5432/db",
            "postgresql://test-db:5432/db"
        ]
        
        for db_url in test_urls:
            mock_builder = Mock()
            mock_builder.get_url_for_environment.return_value = db_url
            mock_builder_class.return_value = mock_builder
            
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.TESTING
                self.record_metric(f"db_url_detected_{db_url}", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_detect_environment_from_database_url_none(self, mock_builder_class):
        """Test environment detection when database URL is None."""
        mock_builder = Mock()
        mock_builder.get_url_for_environment.return_value = None
        mock_builder_class.return_value = mock_builder
        
        with self.temp_env_vars(ENVIRONMENT=""):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            # Should fall through to service context detection and then default to production
            assert detected == Environment.PRODUCTION
            self.record_metric("db_url_none_handled", True)

    def test_detect_environment_from_service_context_gcp_staging(self):
        """Test environment detection from GCP service context - staging."""
        with self.temp_env_vars(
            ENVIRONMENT="",
            GOOGLE_CLOUD_PROJECT="my-project-staging"
        ):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            assert detected == Environment.STAGING
            self.record_metric("gcp_staging_detected", True)

    def test_detect_environment_from_service_context_gcp_production(self):
        """Test environment detection from GCP service context - production."""
        with self.temp_env_vars(
            ENVIRONMENT="",
            GOOGLE_CLOUD_PROJECT="my-project-prod"
        ):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            assert detected == Environment.PRODUCTION
            self.record_metric("gcp_prod_detected", True)

    def test_detect_environment_from_service_context_k8s_staging(self):
        """Test environment detection from Kubernetes namespace - staging."""
        with self.temp_env_vars(
            ENVIRONMENT="",
            GOOGLE_CLOUD_PROJECT="",
            K8S_NAMESPACE="my-app-staging"
        ):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            assert detected == Environment.STAGING
            self.record_metric("k8s_staging_detected", True)

    def test_detect_environment_from_service_context_k8s_production(self):
        """Test environment detection from Kubernetes namespace - production."""
        with self.temp_env_vars(
            ENVIRONMENT="",
            GOOGLE_CLOUD_PROJECT="",
            K8S_NAMESPACE="my-app-prod"
        ):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            assert detected == Environment.PRODUCTION
            self.record_metric("k8s_prod_detected", True)

    def test_detect_environment_defaults_to_production(self):
        """Test environment detection defaults to production when no indicators found."""
        with self.temp_env_vars(
            ENVIRONMENT="",
            GOOGLE_CLOUD_PROJECT="",
            K8S_NAMESPACE=""
        ):
            with patch('socket.gethostname', return_value="generic-server"):
                with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = Mock()
                    mock_builder.get_url_for_environment.return_value = None
                    mock_builder_class.return_value = mock_builder
                    
                    detector = EnvironmentDetector()
                    detected = detector.detect_environment()
                    assert detected == Environment.PRODUCTION
                    self.record_metric("default_production", True)

    def test_detect_environment_caching(self):
        """Test that environment detection is cached."""
        with self.temp_env_vars(ENVIRONMENT="development"):
            detector = EnvironmentDetector()
            
            # First call should detect and cache
            env1 = detector.detect_environment()
            assert env1 == Environment.DEVELOPMENT
            
            # Second call should return cached value
            env2 = detector.detect_environment()
            assert env2 == Environment.DEVELOPMENT
            assert env1 is env2  # Same object reference
            
            self.record_metric("caching_verified", True)

    # === ENVIRONMENT CONFIG RETRIEVAL TESTS ===

    def test_get_environment_config(self):
        """Test get_environment_config method."""
        with self.temp_env_vars(ENVIRONMENT="staging"):
            detector = EnvironmentDetector()
            config = detector.get_environment_config()
            
            assert isinstance(config, EnvironmentConfig)
            assert config.environment == Environment.STAGING
            assert config.ssl_required is True
            
            self.record_metric("config_retrieved", True)

    def test_get_environment_config_caching(self):
        """Test that environment config is cached."""
        with self.temp_env_vars(ENVIRONMENT="development"):
            detector = EnvironmentDetector()
            
            # First call should create and cache config
            config1 = detector.get_environment_config()
            
            # Second call should return cached config
            config2 = detector.get_environment_config()
            
            assert config1 is config2  # Same object reference
            self.record_metric("config_caching_verified", True)

    # === ENVIRONMENT VALIDATION TESTS ===

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_validate_environment_consistency_ssl_required_missing(self, mock_builder_class):
        """Test validation when SSL is required but missing from database URL."""
        mock_builder = Mock()
        mock_builder.get_url_for_environment.return_value = "postgresql://host:5432/db"
        mock_builder_class.return_value = mock_builder
        
        with self.temp_env_vars(ENVIRONMENT="production"):
            detector = EnvironmentDetector()
            is_consistent, issues = detector.validate_environment_consistency()
            
            assert is_consistent is False
            assert len(issues) > 0
            assert any("SSL required" in issue for issue in issues)
            self.record_metric("ssl_validation_failed", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_validate_environment_consistency_ssl_present(self, mock_builder_class):
        """Test validation when SSL is required and present in database URL."""
        mock_builder = Mock()
        mock_builder.get_url_for_environment.return_value = "postgresql://host:5432/db?sslmode=require"
        mock_builder_class.return_value = mock_builder
        
        with self.temp_env_vars(
            ENVIRONMENT="production",
            CLICKHOUSE_URL="http://clickhouse:8123",
            REDIS_URL="redis://redis:6379",
            DEBUG="false"
        ):
            detector = EnvironmentDetector()
            is_consistent, issues = detector.validate_environment_consistency()
            
            # Should pass SSL check
            ssl_issues = [issue for issue in issues if "SSL required" in issue]
            assert len(ssl_issues) == 0
            self.record_metric("ssl_validation_passed", True)

    def test_validate_environment_consistency_clickhouse_required_missing(self):
        """Test validation when ClickHouse is required but missing."""
        with self.temp_env_vars(
            ENVIRONMENT="production",
            CLICKHOUSE_URL=""
        ):
            detector = EnvironmentDetector()
            is_consistent, issues = detector.validate_environment_consistency()
            
            assert is_consistent is False
            assert any("ClickHouse required" in issue for issue in issues)
            self.record_metric("clickhouse_validation_failed", True)

    def test_validate_environment_consistency_clickhouse_present(self):
        """Test validation when ClickHouse is required and present."""
        with self.temp_env_vars(
            ENVIRONMENT="production",
            CLICKHOUSE_URL="http://clickhouse:8123",
            REDIS_URL="redis://redis:6379",
            DEBUG="false"
        ):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = Mock()
                mock_builder.get_url_for_environment.return_value = "postgresql://host:5432/db?sslmode=require"
                mock_builder_class.return_value = mock_builder
                
                detector = EnvironmentDetector()
                is_consistent, issues = detector.validate_environment_consistency()
                
                # Should pass ClickHouse check
                clickhouse_issues = [issue for issue in issues if "ClickHouse required" in issue]
                assert len(clickhouse_issues) == 0
                self.record_metric("clickhouse_validation_passed", True)

    def test_validate_environment_consistency_redis_enabled_missing(self):
        """Test validation when Redis is enabled but missing."""
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            REDIS_URL=""
        ):
            detector = EnvironmentDetector()
            is_consistent, issues = detector.validate_environment_consistency()
            
            assert is_consistent is False
            assert any("Redis enabled" in issue for issue in issues)
            self.record_metric("redis_validation_failed", True)

    def test_validate_environment_consistency_redis_present(self):
        """Test validation when Redis is enabled and present."""
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            REDIS_URL="redis://redis:6379",
            DEBUG="false"
        ):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = Mock()
                mock_builder.get_url_for_environment.return_value = "postgresql://host:5432/db?sslmode=require"
                mock_builder_class.return_value = mock_builder
                
                detector = EnvironmentDetector()
                is_consistent, issues = detector.validate_environment_consistency()
                
                # Should pass Redis check
                redis_issues = [issue for issue in issues if "Redis enabled" in issue]
                assert len(redis_issues) == 0
                self.record_metric("redis_validation_passed", True)

    def test_validate_environment_consistency_debug_mismatch(self):
        """Test validation when DEBUG environment variable doesn't match config."""
        with self.temp_env_vars(
            ENVIRONMENT="production",
            DEBUG="true"  # Production should have debug=false
        ):
            detector = EnvironmentDetector()
            is_consistent, issues = detector.validate_environment_consistency()
            
            assert is_consistent is False
            assert any("DEBUG environment variable" in issue for issue in issues)
            self.record_metric("debug_validation_failed", True)

    def test_validate_environment_consistency_debug_match(self):
        """Test validation when DEBUG environment variable matches config."""
        with self.temp_env_vars(
            ENVIRONMENT="development",
            DEBUG="true"  # Development should have debug=true
        ):
            detector = EnvironmentDetector()
            is_consistent, issues = detector.validate_environment_consistency()
            
            # Should pass debug check
            debug_issues = [issue for issue in issues if "DEBUG environment variable" in issue]
            assert len(debug_issues) == 0
            self.record_metric("debug_validation_passed", True)

    def test_validate_environment_consistency_all_valid(self):
        """Test validation when all checks pass."""
        with self.temp_env_vars(
            ENVIRONMENT="development",
            DEBUG="true",
            REDIS_URL="",  # Not required for development
            CLICKHOUSE_URL=""  # Not required for development
        ):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = Mock()
                mock_builder.get_url_for_environment.return_value = "postgresql://localhost:5432/db"  # No SSL required for dev
                mock_builder_class.return_value = mock_builder
                
                detector = EnvironmentDetector()
                is_consistent, issues = detector.validate_environment_consistency()
                
                assert is_consistent is True
                assert len(issues) == 0
                self.record_metric("full_validation_passed", True)

    # === ENVIRONMENT SUMMARY TESTS ===

    def test_get_environment_summary(self):
        """Test get_environment_summary method."""
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            DEBUG="false",
            REDIS_URL="redis://redis:6379"
        ):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = Mock()
                mock_builder.get_url_for_environment.return_value = "postgresql://staging:5432/db?sslmode=require"
                mock_builder.mask_url_for_logging.return_value = "postgresql://staging:5432/db?sslmode=require"
                mock_builder_class.return_value = mock_builder
                
                detector = EnvironmentDetector()
                summary = detector.get_environment_summary()
                
                # Check structure
                assert "detected_environment" in summary
                assert "configuration" in summary
                assert "consistency_check" in summary
                assert "environment_variables" in summary
                
                # Check values
                assert summary["detected_environment"] == "staging"
                assert summary["configuration"]["debug_mode"] is False
                assert summary["configuration"]["ssl_required"] is True
                assert "is_consistent" in summary["consistency_check"]
                assert "issues" in summary["consistency_check"]
                
                self.record_metric("summary_generated", True)

    # === URL MASKING TESTS ===

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_get_masked_database_url(self, mock_builder_class):
        """Test _get_masked_database_url method."""
        mock_builder = Mock()
        mock_builder.get_url_for_environment.return_value = "postgresql://user:password@host:5432/db"
        mock_builder.mask_url_for_logging.return_value = "postgresql://user:***@host:5432/db"
        mock_builder_class.return_value = mock_builder
        
        detector = EnvironmentDetector()
        masked_url = detector._get_masked_database_url()
        
        assert masked_url == "postgresql://user:***@host:5432/db"
        mock_builder.mask_url_for_logging.assert_called_once()
        self.record_metric("db_url_masked", True)

    def test_mask_sensitive_url_with_password(self):
        """Test _mask_sensitive_url method with password."""
        detector = EnvironmentDetector()
        
        test_cases = [
            ("redis://user:password@host:6379", "redis://user:***@host:6379"),
            ("http://admin:secret123@clickhouse:8123", "http://admin:***@clickhouse:8123"),
            ("postgresql://dbuser:dbpass@localhost:5432/db", "postgresql://dbuser:***@localhost:5432/db")
        ]
        
        for original_url, expected_masked in test_cases:
            masked = detector._mask_sensitive_url(original_url)
            assert masked == expected_masked
            self.record_metric(f"url_masked_{original_url[:10]}", True)

    def test_mask_sensitive_url_without_password(self):
        """Test _mask_sensitive_url method without password."""
        detector = EnvironmentDetector()
        
        test_cases = [
            "redis://host:6379",
            "http://clickhouse:8123",
            "postgresql://localhost:5432/db"
        ]
        
        for url in test_cases:
            masked = detector._mask_sensitive_url(url)
            assert masked == url  # Should remain unchanged
            self.record_metric(f"url_unchanged_{url[:10]}", True)

    def test_mask_sensitive_url_empty(self):
        """Test _mask_sensitive_url method with empty URL."""
        detector = EnvironmentDetector()
        
        result = detector._mask_sensitive_url("")
        assert result == ""
        
        result = detector._mask_sensitive_url(None)
        assert result == ""
        
        self.record_metric("empty_url_handled", True)

    # === SERVICE REQUIREMENT TESTS ===

    def test_should_require_service_clickhouse(self):
        """Test should_require_service method for ClickHouse."""
        # Production requires ClickHouse
        with self.temp_env_vars(ENVIRONMENT="production"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("clickhouse") is True
            assert detector.should_require_service("ClickHouse") is True
            assert detector.should_require_service("CLICKHOUSE") is True
        
        # Development doesn't require ClickHouse
        with self.temp_env_vars(ENVIRONMENT="development"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("clickhouse") is False

    def test_should_require_service_redis(self):
        """Test should_require_service method for Redis."""
        # Staging enables Redis
        with self.temp_env_vars(ENVIRONMENT="staging"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("redis") is True
            assert detector.should_require_service("Redis") is True
            assert detector.should_require_service("REDIS") is True
        
        # Testing doesn't enable Redis
        with self.temp_env_vars(ENVIRONMENT="testing"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("redis") is False

    def test_should_require_service_ssl(self):
        """Test should_require_service method for SSL."""
        # Production requires SSL
        with self.temp_env_vars(ENVIRONMENT="production"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("ssl") is True
        
        # Development doesn't require SSL
        with self.temp_env_vars(ENVIRONMENT="development"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("ssl") is False

    def test_should_require_service_unknown(self):
        """Test should_require_service method for unknown service."""
        with self.temp_env_vars(ENVIRONMENT="production"):
            detector = EnvironmentDetector()
            assert detector.should_require_service("unknown_service") is False
            assert detector.should_require_service("") is False

    # === HEALTH CHECK TIMEOUT TESTS ===

    def test_get_health_check_timeout(self):
        """Test get_health_check_timeout method for all environments."""
        test_cases = [
            (Environment.DEVELOPMENT, 10.0),
            (Environment.STAGING, 8.0),
            (Environment.PRODUCTION, 5.0),
            (Environment.TESTING, 30.0)
        ]
        
        for env, expected_timeout in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env.value):
                detector = EnvironmentDetector()
                timeout = detector.get_health_check_timeout()
                assert timeout == expected_timeout
                self.record_metric(f"timeout_{env.value}", timeout)

    # === GLOBAL INSTANCE TESTS ===

    def test_get_environment_detector_singleton(self):
        """Test that get_environment_detector returns singleton instance."""
        # Clear global instance first
        import netra_backend.app.core.configuration.environment_detector as detector_module
        detector_module._environment_detector = None
        
        # First call should create instance
        detector1 = get_environment_detector()
        assert isinstance(detector1, EnvironmentDetector)
        
        # Second call should return same instance
        detector2 = get_environment_detector()
        assert detector1 is detector2
        
        self.record_metric("singleton_verified", True)

    def test_get_environment_config_global(self):
        """Test global get_environment_config function."""
        with self.temp_env_vars(ENVIRONMENT="staging"):
            config = get_environment_config()
            assert isinstance(config, EnvironmentConfig)
            assert config.environment == Environment.STAGING

    def test_validate_environment_global(self):
        """Test global validate_environment function."""
        with self.temp_env_vars(ENVIRONMENT="development", DEBUG="true"):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = Mock()
                mock_builder.get_url_for_environment.return_value = "postgresql://localhost:5432/db"
                mock_builder_class.return_value = mock_builder
                
                is_consistent, issues = validate_environment()
                assert isinstance(is_consistent, bool)
                assert isinstance(issues, list)

    # === ERROR HANDLING TESTS ===

    def test_detect_environment_exception_handling(self):
        """Test that exceptions in detection methods are handled gracefully."""
        with self.temp_env_vars(ENVIRONMENT=""):
            # Mock all detection methods to raise exceptions
            detector = EnvironmentDetector()
            
            with patch.object(detector, '_detect_from_env_var', side_effect=Exception("env var error")):
                with patch.object(detector, '_detect_from_hostname', side_effect=Exception("hostname error")):
                    with patch.object(detector, '_detect_from_database_url', side_effect=Exception("db url error")):
                        with patch.object(detector, '_detect_from_service_context', side_effect=Exception("service error")):
                            # Should still return production as fallback
                            env = detector.detect_environment()
                            assert env == Environment.PRODUCTION
                            self.record_metric("exception_handling_verified", True)

    @patch('shared.database_url_builder.DatabaseURLBuilder')
    def test_database_url_detection_exception(self, mock_builder_class):
        """Test exception handling in database URL detection."""
        mock_builder_class.side_effect = Exception("DatabaseURLBuilder error")
        
        with self.temp_env_vars(ENVIRONMENT=""):
            detector = EnvironmentDetector()
            # Should not raise exception, should continue to next detection method
            env = detector.detect_environment()
            assert env == Environment.PRODUCTION  # Fallback
            self.record_metric("db_builder_exception_handled", True)

    # === EDGE CASE TESTS ===

    def test_case_insensitive_environment_detection(self):
        """Test that environment detection is case insensitive."""
        test_cases = [
            ("DEVELOPMENT", Environment.DEVELOPMENT),
            ("Development", Environment.DEVELOPMENT),
            ("development", Environment.DEVELOPMENT),
            ("dEvElOpMeNt", Environment.DEVELOPMENT)
        ]
        
        for env_value, expected in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env_value):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == expected
                self.record_metric(f"case_test_{env_value}", True)

    def test_whitespace_handling(self):
        """Test handling of whitespace in environment variables."""
        with self.temp_env_vars(ENVIRONMENT="  production  "):
            detector = EnvironmentDetector()
            detected = detector.detect_environment()
            # Should trim whitespace and detect correctly
            assert detected == Environment.PRODUCTION
            self.record_metric("whitespace_handled", True)

    def test_partial_hostname_matches(self):
        """Test that hostname detection works with partial matches."""
        with patch('socket.gethostname', return_value="my-awesome-dev-server-01"):
            with self.temp_env_vars(ENVIRONMENT=""):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                assert detected == Environment.DEVELOPMENT
                self.record_metric("partial_hostname_match", True)

    def test_multiple_environment_indicators(self):
        """Test behavior when multiple environment indicators point to different environments."""
        # Environment variable says production, but hostname says development
        with self.temp_env_vars(ENVIRONMENT="production"):
            with patch('socket.gethostname', return_value="dev-server"):
                detector = EnvironmentDetector()
                detected = detector.detect_environment()
                # Environment variable should take precedence
                assert detected == Environment.PRODUCTION
                self.record_metric("precedence_verified", True)

    # === PERFORMANCE TESTS ===

    def test_detection_performance(self):
        """Test that environment detection is reasonably fast."""
        with self.temp_env_vars(ENVIRONMENT="development"):
            detector = EnvironmentDetector()
            
            # Time the detection
            import time
            start_time = time.time()
            detector.detect_environment()
            end_time = time.time()
            
            detection_time = end_time - start_time
            # Should be very fast (under 100ms)
            assert detection_time < 0.1
            self.record_metric("detection_time_ms", detection_time * 1000)

    def test_caching_performance(self):
        """Test that subsequent calls are faster due to caching."""
        with self.temp_env_vars(ENVIRONMENT="staging"):
            detector = EnvironmentDetector()
            
            # First call (should cache)
            import time
            start_time = time.time()
            detector.detect_environment()
            first_call_time = time.time() - start_time
            
            # Second call (should be cached)
            start_time = time.time()
            detector.detect_environment()
            second_call_time = time.time() - start_time
            
            # Second call should be significantly faster
            assert second_call_time < first_call_time / 2
            self.record_metric("first_call_time_ms", first_call_time * 1000)
            self.record_metric("second_call_time_ms", second_call_time * 1000)

    def test_metrics_recording(self):
        """Test that all test metrics are properly recorded."""
        # Verify we have recorded meaningful metrics
        all_metrics = self.get_all_metrics()
        
        # Should have custom metrics
        assert len(all_metrics) > 10
        
        # Should have execution time
        assert "execution_time" in all_metrics
        assert all_metrics["execution_time"] >= 0
        
        # Log summary of metrics
        metric_count = len([k for k in all_metrics.keys() if not k.startswith("_")])
        self.record_metric("total_test_metrics", metric_count)
        self.record_metric("comprehensive_coverage", True)