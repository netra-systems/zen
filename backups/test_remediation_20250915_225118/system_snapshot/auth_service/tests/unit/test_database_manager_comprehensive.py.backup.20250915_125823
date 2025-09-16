"""
Comprehensive unit tests for Auth Service Database Manager

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable database engine management and URL construction
- Value Impact: Prevents auth service failures due to database configuration issues
- Strategic Impact: Foundation for consistent database connectivity across environments

Tests database engine creation, URL construction, environment handling,
configuration validation, and integration with shared components.
Uses real PostgreSQL database for comprehensive validation.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder
from test_framework.real_services_test_fixtures import real_services_fixture


class TestAuthDatabaseManagerEngineCreation:
    """Test database engine creation functionality"""
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_create_async_engine(self, real_services_fixture):
        """Test basic async engine creation"""
        engine = AuthDatabaseManager.create_async_engine()
        
        assert isinstance(engine, AsyncEngine)
        assert engine is not None
        
        # Verify engine configuration
        assert isinstance(engine.pool, NullPool)
        assert engine.echo is False
        
        # Test engine connectivity
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1
        
        await engine.dispose()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_create_async_engine_with_kwargs(self, real_services_fixture):
        """Test engine creation with custom kwargs"""
        engine = AuthDatabaseManager.create_async_engine(
            echo=True,
            pool_timeout=60
        )
        
        assert isinstance(engine, AsyncEngine)
        assert engine.echo is True
        
        # Test connectivity
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 42"))
            value = result.scalar()
            assert value == 42
        
        await engine.dispose()
    
    @pytest.mark.unit
    async def test_create_async_engine_no_url_error(self):
        """Test engine creation failure when no URL available"""
        with patch.object(AuthDatabaseManager, 'get_database_url', return_value=None):
            with pytest.raises(ValueError, match="No database URL available"):
                AuthDatabaseManager.create_async_engine()
    
    @pytest.mark.unit
    async def test_create_async_engine_empty_url_error(self):
        """Test engine creation failure with empty URL"""
        with patch.object(AuthDatabaseManager, 'get_database_url', return_value=""):
            with pytest.raises(ValueError, match="No database URL available"):
                AuthDatabaseManager.create_async_engine()


class TestAuthDatabaseManagerURLConstruction:
    """Test database URL construction and validation"""
    
    @pytest.mark.unit
    @pytest.mark.real_services
    def test_get_database_url_normal_mode(self, real_services_fixture):
        """Test database URL construction in normal mode"""
        url = AuthDatabaseManager.get_database_url()
        
        assert url is not None
        assert isinstance(url, str)
        assert url.startswith(("postgresql://", "postgres://"))
        
        # Should contain expected components for PostgreSQL URL
        assert "postgresql" in url or "postgres" in url
    
    @pytest.mark.unit
    def test_get_database_url_fast_test_mode(self):
        """Test database URL construction in fast test mode"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "true",
                "ENVIRONMENT": "test"
            }.get(key, default)
            
            url = AuthDatabaseManager.get_database_url()
            
            assert url == "sqlite+aiosqlite:///:memory:"
    
    @pytest.mark.unit
    def test_get_database_url_environment_variables(self):
        """Test URL construction with various environment variables"""
        test_env_vars = {
            "AUTH_FAST_TEST_MODE": "false",
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_pass"
        }
        
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: test_env_vars.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = "postgresql://test_user:test_pass@localhost:5432/test_db"
                mock_builder.get_safe_log_message.return_value = "Connected to localhost:5432"
                mock_builder_class.return_value = mock_builder
                
                url = AuthDatabaseManager.get_database_url()
                
                assert url == "postgresql://test_user:test_pass@localhost:5432/test_db"
                
                # Verify builder was configured correctly
                mock_builder_class.assert_called_once()
                call_args = mock_builder_class.call_args[0][0]
                assert call_args["ENVIRONMENT"] == "development"
                assert call_args["POSTGRES_HOST"] == "localhost"
                assert call_args["POSTGRES_USER"] == "test_user"
    
    @pytest.mark.unit
    def test_get_database_url_validation_failure(self):
        """Test URL construction with validation failure"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "false",
                "ENVIRONMENT": "test"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (False, "Missing required configuration")
                mock_builder_class.return_value = mock_builder
                
                with pytest.raises(ValueError, match="Database configuration error"):
                    AuthDatabaseManager.get_database_url()
    
    @pytest.mark.unit
    def test_get_database_url_no_url_generated(self):
        """Test URL construction when builder returns no URL"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "false",
                "ENVIRONMENT": "test"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = None
                mock_builder.debug_info.return_value = {"error": "No credentials"}
                mock_builder_class.return_value = mock_builder
                
                with pytest.raises(ValueError, match="DatabaseURLBuilder failed to generate URL"):
                    AuthDatabaseManager.get_database_url()


