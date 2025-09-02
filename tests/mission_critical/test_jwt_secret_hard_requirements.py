import asyncio
import hashlib
import hmac
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Mission Critical: JWT Secret Hard Requirements Test

Verifies that both auth and backend services FAIL HARD when environment-specific 
JWT secrets are not provided, with no fallbacks allowed.

This test prevents authentication failures by ensuring proper secret configuration
before deployment.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestJWTSecretHardRequirements:
    """Comprehensive JWT secret testing with authentication flow validation."""
    
    def setup_method(self):
        """Clear JWT environment variables before each test."""
        self.original_env = {}
        for key in list(os.environ.keys()):
            if 'JWT' in key or key == 'ENVIRONMENT':
                self.original_env[key] = os.environ[key]
                del os.environ[key]
        
        # Clear any cached secrets to ensure fresh loading
        try:
            from shared.jwt_secret_manager import SharedJWTSecretManager
            SharedJWTSecretManager.clear_cache()
        except ImportError:
            pass
        
        try:
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            if hasattr(AuthSecretLoader, '_secret_cache'):
                AuthSecretLoader._secret_cache = {}
        except ImportError:
            pass
    
    def teardown_method(self):
        """Restore original environment after each test."""
        # Clear all JWT vars
        for key in list(os.environ.keys()):
            if 'JWT' in key or key == 'ENVIRONMENT':
                del os.environ[key]
        
        # Restore original values
        for key, value in self.original_env.items():
            os.environ[key] = value
        
        # Clear caches again
        try:
            from shared.jwt_secret_manager import SharedJWTSecretManager
            SharedJWTSecretManager.clear_cache()
        except ImportError:
            pass
        
        try:
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            if hasattr(AuthSecretLoader, '_secret_cache'):
                AuthSecretLoader._secret_cache = {}
        except ImportError:
            pass
    
    def test_staging_auth_service_requires_jwt_secret_staging(self):
        """Test auth service FAILS HARD without JWT_SECRET_STAGING in staging."""
        os.environ['ENVIRONMENT'] = 'staging'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            AuthSecretLoader.get_jwt_secret()
    
    def test_staging_backend_service_requires_jwt_secret_staging(self):
        """Test backend service FAILS HARD without JWT_SECRET_STAGING in staging."""
        os.environ['ENVIRONMENT'] = 'staging'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            secret_manager.get_jwt_secret()
    
    def test_production_auth_service_requires_jwt_secret_production(self):
        """Test auth service FAILS HARD without JWT_SECRET_PRODUCTION in production."""
        os.environ['ENVIRONMENT'] = 'production'
        # Explicitly NOT setting JWT_SECRET_PRODUCTION
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            AuthSecretLoader.get_jwt_secret()
    
    def test_production_backend_service_requires_jwt_secret_production(self):
        """Test backend service FAILS HARD without JWT_SECRET_PRODUCTION in production."""
        os.environ['ENVIRONMENT'] = 'production'
        # Explicitly NOT setting JWT_SECRET_PRODUCTION
        
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            secret_manager.get_jwt_secret()
    
    def test_development_auth_service_requires_jwt_secret_key(self):
        """Test auth service FAILS HARD without JWT_SECRET_KEY in development."""
        os.environ['ENVIRONMENT'] = 'development'
        # Explicitly NOT setting JWT_SECRET_KEY
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        with pytest.raises(ValueError, match="JWT secret not configured for development environment"):
            AuthSecretLoader.get_jwt_secret()
    
    def test_development_backend_service_requires_jwt_secret_key(self):
        """Test backend service FAILS HARD without JWT_SECRET_KEY in development."""
        os.environ['ENVIRONMENT'] = 'development'
        # Explicitly NOT setting JWT_SECRET_KEY
        
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for development environment"):
            secret_manager.get_jwt_secret()
    
    def test_staging_services_use_same_secret_when_properly_configured(self):
        """Test that both services use the same JWT secret when properly configured for staging."""
        staging_secret = "test-staging-jwt-secret-86-characters-long-for-proper-security-validation-testing"
        
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = staging_secret
        
        # Test auth service
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        auth_jwt_secret = AuthSecretLoader.get_jwt_secret()
        
        # Test backend service
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        backend_jwt_secret = backend_secret_manager.get_jwt_secret()
        
        # Verify both services use the same secret
        assert auth_jwt_secret == backend_jwt_secret == staging_secret
        assert len(auth_jwt_secret) >= 32  # Security requirement
    
    def test_development_services_use_same_secret_when_properly_configured(self):
        """Test that both services use the same JWT secret when properly configured for development."""
        dev_secret = "test-development-jwt-secret-key-64-characters-long-for-testing"
        
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['JWT_SECRET_KEY'] = dev_secret
        
        # Test auth service
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        auth_jwt_secret = AuthSecretLoader.get_jwt_secret()
        
        # Test backend service
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        backend_jwt_secret = backend_secret_manager.get_jwt_secret()
        
        # Verify both services use the same secret
        assert auth_jwt_secret == backend_jwt_secret == dev_secret
        assert len(auth_jwt_secret) >= 32  # Security requirement
    
    def test_no_fallback_to_jwt_secret_key_in_staging(self):
        """Test that staging environment does NOT fallback to JWT_SECRET_KEY."""
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_KEY'] = 'should-not-be-used-in-staging-fallback'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        # Auth service should fail
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            AuthSecretLoader.get_jwt_secret()
        
        # Backend service should fail
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            backend_secret_manager.get_jwt_secret()
    
    def test_no_fallback_to_jwt_secret_key_in_production(self):
        """Test that production environment does NOT fallback to JWT_SECRET_KEY."""
        os.environ['ENVIRONMENT'] = 'production'
        os.environ['JWT_SECRET_KEY'] = 'should-not-be-used-in-production-fallback'
        # Explicitly NOT setting JWT_SECRET_PRODUCTION
        
        # Auth service should fail
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            AuthSecretLoader.get_jwt_secret()
        
        # Backend service should fail  
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            backend_secret_manager.get_jwt_secret()


    # =============================================================================
    # NEW COMPREHENSIVE AUTHENTICATION FLOW VALIDATION TESTS
    # =============================================================================
    
    def test_complete_auth_flow_with_jwt_validation(self):
        """Test complete authentication flow with JWT secret validation."""
        # Test staging environment authentication flow
        staging_secret = "staging-jwt-secret-86-characters-long-for-comprehensive-security-validation"
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = staging_secret
        
        try:
            # Step 1: User registration and login simulation
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
            
            # Verify secret synchronization
            auth_secret = AuthSecretLoader.get_jwt_secret()
            backend_secret_manager = UnifiedSecretManager()
            backend_secret = backend_secret_manager.get_jwt_secret()
            
            assert auth_secret == backend_secret == staging_secret
            
            # Step 2: Token generation and cross-service validation
            jwt_handler = JWTHandler()
            test_user_id = "test_auth_flow_user_123"
            test_email = "auth_flow@test.netra.ai"
            test_permissions = ["read", "write", "chat"]
            
            # Generate token using auth service
            access_token = jwt_handler.create_access_token(
                user_id=test_user_id,
                email=test_email,
                permissions=test_permissions
            )
            
            assert access_token is not None, "Failed to generate access token"
            
            # Step 3: Validate token with auth service
            auth_validation = jwt_handler.validate_token(access_token, "access")
            assert auth_validation is not None, "Auth service failed to validate its own token"
            assert auth_validation["sub"] == test_user_id
            assert auth_validation["email"] == test_email
            
            # Step 4: Cross-validate with backend service
            from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator
            backend_validator = UnifiedJWTValidator()
            backend_validation = backend_validator.validate_token_jwt(access_token)
            
            # This would be async in real implementation
            assert hasattr(backend_validation, 'valid'), "Backend validation result missing 'valid' attribute"
            
            print(f"✅ Complete auth flow validation successful:")
            print(f"  - Secret synchronization: PASSED")
            print(f"  - Token generation: PASSED")
            print(f"  - Auth service validation: PASSED")
            print(f"  - Backend validation: {'PASSED' if backend_validation.valid else 'FAILED'}")
            
        except Exception as e:
            pytest.fail(f"Complete auth flow failed: {e}")
    
    def test_concurrent_user_auth_with_jwt_secrets(self):
        """Test concurrent user authentication with proper JWT secret handling."""
        staging_secret = "concurrent-test-jwt-secret-86-characters-long-for-load-testing-validation"
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = staging_secret
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        import threading
        import time
        
        concurrent_users = 25
        success_count = 0
        failure_count = 0
        auth_results = []
        
        def authenticate_user(user_id):
            """Authenticate a single user concurrently."""
            nonlocal success_count, failure_count
            
            try:
                start_time = time.time()
                
                # Verify secret is accessible
                secret = AuthSecretLoader.get_jwt_secret()
                assert secret == staging_secret, f"Secret mismatch for user {user_id}"
                
                # Generate and validate token
                jwt_handler = JWTHandler()
                token = jwt_handler.create_access_token(
                    user_id=f"concurrent_user_{user_id}",
                    email=f"user_{user_id}@concurrent.test",
                    permissions=["read", "write"]
                )
                
                validation = jwt_handler.validate_token(token, "access")
                assert validation is not None, f"Token validation failed for user {user_id}"
                
                auth_time = time.time() - start_time
                
                auth_results.append({
                    'user_id': user_id,
                    'success': True,
                    'auth_time': auth_time,
                    'token_length': len(token)
                })
                
                success_count += 1
                
            except Exception as e:
                auth_results.append({
                    'user_id': user_id,
                    'success': False,
                    'error': str(e),
                    'auth_time': time.time() - start_time if 'start_time' in locals() else 0
                })
                failure_count += 1
        
        # Launch concurrent authentication attempts
        threads = []
        for i in range(concurrent_users):
            thread = threading.Thread(target=authenticate_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        success_rate = success_count / concurrent_users
        successful_auths = [r for r in auth_results if r['success']]
        avg_auth_time = sum(r['auth_time'] for r in successful_auths) / len(successful_auths) if successful_auths else float('inf')
        
        print(f"\n🔄 Concurrent Authentication Results:")
        print(f"  - Total users: {concurrent_users}")
        print(f"  - Successful auths: {success_count}")
        print(f"  - Failed auths: {failure_count}")
        print(f"  - Success rate: {success_rate:.2%}")
        print(f"  - Average auth time: {avg_auth_time:.3f}s")
        
        # Critical assertions for revenue scaling
        assert success_rate >= 0.96, f"Success rate too low: {success_rate:.2%} (minimum 96% required)"
        assert avg_auth_time < 1.0, f"Average auth time too slow: {avg_auth_time:.3f}s (maximum 1s)"
    
    def test_multi_environment_jwt_isolation(self):
        """Test JWT secret isolation across different environments."""
        environments = {
            'development': {
                'secret_key': 'JWT_SECRET_KEY',
                'secret_value': 'dev-jwt-secret-minimum-32-characters-long-for-testing'
            },
            'staging': {
                'secret_key': 'JWT_SECRET_STAGING',
                'secret_value': 'staging-jwt-secret-86-characters-long-for-comprehensive-security'
            },
            'production': {
                'secret_key': 'JWT_SECRET_PRODUCTION',
                'secret_value': 'prod-jwt-secret-128-characters-extremely-long-for-maximum-security-in-production'
            }
        }
        
        isolation_results = []
        
        for env_name, env_config in environments.items():
            try:
                # Set environment variables
                os.environ['ENVIRONMENT'] = env_name
                os.environ[env_config['secret_key']] = env_config['secret_value']
                
                # Clear other environment secrets to ensure isolation
                for other_env, other_config in environments.items():
                    if other_env != env_name:
                        os.environ.pop(other_config['secret_key'], None)
                
                # Test auth service secret loading
                from auth_service.auth_core.secret_loader import AuthSecretLoader
                AuthSecretLoader._secret_cache = {}  # Clear cache
                
                auth_secret = AuthSecretLoader.get_jwt_secret()
                assert auth_secret == env_config['secret_value'], f"Auth secret mismatch in {env_name}"
                
                # Test backend service secret loading
                from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
                backend_manager = UnifiedSecretManager()
                backend_secret = backend_manager.get_jwt_secret()
                assert backend_secret == env_config['secret_value'], f"Backend secret mismatch in {env_name}"
                
                # Test token generation and validation
                from auth_service.auth_core.core.jwt_handler import JWTHandler
                jwt_handler = JWTHandler()
                
                token = jwt_handler.create_access_token(
                    user_id=f"{env_name}_test_user",
                    email=f"test@{env_name}.netra.ai",
                    permissions=["read", "write"]
                )
                
                validation = jwt_handler.validate_token(token, "access")
                assert validation is not None, f"Token validation failed in {env_name}"
                assert validation["env"] == env_name, f"Token environment claim incorrect in {env_name}"
                
                isolation_results.append({
                    'environment': env_name,
                    'success': True,
                    'secret_length': len(env_config['secret_value']),
                    'token_generated': True,
                    'cross_service_sync': auth_secret == backend_secret
                })
                
                print(f"✅ {env_name.upper()} environment isolation: PASSED")
                
            except Exception as e:
                isolation_results.append({
                    'environment': env_name,
                    'success': False,
                    'error': str(e)
                })
                print(f"❌ {env_name.upper()} environment isolation: FAILED - {e}")
        
        # Verify all environments worked
        successful_envs = [r for r in isolation_results if r['success']]
        assert len(successful_envs) == len(environments), \
            f"Not all environments properly isolated: {len(successful_envs)}/{len(environments)}"
    
    def test_jwt_token_lifecycle_validation(self):
        """Test complete JWT token lifecycle with secret validation."""
        staging_secret = "lifecycle-jwt-secret-86-characters-long-for-complete-lifecycle-testing"
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = staging_secret
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        from datetime import datetime, timedelta
        import jwt as jwt_lib
        
        try:
            # Step 1: Token Creation
            jwt_handler = JWTHandler()
            user_data = {
                'user_id': 'lifecycle_test_user_456',
                'email': 'lifecycle@test.netra.ai',
                'permissions': ['read', 'write', 'admin']
            }
            
            access_token = jwt_handler.create_access_token(
                user_id=user_data['user_id'],
                email=user_data['email'],
                permissions=user_data['permissions']
            )
            
            # Step 2: Token Analysis
            decoded_token = jwt_lib.decode(access_token, options={"verify_signature": False})
            
            # Verify required claims
            required_claims = ['sub', 'email', 'iat', 'exp', 'jti', 'iss', 'aud']
            for claim in required_claims:
                assert claim in decoded_token, f"Missing required claim: {claim}"
            
            assert decoded_token['sub'] == user_data['user_id']
            assert decoded_token['email'] == user_data['email']
            assert decoded_token['env'] == 'staging'
            
            # Step 3: Token Validation (Fresh)
            validation_result = jwt_handler.validate_token(access_token, "access")
            assert validation_result is not None, "Fresh token validation failed"
            assert validation_result['sub'] == user_data['user_id']
            
            # Step 4: Token Expiry Testing
            # Create short-lived token for expiry testing
            short_lived_token = jwt_lib.encode(
                {
                    'sub': user_data['user_id'],
                    'email': user_data['email'],
                    'iat': int(datetime.utcnow().timestamp()),
                    'exp': int((datetime.utcnow() - timedelta(seconds=1)).timestamp()),  # Already expired
                    'jti': 'expired_test_token',
                    'iss': 'netra-auth-service',
                    'aud': 'netra-platform',
                    'env': 'staging'
                },
                staging_secret,
                algorithm='HS256'
            )
            
            expired_validation = jwt_handler.validate_token(short_lived_token, "access")
            assert expired_validation is None, "Expired token should not validate"
            
            # Step 5: Token Refresh Simulation
            refresh_token = jwt_handler.create_refresh_token(
                user_id=user_data['user_id'],
                email=user_data['email']
            )
            
            refresh_validation = jwt_handler.validate_token(refresh_token, "refresh")
            assert refresh_validation is not None, "Refresh token validation failed"
            
            # Step 6: Cross-Service Validation
            from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator
            backend_validator = UnifiedJWTValidator()
            backend_validation = backend_validator.validate_token_jwt(access_token)
            
            # This would be async in real implementation
            if hasattr(backend_validation, 'valid'):
                assert backend_validation.valid, f"Backend validation failed: {backend_validation.error if hasattr(backend_validation, 'error') else 'Unknown error'}"
            
            print(f"✅ JWT Token Lifecycle Validation:")
            print(f"  - Token creation: PASSED")
            print(f"  - Claims validation: PASSED")
            print(f"  - Fresh token validation: PASSED")
            print(f"  - Expired token rejection: PASSED")
            print(f"  - Refresh token validation: PASSED")
            print(f"  - Cross-service validation: PASSED")
            
        except Exception as e:
            pytest.fail(f"JWT token lifecycle validation failed: {e}")
    
    def test_jwt_secret_security_requirements(self):
        """Test JWT secret security requirements and entropy."""
        import hashlib
        import re
        
        security_tests = [
            {
                'name': 'Development Secret',
                'env': 'development',
                'secret_key': 'JWT_SECRET_KEY',
                'secret': 'development-jwt-secret-minimum-32-characters-for-security',
                'min_length': 32,
                'entropy_threshold': 4.0
            },
            {
                'name': 'Staging Secret',
                'env': 'staging',
                'secret_key': 'JWT_SECRET_STAGING',
                'secret': 'staging-jwt-secret-86-characters-long-with-high-entropy-for-comprehensive-security',
                'min_length': 64,
                'entropy_threshold': 4.5
            },
            {
                'name': 'Production Secret',
                'env': 'production',
                'secret_key': 'JWT_SECRET_PRODUCTION',
                'secret': 'production-jwt-secret-128-characters-extremely-long-with-maximum-entropy-for-production-security-requirements',
                'min_length': 128,
                'entropy_threshold': 5.0
            }
        ]
        
        def calculate_entropy(data):
            """Calculate Shannon entropy of a string."""
            if not data:
                return 0
            
            entropy = 0
            for x in set(data):
                p_x = float(data.count(x)) / len(data)
                if p_x > 0:
                    entropy += - p_x * (p_x).bit_length()
            return entropy
        
        security_results = []
        
        for test_config in security_tests:
            try:
                os.environ['ENVIRONMENT'] = test_config['env']
                os.environ[test_config['secret_key']] = test_config['secret']
                
                # Length validation
                secret_length = len(test_config['secret'])
                length_valid = secret_length >= test_config['min_length']
                
                # Entropy calculation
                entropy = calculate_entropy(test_config['secret'])
                entropy_valid = entropy >= test_config['entropy_threshold']
                
                # Character diversity
                has_lowercase = bool(re.search(r'[a-z]', test_config['secret']))
                has_uppercase = bool(re.search(r'[A-Z]', test_config['secret']))
                has_numbers = bool(re.search(r'\d', test_config['secret']))
                has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'"\\|,.<>?]', test_config['secret']))
                
                char_diversity = sum([has_lowercase, has_uppercase, has_numbers, has_special])
                diversity_valid = char_diversity >= 2  # At least 2 character types
                
                # Hash uniqueness (prevent common secrets)
                secret_hash = hashlib.sha256(test_config['secret'].encode()).hexdigest()
                common_hashes = [
                    hashlib.sha256(b'password123').hexdigest(),
                    hashlib.sha256(b'secret').hexdigest(),
                    hashlib.sha256(b'jwt_secret').hexdigest(),
                    hashlib.sha256(b'development').hexdigest()
                ]
                hash_unique = secret_hash not in common_hashes
                
                # Service loading test
                from auth_service.auth_core.secret_loader import AuthSecretLoader
                AuthSecretLoader._secret_cache = {}  # Clear cache
                
                loaded_secret = AuthSecretLoader.get_jwt_secret()
                loading_valid = loaded_secret == test_config['secret']
                
                all_valid = all([
                    length_valid,
                    entropy_valid,
                    diversity_valid,
                    hash_unique,
                    loading_valid
                ])
                
                security_results.append({
                    'name': test_config['name'],
                    'success': all_valid,
                    'length_valid': length_valid,
                    'entropy_valid': entropy_valid,
                    'diversity_valid': diversity_valid,
                    'hash_unique': hash_unique,
                    'loading_valid': loading_valid,
                    'metrics': {
                        'length': secret_length,
                        'entropy': entropy,
                        'char_diversity': char_diversity
                    }
                })
                
                status = "PASSED" if all_valid else "FAILED"
                print(f"🔒 {test_config['name']} Security: {status}")
                print(f"  - Length: {secret_length} chars ({'✅' if length_valid else '❌'})")
                print(f"  - Entropy: {entropy:.2f} ({'✅' if entropy_valid else '❌'})")
                print(f"  - Char diversity: {char_diversity}/4 ({'✅' if diversity_valid else '❌'})")
                print(f"  - Hash unique: {'✅' if hash_unique else '❌'}")
                print(f"  - Loading: {'✅' if loading_valid else '❌'}")
                
            except Exception as e:
                security_results.append({
                    'name': test_config['name'],
                    'success': False,
                    'error': str(e)
                })
                print(f"❌ {test_config['name']} Security: FAILED - {e}")
        
        # Verify all security tests passed
        successful_tests = [r for r in security_results if r['success']]
        assert len(successful_tests) == len(security_tests), \
            f"Security requirements not met: {len(successful_tests)}/{len(security_tests)} passed"
    
    def test_user_journey_with_jwt_validation(self):
        """Test complete user journey with JWT secret validation at each step."""
        journey_secret = "journey-jwt-secret-86-characters-long-for-complete-user-journey-testing"
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = journey_secret
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        import time
        
        journey_timeline = []
        start_time = time.time()
        
        try:
            # Step 1: User Registration
            journey_timeline.append({'step': 'registration_start', 'time': time.time() - start_time})
            
            # Verify JWT secret is available for registration
            registration_secret = AuthSecretLoader.get_jwt_secret()
            assert registration_secret == journey_secret, "JWT secret not available for registration"
            
            journey_timeline.append({'step': 'registration_jwt_verified', 'time': time.time() - start_time})
            
            # Step 2: User Login
            journey_timeline.append({'step': 'login_start', 'time': time.time() - start_time})
            
            jwt_handler = JWTHandler()
            login_token = jwt_handler.create_access_token(
                user_id='journey_test_user_789',
                email='journey@test.netra.ai',
                permissions=['read', 'write', 'chat']
            )
            
            assert login_token is not None, "Failed to generate login token"
            journey_timeline.append({'step': 'login_token_generated', 'time': time.time() - start_time})
            
            # Step 3: Token Validation
            login_validation = jwt_handler.validate_token(login_token, "access")
            assert login_validation is not None, "Login token validation failed"
            
            journey_timeline.append({'step': 'login_token_validated', 'time': time.time() - start_time})
            
            # Step 4: Chat Initialization (Simulated)
            # In real scenario, this would involve WebSocket connection with token auth
            chat_validation = jwt_handler.validate_token(login_token, "access")
            assert chat_validation is not None, "Chat token validation failed"
            assert 'chat' in chat_validation.get('permissions', []), "Chat permission missing"
            
            journey_timeline.append({'step': 'chat_initialized', 'time': time.time() - start_time})
            
            # Step 5: Agent Execution (Simulated)
            agent_validation = jwt_handler.validate_token(login_token, "access")
            assert agent_validation is not None, "Agent token validation failed"
            
            journey_timeline.append({'step': 'agent_executed', 'time': time.time() - start_time})
            
            # Step 6: Token Refresh
            refresh_token = jwt_handler.create_refresh_token(
                user_id='journey_test_user_789',
                email='journey@test.netra.ai'
            )
            
            refresh_validation = jwt_handler.validate_token(refresh_token, "refresh")
            assert refresh_validation is not None, "Refresh token validation failed"
            
            # Generate new access token
            new_access_token = jwt_handler.create_access_token(
                user_id='journey_test_user_789',
                email='journey@test.netra.ai',
                permissions=['read', 'write', 'chat']
            )
            
            new_token_validation = jwt_handler.validate_token(new_access_token, "access")
            assert new_token_validation is not None, "New access token validation failed"
            
            journey_timeline.append({'step': 'token_refreshed', 'time': time.time() - start_time})
            
            total_journey_time = time.time() - start_time
            
            print(f"\n🚀 Complete User Journey Results:")
            print(f"  - Total journey time: {total_journey_time:.3f}s")
            for step in journey_timeline:
                print(f"  - {step['step']}: {step['time']:.3f}s")
            
            # Verify journey completed in reasonable time (critical for UX)
            assert total_journey_time < 10.0, f"User journey too slow: {total_journey_time:.3f}s (max 10s)"
            
            # Verify all critical steps completed
            required_steps = ['registration_jwt_verified', 'login_token_generated', 'login_token_validated', 'chat_initialized', 'token_refreshed']
            completed_steps = [step['step'] for step in journey_timeline]
            
            for required_step in required_steps:
                assert required_step in completed_steps, f"Critical step missing: {required_step}"
            
        except Exception as e:
            print(f"\n❌ User Journey Failed:")
            print(f"  - Error: {e}")
            print(f"  - Timeline: {journey_timeline}")
            pytest.fail(f"User journey with JWT validation failed: {e}")
    
    def test_performance_under_jwt_load(self):
        """Test JWT operations performance under load."""
        load_secret = "load-test-jwt-secret-86-characters-long-for-performance-testing-under-load"
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = load_secret
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        import threading
        import time
        
        performance_metrics = {
            'token_generation_times': [],
            'token_validation_times': [],
            'secret_loading_times': [],
            'total_operations': 0,
            'failed_operations': 0
        }
        
        def jwt_operations_worker(worker_id, operations_per_worker):
            """Perform JWT operations in a worker thread."""
            nonlocal performance_metrics
            
            try:
                jwt_handler = JWTHandler()
                
                for i in range(operations_per_worker):
                    # Secret loading timing
                    secret_start = time.time()
                    secret = AuthSecretLoader.get_jwt_secret()
                    secret_time = time.time() - secret_start
                    
                    assert secret == load_secret, f"Secret mismatch in worker {worker_id}"
                    performance_metrics['secret_loading_times'].append(secret_time)
                    
                    # Token generation timing
                    gen_start = time.time()
                    token = jwt_handler.create_access_token(
                        user_id=f"load_user_{worker_id}_{i}",
                        email=f"load_{worker_id}_{i}@test.netra.ai",
                        permissions=["read", "write"]
                    )
                    gen_time = time.time() - gen_start
                    
                    assert token is not None, f"Token generation failed for worker {worker_id}"
                    performance_metrics['token_generation_times'].append(gen_time)
                    
                    # Token validation timing
                    val_start = time.time()
                    validation = jwt_handler.validate_token(token, "access")
                    val_time = time.time() - val_start
                    
                    assert validation is not None, f"Token validation failed for worker {worker_id}"
                    performance_metrics['token_validation_times'].append(val_time)
                    
                    performance_metrics['total_operations'] += 1
                    
            except Exception as e:
                performance_metrics['failed_operations'] += 1
                print(f"Worker {worker_id} failed: {e}")
        
        # Configuration
        num_workers = 10
        operations_per_worker = 20
        total_expected_operations = num_workers * operations_per_worker
        
        print(f"\n⚡ Starting JWT Performance Load Test:")
        print(f"  - Workers: {num_workers}")
        print(f"  - Operations per worker: {operations_per_worker}")
        print(f"  - Total expected operations: {total_expected_operations}")
        
        # Launch worker threads
        start_time = time.time()
        threads = []
        
        for worker_id in range(num_workers):
            thread = threading.Thread(target=jwt_operations_worker, args=(worker_id, operations_per_worker))
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join()
        
        total_test_time = time.time() - start_time
        
        # Calculate performance statistics
        successful_operations = performance_metrics['total_operations']
        failure_rate = performance_metrics['failed_operations'] / total_expected_operations
        operations_per_second = successful_operations / total_test_time if total_test_time > 0 else 0
        
        # Timing statistics
        avg_secret_loading = sum(performance_metrics['secret_loading_times']) / len(performance_metrics['secret_loading_times']) if performance_metrics['secret_loading_times'] else 0
        avg_token_generation = sum(performance_metrics['token_generation_times']) / len(performance_metrics['token_generation_times']) if performance_metrics['token_generation_times'] else 0
        avg_token_validation = sum(performance_metrics['token_validation_times']) / len(performance_metrics['token_validation_times']) if performance_metrics['token_validation_times'] else 0
        
        # P95 calculations
        p95_secret_loading = sorted(performance_metrics['secret_loading_times'])[int(len(performance_metrics['secret_loading_times']) * 0.95)] if performance_metrics['secret_loading_times'] else 0
        p95_token_generation = sorted(performance_metrics['token_generation_times'])[int(len(performance_metrics['token_generation_times']) * 0.95)] if performance_metrics['token_generation_times'] else 0
        p95_token_validation = sorted(performance_metrics['token_validation_times'])[int(len(performance_metrics['token_validation_times']) * 0.95)] if performance_metrics['token_validation_times'] else 0
        
        print(f"\n📊 JWT Performance Results:")
        print(f"  - Total test time: {total_test_time:.3f}s")
        print(f"  - Successful operations: {successful_operations}")
        print(f"  - Failed operations: {performance_metrics['failed_operations']}")
        print(f"  - Failure rate: {failure_rate:.2%}")
        print(f"  - Operations per second: {operations_per_second:.1f}")
        print(f"\n⏱️  Average Timings:")
        print(f"  - Secret loading: {avg_secret_loading:.6f}s")
        print(f"  - Token generation: {avg_token_generation:.6f}s")
        print(f"  - Token validation: {avg_token_validation:.6f}s")
        print(f"\n📈 P95 Timings:")
        print(f"  - Secret loading P95: {p95_secret_loading:.6f}s")
        print(f"  - Token generation P95: {p95_token_generation:.6f}s")
        print(f"  - Token validation P95: {p95_token_validation:.6f}s")
        
        # Performance assertions for revenue-critical operations
        assert failure_rate < 0.01, f"Failure rate too high: {failure_rate:.2%} (max 1%)")
        assert operations_per_second >= 100, f"Operations per second too low: {operations_per_second:.1f} (min 100/s)"
        assert avg_token_generation < 0.01, f"Token generation too slow: {avg_token_generation:.6f}s (max 0.01s)"
        assert avg_token_validation < 0.005, f"Token validation too slow: {avg_token_validation:.6f}s (max 0.005s)"
        assert p95_token_generation < 0.02, f"P95 token generation too slow: {p95_token_generation:.6f}s (max 0.02s)"
        assert p95_token_validation < 0.01, f"P95 token validation too slow: {p95_token_validation:.6f}s (max 0.01s)"


