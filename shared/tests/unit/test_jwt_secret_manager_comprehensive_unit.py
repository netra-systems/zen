"""
ULTRA COMPREHENSIVE Unit Tests for JwtSecretManager - CRITICAL AUTHENTICATION SECURITY
Business Value Justification (BVJ):
- Segment: Platform/Internal - AUTHENTICATION SECURITY (CRITICAL)
- Business Goal: ZERO-FAILURE JWT authentication across ALL services and user sessions
- Value Impact: 100% authentication security - ALL user access depends on this SINGLE SOURCE OF TRUTH  
- Strategic Impact: Platform authentication exists or fails based on this module working correctly

CRITICAL MISSION: This is the THIRD MOST IMPORTANT module in the platform.
All JWT authentication, WebSocket connections, and user sessions depend on JwtSecretManager.
ANY bug in this class cascades to COMPLETE AUTHENTICATION FAILURE affecting 100% of users.

Testing Coverage Goals:
✓ 100% line coverage - Every single line must be tested
✓ 100% branch coverage - Every conditional path must be validated
✓ 100% business logic coverage - Every authentication security scenario must pass
✓ Performance critical paths - Secret access under heavy concurrent load
✓ Multi-environment security - Different environments use different secrets
✓ Secret rotation validation - Key rotation doesn't break active sessions
✓ Enterprise security compliance - Secrets meet strength requirements
✓ Cross-service consistency - Unified secret resolution prevents mismatch failures

ULTRA CRITICAL IMPORTANCE:
- JWT secret resolution MUST be consistent across all services
- Secret management MUST prevent the $50K MRR WebSocket 403 failures
- Environment-specific secrets MUST be properly isolated
- Secret strength MUST meet enterprise security requirements
- Secret caching MUST be thread-safe under heavy load
- Secret rotation MUST not interrupt active user sessions
- Legacy compatibility MUST maintain backward compatibility
- Singleton pattern MUST ensure consistency across service instances
- Error handling MUST fail securely without exposing secrets
- Performance MUST scale to enterprise authentication volumes
"""

import pytest
import os
import threading
import time
import tempfile
import concurrent.futures
import logging
import hashlib
from typing import Dict, List, Optional, Any, Set, Callable, Union
from unittest.mock import patch, Mock, MagicMock, call
from dataclasses import dataclass, field
import sys
import re
from pathlib import Path

# ABSOLUTE IMPORTS per SSOT requirements - CLAUDE.md compliance
from shared.jwt_secret_manager import (
    JWTSecretManager,
    get_jwt_secret_manager,
    get_unified_jwt_secret,
    get_unified_jwt_algorithm,
    validate_unified_jwt_config,
    SharedJWTSecretManager,
    _jwt_secret_manager
)
from shared.isolated_environment import get_env

# Set up logging for detailed test diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestJWTSecretManagerSingletonPattern:
    """Test singleton pattern for consistent JWT secret management - MISSION CRITICAL."""
    
    def test_singleton_consistency_across_access_patterns(self):
        """Test singleton maintains consistency across all access patterns."""
        # Clear any existing instance to start fresh
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
        
        # Get instance via all possible methods
        instance_direct = JWTSecretManager()
        instance_function = get_jwt_secret_manager()
        
        # Memory addresses MUST be identical
        memory_id = id(instance_function)
        assert id(instance_direct) != memory_id, "Direct instantiation should create different instance"
        assert id(instance_function) == memory_id, "Function should return singleton"
        
        # Subsequent calls should return same singleton
        instance_second = get_jwt_secret_manager()
        assert id(instance_second) == memory_id, "Subsequent calls should return same singleton"
        assert instance_function is instance_second, "Singleton identity must be maintained"
    
    def test_singleton_thread_safety_under_load(self):
        """Test singleton thread safety under concurrent authentication load."""
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
        
        instances = []
        exceptions = []
        
        def high_frequency_jwt_access():
            """Simulate high-frequency JWT operations."""
            try:
                for _ in range(50):  # High frequency authentication
                    manager = get_jwt_secret_manager()
                    secret = manager.get_jwt_secret()
                    algorithm = manager.get_jwt_algorithm()
                    
                    # Verify we got valid responses
                    assert secret is not None, "JWT secret should never be None"
                    assert algorithm is not None, "JWT algorithm should never be None"
                    assert len(secret) >= 8, "JWT secret should have minimum length"
                    
                    instances.append(manager)
                    
            except Exception as e:
                exceptions.append(f"Thread {threading.current_thread().name}: {str(e)}")
        
        # Create many threads for authentication concurrency simulation
        threads = []
        for i in range(15):  # High concurrency like production authentication load
            thread = threading.Thread(target=high_frequency_jwt_access, name=f"auth_{i}")
            threads.append(thread)
        
        start_time = time.time()
        
        # Start all simultaneously
        for thread in threads:
            thread.start()
        
        # Wait with timeout
        for thread in threads:
            thread.join(timeout=10.0)
            if thread.is_alive():
                raise AssertionError(f"Authentication thread {thread.name} timed out - possible deadlock")
        
        end_time = time.time()
        
        # HARD FAILURE CONDITIONS
        if exceptions:
            raise AssertionError(f"Authentication thread safety violations: {exceptions}")
        
        # Performance requirement - authentication should be fast
        elapsed = end_time - start_time
        if elapsed > 5.0:
            raise AssertionError(f"JWT authentication too slow under load: {elapsed:.2f}s")
        
        # Verify all instances are identical (singleton pattern)
        if instances:
            first_instance = instances[0]
            different_instances = [id(inst) for inst in instances if inst is not first_instance]
            if different_instances:
                raise AssertionError(f"Found {len(different_instances)} different JWT manager instances during authentication")
    
    def test_singleton_global_state_consistency(self):
        """Test global singleton state remains consistent across operations."""
        import shared.jwt_secret_manager as jwt_module
        
        # Start fresh
        jwt_module._jwt_secret_manager = None
        
        # Get manager and configure
        manager1 = get_jwt_secret_manager()
        manager1._cached_secret = "test_cached_secret"
        manager1._cached_algorithm = "RS256"
        
        # Get another reference
        manager2 = get_jwt_secret_manager()
        
        # Should be same instance with same cached values
        assert manager1 is manager2, "Singleton instances must be identical"
        assert manager2._cached_secret == "test_cached_secret", "Cached secret not consistent"
        assert manager2._cached_algorithm == "RS256", "Cached algorithm not consistent"
        
        # Clear cache via one reference
        manager1.clear_cache()
        
        # Should be cleared in both references (same object)
        assert manager2._cached_secret is None, "Cache not cleared consistently"
        assert manager2._cached_algorithm is None, "Algorithm cache not cleared consistently"


