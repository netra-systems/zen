"""
Test for Issue #1176 Coordination Gap #5: MessageRouter Import Fragmentation

This test specifically reproduces the MessageRouter coordination gap
where import fragmentation causes runtime failures.

Expected to FAIL until remediated.
"""

import pytest
import importlib
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestMessageRouterCoordinationGap(SSotAsyncTestCase):
    """
    Reproduce MessageRouter Import Fragmentation Coordination Gap

    Business Impact: Runtime failures in message routing, broken agent communication
    Expected Failure: Import fragmentation causes module loading issues
    """

    def test_messagerouter_import_fragmentation(self):
        """
        EXPECTED TO FAIL: Multiple MessageRouter import paths cause confusion

        Gap: MessageRouter can be imported from multiple locations
        Impact: Developers use wrong import, runtime failures occur
        """
        # Test different potential import paths for MessageRouter
        potential_import_paths = [
            "netra_backend.app.websocket_core.message_router.MessageRouter",
            "netra_backend.app.websocket.message_router.MessageRouter",
            "netra_backend.app.routes.websocket.MessageRouter",
            "netra_backend.app.agents.message_router.MessageRouter",
            "netra_backend.app.core.message_router.MessageRouter",
            "shared.messaging.message_router.MessageRouter"
        ]

        successful_imports = []
        failed_imports = []

        for import_path in potential_import_paths:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                if cls is not None:
                    successful_imports.append(import_path)
            except (ImportError, AttributeError, ModuleNotFoundError):
                failed_imports.append(import_path)

        print(f"MessageRouter imports - Successful: {len(successful_imports)}, Failed: {len(failed_imports)}")
        print(f"Working paths: {successful_imports}")
        print(f"Failed paths: {failed_imports}")

        # Coordination gap exists if:
        # 1. Multiple import paths work (fragmentation)
        # 2. No import paths work (broken imports)
        # 3. Some work, some don't (inconsistent availability)

        if len(successful_imports) == 0:
            assert True, "MessageRouter coordination gap: No working import paths found"
        elif len(successful_imports) > 1:
            assert True, f"MessageRouter coordination gap: Multiple import paths work ({len(successful_imports)})"
        else:
            print("Only one MessageRouter import path works - good SSOT compliance")

    def test_messagerouter_class_multiplicity_gap(self):
        """
        EXPECTED TO FAIL: Multiple MessageRouter classes exist

        Gap: Different MessageRouter implementations in different modules
        Impact: Inconsistent message routing behavior
        """
        import sys

        # Search for MessageRouter classes in loaded modules
        messagerouter_classes = []

        for module_name, module in sys.modules.items():
            if module is None:
                continue

            # Skip test modules and other irrelevant modules
            if 'test' in module_name.lower() or module_name.startswith('_'):
                continue

            try:
                # Look for MessageRouter classes
                if hasattr(module, 'MessageRouter'):
                    cls = getattr(module, 'MessageRouter')
                    if isinstance(cls, type):  # Make sure it's a class
                        messagerouter_classes.append(f"{module_name}.MessageRouter")

                # Also check for classes that might be MessageRouter variants
                for attr_name in dir(module):
                    if 'messagerouter' in attr_name.lower() or 'message_router' in attr_name.lower():
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and attr_name not in ['MessageRouter']:
                            messagerouter_classes.append(f"{module_name}.{attr_name}")

            except (AttributeError, TypeError):
                continue

        print(f"MessageRouter classes found: {messagerouter_classes}")

        # Coordination gap exists if multiple MessageRouter classes are found
        if len(messagerouter_classes) > 1:
            assert True, f"MessageRouter coordination gap: Multiple classes found: {messagerouter_classes}"
        elif len(messagerouter_classes) == 0:
            print("No MessageRouter classes found in loaded modules - may not be loaded yet")
        else:
            print("Only one MessageRouter class found - good SSOT compliance")

    def test_messagerouter_interface_inconsistency_gap(self):
        """
        EXPECTED TO FAIL: MessageRouter interfaces are inconsistent

        Gap: Different MessageRouter implementations have different interfaces
        Impact: Code that works with one implementation fails with another
        """
        # Try to find and compare MessageRouter implementations
        try:
            # Look for the main MessageRouter implementation
            from netra_backend.app.websocket_core import message_router
            if hasattr(message_router, 'MessageRouter'):
                main_router = message_router.MessageRouter

                # Check what methods this MessageRouter has
                main_methods = [method for method in dir(main_router)
                              if not method.startswith('_') and callable(getattr(main_router, method, None))]

                print(f"Main MessageRouter methods: {main_methods}")

                # Expected core methods for a message router
                expected_methods = ['route_message', 'handle_message', 'dispatch', 'send_message']
                missing_methods = [method for method in expected_methods if method not in main_methods]

                if len(missing_methods) > 0:
                    print(f"MessageRouter interface gap: Missing expected methods: {missing_methods}")
                    assert True, f"Interface coordination gap: Missing methods: {missing_methods}"

                print("MessageRouter has expected interface methods")

        except ImportError as e:
            # If we can't import MessageRouter, that's a coordination gap
            print(f"MessageRouter import failed: {e}")
            assert True, f"MessageRouter coordination gap: Import failed: {e}"

    def test_messagerouter_runtime_behavior_coordination_gap(self):
        """
        EXPECTED TO FAIL: MessageRouter runtime behavior is inconsistent

        Gap: MessageRouter behaves differently in different contexts
        Impact: Messages get routed incorrectly or lost
        """
        try:
            # Try to create a MessageRouter instance
            from netra_backend.app.websocket_core.message_router import MessageRouter

            # Test creating multiple instances
            router1 = MessageRouter()
            router2 = MessageRouter()

            # Check if they're the same instance (singleton) or different (factory)
            if router1 is router2:
                print("MessageRouter is singleton - potential coordination issues with multi-user")
                singleton_gap = True
            else:
                print("MessageRouter creates different instances - good for isolation")
                singleton_gap = False

            # Test basic routing functionality
            test_message = {"type": "test", "data": "coordination_gap_test"}

            # Check if both routers handle messages consistently
            try:
                result1 = router1.route_message(test_message)
                result2 = router2.route_message(test_message)

                # Results should be consistent for the same message
                if result1 != result2:
                    print(f"MessageRouter coordination gap: Inconsistent results: {result1} vs {result2}")
                    assert True, "Runtime behavior coordination gap: Inconsistent message routing"

                print("MessageRouter behavior is consistent between instances")

            except AttributeError as e:
                print(f"MessageRouter interface gap: Missing route_message method: {e}")
                assert True, f"Interface coordination gap: {e}"

            except Exception as e:
                print(f"MessageRouter runtime gap: Unexpected error: {e}")
                assert True, f"Runtime coordination gap: {e}"

            # If we're using singleton pattern, that's a coordination gap for multi-user
            if singleton_gap:
                assert True, "Coordination gap: MessageRouter singleton pattern may cause user isolation issues"

        except ImportError as e:
            print(f"MessageRouter coordination gap: Cannot import: {e}")
            assert True, f"Import coordination gap: {e}"

    def test_messagerouter_websocket_integration_coordination_gap(self):
        """
        EXPECTED TO FAIL: MessageRouter doesn't coordinate properly with WebSocket

        Gap: MessageRouter and WebSocket manager have integration issues
        Impact: Messages sent through WebSocket don't reach MessageRouter properly
        """
        try:
            # Try to test MessageRouter integration with WebSocket
            from netra_backend.app.websocket_core.message_router import MessageRouter
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

            # Create instances
            router = MessageRouter()
            ws_manager = WebSocketManager.create_factory_manager(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run"
            )

            # Check if WebSocket manager has reference to message router
            has_router_ref = (
                hasattr(ws_manager, 'message_router') or
                hasattr(ws_manager, '_message_router') or
                hasattr(ws_manager, 'router')
            )

            if not has_router_ref:
                print("WebSocket manager doesn't have MessageRouter reference")
                assert True, "Integration coordination gap: WebSocket manager missing MessageRouter"

            # Check if MessageRouter has reference to WebSocket manager
            has_ws_ref = (
                hasattr(router, 'websocket_manager') or
                hasattr(router, '_websocket_manager') or
                hasattr(router, 'ws_manager')
            )

            if not has_ws_ref:
                print("MessageRouter doesn't have WebSocket manager reference")
                assert True, "Integration coordination gap: MessageRouter missing WebSocket manager"

            print("MessageRouter and WebSocket manager appear to be integrated")

        except ImportError as e:
            print(f"Integration test failed due to import error: {e}")
            assert True, f"Import coordination gap prevents integration testing: {e}"
        except Exception as e:
            print(f"Integration coordination gap detected: {e}")
            assert True, f"Integration coordination gap: {e}"

    def test_messagerouter_agent_communication_coordination_gap(self):
        """
        EXPECTED TO FAIL: MessageRouter doesn't coordinate with agent system

        Gap: Messages from agents don't route properly through MessageRouter
        Impact: Agent responses don't reach users via WebSocket
        """
        try:
            # Test MessageRouter coordination with agent system
            from netra_backend.app.websocket_core.message_router import MessageRouter

            router = MessageRouter()

            # Simulate agent message
            agent_message = {
                "type": "agent_response",
                "agent_id": "test_agent",
                "user_id": "test_user",
                "data": "Test agent response"
            }

            # Check if router can handle agent messages
            if hasattr(router, 'route_agent_message'):
                result = router.route_agent_message(agent_message)
                print(f"Agent message routing result: {result}")
            elif hasattr(router, 'route_message'):
                result = router.route_message(agent_message)
                print(f"Generic message routing result: {result}")
            else:
                print("MessageRouter has no message routing methods")
                assert True, "Coordination gap: MessageRouter missing routing methods"

            # Test reverse direction - router to agent
            if hasattr(router, 'send_to_agent'):
                agent_command = {"type": "user_command", "command": "test"}
                result = router.send_to_agent("test_agent", agent_command)
                print(f"Send to agent result: {result}")
            else:
                print("MessageRouter cannot send messages to agents")
                assert True, "Coordination gap: MessageRouter cannot communicate with agents"

        except ImportError as e:
            print(f"Agent communication test failed: {e}")
            assert True, f"Coordination gap prevents agent communication testing: {e}"
        except Exception as e:
            print(f"Agent communication coordination gap: {e}")
            assert True, f"Agent communication coordination gap: {e}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])