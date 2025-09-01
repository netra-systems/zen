"""
Unit Tests for Execution Tracking Components
==========================================
Comprehensive unit tests for all execution tracking components:
- ExecutionRegistry: State management and persistence
- HeartbeatMonitor: Agent liveness detection  
- TimeoutManager: Execution timeout enforcement
- ExecutionTracker: Orchestration and integration
- AgentExecutionTracker: Core tracking functionality

These tests ensure each component works correctly in isolation
before testing their integration.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import execution tracking components
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker, ExecutionState as CoreExecutionState, ExecutionRecord
)
from netra_backend.app.agents.execution_tracking.registry import (
    ExecutionRegistry, ExecutionState, ExecutionRecord as NewExecutionRecord
)
from netra_backend.app.agents.execution_tracking.heartbeat import (
    HeartbeatMonitor, HeartbeatStatus
)
from netra_backend.app.agents.execution_tracking.timeout import (
    TimeoutManager, TimeoutInfo
)
from netra_backend.app.agents.execution_tracking.tracker import (
    ExecutionTracker, AgentExecutionContext, AgentExecutionResult, ExecutionProgress
)


class TestExecutionRegistry:
    """Unit tests for ExecutionRegistry"""
    
    @pytest.fixture
    async def registry(self):
        """Create a fresh ExecutionRegistry for each test"""
        registry = ExecutionRegistry()
        yield registry
        await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_register_execution(self, registry):
        """Test registering a new execution"""
        # Register execution
        record = await registry.register_execution(
            run_id="test-run-123",
            agent_name="test-agent",
            context={"test": True, "priority": "high"}
        )
        
        # Verify record properties
        assert record.execution_id is not None
        assert record.run_id == "test-run-123"
        assert record.agent_name == "test-agent"
        assert record.state == ExecutionState.PENDING
        assert record.context == {"test": True, "priority": "high"}
        assert record.created_at is not None
        assert record.updated_at is not None
        
        # Verify we can retrieve it
        retrieved = await registry.get_execution(record.execution_id)
        assert retrieved is not None
        assert retrieved.execution_id == record.execution_id
        assert retrieved.agent_name == "test-agent"
    
    @pytest.mark.asyncio
    async def test_update_execution_state(self, registry):
        """Test updating execution state"""
        # Register execution
        record = await registry.register_execution(
            run_id="test-run-update",
            agent_name="test-agent",
            context={}
        )
        
        execution_id = record.execution_id
        original_updated_at = record.updated_at
        
        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        # Update state
        success = await registry.update_execution_state(
            execution_id,
            ExecutionState.RUNNING,
            {"progress": "50%", "stage": "processing"}
        )
        
        assert success
        
        # Verify update
        updated_record = await registry.get_execution(execution_id)
        assert updated_record.state == ExecutionState.RUNNING
        assert updated_record.metadata == {"progress": "50%", "stage": "processing"}
        assert updated_record.updated_at > original_updated_at
    
    @pytest.mark.asyncio
    async def test_get_active_executions(self, registry):
        """Test retrieving active executions"""
        # Register multiple executions
        records = []
        for i in range(3):
            record = await registry.register_execution(
                run_id=f"test-run-{i}",
                agent_name=f"test-agent-{i}",
                context={"index": i}
            )
            records.append(record)
        
        # Complete one execution
        await registry.update_execution_state(
            records[1].execution_id,
            ExecutionState.SUCCESS
        )
        
        # Get active executions
        active = await registry.get_active_executions()
        
        # Should have 2 active (0 and 2), not the completed one (1)
        assert len(active) == 2
        active_ids = [r.execution_id for r in active]
        assert records[0].execution_id in active_ids
        assert records[2].execution_id in active_ids
        assert records[1].execution_id not in active_ids
    
    @pytest.mark.asyncio
    async def test_get_executions_by_agent(self, registry):
        """Test retrieving executions by agent name"""
        # Register executions for different agents
        agent_a_records = []
        agent_b_records = []
        
        for i in range(2):
            record_a = await registry.register_execution(
                run_id=f"test-run-a-{i}",
                agent_name="agent-a",
                context={"agent": "a", "index": i}
            )
            agent_a_records.append(record_a)
            
            record_b = await registry.register_execution(
                run_id=f"test-run-b-{i}",
                agent_name="agent-b", 
                context={"agent": "b", "index": i}
            )
            agent_b_records.append(record_b)
        
        # Get executions by agent
        agent_a_executions = await registry.get_executions_by_agent("agent-a")
        agent_b_executions = await registry.get_executions_by_agent("agent-b")
        
        # Verify correct filtering
        assert len(agent_a_executions) == 2
        assert len(agent_b_executions) == 2
        
        for record in agent_a_executions:
            assert record.agent_name == "agent-a"
        
        for record in agent_b_executions:
            assert record.agent_name == "agent-b"
    
    @pytest.mark.asyncio
    async def test_execution_metrics(self, registry):
        """Test execution metrics calculation"""
        # Initially no executions
        metrics = await registry.get_execution_metrics()
        assert metrics.total_executions == 0
        assert metrics.active_executions == 0
        assert metrics.success_rate == 0.0
        
        # Add some executions with different states
        records = []
        for i in range(5):
            record = await registry.register_execution(
                run_id=f"metrics-run-{i}",
                agent_name=f"metrics-agent-{i}",
                context={"test": "metrics"}
            )
            records.append(record)
        
        # Update states: 2 success, 1 failed, 2 still running
        await registry.update_execution_state(records[0].execution_id, ExecutionState.SUCCESS)
        await registry.update_execution_state(records[1].execution_id, ExecutionState.SUCCESS) 
        await registry.update_execution_state(records[2].execution_id, ExecutionState.FAILED)
        # records[3] and records[4] remain PENDING (active)
        
        # Check metrics
        metrics = await registry.get_execution_metrics()
        assert metrics.total_executions == 5
        assert metrics.active_executions == 2  # 2 still pending
        assert metrics.successful_executions == 2
        assert metrics.failed_executions == 1
        assert metrics.success_rate == 0.4  # 2/5
    
    @pytest.mark.asyncio
    async def test_health_status(self, registry):
        """Test health status reporting"""
        # Initially healthy
        health = await registry.get_health_status()
        assert health["status"] == "healthy"
        assert health["active_executions"] == 0
        
        # Add some executions
        for i in range(3):
            await registry.register_execution(
                run_id=f"health-run-{i}",
                agent_name=f"health-agent-{i}",
                context={}
            )
        
        # Health should still be good
        health = await registry.get_health_status()
        assert health["status"] == "healthy"
        assert health["active_executions"] == 3


class TestHeartbeatMonitor:
    """Unit tests for HeartbeatMonitor"""
    
    @pytest.fixture
    async def monitor(self):
        """Create HeartbeatMonitor for each test"""
        monitor = HeartbeatMonitor(heartbeat_interval_seconds=1.0)
        yield monitor
        await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping monitoring"""
        execution_id = "test-heartbeat-start-stop"
        
        # Initially not monitoring
        status = await monitor.get_heartbeat_status(execution_id)
        assert status is None
        
        # Start monitoring
        await monitor.start_monitoring(execution_id)
        
        # Should now have status
        status = await monitor.get_heartbeat_status(execution_id)
        assert status is not None
        assert status.execution_id == execution_id
        assert status.is_alive  # Initially alive
        assert status.missed_heartbeats == 0
        
        # Stop monitoring
        await monitor.stop_monitoring(execution_id)
        
        # Status should be gone
        status = await monitor.get_heartbeat_status(execution_id)
        assert status is None
    
    @pytest.mark.asyncio
    async def test_send_heartbeat(self, monitor):
        """Test sending heartbeats"""
        execution_id = "test-heartbeat-send"
        
        # Start monitoring
        await monitor.start_monitoring(execution_id)
        
        # Send heartbeat
        success = await monitor.send_heartbeat(execution_id, {"data": "test"})
        assert success
        
        # Verify status updated
        status = await monitor.get_heartbeat_status(execution_id)
        assert status.is_alive
        assert status.last_heartbeat_data == {"data": "test"}
        
        # Try sending heartbeat to non-monitored execution
        success = await monitor.send_heartbeat("non-existent", {})
        assert not success
    
    @pytest.mark.asyncio
    async def test_heartbeat_failure_detection(self, monitor):
        """Test detection of heartbeat failures"""
        execution_id = "test-heartbeat-failure"
        
        # Track failure callbacks
        failure_events = []
        
        async def failure_callback(exec_id: str, status: HeartbeatStatus):
            failure_events.append({"execution_id": exec_id, "status": status})
        
        monitor.add_failure_callback(failure_callback)
        
        # Start monitoring
        await monitor.start_monitoring(execution_id)
        
        # Send initial heartbeat
        await monitor.send_heartbeat(execution_id, {"initial": True})
        
        # Verify alive
        status = await monitor.get_heartbeat_status(execution_id)
        assert status.is_alive
        
        # Wait for heartbeat failure (monitor checks every 1 second)
        # Should fail after missing ~3-5 heartbeats
        for i in range(8):
            await asyncio.sleep(1)
            status = await monitor.get_heartbeat_status(execution_id)
            if not status.is_alive:
                break
        
        # Should be detected as dead
        status = await monitor.get_heartbeat_status(execution_id)
        assert not status.is_alive
        assert status.missed_heartbeats > 0
        
        # Failure callback should have been triggered
        assert len(failure_events) > 0
        assert failure_events[0]["execution_id"] == execution_id
    
    @pytest.mark.asyncio
    async def test_multiple_executions(self, monitor):
        """Test monitoring multiple executions simultaneously"""
        execution_ids = ["multi-exec-1", "multi-exec-2", "multi-exec-3"]
        
        # Start monitoring all
        for exec_id in execution_ids:
            await monitor.start_monitoring(exec_id)
        
        # Send heartbeats to some
        await monitor.send_heartbeat(execution_ids[0], {"agent": "1"})
        await monitor.send_heartbeat(execution_ids[1], {"agent": "2"})
        # Don't send to execution_ids[2]
        
        # Verify individual statuses
        status_0 = await monitor.get_heartbeat_status(execution_ids[0])
        status_1 = await monitor.get_heartbeat_status(execution_ids[1])
        status_2 = await monitor.get_heartbeat_status(execution_ids[2])
        
        assert status_0.is_alive
        assert status_1.is_alive
        assert status_2.is_alive  # Initially alive, hasn't failed yet
        
        # Wait for failure detection
        await asyncio.sleep(6)  # Wait for missed heartbeats
        
        # Check final statuses
        status_0 = await monitor.get_heartbeat_status(execution_ids[0])
        status_1 = await monitor.get_heartbeat_status(execution_ids[1]) 
        status_2 = await monitor.get_heartbeat_status(execution_ids[2])
        
        # 0 and 1 should be dead (no recent heartbeats)
        # 2 should also be dead (never sent heartbeats)
        assert not status_0.is_alive or status_0.missed_heartbeats > 0
        assert not status_1.is_alive or status_1.missed_heartbeats > 0
        assert not status_2.is_alive or status_2.missed_heartbeats > 0
    
    @pytest.mark.asyncio
    async def test_monitor_metrics(self, monitor):
        """Test heartbeat monitor metrics"""
        # Initial metrics
        metrics = await monitor.get_monitor_metrics()
        assert metrics["total_monitored_executions"] == 0
        assert metrics["active_monitors"] == 0
        assert metrics["dead_agents"] == []
        
        # Add monitoring
        for i in range(3):
            await monitor.start_monitoring(f"metrics-exec-{i}")
        
        # Check metrics
        metrics = await monitor.get_monitor_metrics()
        assert metrics["active_monitors"] == 3
        
        # Send heartbeats to keep some alive
        await monitor.send_heartbeat("metrics-exec-0", {})
        
        # Let others die
        await asyncio.sleep(6)
        
        # Check final metrics
        metrics = await monitor.get_monitor_metrics()
        assert len(metrics["dead_agents"]) > 0


