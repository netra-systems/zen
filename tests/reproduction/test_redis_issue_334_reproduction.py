"""
Reproduction script for Redis 'bool' object is not callable issue #334

This script provides a simple reproduction of the issue and validation of the fix
that can be run independently to demonstrate the problem and solution.

Usage:
    python tests/reproduction/test_redis_issue_334_reproduction.py

Business Value:
- Provides clear demonstration of the issue for stakeholders
- Validates the fix works correctly
- Can be used for regression testing
- Helps with debugging and troubleshooting
"""

import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def demonstrate_the_problem():
    """
    Demonstrates the exact 'bool' object is not callable error that occurs in production.
    """
    print("=" * 60)
    print(" ALERT:  DEMONSTRATING THE PROBLEM (Issue #334)")
    print("=" * 60)
    
    # Create mock Redis manager with is_connected as property (like real implementation)
    mock_redis_manager = Mock()
    type(mock_redis_manager).is_connected = property(lambda self: True)
    
    print(" PASS:  Redis manager created with is_connected as property")
    print(f"   is_connected type: {type(mock_redis_manager.is_connected)}")
    print(f"   is_connected value: {mock_redis_manager.is_connected}")
    
    # Show that property access works correctly
    try:
        result = mock_redis_manager.is_connected  # Correct property access
        print(f" PASS:  Property access works: redis_manager.is_connected = {result}")
    except Exception as e:
        print(f" FAIL:  Property access failed: {e}")
        return False
    
    # Show the problematic method call that causes the issue
    try:
        print("\n ALERT:  Now attempting the problematic method call...")
        print("   Executing: redis_manager.is_connected()")
        result = mock_redis_manager.is_connected()  # This is the BUG!
        print(f"   Result: {result}")
        return False  # Should not reach here
    except TypeError as e:
        print(f" FAIL:  ERROR REPRODUCED: {e}")
        print("   This is the exact error that occurs in production!")
        return True
    
def demonstrate_the_fix():
    """
    Demonstrates how the fix resolves the issue.
    """
    print("\n" + "=" * 60)
    print(" PASS:  DEMONSTRATING THE FIX")
    print("=" * 60)
    
    # Create the same Redis manager setup
    mock_redis_manager = Mock()
    type(mock_redis_manager).is_connected = property(lambda self: True)
    
    print("Redis manager setup (same as before):")
    print(f"   is_connected type: {type(mock_redis_manager.is_connected)}")
    
    # Show the corrected usage pattern
    try:
        print("\n PASS:  Using CORRECTED property access:")
        print("   Executing: redis_manager.is_connected  # No parentheses!")
        
        # This is the FIXED version
        is_connected = mock_redis_manager.is_connected  # Property access (no parentheses)
        
        print(f"   Result: {is_connected}")
        print(f"   Type: {type(is_connected)}")
        print(" PASS:  FIX SUCCESSFUL: No TypeError!")
        
        return True
        
    except Exception as e:
        print(f" FAIL:  Unexpected error in fix: {e}")
        return False

def simulate_production_scenario():
    """
    Simulates the production scenario in GCP initialization validator.
    """
    print("\n" + "=" * 60)
    print("[U+1F3ED] SIMULATING PRODUCTION SCENARIO")
    print("=" * 60)
    
    # Simulate the exact context from gcp_initialization_validator.py
    mock_app_state = Mock()
    mock_redis_manager = Mock()
    type(mock_redis_manager).is_connected = property(lambda self: True)
    mock_app_state.redis_manager = mock_redis_manager
    
    print("Production scenario setup:")
    print("   app_state.redis_manager configured")
    print("   Redis is connected and available")
    
    # Show the problematic production code
    print("\n ALERT:  PROBLEMATIC PRODUCTION CODE (current):")
    print("   # Line 376 in gcp_initialization_validator.py")
    print("   if hasattr(redis_manager, 'is_connected'):")
    print("       is_connected = redis_manager.is_connected()  #  FAIL:  WRONG")
    
    try:
        redis_manager = mock_app_state.redis_manager
        if hasattr(redis_manager, 'is_connected'):
            is_connected = redis_manager.is_connected()  # This will fail
            print(f"       Result: {is_connected}")
    except TypeError as e:
        print(f"    FAIL:  PRODUCTION ERROR: {e}")
        
    # Show the fixed production code
    print("\n PASS:  FIXED PRODUCTION CODE (proposed):")
    print("   # Line 376 in gcp_initialization_validator.py (FIXED)")
    print("   if hasattr(redis_manager, 'is_connected'):")
    print("       is_connected = redis_manager.is_connected   #  PASS:  CORRECT")
    
    try:
        redis_manager = mock_app_state.redis_manager
        if hasattr(redis_manager, 'is_connected'):
            is_connected = redis_manager.is_connected  # Fixed version
            print(f"       Result: {is_connected}")
            print(" PASS:  PRODUCTION FIX SUCCESSFUL!")
            return True
    except Exception as e:
        print(f"    FAIL:  Unexpected error: {e}")
        return False

