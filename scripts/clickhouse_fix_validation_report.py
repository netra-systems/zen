#!/usr/bin/env python3
"""
ClickHouse Logging Fix Validation Report
Demonstrates that the fix for GitHub Issue #134 is working correctly.
"""

import os
import sys
from typing import Dict, Any

# Add the project root to path for imports
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

def test_fix_implementation():
    """Validate the actual fix implementation in the code."""
    print("=== IMPLEMENTATION VALIDATION ===")
    
    try:
        # Force environment refresh to ensure settings are picked up
        from shared.isolated_environment import get_env
        env = get_env()
        
        from netra_backend.app.db.clickhouse import _handle_connection_error
        print("✅ Successfully imported _handle_connection_error function")
        
        # Test the fix logic by examining the function behavior
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['CLICKHOUSE_REQUIRED'] = 'false'
        
        # Verify environment is set correctly
        print(f"Debug: ENVIRONMENT = {env.get('ENVIRONMENT')}")
        print(f"Debug: CLICKHOUSE_REQUIRED = {env.get('CLICKHOUSE_REQUIRED')}")
        
        # Create test exception
        test_exception = ConnectionRefusedError("Test connection failure")
        
        # Test optional service behavior (should not raise)
        try:
            _handle_connection_error(test_exception)
            exception_raised = False
            print("✅ Optional service does NOT raise exception (graceful degradation)")
        except Exception as e:
            exception_raised = True
            print(f"❌ Optional service raised exception: {e}")
            return False
        
        # Test required service behavior (should raise)
        os.environ['CLICKHOUSE_REQUIRED'] = 'true'
        print(f"Debug: After setting true, CLICKHOUSE_REQUIRED = {env.get('CLICKHOUSE_REQUIRED')}")
        
        try:
            _handle_connection_error(test_exception)
            print("❌ Required service should raise exception but didn't")
            return False
        except Exception as e:
            print("✅ Required service correctly raises exception for fail-fast behavior")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return False


def analyze_code_changes():
    """Analyze the actual code changes made to fix the issue."""
    print("\n=== CODE CHANGE ANALYSIS ===")
    
    try:
        with open('/Users/anthony/Desktop/netra-apex/netra_backend/app/db/clickhouse.py', 'r') as f:
            content = f.read()
        
        # Check for the critical fix lines
        fix_indicators = [
            'CLICKHOUSE_REQUIRED',
            'clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED"',
            'if not clickhouse_required:',
            'logger.warning',
            'analytics features disabled',
            'return  # Never raise when ClickHouse is not required'
        ]
        
        found_indicators = []
        for indicator in fix_indicators:
            if indicator in content:
                found_indicators.append(indicator)
                print(f"✅ Found fix indicator: {indicator}")
            else:
                print(f"❌ Missing fix indicator: {indicator}")
        
        # Check the specific fix location
        if '_handle_connection_error' in content:
            print("✅ Found _handle_connection_error function")
            
            # Extract the function
            start_idx = content.find('def _handle_connection_error')
            if start_idx != -1:
                # Find the end of the function (next function or class)
                next_def = content.find('\ndef ', start_idx + 1)
                next_class = content.find('\nclass ', start_idx + 1)
                
                end_idx = min([idx for idx in [next_def, next_class, len(content)] if idx > start_idx])
                function_code = content[start_idx:end_idx]
                
                # Check for the critical fix pattern
                critical_patterns = [
                    'clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED"',
                    'if not clickhouse_required:',
                    'return  # Never raise when ClickHouse is not required'
                ]
                
                all_patterns_found = True
                for pattern in critical_patterns:
                    if pattern in function_code:
                        print(f"✅ Found critical fix pattern: {pattern}")
                    else:
                        print(f"❌ Missing critical fix pattern: {pattern}")
                        all_patterns_found = False
                
                return all_patterns_found
        
        return len(found_indicators) >= 4
        
    except Exception as e:
        print(f"❌ Error analyzing code: {e}")
        return False