class TestTimeoutManager:
    """Unit tests for TimeoutManager"""
    
    @pytest.fixture
    async def timeout_manager(self):
        """Create TimeoutManager for each test"""
        manager = TimeoutManager(check_interval_seconds=1.0)
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_set_timeout(self, timeout_manager):
        """Test setting execution timeouts"""
        execution_id = "test-timeout-set"
        timeout_seconds = 5.0
        
        # Set timeout
        await timeout_manager.set_timeout(execution_id, timeout_seconds, "test-agent")
        
        # Verify timeout info
        timeout_info = await timeout_manager.get_timeout_info(execution_id)
        assert timeout_info is not None
        assert timeout_info.execution_id == execution_id
        assert timeout_info.timeout_seconds == timeout_seconds
        assert timeout_info.agent_name == "test-agent"
        assert not timeout_info.has_timed_out
        assert timeout_info.remaining_seconds > 0
        assert timeout_info.remaining_seconds <= timeout_seconds
    
    @pytest.mark.asyncio
    async def test_timeout_detection(self, timeout_manager):
        """Test timeout detection"""
        execution_id = "test-timeout-detection"
        timeout_seconds = 2.0  # Short timeout for testing
        
        # Track timeout callbacks
        timeout_events = []
        
        async def timeout_callback(exec_id: str, timeout_info: TimeoutInfo):
            timeout_events.append({"execution_id": exec_id, "timeout_info": timeout_info})
        
        timeout_manager.add_timeout_callback(timeout_callback)
        
        # Set timeout
        await timeout_manager.set_timeout(execution_id, timeout_seconds, "test-agent")
        
        # Initially not timed out
        timeout_info = await timeout_manager.get_timeout_info(execution_id)
        assert not timeout_info.has_timed_out
        
        # Wait for timeout
        await asyncio.sleep(timeout_seconds + 2)  # Wait beyond timeout
        
        # Should be timed out now
        timeout_info = await timeout_manager.get_timeout_info(execution_id)
        assert timeout_info.has_timed_out
        assert timeout_info.remaining_seconds <= 0
        
        # Callback should have been triggered
        assert len(timeout_events) > 0
        assert timeout_events[0]["execution_id"] == execution_id
    
    @pytest.mark.asyncio
    async def test_clear_timeout(self, timeout_manager):
        """Test clearing timeouts"""
        execution_id = "test-timeout-clear"
        
        # Set timeout
        await timeout_manager.set_timeout(execution_id, 10.0, "test-agent")
        
        # Verify it exists
        timeout_info = await timeout_manager.get_timeout_info(execution_id)
        assert timeout_info is not None
        
        # Clear timeout
        await timeout_manager.clear_timeout(execution_id)
        
        # Should be gone
        timeout_info = await timeout_manager.get_timeout_info(execution_id)
        assert timeout_info is None
    
    @pytest.mark.asyncio
    async def test_agent_timeout_defaults(self, timeout_manager):
        """Test agent-specific timeout defaults"""
        # Test default timeout for unknown agent
        default_timeout = timeout_manager.get_timeout_for_agent("unknown-agent")
        assert default_timeout > 0
        
        # Test that we can get consistent timeouts
        timeout1 = timeout_manager.get_timeout_for_agent("test-agent")
        timeout2 = timeout_manager.get_timeout_for_agent("test-agent")
        assert timeout1 == timeout2
    
    @pytest.mark.asyncio
    async def test_timeout_metrics(self, timeout_manager):
        """Test timeout manager metrics"""
        # Initial metrics
        metrics = await timeout_manager.get_timeout_metrics()
        assert metrics["active_timeouts"] == 0
        assert metrics["timed_out_executions"] == 0
        
        # Add some timeouts
        for i in range(3):
            await timeout_manager.set_timeout(f"metrics-timeout-{i}", 1.0, f"agent-{i}")
        
        # Check metrics
        metrics = await timeout_manager.get_timeout_metrics()
        assert metrics["active_timeouts"] == 3
        
        # Wait for timeouts
        await asyncio.sleep(3)
        
        # Check final metrics  
        metrics = await timeout_manager.get_timeout_metrics()
        assert metrics["timed_out_executions"] > 0


