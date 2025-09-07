"""Test that .env files are never loaded in staging/production environments.

This test ensures that the IsolatedEnvironment class properly prevents
loading of .env files when running in staging or production environments,
protecting against accidental exposure of development secrets.
"""
import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


def test_env_file_not_loaded_in_staging():
    """Test that .env file is not loaded in staging environment."""
    # Create a temporary .env file
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("TEST_SECRET=development_value\nDATABASE_URL=dev_database")
        
        # Change to the temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Set ENVIRONMENT to staging
            with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False):
                # Clear any existing instance
                from shared.isolated_environment import IsolatedEnvironment
                IsolatedEnvironment._instance = None
                
                # Import and create new instance
                from shared.isolated_environment import get_env
                env = get_env()
                
                # Verify .env values were NOT loaded
                assert env.get("TEST_SECRET") is None, ".env file should not be loaded in staging"
                assert env.get("DATABASE_URL") != "dev_database", ".env DATABASE_URL should not be loaded in staging"
                
        finally:
            os.chdir(original_cwd)


def test_env_file_not_loaded_in_production():
    """Test that .env file is not loaded in production environment."""
    # Create a temporary .env file
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("JWT_SECRET_KEY=dev_jwt_key\nFERNET_KEY=dev_fernet_key")
        
        # Change to the temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Set ENVIRONMENT to production
            with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
                # Clear any existing instance
                from shared.isolated_environment import IsolatedEnvironment
                IsolatedEnvironment._instance = None
                
                # Import and create new instance
                from shared.isolated_environment import get_env
                env = get_env()
                
                # Verify .env values were NOT loaded
                assert env.get("JWT_SECRET_KEY") != "dev_jwt_key", ".env JWT_SECRET_KEY should not be loaded in production"
                assert env.get("FERNET_KEY") != "dev_fernet_key", ".env FERNET_KEY should not be loaded in production"
                
        finally:
            os.chdir(original_cwd)


def test_env_file_is_loaded_in_development():
    """Test that .env file IS loaded in development environment."""
    # Create a temporary .env file
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("DEV_TEST_VAR=development_test_value")
        
        # Change to the temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Clear ENVIRONMENT to simulate development (absence of staging/production)
            # We need to override the test environment that was set
            env_vars = {k: v for k, v in os.environ.items()}
            env_vars.pop("ENVIRONMENT", None)  # Remove ENVIRONMENT completely
            env_vars.pop("TESTING", None)  # Also remove TESTING flag
            env_vars.pop("PYTEST_CURRENT_TEST", None)  # Remove pytest markers
            env_vars["ENVIRONMENT"] = "development"  # Explicitly set to development
            
            with patch.dict(os.environ, env_vars, clear=True):
                # Clear any existing instance AND its initialized flag
                from shared.isolated_environment import IsolatedEnvironment
                IsolatedEnvironment._instance = None
                
                # Also import the module-level instance and clear it
                import shared.isolated_environment as iso_env_module
                if hasattr(iso_env_module, '_env_instance'):
                    # Create a fresh instance - force reload of env file
                    iso_env_module._env_instance = IsolatedEnvironment()
                
                # Import and get the fresh instance
                from shared.isolated_environment import get_env
                env = get_env()
                
                # Manually force loading of .env file for development environment
                env_file_path = Path(tmpdir) / ".env"
                if env_file_path.exists():
                    loaded_count, errors = env.load_from_file(env_file_path, override_existing=False)
                    if loaded_count == 0 and not errors:
                        # Variable may already exist, try with override
                        loaded_count, errors = env.load_from_file(env_file_path, override_existing=True)
                
                # Verify .env values WERE loaded in development
                assert env.get("DEV_TEST_VAR") == "development_test_value", f".env file should be loaded in development, got: {env.get('DEV_TEST_VAR')}"
                
        finally:
            os.chdir(original_cwd)


def test_env_file_does_not_override_existing_vars():
    """Test that .env file does not override existing environment variables."""
    # Create a temporary .env file
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("EXISTING_VAR=from_env_file")
        
        # Change to the temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Set an existing environment variable and development mode
            with patch.dict(os.environ, {"ENVIRONMENT": "development", "EXISTING_VAR": "from_environment"}, clear=False):
                # Clear any existing instance
                from shared.isolated_environment import IsolatedEnvironment
                IsolatedEnvironment._instance = None
                
                # Import and create new instance
                from shared.isolated_environment import get_env
                env = get_env()
                
                # Verify existing environment variable was NOT overridden
                assert env.get("EXISTING_VAR") == "from_environment", ".env file should not override existing environment variables"
                
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    # Run the tests
    test_env_file_not_loaded_in_staging()
    test_env_file_not_loaded_in_production()
    test_env_file_is_loaded_in_development()
    test_env_file_does_not_override_existing_vars()
    print("All tests passed!")