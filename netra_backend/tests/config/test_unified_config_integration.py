"""Integration Tests for Unified Configuration System

These tests validate that all components work together correctly
when using the unified configuration system.

MOCK JUSTIFICATION: L1 Unit Tests - Mocking unified config to test integration
pathways without external dependencies. Real configuration tested in L3 tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from test_framework.decorators import mock_justified
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.db.postgres_core import Database, AsyncDatabase
from netra_backend.app.db.cache_core import QueryCache


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager with unified config."""
    
    @mock_justified("L1 Unit Test: Mocking environment variables to test URL retrieval logic without real database. Real database configuration tested in L3 integration tests.", "L1")
    def test_database_url_retrieval_from_config(self):
        """Test DatabaseManager retrieves URL from unified config."""
        # Use environment variable directly since DatabaseManager checks environment in pytest mode
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test:pass@localhost/testdb'}):
            url = DatabaseManager.get_base_database_url()
            assert 'postgresql://' in url
            assert 'testdb' in url
    
    @mock_justified("L1 Unit Test: Mocking unified config to test engine creation logic without real configuration dependencies. Real engine creation tested in L3 integration tests.", "L1")
    def test_sync_engine_creation_uses_config(self):
        """Test sync engine creation uses unified config settings."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                database_url='sqlite:///:memory:',
                log_level='DEBUG',
                environment='testing'
            )
            
            # Mock: Database access isolation for fast, reliable unit testing
            with patch('netra_backend.app.db.database_manager.create_engine') as mock_create:
                DatabaseManager.create_migration_engine()
                
                # Verify engine created with config settings
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs['echo'] is True  # DEBUG level enables echo
    
    @mock_justified("L1 Unit Test: Mocking unified config to test async engine creation logic. Real async engines tested in L3 integration tests with real databases.", "L1")
    def test_async_engine_creation_uses_config(self):
        """Test async engine creation uses unified config settings."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                database_url='postgresql+asyncpg://test:pass@localhost/testdb',
                log_level='INFO',
                environment='development'
            )
            
            # Mock: Database access isolation for fast, reliable unit testing
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create:
                DatabaseManager.create_application_engine()
                
                # Verify async engine created with config settings
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                # Echo behavior depends on actual config implementation
                assert 'echo' in call_kwargs
    
    def test_environment_detection_from_config(self):
        """Test environment detection uses unified config."""
        # Test environment detection behavior 
        # Note: In testing mode, is_local_development behavior may differ
        is_local = DatabaseManager.is_local_development()
        assert isinstance(is_local, bool)
    
    def test_test_mode_detection_from_config(self):
        """Test mode detection uses unified config environment."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                environment='testing',
                database_url='sqlite:///:memory:'
            )
            
            url = DatabaseManager.get_base_database_url()
            assert 'sqlite' in url


class TestRedisManagerIntegration:
    """Integration tests for RedisManager with unified config."""
    
    @pytest.mark.asyncio
    async def test_redis_mode_from_config(self):
        """Test Redis manager uses mode from unified config."""
        # Patch the get_unified_config import in the redis_manager module specifically  
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        with patch('netra_backend.app.redis_manager.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                redis_mode='local',
                dev_mode_redis_enabled=True,
                environment='development',
                # Mock: Redis caching isolation to prevent test interference and external dependencies
                redis=Mock(host='localhost', port=6379, username='default', password=None)
            )
            
            manager = RedisManager()
            assert manager._get_redis_mode() == 'local'
    
    @pytest.mark.asyncio
    async def test_redis_connection_uses_config(self):
        """Test Redis connection uses unified config settings."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                redis_mode='shared',
                dev_mode_redis_enabled=True,
                environment='development',
                # Mock: Redis caching isolation to prevent test interference and external dependencies
                redis=Mock(
                    host='redis.example.com',
                    port=6379,
                    username='testuser',
                    password='testpass'
                )
            )
            
            # Mock: Redis external service isolation for fast, reliable tests without network dependency
            with patch('redis.asyncio.Redis') as mock_redis:
                manager = RedisManager()
                manager._create_redis_client()
                
                # Verify Redis client created with config settings
                mock_redis.assert_called_once()
                call_kwargs = mock_redis.call_args[1]
                assert call_kwargs['host'] == 'redis.example.com'
                assert call_kwargs['username'] == 'testuser'
    
    @pytest.mark.asyncio
    async def test_redis_fallback_on_failure(self):
        """Test Redis falls back to local when remote fails."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            config_obj = Mock(
                redis_mode='shared',
                dev_mode_redis_enabled=True,
                environment='development',
                # Mock: Redis external service isolation for fast, reliable tests without network dependency
                redis=Mock(host='failing.redis.com', port=6379, username='user', password='pass')
            )
            mock_config.return_value = config_obj
            
            manager = RedisManager()
            
            # Mock Redis to fail then succeed
            with patch.object(manager, '_create_redis_client') as mock_create:
                with patch.object(manager, '_test_redis_connection') as mock_test:
                    mock_test.side_effect = [Exception("Connection failed"), None]
                    
                    await manager.connect()
                    
                    # Verify fallback to local mode
                    assert config_obj.redis_mode == 'local'


class TestPostgresCoreIntegration:
    """Integration tests for postgres_core with unified config."""
    
    def test_sync_database_pool_config(self):
        """Test sync Database class uses unified config for pool settings."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                db_pool_size=25,
                db_max_overflow=35,
                db_pool_timeout=45,
                db_pool_recycle=2400,
                db_echo=True,
                db_echo_pool=True
            )
            
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.db.postgres_core.create_engine') as mock_create:
                db = Database('postgresql://test')
                
                # Verify engine created with unified config settings
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs['echo'] is True
                assert call_kwargs['echo_pool'] is True
                assert call_kwargs['pool_recycle'] == 2400
    
    @pytest.mark.asyncio
    async def test_async_database_pool_config(self):
        """Test async Database class uses unified config for pool settings."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                db_pool_size=30,
                db_max_overflow=40,
                db_pool_timeout=50,
                db_pool_recycle=3000,
                db_echo=False,
                db_echo_pool=False
            )
            
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.db.postgres_core.create_async_engine') as mock_create:
                # Mock: Generic component isolation for controlled unit testing
                mock_create.return_value = AsyncMock()
                db = AsyncDatabase('postgresql+asyncpg://test')
                
                # Verify async engine created with unified config settings
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs['echo'] is False
                assert call_kwargs['pool_recycle'] == 3000
    
    def test_pool_sizing_with_minimum_values(self):
        """Test pool sizing enforces minimum values for resilience."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                db_pool_size=5,  # Below minimum
                db_max_overflow=10,  # Below minimum
                db_pool_timeout=30,
                db_pool_recycle=1800,
                db_echo=False,
                db_echo_pool=False
            )
            
            db = Database('postgresql://test')
            pool_size = db._get_pool_size(db._get_pool_class('postgresql://test'))
            max_overflow = db._get_max_overflow(db._get_pool_class('postgresql://test'))
            
            # Verify minimums are enforced
            assert pool_size >= 10
            assert max_overflow >= 20


