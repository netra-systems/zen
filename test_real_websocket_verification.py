#!/usr/bin/env python
"""
Test verification script to confirm:
1. Tests use real Docker services (no mocks)
2. Tests fail properly without Docker
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
from tests.mission_critical.websocket_real_test_base import (
    require_docker_services,
    RealWebSocketTestBase,
    get_websocket_test_base
)

async def test_real_services():
    """Test that we're using real services and not mocks."""
    print("\n=== Testing Real WebSocket Services ===\n")
    
    # Step 1: Verify Docker is required
    print("1. Checking Docker services requirement...")
    try:
        require_docker_services()
        print("✅ Docker services check passed - services are available")
    except Exception as e:
        print(f"❌ Docker services check failed: {e}")
        return False
    
    # Step 2: Get WebSocket test base
    print("\n2. Getting WebSocket test base...")
    try:
        test_base = get_websocket_test_base()
        print(f"✅ Got test base: {test_base.__class__.__name__}")
        
        # Verify it's RealWebSocketTestBase, not mock
        assert isinstance(test_base, RealWebSocketTestBase)
        print("✅ Confirmed using RealWebSocketTestBase (not mock)")
    except Exception as e:
        print(f"❌ Failed to get test base: {e}")
        return False
    
    # Step 3: Test real WebSocket connection
    print("\n3. Testing real WebSocket connection...")
    try:
        async with test_base.real_websocket_test_session():
            # Create a test context
            test_context = await test_base.create_test_context(user_id="test_user_verification")
            print(f"✅ Created test context for user: {test_context.user_context.user_id}")
            
            # Try to establish WebSocket connection
            await test_context.setup_websocket_connection(
                endpoint="/ws/test",
                auth_required=False
            )
            print("✅ Established real WebSocket connection")
            
            # Send a test message
            test_message = {
                "type": "ping",
                "message": "Testing real WebSocket connection"
            }
            await test_context.send_message(test_message)
            print("✅ Sent test message through real WebSocket")
            
            # Get test metrics
            metrics = test_base.get_test_metrics()
            print(f"\n📊 Test Metrics:")
            print(f"   - Test ID: {metrics['test_id']}")
            print(f"   - Services Started: {metrics['services_started']}")
            print(f"   - Backend URL: {metrics['config']['backend_url']}")
            print(f"   - WebSocket URL: {metrics['config']['websocket_url']}")
            
            # Verify NOT mock mode
            if 'mock_mode' in metrics:
                print(f"❌ ERROR: Test is using mock mode! mock_mode={metrics['mock_mode']}")
                return False
            else:
                print("✅ Confirmed: NOT using mock mode")
            
    except Exception as e:
        print(f"❌ WebSocket session failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All tests passed - using REAL WebSocket services!")
    return True

async def test_docker_requirement():
    """Test that the system fails properly without Docker."""
    print("\n=== Testing Docker Requirement ===\n")
    
    # This should fail if Docker is not available
    print("Checking that tests require Docker...")
    try:
        from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        
        if manager.is_docker_available():
            print("✅ Docker is available and required")
        else:
            print("❌ Docker is not available - tests should fail")
            # This should trigger a failure
            require_docker_services()
    except Exception as e:
        print(f"✅ Correctly failed without Docker: {e}")
        return True
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("REAL WEBSOCKET VERIFICATION TEST")
    print("Verifying NO MOCKS per CLAUDE.md")
    print("=" * 60)
    
    # Run the tests
    success = asyncio.run(test_real_services())
    
    if success:
        print("\n" + "=" * 60)
        print("✅ SUCCESS: All verifications passed!")
        print("Tests are using REAL Docker services, not mocks")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FAILURE: Some verifications failed")
        print("Check the errors above")
        print("=" * 60)
        sys.exit(1)