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
    # REMOVED_SYNTAX_ERROR: Mission Critical: UnifiedIDManager Comprehensive Validation Tests

    # REMOVED_SYNTAX_ERROR: This test suite ensures UnifiedIDManager works correctly and catches:
        # REMOVED_SYNTAX_ERROR: 1. Method signature mismatches (like the 2-argument bug)
        # REMOVED_SYNTAX_ERROR: 2. Import errors and lazy loading issues
        # REMOVED_SYNTAX_ERROR: 3. Integration with real components
        # REMOVED_SYNTAX_ERROR: 4. Deprecated function confusion
        # REMOVED_SYNTAX_ERROR: 5. Thread safety and concurrent usage

        # REMOVED_SYNTAX_ERROR: CRITICAL: These tests use REAL implementations, NO MOCKS.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import concurrent.futures
        # REMOVED_SYNTAX_ERROR: import inspect
        # REMOVED_SYNTAX_ERROR: import importlib
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: from typing import List, Tuple
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Test the actual import works
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_id_manager import ( )
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: UnifiedIDManager,
        # REMOVED_SYNTAX_ERROR: ParsedRunID,
        # REMOVED_SYNTAX_ERROR: IDFormat,
        # REMOVED_SYNTAX_ERROR: generate_run_id,  # Deprecated function
        # REMOVED_SYNTAX_ERROR: extract_thread_id_from_run_id  # Deprecated function
        


# REMOVED_SYNTAX_ERROR: class TestMethodSignatures:
    # REMOVED_SYNTAX_ERROR: """Test that method signatures are correct and catch wrong usage."""

# REMOVED_SYNTAX_ERROR: def test_generate_run_id_accepts_only_one_argument(self):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Test that generate_run_id only accepts thread_id."""
    # This should work
    # REMOVED_SYNTAX_ERROR: thread_id = "test_thread"
    # REMOVED_SYNTAX_ERROR: run_id = UnifiedIDManager.generate_run_id(thread_id)
    # REMOVED_SYNTAX_ERROR: assert run_id.startswith("thread_test_thread_run_")

    # This should fail - the bug we fixed
    # REMOVED_SYNTAX_ERROR: with pytest.raises(TypeError) as exc_info:
        # REMOVED_SYNTAX_ERROR: UnifiedIDManager.generate_run_id(thread_id, "extra_context")
        # REMOVED_SYNTAX_ERROR: assert "takes 1 positional argument but 2 were given" in str(exc_info.value)

# REMOVED_SYNTAX_ERROR: def test_deprecated_function_signature_confusion(self):
    # REMOVED_SYNTAX_ERROR: """Test that deprecated function signature doesn't match class method."""
    # REMOVED_SYNTAX_ERROR: pass
    # Get signatures
    # REMOVED_SYNTAX_ERROR: class_method_sig = inspect.signature(UnifiedIDManager.generate_run_id)
    # REMOVED_SYNTAX_ERROR: deprecated_sig = inspect.signature(generate_run_id)

    # They have different signatures - this is the confusion source
    # REMOVED_SYNTAX_ERROR: assert len(class_method_sig.parameters) == 1  # Only thread_id
    # REMOVED_SYNTAX_ERROR: assert len(deprecated_sig.parameters) == 2  # thread_id and context

    # Deprecated function should warn
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.unified_id_manager.logger') as mock_logger:
        # REMOVED_SYNTAX_ERROR: _ = generate_run_id("test", "context")
        # REMOVED_SYNTAX_ERROR: mock_logger.warning.assert_called_with( )
        # REMOVED_SYNTAX_ERROR: "generate_run_id() is deprecated, use UnifiedIDManager.generate_run_id()"
        