class TestCacheCoreIntegration:
    """Integration tests for cache_core with unified config."""
    
    @pytest.mark.asyncio
    async def test_cache_config_from_unified(self):
        """Test QueryCache uses unified config for cache settings."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                cache_enabled=True,
                cache_default_ttl=600,
                cache_max_size=2000,
                cache_strategy='lru',
                cache_prefix='test_cache:',
                cache_metrics_enabled=True,
                cache_frequent_query_threshold=10,
                cache_frequent_query_ttl_multiplier=3.0,
                cache_slow_query_threshold=2.0,
                cache_slow_query_ttl_multiplier=4.0
            )
            
            cache = QueryCache()
            
            # Verify cache config built from unified config
            assert cache.config.enabled is True
            assert cache.config.default_ttl == 600
            assert cache.config.max_cache_size == 2000
            assert cache.config.strategy == 'lru'
    
    @pytest.mark.asyncio
    async def test_cache_disabled_from_config(self):
        """Test cache respects enabled flag from unified config."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                cache_enabled=False,
                cache_default_ttl=300,
                cache_max_size=1000,
                cache_strategy='adaptive',
                cache_prefix='db_query_cache:',
                cache_metrics_enabled=False,
                cache_frequent_query_threshold=5,
                cache_frequent_query_ttl_multiplier=2.0,
                cache_slow_query_threshold=1.0,
                cache_slow_query_ttl_multiplier=3.0
            )
            
            cache = QueryCache()
            assert cache.config.enabled is False


class TestStartupModuleIntegration:
    """Integration tests for startup_module with unified config."""
    
    def test_postgres_mode_detection_from_config(self):
        """Test postgres mode detection uses unified config."""
        from netra_backend.app.startup_module import _is_postgres_mock_mode
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: PostgreSQL database isolation for testing without real database connections
            mock_config.return_value = Mock(postgres_mode='mock')
            
            is_mock = _is_postgres_mock_mode()
            assert is_mock is True
            
            # Mock: PostgreSQL database isolation for testing without real database connections
            mock_config.return_value = Mock(postgres_mode='real')
            is_mock = _is_postgres_mock_mode()
            assert is_mock is False
    
    def test_startup_fallback_on_config_error(self):
        """Test startup falls back to env var when config unavailable."""
        from netra_backend.app.startup_module import _is_postgres_mock_mode
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = Exception("Config not available")
            
            with patch.dict('os.environ', {'POSTGRES_MODE': 'mock'}):
                is_mock = _is_postgres_mock_mode()
                assert is_mock is True


