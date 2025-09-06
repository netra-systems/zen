# REMOVED_SYNTAX_ERROR: '''Core Background Task Security Tests

# REMOVED_SYNTAX_ERROR: SECURITY CRITICAL: These tests validate the core security implementations
# REMOVED_SYNTAX_ERROR: for background task user context isolation.

# REMOVED_SYNTAX_ERROR: Focuses on testing our security implementations without external dependencies.
# REMOVED_SYNTAX_ERROR: '''

import asyncio
import pytest
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment

# Import our security implementations
# REMOVED_SYNTAX_ERROR: from netra_backend.app.services.secure_background_task_manager import ( )
SecureBackgroundTaskManager,
SecureBackgroundTask,
TaskStatus

# REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import ( )
UserExecutionContext,
InvalidContextError

# REMOVED_SYNTAX_ERROR: from shared.context_serialization import ( )
SecureContextSerializer,
ContextSerializationError,
ContextIntegrityError,
create_secure_task_payload,
extract_context_from_task_payload

# REMOVED_SYNTAX_ERROR: from shared.background_task_security_validator import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
BackgroundTaskSecurityValidator,
SecurityViolationType,
security_required,
validate_background_task


# Test fixtures

# REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_user_context() -> UserExecutionContext:
    # REMOVED_SYNTAX_ERROR: """Create a test UserExecutionContext."""
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_" + str(uuid.uuid4())
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_user_context_2() -> UserExecutionContext:
    # REMOVED_SYNTAX_ERROR: """Create a second test UserExecutionContext for isolation tests."""
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user_999",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_888",
    # REMOVED_SYNTAX_ERROR: run_id="run_777",
    # REMOVED_SYNTAX_ERROR: request_id="req_" + str(uuid.uuid4())
    


# REMOVED_SYNTAX_ERROR: class TestSecureBackgroundTaskManager:
    # REMOVED_SYNTAX_ERROR: """Test security for secure background task manager."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_task_manager_requires_user_context(self, test_user_context):
        # REMOVED_SYNTAX_ERROR: """Test that task manager enforces user context requirement."""
        # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

        # Removed problematic line: async def test_task():
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return "test_result"

            # Should fail without user context
            # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError, match="requires UserExecutionContext"):
                # REMOVED_SYNTAX_ERROR: await manager.start_task("test_task", "Test Task", test_task)

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_task_manager_user_context_propagation(self, test_user_context):
                    # REMOVED_SYNTAX_ERROR: """Test that user context is properly propagated to tasks."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

                    # REMOVED_SYNTAX_ERROR: received_context = None

                    # Removed problematic line: async def test_task(user_context: Optional[UserExecutionContext] = None):
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: nonlocal received_context
                        # REMOVED_SYNTAX_ERROR: received_context = user_context
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                        # REMOVED_SYNTAX_ERROR: return "test_result"

                        # Start task with context
                        # REMOVED_SYNTAX_ERROR: task = await manager.start_task("test_task", "Test Task", test_task, user_context=test_user_context)

                        # Wait for completion
                        # REMOVED_SYNTAX_ERROR: result = await manager.wait_for_task("test_task", user_context=test_user_context)

                        # REMOVED_SYNTAX_ERROR: assert result == "test_result"
                        # REMOVED_SYNTAX_ERROR: assert received_context is not None
                        # REMOVED_SYNTAX_ERROR: assert received_context.user_id == test_user_context.user_id

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_task_manager_user_isolation(self, test_user_context, test_user_context_2):
                            # REMOVED_SYNTAX_ERROR: """Test that users cannot access each other's tasks."""
                            # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

                            # Removed problematic line: async def test_task():
                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                                # REMOVED_SYNTAX_ERROR: return "test_result"

                                # Start task for user 1
                                # REMOVED_SYNTAX_ERROR: task1 = await manager.start_task("user1_task", "User 1 Task", test_task, user_context=test_user_context)

                                # User 2 should not be able to access user 1's task
                                # REMOVED_SYNTAX_ERROR: task_access = manager.get_task("user1_task", user_context=test_user_context_2)
                                # REMOVED_SYNTAX_ERROR: assert task_access is None

                                # User 1 should be able to access their own task
                                # REMOVED_SYNTAX_ERROR: task_access = manager.get_task("user1_task", user_context=test_user_context)
                                # REMOVED_SYNTAX_ERROR: assert task_access is not None

