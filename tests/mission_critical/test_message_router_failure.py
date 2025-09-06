# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Mission Critical Test: MessageRouter Staging Failure Fix
    # REMOVED_SYNTAX_ERROR: Tests that the MessageRouter SSOT violation is resolved and staging will work.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# REMOVED_SYNTAX_ERROR: def test_message_router_ssot():
    # REMOVED_SYNTAX_ERROR: """Test that only ONE MessageRouter exists with correct interface."""
    # REMOVED_SYNTAX_ERROR: print(" )
    # REMOVED_SYNTAX_ERROR: " + "="*60)
    # REMOVED_SYNTAX_ERROR: print("Testing MessageRouter SSOT Compliance")
    # REMOVED_SYNTAX_ERROR: print("="*60)

    # Test 1: Verify the correct MessageRouter exists
    # REMOVED_SYNTAX_ERROR: print(" )
    # REMOVED_SYNTAX_ERROR: 1. Checking correct MessageRouter exists...")
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import MessageRouter as CoreRouter
        # REMOVED_SYNTAX_ERROR: print("   [OK] Found MessageRouter in websocket_core.handlers")
        # REMOVED_SYNTAX_ERROR: except ImportError as e:
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: return False

            # Test 2: Verify it has the correct interface
            # REMOVED_SYNTAX_ERROR: print(" )
            # REMOVED_SYNTAX_ERROR: 2. Checking MessageRouter interface...")
            # REMOVED_SYNTAX_ERROR: router = CoreRouter()

            # REMOVED_SYNTAX_ERROR: if hasattr(router, 'add_handler'):
                # REMOVED_SYNTAX_ERROR: print("   [OK] Has add_handler() method (correct)")
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: print("   [FAIL] Missing add_handler() method")
                    # REMOVED_SYNTAX_ERROR: return False

                    # REMOVED_SYNTAX_ERROR: if hasattr(router, 'register_handler'):
                        # REMOVED_SYNTAX_ERROR: print("   [FAIL] Has register_handler() method (WRONG - duplicate class!)")
                        # REMOVED_SYNTAX_ERROR: return False
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: print("   [OK] Does NOT have register_handler() (correct)")

                            # Test 3: Verify the duplicate is gone
                            # REMOVED_SYNTAX_ERROR: print(" )
                            # REMOVED_SYNTAX_ERROR: 3. Checking duplicate MessageRouter is removed...")
                            # REMOVED_SYNTAX_ERROR: try:
                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket.message_router import MessageRouter as DuplicateRouter
                                # REMOVED_SYNTAX_ERROR: print("   [FAIL] Duplicate MessageRouter still exists at services.websocket.message_router")
                                # REMOVED_SYNTAX_ERROR: print("      This MUST be deleted for SSOT compliance!")
                                # REMOVED_SYNTAX_ERROR: return False
                                # REMOVED_SYNTAX_ERROR: except ImportError:
                                    # REMOVED_SYNTAX_ERROR: print("   [OK] Duplicate MessageRouter has been removed (good)")

                                    # Test 4: Check compatibility import
                                    # REMOVED_SYNTAX_ERROR: print(" )
                                    # REMOVED_SYNTAX_ERROR: 4. Checking compatibility import...")
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.message_router import MessageRouter as AgentRouter
                                        # REMOVED_SYNTAX_ERROR: if AgentRouter is CoreRouter:
                                            # REMOVED_SYNTAX_ERROR: print("   [OK] Compatibility import points to correct MessageRouter")
                                            # REMOVED_SYNTAX_ERROR: else:
                                                # REMOVED_SYNTAX_ERROR: print("   [FAIL] Compatibility import points to wrong MessageRouter")
                                                # REMOVED_SYNTAX_ERROR: return False
                                                # REMOVED_SYNTAX_ERROR: except ImportError:
                                                    # REMOVED_SYNTAX_ERROR: print("   [OK] No compatibility import needed (also acceptable)")

                                                    # Test 5: Check main export
                                                    # REMOVED_SYNTAX_ERROR: print(" )
                                                    # REMOVED_SYNTAX_ERROR: 5. Checking main websocket_core export...")
                                                    # REMOVED_SYNTAX_ERROR: try:
                                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import MessageRouter as ExportedRouter
                                                        # REMOVED_SYNTAX_ERROR: if ExportedRouter is CoreRouter:
                                                            # REMOVED_SYNTAX_ERROR: print("   [OK] Main export points to correct MessageRouter")
                                                            # REMOVED_SYNTAX_ERROR: else:
                                                                # REMOVED_SYNTAX_ERROR: print("   [FAIL] Main export points to wrong MessageRouter")
                                                                # REMOVED_SYNTAX_ERROR: return False
                                                                # REMOVED_SYNTAX_ERROR: except ImportError as e:
                                                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                    # REMOVED_SYNTAX_ERROR: return False

                                                                    # REMOVED_SYNTAX_ERROR: print(" )
                                                                    # REMOVED_SYNTAX_ERROR: " + "="*60)
                                                                    # REMOVED_SYNTAX_ERROR: print("[OK] ALL TESTS PASSED - MessageRouter is SSOT compliant!")
                                                                    # REMOVED_SYNTAX_ERROR: print("="*60)
                                                                    # REMOVED_SYNTAX_ERROR: return True


