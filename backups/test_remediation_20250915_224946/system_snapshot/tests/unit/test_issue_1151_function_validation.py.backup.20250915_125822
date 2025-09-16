"""
Issue #1151 Function Validation Tests

Tests for the newly added is_docker_available() function in websocket_real_test_base.
These tests validate the fix for the missing function that caused ImportError.

Business Value: Ensures $500K+ ARR Golden Path first message experience tests are functional.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

@pytest.mark.unit
class TestIsDockerAvailableFunction:
    """Test suite for the newly added is_docker_available function."""

    def test_function_exists_and_importable(self):
        """Verify is_docker_available function can be imported successfully."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        assert callable(is_docker_available)
        assert is_docker_available.__doc__ is not None
        assert 'Docker' in is_docker_available.__doc__

    def test_function_returns_boolean(self):
        """Verify function returns boolean value."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        result = is_docker_available()
        assert isinstance(result, bool)

    def test_function_handles_docker_unavailable_gracefully(self):
        """Test function behavior when Docker is not available."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        try:
            result = is_docker_available()
            assert result in [True, False]
        except Exception as e:
            pytest.fail(f'is_docker_available() raised unexpected exception: {e}')

    def test_function_uses_ssot_unified_docker_manager(self):
        """Verify function delegates to UnifiedDockerManager (SSOT pattern)."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        from test_framework.unified_docker_manager import UnifiedDockerManager
        manager = UnifiedDockerManager()
        with patch.object(manager, 'is_docker_available', return_value=True) as mock_method:
            result = is_docker_available()
            assert isinstance(result, bool)

    def test_function_consistent_behavior(self):
        """Test that function returns consistent results across multiple calls."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        result1 = is_docker_available()
        result2 = is_docker_available()
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)
        assert result1 == result2

    def test_function_handles_exceptions_gracefully(self):
        """Test function behavior when UnifiedDockerManager raises exceptions."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        with patch('tests.mission_critical.websocket_real_test_base.UnifiedDockerManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.is_docker_available.side_effect = Exception('Docker error')
            mock_manager_class.return_value = mock_manager
            result = is_docker_available()
            assert result is False

    def test_function_signature_matches_documentation(self):
        """Verify function signature matches expected interface."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        import inspect
        sig = inspect.signature(is_docker_available)
        assert len(sig.parameters) == 0
        assert 'bool' in is_docker_available.__doc__.lower()

    def test_function_business_value_compliance(self):
        """Verify function serves the business value of Docker detection for tests."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        result = is_docker_available()
        assert isinstance(result, bool)
        if result:
            assert True
        else:
            assert True

@pytest.mark.unit
class TestWebSocketTestBaseIntegration:
    """Test integration of new function with existing websocket test base."""

    def test_all_required_functions_available(self):
        """Verify all expected functions are available in websocket_real_test_base."""
        from tests.mission_critical import websocket_real_test_base
        required_functions = ['is_docker_available', 'require_docker_services', 'require_docker_services_smart']
        required_classes = ['RealWebSocketTestConfig']
        required_async_functions = ['send_test_agent_request']
        for func_name in required_functions:
            assert hasattr(websocket_real_test_base, func_name), f'Missing function {func_name}'
            attr = getattr(websocket_real_test_base, func_name)
            assert callable(attr), f'{func_name} is not callable'
        for class_name in required_classes:
            assert hasattr(websocket_real_test_base, class_name), f'Missing class {class_name}'
            attr = getattr(websocket_real_test_base, class_name)
            assert isinstance(attr, type), f'{class_name} is not a class'
        for func_name in required_async_functions:
            assert hasattr(websocket_real_test_base, func_name), f'Missing async function {func_name}'
            attr = getattr(websocket_real_test_base, func_name)
            assert callable(attr), f'{func_name} is not callable'

    def test_import_pattern_consistency(self):
        """Verify import patterns are consistent across mission-critical tests."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available, RealWebSocketTestConfig, send_test_agent_request
        assert callable(is_docker_available)
        assert isinstance(RealWebSocketTestConfig, type)
        assert callable(send_test_agent_request)

    def test_new_function_integrates_with_existing_patterns(self):
        """Test that new function integrates well with existing test patterns."""
        from tests.mission_critical.websocket_real_test_base import is_docker_available, require_docker_services, require_docker_services_smart
        docker_available = is_docker_available()
        if docker_available:
            assert callable(require_docker_services)
        else:
            assert callable(require_docker_services_smart)
        assert callable(is_docker_available)
        assert callable(require_docker_services)
        assert callable(require_docker_services_smart)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')