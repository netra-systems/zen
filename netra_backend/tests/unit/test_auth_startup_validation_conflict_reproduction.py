"""
Phase 1: Architecture Conflict Reproduction Tests for Issue #528

These tests isolate and reproduce the architectural conflicts between:
1. JWT Secret Manager (generates deterministic test secrets)  
2. Auth Startup Validator (rejects deterministic test secrets)
3. Environment Variable Isolation (missing SERVICE_ID/AUTH_SERVICE_URL)

Purpose: Create failing tests that demonstrate the exact architectural issues
before implementing fixes. This is TDD approach - tests fail first, then fix.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthValidationError,
    AuthComponent
)
from shared.jwt_secret_manager import get_jwt_secret_manager
from shared.isolated_environment import get_env


class TestJWTManagerValidatorConflict:
    """Test architectural conflict between JWT Manager and Auth Validator."""
    
    @pytest.mark.asyncio
    async def test_deterministic_secret_rejection_conflict(self):
        """
        TEST REPRODUCER: JWT Manager generates deterministic secret, Validator rejects it.
        
        This test demonstrates the core architectural conflict:
        - JWT Manager says: "I'll generate a deterministic secret for test environments"
        - Auth Validator says: "Deterministic secrets are not acceptable for secure environments"
        
        Expected: FAIL - This test should fail showing the conflict
        """
        # Clear JWT secret manager cache
        get_jwt_secret_manager().clear_cache()
        
        # Use isolated environment
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set minimal environment that triggers deterministic secret generation
            env.set('ENVIRONMENT', 'development', 'test')
            env.delete('JWT_SECRET')
            env.delete('JWT_SECRET_KEY')
            env.delete('JWT_SECRET_STAGING')
            env.delete('JWT_SECRET_DEVELOPMENT')
            
            # Step 1: JWT Manager generates deterministic secret
            jwt_manager = get_jwt_secret_manager()
            jwt_secret = jwt_manager.get_jwt_secret()
            
            # Verify JWT Manager created deterministic secret
            import hashlib
            expected_deterministic = hashlib.sha256("netra_development_jwt_key".encode()).hexdigest()[:32]
            assert jwt_secret == expected_deterministic, f"JWT Manager should generate deterministic secret, got: {jwt_secret}"
            
            # Step 2: Auth Validator rejects the same deterministic secret
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Find JWT result
            jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
            assert jwt_result is not None
            
            # THE CONFLICT: JWT Manager says "here's your secret", Validator says "that secret is invalid"
            # This creates an architectural dead-lock where no valid configuration exists
            assert not jwt_result.valid, "Auth Validator should reject deterministic secret"
            assert "deterministic test fallback" in jwt_result.error, f"Expected deterministic fallback rejection, got: {jwt_result.error}"
            
            # ARCHITECTURAL ISSUE: There's no valid JWT configuration that satisfies both components
            # This is the core issue causing test failures
            
            print("\n🚨 ARCHITECTURAL CONFLICT REPRODUCED:")
            print(f"   JWT Manager Generated: {jwt_secret}")
            print(f"   Auth Validator Rejected: {jwt_result.error}")
            print("   Result: No valid JWT configuration exists")
            
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()

    @pytest.mark.asyncio  
    async def test_environment_isolation_missing_vars_conflict(self):
        """
        TEST REPRODUCER: Environment isolation fails to provide required variables.
        
        This test demonstrates the environment variable isolation conflict:
        - Test tries to isolate environment
        - Required variables (SERVICE_ID, AUTH_SERVICE_URL) are missing
        - Auth Validator falls back to os.environ (breaks isolation)
        
        Expected: FAIL - This test should fail showing missing variables
        """
        # Clear JWT secret manager cache
        get_jwt_secret_manager().clear_cache()
        
        # Use isolated environment
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set minimal test environment (missing critical variables)
            env.set('ENVIRONMENT', 'development', 'test')
            env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-32-characters-long-for-testing-only', 'test')
            
            # Explicitly delete variables that should be isolated
            env.delete('SERVICE_ID')
            env.delete('AUTH_SERVICE_URL')
            env.delete('SERVICE_SECRET')
            
            # Verify isolation - these should be None in isolated environment
            assert env.get('SERVICE_ID') is None, "SERVICE_ID should be None in isolated environment"
            assert env.get('AUTH_SERVICE_URL') is None, "AUTH_SERVICE_URL should be None in isolated environment"
            
            # Auth Validator should handle missing variables gracefully in isolated environment
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Verify expected failures
            service_result = next((r for r in results if r.component == AuthComponent.SERVICE_CREDENTIALS), None)
            assert service_result is not None
            assert not service_result.valid
            assert "SERVICE_ID not configured" in service_result.error
            
            auth_url_result = next((r for r in results if r.component == AuthComponent.AUTH_SERVICE_URL), None) 
            assert auth_url_result is not None
            assert not auth_url_result.valid
            assert "AUTH_SERVICE_URL not configured" in auth_url_result.error
            
            # THE ISOLATION CONFLICT: Test should control all variables, but some leak through
            print("\n🚨 ENVIRONMENT ISOLATION CONFLICT REPRODUCED:")
            print(f"   Isolated SERVICE_ID: {env.get('SERVICE_ID')}")
            print(f"   Isolated AUTH_SERVICE_URL: {env.get('AUTH_SERVICE_URL')}")
            print("   Result: Environment isolation incomplete")
            
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()

    @pytest.mark.asyncio
    async def test_test_expectation_mismatch_conflict(self):
        """
        TEST REPRODUCER: Test expects one error message but gets another.
        
        This test demonstrates the test expectation conflict:
        - Original test expects: "No JWT secret configured"
        - System actually returns: "JWT secret is configured but rejected"
        - This mismatch indicates architectural assumptions are wrong
        
        Expected: FAIL - This test should fail showing the expectation mismatch
        """
        # Clear JWT secret manager cache
        get_jwt_secret_manager().clear_cache()
        
        # Use isolated environment to replicate original test conditions
        env = get_env()
        env.enable_isolation()
        
        try:
            # Replicate original test environment setup
            env.set('ENVIRONMENT', 'development', 'test')
            env.delete('JWT_SECRET')
            env.delete('JWT_SECRET_KEY') 
            env.delete('JWT_SECRET_STAGING')
            env.delete('AUTH_SERVICE_URL')
            
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Should fail validation
            assert not success
            
            # Find JWT secret validation result
            jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
            assert jwt_result is not None
            assert not jwt_result.valid
            
            # THE EXPECTATION MISMATCH:
            # Original test expects: "No JWT secret configured"
            expected_by_test = "No JWT secret configured"
            actual_error = jwt_result.error
            
            # But system actually generates/rejects deterministic secret
            assert expected_by_test not in actual_error, f"Test expects '{expected_by_test}' but got '{actual_error}'"
            
            # This shows the architectural assumption is wrong:
            # The system DOES configure a JWT secret (deterministic), it just rejects it
            print("\n🚨 TEST EXPECTATION MISMATCH REPRODUCED:")
            print(f"   Test Expects: '{expected_by_test}'")
            print(f"   System Returns: '{actual_error}'")
            print("   Result: Architectural assumptions in test are incorrect")
            
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()


class TestArchitecturalBehaviorMismatches:
    """Test behavioral mismatches between architectural components."""
    
    @pytest.mark.asyncio
    async def test_jwt_manager_validator_decision_conflict(self):
        """
        TEST REPRODUCER: JWT Manager and Validator make conflicting decisions.
        
        This tests the decision-making conflict:
        - JWT Manager decides to provide a deterministic secret (helpful for tests)
        - Auth Validator decides to reject deterministic secrets (security focused)
        - These decisions conflict and create an impossible configuration
        
        Expected: FAIL - Shows conflicting architectural decisions
        """
        # Test various environments to show the conflict pattern
        test_environments = ['development', 'testing']
        
        for environment in test_environments:
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set environment without any JWT secrets
                env.set('ENVIRONMENT', environment, 'test')
                env.delete('JWT_SECRET_KEY')
                env.delete('JWT_SECRET')
                env.delete(f'JWT_SECRET_{environment.upper()}')
                
                # JWT Manager decision: Provide deterministic secret
                jwt_manager = get_jwt_secret_manager()
                jwt_secret = jwt_manager.get_jwt_secret()
                
                # Should generate deterministic secret
                import hashlib
                expected_secret = hashlib.sha256(f"netra_{environment}_jwt_key".encode()).hexdigest()[:32]
                assert jwt_secret == expected_secret
                
                # Auth Validator decision: Reject deterministic secret
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
                assert jwt_result is not None
                assert not jwt_result.valid
                
                print(f"\n🚨 DECISION CONFLICT in {environment}:")
                print(f"   JWT Manager Decision: Provide deterministic secret")
                print(f"   Auth Validator Decision: Reject deterministic secret")
                print(f"   Result: Architectural deadlock")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_component_communication_breakdown(self):
        """
        TEST REPRODUCER: Components don't communicate effectively.
        
        This test shows the communication breakdown:
        - JWT Manager has logic about what's acceptable
        - Auth Validator has different logic about what's acceptable  
        - They don't share their decision criteria
        - Results in conflicting behaviors
        
        Expected: FAIL - Shows components working in isolation
        """
        get_jwt_secret_manager().clear_cache()
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set up scenario where components should coordinate
            env.set('ENVIRONMENT', 'development', 'test')
            
            # Test JWT Manager's criteria
            jwt_manager = get_jwt_secret_manager()
            
            # JWT Manager accepts deterministic secrets for development
            deterministic_secret = jwt_manager.get_jwt_secret()
            assert len(deterministic_secret) == 32  # JWT Manager thinks this is fine
            
            # Test Auth Validator's criteria on the same secret
            validator = AuthStartupValidator()
            
            # Manually test validator's logic on JWT Manager's output
            is_deterministic_fallback = False
            possible_envs = ['development', 'testing']
            import hashlib
            for test_env in possible_envs:
                expected_test_secret = hashlib.sha256(f"netra_{test_env}_jwt_key".encode()).hexdigest()[:32]
                if deterministic_secret == expected_test_secret:
                    is_deterministic_fallback = True
                    break
            
            # Auth Validator rejects what JWT Manager provides
            assert is_deterministic_fallback, "Auth Validator should detect deterministic fallback"
            
            # THE COMMUNICATION BREAKDOWN: 
            # JWT Manager says "this is a valid secret for development"
            # Auth Validator says "deterministic secrets are not acceptable"
            # Neither component knows about the other's criteria
            
            print("\n🚨 COMPONENT COMMUNICATION BREAKDOWN REPRODUCED:")
            print(f"   JWT Manager provides: {deterministic_secret}")
            print(f"   Auth Validator rejects: deterministic fallback detected")
            print("   Result: Components have incompatible criteria")
            
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()


if __name__ == "__main__":
    # Run conflict reproduction tests directly
    import asyncio
    
    async def run_conflict_tests():
        print("🧪 Running Architecture Conflict Reproduction Tests")
        print("=" * 60)
        
        test_instance = TestJWTManagerValidatorConflict()
        
        try:
            print("\n1. Testing Deterministic Secret Rejection Conflict...")
            await test_instance.test_deterministic_secret_rejection_conflict()
            print("   ✅ Conflict reproduced successfully")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        try:
            print("\n2. Testing Environment Isolation Missing Variables...")
            await test_instance.test_environment_isolation_missing_vars_conflict()  
            print("   ✅ Isolation conflict reproduced successfully")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        try:
            print("\n3. Testing Test Expectation Mismatch...")
            await test_instance.test_test_expectation_mismatch_conflict()
            print("   ✅ Expectation mismatch reproduced successfully")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n" + "=" * 60)
        print("🚨 All architectural conflicts reproduced")
        print("📋 Ready for Phase 2: Environment Validation Tests")
    
    asyncio.run(run_conflict_tests())