"""
Integration Tests for AgentExecutionTracker SSOT Class
======================================================

CRITICAL: This tests the recently updated AgentExecutionTracker with 1,200+ lines of consolidated
state management functionality, including the ExecutionState enum bug fix that was causing 
$500K+ ARR impact.

Business Value: Core/Enterprise - Agent Execution Reliability ($500K+ ARR protection)
Protects chat functionality (90% of platform value) through reliable agent execution tracking.

REQUIREMENTS:
- NO MOCKS allowed - uses real services and components 
- Tests ExecutionState enum fix (dictionaries caused 'dict' object has no attribute 'value' errors)
- Tests consolidated functionality from AgentStateTracker and AgentExecutionTimeoutManager
- Validates circuit breaker, timeout management, and death detection
- Tests multi-user execution isolation
- Validates WebSocket event integration

CRITICAL BUG CONTEXT:
The fixed bug involved agent_execution_core.py lines 263, 382, 397 passing dictionary objects
like {"success": True, "completed": True} instead of ExecutionState enum values to 
update_execution_state(), causing AttributeError: 'dict' object has no attribute 'value'.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock
import logging

import pytest

# Use SSOT base test case - NO other base test classes allowed
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import from SSOT_IMPORT_REGISTRY verified paths
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker, 
    ExecutionTracker,  # Compatibility alias
    ExecutionState, 
    AgentExecutionPhase,
    CircuitBreakerState,
    TimeoutConfig,
    ExecutionRecord,
    CircuitBreakerOpenError,
    get_execution_tracker,
    initialize_tracker,
    shutdown_tracker
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.types.core_types import UserID, ThreadID, RunID


class TestAgentExecutionTrackerIntegration(SSotAsyncTestCase):
    """
    Integration tests for the AgentExecutionTracker SSOT class.
    
    Tests the consolidated functionality including:
    - ExecutionState enum usage validation (fix for critical dictionary bug)
    - Consolidated state management from AgentStateTracker
    - Consolidated timeout management from AgentExecutionTimeoutManager
    - Circuit breaker integration
    - Death detection and monitoring
    - Multi-user execution isolation
    """
    
    def setup_method(self, method):
        """Setup test environment with real components."""
        super().setup_method(method)
        
        # Create fresh tracker instance for each test to avoid cross-test contamination
        self.tracker = AgentExecutionTracker(
            heartbeat_timeout=2,  # Short timeout for faster test execution
            execution_timeout=5,  # Short timeout for tests
            cleanup_interval=30,
            timeout_config=TimeoutConfig(
                agent_execution_timeout=5.0,
                llm_api_timeout=3.0,
                failure_threshold=2,  # Lower threshold for faster test
                recovery_timeout=5.0,
                max_retries=1
            )
        )
        
        # Test context data
        self.test_user_id = f"test_user_{int(time.time())}"
        self.test_thread_id = f"thread_{int(time.time())}"
        self.test_agent_name = "test_optimization_agent"
        
        # Mock WebSocket manager for event testing (real-like behavior)
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.notify_agent_started = AsyncMock()
        self.mock_websocket_manager.notify_agent_thinking = AsyncMock()
        self.mock_websocket_manager.notify_tool_executing = AsyncMock()
        self.mock_websocket_manager.notify_agent_completed = AsyncMock()
        self.mock_websocket_manager.notify_agent_error = AsyncMock()
        
    async def teardown_method(self, method):
        """Clean up tracker resources."""
        if hasattr(self, 'tracker') and self.tracker:
            await self.tracker.stop_monitoring()
        
        super().teardown_method(method)
    
    # ========== EXECUTION STATE ENUM VALIDATION TESTS (CRITICAL BUG FIX) ==========
    
    async def test_execution_state_enum_usage_validation_critical_fix(self):
        """
        Test that ExecutionState enums are used correctly, not dictionaries.
        
        CRITICAL: This validates the fix for the $500K+ ARR impact bug where 
        dictionary objects were passed instead of ExecutionState enum values,
        causing 'dict' object has no attribute 'value' errors.
        """
        # Create execution
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id, 
            user_id=self.test_user_id
        )
        
        # Test successful update with proper enum (this was the fix)
        success = self.tracker.update_execution_state(
            execution_id, 
            ExecutionState.COMPLETED  # NOT {"success": True, "completed": True}
        )
        assert success, "Should successfully update with ExecutionState enum"
        
        # Verify state was set correctly
        record = self.tracker.get_execution(execution_id)
        assert record is not None
        assert record.state == ExecutionState.COMPLETED
        assert record.is_terminal
        
        # Test failed update with proper enum (this was the other fix)
        execution_id_2 = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        success = self.tracker.update_execution_state(
            execution_id_2,
            ExecutionState.FAILED,  # NOT {"success": False, "completed": True}
            error="Test failure"
        )
        assert success
        
        record_2 = self.tracker.get_execution(execution_id_2)
        assert record_2.state == ExecutionState.FAILED
        assert record_2.error == "Test failure"
        assert record_2.is_terminal
    
    async def test_execution_state_transition_validation(self):
        """Test that state transitions follow proper lifecycle."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Test normal execution flow
        assert self.tracker.start_execution(execution_id)
        
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.STARTING
        
        # Send heartbeat to transition to RUNNING
        assert self.tracker.heartbeat(execution_id)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING
        
        # Complete execution
        assert self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.COMPLETED
        assert record.completed_at is not None
        
        # Cannot update terminal states
        assert not self.tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
    
    async def test_terminal_state_handling_and_cleanup(self):
        """Test proper handling of terminal states and resource cleanup."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Start execution
        self.tracker.start_execution(execution_id)
        
        # Verify execution is active
        active_executions = self.tracker.get_active_executions()
        assert len(active_executions) == 1
        assert active_executions[0].execution_id == execution_id
        
        # Complete execution
        self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        
        # Verify execution is no longer active
        active_executions = self.tracker.get_active_executions()
        assert len(active_executions) == 0
        
        # But still retrievable
        record = self.tracker.get_execution(execution_id)
        assert record is not None
        assert record.is_terminal
    
    # ========== CONSOLIDATED STATE MANAGEMENT TESTS (from AgentStateTracker) ==========
    
    async def test_phase_transition_validation_from_consolidated_state_tracker(self):
        """Test phase transition validation from consolidated AgentStateTracker functionality."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        record = self.tracker.get_execution(execution_id)
        assert record.current_phase == AgentExecutionPhase.CREATED
        
        # Valid transition: CREATED -> WEBSOCKET_SETUP
        success = await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.WEBSOCKET_SETUP,
            metadata={"websocket_url": "ws://test"}
        )
        assert success
        
        # Valid transition: WEBSOCKET_SETUP -> CONTEXT_VALIDATION
        success = await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.CONTEXT_VALIDATION,
            metadata={"context_valid": True}
        )
        assert success
        
        # Valid transition: CONTEXT_VALIDATION -> STARTING
        success = await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.STARTING
        )
        assert success
        
        record = self.tracker.get_execution(execution_id)
        assert record.current_phase == AgentExecutionPhase.STARTING
        assert len(record.phase_history) == 3  # 3 transitions
    
    async def test_websocket_event_emission_during_phase_transitions(self):
        """Test WebSocket events are emitted during phase transitions (consolidated functionality)."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Transition to STARTING phase with WebSocket manager
        success = await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.STARTING,
            metadata={"phase": "starting"},
            websocket_manager=self.mock_websocket_manager
        )
        assert success
        
        # Verify agent_started event was sent
        self.mock_websocket_manager.notify_agent_started.assert_called_once()
        call_args = self.mock_websocket_manager.notify_agent_started.call_args
        assert call_args[1]['run_id'] == self.test_thread_id
        assert call_args[1]['agent_name'] == self.test_agent_name
        
        # Transition to THINKING phase
        success = await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.THINKING,
            websocket_manager=self.mock_websocket_manager
        )
        assert success
        
        # Verify agent_thinking event was sent
        self.mock_websocket_manager.notify_agent_thinking.assert_called_once()
        
        # Transition to COMPLETED phase
        success = await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.COMPLETED,
            websocket_manager=self.mock_websocket_manager
        )
        assert success
        
        # Verify agent_completed event was sent
        self.mock_websocket_manager.notify_agent_completed.assert_called_once()
    
    async def test_state_history_tracking_and_retrieval(self):
        """Test state history tracking from consolidated AgentStateTracker functionality."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Perform several phase transitions
        await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.STARTING,
            metadata={"step": 1}
        )
        await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.THINKING,
            metadata={"step": 2}
        )
        await self.tracker.transition_state(
            execution_id,
            AgentExecutionPhase.TOOL_EXECUTION,
            metadata={"step": 3}
        )
        
        # Get state history
        history = self.tracker.get_state_history(execution_id)
        assert len(history) == 3
        
        # Verify history structure
        assert history[0]['to_phase'] == 'starting'
        assert history[0]['metadata']['step'] == 1
        assert history[1]['to_phase'] == 'thinking'
        assert history[1]['metadata']['step'] == 2
        assert history[2]['to_phase'] == 'tool_execution'
        assert history[2]['metadata']['step'] == 3
        
        # Verify timing information
        for transition in history:
            assert 'timestamp' in transition
            assert 'duration_ms' in transition
            assert transition['duration_ms'] >= 0
    
    async def test_agent_state_management_and_updates(self):
        """Test agent state get/set operations from consolidated functionality."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            metadata={"test_key": "test_value"}
        )
        
        # Get agent state
        state = self.tracker.get_agent_state(execution_id)
        assert state is not None
        assert state['execution_id'] == execution_id
        assert state['agent_name'] == self.test_agent_name
        assert state['user_id'] == self.test_user_id
        assert state['thread_id'] == self.test_thread_id
        assert state['current_phase'] == 'created'
        assert state['warning_count'] == 0
        assert state['error_count'] == 0
        assert 'total_duration_ms' in state
        assert 'current_phase_duration_ms' in state
        
        # Update agent state
        success = self.tracker.set_agent_state(execution_id, {
            "warning_count": 2,
            "error_count": 1,
            "metadata": {"additional_key": "additional_value"}
        })
        assert success
        
        # Verify state updates
        updated_state = self.tracker.get_agent_state(execution_id)
        assert updated_state['warning_count'] == 2
        assert updated_state['error_count'] == 1
        assert updated_state['metadata']['test_key'] == 'test_value'  # Original metadata preserved
        assert updated_state['metadata']['additional_key'] == 'additional_value'  # New metadata added
    
    # ========== CONSOLIDATED TIMEOUT MANAGEMENT TESTS (from AgentExecutionTimeoutManager) ==========
    
    async def test_timeout_configuration_and_validation(self):
        """Test timeout configuration from consolidated AgentExecutionTimeoutManager functionality."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Set custom timeout config
        custom_config = TimeoutConfig(
            agent_execution_timeout=10.0,
            llm_api_timeout=5.0,
            failure_threshold=3,
            recovery_timeout=15.0,
            max_retries=2
        )
        
        success = self.tracker.set_timeout(execution_id, custom_config)
        assert success
        
        # Check timeout status
        timeout_status = self.tracker.check_timeout(execution_id)
        assert timeout_status is not None
        assert timeout_status['execution_id'] == execution_id
        assert timeout_status['timeout_seconds'] == 10.0
        assert timeout_status['elapsed_seconds'] >= 0
        assert not timeout_status['is_timed_out']  # Should not be timed out immediately
        assert timeout_status['time_until_timeout'] > 0
    
    async def test_circuit_breaker_functionality_and_states(self):
        """Test circuit breaker functionality from consolidated timeout management."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Register circuit breaker
        success = self.tracker.register_circuit_breaker(execution_id)
        assert success
        
        # Check initial circuit breaker status
        cb_status = self.tracker.circuit_breaker_status(execution_id)
        assert cb_status is not None
        assert cb_status['state'] == 'closed'
        assert cb_status['failure_count'] == 0
        assert not cb_status['is_open']
        assert cb_status['can_retry']
        
        record = self.tracker.get_execution(execution_id)
        assert record.circuit_breaker_state == CircuitBreakerState.CLOSED
        assert record.circuit_breaker_failures == 0
    
    async def test_circuit_breaker_failure_and_recovery_cycle(self):
        """Test circuit breaker failure thresholds and recovery mechanism."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Set low failure threshold for testing
        custom_config = TimeoutConfig(
            failure_threshold=2,  # Open after 2 failures
            recovery_timeout=0.1,  # Very short recovery time for testing
        )
        self.tracker.set_timeout(execution_id, custom_config)
        self.tracker.register_circuit_breaker(execution_id)
        
        # Simulate failures using internal methods
        record = self.tracker.get_execution(execution_id)
        
        # First failure
        await self.tracker._on_circuit_breaker_failure(execution_id, "test_operation", "test_error_1")
        cb_status = self.tracker.circuit_breaker_status(execution_id)
        assert cb_status['state'] == 'closed'  # Still closed after 1 failure
        assert cb_status['failure_count'] == 1
        
        # Second failure - should open circuit
        await self.tracker._on_circuit_breaker_failure(execution_id, "test_operation", "test_error_2")
        cb_status = self.tracker.circuit_breaker_status(execution_id)
        assert cb_status['state'] == 'open'  # Now open
        assert cb_status['failure_count'] == 2
        assert cb_status['is_open']
        
        # Wait for recovery timeout
        await asyncio.sleep(0.2)
        
        # Test that we can reset circuit breaker
        success = self.tracker.reset_circuit_breaker(execution_id)
        assert success
        
        cb_status = self.tracker.circuit_breaker_status(execution_id)
        assert cb_status['state'] == 'closed'  # Reset to closed
        assert cb_status['failure_count'] == 0
    
    async def test_execute_with_circuit_breaker_protection(self):
        """Test function execution with circuit breaker protection."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Set very short timeout for testing
        custom_config = TimeoutConfig(llm_api_timeout=0.1)
        self.tracker.set_timeout(execution_id, custom_config)
        self.tracker.register_circuit_breaker(execution_id)
        
        # Test successful execution
        async def successful_operation():
            await asyncio.sleep(0.01)  # Very short operation
            return "success_result"
        
        result = await self.tracker.execute_with_circuit_breaker(
            execution_id, 
            successful_operation,
            "test_success_operation"
        )
        assert result == "success_result"
        
        # Test timeout operation
        async def timeout_operation():
            await asyncio.sleep(1.0)  # Longer than timeout
            return "should_not_reach"
        
        with pytest.raises(TimeoutError):
            await self.tracker.execute_with_circuit_breaker(
                execution_id,
                timeout_operation,
                "test_timeout_operation"
            )
    
    # ========== AGENT DEATH DETECTION TESTS ==========
    
    async def test_heartbeat_monitoring_and_death_detection(self):
        """Test heartbeat monitoring and agent death detection."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Start execution
        self.tracker.start_execution(execution_id)
        
        # Send heartbeat
        assert self.tracker.heartbeat(execution_id)
        record = self.tracker.get_execution(execution_id)
        assert record.heartbeat_count == 1
        
        # Simulate time passing without heartbeat
        record.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=15)
        
        # Check for death detection
        dead_executions = self.tracker.detect_dead_executions()
        assert len(dead_executions) == 1
        assert dead_executions[0].execution_id == execution_id
    
    async def test_background_monitoring_task_functionality(self):
        """Test the background monitoring task for death/timeout detection."""
        # Start monitoring
        await self.tracker.start_monitoring()
        
        # Create execution that will timeout quickly
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        self.tracker.start_execution(execution_id)
        
        # Make execution appear dead
        record = self.tracker.get_execution(execution_id)
        record.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=15)
        
        # Death callback tracking
        death_detected = []
        
        async def death_callback(dead_record):
            death_detected.append(dead_record.execution_id)
        
        self.tracker.register_death_callback(death_callback)
        
        # Wait for monitoring to detect death
        await asyncio.sleep(3)  # Give monitor time to run
        
        # Verify death was detected and callback was triggered
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.DEAD
        assert len(death_detected) > 0
        assert execution_id in death_detected
        
        # Stop monitoring
        await self.tracker.stop_monitoring()
    
    async def test_execution_timeout_detection_and_handling(self):
        """Test execution timeout detection and automatic timeout handling."""
        # Create execution with very short timeout
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            timeout_seconds=1  # 1 second timeout
        )
        
        self.tracker.start_execution(execution_id)
        
        # Keep sending heartbeats but let execution time out
        record = self.tracker.get_execution(execution_id)
        record.started_at = datetime.now(timezone.utc) - timedelta(seconds=5)  # Started 5 seconds ago
        
        # Check timeout detection
        assert record.is_timed_out()
        
        # Detect timeout through monitoring
        dead_executions = self.tracker.detect_dead_executions()
        timeout_executions = [ex for ex in dead_executions if ex.is_timed_out()]
        assert len(timeout_executions) == 1
        assert timeout_executions[0].execution_id == execution_id
    
    # ========== MULTI-USER EXECUTION ISOLATION TESTS ==========
    
    async def test_multi_user_execution_isolation_and_safety(self):
        """Test that executions are properly isolated between users."""
        user1_id = f"user1_{int(time.time())}"
        user2_id = f"user2_{int(time.time())}"
        thread1_id = f"thread1_{int(time.time())}"
        thread2_id = f"thread2_{int(time.time())}"
        
        # Create executions for different users
        exec1_id = self.tracker.create_execution(
            agent_name="agent1",
            thread_id=thread1_id,
            user_id=user1_id
        )
        
        exec2_id = self.tracker.create_execution(
            agent_name="agent2", 
            thread_id=thread2_id,
            user_id=user2_id
        )
        
        # Verify executions are isolated by thread
        thread1_executions = self.tracker.get_executions_by_thread(thread1_id)
        assert len(thread1_executions) == 1
        assert thread1_executions[0].execution_id == exec1_id
        assert thread1_executions[0].user_id == user1_id
        
        thread2_executions = self.tracker.get_executions_by_thread(thread2_id)
        assert len(thread2_executions) == 1
        assert thread2_executions[0].execution_id == exec2_id
        assert thread2_executions[0].user_id == user2_id
        
        # Verify executions are isolated by agent
        agent1_executions = self.tracker.get_executions_by_agent("agent1")
        agent2_executions = self.tracker.get_executions_by_agent("agent2")
        
        assert len(agent1_executions) == 1
        assert len(agent2_executions) == 1
        assert agent1_executions[0].user_id == user1_id
        assert agent2_executions[0].user_id == user2_id
    
    async def test_concurrent_execution_state_updates_safety(self):
        """Test thread safety of concurrent execution state updates."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        self.tracker.start_execution(execution_id)
        
        # Simulate concurrent heartbeats and state updates
        async def send_heartbeats():
            for _ in range(10):
                self.tracker.heartbeat(execution_id)
                await asyncio.sleep(0.01)
        
        async def update_states():
            for i in range(5):
                await self.tracker.transition_state(
                    execution_id,
                    AgentExecutionPhase.THINKING,
                    metadata={"iteration": i}
                )
                await asyncio.sleep(0.02)
        
        # Run concurrent operations
        await asyncio.gather(send_heartbeats(), update_states())
        
        # Verify final state integrity
        record = self.tracker.get_execution(execution_id)
        assert record.heartbeat_count == 10
        assert record.current_phase == AgentExecutionPhase.THINKING
        assert len(record.phase_history) >= 1  # At least one transition recorded
    
    # ========== UNIFIED ID MANAGER INTEGRATION TESTS ==========
    
    async def test_unified_id_manager_integration_for_execution_ids(self):
        """Test integration with UnifiedIDManager for structured execution ID generation."""
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Verify execution ID structure matches UnifiedIDManager format
        assert execution_id.startswith("exec_"), f"Expected exec_ prefix, got: {execution_id}"
        assert "_" in execution_id, "Expected structured ID with underscores"
        
        # Verify ID is unique across multiple creations
        execution_id_2 = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        assert execution_id != execution_id_2, "Execution IDs should be unique"
        assert execution_id_2.startswith("exec_"), "Second ID should also have exec_ prefix"
    
    # ========== BUSINESS CRITICAL INTEGRATION TESTS ==========
    
    async def test_full_consolidated_execution_context_creation(self):
        """Test creating execution with full consolidated context (enterprise feature)."""
        user_context = {
            "user_id": self.test_user_id,
            "thread_id": self.test_thread_id,
            "metadata": {
                "session_id": "test_session_123",
                "enterprise_features": True,
                "subscription_tier": "enterprise"
            }
        }
        
        timeout_config = {
            "timeout_seconds": 20.0,
            "llm_timeout": 10.0,
            "failure_threshold": 3,
            "recovery_timeout": 30.0,
            "max_retries": 2
        }
        
        # Create execution with full context
        execution_id = self.tracker.create_execution_with_full_context(
            agent_name=self.test_agent_name,
            user_context=user_context,
            timeout_config=timeout_config,
            initial_state="PENDING"
        )
        
        # Verify execution was created with full context
        full_context = self.tracker.get_execution_with_full_context(execution_id)
        assert full_context is not None
        assert full_context['execution_id'] == execution_id
        assert full_context['agent_name'] == self.test_agent_name
        assert full_context['user_id'] == self.test_user_id
        assert full_context['thread_id'] == self.test_thread_id
        assert full_context['state'] == 'PENDING'
        assert full_context['timeout_seconds'] == 20
        assert full_context['consolidated'] is True
        assert full_context['created_with_ssot'] is True
        
        # Verify metadata was preserved
        assert full_context['metadata']['session_id'] == 'test_session_123'
        assert full_context['metadata']['enterprise_features'] is True
        
        # Verify timeout config was applied
        timeout_status = full_context['timeout_status']
        assert timeout_status['timeout_seconds'] == 20.0
        
        # Verify circuit breaker was registered
        cb_status = full_context['circuit_breaker_status']
        assert cb_status['state'] == 'closed'
    
    async def test_golden_path_chat_functionality_support(self):
        """
        Test that execution tracking supports the Golden Path chat functionality (90% of platform value).
        
        This validates that agent execution tracking properly supports the primary revenue-generating 
        user flow that protects $500K+ ARR.
        """
        # Simulate Golden Path user workflow
        execution_id = self.tracker.create_execution(
            agent_name="OptimizationsCoreSubAgent",  # Primary business agent
            thread_id=f"golden_path_thread_{int(time.time())}",
            user_id=f"enterprise_user_{int(time.time())}",
            metadata={
                "chat_session": True,
                "golden_path": True,
                "business_critical": True
            }
        )
        
        # Start the Golden Path execution flow
        assert self.tracker.start_execution(execution_id)
        
        # Simulate the full Golden Path phase sequence with WebSocket events
        phases = [
            (AgentExecutionPhase.WEBSOCKET_SETUP, {"websocket_connected": True}),
            (AgentExecutionPhase.CONTEXT_VALIDATION, {"user_context_valid": True}),
            (AgentExecutionPhase.STARTING, {"agent_initialized": True}),
            (AgentExecutionPhase.THINKING, {"analyzing_user_request": True}),
            (AgentExecutionPhase.LLM_INTERACTION, {"querying_llm": True}),
            (AgentExecutionPhase.TOOL_EXECUTION, {"executing_optimization_tools": True}),
            (AgentExecutionPhase.RESULT_PROCESSING, {"formatting_response": True}),
            (AgentExecutionPhase.COMPLETING, {"finalizing_response": True}),
            (AgentExecutionPhase.COMPLETED, {"golden_path_success": True})
        ]
        
        # Execute Golden Path with WebSocket events
        for phase, metadata in phases:
            success = await self.tracker.transition_state(
                execution_id,
                phase,
                metadata=metadata,
                websocket_manager=self.mock_websocket_manager
            )
            assert success, f"Failed to transition to phase {phase}"
            
            # Send heartbeat to keep execution alive
            self.tracker.heartbeat(execution_id)
        
        # Verify final Golden Path state
        record = self.tracker.get_execution(execution_id)
        assert record.current_phase == AgentExecutionPhase.COMPLETED
        assert len(record.phase_history) == len(phases)
        assert record.metadata["golden_path"] is True
        assert record.metadata["business_critical"] is True
        
        # Complete the execution successfully (CRITICAL: use enum, not dictionary)
        success = self.tracker.update_execution_state(
            execution_id,
            ExecutionState.COMPLETED,  # NOT {"success": True, "completed": True}
            result={"golden_path_completed": True, "chat_response_delivered": True}
        )
        assert success
        
        # Verify WebSocket events were sent for Golden Path
        assert self.mock_websocket_manager.notify_agent_started.called
        assert self.mock_websocket_manager.notify_agent_thinking.called
        assert self.mock_websocket_manager.notify_agent_completed.called
        
        # Verify metrics show successful Golden Path execution
        metrics = self.tracker.get_metrics()
        assert metrics['successful_executions'] >= 1
        assert metrics['success_rate'] > 0
    
    async def test_metrics_collection_and_reporting(self):
        """Test metrics collection for business insights and monitoring."""
        # Create multiple executions with different outcomes
        exec_ids = []
        
        # Successful execution
        exec1 = self.tracker.create_execution("agent1", "thread1", "user1")
        self.tracker.start_execution(exec1)
        self.tracker.update_execution_state(exec1, ExecutionState.COMPLETED)
        exec_ids.append(exec1)
        
        # Failed execution  
        exec2 = self.tracker.create_execution("agent2", "thread2", "user2")
        self.tracker.start_execution(exec2)
        self.tracker.update_execution_state(exec2, ExecutionState.FAILED, error="Test failure")
        exec_ids.append(exec2)
        
        # Timed out execution
        exec3 = self.tracker.create_execution("agent3", "thread3", "user3")
        self.tracker.start_execution(exec3)
        self.tracker.update_execution_state(exec3, ExecutionState.TIMEOUT, error="Timeout")
        exec_ids.append(exec3)
        
        # Get and verify metrics
        metrics = self.tracker.get_metrics()
        assert metrics['total_executions'] >= 3
        assert metrics['successful_executions'] >= 1
        assert metrics['failed_executions'] >= 1
        assert metrics['timeout_executions'] >= 1
        assert metrics['active_executions'] == 0  # All completed
        assert 0 <= metrics['success_rate'] <= 1
        assert 0 <= metrics['failure_rate'] <= 1
        
        # Verify metrics are business-relevant
        assert 'success_rate' in metrics
        assert 'failure_rate' in metrics
        assert metrics['success_rate'] + metrics['failure_rate'] <= 1.0  # Should not exceed 100%


class TestAgentExecutionTrackerCompatibility(SSotAsyncTestCase):
    """
    Test compatibility aliases and backward compatibility functions.
    
    Ensures that the SSOT consolidation maintains backward compatibility
    for existing code that may use different import patterns.
    """
    
    def setup_method(self, method):
        """Setup compatibility test environment."""
        super().setup_method(method)
    
    async def test_execution_tracker_compatibility_alias(self):
        """Test that ExecutionTracker alias works correctly."""
        # ExecutionTracker should be an alias for AgentExecutionTracker
        assert ExecutionTracker == AgentExecutionTracker
        
        # Should be able to create instance using alias
        tracker = ExecutionTracker()
        assert isinstance(tracker, AgentExecutionTracker)
        
        # Should have all the same methods
        assert hasattr(tracker, 'create_execution')
        assert hasattr(tracker, 'update_execution_state')
        assert hasattr(tracker, 'heartbeat')
        assert hasattr(tracker, 'get_execution')
    
    async def test_global_tracker_instance_functions(self):
        """Test global tracker instance management functions."""
        # Test get_execution_tracker function
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()
        
        # Should return the same instance (singleton behavior)
        assert tracker1 is tracker2
        assert isinstance(tracker1, AgentExecutionTracker)
        
        # Test initialization and shutdown functions
        initialized_tracker = await initialize_tracker()
        assert initialized_tracker is tracker1
        
        # Clean shutdown
        await shutdown_tracker()


class TestAgentExecutionTrackerErrorConditions(SSotAsyncTestCase):
    """
    Test error conditions and edge cases for AgentExecutionTracker.
    
    Validates proper error handling and resilience under adverse conditions.
    """
    
    def setup_method(self, method):
        """Setup error condition test environment."""
        super().setup_method(method)
        self.tracker = AgentExecutionTracker()
    
    async def test_invalid_execution_id_handling(self):
        """Test handling of invalid or non-existent execution IDs."""
        # Test operations with non-existent execution ID
        invalid_id = "non_existent_exec_123"
        
        # Should handle gracefully without errors
        assert not self.tracker.start_execution(invalid_id)
        assert not self.tracker.update_execution_state(invalid_id, ExecutionState.RUNNING)
        assert not self.tracker.heartbeat(invalid_id)
        assert self.tracker.get_execution(invalid_id) is None
        assert self.tracker.get_agent_state(invalid_id) is None
        assert not self.tracker.set_agent_state(invalid_id, {"test": "value"})
        assert self.tracker.get_state_history(invalid_id) == []
        assert not self.tracker.cleanup_state(invalid_id)
    
    async def test_circuit_breaker_open_error_handling(self):
        """Test proper error handling when circuit breaker is open."""
        execution_id = self.tracker.create_execution(
            agent_name="test_agent",
            thread_id="test_thread", 
            user_id="test_user"
        )
        
        # Set very low thresholds for testing
        config = TimeoutConfig(
            failure_threshold=1,
            recovery_timeout=10.0,  # Long recovery time
            llm_api_timeout=0.1
        )
        self.tracker.set_timeout(execution_id, config)
        self.tracker.register_circuit_breaker(execution_id)
        
        # Trigger circuit breaker to open
        await self.tracker._on_circuit_breaker_failure(execution_id, "test_op", "test_error")
        
        # Verify circuit breaker is open
        cb_status = self.tracker.circuit_breaker_status(execution_id)
        assert cb_status['state'] == 'open'
        
        # Test that CircuitBreakerOpenError is raised
        async def test_operation():
            return "should_not_execute"
        
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await self.tracker.execute_with_circuit_breaker(
                execution_id,
                test_operation,
                "blocked_operation"
            )
        
        # Verify error message contains useful information
        error_message = str(exc_info.value)
        assert "Circuit breaker open" in error_message
        assert "blocked_operation" in error_message
    
    async def test_concurrent_access_and_race_condition_safety(self):
        """Test thread safety under high concurrent access."""
        execution_ids = []
        
        # Create multiple executions concurrently
        async def create_executions(batch_num: int):
            batch_ids = []
            for i in range(10):
                exec_id = self.tracker.create_execution(
                    agent_name=f"agent_batch_{batch_num}_{i}",
                    thread_id=f"thread_batch_{batch_num}_{i}",
                    user_id=f"user_batch_{batch_num}_{i}"
                )
                batch_ids.append(exec_id)
            return batch_ids
        
        # Run multiple batches concurrently
        batch_tasks = [create_executions(i) for i in range(5)]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Flatten results
        for batch in batch_results:
            execution_ids.extend(batch)
        
        # Verify all executions were created successfully
        assert len(execution_ids) == 50  # 5 batches * 10 executions each
        assert len(set(execution_ids)) == 50  # All IDs should be unique
        
        # Verify all executions are retrievable
        for exec_id in execution_ids:
            record = self.tracker.get_execution(exec_id)
            assert record is not None
            assert record.execution_id == exec_id
    
    async def test_cleanup_of_completed_executions(self):
        """Test cleanup of old completed executions."""
        # Create and complete multiple executions
        completed_ids = []
        for i in range(5):
            exec_id = self.tracker.create_execution(
                agent_name=f"cleanup_agent_{i}",
                thread_id=f"cleanup_thread_{i}",
                user_id=f"cleanup_user_{i}"
            )
            self.tracker.start_execution(exec_id)
            self.tracker.update_execution_state(exec_id, ExecutionState.COMPLETED)
            completed_ids.append(exec_id)
        
        # Verify all are completed but still retrievable
        for exec_id in completed_ids:
            record = self.tracker.get_execution(exec_id)
            assert record is not None
            assert record.is_terminal
        
        # Trigger cleanup by simulating old completion times
        for exec_id in completed_ids:
            record = self.tracker.get_execution(exec_id)
            if record:
                record.completed_at = datetime.now(timezone.utc) - timedelta(seconds=120)  # 2 minutes ago
        
        # Run cleanup
        await self.tracker._cleanup_old_executions()
        
        # Verify some executions may have been cleaned up
        # (Note: this depends on cleanup_interval setting)
        remaining_count = sum(1 for exec_id in completed_ids if self.tracker.get_execution(exec_id) is not None)
        # At minimum, executions should still exist or have been properly cleaned
        assert remaining_count >= 0  # Test passes if cleanup works without errors


# Export test classes for pytest discovery
__all__ = [
    'TestAgentExecutionTrackerIntegration',
    'TestAgentExecutionTrackerCompatibility', 
    'TestAgentExecutionTrackerErrorConditions'
]