# REMOVED_SYNTAX_ERROR: def test_task_manager_list_tasks_isolation(self, test_user_context, test_user_context_2):
    # REMOVED_SYNTAX_ERROR: """Test that task listing is properly isolated by user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

    # Create tasks for different users
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager.start_task("user1_task", "User 1 Task", lambda x: None "result1", user_context=test_user_context))
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager.start_task("user2_task", "User 2 Task", lambda x: None "result2", user_context=test_user_context_2))

    # User 1 should only see their tasks
    # REMOVED_SYNTAX_ERROR: user1_tasks = manager.list_tasks(user_context=test_user_context)
    # REMOVED_SYNTAX_ERROR: assert len(user1_tasks) == 1
    # REMOVED_SYNTAX_ERROR: assert user1_tasks[0].task_id == "user1_task"

    # User 2 should only see their tasks
    # REMOVED_SYNTAX_ERROR: user2_tasks = manager.list_tasks(user_context=test_user_context_2)
    # REMOVED_SYNTAX_ERROR: assert len(user2_tasks) == 1
    # REMOVED_SYNTAX_ERROR: assert user2_tasks[0].task_id == "user2_task"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_task_manager_metrics_isolation(self, test_user_context, test_user_context_2):
        # REMOVED_SYNTAX_ERROR: """Test that task metrics don't leak user information."""
        # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

        # Removed problematic line: async def test_task():
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Brief delay
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return "completed"

            # Start tasks for both users
            # REMOVED_SYNTAX_ERROR: await manager.start_task("task1", "Task 1", test_task, user_context=test_user_context)
            # REMOVED_SYNTAX_ERROR: await manager.start_task("task2", "Task 2", test_task, user_context=test_user_context_2)

            # Get metrics
            # REMOVED_SYNTAX_ERROR: metrics = manager.get_metrics()

            # Metrics should show aggregate data without user details
            # REMOVED_SYNTAX_ERROR: assert metrics['total_tasks'] >= 2
            # REMOVED_SYNTAX_ERROR: assert 'user_ids' not in metrics  # Should not expose user IDs
            # REMOVED_SYNTAX_ERROR: assert 'task_details' not in metrics  # Should not expose task details


# REMOVED_SYNTAX_ERROR: class TestContextSerialization:
    # REMOVED_SYNTAX_ERROR: """Test security for context serialization."""

# REMOVED_SYNTAX_ERROR: def test_context_serialization_integrity(self, test_user_context):
    # REMOVED_SYNTAX_ERROR: """Test that context serialization maintains integrity."""
    # REMOVED_SYNTAX_ERROR: serializer = SecureContextSerializer()

    # Serialize context
    # REMOVED_SYNTAX_ERROR: serialized = serializer.serialize_context(test_user_context)

    # Should be base64 encoded string
    # REMOVED_SYNTAX_ERROR: assert isinstance(serialized, str)
    # REMOVED_SYNTAX_ERROR: assert len(serialized) > 0

    # Deserialize context
    # REMOVED_SYNTAX_ERROR: deserialized = serializer.deserialize_context(serialized)

    # Verify integrity
    # REMOVED_SYNTAX_ERROR: assert deserialized.user_id == test_user_context.user_id
    # REMOVED_SYNTAX_ERROR: assert deserialized.thread_id == test_user_context.thread_id
    # REMOVED_SYNTAX_ERROR: assert deserialized.run_id == test_user_context.run_id
    # REMOVED_SYNTAX_ERROR: assert deserialized.request_id == test_user_context.request_id

