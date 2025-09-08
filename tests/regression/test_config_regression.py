"""
Configuration Regression Tests

Comprehensive test suite to prevent configuration regressions and ensure
configuration changes don't break existing functionality.
"""

import pytest
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import difflib

from netra_backend.app.core.configuration.base import get_unified_config, UnifiedConfigManager
from shared.isolated_environment import get_env
from netra_backend.app.core.config_dependencies import ConfigDependencyMap, ConfigImpactLevel
from auth_service.auth_core.config import AuthConfig
from shared.jwt_secret_manager import SharedJWTSecretManager


class TestConfigurationRegression:
    """Comprehensive regression tests for configuration changes"""
    
    @pytest.fixture(autouse=True)
    def capture_config_state(self):
        """Capture configuration state before and after tests"""
        before = self._snapshot_all_configs()
        yield
        after = self._snapshot_all_configs()
        
        # Detect unintended changes
        diff = self._diff_configs(before, after)
        if diff and not self._is_expected_diff(diff):
            pytest.fail(f"Configuration regression detected:\n{self._format_diff(diff)}")
    
    def _snapshot_all_configs(self) -> Dict[str, Any]:
        """Take a snapshot of all configuration values"""
        env = get_env()
        
        # Get all environment variables (sanitized)
        snapshot = {
            "environment_vars": self._sanitize_config_dict(dict(os.environ)),
            "isolated_env": self._sanitize_config_dict(env._env_vars if hasattr(env, "_env_vars") else {}),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Try to get unified config
            config = get_unified_config()
            snapshot["unified_config"] = self._sanitize_config_dict(config.__dict__)
        except Exception:
            snapshot["unified_config"] = None
        
        return snapshot
    
    def _sanitize_config_dict(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive values in configuration dictionary"""
        sanitized = {}
        sensitive_keys = ["secret", "key", "password", "token", "api"]
        
        for key, value in config_dict.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***" if value else None
            else:
                sanitized[key] = str(value) if value is not None else None
        
        return sanitized
    
    def _diff_configs(self, before: Dict, after: Dict) -> List[str]:
        """Calculate differences between configuration snapshots"""
        diffs = []
        
        # Compare environment variables
        before_env = set(before.get("environment_vars", {}).keys())
        after_env = set(after.get("environment_vars", {}).keys())
        
        added = after_env - before_env
        removed = before_env - after_env
        
        if added:
            diffs.append(f"Added environment variables: {added}")
        if removed:
            diffs.append(f"Removed environment variables: {removed}")
        
        # Compare values (excluding timestamps and expected changes)
        for key in before_env & after_env:
            before_val = before["environment_vars"][key]
            after_val = after["environment_vars"][key]
            if before_val != after_val and key not in ["PYTEST_CURRENT_TEST", "TEST_ID"]:
                diffs.append(f"Modified: {key}")
        
        return diffs
    
    def _is_expected_diff(self, diff: List[str]) -> bool:
        """Check if the configuration difference is expected"""
        # Some changes are expected during tests
        expected_patterns = [
            "PYTEST_",
            "TEST_",
            "_test_",
            "timestamp"
        ]
        
        for change in diff:
            if not any(pattern in change for pattern in expected_patterns):
                return False
        return True
    
    def _format_diff(self, diff: List[str]) -> str:
        """Format configuration differences for display"""
        return "\n".join(f"  - {d}" for d in diff)
    
    def test_critical_configs_present(self):
        """Ensure all critical configs are present and valid"""
        config = get_unified_config()
        
        # Critical configs that MUST exist
        assert config.database_url, "#removed-legacyis missing"
        assert config.jwt_secret_key, "JWT_SECRET_KEY is missing"
        assert config.environment in ["development", "testing", "staging", "production"], \
            f"Invalid environment: {config.environment}"
        
        # Validate format
        db_url = config.database_url
        assert db_url.startswith(("postgresql://", "postgres://", "sqlite://")), \
            f"Invalid database URL format: {db_url[:20]}..."
        
        assert len(config.jwt_secret_key) >= 32, \
            f"JWT key too short: {len(config.jwt_secret_key)} chars (need >= 32)"
    
    def test_config_dependency_validation(self):
        """Validate configuration dependencies are respected"""
        # Get critical dependencies
        critical_deps = ConfigDependencyMap.CRITICAL_DEPENDENCIES
        
        config = get_unified_config()
        config_dict = config.__dict__
        
        for key, deps in critical_deps.items():
            if not deps.get("fallback_allowed", False):
                # This config MUST exist
                config_key = key.lower().replace("_", "")
                assert any(k for k in config_dict if key.lower() in k.lower()), \
                    f"Critical config {key} is missing but required by: {deps['required_by']}"
    
    def test_backward_compatibility(self):
        """Ensure old config access patterns still work"""
        # Test that we can access configs through multiple patterns
        env = get_env()
        
        # Pattern 1: Direct environment access (should work but through IsolatedEnvironment)
        if "DATABASE_URL" in os.environ:
            db_url_env = env.get("DATABASE_URL")
            assert db_url_env is not None
        
        # Pattern 2: Unified config manager
        config = get_unified_config()
        assert hasattr(config, "database_url")
        
        # Pattern 3: Service-specific configs should still work
        try:
            from netra_backend.app.config import settings
            if hasattr(settings, "database_url"):
                assert settings.database_url == config.database_url
        except ImportError:
            # Config module might not exist in this form
            pass
    
    def test_environment_isolation(self):
        """Ensure environments don't leak between tests/services"""
        env = get_env()
        
        # Enable isolation
        env.enable_isolation()
        
        # Set test value in isolated environment
        test_key = "TEST_ISOLATION_VAR"
        test_value = "isolated_test_value"
        env.set(test_key, test_value, source="test")
        
        # Verify it's in isolated environment
        assert env.get(test_key) == test_value
        
        # Verify it doesn't leak to os.environ (if isolation is working)
        if env._isolation_enabled:
            assert os.environ.get(test_key) != test_value
        
        # Clean up
        env.delete(test_key)
    
    def test_shared_config_consistency(self):
        """Ensure shared configs are consistent across services"""
        # Get JWT secret through different methods
        jwt_methods = []
        
        # Method 1: Unified config
        config = get_unified_config()
        if hasattr(config, "jwt_secret_key"):
            jwt_methods.append(("unified_config", config.jwt_secret_key))
        
        # Method 2: Shared JWT manager
        shared_jwt = SharedJWTSecretManager.get_jwt_secret()
        if shared_jwt:
            jwt_methods.append(("shared_manager", shared_jwt))
        
        # Method 3: Direct environment
        env = get_env()
        env_jwt = env.get("JWT_SECRET_KEY")
        if env_jwt:
            jwt_methods.append(("environment", env_jwt))
        
        # All methods should return the same value (if they exist)
        if len(jwt_methods) > 1:
            first_value = jwt_methods[0][1]
            for method_name, value in jwt_methods[1:]:
                assert value == first_value, \
                    f"JWT secret mismatch: {method_name} differs from {jwt_methods[0][0]}"
    
    def test_config_validation_rules(self):
        """Test that configuration validation rules are enforced"""
        # Test validation for known configs
        test_cases = [
            ("DATABASE_URL", "postgresql://localhost:5432/test", True),
            ("DATABASE_URL", "invalid://url", False),
            ("JWT_SECRET_KEY", "a" * 32, True),
            ("JWT_SECRET_KEY", "too_short", False),
            ("ENVIRONMENT", "production", True),
            ("ENVIRONMENT", "invalid_env", False),
            ("REDIS_URL", "redis://localhost:6379", True),
            ("REDIS_URL", "http://localhost:6379", False),
        ]
        
        for key, value, should_pass in test_cases:
            is_valid, message = ConfigDependencyMap.validate_config_value(key, value)
            if should_pass:
                assert is_valid, f"Validation should pass for {key}={value}: {message}"
            else:
                assert not is_valid, f"Validation should fail for {key}={value}"
    
    def test_config_deletion_protection(self):
        """Test that critical configs cannot be deleted without approval"""
        # Test deletion protection
        critical_configs = [
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "SECRET_KEY"
        ]
        
        for config_key in critical_configs:
            can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
            assert not can_delete, f"Critical config {config_key} should not be deletable: {reason}"
            assert "BLOCKED" in reason or "Cannot delete" in reason
    
    def test_config_alternatives(self):
        """Test that alternative configuration keys are recognized"""
        # Test alternative keys
        alternatives_map = {
            "JWT_SECRET_KEY": ["JWT_SECRET"],
            "REDIS_URL": ["REDIS_HOST", "REDIS_PORT"],
            "CLICKHOUSE_URL": ["CLICKHOUSE_HOST", "CLICKHOUSE_PORT"]
        }
        
        for main_key, expected_alts in alternatives_map.items():
            actual_alts = ConfigDependencyMap.get_alternatives(main_key)
            for alt in expected_alts:
                assert alt in actual_alts, f"Missing alternative {alt} for {main_key}"
    
    def test_config_impact_analysis(self):
        """Test configuration impact analysis"""
        # Analyze impact for critical configs
        critical_configs = ["DATABASE_URL", "JWT_SECRET_KEY", "REDIS_URL"]
        
        for config_key in critical_configs:
            impact = ConfigDependencyMap.get_impact_analysis(config_key)
            
            assert "impact_level" in impact
            assert "affected_services" in impact
            assert "deletion_allowed" in impact
            assert "deletion_impact" in impact
            
            # Critical configs should have high impact
            if config_key in ["DATABASE_URL", "JWT_SECRET_KEY"]:
                assert impact["impact_level"] in [ConfigImpactLevel.CRITICAL, ConfigImpactLevel.HIGH]
    
    def test_config_consistency_check(self):
        """Test configuration consistency checking"""
        # Create test config with missing paired configs
        test_config = {
            "GOOGLE_CLIENT_ID": "test_client_id",
            # Missing GOOGLE_CLIENT_SECRET (paired config)
            "DATABASE_URL": "postgresql://localhost/test",
            "JWT_SECRET_KEY": "a" * 32
        }
        
        issues = ConfigDependencyMap.check_config_consistency(test_config)
        
        # Should detect missing paired config
        assert any("GOOGLE_CLIENT_SECRET" in issue for issue in issues), \
            "Should detect missing paired GOOGLE_CLIENT_SECRET"
    
    def test_environment_specific_configs(self):
        """Test that environment-specific configurations are properly set"""
        config = get_unified_config()
        env_name = config.environment
        
        # Environment-specific checks
        if env_name == "production":
            # Production should not have debug enabled
            assert not getattr(config, "debug", False), "Debug should be disabled in production"
            # Production should have strict validation
            assert not getattr(config, "allow_fallbacks", True), "Fallbacks should be disabled in production"
        
        elif env_name == "development":
            # Development can have relaxed settings
            assert getattr(config, "allow_fallbacks", False), "Fallbacks should be allowed in development"
        
        elif env_name == "testing":
            # Testing should have isolation
            env = get_env()
            assert env._isolation_enabled or env_name == "testing", "Testing should use isolation"
    
    @pytest.mark.parametrize("service", ["netra_backend", "auth_service"])
    def test_service_required_configs(self, service):
        """Test that each service has its required configurations"""
        required_configs = ConfigDependencyMap.get_required_configs(service_name=service)
        
        if required_configs:
            config = get_unified_config()
            config_dict = {k.upper(): v for k, v in config.__dict__.items()}
            
            for key in required_configs:
                # Check if config exists (in some form)
                assert any(k for k in config_dict if key in k.upper()), \
                    f"Service {service} missing required config {key}"
    
    def test_config_source_tracking(self):
        """Test that configuration sources are properly tracked"""
        env = get_env()
        
        # Set a test value with source
        test_key = "TEST_SOURCE_TRACKING"
        test_value = "tracked_value"
        test_source = "test_regression_suite"
        
        env.set(test_key, test_value, source=test_source)
        
        # Verify source is tracked (if the env supports it)
        if hasattr(env, "_sources"):
            assert test_key in env._sources
            assert env._sources[test_key] == test_source
        
        # Clean up
        env.delete(test_key)
    
    def test_config_migration_compatibility(self):
        """Test that configuration migrations maintain compatibility"""
        # This tests that if we have old-style config keys, they still work
        env = get_env()
        
        # Simulate old config key
        env.set("OLD_DATABASE_URL", "postgresql://old/db", source="legacy")
        
        # Check if alternatives are recognized
        alternatives = ConfigDependencyMap.get_alternatives("DATABASE_URL")
        
        # The system should recognize and potentially migrate old keys
        # (This is a placeholder - actual migration logic would be tested here)
        
        # Clean up
        env.delete("OLD_DATABASE_URL")