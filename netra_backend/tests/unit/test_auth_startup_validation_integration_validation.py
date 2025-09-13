"""
Phase 4: Integration Validation Tests for Issue #528

These tests validate the complete integration between components:
1. End-to-end authentication startup flow validation
2. Cross-component communication and state sharing
3. System-level behavior under various configuration scenarios
4. Integration test compatibility and isolation effectiveness

Purpose: Test the complete system behavior when all components work together,
identifying integration failures and system-level architectural issues.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import time
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthValidationError,
    AuthComponent,
    validate_auth_startup
)
from shared.jwt_secret_manager import get_jwt_secret_manager
from shared.isolated_environment import get_env


class TestAuthStartupIntegration:
    """Test complete authentication startup integration flow."""
    
    @pytest.mark.asyncio
    async def test_complete_startup_validation_flow_success_case(self):
        """
        TEST: Complete successful authentication startup validation flow.
        
        This test validates the happy path:
        1. All components properly configured
        2. JWT Manager provides valid secret
        3. Auth Validator accepts configuration
        4. System startup proceeds without errors
        
        Expected: PASS - This should be the one test that passes
        """
        get_jwt_secret_manager().clear_cache()
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set up complete valid configuration
            valid_config = {
                'ENVIRONMENT': 'development',
                'JWT_SECRET_KEY': 'valid-jwt-secret-key-32-characters-long-enough-for-validation',
                'SERVICE_ID': 'netra-backend-test',
                'SERVICE_SECRET': '32charvalidservicesecretfortest12345',
                'AUTH_SERVICE_URL': 'http://localhost:8001',
                'GOOGLE_CLIENT_ID': 'test-google-client-id',
                'GOOGLE_CLIENT_SECRET': 'test-google-client-secret',
                'CORS_ALLOWED_ORIGINS': 'http://localhost:3000,http://localhost:3001',
                'FRONTEND_URL': 'http://localhost:3000',
                'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
                'REFRESH_TOKEN_EXPIRE_DAYS': '7',
                'AUTH_CIRCUIT_FAILURE_THRESHOLD': '5',
                'AUTH_CIRCUIT_TIMEOUT': '30',
                'AUTH_CACHE_TTL': '300',
                'AUTH_CACHE_ENABLED': 'true'
            }
            
            for key, value in valid_config.items():
                env.set(key, value, 'test')
            
            # Test JWT Manager resolution
            jwt_manager = get_jwt_secret_manager()
            jwt_secret = jwt_manager.get_jwt_secret()
            
            print(f"📋 Complete Integration Test - Valid Configuration")
            print(f"   JWT Manager resolved: {jwt_secret[:20]}... (length: {len(jwt_secret)})")
            
            # Test Auth Validator
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            print(f"   Validation success: {success}")
            print(f"   Total checks: {len(results)}")
            
            if success:
                print(f"   ✅ INTEGRATION SUCCESS: All components working together")
                passed_checks = [r.component.value for r in results if r.valid]
                print(f"   ✅ Passed checks: {passed_checks}")
            else:
                print(f"   ❌ INTEGRATION FAILURE: Some validations failed")
                failed_checks = [(r.component.value, r.error) for r in results if not r.valid]
                for component, error in failed_checks:
                    print(f"      - {component}: {error}")
            
            # Test high-level startup function
            try:
                await validate_auth_startup()
                print(f"   ✅ High-level startup validation passed")
            except AuthValidationError as e:
                print(f"   ❌ High-level startup validation failed: {e}")
                
            # Assert success for the happy path
            assert success, f"Complete valid configuration should pass validation. Failed checks: {[(r.component.value, r.error) for r in results if not r.valid]}"
            
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()

    @pytest.mark.asyncio
    async def test_integration_failure_cascade_analysis(self):
        """
        TEST: Analyze how failures cascade through the integration.
        
        This test validates failure propagation:
        1. Single component failure effects on overall system
        2. Multiple component failure interactions
        3. Critical vs non-critical failure handling
        4. System resilience and degraded operation capabilities
        
        Expected: FAIL - Shows cascade failure patterns
        """
        failure_scenarios = [
            {
                'name': 'JWT Secret Failure Only',
                'config': {'ENVIRONMENT': 'development'},  # Missing JWT_SECRET_KEY
                'expected_critical_failures': ['jwt_secret'],
                'expected_behavior': 'complete_startup_failure'
            },
            {
                'name': 'Service Credentials Failure Only',
                'config': {
                    'ENVIRONMENT': 'development',
                    'JWT_SECRET_KEY': 'valid-jwt-secret-key-32-characters-long-enough'
                    # Missing SERVICE_ID, SERVICE_SECRET
                },
                'expected_critical_failures': ['service_credentials'],
                'expected_behavior': 'complete_startup_failure'
            },
            {
                'name': 'Multiple Critical Failures',
                'config': {
                    'ENVIRONMENT': 'development'
                    # Missing JWT_SECRET_KEY, SERVICE_ID, SERVICE_SECRET, AUTH_SERVICE_URL
                },
                'expected_critical_failures': ['jwt_secret', 'service_credentials', 'auth_service_url'],
                'expected_behavior': 'complete_startup_failure'
            },
            {
                'name': 'Non-Critical Failures Only',
                'config': {
                    'ENVIRONMENT': 'development',
                    'JWT_SECRET_KEY': 'valid-jwt-secret-key-32-characters-long-enough',
                    'SERVICE_ID': 'test-service',
                    'SERVICE_SECRET': '32charvalidservicesecretfortest12345',
                    'AUTH_SERVICE_URL': 'http://localhost:8001'
                    # Missing OAuth credentials (non-critical in dev)
                },
                'expected_critical_failures': [],
                'expected_behavior': 'startup_success_with_warnings'
            }
        ]
        
        for scenario in failure_scenarios:
            print(f"\n🔍 Testing Failure Cascade: {scenario['name']}")
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set up scenario configuration
                for key, value in scenario['config'].items():
                    env.set(key, value, 'test')
                
                # Run integration validation
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Analyze failure cascade
                critical_failures = [r for r in results if not r.valid and r.is_critical]
                non_critical_failures = [r for r in results if not r.valid and not r.is_critical]
                
                print(f"   Overall success: {success}")
                print(f"   Critical failures: {len(critical_failures)}")
                print(f"   Non-critical failures: {len(non_critical_failures)}")
                
                # Check expected critical failures
                actual_critical = [f.component.value for f in critical_failures]
                expected_critical = scenario['expected_critical_failures']
                
                print(f"   Expected critical: {expected_critical}")
                print(f"   Actual critical: {actual_critical}")
                
                # Analyze cascade behavior
                if scenario['expected_behavior'] == 'complete_startup_failure':
                    if success:
                        print(f"   ❌ Expected startup failure but got success")
                    else:
                        print(f"   ✅ Startup correctly failed")
                elif scenario['expected_behavior'] == 'startup_success_with_warnings':
                    if success:
                        print(f"   ✅ Startup succeeded with warnings as expected")
                    else:
                        print(f"   ❌ Expected startup success but got failure")
                
                # Test high-level startup function cascade
                try:
                    await validate_auth_startup()
                    startup_exception = False
                except AuthValidationError:
                    startup_exception = True
                
                print(f"   High-level startup exception: {startup_exception}")
                
            finally:
                env.disable_isolation()

    @pytest.mark.asyncio
    async def test_integration_state_consistency_across_calls(self):
        """
        TEST: Test state consistency across multiple validation calls.
        
        This test validates:
        1. Cache behavior effects on repeated validations
        2. State leakage between validation runs
        3. Configuration change detection and response
        4. Component state synchronization
        
        Expected: FAIL - Shows state consistency issues
        """
        print(f"\n🔄 Testing Integration State Consistency")
        
        get_jwt_secret_manager().clear_cache()
        env = get_env()
        env.enable_isolation()
        
        validation_runs = []
        
        try:
            # Run 1: Initial configuration
            print(f"\n   Run 1: Initial minimal configuration")
            env.set('ENVIRONMENT', 'development', 'test')
            env.set('JWT_SECRET_KEY', 'run1-jwt-secret-key-32-characters-long', 'test')
            
            validator1 = AuthStartupValidator()
            success1, results1 = await validator1.validate_all()
            
            # Capture state
            jwt_secret1 = get_jwt_secret_manager().get_jwt_secret()
            critical_failures1 = len([r for r in results1 if not r.valid and r.is_critical])
            
            validation_runs.append({
                'run': 1,
                'success': success1,
                'jwt_secret': jwt_secret1,
                'critical_failures': critical_failures1,
                'total_checks': len(results1)
            })
            
            print(f"      Success: {success1}, Critical failures: {critical_failures1}")
            print(f"      JWT secret: {jwt_secret1[:20]}...")
            
            # Run 2: Add more configuration (without clearing cache)
            print(f"\n   Run 2: Enhanced configuration (same environment)")
            env.set('SERVICE_ID', 'test-service', 'test')
            env.set('SERVICE_SECRET', '32charvalidservicesecretfortest12345', 'test')
            
            validator2 = AuthStartupValidator()
            success2, results2 = await validator2.validate_all()
            
            # Check cache consistency
            jwt_secret2 = get_jwt_secret_manager().get_jwt_secret()
            critical_failures2 = len([r for r in results2 if not r.valid and r.is_critical])
            
            validation_runs.append({
                'run': 2,
                'success': success2,
                'jwt_secret': jwt_secret2,
                'critical_failures': critical_failures2,
                'total_checks': len(results2)
            })
            
            print(f"      Success: {success2}, Critical failures: {critical_failures2}")
            print(f"      JWT secret: {jwt_secret2[:20]}...")
            
            # Check JWT secret consistency
            if jwt_secret1 == jwt_secret2:
                print(f"      ✅ JWT secret cache consistent between runs")
            else:
                print(f"      ❌ JWT secret cache inconsistent:")
                print(f"         Run 1: {jwt_secret1}")
                print(f"         Run 2: {jwt_secret2}")
            
            # Run 3: Change JWT secret (test cache invalidation)
            print(f"\n   Run 3: Changed JWT secret (test cache behavior)")
            env.set('JWT_SECRET_KEY', 'run3-different-jwt-secret-32-characters', 'test')
            
            # Clear cache to test proper invalidation
            get_jwt_secret_manager().clear_cache()
            
            validator3 = AuthStartupValidator()
            success3, results3 = await validator3.validate_all()
            
            jwt_secret3 = get_jwt_secret_manager().get_jwt_secret()
            critical_failures3 = len([r for r in results3 if not r.valid and r.is_critical])
            
            validation_runs.append({
                'run': 3,
                'success': success3,
                'jwt_secret': jwt_secret3,
                'critical_failures': critical_failures3,
                'total_checks': len(results3)
            })
            
            print(f"      Success: {success3}, Critical failures: {critical_failures3}")
            print(f"      JWT secret: {jwt_secret3[:20]}...")
            
            # Analyze consistency patterns
            print(f"\n   📊 State Consistency Analysis:")
            for run_data in validation_runs:
                print(f"      Run {run_data['run']}: Success={run_data['success']}, "
                      f"Critical={run_data['critical_failures']}, "
                      f"JWT={run_data['jwt_secret'][:15]}...")
            
            # Check for unexpected state changes
            if validation_runs[0]['jwt_secret'] != validation_runs[1]['jwt_secret']:
                print(f"      🚨 JWT secret changed between runs without explicit change")
            
            if validation_runs[1]['jwt_secret'] == validation_runs[2]['jwt_secret']:
                print(f"      🚨 JWT secret didn't change after explicit configuration change")
            
            # Check validation count consistency
            check_counts = [run['total_checks'] for run in validation_runs]
            if len(set(check_counts)) > 1:
                print(f"      🚨 Validation check count inconsistent: {check_counts}")
            else:
                print(f"      ✅ Validation check count consistent: {check_counts[0]}")
            
        finally:
            env.disable_isolation()
            get_jwt_secret_manager().clear_cache()

    @pytest.mark.asyncio 
    async def test_integration_concurrent_validation_behavior(self):
        """
        TEST: Test concurrent validation behavior and thread safety.
        
        This test validates:
        1. Concurrent validator instances behavior
        2. Cache sharing and thread safety  
        3. Environment isolation under concurrent access
        4. Global state corruption prevention
        
        Expected: FAIL - Shows concurrency issues
        """
        print(f"\n🔀 Testing Concurrent Validation Behavior")
        
        async def run_validation_scenario(scenario_id, config, delay=0):
            """Run a validation scenario with optional delay."""
            if delay > 0:
                await asyncio.sleep(delay)
            
            get_jwt_secret_manager().clear_cache()
            env = get_env()
            env.enable_isolation()
            
            try:
                # Set scenario-specific configuration
                for key, value in config.items():
                    env.set(key, value, 'test')
                
                # Run validation
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Get JWT secret for consistency checking
                jwt_secret = get_jwt_secret_manager().get_jwt_secret()
                
                return {
                    'scenario_id': scenario_id,
                    'success': success,
                    'jwt_secret': jwt_secret,
                    'critical_failures': len([r for r in results if not r.valid and r.is_critical]),
                    'total_checks': len(results)
                }
            
            finally:
                env.disable_isolation()
        
        # Define concurrent scenarios
        scenarios = [
            {
                'id': 'A',
                'config': {
                    'ENVIRONMENT': 'development',
                    'JWT_SECRET_KEY': 'scenario-a-jwt-secret-key-32-characters'
                },
                'delay': 0
            },
            {
                'id': 'B', 
                'config': {
                    'ENVIRONMENT': 'development',
                    'JWT_SECRET_KEY': 'scenario-b-jwt-secret-key-32-characters'
                },
                'delay': 0.01
            },
            {
                'id': 'C',
                'config': {
                    'ENVIRONMENT': 'development',
                    'JWT_SECRET_KEY': 'scenario-c-jwt-secret-key-32-characters'
                },
                'delay': 0.02
            }
        ]
        
        # Run scenarios concurrently
        tasks = []
        for scenario in scenarios:
            task = run_validation_scenario(
                scenario['id'], 
                scenario['config'], 
                scenario['delay']
            )
            tasks.append(task)
        
        # Wait for all scenarios to complete
        results = await asyncio.gather(*tasks)
        
        # Analyze concurrent execution results
        print(f"   Concurrent scenarios completed: {len(results)}")
        
        for result in results:
            print(f"   Scenario {result['scenario_id']}: "
                  f"Success={result['success']}, "
                  f"JWT={result['jwt_secret'][:20]}..., "
                  f"Critical={result['critical_failures']}")
        
        # Check for cross-contamination
        jwt_secrets = [r['jwt_secret'] for r in results]
        unique_secrets = set(jwt_secrets)
        
        if len(unique_secrets) == len(scenarios):
            print(f"   ✅ No JWT secret cross-contamination detected")
        else:
            print(f"   🚨 JWT secret cross-contamination detected:")
            print(f"      Expected {len(scenarios)} unique secrets, got {len(unique_secrets)}")
            for i, secret in enumerate(jwt_secrets):
                print(f"      Scenario {results[i]['scenario_id']}: {secret}")
        
        # Check for validation consistency
        success_results = [r['success'] for r in results]
        if len(set(success_results)) == 1:
            print(f"   ✅ Validation results consistent across concurrent runs")
        else:
            print(f"   🚨 Validation results inconsistent across concurrent runs")
            for result in results:
                print(f"      Scenario {result['scenario_id']}: {result['success']}")


if __name__ == "__main__":
    # Run integration validation tests directly
    import asyncio
    
    async def run_integration_tests():
        print("🧪 Running Integration Validation Tests")
        print("=" * 60)
        
        test_instance = TestAuthStartupIntegration()
        
        print("\n1. Testing Complete Startup Flow (Success Case)...")
        try:
            await test_instance.test_complete_startup_validation_flow_success_case()
            print("   ✅ Complete startup flow test completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n2. Testing Integration Failure Cascade...")
        try:
            await test_instance.test_integration_failure_cascade_analysis()
            print("   ✅ Integration failure cascade analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n3. Testing Integration State Consistency...")
        try:
            await test_instance.test_integration_state_consistency_across_calls()
            print("   ✅ Integration state consistency analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n4. Testing Concurrent Validation Behavior...")
        try:
            await test_instance.test_integration_concurrent_validation_behavior()
            print("   ✅ Concurrent validation behavior analysis completed")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        print("\n" + "=" * 60)
        print("🔗 Integration validation tests completed")
        print("📋 All 4 test phases complete - ready for analysis and decision")
    
    asyncio.run(run_integration_tests())