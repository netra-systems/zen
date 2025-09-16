#!/usr/bin/env python3
"""
Basic import test for ExecutionEngineFactory after Issue #920 changes.
"""

def test_basic_imports():
    """Test that ExecutionEngineFactory can be imported without errors."""
    try:
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        print("✅ ExecutionEngineFactory import successful")
        return True
    except ImportError as e:
        print(f"❌ ExecutionEngineFactory import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

def test_factory_instantiation():
    """Test that ExecutionEngineFactory can be instantiated with websocket_bridge=None."""
    try:
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        factory = ExecutionEngineFactory(websocket_bridge=None)
        print("✅ ExecutionEngineFactory instantiation with websocket_bridge=None successful")
        return True
    except Exception as e:
        print(f"❌ ExecutionEngineFactory instantiation failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Issue #920 Stability Verification ===")
    print("Testing basic imports and instantiation...")
    
    import_success = test_basic_imports()
    instantiation_success = test_factory_instantiation()
    
    if import_success and instantiation_success:
        print("\n✅ All basic tests PASSED - System appears stable")
    else:
        print("\n❌ Some basic tests FAILED - System may have issues")