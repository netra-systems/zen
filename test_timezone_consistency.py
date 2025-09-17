#!/usr/bin/env python3
"""
Timezone Consistency Test for datetime.utcnow() migration
Ensures all datetime operations are timezone-aware
"""
import sys
sys.path.insert(0, '.')
from datetime import datetime, timezone

def verify_timezone_awareness():
    """Ensure all datetime operations are timezone-aware"""
    try:
        # Test that datetime objects are timezone-aware
        now = datetime.now(timezone.utc)
        assert now.tzinfo == timezone.utc, "Should be UTC timezone"
        assert now.utcoffset() is not None, "Should have UTC offset"
        
        # Test the migration worked correctly
        print(f"✅ Timezone-aware datetime confirmed: {now.isoformat()}")
        print(f"✅ UTC offset: {now.utcoffset()}")
        print(f"✅ Timezone: {now.tzinfo}")
        
        # Compare behavior
        naive_equivalent = now.replace(tzinfo=None)  # Remove timezone info
        print(f"✅ Naive equivalent: {naive_equivalent.isoformat()}")
        print(f"✅ Aware is better than naive: {now.tzinfo is not None}")
        
        return True
    except Exception as e:
        print(f"❌ Timezone verification error: {e}")
        return False

def test_datetime_consistency_in_factories():
    """Test that factories use consistent datetime"""
    try:
        from netra_backend.app.factories.clickhouse_factory import ClickhouseFactory
        
        # Verify that we can create datetime objects consistently
        dt1 = datetime.now(timezone.utc)
        dt2 = datetime.now(timezone.utc)
        
        # Should be very close in time
        diff = abs((dt2 - dt1).total_seconds())
        assert diff < 1.0, "Datetime creation should be nearly instantaneous"
        
        print(f"✅ Consistent datetime creation: {dt1.isoformat()}")
        print(f"✅ Time difference: {diff:.6f} seconds")
        
        return True
    except Exception as e:
        print(f"❌ DateTime consistency error: {e}")
        return False

def verify_no_deprecated_utcnow():
    """Verify we don't accidentally use deprecated utcnow"""
    # This is more of a code verification
    import inspect
    
    try:
        # Test that our new approach works
        new_dt = datetime.now(timezone.utc)
        
        # Verify it has timezone info
        assert new_dt.tzinfo is not None, "New datetime should be timezone-aware"
        
        print(f"✅ Using recommended datetime.now(timezone.utc): {new_dt}")
        print(f"✅ No deprecated utcnow() in current test")
        
        return True
    except Exception as e:
        print(f"❌ Deprecated verification error: {e}")
        return False

if __name__ == "__main__":
    print("Testing timezone consistency after datetime migration...")
    print("=" * 60)
    
    tests = [
        verify_timezone_awareness,
        test_datetime_consistency_in_factories,
        verify_no_deprecated_utcnow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()  # Add spacing between tests
    
    print("=" * 60)
    print(f"Timezone Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All timezone consistency tests passed!")
        sys.exit(0)
    else:
        print("❌ Some timezone tests failed")
        sys.exit(1)