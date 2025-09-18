#!/usr/bin/env python3
"""
Quick test to verify MessageRouter handler registration fix
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def test_message_router_handlers():
    """Test that MessageRouter initializes with built-in handlers"""
    try:
        from netra_backend.app.websocket_core.handlers import MessageRouter

        print("Creating MessageRouter instance...")
        router = MessageRouter()

        print(f"Router created successfully!")
        print(f"Router has handlers attribute: {hasattr(router, 'handlers')}")

        handlers = router.handlers
        handler_count = len(handlers)

        print(f"Handler count: {handler_count}")
        print(f"Handler types: {[type(h).__name__ for h in handlers]}")

        # Test basic requirements
        if handler_count > 0:
            print("✅ SUCCESS: MessageRouter initializes with built-in handlers")
            return True
        else:
            print("❌ FAIL: MessageRouter has no handlers")
            return False

    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_message_router_handlers()
    sys.exit(0 if success else 1)