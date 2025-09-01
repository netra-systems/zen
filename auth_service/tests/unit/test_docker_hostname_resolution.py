from shared.isolated_environment import get_env
"""
Test Docker hostname resolution for database connections.

This test ensures that the auth service correctly detects Docker environments
and adjusts database hostnames accordingly.
"""
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
import tempfile

from auth_service.auth_core.config import AuthConfig


env = get_env()
class TestDockerHostnameResolution(unittest.TestCase):
    """Test Docker environment detection and hostname resolution.
    
    Note: Docker hostname resolution only applies in development and test environments,
    not in staging or production.
    """
    
    def setUp(self):
        """Set up test environment."""
        # Store original environment
        self.original_env = env.get_all()
        # Clear Docker-related environment variables
        for key in ['RUNNING_IN_DOCKER', 'IS_DOCKER', 'DOCKER_CONTAINER']:
            os.environ.pop(key, None)
    
    def tearDown(self):
        """Restore original environment."""
        env.clear()
        env.update(self.original_env, "test")
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_docker_detection_via_env_variable(self, mock_exists, mock_get_env):
        """Test Docker detection via RUNNING_IN_DOCKER environment variable."""
        # Setup mocks
        mock_exists.return_value = False  # No .dockerenv file
        
        # Configure environment mock
        env_values = {
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development',
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should use 'postgres' instead of 'localhost' in Docker
        self.assertIn('@postgres:', db_url)
        self.assertNotIn('@localhost:', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_docker_detection_via_dockerenv_file(self, mock_exists, mock_get_env):
        """Test Docker detection via .dockerenv file."""
        # Setup mocks
        def exists_side_effect(path):
            return path == '/.dockerenv'
        mock_exists.side_effect = exists_side_effect
        
        # Configure environment mock
        env_values = {
            'POSTGRES_HOST': '127.0.0.1',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development',
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should use 'postgres' instead of '127.0.0.1' in Docker
        self.assertIn('@postgres:', db_url)
        self.assertNotIn('@127.0.0.1:', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('builtins.open', new_callable=mock_open, read_data='1:cpu:/docker/abc123')
    @patch('os.path.exists')
    def test_docker_detection_via_cgroup(self, mock_exists, mock_file, mock_get_env):
        """Test Docker detection via /proc/self/cgroup file."""
        # Setup mocks
        def exists_side_effect(path):
            return path == '/proc/self/cgroup'
        mock_exists.side_effect = exists_side_effect
        
        # Configure environment mock
        env_values = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development',
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should use 'postgres' instead of 'localhost' in Docker
        self.assertIn('@postgres:', db_url)
        self.assertNotIn('@localhost:', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_non_docker_environment(self, mock_exists, mock_get_env):
        """Test that non-Docker environments keep original hostname."""
        # Setup mocks - no Docker indicators
        mock_exists.return_value = False
        
        # Configure environment mock
        env_values = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development',
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep 'localhost' when not in Docker
        self.assertIn('@localhost:', db_url)
        self.assertNotIn('@postgres:', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_non_localhost_host_not_overridden(self, mock_exists, mock_get_env):
        """Test that non-localhost hosts are not overridden in Docker."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Configure environment mock with custom host
        env_values = {
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'custom-db-host.example.com',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development',
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep custom host even in Docker
        self.assertIn('@custom-db-host.example.com:', db_url)
        self.assertNotIn('@postgres:', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_database_url_override(self, mock_exists, mock_get_env):
        """Test that DATABASE_URL takes precedence when set."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Configure environment mock with DATABASE_URL
        env_values = {
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://custom_user:custom_pass@custom_host:5433/custom_db'
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should use the provided DATABASE_URL
        self.assertIn('@custom_host:', db_url)
        self.assertIn(':5433/', db_url)
        self.assertIn('/custom_db', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_docker_not_applied_in_production(self, mock_exists, mock_get_env):
        """Test that Docker hostname resolution is NOT applied in production."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Configure environment mock for PRODUCTION
        env_values = {
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'prod_db',
            'POSTGRES_USER': 'prod_user',
            'POSTGRES_PASSWORD': 'prod_pass',
            'ENVIRONMENT': 'production',  # Production environment
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep 'localhost' even in Docker for production
        self.assertIn('@localhost:', db_url)
        self.assertNotIn('@postgres:', db_url)
    
    @patch('auth_service.auth_core.config.get_env')
    @patch('os.path.exists')
    def test_docker_not_applied_in_staging(self, mock_exists, mock_get_env):
        """Test that Docker hostname resolution is NOT applied in staging."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Configure environment mock for STAGING
        env_values = {
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'staging_db',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_pass',
            'ENVIRONMENT': 'staging',  # Staging environment
            'DATABASE_URL': None
        }
        mock_get_env.return_value.get.side_effect = lambda key, default=None: env_values.get(key, default)
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep 'localhost' even in Docker for staging
        self.assertIn('@localhost:', db_url)
        self.assertNotIn('@postgres:', db_url)


if __name__ == '__main__':
    unittest.main()