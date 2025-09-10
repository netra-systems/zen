"""
Comprehensive Unit Tests for ExecutionContext SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability 
- Business Goal: Ensure reliable agent execution tracking and user isolation
- Value Impact: ExecutionContext is critical for agent execution tracking, resource monitoring,
  and multi-user isolation which enables reliable AI service delivery
- Strategic Impact: Core infrastructure for agent execution pipeline that directly impacts
  customer experience and system reliability

Test Coverage:
- ExecutionStatus enum states and transitions
- ExecutionMetadata dataclass operations and validation
- ResourceUsage tracking with increment/absolute patterns
- ExecutionContext initialization, state management, and lifecycle
- Multi-user isolation scenarios and context separation
- Thread safety and concurrent operations
- Error handling and edge cases
- ExecutionContextManager lifecycle and cleanup
- AgentExecutionContext backwards compatibility
- Global context manager functions
- Race condition prevention and thread safety

CRITICAL: This is a unit test suite using minimal mocks and focusing on real object behavior.
All tests inherit from SSOT base test class and follow CLAUDE.md standards.
"""

import asyncio
import pytest
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase

from netra_backend.app.agents.base.execution_context import (
    ExecutionStatus,
    ExecutionMetadata,
    ResourceUsage,
    ExecutionContext,
    ExecutionContextManager,
    AgentExecutionContext,
    get_context_manager,
    create_execution_context,
    create_agent_execution_context,
)


class TestExecutionStatus(SSotBaseTestCase):
    """Test ExecutionStatus enum functionality."""
    
    def test_execution_status_enum_values(self):
        """Test all ExecutionStatus enum values are correctly defined."""
        # Test all enum values exist
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
        assert ExecutionStatus.TIMEOUT.value == "timeout"
        
        # Test enum completeness
        expected_statuses = {"pending", "running", "completed", "failed", "cancelled", "timeout"}
        actual_statuses = {status.value for status in ExecutionStatus}
        assert actual_statuses == expected_statuses
        
        self.record_metric("execution_status_values_tested", len(expected_statuses))
    
    def test_execution_status_string_representation(self):
        """Test ExecutionStatus string representation."""
        assert str(ExecutionStatus.PENDING) == "ExecutionStatus.PENDING"
        assert repr(ExecutionStatus.RUNNING) == "<ExecutionStatus.RUNNING: 'running'>"
        
    def test_execution_status_comparison(self):
        """Test ExecutionStatus comparison operations."""
        # Test equality
        assert ExecutionStatus.PENDING == ExecutionStatus.PENDING
        assert ExecutionStatus.RUNNING != ExecutionStatus.COMPLETED
        
        # Test membership
        running_statuses = [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]
        assert ExecutionStatus.RUNNING in running_statuses
        assert ExecutionStatus.FAILED not in running_statuses


class TestExecutionMetadata(SSotBaseTestCase):
    """Test ExecutionMetadata dataclass functionality."""
    
    def test_execution_metadata_initialization(self):
        """Test ExecutionMetadata initialization with default values."""
        metadata = ExecutionMetadata()
        
        # Test default values
        assert metadata.user_id is None
        assert metadata.session_id is None
        assert metadata.request_id is None
        assert metadata.agent_name is None
        assert metadata.tool_name is None
        assert metadata.start_time is None
        assert metadata.end_time is None
        assert metadata.duration is None
        assert metadata.custom_data == {}
        
        self.record_metric("metadata_default_fields", 9)
    
    def test_execution_metadata_initialization_with_values(self):
        """Test ExecutionMetadata initialization with specific values."""
        custom_data = {"key1": "value1", "key2": 42}
        metadata = ExecutionMetadata(
            user_id="user123",
            session_id="session456",
            request_id="request789",
            agent_name="test_agent",
            tool_name="test_tool",
            start_time=1000.0,
            end_time=1010.0,
            custom_data=custom_data
        )
        
        assert metadata.user_id == "user123"
        assert metadata.session_id == "session456"
        assert metadata.request_id == "request789"
        assert metadata.agent_name == "test_agent"
        assert metadata.tool_name == "test_tool"
        assert metadata.start_time == 1000.0
        assert metadata.end_time == 1010.0
        assert metadata.custom_data == custom_data
        assert metadata.duration is None  # Not calculated automatically
    
    def test_execution_metadata_update_duration(self):
        """Test ExecutionMetadata duration calculation."""
        metadata = ExecutionMetadata()
        
        # Test with no times set
        metadata.update_duration()
        assert metadata.duration is None
        
        # Test with only start time
        metadata.start_time = 1000.0
        metadata.update_duration()
        assert metadata.duration is None
        
        # Test with only end time
        metadata.start_time = None
        metadata.end_time = 1010.0
        metadata.update_duration()
        assert metadata.duration is None
        
        # Test with both times set
        metadata.start_time = 1000.0
        metadata.end_time = 1010.0
        metadata.update_duration()
        assert metadata.duration == 10.0
        
        self.record_metric("duration_calculation_tested", True)
    
    def test_execution_metadata_update_duration_precision(self):
        """Test ExecutionMetadata duration calculation precision."""
        metadata = ExecutionMetadata()
        metadata.start_time = 1000.123456
        metadata.end_time = 1000.789012
        metadata.update_duration()
        
        expected_duration = 1000.789012 - 1000.123456
        assert abs(metadata.duration - expected_duration) < 1e-10
    
    def test_execution_metadata_custom_data_mutation(self):
        """Test ExecutionMetadata custom_data dictionary mutation."""
        metadata = ExecutionMetadata()
        
        # Test initial empty dict
        assert metadata.custom_data == {}
        
        # Test adding data
        metadata.custom_data["test_key"] = "test_value"
        assert metadata.custom_data["test_key"] == "test_value"
        
        # Test multiple values
        metadata.custom_data.update({"key1": 1, "key2": [1, 2, 3]})
        assert len(metadata.custom_data) == 3
        assert metadata.custom_data["key1"] == 1
        assert metadata.custom_data["key2"] == [1, 2, 3]