class TestJWTSecretManagerSecretResolution:
    """Test JWT secret resolution logic - AUTHENTICATION SECURITY CRITICAL."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton to ensure fresh state
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_environment_specific_secret_priority(self):
        """Test environment-specific JWT secrets have highest priority."""
        # Set environment to staging
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Set multiple JWT secret options
        self.env.set("JWT_SECRET_STAGING", "staging-specific-secret", "test")
        self.env.set("JWT_SECRET_KEY", "generic-secret", "test")
        self.env.set("JWT_SECRET", "legacy-secret", "test")
        
        manager = get_jwt_secret_manager()
        secret = manager.get_jwt_secret()
        
        # Should use environment-specific secret (highest priority)
        assert secret == "staging-specific-secret", "Environment-specific secret should have highest priority"
    
    def test_generic_jwt_secret_key_fallback(self):
        """Test generic JWT_SECRET_KEY fallback when environment-specific not available."""
        self.env.set("ENVIRONMENT", "production", "test")
        
        # Only set generic key (no environment-specific)
        self.env.set("JWT_SECRET_KEY", "generic-production-secret", "test")
        self.env.set("JWT_SECRET", "legacy-secret", "test")  # Should not be used
        
        manager = get_jwt_secret_manager()
        secret = manager.get_jwt_secret()
        
        # Should use generic JWT_SECRET_KEY
        assert secret == "generic-production-secret", "Should fallback to JWT_SECRET_KEY"
    
    def test_development_deterministic_secret_generation(self):
        """Test deterministic secret generation for development environments."""
        # Test environments that should generate deterministic secrets
        test_environments = ["development", "testing", "test"]
        
        for env_name in test_environments:
            # Clear previous state
            self.env.clear()
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            self.env.set("ENVIRONMENT", env_name, "test")
            
            # No explicit JWT secrets set
            secret = manager.get_jwt_secret()
            
            # Should generate deterministic secret
            expected_secret = hashlib.sha256(f"netra_{env_name}_jwt_key".encode()).hexdigest()[:32]
            assert secret == expected_secret, f"Deterministic secret incorrect for {env_name}, got: {secret}, expected: {expected_secret}"
            
            # Should be consistent across calls
            secret2 = manager.get_jwt_secret()
            assert secret2 == secret, f"Deterministic secret not consistent for {env_name}"
    
    def test_staging_production_hard_failure_requirements(self):
        """Test staging/production environments require proper JWT configuration."""
        critical_environments = ["staging", "production"]
        
        for env_name in critical_environments:
            # Clear state
            self.env.clear()
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            self.env.set("ENVIRONMENT", env_name, "test")
            
            # No JWT secrets configured - should raise ValueError
            with pytest.raises(ValueError, match=f"JWT secret not configured for {env_name} environment"):
                manager.get_jwt_secret()
            
            # Error should mention business impact
            with pytest.raises(ValueError, match="50K MRR WebSocket functionality"):
                manager.get_jwt_secret()
    
    def test_unknown_environment_emergency_fallback(self):
        """Test emergency fallback for unknown environments."""
        self.env.clear()
        self.env.set("ENVIRONMENT", "unknown_environment", "test")
        
        manager = get_jwt_secret_manager()
        manager.clear_cache()
        secret = manager.get_jwt_secret()
        
        # Should use emergency fallback
        assert secret == "emergency_jwt_secret_please_configure_properly", f"Unknown environment should use emergency fallback, got: {secret}"
    
    def test_import_error_fallback_resilience(self):
        """Test resilience to import errors in environment access."""
        manager = get_jwt_secret_manager()
        
        # Mock import error in get_env
        with patch.object(manager, '_get_env', side_effect=ImportError("Mock import error")):
            secret = manager.get_jwt_secret()
            
            # Should use emergency fallback
            assert secret == "fallback_jwt_secret_for_emergency_only", "Import error should trigger fallback"
    
    def test_secret_caching_behavior(self):
        """Test JWT secret caching for performance."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "cacheable-secret", "test")
        
        manager = get_jwt_secret_manager()
        
        # First call should cache secret
        secret1 = manager.get_jwt_secret()
        assert secret1 == "cacheable-secret", "First call should return correct secret"
        assert manager._cached_secret == "cacheable-secret", "Secret should be cached"
        
        # Second call should use cache (test by removing env var)
        self.env.delete("JWT_SECRET_KEY", "test")
        secret2 = manager.get_jwt_secret()
        
        # Should still return cached value
        assert secret2 == "cacheable-secret", "Should use cached secret"
        
        # Clear cache and try again
        manager.clear_cache()
        secret3 = manager.get_jwt_secret()
        
        # Should fall back to test defaults now
        expected_test_secret = hashlib.sha256("netra_test_jwt_key".encode()).hexdigest()[:32]
        assert secret3 == expected_test_secret, "Should use test defaults after cache clear"
    
    def test_secret_whitespace_stripping(self):
        """Test JWT secrets are properly stripped of whitespace."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "  whitespace-padded-secret  \n\t", "test")
        
        manager = get_jwt_secret_manager()
        secret = manager.get_jwt_secret()
        
        # Should be stripped
        assert secret == "whitespace-padded-secret", "Secret should be stripped of whitespace"


class TestJWTSecretManagerAlgorithmManagement:
    """Test JWT algorithm management functionality."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_explicit_algorithm_configuration(self):
        """Test explicit JWT algorithm configuration takes priority."""
        self.env.set("JWT_ALGORITHM", "RS256", "test")
        self.env.set("ENVIRONMENT", "production", "test")
        
        manager = get_jwt_secret_manager()
        algorithm = manager.get_jwt_algorithm()
        
        assert algorithm == "RS256", "Explicit algorithm configuration should be used"
    
    def test_production_algorithm_defaults(self):
        """Test production environment algorithm defaults."""
        self.env.set("ENVIRONMENT", "production", "test")
        # No explicit JWT_ALGORITHM set
        
        manager = get_jwt_secret_manager()
        algorithm = manager.get_jwt_algorithm()
        
        assert algorithm == "HS256", "Production should default to HS256"
    
    def test_staging_algorithm_defaults(self):
        """Test staging environment uses production-like defaults."""
        self.env.set("ENVIRONMENT", "staging", "test")
        # No explicit JWT_ALGORITHM set
        
        manager = get_jwt_secret_manager()
        algorithm = manager.get_jwt_algorithm()
        
        assert algorithm == "HS256", "Staging should use production-like HS256"
    
    def test_development_algorithm_defaults(self):
        """Test development environments use standard algorithm."""
        test_environments = ["development", "test", "local"]
        
        for env_name in test_environments:
            self.env.set("ENVIRONMENT", env_name, "test")
            
            manager = get_jwt_secret_manager()
            manager.clear_cache()  # Clear algorithm cache
            algorithm = manager.get_jwt_algorithm()
            
            assert algorithm == "HS256", f"Development environment {env_name} should default to HS256"
    
    def test_algorithm_caching_behavior(self):
        """Test JWT algorithm caching for performance."""
        self.env.set("JWT_ALGORITHM", "RS384", "test")
        
        manager = get_jwt_secret_manager()
        
        # First call should cache algorithm
        alg1 = manager.get_jwt_algorithm()
        assert alg1 == "RS384", "First call should return correct algorithm"
        assert manager._cached_algorithm == "RS384", "Algorithm should be cached"
        
        # Second call should use cache
        self.env.delete("JWT_ALGORITHM", "test")
        alg2 = manager.get_jwt_algorithm()
        
        # Should still return cached value
        assert alg2 == "RS384", "Should use cached algorithm"
        
        # Clear cache and try again
        manager.clear_cache()
        alg3 = manager.get_jwt_algorithm()
        
        # Should use default now
        assert alg3 == "HS256", "Should use default after cache clear"


