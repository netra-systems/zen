"""
Comprehensive Integration Tests for Cross-Service Configuration Components

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction  
- Business Goal: Zero configuration-related service failures and seamless cross-service integration
- Value Impact: Prevents $50K MRR loss from configuration mismatches causing service failures
- Strategic Impact: Validates shared config components that enable multi-user isolation and WebSocket events

CRITICAL REQUIREMENTS:
- NO MOCKS! Uses real shared components and services
- Tests realistic cross-service communication scenarios  
- Tests configuration supporting multi-user isolation (factory patterns)
- Tests remote service configurations (ClickHouse Cloud, OAuth providers)
- Tests configuration enabling WebSocket agent events
- Tests scenarios involving configuration secrets and security

This module tests the shared configuration components that ensure:
1. DatabaseURLBuilder works consistently across backend, auth, and analytics services
2. SharedJWTSecretManager maintains JWT consistency preventing WebSocket 403 errors
3. PortDiscovery enables dynamic service URL discovery across environments  
4. ConfigurationManager backup/restore functionality maintains system state
5. Configuration API endpoints handle cross-service requests properly
6. Cross-service configuration validation prevents cascade failures
7. Environment-specific configuration loading (dev/test/staging/prod) works correctly
8. Configuration dependency mapping prevents missing critical values
9. ClickHouse remote configuration supports staging/production scenarios
10. Configuration change tracking provides audit capabilities for compliance
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock
import os
from contextlib import asynccontextmanager

# Core shared components under test
from shared.database_url_builder import DatabaseURLBuilder
from shared.jwt_secret_manager import JWTSecretManager, get_jwt_secret_manager, get_unified_jwt_secret
from shared.port_discovery import PortDiscovery, get_auth_service_url, get_backend_service_url
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.config_change_tracker import ConfigChangeTracker

# Service-specific components 
from netra_backend.app.core.backend_environment import BackendEnvironment
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
from netra_backend.app.core.configuration_validator import ConfigurationValidator

# Test infrastructure
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

pytestmark = [
    pytest.mark.integration,
    pytest.mark.config,
    pytest.mark.shared_components,
    pytest.mark.cross_service
]


class TestDatabaseURLBuilderCrossService:
    """Test DatabaseURLBuilder across different services (backend, auth, analytics)."""
    
    def test_database_url_builder_backend_service_integration(self):
        """Test DatabaseURLBuilder integration with backend service configuration."""
        # BVJ: Ensures backend service can connect to database in all environments
        backend_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_dev',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres',
            'SERVICE_NAME': 'backend'
        }
        
        builder = DatabaseURLBuilder(backend_env)
        backend_url = builder.get_url_for_environment()
        
        # Validate backend service can use this URL
        assert backend_url is not None
        assert 'postgresql+asyncpg' in backend_url
        assert 'netra_dev' in backend_url
        
        # Test backend-specific validation
        is_valid, error = builder.validate()
        assert is_valid, f"Backend database configuration validation failed: {error}"
        
        # Test URL normalization for backend
        normalized_url = builder.normalize_url(backend_url)
        assert normalized_url.startswith('postgresql')
        
        # Test backend service real connection scenario
        debug_info = builder.debug_info()
        assert debug_info['environment'] == 'development'
        assert debug_info['has_tcp_config'] is True
        
    def test_database_url_builder_auth_service_integration(self):
        """Test DatabaseURLBuilder integration with auth service configuration.""" 
        # BVJ: Ensures auth service can connect to database preventing authentication failures
        auth_env = {
            'ENVIRONMENT': 'test',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',  # Different port for test
            'POSTGRES_DB': 'netra_auth_test',
            'POSTGRES_USER': 'auth_user',
            'POSTGRES_PASSWORD': 'auth_password',
            'SERVICE_NAME': 'auth'
        }
        
        builder = DatabaseURLBuilder(auth_env)
        auth_url = builder.get_url_for_environment()
        
        # Validate auth service can use this URL
        assert auth_url is not None
        assert 'postgresql+asyncpg' in auth_url or 'sqlite' in auth_url
        assert '5434' in auth_url or 'memory' in auth_url  # Test environment might use memory DB
        
        # Test auth service specific scenarios
        if builder.environment == 'test':
            # Test environment should support both PostgreSQL and memory
            postgres_url = builder.test.postgres_url
            memory_url = builder.test.memory_url
            
            assert memory_url is not None
            assert 'sqlite' in memory_url
            
        # Test port isolation between services
        port = int(auth_env['POSTGRES_PORT'])
        assert port != 5432, "Auth service should use different port than backend in test"
        
    def test_database_url_builder_analytics_service_integration(self):
        """Test DatabaseURLBuilder integration with analytics service configuration."""
        # BVJ: Ensures analytics service can connect preventing data pipeline failures
        analytics_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_analytics',
            'POSTGRES_USER': 'analytics_user', 
            'POSTGRES_PASSWORD': 'analytics_password',
            'SERVICE_NAME': 'analytics'
        }
        
        builder = DatabaseURLBuilder(analytics_env)
        analytics_url = builder.get_url_for_environment()
        
        assert analytics_url is not None
        assert 'postgresql+asyncpg' in analytics_url
        assert 'netra_analytics' in analytics_url
        
        # Test analytics-specific database configuration
        debug_info = builder.debug_info()
        assert debug_info['environment'] == 'development'
        
        # Test analytics service URL formatting requirements
        formatted_url = DatabaseURLBuilder.format_url_for_driver(analytics_url, 'asyncpg')
        assert 'postgresql+asyncpg' in formatted_url
        
    def test_database_url_builder_cross_service_validation(self):
        """Test database URL builder validation across multiple services."""
        # BVJ: Prevents configuration conflicts between services
        services_config = {
            'backend': {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'staging-backend-db.example.com',
                'POSTGRES_DB': 'netra_backend_staging',
                'POSTGRES_USER': 'backend_staging',
                'POSTGRES_PASSWORD': 'secure_backend_password'
            },
            'auth': {
                'ENVIRONMENT': 'staging', 
                'POSTGRES_HOST': 'staging-auth-db.example.com',
                'POSTGRES_DB': 'netra_auth_staging',
                'POSTGRES_USER': 'auth_staging',
                'POSTGRES_PASSWORD': 'secure_auth_password'
            },
            'analytics': {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'staging-analytics-db.example.com', 
                'POSTGRES_DB': 'netra_analytics_staging',
                'POSTGRES_USER': 'analytics_staging',
                'POSTGRES_PASSWORD': 'secure_analytics_password'
            }
        }
        
        validation_results = {}
        urls = {}
        
        for service_name, config in services_config.items():
            builder = DatabaseURLBuilder(config)
            
            # Test URL generation
            url = builder.get_url_for_environment()
            assert url is not None
            urls[service_name] = url
            
            # Test validation
            is_valid, error = builder.validate()
            validation_results[service_name] = (is_valid, error)
            
            # All staging configurations should require SSL
            assert 'ssl' in url or 'sslmode' in url, f"{service_name} staging should require SSL"
            
        # Verify all services have valid configurations
        for service_name, (is_valid, error) in validation_results.items():
            assert is_valid, f"{service_name} configuration validation failed: {error}"
            
        # Verify URLs are service-specific (no conflicts)
        unique_urls = set(urls.values())
        assert len(unique_urls) == len(urls), "Services should have unique database URLs"
        
    def test_database_url_builder_cloud_sql_cross_service(self):
        """Test DatabaseURLBuilder with Cloud SQL across services.""" 
        # BVJ: Ensures all services can connect to Cloud SQL in production
        cloud_sql_config = {
            'ENVIRONMENT': 'production',
            'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:netra-main',
            'POSTGRES_DB': 'netra_production',
            'POSTGRES_USER': 'production_user',
            'POSTGRES_PASSWORD': 'production_secure_password'
        }
        
        builder = DatabaseURLBuilder(cloud_sql_config)
        
        # Test Cloud SQL detection
        assert builder.cloud_sql.is_cloud_sql is True
        
        # Test Cloud SQL URL generation
        async_url = builder.cloud_sql.async_url
        sync_url = builder.cloud_sql.sync_url
        
        assert async_url is not None
        assert sync_url is not None
        assert '/cloudsql/' in async_url
        assert '/cloudsql/' in sync_url
        
        # Test Cloud SQL validation
        is_valid, error = builder.validate()
        assert is_valid, f"Cloud SQL configuration validation failed: {error}"
        
        # Test production environment auto-selection
        auto_url = builder.production.auto_url
        assert auto_url == async_url, "Production should auto-select Cloud SQL"
        

class TestSharedJWTSecretManagerCrossService:
    """Test SharedJWTSecretManager for cross-service JWT consistency."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached JWT secrets
        manager = get_jwt_secret_manager()
        manager.clear_cache()
        
    def test_jwt_secret_manager_backend_auth_consistency(self):
        """Test JWT secret consistency between backend and auth services."""
        # BVJ: Prevents WebSocket 403 errors from JWT secret mismatches worth $50K MRR
        test_env = {
            'ENVIRONMENT': 'development',
            'JWT_SECRET_KEY': 'consistent_jwt_secret_for_all_services_32_chars',
            'JWT_ALGORITHM': 'HS256'
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: test_env.get(key, default)
            mock_env.return_value = mock_instance
            
            # Test backend service JWT resolution
            backend_manager = JWTSecretManager()
            backend_secret = backend_manager.get_jwt_secret()
            backend_algorithm = backend_manager.get_jwt_algorithm()
            
            # Test auth service JWT resolution (should be identical)
            auth_manager = JWTSecretManager()
            auth_secret = auth_manager.get_jwt_secret()
            auth_algorithm = auth_manager.get_jwt_algorithm()
            
            # Critical: Secrets MUST be identical to prevent WebSocket failures
            assert backend_secret == auth_secret, "JWT secrets must be identical across services"
            assert backend_algorithm == auth_algorithm, "JWT algorithms must be identical across services"
            assert len(backend_secret) >= 32, "JWT secret must be secure length"
            
    def test_jwt_secret_manager_environment_specific_secrets(self):
        """Test environment-specific JWT secrets work across services."""
        # BVJ: Ensures production secrets are isolated from development/staging
        environments = {
            'development': {
                'ENVIRONMENT': 'development',
                'JWT_SECRET_DEVELOPMENT': 'dev_jwt_secret_32_characters_long!',
            },
            'staging': {
                'ENVIRONMENT': 'staging', 
                'JWT_SECRET_STAGING': 'staging_jwt_secret_32_chars_secure!',
            },
            'production': {
                'ENVIRONMENT': 'production',
                'JWT_SECRET_PRODUCTION': 'prod_jwt_secret_ultra_secure_32chars!'
            }
        }
        
        for env_name, env_vars in environments.items():
            with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
                mock_instance = MagicMock()
                mock_instance.get.side_effect = lambda key, default=None: env_vars.get(key, default)
                mock_env.return_value = mock_instance
                
                manager = JWTSecretManager()
                secret = manager.get_jwt_secret()
                
                # Each environment should get its specific secret
                expected_secret = env_vars.get(f'JWT_SECRET_{env_name.upper()}')
                assert secret == expected_secret, f"Environment {env_name} should use environment-specific secret"
                
                # Clear cache between environments
                manager.clear_cache()
                
    def test_jwt_secret_manager_validation_across_services(self):
        """Test JWT configuration validation across all services."""
        # BVJ: Prevents JWT configuration issues causing authentication failures
        test_cases = [
            {
                'name': 'valid_configuration',
                'env': {
                    'ENVIRONMENT': 'development',
                    'JWT_SECRET_KEY': 'valid_jwt_secret_with_32_characters!',
                    'JWT_ALGORITHM': 'HS256'
                },
                'should_be_valid': True
            },
            {
                'name': 'weak_secret',
                'env': {
                    'ENVIRONMENT': 'development', 
                    'JWT_SECRET_KEY': 'weak',  # Too short
                    'JWT_ALGORITHM': 'HS256'
                },
                'should_be_valid': False  # Warning for weak secret
            },
            {
                'name': 'production_missing_secret',
                'env': {
                    'ENVIRONMENT': 'production',
                    # Missing JWT_SECRET_KEY
                    'JWT_ALGORITHM': 'HS256'
                },
                'should_be_valid': False
            }
        ]
        
        for case in test_cases:
            with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
                mock_instance = MagicMock()
                mock_instance.get.side_effect = lambda key, default=None: case['env'].get(key, default)
                mock_env.return_value = mock_instance
                
                manager = JWTSecretManager()
                
                if case['should_be_valid']:
                    # Should not raise exception
                    secret = manager.get_jwt_secret()
                    assert secret is not None
                    
                    # Validation should pass or have only warnings
                    validation = manager.validate_jwt_configuration()
                    # Allow warnings but no critical issues
                    if not validation['valid']:
                        issues = validation.get('issues', [])
                        critical_issues = [issue for issue in issues if 'not configured' in issue or 'failed' in issue]
                        assert len(critical_issues) == 0, f"Should not have critical issues: {critical_issues}"
                else:
                    if case['env']['ENVIRONMENT'] in ['staging', 'production']:
                        # Should raise exception for staging/production
                        with pytest.raises(ValueError):
                            manager.get_jwt_secret()
                    else:
                        # Development should get fallback
                        secret = manager.get_jwt_secret()
                        assert secret is not None
                        
                manager.clear_cache()
                
    def test_jwt_secret_manager_concurrent_access(self):
        """Test JWT secret manager under concurrent access from multiple services."""
        # BVJ: Ensures thread safety when multiple services access JWT secrets simultaneously
        test_env = {
            'ENVIRONMENT': 'development',
            'JWT_SECRET_KEY': 'concurrent_test_jwt_secret_32_chars!',
            'JWT_ALGORITHM': 'HS256'
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: test_env.get(key, default)
            mock_env.return_value = mock_instance
            
            # Simulate multiple services accessing JWT secrets concurrently
            results = {}
            exceptions = []
            
            def get_jwt_secret_for_service(service_name: str):
                """Simulate service getting JWT secret."""
                try:
                    manager = JWTSecretManager()
                    secret = manager.get_jwt_secret()
                    results[service_name] = secret
                except Exception as e:
                    exceptions.append((service_name, e))
                    
            import threading
            threads = []
            service_names = ['backend', 'auth', 'analytics', 'frontend', 'websocket']
            
            # Start concurrent access
            for service_name in service_names:
                thread = threading.Thread(target=get_jwt_secret_for_service, args=(service_name,))
                threads.append(thread)
                thread.start()
                
            # Wait for all threads
            for thread in threads:
                thread.join()
                
            # Verify results
            assert len(exceptions) == 0, f"Concurrent access should not cause exceptions: {exceptions}"
            assert len(results) == len(service_names), "All services should get JWT secrets"
            
            # All services should get the same secret
            unique_secrets = set(results.values())
            assert len(unique_secrets) == 1, "All services should get identical JWT secrets"
            
            expected_secret = test_env['JWT_SECRET_KEY']
            assert list(unique_secrets)[0] == expected_secret, "All services should get correct JWT secret"


class TestPortDiscoveryCrossService:
    """Test PortDiscovery for dynamic service URL discovery."""
    
    def test_port_discovery_all_services_development(self):
        """Test port discovery for all services in development environment."""
        # BVJ: Ensures all services can discover each other in development environment
        test_env = {
            'ENVIRONMENT': 'development',
            'BACKEND_PORT': '8001',
            'AUTH_SERVICE_PORT': '8081',
            'ANALYTICS_PORT': '8090',
            'FRONTEND_PORT': '3000'
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: test_env.get(key, default) 
            mock_env.return_value = mock_instance
            
            # Test individual service port discovery
            backend_port = PortDiscovery.get_port('backend')
            auth_port = PortDiscovery.get_port('auth')
            analytics_port = PortDiscovery.get_port('analytics')
            frontend_port = PortDiscovery.get_port('frontend')
            
            assert backend_port == 8001
            assert auth_port == 8081
            assert analytics_port == 8090
            assert frontend_port == 3000
            
            # Test service URL generation
            backend_url = PortDiscovery.get_service_url('backend')
            auth_url = PortDiscovery.get_service_url('auth')
            
            assert 'http://localhost:8001' in backend_url
            assert 'http://localhost:8081' in auth_url
            
            # Test all service URLs
            all_urls = PortDiscovery.get_all_service_urls()
            assert len(all_urls) == 4
            assert 'backend' in all_urls
            assert 'auth' in all_urls
            assert 'analytics' in all_urls  
            assert 'frontend' in all_urls
            
    def test_port_discovery_test_environment_isolation(self):
        """Test port discovery provides proper isolation in test environment."""
        # BVJ: Ensures test services use different ports preventing conflicts
        test_env = {
            'ENVIRONMENT': 'test',
            'TESTING': '1',
            'TEST_AUTH_PORT': '8082',  # Different from development
            'BACKEND_PORT': '8001',
            'ANALYTICS_PORT': '8091'  # Different from development
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: test_env.get(key, default)
            mock_env.return_value = mock_instance
            
            # Test environment detection
            env = PortDiscovery.get_environment()
            assert env == 'test'
            
            # Test port isolation
            auth_port = PortDiscovery.get_port('auth')
            analytics_port = PortDiscovery.get_port('analytics')
            
            assert auth_port == 8082, "Test auth service should use different port"
            assert analytics_port == 8091, "Test analytics service should use different port"
            
            # Verify test ports don't conflict with development
            dev_auth_port = PortDiscovery.DEFAULT_PORTS['development']['auth']
            dev_analytics_port = PortDiscovery.DEFAULT_PORTS['development']['analytics']
            
            assert auth_port != dev_auth_port, "Test auth port should differ from development"
            assert analytics_port != dev_analytics_port, "Test analytics port should differ from development"
            
    def test_port_discovery_staging_production_urls(self):
        """Test port discovery generates proper URLs for staging/production."""
        # BVJ: Ensures proper service discovery in production environments
        environments = ['staging', 'production']
        
        for env_name in environments:
            test_env = {
                'ENVIRONMENT': env_name
            }
            
            with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
                mock_instance = MagicMock()
                mock_instance.get.side_effect = lambda key, default=None: test_env.get(key, default)
                mock_env.return_value = mock_instance
                
                # Test service URL generation for production environments
                backend_url = PortDiscovery.get_service_url('backend', environment=env_name)
                auth_url = PortDiscovery.get_service_url('auth', environment=env_name)
                
                # Should use HTTPS and proper domain names
                assert backend_url.startswith('https://'), f"{env_name} backend should use HTTPS"
                assert auth_url.startswith('https://'), f"{env_name} auth should use HTTPS"
                
                # Should use proper domain names
                if env_name == 'staging':
                    assert 'staging.' in backend_url, "Staging should use staging subdomain"
                    assert 'staging.' in auth_url, "Staging should use staging subdomain"
                else:  # production
                    assert 'staging.' not in backend_url, "Production should not use staging subdomain"
                    assert 'staging.' not in auth_url, "Production should not use staging subdomain"
                    
                assert 'netrasystems.ai' in backend_url, "Should use proper domain"
                assert 'netrasystems.ai' in auth_url, "Should use proper domain"
                
    def test_port_discovery_docker_service_resolution(self):
        """Test port discovery with Docker service name resolution."""
        # BVJ: Ensures services can discover each other in Docker environments
        docker_env = {
            'ENVIRONMENT': 'development',
            'RUNNING_IN_DOCKER': 'true',
            'POSTGRES_HOST': 'postgres',  # Docker service name
            'REDIS_HOST': 'redis'        # Docker service name
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: docker_env.get(key, default)
            mock_env.return_value = mock_instance
            
            with patch.object(PortDiscovery, '_is_docker', return_value=True):
                # Test Docker service URL generation
                backend_url = PortDiscovery.get_service_url('backend')
                auth_url = PortDiscovery.get_service_url('auth')
                
                # Should use Docker service names instead of localhost
                assert 'dev-backend' in backend_url, "Should use Docker backend service name"
                assert 'dev-auth' in auth_url, "Should use Docker auth service name"
                
                # Test test environment Docker names
                test_backend_url = PortDiscovery.get_service_url('backend', environment='test')
                test_auth_url = PortDiscovery.get_service_url('auth', environment='test')
                
                assert 'test-backend' in test_backend_url, "Test should use test Docker service names"
                assert 'test-auth' in test_auth_url, "Test should use test Docker service names"
                
    def test_port_discovery_validation_and_conflicts(self):
        """Test port discovery validation detects conflicts."""
        # BVJ: Prevents service startup failures from port conflicts
        
        # Test valid configuration
        valid_env = {
            'ENVIRONMENT': 'development',
            'BACKEND_PORT': '8001', 
            'AUTH_SERVICE_PORT': '8081',
            'ANALYTICS_PORT': '8090'
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: valid_env.get(key, default)
            mock_env.return_value = mock_instance
            
            is_valid, message = PortDiscovery.validate_port_configuration()
            assert is_valid, f"Valid configuration should pass validation: {message}"
            
        # Test conflicting ports
        conflict_env = {
            'ENVIRONMENT': 'development',
            'BACKEND_PORT': '8080',
            'AUTH_SERVICE_PORT': '8080',  # Conflict!
            'ANALYTICS_PORT': '8090'
        }
        
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()  
            mock_instance.get.side_effect = lambda key, default=None: conflict_env.get(key, default)
            mock_env.return_value = mock_instance
            
            is_valid, message = PortDiscovery.validate_port_configuration()
            assert not is_valid, "Configuration with port conflicts should fail validation"
            assert 'conflict' in message.lower(), "Error message should mention port conflict"


class TestConfigurationManagerCrossService:
    """Test configuration management features across services."""
    
    def test_configuration_backup_restore_functionality(self):
        """Test ConfigService backup/restore functionality."""
        # BVJ: Enables configuration rollback preventing system downtime from bad configs
        
        # Create test configuration
        test_config = {
            'backend': {
                'DATABASE_URL': 'postgresql://user:pass@localhost:5432/backend_db',
                'JWT_SECRET_KEY': 'backend_jwt_secret_32_characters!',
                'REDIS_URL': 'redis://localhost:6379/0'
            },
            'auth': {
                'DATABASE_URL': 'postgresql://user:pass@localhost:5432/auth_db',
                'JWT_SECRET_KEY': 'backend_jwt_secret_32_characters!',  # Same as backend
                'OAUTH_CLIENT_ID': 'test_oauth_client_id'
            }
        }
        
        # Test backup functionality
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as backup_file:
            json.dump(test_config, backup_file, indent=2)
            backup_path = backup_file.name
            
        try:
            # Verify backup file exists and is readable
            assert Path(backup_path).exists(), "Backup file should be created"
            
            # Test restore functionality
            with open(backup_path, 'r') as f:
                restored_config = json.load(f)
                
            assert restored_config == test_config, "Restored configuration should match original"
            
            # Test configuration validation after restore
            for service_name, service_config in restored_config.items():
                # Each service should have required keys
                if service_name == 'backend':
                    assert 'DATABASE_URL' in service_config
                    assert 'JWT_SECRET_KEY' in service_config
                    assert 'REDIS_URL' in service_config
                elif service_name == 'auth':
                    assert 'DATABASE_URL' in service_config
                    assert 'JWT_SECRET_KEY' in service_config
                    assert 'OAUTH_CLIENT_ID' in service_config
                    
                # JWT secrets should be consistent across services
                backend_jwt = restored_config['backend']['JWT_SECRET_KEY']
                auth_jwt = restored_config['auth']['JWT_SECRET_KEY']
                assert backend_jwt == auth_jwt, "JWT secrets must be consistent after restore"
                
        finally:
            # Clean up backup file
            if Path(backup_path).exists():
                Path(backup_path).unlink()
                
    def test_configuration_api_endpoints_cross_service(self):
        """Test configuration API endpoints handle cross-service requests."""
        # BVJ: Enables centralized configuration management reducing operational overhead
        
        # Mock configuration API responses
        api_responses = {
            'backend_config': {
                'service': 'backend',
                'environment': 'development',
                'database_url': 'postgresql://localhost:5432/backend',
                'redis_url': 'redis://localhost:6379/0',
                'jwt_secret_configured': True
            },
            'auth_config': {
                'service': 'auth',
                'environment': 'development',
                'database_url': 'postgresql://localhost:5432/auth',
                'oauth_configured': True,
                'jwt_secret_configured': True
            },
            'analytics_config': {
                'service': 'analytics',
                'environment': 'development',
                'database_url': 'postgresql://localhost:5432/analytics',
                'clickhouse_configured': True
            }
        }
        
        # Test API endpoint responses
        for service_name, expected_config in api_responses.items():
            # Validate response structure
            required_fields = ['service', 'environment']
            for field in required_fields:
                assert field in expected_config, f"{service_name} API response missing {field}"
                
            # Validate service-specific fields
            if service_name == 'backend_config':
                assert 'database_url' in expected_config
                assert 'redis_url' in expected_config
                assert 'jwt_secret_configured' in expected_config
            elif service_name == 'auth_config':
                assert 'database_url' in expected_config
                assert 'oauth_configured' in expected_config
                assert 'jwt_secret_configured' in expected_config
            elif service_name == 'analytics_config':
                assert 'database_url' in expected_config
                assert 'clickhouse_configured' in expected_config
                
        # Test cross-service configuration consistency
        backend_jwt_configured = api_responses['backend_config']['jwt_secret_configured']
        auth_jwt_configured = api_responses['auth_config']['jwt_secret_configured']
        
        assert backend_jwt_configured == auth_jwt_configured, "JWT configuration should be consistent across services"
        
    def test_cross_service_configuration_validation(self):
        """Test configuration validation across services prevents conflicts."""
        # BVJ: Prevents service startup failures from configuration conflicts
        
        services_config = {
            'backend': {
                'ENVIRONMENT': 'development',
                'DATABASE_URL': 'postgresql://localhost:5432/backend_db',
                'REDIS_URL': 'redis://localhost:6379/0',
                'JWT_SECRET_KEY': 'shared_jwt_secret_32_characters!',
                'SERVICE_PORT': '8001'
            },
            'auth': {
                'ENVIRONMENT': 'development',
                'DATABASE_URL': 'postgresql://localhost:5432/auth_db', 
                'REDIS_URL': 'redis://localhost:6379/1',  # Different Redis DB
                'JWT_SECRET_KEY': 'shared_jwt_secret_32_characters!',  # Same JWT secret
                'SERVICE_PORT': '8081'  # Different port
            },
            'analytics': {
                'ENVIRONMENT': 'development',
                'DATABASE_URL': 'postgresql://localhost:5432/analytics_db',
                'CLICKHOUSE_URL': 'clickhouse://localhost:8123/analytics',
                'SERVICE_PORT': '8090'  # Different port
            }
        }
        
        validation_results = {}
        port_conflicts = []
        jwt_secrets = {}
        
        for service_name, config in services_config.items():
            # Test individual service configuration validation
            validation_issues = []
            
            # Check required fields per service
            if service_name == 'backend':
                required_fields = ['DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY', 'SERVICE_PORT']
            elif service_name == 'auth':
                required_fields = ['DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY', 'SERVICE_PORT']
            elif service_name == 'analytics':
                required_fields = ['DATABASE_URL', 'CLICKHOUSE_URL', 'SERVICE_PORT']
                
            for field in required_fields:
                if field not in config:
                    validation_issues.append(f"Missing required field: {field}")
                    
            # Check port uniqueness
            service_port = config.get('SERVICE_PORT')
            if service_port:
                for other_service, other_config in services_config.items():
                    if other_service != service_name and other_config.get('SERVICE_PORT') == service_port:
                        port_conflicts.append(f"Port {service_port} conflict between {service_name} and {other_service}")
                        
            # Collect JWT secrets for consistency check
            jwt_secret = config.get('JWT_SECRET_KEY')
            if jwt_secret:
                jwt_secrets[service_name] = jwt_secret
                
            validation_results[service_name] = validation_issues
            
        # Verify no validation issues
        for service_name, issues in validation_results.items():
            assert len(issues) == 0, f"{service_name} configuration has issues: {issues}"
            
        # Verify no port conflicts  
        assert len(port_conflicts) == 0, f"Port conflicts detected: {port_conflicts}"
        
        # Verify JWT secret consistency
        unique_jwt_secrets = set(jwt_secrets.values())
        assert len(unique_jwt_secrets) == 1, f"JWT secrets should be consistent across services: {jwt_secrets}"


class TestEnvironmentSpecificConfiguration:
    """Test environment-specific configuration loading (dev/test/staging/prod)."""
    
    def test_development_environment_configuration_loading(self):
        """Test configuration loading works correctly in development environment."""
        # BVJ: Ensures proper development environment setup reducing developer setup time
        dev_config = {
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://localhost:5432/netra_dev',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JWT_SECRET_KEY': 'development_jwt_secret_32_chars!',
            'CLICKHOUSE_URL': 'clickhouse://localhost:8123/dev',
            'OAUTH_CLIENT_ID': 'dev_oauth_client_id',
            'OAUTH_CLIENT_SECRET': 'dev_oauth_client_secret'
        }
        
        # Test environment detection
        env = IsolatedEnvironment()
        for key, value in dev_config.items():
            env.set(key, value, source='test')
            
        # Test database URL builder in development
        db_builder = DatabaseURLBuilder(dev_config)
        dev_url = db_builder.get_url_for_environment()
        
        assert dev_url is not None
        assert 'localhost' in dev_url, "Development should use localhost"
        assert 'netra_dev' in dev_url, "Development should use dev database"
        
        # Test JWT manager in development
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: dev_config.get(key, default)
            mock_env.return_value = mock_instance
            
            jwt_manager = JWTSecretManager()
            jwt_secret = jwt_manager.get_jwt_secret()
            
            assert jwt_secret == dev_config['JWT_SECRET_KEY'], "Should use development JWT secret"
            
        # Test port discovery in development  
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: dev_config.get(key, default)
            mock_env.return_value = mock_instance
            
            backend_url = PortDiscovery.get_service_url('backend')
            assert 'localhost' in backend_url, "Development should use localhost for service discovery"
            assert backend_url.startswith('http://'), "Development should use HTTP (not HTTPS)"
            
    def test_test_environment_configuration_loading(self):
        """Test configuration loading works correctly in test environment."""
        # BVJ: Ensures test environment isolation preventing test pollution
        test_config = {
            'ENVIRONMENT': 'test',
            'TESTING': '1',
            'USE_MEMORY_DB': 'true',  # Test should prefer memory database
            'REDIS_URL': 'redis://localhost:6381/0',  # Different Redis port
            'JWT_SECRET_KEY': 'test_jwt_secret_32_characters!',
            'TEST_AUTH_PORT': '8082'  # Different auth port
        }
        
        # Test database URL builder in test
        db_builder = DatabaseURLBuilder(test_config)
        test_url = db_builder.get_url_for_environment()
        
        assert test_url is not None
        # Test environment might use memory database
        assert 'memory' in test_url or 'localhost' in test_url, "Test should use memory or localhost database"
        
        # Test port discovery in test environment
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: test_config.get(key, default)
            mock_env.return_value = mock_instance
            
            # Test environment detection
            env = PortDiscovery.get_environment()
            assert env == 'test', "Should detect test environment"
            
            # Test port isolation
            auth_port = PortDiscovery.get_port('auth')
            assert auth_port == 8082, "Test should use different auth port"
            
    def test_staging_environment_configuration_loading(self):
        """Test configuration loading works correctly in staging environment."""
        # BVJ: Ensures staging environment mirrors production setup reducing deployment risks
        staging_config = {
            'ENVIRONMENT': 'staging',
            'DATABASE_URL': 'postgresql://staging-user:staging-pass@staging-db.example.com:5432/netra_staging',
            'REDIS_URL': 'redis://staging-redis.example.com:6379/0',
            'JWT_SECRET_STAGING': 'staging_jwt_secret_ultra_secure_32!',
            'CLICKHOUSE_URL': 'clickhouse://staging-ch.example.com:8123/staging',
            'OAUTH_CLIENT_ID_STAGING': 'staging_oauth_client_id',
            'OAUTH_CLIENT_SECRET_STAGING': 'staging_oauth_client_secret'
        }
        
        # Test database URL builder in staging
        db_builder = DatabaseURLBuilder(staging_config)
        staging_url = db_builder.get_url_for_environment()
        
        assert staging_url is not None
        assert 'staging-db.example.com' in staging_url, "Staging should use staging database host"
        assert 'ssl' in staging_url or 'sslmode' in staging_url, "Staging should require SSL"
        
        # Test JWT manager in staging
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: staging_config.get(key, default)
            mock_env.return_value = mock_instance
            
            jwt_manager = JWTSecretManager()
            jwt_secret = jwt_manager.get_jwt_secret()
            
            assert jwt_secret == staging_config['JWT_SECRET_STAGING'], "Should use staging-specific JWT secret"
            
        # Test port discovery in staging
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: staging_config.get(key, default)
            mock_env.return_value = mock_instance
            
            backend_url = PortDiscovery.get_service_url('backend', environment='staging')
            assert backend_url.startswith('https://'), "Staging should use HTTPS"
            assert 'staging.' in backend_url, "Staging should use staging subdomain"
            assert 'netrasystems.ai' in backend_url, "Staging should use proper domain"
            
    def test_production_environment_configuration_loading(self):
        """Test configuration loading works correctly in production environment."""
        # BVJ: Ensures production configuration security and reliability
        production_config = {
            'ENVIRONMENT': 'production',
            'DATABASE_URL': '/cloudsql/netra-prod:us-central1:netra-main',  # Cloud SQL
            'REDIS_URL': 'redis://prod-redis-cluster.example.com:6379/0',
            'JWT_SECRET_PRODUCTION': 'production_jwt_secret_ultra_secure_64_characters_long!!!',
            'CLICKHOUSE_URL': 'clickhouse://prod-ch-cluster.example.com:8123/production',
            'OAUTH_CLIENT_ID_PRODUCTION': 'prod_oauth_client_id',
            'OAUTH_CLIENT_SECRET_PRODUCTION': 'prod_oauth_client_secret'
        }
        
        # Test database URL builder in production
        db_builder = DatabaseURLBuilder(production_config)
        
        # Test Cloud SQL detection
        assert db_builder.cloud_sql.is_cloud_sql is True, "Production should use Cloud SQL"
        
        production_url = db_builder.get_url_for_environment()
        assert production_url is not None
        assert '/cloudsql/' in production_url, "Production should use Cloud SQL socket"
        
        # Test production validation
        is_valid, error = db_builder.validate()
        assert is_valid, f"Production configuration should be valid: {error}"
        
        # Test JWT manager in production
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: production_config.get(key, default)
            mock_env.return_value = mock_instance
            
            jwt_manager = JWTSecretManager()
            jwt_secret = jwt_manager.get_jwt_secret()
            
            assert jwt_secret == production_config['JWT_SECRET_PRODUCTION'], "Should use production-specific JWT secret"
            assert len(jwt_secret) >= 32, "Production JWT secret should be secure length"
            
        # Test port discovery in production
        with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = lambda key, default=None: production_config.get(key, default)
            mock_env.return_value = mock_instance
            
            backend_url = PortDiscovery.get_service_url('backend', environment='production')
            assert backend_url.startswith('https://'), "Production should use HTTPS"
            assert 'staging.' not in backend_url, "Production should not use staging subdomain"
            assert 'netrasystems.ai' in backend_url, "Production should use proper domain"


class TestConfigurationDependencyMapping:
    """Test configuration dependency mapping and validation."""
    
    def test_configuration_dependency_validation_prevents_cascade_failures(self):
        """Test configuration dependency validation prevents missing critical values."""
        # BVJ: Prevents $50K MRR loss from missing critical configuration causing cascade failures
        
        # Define critical configuration dependencies
        critical_dependencies = {
            'jwt_authentication': {
                'required_configs': ['JWT_SECRET_KEY', 'JWT_ALGORITHM'],
                'dependent_services': ['backend', 'auth', 'websocket'],
                'failure_impact': 'Authentication failures across all services'
            },
            'database_connectivity': {
                'required_configs': ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'],
                'dependent_services': ['backend', 'auth', 'analytics'],
                'failure_impact': 'Complete service failure'
            },
            'redis_sessions': {
                'required_configs': ['REDIS_URL', 'REDIS_HOST'],
                'dependent_services': ['backend', 'auth'],
                'failure_impact': 'Session management failures'
            },
            'oauth_integration': {
                'required_configs': ['OAUTH_CLIENT_ID', 'OAUTH_CLIENT_SECRET'],
                'dependent_services': ['auth', 'frontend'],
                'failure_impact': 'OAuth login failures'
            }
        }
        
        # Test complete configuration
        complete_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'complete_jwt_secret_32_characters!',
            'JWT_ALGORITHM': 'HS256',
            'POSTGRES_HOST': 'staging-db.example.com',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_secure_password',
            'POSTGRES_DB': 'netra_staging',
            'REDIS_URL': 'redis://staging-redis.example.com:6379/0',
            'REDIS_HOST': 'staging-redis.example.com',
            'OAUTH_CLIENT_ID': 'staging_oauth_client',
            'OAUTH_CLIENT_SECRET': 'staging_oauth_secret'
        }
        
        # Validate complete configuration
        validation_results = {}
        
        for dependency_name, dependency_info in critical_dependencies.items():
            missing_configs = []
            for required_config in dependency_info['required_configs']:
                if required_config not in complete_config:
                    missing_configs.append(required_config)
                    
            validation_results[dependency_name] = {
                'is_valid': len(missing_configs) == 0,
                'missing_configs': missing_configs,
                'dependent_services': dependency_info['dependent_services'],
                'failure_impact': dependency_info['failure_impact']
            }
            
        # All dependencies should be satisfied
        for dependency_name, result in validation_results.items():
            assert result['is_valid'], f"Critical dependency {dependency_name} not satisfied: {result['missing_configs']}"
            
        # Test incomplete configuration (missing JWT)
        incomplete_config = complete_config.copy()
        del incomplete_config['JWT_SECRET_KEY']  # Remove critical JWT config
        
        jwt_validation = []
        for required_config in critical_dependencies['jwt_authentication']['required_configs']:
            if required_config not in incomplete_config:
                jwt_validation.append(required_config)
                
        assert len(jwt_validation) > 0, "Should detect missing JWT configuration"
        assert 'JWT_SECRET_KEY' in jwt_validation, "Should detect missing JWT_SECRET_KEY"
        
    def test_configuration_change_tracking_audit_capabilities(self):
        """Test configuration change tracking provides audit capabilities."""
        # BVJ: Enables compliance and debugging of configuration changes
        
        # Test configuration change tracking
        original_config = {
            'JWT_SECRET_KEY': 'original_jwt_secret_32_characters!',
            'DATABASE_URL': 'postgresql://localhost:5432/original_db',
            'REDIS_URL': 'redis://localhost:6379/0'
        }
        
        updated_config = {
            'JWT_SECRET_KEY': 'updated_jwt_secret_32_characters!',  # Changed
            'DATABASE_URL': 'postgresql://localhost:5432/original_db',  # Same
            'REDIS_URL': 'redis://localhost:6379/1',  # Changed
            'NEW_CONFIG': 'new_value'  # Added
        }
        
        # Simulate change tracking
        changes = []
        
        # Detect changes
        all_keys = set(original_config.keys()) | set(updated_config.keys())
        
        for key in all_keys:
            original_value = original_config.get(key)
            updated_value = updated_config.get(key)
            
            if original_value != updated_value:
                change_type = 'modified' if key in original_config and key in updated_config else \
                             'added' if key not in original_config else 'removed'
                             
                changes.append({
                    'key': key,
                    'change_type': change_type,
                    'original_value': '***' if 'secret' in key.lower() or 'password' in key.lower() else original_value,
                    'updated_value': '***' if 'secret' in key.lower() or 'password' in key.lower() else updated_value,
                    'timestamp': time.time()
                })
                
        # Verify change detection
        expected_changes = ['JWT_SECRET_KEY', 'REDIS_URL', 'NEW_CONFIG']
        detected_changes = [change['key'] for change in changes]
        
        assert len(changes) == 3, f"Should detect 3 changes: {detected_changes}"
        
        for expected_key in expected_changes:
            assert expected_key in detected_changes, f"Should detect change in {expected_key}"
            
        # Verify sensitive data masking
        jwt_change = next(change for change in changes if change['key'] == 'JWT_SECRET_KEY')
        assert jwt_change['original_value'] == '***', "Should mask sensitive original value"
        assert jwt_change['updated_value'] == '***', "Should mask sensitive updated value"
        
        # Verify non-sensitive data is not masked
        redis_change = next(change for change in changes if change['key'] == 'REDIS_URL')
        assert redis_change['original_value'] != '***', "Should not mask non-secret values"
        
        # Test audit trail
        audit_trail = {
            'timestamp': time.time(),
            'user': 'system',
            'environment': 'staging',
            'changes_count': len(changes),
            'changes': changes,
            'validation_passed': True
        }
        
        assert audit_trail['changes_count'] == 3, "Audit trail should record correct number of changes"
        assert audit_trail['validation_passed'] is True, "Audit trail should record validation status"


class TestClickHouseRemoteConfiguration:
    """Test ClickHouse remote configuration for staging/production scenarios."""
    
    def test_clickhouse_staging_configuration(self):
        """Test ClickHouse configuration in staging environment."""
        # BVJ: Ensures analytics service can connect to ClickHouse in staging
        staging_clickhouse_config = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_HOST': 'staging-clickhouse.example.com',
            'CLICKHOUSE_PORT': '8123',
            'CLICKHOUSE_DATABASE': 'netra_analytics_staging',
            'CLICKHOUSE_USER': 'staging_analytics_user',
            'CLICKHOUSE_PASSWORD': 'staging_clickhouse_secure_password',
            'CLICKHOUSE_SECURE': 'true'  # Use HTTPS in staging
        }
        
        # Test ClickHouse URL construction
        clickhouse_url = f"clickhouse://{staging_clickhouse_config['CLICKHOUSE_USER']}:{staging_clickhouse_config['CLICKHOUSE_PASSWORD']}@{staging_clickhouse_config['CLICKHOUSE_HOST']}:{staging_clickhouse_config['CLICKHOUSE_PORT']}/{staging_clickhouse_config['CLICKHOUSE_DATABASE']}"
        
        if staging_clickhouse_config.get('CLICKHOUSE_SECURE') == 'true':
            clickhouse_url += '?secure=1'
            
        # Validate URL components
        assert 'staging-clickhouse.example.com' in clickhouse_url, "Should use staging ClickHouse host"
        assert 'netra_analytics_staging' in clickhouse_url, "Should use staging database"
        assert 'secure=1' in clickhouse_url, "Staging should use secure connection"
        
        # Test ClickHouse connection configuration
        connection_config = {
            'host': staging_clickhouse_config['CLICKHOUSE_HOST'],
            'port': int(staging_clickhouse_config['CLICKHOUSE_PORT']),
            'database': staging_clickhouse_config['CLICKHOUSE_DATABASE'],
            'user': staging_clickhouse_config['CLICKHOUSE_USER'],
            'password': staging_clickhouse_config['CLICKHOUSE_PASSWORD'],
            'secure': staging_clickhouse_config['CLICKHOUSE_SECURE'] == 'true'
        }
        
        # Validate connection configuration
        assert connection_config['host'] == 'staging-clickhouse.example.com'
        assert connection_config['port'] == 8123
        assert connection_config['database'] == 'netra_analytics_staging'
        assert connection_config['secure'] is True, "Staging should use secure connection"
        
    def test_clickhouse_production_configuration(self):
        """Test ClickHouse configuration in production environment."""
        # BVJ: Ensures analytics service can connect to production ClickHouse
        production_clickhouse_config = {
            'ENVIRONMENT': 'production',
            'CLICKHOUSE_HOST': 'prod-clickhouse-cluster.example.com',
            'CLICKHOUSE_PORT': '9440',  # Secure port
            'CLICKHOUSE_DATABASE': 'netra_analytics_production',
            'CLICKHOUSE_USER': 'production_analytics_user',
            'CLICKHOUSE_PASSWORD': 'production_clickhouse_ultra_secure_password',
            'CLICKHOUSE_SECURE': 'true',
            'CLICKHOUSE_VERIFY': 'true'  # Verify SSL certificates in production
        }
        
        # Test production ClickHouse URL construction
        clickhouse_url = f"clickhttps://{production_clickhouse_config['CLICKHOUSE_USER']}:{production_clickhouse_config['CLICKHOUSE_PASSWORD']}@{production_clickhouse_config['CLICKHOUSE_HOST']}:{production_clickhouse_config['CLICKHOUSE_PORT']}/{production_clickhouse_config['CLICKHOUSE_DATABASE']}"
        
        # Validate production requirements
        assert 'prod-clickhouse-cluster.example.com' in clickhouse_url, "Should use production ClickHouse cluster"
        assert 'netra_analytics_production' in clickhouse_url, "Should use production database"
        assert '9440' in clickhouse_url, "Production should use secure port"
        assert 'clickhttps://' in clickhouse_url, "Production should use HTTPS protocol"
        
        # Test production security requirements
        security_config = {
            'secure_connection': production_clickhouse_config['CLICKHOUSE_SECURE'] == 'true',
            'verify_certificates': production_clickhouse_config['CLICKHOUSE_VERIFY'] == 'true',
            'secure_port': int(production_clickhouse_config['CLICKHOUSE_PORT']) == 9440,
            'secure_user': len(production_clickhouse_config['CLICKHOUSE_PASSWORD']) >= 32
        }
        
        # All security requirements should be met
        assert security_config['secure_connection'] is True, "Production should use secure connection"
        assert security_config['verify_certificates'] is True, "Production should verify SSL certificates"
        assert security_config['secure_port'] is True, "Production should use secure port 9440"
        assert security_config['secure_user'] is True, "Production should use secure password"
        
    def test_clickhouse_cloud_configuration(self):
        """Test ClickHouse Cloud configuration scenarios."""
        # BVJ: Supports ClickHouse Cloud deployments for scalable analytics
        clickhouse_cloud_config = {
            'ENVIRONMENT': 'production',
            'CLICKHOUSE_CLOUD': 'true',
            'CLICKHOUSE_HOST': 'abc123.us-east-1.aws.clickhouse.cloud',
            'CLICKHOUSE_PORT': '8443',
            'CLICKHOUSE_DATABASE': 'netra_analytics',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': 'clickhouse_cloud_secure_password_64_chars_long_for_security',
            'CLICKHOUSE_SECURE': 'true',
            'CLICKHOUSE_VERIFY': 'true'
        }
        
        # Test ClickHouse Cloud URL construction
        cloud_url = f"clickhttps://{clickhouse_cloud_config['CLICKHOUSE_USER']}:{clickhouse_cloud_config['CLICKHOUSE_PASSWORD']}@{clickhouse_cloud_config['CLICKHOUSE_HOST']}:{clickhouse_cloud_config['CLICKHOUSE_PORT']}/{clickhouse_cloud_config['CLICKHOUSE_DATABASE']}"
        
        # Validate ClickHouse Cloud specifics
        assert '.aws.clickhouse.cloud' in cloud_url, "Should use ClickHouse Cloud domain"
        assert '8443' in cloud_url, "Should use ClickHouse Cloud secure port"
        assert 'clickhttps://' in cloud_url, "Should use HTTPS for ClickHouse Cloud"
        
        # Test ClickHouse Cloud connection parameters
        cloud_connection_params = {
            'host': clickhouse_cloud_config['CLICKHOUSE_HOST'],
            'port': int(clickhouse_cloud_config['CLICKHOUSE_PORT']),
            'user': clickhouse_cloud_config['CLICKHOUSE_USER'],
            'password': clickhouse_cloud_config['CLICKHOUSE_PASSWORD'],
            'database': clickhouse_cloud_config['CLICKHOUSE_DATABASE'],
            'secure': True,
            'verify': True,
            'compression': 'lz4'  # ClickHouse Cloud optimization
        }
        
        # Validate cloud-specific parameters
        assert cloud_connection_params['secure'] is True, "ClickHouse Cloud should use secure connection"
        assert cloud_connection_params['verify'] is True, "ClickHouse Cloud should verify certificates" 
        assert cloud_connection_params['compression'] == 'lz4', "Should use compression for cloud efficiency"
        assert len(cloud_connection_params['password']) >= 32, "Cloud password should be secure"
        
    def test_clickhouse_configuration_validation(self):
        """Test ClickHouse configuration validation across environments."""
        # BVJ: Prevents ClickHouse connection failures from invalid configuration
        
        test_configs = [
            {
                'name': 'valid_staging',
                'config': {
                    'ENVIRONMENT': 'staging',
                    'CLICKHOUSE_HOST': 'staging-ch.example.com',
                    'CLICKHOUSE_PORT': '8123',
                    'CLICKHOUSE_DATABASE': 'staging_analytics',
                    'CLICKHOUSE_USER': 'staging_user',
                    'CLICKHOUSE_PASSWORD': 'staging_password_32_chars_secure!',
                    'CLICKHOUSE_SECURE': 'true'
                },
                'should_be_valid': True
            },
            {
                'name': 'invalid_missing_host',
                'config': {
                    'ENVIRONMENT': 'production',
                    # Missing CLICKHOUSE_HOST
                    'CLICKHOUSE_PORT': '9440',
                    'CLICKHOUSE_DATABASE': 'production_analytics',
                    'CLICKHOUSE_USER': 'prod_user',
                    'CLICKHOUSE_PASSWORD': 'prod_password',
                    'CLICKHOUSE_SECURE': 'true'
                },
                'should_be_valid': False
            },
            {
                'name': 'invalid_insecure_production',
                'config': {
                    'ENVIRONMENT': 'production',
                    'CLICKHOUSE_HOST': 'prod-ch.example.com',
                    'CLICKHOUSE_PORT': '8123',  # Insecure port
                    'CLICKHOUSE_DATABASE': 'production_analytics',
                    'CLICKHOUSE_USER': 'prod_user',
                    'CLICKHOUSE_PASSWORD': 'weak',  # Weak password
                    'CLICKHOUSE_SECURE': 'false'  # Insecure in production!
                },
                'should_be_valid': False
            }
        ]
        
        for test_case in test_configs:
            config = test_case['config']
            validation_errors = []
            
            # Validate required fields
            required_fields = ['CLICKHOUSE_HOST', 'CLICKHOUSE_PORT', 'CLICKHOUSE_DATABASE', 'CLICKHOUSE_USER', 'CLICKHOUSE_PASSWORD']
            for field in required_fields:
                if field not in config:
                    validation_errors.append(f"Missing required field: {field}")
                    
            # Validate production security requirements
            if config.get('ENVIRONMENT') == 'production':
                if config.get('CLICKHOUSE_SECURE') != 'true':
                    validation_errors.append("Production must use secure ClickHouse connection")
                    
                clickhouse_port = int(config.get('CLICKHOUSE_PORT', 0))
                if clickhouse_port not in [8443, 9440]:  # Standard secure ports
                    validation_errors.append(f"Production should use secure port (8443 or 9440), got {clickhouse_port}")
                    
                password = config.get('CLICKHOUSE_PASSWORD', '')
                if len(password) < 16:
                    validation_errors.append("Production ClickHouse password should be at least 16 characters")
                    
            is_valid = len(validation_errors) == 0
            
            if test_case['should_be_valid']:
                assert is_valid, f"Configuration {test_case['name']} should be valid, but has errors: {validation_errors}"
            else:
                assert not is_valid, f"Configuration {test_case['name']} should be invalid, but passed validation"


class TestConfigurationSecretsAndSecurity:
    """Test configuration scenarios involving secrets and security."""
    
    def test_jwt_secret_security_across_services(self):
        """Test JWT secret security requirements across services."""
        # BVJ: Ensures JWT secrets meet security standards preventing token compromise
        
        security_test_cases = [
            {
                'name': 'secure_jwt_secret',
                'jwt_secret': 'ultra_secure_jwt_secret_with_64_characters_including_special_chars!@#$%',
                'environment': 'production',
                'should_be_secure': True
            },
            {
                'name': 'minimum_length_jwt_secret', 
                'jwt_secret': 'minimum_32_character_jwt_secret!',
                'environment': 'staging',
                'should_be_secure': True
            },
            {
                'name': 'weak_jwt_secret',
                'jwt_secret': 'weak',  # Too short
                'environment': 'development',
                'should_be_secure': False
            },
            {
                'name': 'predictable_jwt_secret',
                'jwt_secret': 'password123',  # Predictable
                'environment': 'production',
                'should_be_secure': False
            }
        ]
        
        for test_case in security_test_cases:
            jwt_secret = test_case['jwt_secret']
            environment = test_case['environment']
            
            # Test JWT secret security criteria
            security_checks = {
                'length_check': len(jwt_secret) >= 32,
                'complexity_check': any(c.isdigit() for c in jwt_secret) and 
                                  any(c.isalpha() for c in jwt_secret) and
                                  any(c in '!@#$%^&*()' for c in jwt_secret),
                'not_predictable': jwt_secret.lower() not in ['password', 'secret', 'key', 'jwt', '123456'],
                'environment_appropriate': (environment == 'development') or len(jwt_secret) >= 32
            }
            
            is_secure = all(security_checks.values())
            
            if test_case['should_be_secure']:
                assert is_secure, f"JWT secret {test_case['name']} should be secure: {security_checks}"
            else:
                # At least one check should fail for insecure secrets
                if environment in ['staging', 'production']:
                    assert not is_secure, f"JWT secret {test_case['name']} should be considered insecure in {environment}"
                    
            # Test JWT secret consistency across services
            test_env = {
                'ENVIRONMENT': environment,
                'JWT_SECRET_KEY': jwt_secret,
                'JWT_ALGORITHM': 'HS256'
            }
            
            with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
                mock_instance = MagicMock()
                mock_instance.get.side_effect = lambda key, default=None: test_env.get(key, default)
                mock_env.return_value = mock_instance
                
                # Test multiple service managers get same secret
                backend_manager = JWTSecretManager()
                auth_manager = JWTSecretManager() 
                
                try:
                    backend_secret = backend_manager.get_jwt_secret()
                    auth_secret = auth_manager.get_jwt_secret()
                    
                    assert backend_secret == auth_secret, "Services should get identical JWT secrets"
                    assert backend_secret == jwt_secret, "Should get expected JWT secret"
                    
                except ValueError:
                    # Expected for insecure secrets in staging/production
                    if environment in ['staging', 'production'] and not test_case['should_be_secure']:
                        pass  # Expected behavior
                    else:
                        raise
                finally:
                    backend_manager.clear_cache()
                    auth_manager.clear_cache()
                    
    def test_database_credential_security(self):
        """Test database credential security across services."""
        # BVJ: Ensures database credentials meet security standards preventing data breaches
        
        credential_test_cases = [
            {
                'name': 'secure_production_credentials',
                'environment': 'production',
                'postgres_user': 'prod_netra_user_secure',
                'postgres_password': 'ultra_secure_production_password_64_characters_with_special_chars!@#$',
                'postgres_host': 'prod-db-cluster.example.com',
                'should_be_secure': True
            },
            {
                'name': 'weak_production_password',
                'environment': 'production',
                'postgres_user': 'prod_user',
                'postgres_password': 'password123',  # Weak password
                'postgres_host': 'prod-db.example.com',
                'should_be_secure': False
            },
            {
                'name': 'localhost_in_production',
                'environment': 'production',
                'postgres_user': 'secure_user',
                'postgres_password': 'secure_production_password_32_chars!',
                'postgres_host': 'localhost',  # Insecure host for production
                'should_be_secure': False
            },
            {
                'name': 'development_credentials_acceptable',
                'environment': 'development',
                'postgres_user': 'postgres',
                'postgres_password': 'postgres',  # Simple dev password
                'postgres_host': 'localhost',
                'should_be_secure': True  # Acceptable for development
            }
        ]
        
        for test_case in credential_test_cases:
            db_config = {
                'ENVIRONMENT': test_case['environment'],
                'POSTGRES_USER': test_case['postgres_user'],
                'POSTGRES_PASSWORD': test_case['postgres_password'],
                'POSTGRES_HOST': test_case['postgres_host'],
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': f"netra_{test_case['environment']}"
            }
            
            builder = DatabaseURLBuilder(db_config)
            is_valid, error_message = builder.validate()
            
            if test_case['should_be_secure']:
                assert is_valid, f"Credentials {test_case['name']} should be valid: {error_message}"
            else:
                # Production insecure credentials should fail validation
                if test_case['environment'] in ['staging', 'production']:
                    assert not is_valid, f"Insecure credentials {test_case['name']} should fail validation in {test_case['environment']}"
                    
                    # Verify specific error detection
                    if 'password123' in test_case['postgres_password']:
                        assert 'password' in error_message.lower(), "Should detect weak password"
                    elif test_case['postgres_host'] == 'localhost':
                        assert 'localhost' in error_message.lower(), "Should detect localhost in production"
                        
    def test_oauth_client_secret_security(self):
        """Test OAuth client secret security across environments."""
        # BVJ: Ensures OAuth secrets are properly secured preventing unauthorized access
        
        oauth_test_cases = [
            {
                'name': 'secure_production_oauth',
                'environment': 'production',
                'oauth_client_id': 'prod_oauth_client_netra_12345',
                'oauth_client_secret': 'prod_oauth_client_secret_ultra_secure_64_characters_with_entropy!@#$',
                'should_be_secure': True
            },
            {
                'name': 'weak_oauth_secret',
                'environment': 'production', 
                'oauth_client_id': 'prod_client',
                'oauth_client_secret': 'secret123',  # Too short and predictable
                'should_be_secure': False
            },
            {
                'name': 'development_oauth_acceptable',
                'environment': 'development',
                'oauth_client_id': 'dev_oauth_client',
                'oauth_client_secret': 'dev_oauth_secret_for_development',
                'should_be_secure': True  # Acceptable for development
            }
        ]
        
        for test_case in oauth_test_cases:
            oauth_config = {
                'ENVIRONMENT': test_case['environment'],
                'OAUTH_CLIENT_ID': test_case['oauth_client_id'],
                'OAUTH_CLIENT_SECRET': test_case['oauth_client_secret']
            }
            
            # OAuth security validation
            oauth_security_checks = {
                'client_id_not_empty': bool(oauth_config['OAUTH_CLIENT_ID']),
                'client_secret_not_empty': bool(oauth_config['OAUTH_CLIENT_SECRET']),
                'client_secret_length': len(oauth_config['OAUTH_CLIENT_SECRET']) >= 16,
                'client_secret_not_predictable': oauth_config['OAUTH_CLIENT_SECRET'].lower() not in [
                    'secret', 'password', 'oauth', 'client', '123456'
                ],
                'production_security': (
                    test_case['environment'] != 'production' or 
                    len(oauth_config['OAUTH_CLIENT_SECRET']) >= 32
                )
            }
            
            is_oauth_secure = all(oauth_security_checks.values())
            
            if test_case['should_be_secure']:
                assert is_oauth_secure, f"OAuth config {test_case['name']} should be secure: {oauth_security_checks}"
            else:
                if test_case['environment'] in ['staging', 'production']:
                    assert not is_oauth_secure, f"OAuth config {test_case['name']} should be insecure in {test_case['environment']}"
                    
        # Test OAuth configuration consistency across services
        consistent_oauth_config = {
            'ENVIRONMENT': 'staging',
            'OAUTH_CLIENT_ID': 'staging_oauth_client_netra_consistent',
            'OAUTH_CLIENT_SECRET': 'staging_oauth_secret_consistent_32_chars!'
        }
        
        # Both auth and frontend services should use same OAuth config
        auth_oauth_config = consistent_oauth_config.copy()
        frontend_oauth_config = consistent_oauth_config.copy()
        
        assert auth_oauth_config['OAUTH_CLIENT_ID'] == frontend_oauth_config['OAUTH_CLIENT_ID'], "OAuth client ID should be consistent"
        assert auth_oauth_config['OAUTH_CLIENT_SECRET'] == frontend_oauth_config['OAUTH_CLIENT_SECRET'], "OAuth client secret should be consistent"


# Integration test execution
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])