"""
Integration test for environment loading regression prevention.

This test verifies that the dev launcher properly prevents environment variable
conflicts using the EnvironmentManager.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from dev_launcher.config import LauncherConfig
from dev_launcher.isolated_environment import get_env
from dev_launcher.launcher import DevLauncher


class TestEnvironmentLoadingRegression:
    """Test that environment loading prevents conflicts and race conditions."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset global manager before each test
        reset_global_manager()
        # Store original env vars to restore later
        self.original_env = dict(os.environ)
    
    def teardown_method(self):
        """Cleanup after each test."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        reset_global_manager()
    
    def test_no_auth_service_port_duplicate_setting(self):
        """Test that AUTH_SERVICE_PORT is not set multiple times by different components."""
        # Setup environment for development mode
        os.environ["ENVIRONMENT"] = "development"
        
        manager = get_environment_manager()
        
        # Simulate auth_starter setting the port first
        result1 = manager.set_environment("AUTH_SERVICE_PORT", "8081", source="auth_starter")
        assert result1 is True
        
        # Simulate service_startup trying to set the same port (the old bug)
        result2 = manager.set_environment("AUTH_SERVICE_PORT", "8081", source="service_startup")
        assert result2 is True  # Same value should be allowed
        
        # Simulate service_startup trying to set a different port (conflict)
        result3 = manager.set_environment("AUTH_SERVICE_PORT", "8082", source="service_startup")
        assert result3 is False  # Different value should be prevented
        
        # Verify the correct port is preserved
        assert manager.get_environment("AUTH_SERVICE_PORT") == "8081"
        assert manager.get_variable_source("AUTH_SERVICE_PORT") == "auth_starter"
        
        # Verify conflict was tracked
        conflicts = manager.get_conflicts_report()
        assert conflicts["total_conflicts"] == 1
        assert "AUTH_SERVICE_PORT" in conflicts["conflicts_prevented"]
    
    def test_temporary_secrets_loading_flag_cleanup(self):
        """Test that NETRA_SECRETS_LOADING flag is properly cleaned up."""
        os.environ["ENVIRONMENT"] = "development"
        
        manager = get_environment_manager()
        
        # Use temporary flag (simulating launcher behavior)
        with manager.set_temporary_flag("NETRA_SECRETS_LOADING", "true", source="launcher_early_load"):
            # During loading, flag should be present
            assert manager.get_environment("NETRA_SECRETS_LOADING") == "true"
            
            # Simulate secret loader setting actual secrets
            manager.set_environment("DATABASE_URL", "postgresql://test", source="secret_loader")
            manager.set_environment("JWT_SECRET_KEY", "test_secret", source="secret_loader")
        
        # After context, temporary flag should be gone
        assert manager.get_environment("NETRA_SECRETS_LOADING") is None
        assert not manager.has_variable("NETRA_SECRETS_LOADING")
        
        # But actual secrets should remain
        assert manager.get_environment("DATABASE_URL") == "postgresql://test"
        assert manager.get_environment("JWT_SECRET_KEY") == "test_secret"
    
    def test_isolation_mode_prevents_os_environ_pollution_in_development(self):
        """Test that development mode uses isolation to prevent os.environ pollution."""
        os.environ["ENVIRONMENT"] = "development"
        
        # Get manager should auto-detect development mode
        manager = get_environment_manager()
        assert manager.isolation_mode is True
        
        # Set variables that should not appear in os.environ
        test_vars = {
            "TEST_VAR_1": "value1",
            "TEST_VAR_2": "value2",
            "DEVELOPMENT_FLAG": "true"
        }
        
        for key, value in test_vars.items():
            manager.set_environment(key, value, source="test_component")
        
        # Variables should be in manager but not in os.environ
        for key, expected_value in test_vars.items():
            assert manager.get_environment(key) == expected_value
            assert key not in os.environ
    
    def test_production_mode_sets_os_environ(self):
        """Test that production mode sets variables in os.environ."""
        os.environ["ENVIRONMENT"] = "production"
        
        # Reset to get fresh manager for production
        reset_global_manager()
        manager = get_environment_manager()
        assert manager.isolation_mode is False
        
        # Set variables
        test_vars = {
            "PROD_VAR_1": "prod_value1",
            "PROD_VAR_2": "prod_value2"
        }
        
        for key, value in test_vars.items():
            manager.set_environment(key, value, source="prod_component")
        
        # Variables should be in both manager and os.environ
        for key, expected_value in test_vars.items():
            assert manager.get_environment(key) == expected_value
            assert os.environ.get(key) == expected_value
    
    @patch('dev_launcher.secret_loader.SecretLoader')
    def test_secret_loader_uses_environment_manager(self, mock_secret_loader_class):
        """Test that SecretLoader uses EnvironmentManager instead of direct os.environ."""
        os.environ["ENVIRONMENT"] = "development"
        
        # Create a mock secret loader instance
        mock_loader = MagicMock()
        mock_secret_loader_class.return_value = mock_loader
        
        # Mock the load_all_secrets method to return True
        mock_loader.load_all_secrets.return_value = True
        
        # Get the environment manager (should be in isolation mode)
        manager = get_environment_manager()
        
        # Verify isolation mode is active
        assert manager.isolation_mode is True
        
        # Set some secrets using the manager (simulating what SecretLoader should do)
        secrets = {
            "DATABASE_URL": "postgresql://localhost/test",
            "JWT_SECRET_KEY": "test_jwt_secret",
            "API_KEY": "test_api_key"
        }
        
        for key, value in secrets.items():
            manager.set_environment(key, value, source="secret_loader")
        
        # Verify secrets are accessible through manager but not in os.environ
        for key, expected_value in secrets.items():
            assert manager.get_environment(key) == expected_value
            assert key not in os.environ  # Should not pollute os.environ in development
    
    def test_environment_manager_singleton_behavior_in_launcher(self):
        """Test that all components get the same EnvironmentManager instance."""
        os.environ["ENVIRONMENT"] = "development"
        
        # Simulate different components getting the manager
        secret_loader_manager = get_environment_manager()
        auth_starter_manager = get_environment_manager()
        service_startup_manager = get_environment_manager()
        launcher_manager = get_environment_manager()
        
        # All should be the same instance
        assert secret_loader_manager is auth_starter_manager
        assert auth_starter_manager is service_startup_manager
        assert service_startup_manager is launcher_manager
        
        # All should have the same isolation mode
        assert all(manager.isolation_mode for manager in [
            secret_loader_manager, auth_starter_manager, 
            service_startup_manager, launcher_manager
        ])
    
    def test_component_environment_variable_precedence(self):
        """Test proper precedence handling between different components."""
        os.environ["ENVIRONMENT"] = "development"
        
        manager = get_environment_manager()
        
        # 1. Launcher sets defaults first (lowest precedence)
        defaults_result = manager.bulk_set_environment({
            "BACKEND_PORT": "8000",
            "LOG_LEVEL": "INFO",
            "CORS_ORIGINS": "*"
        }, source="launcher_defaults")
        assert all(defaults_result.values())
        
        # 2. Secret loader can override with explicit flag (higher precedence)
        secret_result = manager.set_environment("BACKEND_PORT", "8001", 
                                              source="secret_loader", allow_override=True)
        assert secret_result is True
        assert manager.get_environment("BACKEND_PORT") == "8001"
        
        # 3. Auth starter sets its specific variables (should succeed)
        auth_results = manager.bulk_set_environment({
            "AUTH_SERVICE_PORT": "8081",
            "AUTH_SERVICE_URL": "http://localhost:8081"
        }, source="auth_starter")
        assert all(auth_results.values())
        
        # 4. Another component tries to override without permission (should fail)
        conflict_result = manager.set_environment("BACKEND_PORT", "8002", 
                                                source="random_component")
        assert conflict_result is False  # Should be prevented
        assert manager.get_environment("BACKEND_PORT") == "8001"  # Unchanged
        
        # Verify conflict tracking
        conflicts = manager.get_conflicts_report()
        assert conflicts["total_conflicts"] == 1
        assert "BACKEND_PORT" in conflicts["conflicts_prevented"]
        assert "random_component" in conflicts["conflicts_prevented"]["BACKEND_PORT"]
    
    def test_no_race_conditions_with_temporary_flags(self):
        """Test that temporary flags don't cause race conditions."""
        os.environ["ENVIRONMENT"] = "development"
        
        manager = get_environment_manager()
        
        # Simulate the loading sequence that previously caused race conditions
        # 1. Set temporary loading flag
        with manager.set_temporary_flag("NETRA_SECRETS_LOADING", "true", source="launcher"):
            # 2. Check if loading is in progress (another component checking)
            assert manager.has_variable("NETRA_SECRETS_LOADING")
            assert manager.get_environment("NETRA_SECRETS_LOADING") == "true"
            
            # 3. Load actual environment variables during loading
            loader_results = manager.bulk_set_environment({
                "DATABASE_URL": "postgresql://localhost/netra",
                "JWT_SECRET_KEY": "super_secret_key",
                "REDIS_URL": "redis://localhost:6379"
            }, source="secret_loader")
            
            # All should succeed during loading
            assert all(loader_results.values())
            
            # 4. Verify loading flag is still present
            assert manager.get_environment("NETRA_SECRETS_LOADING") == "true"
        
        # 5. After loading context, flag should be automatically cleaned up
        assert not manager.has_variable("NETRA_SECRETS_LOADING")
        assert manager.get_environment("NETRA_SECRETS_LOADING") is None
        
        # 6. But actual secrets should remain accessible
        assert manager.get_environment("DATABASE_URL") == "postgresql://localhost/netra"
        assert manager.get_environment("JWT_SECRET_KEY") == "super_secret_key"
        assert manager.get_environment("REDIS_URL") == "redis://localhost:6379"
        
        # 7. Verify no conflicts occurred during the loading process
        conflicts = manager.get_conflicts_report()
        assert conflicts["total_conflicts"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])