class TestResourceUsage(SSotBaseTestCase):
    """Test ResourceUsage dataclass functionality."""
    
    def test_resource_usage_initialization(self):
        """Test ResourceUsage initialization with default values."""
        usage = ResourceUsage()
        
        assert usage.cpu_time == 0.0
        assert usage.memory_peak == 0
        assert usage.network_requests == 0
        assert usage.database_queries == 0
        assert usage.llm_tokens == 0
        assert usage.cost_estimate == 0.0
        
        self.record_metric("resource_usage_fields", 6)
    
    def test_resource_usage_initialization_with_values(self):
        """Test ResourceUsage initialization with specific values."""
        usage = ResourceUsage(
            cpu_time=1.5,
            memory_peak=1024000,
            network_requests=10,
            database_queries=5,
            llm_tokens=1500,
            cost_estimate=0.05
        )
        
        assert usage.cpu_time == 1.5
        assert usage.memory_peak == 1024000
        assert usage.network_requests == 10
        assert usage.database_queries == 5
        assert usage.llm_tokens == 1500
        assert usage.cost_estimate == 0.05
    
    def test_resource_usage_field_types(self):
        """Test ResourceUsage field type validation."""
        usage = ResourceUsage()
        
        # Test float fields
        usage.cpu_time = 2.5
        usage.cost_estimate = 0.10
        assert isinstance(usage.cpu_time, float)
        assert isinstance(usage.cost_estimate, float)
        
        # Test int fields
        usage.memory_peak = 2048000
        usage.network_requests = 20
        usage.database_queries = 10
        usage.llm_tokens = 3000
        assert isinstance(usage.memory_peak, int)
        assert isinstance(usage.network_requests, int)
        assert isinstance(usage.database_queries, int)
        assert isinstance(usage.llm_tokens, int)