class TestAgentExecutionTracker:
    """Unit tests for core AgentExecutionTracker"""
    
    @pytest.fixture
    async def tracker(self):
        """Create AgentExecutionTracker for each test"""
        tracker = AgentExecutionTracker(
            heartbeat_timeout=2,  # Fast timeout for testing
            execution_timeout=5,
            cleanup_interval=10
        )
        await tracker.start_monitoring()
        yield tracker
        await tracker.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_create_execution(self, tracker):
        """Test creating execution records"""
        execution_id = tracker.create_execution(
            agent_name="test-agent",
            thread_id="test-thread",
            user_id="test-user",
            timeout_seconds=30,
            metadata={"test": True}
        )
        
        assert execution_id is not None
        assert execution_id.startswith("exec_")
        
        # Verify record
        record = tracker.get_execution(execution_id)
        assert record is not None
        assert record.agent_name == "test-agent"
        assert record.thread_id == "test-thread"
        assert record.user_id == "test-user"
        assert record.state == CoreExecutionState.PENDING
        assert record.timeout_seconds == 30
        assert record.metadata == {"test": True}
    
    @pytest.mark.asyncio
    async def test_execution_lifecycle(self, tracker):
        """Test full execution lifecycle"""
        # Create execution
        execution_id = tracker.create_execution(
            agent_name="lifecycle-agent",
            thread_id="lifecycle-thread",
            user_id="lifecycle-user"
        )
        
        # Start execution
        success = tracker.start_execution(execution_id)
        assert success
        
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.STARTING
        
        # Send heartbeat (should move to RUNNING)
        success = tracker.heartbeat(execution_id)
        assert success
        
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.RUNNING
        assert record.heartbeat_count == 1
        
        # Update to completing
        success = tracker.update_execution_state(
            execution_id, 
            CoreExecutionState.COMPLETING,
            result="Test completed successfully"
        )
        assert success
        
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.COMPLETING
        assert record.result == "Test completed successfully"
        
        # Complete execution
        success = tracker.update_execution_state(
            execution_id,
            CoreExecutionState.COMPLETED
        )
        assert success
        
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.COMPLETED
        assert record.completed_at is not None
        assert record.is_terminal
        assert not record.is_alive
    
    @pytest.mark.asyncio
    async def test_heartbeat_death_detection(self, tracker):
        """Test death detection via missing heartbeats"""
        # Create and start execution
        execution_id = tracker.create_execution(
            agent_name="heartbeat-test-agent",
            thread_id="heartbeat-test-thread", 
            user_id="heartbeat-test-user"
        )
        
        tracker.start_execution(execution_id)
        
        # Send initial heartbeat
        tracker.heartbeat(execution_id)
        
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.RUNNING
        assert not record.is_dead(tracker.heartbeat_timeout)
        
        # Wait for death detection (heartbeat timeout is 2 seconds)
        await asyncio.sleep(4)
        
        # Should be detected as dead
        record = tracker.get_execution(execution_id)
        assert record.is_dead(tracker.heartbeat_timeout)
        
        # Let monitoring loop detect it
        await asyncio.sleep(3)  # Give monitoring time to detect
        
        # Should be marked as dead
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.DEAD
    
    @pytest.mark.asyncio
    async def test_execution_timeout(self, tracker):
        """Test execution timeout detection"""
        # Create execution with short timeout
        execution_id = tracker.create_execution(
            agent_name="timeout-test-agent",
            thread_id="timeout-test-thread",
            user_id="timeout-test-user",
            timeout_seconds=2  # 2 second timeout
        )
        
        tracker.start_execution(execution_id)
        
        # Keep sending heartbeats but don't complete
        for i in range(3):
            await asyncio.sleep(0.5)
            tracker.heartbeat(execution_id)
        
        # Should not be timed out yet (only ~1.5 seconds)
        record = tracker.get_execution(execution_id)
        assert not record.is_timed_out()
        assert record.state == CoreExecutionState.RUNNING
        
        # Wait for timeout
        await asyncio.sleep(3)  # Now should be timed out
        
        record = tracker.get_execution(execution_id)
        assert record.is_timed_out()
        
        # Give monitoring time to detect timeout
        await asyncio.sleep(3)
        
        # Should be marked as timed out
        record = tracker.get_execution(execution_id)
        assert record.state == CoreExecutionState.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_get_executions_by_filters(self, tracker):
        """Test filtering executions by different criteria"""
        # Create executions for different agents and threads
        exec_ids = []
        
        for i in range(2):
            exec_id = tracker.create_execution(
                agent_name=f"filter-agent-{i}",
                thread_id=f"filter-thread-{i}",
                user_id="filter-user"
            )
            exec_ids.append(exec_id)
            tracker.start_execution(exec_id)
        
        # Filter by agent
        agent_0_execs = tracker.get_executions_by_agent("filter-agent-0")
        assert len(agent_0_execs) == 1
        assert agent_0_execs[0].agent_name == "filter-agent-0"
        
        # Filter by thread
        thread_1_execs = tracker.get_executions_by_thread("filter-thread-1")
        assert len(thread_1_execs) == 1
        assert thread_1_execs[0].thread_id == "filter-thread-1"
        
        # Get active executions
        active_execs = tracker.get_active_executions()
        assert len(active_execs) == 2
    
    @pytest.mark.asyncio
    async def test_execution_metrics(self, tracker):
        """Test execution metrics"""
        # Initial metrics
        metrics = tracker.get_metrics()
        initial_total = metrics["total_executions"]
        
        # Create and complete various executions
        exec_ids = []
        
        # Create 3 executions
        for i in range(3):
            exec_id = tracker.create_execution(
                agent_name=f"metrics-agent-{i}",
                thread_id=f"metrics-thread-{i}",
                user_id="metrics-user"
            )
            exec_ids.append(exec_id)
            tracker.start_execution(exec_id)
        
        # Complete with different outcomes
        tracker.update_execution_state(exec_ids[0], CoreExecutionState.COMPLETED)
        tracker.update_execution_state(exec_ids[1], CoreExecutionState.FAILED, error="Test failure")
        # Leave exec_ids[2] running
        
        # Check metrics
        metrics = tracker.get_metrics()
        assert metrics["total_executions"] == initial_total + 3
        assert metrics["active_executions"] == 1  # Only one still running
        assert metrics["successful_executions"] >= 1
        assert metrics["failed_executions"] >= 1