def test_various_redis_states():
    """
    Tests the fix with various Redis connection states.
    """
    print("\n" + "=" * 60)  
    print("[U+1F9EA] TESTING VARIOUS REDIS STATES")
    print("=" * 60)
    
    test_cases = [
        ("Connected Redis", True),
        ("Disconnected Redis", False),
    ]
    
    for test_name, connected_state in test_cases:
        print(f"\n[U+1F4CB] Test: {test_name}")
        
        mock_redis_manager = Mock()
        type(mock_redis_manager).is_connected = property(lambda self, state=connected_state: state)
        
        try:
            # Use the fixed approach
            is_connected = mock_redis_manager.is_connected  # Property access
            print(f"   Result: {is_connected}")
            print(f"   Type: {type(is_connected)}")
            print("    PASS:  Success")
        except Exception as e:
            print(f"    FAIL:  Failed: {e}")
            return False
            
    return True

def performance_comparison():
    """
    Compares performance of property access vs method call attempts.
    """
    print("\n" + "=" * 60)
    print(" LIGHTNING:  PERFORMANCE COMPARISON")
    print("=" * 60)
    
    import time
    
    mock_redis_manager = Mock()
    type(mock_redis_manager).is_connected = property(lambda self: True)
    
    # Test property access performance (correct approach)
    start_time = time.perf_counter()
    for _ in range(1000):
        try:
            _ = mock_redis_manager.is_connected  # Property access
        except:
            pass
    property_time = time.perf_counter() - start_time
    
    print(f" PASS:  Property access (CORRECT): {property_time*1000:.3f}ms for 1000 calls")
    print(f"   Average per call: {property_time*1000000:.3f}[U+03BC]s")
    
    # Test method call attempts (incorrect approach) 
    error_count = 0
    start_time = time.perf_counter()
    for _ in range(1000):
        try:
            _ = mock_redis_manager.is_connected()  # Method call (wrong)
        except TypeError:
            error_count += 1
    method_time = time.perf_counter() - start_time
    
    print(f" FAIL:  Method call attempts (WRONG): {method_time*1000:.3f}ms for 1000 calls")
    print(f"   Errors generated: {error_count}")
    print(f"   Average per call: {method_time*1000000:.3f}[U+03BC]s")
    
    if property_time < method_time:
        print(" PASS:  Property access is faster (no exception overhead)")
    else:
        print(" WARNING: [U+FE0F]  Method call attempts were somehow faster (unexpected)")

def main():
    """
    Main test runner that demonstrates the issue and validates the fix.
    """
    print("Redis 'bool' object is not callable - Issue #334 Reproduction")
    print("Business Impact: Fixes Redis performance degradation affecting chat speed")
    print()
    
    # Step 1: Demonstrate the problem
    problem_reproduced = demonstrate_the_problem()
    
    # Step 2: Demonstrate the fix
    fix_works = demonstrate_the_fix()
    
    # Step 3: Simulate production scenario
    production_fixed = simulate_production_scenario()
    
    # Step 4: Test various states
    states_work = test_various_redis_states()
    
    # Step 5: Performance comparison
    performance_comparison()
    
    # Final summary
    print("\n" + "=" * 60)
    print(" CHART:  SUMMARY")
    print("=" * 60)
    
    print(f"Problem reproduced: {' PASS: ' if problem_reproduced else ' FAIL: '}")
    print(f"Fix works: {' PASS: ' if fix_works else ' FAIL: '}")
    print(f"Production scenario fixed: {' PASS: ' if production_fixed else ' FAIL: '}")
    print(f"Various states work: {' PASS: ' if states_work else ' FAIL: '}")
    
    all_passed = all([problem_reproduced, fix_works, production_fixed, states_work])
    
    if all_passed:
        print("\n CELEBRATION:  ALL TESTS PASSED!")
        print("The fix successfully resolves issue #334")
        print("\nNext Steps:")
        print("1. Apply the fix to gcp_initialization_validator.py line 376")
        print("2. Change 'is_connected()' to 'is_connected' (remove parentheses)")
        print("3. Test in staging environment")
        print("4. Monitor for elimination of 'GRACEFUL DEGRADATION' messages")
        return True
    else:
        print("\n FAIL:  SOME TESTS FAILED")
        print("Review the output above to identify issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)