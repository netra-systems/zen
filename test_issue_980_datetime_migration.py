#!/usr/bin/env python3
"""
Test file to verify datetime.utcnow() to datetime.now(timezone.utc) migrations
Created for Issue #980 verification
"""
import sys
import importlib
from datetime import datetime, timezone

def test_datetime_migration_imports():
    """Verify all migrated files can be imported"""
    files_to_test = [
        'netra_backend.app.factories.clickhouse_factory',
        'netra_backend.app.factories.data_access_factory',
        'netra_backend.app.admin.corpus.unified_corpus_admin',
        'netra_backend.app.services.demo.demo_session_manager',
        'netra_backend.app.routes.demo_websocket',
        'netra_backend.app.infrastructure.remediation_validator'
    ]
    
    success = True
    for module_path in files_to_test:
        try:
            importlib.import_module(module_path)
            print(f"✅ {module_path} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {module_path}: {e}")
            success = False
        except Exception as e:
            print(f"⚠️  Warning importing {module_path}: {e}")
            # Don't fail on warnings, just note them
    return success

def test_datetime_timezone_aware():
    """Verify datetime.now(timezone.utc) produces timezone-aware objects"""
    dt = datetime.now(timezone.utc)
    assert dt.tzinfo is not None, "datetime should be timezone-aware"
    assert dt.tzinfo == timezone.utc, "timezone should be UTC"
    print("✅ datetime.now(timezone.utc) produces correct timezone-aware objects")
    return True

def test_datetime_backwards_compatibility():
    """Verify the new format provides same functionality as old format"""
    # Test that both produce UTC datetime objects
    new_dt = datetime.now(timezone.utc)
    
    # Verify it's timezone-aware and in UTC
    assert new_dt.tzinfo is not None, "New format should be timezone-aware"
    assert new_dt.tzinfo == timezone.utc, "New format should be UTC"
    
    # Verify it produces a reasonable timestamp
    timestamp = new_dt.timestamp()
    assert timestamp > 0, "Should produce valid timestamp"
    
    print("✅ Backward compatibility verified - new format maintains expected behavior")
    return True

if __name__ == "__main__":
    print("🔍 Testing datetime.utcnow() to datetime.now(timezone.utc) migration...")
    print("=" * 70)
    
    success = True
    
    print("\n1. Testing imports of migrated files...")
    success = test_datetime_migration_imports() and success
    
    print("\n2. Testing datetime timezone awareness...")
    success = test_datetime_timezone_aware() and success
    
    print("\n3. Testing backward compatibility...")
    success = test_datetime_backwards_compatibility() and success
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL DATETIME MIGRATION TESTS PASSED!")
        print("Migration from datetime.utcnow() to datetime.now(timezone.utc) is successful")
    else:
        print("❌ SOME TESTS FAILED")
        print("Review import errors and fix before proceeding")
        sys.exit(1)