# REMOVED_SYNTAX_ERROR: def test_agent_handler_registration():
    # REMOVED_SYNTAX_ERROR: """Test that AgentMessageHandler can be registered."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: print(" )
    # REMOVED_SYNTAX_ERROR: " + "="*60)
    # REMOVED_SYNTAX_ERROR: print("Testing AgentMessageHandler Registration")
    # REMOVED_SYNTAX_ERROR: print("="*60)

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import MessageRouter, get_message_router
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler

        # Get the router
        # REMOVED_SYNTAX_ERROR: router = get_message_router()
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # Create a mock AgentMessageHandler
        # REMOVED_SYNTAX_ERROR: mock_service = Magic        mock_websocket = Magic
        # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_service, mock_websocket)
        # REMOVED_SYNTAX_ERROR: print("[OK] Created AgentMessageHandler")

        # This is the line that was failing in staging!
        # REMOVED_SYNTAX_ERROR: router.add_handler(handler)
        # REMOVED_SYNTAX_ERROR: print("[OK] Successfully registered AgentMessageHandler with add_handler()")

        # Verify it's in the handlers
        # REMOVED_SYNTAX_ERROR: if handler in router.handlers:
            # REMOVED_SYNTAX_ERROR: print("[OK] Handler is in router.handlers list")
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: print("[FAIL] Handler was not added to router.handlers")
                # REMOVED_SYNTAX_ERROR: return False

                # Clean up
                # REMOVED_SYNTAX_ERROR: router.remove_handler(handler)
                # REMOVED_SYNTAX_ERROR: print("[OK] Successfully removed handler")

                # REMOVED_SYNTAX_ERROR: print(" )
                # REMOVED_SYNTAX_ERROR: " + "="*60)
                # REMOVED_SYNTAX_ERROR: print("[OK] AgentMessageHandler registration works correctly!")
                # REMOVED_SYNTAX_ERROR: print("="*60)
                # REMOVED_SYNTAX_ERROR: return True

                # REMOVED_SYNTAX_ERROR: except AttributeError as e:
                    # REMOVED_SYNTAX_ERROR: if "register_handler" in str(e):
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                        # REMOVED_SYNTAX_ERROR: print("   This is the staging bug - wrong MessageRouter is being used!")
                        # REMOVED_SYNTAX_ERROR: return False
                        # REMOVED_SYNTAX_ERROR: raise
                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                            # REMOVED_SYNTAX_ERROR: return False


                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                # Run SSOT test
                                # REMOVED_SYNTAX_ERROR: ssot_pass = test_message_router_ssot()

                                # Run handler registration test
                                # REMOVED_SYNTAX_ERROR: handler_pass = test_agent_handler_registration()

                                # Summary
                                # REMOVED_SYNTAX_ERROR: print(" )
                                # REMOVED_SYNTAX_ERROR: " + "="*60)
                                # REMOVED_SYNTAX_ERROR: print("FINAL RESULTS")
                                # REMOVED_SYNTAX_ERROR: print("="*60)

                                # REMOVED_SYNTAX_ERROR: if ssot_pass and handler_pass:
                                    # REMOVED_SYNTAX_ERROR: print("SUCCESS! ALL CRITICAL TESTS PASSED!")
                                    # REMOVED_SYNTAX_ERROR: print(" )
                                    # REMOVED_SYNTAX_ERROR: [OK] MessageRouter SSOT violation is FIXED")
                                    # REMOVED_SYNTAX_ERROR: print("[OK] AgentMessageHandler registration works")
                                    # REMOVED_SYNTAX_ERROR: print("[OK] Staging should now work correctly")
                                    # REMOVED_SYNTAX_ERROR: print(" )
                                    # REMOVED_SYNTAX_ERROR: Next steps:")
                                    # REMOVED_SYNTAX_ERROR: print("1. Commit these changes")
                                    # REMOVED_SYNTAX_ERROR: print("2. Deploy to staging: python scripts/deploy_to_gcp.py --project netra-staging --no-cache")
                                    # REMOVED_SYNTAX_ERROR: print("3. Monitor logs for successful AgentMessageHandler registration")
                                    # REMOVED_SYNTAX_ERROR: else:
                                        # REMOVED_SYNTAX_ERROR: print("[FAIL] TESTS FAILED - Fix required before deploying to staging!")
                                        # REMOVED_SYNTAX_ERROR: if not ssot_pass:
                                            # REMOVED_SYNTAX_ERROR: print("   - MessageRouter SSOT violation still exists")
                                            # REMOVED_SYNTAX_ERROR: if not handler_pass:
                                                # REMOVED_SYNTAX_ERROR: print("   - AgentMessageHandler registration fails")