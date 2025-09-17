#!/usr/bin/env python3
"""
Simple validation script to test domain configuration fixes
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_configuration_loading():
    """Test that staging configuration loads with corrected domains"""
    print("🔧 Testing configuration loading...")
    
    try:
        from tests.e2e.staging_test_config import get_staging_config
        config = get_staging_config()
        
        print("✅ Configuration loaded successfully:")
        print(f"  - Backend URL: {config.backend_url}")
        print(f"  - WebSocket URL: {config.websocket_url}")  
        print(f"  - API URL: {config.api_url}")
        print(f"  - Base URL: {config.base_url}")
        
        # Validate domain patterns are correct per CLAUDE.md requirements
        assert config.backend_url == "https://staging.netrasystems.ai", f"Backend URL incorrect: {config.backend_url}"
        assert config.websocket_url == "wss://api-staging.netrasystems.ai/api/v1/websocket", f"WebSocket URL incorrect: {config.websocket_url}"
        assert config.api_url == "https://staging.netrasystems.ai/api", f"API URL incorrect: {config.api_url}"
        
        print("✅ All domain patterns match CLAUDE.md requirements")
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_import_functionality():
    """Test that critical imports work"""
    print("\n🔧 Testing critical imports...")
    
    try:
        # Test SSOT imports that were previously failing
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
        
        print("✅ Agent WebSocket bridge imports successful:")
        print(f"  - create_agent_websocket_bridge: {callable(create_agent_websocket_bridge)}")
        print(f"  - AgentWebSocketBridge class: {AgentWebSocketBridge is not None}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

async def test_basic_connectivity():
    """Test basic connectivity to staging environment"""
    print("\n🔧 Testing basic staging connectivity...")
    
    try:
        import httpx
        
        # Test health endpoint
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get("https://staging.netrasystems.ai/health")
                print(f"✅ Health endpoint response: {response.status_code}")
                if response.status_code == 200:
                    print("✅ Staging environment is responsive")
                    return True
                else:
                    print(f"⚠️ Staging returned non-200 status: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Health check failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Connectivity test setup failed: {e}")
        return False

def test_websocket_url_format():
    """Test WebSocket URL format is correctly configured"""
    print("\n🔧 Testing WebSocket URL format...")
    
    try:
        from tests.e2e.staging_test_config import get_staging_config
        config = get_staging_config()
        
        websocket_url = config.websocket_url
        print(f"WebSocket URL: {websocket_url}")
        
        # Validate format matches requirements
        expected_pattern = "wss://api-staging.netrasystems.ai/api/v1/websocket"
        if websocket_url == expected_pattern:
            print("✅ WebSocket URL format is correct")
            return True
        else:
            print(f"❌ WebSocket URL format incorrect. Expected: {expected_pattern}, Got: {websocket_url}")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket URL test failed: {e}")
        return False

async def main():
    """Run all validation tests"""
    print("=" * 60)
    print("🚀 DOMAIN CONFIGURATION VALIDATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Purpose: Validate Issue #1278 domain configuration fixes")
    print()
    
    results = {
        "configuration_loading": test_configuration_loading(),
        "import_functionality": test_import_functionality(), 
        "websocket_url_format": test_websocket_url_format(),
        "basic_connectivity": await test_basic_connectivity()
    }
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for result in results.values() if result)
    total_tests = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name.replace('_', ' ').title()}")
    
    print()
    print(f"Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Domain fixes are working correctly!")
        print("\n📋 NEXT STEPS:")
        print("  1. Domain configuration fixes are validated")
        print("  2. Ready to run full E2E tests against staging")
        print("  3. If staging is not deployed, consider Terraform deployment")
        return True
    else:
        print("⚠️ SOME TESTS FAILED - Issues remain to be resolved")
        print("\n📋 RECOMMENDED ACTIONS:")
        if not results["basic_connectivity"]:
            print("  - Staging environment may not be deployed or accessible")
            print("  - Consider running Terraform deployment")
        if not results["configuration_loading"] or not results["websocket_url_format"]:
            print("  - Review domain configuration settings")
        if not results["import_functionality"]:
            print("  - Check Python path and import dependencies")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)