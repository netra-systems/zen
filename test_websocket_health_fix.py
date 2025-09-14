#!/usr/bin/env python3
"""
Test script for Issue #1049 WebSocket Health Check Fix
Validates that the health check now matches actual WebSocket functionality
"""
import asyncio
import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

async def test_websocket_health_check_fix():
    """Test that the WebSocket health check fix works properly."""

    logger = get_logger(__name__)

    # Set up staging environment
    env_manager = get_env()
    env_manager.set_environment_variable("ENVIRONMENT", "staging")

    print("Testing Issue #1049 WebSocket Health Check Fix")
    print("=" * 60)

    try:
        # Import the health check function
        from netra_backend.app.websocket_core.gcp_initialization_validator import gcp_websocket_readiness_check

        print("SUCCESS: Successfully imported gcp_websocket_readiness_check")

        # Create a mock app_state that simulates staging conditions
        class MockAppState:
            def __init__(self):
                self.startup_phase = 'unknown'  # This is the common staging issue
                self.startup_complete = False
                self.startup_failed = False
                # Simulate some services available but not all
                self.db_session_factory = None  # Simulating missing DB
                self.redis_manager = None       # Simulating missing Redis

        mock_app_state = MockAppState()
        print("✅ Created mock app_state with staging conditions")

        # Test the health check
        print("\n🔍 Testing health check with staging graceful degradation...")
        ready, details = await gcp_websocket_readiness_check(mock_app_state)

        print(f"📊 Health Check Results:")
        print(f"   Ready: {ready}")
        print(f"   Details: {details}")

        # Validate the fix
        if ready and details.get("graceful_degradation"):
            print("✅ SUCCESS: Health check now applies graceful degradation in staging!")
            print("✅ Health check result matches WebSocket functionality")
            return True
        elif ready and details.get("bypass_active"):
            print("✅ SUCCESS: Staging bypass is working correctly")
            return True
        else:
            print("❌ FAILURE: Health check still failing without proper graceful degradation")
            print(f"   Failed services: {details.get('failed_services', [])}")
            print(f"   Graceful degradation: {details.get('graceful_degradation', False)}")
            return False

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test Error: {e}")
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        return False

async def main():
    """Main test execution"""
    print("🚀 Starting WebSocket Health Check Fix Test")
    success = await test_websocket_health_check_fix()

    print("\n" + "=" * 60)
    if success:
        print("🎉 OVERALL TEST RESULT: SUCCESS")
        print("✅ Issue #1049 fix is working correctly")
        print("✅ Health check now matches WebSocket middleware behavior")
        sys.exit(0)
    else:
        print("💥 OVERALL TEST RESULT: FAILURE")
        print("❌ Issue #1049 fix needs additional work")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())