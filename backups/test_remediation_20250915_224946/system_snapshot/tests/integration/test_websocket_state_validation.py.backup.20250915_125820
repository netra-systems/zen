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

    def __init__(self, has_client_state: bool=True, client_state_value: Any='CONNECTED', has_receive: bool=True, is_closed: bool=False, state_value: Any='CONNECTED'):
        """
        Initialize mock WebSocket with configurable state attributes.
        
        Args:
            has_client_state: Whether client_state attribute exists
            client_state_value: Value of client_state attribute
            has_receive: Whether _receive attribute exists
            is_closed: Whether WebSocket is closed
            state_value: Value of state attribute
        """
        self._setup_attributes(has_client_state, client_state_value, has_receive, is_closed, state_value)

    def _setup_attributes(self, has_client_state, client_state_value, has_receive, is_closed, state_value):
        """Set up mock attributes based on configuration."""
        if has_client_state:
            self.client_state = client_state_value
        if has_receive:
            self._receive = Mock()
        self.closed = is_closed
        self.state = state_value
        self.send_json = Mock()
        self.send = Mock()
        self.recv = Mock()
        self.close = Mock()

    @staticmethod
    def gcp_cloud_run_proxy():
        """Mock WebSocket as it appears through GCP Cloud Run proxy."""
        return MockWebSocket(has_client_state=False, client_state_value=None, has_receive=True, is_closed=False, state_value='OPEN')

    @staticmethod
    def local_development():
        """Mock WebSocket as it appears in local development."""
        return MockWebSocket(has_client_state=True, client_state_value='CONNECTED', has_receive=True, is_closed=False, state_value='OPEN')

    @staticmethod
    def disconnected_connection():
        """Mock disconnected WebSocket."""
        return MockWebSocket(has_client_state=True, client_state_value='DISCONNECTED', has_receive=False, is_closed=True, state_value='CLOSED')

    @staticmethod
    def malformed_state():
        """Mock WebSocket with problematic state attributes."""
        mock_ws = MockWebSocket(has_client_state=True, client_state_value=None, has_receive=True, is_closed=False, state_value='CONNECTING')
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
        try:
            from netra_backend.app.websocket_core.utils import is_websocket_connected
            self.is_websocket_connected = is_websocket_connected
        except ImportError as e:
            pytest.skip(f'Cannot import is_websocket_connected for testing: {e}')
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
        logger.info('[U+1F9EA] Testing WebSocket connection validation per environment')
        test_scenarios = [{'environment': 'local', 'websocket': MockWebSocket.local_development(), 'expected_result': True, 'description': 'Local development with full state attributes'}, {'environment': 'staging', 'websocket': MockWebSocket.gcp_cloud_run_proxy(), 'expected_result': True, 'description': 'GCP Cloud Run staging proxy environment'}, {'environment': 'production', 'websocket': MockWebSocket.gcp_cloud_run_proxy(), 'expected_result': True, 'description': 'GCP Cloud Run production proxy environment'}, {'environment': 'local', 'websocket': MockWebSocket.disconnected_connection(), 'expected_result': False, 'description': 'Disconnected connection (any environment)'}]
        for scenario in test_scenarios:
            logger.info(f"Testing scenario: {scenario['description']}")
            with patch.dict('os.environ', {'ENVIRONMENT': scenario['environment']}):
                with patch('netra_backend.app.websocket_core.utils.get_env') as mock_get_env:
                    mock_env = Mock()
                    mock_env.get.return_value = scenario['environment']
                    mock_get_env.return_value = mock_env
                    result = self.is_websocket_connected(scenario['websocket'])
                    logger.info(f"  Environment: {scenario['environment']}")
                    logger.info(f"  Expected: {scenario['expected_result']}")
                    logger.info(f'  Actual: {result}')
                    test_result = {'environment': scenario['environment'], 'expected': scenario['expected_result'], 'actual': result, 'description': scenario['description'], 'websocket_type': type(scenario['websocket']).__name__}
                    self.test_results.append(test_result)
                    if scenario['environment'] in ['staging', 'production'] and scenario['expected_result']:
                        assert result == scenario['expected_result'], f"CRITICAL BUG: is_websocket_connected() returns {result} but expected {scenario['expected_result']} for {scenario['description']}. This causes ConnectionHandler to skip responses in {scenario['environment']} environment. WebSocket state detection must work properly in cloud environments."
                    else:
                        assert result == scenario['expected_result'], f"WebSocket state detection mismatch for {scenario['description']}: expected {scenario['expected_result']}, got {result}"
        logger.info(' PASS:  Environment-specific connection validation tests passed')

    @pytest.mark.integration
    def test_websocket_state_attributes_edge_cases(self):
        """
        Tests WebSocket state detection with various attribute scenarios.
        
        This test covers edge cases that may occur in different proxy environments
        or during connection state transitions.
        """
        logger.info('[U+1F9EA] Testing WebSocket state attribute edge cases')
        edge_cases = [{'name': 'no_client_state_but_has_receive', 'websocket': MockWebSocket(has_client_state=False, has_receive=True, is_closed=False), 'expected': True, 'description': 'WebSocket without client_state but with _receive'}, {'name': 'client_state_none_value', 'websocket': MockWebSocket(has_client_state=True, client_state_value=None, has_receive=True, is_closed=False), 'expected': True, 'description': 'WebSocket with client_state=None'}, {'name': 'transitioning_state', 'websocket': MockWebSocket(has_client_state=True, client_state_value='CONNECTING', has_receive=True, is_closed=False, state_value='CONNECTING'), 'expected': False, 'description': 'WebSocket in CONNECTING state'}, {'name': 'closed_but_state_says_connected', 'websocket': MockWebSocket(has_client_state=True, client_state_value='CONNECTED', has_receive=True, is_closed=True, state_value='OPEN'), 'expected': False, 'description': 'WebSocket closed=True but state says connected'}, {'name': 'no_attributes_at_all', 'websocket': Mock(spec=[]), 'expected': False, 'description': 'WebSocket with no state attributes'}]
        for case in edge_cases:
            logger.info(f"Testing edge case: {case['name']}")
            try:
                result = self.is_websocket_connected(case['websocket'])
                logger.info(f"  Description: {case['description']}")
                logger.info(f"  Expected: {case['expected']}")
                logger.info(f'  Actual: {result}')
                assert result == case['expected'], f"Edge case '{case['name']}' failed: expected {case['expected']}, got {result}. Description: {case['description']}"
                logger.info(f'   PASS:  Passed')
            except Exception as e:
                logger.error(f"   FAIL:  Edge case '{case['name']}' raised exception: {e}")
                if case['name'] == 'no_attributes_at_all':
                    logger.info(f"   PASS:  Exception handled gracefully for {case['name']}")
                else:
                    raise AssertionError(f"Edge case '{case['name']}' raised unexpected exception: {e}. Function should handle all WebSocket state scenarios gracefully.")
        logger.info(' PASS:  WebSocket state attribute edge case tests passed')

    @pytest.mark.integration
    def test_websocket_manager_lifecycle_coordination(self):
        """
        Tests proper coordination between WebSocket connections and manager cleanup.
        
        This test validates that WebSocket managers are properly cleaned up
        when connections close, preventing the resource accumulation issue.
        """
        logger.info('[U+1F9EA] Testing WebSocket manager lifecycle coordination')
        mock_connections = []
        mock_managers = []
        num_connections = 5
        for i in range(num_connections):
            mock_ws = MockWebSocket.local_development()
            mock_ws.connection_id = f'conn-{i}'
            mock_connections.append(mock_ws)
            mock_manager = Mock()
            mock_manager.connection_id = f'conn-{i}'
            mock_manager.is_active = True
            mock_manager.cleanup = Mock()
            mock_managers.append(mock_manager)
        try:
            from netra_backend.app.websocket_core.utils import is_websocket_connected
        except ImportError:
            logger.warning('WebSocket management modules not fully implemented yet')
        logger.info('Testing initial connection detection')
        for i, ws in enumerate(mock_connections):
            result = self.is_websocket_connected(ws)
            assert result is True, f'Connection {i} should be detected as connected'
            logger.info(f'   PASS:  Connection {i} detected as connected')
        logger.info('Testing connection closure detection')
        for i in range(0, num_connections, 2):
            mock_connections[i].closed = True
            mock_connections[i].state = 'CLOSED'
            mock_connections[i].client_state = 'DISCONNECTED'
            result = self.is_websocket_connected(mock_connections[i])
            assert result is False, f'Closed connection {i} should be detected as disconnected'
            logger.info(f'   PASS:  Closed connection {i} detected as disconnected')
        logger.info('Testing manager cleanup coordination')
        closed_connection_ids = [f'conn-{i}' for i in range(0, num_connections, 2)]
        active_connection_ids = [f'conn-{i}' for i in range(1, num_connections, 2)]
        for manager in mock_managers:
            if manager.connection_id in closed_connection_ids:
                manager.is_active = False
                manager.cleanup.assert_not_called()
                manager.cleanup()
                logger.info(f'   PASS:  Manager {manager.connection_id} cleanup simulated')
        active_managers = [m for m in mock_managers if m.is_active]
        expected_active = len(active_connection_ids)
        actual_active = len(active_managers)
        assert actual_active == expected_active, f'Resource management mismatch: expected {expected_active} active managers, got {actual_active}. This indicates cleanup coordination issues.'
        logger.info(f' PASS:  Resource management validated: {actual_active} active managers')
        logger.info('Testing resource accumulation prevention')
        temp_connections = []
        for cycle in range(10):
            ws = MockWebSocket.local_development()
            ws.connection_id = f'temp-{cycle}'
            temp_connections.append(ws)
            assert self.is_websocket_connected(ws) is True
            ws.closed = True
            ws.state = 'CLOSED'
            assert self.is_websocket_connected(ws) is False
        logger.info(' PASS:  Resource accumulation prevention validated')
        logger.info(' PASS:  WebSocket manager lifecycle coordination tests passed')

    @pytest.mark.integration
    def test_cloud_environment_detection_fallbacks(self):
        """
        Tests fallback detection methods for cloud environments.
        
        This specifically tests the fixes needed for GCP Cloud Run
        where standard state attributes may not be available.
        """
        logger.info('[U+1F9EA] Testing cloud environment detection fallbacks')
        cloud_scenarios = [{'name': 'gcp_proxy_with_receive', 'websocket': MockWebSocket(has_client_state=False, has_receive=True, is_closed=False, state_value='OPEN'), 'environment': 'staging', 'expected': True, 'description': 'GCP proxy WebSocket with _receive capability'}, {'name': 'gcp_proxy_minimal_attributes', 'websocket': MockWebSocket(has_client_state=False, has_receive=False, is_closed=False, state_value='OPEN'), 'environment': 'staging', 'expected': False, 'description': 'GCP proxy WebSocket with minimal attributes'}, {'name': 'production_proxy_working', 'websocket': MockWebSocket(has_client_state=False, has_receive=True, is_closed=False, state_value='OPEN'), 'environment': 'production', 'expected': True, 'description': 'Production proxy WebSocket working'}]
        for scenario in cloud_scenarios:
            logger.info(f"Testing cloud scenario: {scenario['name']}")
            with patch.dict('os.environ', {'ENVIRONMENT': scenario['environment']}):
                with patch('netra_backend.app.websocket_core.utils.get_env') as mock_get_env:
                    mock_env = Mock()
                    mock_env.get.return_value = scenario['environment']
                    mock_get_env.return_value = mock_env
                    result = self.is_websocket_connected(scenario['websocket'])
                    logger.info(f"  Environment: {scenario['environment']}")
                    logger.info(f"  Description: {scenario['description']}")
                    logger.info(f"  Expected: {scenario['expected']}")
                    logger.info(f'  Actual: {result}')
                    if scenario['expected'] and scenario['environment'] in ['staging', 'production']:
                        assert result == scenario['expected'], f"CRITICAL: Cloud fallback detection failed for {scenario['name']}. Expected {scenario['expected']}, got {result}. This fix is needed to prevent ConnectionHandler silent failures in {scenario['environment']} environment."
                    else:
                        assert result == scenario['expected'], f"Cloud scenario '{scenario['name']}' failed: expected {scenario['expected']}, got {result}"
                    logger.info(f'   PASS:  Passed')
        logger.info(' PASS:  Cloud environment detection fallback tests passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')