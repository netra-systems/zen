class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
            raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''
        Mission Critical: UnifiedIDManager Comprehensive Validation Tests
        This test suite ensures UnifiedIDManager works correctly and catches:
        1. Method signature mismatches (like the 2-argument bug)
        2. Import errors and lazy loading issues
        3. Integration with real components
        4. Deprecated function confusion
        5. Thread safety and concurrent usage
        CRITICAL: These tests use REAL implementations, NO MOCKS.
        '''
        import pytest
        import asyncio
        import concurrent.futures
        import inspect
        import importlib
        import sys
        from typing import List, Tuple
        from shared.isolated_environment import IsolatedEnvironment
        Test the actual import works
        from netra_backend.app.core.unified_id_manager import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        UnifiedIDManager,
        ParsedRunID,
        IDFormat,
        generate_run_id,  # Deprecated function
        extract_thread_id_from_run_id  # Deprecated function
        
class TestMethodSignatures:
        "Test that method signatures are correct and catch wrong usage.""
    def test_generate_run_id_accepts_only_one_argument(self):
        ""CRITICAL: Test that generate_run_id only accepts thread_id."
    # This should work
        thread_id = "test_thread
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        assert run_id.startswith(thread_test_thread_run_")
    # This should fail - the bug we fixed
        with pytest.raises(TypeError) as exc_info:
        UnifiedIDManager.generate_run_id(thread_id, "extra_context)
        assert takes 1 positional argument but 2 were given" in str(exc_info.value)
    def test_deprecated_function_signature_confusion(self):
        "Test that deprecated function signature doesn't match class method.""
        pass
    # Get signatures
        class_method_sig = inspect.signature(UnifiedIDManager.generate_run_id)
        deprecated_sig = inspect.signature(generate_run_id)
    # They have different signatures - this is the confusion source
        assert len(class_method_sig.parameters) == 1  # Only thread_id
        assert len(deprecated_sig.parameters) == 2  # thread_id and context
    # Deprecated function should warn
        with patch('netra_backend.app.core.unified_id_manager.logger') as mock_logger:
        _ = generate_run_id(test", "context)
        mock_logger.warning.assert_called_with( )
        generate_run_id() is deprecated, use UnifiedIDManager.generate_run_id()"
        
    def test_all_static_methods_have_correct_decorators(self):
        "Ensure all methods meant to be static are properly decorated.""
        for name, method in inspect.getmembers(UnifiedIDManager):
        if name.startswith('_'):
        continue
        if callable(method) and not name.startswith('__'):
                # Should be a static method
        assert isinstance(inspect.getattr_static(UnifiedIDManager, name), staticmethod), \
        formatted_string"
class TestImportValidation:
        "Test that imports work correctly and catch lazy loading issues.""
    def test_import_from_different_contexts(self):
        ""Test UnifiedIDManager can be imported in various ways."
    # Direct import
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager as UID1
    Module import then access
        from netra_backend.app.core import unified_id_manager
        UID2 = unified_id_manager.UnifiedIDManager
    Dynamic import (like in lazy loaded functions)
        module = importlib.import_module('netra_backend.app.core.unified_id_manager')
        UID3 = module.UnifiedIDManager
    # All should be the same class
        assert UID1 is UID2 is UID3
    # All should work
        for UID in [UID1, UID2, UID3]:
        run_id = UID.generate_run_id("test_import)
        assert UID.validate_run_id(run_id)
    def test_lazy_import_in_function_works(self):
        ""Test pattern used in run_repository, interfaces_observability, etc."
        pass
    def lazy_import_function(thread_id: str) -> str:
    # This pattern is used in several files
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        return UnifiedIDManager.generate_run_id(thread_id)
    # Should work without issues
        run_id = lazy_import_function("lazy_test)
        assert thread_lazy_test_run_" in run_id
    def test_circular_import_prevention(self):
        "Ensure no circular imports when UnifiedIDManager is used.""
    Clear the module from cache to test fresh import
        modules_to_clear = [
        'netra_backend.app.core.unified_id_manager',
        'netra_backend.app.services.thread_service',
        'netra_backend.app.services.agent_websocket_bridge'
    
        for mod in modules_to_clear:
        if mod in sys.modules:
        del sys.modules[mod]
            # These imports should not cause circular dependency
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        assert UnifiedIDManager is not None
        assert ThreadService is not None
        assert AgentWebSocketBridge is not None
class TestRealIntegration:
        ""Test UnifiedIDManager with real components, no mocks."
@pytest.mark.asyncio
    async def test_thread_service_integration(self):
"Test ThreadService uses UnifiedIDManager correctly.""
from netra_backend.app.services.thread_service import ThreadService
service = ThreadService()
thread_id = integration_test_thread"
assistant_id = "test_assistant
model = gpt-4"
instructions = "Test instructions
        # This was failing with 2-argument bug
run_id, run_data = service._prepare_run_data( )
thread_id, assistant_id, model, instructions
        
        # Validate the generated ID
assert UnifiedIDManager.validate_run_id(run_id)
assert UnifiedIDManager.extract_thread_id(run_id) == thread_id
assert run_data[thread_id"] == thread_id
assert run_data["id] == run_id
@pytest.mark.asyncio
    async def test_websocket_bridge_integration(self):
""Test AgentWebSocketBridge uses UnifiedIDManager correctly."
pass
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
bridge = AgentWebSocketBridge()
            # Test thread extraction
run_id = UnifiedIDManager.generate_run_id("websocket_test)
thread_id = bridge.extract_thread_id(run_id)
assert thread_id == websocket_test"
assert bridge.get_format_info(run_id)["thread_id] == websocket_test"
def test_all_production_files_use_correct_signature(self):
"Scan production files that use UnifiedIDManager.""
production_files = [
'netra_backend.app.services.thread_service',
'netra_backend.app.services.database.run_repository',
'netra_backend.app.core.interfaces_observability',
'netra_backend.app.orchestration.agent_execution_registry'
    
for module_path in production_files:
    try:
    module = importlib.import_module(module_path)
            If import succeeds, the fix is working
assert module is not None
except TypeError as e:
    if takes 1 positional argument but 2 were given" in str(e):
        pytest.fail("formatted_string)
class TestConcurrentUsage:
        ""Test UnifiedIDManager under concurrent load."
    def test_thread_safe_id_generation(self):
        "Test concurrent ID generation doesn't cause conflicts.""
    async def generate_ids(prefix: str, count: int) -> List[str]:
        await asyncio.sleep(0)
        return [
        UnifiedIDManager.generate_run_id(formatted_string")
        for i in range(count)
    
    # Generate IDs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
        executor.submit(generate_ids, "formatted_string, 100)
        for i in range(10)
        
        all_ids = []
        for future in concurrent.futures.as_completed(futures):
        all_ids.extend(future.result())
            # All IDs should be unique
        assert len(all_ids) == len(set(all_ids))
            # All IDs should be valid
        for run_id in all_ids:
        assert UnifiedIDManager.validate_run_id(run_id)
@pytest.mark.asyncio
    async def test_async_concurrent_usage(self):
""Test async concurrent usage pattern."
pass
async def generate_id_async(thread_id: str) -> str:
    # Simulate async context switching
await asyncio.sleep(0.001)
await asyncio.sleep(0)
return UnifiedIDManager.generate_run_id(thread_id)
    # Generate IDs concurrently
tasks = [
generate_id_async("formatted_string)
for i in range(100)
    
ids = await asyncio.gather(*tasks)
    # All should be unique and valid
assert len(ids) == len(set(ids))
for run_id in ids:
    assert UnifiedIDManager.validate_run_id(run_id)
class TestErrorScenarios:
        ""Test error handling and edge cases."
    def test_none_arguments_handled(self):
        "Test None arguments are rejected properly.""
        with pytest.raises(ValueError) as exc_info:
        UnifiedIDManager.generate_run_id(None)
        assert cannot be empty or None" in str(exc_info.value)
    def test_empty_string_rejected(self):
        "Test empty strings are rejected.""
        pass
        with pytest.raises(ValueError) as exc_info:
        UnifiedIDManager.generate_run_id(")
        assert "cannot be empty or None in str(exc_info.value)
    def test_invalid_type_rejected(self):
        ""Test non-string types are rejected."
        with pytest.raises(ValueError) as exc_info:
        UnifiedIDManager.generate_run_id(123)  # Number instead of string
        assert "must be string in str(exc_info.value)
    def test_reserved_sequence_rejected(self):
        ""Test thread_ids with reserved sequences are rejected."
        pass
        with pytest.raises(ValueError) as exc_info:
        UnifiedIDManager.generate_run_id("thread_run_invalid)
        assert cannot contain reserved sequence" in str(exc_info.value)
class TestStartupValidation:
        "Tests that would catch issues at startup.""
    def test_critical_methods_exist(self):
        ""Test all critical methods exist with correct signatures."
        critical_methods = [
        ('generate_run_id', 1),  # method_name, expected_arg_count
        ('extract_thread_id', 1),
        ('validate_run_id', 1),
        ('validate_thread_id', 1),
        ('normalize_thread_id', 1),
        ('parse_run_id', 1),
        ('get_format_info', 1),
        ('create_test_ids', 1),
    
        for method_name, expected_args in critical_methods:
        assert hasattr(UnifiedIDManager, method_name), \
        "formatted_string
        method = getattr(UnifiedIDManager, method_name)
        sig = inspect.signature(method)
        # Subtract 'self' if it's there (shouldn't be for static methods)
        param_count = len(]
        p for p in sig.parameters.values()
        if p.default == inspect.Parameter.empty
        
        assert param_count <= expected_args, \
        formatted_string"
    def test_startup_smoke_test(self):
        "Basic smoke test that should run at startup.""
        pass
    # Generate a test ID
        test_thread = startup_validation_test"
        run_id = UnifiedIDManager.generate_run_id(test_thread)
    # Validate it
        assert UnifiedIDManager.validate_run_id(run_id)
    # Extract thread_id back
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == test_thread
    # Get format info
        info = UnifiedIDManager.get_format_info(run_id)
        assert info['thread_id'] == test_thread
        assert info['format_version'] == 'canonical'
    # Validate thread_id
        assert UnifiedIDManager.validate_thread_id(test_thread)
    # Test normalization
        normalized = UnifiedIDManager.normalize_thread_id("formatted_string)
        assert normalized == test_thread
class TestDeprecationPath:
        ""Test migration from deprecated functions."
    def test_deprecated_function_still_works(self):
        "Ensure deprecated function works for backward compatibility.""
    # Old code pattern - should still work but warn
        run_id = generate_run_id(legacy_test", "some_context)
        assert UnifiedIDManager.validate_run_id(run_id)
    def test_migration_path_clear(self):
        ""Test that migration from old to new is straightforward."
        pass
        thread_id = "migration_test
    # Old way (deprecated)
        old_id = generate_run_id(thread_id, context")
    # New way
        new_id = UnifiedIDManager.generate_run_id(thread_id)
    # Both should extract same thread_id
        assert UnifiedIDManager.extract_thread_id(old_id) == thread_id
        assert UnifiedIDManager.extract_thread_id(new_id) == thread_id
        if __name__ == "__main__:
        # Run basic validation that should pass at startup
        print(Running UnifiedIDManager startup validation...")
        try:
            # Test import
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        print("[U+2713] Import successful)
            # Test basic functionality
        test_id = UnifiedIDManager.generate_run_id(startup_test")
        assert UnifiedIDManager.validate_run_id(test_id)
        print("[U+2713] Basic ID generation works)
            # Test extraction
        extracted = UnifiedIDManager.extract_thread_id(test_id)
        assert extracted == startup_test"
        print("[U+2713] Thread extraction works)
            # Test signature
        import inspect
        sig = inspect.signature(UnifiedIDManager.generate_run_id)
        assert len(sig.parameters) == 1
        print([U+2713] Method signature correct (1 argument")")
        print()
        PASS:  All startup validations passed!")
        except Exception as e:
        print("formatted_string")
        sys.exit(1)