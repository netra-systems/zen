"""
Test WebSocket Manager Setup Integration Gaps - Issue #991 Phase 1

This test module creates FAILING integration tests to prove WebSocket manager
setup gaps exist in real service integration scenarios.

Business Value: Protects $500K+ ARR by identifying WebSocket integration gaps
that prevent real-time agent events in the Golden Path user flow.

Test Category: Integration (requires real services)
Purpose: Failing tests that prove WebSocket integration gaps exist
"""
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class WebSocketManagerSetupGapsTests(SSotAsyncTestCase):
    """
    Test WebSocket manager setup integration gaps for Issue #991 Phase 1.
    
    These tests are DESIGNED TO FAIL initially to prove that WebSocket manager
    integration has critical gaps that prevent Golden Path functionality.
    
    Focus: Real service integration scenarios that expose WebSocket setup gaps.
    """

    async def test_websocket_manager_registry_integration_FAILS(self, real_services_fixture):
        """
        TEST DESIGNED TO FAIL: Prove WebSocket manager integration with registry fails.
        
        This test uses real services to validate that WebSocket managers can be
        properly integrated with agent registries for real-time events.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            
            # Create real service components
            llm_manager = LLMManager()
            registry = AgentRegistry(llm_manager=llm_manager)
            
            # Create mock WebSocket manager (simulating real WebSocket service)
            mock_websocket_manager = Mock()
            mock_websocket_manager.emit_event = AsyncMock()
            mock_websocket_manager.is_connected = Mock(return_value=True)
            
            # Test WebSocket manager integration
            integration_failures = []
            
            # Test 1: Can we set a WebSocket manager?
            try:
                if hasattr(registry, 'set_websocket_manager'):
                    set_method = getattr(registry, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(set_method):
                        await set_method(mock_websocket_manager)
                    else:
                        set_method(mock_websocket_manager)
                else:
                    integration_failures.append("set_websocket_manager method missing")
            except Exception as e:
                integration_failures.append(f"set_websocket_manager failed: {e}")
            
            # Test 2: Can we retrieve the WebSocket manager?
            try:
                if hasattr(registry, 'get_websocket_manager'):
                    get_method = getattr(registry, 'get_websocket_manager')
                    if asyncio.iscoroutinefunction(get_method):
                        retrieved_manager = await get_method()
                    else:
                        retrieved_manager = get_method()
                    
                    if retrieved_manager is None:
                        integration_failures.append("get_websocket_manager returns None after setting")
                    elif retrieved_manager != mock_websocket_manager:
                        integration_failures.append("get_websocket_manager returns different instance")
                else:
                    integration_failures.append("get_websocket_manager method missing")
            except Exception as e:
                integration_failures.append(f"get_websocket_manager failed: {e}")
            
            # Test 3: Can we diagnose WebSocket wiring?
            try:
                if hasattr(registry, 'diagnose_websocket_wiring'):
                    diagnosis = registry.diagnose_websocket_wiring()
                    if not isinstance(diagnosis, dict):
                        integration_failures.append("diagnose_websocket_wiring returns non-dict")
                    elif not diagnosis.get('registry_has_websocket_manager', False):
                        integration_failures.append("WebSocket manager not properly wired according to diagnosis")
                else:
                    integration_failures.append("diagnose_websocket_wiring method missing")
            except Exception as e:
                integration_failures.append(f"diagnose_websocket_wiring failed: {e}")
            
            # Test 4: Can agents access WebSocket manager for events?
            try:
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                test_user_context = UserExecutionContext(
                    user_id="test_websocket_user",
                    request_id="test_websocket_request",
                    thread_id="test_websocket_thread",
                    run_id="test_websocket_run"
                )
                
                # Try to create an agent that should have WebSocket access
                if hasattr(registry, 'create_agent_for_user'):
                    agent = await registry.create_agent_for_user(
                        user_id="test_websocket_user",
                        agent_type="triage",
                        user_context=test_user_context,
                        websocket_manager=mock_websocket_manager
                    )
                    
                    if agent is None:
                        integration_failures.append("create_agent_for_user returned None")
                    else:
                        # Check if agent has WebSocket access
                        if not hasattr(agent, '_websocket_bridge') and not hasattr(agent, 'websocket_manager'):
                            integration_failures.append("Created agent has no WebSocket access")
                else:
                    integration_failures.append("create_agent_for_user method missing")
                    
            except Exception as e:
                integration_failures.append(f"Agent WebSocket integration failed: {e}")
            
            # Test 5: Can we emit events through the integration?
            try:
                if hasattr(registry, 'emit_agent_event'):
                    emit_method = getattr(registry, 'emit_agent_event')
                    if asyncio.iscoroutinefunction(emit_method):
                        await emit_method("agent_started", {"agent": "triage", "user_id": "test_user"})
                    else:
                        emit_method("agent_started", {"agent": "triage", "user_id": "test_user"})
                    
                    # Verify the mock was called
                    if not mock_websocket_manager.emit_event.called:
                        integration_failures.append("WebSocket manager emit_event not called")
                else:
                    integration_failures.append("emit_agent_event method missing")
            except Exception as e:
                integration_failures.append(f"Event emission failed: {e}")
            
            if integration_failures:
                self.fail(
                    f"CRITICAL WEBSOCKET INTEGRATION FAILURE CONFIRMED: WebSocket manager integration "
                    f"with agent registry has critical gaps that prevent Golden Path real-time events. "
                    f"Integration failures: {integration_failures}. This blocks the $500K+ ARR chat "
                    f"functionality that depends on real-time agent progress updates."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import required components: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("WebSocket manager integration is working - this test should be updated after Issue #991 Phase 1 fix")

    async def test_user_session_websocket_isolation_FAILS(self, real_services_fixture):
        """
        TEST DESIGNED TO FAIL: Prove user session WebSocket isolation fails.
        
        This test validates that WebSocket events are properly isolated per user
        to prevent cross-user event contamination.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            llm_manager = LLMManager()
            registry = AgentRegistry(llm_manager=llm_manager)
            
            # Create separate WebSocket managers for different users
            user1_ws_manager = Mock()
            user1_ws_manager.emit_event = AsyncMock()
            user1_ws_manager.user_id = "user1"
            
            user2_ws_manager = Mock()
            user2_ws_manager.emit_event = AsyncMock()
            user2_ws_manager.user_id = "user2"
            
            isolation_failures = []
            
            # Test 1: Create isolated user sessions
            try:
                user1_context = UserExecutionContext(
                    user_id="user1",
                    request_id="user1_request",
                    thread_id="user1_thread", 
                    run_id="user1_run"
                )
                
                user2_context = UserExecutionContext(
                    user_id="user2",
                    request_id="user2_request", 
                    thread_id="user2_thread",
                    run_id="user2_run"
                )
                
                # Create user sessions with different WebSocket managers
                if hasattr(registry, 'create_user_session'):
                    session1 = await registry.create_user_session("user1")
                    session2 = await registry.create_user_session("user2")
                    
                    if session1 is None or session2 is None:
                        isolation_failures.append("create_user_session returned None")
                else:
                    isolation_failures.append("create_user_session method missing")
                    
            except Exception as e:
                isolation_failures.append(f"User session creation failed: {e}")
            
            # Test 2: Set different WebSocket managers per user
            try:
                # This should set WebSocket manager only for user1
                session1 = await registry.get_user_session("user1")
                if hasattr(session1, 'set_websocket_manager'):
                    await session1.set_websocket_manager(user1_ws_manager, user1_context)
                else:
                    isolation_failures.append("User session missing set_websocket_manager")
                
                # This should set WebSocket manager only for user2
                session2 = await registry.get_user_session("user2")
                if hasattr(session2, 'set_websocket_manager'):
                    await session2.set_websocket_manager(user2_ws_manager, user2_context)
                else:
                    isolation_failures.append("User session missing set_websocket_manager")
                    
            except Exception as e:
                isolation_failures.append(f"Per-user WebSocket manager setup failed: {e}")
            
            # Test 3: Create agents for each user and verify isolation
            try:
                agent1 = await registry.create_agent_for_user(
                    user_id="user1",
                    agent_type="triage",
                    user_context=user1_context,
                    websocket_manager=user1_ws_manager
                )
                
                agent2 = await registry.create_agent_for_user(
                    user_id="user2", 
                    agent_type="triage",
                    user_context=user2_context,
                    websocket_manager=user2_ws_manager
                )
                
                if agent1 is None or agent2 is None:
                    isolation_failures.append("Agent creation failed for isolated users")
                
                # Verify agents have different WebSocket access
                if hasattr(agent1, '_websocket_bridge') and hasattr(agent2, '_websocket_bridge'):
                    if agent1._websocket_bridge == agent2._websocket_bridge:
                        isolation_failures.append("Agents share the same WebSocket bridge - isolation broken")
                        
            except Exception as e:
                isolation_failures.append(f"Agent creation with isolation failed: {e}")
            
            # Test 4: Verify events are sent to correct user only
            try:
                # Simulate agent1 emitting an event
                if hasattr(registry, 'emit_user_agent_event'):
                    await registry.emit_user_agent_event(
                        user_id="user1",
                        event_type="agent_started",
                        event_data={"agent": "triage", "message": "User1 agent started"}
                    )
                    
                    # User1's WebSocket manager should be called
                    if not user1_ws_manager.emit_event.called:
                        isolation_failures.append("User1 WebSocket manager not called for user1 event")
                    
                    # User2's WebSocket manager should NOT be called
                    if user2_ws_manager.emit_event.called:
                        isolation_failures.append("User2 WebSocket manager called for user1 event - isolation broken")
                else:
                    isolation_failures.append("emit_user_agent_event method missing")
                    
            except Exception as e:
                isolation_failures.append(f"Event isolation testing failed: {e}")
            
            if isolation_failures:
                self.fail(
                    f"CRITICAL USER ISOLATION FAILURE CONFIRMED: WebSocket event isolation per user "
                    f"has critical gaps that allow cross-user event contamination. This creates "
                    f"security vulnerabilities and privacy violations. Isolation failures: {isolation_failures}. "
                    f"This blocks enterprise deployment of the $500K+ ARR platform."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import required components: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("User session WebSocket isolation is working - this test should be updated after Issue #991 Phase 1 fix")

    async def test_websocket_event_delivery_completeness_FAILS(self, real_services_fixture):
        """
        TEST DESIGNED TO FAIL: Prove WebSocket event delivery is incomplete.
        
        This test validates that all 5 critical WebSocket events are properly
        delivered through the registry integration.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            llm_manager = LLMManager()
            registry = AgentRegistry(llm_manager=llm_manager)
            
            # Create WebSocket manager that tracks events
            event_tracker = Mock()
            event_tracker.emit_event = AsyncMock()
            event_tracker.emitted_events = []
            
            def track_event(event_type, event_data):
                event_tracker.emitted_events.append({
                    'type': event_type,
                    'data': event_data
                })
                
            event_tracker.emit_event.side_effect = track_event
            
            # Set up WebSocket manager
            if hasattr(registry, 'set_websocket_manager'):
                set_method = getattr(registry, 'set_websocket_manager')
                if asyncio.iscoroutinefunction(set_method):
                    await set_method(event_tracker)
                else:
                    set_method(event_tracker)
            
            # Required Golden Path events
            required_events = [
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]
            
            event_delivery_failures = []
            
            # Test event delivery for each required event
            for event_type in required_events:
                try:
                    # Test if registry can emit this event type
                    if hasattr(registry, 'emit_agent_event'):
                        emit_method = getattr(registry, 'emit_agent_event')
                        test_data = {
                            'agent': 'triage',
                            'user_id': 'test_user',
                            'message': f'Test {event_type} event'
                        }
                        
                        if asyncio.iscoroutinefunction(emit_method):
                            await emit_method(event_type, test_data)
                        else:
                            emit_method(event_type, test_data)
                        
                        # Check if event was delivered
                        delivered = any(
                            event['type'] == event_type 
                            for event in event_tracker.emitted_events
                        )
                        
                        if not delivered:
                            event_delivery_failures.append(f"{event_type} event not delivered")
                    else:
                        event_delivery_failures.append("emit_agent_event method missing")
                        break
                        
                except Exception as e:
                    event_delivery_failures.append(f"{event_type} event delivery failed: {e}")
            
            # Test event delivery through agent execution
            try:
                user_context = UserExecutionContext(
                    user_id="test_event_user",
                    request_id="test_event_request",
                    thread_id="test_event_thread",
                    run_id="test_event_run"
                )
                
                # Create agent and try to trigger events
                agent = await registry.create_agent_for_user(
                    user_id="test_event_user",
                    agent_type="triage",
                    user_context=user_context,
                    websocket_manager=event_tracker
                )
                
                if agent is not None:
                    # Try to execute agent and capture events
                    if hasattr(agent, 'execute'):
                        # Reset event tracker
                        event_tracker.emitted_events.clear()
                        
                        # This should trigger multiple events
                        try:
                            result = await agent.execute("Test message for event delivery")
                            
                            # Check if all required events were emitted
                            emitted_event_types = [
                                event['type'] for event in event_tracker.emitted_events
                            ]
                            
                            missing_events = [
                                event_type for event_type in required_events
                                if event_type not in emitted_event_types
                            ]
                            
                            if missing_events:
                                event_delivery_failures.append(
                                    f"Agent execution missing events: {missing_events}"
                                )
                                
                        except Exception as e:
                            event_delivery_failures.append(f"Agent execution failed: {e}")
                            
            except Exception as e:
                event_delivery_failures.append(f"Agent event delivery test failed: {e}")
            
            if event_delivery_failures:
                self.fail(
                    f"CRITICAL EVENT DELIVERY FAILURE CONFIRMED: WebSocket event delivery through "
                    f"registry integration is incomplete. Required Golden Path events are not being "
                    f"delivered, which prevents users from seeing real-time agent progress. "
                    f"Event delivery failures: {event_delivery_failures}. This blocks the core "
                    f"real-time chat experience that drives $500K+ ARR business value."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import required components: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("WebSocket event delivery is working - this test should be updated after Issue #991 Phase 1 fix")


if __name__ == '__main__':
    # MIGRATED: Use SSOT unified test runner
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --test-file tests/integration/issue_991_websocket_integration/test_websocket_manager_setup_gaps.py --real-services')