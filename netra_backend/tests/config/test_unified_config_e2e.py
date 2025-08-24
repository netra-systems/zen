"""End-to-End Tests for Unified Configuration System

These tests validate the complete configuration flow from environment
variables through to actual service usage, testing real scenarios.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

from netra_backend.app.core.configuration.base import (
    get_unified_config,
    reload_unified_config,
    validate_config_integrity,
)


class TestConfigurationBootstrap:
    """E2E tests for configuration bootstrap process."""
    
    def test_fresh_startup_loads_config(self):
        """Test fresh application startup loads configuration correctly."""
        # Simulate fresh startup
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://localhost/testdb',
            'REDIS_URL': 'redis://localhost:6379',
        }, clear=True):
            # Clear any cached config
            from netra_backend.app.core.configuration.base import config_manager
            config_manager._config_cache = None
            
            # Load config fresh
            config = get_unified_config()
            
            assert config.environment == 'development'
            assert config.database_url == 'postgresql://localhost/testdb'
            assert config.redis_url == 'redis://localhost:6379'
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': '0'})
    def test_staging_environment_bootstrap(self):
        """Test staging environment bootstrap with GCP settings."""
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend',
            'K_REVISION': 'netra-backend-00001',
            'GCP_PROJECT_ID_NUMERICAL_STAGING': '701982941522',
        }):
            from netra_backend.app.core.configuration.base import config_manager
            config_manager._config_cache = None
            config_manager._environment = config_manager._detect_environment()
            
            config = get_unified_config()
            
            assert config.environment in ['staging', 'testing']
            assert config.k_service == 'netra-backend'
            assert config.k_revision == 'netra-backend-00001'
    
    def test_production_environment_security(self):
        """Test production environment enforces security settings."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            from netra_backend.app.core.configuration.base import config_manager
            config_manager._config_cache = None
            config_manager._environment = 'production'
            
            with patch.object(config_manager, '_get_config_class_for_environment'):
                config = get_unified_config()
                
                # Production should enforce security
                assert not config.disable_https_only
                assert not config.log_secrets


