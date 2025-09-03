"""Test to reproduce MessageRouter register_handler bug

This test proves that the wrong MessageRouter is being used, causing
'register_handler' AttributeError in staging.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_message_router_has_wrong_interface():
    """Test that exposes the MessageRouter SSOT violation bug."""
    
    # Import the MessageRouter from websocket_core (the one get_message_router returns)
    from netra_backend.app.websocket_core.handlers import MessageRouter as CoreMessageRouter
    from netra_backend.app.websocket_core.handlers import get_message_router
    
    # Import the MessageRouter from services (the one expected by websocket.py)
    from netra_backend.app.services.websocket.message_router import MessageRouter as ServiceMessageRouter
    
    # Get the router instance that websocket.py uses
    router_instance = get_message_router()
    
    # Test 1: Verify the instance is from the wrong class
    assert isinstance(router_instance, CoreMessageRouter), "Router instance is CoreMessageRouter"
    assert not isinstance(router_instance, ServiceMessageRouter), "Router instance is NOT ServiceMessageRouter"
    
    # Test 2: Verify the method mismatch
    assert not hasattr(router_instance, 'register_handler'), "CoreMessageRouter does NOT have register_handler"
    assert hasattr(router_instance, 'add_handler'), "CoreMessageRouter has add_handler instead"
    
    # Test 3: Verify ServiceMessageRouter has the expected method
    service_router = ServiceMessageRouter()
    assert hasattr(service_router, 'register_handler'), "ServiceMessageRouter HAS register_handler"
    
    print("\nBUG CONFIRMED:")
    print(f"1. get_message_router() returns: {type(router_instance).__name__} from {type(router_instance).__module__}")
    print(f"2. This router has methods: {[m for m in dir(router_instance) if not m.startswith('_')]}")
    print(f"3. websocket.py expects 'register_handler' but router only has 'add_handler'")
    print(f"4. This is a SSOT violation - two MessageRouter classes with different interfaces")


def test_websocket_registration_will_fail():
    """Test that simulates the exact failure in websocket.py."""
    from netra_backend.app.websocket_core.handlers import get_message_router
    
    message_router = get_message_router()
    
    # This will raise AttributeError just like in staging
    with pytest.raises(AttributeError) as exc_info:
        # Simulate what websocket.py line 218 does
        mock_handler = object()  # Stand-in for AgentMessageHandler
        message_router.register_handler(mock_handler)
    
    assert "'MessageRouter' object has no attribute 'register_handler'" in str(exc_info.value)
    print(f"\nError reproduced: {exc_info.value}")


if __name__ == "__main__":
    print("Running MessageRouter bug reproduction tests...")
    test_message_router_has_wrong_interface()
    test_websocket_registration_will_fail()
    print("\nAll tests completed - bug confirmed!")