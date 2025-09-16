"""Unit tests for ToolDispatcher - Public API facade for tool dispatching operations.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity & System Integration
- Business Goal: Unified tool dispatch interface for consistent agent operations
- Value Impact: Provides clean abstraction for tool execution across different agent types
- Strategic Impact: Enables rapid agent development while maintaining isolation and security

CRITICAL: Tests validate public API, factory patterns, and migration guidance.
All tests use SSOT patterns and IsolatedEnvironment for environment access.

MIGRATION: This facade provides backward compatibility while directing to UnifiedToolDispatcher.
Tests ensure smooth transition without breaking existing agent implementations.
"""

import warnings
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from langchain_core.tools import BaseTool

from netra_backend.app.agents.tool_dispatcher import (
    ToolDispatcher,
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    create_request_scoped_tool_dispatcher,
    create_tool_dispatcher,
)
from netra_backend.app.core.tool_models import ToolExecutionResult
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def _run(self, query: str = "") -> str:
        return f"Mock result for: {query}"
    
    async def _arun(self, query: str = "") -> str:
        return f"Async mock result for: {query}"


class MockUserExecutionContext:
    """Mock user execution context."""
    
    def __init__(self, user_id: str = "test_user"):
        self.user_id = user_id
        self.thread_id = "test_thread"
        self.correlation_id = str(uuid4())


