"""
Unit Tests for UnifiedToolDispatcherFactory SSOT Validation Failures

These tests are DESIGNED TO FAIL initially to prove SSOT validation issues
exist in the UnifiedToolDispatcherFactory implementation. The tests demonstrate
specific SSOT violations that prevent proper factory initialization.

Test Categories:
1. Factory Instantiation SSOT - Direct instantiation prevention failures
2. Tool Registry SSOT Validation - Missing or invalid tool registry dependencies  
3. User Context Dispatcher Creation - SSOT validation failures during dispatcher creation
4. WebSocket Manager Integration - SSOT violations in WebSocket integration
5. Tool Dispatcher Isolation - Factory isolation and cleanup management violations

Expected Outcomes:
- All tests should FAIL initially with specific SSOT error messages
- Failures demonstrate the factory initialization problems affecting golden path
- Error messages provide concrete evidence of SSOT validation violations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy,
    AuthenticationError,
    PermissionError,
    SecurityViolationError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUnifiedToolDispatcherFactorySSotValidation:
    """Test SSOT validation failures in UnifiedToolDispatcherFactory."""
    
    def test_unified_tool_dispatcher_direct_instantiation_ssot_violation(self):
        """
        TEST DESIGNED TO FAIL: UnifiedToolDispatcher should prevent direct instantiation.
        
        SSOT Issue: Direct instantiation violates factory pattern SSOT requirement.
        Expected Failure: Should raise error preventing direct instantiation.
        """
        # This should FAIL with SSOT enforcement error
        with pytest.raises(RuntimeError, match="Direct instantiation.*forbidden"):
            UnifiedToolDispatcher()  # SSOT violation: direct instantiation
    
    async def test_tool_dispatcher_factory_requires_tool_registry_ssot_validation(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate tool registry SSOT requirement.
        
        SSOT Issue: Factory operates without tool registry, violating SSOT dependency pattern.
        Expected Failure: Factory should require valid tool registry for dispatcher creation.
        """
        factory = UnifiedToolDispatcherFactory()
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # This should FAIL - factory without tool registry should reject dispatcher creation
        with pytest.raises(RuntimeError, match="tool registry"):
            dispatcher = await factory.create_dispatcher(
                user_context=valid_context,
                websocket_manager=Mock(),
                tools=None
            )
    
    def test_tool_dispatcher_factory_tool_registry_type_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate tool registry type SSOT.
        
        SSOT Issue: Factory accepts invalid tool registry types without validation.
        Expected Failure: Factory should validate tool registry interface compliance.
        """
        factory = UnifiedToolDispatcherFactory()
        
        # This should FAIL - invalid tool registry type should be rejected
        invalid_registry = "not_a_tool_registry"  # SSOT violation: wrong type
        
        with pytest.raises(TypeError, match="tool registry"):
            factory.set_tool_registry(invalid_registry)  # SSOT violation: invalid type
    
    @pytest.mark.asyncio
    async def test_dispatcher_creation_user_context_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Dispatcher creation should validate user context SSOT.
        
        SSOT Issue: Factory creates dispatchers without validating UserExecutionContext.
        Expected Failure: Should reject invalid or incomplete user contexts.
        """
        factory = UnifiedToolDispatcherFactory()
        mock_registry = Mock()
        factory.set_tool_registry(mock_registry)
        
        # This should FAIL - invalid user context should be rejected
        invalid_context = UserExecutionContext(
            user_id="",  # SSOT violation: empty user_id
            thread_id="valid_thread",
            run_id="valid_run",
            request_id="valid_request"
        )
        
        with pytest.raises(AuthenticationError, match="UserExecutionContext"):
            await factory.create_dispatcher(
                user_context=invalid_context,  # SSOT violation: invalid context
                websocket_manager=Mock(),
                tools=None
            )
    
    @pytest.mark.asyncio
    async def test_dispatcher_websocket_manager_ssot_integration_failure(self):
        """
        TEST DESIGNED TO FAIL: Dispatcher should validate WebSocket manager SSOT integration.
        
        SSOT Issue: Factory creates dispatchers without proper WebSocket manager validation.
        Expected Failure: Should reject dispatchers with invalid WebSocket managers.
        """
        factory = UnifiedToolDispatcherFactory()
        mock_registry = Mock()
        factory.set_tool_registry(mock_registry)
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run", 
            request_id="test_request"
        )
        
        # This should FAIL - invalid websocket manager should be rejected
        invalid_websocket_manager = "not_a_websocket_manager"  # SSOT violation: wrong type
        
        with pytest.raises(TypeError, match="WebSocket manager"):
            await factory.create_dispatcher(
                user_context=valid_context,
                websocket_manager=invalid_websocket_manager,  # SSOT violation: invalid type
                tools=None
            )
    
    @pytest.mark.asyncio
    async def test_dispatcher_tools_list_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Dispatcher should validate tools list SSOT structure.
        
        SSOT Issue: Factory accepts invalid tools list without proper validation.
        Expected Failure: Should validate tools list contains proper BaseTool instances.
        """
        factory = UnifiedToolDispatcherFactory()
        mock_registry = Mock()
        factory.set_tool_registry(mock_registry)
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # This should FAIL - invalid tools list should be rejected
        invalid_tools = ["not_a_tool", "also_not_a_tool"]  # SSOT violation: invalid tool types
        
        with pytest.raises(TypeError, match="BaseTool"):
            await factory.create_dispatcher(
                user_context=valid_context,
                websocket_manager=Mock(),
                tools=invalid_tools  # SSOT violation: invalid tool types
            )
    
    @pytest.mark.asyncio
    async def test_dispatcher_create_for_user_ssot_authentication_failure(self):
        """
        TEST DESIGNED TO FAIL: create_for_user should enforce authentication SSOT.
        
        SSOT Issue: create_for_user allows creation without proper authentication context.
        Expected Failure: Should reject creation when authentication context is missing.
        """
        # This should FAIL - None user context violates SSOT authentication requirement
        with pytest.raises(AuthenticationError, match="UserExecutionContext"):
            await UnifiedToolDispatcher.create_for_user(
                user_context=None,  # SSOT violation: None context
                websocket_bridge=Mock(),
                tools=None,
                enable_admin_tools=False
            )
    
    @pytest.mark.asyncio
    async def test_dispatcher_admin_tools_ssot_permission_failure(self):
        """
        TEST DESIGNED TO FAIL: Admin tools should enforce permission SSOT validation.
        
        SSOT Issue: Dispatcher allows admin tools without proper permission validation.
        Expected Failure: Should reject admin tools for non-admin users.
        """
        regular_user_context = UserExecutionContext(
            user_id="regular_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
            # Missing admin permissions
        )
        
        # This should FAIL - regular user requesting admin tools violates SSOT permissions
        with pytest.raises(PermissionError, match="admin permission"):
            await UnifiedToolDispatcher.create_for_user(
                user_context=regular_user_context,
                websocket_bridge=Mock(),
                tools=None,
                enable_admin_tools=True  # SSOT violation: admin tools without permission
            )
    
    @pytest.mark.asyncio
    async def test_dispatcher_scoped_creation_ssot_cleanup_failure(self):
        """
        TEST DESIGNED TO FAIL: Scoped dispatcher should enforce cleanup SSOT pattern.
        
        SSOT Issue: Scoped dispatcher doesn't properly cleanup resources on exit.
        Expected Failure: Should cleanup all resources when scope exits.
        """
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Track active dispatchers before scoped creation
        initial_dispatchers = len(UnifiedToolDispatcher._active_dispatchers)
        
        # This should FAIL if SSOT cleanup is not enforced
        async with UnifiedToolDispatcher.create_scoped(
            user_context=valid_context,
            websocket_bridge=Mock(),
            tools=None
        ) as dispatcher:
            # Dispatcher should be tracked
            current_dispatchers = len(UnifiedToolDispatcher._active_dispatchers)
            assert current_dispatchers > initial_dispatchers, \
                "SSOT violation: Scoped dispatcher not tracked in active dispatchers"
        
        # After scope exit, dispatcher should be cleaned up
        final_dispatchers = len(UnifiedToolDispatcher._active_dispatchers)
        assert final_dispatchers == initial_dispatchers, \
            "SSOT violation: Scoped dispatcher not cleaned up after scope exit"
    
    def test_dispatcher_max_dispatchers_per_user_ssot_enforcement_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce max dispatchers per user SSOT limit.
        
        SSOT Issue: Factory allows unlimited dispatchers per user, violating resource SSOT.
        Expected Failure: Should reject dispatcher creation when user exceeds limits.
        """
        # Set low limit for testing
        original_limit = UnifiedToolDispatcher._max_dispatchers_per_user
        UnifiedToolDispatcher._max_dispatchers_per_user = 1
        
        try:
            valid_context = UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_request"
            )
            
            # Create first dispatcher (should succeed)
            dispatcher1 = asyncio.run(UnifiedToolDispatcher.create_for_user(
                user_context=valid_context,
                websocket_bridge=Mock(),
                tools=None
            ))
            
            # Create second dispatcher for same user (should FAIL - exceeds limit)
            second_context = UserExecutionContext(
                user_id="test_user",  # Same user
                thread_id="test_thread2",
                run_id="test_run2",
                request_id="test_request2"
            )
            
            with pytest.raises(SecurityViolationError, match="maximum.*dispatchers"):
                asyncio.run(UnifiedToolDispatcher.create_for_user(
                    user_context=second_context,
                    websocket_bridge=Mock(),
                    tools=None
                ))
                
        finally:
            # Restore original limit
            UnifiedToolDispatcher._max_dispatchers_per_user = original_limit
    
    def test_dispatcher_security_violations_ssot_tracking_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should track security violations SSOT globally.
        
        SSOT Issue: Security violations not properly tracked across dispatcher instances.
        Expected Failure: Should increment global security violation counter.
        """
        initial_violations = UnifiedToolDispatcher._security_violations
        
        # Trigger security violation
        try:
            UnifiedToolDispatcher()  # Direct instantiation - security violation
        except RuntimeError:
            pass  # Expected
        
        # This should FAIL if SSOT security tracking is not implemented
        current_violations = UnifiedToolDispatcher._security_violations
        assert current_violations > initial_violations, \
            "SSOT violation: Security violations not tracked globally"
    
    @pytest.mark.asyncio
    async def test_factory_active_dispatchers_ssot_tracking_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should track active dispatchers SSOT consistently.
        
        SSOT Issue: Active dispatchers tracking doesn't match actual dispatcher state.
        Expected Failure: Should maintain consistent tracking of active dispatchers.
        """
        factory = UnifiedToolDispatcherFactory()
        mock_registry = Mock()
        factory.set_tool_registry(mock_registry)
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        initial_count = len(factory._active_dispatchers)
        
        # Create dispatcher
        dispatcher = await factory.create_dispatcher(
            user_context=valid_context,
            websocket_manager=Mock(),
            tools=None
        )
        
        # This should FAIL if SSOT tracking is inconsistent
        current_count = len(factory._active_dispatchers)
        assert current_count == initial_count + 1, \
            "SSOT violation: Active dispatchers count not incremented correctly"
            
        # Verify dispatcher is actually tracked
        assert dispatcher in factory._active_dispatchers, \
            "SSOT violation: Created dispatcher not tracked in active dispatchers list"
    
    def test_dispatcher_strategy_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Dispatcher should validate strategy SSOT enumeration.
        
        SSOT Issue: Dispatcher accepts invalid strategy values outside SSOT enum.
        Expected Failure: Should reject invalid strategy values.
        """
        # This should FAIL - invalid strategy should be rejected
        invalid_strategy = "INVALID_STRATEGY"  # SSOT violation: not in DispatchStrategy enum
        
        with pytest.raises(ValueError, match="Invalid strategy"):
            # Attempt to use invalid strategy
            request = ToolDispatchRequest(
                tool_name="test_tool",
                parameters={"strategy": invalid_strategy}  # SSOT violation: invalid strategy
            )
    
    @pytest.mark.asyncio
    async def test_dispatcher_websocket_bridge_adapter_ssot_failure(self):
        """
        TEST DESIGNED TO FAIL: Dispatcher should validate WebSocket bridge adapter SSOT.
        
        SSOT Issue: WebSocket bridge adapter doesn't properly validate bridge interface.
        Expected Failure: Should reject bridges without required interface methods.
        """
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            request_id="test_request"
        )
        
        # Create mock bridge without required methods (SSOT violation)
        invalid_bridge = Mock()
        # Missing notify_tool_executing method - SSOT interface violation
        
        # This should FAIL - bridge without required interface should be rejected
        with pytest.raises(AttributeError, match="notify_tool_executing"):
            await UnifiedToolDispatcher.create_for_user(
                user_context=valid_context,
                websocket_bridge=invalid_bridge,  # SSOT violation: missing interface
                tools=None,
                enable_admin_tools=False
            )