class TestExecutionContext(SSotBaseTestCase):
    """Test ExecutionContext core functionality."""
    
    def test_execution_context_initialization(self):
        """Test ExecutionContext initialization with defaults."""
        context = ExecutionContext()
        
        # Test default values
        assert context.execution_id is not None
        assert len(context.execution_id) > 0
        assert isinstance(context.metadata, ExecutionMetadata)
        assert context.status == ExecutionStatus.PENDING
        assert isinstance(context.resource_usage, ResourceUsage)
        assert context._context_data == {}
        assert context._error_info is None
        assert context._logs == []
        assert hasattr(context._lock, 'acquire') and hasattr(context._lock, 'release')  # Check it's a lock-like object
        
        self.record_metric("context_initialization_fields", 8)
    
    def test_execution_context_initialization_with_params(self):
        """Test ExecutionContext initialization with specific parameters."""
        execution_id = "test_execution_123"
        metadata = ExecutionMetadata(user_id="user123", agent_name="test_agent")
        
        context = ExecutionContext(execution_id=execution_id, metadata=metadata)
        
        assert context.execution_id == execution_id
        assert context.metadata is metadata
        assert context.metadata.user_id == "user123"
        assert context.metadata.agent_name == "test_agent"
    
    def test_execution_context_unique_ids(self):
        """Test ExecutionContext generates unique IDs."""
        contexts = [ExecutionContext() for _ in range(100)]
        execution_ids = [ctx.execution_id for ctx in contexts]
        
        # All IDs should be unique
        assert len(set(execution_ids)) == len(execution_ids)
        
        # All IDs should be valid UUIDs (basic format check)
        for exec_id in execution_ids:
            assert len(exec_id) > 20  # UUID should be longer than 20 chars
            assert "-" in exec_id  # UUID format includes dashes
        
        self.record_metric("unique_ids_generated", len(contexts))
    
    def test_start_execution(self):
        """Test start_execution state transition."""
        context = ExecutionContext()
        
        # Initial state
        assert context.status == ExecutionStatus.PENDING
        assert context.metadata.start_time is None
        
        # Start execution
        start_time_before = time.time()
        context.start_execution()
        start_time_after = time.time()
        
        assert context.status == ExecutionStatus.RUNNING
        assert context.metadata.start_time is not None
        assert start_time_before <= context.metadata.start_time <= start_time_after
        assert len(context._logs) > 0
        assert "Execution started" in context._logs[0]
        
        self.record_metric("start_execution_tested", True)
    
    def test_complete_execution_success(self):
        """Test complete_execution with success=True."""
        context = ExecutionContext()
        context.start_execution()
        start_time = context.metadata.start_time
        
        # Complete execution
        end_time_before = time.time()
        context.complete_execution(success=True)
        end_time_after = time.time()
        
        assert context.status == ExecutionStatus.COMPLETED
        assert context.metadata.end_time is not None
        assert end_time_before <= context.metadata.end_time <= end_time_after
        assert context.metadata.duration is not None
        assert context.metadata.duration > 0
        assert context.metadata.duration == context.metadata.end_time - start_time
        
        # Check log
        completed_logs = [log for log in context._logs if "completed successfully" in log]
        assert len(completed_logs) > 0
    
    def test_complete_execution_failure(self):
        """Test complete_execution with success=False."""
        context = ExecutionContext()
        context.start_execution()
        
        context.complete_execution(success=False)
        
        assert context.status == ExecutionStatus.FAILED
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        
        # Check log
        failed_logs = [log for log in context._logs if "failed" in log]
        assert len(failed_logs) > 0
    
    def test_fail_execution(self):
        """Test fail_execution with error information."""
        context = ExecutionContext()
        context.start_execution()
        
        test_error = ValueError("Test error message")
        context.fail_execution(test_error)
        
        assert context.status == ExecutionStatus.FAILED
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        assert context._error_info is not None
        assert context._error_info["type"] == "ValueError"
        assert context._error_info["message"] == "Test error message"
        assert "timestamp" in context._error_info
        
        # Check log
        error_logs = [log for log in context._logs if "Test error message" in log]
        assert len(error_logs) > 0
        
        self.record_metric("error_handling_tested", True)
    
    def test_cancel_execution(self):
        """Test cancel_execution state transition."""
        context = ExecutionContext()
        context.start_execution()
        
        context.cancel_execution()
        
        assert context.status == ExecutionStatus.CANCELLED
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        
        # Check log
        cancelled_logs = [log for log in context._logs if "cancelled" in log]
        assert len(cancelled_logs) > 0
    
    def test_timeout_execution(self):
        """Test timeout_execution state transition."""
        context = ExecutionContext()
        context.start_execution()
        
        context.timeout_execution()
        
        assert context.status == ExecutionStatus.TIMEOUT
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
        
        # Check log
        timeout_logs = [log for log in context._logs if "timed out" in log]
        assert len(timeout_logs) > 0
    
    def test_context_data_operations(self):
        """Test set_context_data and get_context_data operations."""
        context = ExecutionContext()
        
        # Test setting and getting data
        context.set_context_data("key1", "value1")
        context.set_context_data("key2", 42)
        context.set_context_data("key3", {"nested": "dict"})
        
        assert context.get_context_data("key1") == "value1"
        assert context.get_context_data("key2") == 42
        assert context.get_context_data("key3") == {"nested": "dict"}
        
        # Test default values
        assert context.get_context_data("nonexistent") is None
        assert context.get_context_data("nonexistent", "default") == "default"
        
        self.record_metric("context_data_operations_tested", True)
    
    def test_update_resource_usage_incremental(self):
        """Test update_resource_usage with incremental counters."""
        context = ExecutionContext()
        
        # Test incremental fields
        context.update_resource_usage(network_requests=5)
        assert context.resource_usage.network_requests == 5
        
        context.update_resource_usage(network_requests=3)
        assert context.resource_usage.network_requests == 8
        
        context.update_resource_usage(database_queries=2, llm_tokens=100)
        assert context.resource_usage.database_queries == 2
        assert context.resource_usage.llm_tokens == 100
        
        context.update_resource_usage(database_queries=1, llm_tokens=50)
        assert context.resource_usage.database_queries == 3
        assert context.resource_usage.llm_tokens == 150
        
        self.record_metric("incremental_updates_tested", True)
    
    def test_update_resource_usage_absolute(self):
        """Test update_resource_usage with absolute values."""
        context = ExecutionContext()
        
        # Test absolute fields
        context.update_resource_usage(cpu_time=1.5, memory_peak=1024, cost_estimate=0.05)
        assert context.resource_usage.cpu_time == 1.5
        assert context.resource_usage.memory_peak == 1024
        assert context.resource_usage.cost_estimate == 0.05
        
        # Update again - should replace, not increment
        context.update_resource_usage(cpu_time=2.0, memory_peak=2048)
        assert context.resource_usage.cpu_time == 2.0
        assert context.resource_usage.memory_peak == 2048
        assert context.resource_usage.cost_estimate == 0.05  # Unchanged
    
    def test_update_resource_usage_invalid_fields(self):
        """Test update_resource_usage ignores invalid fields."""
        context = ExecutionContext()
        
        # This should not raise an error and should be ignored
        context.update_resource_usage(invalid_field=123, cpu_time=1.0)
        assert context.resource_usage.cpu_time == 1.0
        assert not hasattr(context.resource_usage, "invalid_field")
    
    def test_status_methods(self):
        """Test is_running and is_completed status methods."""
        context = ExecutionContext()
        
        # Initial state
        assert not context.is_running()
        assert not context.is_completed()
        assert context.get_status() == ExecutionStatus.PENDING
        
        # Running state
        context.start_execution()
        assert context.is_running()
        assert not context.is_completed()
        assert context.get_status() == ExecutionStatus.RUNNING
        
        # Completed state
        context.complete_execution(success=True)
        assert not context.is_running()
        assert context.is_completed()
        assert context.get_status() == ExecutionStatus.COMPLETED
        
        # Failed state (also completed)
        context = ExecutionContext()
        context.start_execution()
        context.fail_execution(Exception("test"))
        assert not context.is_running()
        assert context.is_completed()
        assert context.get_status() == ExecutionStatus.FAILED
    
    def test_get_summary(self):
        """Test get_summary comprehensive data export."""
        metadata = ExecutionMetadata(user_id="user123", agent_name="test_agent")
        context = ExecutionContext(execution_id="test_123", metadata=metadata)
        
        context.start_execution()
        context.set_context_data("test_key", "test_value")
        context.update_resource_usage(cpu_time=1.5, network_requests=3)
        context.complete_execution(success=True)
        
        summary = context.get_summary()
        
        # Test structure
        assert "execution_id" in summary
        assert "status" in summary
        assert "metadata" in summary
        assert "resource_usage" in summary
        assert "error_info" in summary
        assert "log_count" in summary
        assert "context_keys" in summary
        
        # Test values
        assert summary["execution_id"] == "test_123"
        assert summary["status"] == "completed"
        assert summary["metadata"]["user_id"] == "user123"
        assert summary["metadata"]["agent_name"] == "test_agent"
        assert summary["resource_usage"]["cpu_time"] == 1.5
        assert summary["resource_usage"]["network_requests"] == 3
        assert summary["error_info"] is None
        assert summary["log_count"] > 0
        assert "test_key" in summary["context_keys"]
        
        self.record_metric("summary_structure_validated", True)
    
    def test_logs_operations(self):
        """Test log operations and management."""
        context = ExecutionContext()
        
        # Test initial state
        logs = context.get_logs()
        assert logs == []
        
        # Test logging through execution operations
        context.start_execution()
        context.complete_execution(success=True)
        
        logs = context.get_logs()
        assert len(logs) >= 2
        assert any("started" in log for log in logs)
        assert any("completed" in log for log in logs)
        
        # Test log format (should include timestamp)
        for log in logs:
            assert "[" in log and "]" in log  # Timestamp format
        
        # Test limited logs
        limited_logs = context.get_logs(limit=1)
        assert len(limited_logs) == 1
        assert limited_logs[0] == logs[-1]  # Should be the last log
        
        # Test clear logs
        context.clear_logs()
        assert context.get_logs() == []
    
    def test_logs_limit_management(self):
        """Test log limit management (max 100 entries)."""
        context = ExecutionContext()
        
        # Add more than 100 log entries manually
        for i in range(150):
            context._add_log(f"Test log entry {i}")
        
        logs = context.get_logs()
        assert len(logs) == 100  # Should be limited to 100
        assert "Test log entry 149" in logs[-1]  # Should have the latest entries
        assert not any("Test log entry 0" in log for log in logs)  # Should not have early entries


