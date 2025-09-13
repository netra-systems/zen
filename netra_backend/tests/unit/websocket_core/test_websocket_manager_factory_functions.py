"""
Unit Tests for WebSocket Manager Factory Functions - Critical Coverage Gap

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure WebSocket manager creation is reliable and secure
- Value Impact: Factory functions are critical for Golden Path user isolation ($500K+ ARR)
- Strategic Impact: CRITICAL - WebSocket manager creation must work correctly for all user contexts

This test suite provides comprehensive coverage for the websocket_manager.py factory functions,
specifically targeting the `get_websocket_manager` function and related functionality.

COVERAGE TARGET: websocket_manager.py factory functions and exports
Issue: #727 - WebSocket core coverage gaps

The `get_websocket_manager` function is mission-critical because:
1. It creates properly isolated WebSocket managers for each user
2. It implements security patterns required for multi-user environments  
3. It supports test environments with appropriate fallbacks
4. It handles errors gracefully to prevent system failures

CRITICAL REQUIREMENTS:
- User context isolation must be maintained
- Test environments must get appropriate managers
- Production environments must enforce security
- Error handling must be graceful and logged
- SSOT compliance must be maintained

Test Strategy:
- Factory function behavior with different user contexts
- Error handling and fallback scenarios
- Security enforcement in different environments  
- SSOT compliance validation
- Performance and resource management
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict, Optional

# SSOT Test Framework Import
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the system under test
from netra_backend.app.websocket_core import websocket_manager
from netra_backend.app.websocket_core.websocket_manager import (
    get_websocket_manager,
    WebSocketManager,
    WebSocketConnection,
    WebSocketManagerProtocol,
    _serialize_message_safely,
    WebSocketEventEmitter,
    UnifiedWebSocketEmitter
)

# Import dependencies for mocking
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketManagerMode
)


class TestWebSocketManagerFactoryFunctions(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket manager factory functions.
    
    Targeting: netra_backend/app/websocket_core/websocket_manager.py
    Issue: #727 - websocket-core coverage gaps  
    Priority: CRITICAL - Golden Path infrastructure
    """
    
    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)
        self.test_user_id = "test-user-123"
        self.test_thread_id = "test-thread-456"
        self.test_request_id = "test-request-789"
        
        # Create mock user context
        self.mock_user_context = type('MockUserContext', (), {
            'user_id': self.test_user_id,
            'thread_id': self.test_thread_id, 
            'request_id': self.test_request_id,
            'is_test': False
        })()

    async def test_get_websocket_manager_with_user_context(self):
        """
        Test get_websocket_manager creates manager correctly with proper user context.
        
        Business Critical: User isolation prevents data contamination ($100K+ data breach risk).
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Call with user context
            result = await get_websocket_manager(
                user_context=self.mock_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )
            
            # Verify UnifiedWebSocketManager was called with correct parameters
            mock_unified.assert_called_once_with(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=self.mock_user_context
            )
            
            # Verify result is the created manager
            assert result is mock_manager

    async def test_get_websocket_manager_without_user_context_creates_test_instance(self):
        """
        Test that missing user context creates appropriate test instance.
        
        Business Critical: Test environments must work without breaking security patterns.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified, \
             patch('netra_backend.app.websocket_core.websocket_manager.UnifiedIDManager') as mock_id_manager:
            
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Setup ID manager mock
            mock_id_instance = Mock()
            mock_id_manager.return_value = mock_id_instance
            mock_id_instance.generate_id.side_effect = [
                "test-user-id-123",  # User ID
                "test-thread-id-456",  # Thread ID
                "test-request-id-789"  # Request ID
            ]
            
            # Call without user context
            result = await get_websocket_manager(user_context=None)
            
            # Verify ID manager was used to create test IDs
            assert mock_id_instance.generate_id.call_count == 3
            
            # Verify UnifiedWebSocketManager was called with ISOLATED mode for testing
            mock_unified.assert_called_once()
            call_args = mock_unified.call_args
            assert call_args[1]['mode'] == WebSocketManagerMode.ISOLATED
            
            # Verify test context was created with generated IDs
            test_context = call_args[1]['user_context']
            assert test_context.user_id == "test-user-id-123"
            assert test_context.thread_id == "test-thread-id-456"
            assert test_context.request_id == "test-request-id-789"
            assert test_context.is_test is True

    async def test_get_websocket_manager_error_handling_creates_emergency_fallback(self):
        """
        Test that errors during manager creation result in emergency fallback.
        
        Business Critical: System must remain functional even when errors occur.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            # Make first call raise exception, second call succeed (for fallback)
            mock_fallback_manager = Mock()
            mock_unified.side_effect = [
                Exception("Simulated manager creation failure"),
                mock_fallback_manager
            ]
            
            # Call should not raise exception despite internal error
            result = await get_websocket_manager(user_context=self.mock_user_context)
            
            # Verify emergency fallback was created
            assert result is mock_fallback_manager
            
            # Verify both attempts were made
            assert mock_unified.call_count == 2
            
            # Verify first call was normal, second was emergency
            first_call = mock_unified.call_args_list[0]
            second_call = mock_unified.call_args_list[1]
            
            assert second_call[1]['mode'] == WebSocketManagerMode.EMERGENCY

    async def test_get_websocket_manager_ssot_validation_called(self):
        """
        Test that SSOT validation is called when available (Issue #712 fix).
        
        Business Critical: SSOT compliance prevents architectural violations.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified, \
             patch('netra_backend.app.websocket_core.websocket_manager.validate_websocket_manager_creation') as mock_validate:
            
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Call with user context
            result = await get_websocket_manager(user_context=self.mock_user_context)
            
            # Verify SSOT validation was called
            mock_validate.assert_called_once_with(
                manager_instance=mock_manager,
                user_context=self.mock_user_context,
                creation_method="get_websocket_manager"
            )

    async def test_get_websocket_manager_ssot_validation_missing_graceful_degradation(self):
        """
        Test graceful degradation when SSOT validation enhancer is not available.
        
        Business Critical: System must work even if optional validation is missing.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified, \
             patch('netra_backend.app.websocket_core.websocket_manager.validate_websocket_manager_creation', side_effect=ImportError("Validation not available")) as mock_validate:
            
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Should not raise exception despite import error
            result = await get_websocket_manager(user_context=self.mock_user_context)
            
            # Should still return manager
            assert result is mock_manager

    def test_websocket_manager_alias_points_to_unified_manager(self):
        """
        Test that WebSocketManager is correctly aliased to UnifiedWebSocketManager.
        
        Business Critical: Backward compatibility must be maintained.
        """
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        # WebSocketManager should be the same as UnifiedWebSocketManager
        assert WebSocketManager is UnifiedWebSocketManager

    def test_websocket_event_emitter_alias_compatibility(self):
        """
        Test that WebSocketEventEmitter alias works correctly.
        
        Business Critical: Event emission is core to WebSocket functionality.
        """
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # WebSocketEventEmitter should be aliased to UnifiedWebSocketEmitter
        assert WebSocketEventEmitter is UnifiedWebSocketEmitter

    def test_all_expected_exports_are_present(self):
        """
        Test that all expected exports are present in __all__.
        
        Business Critical: Import contracts must be maintained for existing code.
        """
        expected_exports = [
            'WebSocketManager',
            'WebSocketConnection',
            'WebSocketManagerProtocol', 
            '_serialize_message_safely',
            'get_websocket_manager',
            'WebSocketEventEmitter',
            'UnifiedWebSocketEmitter'
        ]
        
        # Verify __all__ contains expected exports
        assert hasattr(websocket_manager, '__all__')
        actual_exports = set(websocket_manager.__all__)
        expected_set = set(expected_exports)
        
        assert expected_set.issubset(actual_exports), f"Missing exports: {expected_set - actual_exports}"
        
        # Verify all exports are accessible
        for export_name in expected_exports:
            assert hasattr(websocket_manager, export_name), f"Export {export_name} not accessible"

    async def test_concurrent_manager_creation_isolation(self):
        """
        Test that concurrent manager creation maintains proper isolation.
        
        Business Critical: Race conditions could cause user data contamination.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            mock_managers = [Mock() for _ in range(3)]
            mock_unified.side_effect = mock_managers
            
            # Create different user contexts
            user_contexts = [
                type('MockUserContext', (), {
                    'user_id': f'user-{i}',
                    'thread_id': f'thread-{i}',
                    'request_id': f'request-{i}',
                    'is_test': False
                })() for i in range(3)
            ]
            
            # Create managers concurrently
            tasks = [
                get_websocket_manager(user_context=ctx)
                for ctx in user_contexts
            ]
            results = await asyncio.gather(*tasks)
            
            # Verify each got a different manager instance
            assert len(results) == 3
            assert len(set(results)) == 3  # All should be unique
            
            # Verify each was created with correct user context
            for i, call_args in enumerate(mock_unified.call_args_list):
                user_ctx = call_args[1]['user_context']
                assert user_ctx.user_id == f'user-{i}'

    def test_module_docstring_and_logging_initialization(self):
        """
        Test that module is properly documented and logging is initialized.
        
        Business Critical: Proper documentation and logging aid in debugging.
        """
        # Module should have comprehensive docstring
        assert websocket_manager.__doc__ is not None
        docstring = websocket_manager.__doc__
        
        # Should mention SSOT, business value, and user isolation  
        assert 'ssot' in docstring.lower() or 'single source' in docstring.lower()
        assert 'user' in docstring.lower() and 'isolation' in docstring.lower()
        
        # Should indicate Issue #89 remediation (ID management fix)
        assert 'issue #89' in docstring.lower() or '#89' in docstring


class TestWebSocketManagerFactoryEdgeCases(SSotAsyncTestCase):
    """
    Edge case and error scenario tests for WebSocket manager factory functions.
    
    These tests cover boundary conditions and failure scenarios that could
    cause system instability if not handled properly.
    """
    
    async def test_get_websocket_manager_with_none_mode_uses_default(self):
        """
        Test that None mode parameter uses default UNIFIED mode.
        
        Business Critical: Default behavior must be predictable.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Call without mode parameter (should default)
            result = await get_websocket_manager(user_context=self.mock_user_context)
            
            # Should use UNIFIED mode by default
            call_args = mock_unified.call_args
            assert call_args[1]['mode'] == WebSocketManagerMode.UNIFIED

    async def test_get_websocket_manager_with_invalid_user_context(self):
        """
        Test behavior with invalid or malformed user context.
        
        Business Critical: Invalid input should not crash the system.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Test with various invalid contexts
            invalid_contexts = [
                {},  # Empty dict
                type('BadContext', (), {})(),  # Object without required attributes
                "not-an-object",  # String instead of object
            ]
            
            for invalid_ctx in invalid_contexts:
                # Should not raise exception
                result = await get_websocket_manager(user_context=invalid_ctx)
                
                # Should return some manager (possibly fallback)
                assert result is not None

    async def test_get_websocket_manager_id_generation_failure_handling(self):
        """
        Test handling of ID generation failures during test context creation.
        
        Business Critical: ID generation failures should not prevent manager creation.
        """
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified, \
             patch('netra_backend.app.websocket_core.websocket_manager.UnifiedIDManager') as mock_id_manager:
            
            # Setup ID manager to fail
            mock_id_instance = Mock()
            mock_id_manager.return_value = mock_id_instance
            mock_id_instance.generate_id.side_effect = Exception("ID generation failed")
            
            # Setup fallback manager
            mock_fallback = Mock()
            mock_unified.return_value = mock_fallback
            
            # Should not raise exception despite ID generation failure
            result = await get_websocket_manager(user_context=None)
            
            # Should get emergency fallback manager
            assert result is mock_fallback

    def test_websocket_connection_dataclass_post_init_validation(self):
        """
        Test WebSocketConnection __post_init__ validation works correctly.
        
        Business Critical: Invalid connections must be caught at creation time.
        """
        from datetime import datetime
        
        # Valid connection should work
        valid_connection = WebSocketConnection(
            connection_id="valid-conn-123",
            user_id="valid-user-456",
            websocket=Mock(),
            thread_id="valid-thread-789"
        )
        assert valid_connection.connection_id == "valid-conn-123"
        
        # Invalid connection should raise error
        with pytest.raises((ValueError, AssertionError)):
            WebSocketConnection(
                connection_id="",  # Invalid empty ID
                user_id="user-456",
                websocket=Mock()
            )

    def test_serialize_message_safely_with_extreme_edge_cases(self):
        """
        Test _serialize_message_safely with challenging data types.
        
        Business Critical: Message serialization must never fail completely.
        """
        from datetime import datetime, timezone
        from enum import Enum
        from dataclasses import dataclass
        
        @dataclass
        class TestDataclass:
            value: str
            number: int
        
        class TestEnum(Enum):
            OPTION_A = "option_a"
            OPTION_B = 42
        
        # Test various challenging inputs
        challenging_inputs = [
            None,  # None value
            {"circular": None},  # Will be modified to create circular reference
            datetime.now(timezone.utc),  # Datetime object
            TestEnum.OPTION_A,  # Enum value
            TestDataclass("test", 123),  # Dataclass instance
            {"nested": {"deep": {"very": {"deep": "value"}}}},  # Deep nesting
            {"large_list": list(range(1000))},  # Large list
            {"unicode": "🚀💎🎯"},  # Unicode characters
        ]
        
        # Create circular reference
        circular_dict = {"circular": None}
        circular_dict["circular"] = circular_dict
        challenging_inputs[1] = circular_dict
        
        for test_input in challenging_inputs:
            # Should not raise exception regardless of input
            try:
                result = _serialize_message_safely(test_input)
                assert isinstance(result, dict), f"Should return dict for input: {type(test_input)}"
            except Exception as e:
                pytest.fail(f"Serialization failed for {type(test_input)}: {e}")


class TestWebSocketManagerFactoryPerformance(SSotAsyncTestCase):
    """
    Performance and resource management tests for WebSocket manager factory functions.
    
    These tests ensure that manager creation is efficient and doesn't leak resources.
    """
    
    async def test_manager_creation_performance_is_reasonable(self):
        """
        Test that manager creation performance is within reasonable bounds.
        
        Business Critical: Slow manager creation affects user experience.
        """
        import time
        
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            mock_manager = Mock()
            mock_unified.return_value = mock_manager
            
            # Measure creation time
            start_time = time.time()
            result = await get_websocket_manager(user_context=self.mock_user_context)
            end_time = time.time()
            
            creation_time = end_time - start_time
            
            # Should be very fast (under 100ms)
            assert creation_time < 0.1, f"Manager creation too slow: {creation_time}s"

    async def test_multiple_manager_creation_memory_efficiency(self):
        """
        Test that creating multiple managers doesn't cause memory leaks.
        
        Business Critical: Memory leaks could crash the system under load.
        """
        import gc
        import sys
        
        with patch('netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager') as mock_unified:
            # Create unique mock managers to prevent object reuse
            mock_unified.side_effect = lambda **kwargs: Mock()
            
            # Measure initial memory
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Create many managers
            managers = []
            for i in range(100):
                ctx = type('TestCtx', (), {
                    'user_id': f'user-{i}',
                    'thread_id': f'thread-{i}',
                    'request_id': f'req-{i}',
                    'is_test': True
                })()
                
                manager = await get_websocket_manager(user_context=ctx)
                managers.append(manager)
            
            # Clean up managers
            del managers
            gc.collect()
            final_objects = len(gc.get_objects())
            
            # Should not have excessive object growth
            object_growth = final_objects - initial_objects
            assert object_growth < 1000, f"Possible memory leak: {object_growth} new objects"

    def test_module_import_time_is_reasonable(self):
        """
        Test that importing the websocket_manager module is reasonably fast.
        
        Business Critical: Slow imports affect application startup time.
        """
        import time
        import importlib
        import sys
        
        # Remove module from cache to test fresh import
        if 'netra_backend.app.websocket_core.websocket_manager' in sys.modules:
            del sys.modules['netra_backend.app.websocket_core.websocket_manager']
        
        # Measure import time
        start_time = time.time()
        import netra_backend.app.websocket_core.websocket_manager as fresh_module
        end_time = time.time()
        
        import_time = end_time - start_time
        
        # Should be reasonably fast (under 1 second)
        assert import_time < 1.0, f"Module import too slow: {import_time}s"
        
        # Module should be properly initialized
        assert hasattr(fresh_module, '__all__')
        assert hasattr(fresh_module, 'get_websocket_manager')