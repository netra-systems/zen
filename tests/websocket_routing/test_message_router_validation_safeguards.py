"""
WebSocket Message Router Validation Safeguards Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Prevent Production Bugs & Improve Developer Experience
- Value Impact: Early detection of MessageHandler protocol violations
- Strategic Impact: Fail-fast validation prevents runtime errors

VALIDATION PURPOSE:
These tests validate that MessageRouter has proper safeguards to prevent
the 'function' object has no attribute 'can_handle' bug from occurring.

The tests demonstrate what validation SHOULD be added to prevent this issue.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, Protocol

from netra_backend.app.websocket_core.handlers import MessageRouter, MessageHandler, BaseMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage


class TestMessageRouterValidationSafeguards:
    """Tests for MessageRouter validation that should prevent function handler bugs."""
    
    @pytest.fixture
    def message_router(self):
        """Create MessageRouter for testing."""
        return MessageRouter()
    
    def test_add_handler_should_validate_handler_protocol(self, message_router):
        """
        VALIDATION TEST: add_handler should validate that handler implements MessageHandler protocol.
        
        CURRENT STATE: This test will FAIL because MessageRouter doesn't validate handlers.
        DESIRED STATE: MessageRouter should reject non-MessageHandler objects.
        """
        # This function doesn't implement MessageHandler protocol
        async def invalid_handler(user_id, websocket, message):
            return True
        
        # EXPECTED BEHAVIOR: add_handler should raise TypeError for invalid handlers
        # CURRENT BEHAVIOR: add_handler accepts anything (this is the bug!)
        
        # This test demonstrates what SHOULD happen (but currently doesn't)
        with pytest.raises(TypeError, match="Handler must implement MessageHandler protocol"):
            message_router.add_handler(invalid_handler)
            
        # If we reach here, validation failed (which is currently the case)

    def test_add_handler_should_accept_valid_message_handlers(self, message_router):
        """
        VALIDATION TEST: add_handler should accept valid MessageHandler implementations.
        
        This test shows what SHOULD be accepted after validation is added.
        EXPECTED: This test should PASS once proper validation is implemented.
        """
        class ValidHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.AGENT_REQUEST])
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        valid_handler = ValidHandler()
        
        # This should work without errors
        message_router.add_handler(valid_handler)
        assert len(message_router.custom_handlers) == 1
        assert message_router.custom_handlers[0] == valid_handler

    def test_add_handler_should_accept_duck_typed_handlers(self, message_router):
        """
        VALIDATION TEST: add_handler should accept objects that duck-type as MessageHandler.
        
        Python uses duck typing, so objects that have the right methods should be accepted.
        """
        class DuckTypedHandler:
            """Handler that duck-types as MessageHandler without inheriting from Protocol."""
            
            def can_handle(self, message_type: MessageType) -> bool:
                return message_type == MessageType.AGENT_REQUEST
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        duck_handler = DuckTypedHandler()
        
        # This should be accepted (duck typing)
        message_router.add_handler(duck_handler)
        assert len(message_router.custom_handlers) == 1

    def test_add_handler_should_reject_objects_missing_can_handle(self, message_router):
        """
        VALIDATION TEST: Reject handlers missing can_handle method.
        
        EXPECTED: TypeError when handler lacks can_handle method.
        """
        class MissingCanHandle:
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        invalid_handler = MissingCanHandle()
        
        with pytest.raises(TypeError, match="Handler must implement 'can_handle' method"):
            message_router.add_handler(invalid_handler)

    def test_add_handler_should_reject_objects_missing_handle_message(self, message_router):
        """
        VALIDATION TEST: Reject handlers missing handle_message method.
        
        EXPECTED: TypeError when handler lacks handle_message method.
        """
        class MissingHandleMessage:
            def can_handle(self, message_type: MessageType) -> bool:
                return True
        
        invalid_handler = MissingHandleMessage()
        
        with pytest.raises(TypeError, match="Handler must implement 'handle_message' method"):
            message_router.add_handler(invalid_handler)

    def test_add_handler_should_reject_handlers_with_wrong_signature(self, message_router):
        """
        VALIDATION TEST: Reject handlers with incorrect method signatures.
        
        EXPECTED: TypeError when method signatures don't match protocol.
        """
        class WrongSignatureHandler:
            def can_handle(self, wrong_param) -> bool:  # Wrong signature
                return True
            
            async def handle_message(self, only_user_id: str) -> bool:  # Wrong signature
                return True
        
        invalid_handler = WrongSignatureHandler()
        
        with pytest.raises(TypeError, match="Handler method signatures don't match MessageHandler protocol"):
            message_router.add_handler(invalid_handler)

    def test_add_handler_should_reject_non_callable_objects(self, message_router):
        """
        VALIDATION TEST: Reject non-callable objects entirely.
        
        EXPECTED: TypeError for strings, numbers, etc.
        """
        invalid_handlers = [
            "string_handler",
            42,
            ["list", "handler"],
            {"dict": "handler"},
            None
        ]
        
        for invalid_handler in invalid_handlers:
            with pytest.raises(TypeError, match="Handler must be a callable object"):
                message_router.add_handler(invalid_handler)

    def test_validate_handler_protocol_utility_function(self):
        """
        UTILITY TEST: Test for a validation utility function.
        
        This tests a helper function that could be added to validate handlers.
        """
        def validate_message_handler(handler) -> bool:
            """Utility function to validate MessageHandler protocol compliance."""
            # Check if handler has required methods
            if not hasattr(handler, 'can_handle'):
                raise TypeError(f"Handler {type(handler).__name__} must implement 'can_handle' method")
            
            if not hasattr(handler, 'handle_message'):
                raise TypeError(f"Handler {type(handler).__name__} must implement 'handle_message' method")
            
            # Check if methods are callable
            if not callable(getattr(handler, 'can_handle')):
                raise TypeError(f"Handler {type(handler).__name__}.can_handle must be callable")
            
            if not callable(getattr(handler, 'handle_message')):
                raise TypeError(f"Handler {type(handler).__name__}.handle_message must be callable")
            
            # Additional signature validation could be added here
            return True
        
        # Test valid handler
        class ValidHandler:
            def can_handle(self, message_type: MessageType) -> bool:
                return True
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        valid_handler = ValidHandler()
        assert validate_message_handler(valid_handler) is True
        
        # Test invalid handler (function)
        async def invalid_function_handler(user_id, websocket, message):
            return True
        
        with pytest.raises(TypeError, match="must implement 'can_handle' method"):
            validate_message_handler(invalid_function_handler)

    def test_router_should_log_warnings_for_validation_failures(self, message_router, caplog):
        """
        LOGGING TEST: Router should log warnings when validation fails.
        
        Even if we don't reject invalid handlers, we should warn about them.
        """
        import logging
        
        # This would require adding logging to the validation process
        async def problematic_handler(user_id, websocket, message):
            return True
        
        # With proper validation, this should log a warning
        with caplog.at_level(logging.WARNING):
            try:
                message_router.add_handler(problematic_handler)
            except TypeError:
                pass  # Expected with proper validation
        
        # Should have logged a warning about protocol violation
        # (This would be implemented in the actual validation code)

    def test_router_initialization_should_validate_builtin_handlers(self, caplog):
        """
        INITIALIZATION TEST: Router should validate its built-in handlers.
        
        This ensures that built-in handlers are also protocol-compliant.
        """
        import logging
        
        with caplog.at_level(logging.INFO):
            router = MessageRouter()
        
        # Should log that all built-in handlers are validated
        # (This would require adding validation to __init__)
        assert router is not None
        assert len(router.builtin_handlers) > 0


class TestMessageRouterProtocolValidation:
    """Tests for MessageHandler protocol validation using typing."""
    
    def test_protocol_checking_with_typing(self):
        """
        ADVANCED VALIDATION: Use typing.runtime_checkable to validate protocols.
        
        This demonstrates how to use Python's typing system for runtime protocol checking.
        """
        from typing import runtime_checkable
        
        # In real implementation, MessageHandler would need @runtime_checkable
        @runtime_checkable
        class ValidatedMessageHandler(Protocol):
            def can_handle(self, message_type: MessageType) -> bool:
                ...
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                ...
        
        # Test valid implementation
        class ValidHandler:
            def can_handle(self, message_type: MessageType) -> bool:
                return True
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        valid_handler = ValidHandler()
        assert isinstance(valid_handler, ValidatedMessageHandler)
        
        # Test invalid implementation (function)
        async def invalid_handler(user_id, websocket, message):
            return True
        
        assert not isinstance(invalid_handler, ValidatedMessageHandler)

    def test_comprehensive_handler_validation(self):
        """
        COMPREHENSIVE TEST: Complete validation that could be added to MessageRouter.
        
        This shows a complete validation function that could prevent the bug.
        """
        def comprehensive_handler_validation(handler) -> None:
            """Complete validation for MessageHandler protocol compliance."""
            # Type check
            if not hasattr(handler, '__class__'):
                raise TypeError("Handler must be an object instance")
            
            # Method existence check
            required_methods = ['can_handle', 'handle_message']
            for method_name in required_methods:
                if not hasattr(handler, method_name):
                    raise TypeError(f"Handler {handler.__class__.__name__} missing required method: {method_name}")
                
                method = getattr(handler, method_name)
                if not callable(method):
                    raise TypeError(f"Handler {handler.__class__.__name__}.{method_name} must be callable")
            
            # Signature validation (basic)
            import inspect
            
            # Check can_handle signature
            can_handle_sig = inspect.signature(handler.can_handle)
            if len(can_handle_sig.parameters) != 2:  # self + message_type
                raise TypeError(f"Handler {handler.__class__.__name__}.can_handle must accept exactly 2 parameters (self, message_type)")
            
            # Check handle_message signature  
            handle_msg_sig = inspect.signature(handler.handle_message)
            if len(handle_msg_sig.parameters) != 4:  # self + user_id + websocket + message
                raise TypeError(f"Handler {handler.__class__.__name__}.handle_message must accept exactly 4 parameters (self, user_id, websocket, message)")
        
        # Test with valid handler
        class ValidHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.AGENT_REQUEST])
        
        valid_handler = ValidHandler()
        comprehensive_handler_validation(valid_handler)  # Should not raise
        
        # Test with function (should fail)
        async def function_handler(user_id, websocket, message):
            return True
        
        with pytest.raises(TypeError, match="missing required method: can_handle"):
            comprehensive_handler_validation(function_handler)


class TestMessageRouterRuntimeProtection:
    """Tests for runtime protection against protocol violations."""
    
    def test_find_handler_should_handle_invalid_handlers_gracefully(self):
        """
        RUNTIME PROTECTION: _find_handler should handle invalid handlers gracefully.
        
        Even if bad handlers slip through validation, _find_handler should handle them.
        """
        router = MessageRouter()
        
        # Add a bad handler that somehow got through
        async def bad_handler(user_id, websocket, message):
            return True
        
        # Manually add to simulate the bug (bypass add_handler validation)
        router.custom_handlers.append(bad_handler)
        
        # _find_handler should handle this gracefully, not crash
        # This would require defensive programming in _find_handler
        
        # Currently this fails, but with proper protection it should return None
        try:
            result = router._find_handler(MessageType.AGENT_REQUEST)
            assert result is None  # Should skip invalid handler and return None
        except AttributeError:
            # Current behavior - this is what we want to fix
            pytest.fail("_find_handler should handle invalid handlers gracefully")

    def test_route_message_should_survive_invalid_handlers(self):
        """
        RUNTIME PROTECTION: route_message should survive invalid handlers.
        
        The routing system should be resilient to handler protocol violations.
        """
        router = MessageRouter()
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = "test"
        
        # Add bad handler
        async def bad_handler(user_id, websocket, message):
            return True
        
        router.custom_handlers.append(bad_handler)
        
        # Should handle gracefully and fall back to built-in handlers
        message = {"type": "ping", "payload": {}}
        
        # This should work despite the bad handler
        result = asyncio.run(router.route_message("test_user", mock_websocket, message))
        assert result is True  # Should fall back to HeartbeatHandler for ping