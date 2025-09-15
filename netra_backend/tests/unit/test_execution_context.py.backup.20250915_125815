"""
Test Execution Context Management

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent execution tracking and resource management
- Value Impact: Reliable execution context enables performance monitoring and debugging
- Strategic Impact: Core platform infrastructure for agent operations
"""

import pytest
import time
import threading
from unittest.mock import MagicMock
from netra_backend.app.agents.base.execution_context import (
    ExecutionContext,
    ExecutionContextManager,
    AgentExecutionContext,
    ExecutionStatus,
    ExecutionMetadata,
    ResourceUsage,
    create_execution_context,
    create_agent_execution_context,
    get_context_manager
)


class TestExecutionContext:
    """Test ExecutionContext business logic"""
    
    @pytest.mark.unit
    def test_execution_context_initialization(self):
        """Test ExecutionContext initialization with default values"""
        # Test with defaults
        context = ExecutionContext()
        
        assert context.execution_id is not None
        assert len(context.execution_id) > 0
        assert context.status == ExecutionStatus.PENDING
        assert context.metadata is not None
        assert context.resource_usage is not None
        assert len(context._context_data) == 0
        assert context._error_info is None
        assert len(context._logs) == 0
    
    @pytest.mark.unit
    def test_execution_context_custom_initialization(self):
        """Test ExecutionContext initialization with custom values"""
        execution_id = "test-exec-123"
        metadata = ExecutionMetadata(
            user_id="user123",
            session_id="session456",
            agent_name="test_agent"
        )
        
        context = ExecutionContext(execution_id=execution_id, metadata=metadata)
        
        assert context.execution_id == execution_id
        assert context.metadata.user_id == "user123"
        assert context.metadata.session_id == "session456"
        assert context.metadata.agent_name == "test_agent"
    
    @pytest.mark.unit
    def test_execution_lifecycle_success(self):
        """Test successful execution lifecycle"""
        context = ExecutionContext()
        
        # Start execution
        start_time = time.time()
        context.start_execution()
        
        assert context.status == ExecutionStatus.RUNNING
        assert context.metadata.start_time is not None
        assert context.metadata.start_time >= start_time
        assert context.is_running() is True
        assert context.is_completed() is False
        
        # Complete execution
        time.sleep(0.01)  # Small delay for duration calculation
        context.complete_execution(success=True)
        
        assert context.status == ExecutionStatus.COMPLETED
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        assert context.metadata.duration > 0
        assert context.is_running() is False
        assert context.is_completed() is True
    
    @pytest.mark.unit
    def test_execution_lifecycle_failure(self):
        """Test failed execution lifecycle"""
        context = ExecutionContext()
        context.start_execution()
        
        # Fail execution with exception
        test_error = ValueError("Test error message")
        context.fail_execution(test_error)
        
        assert context.status == ExecutionStatus.FAILED
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        assert context._error_info is not None
        assert context._error_info['type'] == 'ValueError'
        assert context._error_info['message'] == 'Test error message'
        assert context._error_info['timestamp'] is not None
        assert context.is_completed() is True
    
    @pytest.mark.unit
    def test_execution_cancellation(self):
        """Test execution cancellation"""
        context = ExecutionContext()
        context.start_execution()
        
        context.cancel_execution()
        
        assert context.status == ExecutionStatus.CANCELLED
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        assert context.is_completed() is True
    
    @pytest.mark.unit
    def test_execution_timeout(self):
        """Test execution timeout"""
        context = ExecutionContext()
        context.start_execution()
        
        context.timeout_execution()
        
        assert context.status == ExecutionStatus.TIMEOUT
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        assert context.is_completed() is True
    
    @pytest.mark.unit
    def test_context_data_management(self):
        """Test context data storage and retrieval"""
        context = ExecutionContext()
        
        # Set context data
        context.set_context_data("user_id", "test_user")
        context.set_context_data("settings", {"theme": "dark", "lang": "en"})
        
        # Retrieve context data
        assert context.get_context_data("user_id") == "test_user"
        assert context.get_context_data("settings") == {"theme": "dark", "lang": "en"}
        assert context.get_context_data("non_existent") is None
        assert context.get_context_data("non_existent", "default") == "default"
    
    @pytest.mark.unit
    def test_resource_usage_tracking(self):
        """Test resource usage tracking and updates"""
        context = ExecutionContext()
        
        # Update resource usage - absolute values
        context.update_resource_usage(
            cpu_time=1.5,
            memory_peak=1024000,
            cost_estimate=0.05
        )
        
        assert context.resource_usage.cpu_time == 1.5
        assert context.resource_usage.memory_peak == 1024000
        assert context.resource_usage.cost_estimate == 0.05
        
        # Update resource usage - incremental counters
        context.update_resource_usage(
            network_requests=5,
            database_queries=3,
            llm_tokens=100
        )
        
        assert context.resource_usage.network_requests == 5
        assert context.resource_usage.database_queries == 3
        assert context.resource_usage.llm_tokens == 100
        
        # Update again - should increment counters
        context.update_resource_usage(
            network_requests=2,
            database_queries=1,
            llm_tokens=50
        )
        
        assert context.resource_usage.network_requests == 7
        assert context.resource_usage.database_queries == 4
        assert context.resource_usage.llm_tokens == 150
    
    @pytest.mark.unit
    def test_log_management(self):
        """Test log entry management"""
        context = ExecutionContext()
        
        # Add logs
        context._add_log("First log entry")
        context._add_log("Second log entry")
        
        logs = context.get_logs()
        assert len(logs) == 2
        assert "First log entry" in logs[0]
        assert "Second log entry" in logs[1]
        
        # Test log limit
        limited_logs = context.get_logs(limit=1)
        assert len(limited_logs) == 1
        assert "Second log entry" in limited_logs[0]
        
        # Clear logs
        context.clear_logs()
        assert len(context.get_logs()) == 0
    
    @pytest.mark.unit
    def test_log_size_limit(self):
        """Test log size limitation to prevent memory issues"""
        context = ExecutionContext()
        
        # Add more than 100 log entries
        for i in range(105):
            context._add_log(f"Log entry {i}")
        
        logs = context.get_logs()
        assert len(logs) == 100  # Should be limited to 100
        assert "Log entry 5" in logs[0]  # First 5 should be removed
        assert "Log entry 104" in logs[-1]  # Last entry should be present
    
    @pytest.mark.unit
    def test_execution_summary(self):
        """Test execution summary generation"""
        metadata = ExecutionMetadata(
            user_id="user123",
            session_id="session456",
            agent_name="test_agent"
        )
        context = ExecutionContext(execution_id="test-exec", metadata=metadata)
        
        context.set_context_data("key1", "value1")
        context.update_resource_usage(llm_tokens=50, cost_estimate=0.02)
        context.start_execution()
        
        summary = context.get_summary()
        
        assert summary['execution_id'] == "test-exec"
        assert summary['status'] == ExecutionStatus.RUNNING.value
        assert summary['metadata']['user_id'] == "user123"
        assert summary['metadata']['session_id'] == "session456"
        assert summary['metadata']['agent_name'] == "test_agent"
        assert summary['resource_usage']['llm_tokens'] == 50
        assert summary['resource_usage']['cost_estimate'] == 0.02
        assert summary['error_info'] is None
        assert summary['context_keys'] == ['key1']
    
    @pytest.mark.unit
    def test_thread_safety(self):
        """Test thread safety of execution context operations"""
        context = ExecutionContext()
        results = []
        errors = []
        
        def worker_thread(thread_id: int):
            try:
                # Each thread performs various operations
                context.set_context_data(f"thread_{thread_id}", thread_id)
                context.update_resource_usage(network_requests=1)
                context._add_log(f"Log from thread {thread_id}")
                
                # Get data back
                value = context.get_context_data(f"thread_{thread_id}")
                results.append(value == thread_id)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors and all operations succeeded
        assert len(errors) == 0
        assert len(results) == 10
        assert all(results)
        assert context.resource_usage.network_requests == 10
        assert len(context.get_logs()) == 10


