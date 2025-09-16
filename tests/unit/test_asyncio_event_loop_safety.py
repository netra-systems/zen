"""
Unit Tests for Asyncio Event Loop Safety

Tests to prevent regression of nested event loop issues and similar asyncio problems.
"""
import asyncio
import sys
import threading
import pytest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.utils.asyncio_test_utils import AsyncioTestUtils, EventLoopTestError, AsyncioRegressionTester, EventLoopValidator, create_mock_async_function_with_nested_run, create_mock_async_function_proper, run_in_thread_with_loop
from unittest.mock import patch

@pytest.mark.unit
class AsyncioSafetyChecksTests:
    """Test suite for asyncio safety checks"""

    def test_detect_event_loop_running_no_loop(self):
        """Test detection when no event loop is running"""
        assert AsyncioTestUtils.is_event_loop_running() is False

    @pytest.mark.asyncio
    async def test_detect_event_loop_running_with_loop(self):
        """Test detection when event loop is running"""
        assert AsyncioTestUtils.is_event_loop_running() is True

    def test_detect_nested_asyncio_run_in_bad_function(self):
        """Test detection of nested asyncio.run() in problematic function"""
        bad_func = create_mock_async_function_with_nested_run()
        assert AsyncioTestUtils.detect_nested_asyncio_run(bad_func) is True

    def test_detect_nested_asyncio_run_in_good_function(self):
        """Test no false positive for proper async function"""
        good_func = create_mock_async_function_proper()
        assert AsyncioTestUtils.detect_nested_asyncio_run(good_func) is False

    @pytest.mark.asyncio
    async def test_assert_no_nested_asyncio_run_context_manager(self):
        """Test the assert_no_nested_asyncio_run context manager"""
        with pytest.raises(EventLoopTestError) as exc_info:
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                asyncio.run(asyncio.sleep(0))
        assert 'Nested asyncio.run() detected' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_assert_no_nested_asyncio_run_allows_await(self):
        """Test context manager allows proper await usage"""
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            await asyncio.sleep(0)

    def test_create_test_event_loop(self):
        """Test event loop creation utility"""
        loop = AsyncioTestUtils.create_test_event_loop()
        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)
        loop.close()

    @pytest.mark.asyncio
    async def test_simulate_nested_call_with_bad_function(self):
        """Test simulating nested call with problematic function"""

        async def bad_func():
            return asyncio.run(asyncio.sleep(0))
        success, error = await AsyncioTestUtils.simulate_nested_call(bad_func)
        assert success is False
        assert error is not None
        assert 'cannot be called from a running event loop' in str(error)

    @pytest.mark.asyncio
    async def test_simulate_nested_call_with_good_function(self):
        """Test simulating nested call with proper function"""

        async def good_func():
            await asyncio.sleep(0)
            return 'success'
        success, error = await AsyncioTestUtils.simulate_nested_call(good_func)
        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_test_async_function_safety(self):
        """Test the comprehensive async function safety checker"""

        async def test_func():
            await asyncio.sleep(0)
            return 'ok'
        results = await AsyncioTestUtils.test_async_function_safety(test_func)
        assert results['has_nested_asyncio_run'] is False
        assert results['executes_successfully'] is True
        assert results['error'] is None
        assert results['is_coroutine_function'] is True

@pytest.mark.unit
class AsyncioRegressionTesterTests:
    """Test the regression tester functionality"""

    @pytest.mark.asyncio
    async def test_regression_tester_with_good_function(self):
        """Test regression tester with proper async function"""
        tester = AsyncioRegressionTester()

        async def good_func():
            await asyncio.sleep(0)
            return 'ok'
        passed = await tester.test_function_for_nested_loops(good_func, 'good_func')
        assert passed is True
        assert len(tester.failures) == 0
        assert len(tester.results) == 1

    @pytest.mark.asyncio
    async def test_regression_tester_report_generation(self):
        """Test report generation"""
        tester = AsyncioRegressionTester()

        async def func1():
            await asyncio.sleep(0)
        await tester.test_function_for_nested_loops(func1, 'func1')
        report = tester.generate_report()
        assert 'Asyncio Regression Test Report' in report
        assert 'Total tests run: 1' in report
        assert 'Passed: 1' in report
        assert 'Failed: 0' in report