# REMOVED_SYNTAX_ERROR: def test_context_serialization_tampering_detection(self, test_user_context):
    # REMOVED_SYNTAX_ERROR: """Test that context serialization detects tampering."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: serializer = SecureContextSerializer()

    # Serialize context
    # REMOVED_SYNTAX_ERROR: serialized = serializer.serialize_context(test_user_context)

    # Tamper with serialized data
    # REMOVED_SYNTAX_ERROR: tampered = serialized[:-10] + "TAMPERED=="

    # Should fail to deserialize
    # REMOVED_SYNTAX_ERROR: with pytest.raises((ContextSerializationError, json.JSONDecodeError, Exception)):
        # REMOVED_SYNTAX_ERROR: serializer.deserialize_context(tampered)

# REMOVED_SYNTAX_ERROR: def test_context_serialization_cross_user_prevention(self, test_user_context, test_user_context_2):
    # REMOVED_SYNTAX_ERROR: """Test that serialized contexts cannot be mixed between users."""
    # REMOVED_SYNTAX_ERROR: serializer = SecureContextSerializer()

    # Serialize both contexts
    # REMOVED_SYNTAX_ERROR: serialized1 = serializer.serialize_context(test_user_context)
    # REMOVED_SYNTAX_ERROR: serialized2 = serializer.serialize_context(test_user_context_2)

    # Should produce different serialized strings
    # REMOVED_SYNTAX_ERROR: assert serialized1 != serialized2

    # Deserialize
    # REMOVED_SYNTAX_ERROR: deserialized1 = serializer.deserialize_context(serialized1)
    # REMOVED_SYNTAX_ERROR: deserialized2 = serializer.deserialize_context(serialized2)

    # Verify no cross-contamination
    # REMOVED_SYNTAX_ERROR: assert deserialized1.user_id == test_user_context.user_id
    # REMOVED_SYNTAX_ERROR: assert deserialized2.user_id == test_user_context_2.user_id
    # REMOVED_SYNTAX_ERROR: assert deserialized1.user_id != deserialized2.user_id

# REMOVED_SYNTAX_ERROR: def test_secure_task_payload_creation(self, test_user_context):
    # REMOVED_SYNTAX_ERROR: """Test secure task payload creation and extraction."""
    # REMOVED_SYNTAX_ERROR: pass
    # Create secure payload
    # REMOVED_SYNTAX_ERROR: payload = create_secure_task_payload( )
    # REMOVED_SYNTAX_ERROR: context=test_user_context,
    # REMOVED_SYNTAX_ERROR: task_name="test_analytics",
    # REMOVED_SYNTAX_ERROR: task_parameters={"data": "test_data", "user_specific": True}
    

    # Verify payload structure
    # REMOVED_SYNTAX_ERROR: assert 'task_name' in payload
    # REMOVED_SYNTAX_ERROR: assert 'task_parameters' in payload
    # REMOVED_SYNTAX_ERROR: assert 'user_context' in payload
    # REMOVED_SYNTAX_ERROR: assert 'created_at' in payload
    # REMOVED_SYNTAX_ERROR: assert 'security_version' in payload

    # Extract from payload
    # REMOVED_SYNTAX_ERROR: task_name, task_params, extracted_context = extract_context_from_task_payload(payload)

    # Verify extraction
    # REMOVED_SYNTAX_ERROR: assert task_name == "test_analytics"
    # REMOVED_SYNTAX_ERROR: assert task_params['data'] == "test_data"
    # REMOVED_SYNTAX_ERROR: assert extracted_context.user_id == test_user_context.user_id


# REMOVED_SYNTAX_ERROR: class TestSecurityValidator:
    # REMOVED_SYNTAX_ERROR: """Test security validator functionality."""

# REMOVED_SYNTAX_ERROR: def test_validator_detects_missing_context(self):
    # REMOVED_SYNTAX_ERROR: """Test that validator detects missing user context."""
    # REMOVED_SYNTAX_ERROR: validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
    # REMOVED_SYNTAX_ERROR: validator.clear_violations()  # Clear any previous violations

    # Should detect violation
    # REMOVED_SYNTAX_ERROR: result = validator.validate_background_task_context( )
    # REMOVED_SYNTAX_ERROR: task_name="test_task",
    # REMOVED_SYNTAX_ERROR: task_id="test_123",
    # REMOVED_SYNTAX_ERROR: user_context=None,
    # REMOVED_SYNTAX_ERROR: require_context=True
    

    # REMOVED_SYNTAX_ERROR: assert result is False
    # REMOVED_SYNTAX_ERROR: assert len(validator.violations) == 1
    # REMOVED_SYNTAX_ERROR: assert validator.violations[0].violation_type == SecurityViolationType.MISSING_CONTEXT