class TestExecutionMetadata:
    """Test ExecutionMetadata business logic"""
    
    @pytest.mark.unit
    def test_metadata_duration_calculation(self):
        """Test duration calculation in metadata"""
        metadata = ExecutionMetadata()
        
        # No times set
        metadata.update_duration()
        assert metadata.duration is None
        
        # Only start time
        metadata.start_time = time.time()
        metadata.update_duration()
        assert metadata.duration is None
        
        # Both start and end times
        metadata.end_time = metadata.start_time + 2.5
        metadata.update_duration()
        assert metadata.duration == 2.5
    
    @pytest.mark.unit
    def test_metadata_custom_data(self):
        """Test custom data handling in metadata"""
        metadata = ExecutionMetadata()
        
        assert len(metadata.custom_data) == 0
        
        metadata.custom_data['priority'] = 'high'
        metadata.custom_data['tags'] = ['agent', 'optimization']
        
        assert metadata.custom_data['priority'] == 'high'
        assert metadata.custom_data['tags'] == ['agent', 'optimization']


class TestExecutionContextManager:
    """Test ExecutionContextManager business logic"""
    
    @pytest.mark.unit
    def test_context_manager_initialization(self):
        """Test ExecutionContextManager initialization"""
        manager = ExecutionContextManager()
        
        assert len(manager._contexts) == 0
        assert manager._lock is not None
    
    @pytest.mark.unit
    def test_create_and_get_context(self):
        """Test context creation and retrieval"""
        manager = ExecutionContextManager()
        
        # Create context with default ID
        context1 = manager.create_context()
        assert context1 is not None
        assert context1.execution_id is not None
        
        # Retrieve context
        retrieved = manager.get_context(context1.execution_id)
        assert retrieved is context1
        
        # Create context with custom ID
        metadata = ExecutionMetadata(user_id="user123")
        context2 = manager.create_context(execution_id="custom-id", metadata=metadata)
        assert context2.execution_id == "custom-id"
        assert context2.metadata.user_id == "user123"
        
        # Manager should have both contexts
        all_contexts = manager.get_all_contexts()
        assert len(all_contexts) == 2
        assert context1 in all_contexts
        assert context2 in all_contexts
    
    @pytest.mark.unit
    def test_remove_context(self):
        """Test context removal"""
        manager = ExecutionContextManager()
        context = manager.create_context()
        
        # Context should exist
        assert manager.get_context(context.execution_id) is not None
        
        # Remove context
        removed = manager.remove_context(context.execution_id)
        assert removed is True
        assert manager.get_context(context.execution_id) is None
        
        # Try to remove non-existent context
        removed = manager.remove_context("non-existent")
        assert removed is False
    
    @pytest.mark.unit
    def test_get_active_contexts(self):
        """Test active contexts retrieval"""
        manager = ExecutionContextManager()
        
        # Create contexts with different states
        pending_context = manager.create_context()
        running_context = manager.create_context()
        completed_context = manager.create_context()
        
        running_context.start_execution()
        completed_context.start_execution()
        completed_context.complete_execution()
        
        # Only running context should be active
        active_contexts = manager.get_active_contexts()
        assert len(active_contexts) == 1
        assert active_contexts[0] is running_context
    
    @pytest.mark.unit
    def test_cleanup_completed_contexts(self):
        """Test cleanup of completed contexts"""
        manager = ExecutionContextManager()
        
        # Create contexts
        running_context = manager.create_context()
        old_completed_context = manager.create_context()
        new_completed_context = manager.create_context()
        
        # Set up states
        running_context.start_execution()
        
        old_completed_context.start_execution()
        old_completed_context.complete_execution()
        old_completed_context.metadata.end_time = time.time() - 7200  # 2 hours ago
        
        new_completed_context.start_execution()
        new_completed_context.complete_execution()
        new_completed_context.metadata.end_time = time.time() - 300   # 5 minutes ago
        
        # Cleanup with 1 hour threshold
        removed_count = manager.cleanup_completed(max_age_seconds=3600)
        
        assert removed_count == 1  # Only old completed context should be removed
        assert manager.get_context(running_context.execution_id) is not None
        assert manager.get_context(old_completed_context.execution_id) is None
        assert manager.get_context(new_completed_context.execution_id) is not None
    
    @pytest.mark.unit
    def test_manager_thread_safety(self):
        """Test thread safety of context manager operations"""
        manager = ExecutionContextManager()
        created_contexts = []
        errors = []
        
        def worker_thread(thread_id: int):
            try:
                # Create context
                context = manager.create_context()
                created_contexts.append(context.execution_id)
                
                # Get context
                retrieved = manager.get_context(context.execution_id)
                assert retrieved is context
                
                # Start and complete execution
                context.start_execution()
                context.complete_execution()
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(created_contexts) == 10
        assert len(manager.get_all_contexts()) == 10