class TestExecutionContextThreadSafety(SSotBaseTestCase):
    """Test ExecutionContext thread safety and concurrent operations."""
    
    def test_concurrent_context_data_access(self):
        """Test concurrent access to context data."""
        context = ExecutionContext()
        
        def worker(worker_id: int):
            for i in range(50):
                key = f"worker_{worker_id}_item_{i}"
                value = f"value_{worker_id}_{i}"
                context.set_context_data(key, value)
                retrieved = context.get_context_data(key)
                assert retrieved == value, f"Data corruption detected: {key}"
        
        # Run multiple workers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            for future in futures:
                future.result()  # Wait for completion and check for exceptions
        
        # Verify all data was stored correctly
        for worker_id in range(5):
            for i in range(50):
                key = f"worker_{worker_id}_item_{i}"
                expected_value = f"value_{worker_id}_{i}"
                actual_value = context.get_context_data(key)
                assert actual_value == expected_value
        
        self.record_metric("concurrent_context_operations", 250)
    
    def test_concurrent_resource_usage_updates(self):
        """Test concurrent resource usage updates."""
        context = ExecutionContext()
        
        def worker(iterations: int):
            for _ in range(iterations):
                context.update_resource_usage(
                    network_requests=1,
                    database_queries=1,
                    llm_tokens=10,
                    cpu_time=0.1,
                    memory_peak=1024
                )
        
        iterations_per_worker = 100
        num_workers = 5
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, iterations_per_worker) for _ in range(num_workers)]
            for future in futures:
                future.result()
        
        # Verify incremental counters
        expected_incremental = iterations_per_worker * num_workers
        assert context.resource_usage.network_requests == expected_incremental
        assert context.resource_usage.database_queries == expected_incremental
        assert context.resource_usage.llm_tokens == expected_incremental * 10
        
        # Verify absolute values (should be the last written value)
        assert context.resource_usage.cpu_time == 0.1
        assert context.resource_usage.memory_peak == 1024
        
        self.record_metric("concurrent_resource_updates", expected_incremental)
    
    def test_concurrent_status_transitions(self):
        """Test concurrent status transitions are properly serialized."""
        context = ExecutionContext()
        
        def start_worker():
            context.start_execution()
        
        def complete_worker():
            time.sleep(0.01)  # Small delay to ensure start happens first
            context.complete_execution(success=True)
        
        # Run concurrent status changes
        with ThreadPoolExecutor(max_workers=2) as executor:
            start_future = executor.submit(start_worker)
            complete_future = executor.submit(complete_worker)
            
            start_future.result()
            complete_future.result()
        
        # Verify final state is consistent
        assert context.status == ExecutionStatus.COMPLETED
        assert context.metadata.start_time is not None
        assert context.metadata.end_time is not None
        assert context.metadata.duration is not None
    
    def test_concurrent_log_operations(self):
        """Test concurrent log operations."""
        context = ExecutionContext()
        
        def log_worker(worker_id: int):
            for i in range(20):
                # Use start_execution to generate logs (which calls _add_log)
                test_context = ExecutionContext()
                test_context._add_log(f"Worker {worker_id} - Log {i}")
                
                # Copy log to main context safely
                with context._lock:
                    context._logs.extend(test_context._logs)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(log_worker, i) for i in range(3)]
            for future in futures:
                future.result()
        
        logs = context.get_logs()
        assert len(logs) == 60  # 3 workers * 20 logs each
        
        # Verify all worker logs are present
        for worker_id in range(3):
            worker_logs = [log for log in logs if f"Worker {worker_id}" in log]
            assert len(worker_logs) == 20