# REMOVED_SYNTAX_ERROR: def test_validator_strict_mode(self):
    # REMOVED_SYNTAX_ERROR: """Test that validator raises exceptions in strict mode."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)

    # Should raise exception
    # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError):
        # REMOVED_SYNTAX_ERROR: validator.validate_background_task_context( )
        # REMOVED_SYNTAX_ERROR: task_name="test_task",
        # REMOVED_SYNTAX_ERROR: task_id="test_123",
        # REMOVED_SYNTAX_ERROR: user_context=None,
        # REMOVED_SYNTAX_ERROR: require_context=True
        

# REMOVED_SYNTAX_ERROR: def test_validator_whitelisting(self):
    # REMOVED_SYNTAX_ERROR: """Test that validator respects whitelisted tasks."""
    # REMOVED_SYNTAX_ERROR: validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)

    # Whitelist task
    # REMOVED_SYNTAX_ERROR: validator.whitelist_task("system_task", "System maintenance task")

    # Should pass even without context
    # REMOVED_SYNTAX_ERROR: result = validator.validate_background_task_context( )
    # REMOVED_SYNTAX_ERROR: task_name="system_task",
    # REMOVED_SYNTAX_ERROR: task_id="sys_123",
    # REMOVED_SYNTAX_ERROR: user_context=None,
    # REMOVED_SYNTAX_ERROR: require_context=False
    

    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def test_validator_context_mismatch_detection(self, test_user_context):
    # REMOVED_SYNTAX_ERROR: """Test that validator detects user context mismatches."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
    # REMOVED_SYNTAX_ERROR: validator.clear_violations()

    # Should detect mismatch
    # REMOVED_SYNTAX_ERROR: result = validator.validate_background_task_context( )
    # REMOVED_SYNTAX_ERROR: task_name="user_task",
    # REMOVED_SYNTAX_ERROR: task_id="task_123",
    # REMOVED_SYNTAX_ERROR: user_context=test_user_context,
    # REMOVED_SYNTAX_ERROR: require_context=True,
    # REMOVED_SYNTAX_ERROR: expected_user_id="different_user_id"
    

    # REMOVED_SYNTAX_ERROR: assert result is False
    # REMOVED_SYNTAX_ERROR: assert len(validator.violations) == 1
    # REMOVED_SYNTAX_ERROR: assert validator.violations[0].violation_type == SecurityViolationType.CONTEXT_MISMATCH

# REMOVED_SYNTAX_ERROR: def test_security_required_decorator(self, test_user_context):
    # REMOVED_SYNTAX_ERROR: """Test that security_required decorator works correctly."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: async def test_task(user_context: Optional[UserExecutionContext] = None):
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return "formatted_string"

        # Should work with context
        # REMOVED_SYNTAX_ERROR: result = asyncio.run(test_task(user_context=test_user_context))
        # REMOVED_SYNTAX_ERROR: assert result == "formatted_string"

        # Should fail without context (strict mode is on by default)
        # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError):
            # REMOVED_SYNTAX_ERROR: asyncio.run(test_task())

# REMOVED_SYNTAX_ERROR: def test_validator_metrics_and_reporting(self, test_user_context):
    # REMOVED_SYNTAX_ERROR: """Test validator metrics and reporting functionality."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
    # REMOVED_SYNTAX_ERROR: validator.clear_violations()

    # Create some violations
    # REMOVED_SYNTAX_ERROR: validator.validate_background_task_context("task1", "id1", None, True)
    # REMOVED_SYNTAX_ERROR: validator.validate_background_task_context("task2", "id2", test_user_context, True, "wrong_user")

    # Get summary
    # REMOVED_SYNTAX_ERROR: summary = validator.get_violation_summary()

    # REMOVED_SYNTAX_ERROR: assert summary['total_violations'] == 2
    # REMOVED_SYNTAX_ERROR: assert SecurityViolationType.MISSING_CONTEXT in summary['violation_types']
    # REMOVED_SYNTAX_ERROR: assert SecurityViolationType.CONTEXT_MISMATCH in summary['violation_types']

    # Generate report
    # REMOVED_SYNTAX_ERROR: report = validator.generate_security_report()
    # REMOVED_SYNTAX_ERROR: assert "BACKGROUND TASK SECURITY REPORT" in report
    # REMOVED_SYNTAX_ERROR: assert "Total Violations: 2" in report


