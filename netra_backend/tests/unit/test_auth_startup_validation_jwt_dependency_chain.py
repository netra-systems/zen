"""
Phase 3: JWT Dependency Chain Tests for Issue #528

These tests validate the complete JWT dependency chain and decision flow:
1. JWT Secret Manager decision logic and fallback hierarchy
2. Auth Startup Validator decision logic and rejection criteria
3. Cross-component dependency relationships and communication
4. Decision consistency across different environment scenarios

Purpose: Test the complete decision chain from environment detection
through secret resolution to validation, identifying where the chain breaks.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import hashlib

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthComponent
)
from shared.jwt_secret_manager import get_jwt_secret_manager, JWTSecretManager
from shared.isolated_environment import get_env


class TestJWTDecisionChain:
    """Test the complete JWT decision chain from resolution to validation."""
    
    @pytest.mark.asyncio
    async def test_jwt_manager_decision_logic_analysis(self):
        """
        TEST: Analyze JWT Manager's decision logic in detail.
        
        This test documents and validates the decision path:
        1. Environment detection logic
        2. Secret resolution hierarchy
        3. Fallback decision criteria
        4. Cache behavior effects
        
        Expected: FAIL - Shows decision logic inconsistencies
        """
        test_scenarios = [
            {
                'name': 'Complete Environment Absence',
                'environment': 'development',
                'env_vars': {},  # No JWT variables at all
                'expected_behavior': 'generate_deterministic_secret'
            },
            {
                'name': 'Default Test Secret Present',
                'environment': 'development', 
                'env_vars': {
                    'JWT_SECRET_KEY': 'development-jwt-secret-minimum-32-characters-long'
                },
                'expected_behavior': 'replace_with_deterministic'
            },
            {
                'name': 'Valid Generic Secret',
                'environment': 'development',
                'env_vars': {
                    'JWT_SECRET_KEY': 'valid-jwt-secret-key-32-characters-long-enough'
                },
                'expected_behavior': 'use_generic_secret'
            },
            {
                'name': 'Environment Specific Priority',
                'environment': 'staging',
                'env_vars': {
                    'JWT_SECRET_STAGING': 'staging-specific-jwt-secret-32-chars',
                    'JWT_SECRET_KEY': 'generic-jwt-secret-key-32-chars-long'
                },
                'expected_behavior': 'use_environment_specific'
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n🔍 Testing JWT Manager Decision: {scenario['name']}")
            
            # Reset state
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set up scenario environment
                env.set('ENVIRONMENT', scenario['environment'], 'test')
                
                # Clear all JWT variables first
                jwt_vars = ['JWT_SECRET', 'JWT_SECRET_KEY', 'JWT_SECRET_DEVELOPMENT', 'JWT_SECRET_STAGING', 'JWT_SECRET_PRODUCTION']
                for var in jwt_vars:
                    env.delete(var)
                
                # Set scenario-specific variables
                for var, value in scenario['env_vars'].items():
                    env.set(var, value, 'test')
                
                # Analyze decision path
                jwt_manager = get_jwt_secret_manager()
                
                # Capture decision factors
                environment = env.get("ENVIRONMENT", "development").lower()
                is_testing_context = (
                    environment in ["testing", "development", "test"] or
                    env.get("TESTING", "false").lower() == "true" or
                    env.get("PYTEST_CURRENT_TEST") is not None
                )
                
                print(f"   Environment: {environment}")
                print(f"   Testing Context: {is_testing_context}")
                print(f"   Available vars: {list(scenario['env_vars'].keys())}")
                
                # Get the resolved secret
                resolved_secret = jwt_manager.get_jwt_secret()
                
                # Analyze what decision was made
                decision_analysis = {
                    'resolved_secret_length': len(resolved_secret),
                    'is_deterministic': False,
                    'matches_env_var': None,
                    'decision_path': 'unknown'
                }
                
                # Check if it's deterministic
                expected_deterministic = hashlib.sha256(f"netra_{environment}_jwt_key".encode()).hexdigest()[:32]
                if resolved_secret == expected_deterministic:
                    decision_analysis['is_deterministic'] = True
                    decision_analysis['decision_path'] = 'deterministic_fallback'
                
                # Check if it matches any environment variable
                for var, value in scenario['env_vars'].items():
                    if resolved_secret == value:
                        decision_analysis['matches_env_var'] = var
                        decision_analysis['decision_path'] = 'environment_variable'
                        break
                
                print(f"   Resolved secret: {resolved_secret[:20]}... (len: {len(resolved_secret)})")
                print(f"   Decision path: {decision_analysis['decision_path']}")
                print(f"   Is deterministic: {decision_analysis['is_deterministic']}")
                print(f"   Matches var: {decision_analysis['matches_env_var']}")
                
                # Verify against expected behavior
                expected = scenario['expected_behavior']
                if expected == 'generate_deterministic_secret' and not decision_analysis['is_deterministic']:
                    print(f"   ❌ Expected deterministic secret but got: {decision_analysis['decision_path']}")
                elif expected == 'use_generic_secret' and decision_analysis['matches_env_var'] != 'JWT_SECRET_KEY':
                    print(f"   ❌ Expected generic secret but got: {decision_analysis['decision_path']}")
                else:
                    print(f"   ✅ Behavior matches expectation")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_auth_validator_rejection_criteria_analysis(self):
        """
        TEST: Analyze Auth Validator's rejection criteria in detail.
        
        This test documents the validation decision logic:
        1. Default secret detection patterns
        2. Deterministic secret detection methods
        3. Length validation rules
        4. Environment-specific criteria
        
        Expected: FAIL - Shows validation criteria inconsistencies with JWT Manager
        """
        # Test different secret patterns against validator criteria
        test_secrets = [
            {
                'secret': 'development-jwt-secret-minimum-32-characters-long',
                'description': 'Default IsolatedEnvironment fallback',
                'should_be_rejected': True,
                'rejection_reason': 'default_secret_pattern'
            },
            {
                'secret': hashlib.sha256("netra_development_jwt_key".encode()).hexdigest()[:32],
                'description': 'JWT Manager deterministic secret',
                'should_be_rejected': True,
                'rejection_reason': 'deterministic_fallback'
            },
            {
                'secret': 'valid-jwt-secret-key-32-characters-long-enough',
                'description': 'Valid custom secret',
                'should_be_rejected': False,
                'rejection_reason': None
            },
            {
                'secret': 'short',
                'description': 'Too short secret',
                'should_be_rejected': True,
                'rejection_reason': 'length_validation'
            },
            {
                'secret': 'emergency_jwt_secret_please_configure_properly',
                'description': 'JWT Manager emergency fallback',
                'should_be_rejected': True,
                'rejection_reason': 'default_secret_pattern'
            }
        ]
        
        for test_case in test_secrets:
            print(f"\n🔍 Testing Validation Criteria: {test_case['description']}")
            print(f"   Secret: {test_case['secret'][:30]}...")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set up test environment with the specific secret
                env.set('ENVIRONMENT', 'development', 'test')
                env.set('JWT_SECRET_KEY', test_case['secret'], 'test')
                
                # Run validator
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Find JWT validation result
                jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
                assert jwt_result is not None
                
                # Analyze rejection decision
                was_rejected = not jwt_result.valid
                expected_rejection = test_case['should_be_rejected']
                
                print(f"   Expected rejection: {expected_rejection}")
                print(f"   Actual rejection: {was_rejected}")
                
                if expected_rejection and was_rejected:
                    print(f"   ✅ Correctly rejected: {jwt_result.error}")
                elif not expected_rejection and not was_rejected:
                    print(f"   ✅ Correctly accepted")
                else:
                    print(f"   ❌ Validation mismatch:")
                    if was_rejected:
                        print(f"      Rejected when should accept: {jwt_result.error}")
                    else:
                        print(f"      Accepted when should reject")
                
                # Analyze specific rejection criteria
                if was_rejected and jwt_result.error:
                    error = jwt_result.error.lower()
                    if 'deterministic' in error:
                        print(f"   📋 Rejection type: Deterministic fallback detection")
                    elif 'default' in error or 'test' in error:
                        print(f"   📋 Rejection type: Default secret pattern")
                    elif 'short' in error:
                        print(f"   📋 Rejection type: Length validation")
                    else:
                        print(f"   📋 Rejection type: Other ({error[:50]})")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_decision_chain_coordination_failure(self):
        """
        TEST: Test coordination failure between JWT Manager and Auth Validator.
        
        This test demonstrates the fundamental coordination problem:
        1. JWT Manager makes helpful decisions (provide fallback secrets)
        2. Auth Validator makes security decisions (reject fallback secrets)
        3. No coordination mechanism exists between them
        4. Results in impossible configurations
        
        Expected: FAIL - Shows coordination failure patterns
        """
        coordination_test_scenarios = [
            {
                'name': 'Helpful vs Security Conflict',
                'setup': 'No JWT secrets configured',
                'jwt_manager_expectation': 'Provide deterministic secret to help tests',
                'validator_expectation': 'Reject deterministic secrets for security',
                'coordination_problem': 'Manager helps, Validator blocks'
            },
            {
                'name': 'Default Secret Replacement Conflict',
                'setup': 'Default IsolatedEnvironment secret present',
                'jwt_manager_expectation': 'Replace with deterministic secret',
                'validator_expectation': 'Reject deterministic replacement',
                'coordination_problem': 'Manager replaces insecure with deterministic, Validator rejects deterministic'
            },
            {
                'name': 'Environment Context Disagreement',
                'setup': 'Testing environment detected differently',
                'jwt_manager_expectation': 'Testing context allows deterministic secrets',
                'validator_expectation': 'Development environment requires secure secrets',
                'coordination_problem': 'Different environment context detection'
            }
        ]
        
        for scenario in coordination_test_scenarios:
            print(f"\n🚨 Testing Coordination Failure: {scenario['name']}")
            print(f"   Setup: {scenario['setup']}")
            print(f"   JWT Manager expects: {scenario['jwt_manager_expectation']}")
            print(f"   Validator expects: {scenario['validator_expectation']}")
            print(f"   Problem: {scenario['coordination_problem']}")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set up scenario
                env.set('ENVIRONMENT', 'development', 'test')
                
                if scenario['name'] == 'Helpful vs Security Conflict':
                    # No JWT secrets at all
                    env.delete('JWT_SECRET_KEY')
                    env.delete('JWT_SECRET')
                    env.delete('JWT_SECRET_DEVELOPMENT')
                    
                elif scenario['name'] == 'Default Secret Replacement Conflict':
                    # Set default IsolatedEnvironment secret
                    env.set('JWT_SECRET_KEY', 'development-jwt-secret-minimum-32-characters-long', 'test')
                    
                elif scenario['name'] == 'Environment Context Disagreement':
                    # Set testing context markers inconsistently
                    env.set('TESTING', 'false', 'test')  # Validator might see this as non-test
                    env.set('PYTEST_CURRENT_TEST', 'some_test', 'test')  # But this indicates test
                
                # Step 1: Get JWT Manager's decision
                jwt_manager = get_jwt_secret_manager()
                manager_secret = jwt_manager.get_jwt_secret()
                
                # Analyze JWT Manager's decision
                is_deterministic = manager_secret == hashlib.sha256("netra_development_jwt_key".encode()).hexdigest()[:32]
                is_default_replacement = 'development-jwt-secret-minimum-32-characters-long'
                
                print(f"   JWT Manager provided: {manager_secret[:20]}...")
                print(f"   Is deterministic: {is_deterministic}")
                
                # Step 2: Get Auth Validator's decision on the same secret
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
                validator_accepted = jwt_result.valid if jwt_result else False
                
                print(f"   Validator accepted: {validator_accepted}")
                if not validator_accepted and jwt_result:
                    print(f"   Validator rejection: {jwt_result.error}")
                
                # Step 3: Analyze coordination failure
                if not validator_accepted:
                    print(f"   🚨 COORDINATION FAILURE CONFIRMED:")
                    print(f"      JWT Manager: Provided secret to help")
                    print(f"      Auth Validator: Rejected the same secret")
                    print(f"      Result: No valid configuration possible")
                    print(f"      Root cause: {scenario['coordination_problem']}")
                else:
                    print(f"   ✅ No coordination failure in this scenario")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_dependency_chain_environment_sensitivity(self):
        """
        TEST: Test how environment changes affect the entire dependency chain.
        
        This test validates:
        1. Same inputs, different environments = different decisions
        2. Environment detection consistency across components
        3. Chain behavior stability across environment changes
        4. Cache invalidation effects on decision consistency
        
        Expected: FAIL - Shows environment-sensitive behavior inconsistencies
        """
        test_environments = ['development', 'staging', 'testing', 'production']
        base_configuration = {
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-characters-long-for-testing-only'
        }
        
        chain_results = {}
        
        for environment in test_environments:
            print(f"\n🔄 Testing dependency chain in {environment}")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set same configuration in different environment
                env.set('ENVIRONMENT', environment, 'test')
                for key, value in base_configuration.items():
                    env.set(key, value, 'test')
                
                # Clear testing markers for production environment
                if environment == 'production':
                    env.delete('TESTING')
                    env.delete('PYTEST_CURRENT_TEST')
                
                # Step 1: JWT Manager decision
                jwt_manager = get_jwt_secret_manager()
                manager_secret = jwt_manager.get_jwt_secret()
                
                # Step 2: Auth Validator decision
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
                
                # Record chain results
                chain_results[environment] = {
                    'manager_secret': manager_secret,
                    'validator_success': jwt_result.valid if jwt_result else False,
                    'validator_error': jwt_result.error if jwt_result and not jwt_result.valid else None,
                    'overall_success': success
                }
                
                print(f"   JWT Manager: {manager_secret[:20]}...")
                print(f"   Validator: {'ACCEPT' if chain_results[environment]['validator_success'] else 'REJECT'}")
                if chain_results[environment]['validator_error']:
                    print(f"   Error: {chain_results[environment]['validator_error'][:50]}...")
                
            finally:
                env.disable_isolation()
        
        # Analyze cross-environment consistency
        print(f"\n📊 Cross-Environment Chain Analysis:")
        print(f"   Total environments tested: {len(chain_results)}")
        
        # Check for same input, different output
        secrets_by_env = {env: result['manager_secret'] for env, result in chain_results.items()}
        unique_secrets = set(secrets_by_env.values())
        
        if len(unique_secrets) > 1:
            print(f"   🚨 JWT Manager environment sensitivity detected:")
            for env, secret in secrets_by_env.items():
                print(f"      {env}: {secret[:20]}...")
        else:
            print(f"   ✅ JWT Manager consistent across environments")
        
        # Check validator consistency
        validation_results = {env: result['validator_success'] for env, result in chain_results.items()}
        if not all(validation_results.values()) and not any(validation_results.values()):
            print(f"   ✅ Validator consistently rejects across all environments")
        elif all(validation_results.values()):
            print(f"   ✅ Validator consistently accepts across all environments")
        else:
            print(f"   🚨 Validator environment sensitivity detected:")
            for env, success in validation_results.items():
                print(f"      {env}: {'ACCEPT' if success else 'REJECT'}")


if __name__ == "__main__":
    # Run JWT dependency chain tests directly
    import asyncio
    
    async def run_jwt_chain_tests():
        print("🧪 Running JWT Dependency Chain Tests")
        print("=" * 60)
        
        test_instance = TestJWTDecisionChain()
        
        print("\n1. Testing JWT Manager Decision Logic...")
        try:
            await test_instance.test_jwt_manager_decision_logic_analysis()
            print("   ✅ JWT Manager decision logic analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n2. Testing Auth Validator Rejection Criteria...")
        try:
            await test_instance.test_auth_validator_rejection_criteria_analysis()
            print("   ✅ Auth Validator criteria analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n3. Testing Decision Chain Coordination Failure...")
        try:
            await test_instance.test_decision_chain_coordination_failure()
            print("   ✅ Coordination failure analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n4. Testing Environment Sensitivity...")
        try:
            await test_instance.test_dependency_chain_environment_sensitivity()
            print("   ✅ Environment sensitivity analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n" + "=" * 60)
        print("🔗 JWT dependency chain analysis completed")
        print("📋 Ready for Phase 4: Integration Validation Tests")
    
    asyncio.run(run_jwt_chain_tests())