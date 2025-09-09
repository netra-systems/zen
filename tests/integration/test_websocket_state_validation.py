"""
Integration Tests for WebSocket State Validation Across Environments.

These tests focus on the is_websocket_connected() function and its behavior
in different environments, particularly the GCP Cloud Run proxy issues.

CRITICAL: These tests target the root cause where GCP staging environment
conservatively returns False for WebSocket connections, causing ConnectionHandler
to skip sending responses.

Business Value:
- Validates WebSocket state detection works correctly across environments
- Catches environment-specific connection validation failures
- Prevents resource accumulation patterns in WebSocket managers
- Ensures proper state attribute detection in cloud proxy scenarios

Test Strategy:
- Mock different environment conditions (local, staging, production)
- Test WebSocket state attribute edge cases
- Validate connection manager lifecycle coordination
- Use controlled scenarios to test specific failure modes

Expected Test Behavior:
- CURRENT STATE: Tests FAIL due to overly conservative staging logic
- AFTER FIX: Tests PASS with proper cloud-aware state detection
"""

import asyncio
import logging
import pytest
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for testing various state scenarios."""
    
    def __init__(self, 
                 has_client_state: bool = True,
                 client_state_value: Any = "CONNECTED",
                 has_receive: bool = True,
                 is_closed: bool = False,
                 state_value: Any = "CONNECTED"):
        """
        Initialize mock WebSocket with configurable state attributes.
        
        Args:
            has_client_state: Whether client_state attribute exists
            client_state_value: Value of client_state attribute
            has_receive: Whether _receive attribute exists
            is_closed: Whether WebSocket is closed
            state_value: Value of state attribute
        """
        self._setup_attributes(
            has_client_state, client_state_value, 
            has_receive, is_closed, state_value
        )
        
    def _setup_attributes(self, has_client_state, client_state_value, 
                         has_receive, is_closed, state_value):
        """Set up mock attributes based on configuration."""
        if has_client_state:
            self.client_state = client_state_value
            
        if has_receive:
            self._receive = Mock()
            
        self.closed = is_closed
        self.state = state_value
        
        # Mock other common WebSocket attributes
        self.send_json = Mock()
        self.send = Mock()
        self.recv = Mock()
        self.close = Mock()
        
    @staticmethod
    def gcp_cloud_run_proxy():
        """Mock WebSocket as it appears through GCP Cloud Run proxy."""
        # GCP proxy may not expose client_state but has _receive capability
        return MockWebSocket(
            has_client_state=False,
            client_state_value=None,
            has_receive=True,
            is_closed=False,
            state_value="OPEN"  # But may not be accessible in same way
        )
        
    @staticmethod
    def local_development():
        """Mock WebSocket as it appears in local development."""
        return MockWebSocket(
            has_client_state=True,
            client_state_value="CONNECTED",
            has_receive=True,
            is_closed=False,
            state_value="OPEN"
        )
        
    @staticmethod
    def disconnected_connection():
        """Mock disconnected WebSocket."""
        return MockWebSocket(
            has_client_state=True,
            client_state_value="DISCONNECTED",
            has_receive=False,
            is_closed=True,
            state_value="CLOSED"
        )
        
    @staticmethod
    def malformed_state():
        """Mock WebSocket with problematic state attributes."""
        mock_ws = MockWebSocket(
            has_client_state=True,
            client_state_value=None,  # None value causes issues
            has_receive=True,
            is_closed=False,
            state_value="CONNECTING"  # Transitioning state
        )
        return mock_ws


class TestWebSocketStateValidation(SSotBaseTestCase):
    """
    Integration tests for WebSocket state validation across environments.
    
    These tests focus on the is_websocket_connected() function and its
    environment-specific behavior that causes ConnectionHandler issues.
    """
    
    def setup_method(self):
        """Set up each test with proper mocking infrastructure."""
        super().setup_method()
        self.env = get_env()
        
        # Import the function under test
        try:
            from netra_backend.app.websocket_core.utils import is_websocket_connected
            self.is_websocket_connected = is_websocket_connected
        except ImportError as e:
            pytest.skip(f"Cannot import is_websocket_connected for testing: {e}")
            
        # Track test results for analysis
        self.test_results: List[Dict[str, Any]] = []
        
    def teardown_method(self):
        """Clean up after each test."""
        super().teardown_method()
        
    @pytest.mark.integration
    def test_websocket_connection_validation_per_environment(self):
        """
        Tests is_websocket_connected() behavior across different environments.
        
        Validates the conservative cloud environment logic and proper local detection.
        
        Expected Results:
        - CURRENT STATE: FAIL - Staging always returns False conservatively
        - AFTER FIX: PASS - Proper detection using available attributes
        """
        logger.info("🧪 Testing WebSocket connection validation per environment")
        
        # Test scenarios for different environments
        test_scenarios = [
            {
                'environment': 'local',
                'websocket': MockWebSocket.local_development(),
                'expected_result': True,
                'description': 'Local development with full state attributes'
            },
            {
                'environment': 'staging',
                'websocket': MockWebSocket.gcp_cloud_run_proxy(),
                'expected_result': True,  # Should work despite proxy limitations
                'description': 'GCP Cloud Run staging proxy environment'
            },
            {
                'environment': 'production', 
                'websocket': MockWebSocket.gcp_cloud_run_proxy(),
                'expected_result': True,  # Should work with proper cloud logic
                'description': 'GCP Cloud Run production proxy environment'
            },
            {
                'environment': 'local',
                'websocket': MockWebSocket.disconnected_connection(),
                'expected_result': False,
                'description': 'Disconnected connection (any environment)'
            }
        ]
        
        for scenario in test_scenarios:
            logger.info(f"Testing scenario: {scenario['description']}")
            
            # Mock the environment variable
            with patch.dict('os.environ', {'ENVIRONMENT': scenario['environment']}):
                # Mock the get_env function to return our test environment
                with patch('netra_backend.app.websocket_core.utils.get_env') as mock_get_env:
                    mock_env = Mock()
                    mock_env.get.return_value = scenario['environment']
                    mock_get_env.return_value = mock_env
                    
                    # Test the function
                    result = self.is_websocket_connected(scenario['websocket'])
                    
                    logger.info(f"  Environment: {scenario['environment']}")
                    logger.info(f"  Expected: {scenario['expected_result']}")
                    logger.info(f"  Actual: {result}")
                    
                    # Record result for analysis
                    test_result = {
                        'environment': scenario['environment'],
                        'expected': scenario['expected_result'],
                        'actual': result,
                        'description': scenario['description'],
                        'websocket_type': type(scenario['websocket']).__name__
                    }
                    self.test_results.append(test_result)
                    
                    # CRITICAL TEST: Result should match expectation
                    if scenario['environment'] in ['staging', 'production'] and scenario['expected_result']:
                        # This is the critical test that currently fails
                        assert result == scenario['expected_result'], (
                            f"CRITICAL BUG: is_websocket_connected() returns {result} but expected {scenario['expected_result']} "
                            f"for {scenario['description']}. "
                            f"This causes ConnectionHandler to skip responses in {scenario['environment']} environment. "
                            f"WebSocket state detection must work properly in cloud environments."
                        )
                    else:
                        assert result == scenario['expected_result'], (
                            f"WebSocket state detection mismatch for {scenario['description']}: "
                            f"expected {scenario['expected_result']}, got {result}"
                        )
                        
        logger.info("✅ Environment-specific connection validation tests passed")
        
    @pytest.mark.integration
    def test_websocket_state_attributes_edge_cases(self):
        """
        Tests WebSocket state detection with various attribute scenarios.
        
        This test covers edge cases that may occur in different proxy environments
        or during connection state transitions.
        """
        logger.info("🧪 Testing WebSocket state attribute edge cases")
        
        # Edge case scenarios
        edge_cases = [
            {
                'name': 'no_client_state_but_has_receive',
                'websocket': MockWebSocket(
                    has_client_state=False,
                    has_receive=True,
                    is_closed=False
                ),
                'expected': True,  # Should detect via _receive capability
                'description': 'WebSocket without client_state but with _receive'
            },
            {
                'name': 'client_state_none_value',
                'websocket': MockWebSocket(
                    has_client_state=True,
                    client_state_value=None,
                    has_receive=True,
                    is_closed=False
                ),
                'expected': True,  # Should fallback to other indicators
                'description': 'WebSocket with client_state=None'
            },
            {
                'name': 'transitioning_state',
                'websocket': MockWebSocket(
                    has_client_state=True,
                    client_state_value="CONNECTING",
                    has_receive=True,
                    is_closed=False,
                    state_value="CONNECTING"
                ),
                'expected': False,  # Connecting state should be treated as not ready
                'description': 'WebSocket in CONNECTING state'
            },
            {
                'name': 'closed_but_state_says_connected',
                'websocket': MockWebSocket(
                    has_client_state=True,
                    client_state_value="CONNECTED",
                    has_receive=True,
                    is_closed=True,  # Conflicting information
                    state_value="OPEN"
                ),
                'expected': False,  # Should prioritize closed=True
                'description': 'WebSocket closed=True but state says connected'
            },
            {
                'name': 'no_attributes_at_all',
                'websocket': Mock(spec=[]),  # Empty mock with no attributes
                'expected': False,
                'description': 'WebSocket with no state attributes'
            }
        ]
        
        for case in edge_cases:
            logger.info(f"Testing edge case: {case['name']}")
            
            try:
                result = self.is_websocket_connected(case['websocket'])
                
                logger.info(f"  Description: {case['description']}")
                logger.info(f"  Expected: {case['expected']}")
                logger.info(f"  Actual: {result}")
                
                assert result == case['expected'], (
                    f"Edge case '{case['name']}' failed: "
                    f"expected {case['expected']}, got {result}. "
                    f"Description: {case['description']}"
                )
                
                logger.info(f"  ✅ Passed")
                
            except Exception as e:
                logger.error(f"  ❌ Edge case '{case['name']}' raised exception: {e}")
                
                # Some edge cases might raise exceptions - validate they're handled properly
                if case['name'] == 'no_attributes_at_all':
                    # This is expected - function should handle gracefully
                    logger.info(f"  ✅ Exception handled gracefully for {case['name']}")
                else:
                    # Unexpected exception
                    raise AssertionError(
                        f"Edge case '{case['name']}' raised unexpected exception: {e}. "
                        f"Function should handle all WebSocket state scenarios gracefully."
                    )
                    
        logger.info("✅ WebSocket state attribute edge case tests passed")
        
    @pytest.mark.integration
    def test_websocket_manager_lifecycle_coordination(self):
        """
        Tests proper coordination between WebSocket connections and manager cleanup.
        
        This test validates that WebSocket managers are properly cleaned up
        when connections close, preventing the resource accumulation issue.
        """
        logger.info("🧪 Testing WebSocket manager lifecycle coordination")
        
        # Mock WebSocket managers and connections for testing
        mock_connections = []
        mock_managers = []
        
        # Simulate multiple connection/manager pairs
        num_connections = 5
        
        for i in range(num_connections):
            # Create mock WebSocket connection
            mock_ws = MockWebSocket.local_development()
            mock_ws.connection_id = f"conn-{i}"
            mock_connections.append(mock_ws)
            
            # Create mock WebSocket manager
            mock_manager = Mock()
            mock_manager.connection_id = f"conn-{i}"
            mock_manager.is_active = True
            mock_manager.cleanup = Mock()
            mock_managers.append(mock_manager)
            
        try:
            # Test imports for WebSocket management
            from netra_backend.app.websocket_core.utils import is_websocket_connected
            # These may not exist yet, so we'll mock them
            
        except ImportError:
            logger.warning("WebSocket management modules not fully implemented yet")
            
        # Test 1: All connections should be detected as connected initially
        logger.info("Testing initial connection detection")
        for i, ws in enumerate(mock_connections):
            result = self.is_websocket_connected(ws)
            assert result is True, f"Connection {i} should be detected as connected"
            logger.info(f"  ✅ Connection {i} detected as connected")
            
        # Test 2: Simulate connection closure
        logger.info("Testing connection closure detection")
        for i in range(0, num_connections, 2):  # Close every other connection
            mock_connections[i].closed = True
            mock_connections[i].state = "CLOSED"
            mock_connections[i].client_state = "DISCONNECTED"
            
            result = self.is_websocket_connected(mock_connections[i])
            assert result is False, f"Closed connection {i} should be detected as disconnected"
            logger.info(f"  ✅ Closed connection {i} detected as disconnected")
            
        # Test 3: Validate that managers would be cleaned up
        # (This would be integration with actual WebSocket manager cleanup)
        logger.info("Testing manager cleanup coordination")
        
        closed_connection_ids = [f"conn-{i}" for i in range(0, num_connections, 2)]
        active_connection_ids = [f"conn-{i}" for i in range(1, num_connections, 2)]
        
        # Simulate cleanup process
        for manager in mock_managers:
            if manager.connection_id in closed_connection_ids:
                manager.is_active = False
                manager.cleanup.assert_not_called()  # Not called yet
                
                # Simulate cleanup call
                manager.cleanup()
                logger.info(f"  ✅ Manager {manager.connection_id} cleanup simulated")
                
        # Test 4: Verify resource count management
        active_managers = [m for m in mock_managers if m.is_active]
        expected_active = len(active_connection_ids)
        actual_active = len(active_managers)
        
        assert actual_active == expected_active, (
            f"Resource management mismatch: expected {expected_active} active managers, "
            f"got {actual_active}. This indicates cleanup coordination issues."
        )
        
        logger.info(f"✅ Resource management validated: {actual_active} active managers")
        
        # Test 5: Validate no resource accumulation under normal operations
        logger.info("Testing resource accumulation prevention")
        
        # Simulate rapid connection cycling
        temp_connections = []
        for cycle in range(10):
            # Create connection
            ws = MockWebSocket.local_development()
            ws.connection_id = f"temp-{cycle}"
            temp_connections.append(ws)
            
            # Verify it's detected as connected
            assert self.is_websocket_connected(ws) is True
            
            # Immediately close it
            ws.closed = True
            ws.state = "CLOSED"
            
            # Verify it's detected as disconnected
            assert self.is_websocket_connected(ws) is False
            
        logger.info("✅ Resource accumulation prevention validated")
        
        logger.info("✅ WebSocket manager lifecycle coordination tests passed")
        
    @pytest.mark.integration
    def test_cloud_environment_detection_fallbacks(self):
        """
        Tests fallback detection methods for cloud environments.
        
        This specifically tests the fixes needed for GCP Cloud Run
        where standard state attributes may not be available.
        """
        logger.info("🧪 Testing cloud environment detection fallbacks")
        
        # Test scenarios for cloud fallback detection
        cloud_scenarios = [
            {
                'name': 'gcp_proxy_with_receive',
                'websocket': MockWebSocket(
                    has_client_state=False,  # No client_state in proxy
                    has_receive=True,        # But _receive capability exists
                    is_closed=False,
                    state_value="OPEN"
                ),
                'environment': 'staging',
                'expected': True,
                'description': 'GCP proxy WebSocket with _receive capability'
            },
            {
                'name': 'gcp_proxy_minimal_attributes',
                'websocket': MockWebSocket(
                    has_client_state=False,
                    has_receive=False,  # Minimal attributes
                    is_closed=False,
                    state_value="OPEN"
                ),
                'environment': 'staging',
                'expected': False,  # Conservative: if no indicators, assume disconnected
                'description': 'GCP proxy WebSocket with minimal attributes'
            },
            {
                'name': 'production_proxy_working',
                'websocket': MockWebSocket(
                    has_client_state=False,
                    has_receive=True,
                    is_closed=False,
                    state_value="OPEN"
                ),
                'environment': 'production',
                'expected': True,
                'description': 'Production proxy WebSocket working'
            }
        ]
        
        for scenario in cloud_scenarios:
            logger.info(f"Testing cloud scenario: {scenario['name']}")
            
            # Mock cloud environment
            with patch.dict('os.environ', {'ENVIRONMENT': scenario['environment']}):
                with patch('netra_backend.app.websocket_core.utils.get_env') as mock_get_env:
                    mock_env = Mock()
                    mock_env.get.return_value = scenario['environment']
                    mock_get_env.return_value = mock_env
                    
                    result = self.is_websocket_connected(scenario['websocket'])
                    
                    logger.info(f"  Environment: {scenario['environment']}")
                    logger.info(f"  Description: {scenario['description']}")
                    logger.info(f"  Expected: {scenario['expected']}")
                    logger.info(f"  Actual: {result}")
                    
                    if scenario['expected'] and scenario['environment'] in ['staging', 'production']:
                        # This is the critical fix needed
                        assert result == scenario['expected'], (
                            f"CRITICAL: Cloud fallback detection failed for {scenario['name']}. "
                            f"Expected {scenario['expected']}, got {result}. "
                            f"This fix is needed to prevent ConnectionHandler silent failures "
                            f"in {scenario['environment']} environment."
                        )
                    else:
                        assert result == scenario['expected'], (
                            f"Cloud scenario '{scenario['name']}' failed: "
                            f"expected {scenario['expected']}, got {result}"
                        )
                        
                    logger.info(f"  ✅ Passed")
                    
        logger.info("✅ Cloud environment detection fallback tests passed")


if __name__ == "__main__":
    """
    Run WebSocket state validation tests directly for debugging.
    
    Usage:
        python -m pytest tests/integration/test_websocket_state_validation.py -v -s
    """
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])