class TestAgentExecutionContext:
    """Test AgentExecutionContext business logic"""
    
    @pytest.mark.unit
    def test_agent_context_initialization(self):
        """Test AgentExecutionContext initialization"""
        context = AgentExecutionContext()
        
        assert context.execution_id is not None
        assert context.timestamp is not None
        assert context.status == ExecutionStatus.PENDING
        assert isinstance(context.timestamp, float)
        assert context.timestamp > 0
    
    @pytest.mark.unit
    def test_agent_context_timestamp_update(self):
        """Test timestamp update functionality"""
        context = AgentExecutionContext()
        original_timestamp = context.timestamp
        
        time.sleep(0.01)  # Small delay
        context.update_timestamp()
        
        assert context.timestamp > original_timestamp
        assert context.metadata.start_time == context.timestamp
    
    @pytest.mark.unit
    def test_agent_context_backwards_compatibility(self):
        """Test backwards compatibility with existing agent code"""
        metadata = ExecutionMetadata(user_id="agent_user", agent_name="test_agent")
        context = AgentExecutionContext(execution_id="agent-exec", metadata=metadata)
        
        # Should have all ExecutionContext functionality
        context.start_execution()
        context.set_context_data("agent_type", "optimization")
        context.update_resource_usage(llm_tokens=100)
        
        assert context.status == ExecutionStatus.RUNNING
        assert context.get_context_data("agent_type") == "optimization"
        assert context.resource_usage.llm_tokens == 100
        
        # Should also have agent-specific functionality
        assert hasattr(context, 'timestamp')
        assert context.timestamp is not None


