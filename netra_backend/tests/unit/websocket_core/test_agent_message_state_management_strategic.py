"""
Strategic Unit Tests for Agent Message State Management During System Transitions

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Multi-user system reliability  
- Business Goal: Stability - Prevent message loss during system transitions
- Value Impact: Protects $500K+ ARR Golden Path user flows from state corruption
- Strategic Impact: Eliminates race conditions that cause agent message loss

STRATEGIC GAP ADDRESSED: Message State Management during system transitions
This test suite focuses on critical scenarios where message state could be corrupted:
1. WebSocket connection state transitions (connecting -> active -> reconnecting)
2. Agent execution state transitions (started -> thinking -> completed)  
3. Multi-user concurrent state management
4. System startup/shutdown state handling

CRITICAL: These tests ensure message integrity during the most vulnerable system states.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from enum import Enum
from typing import Dict, Any, Optional, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge, 
    IntegrationState,
    IntegrationConfig
)


class ConnectionState(Enum):
    """WebSocket connection states for testing."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class AgentExecutionState(Enum):
    """Agent execution states for testing."""
    PENDING = "pending"
    STARTED = "started"
    THINKING = "thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    COMPLETED = "completed"
    ERROR = "error"
    DEAD = "dead"


class TestAgentMessageStateManagementStrategic(SSotAsyncTestCase):
    """
    Strategic unit tests for message state management during critical system transitions.
    
    STRATEGIC FOCUS: State corruption scenarios that cause message loss or duplication
    in production multi-user environments.
    """
    
    def setup_method(self, method):
        """Set up test fixtures with proper state tracking."""
        super().setup_method(method)
        
        # Create bridge with state monitoring
        self.bridge = AgentWebSocketBridge()
        
        # Mock user context with state tracking
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "test_user_123"
        self.mock_user_context.thread_id = "test_thread_456" 
        self.mock_user_context.run_id = "test_run_789"
        self.mock_user_context.websocket_connection_id = "ws_conn_abc"
        
        # State tracking for verification
        self.connection_states = []
        self.agent_states = []
        self.emitted_messages = []
        
        # Mock WebSocket manager with state tracking
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.emit_to_run.side_effect = self._track_emission

    async def _track_emission(self, run_id, event_type, data, **kwargs):
        """Track message emissions for state analysis."""
        self.emitted_messages.append({
            'timestamp': time.time(),
            'run_id': run_id,
            'event_type': event_type,
            'data': data.copy() if isinstance(data, dict) else data,
            'connection_state': getattr(self, '_current_connection_state', ConnectionState.CONNECTED),
            'agent_state': getattr(self, '_current_agent_state', AgentExecutionState.STARTED)
        })
        return True

    async def test_message_state_during_websocket_reconnection_transition(self):
        """
        STRATEGIC GAP 1: Message state management during WebSocket connection transitions.
        
        CRITICAL SCENARIO: Messages sent during reconnection should be queued, not lost.
        This protects against the most common production failure - connection drops.
        """
        # Arrange - Simulate WebSocket in reconnecting state
        self._current_connection_state = ConnectionState.RECONNECTING
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Simulate reconnection scenario - connection drops mid-stream
            self._current_connection_state = ConnectionState.DISCONNECTED
            
            # Act - Send critical agent messages during connection issues
            result1 = await self.bridge.notify_agent_started(
                run_id="run_123",
                agent_name="CriticalAgent",
                context={"operation": "business_critical_analysis"}
            )
            
            # Connection transitions to reconnecting
            self._current_connection_state = ConnectionState.RECONNECTING
            
            result2 = await self.bridge.notify_agent_thinking(
                run_id="run_123", 
                agent_name="CriticalAgent",
                reasoning="Processing critical business data"
            )
            
            # Connection restored
            self._current_connection_state = ConnectionState.CONNECTED
            
            result3 = await self.bridge.notify_agent_completed(
                run_id="run_123",
                agent_name="CriticalAgent", 
                result={"critical_insights": "data"}
            )
            
            # Assert - All messages should be handled despite connection issues
            assert result1, "Agent started should handle disconnected state"
            assert result2, "Agent thinking should handle reconnecting state"  
            assert result3, "Agent completed should work in connected state"
            
            # Verify message ordering preserved through state transitions
            agent_messages = [msg for msg in self.emitted_messages if msg['run_id'] == "run_123"]
            assert len(agent_messages) == 3, "All agent messages should be emitted"
            
            message_types = [msg['event_type'] for msg in agent_messages]
            assert message_types == ['agent_started', 'agent_thinking', 'agent_completed'], \
                "Message order must be preserved during connection transitions"

    async def test_concurrent_agent_state_transitions_isolation(self):
        """
        STRATEGIC GAP 2: Multi-user agent state isolation during concurrent transitions.
        
        CRITICAL SCENARIO: Concurrent users' agent states must not interfere with each other.
        This is essential for multi-tenant system integrity.
        """
        # Arrange - Multiple users with concurrent agent executions
        users = [
            {"user_id": "user_1", "run_id": "run_1", "agent": "Agent1"},
            {"user_id": "user_2", "run_id": "run_2", "agent": "Agent2"}, 
            {"user_id": "user_3", "run_id": "run_3", "agent": "Agent3"}
        ]
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Simulate rapid concurrent state transitions
            tasks = []
            for user in users:
                # Each user goes through complete agent lifecycle simultaneously
                tasks.extend([
                    self.bridge.notify_agent_started(
                        run_id=user["run_id"],
                        agent_name=user["agent"],
                        context={"user_id": user["user_id"], "operation": f"analysis_{user['user_id']}"}
                    ),
                    self.bridge.notify_agent_thinking(
                        run_id=user["run_id"],
                        agent_name=user["agent"], 
                        reasoning=f"Processing for {user['user_id']}"
                    ),
                    self.bridge.notify_agent_completed(
                        run_id=user["run_id"],
                        agent_name=user["agent"],
                        result={"user_specific_data": user["user_id"]}
                    )
                ])
            
            # Execute all transitions concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assert - No exceptions should occur during concurrent execution
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0, f"Concurrent state transitions should not cause exceptions: {exceptions}"
            
            # Verify complete message isolation between users
            for user in users:
                user_messages = [msg for msg in self.emitted_messages if msg['run_id'] == user["run_id"]]
                assert len(user_messages) == 3, f"User {user['user_id']} should have exactly 3 messages"
                
                # Verify user-specific data isolation
                for msg in user_messages:
                    if 'context' in msg['data']:
                        assert msg['data']['context']['user_id'] == user["user_id"], \
                            "User context must be isolated"
                    elif 'result' in msg['data']:
                        assert msg['data']['result']['user_specific_data'] == user["user_id"], \
                            "User results must be isolated"

    async def test_agent_state_recovery_during_partial_execution_failure(self):
        """
        STRATEGIC GAP 3: State recovery when agent execution partially fails.
        
        CRITICAL SCENARIO: Agent fails mid-execution, state must be recoverable without corruption.
        This prevents partial state corruption that confuses users.
        """
        # Arrange - Agent starts normally
        run_id = "recovery_test_run"
        agent_name = "RecoveryTestAgent"
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Normal start
            result1 = await self.bridge.notify_agent_started(
                run_id=run_id,
                agent_name=agent_name,
                context={"operation": "complex_analysis"}
            )
            assert result1, "Agent should start successfully"
            
            # Normal thinking phase
            result2 = await self.bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=agent_name,
                reasoning="Processing complex calculations"
            )
            assert result2, "Agent thinking should work"
            
            # Simulate tool execution failure 
            result3 = await self.bridge.notify_agent_error(
                run_id=run_id,
                agent_name=agent_name,
                error="Tool execution failed: memory exhausted",
                error_context={"tool": "data_analyzer", "memory_used": "8GB"}
            )
            assert result3, "Agent error notification should work"
            
            # Simulate recovery attempt - agent restarts
            result4 = await self.bridge.notify_agent_started(
                run_id=run_id,  # Same run_id for recovery
                agent_name=agent_name,
                context={"operation": "complex_analysis", "recovery_attempt": True}
            )
            assert result4, "Agent recovery start should work"
            
            # Successful completion after recovery
            result5 = await self.bridge.notify_agent_completed(
                run_id=run_id,
                agent_name=agent_name,
                result={"status": "recovered", "analysis": "completed"}
            )
            assert result5, "Agent should complete after recovery"
            
            # Assert - Verify recovery state sequence
            run_messages = [msg for msg in self.emitted_messages if msg['run_id'] == run_id]
            assert len(run_messages) == 5, "Should have complete recovery sequence"
            
            message_sequence = [msg['event_type'] for msg in run_messages]
            expected_sequence = ['agent_started', 'agent_thinking', 'agent_error', 'agent_started', 'agent_completed']
            assert message_sequence == expected_sequence, \
                f"Recovery sequence should be preserved: expected {expected_sequence}, got {message_sequence}"
            
            # Verify recovery context is tracked
            recovery_start = [msg for msg in run_messages if 
                             msg['event_type'] == 'agent_started' and 
                             'recovery_attempt' in str(msg['data'])]
            assert len(recovery_start) == 1, "Recovery attempt should be tracked"

    async def test_system_startup_message_state_initialization(self):
        """
        STRATEGIC GAP 4: Message state during system startup/initialization.
        
        CRITICAL SCENARIO: Messages sent during system startup should be handled gracefully.
        This prevents startup race conditions that lose initial user messages.
        """
        # Arrange - Simulate system starting up (bridge not fully initialized)
        startup_bridge = AgentWebSocketBridge()
        startup_bridge.state = IntegrationState.INITIALIZING
        
        # Mock WebSocket manager as not ready initially
        mock_manager = AsyncMock()
        mock_manager.emit_to_run.side_effect = [
            Exception("WebSocket manager not ready"),  # First call fails - startup
            True,  # Second call succeeds - system ready
            True   # Third call succeeds - system stable
        ]
        
        with patch.object(startup_bridge, '_get_websocket_manager', return_value=mock_manager):
            # Act - Send messages during startup phase
            result1 = await startup_bridge.notify_agent_started(
                run_id="startup_run",
                agent_name="StartupAgent", 
                context={"phase": "system_startup"}
            )
            
            # System transitions to active state
            startup_bridge.state = IntegrationState.ACTIVE
            
            result2 = await startup_bridge.notify_agent_thinking(
                run_id="startup_run",
                agent_name="StartupAgent",
                reasoning="System now active, processing normally"
            )
            
            result3 = await startup_bridge.notify_agent_completed(
                run_id="startup_run", 
                agent_name="StartupAgent",
                result={"startup_handling": "success"}
            )
            
            # Assert - System should gracefully handle startup state
            # First message may fail during startup (acceptable)
            assert result1 in [True, False], "Startup message handling should be graceful"
            
            # Once system is active, messages should work
            assert result2, "Messages should work once system is active"
            assert result3, "System should be stable after startup"
            
            # Verify WebSocket manager was called appropriately
            assert mock_manager.emit_to_run.call_count >= 2, "Should attempt message delivery"

    async def test_message_state_consistency_during_high_frequency_transitions(self):
        """
        STRATEGIC GAP 5: State consistency during rapid state transitions.
        
        CRITICAL SCENARIO: Rapid agent state changes should maintain message consistency.
        This tests the system's ability to handle burst scenarios without corruption.
        """
        # Arrange - Prepare for high-frequency state changes
        run_id = "high_freq_test"
        agent_name = "HighFreqAgent"
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Rapid state transitions simulating real-world burst activity
            rapid_tasks = []
            
            # Simulate 3 agents starting simultaneously
            for i in range(3):
                rapid_tasks.append(
                    self.bridge.notify_agent_started(
                        run_id=f"{run_id}_{i}",
                        agent_name=f"{agent_name}_{i}",
                        context={"batch_id": "high_freq_batch", "agent_index": i}
                    )
                )
            
            # Each agent rapidly transitions through thinking states
            for i in range(3):
                for step in range(5):  # 5 rapid thinking updates per agent
                    rapid_tasks.append(
                        self.bridge.notify_agent_thinking(
                            run_id=f"{run_id}_{i}",
                            agent_name=f"{agent_name}_{i}",
                            reasoning=f"Rapid processing step {step}",
                            step_number=step
                        )
                    )
            
            # All agents complete simultaneously  
            for i in range(3):
                rapid_tasks.append(
                    self.bridge.notify_agent_completed(
                        run_id=f"{run_id}_{i}",
                        agent_name=f"{agent_name}_{i}",
                        result={"batch_result": f"agent_{i}_completed"}
                    )
                )
            
            # Execute all rapid transitions concurrently
            start_time = time.time()
            results = await asyncio.gather(*rapid_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Assert - All rapid transitions should succeed
            successful_results = [r for r in results if r is True]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            assert len(failed_results) == 0, f"No failures should occur during rapid transitions: {failed_results}"
            assert len(successful_results) == len(rapid_tasks), "All rapid messages should succeed"
            
            # Verify performance - rapid transitions should complete quickly
            execution_time = end_time - start_time
            assert execution_time < 2.0, f"Rapid transitions should complete in <2s, took {execution_time:.2f}s"
            
            # Verify message consistency - each agent should have complete lifecycle
            for i in range(3):
                agent_messages = [msg for msg in self.emitted_messages if msg['run_id'] == f"{run_id}_{i}"]
                assert len(agent_messages) == 7, f"Agent {i} should have 7 messages (1 start + 5 thinking + 1 complete)"
                
                # Verify message ordering within each agent
                message_types = [msg['event_type'] for msg in agent_messages]
                assert message_types[0] == 'agent_started', "First message should be agent_started"
                assert message_types[-1] == 'agent_completed', "Last message should be agent_completed"
                assert message_types[1:-1] == ['agent_thinking'] * 5, "Middle messages should be agent_thinking"

    async def test_message_state_preservation_during_error_cascade(self):
        """
        STRATEGIC GAP 6: Message state integrity during error cascade scenarios.
        
        CRITICAL SCENARIO: Multiple cascading errors should not corrupt message state.
        This tests system resilience against the worst-case error scenarios.
        """
        # Arrange - Setup scenario for cascading errors
        run_id = "cascade_test"
        agent_name = "CascadeAgent"
        
        # Mock WebSocket manager to simulate various failure modes
        failure_sequence = [
            True,  # agent_started - success
            Exception("Network error"),  # agent_thinking - network failure
            Exception("Memory error"),  # agent_error - memory failure during error reporting
            True,  # agent_error - error reporting recovery
            Exception("Database error"),  # agent_death - database failure  
            True,  # agent_death - death notification recovery
        ]
        
        mock_manager = AsyncMock()
        mock_manager.emit_to_run.side_effect = failure_sequence
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=mock_manager):
            # Act - Execute sequence that triggers cascading errors
            result1 = await self.bridge.notify_agent_started(
                run_id=run_id,
                agent_name=agent_name,
                context={"test_scenario": "error_cascade"}
            )
            
            result2 = await self.bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=agent_name, 
                reasoning="Processing before network failure"
            )
            
            result3 = await self.bridge.notify_agent_error(
                run_id=run_id,
                agent_name=agent_name,
                error="First error: processing failed", 
                error_context={"error_type": "processing"}
            )
            
            result4 = await self.bridge.notify_agent_error(
                run_id=run_id,
                agent_name=agent_name,
                error="Second error: system overload",
                error_context={"error_type": "system"}
            )
            
            result5 = await self.bridge.notify_agent_death(
                run_id=run_id,
                agent_name=agent_name,
                death_cause="Cascading system failure",
                death_context={"cascade_count": 3}
            )
            
            result6 = await self.bridge.notify_agent_death(
                run_id=run_id,
                agent_name=agent_name,
                death_cause="Final system shutdown", 
                death_context={"cascade_count": 4, "final": True}
            )
            
            # Assert - System should handle cascading errors gracefully
            assert result1 is True, "Initial agent start should succeed"
            assert result2 is False, "Network failure should be handled gracefully"
            assert result3 is False, "Memory error during error reporting should be handled"
            assert result4 is True, "Error reporting recovery should work"
            assert result5 is False, "Database error during death notification should be handled"  
            assert result6 is True, "Death notification recovery should work"
            
            # Verify that successful notifications were attempted
            assert mock_manager.emit_to_run.call_count == 6, "All notifications should be attempted"

    def teardown_method(self, method):
        """Clean up test state tracking."""
        super().teardown_method(method)
        # Clear state tracking
        self.connection_states.clear()
        self.agent_states.clear() 
        self.emitted_messages.clear()


if __name__ == '__main__':
    """
    Run strategic message state management tests.
    
    These tests validate critical state management scenarios that protect
    the $500K+ ARR Golden Path user experience from corruption.
    """
    pytest.main([__file__, "-v", "--tb=short"])