class TestJWTSecretManagerValidation:
    """Test JWT configuration validation functionality - SECURITY COMPLIANCE."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_valid_configuration_validation(self):
        """Test validation of valid JWT configuration."""
        # Set up valid configuration
        self.env.set("ENVIRONMENT", "staging", "test")
        self.env.set("JWT_SECRET_STAGING", "secure-staging-jwt-secret-with-32-chars", "test")
        self.env.set("JWT_ALGORITHM", "HS256", "test")
        
        manager = get_jwt_secret_manager()
        result = manager.validate_jwt_configuration()
        
        assert result["valid"] is True, "Valid configuration should pass validation"
        assert len(result["issues"]) == 0, f"Valid configuration should have no issues: {result['issues']}"
        assert result["environment"] == "staging", "Environment should be correctly identified"
        assert result["info"]["secret_length"] >= 32, "Secret length should meet requirements"
        assert result["info"]["algorithm"] == "HS256", "Algorithm should be correctly identified"
    
    def test_short_secret_warning(self):
        """Test warning for short JWT secrets."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "short", "test")
        
        manager = get_jwt_secret_manager()
        result = manager.validate_jwt_configuration()
        
        assert result["valid"] is True, "Short secret should still be valid"
        assert len(result["warnings"]) > 0, "Short secret should generate warning"
        
        warning_text = " ".join(result["warnings"]).lower()
        assert "only 5 characters" in warning_text, "Warning should mention actual length"
        assert "recommend 32+" in warning_text, "Warning should recommend minimum length"
    
    def test_emergency_fallback_detection(self):
        """Test detection of emergency fallback secrets."""
        self.env.clear()
        self.env.set("ENVIRONMENT", "unknown_env", "test")
        
        manager = get_jwt_secret_manager()
        manager.clear_cache()
        result = manager.validate_jwt_configuration()
        
        assert result["valid"] is False, f"Emergency fallback should be invalid, got: {result}"
        assert len(result["issues"]) > 0, f"Emergency fallback should generate issues, got: {result['issues']}"
        
        issues_text = " ".join(result["issues"]).lower()
        assert "emergency fallback" in issues_text, f"Should detect emergency fallback usage, got: {issues_text}"
    
    def test_staging_production_environment_validation(self):
        """Test validation requirements for staging/production environments."""
        critical_environments = ["staging", "production"]
        
        for env_name in critical_environments:
            self.env.clear()
            self.env.set("ENVIRONMENT", env_name, "test")
            # No JWT secrets configured
            
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            # For staging/production without config, get_jwt_secret should raise ValueError
            # Validation should detect this
            result = manager.validate_jwt_configuration()
            
            # The validation should fail because JWT secret resolution failed
            assert result["valid"] is False, f"{env_name} without JWT config should be invalid, got: {result}"
            assert len(result["issues"]) > 0, f"{env_name} should generate configuration issues, got: {result['issues']}"
            
            issues_text = " ".join(result["issues"]).lower()
            assert "jwt secret resolution failed" in issues_text, f"Should detect JWT resolution failure for {env_name}, got: {issues_text}"
    
    def test_unusual_algorithm_warning(self):
        """Test warning for unusual JWT algorithms."""
        self.env.set("ENVIRONMENT", "test", "test") 
        self.env.set("JWT_SECRET_KEY", "test-secret-with-32-characters-long", "test")
        self.env.set("JWT_ALGORITHM", "ES256", "test")  # Unusual algorithm
        
        manager = get_jwt_secret_manager()
        result = manager.validate_jwt_configuration()
        
        assert result["valid"] is True, "Unusual algorithm should still be valid"
        assert len(result["warnings"]) > 0, "Unusual algorithm should generate warning"
        
        warnings_text = " ".join(result["warnings"]).lower()
        assert "unusual jwt algorithm: es256" in warnings_text, "Should warn about unusual algorithm"
    
    def test_validation_error_handling(self):
        """Test validation handles errors gracefully."""
        manager = get_jwt_secret_manager()
        
        # Mock get_jwt_secret to raise exception
        with patch.object(manager, 'get_jwt_secret', side_effect=Exception("Mock secret error")):
            result = manager.validate_jwt_configuration()
            
            assert result["valid"] is False, "Exception should make validation invalid"
            assert len(result["issues"]) > 0, "Exception should generate issues"
            
            issues_text = " ".join(result["issues"]).lower()
            assert "jwt secret resolution failed" in issues_text, "Should report secret resolution failure"
            assert result["info"]["error"] == "Mock secret error", "Should include error details"
        
        # Mock get_jwt_algorithm to raise exception
        with patch.object(manager, 'get_jwt_algorithm', side_effect=Exception("Mock algorithm error")):
            result = manager.validate_jwt_configuration()
            
            assert result["valid"] is False, "Algorithm exception should make validation invalid"
            assert len(result["issues"]) > 0, "Algorithm exception should generate issues"
            
            issues_text = " ".join(result["issues"]).lower()
            assert "jwt algorithm resolution failed" in issues_text, "Should report algorithm resolution failure"