class TestExecutionContextUserIsolation(SSotBaseTestCase):
    """Test ExecutionContext user isolation scenarios."""
    
    def test_multiple_user_contexts_isolation(self):
        """Test that different user contexts are properly isolated."""
        # Create contexts for different users
        user1_metadata = ExecutionMetadata(user_id="user1", session_id="session1")
        user2_metadata = ExecutionMetadata(user_id="user2", session_id="session2")
        
        user1_context = ExecutionContext(metadata=user1_metadata)
        user2_context = ExecutionContext(metadata=user2_metadata)
        
        # Set different data for each user
        user1_context.set_context_data("user_data", "user1_data")
        user1_context.set_context_data("shared_key", "user1_value")
        user1_context.update_resource_usage(network_requests=5, cpu_time=1.0)
        
        user2_context.set_context_data("user_data", "user2_data")
        user2_context.set_context_data("shared_key", "user2_value")
        user2_context.update_resource_usage(network_requests=3, cpu_time=2.0)
        
        # Verify isolation
        assert user1_context.get_context_data("user_data") == "user1_data"
        assert user2_context.get_context_data("user_data") == "user2_data"
        assert user1_context.get_context_data("shared_key") == "user1_value"
        assert user2_context.get_context_data("shared_key") == "user2_value"
        
        assert user1_context.resource_usage.network_requests == 5
        assert user2_context.resource_usage.network_requests == 3
        assert user1_context.resource_usage.cpu_time == 1.0
        assert user2_context.resource_usage.cpu_time == 2.0
        
        self.record_metric("user_isolation_verified", True)
    
    def test_concurrent_multi_user_operations(self):
        """Test concurrent operations across multiple user contexts."""
        contexts = {}
        
        def user_worker(user_id: str):
            metadata = ExecutionMetadata(user_id=user_id, session_id=f"session_{user_id}")
            context = ExecutionContext(metadata=metadata)
            contexts[user_id] = context
            
            # Simulate user-specific operations
            for i in range(50):
                context.set_context_data(f"data_{i}", f"{user_id}_value_{i}")
                context.update_resource_usage(network_requests=1, llm_tokens=10)
            
            context.start_execution()
            time.sleep(0.01)  # Simulate some processing
            context.complete_execution(success=True)
        
        # Run multiple users concurrently
        user_ids = [f"user_{i}" for i in range(5)]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(user_worker, user_id) for user_id in user_ids]
            for future in futures:
                future.result()
        
        # Verify each user's context is isolated and correct
        for user_id in user_ids:
            context = contexts[user_id]
            assert context.metadata.user_id == user_id
            assert context.status == ExecutionStatus.COMPLETED
            assert context.resource_usage.network_requests == 50
            assert context.resource_usage.llm_tokens == 500
            
            # Verify user-specific data
            for i in range(50):
                expected_value = f"{user_id}_value_{i}"
                actual_value = context.get_context_data(f"data_{i}")
                assert actual_value == expected_value
        
        self.record_metric("multi_user_concurrent_operations", len(user_ids))


