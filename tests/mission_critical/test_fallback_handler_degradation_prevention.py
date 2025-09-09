"""
Mission Critical Test Suite: Fallback Handler Degradation Prevention

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core system reliability
- Business Goal: Prevent fallback handlers from degrading real agent business value
- Value Impact: Ensure users always receive authentic AI agent responses, not mock fallbacks
- Strategic Impact: Protects core business value delivery and prevents service degradation

CRITICAL: This test suite prevents the fallback anti-pattern identified in the Five-Whys analysis.
The root cause was that fallback handlers provide mock responses instead of real AI value,
violating SSOT principles and delivering no business value while appearing to "work".

These tests are designed to FAIL HARD when fallback handlers are used inappropriately,
ensuring that only real agent infrastructure delivers responses to users.
"""

import pytest
import asyncio
import time
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient
from test_framework.real_services_test_fixtures import real_services_fixture

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.managers.unified_lifecycle_manager import UnifiedLifecycleManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class MockServiceController:
    """Controller to simulate service unavailability for testing race conditions."""
    
    def __init__(self):
        self.original_services = {}
        self.mocked_services = set()
    
    async def disable_agent_supervisor(self, app_state):
        """Disable agent_supervisor to simulate startup race condition."""
        if hasattr(app_state, 'agent_supervisor'):
            self.original_services['agent_supervisor'] = app_state.agent_supervisor
            app_state.agent_supervisor = None
            self.mocked_services.add('agent_supervisor')
    
    async def disable_thread_service(self, app_state):
        """Disable thread_service to simulate startup race condition."""
        if hasattr(app_state, 'thread_service'):
            self.original_services['thread_service'] = app_state.thread_service
            app_state.thread_service = None
            self.mocked_services.add('thread_service')
    
    async def force_startup_incomplete(self, app_state):
        """Force startup_complete=False to simulate boot race condition."""
        if hasattr(app_state, 'startup_complete'):
            self.original_services['startup_complete'] = app_state.startup_complete
            app_state.startup_complete = False
            self.mocked_services.add('startup_complete')
    
    async def restore_all_services(self, app_state):
        """Restore all disabled services."""
        for service_name, original_value in self.original_services.items():
            setattr(app_state, service_name, original_value)
        self.original_services.clear()
        self.mocked_services.clear()