class TestJWTSecretManagerDebugAndDiagnostics:
    """Test debug and diagnostic functionality."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_debug_info_comprehensive(self):
        """Test comprehensive debug information generation."""
        # Set up test environment
        self.env.set("ENVIRONMENT", "staging", "test")
        self.env.set("JWT_SECRET_STAGING", "staging-secret", "test")
        self.env.set("JWT_SECRET_KEY", "generic-secret", "test")
        self.env.set("JWT_ALGORITHM", "RS256", "test")
        
        manager = get_jwt_secret_manager()
        debug_info = manager.get_debug_info()
        
        # Verify all debug information is present
        assert debug_info["environment"] == "staging", "Environment should be correctly identified"
        assert debug_info["environment_specific_key"] == "JWT_SECRET_STAGING", "Environment-specific key should be correct"
        assert debug_info["has_env_specific"] is True, "Should detect environment-specific secret"
        assert debug_info["has_generic_key"] is True, "Should detect generic key"
        assert debug_info["algorithm"] == "RS256", "Algorithm should be included"
        
        # Verify available keys list
        available_keys = debug_info["available_keys"]
        assert "JWT_SECRET_STAGING" in available_keys, "Environment-specific key should be in available keys"
        assert "JWT_SECRET_KEY" in available_keys, "Generic key should be in available keys"
    
    def test_debug_info_security_no_secret_exposure(self):
        """Test debug info never exposes actual secrets."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "super-secret-jwt-key", "test")
        
        manager = get_jwt_secret_manager()
        debug_info = manager.get_debug_info()
        
        # Debug info should never contain actual secrets
        debug_str = str(debug_info)
        assert "super-secret-jwt-key" not in debug_str, "Debug info must not expose actual secrets"
        
        # Should only contain boolean indicators
        assert debug_info["has_generic_key"] is True, "Should indicate presence without exposing value"
    
    def test_debug_info_missing_configuration(self):
        """Test debug info when configuration is missing."""
        self.env.clear()
        self.env.set("ENVIRONMENT", "production", "test")
        # No JWT secrets configured
        
        manager = get_jwt_secret_manager()
        manager.clear_cache()
        debug_info = manager.get_debug_info()
        
        assert debug_info["environment"] == "production", "Environment should be detected"
        assert debug_info["has_env_specific"] is False, "Should detect missing environment-specific secret"
        assert debug_info["has_generic_key"] is False, "Should detect missing generic key"
        assert debug_info["has_legacy_key"] is False, "Should detect missing legacy key"
        assert len(debug_info["available_keys"]) == 0, "Available keys should be empty"
    
    def test_cache_clearing_functionality(self):
        """Test cache clearing works correctly."""
        self.env.set("JWT_SECRET_KEY", "test-secret", "test")
        self.env.set("JWT_ALGORITHM", "HS384", "test")
        
        manager = get_jwt_secret_manager()
        
        # Populate cache
        secret = manager.get_jwt_secret()
        algorithm = manager.get_jwt_algorithm()
        
        assert manager._cached_secret == "test-secret", "Secret should be cached"
        assert manager._cached_algorithm == "HS384", "Algorithm should be cached"
        
        # Clear cache
        manager.clear_cache()
        
        assert manager._cached_secret is None, "Secret cache should be cleared"
        assert manager._cached_algorithm is None, "Algorithm cache should be cleared"
        
        # Should work normally after cache clear
        secret2 = manager.get_jwt_secret()
        algorithm2 = manager.get_jwt_algorithm()
        
        assert secret2 == "test-secret", "Should work normally after cache clear"
        assert algorithm2 == "HS384", "Should work normally after cache clear"


