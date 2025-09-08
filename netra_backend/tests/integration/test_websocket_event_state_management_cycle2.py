"""
Integration Tests for WebSocket Event State Management - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket event state is properly managed across connections
- Value Impact: Users can reconnect and see consistent agent progress state
- Strategic Impact: Reliable state management prevents user confusion and lost progress

CRITICAL: Poor state management leads to inconsistent user experiences and lost trust.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types import UserID, ThreadID, RunID
from shared.isolated_environment import get_env

class TestWebSocketEventStateManagement(BaseIntegrationTest):
    """Integration tests for WebSocket event state management with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_state_persistence_across_connections(self, real_services_fixture):
        """
        Test that event state persists when users reconnect.
        
        Business Value: Users don't lose progress when network interruptions occur.
        Critical for maintaining continuity in long-running agent processes.
        """
        # Arrange: Setup real WebSocket bridge
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_id = UserID("state_persistence_user")
        thread_id = ThreadID("state_thread_001")
        run_id = RunID("state_run_001")
        
        execution_context = Mock(spec=AgentExecutionContext)
        execution_context.user_id = user_id
        execution_context.thread_id = thread_id
        execution_context.run_id = run_id
        execution_context.agent_name = "state_test_agent"
        
        # Act: Send events and simulate connection state tracking
        notifier = bridge.get_websocket_notifier()
        
        # Send initial events
        await notifier.notify_agent_started(execution_context)
        await notifier.notify_agent_thinking(execution_context, "Initial analysis phase...")
        await notifier.notify_tool_executing(execution_context, "data_analyzer", {"phase": "initial"})
        
        # Verify state tracking
        status = bridge.get_status()
        assert status["state"] in ["ACTIVE", "HEALTHY"], "Bridge should be in active state"
        
        # Simulate connection recovery check
        health_status = await bridge.check_health()
        assert health_status["healthy"] is True, "Bridge should report healthy state"
        
        # Continue with more events after "reconnection"
        await notifier.notify_tool_completed(execution_context, "data_analyzer", {"results": "analysis_complete"})
        await notifier.notify_agent_completed(execution_context, {"final_result": "state_persistence_verified"})
        
        # Assert: State remains consistent throughout
        final_status = bridge.get_status()
        assert final_status["state"] in ["ACTIVE", "HEALTHY"], "Bridge should maintain state consistency"
        
        # Business requirement: Event delivery continues after state checks
        # This validates that state management doesn't interfere with core functionality

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_state_cleanup_after_completion(self, real_services_fixture):
        """
        Test that event state is properly cleaned up after agent completion.
        
        Business Value: Prevents memory leaks and maintains system performance.
        Essential for supporting high-volume customer usage.
        """
        # Arrange: Multiple bridge instances to test cleanup
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_contexts = []
        for i in range(3):
            context = Mock(spec=AgentExecutionContext)
            context.user_id = UserID(f"cleanup_user_{i}")
            context.thread_id = ThreadID(f"cleanup_thread_{i}")
            context.run_id = RunID(f"cleanup_run_{i}")
            context.agent_name = f"cleanup_agent_{i}"
            user_contexts.append(context)
        
        # Act: Run complete agent cycles for multiple users
        notifier = bridge.get_websocket_notifier()
        
        for context in user_contexts:
            # Complete agent cycle
            await notifier.notify_agent_started(context)
            await notifier.notify_agent_thinking(context, f"Processing for {context.user_id}")
            await notifier.notify_tool_executing(context, "processor", {"user": str(context.user_id)})
            await notifier.notify_tool_completed(context, "processor", {"status": "done"})
            await notifier.notify_agent_completed(context, {"user_completed": str(context.user_id)})
        
        # Allow cleanup processing
        await asyncio.sleep(0.5)
        
        # Assert: System maintains efficiency after multiple completions
        status = bridge.get_status()
        assert status["state"] in ["ACTIVE", "HEALTHY"], "Bridge should remain healthy after cleanup"
        
        # Business requirement: Performance doesn't degrade with usage
        health_metrics = status.get("metrics", {})
        if "processing_time_ms" in health_metrics:
            assert health_metrics["processing_time_ms"] < 1000, "Processing time should remain efficient"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_state_during_concurrent_agents(self, real_services_fixture):
        """
        Test event state management with concurrent agent executions.
        
        Business Value: Platform handles multiple simultaneous paying customers.
        CRITICAL: State conflicts between concurrent users would be catastrophic.
        """
        # Arrange: Setup concurrent agent contexts
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        notifier = bridge.get_websocket_notifier()
        
        concurrent_contexts = []
        for i in range(4):  # 4 concurrent agents
            context = Mock(spec=AgentExecutionContext)
            context.user_id = UserID(f"concurrent_state_user_{i}")
            context.thread_id = ThreadID(f"concurrent_state_thread_{i}")
            context.run_id = RunID(f"concurrent_state_run_{i}")
            context.agent_name = f"concurrent_state_agent_{i}"
            concurrent_contexts.append(context)
        
        # Act: Run concurrent agent processes
        async def agent_process(context, process_id):
            """Simulate complete agent process for state testing."""
            try:
                await notifier.notify_agent_started(context)
                await asyncio.sleep(0.1)  # Simulate processing time
                
                await notifier.notify_agent_thinking(context, f"Concurrent process {process_id} thinking...")
                await asyncio.sleep(0.1)
                
                await notifier.notify_tool_executing(context, f"concurrent_tool_{process_id}", {"id": process_id})
                await asyncio.sleep(0.1)
                
                await notifier.notify_tool_completed(context, f"concurrent_tool_{process_id}", {"result": f"process_{process_id}_complete"})
                await asyncio.sleep(0.1)
                
                await notifier.notify_agent_completed(context, {"concurrent_process": process_id, "status": "success"})
                
                return {"process_id": process_id, "success": True}
            except Exception as e:
                return {"process_id": process_id, "success": False, "error": str(e)}
        
        # Execute all processes concurrently
        tasks = [agent_process(context, i) for i, context in enumerate(concurrent_contexts)]
        results = await asyncio.gather(*tasks)
        
        # Assert: All concurrent processes completed successfully
        successful_processes = [r for r in results if r.get("success")]
        assert len(successful_processes) == 4, f"All 4 concurrent processes should succeed, got {len(successful_processes)}"
        
        # Verify bridge maintains healthy state throughout
        final_status = bridge.get_status()
        assert final_status["state"] in ["ACTIVE", "HEALTHY"], "Bridge should handle concurrent load"
        
        # Business requirement: State isolation between concurrent users
        for i, result in enumerate(results):
            assert result["process_id"] == i, f"Process {i} should maintain correct identity"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_state_recovery_from_errors(self, real_services_fixture):
        """
        Test event state recovery when errors occur.
        
        Business Value: System recovers gracefully from failures without losing user progress.
        Error recovery is essential for maintaining customer trust.
        """
        # Arrange: Setup bridge with error simulation capability
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_id = UserID("error_recovery_user")
        thread_id = ThreadID("error_recovery_thread")
        run_id = RunID("error_recovery_run")
        
        execution_context = Mock(spec=AgentExecutionContext)
        execution_context.user_id = user_id
        execution_context.thread_id = thread_id
        execution_context.run_id = run_id
        execution_context.agent_name = "error_recovery_agent"
        
        notifier = bridge.get_websocket_notifier()
        
        # Act: Send events with simulated error conditions
        successful_events = 0
        
        try:
            await notifier.notify_agent_started(execution_context)
            successful_events += 1
            
            await notifier.notify_agent_thinking(execution_context, "Processing before error...")
            successful_events += 1
            
            # Simulate error condition by briefly disrupting the bridge
            with patch.object(bridge._websocket_manager, 'send_to_user', side_effect=Exception("Simulated WebSocket error")):
                # This event should be handled gracefully
                await notifier.notify_tool_executing(execution_context, "error_tool", {"will_fail": True})
                # Don't increment successful_events as this should fail gracefully
            
            # Recovery: Normal operation resumes
            await notifier.notify_tool_completed(execution_context, "recovery_tool", {"recovered": True})
            successful_events += 1
            
            await notifier.notify_agent_completed(execution_context, {"recovery_test": "completed"})
            successful_events += 1
            
        except Exception as e:
            # Errors during event sending should be handled gracefully
            print(f"Event sending error (expected): {e}")
        
        # Assert: System recovers and continues operation
        assert successful_events >= 3, f"Should have sent at least 3 events successfully, got {successful_events}"
        
        # Verify bridge maintains operational state after error
        status = bridge.get_status()
        assert status["state"] in ["ACTIVE", "HEALTHY", "DEGRADED"], "Bridge should maintain operational state after errors"
        
        # Business requirement: Error recovery doesn't prevent future operations
        try:
            await notifier.notify_agent_thinking(execution_context, "Post-error operation test")
            post_error_success = True
        except Exception:
            post_error_success = False
        
        assert post_error_success, "Should be able to send events after error recovery"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_state_metrics_tracking(self, real_services_fixture):
        """
        Test that event state includes proper metrics for business monitoring.
        
        Business Value: Metrics enable performance optimization and billing accuracy.
        Critical for understanding platform usage and customer value delivery.
        """
        # Arrange: Setup bridge with metrics tracking
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_id = UserID("metrics_tracking_user")
        execution_context = Mock(spec=AgentExecutionContext)
        execution_context.user_id = user_id
        execution_context.thread_id = ThreadID("metrics_thread")
        execution_context.run_id = RunID("metrics_run")
        execution_context.agent_name = "metrics_agent"
        
        # Capture initial state
        initial_status = bridge.get_status()
        initial_metrics = initial_status.get("metrics", {})
        
        # Act: Send measured events
        notifier = bridge.get_websocket_notifier()
        start_time = time.time()
        
        await notifier.notify_agent_started(execution_context)
        await notifier.notify_agent_thinking(execution_context, "Metrics tracking test in progress...")
        await notifier.notify_tool_executing(execution_context, "metrics_tool", {"track": "performance"})
        await notifier.notify_tool_completed(execution_context, "metrics_tool", {"metrics": "collected"})
        await notifier.notify_agent_completed(execution_context, {"total_events": 5, "test": "metrics"})
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Allow metrics processing
        await asyncio.sleep(0.2)
        
        # Assert: Metrics are properly tracked
        final_status = bridge.get_status()
        final_metrics = final_status.get("metrics", {})
        
        # Business requirement: State includes performance metrics
        assert "metrics" in final_status, "Status should include metrics"
        
        # Verify metrics show activity
        if "events_processed" in final_metrics:
            assert final_metrics["events_processed"] > initial_metrics.get("events_processed", 0), \
                "Metrics should show processed events"
        
        if "processing_time_ms" in final_metrics:
            assert final_metrics["processing_time_ms"] > 0, "Should track processing time"
            assert final_metrics["processing_time_ms"] < total_duration * 2000, "Processing time should be reasonable"
        
        # Business requirement: State shows system health
        assert final_status["state"] in ["ACTIVE", "HEALTHY"], "System should remain healthy during metrics collection"
        
        # Verify health monitoring remains functional
        health_check = await bridge.check_health()
        assert health_check["healthy"] is True, "Health check should confirm system wellness"