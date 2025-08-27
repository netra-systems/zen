"""Integration test for Secret Manager timeout and caching behavior.

This test validates critical timeout and caching functionality that could cause
production issues if not working correctly.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects ALL customer tiers through service reliability)
- Business Goal: System Reliability, Operational Cost Reduction
- Value Impact: Prevents secret manager timeout issues that cause service hangs
- Strategic Impact: $50K/year in prevented outages from timeout-related failures

CRITICAL ISSUE TESTED:
Secret Manager operations can hang indefinitely if GCP Secret Manager is slow
or unreachable, causing the entire application to freeze during startup.
This test ensures proper timeout behavior and fallback mechanisms.
"""

import os
import time
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, Mock
import pytest

from shared.secret_manager_builder import (
    SecretManagerBuilder,
    SecretInfo,
    SecretValidationResult
)


class TestSecretManagerTimeoutBehavior:
    """Test timeout behavior for Secret Manager operations."""
    
    def setup_method(self):
        """Setup test environment."""
        # Save original environment
        self.original_env = dict(os.environ)
        
        # Set up clean test environment
        os.environ.clear()
        os.environ['ENVIRONMENT'] = 'test'
        os.environ['TESTING'] = '1'
    
    def teardown_method(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch('shared.secret_manager_builder.secretmanager')
    def test_gcp_secret_timeout_doesnt_hang_application(self, mock_secretmanager):
        """Test that GCP Secret Manager timeouts don't hang the application."""
        # Mock a slow/hanging GCP client
        mock_client = Mock()
        mock_secretmanager.SecretManagerServiceClient.return_value = mock_client
        
        # Make access_secret_version hang for a long time
        def slow_access(*args, **kwargs):
            time.sleep(10)  # Simulate 10 second hang
            raise Exception("Timeout after 10 seconds")
        
        mock_client.access_secret_version.side_effect = slow_access
        
        # Set up staging environment to trigger GCP usage
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['GCP_PROJECT_ID_NUMERICAL_STAGING'] = '701982941522'
        
        builder = SecretManagerBuilder(service="test_service")
        
        start_time = time.time()
        
        # This should not hang - should fail gracefully and return None
        result = builder.gcp.get_secret("test-secret")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should fail quickly, not hang for 10 seconds
        assert result is None
        assert elapsed < 5.0, f"Secret fetch took too long: {elapsed}s (should be quick failure)"
    
    def test_cache_ttl_expiration_works_correctly(self):
        """Test that cache TTL expiration works correctly."""
        builder = SecretManagerBuilder(service="test_service")
        
        # Cache a secret with short TTL
        secret_info = SecretInfo(
            name="test_secret",
            value="test_value",
            source="cache",
            environment="test",
            cached_at=datetime.now(timezone.utc),
            ttl_minutes=0.01  # 0.6 seconds
        )
        
        builder.cache.cache_secret_info(secret_info)
        
        # Should be cached initially
        cached_value = builder.cache.get_cached_secret("test_secret")
        assert cached_value == "test_value"
        
        # Wait for TTL expiration
        time.sleep(1)  # Wait 1 second for 0.6 second TTL
        
        # Should be expired now
        expired_value = builder.cache.get_cached_secret("test_secret")
        assert expired_value is None
    
    def test_secret_loading_with_concurrent_access(self):
        """Test that secret loading works correctly under concurrent access."""
        builder = SecretManagerBuilder(service="test_service")
        
        # Set up environment secrets
        os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
        os.environ['POSTGRES_PASSWORD'] = 'test-postgres-password'
        
        results = []
        errors = []
        
        def load_secrets_worker():
            """Worker function to load secrets concurrently."""
            try:
                secrets = builder.environment.load_all_secrets()
                results.append(secrets)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads loading secrets concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=load_secrets_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout per thread
        
        # All threads should complete successfully
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        
        # All results should be identical (consistent)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Concurrent secret loading produced inconsistent results"
    
    def test_validation_with_placeholder_detection(self):
        """Test that validation correctly detects placeholder values that could cause production issues."""
        # Create secrets with various placeholder patterns that could slip through
        test_secrets = {
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-should-be-replaced-in-deployment',
            'POSTGRES_PASSWORD': 'will-be-set-by-secrets',
            'REDIS_PASSWORD': '',  # Empty password
            'CLICKHOUSE_PASSWORD': 'REPLACE',
            'FERNET_KEY': 'placeholder-value'
        }
        
        # Set up staging environment (should be strict about placeholders)
        os.environ['ENVIRONMENT'] = 'staging'
        builder = SecretManagerBuilder(service="test_service")
        
        validation_result = builder.validation.validate_critical_secrets(test_secrets)
        
        # Should detect all placeholder values as errors in staging
        assert not validation_result.is_valid, "Validation should fail for placeholder values in staging"
        assert len(validation_result.errors) >= 3, f"Expected multiple errors, got: {validation_result.errors}"
        assert validation_result.placeholder_count >= 3, "Should detect multiple placeholder values"
        assert len(validation_result.critical_failures) >= 3, "Should have critical failures for placeholder values"
        
        # Check specific error messages
        error_text = ' '.join(validation_result.errors)
        assert 'JWT_SECRET_KEY' in error_text, "Should detect JWT secret placeholder"
        assert 'POSTGRES_PASSWORD' in error_text, "Should detect postgres password placeholder"
    
    def test_environment_detection_edge_cases(self):
        """Test environment detection with edge cases that could cause misclassification."""
        test_cases = [
            # Case 1: Mixed environment signals
            {
                'env_vars': {
                    'ENVIRONMENT': 'production',
                    'K_SERVICE': 'test-service',  # Cloud Run indicator but not staging
                },
                'expected_env': 'production'
            },
            # Case 2: Staging with mixed signals
            {
                'env_vars': {
                    'ENVIRONMENT': 'development',  # Conflicting signal
                    'K_SERVICE': 'netra-staging-backend',  # Clear staging signal
                    'GCP_PROJECT_ID': 'netra-staging'
                },
                'expected_env': 'staging'
            },
            # Case 3: Development fallback
            {
                'env_vars': {
                    'NODE_ENV': 'development',  # Frontend variable
                    'DEBUG': 'true'
                },
                'expected_env': 'development'
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with patch.dict(os.environ, test_case['env_vars'], clear=True):
                builder = SecretManagerBuilder(service="test_service")
                detected_env = builder._environment
                
                assert detected_env == test_case['expected_env'], \
                    f"Test case {i+1}: Expected '{test_case['expected_env']}', " \
                    f"got '{detected_env}' with env_vars: {test_case['env_vars']}"
    
    def test_jwt_secret_fallback_chain_exhaustive(self):
        """Test JWT secret fallback chain handles all failure scenarios correctly."""
        
        # Test case 1: All methods fail - should raise ValueError
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'production'
            
            builder = SecretManagerBuilder(service="test_service")
            
            # Mock GCP to fail
            with patch.object(builder.gcp, 'get_jwt_secret', return_value=None):
                with pytest.raises(ValueError, match="JWT secret not configured"):
                    builder.auth.get_jwt_secret()
        
        # Test case 2: GCP fails but environment variable works
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'production'
            os.environ['JWT_SECRET_KEY'] = 'production-jwt-secret-from-env'
            
            builder = SecretManagerBuilder(service="test_service")
            
            # Mock GCP to fail
            with patch.object(builder.gcp, 'get_jwt_secret', return_value=None):
                result = builder.auth.get_jwt_secret()
                assert result == 'production-jwt-secret-from-env'
        
        # Test case 3: Cache hit should return immediately
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'staging'
            
            builder = SecretManagerBuilder(service="test_service")
            
            # Pre-populate cache
            builder.cache.cache_secret("JWT_SECRET_KEY", "cached-jwt-secret", ttl_minutes=60)
            
            # Should return cached value without calling GCP or env
            with patch.object(builder.gcp, 'get_jwt_secret') as mock_gcp:
                result = builder.auth.get_jwt_secret()
                assert result == "cached-jwt-secret"
                mock_gcp.assert_not_called()  # Should not call GCP when cached
    
    def test_secret_manager_initialization_robustness(self):
        """Test that SecretManagerBuilder initialization is robust against various failure modes."""
        
        # Test 1: Missing service-specific environment manager
        with patch('shared.secret_manager_builder.get_env', side_effect=ImportError("Module not found")):
            # Should fall back to basic environment manager without crashing
            builder = SecretManagerBuilder(service="nonexistent_service")
            
            # Should still work with basic functionality
            assert builder.service == "nonexistent_service"
            assert builder._environment in ['development', 'staging', 'production']
        
        # Test 2: None values in env_vars should be handled gracefully
        env_vars_with_none = {
            'JWT_SECRET_KEY': 'valid-secret',
            'POSTGRES_PASSWORD': None,  # None value
            'REDIS_PASSWORD': '',       # Empty string
            'UNDEFINED_VAR': None       # Undefined with None
        }
        
        builder = SecretManagerBuilder(env_vars=env_vars_with_none, service="test")
        
        # Should handle None values without crashing
        secrets = builder.environment.load_environment_secrets()
        
        # None values should not appear in final secrets
        assert secrets.get('JWT_SECRET_KEY') == 'valid-secret'
        assert 'UNDEFINED_VAR' not in secrets or secrets.get('UNDEFINED_VAR') is None
        
        # Empty strings should be preserved if they exist in environment
        if 'REDIS_PASSWORD' in secrets:
            assert secrets['REDIS_PASSWORD'] == ''
    
    def test_debug_info_provides_comprehensive_status(self):
        """Test that debug info provides comprehensive status for troubleshooting."""
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['GCP_PROJECT_ID_NUMERICAL_STAGING'] = '701982941522'
        
        builder = SecretManagerBuilder(service="test_service")
        
        # Mock GCP connectivity failure for testing
        with patch.object(builder.gcp, 'validate_gcp_connectivity', return_value=(False, "Connection timeout")):
            debug_info = builder.get_debug_info()
        
        # Should provide comprehensive debug information
        assert 'environment' in debug_info
        assert 'service' in debug_info
        assert 'project_id' in debug_info
        assert 'gcp_connectivity' in debug_info
        assert 'validation' in debug_info
        assert 'cache_stats' in debug_info
        assert 'features' in debug_info
        
        # GCP connectivity should show failure
        assert debug_info['gcp_connectivity']['is_valid'] is False
        assert debug_info['gcp_connectivity']['error'] == "Connection timeout"
        
        # Environment should be detected correctly
        assert debug_info['environment'] == 'staging'
        assert debug_info['service'] == 'test_service'
        
        # Features should be set appropriately for staging
        assert debug_info['features']['gcp_enabled'] is True
        assert 'encryption_available' in debug_info['features']


class TestSecretManagerProductionFailures:
    """Test secret manager behavior under production-like failure conditions."""
    
    def test_production_requirements_validation_strict(self):
        """Test that production requirements are strictly validated."""
        
        # Set up production environment
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'production'
            os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/db'  # localhost not allowed
            os.environ['REDIS_URL'] = 'redis://localhost:6379'  # localhost not allowed
            
            builder = SecretManagerBuilder(service="test_service")
            
            # Mock GCP to fail (common production issue)
            with patch.object(builder.gcp, 'validate_gcp_connectivity', return_value=(False, "Network timeout")):
                is_valid, errors = builder.production.validate_production_requirements()
                
                assert not is_valid, "Production validation should fail with localhost URLs and no GCP"
                
                # Should have specific error messages
                error_text = ' '.join(errors)
                assert 'localhost' in error_text, "Should reject localhost connections"
                assert 'GCP connectivity required' in error_text, "Should require GCP connectivity"
    
    def test_staging_requirements_more_permissive_than_production(self):
        """Test that staging requirements are more permissive than production."""
        
        # Set up staging environment with localhost (might be acceptable in staging)
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'staging'
            os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/db'
            os.environ['ALLOW_LOCALHOST_DATABASE'] = 'true'  # Explicit override
            
            # Set critical secrets to non-placeholder values
            os.environ['JWT_SECRET_KEY'] = 'staging-jwt-secret-valid'
            os.environ['POSTGRES_PASSWORD'] = 'staging-postgres-password'
            os.environ['REDIS_PASSWORD'] = 'staging-redis-password'
            os.environ['CLICKHOUSE_PASSWORD'] = 'staging-clickhouse-password'
            os.environ['FERNET_KEY'] = 'staging-fernet-key-valid'
            
            builder = SecretManagerBuilder(service="test_service")
            
            # Mock GCP to succeed for staging
            with patch.object(builder.gcp, 'validate_gcp_connectivity', return_value=(True, "")):
                is_valid, errors = builder.staging.validate_staging_requirements()
                
                # Should be valid in staging with explicit localhost override
                if not is_valid:
                    pytest.fail(f"Staging should allow localhost with ALLOW_LOCALHOST_DATABASE=true. Errors: {errors}")
    
    def test_memory_cleanup_prevents_secret_leaks(self):
        """Test that memory cleanup prevents secret values from lingering."""
        builder = SecretManagerBuilder(service="test_service")
        
        # Store a secret
        secret_name = "sensitive_secret"
        secret_value = "very-sensitive-value-that-should-not-leak"
        
        builder.cache.cache_secret(secret_name, secret_value)
        
        # Verify it's cached
        assert builder.cache.get_cached_secret(secret_name) == secret_value
        
        # Secure wipe
        builder.encryption.secure_wipe(secret_name)
        
        # Should be gone from cache
        assert builder.cache.get_cached_secret(secret_name) is None
        
        # Verify it's not in the internal cache structure
        assert secret_name not in builder._secret_cache
    
    def test_concurrent_cache_access_thread_safety(self):
        """Test that concurrent cache access is thread-safe."""
        builder = SecretManagerBuilder(service="test_service")
        
        results = []
        errors = []
        
        def cache_worker(thread_id):
            """Worker that performs cache operations."""
            try:
                for i in range(10):
                    # Cache and retrieve
                    secret_name = f"thread_{thread_id}_secret_{i}"
                    secret_value = f"value_{thread_id}_{i}"
                    
                    builder.cache.cache_secret(secret_name, secret_value)
                    retrieved = builder.cache.get_cached_secret(secret_name)
                    
                    if retrieved != secret_value:
                        errors.append(f"Thread {thread_id}: Expected {secret_value}, got {retrieved}")
                    
                    results.append((thread_id, i, retrieved == secret_value))
                    
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")
        
        # Start multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=cache_worker, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 50, f"Expected 50 operations, got {len(results)}"  # 5 threads × 10 operations
        
        # All operations should have succeeded
        successful_ops = [r for r in results if r[2] is True]
        assert len(successful_ops) == 50, f"Not all operations succeeded: {len(successful_ops)}/50"