class TestJWTSecretManagerPerformanceAndScalability:
    """Test performance and scalability under enterprise authentication loads."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Set up performance test configuration
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "performance-test-jwt-secret-32chars", "test")
        self.env.set("JWT_ALGORITHM", "HS256", "test")
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_high_frequency_secret_access_performance(self):
        """Test high-frequency JWT secret access performance."""
        manager = get_jwt_secret_manager()
        
        # Warm up cache
        manager.get_jwt_secret()
        manager.get_jwt_algorithm()
        
        num_operations = 10000
        start_time = time.time()
        
        # Perform high-frequency access
        for _ in range(num_operations):
            secret = manager.get_jwt_secret()
            algorithm = manager.get_jwt_algorithm()
            
            # Verify results
            assert secret == "performance-test-jwt-secret-32chars", "Secret should be consistent"
            assert algorithm == "HS256", "Algorithm should be consistent"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance requirements
        ops_per_second = (num_operations * 2) / total_time  # 2 operations per iteration
        assert ops_per_second > 10000, f"JWT access too slow: {ops_per_second:.2f} ops/sec (need >10K)"
        assert total_time < 2.0, f"High-frequency access took too long: {total_time:.2f}s"
    
    def test_concurrent_authentication_simulation(self):
        """Test concurrent authentication loads simulating production traffic."""
        manager = get_jwt_secret_manager()
        
        results = {"secrets": [], "algorithms": [], "errors": []}
        
        def authenticate_user(user_id: int):
            """Simulate user authentication process."""
            try:
                for request in range(20):  # 20 auth requests per user
                    # Simulate JWT operations during authentication
                    secret = manager.get_jwt_secret()
                    algorithm = manager.get_jwt_algorithm()
                    
                    # Verify authentication security
                    assert secret is not None, f"User {user_id} got None secret"
                    assert algorithm is not None, f"User {user_id} got None algorithm"
                    assert len(secret) >= 8, f"User {user_id} got weak secret"
                    
                    results["secrets"].append(secret)
                    results["algorithms"].append(algorithm)
                    
            except Exception as e:
                results["errors"].append(f"User {user_id}: {str(e)}")
        
        # Simulate 50 concurrent users authenticating
        num_users = 50
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(authenticate_user, user_id) for user_id in range(num_users)]
            
            # Wait for all authentications to complete
            for future in concurrent.futures.as_completed(futures, timeout=15.0):
                try:
                    future.result()
                except Exception as e:
                    results["errors"].append(f"Future error: {str(e)}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify no errors
        assert len(results["errors"]) == 0, f"Authentication errors: {results['errors']}"
        
        # Verify all operations completed
        expected_operations = num_users * 20
        assert len(results["secrets"]) == expected_operations, f"Expected {expected_operations} secret operations"
        assert len(results["algorithms"]) == expected_operations, f"Expected {expected_operations} algorithm operations"
        
        # Verify consistency
        unique_secrets = set(results["secrets"])
        unique_algorithms = set(results["algorithms"])
        assert len(unique_secrets) == 1, "All secrets should be identical"
        assert len(unique_algorithms) == 1, "All algorithms should be identical"
        
        # Performance requirements
        total_operations = len(results["secrets"]) + len(results["algorithms"])
        ops_per_second = total_operations / total_time
        assert ops_per_second > 1000, f"Concurrent authentication too slow: {ops_per_second:.2f} ops/sec"
    
    def test_memory_usage_under_load(self):
        """Test memory usage remains stable under authentication load."""
        manager = get_jwt_secret_manager()
        
        # Get baseline memory usage
        initial_objects = len(gc.get_objects())
        
        # Perform many operations that could cause memory leaks
        for cycle in range(100):
            # Clear and repopulate cache multiple times
            manager.clear_cache()
            
            for _ in range(50):
                secret = manager.get_jwt_secret()
                algorithm = manager.get_jwt_algorithm()
                debug_info = manager.get_debug_info()
                validation = manager.validate_jwt_configuration()
        
        # Check memory usage after operations
        gc.collect()  # Force garbage collection
        final_objects = len(gc.get_objects())
        
        # Memory should not grow significantly
        memory_growth = final_objects - initial_objects
        assert memory_growth < 1000, f"Potential memory leak: {memory_growth} new objects"


class TestJWTSecretManagerConvenienceFunctions:
    """Test convenience functions and global access patterns."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_get_unified_jwt_secret_function(self):
        """Test get_unified_jwt_secret convenience function."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "unified-secret-function-test", "test")
        
        # Test convenience function
        secret = get_unified_jwt_secret()
        
        assert secret == "unified-secret-function-test", "Convenience function should return correct secret"
        
        # Should be consistent with manager method
        manager = get_jwt_secret_manager()
        manager_secret = manager.get_jwt_secret()
        
        assert secret == manager_secret, "Convenience function should match manager method"
    
    def test_get_unified_jwt_algorithm_function(self):
        """Test get_unified_jwt_algorithm convenience function."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_ALGORITHM", "RS384", "test")
        
        # Test convenience function
        algorithm = get_unified_jwt_algorithm()
        
        assert algorithm == "RS384", "Convenience function should return correct algorithm"
        
        # Should be consistent with manager method
        manager = get_jwt_secret_manager()
        manager_algorithm = manager.get_jwt_algorithm()
        
        assert algorithm == manager_algorithm, "Convenience function should match manager method"
    
    def test_validate_unified_jwt_config_function(self):
        """Test validate_unified_jwt_config convenience function."""
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "validation-test-secret-32-chars", "test")
        
        # Test convenience function
        result = validate_unified_jwt_config()
        
        assert isinstance(result, dict), "Convenience function should return dict"
        assert "valid" in result, "Result should have valid field"
        assert result["valid"] is True, "Should validate successfully"
        
        # Should be consistent with manager method
        manager = get_jwt_secret_manager()
        manager_result = manager.validate_jwt_configuration()
        
        assert result["valid"] == manager_result["valid"], "Convenience function should match manager method"
    
    def test_convenience_functions_singleton_consistency(self):
        """Test convenience functions use same singleton instance."""
        self.env.set("JWT_SECRET_KEY", "singleton-consistency-test", "test")
        self.env.set("JWT_ALGORITHM", "HS512", "test")
        
        # Get manager directly
        manager = get_jwt_secret_manager()
        
        # Use convenience functions
        secret = get_unified_jwt_secret()
        algorithm = get_unified_jwt_algorithm()
        
        # Should have populated same cache
        assert manager._cached_secret == secret, "Convenience function should use same cache"
        assert manager._cached_algorithm == algorithm, "Convenience function should use same cache"