@pytest.mark.unit
class EventLoopValidatorTests:
    """Test the module validation functionality"""

    def test_validate_module_with_test_file(self, tmp_path):
        """Test module validation with a test Python file"""
        test_file = tmp_path / 'test_module.py'
        test_file.write_text('\nimport asyncio\nfrom netra_backend.app.core.unified_error_handler import UnifiedErrorHandler\nfrom netra_backend.app.db.database_manager import DatabaseManager\nfrom netra_backend.app.clients.auth_client_core import AuthServiceClient\nfrom shared.isolated_environment import get_env\n\nasync def good_async_function():\n    result = await some_operation()\n    return result\n\nasync def bad_async_function():\n    # This is problematic\n    result = asyncio.run(some_operation())\n    return result\n\ndef sync_function():\n    return asyncio.run(some_operation())\n\nasync def some_operation():\n    return "data"\n')
        results = EventLoopValidator.validate_module(str(test_file))
        assert results['module'] == str(test_file)
        assert results['async_functions'] == 3
        assert results['potential_issues'] == 1
        assert len(results['issues']) == 1
        assert results['issues'][0]['type'] == 'nested_asyncio_run'
        assert results['issues'][0]['function'] == 'bad_async_function'

@pytest.mark.unit
class NestedEventLoopPatternsTests:
    """Test specific patterns that caused issues in production"""

    def test_startup_fixes_pattern(self):
        """Test the pattern that caused backend startup deadlock"""

        async def validate_tools_async():
            return await asyncio.sleep(0)

        def validate_tools_wrapper():
            return asyncio.run(validate_tools_async())
        assert AsyncioTestUtils.detect_nested_asyncio_run(validate_tools_wrapper) is False

        async def test_from_async():
            with pytest.raises(RuntimeError) as exc_info:
                validate_tools_wrapper()
            assert 'cannot be called from a running event loop' in str(exc_info.value)
        asyncio.run(test_from_async())

    def test_jwt_handler_pattern(self):
        """Test the JWT handler pattern with try/except around asyncio.run()"""

        def jwt_function_with_fallback():
            try:
                result = asyncio.run(async_jwt_operation())
            except RuntimeError:
                result = 'fallback'
            return result

        async def async_jwt_operation():
            return 'jwt_token'
        assert jwt_function_with_fallback() == 'jwt_token'

        async def test_from_async():
            with patch('asyncio.run', side_effect=RuntimeError('cannot be called from a running event loop')):
                result = jwt_function_with_fallback()
                assert result == 'fallback'
        asyncio.run(test_from_async())

    def test_admin_tool_validation_pattern(self):
        """Test admin tool validation backward compatibility pattern"""

        class AdminToolValidator:

            async def validate_async(self, data):
                await asyncio.sleep(0)
                return {'valid': True}

            def validate(self, data):
                return asyncio.run(self.validate_async(data))
        validator = AdminToolValidator()
        result = validator.validate({'test': 'data'})
        assert result['valid'] is True

        async def test_from_async():
            with pytest.raises(RuntimeError) as exc_info:
                validator.validate({'test': 'data'})
            assert 'cannot be called from a running event loop' in str(exc_info.value)
        asyncio.run(test_from_async())

@pytest.mark.unit
class ThreadSafeExecutionTests:
    """Test thread-safe execution patterns"""

    def test_run_in_thread_with_loop_sync_function(self):
        """Test running sync function in thread with event loop"""

        def sync_func():
            return 'sync_result'
        result = run_in_thread_with_loop(sync_func)
        assert result == 'sync_result'

    def test_run_in_thread_with_loop_async_function(self):
        """Test running async function in thread with event loop"""

        async def async_func():
            await asyncio.sleep(0.01)
            return 'async_result'
        result = run_in_thread_with_loop(async_func)
        assert result == 'async_result'

    def test_run_in_thread_with_loop_error_handling(self):
        """Test error handling in thread execution"""

        def error_func():
            raise ValueError('Test error')
        with pytest.raises(ValueError) as exc_info:
            run_in_thread_with_loop(error_func)
        assert 'Test error' in str(exc_info.value)

@pytest.mark.unit
class EventLoopIsolationTests:
    """Test event loop isolation patterns"""

    def test_isolated_event_loop_execution(self):
        """Test that we can isolate event loop execution"""
        results = []

        def run_isolated():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def isolated_task():
                await asyncio.sleep(0.01)
                return 'isolated'
            try:
                result = loop.run_until_complete(isolated_task())
                results.append(result)
            finally:
                loop.close()
        thread = threading.Thread(target=run_isolated)
        thread.start()
        thread.join()
        assert results[0] == 'isolated'

    def test_multiple_isolated_loops(self):
        """Test running multiple isolated event loops"""
        results = []

        def run_loop(index):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def task():
                await asyncio.sleep(0.01 * index)
                return f'loop_{index}'
            try:
                result = loop.run_until_complete(task())
                results.append(result)
            finally:
                loop.close()
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_loop, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(results) == 3
        assert all((f'loop_{i}' in results for i in range(3)))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')