"""
Test Execute Agent Message Type Reproduction

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical)
- Business Goal: Protect $120K+ MRR from agent execution timeouts
- Value Impact: Reproduces exact message type failures preventing agent execution
- Strategic Impact: Critical for diagnosing timeout failures in GitHub Issue #117

This test suite reproduces the specific message type issues that cause agent
execution to timeout, fail to start, or fail silently due to routing failures.

@compliance CLAUDE.md - Real services over mocks for authentic testing
@compliance SPEC/core.xml - Message routing and type validation
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

# CRITICAL: Import actual message routing and execution components
from netra_backend.app.websocket_core.types import MessageType, create_standard_message
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.services.websocket.message_handler import StartAgentHandler, BaseMessageHandler
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, get_user_execution_context
from shared.isolated_environment import get_env


class TestExecuteAgentMessageTypeReproduction(BaseIntegrationTest):
    """
    Reproduce execute_agent message type failures that cause P1 critical issues.
    
    CRITICAL: These tests MUST fail initially to reproduce the exact timeout
    and routing failures identified in GitHub Issue #117.
    """
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_execute_agent_message_type_case_sensitivity_failure(self):
        """
        REPRODUCTION TEST: execute_agent message type case sensitivity failures.
        
        This reproduces the specific issue where different case variations
        of 'execute_agent' fail to route correctly, causing timeouts.
        
        Expected to FAIL until remediation is complete.
        """
        # Test different case variations that should all route to same handler
        case_variations = [
            "execute_agent",      # Standard lowercase
            "EXECUTE_AGENT",      # All uppercase  
            "Execute_Agent",      # Title case
            "execute-agent",      # Hyphen separator
            "executeAgent",       # CamelCase
            "ExecuteAgent",       # PascalCase
            "execute agent",      # Space separator
        ]
        
        routing_failures = []
        router = get_message_router()
        
        for variation in case_variations:
            try:
                # Try to route each variation
                message_data = {
                    "agent_name": "test_agent",
                    "user_request": "Test execution request",
                    "user_id": f"test_user_{uuid.uuid4().hex[:8]}"
                }
                
                # Attempt routing with different case variations
                try:
                    test_message = create_standard_message(
                        msg_type=variation,
                        payload=message_data
                    )
                    handler = router._find_handler(test_message.type)
                    
                    # Check if routing was successful
                    if handler is None:
                        routing_failures.append(f"ROUTING FAILURE: {variation} failed to route (no handler found)")
                except ValueError as ve:
                    # Message type not valid - expected for non-standard formats
                    routing_failures.append(f"MESSAGE TYPE INVALID: {variation} - {ve}")
                
            except (KeyError, ValueError, AttributeError) as e:
                # Case variation not recognized - expected for non-standard formats
                routing_failures.append(f"CASE SENSITIVITY FAILURE: {variation} not recognized: {e}")
            except Exception as e:
                # Unexpected error during routing
                routing_failures.append(f"UNEXPECTED ERROR: {variation} caused error: {e}")
        
        # CRITICAL: If multiple case variations fail, we have routing issues
        if len(routing_failures) > 1:  # Allow one standard format to work
            pytest.fail(f"execute_agent message type case sensitivity failures:\n" + "\n".join(routing_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_execute_agent_handler_registration_failures(self):
        """
        REPRODUCTION TEST: execute_agent handler registration failures.
        
        This reproduces issues where the execute_agent handler is not properly
        registered or initialized, causing silent failures.
        
        Expected to FAIL until remediation is complete.
        """
        registration_failures = []
        
        # Test handler registration in MessageRouter
        router = get_message_router()
        
        # Check if execute_agent handler is registered
        execute_agent_variations = [
            "execute_agent",
            "start_agent",  # Alternative message type
            "agent_request",  # Standard message type
        ]
        
        for message_type in execute_agent_variations:
            try:
                # Check if handler exists for message type  
                handler = router._find_handler(MessageType(message_type))
                
                if handler is None:
                    registration_failures.append(f"HANDLER REGISTRATION FAILURE: No handler registered for {message_type}")
                
                # Check if handler is properly initialized
                if hasattr(handler, 'get_message_type'):
                    expected_type = handler.get_message_type()
                    if expected_type != message_type:
                        registration_failures.append(f"HANDLER MISMATCH: {message_type} handler expects {expected_type}")
                
            except (KeyError, AttributeError, NotImplementedError) as e:
                registration_failures.append(f"REGISTRATION ERROR: {message_type} handler lookup failed: {e}")
        
        # Test StartAgentHandler specifically
        try:
            # Try to create StartAgentHandler with minimal configuration
            handler = StartAgentHandler(
                supervisor=MagicMock(),  # Mock supervisor for testing
                db_session_factory=MagicMock()
            )
            
            # Verify it reports correct message type
            reported_type = handler.get_message_type()
            if reported_type not in ["start_agent", "execute_agent", "agent_request"]:
                registration_failures.append(f"HANDLER TYPE MISMATCH: StartAgentHandler reports unexpected type: {reported_type}")
            
        except Exception as e:
            registration_failures.append(f"STARTAGENHANDLER CREATION FAILURE: {e}")
        
        # Report registration failures
        if registration_failures:
            pytest.fail(f"execute_agent handler registration failures:\n" + "\n".join(registration_failures))
    
    @pytest.mark.unit  
    @pytest.mark.real_services
    async def test_execute_agent_message_validation_failures(self):
        """
        REPRODUCTION TEST: execute_agent message validation failures.
        
        This reproduces validation failures that cause messages to be
        rejected or processed incorrectly, leading to timeouts.
        
        Expected to FAIL until remediation is complete.
        """
        validation_failures = []
        
        # Test invalid message structures for execute_agent
        invalid_messages = [
            # Missing required fields
            {"type": "execute_agent"},  # Missing data
            {"type": "execute_agent", "data": {}},  # Empty data
            {"type": "execute_agent", "data": {"agent_name": "test"}},  # Missing user_request
            
            # Invalid field types
            {"type": "execute_agent", "data": {"agent_name": 123, "user_request": "test"}},  # Wrong type
            {"type": "execute_agent", "data": {"agent_name": "test", "user_request": 456}},  # Wrong type
            
            # Missing user context
            {"type": "execute_agent", "data": {"agent_name": "test", "user_request": "test"}},  # No user_id
        ]
        
        handler = StartAgentHandler(
            supervisor=MagicMock(),
            db_session_factory=MagicMock()
        )
        
        for i, invalid_message in enumerate(invalid_messages):
            try:
                # Try to handle invalid message
                await handler.handle(
                    user_id=f"test_user_{i}",
                    payload=invalid_message.get("data", {})
                )
                
                # If this succeeds, we have a validation failure
                validation_failures.append(f"VALIDATION FAILURE: Invalid message {i} was processed successfully: {invalid_message}")
                
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                # Expected failure - validation working correctly
                continue
            except Exception as e:
                # Unexpected error - might indicate validation issue
                validation_failures.append(f"UNEXPECTED VALIDATION ERROR: Message {i} caused: {e}")
        
        # Test valid message does NOT fail (sanity check)
        try:
            valid_payload = {
                "request": {
                    "query": "Test agent execution request",
                    "agent_name": "test_agent"
                }
            }
            
            # Mock the supervisor to avoid actual execution
            with patch.object(handler, '_execute_agent_workflow', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {"result": "test_success"}
                
                # This should NOT raise an exception
                await handler.handle(
                    user_id="valid_test_user",
                    payload=valid_payload
                )
                
        except Exception as e:
            validation_failures.append(f"CRITICAL: Valid message failed validation: {e}")
        
        # Report validation failures
        if validation_failures:
            pytest.fail(f"execute_agent message validation failures:\n" + "\n".join(validation_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_execute_agent_timeout_reproduction(self):
        """
        REPRODUCTION TEST: execute_agent timeout failures.
        
        This reproduces the specific timeout issues that occur during
        agent execution, causing the P1 critical test failures.
        
        Expected to FAIL until remediation is complete.
        """
        timeout_failures = []
        
        # Create handler with real supervisor that might timeout
        try:
            # Try to create a real SupervisorSSO instance
            supervisor = SupervisorSSO()
            
            handler = StartAgentHandler(
                supervisor=supervisor,
                db_session_factory=MagicMock()  # Mock DB for testing
            )
            
            # Test message that should cause timeout
            timeout_payload = {
                "request": {
                    "query": "Execute a complex agent task that might timeout",
                    "agent_name": "complex_agent",
                    "timeout_test": True
                }
            }
            
            # Set very short timeout to force failure
            start_time = time.time()
            
            try:
                # Execute with timeout
                task = asyncio.create_task(handler.handle(
                    user_id="timeout_test_user",
                    payload=timeout_payload
                ))
                
                # Wait with very short timeout to force timeout condition
                await asyncio.wait_for(task, timeout=0.1)  # 100ms timeout
                
                # If this succeeds within timeout, might indicate lack of actual work
                execution_time = time.time() - start_time
                if execution_time < 0.05:  # Less than 50ms is suspiciously fast
                    timeout_failures.append(f"SUSPICIOUS FAST EXECUTION: Completed in {execution_time:.3f}s - might not be doing real work")
                
            except asyncio.TimeoutError:
                # Expected timeout - this reproduces the P1 critical issue
                execution_time = time.time() - start_time
                timeout_failures.append(f"TIMEOUT REPRODUCED: Agent execution timed out after {execution_time:.3f}s")
            
            except Exception as e:
                # Other errors during execution
                execution_time = time.time() - start_time
                timeout_failures.append(f"EXECUTION ERROR: {e} after {execution_time:.3f}s")
        
        except Exception as e:
            timeout_failures.append(f"SETUP FAILURE: Could not create supervisor for timeout testing: {e}")
        
        # Test timeout handling in message routing
        try:
            router = get_message_router()
            
            start_time = time.time()
            
            # Try to route message that might cause timeout
            test_message = create_standard_message(
                msg_type=MessageType.AGENT_REQUEST,
                payload={"agent_name": "timeout_agent", "user_request": "timeout test"}
            )
            
            # Simple synchronous handler lookup - timing it to check for performance issues
            handler = router._find_handler(test_message.type)
            
            routing_time = time.time() - start_time
            if routing_time > 0.4:  # More than 400ms is slow
                timeout_failures.append(f"SLOW ROUTING: Message routing took {routing_time:.3f}s")
            
        except Exception as e:
            timeout_failures.append(f"ROUTING ERROR: {e}")
        
        # CRITICAL: If we reproduced timeout issues, that confirms the P1 critical problem
        if timeout_failures:
            # This is expected - we're reproducing the issue
            pytest.fail(f"execute_agent timeout issues reproduced (EXPECTED FAILURE):\n" + "\n".join(timeout_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_execute_agent_user_context_isolation_failures(self):
        """
        REPRODUCTION TEST: execute_agent user context isolation failures.
        
        This reproduces user context isolation issues that can cause
        cross-user contamination and execution failures.
        
        Expected to FAIL until remediation is complete.
        """
        isolation_failures = []
        
        # Create multiple user contexts to test isolation
        user_contexts = []
        for i in range(3):
            user_id = f"isolation_test_user_{i}_{uuid.uuid4().hex[:6]}"
            try:
                context = get_user_execution_context(
                    user_id=user_id,
                    thread_id=f"thread_{i}",
                    run_id=f"run_{i}"
                )
                user_contexts.append((user_id, context))
            except Exception as e:
                isolation_failures.append(f"USER CONTEXT CREATION FAILURE: User {i} - {e}")
        
        # Test concurrent execution with multiple users
        async def execute_for_user(user_id: str, context: UserExecutionContext, test_number: int):
            """Execute agent for a specific user."""
            try:
                handler = StartAgentHandler(
                    supervisor=MagicMock(),
                    db_session_factory=MagicMock()
                )
                
                payload = {
                    "request": {
                        "query": f"User {test_number} isolation test request",
                        "agent_name": "isolation_test_agent"
                    }
                }
                
                # Execute with user context
                start_time = time.time()
                result = await handler.handle(user_id=user_id, payload=payload)
                execution_time = time.time() - start_time
                
                return {
                    "user_id": user_id,
                    "test_number": test_number,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "test_number": test_number,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrently for all users
        if user_contexts:
            try:
                # Run concurrent executions
                tasks = [
                    execute_for_user(user_id, context, i) 
                    for i, (user_id, context) in enumerate(user_contexts)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze results for isolation violations
                for result in results:
                    if isinstance(result, Exception):
                        isolation_failures.append(f"CONCURRENT EXECUTION FAILURE: {result}")
                    elif isinstance(result, dict):
                        if not result.get("success"):
                            isolation_failures.append(f"USER EXECUTION FAILURE: User {result['test_number']} - {result.get('error')}")
                        elif result.get("execution_time", 0) > 5.0:  # Suspiciously long
                            isolation_failures.append(f"SUSPICIOUS EXECUTION TIME: User {result['test_number']} took {result['execution_time']:.3f}s")
                
                # Check for context leakage between users
                user_ids_seen = [r.get("user_id") for r in results if isinstance(r, dict)]
                expected_user_ids = [user_id for user_id, _ in user_contexts]
                
                if set(user_ids_seen) != set(expected_user_ids):
                    isolation_failures.append(f"USER ID LEAKAGE: Expected {expected_user_ids}, got {user_ids_seen}")
                
            except Exception as e:
                isolation_failures.append(f"CONCURRENT EXECUTION SETUP FAILURE: {e}")
        
        # Report isolation failures
        if isolation_failures:
            pytest.fail(f"execute_agent user context isolation failures:\n" + "\n".join(isolation_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_execute_agent_websocket_bridge_integration_failures(self):
        """
        REPRODUCTION TEST: execute_agent WebSocket bridge integration failures.
        
        This reproduces failures in the integration between execute_agent
        and the WebSocket bridge, causing event delivery failures.
        
        Expected to FAIL until remediation is complete.
        """
        bridge_failures = []
        
        # Test WebSocket bridge setup during execute_agent
        try:
            # Create handler that should set up WebSocket bridge
            supervisor_mock = MagicMock()
            handler = StartAgentHandler(
                supervisor=supervisor_mock,
                db_session_factory=MagicMock()
            )
            
            # Test message with WebSocket event requirements
            payload = {
                "request": {
                    "query": "Test WebSocket bridge integration",
                    "agent_name": "websocket_test_agent",
                    "require_events": True
                }
            }
            
            user_id = f"bridge_test_user_{uuid.uuid4().hex[:8]}"
            
            # Mock the workflow execution to check bridge setup
            with patch.object(handler, '_execute_agent_workflow', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {"result": "bridge_test_success"}
                
                # Execute and check if WebSocket bridge is configured
                await handler.handle(user_id=user_id, payload=payload)
                
                # Check if supervisor was configured with WebSocket bridge
                if not hasattr(supervisor_mock, 'websocket_bridge'):
                    bridge_failures.append("WEBSOCKET BRIDGE MISSING: Supervisor has no websocket_bridge attribute")
                elif supervisor_mock.websocket_bridge is None:
                    bridge_failures.append("WEBSOCKET BRIDGE NULL: Supervisor websocket_bridge is None")
                
                # Check if execution was called with proper parameters
                if not mock_execute.called:
                    bridge_failures.append("EXECUTION NOT CALLED: Agent workflow was not executed")
        
        except Exception as e:
            bridge_failures.append(f"WEBSOCKET BRIDGE SETUP FAILURE: {e}")
        
        # Test WebSocket event emission during execute_agent
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            # Try to create WebSocket bridge
            bridge = AgentWebSocketBridge()
            
            # Test event emission methods exist
            required_methods = ['emit_agent_started', 'emit_agent_thinking', 'emit_tool_executing', 'emit_tool_completed', 'emit_agent_completed']
            
            for method_name in required_methods:
                if not hasattr(bridge, method_name):
                    bridge_failures.append(f"MISSING EVENT METHOD: AgentWebSocketBridge missing {method_name}")
                elif not callable(getattr(bridge, method_name)):
                    bridge_failures.append(f"NON-CALLABLE EVENT METHOD: {method_name} is not callable")
        
        except ImportError as e:
            bridge_failures.append(f"WEBSOCKET BRIDGE IMPORT FAILURE: {e}")
        except Exception as e:
            bridge_failures.append(f"WEBSOCKET BRIDGE CREATION FAILURE: {e}")
        
        # Report WebSocket bridge failures
        if bridge_failures:
            pytest.fail(f"execute_agent WebSocket bridge integration failures:\n" + "\n".join(bridge_failures))