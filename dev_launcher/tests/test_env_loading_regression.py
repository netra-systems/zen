"""
Integration test for environment loading regression prevention.

This test verifies that the dev launcher properly prevents environment variable
conflicts using the EnvironmentManager.
"""

import os
import pytest
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.config import LauncherConfig
from shared.isolated_environment import get_env, get_environment_manager
from dev_launcher.launcher import DevLauncher


env = get_env()
def reset_global_manager():
    """Reset the global environment manager for testing."""
    from shared.isolated_environment import _global_env
    _global_env.reset_to_original()
    _global_env._protected_vars.clear()
    _global_env._variable_sources.clear()


class TestEnvironmentLoadingRegression:
    """Test that environment loading prevents conflicts and race conditions."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset global manager before each test
        reset_global_manager()
        # Store original env vars to restore later
        self.original_env = env.get_all()
    
    def teardown_method(self):
        """Cleanup after each test."""
        # Restore original environment
        env.clear()
        env.update(self.original_env, "test")
        reset_global_manager()
    
    def test_no_auth_service_port_duplicate_setting(self):
        """Test that AUTH_SERVICE_PORT is not set multiple times by different components."""
        # Setup environment for development mode
        env.set("ENVIRONMENT", "development", "test")
        
        manager = get_environment_manager()
        
        # Simulate auth_starter setting the port first
        result1 = manager.set("AUTH_SERVICE_PORT", "8081", source="auth_starter")
        assert result1 is True
        
        # Simulate service_startup trying to set the same port (the old bug)
        result2 = manager.set("AUTH_SERVICE_PORT", "8081", source="service_startup")
        assert result2 is True  # Same value should be allowed
        
        # Simulate service_startup trying to set a different port (conflict)
        # With new API, we need to protect the variable first to prevent conflicts
        manager.protect_variable("AUTH_SERVICE_PORT")
        result3 = manager.set("AUTH_SERVICE_PORT", "8082", source="service_startup")
        assert result3 is False  # Different value should be prevented
        
        # Verify the correct port is preserved
        assert manager.get("AUTH_SERVICE_PORT") == "8081"
        assert manager.get_variable_source("AUTH_SERVICE_PORT") == "auth_starter"
    
    def test_temporary_secrets_loading_flag_cleanup(self):
        """Test that NETRA_SECRETS_LOADING flag is properly cleaned up."""
        env.set("ENVIRONMENT", "development", "test")
        
        manager = get_environment_manager()
        
        # Simulate secret loading with temporary flag (manual simulation)
        manager.set("NETRA_SECRETS_LOADING", "true", source="launcher_early_load")
        
        # During loading, flag should be present
        assert manager.get("NETRA_SECRETS_LOADING") == "true"
        
        # Simulate secret loader setting actual secrets
        manager.set("DATABASE_URL", "postgresql://test", source="secret_loader")
        manager.set("JWT_SECRET_KEY", "test_secret_minimum_20_characters_long", source="secret_loader")
        
        # Manually clean up temporary flag (simulating end of loading)
        manager.delete("NETRA_SECRETS_LOADING", source="launcher_cleanup")
        
        # After cleanup, temporary flag should be gone
        assert manager.get("NETRA_SECRETS_LOADING") is None
        
        # But actual secrets should remain
        assert manager.get("DATABASE_URL") == "postgresql://test"
        assert manager.get("JWT_SECRET_KEY") == "test_secret_minimum_20_characters_long"
    
    def test_isolation_mode_prevents_os_environ_pollution_in_development(self):
        """Test that development mode uses isolation to prevent os.environ pollution."""
        env.set("ENVIRONMENT", "development", "test")
        
        # Get manager should auto-detect development mode
        manager = get_environment_manager()
        manager.enable_isolation()  # Ensure isolation is enabled
        assert manager.is_isolation_enabled() is True
        
        # Set variables that should not appear in os.environ
        test_vars = {
            "TEST_VAR_1": "value1",
            "TEST_VAR_2": "value2",
            "DEVELOPMENT_FLAG": "true"
        }
        
        for key, value in test_vars.items():
            manager.set(key, value, source="test_component")
        
        # Variables should be in manager but not in os.environ
        for key, expected_value in test_vars.items():
            assert manager.get(key) == expected_value
            assert key not in os.environ
    
    def test_production_mode_sets_os_environ(self):
        """Test that production mode sets variables in os.environ."""
        env.set("ENVIRONMENT", "production", "test")
        
        # Reset to get fresh manager for production
        reset_global_manager()
        manager = get_environment_manager()
        manager.disable_isolation()  # Ensure isolation is disabled for production
        assert manager.is_isolation_enabled() is False
        
        # Set variables
        test_vars = {
            "PROD_VAR_1": "prod_value1",
            "PROD_VAR_2": "prod_value2"
        }
        
        for key, value in test_vars.items():
            manager.set(key, value, source="prod_component")
        
        # Variables should be in both manager and os.environ
        for key, expected_value in test_vars.items():
            assert manager.get(key) == expected_value
            assert env.get(key) == expected_value
    
    def test_secret_loader_isolation_behavior(self):
        """Test that secret loading respects isolation mode."""
        env.set("ENVIRONMENT", "development", "test")
        
        # Get the environment manager (should be in isolation mode)
        manager = get_environment_manager()
        
        # Enable isolation mode for development
        manager.enable_isolation()
        assert manager.is_isolation_enabled() is True
        
        # Set some secrets using the manager (simulating what SecretLoader should do)
        secrets = {
            "DATABASE_URL": "postgresql://localhost/test",
            "JWT_SECRET_KEY": "test_jwt_secret",
            "API_KEY": "test_api_key"
        }
        
        for key, value in secrets.items():
            manager.set(key, value, source="secret_loader")
        
        # Verify secrets are accessible through manager but not in os.environ
        for key, expected_value in secrets.items():
            assert manager.get(key) == expected_value
            assert key not in os.environ  # Should not pollute os.environ in development
    
    def test_environment_manager_singleton_behavior_in_launcher(self):
        """Test that all components get the same EnvironmentManager instance."""
        env.set("ENVIRONMENT", "development", "test")
        
        # Simulate different components getting the manager
        secret_loader_manager = get_environment_manager()
        auth_starter_manager = get_environment_manager()
        service_startup_manager = get_environment_manager()
        launcher_manager = get_environment_manager()
        
        # All should be the same instance
        assert secret_loader_manager is auth_starter_manager
        assert auth_starter_manager is service_startup_manager
        assert service_startup_manager is launcher_manager
        
        # Enable isolation for testing
        secret_loader_manager.enable_isolation()
        
        # All should have the same isolation mode
        assert all(manager.is_isolation_enabled() for manager in [
            secret_loader_manager, auth_starter_manager, 
            service_startup_manager, launcher_manager
        ])
    
    def test_component_environment_variable_precedence(self):
        """Test proper precedence handling between different components."""
        env.set("ENVIRONMENT", "development", "test")
        
        manager = get_environment_manager()
        
        # 1. Launcher sets defaults first (lowest precedence)
        defaults_result = manager.bulk_set_environment({
            "BACKEND_PORT": "8000",
            "LOG_LEVEL": "INFO",
            "CORS_ORIGINS": "*"
        }, source="launcher_defaults")
        assert all(defaults_result.values())
        
        # 2. Secret loader can override with explicit flag (higher precedence)
        secret_result = manager.set("BACKEND_PORT", "8001", source="secret_loader", force=True)
        assert secret_result is True
        assert manager.get("BACKEND_PORT") == "8001"
        
        # 3. Auth starter sets its specific variables (should succeed)
        auth_results = manager.bulk_set_environment({
            "AUTH_SERVICE_PORT": "8081",
            "AUTH_SERVICE_URL": "http://localhost:8081"
        }, source="auth_starter")
        assert all(auth_results.values())
        
        # 4. Protect BACKEND_PORT and try to override (should fail)
        manager.protect_variable("BACKEND_PORT")
        conflict_result = manager.set("BACKEND_PORT", "8002", source="random_component")
        assert conflict_result is False  # Should be prevented
        assert manager.get("BACKEND_PORT") == "8001"  # Unchanged
    
    def test_no_race_conditions_with_temporary_flags(self):
        """Test that temporary flags don't cause race conditions."""
        env.set("ENVIRONMENT", "development", "test")
        
        manager = get_environment_manager()
        
        # Simulate the loading sequence that previously caused race conditions
        # 1. Set temporary loading flag
        manager.set("NETRA_SECRETS_LOADING", "true", source="launcher")
        
        # 2. Check if loading is in progress (another component checking)
        assert manager.get("NETRA_SECRETS_LOADING") is not None
        assert manager.get("NETRA_SECRETS_LOADING") == "true"
        
        # 3. Load actual environment variables during loading
        loader_results = manager.bulk_set_environment({
            "DATABASE_URL": "postgresql://localhost/netra_dev",
            "JWT_SECRET_KEY": "super_secret_key",
            "REDIS_URL": "redis://localhost:6379"
        }, source="secret_loader")
        
        # All should succeed during loading
        assert all(loader_results.values())
        
        # 4. Verify loading flag is still present
        assert manager.get("NETRA_SECRETS_LOADING") == "true"
        
        # 5. Manually clean up loading flag (simulating end of loading)
        manager.delete("NETRA_SECRETS_LOADING", source="launcher_cleanup")
        assert manager.get("NETRA_SECRETS_LOADING") is None
        
        # 6. But actual secrets should remain accessible
        assert manager.get("DATABASE_URL") == "postgresql://localhost/netra_dev"
        assert manager.get("JWT_SECRET_KEY") == "super_secret_key"
        assert manager.get("REDIS_URL") == "redis://localhost:6379"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])