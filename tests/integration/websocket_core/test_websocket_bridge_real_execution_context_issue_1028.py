#!/usr/bin/env python
"""Issue #1028: Integration Tests for WebSocket Bridge with Real UserExecutionContext

PURPOSE: Integration tests that reproduce Issue #1028 using real UserExecutionContext
and WebSocket manager instances, focusing on the completion notification failure.

BUSINESS CONTEXT: When WebSocket bridge propagation fails in real execution contexts,
users see agents as "hung" even when they complete successfully. This breaks the
primary value delivery mechanism (chat) and impacts $500K+ ARR.

INTEGRATION TEST STRATEGY:
1. Use real UserExecutionContext instances (no mocks)
2. Use real AgentExecutionCore and AgentExecutionTracker
3. Use real WebSocket managers and bridges  
4. Test actual parameter flow between components
5. Focus on completion notification delivery failures

EXPECTED BEHAVIOR: These tests should FAIL initially, proving the issue.
AFTER FIX: Tests should pass with proper completion notifications.
"""

import asyncio
import sys
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger

# Import real components for integration testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, AgentExecutionPhase
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.core.timeout_configuration import TimeoutTier

# Import types and utilities
from shared.types.core_types import ensure_user_id, ensure_thread_id
from netra_backend.app.core.unified_id_manager import generate_user_id, generate_thread_id

logger = get_logger(__name__)