def validate_environment_behavior():
    """Validate environment-specific behavior."""
    print("\n=== ENVIRONMENT BEHAVIOR VALIDATION ===")
    
    # Test scenarios
    scenarios = [
        {
            'name': 'Staging Optional',
            'env': {'ENVIRONMENT': 'staging', 'CLICKHOUSE_REQUIRED': 'false'},
            'expected': 'graceful_degradation'
        },
        {
            'name': 'Production Required',
            'env': {'ENVIRONMENT': 'production', 'CLICKHOUSE_REQUIRED': 'true'},
            'expected': 'fail_fast'
        },
        {
            'name': 'Development Default',
            'env': {'ENVIRONMENT': 'development'},  # No CLICKHOUSE_REQUIRED
            'expected': 'graceful_degradation'  # Should default to optional
        },
        {
            'name': 'Staging Required',
            'env': {'ENVIRONMENT': 'staging', 'CLICKHOUSE_REQUIRED': 'true'},
            'expected': 'fail_fast'
        }
    ]
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        print(f"\n--- Testing {scenario['name']} ---")
        
        # Set environment
        for key, value in scenario['env'].items():
            os.environ[key] = value
        
        # Clear CLICKHOUSE_REQUIRED if not specified (for default testing)
        if 'CLICKHOUSE_REQUIRED' not in scenario['env']:
            if 'CLICKHOUSE_REQUIRED' in os.environ:
                del os.environ['CLICKHOUSE_REQUIRED']
        
        try:
            from netra_backend.app.db.clickhouse import _handle_connection_error
            test_exception = ConnectionRefusedError(f"Test for {scenario['name']}")
            
            try:
                _handle_connection_error(test_exception)
                actual_behavior = 'graceful_degradation'
            except Exception:
                actual_behavior = 'fail_fast'
            
            if actual_behavior == scenario['expected']:
                print(f"✅ {scenario['name']}: Expected {scenario['expected']}, got {actual_behavior}")
                passed += 1
            else:
                print(f"❌ {scenario['name']}: Expected {scenario['expected']}, got {actual_behavior}")
                failed += 1
                
        except Exception as e:
            print(f"❌ {scenario['name']}: Error during test: {e}")
            failed += 1
    
    print(f"\nEnvironment Behavior Results: {passed} passed, {failed} failed")
    return failed == 0


def check_backward_compatibility():
    """Check that the fix doesn't break existing required service behavior."""
    print("\n=== BACKWARD COMPATIBILITY VALIDATION ===")
    
    # Test that production environments still fail fast when ClickHouse is truly required
    production_scenarios = [
        ('production', 'true', 'should_fail'),
        ('staging', 'true', 'should_fail'),  # Explicitly required in staging
    ]
    
    for env, required, expected in production_scenarios:
        os.environ['ENVIRONMENT'] = env
        os.environ['CLICKHOUSE_REQUIRED'] = required
        
        try:
            from netra_backend.app.db.clickhouse import _handle_connection_error
            test_exception = ConnectionRefusedError(f"Production test for {env}")
            
            try:
                _handle_connection_error(test_exception)
                result = 'no_exception'
            except Exception:
                result = 'exception_raised'
            
            if expected == 'should_fail' and result == 'exception_raised':
                print(f"✅ {env} with REQUIRED=true correctly raises exception (backward compatibility maintained)")
            elif expected == 'should_fail' and result == 'no_exception':
                print(f"❌ {env} with REQUIRED=true should raise exception but didn't (backward compatibility broken)")
                return False
            
        except Exception as e:
            print(f"❌ Error testing {env}: {e}")
            return False
    
    print("✅ Backward compatibility maintained - required services still fail fast")
    return True


def generate_stability_report():
    """Generate comprehensive stability report."""
    print("\n" + "=" * 80)
    print("CLICKHOUSE LOGGING FIX STABILITY VALIDATION REPORT")
    print("=" * 80)
    print(f"Issue: https://github.com/netra-systems/netra-apex/issues/134")
    print(f"Fix: Context-aware ClickHouse logging in _handle_connection_error()")
    print(f"Validation Date: {os.popen('date').read().strip()}")
    print("=" * 80)
    
    # Run all validations
    validations = [
        ("Implementation Analysis", analyze_code_changes),
        ("Fix Behavior Testing", test_fix_implementation),
        ("Environment Behavior", validate_environment_behavior),
        ("Backward Compatibility", check_backward_compatibility)
    ]
    
    results = {}
    for name, test_func in validations:
        print(f"\n🔍 {name}:")
        try:
            results[name] = test_func()
            status = "✅ PASS" if results[name] else "❌ FAIL"
            print(f"Result: {status}")
        except Exception as e:
            results[name] = False
            print(f"Result: ❌ ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Validations Passed: {passed}/{total}")
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    # Overall assessment
    if passed == total:
        print("\n🎉 OVERALL: ALL VALIDATIONS PASSED")
        print("✅ The ClickHouse logging fix is working correctly and maintains system stability")
        print("✅ No breaking changes detected")
        print("✅ Graceful degradation working for optional services")  
        print("✅ Fail-fast behavior preserved for required services")
        print("✅ Backward compatibility maintained")
        return True
    else:
        print(f"\n💥 OVERALL: {total - passed} VALIDATIONS FAILED")
        print("❌ The fix needs investigation or has introduced regressions")
        return False


def main():
    """Run comprehensive stability validation."""
    return generate_stability_report()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)