class TestLegacyCompatibilitySharedJWTSecretManager:
    """Test legacy compatibility through SharedJWTSecretManager class."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_legacy_get_jwt_secret_redirect(self):
        """Test legacy get_jwt_secret redirects to unified manager."""
        self.env.set("JWT_SECRET_KEY", "legacy-compatibility-secret", "test")
        
        # Test legacy interface
        legacy_secret = SharedJWTSecretManager.get_jwt_secret()
        
        # Should redirect to unified manager
        unified_secret = get_unified_jwt_secret()
        
        assert legacy_secret == unified_secret, "Legacy method should redirect to unified manager"
        assert legacy_secret == "legacy-compatibility-secret", "Legacy method should return correct secret"
    
    def test_legacy_get_service_secret(self):
        """Test legacy get_service_secret functionality."""
        # Test with explicit SERVICE_SECRET
        self.env.set("SERVICE_SECRET", "explicit-service-secret", "test")
        
        service_secret = SharedJWTSecretManager.get_service_secret()
        assert service_secret == "explicit-service-secret", "Should use explicit SERVICE_SECRET"
        
        # Test with default fallback
        self.env.delete("SERVICE_SECRET", "test")
        
        service_secret = SharedJWTSecretManager.get_service_secret()
        assert service_secret == "test-secret-for-local-development-only-32chars", "Should use default service secret"
    
    def test_legacy_validate_jwt_secret(self):
        """Test legacy JWT secret validation."""
        # Test valid secrets
        valid_secrets = [
            "12345678901234567890123456789012",  # Exactly 32 chars
            "123456789012345678901234567890123",  # More than 32 chars
            "a" * 50  # Much longer
        ]
        
        for secret in valid_secrets:
            result = SharedJWTSecretManager.validate_jwt_secret(secret)
            assert result is True, f"Secret '{secret}' should be valid (length: {len(secret)})"
        
        # Test invalid secrets
        invalid_secrets = [
            None,
            "",
            "short",
            "12345678901234567890123456789",  # Only 29 chars
            "1234567890123456789012345678901"  # Only 31 chars
        ]
        
        for secret in invalid_secrets:
            result = SharedJWTSecretManager.validate_jwt_secret(secret)
            assert result is False, f"Secret '{secret}' should be invalid"
    
    def test_legacy_clear_cache_redirect(self):
        """Test legacy clear_cache redirects to unified manager."""
        self.env.set("JWT_SECRET_KEY", "cache-test-secret", "test")
        
        # Populate cache via unified manager
        manager = get_jwt_secret_manager()
        manager.get_jwt_secret()
        
        assert manager._cached_secret == "cache-test-secret", "Cache should be populated"
        
        # Clear cache via legacy interface
        SharedJWTSecretManager.clear_cache()
        
        assert manager._cached_secret is None, "Legacy clear_cache should affect unified manager"


class TestJWTSecretManagerErrorHandling:
    """Test comprehensive error handling and edge cases."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_environment_access_error_handling(self):
        """Test error handling when environment access fails."""
        manager = get_jwt_secret_manager()
        manager.clear_cache()
        
        # Mock environment access to raise ImportError (which is handled)
        with patch.object(manager, '_get_env', side_effect=ImportError("Environment access error")):
            secret = manager.get_jwt_secret()
            
            # Should fallback gracefully to ImportError handler
            assert secret == "fallback_jwt_secret_for_emergency_only", "Should use emergency fallback on environment error"
    
    def test_invalid_environment_value_handling(self):
        """Test handling of invalid environment values."""
        invalid_environments = ["", "   "]
        
        for invalid_env in invalid_environments:
            self.env.clear()
            
            # Mock environment to return invalid value
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default=None: invalid_env if key == "ENVIRONMENT" else default
            
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            with patch.object(manager, '_get_env', return_value=mock_env):
                secret = manager.get_jwt_secret()
                
                # Should handle gracefully - empty string becomes "development" after lower()
                expected_secret = hashlib.sha256("netra_development_jwt_key".encode()).hexdigest()[:32]
                assert secret == expected_secret, f"Invalid environment '{invalid_env}' should use development defaults, got: {secret}"
    
    def test_partial_environment_corruption(self):
        """Test handling when environment is partially corrupted."""
        # Set up partially corrupted environment
        self.env.clear()
        self.env.set("ENVIRONMENT", "staging", "test")
        # Don't set JWT_SECRET_STAGING at all (missing, not None)
        
        manager = get_jwt_secret_manager()
        manager.clear_cache()
        
        # Should handle missing values gracefully by raising ValueError for staging
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            manager.get_jwt_secret()
    
    def test_extremely_long_secret_handling(self):
        """Test handling of extremely long JWT secrets."""
        # Create very long secret (simulating misconfiguration)
        very_long_secret = "x" * 10000
        self.env.set("JWT_SECRET_KEY", very_long_secret, "test")
        
        manager = get_jwt_secret_manager()
        secret = manager.get_jwt_secret()
        
        # Should handle without error and preserve full secret
        assert secret == very_long_secret, "Should preserve extremely long secrets"
        assert len(secret) == 10000, "Length should be preserved"
    
    def test_unicode_and_special_character_secrets(self):
        """Test handling of Unicode and special characters in secrets."""
        special_secrets = [
            "jwt-secret-with-dashes-and-underscores_123",
            "jwt.secret.with.dots.456",
            "jwt@secret#with$symbols%789",
            "jwt_秘密_secret",  # Unicode
            "jwt🔐secret🗝️key",  # Emoji
            "jwt secret with spaces",
            "jwt\tsecret\twith\ttabs",
        ]
        
        for special_secret in special_secrets:
            self.env.clear()
            self.env.set("JWT_SECRET_KEY", special_secret, "test")
            
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            secret = manager.get_jwt_secret()
            
            # Should preserve special characters (after stripping and sanitization)
            if "\\t" in special_secret or "\t" in special_secret:
                # Control characters are sanitized out
                expected = special_secret.replace("\t", "").strip()
            else:
                expected = special_secret.strip()
            assert secret == expected, f"Special secret not preserved: '{special_secret}', got: '{secret}', expected: '{expected}'"
    
    def test_logging_error_resilience(self):
        """Test resilience to logging errors."""
        manager = get_jwt_secret_manager()
        
        # Mock logger to raise exception
        with patch('shared.jwt_secret_manager.logger') as mock_logger:
            mock_logger.info.side_effect = Exception("Logging error")
            mock_logger.warning.side_effect = Exception("Logging error")
            mock_logger.error.side_effect = Exception("Logging error")
            mock_logger.critical.side_effect = Exception("Logging error")
            
            # Should still work despite logging errors
            try:
                secret = manager.get_jwt_secret()
                algorithm = manager.get_jwt_algorithm()
                
                # Operations should succeed
                assert secret is not None, "Should work despite logging errors"
                assert algorithm is not None, "Should work despite logging errors"
                
            except Exception as e:
                # Should not raise exceptions due to logging failures
                pytest.fail(f"Operations should not fail due to logging errors: {e}")


