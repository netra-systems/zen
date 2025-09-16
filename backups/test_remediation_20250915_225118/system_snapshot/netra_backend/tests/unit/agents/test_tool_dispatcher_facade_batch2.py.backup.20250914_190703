"""
Unit Tests for Tool Dispatcher Facade - Batch 2 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity  
- Business Goal: Ensure tool dispatcher facade provides reliable API abstraction
- Value Impact: Prevents integration failures that would break agent workflows
- Strategic Impact: Core platform interface enabling all AI agent capabilities

Focus Areas:
1. Facade API compatibility and deprecation warnings
2. Factory method delegation and error propagation
3. Module exports and backward compatibility
4. Migration path validation for legacy code
"""

import asyncio
import pytest
import warnings
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.tool_dispatcher import (
    ToolDispatcher, 
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    create_tool_dispatcher,
    create_request_scoped_tool_dispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy,
    ToolExecutionResult,
    UnifiedTool,
    ProductionTool,
    ToolExecuteResponse
)


class TestToolDispatcherFacadeUnit(SSotBaseTestCase):
    """Unit tests for tool dispatcher facade (tool_dispatcher.py)."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "test_user_batch2"
        self.mock_user_context.run_id = "test_run_batch2"
        self.mock_user_context.thread_id = "test_thread_batch2"
        self.mock_user_context.session_id = "test_session_batch2"
        self.mock_websocket_manager = Mock()
        self.mock_tools = [Mock(name="test_tool_1"), Mock(name="test_tool_2")]
    
    # ===================== API COMPATIBILITY TESTS =====================
    
    def test_tool_dispatcher_alias_points_to_unified(self):
        """Test ToolDispatcher alias properly delegates to UnifiedToolDispatcher.
        
        BVJ: Ensures backward compatibility during migration.
        """
        # Test that the alias exists and points to the right class
        assert ToolDispatcher is UnifiedToolDispatcher
        assert ToolDispatcher.__name__ == "UnifiedToolDispatcher"
        
        self.record_metric("compatibility_check_passed", True)
    
    def test_create_tool_dispatcher_shows_deprecation_warning(self):
        """Test legacy create_tool_dispatcher shows deprecation warning.
        
        BVJ: Guides developers toward modern patterns.
        """
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global') as mock_factory:
            mock_dispatcher = Mock()
            mock_factory.return_value = mock_dispatcher
            
            with pytest.warns(DeprecationWarning, match="creates global state"):
                result = create_tool_dispatcher(self.mock_tools)
            
            # Verify factory was called correctly
            mock_factory.assert_called_once_with(self.mock_tools)
            assert result == mock_dispatcher
            
        self.record_metric("deprecation_warning_tested", True)
    
    def test_create_request_scoped_tool_dispatcher_delegates_to_factory(self):
        """Test modern factory method properly delegates to UnifiedToolDispatcherFactory.
        
        BVJ: Ensures recommended pattern works correctly.
        """
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request') as mock_factory:
            mock_dispatcher = Mock()
            mock_factory.return_value = mock_dispatcher
            
            result = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=self.mock_tools
            )
            
            # Verify factory was called with correct parameters
            mock_factory.assert_called_once_with(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=self.mock_tools
            )
            assert result == mock_dispatcher
            
        self.record_metric("factory_delegation_verified", True)
    
    # ===================== MODULE EXPORTS TESTS =====================
    
    def test_all_expected_exports_available(self):
        """Test all expected exports are available in __all__.
        
        BVJ: Prevents import errors that would break dependent systems.
        """
        from netra_backend.app.agents import tool_dispatcher
        
        expected_exports = [
            "ToolDispatcher", "create_tool_dispatcher",
            "UnifiedToolDispatcher", "UnifiedToolDispatcherFactory", 
            "create_request_scoped_tool_dispatcher",
            "create_request_scoped_dispatcher",
            "ToolDispatchRequest", "ToolDispatchResponse",
            "DispatchStrategy", "ToolExecutionResult", "UnifiedTool"
        ]
        
        # Check that all expected exports exist in __all__
        module_all = getattr(tool_dispatcher, '__all__', [])
        
        for export in expected_exports:
            assert export in module_all, f"Expected export '{export}' missing from __all__"
            assert hasattr(tool_dispatcher, export), f"Export '{export}' not available as module attribute"
        
        self.record_metric("exports_verified_count", len(expected_exports))
    
    def test_production_tool_exports_conditional(self):
        """Test ProductionTool exports are added conditionally.
        
        BVJ: Ensures optional dependencies don't break imports.
        """
        from netra_backend.app.agents import tool_dispatcher
        
        # ProductionTool should be in __all__ if available
        if ProductionTool is not None:
            assert "ProductionTool" in tool_dispatcher.__all__
            assert "ToolExecuteResponse" in tool_dispatcher.__all__
        
        self.record_metric("conditional_exports_checked", True)
    
    # ===================== ERROR PROPAGATION TESTS =====================
    
    def test_create_tool_dispatcher_propagates_factory_errors(self):
        """Test legacy create_tool_dispatcher propagates factory errors.
        
        BVJ: Ensures clear error messages for debugging.
        """
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global') as mock_factory:
            mock_factory.side_effect = ValueError("Factory creation failed")
            
            with pytest.raises(ValueError, match="Factory creation failed"):
                create_tool_dispatcher()
        
        self.record_metric("error_propagation_tested", True)
    
    def test_create_request_scoped_dispatcher_propagates_context_validation_errors(self):
        """Test request-scoped factory propagates user context validation errors.
        
        BVJ: Provides clear feedback for integration issues.
        """
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request') as mock_factory:
            mock_factory.side_effect = ValueError("Invalid user context")
            
            with pytest.raises(ValueError, match="Invalid user context"):
                create_request_scoped_tool_dispatcher(
                    user_context=None  # Invalid context
                )
        
        self.record_metric("context_validation_error_tested", True)
    
    # ===================== DATA MODEL TESTS =====================
    
    def test_tool_dispatch_request_model_validation(self):
        """Test ToolDispatchRequest model validates properly.
        
        BVJ: Ensures type safety in tool dispatch operations.
        """
        # Valid request
        valid_request = ToolDispatchRequest(
            tool_name="test_tool",
            parameters={"param1": "value1", "param2": 42}
        )
        assert valid_request.tool_name == "test_tool"
        assert valid_request.parameters == {"param1": "value1", "param2": 42}
        
        # Request with defaults
        minimal_request = ToolDispatchRequest(tool_name="minimal_tool")
        assert minimal_request.tool_name == "minimal_tool"
        assert minimal_request.parameters == {}
        
        self.record_metric("request_model_validated", True)
    
    def test_tool_dispatch_response_model_validation(self):
        """Test ToolDispatchResponse model validates properly.
        
        BVJ: Ensures consistent response structure across system.
        """
        # Success response
        success_response = ToolDispatchResponse(
            success=True,
            result={"output": "success"},
            metadata={"execution_time": 100}
        )
        assert success_response.success is True
        assert success_response.result == {"output": "success"}
        assert success_response.error is None
        assert success_response.metadata == {"execution_time": 100}
        
        # Error response
        error_response = ToolDispatchResponse(
            success=False,
            error="Tool execution failed"
        )
        assert error_response.success is False
        assert error_response.result is None
        assert error_response.error == "Tool execution failed"
        assert error_response.metadata == {}
        
        self.record_metric("response_model_validated", True)
    
    def test_dispatch_strategy_enum_values(self):
        """Test DispatchStrategy enum has expected values.
        
        BVJ: Ensures strategy patterns are available for different use cases.
        """
        expected_strategies = {"DEFAULT", "ADMIN", "ISOLATED", "LEGACY"}
        actual_strategies = {strategy.name for strategy in DispatchStrategy}
        
        assert actual_strategies == expected_strategies
        
        # Test string values
        assert DispatchStrategy.DEFAULT.value == "default"
        assert DispatchStrategy.ADMIN.value == "admin" 
        assert DispatchStrategy.ISOLATED.value == "isolated"
        assert DispatchStrategy.LEGACY.value == "legacy"
        
        self.record_metric("strategy_enum_validated", True)
    
    # ===================== MIGRATION NOTICE TESTS =====================
    
    def test_migration_notice_emitted_on_import(self):
        """Test migration notice is emitted when module is imported.
        
        BVJ: Provides feedback on successful consolidation.
        """
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Force re-execution of the migration notice
            from netra_backend.app.agents.tool_dispatcher import _emit_migration_notice
            _emit_migration_notice()
            
            # Verify info log was called with migration notice
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Tool dispatcher consolidation complete" in call_args
            assert "SSOT" in call_args
        
        self.record_metric("migration_notice_tested", True)
    
    # ===================== INTEGRATION BOUNDARIES TESTS =====================
    
    def test_facade_only_imports_from_unified_implementation(self):
        """Test facade only imports from the consolidated unified implementation.
        
        BVJ: Ensures clean architecture boundaries.
        """
        import inspect
        from netra_backend.app.agents import tool_dispatcher
        
        # Get the module source to check imports
        source_lines = inspect.getsourcelines(tool_dispatcher)[0]
        source_text = ''.join(source_lines)
        
        # Should import from unified_tool_dispatcher
        assert "from netra_backend.app.core.tools.unified_tool_dispatcher" in source_text
        assert "from netra_backend.app.core.tool_models" in source_text
        
        # Should NOT import from legacy scattered implementations
        forbidden_imports = [
            "from netra_backend.app.agents.tool_dispatcher_core",
            "from netra_backend.app.agents.tool_dispatcher_execution", 
            "from netra_backend.app.agents.tool_dispatcher_legacy"
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source_text, f"Facade should not import from: {forbidden}"
        
        self.record_metric("architecture_boundaries_verified", True)


class TestToolDispatcherBackwardCompatibilityUnit(SSotBaseTestCase):
    """Unit tests for backward compatibility features."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "compat_user"
        self.mock_user_context.run_id = "compat_run"
    
    def test_legacy_tool_dispatcher_import_still_works(self):
        """Test legacy import patterns still work with warnings.
        
        BVJ: Prevents breaking changes during migration period.
        """
        # This should work but show warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            
            # ToolDispatcher should be the unified implementation
            assert ToolDispatcher.__name__ == "UnifiedToolDispatcher"
        
        self.record_metric("legacy_import_compatibility_verified", True)
    
    def test_legacy_create_function_parameters_compatible(self):
        """Test legacy create function accepts expected parameters.
        
        BVJ: Ensures smooth migration for existing code.
        """
        # Mock the factory to avoid actual instantiation
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global') as mock_factory:
            mock_dispatcher = Mock()
            mock_factory.return_value = mock_dispatcher
            
            # Should accept legacy parameters
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Ignore deprecation warnings
                
                result = create_tool_dispatcher(
                    tools=[Mock(name="legacy_tool")],
                    websocket_bridge=Mock(),
                    permission_service=Mock()
                )
            
            assert result == mock_dispatcher
            mock_factory.assert_called_once_with([Mock(name="legacy_tool")])
        
        self.record_metric("legacy_parameters_compatible", True)
    
    def test_new_factory_method_signature_correct(self):
        """Test new factory method has correct signature.
        
        BVJ: Ensures new API is properly designed.
        """
        # Mock the factory to avoid actual instantiation
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request') as mock_factory:
            mock_dispatcher = Mock()
            mock_factory.return_value = mock_dispatcher
            
            # Should accept new parameters
            result = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=Mock(),
                tools=[Mock(name="new_tool")]
            )
            
            assert result == mock_dispatcher
            # Verify the factory was called with the right signature
            assert mock_factory.call_count == 1
            call_kwargs = mock_factory.call_args[1]
            assert 'user_context' in call_kwargs
            assert 'websocket_manager' in call_kwargs
            assert 'tools' in call_kwargs
        
        self.record_metric("new_api_signature_verified", True)


