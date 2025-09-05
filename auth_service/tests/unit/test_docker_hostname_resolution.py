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
from shared.database_url_builder import DatabaseURLBuilder


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
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_docker_detection_via_env_variable(self, mock_exists):
        """Test Docker detection via RUNNING_IN_DOCKER environment variable."""
        # Setup mocks
        mock_exists.return_value = False  # No .dockerenv file
        
        # Create environment variables dict for testing
        env_vars = {
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development'
        }
        
        # Create DatabaseURLBuilder instance and test directly
        builder = DatabaseURLBuilder(env_vars)
        db_url = builder.get_url_for_environment(sync=False)
        
        # Should use 'postgres' instead of 'localhost' in Docker
        self.assertIn('@postgres:', db_url)
        self.assertNotIn('@localhost:', db_url)
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_docker_detection_via_dockerenv_file(self, mock_exists):
        """Test Docker detection via .dockerenv file."""
        # Setup mocks
        def exists_side_effect(path):
            return path == '/.dockerenv'
        mock_exists.side_effect = exists_side_effect
        
        # Create environment variables dict for testing
        env_vars = {
            'POSTGRES_HOST': '127.0.0.1',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development'
        }
        
        # Create DatabaseURLBuilder instance and test directly
        builder = DatabaseURLBuilder(env_vars)
        db_url = builder.get_url_for_environment(sync=False)
        
        # Should use 'postgres' instead of '127.0.0.1' in Docker
        self.assertIn('@postgres:', db_url)
        self.assertNotIn('@127.0.0.1:', db_url)
    
    @patch('builtins.open', new_callable=mock_open, read_data='1:cpu:/docker/abc123')
    @patch('shared.database_url_builder.os.path.exists')
    def test_docker_detection_via_cgroup(self, mock_exists, mock_file):
        """Test Docker detection via /proc/self/cgroup file."""
        # Setup mocks
        def exists_side_effect(path):
            return path == '/proc/self/cgroup'
        mock_exists.side_effect = exists_side_effect
        
        # Create environment variables dict for testing
        env_vars = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'ENVIRONMENT': 'development'
        }
        
        # Create DatabaseURLBuilder instance and test directly
        builder = DatabaseURLBuilder(env_vars)
        db_url = builder.get_url_for_environment(sync=False)
        
        # Should use 'postgres' instead of 'localhost' in Docker
        self.assertIn('@postgres:', db_url)
        self.assertNotIn('@localhost:', db_url)
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_non_docker_environment(self, mock_exists):
        """Test that non-Docker environments keep original hostname."""
        # Setup mocks - no Docker indicators
        mock_exists.return_value = False
        
        # Set environment variables for test (no Docker indicators)
        env.set('POSTGRES_HOST', 'localhost', 'test')
        env.set('POSTGRES_PORT', '5432', 'test')
        env.set('POSTGRES_DB', 'test_db', 'test')
        env.set('POSTGRES_USER', 'test_user', 'test')
        env.set('POSTGRES_PASSWORD', 'test_pass', 'test')
        env.set('ENVIRONMENT', 'development', 'test')
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep 'localhost' when not in Docker
        self.assertIn('@localhost:', db_url)
        self.assertNotIn('@postgres:', db_url)
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_non_localhost_host_not_overridden(self, mock_exists):
        """Test that non-localhost hosts are not overridden in Docker."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Set environment variables for test with custom host
        env.set('RUNNING_IN_DOCKER', 'true', 'test')
        env.set('POSTGRES_HOST', 'custom-db-host.example.com', 'test')
        env.set('POSTGRES_PORT', '5432', 'test')
        env.set('POSTGRES_DB', 'test_db', 'test')
        env.set('POSTGRES_USER', 'test_user', 'test')
        env.set('POSTGRES_PASSWORD', 'test_pass', 'test')
        env.set('ENVIRONMENT', 'development', 'test')
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep custom host even in Docker
        self.assertIn('@custom-db-host.example.com:', db_url)
        self.assertNotIn('@postgres:', db_url)
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_database_url_override(self, mock_exists):
        """Test that DATABASE_URL takes precedence when set."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Set environment variables for test with DATABASE_URL
        env.set('RUNNING_IN_DOCKER', 'true', 'test')
        env.set('POSTGRES_HOST', 'localhost', 'test')
        env.set('POSTGRES_PORT', '5432', 'test')
        env.set('POSTGRES_DB', 'test_db', 'test')
        env.set('POSTGRES_USER', 'test_user', 'test')
        env.set('POSTGRES_PASSWORD', 'test_pass', 'test')
        env.set('ENVIRONMENT', 'development', 'test')
        env.set('DATABASE_URL', 'postgresql://custom_user:custom_pass@custom_host:5433/custom_db', 'test')
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should use the provided DATABASE_URL
        self.assertIn('@custom_host:', db_url)
        self.assertIn(':5433/', db_url)
        self.assertIn('/custom_db', db_url)
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_docker_not_applied_in_production(self, mock_exists):
        """Test that Docker hostname resolution is NOT applied in production."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Set environment variables for test in PRODUCTION
        env.set('RUNNING_IN_DOCKER', 'true', 'test')
        env.set('POSTGRES_HOST', 'localhost', 'test')
        env.set('POSTGRES_PORT', '5432', 'test')
        env.set('POSTGRES_DB', 'prod_db', 'test')
        env.set('POSTGRES_USER', 'prod_user', 'test')
        env.set('POSTGRES_PASSWORD', 'prod_pass', 'test')
        env.set('ENVIRONMENT', 'production', 'test')  # Production environment
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep 'localhost' even in Docker for production
        self.assertIn('@localhost:', db_url)
        self.assertNotIn('@postgres:', db_url)
    
    @patch('shared.database_url_builder.os.path.exists')
    def test_docker_not_applied_in_staging(self, mock_exists):
        """Test that Docker hostname resolution is NOT applied in staging."""
        # Setup mocks - Docker environment
        mock_exists.return_value = True  # .dockerenv exists
        
        # Set environment variables for test in STAGING
        env.set('RUNNING_IN_DOCKER', 'true', 'test')
        env.set('POSTGRES_HOST', 'localhost', 'test')
        env.set('POSTGRES_PORT', '5432', 'test')
        env.set('POSTGRES_DB', 'staging_db', 'test')
        env.set('POSTGRES_USER', 'staging_user', 'test')
        env.set('POSTGRES_PASSWORD', 'staging_pass', 'test')
        env.set('ENVIRONMENT', 'staging', 'test')  # Staging environment
        
        # Get database URL
        db_url = AuthConfig.get_database_url()
        
        # Should keep 'localhost' even in Docker for staging
        self.assertIn('@localhost:', db_url)
        self.assertNotIn('@postgres:', db_url)


if __name__ == '__main__':
    unittest.main()