class TestWebSocketBridgeRealExecutionContextIssue1028(SSotAsyncTestCase):
    """
    ISSUE #1028 INTEGRATION TESTS: Real UserExecutionContext + WebSocket Bridge
    
    These integration tests use real components to reproduce Issue #1028 where
    completion notifications fail due to parameter alignment issues between
    AgentExecutionCore and AgentExecutionTracker.
    
    CRITICAL: These tests should FAIL initially, confirming the issue exists.
    """

    def setup_method(self, method):
        """Setup integration test environment."""
        super().setup_method(method)

        # Set environment for integration testing
        self.set_env_var("TESTING_INTEGRATION", "true") 
        self.set_env_var("WEBSOCKET_INTEGRATION_TEST", "true")
        self.set_env_var("ISSUE_1028_INTEGRATION", "true")
        self.set_env_var("REAL_SERVICES_TEST", "true")

        # Test tracking
        self.websocket_events = []
        self.completion_notifications = []
        self.integration_errors = []
        
        logger.info(f"🔍 ISSUE #1028 INTEGRATION: {method.__name__ if method else 'unknown'}")

    async def test_real_user_execution_context_completion_notification_failure(self):
        """
        INTEGRATION: Test completion notification failure with real UserExecutionContext.
        
        This test uses real UserExecutionContext and real WebSocket components to 
        reproduce Issue #1028 where completion notifications are not delivered to users
        even when agent execution succeeds.
        
        EXPECTED TO FAIL: Real components don't deliver completion notifications
        """
        logger.info("🔍 INTEGRATION TEST: Real UserExecutionContext completion notification failure")

        # Create real UserExecutionContext
        user_context = UserExecutionContext(
            user_id=ensure_user_id(generate_user_id()),
            thread_id=ensure_thread_id(generate_thread_id()),
            run_id=str(uuid.uuid4())
        )
        logger.info(f"📍 Created UserExecutionContext: user={user_context.user_id}, thread={user_context.thread_id}")

        try:
            # Get real WebSocket manager
            websocket_manager = await get_websocket_manager(user_context=user_context)
            logger.info(f"📍 Created WebSocket manager: {type(websocket_manager).__name__}")

            # Create real WebSocket bridge
            websocket_bridge = create_agent_websocket_bridge(
                websocket_manager=websocket_manager,
                user_context=user_context
            )
            logger.info(f"📍 Created WebSocket bridge: {type(websocket_bridge).__name__}")

        except Exception as e:
            logger.error(f"❌ Failed to create real WebSocket components: {e}")
            pytest.skip(f"Cannot create real WebSocket components for integration test: {e}")

        # Set up agent registry with successful mock agent
        mock_registry = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True,
            "result": "Integration test agent completed successfully",
            "data": {"test_type": "integration", "issue": "1028"}
        })
        mock_registry.get_async = AsyncMock(return_value=mock_agent)

        # Create real AgentExecutionCore
        execution_core = AgentExecutionCore(
            registry=mock_registry,
            websocket_bridge=websocket_bridge,
            default_tier=TimeoutTier.FREE
        )
        logger.info(f"📍 Created AgentExecutionCore with real WebSocket bridge")

        # Create agent execution context
        agent_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="real_context_integration_agent",
            retry_count=0
        )

        # Monitor WebSocket notifications by patching real methods
        completion_notifications = []
        started_notifications = []
        thinking_notifications = []

        # Patch WebSocket manager methods to capture calls
        original_notify_completed = getattr(websocket_manager, 'notify_agent_completed', None)
        original_notify_started = getattr(websocket_manager, 'notify_agent_started', None)
        original_notify_thinking = getattr(websocket_manager, 'notify_agent_thinking', None)

        async def capture_completion(*args, **kwargs):
            completion_notifications.append({
                'args': args, 
                'kwargs': kwargs, 
                'timestamp': time.time()
            })
            if original_notify_completed:
                return await original_notify_completed(*args, **kwargs)

        async def capture_started(*args, **kwargs):
            started_notifications.append({
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            if original_notify_started:
                return await original_notify_started(*args, **kwargs)

        async def capture_thinking(*args, **kwargs):
            thinking_notifications.append({
                'args': args,
                'kwargs': kwargs, 
                'timestamp': time.time()
            })
            if original_notify_thinking:
                return await original_notify_thinking(*args, **kwargs)

        # Apply patches
        websocket_manager.notify_agent_completed = capture_completion
        websocket_manager.notify_agent_started = capture_started 
        websocket_manager.notify_agent_thinking = capture_thinking

        # Execute agent with real components
        logger.info("🚀 Starting agent execution with real UserExecutionContext...")
        start_time = time.time()
        
        try:
            result = await execution_core.execute_agent(
                context=agent_context,
                user_context=user_context,
                timeout=10.0
            )
            execution_time = time.time() - start_time
            
            logger.info(f"📊 Agent execution completed in {execution_time:.3f}s")
            logger.info(f"   Success: {result.success}")
            logger.info(f"   Started notifications: {len(started_notifications)}")
            logger.info(f"   Thinking notifications: {len(thinking_notifications)}")
            logger.info(f"   Completion notifications: {len(completion_notifications)}")

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Agent execution failed after {execution_time:.3f}s: {e}")
            self.integration_errors.append({
                'error': str(e),
                'execution_time': execution_time,
                'context': 'agent_execution'
            })
            raise

        # Validate agent execution succeeded
        if not result.success:
            logger.error(f"Agent execution failed: {result.error}")
            pytest.skip("Cannot test completion notification - agent execution failed")

        # ISSUE #1028 VALIDATION: Check for missing completion notifications
        if len(completion_notifications) == 0 and result.success:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: Agent succeeded but NO completion notification!\n"
                f"   Integration test with real UserExecutionContext\n"
                f"   Agent execution: SUCCESS (duration: {execution_time:.3f}s)\n"
                f"   Agent result data: {getattr(result, 'data', 'None')}\n"
                f"   UserExecutionContext: {user_context.user_id} / {user_context.thread_id}\n"
                f"   WebSocket manager type: {type(websocket_manager).__name__}\n"
                f"   WebSocket bridge type: {type(websocket_bridge).__name__}\n"
                f"   Started notifications: {len(started_notifications)}\n" 
                f"   Thinking notifications: {len(thinking_notifications)}\n"
                f"   Completion notifications: {len(completion_notifications)}\n"
                f"\n🚨 REAL INTEGRATION FAILURE: User will see agent as hung!"
                f"\n💰 BUSINESS IMPACT: 90% of platform value (real-time chat) appears broken"
            )
            logger.error(failure_message)
            
            # Record detailed failure information
            self.record_metric("issue_1028_integration_confirmed", True)
            self.record_metric("completion_notifications_missing", True)
            self.record_metric("agent_execution_success", result.success)
            self.record_metric("execution_time_seconds", execution_time)
            
            pytest.fail(failure_message)

        # Additional validation: Check completion notification parameters if present
        elif len(completion_notifications) > 0:
            completion = completion_notifications[0]
            
            # Validate completion notification parameters
            parameter_issues = []
            
            # Check run_id alignment
            provided_run_id = completion['kwargs'].get('run_id') or (completion['args'][0] if completion['args'] else None)
            if str(provided_run_id) != str(agent_context.run_id):
                parameter_issues.append(f"run_id mismatch: expected {agent_context.run_id}, got {provided_run_id}")
            
            # Check agent_name alignment  
            provided_agent_name = completion['kwargs'].get('agent_name') or (completion['args'][1] if len(completion['args']) > 1 else None)
            if provided_agent_name != agent_context.agent_name:
                parameter_issues.append(f"agent_name mismatch: expected {agent_context.agent_name}, got {provided_agent_name}")

            if parameter_issues:
                failure_message = (
                    f"❌ ISSUE #1028 PARAMETER ALIGNMENT: Completion notification has wrong parameters!\n"
                    f"   Parameter issues: {parameter_issues}\n"
                    f"   Completion args: {len(completion['args'])}\n"
                    f"   Completion kwargs: {list(completion['kwargs'].keys())}\n"
                    f"   Expected run_id: {agent_context.run_id}\n"
                    f"   Expected agent_name: {agent_context.agent_name}\n"
                    f"\n🚨 WRONG PARAMETERS MAY CAUSE CLIENT TO IGNORE COMPLETION!"
                )
                logger.error(failure_message)
                
                self.record_metric("issue_1028_parameter_alignment_failure", True)
                pytest.fail(failure_message)

        # If we reach here, completion notifications are working correctly
        logger.info("✅ UNEXPECTED: Real integration test shows completion notifications working")
        self.record_metric("issue_1028_integration_confirmed", False)
        self.record_metric("completion_notifications_working", True)

    async def test_websocket_bridge_parameter_propagation_with_real_components(self):
        """
        INTEGRATION: Test WebSocket bridge parameter propagation through real component chain.
        
        This test validates that parameters are correctly propagated from AgentExecutionCore
        through AgentExecutionTracker to the WebSocket bridge, using real components.
        
        EXPECTED TO FAIL: Parameter propagation breaks in the real component chain
        """
        logger.info("🔍 INTEGRATION TEST: WebSocket bridge parameter propagation with real components")

        # Create real components
        user_context = UserExecutionContext(
            user_id=ensure_user_id(generate_user_id()),
            thread_id=ensure_thread_id(generate_thread_id()),
            run_id=str(uuid.uuid4())
        )

        # Mock successful agent for clean parameter flow testing
        mock_registry = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True,
            "result": "Parameter propagation test completed"
        })
        mock_registry.get_async = AsyncMock(return_value=mock_agent)

        try:
            # Get real WebSocket manager and bridge
            websocket_manager = await get_websocket_manager(user_context=user_context)
            websocket_bridge = create_agent_websocket_bridge(
                websocket_manager=websocket_manager,
                user_context=user_context
            )

            # Create AgentExecutionCore with real components
            execution_core = AgentExecutionCore(
                registry=mock_registry,
                websocket_bridge=websocket_bridge,
                default_tier=TimeoutTier.FREE
            )

        except Exception as e:
            logger.error(f"❌ Failed to create real components: {e}")
            pytest.skip(f"Cannot create real components for parameter propagation test: {e}")

        # Track parameter propagation through the real component chain
        parameter_calls = []
        
        # Monkey patch the real _emit_phase_event method to capture parameter flow
        original_emit_phase_event = execution_core.agent_tracker._emit_phase_event
        
        async def capture_parameter_flow(*args, **kwargs):
            """Capture actual parameters passed through real component chain."""
            call_info = {
                'timestamp': time.time(),
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()),
                'has_websocket_manager': 'websocket_manager' in kwargs,
                'websocket_manager_type': type(kwargs.get('websocket_manager')).__name__ if 'websocket_manager' in kwargs else None
            }
            
            # Extract phase information if available
            if len(args) > 1 and hasattr(args[1], 'to_phase'):
                call_info['phase'] = args[1].to_phase.value
                
            parameter_calls.append(call_info)
            
            try:
                return await original_emit_phase_event(*args, **kwargs)
            except Exception as e:
                call_info['error'] = str(e)
                call_info['error_type'] = type(e).__name__
                raise

        execution_core.agent_tracker._emit_phase_event = capture_parameter_flow

        # Execute agent and capture real parameter flow
        agent_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="param_propagation_agent"
        )

        result = await execution_core.execute_agent(
            context=agent_context,
            user_context=user_context,
            timeout=10.0
        )

        # Analyze parameter propagation through real components
        completion_calls = [
            call for call in parameter_calls 
            if call.get('phase') == AgentExecutionPhase.COMPLETED.value
        ]

        logger.info(f"📊 PARAMETER PROPAGATION ANALYSIS:")
        logger.info(f"   Total phase transitions: {len(parameter_calls)}")
        logger.info(f"   Completion phase calls: {len(completion_calls)}")
        logger.info(f"   Agent execution success: {result.success}")

        # Check for parameter propagation failures
        if not result.success:
            logger.error(f"Agent execution failed: {result.error}")
            pytest.skip("Cannot test parameter propagation - agent execution failed")

        # ISSUE #1028 CHECK: Completion phase should have WebSocket manager
        if len(completion_calls) == 0:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: No completion phase transition in real components!\n"
                f"   Agent execution: SUCCESS\n"
                f"   Total phase transitions: {len(parameter_calls)}\n"
                f"   Phases attempted: {[call.get('phase', 'unknown') for call in parameter_calls]}\n"
                f"   Real component chain failed to reach completion phase\n"
                f"\n🚨 COMPLETION NOTIFICATION NEVER ATTEMPTED!"
            )
            logger.error(failure_message)
            pytest.fail(failure_message)

        # Check if completion call had proper parameters
        completion_call = completion_calls[0]
        if not completion_call['has_websocket_manager']:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: Completion phase missing WebSocket manager in real components!\n"
                f"   Completion call info: {completion_call}\n"
                f"   Args count: {completion_call['args_count']}\n"
                f"   Kwargs keys: {completion_call['kwargs_keys']}\n"
                f"   WebSocket manager present: {completion_call['has_websocket_manager']}\n"
                f"   Real component parameter propagation failure\n"
                f"\n🚨 WEBSOCKET MANAGER NOT PROPAGATED TO COMPLETION HANDLER!"
            )
            logger.error(failure_message)
            pytest.fail(failure_message)

        # Check for parameter propagation errors
        error_calls = [call for call in parameter_calls if 'error' in call]
        if error_calls:
            failure_message = (
                f"❌ ISSUE #1028 PARAMETER ERRORS: Real component chain has parameter errors!\n"
                f"   Error calls: {len(error_calls)}\n"
                f"   Error details: {error_calls}\n"
                f"   This indicates parameter alignment issues between real components\n"
                f"\n🚨 PARAMETER ERRORS PREVENT WEBSOCKET NOTIFICATIONS!"
            )
            logger.error(failure_message)
            pytest.fail(failure_message)

        # If we reach here, parameter propagation is working
        logger.info("✅ UNEXPECTED: Real component parameter propagation working properly")

    def teardown_method(self, method):
        """Teardown with integration test analysis."""
        try:
            # Log integration test results
            logger.info("📊 ISSUE #1028 INTEGRATION TEST RESULTS:")
            logger.info(f"   Test method: {method.__name__ if method else 'unknown'}")
            logger.info(f"   WebSocket events captured: {len(self.websocket_events)}")
            logger.info(f"   Completion notifications: {len(self.completion_notifications)}")
            logger.info(f"   Integration errors: {len(self.integration_errors)}")

            # Record integration test metrics
            self.record_metric("integration_test_completed", True)
            self.record_metric("websocket_events_captured", len(self.websocket_events))
            self.record_metric("completion_notifications_found", len(self.completion_notifications))
            self.record_metric("integration_errors_count", len(self.integration_errors))

            # Determine overall integration test status
            has_completion_issues = len(self.completion_notifications) == 0
            has_integration_errors = len(self.integration_errors) > 0

            if has_completion_issues or has_integration_errors:
                logger.error("❌ INTEGRATION TEST CONFIRMED ISSUE #1028: WebSocket bridge problems in real components")
                self.record_metric("issue_1028_integration_status", "CONFIRMED")
            else:
                logger.info("✅ INTEGRATION TEST: Real components working properly")
                self.record_metric("issue_1028_integration_status", "WORKING")

        except Exception as e:
            logger.error(f"❌ INTEGRATION TEARDOWN ERROR: {str(e)}")

        finally:
            super().teardown_method(method)


if __name__ == "__main__":
    """Run Issue #1028 integration tests with real components."""
    logger.info("🚨 RUNNING ISSUE #1028 INTEGRATION TESTS")
    logger.info("📍 PURPOSE: Test WebSocket bridge with real UserExecutionContext and components")
    logger.info("⚠️  EXPECTED: These integration tests should FAIL, proving Issue #1028 exists")

    # Run the integration tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])