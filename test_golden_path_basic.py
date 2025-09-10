#!/usr/bin/env python3
"""
Basic Golden Path Test - Core Chat Functionality
Tests that core WebSocket and Agent functionality works without extra features.
"""

import asyncio
import json
import logging
from typing import Dict, Any

async def test_basic_imports():
    """Test that all core golden path components can be imported"""
    print("🔍 Testing core golden path imports...")
    
    try:
        # Core WebSocket functionality
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        from netra_backend.app.routes.websocket import websocket_endpoint
        print("✅ WebSocket components imported successfully")
        
        # Core Agent functionality  
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        print("✅ Agent components imported successfully")
        
        # Core Auth functionality
        from netra_backend.app.auth.auth_service_client import AuthServiceClient
        print("✅ Auth components imported successfully")
        
        # Message handling
        from netra_backend.app.websocket_core.handlers import MessageRouter
        from netra_backend.app.websocket_core.agent_handler import AgentHandler
        print("✅ Message handling components imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_basic_websocket_manager():
    """Test that WebSocket manager can be created"""
    print("🔍 Testing WebSocket manager creation...")
    
    try:
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        # Create a basic manager instance
        manager = UnifiedWebSocketManager()
        print("✅ WebSocket manager created successfully")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket manager creation failed: {e}")
        return False

async def test_basic_agent_registry():
    """Test that Agent registry can be created"""
    print("🔍 Testing Agent registry creation...")
    
    try:
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        # Create a basic registry instance
        registry = AgentRegistry()
        print("✅ Agent registry created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Agent registry creation failed: {e}")
        return False

async def test_basic_auth_client():
    """Test that Auth client can be created (without connecting)"""
    print("🔍 Testing Auth client creation...")
    
    try:
        from netra_backend.app.auth.auth_service_client import AuthServiceClient
        
        # Create a basic auth client instance (don't connect)
        auth_client = AuthServiceClient(
            auth_service_url="http://localhost:8081",
            service_id="test",
            service_secret="test"
        )
        print("✅ Auth client created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Auth client creation failed: {e}")
        return False

async def run_golden_path_basic_test():
    """Run all basic golden path tests"""
    print("🚀 Starting Golden Path Basic Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_basic_imports),
        ("WebSocket Manager Test", test_basic_websocket_manager),
        ("Agent Registry Test", test_basic_agent_registry),
        ("Auth Client Test", test_basic_auth_client),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Golden Path Basic Test Results:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n📈 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL GOLDEN PATH BASIC TESTS PASSED!")
        print("🚀 Core chat functionality is ready for golden path testing")
        return True
    else:
        print("⚠️  Some basic tests failed - golden path may have issues")
        return False

if __name__ == "__main__":
    asyncio.run(run_golden_path_basic_test())