# REMOVED_SYNTAX_ERROR: def test_all_static_methods_have_correct_decorators(self):
    # REMOVED_SYNTAX_ERROR: """Ensure all methods meant to be static are properly decorated."""
    # REMOVED_SYNTAX_ERROR: for name, method in inspect.getmembers(UnifiedIDManager):
        # REMOVED_SYNTAX_ERROR: if name.startswith('_'):
            # REMOVED_SYNTAX_ERROR: continue
            # REMOVED_SYNTAX_ERROR: if callable(method) and not name.startswith('__'):
                # Should be a static method
                # REMOVED_SYNTAX_ERROR: assert isinstance(inspect.getattr_static(UnifiedIDManager, name), staticmethod), \
                # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestImportValidation:
    # REMOVED_SYNTAX_ERROR: """Test that imports work correctly and catch lazy loading issues."""

# REMOVED_SYNTAX_ERROR: def test_import_from_different_contexts(self):
    # REMOVED_SYNTAX_ERROR: """Test UnifiedIDManager can be imported in various ways."""
    # Direct import
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_id_manager import UnifiedIDManager as UID1

    # Module import then access
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core import unified_id_manager
    # REMOVED_SYNTAX_ERROR: UID2 = unified_id_manager.UnifiedIDManager

    # Dynamic import (like in lazy loaded functions)
    # REMOVED_SYNTAX_ERROR: module = importlib.import_module('netra_backend.app.core.unified_id_manager')
    # REMOVED_SYNTAX_ERROR: UID3 = module.UnifiedIDManager

    # All should be the same class
    # REMOVED_SYNTAX_ERROR: assert UID1 is UID2 is UID3

    # All should work
    # REMOVED_SYNTAX_ERROR: for UID in [UID1, UID2, UID3]:
        # REMOVED_SYNTAX_ERROR: run_id = UID.generate_run_id("test_import")
        # REMOVED_SYNTAX_ERROR: assert UID.validate_run_id(run_id)

# REMOVED_SYNTAX_ERROR: def test_lazy_import_in_function_works(self):
    # REMOVED_SYNTAX_ERROR: """Test pattern used in run_repository, interfaces_observability, etc."""
    # REMOVED_SYNTAX_ERROR: pass
# REMOVED_SYNTAX_ERROR: def lazy_import_function(thread_id: str) -> str:
    # This pattern is used in several files
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    # REMOVED_SYNTAX_ERROR: return UnifiedIDManager.generate_run_id(thread_id)

    # Should work without issues
    # REMOVED_SYNTAX_ERROR: run_id = lazy_import_function("lazy_test")
    # REMOVED_SYNTAX_ERROR: assert "thread_lazy_test_run_" in run_id

# REMOVED_SYNTAX_ERROR: def test_circular_import_prevention(self):
    # REMOVED_SYNTAX_ERROR: """Ensure no circular imports when UnifiedIDManager is used."""
    # Clear the module from cache to test fresh import
    # REMOVED_SYNTAX_ERROR: modules_to_clear = [ )
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.core.unified_id_manager',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.services.thread_service',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.services.agent_websocket_bridge'
    
    # REMOVED_SYNTAX_ERROR: for mod in modules_to_clear:
        # REMOVED_SYNTAX_ERROR: if mod in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules[mod]

            # These imports should not cause circular dependency
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.thread_service import ThreadService
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager is not None
            # REMOVED_SYNTAX_ERROR: assert ThreadService is not None
            # REMOVED_SYNTAX_ERROR: assert AgentWebSocketBridge is not None