class TestJWTSecretManagerMultiEnvironmentSecurity:
    """Test multi-environment security and isolation requirements."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.reset()
        self.env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.reset()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
    
    def test_environment_isolation_prevents_secret_leakage(self):
        """Test environment isolation prevents secret leakage between environments."""
        environment_secrets = {
            "development": ("JWT_SECRET_DEVELOPMENT", "dev-secret-12345"),
            "testing": ("JWT_SECRET_TESTING", "test-secret-67890"),
            "staging": ("JWT_SECRET_STAGING", "staging-secret-abcdef"),
            "production": ("JWT_SECRET_PRODUCTION", "prod-secret-xyz789")
        }
        
        # Test each environment in isolation
        for env_name, (env_key, env_secret) in environment_secrets.items():
            # Clear all environment state
            self.env.clear()
            
            # Set up specific environment
            self.env.set("ENVIRONMENT", env_name, "test")
            self.env.set(env_key, env_secret, "test")
            
            # Add secrets for other environments to test isolation
            for other_env, (other_key, other_secret) in environment_secrets.items():
                if other_env != env_name:
                    self.env.set(other_key, other_secret, "test")
            
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            secret = manager.get_jwt_secret()
            
            # Should use environment-specific secret only
            assert secret == env_secret, f"Environment {env_name} should use its specific secret"
            
            # Should not use secrets from other environments
            for other_env, (other_key, other_secret) in environment_secrets.items():
                if other_env != env_name:
                    assert secret != other_secret, f"Environment {env_name} should not use {other_env} secret"
    
    def test_production_staging_security_requirements(self):
        """Test production and staging environments enforce security requirements."""
        critical_environments = ["staging", "production"]
        
        for env_name in critical_environments:
            self.env.clear()
            self.env.set("ENVIRONMENT", env_name, "test")
            
            # Test various insecure configurations
            insecure_configs = [
                # No secrets at all
                {},
                # Only legacy secret (should require environment-specific)
                {"JWT_SECRET": "legacy-secret"},
                # Generic secret without environment-specific
                {"JWT_SECRET_KEY": "generic-secret"}
            ]
            
            for config in insecure_configs:
                # Clear and apply insecure config
                self.env.clear()
                self.env.set("ENVIRONMENT", env_name, "test")
                
                for key, value in config.items():
                    self.env.set(key, value, "test")
                
                manager = get_jwt_secret_manager()
                manager.clear_cache()
                
                # Should require proper configuration
                with pytest.raises(ValueError, match=f"JWT secret not configured for {env_name} environment"):
                    manager.get_jwt_secret()
    
    def test_development_test_environment_defaults_security(self):
        """Test development/test environments use secure defaults."""
        dev_environments = ["development", "test", "testing"]
        
        for env_name in dev_environments:
            self.env.clear()
            self.env.set("ENVIRONMENT", env_name, "test")
            
            manager = get_jwt_secret_manager()
            manager.clear_cache()
            
            secret = manager.get_jwt_secret()
            
            # Should generate deterministic secret
            expected_secret = hashlib.sha256(f"netra_{env_name}_jwt_key".encode()).hexdigest()[:32]
            assert secret == expected_secret, f"Development environment {env_name} should use deterministic secret"
            
            # Secret should be sufficiently long and complex
            assert len(secret) == 32, "Development secret should be 32 characters"
            assert secret.isalnum(), "Development secret should be alphanumeric"
            
            # Should be consistent across calls
            secret2 = manager.get_jwt_secret()
            assert secret2 == secret, "Development secret should be consistent"
    
    def test_cross_service_secret_consistency(self):
        """Test JWT secrets are consistent across service instances."""
        # Simulate multiple service instances accessing JWT secrets
        service_instances = []
        
        # Set up consistent environment
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "cross-service-consistency-test", "test")
        
        # Create multiple manager instances (simulating different services)
        for i in range(10):
            import shared.jwt_secret_manager as jwt_module
            jwt_module._jwt_secret_manager = None  # Reset singleton
            
            manager = get_jwt_secret_manager()
            secret = manager.get_jwt_secret()
            algorithm = manager.get_jwt_algorithm()
            
            service_instances.append({
                "manager": manager,
                "secret": secret,
                "algorithm": algorithm
            })
        
        # All instances should return identical secrets
        secrets = [instance["secret"] for instance in service_instances]
        algorithms = [instance["algorithm"] for instance in service_instances]
        
        assert all(s == secrets[0] for s in secrets), "All service instances should return identical secrets"
        assert all(a == algorithms[0] for a in algorithms), "All service instances should return identical algorithms"
        
        # All managers should be the same singleton
        managers = [instance["manager"] for instance in service_instances]
        assert all(m is managers[0] for m in managers), "All service instances should use same singleton manager"


# Import gc for memory tests
import gc


class TestJWTSecretManagerComprehensiveFinalValidation:
    """Final comprehensive validation of all JWT secret management functionality."""
    
    def test_complete_authentication_workflow_simulation(self):
        """Simulate complete authentication workflow using JwtSecretManager."""
        # Clear state
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Clear singleton
        import shared.jwt_secret_manager as jwt_module
        jwt_module._jwt_secret_manager = None
        
        try:
            # Simulate production-like authentication setup
            env.set("ENVIRONMENT", "staging", "test")
            env.set("JWT_SECRET_STAGING", "ultra-secure-staging-jwt-secret-for-authentication", "test")
            env.set("JWT_ALGORITHM", "HS256", "test")
            
            # Simulate service startup - JWT manager initialization
            manager = get_jwt_secret_manager()
            
            # Simulate user authentication requests
            authentication_results = []
            
            for user_id in range(100):  # 100 user authentications
                # Each authentication needs JWT secret and algorithm
                secret = manager.get_jwt_secret()
                algorithm = manager.get_jwt_algorithm()
                
                # Validate authentication security requirements
                assert secret is not None, f"User {user_id} authentication failed - no JWT secret"
                assert len(secret) >= 32, f"User {user_id} authentication failed - weak JWT secret"
                assert algorithm in ["HS256", "HS384", "HS512", "RS256"], f"User {user_id} authentication failed - invalid algorithm"
                
                authentication_results.append({
                    "user_id": user_id,
                    "secret": secret,
                    "algorithm": algorithm,
                    "secret_length": len(secret)
                })
            
            # Verify all authentications used consistent secrets
            unique_secrets = set(result["secret"] for result in authentication_results)
            unique_algorithms = set(result["algorithm"] for result in authentication_results)
            
            assert len(unique_secrets) == 1, "All authentications must use same JWT secret"
            assert len(unique_algorithms) == 1, "All authentications must use same JWT algorithm"
            
            # Verify secret meets enterprise security requirements
            secret = authentication_results[0]["secret"]
            assert secret == "ultra-secure-staging-jwt-secret-for-authentication", "Secret should match configuration"
            
            # Simulate configuration validation for security compliance
            validation_result = manager.validate_jwt_configuration()
            assert validation_result["valid"] is True, f"Authentication configuration should be valid: {validation_result}"
            assert len(validation_result["issues"]) == 0, f"No security issues allowed: {validation_result['issues']}"
            
            # Simulate debug diagnostics for production monitoring
            debug_info = manager.get_debug_info()
            assert debug_info["environment"] == "staging", "Debug info should show correct environment"
            assert debug_info["has_env_specific"] is True, "Debug info should show environment-specific config"
            
            # Simulate WebSocket authentication (high-frequency access)
            websocket_authentications = 0
            start_time = time.time()
            
            for _ in range(1000):  # High-frequency WebSocket auth
                secret = manager.get_jwt_secret()
                if secret == "ultra-secure-staging-jwt-secret-for-authentication":
                    websocket_authentications += 1
            
            end_time = time.time()
            websocket_time = end_time - start_time
            
            assert websocket_authentications == 1000, "All WebSocket authentications should succeed"
            assert websocket_time < 1.0, f"WebSocket authentication too slow: {websocket_time:.2f}s"
            
            # Simulate service shutdown and cleanup
            manager.clear_cache()
            
            # Verify functionality still works after cache clear
            post_cleanup_secret = manager.get_jwt_secret()
            assert post_cleanup_secret == "ultra-secure-staging-jwt-secret-for-authentication", "Should work after cleanup"
            
            print(f"✅ AUTHENTICATION WORKFLOW SUCCESS: 100 user authentications + 1000 WebSocket authentications completed in {websocket_time:.3f}s")
            
        finally:
            env.reset()
            # Clear singleton
            jwt_module._jwt_secret_manager = None


if __name__ == "__main__":
    # Allow running tests directly for debugging
    pytest.main([__file__, "-v", "--tb=short", "-x"])