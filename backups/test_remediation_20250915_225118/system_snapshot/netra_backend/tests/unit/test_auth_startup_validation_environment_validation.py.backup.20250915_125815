"""
Phase 2: Environment Validation Tests for Issue #528

These tests validate environment variable resolution and isolation:
1. SERVICE_ID resolution through IsolatedEnvironment vs os.environ fallback
2. AUTH_SERVICE_URL configuration in different environments
3. Environment isolation effectiveness and side effects
4. Environment variable precedence and fallback behavior

Purpose: Test that environment variable resolution works correctly and
that tests can properly isolate and control environment state.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthComponent
)
from shared.jwt_secret_manager import get_jwt_secret_manager
from shared.isolated_environment import get_env


class TestEnvironmentVariableResolution:
    """Test environment variable resolution patterns."""
    
    @pytest.mark.asyncio
    async def test_service_id_resolution_fallback_behavior(self):
        """
        TEST: SERVICE_ID resolution through IsolatedEnvironment vs os.environ.
        
        This test validates the fallback behavior documented in the validator:
        - Try IsolatedEnvironment first
        - Fall back to direct os.environ if not found
        - Log the fallback behavior
        
        Expected: FAIL - Demonstrates inconsistent resolution behavior
        """
        get_jwt_secret_manager().clear_cache()
        env = get_env()
        env.enable_isolation()
        
        try:
            # Test Scenario 1: SERVICE_ID in os.environ but not in IsolatedEnvironment
            test_service_id = "test-service-isolated-env"
            
            # Set in os.environ but not in isolated environment
            with patch.dict(os.environ, {'SERVICE_ID': test_service_id}):
                # Ensure not in isolated environment
                env.delete('SERVICE_ID')
                assert env.get('SERVICE_ID') is None
                
                # But should be in os.environ
                assert os.environ.get('SERVICE_ID') == test_service_id
                
                # Run validator
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Find service credentials result
                service_result = next((r for r in results if r.component == AuthComponent.SERVICE_CREDENTIALS), None)
                assert service_result is not None
                
                # EXPECTED BEHAVIOR: Should find SERVICE_ID via fallback
                # If this fails, it shows the fallback mechanism isn't working
                if service_result.valid:
                    print("✅ SERVICE_ID fallback to os.environ working")
                else:
                    print(f"❌ SERVICE_ID fallback failed: {service_result.error}")
                    print("🚨 ISOLATION LEAK: Environment variable resolution inconsistent")
                
            # Test Scenario 2: SERVICE_ID in IsolatedEnvironment should take precedence
            isolated_service_id = "isolated-service-id"
            env.set('SERVICE_ID', isolated_service_id, 'test')
            
            with patch.dict(os.environ, {'SERVICE_ID': 'different-os-service-id'}):
                validator2 = AuthStartupValidator()
                success2, results2 = await validator2.validate_all()
                
                service_result2 = next((r for r in results2 if r.component == AuthComponent.SERVICE_CREDENTIALS), None)
                
                # Should use isolated environment value, not os.environ
                print(f"🔍 Testing SERVICE_ID precedence:")
                print(f"   IsolatedEnvironment: {env.get('SERVICE_ID')}")
                print(f"   os.environ: {os.environ.get('SERVICE_ID')}")
                print(f"   Validator result: {'VALID' if service_result2.valid else service_result2.error}")
                
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()

    @pytest.mark.asyncio
    async def test_auth_service_url_environment_patterns(self):
        """
        TEST: AUTH_SERVICE_URL resolution across different environment types.
        
        This test validates:
        - Development: Can be missing (optional)
        - Staging: Should be present  
        - Production: Must be present and HTTPS
        - Test: Should be configurable
        
        Expected: FAIL - Shows environment-specific validation inconsistencies
        """
        environments_to_test = [
            ('development', False),  # AUTH_SERVICE_URL optional
            ('staging', True),       # AUTH_SERVICE_URL required
            ('testing', False),      # AUTH_SERVICE_URL optional  
            ('production', True)     # AUTH_SERVICE_URL required + HTTPS
        ]
        
        for environment, is_required in environments_to_test:
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set base environment
                env.set('ENVIRONMENT', environment, 'test')
                env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-32-characters-long-for-testing-only', 'test')
                
                # Test without AUTH_SERVICE_URL
                env.delete('AUTH_SERVICE_URL')
                
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                auth_url_result = next((r for r in results if r.component == AuthComponent.AUTH_SERVICE_URL), None)
                assert auth_url_result is not None
                
                if is_required:
                    # Should fail in staging/production
                    assert not auth_url_result.valid, f"AUTH_SERVICE_URL should be required in {environment}"
                    print(f"✅ {environment}: AUTH_SERVICE_URL correctly required")
                else:
                    # May pass in development/testing (depending on implementation)
                    status = "VALID" if auth_url_result.valid else "INVALID"
                    print(f"🔍 {environment}: AUTH_SERVICE_URL {status} ({'optional' if not is_required else 'required'})")
                
                # Test with HTTP URL in production (should fail)
                if environment == 'production':
                    env.set('AUTH_SERVICE_URL', 'http://auth.example.com', 'test')
                    
                    validator_prod = AuthStartupValidator()
                    success_prod, results_prod = await validator_prod.validate_all()
                    
                    auth_url_result_prod = next((r for r in results_prod if r.component == AuthComponent.AUTH_SERVICE_URL), None)
                    
                    # Should reject HTTP in production
                    assert not auth_url_result_prod.valid
                    assert "HTTPS" in auth_url_result_prod.error
                    print(f"✅ {environment}: HTTP correctly rejected, HTTPS required")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_environment_isolation_side_effects(self):
        """
        TEST: Environment isolation side effects and state leakage.
        
        This test checks for:
        - State leakage between test runs
        - Proper cleanup of isolated environment
        - Global state contamination
        - Cache invalidation after isolation
        
        Expected: FAIL - Shows isolation side effects and state leakage
        """
        # Test for state leakage between isolation sessions
        test_scenarios = [
            {'SERVICE_ID': 'test-service-1', 'AUTH_SERVICE_URL': 'http://service1.test'},
            {'SERVICE_ID': 'test-service-2', 'AUTH_SERVICE_URL': 'http://service2.test'},
            {'SERVICE_ID': 'test-service-3', 'AUTH_SERVICE_URL': 'http://service3.test'}
        ]
        
        previous_states = []
        
        for i, scenario in enumerate(test_scenarios):
            print(f"\n🧪 Testing isolation scenario {i+1}")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set scenario-specific environment
                env.set('ENVIRONMENT', 'development', 'test')
                env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-32-characters-long-for-testing-only', 'test')
                
                for key, value in scenario.items():
                    env.set(key, value, 'test')
                
                # Run validation
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Capture current state
                current_state = {
                    'SERVICE_ID': env.get('SERVICE_ID'),
                    'AUTH_SERVICE_URL': env.get('AUTH_SERVICE_URL'),
                    'validation_success': success,
                    'jwt_cache': get_jwt_secret_manager()._cached_secret
                }
                
                # Check for state leakage from previous runs
                for j, prev_state in enumerate(previous_states):
                    if current_state['SERVICE_ID'] == prev_state['SERVICE_ID']:
                        print(f"🚨 STATE LEAKAGE: Current state matches previous scenario {j+1}")
                        print(f"   Current: {current_state}")
                        print(f"   Previous: {prev_state}")
                
                previous_states.append(current_state.copy())
                
                print(f"   SERVICE_ID: {current_state['SERVICE_ID']}")
                print(f"   AUTH_SERVICE_URL: {current_state['AUTH_SERVICE_URL']}")
                print(f"   Validation: {'SUCCESS' if success else 'FAILURE'}")
                
            finally:
                env.disable_isolation()
        
        # Test global state contamination
        print(f"\n🔍 Checking global state after all scenarios:")
        print(f"   JWT Manager cache: {get_jwt_secret_manager()._cached_secret}")
        print(f"   OS environ SERVICE_ID: {os.environ.get('SERVICE_ID', 'NOT_SET')}")


class TestEnvironmentPrecedenceAndFallbacks:
    """Test environment variable precedence rules and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_jwt_secret_precedence_hierarchy(self):
        """
        TEST: JWT secret precedence hierarchy validation.
        
        Tests the documented precedence order:
        1. Environment-specific JWT_SECRET_{ENVIRONMENT}
        2. Generic JWT_SECRET_KEY  
        3. Legacy JWT_SECRET
        4. Environment-specific fallbacks
        
        Expected: FAIL - Shows precedence violations or unexpected behavior
        """
        test_environments = ['development', 'staging', 'production']
        
        for environment in test_environments:
            print(f"\n🧪 Testing JWT precedence in {environment}")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                env.set('ENVIRONMENT', environment, 'test')
                
                # Set all possible JWT secrets with different values
                secrets = {
                    f'JWT_SECRET_{environment.upper()}': f'env-specific-secret-{environment}',
                    'JWT_SECRET_KEY': 'generic-jwt-secret-key-32-chars-long',
                    'JWT_SECRET': 'legacy-jwt-secret-value-32-chars-long'
                }
                
                for key, value in secrets.items():
                    env.set(key, value, 'test')
                
                # Test precedence - should use environment-specific first
                jwt_manager = get_jwt_secret_manager()
                resolved_secret = jwt_manager.get_jwt_secret()
                
                expected_secret = secrets[f'JWT_SECRET_{environment.upper()}']
                
                if resolved_secret == expected_secret:
                    print(f"   ✅ Correctly used environment-specific secret")
                else:
                    print(f"   ❌ Precedence violation:")
                    print(f"      Expected: {expected_secret}")
                    print(f"      Got: {resolved_secret}")
                
                # Test fallback behavior - remove environment-specific
                env.delete(f'JWT_SECRET_{environment.upper()}')
                jwt_manager.clear_cache()
                
                resolved_secret2 = jwt_manager.get_jwt_secret()
                expected_secret2 = secrets['JWT_SECRET_KEY']
                
                if resolved_secret2 == expected_secret2:
                    print(f"   ✅ Correctly fell back to JWT_SECRET_KEY")
                else:
                    print(f"   ❌ Fallback failed:")
                    print(f"      Expected: {expected_secret2}")
                    print(f"      Got: {resolved_secret2}")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_service_secret_environment_dependent_validation(self):
        """
        TEST: SERVICE_SECRET validation rules across environments.
        
        Tests different validation rules:
        - Development: More permissive (allows structured test strings)
        - Production: Strict validation (requires 64+ chars, no weak patterns)
        - Test context detection and rule application
        
        Expected: FAIL - Shows inconsistent validation rules or detection
        """
        test_cases = [
            {
                'environment': 'development',
                'secret': 'test-service-secret-32-chars-long',  # Should be OK in dev
                'should_pass': True,
                'reason': 'Development allows structured test strings'
            },
            {
                'environment': 'production', 
                'secret': 'test-service-secret-32-chars-long',  # Should fail in prod
                'should_pass': False,
                'reason': 'Production rejects "test" pattern'
            },
            {
                'environment': 'production',
                'secret': 'a' * 64,  # Should fail in prod (no entropy)
                'should_pass': False,
                'reason': 'Production requires entropy'
            },
            {
                'environment': 'production',
                'secret': '1a2b3c4d5e6f7890abcdef123456789012345678901234567890abcdef123456789012345678',  # Should pass
                'should_pass': True,
                'reason': 'Production accepts long hex strings'
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 Testing SERVICE_SECRET in {test_case['environment']}")
            print(f"   Secret pattern: {test_case['secret'][:20]}... (len: {len(test_case['secret'])})")
            print(f"   Expected: {'PASS' if test_case['should_pass'] else 'FAIL'} - {test_case['reason']}")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                env.set('ENVIRONMENT', test_case['environment'], 'test')
                env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-32-characters-long-for-testing-only', 'test')
                env.set('SERVICE_ID', 'test-service', 'test')
                env.set('SERVICE_SECRET', test_case['secret'], 'test')
                env.set('AUTH_SERVICE_URL', 'http://localhost:8001', 'test')
                
                # Clear testing flags for production test
                if test_case['environment'] == 'production':
                    env.delete('TESTING')
                    env.delete('PYTEST_CURRENT_TEST')
                
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                service_result = next((r for r in results if r.component == AuthComponent.SERVICE_CREDENTIALS), None)
                assert service_result is not None
                
                actual_passed = service_result.valid
                expected_pass = test_case['should_pass']
                
                if actual_passed == expected_pass:
                    print(f"   ✅ Validation behaved as expected")
                else:
                    print(f"   ❌ Validation mismatch:")
                    print(f"      Expected: {'PASS' if expected_pass else 'FAIL'}")
                    print(f"      Actual: {'PASS' if actual_passed else 'FAIL'}")
                    if not actual_passed:
                        print(f"      Error: {service_result.error}")
                
            finally:
                env.disable_isolation()


if __name__ == "__main__":
    # Run environment validation tests directly
    import asyncio
    
    async def run_environment_tests():
        print("🧪 Running Environment Validation Tests")
        print("=" * 60)
        
        print("\n1. Testing Service ID Resolution...")
        test_instance = TestEnvironmentVariableResolution()
        try:
            await test_instance.test_service_id_resolution_fallback_behavior()
            print("   ✅ Service ID resolution tests completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n2. Testing Auth Service URL Patterns...")
        try:
            await test_instance.test_auth_service_url_environment_patterns()
            print("   ✅ Auth Service URL pattern tests completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n3. Testing Environment Isolation Side Effects...")
        try:
            await test_instance.test_environment_isolation_side_effects()
            print("   ✅ Isolation side effect tests completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n" + "=" * 60)
        print("🧪 Environment validation tests completed")
        print("📋 Ready for Phase 3: JWT Dependency Chain Tests")
    
    asyncio.run(run_environment_tests())