class TestConvenienceFunctions:
    """Test convenience functions for context creation"""
    
    @pytest.mark.unit
    def test_create_execution_context(self):
        """Test create_execution_context convenience function"""
        metadata = ExecutionMetadata(user_id="test_user")
        context = create_execution_context(execution_id="test-id", metadata=metadata)
        
        assert isinstance(context, ExecutionContext)
        assert context.execution_id == "test-id"
        assert context.metadata.user_id == "test_user"
    
    @pytest.mark.unit
    def test_create_agent_execution_context(self):
        """Test create_agent_execution_context convenience function"""
        metadata = ExecutionMetadata(agent_name="test_agent")
        context = create_agent_execution_context(metadata=metadata)
        
        assert isinstance(context, AgentExecutionContext)
        assert context.metadata.agent_name == "test_agent"
        assert hasattr(context, 'timestamp')
    
    @pytest.mark.unit
    def test_get_context_manager_singleton(self):
        """Test global context manager singleton behavior"""
        manager1 = get_context_manager()
        manager2 = get_context_manager()
        
        assert manager1 is manager2  # Should be same instance
        
        # Should work with contexts
        context = manager1.create_context()
        retrieved = manager2.get_context(context.execution_id)
        assert retrieved is context


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_complete_execution_without_start(self):
        """Test completing execution without starting"""
        context = ExecutionContext()
        
        # Complete without starting
        context.complete_execution(success=True)
        
        assert context.status == ExecutionStatus.COMPLETED
        assert context.metadata.end_time is not None
        # start_time should still be None
        assert context.metadata.start_time is None
        assert context.metadata.duration is None  # Can't calculate without start
    
    @pytest.mark.unit
    def test_resource_usage_invalid_attributes(self):
        """Test resource usage updates with invalid attributes"""
        context = ExecutionContext()
        
        # Try to update non-existent attribute
        context.update_resource_usage(invalid_attribute=100)
        
        # Should not crash, invalid attributes should be ignored
        assert not hasattr(context.resource_usage, 'invalid_attribute')
        
        # Valid attributes should still work
        context.update_resource_usage(cpu_time=1.5)
        assert context.resource_usage.cpu_time == 1.5
    
    @pytest.mark.unit
    def test_multiple_status_changes(self):
        """Test multiple status changes and their effects"""
        context = ExecutionContext()
        
        # Start -> Cancel -> Complete (should stay cancelled)
        context.start_execution()
        assert context.status == ExecutionStatus.RUNNING
        
        context.cancel_execution()
        assert context.status == ExecutionStatus.CANCELLED
        
        # Trying to complete after cancellation
        context.complete_execution()
        assert context.status == ExecutionStatus.COMPLETED  # Should change
        
        # End time should be updated
        assert context.metadata.end_time is not None
    
    @pytest.mark.unit
    def test_summary_with_empty_context(self):
        """Test summary generation with minimal context data"""
        context = ExecutionContext()
        summary = context.get_summary()
        
        # Should handle empty/null values gracefully
        assert summary['execution_id'] is not None
        assert summary['status'] == ExecutionStatus.PENDING.value
        assert summary['error_info'] is None
        assert summary['log_count'] == 0
        assert summary['context_keys'] == []
        
        # Resource usage should have default values
        resource_usage = summary['resource_usage']
        assert resource_usage['cpu_time'] == 0.0
        assert resource_usage['memory_peak'] == 0
        assert resource_usage['llm_tokens'] == 0
        assert resource_usage['cost_estimate'] == 0.0