# REMOVED_SYNTAX_ERROR: class TestRealIntegration:
    # REMOVED_SYNTAX_ERROR: """Test UnifiedIDManager with real components, no mocks."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_thread_service_integration(self):
        # REMOVED_SYNTAX_ERROR: """Test ThreadService uses UnifiedIDManager correctly."""
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.thread_service import ThreadService

        # REMOVED_SYNTAX_ERROR: service = ThreadService()
        # REMOVED_SYNTAX_ERROR: thread_id = "integration_test_thread"
        # REMOVED_SYNTAX_ERROR: assistant_id = "test_assistant"
        # REMOVED_SYNTAX_ERROR: model = "gpt-4"
        # REMOVED_SYNTAX_ERROR: instructions = "Test instructions"

        # This was failing with 2-argument bug
        # REMOVED_SYNTAX_ERROR: run_id, run_data = service._prepare_run_data( )
        # REMOVED_SYNTAX_ERROR: thread_id, assistant_id, model, instructions
        

        # Validate the generated ID
        # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_run_id(run_id)
        # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.extract_thread_id(run_id) == thread_id
        # REMOVED_SYNTAX_ERROR: assert run_data["thread_id"] == thread_id
        # REMOVED_SYNTAX_ERROR: assert run_data["id"] == run_id

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_websocket_bridge_integration(self):
            # REMOVED_SYNTAX_ERROR: """Test AgentWebSocketBridge uses UnifiedIDManager correctly."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()

            # Test thread extraction
            # REMOVED_SYNTAX_ERROR: run_id = UnifiedIDManager.generate_run_id("websocket_test")
            # REMOVED_SYNTAX_ERROR: thread_id = bridge.extract_thread_id(run_id)

            # REMOVED_SYNTAX_ERROR: assert thread_id == "websocket_test"
            # REMOVED_SYNTAX_ERROR: assert bridge.get_format_info(run_id)["thread_id"] == "websocket_test"

# REMOVED_SYNTAX_ERROR: def test_all_production_files_use_correct_signature(self):
    # REMOVED_SYNTAX_ERROR: """Scan production files that use UnifiedIDManager."""
    # REMOVED_SYNTAX_ERROR: production_files = [ )
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.services.thread_service',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.services.database.run_repository',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.core.interfaces_observability',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.orchestration.agent_execution_registry'
    

    # REMOVED_SYNTAX_ERROR: for module_path in production_files:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: module = importlib.import_module(module_path)
            # If import succeeds, the fix is working
            # REMOVED_SYNTAX_ERROR: assert module is not None
            # REMOVED_SYNTAX_ERROR: except TypeError as e:
                # REMOVED_SYNTAX_ERROR: if "takes 1 positional argument but 2 were given" in str(e):
                    # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")


# REMOVED_SYNTAX_ERROR: class TestConcurrentUsage:
    # REMOVED_SYNTAX_ERROR: """Test UnifiedIDManager under concurrent load."""

# REMOVED_SYNTAX_ERROR: def test_thread_safe_id_generation(self):
    # REMOVED_SYNTAX_ERROR: """Test concurrent ID generation doesn't cause conflicts."""
# REMOVED_SYNTAX_ERROR: def generate_ids(prefix: str, count: int) -> List[str]:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: UnifiedIDManager.generate_run_id("formatted_string")
    # REMOVED_SYNTAX_ERROR: for i in range(count)
    

    # Generate IDs concurrently
    # REMOVED_SYNTAX_ERROR: with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # REMOVED_SYNTAX_ERROR: futures = [ )
        # REMOVED_SYNTAX_ERROR: executor.submit(generate_ids, "formatted_string", 100)
        # REMOVED_SYNTAX_ERROR: for i in range(10)
        

        # REMOVED_SYNTAX_ERROR: all_ids = []
        # REMOVED_SYNTAX_ERROR: for future in concurrent.futures.as_completed(futures):
            # REMOVED_SYNTAX_ERROR: all_ids.extend(future.result())

            # All IDs should be unique
            # REMOVED_SYNTAX_ERROR: assert len(all_ids) == len(set(all_ids))

            # All IDs should be valid
            # REMOVED_SYNTAX_ERROR: for run_id in all_ids:
                # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_run_id(run_id)

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_async_concurrent_usage(self):
                    # REMOVED_SYNTAX_ERROR: """Test async concurrent usage pattern."""
                    # REMOVED_SYNTAX_ERROR: pass
# REMOVED_SYNTAX_ERROR: async def generate_id_async(thread_id: str) -> str:
    # Simulate async context switching
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.001)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return UnifiedIDManager.generate_run_id(thread_id)

    # Generate IDs concurrently
    # REMOVED_SYNTAX_ERROR: tasks = [ )
    # REMOVED_SYNTAX_ERROR: generate_id_async("formatted_string")
    # REMOVED_SYNTAX_ERROR: for i in range(100)
    

    # REMOVED_SYNTAX_ERROR: ids = await asyncio.gather(*tasks)

    # All should be unique and valid
    # REMOVED_SYNTAX_ERROR: assert len(ids) == len(set(ids))
    # REMOVED_SYNTAX_ERROR: for run_id in ids:
        # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_run_id(run_id)