class TestExecutionContextManager(SSotBaseTestCase):
    """Test ExecutionContextManager functionality."""
    
    def test_context_manager_initialization(self):
        """Test ExecutionContextManager initialization."""
        manager = ExecutionContextManager()
        
        assert manager._contexts == {}
        assert hasattr(manager._lock, 'acquire') and hasattr(manager._lock, 'release')  # Check it's a lock-like object
    
    def test_create_context(self):
        """Test context creation through manager."""
        manager = ExecutionContextManager()
        
        # Create context with default parameters
        context1 = manager.create_context()
        assert context1 is not None
        assert context1.execution_id in manager._contexts
        assert manager._contexts[context1.execution_id] is context1
        
        # Create context with specific parameters
        metadata = ExecutionMetadata(user_id="user123")
        context2 = manager.create_context(execution_id="custom_id", metadata=metadata)
        assert context2.execution_id == "custom_id"
        assert context2.metadata.user_id == "user123"
        assert "custom_id" in manager._contexts
        
        self.record_metric("contexts_created", 2)
    
    def test_get_context(self):
        """Test context retrieval through manager."""
        manager = ExecutionContextManager()
        
        # Test non-existent context
        assert manager.get_context("nonexistent") is None
        
        # Test existing context
        context = manager.create_context(execution_id="test_id")
        retrieved = manager.get_context("test_id")
        assert retrieved is context
        assert retrieved.execution_id == "test_id"
    
    def test_remove_context(self):
        """Test context removal through manager."""
        manager = ExecutionContextManager()
        
        # Test removing non-existent context
        assert manager.remove_context("nonexistent") is False
        
        # Test removing existing context
        context = manager.create_context(execution_id="test_id")
        assert "test_id" in manager._contexts
        
        result = manager.remove_context("test_id")
        assert result is True
        assert "test_id" not in manager._contexts
        
        # Test removing again
        assert manager.remove_context("test_id") is False
    
    def test_get_active_contexts(self):
        """Test retrieving active (running) contexts."""
        manager = ExecutionContextManager()
        
        # Create contexts in different states
        pending_context = manager.create_context()
        running_context = manager.create_context()
        completed_context = manager.create_context()
        
        running_context.start_execution()
        completed_context.start_execution()
        completed_context.complete_execution(success=True)
        
        active_contexts = manager.get_active_contexts()
        assert len(active_contexts) == 1
        assert active_contexts[0] is running_context
        assert pending_context not in active_contexts
        assert completed_context not in active_contexts
    
    def test_get_all_contexts(self):
        """Test retrieving all contexts."""
        manager = ExecutionContextManager()
        
        # Create multiple contexts
        contexts = [manager.create_context() for _ in range(5)]
        
        all_contexts = manager.get_all_contexts()
        assert len(all_contexts) == 5
        
        for context in contexts:
            assert context in all_contexts
    
    def test_cleanup_completed(self):
        """Test cleanup of completed contexts based on age."""
        manager = ExecutionContextManager()
        
        # Create contexts
        old_completed = manager.create_context(execution_id="old_completed")
        recent_completed = manager.create_context(execution_id="recent_completed")
        running_context = manager.create_context(execution_id="running")
        
        # Set up states and times
        old_time = time.time() - 7200  # 2 hours ago
        recent_time = time.time() - 1800  # 30 minutes ago
        
        old_completed.start_execution()
        old_completed.metadata.start_time = old_time - 10
        old_completed.complete_execution(success=True)
        old_completed.metadata.end_time = old_time
        
        recent_completed.start_execution()
        recent_completed.metadata.start_time = recent_time - 10
        recent_completed.complete_execution(success=True)
        recent_completed.metadata.end_time = recent_time
        
        running_context.start_execution()
        
        # Test cleanup with 1 hour threshold
        removed_count = manager.cleanup_completed(max_age_seconds=3600)
        
        assert removed_count == 1
        assert "old_completed" not in manager._contexts
        assert "recent_completed" in manager._contexts
        assert "running" in manager._contexts
        
        self.record_metric("contexts_cleaned_up", removed_count)
    
    def test_cleanup_completed_no_end_time(self):
        """Test cleanup ignores contexts without end_time."""
        manager = ExecutionContextManager()
        
        context = manager.create_context()
        context.status = ExecutionStatus.COMPLETED
        # No end_time set
        
        removed_count = manager.cleanup_completed(max_age_seconds=0)
        assert removed_count == 0
        assert context.execution_id in manager._contexts