class TestAuthDatabaseManagerEnvironmentHandling:
    """Test environment-specific behavior"""
    
    @pytest.mark.unit
    def test_environment_detection_development(self):
        """Test environment detection for development"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "development"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = "postgresql://dev_url"
                mock_builder.get_safe_log_message.return_value = "Dev connection"
                mock_builder_class.return_value = mock_builder
                
                url = AuthDatabaseManager.get_database_url()
                
                # Verify environment was passed correctly
                call_args = mock_builder_class.call_args[0][0]
                assert call_args["ENVIRONMENT"] == "development"
    
    @pytest.mark.unit
    def test_environment_detection_staging(self):
        """Test environment detection for staging"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "staging"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = "postgresql://staging_url"
                mock_builder.get_safe_log_message.return_value = "Staging connection"
                mock_builder_class.return_value = mock_builder
                
                url = AuthDatabaseManager.get_database_url()
                
                # Verify environment was passed correctly
                call_args = mock_builder_class.call_args[0][0]
                assert call_args["ENVIRONMENT"] == "staging"
    
    @pytest.mark.unit
    def test_environment_detection_production(self):
        """Test environment detection for production"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "production"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = "postgresql://prod_url"
                mock_builder.get_safe_log_message.return_value = "Production connection"
                mock_builder_class.return_value = mock_builder
                
                url = AuthDatabaseManager.get_database_url()
                
                # Verify environment was passed correctly
                call_args = mock_builder_class.call_args[0][0]
                assert call_args["ENVIRONMENT"] == "production"
    
    @pytest.mark.unit
    def test_environment_detection_default(self):
        """Test default environment when not specified"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                # No ENVIRONMENT set
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = "postgresql://default_url"
                mock_builder.get_safe_log_message.return_value = "Default connection"
                mock_builder_class.return_value = mock_builder
                
                url = AuthDatabaseManager.get_database_url()
                
                # Should default to "development"
                call_args = mock_builder_class.call_args[0][0]
                assert call_args["ENVIRONMENT"] == "development"


