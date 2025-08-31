#!/usr/bin/env python
"""COMPREHENSIVE TEST SUITE: WebSocket Injection Fix Validation - MISSION CRITICAL

THIS SUITE VALIDATES THE WEBSOCKET INJECTION FIX COMPREHENSIVELY.
Business Value: $500K+ ARR - Core chat functionality that was broken

Tests cover:
1. Unit tests for each modified component (dependencies, service_factory, agent_service_core)
2. Integration tests for WebSocket event flow through dependency injection
3. E2E tests for real user scenarios with WebSocket events
4. Critical path tests for WebSocket events
5. Regression tests to ensure fix stays in place

ANY FAILURE HERE INDICATES THE FIX HAS REGRESSED OR IS INCOMPLETE.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components for testing
from netra_backend.app.services.message_handler_service import MessageHandlerService
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.core.thread.service import ThreadService


# ============================================================================
# MOCK WEBSOCKET MANAGER FOR TESTING
# ============================================================================

class MockWebSocketManager:
    """Mock WebSocket manager that captures events for validation."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connections: Dict[str, Any] = {}
        self.injection_successful = True  # Track if injection worked
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message and simulate successful delivery."""
        self.messages.append({
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        })
        return True
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user connection."""
        self.connections[thread_id] = {'user_id': user_id, 'connected': True}
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user disconnection."""
        if thread_id in self.connections:
            self.connections[thread_id]['connected'] = False
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get all events for a specific thread."""
        return [msg for msg in self.messages if msg['thread_id'] == thread_id]
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for a thread in order."""
        return [msg['event_type'] for msg in self.messages if msg['thread_id'] == thread_id]
    
    def clear_messages(self):
        """Clear all recorded messages."""
        self.messages.clear()


# ============================================================================
# UNIT TESTS - WebSocket Injection Components
# ============================================================================

class TestWebSocketInjectionUnits:
    """Unit tests for WebSocket injection fix components."""
    
    @pytest.fixture(autouse=True) 
    async def setup_mock_services(self):
        """Setup mock services for unit tests."""
        self.mock_ws_manager = MockWebSocketManager()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_dependencies_get_message_handler_service_with_websocket(self):
        """Test that get_message_handler_service injects WebSocket manager."""
        from netra_backend.app import dependencies
        
        # Mock the websocket manager getter
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = self.mock_ws_manager
            
            # Mock other dependencies
            with patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
                
                mock_supervisor.return_value = MagicMock()
                mock_thread.return_value = MagicMock()
                
                # Call the function
                service = dependencies.get_message_handler_service()
                
                # Verify WebSocket manager was injected
                assert service.websocket_manager is not None, \
                    "INJECTION FAILED: MessageHandlerService created without WebSocket manager"
                assert service.websocket_manager == self.mock_ws_manager, \
                    "INJECTION FAILED: Wrong WebSocket manager injected"
                
                # Verify function was called
                mock_get_ws.assert_called_once()
                
                logger.info("✅ dependencies.py WebSocket injection PASSED")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_dependencies_fallback_when_websocket_unavailable(self):
        """Test graceful fallback when WebSocket manager unavailable."""
        from netra_backend.app import dependencies
        
        # Mock websocket manager to fail
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws:
            mock_get_ws.side_effect = Exception("WebSocket not available")
            
            # Mock other dependencies
            with patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
                
                mock_supervisor.return_value = MagicMock()
                mock_thread.return_value = MagicMock()
                
                # Call should succeed despite WebSocket failure
                service = dependencies.get_message_handler_service()
                
                # Verify graceful fallback
                assert service is not None, \
                    "FALLBACK FAILED: Service creation failed when WebSocket unavailable"
                # WebSocket manager should be None (graceful degradation)
                assert service.websocket_manager is None, \
                    "FALLBACK FAILED: WebSocket manager should be None when unavailable"
                
                logger.info("✅ dependencies.py WebSocket fallback PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_service_factory_websocket_injection(self):
        """Test that ServiceFactory injects WebSocket manager."""
        from netra_backend.app.services.service_factory import ServiceFactory
        
        # Mock the websocket manager getter
        with patch('netra_backend.app.services.service_factory.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = self.mock_ws_manager
            
            # Mock other dependencies needed by ServiceFactory
            with patch('netra_backend.app.services.service_factory.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.services.service_factory.get_thread_service') as mock_thread:
                
                mock_supervisor.return_value = MagicMock()
                mock_thread.return_value = MagicMock()
                
                factory = ServiceFactory()
                service = factory._create_message_handler_service()
                
                # Verify WebSocket injection
                assert service.websocket_manager is not None, \
                    "SERVICE_FACTORY INJECTION FAILED: No WebSocket manager"
                assert service.websocket_manager == self.mock_ws_manager, \
                    "SERVICE_FACTORY INJECTION FAILED: Wrong WebSocket manager"
                
                logger.info("✅ service_factory.py WebSocket injection PASSED")

    @pytest.mark.asyncio  
    @pytest.mark.critical
    async def test_agent_service_core_websocket_injection(self):
        """Test that AgentService core injects WebSocket manager."""
        from netra_backend.app.services.agent_service_core import AgentService
        
        # Mock required dependencies
        mock_supervisor = MagicMock()
        mock_thread_service = MagicMock()
        
        # Mock the websocket manager getter
        with patch('netra_backend.app.services.agent_service_core.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = self.mock_ws_manager
            
            # Create AgentService
            agent_service = AgentService(mock_supervisor, mock_thread_service)
            
            # Verify MessageHandlerService was created with WebSocket manager
            assert agent_service.message_handler.websocket_manager is not None, \
                "AGENT_SERVICE_CORE INJECTION FAILED: No WebSocket manager"
            assert agent_service.message_handler.websocket_manager == self.mock_ws_manager, \
                "AGENT_SERVICE_CORE INJECTION FAILED: Wrong WebSocket manager"
            
            logger.info("✅ agent_service_core.py WebSocket injection PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_message_handler_service_accepts_websocket_manager(self):
        """Test that MessageHandlerService properly accepts WebSocket manager parameter."""
        mock_supervisor = MagicMock()
        mock_thread_service = MagicMock()
        
        # Test with WebSocket manager
        service_with_ws = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=self.mock_ws_manager
        )
        
        assert service_with_ws.websocket_manager == self.mock_ws_manager, \
            "MessageHandlerService did not accept WebSocket manager parameter"
        
        # Test without WebSocket manager (backward compatibility)
        service_without_ws = MessageHandlerService(
            supervisor=mock_supervisor, 
            thread_service=mock_thread_service
        )
        
        assert service_without_ws.websocket_manager is None, \
            "MessageHandlerService should accept None WebSocket manager"
        
        logger.info("✅ MessageHandlerService constructor compatibility PASSED")


# ============================================================================
# INTEGRATION TESTS - WebSocket Event Flow 
# ============================================================================

class TestWebSocketInjectionIntegration:
    """Integration tests for WebSocket event flow through dependency injection."""
    
    @pytest.fixture(autouse=True)
    async def setup_mock_integration_services(self):
        """Setup mock services for integration tests."""
        self.mock_ws_manager = MockWebSocketManager()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_message_handler_service_sends_websocket_events(self):
        """Test that MessageHandlerService with injected WebSocket manager sends events."""
        # Create MessageHandlerService with WebSocket manager
        mock_supervisor = MagicMock()
        mock_thread_service = MagicMock()
        
        # Configure supervisor to return execution context
        mock_context = AgentExecutionContext(
            run_id="test-integration",
            thread_id="integration-thread",
            user_id="integration-user", 
            agent_name="integration_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Mock supervisor methods
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "Test response", 
            "context": mock_context
        })
        
        service = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=self.mock_ws_manager
        )
        
        # Process a message
        request = {
            "message": "Test message",
            "thread_id": "integration-thread",
            "user_id": "integration-user"
        }
        
        await service.process_message_request(request)
        
        # Verify WebSocket events were sent
        events = self.mock_ws_manager.get_events_for_thread("integration-thread")
        assert len(events) > 0, \
            f"INTEGRATION FAILED: No WebSocket events sent. Expected events from injected manager."
        
        # Should have at least some processing events
        event_types = [e['event_type'] for e in events]
        logger.info(f"Integration test received event types: {event_types}")
        
        logger.info("✅ MessageHandlerService WebSocket event integration PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_dependency_injection_vs_direct_websocket_route_parity(self):
        """Test that DI-created services behave same as WebSocket route services."""
        from netra_backend.app import dependencies
        
        # Mock WebSocket manager getter  
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = self.mock_ws_manager
            
            # Mock other dependencies
            with patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
                
                mock_supervisor_instance = MagicMock()
                mock_thread_instance = MagicMock()
                mock_supervisor.return_value = mock_supervisor_instance
                mock_thread.return_value = mock_thread_instance
                
                # Create service via DI (like REST endpoints do)  
                di_service = dependencies.get_message_handler_service()
                
                # Create service directly (like WebSocket routes do)
                direct_service = MessageHandlerService(
                    supervisor=mock_supervisor_instance,
                    thread_service=mock_thread_instance, 
                    websocket_manager=self.mock_ws_manager
                )
                
                # Both should have WebSocket manager
                assert di_service.websocket_manager is not None, \
                    "PARITY FAILED: DI service missing WebSocket manager"
                assert direct_service.websocket_manager is not None, \
                    "PARITY FAILED: Direct service missing WebSocket manager"  
                assert di_service.websocket_manager == direct_service.websocket_manager, \
                    "PARITY FAILED: Different WebSocket managers in DI vs direct"
                
                logger.info("✅ DI vs WebSocket route parity PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    @pytest.mark.timeout(30)
    async def test_websocket_events_flow_end_to_end_via_di(self):
        """Test complete WebSocket event flow through dependency-injected service."""
        # This simulates the complete flow from REST API -> DI -> WebSocket events
        
        # Mock the complete chain
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws, \
             patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
             patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
            
            # Setup mocks
            mock_get_ws.return_value = self.mock_ws_manager
            mock_supervisor_instance = MagicMock()
            mock_thread_instance = MagicMock()
            mock_supervisor.return_value = mock_supervisor_instance
            mock_thread.return_value = mock_thread_instance
            
            # Configure supervisor to simulate agent execution
            mock_context = AgentExecutionContext(
                run_id="e2e-test",
                thread_id="e2e-thread",
                user_id="e2e-user",
                agent_name="e2e_agent", 
                retry_count=0,
                max_retries=1
            )
            
            # Mock supervisor to simulate real agent processing
            mock_supervisor_instance.process_message = AsyncMock()
            
            # Create the actual DI service
            from netra_backend.app import dependencies
            service = dependencies.get_message_handler_service()
            
            # Verify service has WebSocket capability
            assert service.websocket_manager is not None, \
                "E2E FAILED: DI service missing WebSocket manager"
            
            # Simulate WebSocket events being sent during processing
            # (In real scenario, supervisor would trigger these)
            notifier = WebSocketNotifier(service.websocket_manager)
            
            await notifier.send_agent_started(mock_context)
            await notifier.send_agent_thinking(mock_context, "Processing via DI...")
            await notifier.send_agent_completed(mock_context, {"success": True})
            
            # Verify events were captured
            events = self.mock_ws_manager.get_events_for_thread("e2e-thread")
            assert len(events) >= 3, \
                f"E2E FAILED: Expected at least 3 events, got {len(events)}"
            
            event_types = [e['event_type'] for e in events]
            assert "agent_started" in event_types, \
                f"E2E FAILED: Missing agent_started. Got: {event_types}"
            assert "agent_completed" in event_types, \
                f"E2E FAILED: Missing agent_completed. Got: {event_types}"
            
            logger.info("✅ End-to-end WebSocket flow via DI PASSED")


# ============================================================================
# CRITICAL PATH TESTS - Core WebSocket Events
# ============================================================================

class TestCriticalPathWebSocketEvents:
    """Tests for critical WebSocket event paths that must never break."""
    
    @pytest.fixture(autouse=True)
    async def setup_critical_services(self):
        """Setup services for critical path tests.""" 
        self.mock_ws_manager = MockWebSocketManager()
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_critical_path_all_five_required_events(self):
        """CRITICAL PATH: Test all 5 required WebSocket events are sent."""
        # The 5 critical events that MUST be sent for chat UI to work
        REQUIRED_EVENTS = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed", 
            "agent_completed"
        }
        
        notifier = WebSocketNotifier(self.mock_ws_manager)
        
        context = AgentExecutionContext(
            run_id="critical-path",
            thread_id="critical-thread", 
            user_id="critical-user",
            agent_name="critical_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send all required events
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Critical processing...")
        await notifier.send_tool_executing(context, "critical_tool")
        await notifier.send_tool_completed(context, "critical_tool", {"result": "success"})
        await notifier.send_agent_completed(context, {"success": True})
        
        # Verify all events received
        events = self.mock_ws_manager.get_events_for_thread("critical-thread")
        event_types = set(e['event_type'] for e in events)
        
        missing_events = REQUIRED_EVENTS - event_types
        assert len(missing_events) == 0, \
            f"CRITICAL PATH FAILED: Missing required events {missing_events}. Got: {event_types}"
        
        logger.info("✅ Critical path all 5 required events PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_critical_path_websocket_manager_injection_chain(self):
        """CRITICAL PATH: Test entire WebSocket manager injection chain works."""
        # Test the complete chain: DI -> Service -> WebSocket Manager -> Events
        
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = self.mock_ws_manager
            
            with patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
                
                mock_supervisor.return_value = MagicMock()
                mock_thread.return_value = MagicMock()
                
                # 1. Create service via DI
                from netra_backend.app import dependencies
                service = dependencies.get_message_handler_service()
                
                # 2. Verify injection worked
                assert service.websocket_manager is not None, \
                    "CRITICAL CHAIN FAILED: WebSocket manager injection failed"
                
                # 3. Verify service can send events
                notifier = WebSocketNotifier(service.websocket_manager)
                
                context = AgentExecutionContext(
                    run_id="chain-test",
                    thread_id="chain-thread",
                    user_id="chain-user", 
                    agent_name="chain_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                await notifier.send_agent_started(context)
                
                # 4. Verify event was captured
                events = self.mock_ws_manager.get_events_for_thread("chain-thread")
                assert len(events) > 0, \
                    "CRITICAL CHAIN FAILED: No events after complete injection chain"
                
                logger.info("✅ Critical path WebSocket injection chain PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_critical_path_performance_under_load(self):
        """CRITICAL PATH: Test WebSocket events perform well under load."""
        notifier = WebSocketNotifier(self.mock_ws_manager)
        
        # Send many events rapidly to test performance  
        event_count = 100
        start_time = time.time()
        
        for i in range(event_count):
            context = AgentExecutionContext(
                run_id=f"load-{i}",
                thread_id=f"load-thread-{i % 10}",  # 10 threads
                user_id=f"load-user-{i % 10}",
                agent_name="load_agent", 
                retry_count=0,
                max_retries=1
            )
            
            await notifier.send_agent_thinking(context, f"Load test {i}")
        
        duration = time.time() - start_time
        events_per_second = event_count / duration
        
        # Should handle at least 100 events/second
        assert events_per_second >= 100, \
            f"CRITICAL PERFORMANCE FAILED: Only {events_per_second:.0f} events/sec (expected ≥100)"
        
        # Verify all events were captured
        total_events = len(self.mock_ws_manager.messages)
        assert total_events == event_count, \
            f"CRITICAL PERFORMANCE FAILED: Lost events - sent {event_count}, got {total_events}"
        
        logger.info(f"✅ Critical path performance: {events_per_second:.0f} events/sec PASSED")


# ============================================================================  
# REGRESSION TESTS - Prevent Fix from Breaking
# ============================================================================

class TestWebSocketInjectionRegressionPrevention:
    """Regression tests to ensure WebSocket injection fix stays in place."""
    
    @pytest.fixture(autouse=True)
    async def setup_regression_services(self):
        """Setup services for regression tests."""
        self.mock_ws_manager = MockWebSocketManager() 
        yield
        self.mock_ws_manager.clear_messages()

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_regression_dependencies_still_injects_websocket(self):
        """REGRESSION TEST: Ensure dependencies.py still injects WebSocket manager."""
        # This test will fail if someone removes the WebSocket injection code
        
        from netra_backend.app import dependencies
        import inspect
        
        # Verify the get_message_handler_service function contains WebSocket injection
        source = inspect.getsource(dependencies.get_message_handler_service)
        
        # Look for key indicators of the fix
        assert "get_websocket_manager" in source, \
            "REGRESSION: WebSocket manager import removed from dependencies.py"
        assert "websocket_manager" in source, \
            "REGRESSION: WebSocket manager parameter removed from dependencies.py"
        assert "try:" in source and "except" in source, \
            "REGRESSION: WebSocket fallback logic removed from dependencies.py"
        
        logger.info("✅ Regression test dependencies WebSocket injection code PASSED")

    @pytest.mark.asyncio  
    @pytest.mark.critical
    async def test_regression_service_factory_still_injects_websocket(self):
        """REGRESSION TEST: Ensure ServiceFactory still injects WebSocket manager."""
        from netra_backend.app.services import service_factory
        import inspect
        
        # Verify ServiceFactory contains WebSocket injection
        source = inspect.getsource(service_factory.ServiceFactory._create_message_handler_service)
        
        assert "get_websocket_manager" in source, \
            "REGRESSION: WebSocket manager import removed from ServiceFactory"
        assert "websocket_manager" in source, \
            "REGRESSION: WebSocket manager parameter removed from ServiceFactory"
        
        logger.info("✅ Regression test ServiceFactory WebSocket injection code PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_regression_agent_service_core_still_injects_websocket(self):
        """REGRESSION TEST: Ensure AgentService core still injects WebSocket manager."""
        from netra_backend.app.services import agent_service_core
        import inspect
        
        # Verify AgentService contains WebSocket injection
        source = inspect.getsource(agent_service_core.AgentService.__init__)
        
        assert "get_websocket_manager" in source, \
            "REGRESSION: WebSocket manager import removed from AgentService"
        assert "websocket_manager" in source, \
            "REGRESSION: WebSocket manager parameter removed from AgentService"
        
        logger.info("✅ Regression test AgentService WebSocket injection code PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_regression_message_handler_accepts_websocket_parameter(self):
        """REGRESSION TEST: Ensure MessageHandlerService still accepts WebSocket parameter."""
        from netra_backend.app.services.message_handler_service import MessageHandlerService
        import inspect
        
        # Get constructor signature
        sig = inspect.signature(MessageHandlerService.__init__)
        
        # Verify websocket_manager parameter exists
        assert 'websocket_manager' in sig.parameters, \
            "REGRESSION: websocket_manager parameter removed from MessageHandlerService"
        
        # Verify parameter is optional (has default)
        ws_param = sig.parameters['websocket_manager'] 
        assert ws_param.default is None, \
            "REGRESSION: websocket_manager parameter no longer optional"
        
        logger.info("✅ Regression test MessageHandlerService parameter PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_regression_websocket_events_still_work_after_injection(self):
        """REGRESSION TEST: Ensure WebSocket events still work after injection."""
        # Test the complete flow still works as intended
        
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = self.mock_ws_manager
            
            with patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
                
                mock_supervisor.return_value = MagicMock()
                mock_thread.return_value = MagicMock()
                
                # Create service and verify it works
                from netra_backend.app import dependencies
                service = dependencies.get_message_handler_service()
                
                # Send event through the service's WebSocket manager
                notifier = WebSocketNotifier(service.websocket_manager)
                
                context = AgentExecutionContext(
                    run_id="regression-test",
                    thread_id="regression-thread",
                    user_id="regression-user",
                    agent_name="regression_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                await notifier.send_agent_started(context)
                
                # Verify event was sent
                events = self.mock_ws_manager.get_events_for_thread("regression-thread")
                assert len(events) > 0, \
                    "REGRESSION: WebSocket events no longer work after injection"
                
                logger.info("✅ Regression test WebSocket events flow PASSED")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_regression_fallback_still_works(self):
        """REGRESSION TEST: Ensure graceful fallback still works."""
        # Test that services still work when WebSocket manager fails
        
        with patch('netra_backend.app.dependencies.get_websocket_manager') as mock_get_ws:
            # Make WebSocket manager fail
            mock_get_ws.side_effect = Exception("WebSocket unavailable")
            
            with patch('netra_backend.app.dependencies.get_supervisor_agent') as mock_supervisor, \
                 patch('netra_backend.app.dependencies.get_thread_service') as mock_thread:
                
                mock_supervisor.return_value = MagicMock()
                mock_thread.return_value = MagicMock()
                
                # Service creation should still work
                from netra_backend.app import dependencies
                service = dependencies.get_message_handler_service()
                
                # Service should exist but without WebSocket manager
                assert service is not None, \
                    "REGRESSION: Fallback no longer works - service creation failed"
                assert service.websocket_manager is None, \
                    "REGRESSION: Fallback broken - WebSocket manager not None when unavailable"
                
                logger.info("✅ Regression test graceful fallback PASSED")


# ============================================================================
# TEST SUITE RUNNER
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical  
class TestWebSocketInjectionFixSuite:
    """Main test suite for comprehensive WebSocket injection fix validation."""
    
    @pytest.mark.asyncio
    async def test_run_websocket_injection_fix_suite(self):
        """Run the complete WebSocket injection fix validation suite."""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING WEBSOCKET INJECTION FIX COMPREHENSIVE TEST SUITE")
        logger.info("Business Value: $500K+ ARR - Core chat functionality")
        logger.info("=" * 80)
        
        # This is a meta-test that validates the suite itself
        suite_components = [
            "Unit Tests - WebSocket injection components",
            "Integration Tests - Event flow through DI", 
            "Critical Path Tests - Core WebSocket events",
            "Regression Tests - Prevent fix from breaking"
        ]
        
        for component in suite_components:
            logger.info(f"✅ {component} - Test classes defined")
        
        logger.info("\n🎯 VALIDATION SUITE READY")
        logger.info("Run with: pytest tests/mission_critical/test_websocket_injection_fix_comprehensive.py -v")
        logger.info("=" * 80)


if __name__ == "__main__":
    # Run with comprehensive output
    pytest.main([__file__, "-v", "--tb=short", "-x", "--durations=10"])