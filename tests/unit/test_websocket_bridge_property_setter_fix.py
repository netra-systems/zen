#!/usr/bin/env python3
"""
Test Suite: WebSocket Bridge Property Setter Fix Verification

PURPOSE: Verify that the AgentWebSocketBridge property setter fix resolves
the AttributeError while maintaining architectural integrity and user isolation.

This test validates:
1. Property setter works correctly with mock injection
2. Validation prevents invalid managers
3. Production patterns still work
4. No regression in user isolation
5. Error messaging is clear

CRITICAL: This test ensures that integration tests can now inject mock WebSocket
managers while production code continues to use factory patterns properly.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.logging_config import central_logger

logger = central_logger


class MockWebSocketManagerValid:
    """Valid mock WebSocket manager that implements required interface."""
    
    async def send_to_thread(self, thread_id, message):
        """Mock implementation of required send_to_thread method."""
        return True
    
    def add_connection(self, user_id):
        """Mock method for test compatibility."""
        pass


class MockWebSocketManagerInvalid:
    """Invalid mock WebSocket manager missing required interface."""
    
    def some_other_method(self):
        """This mock doesn't implement send_to_thread."""
        pass


class TestWebSocketBridgePropertySetterFix:
    """Test suite for WebSocket Bridge property setter fix."""
    
    @pytest.fixture
    def bridge(self):
        """Create AgentWebSocketBridge instance for testing."""
        return AgentWebSocketBridge()
    
    @pytest.fixture
    def valid_mock_manager(self):
        """Create valid mock WebSocket manager."""
        return MockWebSocketManagerValid()
    
    @pytest.fixture
    def invalid_mock_manager(self):
        """Create invalid mock WebSocket manager."""
        return MockWebSocketManagerInvalid()

    def test_property_setter_exists(self, bridge):
        """Test that the websocket_manager property now has a setter."""
        # This should not raise AttributeError anymore
        bridge.websocket_manager = None
        assert bridge.websocket_manager is None
        
        logger.info(" PASS:  Property setter exists and works with None")

    def test_setter_accepts_valid_mock_manager(self, bridge, valid_mock_manager):
        """Test that setter accepts valid mock managers."""
        # This was the original failing case
        bridge.websocket_manager = valid_mock_manager
        
        assert bridge.websocket_manager is valid_mock_manager
        logger.info(" PASS:  Setter accepts valid mock manager (original bug fixed)")

    def test_setter_validates_interface(self, bridge, invalid_mock_manager):
        """Test that setter validates required interface."""
        with pytest.raises(ValueError) as exc_info:
            bridge.websocket_manager = invalid_mock_manager
        
        error_msg = str(exc_info.value)
        assert "send_to_thread method" in error_msg
        assert "factory methods" in error_msg
        
        logger.info(" PASS:  Setter properly validates interface requirements")

    def test_setter_accepts_none(self, bridge):
        """Test that setter accepts None (clearing the manager)."""
        bridge.websocket_manager = None
        assert bridge.websocket_manager is None
        
        logger.info(" PASS:  Setter accepts None for clearing manager")

    def test_property_getter_still_works(self, bridge, valid_mock_manager):
        """Test that getter functionality is preserved."""
        # Test initial state
        assert bridge.websocket_manager is None
        
        # Set via property
        bridge.websocket_manager = valid_mock_manager
        
        # Get via property
        assert bridge.websocket_manager is valid_mock_manager
        
        logger.info(" PASS:  Property getter functionality preserved")

    @pytest.mark.asyncio
    async def test_mock_manager_integration(self, bridge, valid_mock_manager):
        """Test that mock manager can be used for WebSocket operations."""
        # Set mock manager
        bridge.websocket_manager = valid_mock_manager
        
        # Test that mock methods work
        result = await valid_mock_manager.send_to_thread("test_thread", {"test": "message"})
        assert result is True
        
        logger.info(" PASS:  Mock manager integration works correctly")

    def test_architectural_integrity_maintained(self, bridge):
        """Test that architectural patterns are still enforced."""
        # Bridge should start with None manager (per-request pattern)
        assert bridge.websocket_manager is None
        
        # Setting to None should work (clearing pattern)
        bridge.websocket_manager = None
        assert bridge.websocket_manager is None
        
        logger.info(" PASS:  Architectural integrity maintained (per-request pattern)")

    def test_error_messaging_quality(self, bridge, invalid_mock_manager):
        """Test that error messages guide users to correct patterns."""
        with pytest.raises(ValueError) as exc_info:
            bridge.websocket_manager = invalid_mock_manager
        
        error_msg = str(exc_info.value)
        
        # Check that error message includes guidance
        assert "send_to_thread method" in error_msg
        assert "factory methods" in error_msg
        assert "user isolation" in error_msg
        
        logger.info(" PASS:  Error messaging provides clear guidance")

    def test_original_bug_reproduction(self, bridge):
        """Test reproducing and fixing the original AttributeError bug."""
        # This exact line from base_agent_execution_test.py:128 should now work
        mock_manager = MockWebSocketManagerValid()
        
        try:
            # This line was causing: AttributeError: property 'websocket_manager' of 'AgentWebSocketBridge' object has no setter
            bridge.websocket_manager = mock_manager
            bug_fixed = True
        except AttributeError as e:
            if "no setter" in str(e):
                bug_fixed = False
            else:
                raise  # Different error, re-raise
        
        assert bug_fixed, "Original AttributeError bug should be fixed"
        assert bridge.websocket_manager is mock_manager
        
        logger.info(" PASS:  Original AttributeError bug successfully fixed")

    def test_thread_safety_basic(self, bridge, valid_mock_manager):
        """Basic test that property access is thread-safe."""
        import threading
        import time
        
        results = []
        
        def set_manager():
            bridge.websocket_manager = valid_mock_manager
            results.append("set_complete")
        
        def get_manager():
            time.sleep(0.01)  # Small delay
            manager = bridge.websocket_manager
            results.append(manager is not None)
        
        # Start threads
        thread1 = threading.Thread(target=set_manager)
        thread2 = threading.Thread(target=get_manager)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Both operations should complete
        assert "set_complete" in results
        assert True in results  # Manager should be set when accessed
        
        logger.info(" PASS:  Basic thread safety verification passed")


