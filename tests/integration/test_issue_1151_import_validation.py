"""
Issue #1151 Import Validation Tests

Tests to verify that the previously failing imports in test_first_message_experience.py
now succeed after adding the missing is_docker_available function.

Business Value: Ensures mission-critical first message experience tests can be collected and executed.
"""
import pytest
import sys
import importlib.util
from pathlib import Path
from typing import Any, Dict, List
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class TestFirstMessageExperienceImports:
    """Test suite for import resolution in previously failing test file."""

    def test_first_message_experience_imports_resolve(self):
        """Test that test_first_message_experience.py imports resolve without errors."""
        test_file = project_root / 'tests' / 'mission_critical' / 'test_first_message_experience.py'
        assert test_file.exists(), f'Test file not found: {test_file}'
        spec = importlib.util.spec_from_file_location('test_first_message_experience', test_file)
        assert spec is not None, 'Could not create module spec'
        assert spec.loader is not None, 'Module spec has no loader'
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except ImportError as e:
            pytest.fail(f'ImportError still occurring after fix: {e}')
        except Exception as e:
            print(f'Note: Non-import error during module loading (expected): {e}')
        assert hasattr(module, 'is_docker_available'), 'is_docker_available not found in module'

    def test_specific_failing_import_statement(self):
        """Test the exact import statement that was causing the Issue #1151 failure."""
        try:
            from tests.mission_critical.websocket_real_test_base import is_docker_available, RealWebSocketTestConfig, send_test_agent_request
            assert callable(is_docker_available), 'is_docker_available is not callable'
            assert isinstance(RealWebSocketTestConfig, type), 'RealWebSocketTestConfig is not a class'
            assert callable(send_test_agent_request), 'send_test_agent_request is not callable'
        except ImportError as e:
            pytest.fail(f'Issue #1151 fix failed - ImportError still occurs: {e}')

    def test_websocket_real_test_base_module_completeness(self):
        """Verify websocket_real_test_base module has all expected exports."""
        import tests.mission_critical.websocket_real_test_base as base_module
        expected_exports = {'is_docker_available': 'function', 'require_docker_services': 'function', 'require_docker_services_smart': 'function', 'RealWebSocketTestConfig': 'class', 'send_test_agent_request': 'function', 'RealWebSocketTestBase': 'class', 'get_websocket_test_base': 'function'}
        missing_exports = []
        wrong_type_exports = []
        for export_name, expected_type in expected_exports.items():
            if not hasattr(base_module, export_name):
                missing_exports.append(export_name)
                continue
            attr = getattr(base_module, export_name)
            if expected_type == 'function' and (not callable(attr)):
                wrong_type_exports.append(f'{export_name} (expected function, got {type(attr)})')
            elif expected_type == 'class' and (not isinstance(attr, type)):
                wrong_type_exports.append(f'{export_name} (expected class, got {type(attr)})')
        error_messages = []
        if missing_exports:
            error_messages.append(f'Missing exports: {missing_exports}')
        if wrong_type_exports:
            error_messages.append(f'Wrong type exports: {wrong_type_exports}')
        if error_messages:
            pytest.fail(f"Module completeness issues: {'; '.join(error_messages)}")

    def test_import_no_side_effects(self):
        """Verify that importing the function doesn't cause unwanted side effects."""
        import sys
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            from tests.mission_critical.websocket_real_test_base import is_docker_available
            import_warnings = [warning for warning in w if 'websocket_real_test_base' in str(warning.filename)]
            if import_warnings:
                warning_messages = [str(warning.message) for warning in import_warnings]
                print(f'Warnings during import (informational): {warning_messages}')
        assert 'tests.mission_critical.websocket_real_test_base' in sys.modules
        assert callable(is_docker_available)

    def test_circular_import_prevention(self):
        """Verify no circular import issues exist with the new function."""
        import sys
        modules_to_clear = ['tests.mission_critical.websocket_real_test_base', 'test_framework.unified_docker_manager']
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]
        try:
            from tests.mission_critical.websocket_real_test_base import is_docker_available
            from test_framework.unified_docker_manager import UnifiedDockerManager
            assert callable(is_docker_available)
            assert isinstance(UnifiedDockerManager, type)
        except ImportError as e:
            pytest.fail(f'Circular import or dependency issue: {e}')