class TestDatabaseE2E:
    """E2E tests for database configuration usage."""
    
    @pytest.mark.asyncio
    async def test_database_connection_lifecycle(self):
        """Test complete database connection lifecycle with config."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/testdb',
        }):
            # Get URLs for different contexts
            base_url = DatabaseManager.get_base_database_url()
            migration_url = DatabaseManager.get_migration_url_sync_format()
            app_url = DatabaseManager.get_application_url_async()
            
            assert 'postgresql://' in base_url
            assert 'postgresql://' in migration_url or 'postgresql+pg8000://' in migration_url
            assert 'postgresql+asyncpg://' in app_url
    
    @pytest.mark.asyncio
    async def test_database_pool_behavior(self):
        """Test database pool behavior with config settings."""
        from netra_backend.app.db.postgres_core import AsyncDatabase
        
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.return_value = Mock(
                db_pool_size=5,
                db_max_overflow=10,
                db_pool_timeout=30,
                db_pool_recycle=600,
                db_echo=False,
                db_echo_pool=False
            )
            
            with patch('netra_backend.app.db.postgres_core.create_async_engine') as mock_engine:
                mock_engine.return_value = AsyncMock()
                
                db = AsyncDatabase('postgresql+asyncpg://localhost/test')
                
                # Verify pool settings applied with minimums
                call_kwargs = mock_engine.call_args[1]
                assert call_kwargs['pool_size'] >= 10  # Minimum enforced
                assert call_kwargs['pool_recycle'] == 600
    
    def test_database_transaction_retry_config(self):
        """Test database transaction retry uses config settings."""
        config = get_unified_config()
        
        assert config.db_transaction_retry_attempts == 3
        assert config.db_transaction_retry_delay == 0.1
        assert config.db_transaction_retry_backoff == 2.0
        
        # Simulate retry logic
        attempts = 0
        delay = config.db_transaction_retry_delay
        
        for i in range(config.db_transaction_retry_attempts):
            attempts += 1
            if i > 0:
                delay *= config.db_transaction_retry_backoff
        
        assert attempts == 3
        assert delay == 0.1 * (2.0 ** 2)  # 0.4


class TestRedisE2E:
    """E2E tests for Redis configuration usage."""
    
    @pytest.mark.asyncio
    async def test_redis_connection_modes(self):
        """Test Redis connection in different modes."""
        from netra_backend.app.redis_manager import RedisManager
        
        # Test local mode
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.return_value = Mock(
                redis_mode='local',
                environment='development',
                dev_mode_redis_enabled=True,
                redis=Mock(host='localhost', port=6379, username='default', password=None)
            )
            
            manager = RedisManager()
            assert manager._get_redis_mode() == 'local'
            
            # Test shared mode
            mock_config.return_value.redis_mode = 'shared'
            manager = RedisManager()
            assert manager._get_redis_mode() == 'shared'
            
            # Test disabled mode
            mock_config.return_value.redis_mode = 'disabled'
            manager = RedisManager()
            assert not manager.enabled
    
    @pytest.mark.asyncio
    async def test_redis_failover_scenario(self):
        """Test Redis failover from shared to local."""
        from netra_backend.app.redis_manager import RedisManager
        
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            config_obj = Mock(
                redis_mode='shared',
                environment='development',
                dev_mode_redis_enabled=True,
                redis=Mock(
                    host='failing.redis.com',
                    port=6379,
                    username='user',
                    password='pass'
                )
            )
            mock_config.return_value = config_obj
            
            manager = RedisManager()
            
            with patch.object(manager, '_create_redis_client') as mock_create:
                mock_client = AsyncMock()
                mock_client.ping.side_effect = [
                    Exception("Connection failed"),  # First attempt fails
                    None  # Second attempt (local) succeeds
                ]
                mock_create.return_value = mock_client
                
                await manager.connect()
                
                # Should have switched to local mode
                assert config_obj.redis_mode == 'local'


class TestCacheE2E:
    """E2E tests for cache configuration usage."""
    
    @pytest.mark.asyncio
    async def test_cache_with_adaptive_ttl(self):
        """Test cache with adaptive TTL strategy from config."""
        from netra_backend.app.db.cache_core import QueryCache
        from netra_backend.app.db.cache_config import AdaptiveTTLCalculator
        
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.return_value = Mock(
                cache_enabled=True,
                cache_default_ttl=300,
                cache_max_size=1000,
                cache_strategy='adaptive',
                cache_prefix='test:',
                cache_metrics_enabled=True,
                cache_frequent_query_threshold=3,
                cache_frequent_query_ttl_multiplier=2.0,
                cache_slow_query_threshold=1.0,
                cache_slow_query_ttl_multiplier=3.0
            )
            
            cache = QueryCache()
            
            # Test adaptive TTL calculation
            query_patterns = {'SELECT * FROM users': 5}  # Frequent query
            
            ttl = AdaptiveTTLCalculator.calculate_adaptive_ttl(
                'SELECT * FROM users',
                0.5,  # Fast query
                query_patterns,
                cache.config
            )
            
            # Should get frequent query multiplier
            assert ttl == 600  # 300 * 2.0
    
    @pytest.mark.asyncio
    async def test_cache_disabled_scenario(self):
        """Test cache behavior when disabled via config."""
        from netra_backend.app.db.cache_core import QueryCache
        
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.return_value = Mock(
                cache_enabled=False,
                cache_default_ttl=300,
                cache_max_size=1000,
                cache_strategy='adaptive',
                cache_prefix='test:',
                cache_metrics_enabled=False,
                cache_frequent_query_threshold=5,
                cache_frequent_query_ttl_multiplier=2.0,
                cache_slow_query_threshold=1.0,
                cache_slow_query_ttl_multiplier=3.0
            )
            
            cache = QueryCache()
            
            # Cache should not store when disabled
            result = await cache.cache_result(
                'SELECT * FROM test',
                [{'id': 1}],
                None,
                1.0,
                None
            )
            
            assert result is False  # Should not cache


class TestMultiEnvironmentE2E:
    """E2E tests for multi-environment configuration."""
    
    def test_development_to_staging_transition(self):
        """Test configuration transition from development to staging."""
        from netra_backend.app.core.configuration.base import config_manager
        
        # Start in development
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            config_manager._config_cache = None
            config_manager._environment = 'development'
            
            dev_config = get_unified_config()
            assert dev_config.environment == 'development'
            assert dev_config.log_level == 'DEBUG'
        
        # Transition to staging
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            reload_unified_config(force=True)
            
            staging_config = get_unified_config()
            assert staging_config.environment in ['staging', 'testing']
            assert staging_config.log_level == 'INFO'
    
    def test_pr_environment_detection(self):
        """Test PR environment detection and configuration."""
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'staging',
            'PR_NUMBER': '123',
            'K_SERVICE': 'netra-backend-pr-123'
        }):
            from netra_backend.app.core.configuration.base import config_manager
            config_manager._config_cache = None
            
            config = get_unified_config()
            
            assert config.pr_number == '123'
            assert config.k_service == 'netra-backend-pr-123'
            assert config.environment in ['staging', 'testing']


class TestConfigValidationE2E:
    """E2E tests for configuration validation."""
    
    def test_complete_config_validation(self):
        """Test complete configuration validation process."""
        config = get_unified_config()
        valid, issues = validate_config_integrity()
        
        # Even with missing secrets, config should load
        assert config is not None
        
        # Check for critical fields
        assert hasattr(config, 'environment')
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'redis_url')
    
    def test_validation_with_missing_secrets(self):
        """Test validation identifies missing secrets."""
        with patch('netra_backend.app.core.configuration.base.config_manager._secrets_manager') as mock_secrets:
            mock_secrets.validate_secrets_consistency.return_value = [
                'Missing secret: JWT_SECRET_KEY',
                'Missing secret: FERNET_KEY'
            ]
            
            valid, issues = validate_config_integrity()
            
            assert not valid
            assert len(issues) >= 2
            assert any('JWT_SECRET_KEY' in issue for issue in issues)
    
    def test_validation_with_database_issues(self):
        """Test validation identifies database configuration issues."""
        with patch('netra_backend.app.core.configuration.base.config_manager._database_manager') as mock_db:
            mock_db.validate_database_consistency.return_value = [
                'Database URL not configured',
                'Pool size below minimum'
            ]
            
            valid, issues = validate_config_integrity()
            
            assert not valid
            assert any('Database' in issue for issue in issues)


class TestConfigPerformanceE2E:
    """E2E tests for configuration performance."""
    
    def test_config_caching_performance(self):
        """Test configuration caching improves performance."""
        import time
        
        # First load (cold)
        start = time.time()
        config1 = get_unified_config()
        cold_time = time.time() - start
        
        # Second load (cached)
        start = time.time()
        config2 = get_unified_config()
        cached_time = time.time() - start
        
        assert config1 is config2  # Same instance
        assert cached_time < cold_time * 0.1  # At least 10x faster
    
    def test_hot_reload_performance(self):
        """Test hot reload performance is acceptable."""
        import time
        
        start = time.time()
        reload_unified_config(force=True)
        reload_time = time.time() - start
        
        # Reload should be fast
        assert reload_time < 1.0  # Less than 1 second


class TestConfigRecoveryE2E:
    """E2E tests for configuration error recovery."""
    
    def test_recovery_from_corrupt_config(self):
        """Test recovery from corrupted configuration."""
        from netra_backend.app.core.configuration.base import config_manager
        
        # Simulate corrupted config
        with patch.object(config_manager, '_create_base_config') as mock_create:
            mock_create.side_effect = [
                Exception("Config corrupted"),
                Mock(environment='development')  # Recovery succeeds
            ]
            
            # First attempt fails
            config_manager._config_cache = None
            try:
                config = config_manager.get_config()
            except:
                pass
            
            # Recovery attempt
            mock_create.side_effect = None
            mock_create.return_value = Mock(
                environment='development',
                database_url='postgresql://localhost/recovery'
            )
            
            config = config_manager.get_config()
            assert config.environment == 'development'
    
    def test_fallback_chain_for_critical_services(self):
        """Test fallback chain for critical service configuration."""
        # Test database fallback chain
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = Exception("Config unavailable")
            
            with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://fallback/db'}):
                from netra_backend.app.db.database_manager import DatabaseManager
                
                url = DatabaseManager.get_base_database_url()
                assert 'postgresql://fallback/db' in url
        
        # Test Redis fallback chain
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # First call fails, second returns config
            mock_config.side_effect = [
                Exception("Config error"),
                Mock(redis_mode='local', environment='development', dev_mode_redis_enabled=True)
            ]
            
            from netra_backend.app.redis_manager import RedisManager
            manager = RedisManager()
            
            # Should recover and initialize
            assert hasattr(manager, 'enabled')


class TestConfigObservabilityE2E:
    """E2E tests for configuration observability."""
    
    def test_config_summary_provides_insights(self):
        """Test configuration summary provides operational insights."""
        from netra_backend.app.core.configuration.base import config_manager
        
        summary = config_manager.get_config_summary()
        
        # Should provide key operational metrics
        assert 'environment' in summary
        assert 'database_configured' in summary
        assert 'secrets_loaded' in summary
        assert 'services_enabled' in summary
        assert 'hot_reload_enabled' in summary
        
        # Should have meaningful values
        assert summary['environment'] in ['development', 'staging', 'production', 'testing']
        assert isinstance(summary['database_configured'], bool)
        assert isinstance(summary['secrets_loaded'], int)
    
    def test_environment_overrides_visibility(self):
        """Test environment override detection for debugging."""
        from netra_backend.app.core.configuration.base import config_manager
        
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://override/db',
            'REDIS_URL': 'redis://override:6379',
            'CONFIG_HOT_RELOAD': 'true'
        }):
            overrides = config_manager.get_environment_overrides()
            
            assert overrides['DATABASE_URL'] == 'postgresql://override/db'
            assert overrides['REDIS_URL'] == 'redis://override:6379'
            assert overrides['CONFIG_HOT_RELOAD'] == 'true'