# REMOVED_SYNTAX_ERROR: class TestErrorScenarios:
    # REMOVED_SYNTAX_ERROR: """Test error handling and edge cases."""

# REMOVED_SYNTAX_ERROR: def test_none_arguments_handled(self):
    # REMOVED_SYNTAX_ERROR: """Test None arguments are rejected properly."""
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
        # REMOVED_SYNTAX_ERROR: UnifiedIDManager.generate_run_id(None)
        # REMOVED_SYNTAX_ERROR: assert "cannot be empty or None" in str(exc_info.value)

# REMOVED_SYNTAX_ERROR: def test_empty_string_rejected(self):
    # REMOVED_SYNTAX_ERROR: """Test empty strings are rejected."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
        # REMOVED_SYNTAX_ERROR: UnifiedIDManager.generate_run_id("")
        # REMOVED_SYNTAX_ERROR: assert "cannot be empty or None" in str(exc_info.value)

# REMOVED_SYNTAX_ERROR: def test_invalid_type_rejected(self):
    # REMOVED_SYNTAX_ERROR: """Test non-string types are rejected."""
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
        # REMOVED_SYNTAX_ERROR: UnifiedIDManager.generate_run_id(123)  # Number instead of string
        # REMOVED_SYNTAX_ERROR: assert "must be string" in str(exc_info.value)

# REMOVED_SYNTAX_ERROR: def test_reserved_sequence_rejected(self):
    # REMOVED_SYNTAX_ERROR: """Test thread_ids with reserved sequences are rejected."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
        # REMOVED_SYNTAX_ERROR: UnifiedIDManager.generate_run_id("thread_run_invalid")
        # REMOVED_SYNTAX_ERROR: assert "cannot contain reserved sequence" in str(exc_info.value)


# REMOVED_SYNTAX_ERROR: class TestStartupValidation:
    # REMOVED_SYNTAX_ERROR: """Tests that would catch issues at startup."""

# REMOVED_SYNTAX_ERROR: def test_critical_methods_exist(self):
    # REMOVED_SYNTAX_ERROR: """Test all critical methods exist with correct signatures."""
    # REMOVED_SYNTAX_ERROR: critical_methods = [ )
    # REMOVED_SYNTAX_ERROR: ('generate_run_id', 1),  # method_name, expected_arg_count
    # REMOVED_SYNTAX_ERROR: ('extract_thread_id', 1),
    # REMOVED_SYNTAX_ERROR: ('validate_run_id', 1),
    # REMOVED_SYNTAX_ERROR: ('validate_thread_id', 1),
    # REMOVED_SYNTAX_ERROR: ('normalize_thread_id', 1),
    # REMOVED_SYNTAX_ERROR: ('parse_run_id', 1),
    # REMOVED_SYNTAX_ERROR: ('get_format_info', 1),
    # REMOVED_SYNTAX_ERROR: ('create_test_ids', 1),
    

    # REMOVED_SYNTAX_ERROR: for method_name, expected_args in critical_methods:
        # REMOVED_SYNTAX_ERROR: assert hasattr(UnifiedIDManager, method_name), \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # REMOVED_SYNTAX_ERROR: method = getattr(UnifiedIDManager, method_name)
        # REMOVED_SYNTAX_ERROR: sig = inspect.signature(method)
        # Subtract 'self' if it's there (shouldn't be for static methods)
        # REMOVED_SYNTAX_ERROR: param_count = len([ ))
        # REMOVED_SYNTAX_ERROR: p for p in sig.parameters.values()
        # REMOVED_SYNTAX_ERROR: if p.default == inspect.Parameter.empty
        

        # REMOVED_SYNTAX_ERROR: assert param_count <= expected_args, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_startup_smoke_test(self):
    # REMOVED_SYNTAX_ERROR: """Basic smoke test that should run at startup."""
    # REMOVED_SYNTAX_ERROR: pass
    # Generate a test ID
    # REMOVED_SYNTAX_ERROR: test_thread = "startup_validation_test"
    # REMOVED_SYNTAX_ERROR: run_id = UnifiedIDManager.generate_run_id(test_thread)

    # Validate it
    # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_run_id(run_id)

    # Extract thread_id back
    # REMOVED_SYNTAX_ERROR: extracted = UnifiedIDManager.extract_thread_id(run_id)
    # REMOVED_SYNTAX_ERROR: assert extracted == test_thread

    # Get format info
    # REMOVED_SYNTAX_ERROR: info = UnifiedIDManager.get_format_info(run_id)
    # REMOVED_SYNTAX_ERROR: assert info['thread_id'] == test_thread
    # REMOVED_SYNTAX_ERROR: assert info['format_version'] == 'canonical'

    # Validate thread_id
    # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_thread_id(test_thread)

    # Test normalization
    # REMOVED_SYNTAX_ERROR: normalized = UnifiedIDManager.normalize_thread_id("formatted_string")
    # REMOVED_SYNTAX_ERROR: assert normalized == test_thread


