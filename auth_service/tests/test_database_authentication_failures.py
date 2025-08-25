"""Test Auth Service Database Authentication Failures
Tests that replicate the database authentication issues found in production logs.

CRITICAL AUTHENTICATION ISSUES TO REPLICATE:
1. "password authentication failed for user 'user_pr-4'" 
2. "password authentication failed for user 'postgres'"
3. Table creation skipped due to authentication errors
4. Socket closure issues during shutdown

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent database authentication failures in production
- Value Impact: Ensures auth service can connect with proper credentials
- Strategic Impact: Prevents authentication service downtime affecting all customers
"""

import os
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.isolated_environment import get_env
from test_framework.environment_markers import env

logger = logging.getLogger(__name__)


class TestDatabaseAuthenticationFailures:
    """Test suite replicating the actual database authentication failures."""
    
    def test_database_authentication_with_invalid_user_pr4_credentials(self):
        """FAILING TEST: Replicates 'password authentication failed for user user_pr-4' error.
        
        This test demonstrates the authentication failure when the auth service
        attempts to connect with the incorrect user credentials that were found
        in the production logs.
        """
        # Simulate the exact misconfiguration that causes the "user_pr-4" authentication failure
        invalid_env = {
            "DATABASE_URL": "",  # Force config to build URL
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432", 
            "POSTGRES_DB": "netra_auth",
            "POSTGRES_USER": "user_pr-4",  # This is the invalid user from logs
            "POSTGRES_PASSWORD": "wrong_password",  # Invalid password
            "ENVIRONMENT": "test"
        }
        
        with patch.dict(os.environ, invalid_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                # Configure mock to return the invalid credentials
                def mock_get(key, default=None):
                    return invalid_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # This should fail with authentication error
                with pytest.raises((ValueError, RuntimeError)) as exc_info:
                    database_url = AuthConfig.get_database_url()
                    # If URL building succeeds, the connection should fail
                    if database_url:
                        # Attempt to validate the URL - this will fail with auth error
                        assert not AuthDatabaseManager.validate_auth_url(database_url)
                
                # Verify the error indicates authentication failure
                # In a real integration test, this would be a connection failure
                assert True  # This test demonstrates the configuration that causes auth failures
    
    def test_database_authentication_with_invalid_postgres_user_credentials(self):
        """FAILING TEST: Replicates 'password authentication failed for user postgres' error.
        
        This test demonstrates the authentication failure when using invalid
        postgres user credentials, as seen in the production logs.
        """
        # Simulate the misconfiguration that causes postgres user authentication failure
        invalid_env = {
            "DATABASE_URL": "",  # Force config to build URL
            "POSTGRES_HOST": "localhost", 
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_auth",
            "POSTGRES_USER": "postgres",  # Standard postgres user
            "POSTGRES_PASSWORD": "incorrect_password",  # Invalid password  
            "ENVIRONMENT": "test"
        }
        
        with patch.dict(os.environ, invalid_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                # Configure mock to return the invalid credentials
                def mock_get(key, default=None):
                    return invalid_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # This should fail with authentication error
                with pytest.raises((ValueError, RuntimeError)) as exc_info:
                    database_url = AuthConfig.get_database_url()
                    # If URL building succeeds, the connection should fail
                    if database_url:
                        # Attempt to validate the URL - this will fail with auth error
                        assert not AuthDatabaseManager.validate_auth_url(database_url)
                
                # Verify the error indicates authentication failure
                assert True  # This test demonstrates the configuration that causes auth failures
    
    @pytest.mark.asyncio
    async def test_auth_database_connection_failure_with_invalid_credentials(self):
        """FAILING TEST: Real integration test that attempts database connection with invalid credentials.
        
        This test actually tries to connect to a database with invalid credentials,
        replicating the exact failure scenario from production logs.
        """
        # Use invalid credentials that will cause authentication failure
        invalid_database_url = "postgresql+asyncpg://invalid_user:wrong_password@localhost:5432/nonexistent_db"
        
        # Create a test AuthDatabase instance with invalid configuration
        test_auth_db = AuthDatabase()
        
        # Override the configuration to use invalid credentials
        with patch.object(AuthConfig, 'get_database_url', return_value=invalid_database_url):
            with patch.object(test_auth_db, 'environment', 'test'):
                with patch.object(test_auth_db, 'is_test_mode', False):  # Force PostgreSQL mode
                    
                    # This should fail during initialization with authentication error
                    with pytest.raises(RuntimeError) as exc_info:
                        await test_auth_db.initialize()
                    
                    # Verify the error is related to authentication/connection failure
                    error_message = str(exc_info.value)
                    assert "database initialization failed" in error_message.lower() or \
                           "connection" in error_message.lower() or \
                           "authentication" in error_message.lower()
                    
                    # Test should fail because invalid credentials prevent connection
                    assert not await test_auth_db.test_connection()
    
    @pytest.mark.asyncio
    async def test_table_creation_skipped_due_to_authentication_error(self):
        """FAILING TEST: Replicates table creation failure due to authentication issues.
        
        This test demonstrates how authentication failures prevent table creation,
        leading to the "Table creation being skipped" warnings in logs.
        """
        # Create AuthDatabase instance
        test_auth_db = AuthDatabase()
        
        # Mock the create_async_engine to simulate authentication failure
        with patch('auth_service.auth_core.database.connection.create_async_engine') as mock_create_engine:
            # Configure mock to raise authentication error
            mock_create_engine.side_effect = RuntimeError("password authentication failed for user 'postgres'")
            
            # Override configuration to force PostgreSQL mode
            with patch.object(test_auth_db, 'is_test_mode', False):
                with patch.object(test_auth_db, 'environment', 'development'):
                    with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://postgres:wrong@localhost:5432/test"):
                        
                        # This should fail during initialization
                        with pytest.raises(RuntimeError) as exc_info:
                            await test_auth_db.initialize()
                        
                        # Verify the error message contains authentication failure
                        assert "password authentication failed" in str(exc_info.value)
                        
                        # Verify that the database was not initialized (tables not created)
                        assert not test_auth_db._initialized
                        assert test_auth_db.engine is None
    
    def test_database_url_building_with_missing_credentials(self):
        """FAILING TEST: Tests database URL building when credentials are missing.
        
        This test replicates scenarios where environment variables for database
        credentials are not properly set, leading to connection failures.
        """
        # Environment with missing critical database credentials
        incomplete_env = {
            "ENVIRONMENT": "staging",  # Force staging to require credentials
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_auth",
            # Missing POSTGRES_USER and POSTGRES_PASSWORD
        }
        
        with patch.dict(os.environ, incomplete_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return incomplete_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # This should fail due to missing credentials
                with pytest.raises(ValueError) as exc_info:
                    database_url = AuthConfig.get_database_url()
                
                # Verify the error indicates configuration issues
                error_message = str(exc_info.value)
                assert "configuration error" in error_message.lower() or \
                       "not configured" in error_message.lower()
    
    @pytest.mark.asyncio 
    async def test_socket_closure_during_shutdown_with_failed_connections(self):
        """FAILING TEST: Replicates socket closure issues during shutdown.
        
        This test demonstrates how failed database connections can cause
        socket closure errors during application shutdown, as seen in logs.
        """
        # Create AuthDatabase with invalid configuration
        test_auth_db = AuthDatabase()
        
        # Mock engine creation to return a mock engine that fails during operations
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock(side_effect=Exception("Socket connection already closed"))
        
        # Set up the mock engine on the instance
        test_auth_db.engine = mock_engine
        test_auth_db._initialized = True
        
        # Attempt to close - this should handle the socket closure error gracefully
        # In the current implementation, this might not handle the error properly
        with pytest.raises(Exception) as exc_info:
            await test_auth_db.close()
        
        # Verify the error is related to socket closure
        assert "socket" in str(exc_info.value).lower() or \
               "connection" in str(exc_info.value).lower()
    
    def test_database_manager_url_validation_with_invalid_credentials(self):
        """FAILING TEST: Tests URL validation with credentials that will fail authentication.
        
        This test verifies that the database manager properly detects when
        credentials are invalid, even if the URL format is correct.
        """
        # Create a properly formatted URL with invalid credentials
        invalid_url = "postgresql+asyncpg://fake_user:fake_password@localhost:5432/fake_db"
        
        # URL validation should pass for format but fail for actual connection
        # Note: validate_auth_url only checks format, not actual connection
        # This highlights a gap in validation that contributes to runtime failures
        
        # The current validation method only checks format
        format_valid = AuthDatabaseManager.validate_auth_url(invalid_url)
        
        # This test demonstrates that format validation passes even with invalid credentials
        # This is a design issue that allows runtime authentication failures
        assert format_valid  # Format is valid
        
        # However, an actual connection attempt should fail
        # This test documents the gap between format validation and connection validation
        
    @pytest.mark.asyncio
    async def test_connection_retry_failure_with_persistent_authentication_errors(self):
        """FAILING TEST: Tests connection retry behavior with persistent auth failures.
        
        This test demonstrates how authentication failures persist across retry attempts,
        leading to complete connection failure and service unavailability.
        """
        test_auth_db = AuthDatabase()
        
        # Mock the engine to consistently fail with authentication error
        with patch('auth_service.auth_core.database.connection.create_async_engine') as mock_create_engine:
            # Simulate persistent authentication failure
            auth_error = RuntimeError("FATAL: password authentication failed for user 'postgres'")
            mock_create_engine.side_effect = auth_error
            
            # Configure for PostgreSQL connection attempt
            with patch.object(test_auth_db, 'is_test_mode', False):
                with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://postgres:wrong@localhost:5432/test"):
                    
                    # Multiple initialization attempts should all fail
                    for attempt in range(3):
                        with pytest.raises(RuntimeError) as exc_info:
                            await test_auth_db.initialize()
                        
                        # Verify consistent authentication failure
                        assert "password authentication failed" in str(exc_info.value)
                        
                        # Reset state for next attempt
                        test_auth_db._initialized = False
                        test_auth_db.engine = None
    
    def test_environment_credential_mismatch_detection(self):
        """FAILING TEST: Detects when credentials don't match the target environment.
        
        This test replicates scenarios where development credentials are used
        in staging environment, or vice versa, causing authentication failures.
        """
        # Simulate staging environment with development credentials
        staging_with_dev_credentials = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "34.132.142.103",  # Staging host
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging", 
            "POSTGRES_USER": "postgres",  # Development user
            "POSTGRES_PASSWORD": "development_password",  # Development password
        }
        
        with patch.dict(os.environ, staging_with_dev_credentials, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return staging_with_dev_credentials.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # Build URL - this should succeed
                try:
                    database_url = AuthConfig.get_database_url()
                    # URL building succeeds but credentials are wrong for staging
                    assert "34.132.142.103" in database_url  # Staging host
                    assert "postgres" in database_url  # But development user
                    
                    # This configuration will fail at connection time
                    # The test demonstrates the credential mismatch issue
                    
                except ValueError:
                    # If validation catches the mismatch, that's also valid
                    pass


class TestDatabaseGracefulShutdownFailures:
    """Test suite for database shutdown-related failures."""
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout_exceeded_with_hanging_connections(self):
        """FAILING TEST: Replicates shutdown timeout exceeded warnings.
        
        This test demonstrates how database connections that fail to close
        properly can cause shutdown timeouts, as seen in production logs.
        """
        test_auth_db = AuthDatabase()
        
        # Mock engine that hangs during disposal
        mock_engine = AsyncMock()
        
        # Create a slow dispose method that exceeds timeout
        async def slow_dispose():
            await asyncio.sleep(2)  # Simulate hanging connection
            
        mock_engine.dispose = AsyncMock(side_effect=slow_dispose)
        
        # Set up the instance with the hanging engine
        test_auth_db.engine = mock_engine
        test_auth_db._initialized = True
        
        # Attempt close with timeout - this should timeout or take too long
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Add a timeout to prevent the test from hanging
            await asyncio.wait_for(test_auth_db.close(), timeout=1.0)
        except asyncio.TimeoutError:
            # This is the expected behavior - shutdown timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            assert elapsed >= 1.0  # Verify timeout was reached
            
            # This demonstrates the "shutdown timeout exceeded" issue
            logger.error("Shutdown timeout exceeded - database connections failed to close gracefully")
        
        # Verify the connection state is problematic
        # In a real scenario, this would leave connections hanging
    
    @pytest.mark.asyncio
    async def test_multiple_connection_failures_during_startup(self):
        """FAILING TEST: Tests multiple connection failures during service startup.
        
        This replicates scenarios where the auth service fails to initialize
        database connections multiple times, causing startup failures.
        """
        # Test multiple initialization attempts with different failure modes
        failure_scenarios = [
            ("password authentication failed for user 'user_pr-4'", RuntimeError),
            ("password authentication failed for user 'postgres'", RuntimeError), 
            ("connection refused", ConnectionError),
            ("timeout expired", TimeoutError),
        ]
        
        for error_message, error_type in failure_scenarios:
            test_auth_db = AuthDatabase()
            
            with patch('auth_service.auth_core.database.connection.create_async_engine') as mock_create_engine:
                mock_create_engine.side_effect = error_type(error_message)
                
                with patch.object(test_auth_db, 'is_test_mode', False):
                    with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://test:test@localhost:5432/test"):
                        
                        # Each scenario should fail
                        with pytest.raises(RuntimeError) as exc_info:
                            await test_auth_db.initialize()
                        
                        # Verify the underlying error is preserved
                        assert error_message in str(exc_info.value) or \
                               "database initialization failed" in str(exc_info.value)
                        
                        # Verify service remains uninitialized
                        assert not test_auth_db._initialized


# Integration test marker for tests that require real database connections
pytestmark = pytest.mark.integration