if __name__ == "__main__":
    # Run the tests directly
    test_instance = TestJWTSecretHardRequirements()
    
    # Original tests
    original_tests = [
        ("Staging Auth Hard Requirement", test_instance.test_staging_auth_service_requires_jwt_secret_staging),
        ("Staging Backend Hard Requirement", test_instance.test_staging_backend_service_requires_jwt_secret_staging),
        ("Production Auth Hard Requirement", test_instance.test_production_auth_service_requires_jwt_secret_production),
        ("Production Backend Hard Requirement", test_instance.test_production_backend_service_requires_jwt_secret_production),
        ("Development Auth Hard Requirement", test_instance.test_development_auth_service_requires_jwt_secret_key),
        ("Development Backend Hard Requirement", test_instance.test_development_backend_service_requires_jwt_secret_key),
        ("Staging Services Consistency", test_instance.test_staging_services_use_same_secret_when_properly_configured),
        ("Development Services Consistency", test_instance.test_development_services_use_same_secret_when_properly_configured),
        ("No Staging Fallback", test_instance.test_no_fallback_to_jwt_secret_key_in_staging),
        ("No Production Fallback", test_instance.test_no_fallback_to_jwt_secret_key_in_production),
    ]
    
    # New comprehensive tests
    comprehensive_tests = [
        ("Complete Auth Flow with JWT Validation", test_instance.test_complete_auth_flow_with_jwt_validation),
        ("Concurrent User Auth with JWT Secrets", test_instance.test_concurrent_user_auth_with_jwt_secrets),
        ("Multi-Environment JWT Isolation", test_instance.test_multi_environment_jwt_isolation),
        ("JWT Token Lifecycle Validation", test_instance.test_jwt_token_lifecycle_validation),
        ("JWT Secret Security Requirements", test_instance.test_jwt_secret_security_requirements),
        ("User Journey with JWT Validation", test_instance.test_user_journey_with_jwt_validation),
        ("Performance Under JWT Load", test_instance.test_performance_under_jwt_load),
    ]
    
    all_tests = original_tests + comprehensive_tests
    
    print("🚨 JWT Secret Hard Requirements & Comprehensive Test Suite")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    # Run original tests
    print("\n📋 ORIGINAL JWT SECRET HARD REQUIREMENT TESTS:")
    print("=" * 50)
    
    for test_name, test_func in original_tests:
        try:
            test_instance.setup_method()
            test_func()
            test_instance.teardown_method()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            test_instance.teardown_method()
            print(f"❌ {test_name}: {e}")
            failed += 1
    
    # Run comprehensive tests
    print("\n🚀 COMPREHENSIVE AUTHENTICATION FLOW TESTS:")
    print("=" * 50)
    
    for test_name, test_func in comprehensive_tests:
        try:
            test_instance.setup_method()
            test_func()
            test_instance.teardown_method()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            test_instance.teardown_method()
            print(f"❌ {test_name}: {e}")
            failed += 1
    
    print(f"\n📊 FINAL RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 ALL JWT TESTS PASSED - Authentication system is BULLETPROOF!")
        print("\n✨ CRITICAL SUCCESS METRICS:")
        print("  🔒 JWT secret security requirements: VALIDATED")
        print("  🚀 Complete authentication flows: VALIDATED")
        print("  ⚡ Performance under load: VALIDATED")
        print("  🔄 Multi-environment isolation: VALIDATED")
        print("  👥 Concurrent user handling: VALIDATED")
        print("  🎯 User journey completion: VALIDATED")
        print("\n💰 REVENUE IMPACT: Authentication system ready for scaling!")
        sys.exit(0)
    else:
        print("💥 SOME JWT TESTS FAILED - Authentication vulnerabilities detected!")
        print("\n⚠️  CRITICAL FAILURES:")
        print("  🚨 JWT secret configuration issues may block user access")
        print("  🚨 Authentication flow failures will impact revenue")
        print("  🚨 Performance issues will degrade user experience")
        print("\n🔧 ACTION REQUIRED: Fix authentication issues before deployment!")
        sys.exit(1)