class TestGlobalContextManager(SSotBaseTestCase):
    """Test global context manager functions."""
    
    def test_get_context_manager_singleton(self):
        """Test get_context_manager returns singleton instance."""
        # Reset global state first
        import netra_backend.app.agents.base.execution_context as ec_module
        ec_module._context_manager = None
        
        manager1 = get_context_manager()
        manager2 = get_context_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, ExecutionContextManager)
    
    def test_create_execution_context_convenience(self):
        """Test create_execution_context convenience function."""
        # Reset global state
        import netra_backend.app.agents.base.execution_context as ec_module
        ec_module._context_manager = None
        
        metadata = ExecutionMetadata(user_id="user123")
        context = create_execution_context(execution_id="test_id", metadata=metadata)
        
        assert context.execution_id == "test_id"
        assert context.metadata.user_id == "user123"
        
        # Verify it's registered with global manager
        manager = get_context_manager()
        assert manager.get_context("test_id") is context
    
    def test_create_agent_execution_context_convenience(self):
        """Test create_agent_execution_context convenience function."""
        metadata = ExecutionMetadata(agent_name="test_agent")
        context = create_agent_execution_context(execution_id="agent_test", metadata=metadata)
        
        assert isinstance(context, AgentExecutionContext)
        assert context.execution_id == "agent_test"
        assert context.metadata.agent_name == "test_agent"
        assert hasattr(context, "timestamp")


class TestAgentExecutionContext(SSotBaseTestCase):
    """Test AgentExecutionContext backwards compatibility."""
    
    def test_agent_execution_context_initialization(self):
        """Test AgentExecutionContext initialization."""
        context = AgentExecutionContext()
        
        # Test inheritance
        assert isinstance(context, ExecutionContext)
        assert isinstance(context, AgentExecutionContext)
        
        # Test additional fields
        assert hasattr(context, "timestamp")
        assert context.timestamp is not None
        assert context.timestamp > 0
    
    def test_agent_execution_context_with_params(self):
        """Test AgentExecutionContext with parameters."""
        metadata = ExecutionMetadata(agent_name="test_agent", start_time=1000.0)
        context = AgentExecutionContext(execution_id="agent_123", metadata=metadata)
        
        assert context.execution_id == "agent_123"
        assert context.metadata.agent_name == "test_agent"
        assert context.timestamp == 1000.0  # Should use metadata.start_time
    
    def test_agent_execution_context_timestamp_fallback(self):
        """Test AgentExecutionContext timestamp when no start_time."""
        before_time = time.time()
        context = AgentExecutionContext()
        after_time = time.time()
        
        assert before_time <= context.timestamp <= after_time
        assert context.metadata.start_time is None  # Should not be set automatically
    
    def test_update_timestamp(self):
        """Test update_timestamp method."""
        context = AgentExecutionContext()
        original_timestamp = context.timestamp
        
        time.sleep(0.01)  # Small delay
        before_update = time.time()
        context.update_timestamp()
        after_update = time.time()
        
        assert context.timestamp != original_timestamp
        assert before_update <= context.timestamp <= after_update
        
        # Should also set metadata.start_time if not set
        assert context.metadata.start_time == context.timestamp
    
    def test_update_timestamp_preserves_existing_start_time(self):
        """Test update_timestamp preserves existing start_time."""
        metadata = ExecutionMetadata(start_time=1000.0)
        context = AgentExecutionContext(metadata=metadata)
        
        context.update_timestamp()
        
        # timestamp should be updated but start_time should remain
        assert context.timestamp != 1000.0
        assert context.metadata.start_time == 1000.0