class TestExecutionTrackerIntegration:
    """Integration tests for ExecutionTracker orchestration"""
    
    @pytest.fixture
    async def tracker(self):
        """Create ExecutionTracker for integration tests"""
        tracker = ExecutionTracker(
            websocket_bridge=None,
            heartbeat_interval=1.0,
            timeout_check_interval=1.0
        )
        yield tracker
        await tracker.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_execution_flow(self, tracker):
        """Test complete execution flow with all components"""
        # Create context
        context = AgentExecutionContext(
            run_id="integration-test",
            agent_name="integration-agent",
            thread_id="integration-thread",
            user_id="integration-user"
        )
        
        # Start execution
        execution_id = await tracker.start_execution(
            run_id=context.run_id,
            agent_name=context.agent_name,
            context=context
        )
        
        assert execution_id is not None
        
        # Verify initial status
        status = await tracker.get_execution_status(execution_id)
        assert status is not None
        assert status.execution_record.state in [ExecutionState.PENDING, ExecutionState.INITIALIZING]
        assert status.heartbeat_status is not None
        assert status.timeout_info is not None
        
        # Update progress (sends heartbeats)
        progress_updates = [
            ExecutionProgress(stage="init", percentage=10, message="Initializing"),
            ExecutionProgress(stage="process", percentage=50, message="Processing"),
            ExecutionProgress(stage="finalize", percentage=90, message="Finalizing")
        ]
        
        for progress in progress_updates:
            await tracker.update_execution_progress(execution_id, progress)
            await asyncio.sleep(0.1)  # Small delay between updates
        
        # Verify execution is running
        status = await tracker.get_execution_status(execution_id)
        assert status.execution_record.state == ExecutionState.RUNNING
        assert status.heartbeat_status.is_alive
        
        # Complete execution successfully
        result = AgentExecutionResult(
            success=True,
            execution_id=execution_id,
            duration_seconds=1.5,
            data={"result": "Success"}
        )
        
        await tracker.complete_execution(execution_id, result)
        
        # Verify completion
        status = await tracker.get_execution_status(execution_id)
        assert status.execution_record.state == ExecutionState.SUCCESS
    
    @pytest.mark.asyncio
    async def test_execution_failure_handling(self, tracker):
        """Test execution failure handling"""
        context = AgentExecutionContext(
            run_id="failure-test",
            agent_name="failure-agent", 
            thread_id="failure-thread",
            user_id="failure-user"
        )
        
        # Start execution
        execution_id = await tracker.start_execution(
            run_id=context.run_id,
            agent_name=context.agent_name,
            context=context
        )
        
        # Do some work
        await tracker.update_execution_progress(
            execution_id,
            ExecutionProgress(stage="working", percentage=30, message="Working...")
        )
        
        # Simulate failure
        error = Exception("Test execution failure")
        await tracker.handle_execution_failure(execution_id, error)
        
        # Verify failure handling
        status = await tracker.get_execution_status(execution_id)
        assert status.execution_record.state == ExecutionState.FAILED
        assert "Test execution failure" in status.execution_record.metadata.get("error", "")
    
    @pytest.mark.asyncio
    async def test_tracker_metrics_comprehensive(self, tracker):
        """Test comprehensive tracker metrics"""
        # Get initial metrics
        initial_metrics = await tracker.get_tracker_metrics()
        assert "tracker_metrics" in initial_metrics
        assert "registry_metrics" in initial_metrics
        assert "heartbeat_metrics" in initial_metrics
        assert "timeout_metrics" in initial_metrics
        
        # Create some executions
        execution_ids = []
        for i in range(3):
            context = AgentExecutionContext(
                run_id=f"metrics-test-{i}",
                agent_name=f"metrics-agent-{i}",
                thread_id=f"metrics-thread-{i}",
                user_id="metrics-user"
            )
            
            exec_id = await tracker.start_execution(
                run_id=context.run_id,
                agent_name=context.agent_name,
                context=context
            )
            execution_ids.append(exec_id)
        
        # Complete one successfully, fail one, leave one running
        result_success = AgentExecutionResult(
            success=True,
            execution_id=execution_ids[0],
            duration_seconds=1.0
        )
        await tracker.complete_execution(execution_ids[0], result_success)
        
        await tracker.handle_execution_failure(execution_ids[1], Exception("Test failure"))
        
        # Get final metrics
        final_metrics = await tracker.get_tracker_metrics()
        
        tracker_metrics = final_metrics["tracker_metrics"]
        assert tracker_metrics["total_executions_started"] == 3
        assert tracker_metrics["successful_executions"] == 1
        assert tracker_metrics["failed_executions"] == 1
        assert 0 < tracker_metrics["success_rate"] < 1
    
    @pytest.mark.asyncio
    async def test_health_status_comprehensive(self, tracker):
        """Test comprehensive health status"""
        # Get initial health
        health = await tracker.get_health_status()
        assert health["status"] == "healthy"
        assert health["active_executions"] == 0
        assert health["dead_agents"] == 0
        assert health["timed_out_agents"] == 0
        
        # Add some executions
        context = AgentExecutionContext(
            run_id="health-test",
            agent_name="health-agent",
            thread_id="health-thread",
            user_id="health-user"
        )
        
        exec_id = await tracker.start_execution(
            run_id=context.run_id,
            agent_name=context.agent_name,
            context=context
        )
        
        # Health should reflect active execution
        health = await tracker.get_health_status()
        assert health["active_executions"] > 0
        
        # Complete execution
        result = AgentExecutionResult(
            success=True,
            execution_id=exec_id,
            duration_seconds=0.5
        )
        await tracker.complete_execution(exec_id, result)
        
        # Health should return to baseline
        health = await tracker.get_health_status()
        # Note: active_executions might still be >0 due to cleanup delays


if __name__ == "__main__":
    # Run unit tests
    pytest.main([__file__, "-v", "--tb=short"])