# REMOVED_SYNTAX_ERROR: class TestCrossUserDataLeakagePrevention:
    # REMOVED_SYNTAX_ERROR: """Test prevention of cross-user data leakage in background tasks."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_background_task_data_isolation(self, test_user_context, test_user_context_2):
        # REMOVED_SYNTAX_ERROR: """Test that background tasks maintain data isolation between users."""
        # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

        # Store to simulate user-specific data
        # REMOVED_SYNTAX_ERROR: user_data = {}

# REMOVED_SYNTAX_ERROR: async def user_specific_task(data_key: str, user_context: Optional[UserExecutionContext] = None):
    # REMOVED_SYNTAX_ERROR: if user_context:
        # Store data with user prefix to simulate isolation
        # REMOVED_SYNTAX_ERROR: storage_key = "formatted_string"
        # REMOVED_SYNTAX_ERROR: user_data[storage_key] = "formatted_string"
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return storage_key
        # REMOVED_SYNTAX_ERROR: return None

        # Start tasks for different users using proper async functions
# REMOVED_SYNTAX_ERROR: async def task1_func():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return await user_specific_task("secret_data", user_context=test_user_context)

# REMOVED_SYNTAX_ERROR: async def task2_func():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return await user_specific_task("secret_data", user_context=test_user_context_2)

    # REMOVED_SYNTAX_ERROR: task1 = await manager.start_task( )
    # REMOVED_SYNTAX_ERROR: "data_task_1", "User 1 Data Task",
    # REMOVED_SYNTAX_ERROR: task1_func,
    # REMOVED_SYNTAX_ERROR: user_context=test_user_context
    

    # REMOVED_SYNTAX_ERROR: task2 = await manager.start_task( )
    # REMOVED_SYNTAX_ERROR: "data_task_2", "User 2 Data Task",
    # REMOVED_SYNTAX_ERROR: task2_func,
    # REMOVED_SYNTAX_ERROR: user_context=test_user_context_2
    

    # Wait for completion
    # REMOVED_SYNTAX_ERROR: result1 = await manager.wait_for_task("data_task_1", user_context=test_user_context)
    # REMOVED_SYNTAX_ERROR: result2 = await manager.wait_for_task("data_task_2", user_context=test_user_context_2)

    # Verify data isolation
    # REMOVED_SYNTAX_ERROR: assert result1 == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert result2 == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert result1 != result2

    # Verify stored data is isolated
    # REMOVED_SYNTAX_ERROR: assert user_data[result1] == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert user_data[result2] == "formatted_string"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_concurrent_user_task_isolation(self, test_user_context, test_user_context_2):
        # REMOVED_SYNTAX_ERROR: """Test isolation when tasks run concurrently."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: manager = SecureBackgroundTaskManager(enforce_user_context=True)

        # REMOVED_SYNTAX_ERROR: results = {}

# REMOVED_SYNTAX_ERROR: async def concurrent_task(user_id: str, user_context: Optional[UserExecutionContext] = None):
    # REMOVED_SYNTAX_ERROR: pass
    # Simulate some processing time
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)

    # Store result with user validation
    # REMOVED_SYNTAX_ERROR: if user_context and user_context.user_id == user_id:
        # REMOVED_SYNTAX_ERROR: results[user_context.user_id] = "formatted_string"
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return "formatted_string"
        # REMOVED_SYNTAX_ERROR: else:
            # REMOVED_SYNTAX_ERROR: return "failed_validation"

            # Start concurrent tasks using proper async functions
# REMOVED_SYNTAX_ERROR: async def concurrent_task1():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return await concurrent_task(test_user_context.user_id, user_context=test_user_context)