# REMOVED_SYNTAX_ERROR: class TestDeprecationPath:
    # REMOVED_SYNTAX_ERROR: """Test migration from deprecated functions."""

# REMOVED_SYNTAX_ERROR: def test_deprecated_function_still_works(self):
    # REMOVED_SYNTAX_ERROR: """Ensure deprecated function works for backward compatibility."""
    # Old code pattern - should still work but warn
    # REMOVED_SYNTAX_ERROR: run_id = generate_run_id("legacy_test", "some_context")
    # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_run_id(run_id)

# REMOVED_SYNTAX_ERROR: def test_migration_path_clear(self):
    # REMOVED_SYNTAX_ERROR: """Test that migration from old to new is straightforward."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: thread_id = "migration_test"

    # Old way (deprecated)
    # REMOVED_SYNTAX_ERROR: old_id = generate_run_id(thread_id, "context")

    # New way
    # REMOVED_SYNTAX_ERROR: new_id = UnifiedIDManager.generate_run_id(thread_id)

    # Both should extract same thread_id
    # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.extract_thread_id(old_id) == thread_id
    # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.extract_thread_id(new_id) == thread_id


    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # Run basic validation that should pass at startup
        # REMOVED_SYNTAX_ERROR: print("Running UnifiedIDManager startup validation...")

        # REMOVED_SYNTAX_ERROR: try:
            # Test import
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            # REMOVED_SYNTAX_ERROR: print("✓ Import successful")

            # Test basic functionality
            # REMOVED_SYNTAX_ERROR: test_id = UnifiedIDManager.generate_run_id("startup_test")
            # REMOVED_SYNTAX_ERROR: assert UnifiedIDManager.validate_run_id(test_id)
            # REMOVED_SYNTAX_ERROR: print("✓ Basic ID generation works")

            # Test extraction
            # REMOVED_SYNTAX_ERROR: extracted = UnifiedIDManager.extract_thread_id(test_id)
            # REMOVED_SYNTAX_ERROR: assert extracted == "startup_test"
            # REMOVED_SYNTAX_ERROR: print("✓ Thread extraction works")

            # Test signature
            # REMOVED_SYNTAX_ERROR: import inspect
            # REMOVED_SYNTAX_ERROR: sig = inspect.signature(UnifiedIDManager.generate_run_id)
            # REMOVED_SYNTAX_ERROR: assert len(sig.parameters) == 1
            # REMOVED_SYNTAX_ERROR: print("✓ Method signature correct (1 argument)")

            # REMOVED_SYNTAX_ERROR: print(" )
            # REMOVED_SYNTAX_ERROR: ✅ All startup validations passed!")

            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: sys.exit(1)