class TestAuthDatabaseManagerIntegrationWithSharedComponents:
    """Test integration with shared components"""
    
    @pytest.mark.unit
    def test_integration_with_database_url_builder(self):
        """Test proper integration with DatabaseURLBuilder"""
        test_env = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "test-host",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test-db",
            "POSTGRES_USER": "test-user",
            "POSTGRES_PASSWORD": "test-pass"
        }
        
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: test_env.get(key, default)
            
            # Use real DatabaseURLBuilder to test integration
            with patch('shared.database_url_builder.DatabaseURLBuilder.get_url_for_environment') as mock_get_url:
                mock_get_url.return_value = "postgresql://test-user:test-pass@test-host:5432/test-db"
                
                with patch('shared.database_url_builder.DatabaseURLBuilder.validate') as mock_validate:
                    mock_validate.return_value = (True, None)
                    
                    with patch('shared.database_url_builder.DatabaseURLBuilder.get_safe_log_message') as mock_log:
                        mock_log.return_value = "Safe log message"
                        
                        url = AuthDatabaseManager.get_database_url()
                        
                        assert url == "postgresql://test-user:test-pass@test-host:5432/test-db"
    
    @pytest.mark.unit
    def test_integration_with_isolated_environment(self):
        """Test proper integration with IsolatedEnvironment"""
        # Test that get_env() is used correctly
        original_get_env = get_env
        
        with patch('auth_service.auth_core.database.database_manager.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "true",
                "ENVIRONMENT": "test"
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            url = AuthDatabaseManager.get_database_url()
            
            # Should use fast test mode
            assert url == "sqlite+aiosqlite:///:memory:"
            
            # Verify get_env was called
            mock_get_env.assert_called_once()
    
    @pytest.mark.unit
    def test_url_masking_for_logging(self):
        """Test that URL masking is used for secure logging"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "false",
                "ENVIRONMENT": "test"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (True, None)
                mock_builder.get_url_for_environment.return_value = "postgresql://user:password@host:5432/db"
                mock_builder.get_safe_log_message.return_value = "Connected to host:5432"
                mock_builder_class.return_value = mock_builder
                
                with patch('auth_service.auth_core.database.database_manager.DatabaseURLBuilder.mask_url_for_logging') as mock_mask:
                    mock_mask.return_value = "postgresql://***:***@host:5432/db"
                    
                    # This should trigger URL masking for logging
                    url = AuthDatabaseManager.get_database_url()
                    
                    # Verify masking was called
                    mock_mask.assert_called_once_with("postgresql://user:password@host:5432/db")


class TestAuthDatabaseManagerErrorHandlingAndEdgeCases:
    """Test error handling and edge cases"""
    
    @pytest.mark.unit
    def test_missing_environment_variables(self):
        """Test handling of missing environment variables"""
        with patch.object(get_env(), 'get') as mock_get:
            # Return None for all environment variables
            mock_get.return_value = None
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (False, "Missing POSTGRES_HOST")
                mock_builder_class.return_value = mock_builder
                
                with pytest.raises(ValueError, match="Database configuration error"):
                    AuthDatabaseManager.get_database_url()
    
    @pytest.mark.unit
    def test_invalid_environment_values(self):
        """Test handling of invalid environment values"""
        invalid_env = {
            "ENVIRONMENT": "invalid_env",
            "POSTGRES_HOST": "",  # Empty host
            "POSTGRES_PORT": "not_a_number",  # Invalid port
            "POSTGRES_USER": "",  # Empty user
        }
        
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: invalid_env.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.validate.return_value = (False, "Invalid configuration values")
                mock_builder_class.return_value = mock_builder
                
                with pytest.raises(ValueError, match="Database configuration error"):
                    AuthDatabaseManager.get_database_url()
    
    @pytest.mark.unit
    def test_database_url_builder_exception(self):
        """Test handling of DatabaseURLBuilder exceptions"""
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "false",
                "ENVIRONMENT": "test"
            }.get(key, default)
            
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder_class.side_effect = Exception("Builder initialization failed")
                
                with pytest.raises(Exception, match="Builder initialization failed"):
                    AuthDatabaseManager.get_database_url()
    
    @pytest.mark.unit
    def test_fast_test_mode_variations(self):
        """Test various fast test mode values"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("", False),
            ("invalid", False),
        ]
        
        for test_value, should_be_fast in test_cases:
            with patch.object(get_env(), 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: {
                    "AUTH_FAST_TEST_MODE": test_value,
                    "ENVIRONMENT": "test"
                }.get(key, default)
                
                url = AuthDatabaseManager.get_database_url()
                
                if should_be_fast:
                    assert url == "sqlite+aiosqlite:///:memory:"
                else:
                    # Should try to build PostgreSQL URL (will fail without proper env vars)
                    with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                        mock_builder = MagicMock()
                        mock_builder.validate.return_value = (True, None)
                        mock_builder.get_url_for_environment.return_value = "postgresql://test"
                        mock_builder.get_safe_log_message.return_value = "Test"
                        mock_builder_class.return_value = mock_builder
                        
                        url = AuthDatabaseManager.get_database_url()
                        assert url == "postgresql://test"


class TestAuthDatabaseManagerRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_engine_creation_full_flow(self, real_services_fixture):
        """Test complete engine creation flow with real database"""
        # Test URL construction
        url = AuthDatabaseManager.get_database_url()
        assert url is not None
        
        # Test engine creation
        engine = AuthDatabaseManager.create_async_engine()
        assert engine is not None
        
        # Test engine usage
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            assert version is not None
            assert "PostgreSQL" in version
        
        await engine.dispose()
    
    @pytest.mark.unit
    @pytest.mark.real_services 
    async def test_multiple_engine_creation(self, real_services_fixture):
        """Test creating multiple engines (should work independently)"""
        engines = []
        
        try:
            # Create multiple engines
            for i in range(3):
                engine = AuthDatabaseManager.create_async_engine()
                engines.append(engine)
                
                # Each should work independently
                async with engine.connect() as conn:
                    result = await conn.execute(text(f"SELECT {i + 1}"))
                    value = result.scalar()
                    assert value == i + 1
        
        finally:
            # Clean up all engines
            for engine in engines:
                await engine.dispose()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_engine_with_custom_configuration(self, real_services_fixture):
        """Test engine creation with custom configuration"""
        engine = AuthDatabaseManager.create_async_engine(
            echo=False,  # Disable logging
            pool_timeout=30,  # Custom timeout
        )
        
        try:
            # Test custom configuration works
            assert engine.echo is False
            
            # Test connectivity
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                assert db_name is not None
        
        finally:
            await engine.dispose()
    
    @pytest.mark.unit
    def test_environment_specific_url_construction(self):
        """Test URL construction for different environments"""
        environments = ["development", "staging", "production", "test"]
        
        for env in environments:
            with patch.object(get_env(), 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: {
                    "ENVIRONMENT": env,
                    "AUTH_FAST_TEST_MODE": "false"
                }.get(key, default)
                
                with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = MagicMock()
                    mock_builder.validate.return_value = (True, None)
                    mock_builder.get_url_for_environment.return_value = f"postgresql://{env}_url"
                    mock_builder.get_safe_log_message.return_value = f"{env} connection"
                    mock_builder_class.return_value = mock_builder
                    
                    url = AuthDatabaseManager.get_database_url()
                    
                    assert url == f"postgresql://{env}_url"
                    
                    # Verify correct environment was passed
                    call_args = mock_builder_class.call_args[0][0]
                    assert call_args["ENVIRONMENT"] == env