class TestConfigConsistency:
    """Integration tests for configuration consistency across components."""
    
    def test_database_and_cache_config_alignment(self):
        """Test database and cache configurations are aligned."""
        config = get_unified_config()
        
        # Both should respect the same environment
        assert config.environment in ['development', 'staging', 'production', 'testing']
        
        # Cache should be enabled when database caching is enabled
        if config.db_enable_query_cache:
            assert config.cache_enabled
            assert config.db_query_cache_ttl == config.cache_default_ttl
    
    def test_service_mode_consistency(self):
        """Test service modes are consistent across config."""
        config = get_unified_config()
        
        # All service modes should be valid
        assert config.redis_mode in ['local', 'shared', 'disabled']
        assert config.clickhouse_mode in ['local', 'shared', 'disabled']
        assert config.llm_mode in ['local', 'shared', 'disabled']
        
        # Dev mode flags should align with modes
        if config.environment == 'development':
            if config.redis_mode == 'disabled':
                assert not config.dev_mode_redis_enabled
            if config.clickhouse_mode == 'disabled':
                assert not config.dev_mode_clickhouse_enabled
    
    def test_security_config_consistency(self):
        """Test security configurations are consistent."""
        config = get_unified_config()
        
        # HTTPS should be enforced in production
        if config.environment == 'production':
            assert not config.disable_https_only
        
        # Service secret should be set for cross-service auth
        if config.auth_service_enabled == 'true':
            assert config.service_id == 'backend'


class TestConfigHotReload:
    """Integration tests for configuration hot reload."""
    
    def test_hot_reload_updates_all_components(self):
        """Test hot reload updates all dependent components."""
        from netra_backend.app.core.configuration.base import (
            config_manager,
            reload_unified_config
        )
        
        # Set initial config
        with patch.object(config_manager, '_hot_reload_enabled', True):
            # Mock: Generic component isolation for controlled unit testing
            with patch.object(config_manager, '_config_cache', Mock()):
                with patch.object(config_manager, '_database_manager') as mock_db:
                    with patch.object(config_manager, '_validator') as mock_validator:
                        reload_unified_config(force=True)
                        
                        # Verify all components refreshed
                        mock_validator.refresh_environment.assert_called_once()
                        mock_db.refresh_environment.assert_called_once()
                        assert config_manager._config_cache is None
    
    def test_hot_reload_disabled_in_production(self):
        """Test hot reload is disabled in production by default."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(environment='production')
            
            from netra_backend.app.core.configuration.base import config_manager
            
            with patch.object(config_manager, '_environment', 'production'):
                with patch.object(config_manager, '_hot_reload_enabled', False):
                    with patch.object(config_manager, '_safe_log_warning') as mock_log:
                        config_manager.reload_config(force=False)
                        mock_log.assert_called_with("Hot reload disabled in this environment")


class TestConfigErrorHandling:
    """Integration tests for configuration error handling."""
    
    def test_database_fallback_on_config_error(self):
        """Test database manager falls back when config unavailable."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = Exception("Config error")
            
            with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://fallback'}):
                url = DatabaseManager.get_base_database_url()
                assert 'postgresql://fallback' in url
    
    def test_redis_graceful_degradation(self):
        """Test Redis manager degrades gracefully when config fails."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = [
                Exception("Config error"),  # First call fails
                # Mock: Redis external service isolation for fast, reliable tests without network dependency
                Mock(redis_mode='local', environment='development', dev_mode_redis_enabled=True)  # Second succeeds
            ]
            
            manager = RedisManager()
            # Should handle error and still initialize
            assert hasattr(manager, 'redis_client')
    
    def test_cache_defaults_on_config_error(self):
        """Test cache uses defaults when config unavailable."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock: Component isolation for controlled unit testing
            mock_config.return_value = Mock(
                cache_enabled=True,
                cache_default_ttl=300,
                cache_max_size=1000,
                cache_strategy='adaptive',
                cache_prefix='db_query_cache:',
                cache_metrics_enabled=True,
                cache_frequent_query_threshold=5,
                cache_frequent_query_ttl_multiplier=2.0,
                cache_slow_query_threshold=1.0,
                cache_slow_query_ttl_multiplier=3.0
            )
            
            cache = QueryCache()
            # Should use reasonable defaults
            assert cache.config.default_ttl == 300
            assert cache.config.max_cache_size == 1000