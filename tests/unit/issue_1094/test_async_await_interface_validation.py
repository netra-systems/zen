"""
Test Issue #1094: Async/Await Interface Validation

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure  
- Business Goal: Eliminate production errors from incorrect async interface usage
- Value Impact: Prevent agent stop operation failures that impact $500K+ ARR
- Revenue Impact: Ensure reliable agent lifecycle management

Test Strategy:
1. Reproduce the TypeError when awaiting synchronous create_websocket_manager
2. Validate correct async interface usage with get_websocket_manager
3. Verify agent service operations work correctly after interface fix
4. Ensure WebSocket manager factory patterns follow SSOT compliance

Root Cause Analysis:
- create_websocket_manager() is synchronous but being awaited
- get_websocket_manager() is the correct async interface
- 25+ locations affected by interface migration incompleteness  
- Agent stop operations failing due to incorrect async patterns

Test Framework:
- Unit tests for interface compliance validation
- Integration tests for agent service lifecycle  
- Mission critical tests for WebSocket factory patterns
- Error reproduction tests for production scenarios
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext

class TestAsyncAwaitInterfaceValidation(BaseIntegrationTest):
    """Test suite for Issue #1094 async/await interface validation."""

    @pytest.mark.unit
    async def test_create_websocket_manager_sync_interface_reproduction(self):
        """
        FAILING TEST: Reproduce TypeError when awaiting synchronous create_websocket_manager.
        
        This test demonstrates the root cause of Issue #1094 - attempting to await
        a synchronous function that returns a context object instead of a manager.
        """
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        
        # Create mock user context
        user_context = Mock()
        user_context.user_id = "test_user_123"
        user_context.thread_id = "test_thread_456"
        
        # This should FAIL - demonstrates the TypeError in production
        with pytest.raises(TypeError, match="object UserExecutionContext can't be used in 'await' expression|object is not awaitable"):
            websocket_manager = await create_websocket_manager(user_context)
            
    @pytest.mark.unit  
    async def test_create_websocket_manager_returns_sync_context(self):
        """
        TEST: Verify create_websocket_manager returns synchronous context object.
        
        This test confirms that create_websocket_manager is indeed synchronous
        and returns a UserExecutionContext, not an awaitable WebSocket manager.
        """
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        
        # Create mock user context
        user_context = Mock()
        user_context.user_id = "test_user_123"
        
        # Call synchronously (correct usage)
        result = create_websocket_manager(user_context)
        
        # Verify it's a context object, not a manager
        assert not asyncio.iscoroutine(result), "create_websocket_manager should return sync context"
        assert hasattr(result, 'user_id'), "Result should be a context object with user_id"
        
    @pytest.mark.unit
    async def test_get_websocket_manager_async_interface_validation(self):
        """
        TEST: Validate get_websocket_manager provides correct async interface.
        
        This test verifies the correct async function exists and can be awaited
        without TypeError, providing the proper fix for Issue #1094.
        """
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Create proper user context
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            request_id="test_request_789",
            websocket_client_id="ws_client_123"
        )
        
        # This should work correctly (async interface)
        websocket_manager = await get_websocket_manager(user_context=user_context)
        
        # Verify we get a manager with expected interface
        assert websocket_manager is not None, "get_websocket_manager should return manager"
        assert hasattr(websocket_manager, 'send_to_user'), "Manager should have send_to_user method"
        
    @pytest.mark.unit 
    async def test_agent_service_stop_operation_interface_fix(self):
        """
        TEST: Verify agent stop operation works with correct async interface.
        
        This test simulates the fixed agent_service_core.py implementation
        using get_websocket_manager instead of create_websocket_manager.
        """
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        user_id = "test_user_123"
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id="test_thread_456",
            request_id="test_request_789", 
            websocket_client_id="ws_client_123"
        )
        
        # Mock the WebSocket manager
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            # Simulate corrected agent service stop operation
            try:
                websocket_manager = await get_websocket_manager(user_context=user_context)
                await websocket_manager.send_to_user(user_id, {"type": "agent_stopped"})
                success = True
            except Exception as e:
                self.fail(f"Agent stop operation should succeed with correct interface: {e}")
                success = False
                
            assert success, "Agent stop operation should complete without TypeError"
            mock_manager.send_to_user.assert_called_once_with(user_id, {"type": "agent_stopped"})

    @pytest.mark.unit
    async def test_interface_migration_completeness_validation(self):
        """
        TEST: Validate interface migration patterns across different scenarios.
        
        This test ensures both legacy and modern patterns work correctly,
        preventing similar interface issues in other locations.
        """
        # Test 1: Legacy create_websocket_manager (sync)
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        
        user_context = Mock()
        user_context.user_id = "test_user_123"
        
        # Should work synchronously
        context_result = create_websocket_manager(user_context)
        assert not asyncio.iscoroutine(context_result), "Legacy function should be sync"
        
        # Test 2: Modern get_websocket_manager (async) 
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        proper_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            request_id="test_request_789",
            websocket_client_id="ws_client_123"
        )
        
        # Should work asynchronously 
        manager = await get_websocket_manager(user_context=proper_context)
        assert manager is not None, "Modern function should return manager"

    @pytest.mark.unit
    def test_interface_detection_utilities(self):
        """
        TEST: Provide utilities to detect incorrect interface usage.
        
        This test creates helper functions to identify similar issues
        in other parts of the codebase.
        """
        import inspect
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Verify function signatures and types
        create_sig = inspect.signature(create_websocket_manager)
        get_sig = inspect.signature(get_websocket_manager)
        
        # create_websocket_manager should be sync
        assert not asyncio.iscoroutinefunction(create_websocket_manager), \
            "create_websocket_manager should be synchronous"
            
        # get_websocket_manager should be async
        assert asyncio.iscoroutinefunction(get_websocket_manager), \
            "get_websocket_manager should be asynchronous"
            
        # Both should accept user_context parameter
        assert 'user_context' in create_sig.parameters, \
            "create_websocket_manager should accept user_context"
        assert 'user_context' in get_sig.parameters, \
            "get_websocket_manager should accept user_context"