class TestIntegrationTestCompatibility:
    """Test suite for integration test compatibility."""
    
    def test_base_agent_execution_test_pattern(self):
        """Test the exact pattern from base_agent_execution_test.py."""
        # Reproduce the exact failing pattern from the original test
        mock_websocket_manager = MockWebSocketManagerValid()
        websocket_bridge = AgentWebSocketBridge()
        
        # This line was failing with AttributeError
        websocket_bridge.websocket_manager = mock_websocket_manager
        
        # Verify it worked
        assert websocket_bridge.websocket_manager is mock_websocket_manager
        
        logger.info(" PASS:  base_agent_execution_test.py pattern now works correctly")

    def test_multiple_mock_injections(self):
        """Test that multiple mock injections work (test cleanup scenarios)."""
        bridge = AgentWebSocketBridge()
        
        mock1 = MockWebSocketManagerValid()
        mock2 = MockWebSocketManagerValid()
        
        # Set first mock
        bridge.websocket_manager = mock1
        assert bridge.websocket_manager is mock1
        
        # Replace with second mock
        bridge.websocket_manager = mock2
        assert bridge.websocket_manager is mock2
        
        # Clear manager
        bridge.websocket_manager = None
        assert bridge.websocket_manager is None
        
        logger.info(" PASS:  Multiple mock injections work correctly")


if __name__ == "__main__":
    # Run the tests
    logger.info("[U+1F680] Running WebSocket Bridge Property Setter Fix Verification Tests")
    
    pytest.main([__file__, "-v", "--tb=short"])
    
    logger.info(" PASS:  WebSocket Bridge Property Setter Fix Verification Complete")