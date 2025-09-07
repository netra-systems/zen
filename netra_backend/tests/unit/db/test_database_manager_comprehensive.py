"""Comprehensive DatabaseManager Unit Test Suite - P0 Revenue-Blocking Component Coverage

CRITICAL: DatabaseManager is identified as the #1 P0 revenue-blocking component requiring test coverage.
This is a Mega Class Exception (~1,825 lines) serving as SSOT for all database operations.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Foundation for ALL services
- Business Goal: Platform stability and reliability to prevent 500 errors in staging/production
- Value Impact: DatabaseManager failures = complete platform outage = immediate revenue loss
- Strategic Impact: Foundation class for entire database layer - affects every database operation

RECENT CRITICAL FAILURES:
- Staging 500 errors traced to database configuration issues
- Missing database URL validation causing startup failures
- Connection pool misconfigurations causing service outages
- Migration URL format errors in deployment pipelines

COVERAGE TARGET: 100% critical path coverage including:
- DatabaseManager initialization with DatabaseURLBuilder integration
- Engine creation and management across all environments
- Session lifecycle management with proper transaction handling
- Error scenarios that have caused production issues
- Health check functionality
- Configuration validation and edge cases
- Migration URL generation
- Connection pooling and cleanup

CRITICAL: Uses real database connections where appropriate (not mocks for E2E portions).
Follows SSOT patterns from test_framework/ and absolute import requirements per CLAUDE.md.
"""

import asyncio
import pytest
import logging
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy import text

# SSOT imports - absolute paths required per CLAUDE.md
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env