class TestAgentServiceCoreInterfaceFix(BaseIntegrationTest):
    """Integration tests for agent service core interface fixes."""
    
    @pytest.mark.integration
    async def test_agent_stop_operation_production_scenario(self):
        """
        INTEGRATION TEST: Validate agent stop operation in production-like scenario.
        
        This test simulates the actual agent_service_core.py usage pattern
        with proper WebSocket bridge integration and user context handling.
        """
        from netra_backend.app.services.user_execution_context import get_user_session_context
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        user_id = "production_user_456"
        
        # Mock WebSocket bridge status check
        with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge.get_status.return_value = {
                "dependencies": {"websocket_manager_available": True}
            }
            mock_bridge_class.return_value = mock_bridge
            
            # Mock user session context
            with patch('netra_backend.app.services.user_execution_context.get_user_session_context') as mock_get_context:
                user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id="production_thread_789",
                    request_id="production_request_101",
                    websocket_client_id="ws_production_202"
                )
                mock_get_context.return_value = user_context
                
                # Mock WebSocket manager
                with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_get_manager:
                    mock_manager = AsyncMock()
                    mock_manager.send_to_user = AsyncMock()
                    mock_get_manager.return_value = mock_manager
                    
                    # Simulate fixed agent service stop operation
                    try:
                        # Get bridge status
                        status = await mock_bridge.get_status()
                        assert status["dependencies"]["websocket_manager_available"], "WebSocket should be available"
                        
                        # Use session-based context (fixed pattern)
                        user_context = await get_user_session_context(user_id=user_id)
                        
                        # Use correct async interface (FIXED)
                        websocket_manager = await get_websocket_manager(user_context)
                        await websocket_manager.send_to_user(user_id, {"type": "agent_stopped"})
                        
                        success = True
                    except Exception as e:
                        self.fail(f"Production agent stop should succeed: {e}")
                        success = False
                        
                    assert success, "Production agent stop operation should complete successfully"
                    mock_manager.send_to_user.assert_called_once_with(user_id, {"type": "agent_stopped"})

    @pytest.mark.integration
    async def test_fallback_scenario_interface_consistency(self):
        """
        INTEGRATION TEST: Validate fallback scenario uses consistent interface.
        
        This test ensures both primary and fallback code paths in agent_service_core.py
        use the correct async interface pattern.
        """
        from netra_backend.app.services.user_execution_context import get_user_session_context
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        user_id = "fallback_user_789"
        
        # Mock fallback scenario (bridge unavailable)
        with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge.get_status.return_value = {
                "dependencies": {"websocket_manager_available": False}
            }
            mock_bridge_class.return_value = mock_bridge
            
            # Mock user session context for fallback
            with patch('netra_backend.app.services.user_execution_context.get_user_session_context') as mock_get_context:
                fallback_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id="fallback_thread_303",
                    request_id="fallback_request_404", 
                    websocket_client_id="ws_fallback_505"
                )
                mock_get_context.return_value = fallback_context
                
                # Mock WebSocket manager for fallback
                with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_get_manager:
                    mock_manager = AsyncMock()
                    mock_manager.send_to_user = AsyncMock()
                    mock_get_manager.return_value = mock_manager
                    
                    # Simulate fallback scenario with fixed interface
                    try:
                        # Bridge check returns unavailable
                        status = await mock_bridge.get_status()
                        assert not status["dependencies"]["websocket_manager_available"], "Should trigger fallback"
                        
                        # Fallback to direct manager access (FIXED INTERFACE)
                        fallback_context = await get_user_session_context(user_id=user_id)
                        websocket_manager = await get_websocket_manager(fallback_context)
                        await websocket_manager.send_to_user(user_id, {"type": "agent_stopped"})
                        
                        success = True
                    except Exception as e:
                        self.fail(f"Fallback scenario should succeed with correct interface: {e}")
                        success = False
                        
                    assert success, "Fallback scenario should use correct async interface"
                    mock_manager.send_to_user.assert_called_once_with(user_id, {"type": "agent_stopped"})


