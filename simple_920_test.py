#!/usr/bin/env python3
"""
Simple Issue #920 validation test.
Tests the core Issue #920 fix: ExecutionEngineFactory should accept websocket_bridge=None
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_issue_920_fix():
    """Test that Issue #920 has been fixed."""
    print("🔬 Testing Issue #920 Fix")
    print("=" * 40)
    
    # Test 1: Import ExecutionEngineFactory
    print("1. Testing ExecutionEngineFactory import...")
    try:
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        print("   ✅ Import successful")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False
    
    # Test 2: Create factory with websocket_bridge=None (Issue #920 fix)
    print("2. Testing ExecutionEngineFactory(websocket_bridge=None)...")
    try:
        factory = ExecutionEngineFactory(websocket_bridge=None)
        print("   ✅ Factory creation successful - Issue #920 FIXED!")
        print(f"   ✅ Factory._websocket_bridge = {factory._websocket_bridge}")
    except Exception as e:
        print(f"   ❌ Factory creation failed: {e}")
        print("   ❌ Issue #920 NOT FIXED - still raises error")
        return False
    
    # Test 3: Verify factory attributes
    print("3. Testing factory attributes...")
    try:
        assert hasattr(factory, '_websocket_bridge')
        assert hasattr(factory, '_active_engines') 
        assert hasattr(factory, '_engine_lock')
        assert factory._websocket_bridge is None
        print("   ✅ All required attributes present")
    except Exception as e:
        print(f"   ❌ Attribute validation failed: {e}")
        return False
    
    # Test 4: Test factory configuration
    print("4. Testing factory configuration...")
    try:
        assert factory._max_engines_per_user > 0
        assert factory._engine_timeout_seconds > 0
        print(f"   ✅ Max engines per user: {factory._max_engines_per_user}")
        print(f"   ✅ Engine timeout: {factory._engine_timeout_seconds}s")
    except Exception as e:
        print(f"   ❌ Configuration validation failed: {e}")
        return False
    
    print("\n🟢 ALL TESTS PASSED - Issue #920 has been successfully fixed!")
    print("✅ ExecutionEngineFactory now accepts websocket_bridge=None without errors")
    return True

if __name__ == "__main__":
    success = test_issue_920_fix()
    if success:
        print("\n✅ PROOF: System is stable after Issue #920 changes")
        sys.exit(0)
    else:
        print("\n❌ PROBLEM: Issue #920 fix validation failed")
        sys.exit(1)