class TestToolDispatcherErrorHandlingUnit(SSotBaseTestCase):
    """Unit tests for error handling in the facade layer."""
    
    def test_import_error_handling_for_optional_dependencies(self):
        """Test graceful handling of optional dependency import errors.
        
        BVJ: Ensures system works even without optional components.
        """
        # Test the import error handling for ProductionTool
        with patch('netra_backend.app.agents.tool_dispatcher.ProductionTool', None):
            with patch('netra_backend.app.agents.tool_dispatcher.ToolExecuteResponse', None):
                # Re-import the module to test the import error handling
                import importlib
                import netra_backend.app.agents.tool_dispatcher as td_module
                importlib.reload(td_module)
                
                # ProductionTool and ToolExecuteResponse should be None
                assert td_module.ProductionTool is None
                assert td_module.ToolExecuteResponse is None
                
                # Module should still be usable
                assert hasattr(td_module, 'UnifiedToolDispatcher')
                assert hasattr(td_module, 'create_request_scoped_tool_dispatcher')
        
        self.record_metric("optional_dependency_error_handling_tested", True)
    
    def test_facade_handles_circular_import_prevention(self):
        """Test facade properly handles circular import prevention.
        
        BVJ: Ensures system architecture remains stable.
        """
        # The facade should use TYPE_CHECKING imports to prevent circular imports
        import inspect
        from netra_backend.app.agents import tool_dispatcher
        
        source_lines = inspect.getsourcelines(tool_dispatcher)[0]
        source_text = ''.join(source_lines)
        
        # Should use TYPE_CHECKING pattern
        assert "from typing import" in source_text
        # Should have TYPE_CHECKING conditional imports if needed
        if "if TYPE_CHECKING:" in source_text:
            # If using TYPE_CHECKING, imports should be properly conditioned
            assert "UserExecutionContext" in source_text or "WebSocketManager" in source_text
        
        self.record_metric("circular_import_prevention_verified", True)


if __name__ == "__main__":
    # Run tests with pytest for better output
    pytest.main([__file__, "-v", "--tb=short"])