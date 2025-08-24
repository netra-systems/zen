"""Tests for unified environment loading from .env files.

These tests verify that the configuration system correctly loads
environment variables from .env files in development mode.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from netra_backend.app.core.configuration import unified_config_manager


class TestUnifiedEnvLoading:
    """Test suite for unified environment loading."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Save original environment
        self.original_env = os.environ.copy()
        
        # Clear critical environment variables
        env_vars_to_clear = [
            'ENVIRONMENT', 'GEMINI_API_KEY', 'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET', 'JWT_SECRET_KEY', 'FERNET_KEY',
            'SERVICE_SECRET', 'CLICKHOUSE_DEFAULT_PASSWORD',
            'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DATABASE_URL',
            'REDIS_URL', 'CLICKHOUSE_HOST', 'CLICKHOUSE_PORT',
            'LLM_MODE', 'REDIS_MODE', 'CLICKHOUSE_MODE',
            'NETRA_SECRETS_LOADING', 'CORS_ORIGINS'
        ]
        for var in env_vars_to_clear:
            os.environ.pop(var, None)
        
        yield
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_load_from_dotenv_file_in_development(self):
        """Test that .env file is loaded in development mode."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('GEMINI_API_KEY=test_gemini_key\n')
            f.write('GOOGLE_CLIENT_ID=test_client_id\n')
            f.write('GOOGLE_CLIENT_SECRET=test_client_secret\n')
            f.write('JWT_SECRET_KEY=test_jwt_key\n')
            f.write('FERNET_KEY=test_fernet_key\n')
            f.write('SERVICE_SECRET=test_service_secret\n')
            f.write('CLICKHOUSE_DEFAULT_PASSWORD=test_clickhouse_pwd\n')
            f.write('DATABASE_URL=postgresql://test@localhost/testdb\n')
            f.write('REDIS_URL=redis://localhost:6379\n')
            f.write('ANTHROPIC_API_KEY=test_anthropic_key\n')
            f.write('OPENAI_API_KEY=test_openai_key\n')
            env_file = f.name
        
        try:
            # Set development environment
            os.environ['ENVIRONMENT'] = 'development'
            
            # Mock the .env file path
            # Mock: Component isolation for testing without external dependencies
            with patch('pathlib.Path.exists', return_value=True):
                # Mock: Component isolation for testing without external dependencies
                with patch('builtins.open', open(env_file)):
                    # Mock: Component isolation for testing without external dependencies
                    with patch('netra_backend.app.core.configuration.base.Path') as mock_path:
                        mock_path.return_value.parent.parent.parent = Path(os.path.dirname(env_file))
                        mock_path.return_value.parent.parent.parent.joinpath.return_value = Path(env_file)
                        
                        # Force reload of configuration
                        if hasattr(unified_config_manager, '_config'):
                            unified_config_manager._config = None
                        if hasattr(unified_config_manager, '_loaded'):
                            unified_config_manager._loaded = False
                        
                        # Load configuration
                        config = unified_config_manager.get_config()
                        
                        # Verify all values are loaded from .env
                        assert config.gemini_api_key == 'test_gemini_key'
                        assert config.google_client_id == 'test_client_id'
                        assert config.google_client_secret == 'test_client_secret'
                        assert config.jwt_secret_key == 'test_jwt_key'
                        assert config.fernet_key == 'test_fernet_key'
                        assert config.service_secret == 'test_service_secret'
                        assert config.clickhouse_default_password == 'test_clickhouse_pwd'
                        assert config.database_url == 'postgresql://test@localhost/testdb'
                        assert config.redis_url == 'redis://localhost:6379'
                        assert config.anthropic_api_key == 'test_anthropic_key'
                        assert config.openai_api_key == 'test_openai_key'
        finally:
            # Clean up temp file
            os.unlink(env_file)
    
    def test_env_vars_override_dotenv_file(self):
        """Test that environment variables override .env file values."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('GEMINI_API_KEY=file_gemini_key\n')
            f.write('DATABASE_URL=postgresql://file@localhost/filedb\n')
            env_file = f.name
        
        try:
            # Set development environment and override values
            os.environ['ENVIRONMENT'] = 'development'
            os.environ['GEMINI_API_KEY'] = 'env_gemini_key'
            
            # Mock the .env file path
            # Mock: Component isolation for testing without external dependencies
            with patch('pathlib.Path.exists', return_value=True):
                # Mock: Component isolation for testing without external dependencies
                with patch('builtins.open', open(env_file)):
                    # Mock: Component isolation for testing without external dependencies
                    with patch('netra_backend.app.core.configuration.base.Path') as mock_path:
                        mock_path.return_value.parent.parent.parent = Path(os.path.dirname(env_file))
                        mock_path.return_value.parent.parent.parent.joinpath.return_value = Path(env_file)
                        
                        # Force reload of configuration
                        if hasattr(unified_config_manager, '_config'):
                            unified_config_manager._config = None
                        if hasattr(unified_config_manager, '_loaded'):
                            unified_config_manager._loaded = False
                        
                        # Load configuration
                        config = unified_config_manager.get_config()
                        
                        # Verify environment variable overrides .env file
                        assert config.gemini_api_key == 'env_gemini_key'
                        # Verify .env file value is used when no env var exists
                        assert config.database_url == 'postgresql://file@localhost/filedb'
        finally:
            # Clean up temp file
            os.unlink(env_file)
    
    def test_no_dotenv_loading_in_production(self):
        """Test that .env file is NOT loaded in production mode."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('GEMINI_API_KEY=file_gemini_key\n')
            f.write('DATABASE_URL=postgresql://file@localhost/filedb\n')
            env_file = f.name
        
        try:
            # Set production environment
            os.environ['ENVIRONMENT'] = 'production'
            
            # Mock the .env file path
            # Mock: Component isolation for testing without external dependencies
            with patch('pathlib.Path.exists', return_value=True):
                # Mock: Component isolation for testing without external dependencies
                with patch('builtins.open', open(env_file)):
                    # Mock: Component isolation for testing without external dependencies
                    with patch('netra_backend.app.core.configuration.base.Path') as mock_path:
                        mock_path.return_value.parent.parent.parent = Path(os.path.dirname(env_file))
                        mock_path.return_value.parent.parent.parent.joinpath.return_value = Path(env_file)
                        
                        # Force reload of configuration
                        if hasattr(unified_config_manager, '_config'):
                            unified_config_manager._config = None
                        if hasattr(unified_config_manager, '_loaded'):
                            unified_config_manager._loaded = False
                        
                        # Load configuration - should NOT load from .env
                        config = unified_config_manager.get_config()
                        
                        # Verify .env values are NOT loaded
                        assert config.gemini_api_key != 'file_gemini_key'
                        assert config.database_url != 'postgresql://file@localhost/filedb'
        finally:
            # Clean up temp file
            os.unlink(env_file)
    
    def test_all_required_secrets_populated_from_env(self):
        """Test that all required secrets can be populated from environment."""
        # Set all required secrets in environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['GEMINI_API_KEY'] = 'test_gemini'
        os.environ['GOOGLE_CLIENT_ID'] = 'test_client_id'
        os.environ['GOOGLE_CLIENT_SECRET'] = 'test_client_secret'
        os.environ['JWT_SECRET_KEY'] = 'test_jwt'
        os.environ['FERNET_KEY'] = 'test_fernet'
        os.environ['SERVICE_SECRET'] = 'test_service'
        os.environ['CLICKHOUSE_DEFAULT_PASSWORD'] = 'test_clickhouse'
        
        # Force reload of configuration
        if hasattr(unified_config_manager, '_config'):
            unified_config_manager._config = None
        if hasattr(unified_config_manager, '_loaded'):
            unified_config_manager._loaded = False
        
        # Load configuration
        config = unified_config_manager.get_config()
        
        # Verify all secrets are populated
        assert config.gemini_api_key == 'test_gemini'
        assert config.google_client_id == 'test_client_id'
        assert config.google_client_secret == 'test_client_secret'
        assert config.jwt_secret_key == 'test_jwt'
        assert config.fernet_key == 'test_fernet'
        assert config.service_secret == 'test_service'
        assert config.clickhouse_default_password == 'test_clickhouse'
    
    def test_service_modes_from_env(self):
        """Test that service modes are correctly loaded from environment."""
        # Set service modes in environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['LLM_MODE'] = 'mock'
        os.environ['REDIS_MODE'] = 'local'
        os.environ['CLICKHOUSE_MODE'] = 'docker'
        
        # Force reload of configuration
        if hasattr(unified_config_manager, '_config'):
            unified_config_manager._config = None
        if hasattr(unified_config_manager, '_loaded'):
            unified_config_manager._loaded = False
        
        # Load configuration
        config = unified_config_manager.get_config()
        
        # Verify service modes are loaded
        assert config.llm_mode == 'mock'
        assert config.redis_mode == 'local'
        assert config.clickhouse_mode == 'docker'
    
    def test_cors_origins_from_env(self):
        """Test that CORS origins are correctly loaded from environment."""
        # Set CORS origins
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['CORS_ORIGINS'] = '*'
        
        # Force reload of configuration
        if hasattr(unified_config_manager, '_config'):
            unified_config_manager._config = None
        if hasattr(unified_config_manager, '_loaded'):
            unified_config_manager._loaded = False
        
        # Load configuration
        config = unified_config_manager.get_config()
        
        # Verify CORS origins are loaded
        assert config.cors_origins == '*'
    
    def test_no_secrets_loading_flag_during_startup(self):
        """Test that NETRA_SECRETS_LOADING flag doesn't block env loading."""
        # Set flag that indicates secrets are still loading
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['NETRA_SECRETS_LOADING'] = 'true'
        os.environ['GEMINI_API_KEY'] = 'test_key'
        
        # Force reload of configuration
        if hasattr(unified_config_manager, '_config'):
            unified_config_manager._config = None
        if hasattr(unified_config_manager, '_loaded'):
            unified_config_manager._loaded = False
        
        # Load configuration - should still load from environment
        config = unified_config_manager.get_config()
        
        # Verify values are loaded despite flag
        assert config.gemini_api_key == 'test_key'
    
    def test_dev_launcher_env_propagation(self):
        """Test that dev launcher environment variables are properly loaded."""
        # Simulate dev launcher environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['BACKEND_PORT'] = '8000'
        os.environ['PYTHONPATH'] = '/path/to/project'
        os.environ['CORS_ORIGINS'] = '*'
        os.environ['REDIS_MODE'] = 'shared'
        os.environ['CLICKHOUSE_MODE'] = 'shared'
        os.environ['LLM_MODE'] = 'shared'
        os.environ['GEMINI_API_KEY'] = 'launcher_gemini_key'
        
        # Force reload of configuration
        if hasattr(unified_config_manager, '_config'):
            unified_config_manager._config = None
        if hasattr(unified_config_manager, '_loaded'):
            unified_config_manager._loaded = False
        
        # Load configuration
        config = unified_config_manager.get_config()
        
        # Verify all dev launcher values are loaded
        assert config.cors_origins == '*'
        assert config.redis_mode == 'shared'
        assert config.clickhouse_mode == 'shared'
        assert config.llm_mode == 'shared'
        assert config.gemini_api_key == 'launcher_gemini_key'