class BusinessValueValidator:
    """Validates that responses contain real business value, not mock content."""
    
    MOCK_INDICATORS = [
        # Fallback handler mock patterns
        "Agent processed your message:",
        "FallbackAgentHandler",
        "Processing your message:",
        "response_generator",
        "mock agent responses",
        "fallback",
        "ChatAgent",  # Generic fallback agent name
        
        # Emergency handler patterns
        "EmergencyWebSocketManager",
        "emergency_mode",
        "degraded functionality",
        "limited functionality",
        "basic functionality",
        
        # Service unavailable patterns
        "service_info",
        "missing_dependencies",
        "fallback_active",
        "reduced functionality"
    ]
    
    REAL_BUSINESS_VALUE_INDICATORS = [
        # Real agent patterns
        "cost_optimization",
        "data_analysis",
        "recommendations",
        "insights",
        "action_items",
        "analysis_results",
        "optimization_opportunities",
        "performance_metrics",
        
        # Real tool execution
        "tool_result",
        "analysis_complete",
        "data_processed",
        "optimization_complete"
    ]
    
    def validate_real_agent_response(self, response_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that response contains real business value, not mock content.
        
        Returns:
            Tuple[bool, List[str]]: (is_real, list_of_violations)
        """
        violations = []
        response_str = json.dumps(response_data).lower()
        
        # Check for mock indicators (SHOULD NOT be present)
        for mock_indicator in self.MOCK_INDICATORS:
            if mock_indicator.lower() in response_str:
                violations.append(f"Mock indicator found: '{mock_indicator}'")
        
        # Check for real business value indicators (SHOULD be present)
        has_real_value = any(
            indicator.lower() in response_str 
            for indicator in self.REAL_BUSINESS_VALUE_INDICATORS
        )
        
        if not has_real_value:
            violations.append("No real business value indicators found")
        
        # Additional validation: Check event structure
        if 'events' in response_data:
            for event in response_data.get('events', []):
                event_str = json.dumps(event).lower()
                for mock_indicator in self.MOCK_INDICATORS:
                    if mock_indicator.lower() in event_str:
                        violations.append(f"Mock content in event: '{mock_indicator}' in {event.get('type', 'unknown')}")
        
        is_real = len(violations) == 0
        return is_real, violations


class TestFallbackHandlerDegradationPrevention(BaseE2ETest):
    """Mission critical tests to prevent fallback handler degradation."""
    
    @pytest.fixture
    def mock_service_controller(self):
        """Controller for simulating service unavailability."""
        return MockServiceController()
    
    @pytest.fixture
    def business_value_validator(self):
        """Validator for ensuring real business value in responses."""
        return BusinessValueValidator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for authentic business value testing."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    @pytest.mark.fallback_prevention
    async def test_agent_supervisor_unavailable_should_fail_hard(
        self,
        real_services_fixture: Dict[str, Any],
        mock_service_controller: MockServiceController,
        business_value_validator: BusinessValueValidator
    ):
        """
        CRITICAL TEST: When agent_supervisor is None, system MUST fail hard, not use fallbacks.
        
        This test reproduces the exact condition from websocket.py line 529:
        if supervisor is None: ... _create_fallback_agent_handler
        
        EXPECTED BEHAVIOR: System should WAIT for real supervisor or FAIL, never use fallback.
        """
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="supervisor_fail_test@mission_critical.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        try:
            # Connect to WebSocket BEFORE disabling supervisor (simulates race condition)
            websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
            websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
                timeout=10.0
            )
            
            # SIMULATE RACE CONDITION: Disable agent_supervisor after connection
            # This simulates the startup race condition where WebSocket connects 
            # before agent_supervisor is fully initialized
            app_state = real_services_fixture.get('app_state')
            if app_state:
                await mock_service_controller.disable_agent_supervisor(app_state)
            
            # Send agent request that would trigger fallback handler
            agent_request = {
                "type": "user_message",
                "content": "Optimize my cloud costs and provide detailed recommendations",
                "thread_id": str(user_context.thread_id),
                "agent_name": "cost_optimizer",
                "timestamp": time.time()
            }
            
            await websocket_connection.send(json.dumps(agent_request))
            
            # Collect all events with timeout
            events = []
            start_time = time.time()
            timeout = 15.0  # Reasonable timeout for real system
            
            try:
                while time.time() - start_time < timeout:
                    event_raw = await asyncio.wait_for(
                        websocket_connection.recv(), 
                        timeout=2.0
                    )
                    event = json.loads(event_raw)
                    events.append(event)
                    
                    # Stop collecting if we get agent_completed (should not happen with missing supervisor)
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass  # Expected when system properly fails without supervisor
            
            # CRITICAL VALIDATION: System should NOT create fallback responses
            if events:
                # If we got any events, validate they are NOT from fallback handlers
                for event in events:
                    is_real, violations = business_value_validator.validate_real_agent_response(event)
                    
                    if not is_real:
                        pytest.fail(
                            f"FALLBACK HANDLER DETECTED: System used fallback instead of failing hard.\n"
                            f"Event: {event.get('type', 'unknown')}\n"
                            f"Violations: {violations}\n"
                            f"This violates SSOT principles and provides no business value."
                        )
                
                # If we got agent_completed, it better be from a REAL agent, not fallback
                completed_events = [e for e in events if e.get('type') == 'agent_completed']
                if completed_events:
                    for completed_event in completed_events:
                        # Check for fallback signatures in final response
                        final_response = completed_event.get('final_response', '')
                        if any(mock_word in final_response.lower() for mock_word in 
                               business_value_validator.MOCK_INDICATORS):
                            pytest.fail(
                                f"FALLBACK RESPONSE DETECTED: agent_completed contains mock content.\n"
                                f"Response: {final_response}\n"
                                f"System should wait for real supervisor, not send fake responses."
                            )
            
            # ALTERNATIVE ACCEPTABLE BEHAVIOR: System waits and eventually succeeds with real supervisor
            # OR system properly fails with clear error message (not fallback)
            
            self.logger.info("✅ SUCCESS: System did not create fallback handlers when supervisor unavailable")
            
        finally:
            # Restore services for other tests
            if 'app_state' in locals():
                await mock_service_controller.restore_all_services(app_state)
            
            # Close WebSocket connection
            try:
                await websocket_connection.close()
            except:
                pass
    
    @pytest.mark.e2e
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    @pytest.mark.fallback_prevention
    async def test_thread_service_unavailable_should_fail_hard(
        self,
        real_services_fixture: Dict[str, Any],
        mock_service_controller: MockServiceController,
        business_value_validator: BusinessValueValidator
    ):
        """
        CRITICAL TEST: When thread_service is None, system MUST fail hard, not use fallbacks.
        
        This test reproduces the exact condition from websocket.py line 549:
        if thread_service is None: ... fallback handler creation
        
        EXPECTED BEHAVIOR: System should WAIT for real thread_service or FAIL, never use fallback.
        """
        
        # Create authenticated user context  
        user_context = await create_authenticated_user_context(
            user_email="thread_fail_test@mission_critical.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        try:
            # Connect WebSocket
            websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
            websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
                timeout=10.0
            )
            
            # SIMULATE RACE CONDITION: Disable thread_service after connection
            app_state = real_services_fixture.get('app_state')
            if app_state:
                await mock_service_controller.disable_thread_service(app_state)
            
            # Send message that requires thread management
            thread_request = {
                "type": "user_message", 
                "content": "Create a new optimization thread and analyze my infrastructure costs",
                "thread_id": str(user_context.thread_id),
                "requires_thread_management": True,
                "timestamp": time.time()
            }
            
            await websocket_connection.send(json.dumps(thread_request))
            
            # Collect events with timeout
            events = []
            start_time = time.time()
            timeout = 15.0
            
            try:
                while time.time() - start_time < timeout:
                    event_raw = await asyncio.wait_for(
                        websocket_connection.recv(),
                        timeout=2.0
                    )
                    event = json.loads(event_raw)
                    events.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass
            
            # CRITICAL VALIDATION: No fallback responses
            for event in events:
                is_real, violations = business_value_validator.validate_real_agent_response(event)
                
                if not is_real:
                    pytest.fail(
                        f"THREAD SERVICE FALLBACK DETECTED: System used fallback when thread_service unavailable.\n"
                        f"Event type: {event.get('type', 'unknown')}\n"
                        f"Violations: {violations}\n"
                        f"System should fail properly, not provide mock thread management."
                    )
            
            self.logger.info("✅ SUCCESS: System did not create fallback handlers when thread_service unavailable")
            
        finally:
            # Cleanup
            if 'app_state' in locals():
                await mock_service_controller.restore_all_services(app_state)
            try:
                await websocket_connection.close()
            except:
                pass
    
    @pytest.mark.e2e
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    @pytest.mark.startup_race_condition
    async def test_startup_incomplete_should_wait_or_fail_not_fallback(
        self,
        real_services_fixture: Dict[str, Any],
        mock_service_controller: MockServiceController,
        business_value_validator: BusinessValueValidator
    ):
        """
        CRITICAL TEST: When startup_complete=False, system should wait or fail, not use fallbacks.
        
        This test reproduces the startup race condition where WebSocket connections
        are attempted before system initialization is complete.
        
        EXPECTED BEHAVIOR: Wait for startup_complete=True or fail with clear error.
        """
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="startup_race_test@mission_critical.test", 
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        try:
            # SIMULATE STARTUP RACE: Force startup_complete=False
            app_state = real_services_fixture.get('app_state')
            if app_state:
                await mock_service_controller.force_startup_incomplete(app_state)
            
            # Attempt WebSocket connection during "startup"
            websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
            
            connection_start_time = time.time()
            
            try:
                websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
                    timeout=10.0
                )
                
                # Send agent request during startup
                startup_request = {
                    "type": "user_message",
                    "content": "Perform comprehensive cost analysis during system startup", 
                    "thread_id": str(user_context.thread_id),
                    "timestamp": time.time()
                }
                
                await websocket_connection.send(json.dumps(startup_request))
                
                # Collect events
                events = []
                timeout = 20.0  # Longer timeout for startup scenario
                start_time = time.time()
                
                try:
                    while time.time() - start_time < timeout:
                        event_raw = await asyncio.wait_for(
                            websocket_connection.recv(),
                            timeout=3.0
                        )
                        event = json.loads(event_raw)
                        events.append(event)
                        
                        # Check for startup completion indicators
                        if event.get('type') == 'system_message' and 'startup_complete' in str(event):
                            # System notified of startup completion - this is acceptable
                            continue
                        
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    # Timeout is acceptable - system should wait for startup
                    pass
                
                # CRITICAL VALIDATION: Any responses must be from real system, not fallbacks
                for event in events:
                    # Skip system messages about startup status
                    if event.get('type') == 'system_message':
                        continue
                    
                    is_real, violations = business_value_validator.validate_real_agent_response(event)
                    
                    if not is_real:
                        pytest.fail(
                            f"STARTUP FALLBACK DETECTED: System provided fallback during startup_complete=False.\n"
                            f"Event: {event.get('type', 'unknown')}\n" 
                            f"Violations: {violations}\n"
                            f"System should wait for full startup, not send mock responses."
                        )
                
                connection_duration = time.time() - connection_start_time
                
                # If we got quick responses (< 2 seconds), they're likely fallbacks
                if events and connection_duration < 2.0:
                    completed_events = [e for e in events if e.get('type') == 'agent_completed']
                    if completed_events:
                        pytest.fail(
                            f"SUSPICIOUS FAST RESPONSE: Got agent_completed in {connection_duration:.2f}s during startup.\n"
                            f"This is likely a fallback response, not real agent processing.\n"
                            f"Real agents should wait for startup_complete=True."
                        )
                
                self.logger.info(f"✅ SUCCESS: System handled startup race condition properly ({connection_duration:.2f}s)")
                
            except Exception as connection_error:
                # Connection failure during startup is acceptable behavior
                self.logger.info(f"✅ ACCEPTABLE: WebSocket connection failed during startup: {connection_error}")
                # This is actually good - system is properly failing instead of using fallbacks
            
        finally:
            # Restore services
            if 'app_state' in locals():
                await mock_service_controller.restore_all_services(app_state)
            
            # Cleanup connection if it exists
            if 'websocket_connection' in locals():
                try:
                    await websocket_connection.close()
                except:
                    pass
    
    @pytest.mark.e2e
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    @pytest.mark.business_value_validation
    async def test_real_agent_provides_authentic_business_value(
        self,
        real_services_fixture: Dict[str, Any],
        real_agent_registry: AgentRegistry,
        business_value_validator: BusinessValueValidator
    ):
        """
        POSITIVE TEST: Verify that real agent infrastructure provides authentic business value.
        
        This test establishes the baseline for what real agent responses should look like,
        providing a contrast to fallback handlers.
        
        EXPECTED BEHAVIOR: Real agents provide actionable insights, not mock responses.
        """
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="real_value_test@mission_critical.test",
            environment="test", 
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        try:
            # Connect with real WebSocket infrastructure
            websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
            websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
                timeout=15.0
            )
            
            # Send request requiring real business analysis
            business_request = {
                "type": "user_message",
                "content": "Analyze my cloud infrastructure costs and provide specific optimization recommendations with ROI calculations",
                "thread_id": str(user_context.thread_id),
                "agent_name": "cost_optimizer",  # Request specific high-value agent
                "timestamp": time.time()
            }
            
            await websocket_connection.send(json.dumps(business_request))
            
            # Collect all events until completion
            events = []
            timeout = 45.0  # Real agents need time for actual processing
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    event_raw = await asyncio.wait_for(
                        websocket_connection.recv(),
                        timeout=5.0
                    )
                    event = json.loads(event_raw)
                    events.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    break
            
            # CRITICAL VALIDATION: Must have received events
            assert len(events) > 0, "No events received - system may be completely broken"
            
            # CRITICAL VALIDATION: All events must contain real business value
            for event in events:
                is_real, violations = business_value_validator.validate_real_agent_response(event)
                
                assert is_real, (
                    f"REAL AGENT COMPROMISED: Event contains mock/fallback content.\n"
                    f"Event type: {event.get('type', 'unknown')}\n"
                    f"Violations: {violations}\n"
                    f"Event data: {json.dumps(event, indent=2)}\n"
                    f"Real agents must provide authentic business value, not mock responses."
                )
            
            # CRITICAL VALIDATION: Must have received all 5 WebSocket events
            event_types = {event.get('type') for event in events}
            required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
            
            missing_events = required_events - event_types
            if missing_events:
                pytest.fail(
                    f"MISSING CRITICAL EVENTS: {missing_events}\n"
                    f"Received events: {list(event_types)}\n"
                    f"All 5 WebSocket events are required for authentic agent experience."
                )
            
            # CRITICAL VALIDATION: Final response must contain actionable business value
            completed_events = [e for e in events if e.get('type') == 'agent_completed']
            assert len(completed_events) > 0, "No agent_completed event received"
            
            final_response = completed_events[0].get('final_response', '')
            assert len(final_response) > 50, (
                f"Final response too short ({len(final_response)} chars), likely mock content.\n"
                f"Response: {final_response}"
            )
            
            # Check for specific business value indicators
            response_lower = final_response.lower()
            has_optimization_content = any(
                keyword in response_lower for keyword in 
                ['cost', 'saving', 'optimization', 'recommendation', 'analysis', 'efficiency']
            )
            
            assert has_optimization_content, (
                f"Final response lacks business optimization content.\n"
                f"Response: {final_response}\n"
                f"Real agents must provide specific business insights."
            )
            
            processing_duration = time.time() - start_time
            
            # Real agent processing should take reasonable time (not instant like fallbacks)
            assert processing_duration >= 2.0, (
                f"Processing completed too quickly ({processing_duration:.2f}s).\n"
                f"This suggests fallback/mock responses instead of real agent processing."
            )
            
            assert processing_duration <= 60.0, (
                f"Processing took too long ({processing_duration:.2f}s).\n"
                f"System may be failing but not reporting errors properly."
            )
            
            self.logger.info(f"✅ SUCCESS: Real agent provided authentic business value in {processing_duration:.2f}s")
            self.logger.info(f"  - Events received: {len(events)}")
            self.logger.info(f"  - Event types: {list(event_types)}")
            self.logger.info(f"  - Response length: {len(final_response)} characters")
            
        finally:
            # Cleanup
            try:
                await websocket_connection.close()
            except:
                pass
    
    @pytest.mark.e2e
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    @pytest.mark.fallback_prevention
    async def test_multiple_service_failures_should_not_cascade_to_fallbacks(
        self,
        real_services_fixture: Dict[str, Any], 
        mock_service_controller: MockServiceController,
        business_value_validator: BusinessValueValidator
    ):
        """
        CRITICAL TEST: Multiple service failures should result in proper errors, not fallback cascades.
        
        This test simulates the worst-case scenario where multiple services are unavailable
        simultaneously, which could trigger multiple fallback handler creations.
        
        EXPECTED BEHAVIOR: System should fail gracefully with clear error messages,
        not create a chain of fallback handlers that provide no business value.
        """
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="multi_failure_test@mission_critical.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        try:
            # SIMULATE CATASTROPHIC FAILURE: Disable multiple critical services
            app_state = real_services_fixture.get('app_state')
            if app_state:
                await mock_service_controller.disable_agent_supervisor(app_state)
                await mock_service_controller.disable_thread_service(app_state) 
                await mock_service_controller.force_startup_incomplete(app_state)
            
            # Attempt WebSocket connection in degraded state
            websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
            
            try:
                websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
                    timeout=8.0
                )
                
                # Send high-value business request that requires all services
                critical_request = {
                    "type": "user_message",
                    "content": "Perform comprehensive multi-cloud cost optimization analysis with detailed recommendations",
                    "thread_id": str(user_context.thread_id),
                    "agent_name": "cost_optimizer",
                    "priority": "high",
                    "timestamp": time.time()
                }
                
                await websocket_connection.send(json.dumps(critical_request))
                
                # Monitor for any responses (should be minimal or none)
                events = []
                timeout = 10.0  # Shorter timeout for failure case
                start_time = time.time()
                
                try:
                    while time.time() - start_time < timeout:
                        event_raw = await asyncio.wait_for(
                            websocket_connection.recv(),
                            timeout=1.0
                        )
                        event = json.loads(event_raw)
                        events.append(event)
                        
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    # Timeout is expected when services are unavailable
                    pass
                
                # CRITICAL VALIDATION: Any responses must NOT be from fallback handlers
                for event in events:
                    # Allow system error messages
                    if event.get('type') in ['system_message', 'error', 'connection_error']:
                        continue
                    
                    is_real, violations = business_value_validator.validate_real_agent_response(event)
                    
                    if not is_real:
                        pytest.fail(
                            f"CASCADING FALLBACK DETECTED: Multiple service failures triggered fallback responses.\n"
                            f"Event type: {event.get('type', 'unknown')}\n"
                            f"Violations: {violations}\n"
                            f"Disabled services: {list(mock_service_controller.mocked_services)}\n"
                            f"System should fail clearly, not provide mock business value."
                        )
                
                # If we got agent_completed despite multiple failures, that's suspicious
                completed_events = [e for e in events if e.get('type') == 'agent_completed']
                if completed_events:
                    pytest.fail(
                        f"IMPOSSIBLE COMPLETION: Got agent_completed despite multiple service failures.\n"
                        f"Disabled services: {list(mock_service_controller.mocked_services)}\n"
                        f"This indicates fallback handlers are masking critical system failures.\n"
                        f"Events: {[e.get('type') for e in events]}"
                    )
                
                self.logger.info("✅ SUCCESS: Multiple service failures did not trigger fallback cascade")
                
            except Exception as multi_failure_error:
                # Connection/processing failure is the expected and correct behavior
                self.logger.info(f"✅ EXPECTED FAILURE: System properly failed with multiple services unavailable: {multi_failure_error}")
                
                # Verify the error is meaningful, not a generic fallback error
                error_message = str(multi_failure_error).lower()
                fallback_error_indicators = ['fallback', 'degraded', 'mock', 'chatgent']
                
                has_fallback_error = any(indicator in error_message for indicator in fallback_error_indicators)
                if has_fallback_error:
                    pytest.fail(
                        f"FALLBACK ERROR DETECTED: Error message indicates fallback handlers were attempted.\n"
                        f"Error: {multi_failure_error}\n"
                        f"System should fail with service-specific errors, not fallback errors."
                    )
                
        finally:
            # Restore all services for subsequent tests
            if 'app_state' in locals():
                await mock_service_controller.restore_all_services(app_state)
            
            # Cleanup connection if it exists
            if 'websocket_connection' in locals():
                try:
                    await websocket_connection.close()
                except:
                    pass


if __name__ == "__main__":
    """
    Run fallback degradation prevention tests directly.
    
    These tests are designed to FAIL HARD when the system creates fallback handlers
    instead of providing real business value or failing gracefully.
    """
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "-x",  # Stop on first failure
        "--real-services",
        "--log-cli-level=INFO"
    ])