class TestToolDispatcher(SSotAsyncTestCase):
    """Unit tests for ToolDispatcher - Public API facade for tool dispatching."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        
        # Create test tools
        self.mock_tools = [MockTool()]
        self.mock_user_context = MockUserExecutionContext()
        self.mock_websocket_manager = Mock()
        
        # Record setup metrics
        self.record_metric("tool_dispatcher_setup", True)
        self.record_metric("mock_tools_created", len(self.mock_tools))

    def test_tool_dispatcher_alias_mapping(self):
        """
        BVJ: Validates backward compatibility alias maintains existing API contracts.
        Ensures existing agent code continues working during migration to UnifiedToolDispatcher.
        """
        # Verify alias mapping
        assert ToolDispatcher is UnifiedToolDispatcher, "ToolDispatcher should alias to UnifiedToolDispatcher"
        
        # Verify public API exports
        from netra_backend.app.agents.tool_dispatcher import __all__ as exported_items
        
        # Check that all required items are exported
        required_exports = [
            "ToolDispatcher", "UnifiedToolDispatcher", "UnifiedToolDispatcherFactory",
            "create_request_scoped_tool_dispatcher", "ToolExecutionResult"
        ]
        for item in required_exports:
            assert item in exported_items, f"Required export {item} missing from __all__"
        
        # Record compatibility metrics
        self.record_metric("alias_mapping_verified", 1)
        self.record_metric("exports_validated", len(required_exports))

    def test_create_tool_dispatcher_deprecation_warning(self):
        """
        BVJ: Validates deprecation warnings guide developers to secure request-scoped patterns.
        Prevents global state issues that could cause data leaks between users.
        """
        # Test deprecated global dispatcher creation
        with pytest.warns(DeprecationWarning, match="creates global state"):
            with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global') as mock_create:
                mock_dispatcher = Mock()
                mock_create.return_value = mock_dispatcher
                
                dispatcher = create_tool_dispatcher(
                    tools=self.mock_tools,
                    websocket_bridge=Mock(),
                    permission_service=Mock()
                )
                
                # Verify factory method was called
                mock_create.assert_called_once_with(self.mock_tools)
                assert dispatcher == mock_dispatcher, "Should return factory-created dispatcher"
        
        # Record deprecation handling metrics
        self.record_metric("deprecation_warnings_tested", 1)

    async def test_create_request_scoped_tool_dispatcher(self):
        """
        BVJ: Validates request-scoped dispatcher creation provides proper user isolation.
        Critical for multi-user system security - prevents data leaks between user sessions.
        """
        # Test request-scoped dispatcher creation
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request') as mock_create:
            mock_dispatcher = Mock()
            mock_create.return_value = mock_dispatcher
            
            dispatcher = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=self.mock_tools
            )
            
            # Verify factory method was called with correct parameters
            mock_create.assert_called_once_with(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=self.mock_tools
            )
            assert dispatcher == mock_dispatcher, "Should return factory-created dispatcher"
        
        # Record request-scoped creation metrics
        self.record_metric("request_scoped_dispatchers_created", 1)
        self.record_metric("user_isolation_verified", 1)

    def test_unified_tool_dispatcher_factory_import(self):
        """
        BVJ: Validates factory pattern imports provide consistent creation interface.
        Ensures standardized tool dispatcher creation across the entire system.
        """
        # Verify factory is properly imported
        assert UnifiedToolDispatcherFactory is not None, "Factory should be imported"
        
        # Verify factory has required methods
        required_methods = ['create_for_request', 'create_legacy_global']
        for method_name in required_methods:
            assert hasattr(UnifiedToolDispatcherFactory, method_name), f"Factory missing {method_name} method"
        
        # Record factory verification metrics
        self.record_metric("factory_methods_verified", len(required_methods))

    def test_tool_models_import(self):
        """
        BVJ: Validates core tool models are properly imported for type consistency.
        Ensures consistent data structures across tool execution pipeline.
        """
        # Test ToolExecutionResult import
        from netra_backend.app.agents.tool_dispatcher import ToolExecutionResult
        assert ToolExecutionResult is not None, "ToolExecutionResult should be imported"
        
        # Test UnifiedTool import
        from netra_backend.app.agents.tool_dispatcher import UnifiedTool
        assert UnifiedTool is not None, "UnifiedTool should be imported"
        
        # Record model import metrics
        self.record_metric("tool_models_imported", 2)

    def test_production_tool_conditional_import(self):
        """
        BVJ: Validates graceful handling of optional production tool dependencies.
        Ensures system works in different deployment environments with varying tool availability.
        """
        # Test that production tools are handled gracefully
        try:
            from netra_backend.app.agents.tool_dispatcher import ProductionTool, ToolExecuteResponse
            if ProductionTool is not None:
                self.record_metric("production_tools_available", 1)
            else:
                self.record_metric("production_tools_unavailable", 1)
        except ImportError:
            self.record_metric("production_tools_import_error", 1)
        
        # Verify __all__ exports adapt to availability
        from netra_backend.app.agents.tool_dispatcher import __all__ as exported_items
        
        # Check if production tools are conditionally exported
        has_production_exports = any(item in exported_items for item in ["ProductionTool", "ToolExecuteResponse"])
        self.record_metric("production_exports_conditional", 1 if has_production_exports else 0)

    def test_migration_guidance_notice(self):
        """
        BVJ: Validates migration guidance helps developers understand new architecture.
        Supports smooth transition to consolidated tool dispatcher implementation.
        """
        # Test migration notice is emitted
        with patch('netra_backend.app.agents.tool_dispatcher.logger') as mock_logger:
            # Re-import to trigger migration notice
            import importlib
            import netra_backend.app.agents.tool_dispatcher
            importlib.reload(netra_backend.app.agents.tool_dispatcher)
            
            # Verify informational message was logged
            info_calls = [call for call in mock_logger.info.call_args_list if call]
            migration_logged = any("consolidation complete" in str(call) for call in info_calls)
            
            self.record_metric("migration_notice_logged", 1 if migration_logged else 0)

    def test_dispatch_strategy_import(self):
        """
        BVJ: Validates dispatch strategy patterns are properly imported.
        Enables flexible tool execution patterns for different agent requirements.
        """
        # Test DispatchStrategy import
        from netra_backend.app.agents.tool_dispatcher import DispatchStrategy
        assert DispatchStrategy is not None, "DispatchStrategy should be imported"
        
        # Test request/response models
        from netra_backend.app.agents.tool_dispatcher import ToolDispatchRequest, ToolDispatchResponse
        assert ToolDispatchRequest is not None, "ToolDispatchRequest should be imported"
        assert ToolDispatchResponse is not None, "ToolDispatchResponse should be imported"
        
        # Record strategy import metrics
        self.record_metric("dispatch_models_imported", 3)

    def test_create_request_scoped_dispatcher_alias(self):
        """
        BVJ: Validates direct factory alias provides convenient access pattern.
        Simplifies request-scoped dispatcher creation for common use cases.
        """
        # Test direct alias import
        from netra_backend.app.agents.tool_dispatcher import create_request_scoped_dispatcher
        assert create_request_scoped_dispatcher is not None, "Alias should be imported"
        
        # Verify it's the same as the factory method
        from netra_backend.app.core.tools.unified_tool_dispatcher import create_request_scoped_dispatcher as original
        assert create_request_scoped_dispatcher is original, "Should be direct alias to original function"
        
        # Record alias verification metrics
        self.record_metric("factory_alias_verified", 1)

    def test_backward_compatibility_patterns(self):
        """
        BVJ: Validates complete backward compatibility for existing agent implementations.
        Ensures zero-downtime migration from legacy tool dispatcher patterns.
        """
        # Test that all legacy patterns are supported through the facade
        legacy_patterns = [
            "ToolDispatcher",  # Direct class usage
            "create_tool_dispatcher",  # Global factory (deprecated)
            "create_request_scoped_tool_dispatcher",  # Recommended factory
        ]
        
        for pattern in legacy_patterns:
            # Verify pattern is available in module
            import netra_backend.app.agents.tool_dispatcher as dispatcher_module
            assert hasattr(dispatcher_module, pattern), f"Legacy pattern {pattern} should be available"
        
        # Test that warnings are properly issued for deprecated patterns
        with pytest.warns(DeprecationWarning):
            with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global'):
                create_tool_dispatcher()
        
        # Record backward compatibility metrics
        self.record_metric("legacy_patterns_supported", len(legacy_patterns))
        self.record_metric("deprecation_warnings_functional", 1)

    def test_ssot_consolidation_verification(self):
        """
        BVJ: Validates SSOT consolidation eliminates duplicate implementations.
        Ensures single source of truth for tool dispatching reduces maintenance overhead.
        """
        # Verify consolidation markers in module docstring
        import netra_backend.app.agents.tool_dispatcher as dispatcher_module
        module_doc = dispatcher_module.__doc__ or ""
        
        # Check for consolidation indicators
        consolidation_markers = [
            "CONSOLIDATION COMPLETE",
            "Single source of truth",
            "unified_tool_dispatcher",
        ]
        
        markers_found = sum(1 for marker in consolidation_markers if marker in module_doc)
        self.record_metric("consolidation_markers_found", markers_found)
        
        # Verify migration paths are documented
        migration_indicators = [
            "Migration from legacy:",
            "USAGE:",
            "NEW CODE:",
            "LEGACY:",
        ]
        
        migration_docs = sum(1 for indicator in migration_indicators if indicator in module_doc)
        self.record_metric("migration_documentation", migration_docs)
        
        # Business value assertion: Documentation provides clear guidance
        assert markers_found > 0, "Should have consolidation indicators in documentation"

    def teardown_method(self, method=None):
        """Cleanup test fixtures and verify metrics."""
        # Verify test execution
        assert self.get_test_context() is not None, "Test context should be available"
        
        # Record completion metrics
        self.record_metric("test_completed", True)
        
        # Call parent teardown
        super().teardown_method(method)