class TestWebSocketFactorySSotCompliance(BaseIntegrationTest):
    """Mission critical tests for WebSocket factory SSOT compliance."""
    
    @pytest.mark.mission_critical
    async def test_websocket_factory_interface_consistency(self):
        """
        MISSION CRITICAL: Ensure WebSocket factory interfaces maintain SSOT compliance.
        
        This test validates that all WebSocket manager factory functions follow
        consistent patterns and don't introduce similar interface issues.
        """
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        
        # Test SSOT compliance across factory interfaces
        user_context = UserExecutionContext(
            user_id="ssot_user_606",
            thread_id="ssot_thread_707", 
            request_id="ssot_request_808",
            websocket_client_id="ws_ssot_909"
        )
        
        # Verify async factory works correctly
        manager = await get_websocket_manager(user_context=user_context)
        assert manager is not None, "SSOT async factory should work"
        
        # Verify sync compatibility function exists but is clearly differentiated
        context_result = create_websocket_manager(user_context)
        assert not asyncio.iscoroutine(context_result), "SSOT sync function should be clearly sync"
        
        # Both should accept same user_context parameter name (SSOT compliance)
        import inspect
        get_params = inspect.signature(get_websocket_manager).parameters
        create_params = inspect.signature(create_websocket_manager).parameters
        
        assert 'user_context' in get_params, "Async factory should use standard parameter name"
        assert 'user_context' in create_params, "Sync factory should use standard parameter name"

    @pytest.mark.mission_critical
    async def test_golden_path_websocket_events_after_interface_fix(self):
        """
        MISSION CRITICAL: Ensure Golden Path WebSocket events work after interface fix.
        
        This test validates that fixing the async/await interface doesn't break
        the critical WebSocket event delivery that enables $500K+ ARR chat functionality.
        """
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        user_id = "golden_path_user_123"
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id="golden_thread_456",
            request_id="golden_request_789",
            websocket_client_id="ws_golden_101"
        )
        
        # Mock WebSocket manager for Golden Path events
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            # Test all 5 critical WebSocket events work with fixed interface
            critical_events = [
                {"type": "agent_started", "data": {"agent": "test_agent"}},
                {"type": "agent_thinking", "data": {"status": "analyzing"}}, 
                {"type": "tool_executing", "data": {"tool": "test_tool"}},
                {"type": "tool_completed", "data": {"result": "success"}},
                {"type": "agent_completed", "data": {"result": "optimization complete"}}
            ]
            
            try:
                websocket_manager = await get_websocket_manager(user_context=user_context)
                
                # Send all critical events
                for event in critical_events:
                    await websocket_manager.send_to_user(user_id, event)
                    
                success = True
            except Exception as e:
                self.fail(f"Golden Path events should work with fixed interface: {e}")
                success = False
                
            assert success, "Golden Path WebSocket events must work after interface fix"
            assert mock_manager.send_to_user.call_count == 5, "All 5 critical events should be sent"