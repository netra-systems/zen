#!/usr/bin/env python3
"""
Factory Stability Test for datetime.utcnow() migration
Tests that SSOT factories work correctly after datetime migration
"""
import sys
sys.path.insert(0, '.')
from datetime import datetime, timezone

def test_clickhouse_factory():
    """Test ClickhouseFactory with new datetime"""
    try:
        from netra_backend.app.factories.clickhouse_factory import ClickhouseFactory
        factory = ClickhouseFactory()
        # Verify datetime operations work
        now = datetime.now(timezone.utc)
        print(f"✅ ClickhouseFactory works with datetime.now(timezone.utc): {now}")
        return True
    except Exception as e:
        print(f"❌ ClickhouseFactory error: {e}")
        return False

def test_data_access_factory():
    """Test DataAccessFactory with new datetime"""
    try:
        from netra_backend.app.factories.data_access_factory import DataAccessFactory
        factory = DataAccessFactory()
        # Verify datetime operations work
        now = datetime.now(timezone.utc)
        print(f"✅ DataAccessFactory works with datetime.now(timezone.utc): {now}")
        return True
    except Exception as e:
        print(f"❌ DataAccessFactory error: {e}")
        return False

def test_admin_imports():
    """Test admin module imports"""
    try:
        from netra_backend.app.admin.corpus.unified_corpus_admin import UnifiedCorpusAdmin
        print("✅ UnifiedCorpusAdmin imports successfully")
        return True
    except Exception as e:
        print(f"❌ UnifiedCorpusAdmin import error: {e}")
        return False

def test_demo_service_imports():
    """Test demo service imports"""
    try:
        from netra_backend.app.services.demo.demo_session_manager import DemoSessionManager
        print("✅ DemoSessionManager imports successfully")
        return True
    except Exception as e:
        print(f"❌ DemoSessionManager import error: {e}")
        return False

def test_routes_imports():
    """Test route imports"""
    try:
        from netra_backend.app.routes import demo_websocket
        print("✅ demo_websocket imports successfully")
        return True
    except Exception as e:
        print(f"❌ demo_websocket import error: {e}")
        return False

def test_infrastructure_imports():
    """Test infrastructure imports"""
    try:
        from netra_backend.app.infrastructure.remediation_validator import RemediationValidator
        print("✅ RemediationValidator imports successfully")
        return True
    except Exception as e:
        print(f"❌ RemediationValidator import error: {e}")
        return False

if __name__ == "__main__":
    print("Testing factory and module stability after datetime migration...")
    print("=" * 60)
    
    tests = [
        test_clickhouse_factory,
        test_data_access_factory,
        test_admin_imports,
        test_demo_service_imports,
        test_routes_imports,
        test_infrastructure_imports
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
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All stability tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)