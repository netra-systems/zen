#!/usr/bin/env python
"""
Quick test to validate Golden Path imports without running full tests.
"""
import sys
import traceback
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def test_golden_path_imports():
    """Test core Golden Path imports."""
    results = {}

    print("🚀 Testing Golden Path Core Imports...")
    print(f"📁 Project root: {PROJECT_ROOT}")

    # Test 1: User Execution Context
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        results["UserExecutionContext"] = "✅ SUCCESS"
        print("✅ UserExecutionContext imported successfully")
    except Exception as e:
        results["UserExecutionContext"] = f"❌ FAILED: {e}"
        print(f"❌ UserExecutionContext failed: {e}")
        traceback.print_exc()

    # Test 2: Supervisor Agent
    try:
        from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
        results["SupervisorAgent"] = "✅ SUCCESS"
        print("✅ SupervisorAgent imported successfully")
    except Exception as e:
        results["SupervisorAgent"] = f"❌ FAILED: {e}"
        print(f"❌ SupervisorAgent failed: {e}")
        traceback.print_exc()

    # Test 3: WebSocket Manager
    try:
        from netra_backend.app.websocket_core.manager import WebSocketManager
        results["WebSocketManager"] = "✅ SUCCESS"
        print("✅ WebSocketManager imported successfully")
    except Exception as e:
        results["WebSocketManager"] = f"❌ FAILED: {e}"
        print(f"❌ WebSocketManager failed: {e}")
        traceback.print_exc()

    # Test 4: Execution Engine Factory
    try:
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        results["ExecutionEngineFactory"] = "✅ SUCCESS"
        print("✅ ExecutionEngineFactory imported successfully")
    except Exception as e:
        results["ExecutionEngineFactory"] = f"❌ FAILED: {e}"
        print(f"❌ ExecutionEngineFactory failed: {e}")
        traceback.print_exc()

    # Test 5: WebSocket Components
    try:
        from netra_backend.app.websocket_core.handlers import MessageRouter
        from netra_backend.app.websocket_core.agent_handler import AgentHandler
        results["WebSocketComponents"] = "✅ SUCCESS"
        print("✅ WebSocket components imported successfully")
    except Exception as e:
        results["WebSocketComponents"] = f"❌ FAILED: {e}"
        print(f"❌ WebSocket components failed: {e}")
        traceback.print_exc()

    # Test 6: Auth Integration
    try:
        from netra_backend.app.auth_integration.auth import get_auth_service
        from netra_backend.app.websocket_core.auth import WebSocketAuthHandler
        results["AuthComponents"] = "✅ SUCCESS"
        print("✅ Auth components imported successfully")
    except Exception as e:
        results["AuthComponents"] = f"❌ FAILED: {e}"
        print(f"❌ Auth components failed: {e}")
        traceback.print_exc()

    # Summary
    print("\n📊 GOLDEN PATH IMPORT SUMMARY:")
    print("=" * 50)
    success_count = 0
    for component, status in results.items():
        print(f"{component}: {status}")
        if "SUCCESS" in status:
            success_count += 1

    print(f"\n🎯 Success Rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

    if success_count == len(results):
        print("🎉 ALL GOLDEN PATH IMPORTS SUCCESSFUL!")
        return True
    else:
        print("⚠️ SOME GOLDEN PATH IMPORTS FAILED")
        return False

if __name__ == "__main__":
    success = test_golden_path_imports()
    sys.exit(0 if success else 1)