class TestExecutionContextEdgeCases(SSotBaseTestCase):
    """Test ExecutionContext edge cases and error conditions."""
    
    def test_execution_context_with_none_metadata(self):
        """Test ExecutionContext handles None metadata gracefully."""
        context = ExecutionContext(metadata=None)
        
        assert context.metadata is not None
        assert isinstance(context.metadata, ExecutionMetadata)
    
    def test_execution_context_with_empty_execution_id(self):
        """Test ExecutionContext handles empty execution_id."""
        context = ExecutionContext(execution_id="")
        
        # Empty string should be replaced with generated UUID
        assert context.execution_id != ""
        assert len(context.execution_id) > 10
    
    def test_multiple_status_transitions(self):
        """Test multiple status transitions in sequence."""
        context = ExecutionContext()
        
        # Test valid sequence
        context.start_execution()
        assert context.status == ExecutionStatus.RUNNING
        
        context.complete_execution(success=True)
        assert context.status == ExecutionStatus.COMPLETED
        
        # Test transitions from completed state
        context.fail_execution(Exception("Late error"))
        assert context.status == ExecutionStatus.FAILED  # Should override completed
    
    def test_resource_usage_with_negative_values(self):
        """Test resource usage handles negative values."""
        context = ExecutionContext()
        
        # Test negative incremental values
        context.update_resource_usage(network_requests=-1)
        assert context.resource_usage.network_requests == -1
        
        context.update_resource_usage(network_requests=5)
        assert context.resource_usage.network_requests == 4  # -1 + 5
        
        # Test negative absolute values
        context.update_resource_usage(cpu_time=-1.0, memory_peak=-1024)
        assert context.resource_usage.cpu_time == -1.0
        assert context.resource_usage.memory_peak == -1024
    
    def test_logs_with_special_characters(self):
        """Test log handling with special characters."""
        context = ExecutionContext()
        
        # Test various special characters and unicode
        test_messages = [
            "Message with unicode: 你好",
            "Message with emoji: 🚀",
            "Message with newlines:\nLine 2\nLine 3",
            "Message with quotes: 'single' and \"double\"",
            "Message with backslashes: \\n \\t \\r",
        ]
        
        for message in test_messages:
            context._add_log(message)
        
        logs = context.get_logs()
        assert len(logs) == len(test_messages)
        
        for i, expected_message in enumerate(test_messages):
            assert expected_message in logs[i]
    
    def test_context_data_with_complex_objects(self):
        """Test context data storage with complex objects."""
        context = ExecutionContext()
        
        # Test various object types
        test_data = {
            "list": [1, 2, 3, {"nested": "value"}],
            "dict": {"key1": "value1", "key2": {"nested": {"deep": "value"}}},
            "tuple": (1, 2, "three"),
            "set": {1, 2, 3},
            "none": None,
            "bool": True,
            "function": lambda x: x + 1,
        }
        
        for key, value in test_data.items():
            context.set_context_data(key, value)
        
        # Verify all data is retrievable
        for key, expected_value in test_data.items():
            actual_value = context.get_context_data(key)
            if key == "function":
                # Functions should be callable
                assert callable(actual_value)
                assert actual_value(5) == 6
            elif key == "set":
                # Sets should be preserved (though order may vary)
                assert actual_value == expected_value
            else:
                assert actual_value == expected_value
    
    def test_execution_context_memory_efficiency(self):
        """Test ExecutionContext memory usage remains reasonable."""
        contexts = []
        
        # Create many contexts and verify memory usage doesn't explode
        for i in range(1000):
            context = ExecutionContext()
            context.set_context_data("index", i)
            context.update_resource_usage(network_requests=i)
            contexts.append(context)
        
        # Basic sanity check - we should be able to create 1000 contexts
        assert len(contexts) == 1000
        
        # Verify they all work correctly
        for i, context in enumerate(contexts):
            assert context.get_context_data("index") == i
            assert context.resource_usage.network_requests == i
        
        self.record_metric("contexts_created_for_memory_test", len(contexts))


class TestExecutionContextPerformance(SSotBaseTestCase):
    """Test ExecutionContext performance characteristics."""
    
    def test_context_creation_performance(self):
        """Test ExecutionContext creation performance."""
        start_time = time.time()
        
        contexts = []
        for _ in range(1000):
            context = ExecutionContext()
            contexts.append(context)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should be able to create 1000 contexts quickly
        assert creation_time < 1.0  # Less than 1 second
        assert len(contexts) == 1000
        
        # All contexts should have unique IDs
        ids = [ctx.execution_id for ctx in contexts]
        assert len(set(ids)) == len(ids)
        
        self.record_metric("context_creation_time_1000", creation_time)
        self.record_metric("contexts_per_second", 1000 / creation_time)
    
    def test_context_data_operations_performance(self):
        """Test context data operations performance."""
        context = ExecutionContext()
        
        # Test setting performance
        start_time = time.time()
        for i in range(1000):
            context.set_context_data(f"key_{i}", f"value_{i}")
        set_time = time.time() - start_time
        
        # Test getting performance
        start_time = time.time()
        for i in range(1000):
            value = context.get_context_data(f"key_{i}")
            assert value == f"value_{i}"
        get_time = time.time() - start_time
        
        # Operations should be fast
        assert set_time < 0.1  # Less than 100ms
        assert get_time < 0.1  # Less than 100ms
        
        self.record_metric("context_data_set_time_1000", set_time)
        self.record_metric("context_data_get_time_1000", get_time)
    
    def test_resource_usage_update_performance(self):
        """Test resource usage update performance."""
        context = ExecutionContext()
        
        start_time = time.time()
        for i in range(1000):
            context.update_resource_usage(
                network_requests=1,
                database_queries=1,
                llm_tokens=10,
                cpu_time=0.01,
                memory_peak=1024
            )
        update_time = time.time() - start_time
        
        # Updates should be fast
        assert update_time < 0.1  # Less than 100ms
        
        # Verify final state
        assert context.resource_usage.network_requests == 1000
        assert context.resource_usage.database_queries == 1000
        assert context.resource_usage.llm_tokens == 10000
        
        self.record_metric("resource_usage_update_time_1000", update_time)
        self.record_metric("resource_updates_per_second", 1000 / update_time)


# Test execution entry point
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])