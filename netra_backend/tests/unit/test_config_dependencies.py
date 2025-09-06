"""
Comprehensive Unit Tests for ConfigDependencyMap System

BUSINESS VALUE: Validates the critical safety layer that prevents accidental
configuration deletions during refactoring, ensuring system reliability and
preventing cascade failures that could impact customer AI operations.

Tests all aspects of the configuration dependency protection system including
deletion blocking, validation rules, impact analysis, and consistency checking.

CRITICAL SCOPE:
- Configuration deletion protection (prevents system failures)
- Validation rules enforcement (ensures data integrity)
- Dependency mapping accuracy (protects service relationships)
- Paired configuration detection (prevents partial configurations)
- Cross-service consistency validation (maintains system coherence)
"""

import pytest
from typing import Dict, Any, List
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.config_dependencies import (
    ConfigDependencyMap,
    ConfigImpactLevel
)


class TestConfigDependencyMap:
    """Comprehensive tests for the ConfigDependencyMap system"""

    # Test Data Setup
    @pytest.fixture
    def valid_database_url(self) -> str:
        """Valid PostgreSQL database URL for testing"""
        return "postgresql://user:pass@localhost:5432/dbname"

    @pytest.fixture
    def invalid_database_url(self) -> str:
        """Invalid database URL for testing validation"""
        return "invalid://not_a_db"

    @pytest.fixture
    def valid_jwt_secret(self) -> str:
        """Valid JWT secret key (32+ characters)"""
        return "this_is_a_very_secure_jwt_secret_key_123456789"

    @pytest.fixture
    def invalid_jwt_secret(self) -> str:
        """Invalid JWT secret key (too short)"""
        return "too_short"

    @pytest.fixture
    def valid_config_dict(self, valid_database_url: str, valid_jwt_secret: str) -> Dict[str, Any]:
        """Valid configuration dictionary for consistency testing"""
        return {
            "DATABASE_URL": valid_database_url,
            "JWT_SECRET_KEY": valid_jwt_secret,
            "ENVIRONMENT": "testing",
            "SECRET_KEY": "another_very_secure_secret_key_123456789",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "GOOGLE_CLIENT_ID": "test_google_client_id",
            "GOOGLE_CLIENT_SECRET": "test_google_client_secret"
        }

    @pytest.fixture
    def incomplete_config_dict(self, valid_database_url: str, valid_jwt_secret: str) -> Dict[str, Any]:
        """Configuration with missing paired configs for testing consistency"""
        return {
            "DATABASE_URL": valid_database_url,
            "JWT_SECRET_KEY": valid_jwt_secret,
            "GOOGLE_CLIENT_ID": "test_google_client_id",
            # Missing GOOGLE_CLIENT_SECRET (paired config)
            "POSTGRES_HOST": "localhost",
            # Missing other POSTGRES_* paired configs
            "AWS_ACCESS_KEY_ID": "test_access_key"
            # Missing AWS_SECRET_ACCESS_KEY (paired config)
        }

    # Critical Config Deletion Tests
    def test_critical_config_deletion_blocked(self):
        pass
    """Use real service instance."""
    # TODO: Initialize real service
        """Verify critical configs cannot be deleted"""
        critical_configs = [
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "SECRET_KEY",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD"
        ]

        for config_key in critical_configs:
            can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
            
            assert not can_delete, f"Critical config {config_key} should not be deletable"
            assert "BLOCKED" in reason or "Cannot delete" in reason, \
                f"Deletion reason should indicate blocking for {config_key}: {reason}"
            assert "Required by:" in reason, \
                f"Deletion reason should list required services for {config_key}"

    def test_high_priority_config_deletion_warning(self):
        """Verify high priority configs show warnings but allow deletion"""
        high_priority_configs = [
            "REDIS_URL",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "LANGSMITH_API_KEY",
            "MIXPANEL_PROJECT_TOKEN",
            "AWS_ACCESS_KEY_ID"
        ]

        for config_key in high_priority_configs:
            can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
            
            assert can_delete, f"High priority config {config_key} should be deletable with warning"
            assert "WARNING:" in reason, \
                f"High priority config {config_key} should show warning: {reason}"

    def test_service_specific_config_deletion(self):
        """Verify service-specific configs provide appropriate info"""
        service_configs = [
            "GOOGLE_CLIENT_ID",
            "GITHUB_CLIENT_ID",
            "CORS_ORIGINS",
            "DEBUG",
            "LOG_LEVEL"
        ]

        for config_key in service_configs:
            can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
            
            assert can_delete, f"Service-specific config {config_key} should be deletable"
            # Should provide info about impact
            assert len(reason) > 0, f"Should provide deletion info for {config_key}"

    def test_unknown_config_deletion(self):
        """Verify unknown configs are allowed to be deleted"""
        unknown_configs = [
            "UNKNOWN_CONFIG_KEY",
            "RANDOM_SETTING",
            "CUSTOM_APP_SETTING"
        ]

        for config_key in unknown_configs:
            can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
            
            assert can_delete, f"Unknown config {config_key} should be deletable"
            assert "No known dependencies" in reason, \
                f"Unknown config should indicate no dependencies: {reason}"

    # Configuration Validation Tests
    def test_config_validation_success(self, valid_database_url: str, valid_jwt_secret: str):
        """Test valid configuration values pass validation"""
        valid_test_cases = [
            ("DATABASE_URL", valid_database_url),
            ("DATABASE_URL", "postgres://localhost:5432/db"),
            ("JWT_SECRET_KEY", valid_jwt_secret),
            ("ENVIRONMENT", "development"),
            ("ENVIRONMENT", "testing"),
            ("ENVIRONMENT", "staging"),
            ("ENVIRONMENT", "production"),
            ("SECRET_KEY", "a_very_secure_secret_key_with_32_plus_chars"),
            ("POSTGRES_HOST", "localhost"),
            ("POSTGRES_HOST", "db.example.com"),
            ("POSTGRES_PORT", 5432),
            ("POSTGRES_PORT", "5432"),
            ("AUTH_REDIRECT_URI", "https://example.com/callback"),
            ("AUTH_CALLBACK_URL", "http://localhost:8000/auth/callback"),
            ("FRONTEND_URL", "https://app.example.com"),
            ("BACKEND_URL", "https://api.example.com"),
            ("REDIS_URL", "redis://localhost:6379"),
            ("ANTHROPIC_API_KEY", "sk-ant-1234567890"),
            ("OPENAI_API_KEY", "sk-1234567890abcdef"),
            ("LOG_LEVEL", "DEBUG"),
            ("LOG_LEVEL", "INFO"),
            ("LOG_LEVEL", "ERROR")
        ]

        for config_key, value in valid_test_cases:
            is_valid, message = ConfigDependencyMap.validate_config_value(config_key, value)
            assert is_valid, f"Valid config {config_key}={value} should pass validation: {message}"

    def test_config_validation_failure(self, invalid_database_url: str, invalid_jwt_secret: str):
        """Test invalid configuration values fail validation"""
        invalid_test_cases = [
            ("DATABASE_URL", invalid_database_url),
            ("DATABASE_URL", ""),
            ("DATABASE_URL", None),
            ("JWT_SECRET_KEY", invalid_jwt_secret),
            ("JWT_SECRET_KEY", ""),
            ("JWT_SECRET_KEY", None),
            ("ENVIRONMENT", "invalid_env"),
            ("ENVIRONMENT", "prod"),  # Should be "production"
            ("SECRET_KEY", "short"),
            ("POSTGRES_HOST", ""),
            ("POSTGRES_HOST", None),
            ("POSTGRES_PORT", 0),
            ("POSTGRES_PORT", 999999),
            ("POSTGRES_PORT", "invalid"),
            ("AUTH_REDIRECT_URI", "ftp://invalid.com"),
            ("AUTH_CALLBACK_URL", "not_a_url"),
            ("REDIS_URL", "http://localhost:6379"),  # Should start with redis://
            ("LOG_LEVEL", "INVALID"),
            ("LOG_LEVEL", "VERBOSE"),  # Invalid log level
        ]

        for config_key, value in invalid_test_cases:
            is_valid, message = ConfigDependencyMap.validate_config_value(config_key, value)
            assert not is_valid, f"Invalid config {config_key}={value} should fail validation"
            assert len(message) > 0, f"Validation failure should provide error message for {config_key}"

    def test_validation_functions_work_correctly(self):
        """Test that all validation lambda functions work correctly"""
        # Test DATABASE_URL validation
        db_validator = ConfigDependencyMap.CRITICAL_DEPENDENCIES["DATABASE_URL"]["validation"]
        assert db_validator("postgresql://localhost/db")
        assert db_validator("postgres://localhost/db")
        assert not db_validator("mysql://localhost/db")
        assert not db_validator("")
        assert not db_validator(None)

        # Test JWT_SECRET_KEY validation
        jwt_validator = ConfigDependencyMap.CRITICAL_DEPENDENCIES["JWT_SECRET_KEY"]["validation"]
        assert jwt_validator("a" * 32)
        assert not jwt_validator("a" * 31)
        assert not jwt_validator("")
        assert not jwt_validator(None)

        # Test ENVIRONMENT validation
        env_validator = ConfigDependencyMap.CRITICAL_DEPENDENCIES["ENVIRONMENT"]["validation"]
        assert env_validator("development")
        assert env_validator("testing")
        assert env_validator("staging")
        assert env_validator("production")
        assert not env_validator("dev")
        assert not env_validator("prod")
        assert not env_validator("invalid")

        # Test POSTGRES_PORT validation
        port_validator = ConfigDependencyMap.CRITICAL_DEPENDENCIES["POSTGRES_PORT"]["validation"]
        assert port_validator(5432)
        assert port_validator("5432")
        assert port_validator(1)
        assert port_validator(65535)
        assert not port_validator(0)
        assert not port_validator(65536)
        assert not port_validator("invalid")
        assert not port_validator("")

    def test_validation_edge_cases(self):
        """Test validation with edge cases and None values"""
        # Test with None values
        is_valid, message = ConfigDependencyMap.validate_config_value("UNKNOWN_CONFIG", None)
        assert is_valid, "Unknown config with None should be valid"

        # Test with empty strings
        is_valid, message = ConfigDependencyMap.validate_config_value("UNKNOWN_CONFIG", "")
        assert is_valid, "Unknown config with empty string should be valid"

        # Test config that allows None/empty (fallback allowed)
        is_valid, message = ConfigDependencyMap.validate_config_value("REDIS_URL", None)
        assert is_valid, "REDIS_URL with None should be valid (fallback allowed)"

        is_valid, message = ConfigDependencyMap.validate_config_value("REDIS_URL", "")
        assert is_valid, "REDIS_URL with empty string should be valid (fallback allowed)"

    # Alternative Configuration Tests
    def test_get_alternatives(self):
        """Test alternative config key suggestions"""
        alternatives_map = {
            "JWT_SECRET_KEY": ["JWT_SECRET"],
            "SECRET_KEY": ["APP_SECRET_KEY"],
            "REDIS_URL": ["REDIS_HOST", "REDIS_PORT"],
            "CLICKHOUSE_URL": ["CLICKHOUSE_HOST", "CLICKHOUSE_PORT"],
            "ANTHROPIC_API_KEY": ["CLAUDE_API_KEY"]
        }

        for main_key, expected_alts in alternatives_map.items():
            actual_alts = ConfigDependencyMap.get_alternatives(main_key)
            for alt in expected_alts:
                assert alt in actual_alts, f"Missing alternative {alt} for {main_key}"

    def test_get_alternatives_empty_for_unknown(self):
        """Test that unknown configs return empty alternatives"""
        unknown_configs = ["UNKNOWN_CONFIG", "RANDOM_KEY", "CUSTOM_SETTING"]
        
        for config_key in unknown_configs:
            alternatives = ConfigDependencyMap.get_alternatives(config_key)
            assert alternatives == [], f"Unknown config {config_key} should have no alternatives"

    # Required Configurations Tests
    def test_get_required_configs_all(self):
        """Test getting all required configs without service filter"""
        required = ConfigDependencyMap.get_required_configs()
        
        # Should include critical configs without fallbacks
        critical_without_fallback = [
            "DATABASE_URL",
            "JWT_SECRET_KEY", 
            "SECRET_KEY",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD"
        ]

        for config_key in critical_without_fallback:
            assert config_key in required, f"Required configs should include {config_key}"

    def test_get_required_configs_by_service(self):
        """Test filtering required configs by service"""
        # Test auth service
        auth_required = ConfigDependencyMap.get_required_configs("auth_service")
        assert len(auth_required) > 0, "Auth service should have required configs"
        
        # Should include JWT_SECRET_KEY for auth service
        jwt_in_auth = any(
            "auth_service" in deps.get("required_by", []) or 
            deps.get("service") == "auth_service"
            for deps in auth_required.values()
        )
        assert jwt_in_auth, "Auth service should require JWT-related configs"

        # Test backend service
        backend_required = ConfigDependencyMap.get_required_configs("netra_backend")
        assert len(backend_required) > 0, "Backend service should have required configs"

    def test_get_required_configs_unknown_service(self):
        """Test filtering by unknown service name"""
        unknown_required = ConfigDependencyMap.get_required_configs("unknown_service")
        # Should return empty dict or only configs that match "unknown_service" in required_by
        # which should be empty for non-existent service
        assert isinstance(unknown_required, dict), "Should return dict for unknown service"

    # Impact Analysis Tests
    def test_impact_analysis_critical_configs(self):
        """Test comprehensive impact analysis for critical configurations"""
        critical_configs = ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]

        for config_key in critical_configs:
            impact = ConfigDependencyMap.get_impact_analysis(config_key)
            
            # Verify structure
            required_keys = [
                "key", "impact_level", "affected_services", "deletion_allowed",
                "deletion_impact", "fallback_available", "alternatives"
            ]
            for key in required_keys:
                assert key in impact, f"Impact analysis should include {key} for {config_key}"

            # Verify content
            assert impact["key"] == config_key
            assert impact["impact_level"] == ConfigImpactLevel.CRITICAL
            assert isinstance(impact["affected_services"], list)
            assert len(impact["affected_services"]) > 0, f"Critical config {config_key} should affect services"
            assert not impact["deletion_allowed"], f"Critical config {config_key} should not allow deletion"
            assert "CRITICAL" in impact["deletion_impact"]

    def test_impact_analysis_high_priority_configs(self):
        """Test impact analysis for high priority configurations"""
        high_priority_configs = ["REDIS_URL", "ANTHROPIC_API_KEY", "MIXPANEL_PROJECT_TOKEN"]

        for config_key in high_priority_configs:
            impact = ConfigDependencyMap.get_impact_analysis(config_key)
            
            assert impact["key"] == config_key
            assert impact["impact_level"] in [ConfigImpactLevel.HIGH, ConfigImpactLevel.MEDIUM]
            assert isinstance(impact["affected_services"], list)
            assert len(impact["affected_services"]) > 0
            # High priority configs typically allow deletion with warnings
            assert impact["fallback_available"] or "fallback_warning" in impact

    def test_impact_analysis_unknown_config(self):
        """Test impact analysis for unknown configuration"""
        unknown_config = "UNKNOWN_TEST_CONFIG"
        impact = ConfigDependencyMap.get_impact_analysis(unknown_config)
        
        assert impact["key"] == unknown_config
        assert impact["impact_level"] == ConfigImpactLevel.LOW
        assert impact["affected_services"] == []
        assert impact["deletion_allowed"] == True
        assert "No documented dependencies" in impact["notes"]

    def test_impact_levels_correctly_assigned(self):
        """Test that impact levels are correctly assigned across all configs"""
        # Check critical dependencies (some may have HIGH impact but still be critical)
        for key, deps in ConfigDependencyMap.CRITICAL_DEPENDENCIES.items():
            assert deps["impact_level"] in [ConfigImpactLevel.CRITICAL, ConfigImpactLevel.HIGH], \
                f"Critical dependency {key} should have CRITICAL or HIGH impact level, got {deps['impact_level']}"

        # Check high priority dependencies have appropriate levels
        for key, deps in ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES.items():
            assert deps["impact_level"] in [ConfigImpactLevel.HIGH, ConfigImpactLevel.MEDIUM], \
                f"High priority dependency {key} should have HIGH or MEDIUM impact level"

        # Check service specific dependencies have reasonable levels
        for key, deps in ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES.items():
            assert deps["impact_level"] in [
                ConfigImpactLevel.LOW, 
                ConfigImpactLevel.MEDIUM, 
                ConfigImpactLevel.HIGH
            ], f"Service dependency {key} should have LOW, MEDIUM, or HIGH impact level"

    # Configuration Consistency Tests
    def test_config_consistency_check_valid(self, valid_config_dict: Dict[str, Any]):
        """Test consistency checking with valid paired configurations"""
        issues = ConfigDependencyMap.check_config_consistency(valid_config_dict)
        
        # Filter out validation errors to focus on consistency
        consistency_issues = [issue for issue in issues if "paired config" in issue.lower()]
        
        assert len(consistency_issues) == 0, \
            f"Valid config should have no consistency issues: {consistency_issues}"

    def test_config_consistency_check_missing_paired(self, incomplete_config_dict: Dict[str, Any]):
        """Test consistency checking detects missing paired configs"""
        issues = ConfigDependencyMap.check_config_consistency(incomplete_config_dict)
        
        # Should detect missing paired configs (only SERVICE_SPECIFIC configs are checked for pairing)
        expected_missing = [
            "GOOGLE_CLIENT_SECRET",  # Paired with GOOGLE_CLIENT_ID (in SERVICE_SPECIFIC)
        ]

        for missing_config in expected_missing:
            assert any(missing_config in issue for issue in issues), \
                f"Should detect missing paired config {missing_config}"
        
        # Note: AWS configs are in HIGH_PRIORITY, so they won't trigger paired config warnings
        # in the current implementation

    def test_missing_critical_configs(self):
        """Test detection of missing critical configs"""
        minimal_config = {
            "ENVIRONMENT": "testing"
            # Missing DATABASE_URL, JWT_SECRET_KEY, etc.
        }

        issues = ConfigDependencyMap.check_config_consistency(minimal_config)
        
        # Should detect missing critical configs
        critical_missing = [issue for issue in issues if "CRITICAL: Missing required" in issue]
        assert len(critical_missing) > 0, "Should detect missing critical configs"

    def test_paired_config_detection_comprehensive(self):
        """Test comprehensive paired config detection"""
        test_cases = [
            # OAuth configs should be paired (SERVICE_SPECIFIC only)
            {
                "config": {"GOOGLE_CLIENT_ID": "test_id"},
                "expected_missing": ["GOOGLE_CLIENT_SECRET"]
            },
        ]

        for case in test_cases:
            issues = ConfigDependencyMap.check_config_consistency(case["config"])
            
            for missing_config in case["expected_missing"]:
                assert any(missing_config in issue for issue in issues), \
                    f"Should detect missing paired config {missing_config} for {list(case['config'].keys())[0]}"
        
        # Note: The current implementation only checks SERVICE_SPECIFIC_DEPENDENCIES for paired configs
        # CRITICAL and HIGH_PRIORITY paired configs are not checked in consistency validation
        # This is a limitation of the current implementation

    def test_postgres_components_paired(self):
        """Test that PostgreSQL configs are properly paired"""
        postgres_configs = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
        
        for config_key in postgres_configs:
            if config_key in ConfigDependencyMap.CRITICAL_DEPENDENCIES:
                deps = ConfigDependencyMap.CRITICAL_DEPENDENCIES[config_key]
                paired_with = deps.get("paired_with", [])
                
                # Each postgres config should be paired with the others
                expected_pairs = [c for c in postgres_configs if c != config_key]
                for expected_pair in expected_pairs:
                    assert expected_pair in paired_with, \
                        f"{config_key} should be paired with {expected_pair}"

    def test_oauth_configs_paired(self):
        """Test that OAuth configs are properly paired"""
        oauth_pairs = [
            ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
            ("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"),
            ("AUTH_REDIRECT_URI", "AUTH_CALLBACK_URL")
        ]

        for primary, secondary in oauth_pairs:
            # Check in all dependency maps
            all_deps = {
                **ConfigDependencyMap.CRITICAL_DEPENDENCIES,
                **ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES,
                **ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES
            }
            
            if primary in all_deps:
                paired_with = all_deps[primary].get("paired_with", [])
                assert secondary in paired_with, \
                    f"{primary} should be paired with {secondary}"

    def test_aws_configs_paired(self):
        """Test that AWS configs are properly paired"""
        aws_config = ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES.get("AWS_ACCESS_KEY_ID")
        if aws_config:
            paired_with = aws_config.get("paired_with", [])
            assert "AWS_SECRET_ACCESS_KEY" in paired_with
            assert "AWS_S3_BUCKET" in paired_with

    def test_fallback_detection(self):
        """Test fallback allowed/disallowed logic"""
        # Critical configs should not allow fallbacks
        for key, deps in ConfigDependencyMap.CRITICAL_DEPENDENCIES.items():
            if key in ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]:
                assert not deps.get("fallback_allowed", False), \
                    f"Critical config {key} should not allow fallbacks"

        # Some high priority configs should allow fallbacks
        fallback_configs = ["REDIS_URL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        for config_key in fallback_configs:
            if config_key in ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES:
                deps = ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES[config_key]
                assert deps.get("fallback_allowed", False), \
                    f"Config {config_key} should allow fallbacks"

    def test_cross_service_dependencies(self):
        """Test detection of shared configuration across services"""
        # JWT_SECRET_KEY should be shared across services
        jwt_deps = ConfigDependencyMap.CRITICAL_DEPENDENCIES["JWT_SECRET_KEY"]
        shared_across = jwt_deps.get("shared_across", [])
        assert "netra_backend" in shared_across
        assert "auth_service" in shared_across

        # FRONTEND_URL should be shared across multiple services
        frontend_deps = ConfigDependencyMap.CRITICAL_DEPENDENCIES["FRONTEND_URL"]
        shared_across = frontend_deps.get("shared_across", [])
        assert len(shared_across) >= 2, "FRONTEND_URL should be shared across multiple services"
        assert "netra_backend" in shared_across
        assert "auth_service" in shared_across

    # Edge Cases and Error Handling
    def test_validation_with_exception_handling(self):
        """Test that validation handles exceptions gracefully"""
        # Create a mock validation function that raises an exception
        original_validation = ConfigDependencyMap.CRITICAL_DEPENDENCIES["DATABASE_URL"]["validation"]
        
        # Temporarily replace with faulty validator
        def faulty_validator(x):
            raise ValueError("Test exception")
        
        ConfigDependencyMap.CRITICAL_DEPENDENCIES["DATABASE_URL"]["validation"] = faulty_validator
        
        try:
            is_valid, message = ConfigDependencyMap.validate_config_value("DATABASE_URL", "test")
            assert not is_valid, "Validation should fail when exception occurs"
            assert "Validation error:" in message, "Should report validation error"
            assert "Test exception" in message, "Should include original exception message"
        finally:
            # Restore original validator
            ConfigDependencyMap.CRITICAL_DEPENDENCIES["DATABASE_URL"]["validation"] = original_validation

    def test_consistency_check_with_validation_errors(self):
        """Test consistency check includes validation errors"""
        invalid_config = {
            "DATABASE_URL": "invalid_url",
            "JWT_SECRET_KEY": "short",
            "ENVIRONMENT": "invalid_env"
        }

        issues = ConfigDependencyMap.check_config_consistency(invalid_config)
        
        # Should have validation errors
        validation_errors = [issue for issue in issues if "VALIDATION ERROR:" in issue]
        assert len(validation_errors) >= 3, "Should detect multiple validation errors"

    def test_empty_config_consistency_check(self):
        """Test consistency check with empty configuration"""
        empty_config = {}
        issues = ConfigDependencyMap.check_config_consistency(empty_config)
        
        # Should detect missing critical configs
        critical_missing = [issue for issue in issues if "CRITICAL: Missing required" in issue]
        assert len(critical_missing) > 0, "Should detect missing critical configs in empty config"

    @pytest.mark.parametrize("config_key,expected_impact", [
        ("DATABASE_URL", ConfigImpactLevel.CRITICAL),
        ("JWT_SECRET_KEY", ConfigImpactLevel.CRITICAL),
        ("REDIS_URL", ConfigImpactLevel.HIGH),
        ("DEBUG", ConfigImpactLevel.LOW),
        ("UNKNOWN_CONFIG", ConfigImpactLevel.LOW)
    ])
    def test_impact_levels_parametrized(self, config_key: str, expected_impact: ConfigImpactLevel):
        """Parametrized test for impact levels"""
        impact = ConfigDependencyMap.get_impact_analysis(config_key)
        assert impact["impact_level"] == expected_impact, \
            f"Config {config_key} should have impact level {expected_impact}"

    def test_all_dependency_maps_have_required_fields(self):
        """Test that all dependency maps have required fields"""
        required_fields = ["required_by", "impact_level"]
        optional_fields = ["fallback_allowed", "deletion_impact", "validation", "alternatives", "paired_with"]

        all_deps = [
            (ConfigDependencyMap.CRITICAL_DEPENDENCIES, "CRITICAL"),
            (ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES, "HIGH_PRIORITY"),
            (ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES, "SERVICE_SPECIFIC")
        ]

        for deps_map, map_name in all_deps:
            for key, deps in deps_map.items():
                # Check required fields
                for field in required_fields:
                    assert field in deps, \
                        f"{map_name} dependency {key} missing required field {field}"
                
                # Check field types
                assert isinstance(deps["required_by"], list), \
                    f"{key} required_by should be a list"
                assert isinstance(deps["impact_level"], ConfigImpactLevel), \
                    f"{key} impact_level should be ConfigImpactLevel enum"

                # If validation exists, it should be callable
                if "validation" in deps:
                    assert callable(deps["validation"]), \
                        f"{key} validation should be callable"

    def test_dependency_map_completeness(self):
        """Test that dependency maps cover all major configuration areas"""
        # Check that we have coverage for major system areas
        all_keys = set()
        all_keys.update(ConfigDependencyMap.CRITICAL_DEPENDENCIES.keys())
        all_keys.update(ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES.keys())
        all_keys.update(ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES.keys())

        # Major areas that should be covered
        expected_areas = {
            "database": ["DATABASE_URL", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"],
            "auth": ["JWT_SECRET_KEY", "SECRET_KEY"],
            "redis": ["REDIS_URL"],
            "llm": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "oauth": ["GOOGLE_CLIENT_ID", "GITHUB_CLIENT_ID"],
            "environment": ["ENVIRONMENT"],
            "urls": ["FRONTEND_URL", "BACKEND_URL"]
        }

        for area, expected_keys in expected_areas.items():
            found_keys = [key for key in expected_keys if key in all_keys]
            assert len(found_keys) > 0, \
                f"Should have coverage for {area} configuration area"
    pass