# REMOVED_SYNTAX_ERROR: async def concurrent_task2():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return await concurrent_task(test_user_context_2.user_id, user_context=test_user_context_2)

    # REMOVED_SYNTAX_ERROR: task1 = await manager.start_task( )
    # REMOVED_SYNTAX_ERROR: "concurrent_1", "Concurrent Task 1",
    # REMOVED_SYNTAX_ERROR: concurrent_task1,
    # REMOVED_SYNTAX_ERROR: user_context=test_user_context
    

    # REMOVED_SYNTAX_ERROR: task2 = await manager.start_task( )
    # REMOVED_SYNTAX_ERROR: "concurrent_2", "Concurrent Task 2",
    # REMOVED_SYNTAX_ERROR: concurrent_task2,
    # REMOVED_SYNTAX_ERROR: user_context=test_user_context_2
    

    # Wait for both to complete concurrently
    # REMOVED_SYNTAX_ERROR: result1, result2 = await asyncio.gather( )
    # REMOVED_SYNTAX_ERROR: manager.wait_for_task("concurrent_1", user_context=test_user_context),
    # REMOVED_SYNTAX_ERROR: manager.wait_for_task("concurrent_2", user_context=test_user_context_2)
    

    # Verify isolation
    # REMOVED_SYNTAX_ERROR: assert result1 == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert result2 == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert results[test_user_context.user_id] == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert results[test_user_context_2.user_id] == "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestIntegrationSecurity:
    # REMOVED_SYNTAX_ERROR: """Integration tests for end-to-end security."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_end_to_end_context_propagation(self, test_user_context):
        # REMOVED_SYNTAX_ERROR: """Test end-to-end context propagation through multiple layers."""

        # Setup secure components
        # REMOVED_SYNTAX_ERROR: task_manager = SecureBackgroundTaskManager(enforce_user_context=True)
        # REMOVED_SYNTAX_ERROR: validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)
        # REMOVED_SYNTAX_ERROR: serializer = SecureContextSerializer()

        # Simulate a complex workflow
        # REMOVED_SYNTAX_ERROR: workflow_results = []

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def analytics_task(event_data: Dict[str, Any], user_context: Optional[UserExecutionContext] = None):
    # Process analytics
    # REMOVED_SYNTAX_ERROR: workflow_results.append({ ))
    # REMOVED_SYNTAX_ERROR: 'step': 'analytics',
    # REMOVED_SYNTAX_ERROR: 'user_id': user_context.user_id,
    # REMOVED_SYNTAX_ERROR: 'event_data': event_data
    

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def report_task(analytics_result: str, user_context: Optional[UserExecutionContext] = None):
    # Generate report
    # REMOVED_SYNTAX_ERROR: workflow_results.append({ ))
    # REMOVED_SYNTAX_ERROR: 'step': 'report',
    # REMOVED_SYNTAX_ERROR: 'user_id': user_context.user_id,
    # REMOVED_SYNTAX_ERROR: 'analytics_result': analytics_result
    

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # Execute workflow
    # REMOVED_SYNTAX_ERROR: event_data = {"prompt": "test message", "model": "gpt-4"}

    # Step 1: Analytics processing
    # REMOVED_SYNTAX_ERROR: analytics_result = await analytics_task(event_data, user_context=test_user_context)

    # Step 2: Report generation
    # REMOVED_SYNTAX_ERROR: report_result = await report_task(analytics_result, user_context=test_user_context)

    # Verify results
    # REMOVED_SYNTAX_ERROR: assert len(workflow_results) == 2
    # REMOVED_SYNTAX_ERROR: assert workflow_results[0]['user_id'] == test_user_context.user_id
    # REMOVED_SYNTAX_ERROR: assert workflow_results[1]['user_id'] == test_user_context.user_id
    # REMOVED_SYNTAX_ERROR: assert analytics_result == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert report_result == "formatted_string"

    # Verify no violations
    # REMOVED_SYNTAX_ERROR: assert len(validator.violations) == 0


    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s"])
        # REMOVED_SYNTAX_ERROR: pass