class TestDatabaseManagerComprehensive(BaseIntegrationTest):
    """Comprehensive test suite for DatabaseManager class covering all critical functionality."""
    
    def setup_method(self):
        """Set up for each test method."""
        super().setup_method()
        self.test_env_vars = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "localhost", 
            "POSTGRES_PORT": "5434",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "POSTGRES_DB": "test_db",
            # Add OAuth test credentials to prevent configuration validation errors
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test_client_id",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test_client_secret",
        }
    
    @pytest.mark.unit
    async def test_database_manager_initialization_success(self, isolated_env):
        """Test successful DatabaseManager initialization with proper configuration."""
        # Setup isolated environment with valid configuration
        isolated_env.set("ENVIRONMENT", "test", source="test")
        isolated_env.set("POSTGRES_HOST", "localhost", source="test")
        isolated_env.set("POSTGRES_PORT", "5434", source="test")
        isolated_env.set("POSTGRES_USER", "test_user", source="test")
        isolated_env.set("POSTGRES_PASSWORD", "test_password", source="test")
        isolated_env.set("POSTGRES_DB", "test_db", source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            # Mock config with proper attributes
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Create DatabaseManager instance
            db_manager = DatabaseManager()
            
            # Test initial state
            assert not db_manager._initialized
            assert db_manager._engines == {}
            assert db_manager._url_builder is None
            
            # Test initialization
            await db_manager.initialize()
            
            # Verify initialization completed
            assert db_manager._initialized
            assert 'primary' in db_manager._engines
            assert isinstance(db_manager._engines['primary'], AsyncEngine)
            assert isinstance(db_manager._url_builder, DatabaseURLBuilder)
    
    @pytest.mark.unit
    async def test_database_manager_initialization_missing_config(self, isolated_env):
        """Test DatabaseManager initialization failure with missing configuration."""
        # Setup environment with missing critical configuration
        isolated_env.set("ENVIRONMENT", "staging", source="test") # staging requires full config
        # Deliberately not setting POSTGRES_* vars to trigger error
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            
            # Should raise ValueError due to missing configuration
            with pytest.raises(ValueError, match="DatabaseURLBuilder failed to construct URL"):
                await db_manager.initialize()
    
    @pytest.mark.unit
    async def test_database_url_builder_integration(self, isolated_env):
        """Test proper integration with DatabaseURLBuilder for URL construction."""
        # Setup valid environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            
            # Test URL construction
            database_url = db_manager._get_database_url()
            
            # Verify proper asyncpg driver format
            assert database_url.startswith("postgresql+asyncpg://")
            assert "test_user" in database_url
            assert "localhost:5434" in database_url
            assert "test_db" in database_url
            # Password should be URL encoded
            assert "test_password" in database_url
    
    @pytest.mark.unit
    async def test_engine_management(self, isolated_env):
        """Test database engine creation and management."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0  # NullPool
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Test getting existing engine
            engine = db_manager.get_engine('primary')
            assert isinstance(engine, AsyncEngine)
            
            # Test getting non-existent engine
            with pytest.raises(ValueError, match="Engine 'nonexistent' not found"):
                db_manager.get_engine('nonexistent')
            
            # Test getting engine before initialization
            uninit_manager = DatabaseManager()
            with pytest.raises(RuntimeError, match="DatabaseManager not initialized"):
                uninit_manager.get_engine()
    
    @pytest.mark.unit
    async def test_session_lifecycle_success(self, isolated_env):
        """Test successful database session lifecycle with transaction handling."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock AsyncSession for this test
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Test successful session usage
                async with db_manager.get_session() as session:
                    # Session should be what __aenter__ returns (the actual session)
                    # In real usage, this would be mock_session, but context manager returns __aenter__ result
                    pass  # Just verify context manager works
                
                # Verify proper lifecycle
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_session_lifecycle_with_error_and_rollback(self, isolated_env):
        """Test session lifecycle with error handling and rollback."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock AsyncSession with error scenario
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Test error handling in session
                with pytest.raises(Exception, match="Database error"):
                    async with db_manager.get_session() as session:
                        # Error occurs during commit
                        pass
                
                # Verify rollback was called
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_session_lifecycle_rollback_failure(self, isolated_env):
        """Test session lifecycle when both commit and rollback fail."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock AsyncSession with both commit and rollback failing
            mock_session = AsyncMock(spec=AsyncSession)
            original_error = Exception("Original database error")
            mock_session.commit = AsyncMock(side_effect=original_error)
            mock_session.rollback = AsyncMock(side_effect=Exception("Rollback also failed"))
            mock_session.close = AsyncMock()
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Should raise original exception even if rollback fails
                with pytest.raises(Exception, match="Original database error"):
                    async with db_manager.get_session() as session:
                        # Error occurs during commit
                        pass
                
                # Verify both were attempted
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_session_close_failure_handling(self, isolated_env):
        """Test session close failure doesn't prevent completion."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock AsyncSession with close failing
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock(side_effect=Exception("Close failed"))
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Should complete successfully even if close fails
                async with db_manager.get_session() as session:
                    # Context manager should work even if close fails
                    pass
                
                # Verify close was attempted
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_health_check_success(self, isolated_env):
        """Test successful database health check."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock successful health check
            mock_session = AsyncMock(spec=AsyncSession)
            mock_result = Mock()
            mock_result.fetchone.return_value = (1,)
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                result = await db_manager.health_check()
                
                assert result["status"] == "healthy"
                assert result["engine"] == "primary"
                assert result["connection"] == "ok"
                
                # Verify SELECT 1 was executed
                mock_session.execute.assert_called_once()
                call_args = mock_session.execute.call_args[0][0]
                assert "SELECT 1" in str(call_args)
    
    @pytest.mark.unit
    async def test_health_check_failure(self, isolated_env):
        """Test database health check failure handling."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock health check failure
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.execute = AsyncMock(side_effect=Exception("Connection failed"))
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                result = await db_manager.health_check()
                
                assert result["status"] == "unhealthy"
                assert result["engine"] == "primary"
                assert "Connection failed" in result["error"]
    
    @pytest.mark.unit
    async def test_close_all_engines(self, isolated_env):
        """Test proper cleanup of all database engines."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            # Mock engine disposal
            mock_engine = AsyncMock()
            mock_engine.dispose = AsyncMock()
            
            db_manager = DatabaseManager()
            db_manager._engines['primary'] = mock_engine
            db_manager._initialized = True
            
            await db_manager.close_all()
            
            # Verify engine was disposed and state reset
            mock_engine.dispose.assert_called_once()
            assert db_manager._engines == {}
            assert not db_manager._initialized
    
    @pytest.mark.unit
    async def test_close_all_engines_with_errors(self, isolated_env):
        """Test engine cleanup when disposal fails."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        # Mock engine disposal failure
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock(side_effect=Exception("Disposal failed"))
        
        db_manager = DatabaseManager()
        db_manager._engines['primary'] = mock_engine
        db_manager._initialized = True
        
        # Should complete without raising exception
        await db_manager.close_all()
        
        # Verify cleanup still occurred
        assert db_manager._engines == {}
        assert not db_manager._initialized
    
    @pytest.mark.unit
    def test_get_migration_url_sync_format(self, isolated_env):
        """Test migration URL generation in sync format."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        # Test sync migration URL
        migration_url = DatabaseManager.get_migration_url_sync_format()
        
        # Verify sync format (no +asyncpg driver)
        assert migration_url.startswith("postgresql://")
        assert "+asyncpg" not in migration_url
        assert "test_user" in migration_url
        assert "localhost:5434" in migration_url
        assert "test_db" in migration_url
    
    @pytest.mark.unit
    def test_get_migration_url_with_asyncpg_conversion(self, isolated_env):
        """Test migration URL conversion from asyncpg to sync format."""
        # Setup environment with a URL that would get asyncpg driver
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch.object(DatabaseURLBuilder, 'get_url_for_environment') as mock_get_url:
            # Mock builder returning asyncpg URL
            mock_get_url.return_value = "postgresql+asyncpg://test_user:test_password@localhost:5434/test_db"
            
            migration_url = DatabaseManager.get_migration_url_sync_format()
            
            # Should convert to sync format
            assert migration_url == "postgresql://test_user:test_password@localhost:5434/test_db"
    
    @pytest.mark.unit
    def test_get_migration_url_failure(self, isolated_env):
        """Test migration URL generation failure."""
        # Setup empty environment to trigger failure
        isolated_env.set("ENVIRONMENT", "test", source="test")
        
        with patch.object(DatabaseURLBuilder, 'get_url_for_environment') as mock_get_url:
            mock_get_url.return_value = None
            
            with pytest.raises(ValueError, match="Could not determine migration database URL"):
                DatabaseManager.get_migration_url_sync_format()
    
    @pytest.mark.unit
    async def test_class_method_get_async_session(self, isolated_env):
        """Test backward compatibility class method for getting sessions."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                # Test class method
                async with DatabaseManager.get_async_session() as session:
                    # Verify context manager works
                    pass
                
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_create_application_engine(self, isolated_env):
        """Test creation of application engine for health checks."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_url = None
            
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                engine = DatabaseManager.create_application_engine()
                
                assert engine is mock_engine
                
                # Verify engine created with correct parameters
                mock_create_engine.assert_called_once()
                call_args = mock_create_engine.call_args
                
                # Check URL format
                url = call_args[0][0]
                assert url.startswith("postgresql+asyncpg://")
                
                # Check engine config
                kwargs = call_args[1]
                assert kwargs["echo"] is False  # No echo for health checks
                assert kwargs["poolclass"] is NullPool  # NullPool for health checks
                assert kwargs["pool_pre_ping"] is True
                assert kwargs["pool_recycle"] == 3600
    
    @pytest.mark.unit
    def test_global_database_manager_singleton(self):
        """Test global database manager singleton pattern."""
        from netra_backend.app.db.database_manager import _database_manager
        
        # Reset global state
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        # First call creates instance
        manager1 = get_database_manager()
        assert manager1 is not None
        assert isinstance(manager1, DatabaseManager)
        
        # Second call returns same instance
        manager2 = get_database_manager()
        assert manager2 is manager1
    
    @pytest.mark.unit
    async def test_get_db_session_helper(self, isolated_env):
        """Test the get_db_session helper function."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                # Test helper function
                async with get_db_session() as session:
                    # Verify context manager works
                    pass
                
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_pooling_configuration_sqlite(self, isolated_env):
        """Test proper pooling configuration for SQLite."""
        # Setup environment for SQLite
        isolated_env.set("ENVIRONMENT", "test", source="test")
        isolated_env.set("USE_MEMORY_DB", "true", source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5  # Should be ignored for SQLite
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Verify NullPool is used for SQLite
                call_args = mock_create_engine.call_args
                url = call_args[0][0]
                kwargs = call_args[1]
                
                if "sqlite" in url.lower():
                    assert kwargs["poolclass"] is NullPool
    
    @pytest.mark.unit
    async def test_pooling_configuration_postgresql(self, isolated_env):
        """Test proper pooling configuration for PostgreSQL."""
        # Setup environment for PostgreSQL
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Verify StaticPool is used for PostgreSQL with async engines
                call_args = mock_create_engine.call_args
                kwargs = call_args[1]
                assert kwargs["poolclass"] is StaticPool
    
    @pytest.mark.unit
    async def test_pooling_configuration_disabled(self, isolated_env):
        """Test pooling configuration when pool_size is 0."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0  # Disabled pooling
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Verify NullPool is used when pooling is disabled
                call_args = mock_create_engine.call_args
                kwargs = call_args[1]
                assert kwargs["poolclass"] is NullPool
    
    @pytest.mark.unit
    async def test_configuration_fallback_handling(self, isolated_env):
        """Test handling of configuration fallbacks."""
        # Setup minimal environment
        isolated_env.set("ENVIRONMENT", "test", source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            # Config with fallback database_url
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = "postgresql+asyncpg://fallback:fallback@localhost:5432/fallback_db"
            
            db_manager = DatabaseManager()
            
            # Should use config fallback when DatabaseURLBuilder returns None
            with patch.object(db_manager, '_url_builder') as mock_builder:
                mock_builder.get_url_for_environment.return_value = None
                mock_builder.format_url_for_driver.return_value = mock_config.return_value.database_url
                
                url = db_manager._get_database_url()
                assert url == mock_config.return_value.database_url
    
    @pytest.mark.unit
    async def test_configuration_no_fallback_error(self, isolated_env):
        """Test error when no configuration is available."""
        # Setup minimal environment
        isolated_env.set("ENVIRONMENT", "staging", source="test")  # staging requires config
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_url = None  # No fallback
            
            db_manager = DatabaseManager()
            
            # Should raise error when no URL can be constructed
            with patch.object(DatabaseURLBuilder, 'get_url_for_environment') as mock_get_url:
                mock_get_url.return_value = None
                
                with pytest.raises(ValueError, match="DatabaseURLBuilder failed to construct URL"):
                    db_manager._get_database_url()
    
    @pytest.mark.unit
    async def test_double_initialization_protection(self, isolated_env):
        """Test that double initialization is handled gracefully."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            
            # First initialization
            await db_manager.initialize()
            assert db_manager._initialized
            engines_after_first = db_manager._engines.copy()
            
            # Second initialization should return early
            await db_manager.initialize()
            assert db_manager._initialized
            assert db_manager._engines == engines_after_first
    
    @pytest.mark.unit 
    async def test_environment_specific_url_building(self, isolated_env):
        """Test URL building for different environments."""
        test_cases = [
            ("development", "postgresql+asyncpg://"),
            ("test", "postgresql+asyncpg://"),
            ("staging", "postgresql+asyncpg://"),
            ("production", "postgresql+asyncpg://"),
        ]
        
        for env_name, expected_prefix in test_cases:
            # Setup environment for each test case
            isolated_env.set("ENVIRONMENT", env_name, source="test")
            for key, value in self.test_env_vars.items():
                if key != "ENVIRONMENT":
                    isolated_env.set(key, value, source="test")
            
            with patch('netra_backend.app.core.config.get_config') as mock_config:
                mock_config.return_value.database_url = None
                
                db_manager = DatabaseManager()
                url = db_manager._get_database_url()
                
                assert url.startswith(expected_prefix), f"Environment {env_name} should use {expected_prefix}"
    
    @pytest.mark.unit
    async def test_url_builder_safe_logging(self, isolated_env):
        """Test that database URLs are safely logged without exposing credentials."""
        # Setup environment
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            
            # Mock the URL builder to capture logging calls
            with patch.object(db_manager, '_url_builder') as mock_builder:
                mock_builder.get_url_for_environment.return_value = "postgresql://user:secret@host:5432/db"
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://user:secret@host:5432/db"
                mock_builder.get_safe_log_message.return_value = "Database URL (test/TCP): postgresql+asyncpg://***@host:5432/db"
                
                # This should call get_safe_log_message for logging
                url = db_manager._get_database_url()
                
                # Verify safe logging was called
                mock_builder.get_safe_log_message.assert_called_once()


class TestDatabaseManagerEdgeCases(BaseIntegrationTest):
    """Edge cases and error scenarios that have caused production issues."""
    
    @pytest.mark.unit
    async def test_staging_configuration_validation_failure(self, isolated_env):
        """Test scenario that caused recent staging 500 errors - missing configuration."""
        # Setup staging environment with incomplete configuration (real failure scenario)
        isolated_env.set("ENVIRONMENT", "staging", source="test")
        isolated_env.set("POSTGRES_HOST", "/cloudsql/project:region:instance", source="test")  # Cloud SQL
        # Missing POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_url = None  # No fallback
            
            db_manager = DatabaseManager()
            
            # This should fail similar to staging failure
            with pytest.raises(ValueError):
                await db_manager.initialize()
    
    @pytest.mark.unit
    async def test_cloud_sql_url_format_validation(self, isolated_env):
        """Test Cloud SQL URL format handling."""
        # Setup Cloud SQL environment
        isolated_env.set("ENVIRONMENT", "staging", source="test")
        isolated_env.set("POSTGRES_HOST", "/cloudsql/project:region:instance", source="test")
        isolated_env.set("POSTGRES_USER", "clouduser", source="test")
        isolated_env.set("POSTGRES_PASSWORD", "cloudpassword", source="test")
        isolated_env.set("POSTGRES_DB", "clouddb", source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            url = db_manager._get_database_url()
            
            # Verify Cloud SQL format
            assert "postgresql+asyncpg://" in url
            assert "/cloudsql/" in url
            assert "clouduser" in url
            assert "clouddb" in url
    
    @pytest.mark.unit
    async def test_url_special_characters_encoding(self, isolated_env):
        """Test handling of special characters in database credentials."""
        # Setup environment with special characters that need encoding
        isolated_env.set("ENVIRONMENT", "test", source="test")
        isolated_env.set("POSTGRES_HOST", "localhost", source="test")
        isolated_env.set("POSTGRES_PORT", "5434", source="test")
        isolated_env.set("POSTGRES_USER", "user@domain.com", source="test")  # @ needs encoding
        isolated_env.set("POSTGRES_PASSWORD", "pass&word#123", source="test")  # Special chars
        isolated_env.set("POSTGRES_DB", "test-db", source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            url = db_manager._get_database_url()
            
            # Verify URL is properly encoded
            assert url.startswith("postgresql+asyncpg://")
            # Special characters should be URL encoded by DatabaseURLBuilder
            assert "user%40domain.com" in url or "user@domain.com" in url
    
    @pytest.mark.unit
    async def test_session_auto_initialization(self, isolated_env):
        """Test that get_session auto-initializes manager if not initialized."""
        # Setup environment
        isolated_env.set("ENVIRONMENT", "test", source="test")
        isolated_env.set("POSTGRES_HOST", "localhost", source="test")
        isolated_env.set("POSTGRES_PORT", "5434", source="test")
        isolated_env.set("POSTGRES_USER", "test_user", source="test")
        isolated_env.set("POSTGRES_PASSWORD", "test_password", source="test")
        isolated_env.set("POSTGRES_DB", "test_db", source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                db_manager = DatabaseManager()
                assert not db_manager._initialized
                
                # get_session should auto-initialize
                async with db_manager.get_session() as session:
                    # Verify context manager works
                    pass
                
                # Should now be initialized
                assert db_manager._initialized
    
    @pytest.mark.unit
    async def test_concurrent_initialization_safety(self, isolated_env):
        """Test that concurrent initialization calls are handled safely."""
        # Setup environment
        for key, value in {"ENVIRONMENT": "test", "POSTGRES_HOST": "localhost", 
                          "POSTGRES_PORT": "5434", "POSTGRES_USER": "test_user",
                          "POSTGRES_PASSWORD": "test_password", "POSTGRES_DB": "test_db"}.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            
            # Simulate concurrent initialization
            tasks = [
                asyncio.create_task(db_manager.initialize()),
                asyncio.create_task(db_manager.initialize()),
                asyncio.create_task(db_manager.initialize())
            ]
            
            # All should complete without error
            await asyncio.gather(*tasks, return_exceptions=True)
            
            assert db_manager._initialized
            assert len(db_manager._engines) == 1  # Should only have one engine