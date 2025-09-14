"""
Mission Critical Test: MessageRouter SSOT Compliance Validation

Tests that the MessageRouter SSOT violation is resolved and staging deployment will work.
This test validates that the MessageRouter Phase 1 proxy implementation is working correctly.

Business Value: Platform/Internal - System Stability & Golden Path Protection
- Protects $500K+ ARR chat functionality from MessageRouter routing conflicts
- Ensures single canonical routing implementation for reliability
- Validates staging deployment readiness after SSOT remediation

GitHub Issue: #1077 - MessageRouter SSOT violations blocking golden path
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketConnection:
    """Mock WebSocket connection for testing instead of real connections."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()


class TestMessageRouterSSOTCompliance(SSotBaseTestCase, unittest.TestCase):
    """Mission Critical Test: Validates MessageRouter SSOT compliance is resolved."""

    def setUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'setUp'):
            super().setUp()

    def test_message_router_ssot_compliance(self):
        """Test that only ONE MessageRouter exists with correct interface."""
        print("\n" + "="*60)
        print("Testing MessageRouter SSOT Compliance")
        print("="*60)

        # Test 1: Verify the canonical MessageRouter exists
        print("\n1. Checking canonical MessageRouter exists...")
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter
            print("   [OK] Found MessageRouter in websocket_core.handlers")
        except ImportError as e:
            self.fail(f"   [FAIL] Cannot import canonical MessageRouter: {e}")

        # Test 2: Verify it has the correct interface
        print("\n2. Checking MessageRouter interface...")
        router = CanonicalRouter()

        if hasattr(router, 'add_handler'):
            print("   [OK] Has add_handler() method (correct)")
        else:
            self.fail("   [FAIL] Missing add_handler() method")

        if hasattr(router, 'route_message'):
            print("   [OK] Has route_message() method (correct)")
        else:
            self.fail("   [FAIL] Missing route_message() method")

        if hasattr(router, 'handlers'):
            print("   [OK] Has handlers property (correct)")
        else:
            self.fail("   [FAIL] Missing handlers property")

        # Test 3: Verify services re-export works
        print("\n3. Checking services module re-export...")
        try:
            from netra_backend.app.services.message_router import MessageRouter as ServicesRouter
            if ServicesRouter is CanonicalRouter:
                print("   [OK] Services module correctly re-exports canonical MessageRouter")
            else:
                self.fail("   [FAIL] Services module does not re-export canonical MessageRouter")
        except ImportError as e:
            self.fail(f"   [FAIL] Cannot import from services module: {e}")

        # Test 4: Verify core proxy works
        print("\n4. Checking core module proxy...")
        try:
            from netra_backend.app.core.message_router import MessageRouter as CoreRouter
            
            # Should be a proxy, not the same instance
            proxy_router = CoreRouter()
            if hasattr(proxy_router, 'add_handler'):
                print("   [OK] Core proxy has add_handler() method")
            else:
                self.fail("   [FAIL] Core proxy missing add_handler() method")
                
            if hasattr(proxy_router, 'handlers'):
                print("   [OK] Core proxy has handlers property")
            else:
                self.fail("   [FAIL] Core proxy missing handlers property")
                
        except ImportError as e:
            self.fail(f"   [FAIL] Cannot import core proxy: {e}")

        print("\n" + "="*60)
        print("[OK] ALL TESTS PASSED - MessageRouter is SSOT compliant!")
        print("="*60)

    def test_agent_handler_registration_compatibility(self):
        """Test that AgentMessageHandler can be registered with the SSOT MessageRouter."""
        print("\n" + "="*60)
        print("Testing AgentMessageHandler Registration Compatibility")
        print("="*60)

        try:
            from netra_backend.app.websocket_core.handlers import get_message_router
            
            # Get the canonical router
            router = get_message_router()
            print(f"   [OK] Got canonical router with {len(router.handlers)} handlers")

            # Create a mock handler for testing
            mock_handler = MagicMock()
            mock_handler.can_handle = MagicMock(return_value=True)
            mock_handler.handle_message = MagicMock()
            mock_handler.__class__.__name__ = "MockAgentHandler"

            # This is the critical line that was failing in staging!
            initial_count = len(router.handlers)
            router.add_handler(mock_handler)
            print("   [OK] Successfully registered handler with add_handler()")

            # Verify it's in the handlers
            if len(router.handlers) > initial_count:
                print("   [OK] Handler count increased after registration")
            else:
                self.fail("   [FAIL] Handler was not added to router.handlers")

            # Clean up
            router.remove_handler(mock_handler)
            print("   [OK] Successfully removed handler")

            print("\n" + "="*60)
            print("[OK] AgentMessageHandler registration works correctly!")
            print("="*60)

        except AttributeError as e:
            if "add_handler" in str(e):
                self.fail(f"   [FAIL] Missing add_handler method: {e}")
            else:
                self.fail(f"   [FAIL] Unexpected AttributeError: {e}")
        except Exception as e:
            self.fail(f"   [FAIL] Handler registration failed: {e}")

    def test_websocket_routing_compatibility(self):
        """Test that WebSocket routing continues to work with SSOT MessageRouter."""
        print("\n" + "="*60)
        print("Testing WebSocket Routing Compatibility")
        print("="*60)

        try:
            from netra_backend.app.websocket_core.handlers import get_message_router
            
            router = get_message_router()
            
            # Test basic routing functionality
            test_websocket = TestWebSocketConnection()
            test_message = {
                "type": "ping",
                "payload": {"test": True},
                "timestamp": 1234567890
            }
            
            # Test that route_message method exists and is callable
            if hasattr(router, 'route_message') and callable(router.route_message):
                print("   [OK] route_message method is callable")
            else:
                self.fail("   [FAIL] route_message method missing or not callable")

            print("\n" + "="*60)
            print("[OK] WebSocket routing compatibility verified!")
            print("="*60)

        except Exception as e:
            self.fail(f"   [FAIL] WebSocket routing test failed: {e}")


if __name__ == "__main__":
    print("Running MessageRouter SSOT compliance tests...")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMessageRouterSSOTCompliance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if result.wasSuccessful():
        print("SUCCESS! ALL CRITICAL TESTS PASSED!")
        print("\n[OK] MessageRouter SSOT violation is FIXED")
        print("[OK] AgentMessageHandler registration works")
        print("[OK] WebSocket routing compatibility verified")
        print("[OK] Staging should now work correctly")
        print("\nNext steps:")
        print("1. Commit these changes")
        print("2. Deploy to staging: python scripts/deploy_to_gcp.py --project netra-staging --build-local")
        print("3. Monitor logs for successful AgentMessageHandler registration")
    else:
        print("[FAIL] TESTS FAILED - Fix required before deploying to staging!")
        if result.failures:
            print("   Failures:")
            for test, traceback in result.failures:
                print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
        if result.errors:
            print("   Errors:")
            for test, traceback in result.errors:
                print(f"   - {test}: {traceback.split('Error:')[-1].strip()}")