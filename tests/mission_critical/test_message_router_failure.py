"""
Mission Critical Test: MessageRouter Staging Failure Fix
Tests that the MessageRouter SSOT violation is resolved and staging will work.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_message_router_ssot():
    """Test that only ONE MessageRouter exists with correct interface."""
    print("\n" + "="*60)
    print("Testing MessageRouter SSOT Compliance")
    print("="*60)
    
    # Test 1: Verify the correct MessageRouter exists
    print("\n1. Checking correct MessageRouter exists...")
    try:
        from netra_backend.app.websocket_core.handlers import MessageRouter as CoreRouter
        print("   [OK] Found MessageRouter in websocket_core.handlers")
    except ImportError as e:
        print(f"   [FAIL] Failed to import correct MessageRouter: {e}")
        return False
    
    # Test 2: Verify it has the correct interface
    print("\n2. Checking MessageRouter interface...")
    router = CoreRouter()
    
    if hasattr(router, 'add_handler'):
        print("   [OK] Has add_handler() method (correct)")
    else:
        print("   [FAIL] Missing add_handler() method")
        return False
    
    if hasattr(router, 'register_handler'):
        print("   [FAIL] Has register_handler() method (WRONG - duplicate class!)")
        return False
    else:
        print("   [OK] Does NOT have register_handler() (correct)")
    
    # Test 3: Verify the duplicate is gone
    print("\n3. Checking duplicate MessageRouter is removed...")
    try:
        from netra_backend.app.services.websocket.message_router import MessageRouter as DuplicateRouter
        print("   [FAIL] Duplicate MessageRouter still exists at services.websocket.message_router")
        print("      This MUST be deleted for SSOT compliance!")
        return False
    except ImportError:
        print("   [OK] Duplicate MessageRouter has been removed (good)")
    
    # Test 4: Check compatibility import
    print("\n4. Checking compatibility import...")
    try:
        from netra_backend.app.agents.message_router import MessageRouter as AgentRouter
        if AgentRouter is CoreRouter:
            print("   [OK] Compatibility import points to correct MessageRouter")
        else:
            print("   [FAIL] Compatibility import points to wrong MessageRouter")
            return False
    except ImportError:
        print("   [OK] No compatibility import needed (also acceptable)")
    
    # Test 5: Check main export
    print("\n5. Checking main websocket_core export...")
    try:
        from netra_backend.app.websocket_core import MessageRouter as ExportedRouter
        if ExportedRouter is CoreRouter:
            print("   [OK] Main export points to correct MessageRouter")
        else:
            print("   [FAIL] Main export points to wrong MessageRouter")
            return False
    except ImportError as e:
        print(f"   [FAIL] Failed to import from websocket_core: {e}")
        return False
    
    print("\n" + "="*60)
    print("[OK] ALL TESTS PASSED - MessageRouter is SSOT compliant!")
    print("="*60)
    return True


def test_agent_handler_registration():
    """Test that AgentMessageHandler can be registered."""
    print("\n" + "="*60)
    print("Testing AgentMessageHandler Registration")
    print("="*60)
    
    try:
        from netra_backend.app.websocket_core import MessageRouter, get_message_router
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        
        # Get the router
        router = get_message_router()
        print(f"\n[OK] Got MessageRouter with {len(router.handlers)} handlers")
        
        # Create a mock AgentMessageHandler
        from unittest.mock import MagicMock
        mock_service = MagicMock()
        mock_websocket = MagicMock()
        
        handler = AgentMessageHandler(mock_service, mock_websocket)
        print("[OK] Created AgentMessageHandler")
        
        # This is the line that was failing in staging!
        router.add_handler(handler)
        print("[OK] Successfully registered AgentMessageHandler with add_handler()")
        
        # Verify it's in the handlers
        if handler in router.handlers:
            print("[OK] Handler is in router.handlers list")
        else:
            print("[FAIL] Handler was not added to router.handlers")
            return False
        
        # Clean up
        router.remove_handler(handler)
        print("[OK] Successfully removed handler")
        
        print("\n" + "="*60)
        print("[OK] AgentMessageHandler registration works correctly!")
        print("="*60)
        return True
        
    except AttributeError as e:
        if "register_handler" in str(e):
            print(f"\n[FAIL] CRITICAL ERROR: {e}")
            print("   This is the staging bug - wrong MessageRouter is being used!")
            return False
        raise
    except Exception as e:
        print(f"\n[FAIL] Error during handler registration: {e}")
        return False


if __name__ == "__main__":
    # Run SSOT test
    ssot_pass = test_message_router_ssot()
    
    # Run handler registration test
    handler_pass = test_agent_handler_registration()
    
    # Summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if ssot_pass and handler_pass:
        print("SUCCESS! ALL CRITICAL TESTS PASSED!")
        print("\n[OK] MessageRouter SSOT violation is FIXED")
        print("[OK] AgentMessageHandler registration works")
        print("[OK] Staging should now work correctly")
        print("\nNext steps:")
        print("1. Commit these changes")
        print("2. Deploy to staging: python scripts/deploy_to_gcp.py --project netra-staging --no-cache")
        print("3. Monitor logs for successful AgentMessageHandler registration")
    else:
        print("[FAIL] TESTS FAILED - Fix required before deploying to staging!")
        if not ssot_pass:
            print("   - MessageRouter SSOT violation still exists")
        if not handler_pass:
            print("   - AgentMessageHandler registration fails")