class TestMissionCriticalTestCollectability:
    """Test that mission-critical tests can be collected after the fix."""

    def test_mission_critical_tests_discoverable(self):
        """Test that pytest can discover mission-critical tests after the fix."""
        import subprocess
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(project_root)
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/mission_critical/', '--collect-only', '-q'], capture_output=True, text=True, timeout=30)
            assert result.returncode in [0, 5], f'Test collection failed with code {result.returncode}: {result.stderr}'
            assert 'ImportError' not in result.stderr, f'ImportError during collection: {result.stderr}'
            assert "cannot import name 'is_docker_available'" not in result.stderr
        finally:
            os.chdir(original_cwd)

    def test_first_message_experience_test_collectible(self):
        """Test that the specific previously failing test file can be collected."""
        import subprocess
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(project_root)
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/mission_critical/test_first_message_experience.py', '--collect-only', '-v'], capture_output=True, text=True, timeout=30)
            assert result.returncode in [0, 5], f'Test collection failed: {result.stderr}'
            assert "cannot import name 'is_docker_available'" not in result.stderr
            assert 'ImportError' not in result.stderr, f'ImportError still present: {result.stderr}'
            if result.returncode == 0:
                assert 'collected' in result.stdout or 'test session starts' in result.stdout
        finally:
            os.chdir(original_cwd)

    def test_websocket_tests_collection_no_regression(self):
        """Test that other WebSocket tests still collect properly (no regression)."""
        import subprocess
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(project_root)
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/mission_critical/', '-k', 'websocket', '--collect-only', '-v'], capture_output=True, text=True, timeout=30)
            assert result.returncode in [0, 5], f'WebSocket test collection failed: {result.stderr}'
            assert 'ImportError' not in result.stderr, f'Import regression in WebSocket tests: {result.stderr}'
        finally:
            os.chdir(original_cwd)

class TestBackwardsCompatibility:
    """Test that existing functionality is not broken by the fix."""

    def test_existing_docker_functions_still_work(self):
        """Verify existing Docker detection functions are not broken."""
        from tests.mission_critical.websocket_real_test_base import require_docker_services, require_docker_services_smart
        assert callable(require_docker_services)
        assert callable(require_docker_services_smart)
        assert require_docker_services.__doc__ is not None
        assert require_docker_services_smart.__doc__ is not None

    def test_real_websocket_test_config_unchanged(self):
        """Test that RealWebSocketTestConfig class is not affected by the fix."""
        from tests.mission_critical.websocket_real_test_base import RealWebSocketTestConfig
        config = RealWebSocketTestConfig()
        expected_attributes = ['backend_url', 'websocket_url', 'connection_timeout', 'event_timeout', 'max_retries', 'docker_startup_timeout']
        for attr in expected_attributes:
            assert hasattr(config, attr), f'Missing attribute {attr} in RealWebSocketTestConfig'

    def test_send_test_agent_request_unchanged(self):
        """Test that send_test_agent_request function is not affected."""
        from tests.mission_critical.websocket_real_test_base import send_test_agent_request
        import inspect
        assert callable(send_test_agent_request)
        assert inspect.iscoroutinefunction(send_test_agent_request)

    def test_unified_docker_manager_integration_preserved(self):
        """Test that integration with UnifiedDockerManager is preserved."""
        from test_framework.unified_docker_manager import UnifiedDockerManager
        from tests.mission_critical.websocket_real_test_base import is_docker_available
        manager = UnifiedDockerManager()
        manager_result = manager.is_docker_available()
        function_result = is_docker_available()
        assert isinstance(manager_result, bool)
        assert isinstance(function_result, bool)
        assert manager_result == function_result
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')