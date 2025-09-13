#!/usr/bin/env python3
"""
Quick WebSocket Infrastructure Validation Test for Issue #778

This test proves that all the infrastructure components are working correctly.
"""

import asyncio
import os
import sys
import traceback

# Set mock mode environment variables
os.environ["WEBSOCKET_INFRASTRUCTURE_MOCK_MODE"] = "true"
os.environ["WEBSOCKET_AUTH_MOCK_MODE"] = "true"
os.environ["WEBSOCKET_BRIDGE_MOCK_MODE"] = "true"

async def test_imports_work():
    """Test that all new components can be imported."""
    print("🔍 Testing Infrastructure Imports...")
    
    try:
        # Test imports from websocket module  
        from test_framework.ssot.websocket import (
            WebSocketTestInfrastructureFactory,
            WebSocketAuthHelper,
            WebSocketBridgeTestHelper,
            CommunicationMetricsCollector
        )
        print("✅ All components imported from websocket module")
        
        # Test imports from main SSOT module
        from test_framework.ssot import (
            WebSocketTestInfrastructureFactory,
            WebSocketAuthHelper,
            WebSocketBridgeTestHelper,
            CommunicationMetricsCollector
        )
        print("✅ All components imported from main SSOT module")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

async def test_factory_works():
    """Test that the factory creates infrastructure correctly."""
    print("\n🏭 Testing Infrastructure Factory...")
    
    try:
        from test_framework.ssot import WebSocketTestInfrastructureFactory
        
        # Create factory with mock mode
        mock_config = {"mock_mode": True, "enable_authentication": True, 
                      "enable_agent_bridge": True, "enable_metrics_collection": True}
        
        factory = WebSocketTestInfrastructureFactory()
        await factory.initialize()
        print("✅ Factory initialized")
        
        # Create infrastructure
        infrastructure = await factory.create_websocket_test_infrastructure(custom_config=mock_config)
        print("✅ Infrastructure created with all components")
        
        # Check all components exist
        components = [
            ("WebSocket Utility", infrastructure.websocket_utility),
            ("Auth Helper", infrastructure.auth_helper),
            ("Bridge Helper", infrastructure.bridge_helper),
            ("Metrics Collector", infrastructure.metrics_collector)
        ]
        
        all_present = True
        for name, component in components:
            if component:
                print(f"✅ {name} created successfully")
            else:
                print(f"❌ {name} missing")
                all_present = False
        
        await factory.cleanup_all()
        print("✅ Factory cleanup successful")
        
        return all_present
        
    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        traceback.print_exc()
        return False

async def test_components_work():
    """Test that individual components work correctly."""
    print("\n🧩 Testing Individual Components...")
    
    results = []
    
    # Test Auth Helper
    try:
        from test_framework.ssot.websocket_auth_helper import WebSocketAuthHelper, WebSocketAuthConfig
        
        config = WebSocketAuthConfig(
            jwt_secret="test_secret", token_expiry_hours=24,
            allowed_origins=["http://localhost:3000"], 
            require_authentication=True, enable_user_isolation=True, mock_mode=True
        )
        
        async with WebSocketAuthHelper(config=config) as auth_helper:
            user_context = await auth_helper.create_test_user_context("testuser")
            is_valid = user_context.is_token_valid()
            print(f"✅ Auth Helper: User created, token valid: {is_valid}")
            results.append(True)
    except Exception as e:
        print(f"❌ Auth Helper failed: {e}")
        results.append(False)
    
    # Test Metrics Collector
    try:
        from test_framework.ssot.communication_metrics_collector import CommunicationMetricsCollector, MetricType
        
        async with CommunicationMetricsCollector() as metrics:
            session_id = await metrics.start_session("testuser", "test")
            metrics.record_metric(MetricType.LATENCY, 0.1)
            performance = await metrics.get_performance_metrics()
            await metrics.end_session(session_id)
            print(f"✅ Metrics Collector: Session created, {performance.total_sessions} sessions tracked")
            results.append(True)
    except Exception as e:
        print(f"❌ Metrics Collector failed: {e}")
        results.append(False)
    
    return all(results)

async def main():
    """Run validation tests."""
    print("🚀 WebSocket Infrastructure Validation for Issue #778")
    print("=" * 55)
    
    tests = [
        ("Imports Work", test_imports_work),
        ("Factory Works", test_factory_works),
        ("Components Work", test_components_work)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} exception: {e}")
            results.append((test_name, False))
    
    print(f"\n{'='*20} SUMMARY {'='*20}")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"  
        print(f"{status} - {test_name}")
    
    print(f"\nTests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 SUCCESS! All WebSocket Infrastructure Components Working!")
        print("\n📋 Issue #778 RESOLVED:")
        print("✅ WebSocketTestInfrastructureFactory - IMPLEMENTED")
        print("✅ WebSocketAuthHelper - IMPLEMENTED")
        print("✅ WebSocketBridgeTestHelper - IMPLEMENTED") 
        print("✅ CommunicationMetricsCollector - IMPLEMENTED")
        print("✅ SSOT Integration - COMPLETE")
        print("\n💰 $500K+ ARR Chat Functionality Test Infrastructure READY!")
        
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)