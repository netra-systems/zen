from shared.isolated_environment import get_env
"""
env = get_env()
Integration tests for SecretManagerBuilder.

Tests the unified secret management system across different environments
with REAL SERVICES - no mocks allowed per CLAUDE.md standards.

CRITICAL SECURITY TEST:
This test validates end-to-end secret management functionality including:
- Secure secret storage and retrieval
- JWT secret synchronization across services (SSOT principle)
- Real database and Redis connections
- Encryption/decryption of sensitive data
- Environment isolation and validation
- Cross-service secret consistency
"""

import pytest
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ABSOLUTE IMPORTS ONLY per CLAUDE.md
from shared.isolated_environment import IsolatedEnvironment
from shared.secret_manager_builder import (
    SecretManagerBuilder,
    SecretInfo,
    SecretValidationResult,
    get_secret_manager,
    load_secrets_for_service,
    get_jwt_secret
)

# Optional imports for real service testing
try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

try:
    import redis
    _REDIS_AVAILABLE = True  
except ImportError:
    _REDIS_AVAILABLE = False

try:
    from test_framework.real_services import ServiceConfig
    _SERVICE_CONFIG_AVAILABLE = True
except ImportError:
    _SERVICE_CONFIG_AVAILABLE = False


class TestSecretManagerBuilderIntegration:
    """Integration tests for SecretManagerBuilder with REAL services."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        assert builder._environment == 'development'
        assert builder.development.should_allow_fallback() is True
    
    def test_staging_environment_detection(self):
        """Test that staging environment is properly detected."""
        
        builder = SecretManagerBuilder(env_vars=staging_env)
        assert builder._environment == 'staging'
        assert builder.development.should_allow_fallback() is False
    
    def test_production_environment_detection(self):
        """Test that production environment is properly detected."""
        
        builder = SecretManagerBuilder(env_vars=prod_env)
        assert builder._environment == 'production'
        assert builder.development.should_allow_fallback() is False
    
        secrets = builder.load_all_secrets()
        
        # Check critical secrets are loaded
        assert 'JWT_SECRET_KEY' in secrets
        assert secrets['JWT_SECRET_KEY'] == 'test-jwt-secret-key-32-chars-minimum-length-required'
        assert 'POSTGRES_PASSWORD' in secrets
        assert 'REDIS_PASSWORD' in secrets
        assert 'FERNET_KEY' in secrets
        assert 'ANTHROPIC_API_KEY' in secrets
        
        # Validate secrets meet security requirements
        assert len(secrets['JWT_SECRET_KEY']) >= 32
        assert 'test-jwt-secret-key' in secrets['JWT_SECRET_KEY']
        assert secrets['FERNET_KEY'].endswith('=')
    
    def test_get_individual_secret_with_real_caching(self):
        """Test getting individual secrets with real caching performance."""
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        
        # Get secret (should cache it)
        jwt_secret = builder.get_secret('JWT_SECRET_KEY')
        assert jwt_secret == 'test-jwt-secret-key-32-chars-minimum-length-required'
        
        # Get from cache (should be faster)
        start_time = time.time()
        cached_secret = builder.get_secret('JWT_SECRET_KEY', use_cache=True)
        cache_time = time.time() - start_time
        
        assert cached_secret == jwt_secret
        assert cache_time < 0.01  # Should be very fast from cache (< 10ms)
        
        # Test cache invalidation
        builder.cache.invalidate_cache('JWT_SECRET_KEY')
        
        # Should fetch again (slower)
        start_time = time.time()
        fresh_secret = builder.get_secret('JWT_SECRET_KEY', use_cache=False)
        fresh_time = time.time() - start_time
        
        assert fresh_secret == jwt_secret
        assert fresh_time > cache_time  # Should be slower than cache
    
    def test_secret_validation_development_with_real_secrets(self):
        """Test secret validation in development with real secrets."""
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        validation_result = builder.validate_configuration()
        
        # Should be valid in development even with test values
        assert validation_result.is_valid is True
        assert validation_result.placeholder_count == 0
        
        # Check that critical secrets pass validation
        secrets = builder.load_all_secrets()
        critical_validation = builder.validation.validate_critical_secrets(secrets)
        
        assert critical_validation.is_valid is True
        assert len(critical_validation.critical_failures) == 0
    
    def test_secret_validation_production_strict(self):
        """Test strict validation for production environment."""
        
        builder = SecretManagerBuilder(env_vars=prod_env)
        secrets = {'JWT_SECRET_KEY': 'placeholder'}
        
        validation_result = builder.validation.validate_critical_secrets(secrets)
        
        assert validation_result.is_valid is False
        assert validation_result.placeholder_count > 0
        assert 'JWT_SECRET_KEY' in validation_result.critical_failures
    
        
        # Cache a secret with short TTL
        builder.cache.cache_secret('TEST_SECRET', 'test_value', ttl_minutes=0.01)  # 0.6 seconds
        
        # Should be available immediately
        assert builder.cache.get_cached_secret('TEST_SECRET') == 'test_value'
        
        # Test thread safety of cache
        results = []
        
        def cache_reader():
            """Read from cache in thread."""
            results.append(builder.cache.get_cached_secret('TEST_SECRET'))
        
        # Multiple threads should get the same cached value
        threads = [threading.Thread(target=cache_reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert all(result == 'test_value' for result in results)
        
        # Wait for expiration
        time.sleep(1)
        
        # Should be expired
        assert builder.cache.get_cached_secret('TEST_SECRET') is None
        
        # Test invalidation
        builder.cache.cache_secret('TEST_SECRET_2', 'test_value_2', ttl_minutes=60)
        assert builder.cache.get_cached_secret('TEST_SECRET_2') == 'test_value_2'
        
        builder.cache.invalidate_cache('TEST_SECRET_2')
        assert builder.cache.get_cached_secret('TEST_SECRET_2') is None
    
        jwt_secret = builder.auth.get_jwt_secret()
        
        assert jwt_secret == 'test-jwt-secret-key-32-chars-minimum-length-required'
        assert len(jwt_secret) >= 32  # Minimum security requirement
        
        # Test SSOT: Multiple services should get the SAME JWT secret
        auth_builder = SecretManagerBuilder(env_vars=self.env.get_all(), service='auth_service')
        backend_builder = SecretManagerBuilder(env_vars=self.env.get_all(), service='netra_backend')
        
        auth_jwt = auth_builder.auth.get_jwt_secret()
        backend_jwt = backend_builder.auth.get_jwt_secret()
        
        # CRITICAL: JWT secrets MUST be identical across services (SSOT)
        assert auth_jwt == backend_jwt == jwt_secret
        
        # Test secret is cached consistently
        cached_auth_jwt = auth_builder.cache.get_cached_secret('JWT_SECRET_KEY')
        cached_backend_jwt = backend_builder.cache.get_cached_secret('JWT_SECRET_KEY')
        
        assert cached_auth_jwt == cached_backend_jwt == jwt_secret
    
        
        # Test encryption and decryption with sensitive data
        sensitive_secrets = [
            'my-secret-database-password-123',
            'jwt-signing-key-very-secret',
            'api-key-sk-1234567890abcdef',
            'redis-auth-token-sensitive'
        ]
        
        for original_value in sensitive_secrets:
            encrypted = builder.encryption.encrypt_secret(original_value)
            
            # Verify encryption worked
            assert encrypted != original_value  # Should be encrypted
            assert len(encrypted) > len(original_value)  # Encrypted is longer
            assert 'gAAAAA' in encrypted  # Fernet token prefix
            
            # Verify decryption works
            decrypted = builder.encryption.decrypt_secret(encrypted)
            assert decrypted == original_value  # Should decrypt correctly
        
        # Test with real database password
        db_password = self.env.get('POSTGRES_PASSWORD')
        if db_password:
            encrypted_db_pass = builder.encryption.encrypt_secret(db_password)
            decrypted_db_pass = builder.encryption.decrypt_secret(encrypted_db_pass)
            assert decrypted_db_pass == db_password
    
        
        # Test with fallback enabled
        fallback_env['ALLOW_DEVELOPMENT_FALLBACKS'] = 'true'
        builder = SecretManagerBuilder(env_vars=fallback_env)
        
        # Should still fail because we don't allow JWT fallbacks for security
        with pytest.raises(ValueError):
            builder.auth.get_jwt_secret()
    
        
        builder = SecretManagerBuilder(env_vars=staging_env)
        
        # Should use DisabledGCPBuilder
        assert isinstance(builder.gcp, SecretManagerBuilder.DisabledGCPBuilder)
        
        # Should return None for all secret requests
        assert builder.gcp.get_secret('jwt-secret-key') is None
        assert builder.gcp.get_database_password() is None
        assert builder.gcp.get_redis_password() is None
        assert builder.gcp.get_jwt_secret() is None
        
        # Connectivity should be false
        is_valid, error = builder.gcp.validate_gcp_connectivity()
        assert is_valid is False
        assert 'disabled' in error.lower()
        
        # Should return empty secrets list
        assert builder.gcp.list_available_secrets() == []
    
        # Test for netra_backend
        backend_builder = SecretManagerBuilder(env_vars=self.env.get_all(), service='netra_backend')
        assert backend_builder.service == 'netra_backend'
        
        backend_secrets = backend_builder.load_all_secrets()
        assert 'JWT_SECRET_KEY' in backend_secrets
        
        # Test for auth_service  
        auth_builder = SecretManagerBuilder(env_vars=self.env.get_all(), service='auth_service')
        assert auth_builder.service == 'auth_service'
        
        auth_secrets = auth_builder.load_all_secrets()
        assert 'JWT_SECRET_KEY' in auth_secrets
        
        # CRITICAL: Test cross-service JWT secret consistency (SSOT)
        backend_jwt = backend_secrets['JWT_SECRET_KEY']
        auth_jwt = auth_secrets['JWT_SECRET_KEY']
        
        assert backend_jwt == auth_jwt, "JWT secrets MUST be identical across services"
        
        # Test that both services can authenticate with same JWT
        assert len(backend_jwt) >= 32
        assert len(auth_jwt) >= 32
        
        # Test service isolation for non-shared secrets
        backend_debug = backend_builder.get_debug_info()
        auth_debug = auth_builder.get_debug_info()
        
        assert backend_debug['service'] == 'netra_backend'
        assert auth_debug['service'] == 'auth_service'
        assert backend_debug['environment'] == auth_debug['environment']
    
    def test_backward_compatibility_functions_real_integration(self):
        """Test backward compatibility wrapper functions with real integration."""
        # Test get_secret_manager
        manager = get_secret_manager('shared')
        assert isinstance(manager, SecretManagerBuilder)
        
        # Test load_secrets_for_service
        secrets = load_secrets_for_service('shared')
        assert isinstance(secrets, dict)
        assert len(secrets) > 0
        assert 'JWT_SECRET_KEY' in secrets
        
        # Test get_jwt_secret with environment isolation
        # Save current environment
        original_env = self.env.get_all()
        
        try:
            # This should use the global os.environ, but in test it will use test values
            jwt = get_jwt_secret('auth_service')
            assert jwt is not None
            assert len(jwt) >= 32
        finally:
            # Environment should remain isolated
            current_env = self.env.get_all()
            assert current_env == original_env
    
        debug_info = builder.get_debug_info()
        
        # Basic info
        assert 'environment' in debug_info
        assert debug_info['environment'] == 'development'
        assert 'service' in debug_info
        
        # GCP connectivity
        assert 'gcp_connectivity' in debug_info
        assert debug_info['gcp_connectivity']['is_valid'] is False  # Disabled in test
        assert 'disabled' in debug_info['gcp_connectivity']['error'].lower()
        
        # Validation
        assert 'validation' in debug_info
        assert debug_info['validation']['is_valid'] is True  # Should be valid in dev
        assert debug_info['validation']['error_count'] == 0
        assert debug_info['validation']['placeholder_count'] == 0
        
        # Cache stats
        assert 'cache_stats' in debug_info
        assert debug_info['cache_stats']['cache_enabled'] is True
        assert 'cached_secrets' in debug_info['cache_stats']
        
        # Features
        assert 'features' in debug_info
        assert debug_info['features']['gcp_enabled'] is False  # Development env
        assert debug_info['features']['fallbacks_allowed'] is True  # Development
        
        # Test after loading secrets (cache should have entries)
        builder.load_all_secrets()
        updated_debug = builder.get_debug_info()
        assert updated_debug['cache_stats']['cached_secrets'] > 0
    
        
        staging_builder = SecretManagerBuilder(env_vars=staging_env)
        staging_jwt = staging_builder.auth.get_jwt_secret()
        
        # Both should have valid JWT secrets
        assert len(dev_jwt) >= 32
        assert len(staging_jwt) >= 32
        
        # In this test setup, they should be the same (from same test env)
        assert dev_jwt == staging_jwt
        
        # Test environment detection works correctly
        assert dev_builder._environment == 'development'
        assert staging_builder._environment == 'staging'
        
        # Test feature differences
        assert dev_builder.development.should_allow_fallback() is True
        assert staging_builder.development.should_allow_fallback() is False
    
    def test_secret_info_dataclass_with_real_timestamps(self):
        """Test SecretInfo dataclass functionality with real timestamps."""
        current_time = datetime.now(timezone.utc)
        
        secret_info = SecretInfo(
            name='TEST_SECRET',
            value='test_value_sensitive_data',
            source='environment',
            environment='development',
            cached_at=current_time,
            ttl_minutes=60,
            encrypted=False,
            audit_logged=True
        )
        
        assert secret_info.name == 'TEST_SECRET'
        assert secret_info.value == 'test_value_sensitive_data'
        assert secret_info.source == 'environment'
        assert secret_info.environment == 'development'
        assert secret_info.ttl_minutes == 60
        assert secret_info.encrypted is False
        assert secret_info.audit_logged is True
        
        # Test timestamp accuracy
        time_diff = abs((secret_info.cached_at - current_time).total_seconds())
        assert time_diff < 1  # Should be within 1 second
        
        # Test with real builder cache
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        builder.cache.cache_secret_info(secret_info)
        
        # Should be retrievable from cache
        cached_value = builder.cache.get_cached_secret('TEST_SECRET')
        assert cached_value == 'test_value_sensitive_data'
    
        
        for _ in range(5):
            start_time = time.time()
            builder = SecretManagerBuilder(env_vars=self.env.get_all())
            secrets = builder.load_all_secrets()
            load_time_ms = (time.time() - start_time) * 1000
            load_times.append(load_time_ms)
        
        avg_load_time = sum(load_times) / len(load_times)
        max_load_time = max(load_times)
        
        # Should load in under 200ms for development (higher limit due to real services)
        assert avg_load_time < 200, f"Average load time {avg_load_time}ms exceeds 200ms target"
        assert max_load_time < 500, f"Max load time {max_load_time}ms exceeds 500ms limit"
        assert len(secrets) > 0
        
        # Test caching improves performance
        start_time = time.time()
        cached_secrets = builder.load_all_secrets()  # Should use cache
        cached_time_ms = (time.time() - start_time) * 1000
        
        # Cached load should be faster
        assert cached_time_ms < avg_load_time
        assert cached_secrets == secrets
    
    def test_real_database_connection_with_secrets(self):
        """Test that secrets enable real database connections."""
        if not _PSYCOPG2_AVAILABLE:
            pytest.skip("psycopg2 not available for testing")
        if not getattr(self, '_postgres_available', False):
            pytest.skip("PostgreSQL not available for testing")
            
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        secrets = builder.load_all_secrets()
        
        # Extract database connection info
        db_host = secrets.get('POSTGRES_HOST', 'localhost')
        db_port = int(secrets.get('POSTGRES_PORT', self.real_services.postgres_port))
        db_user = secrets.get('POSTGRES_USER', 'test')
        db_password = secrets.get('POSTGRES_PASSWORD', 'test')
        db_name = secrets.get('POSTGRES_DB', 'netra_test')
        
        # Test actual database connection with retrieved secrets
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            connect_timeout=10
        )
        
        # Execute a test query to verify connection works
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        assert version is not None
        assert 'PostgreSQL' in version[0]
        
        cursor.close()
        conn.close()
    
    def test_real_redis_connection_with_secrets(self):
        """Test that secrets enable real Redis connections."""
        if not _REDIS_AVAILABLE:
            pytest.skip("redis library not available for testing")
        if not getattr(self, '_redis_available', False):
            pytest.skip("Redis service not available for testing")
            
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        secrets = builder.load_all_secrets()
        
        # Extract Redis connection info
        redis_host = secrets.get('REDIS_HOST', 'localhost')
        redis_port = int(secrets.get('REDIS_PORT', self.real_services.redis_port))
        redis_db = int(secrets.get('REDIS_DB', '0'))
        redis_password = secrets.get('REDIS_PASSWORD')  # May be None
        
        # Test actual Redis connection with retrieved secrets
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password if redis_password else None,
            socket_timeout=10,
            decode_responses=True
        )
        
        # Test Redis operations
        test_key = 'secret_manager_test'
        test_value = 'integration_test_value'
        
        redis_client.set(test_key, test_value, ex=60)  # Expire in 60s
        retrieved_value = redis_client.get(test_key)
        
        assert retrieved_value == test_value
        
        # Test Redis info
        info = redis_client.info()
        assert 'redis_version' in info
        
        # Cleanup
        redis_client.delete(test_key)
        redis_client.close()
    
    def test_cross_service_jwt_consistency_critical(self):
        """CRITICAL TEST: Ensure JWT secrets are identical across ALL services (SSOT)."""
        services = ['shared', 'auth_service', 'netra_backend']
        jwt_secrets = {}
        
        for service in services:
            builder = SecretManagerBuilder(env_vars=self.env.get_all(), service=service)
            jwt_secrets[service] = builder.auth.get_jwt_secret()
        
        # CRITICAL: All services MUST have identical JWT secrets
        first_jwt = list(jwt_secrets.values())[0]
        
        for service, jwt_secret in jwt_secrets.items():
            assert jwt_secret == first_jwt, (
                f"JWT secret mismatch for {service}: got {jwt_secret[:10]}..., "
                f"expected {first_jwt[:10]}... (SSOT violation)"
            )
        
        # Validate JWT format and security
        assert len(first_jwt) >= 32
        assert first_jwt != 'placeholder'
        assert 'test-jwt-secret-key' in first_jwt
    
    def test_secret_encryption_end_to_end(self):
        """Test end-to-end secret encryption with real sensitive data."""
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        
        # Test with real sensitive secrets
        sensitive_data = {
            'database_password': builder.env.get('POSTGRES_PASSWORD'),
            'jwt_secret': builder.auth.get_jwt_secret(),
            'api_key': builder.env.get('ANTHROPIC_API_KEY')
        }
        
        encrypted_data = {}
        
        # Encrypt all sensitive data
        for key, value in sensitive_data.items():
            if value:  # Only encrypt non-empty values
                encrypted_data[key] = builder.encryption.encrypt_secret(value)
                
                # Verify encryption
                assert encrypted_data[key] != value
                assert len(encrypted_data[key]) > len(value)
                
                # Verify decryption
                decrypted = builder.encryption.decrypt_secret(encrypted_data[key])
                assert decrypted == value
        
        # Test secure wipe
        for key in encrypted_data.keys():
            builder.encryption.secure_wipe(f"encrypted_{key}")
    
    def test_audit_logging_and_security_validation(self):
        """Test audit logging and security validation features."""
        builder = SecretManagerBuilder(env_vars=self.env.get_all())
        
        # Test audit logging
        builder.validation.audit_secret_access('JWT_SECRET_KEY', 'test_component', True)
        builder.validation.audit_secret_access('INVALID_SECRET', 'test_component', False)
        
        # Test password strength validation
        weak_passwords = ['password', '123456', 'admin', 'test']
        strong_password = 'complex-password-with-special-chars-123!@#'
        
        for weak_pass in weak_passwords:
            is_valid, error = builder.validation.validate_password_strength('test_pass', weak_pass)
            assert is_valid is False  # Should reject weak passwords
            assert 'weak' in error.lower() or 'short' in error.lower()
        
        # Strong password should pass in development
        is_valid, error = builder.validation.validate_password_strength('strong_pass', strong_password)
        assert is_valid is True
        assert error == ""
    
    def test_environment_specific_behavior(self):
        """Test environment-specific behavior differences."""
        environments = ['development', 'staging', 'production']
        
        for env_name in environments:
            test_env = self.env.get_all()
            test_env['ENVIRONMENT'] = env_name
            test_env['DISABLE_GCP_SECRET_MANAGER'] = 'true'  # For testing
            
            builder = SecretManagerBuilder(env_vars=test_env)
            
            assert builder._environment == env_name
            
            # Test environment-specific validation
            validation_result = builder.validate_configuration()
            
            if env_name == 'development':
                # Development should be more permissive
                assert builder.development.should_allow_fallback() is True
            else:
                # Staging/production should be stricter
                assert builder.development.should_allow_fallback() is False
            
            # Test debug info for each environment
            debug_info = builder.get_debug_info()
            assert debug_info['environment'] == env_name