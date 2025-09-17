'''Core Background Task Security Tests

SECURITY CRITICAL: These tests validate the core security implementations
for background task user context isolation.

Focuses on testing our security implementations without external dependencies.
'''

import asyncio
import pytest
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment

# Import our security implementations
from netra_backend.app.services.secure_background_task_manager import ( )
SecureBackgroundTaskManager,
SecureBackgroundTask,
TaskStatus

from netra_backend.app.services.user_execution_context import ( )
UserExecutionContext,
InvalidContextError

from shared.context_serialization import ( )
SecureContextSerializer,
ContextSerializationError,
ContextIntegrityError,
create_secure_task_payload,
extract_context_from_task_payload

from shared.background_task_security_validator import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
BackgroundTaskSecurityValidator,
SecurityViolationType,
security_required,
validate_background_task


# Test fixtures

@pytest.fixture
def test_user_context() -> UserExecutionContext:
"""Create a test UserExecutionContext."""
return UserExecutionContext.from_request( )
user_id="user_123",
thread_id="thread_456",
run_id="run_789",
request_id="req_" + str(uuid.uuid4())
    

@pytest.fixture
def test_user_context_2() -> UserExecutionContext:
"""Create a second test UserExecutionContext for isolation tests."""
return UserExecutionContext.from_request( )
user_id="user_999",
thread_id="thread_888",
run_id="run_777",
request_id="req_" + str(uuid.uuid4())
    


class TestSecureBackgroundTaskManager:
        """Test security for secure background task manager."""

@pytest.mark.asyncio
    async def test_task_manager_requires_user_context(self, test_user_context):
"""Test that task manager enforces user context requirement."""
manager = SecureBackgroundTaskManager(enforce_user_context=True)

    async def test_task():
await asyncio.sleep(0)
return "test_result"

            # Should fail without user context
with pytest.raises(InvalidContextError, match="requires UserExecutionContext"):
await manager.start_task("test_task", "Test Task", test_task)

@pytest.mark.asyncio
    async def test_task_manager_user_context_propagation(self, test_user_context):
"""Test that user context is properly propagated to tasks."""
pass
manager = SecureBackgroundTaskManager(enforce_user_context=True)

received_context = None

    async def test_task(user_context:
pass
nonlocal received_context
received_context = user_context
await asyncio.sleep(0)
return "test_result"

                        # Start task with context
task = await manager.start_task("test_task", "Test Task", test_task, user_context=test_user_context)

                        # Wait for completion
result = await manager.wait_for_task("test_task", user_context=test_user_context)

assert result == "test_result"
assert received_context is not None
assert received_context.user_id == test_user_context.user_id

@pytest.mark.asyncio
    async def test_task_manager_user_isolation(self, test_user_context, test_user_context_2):
"""Test that users cannot access each other's tasks."""
manager = SecureBackgroundTaskManager(enforce_user_context=True)

    async def test_task():
await asyncio.sleep(0)
return "test_result"

                                # Start task for user 1
task1 = await manager.start_task("user1_task", "User 1 Task", test_task, user_context=test_user_context)

                                # User 2 should not be able to access user 1's task
task_access = manager.get_task("user1_task", user_context=test_user_context_2)
assert task_access is None

                                # User 1 should be able to access their own task
task_access = manager.get_task("user1_task", user_context=test_user_context)
assert task_access is not None

def test_task_manager_list_tasks_isolation(self, test_user_context, test_user_context_2):
"""Test that task listing is properly isolated by user."""
pass
manager = SecureBackgroundTaskManager(enforce_user_context=True)

    # Create tasks for different users
asyncio.run(manager.start_task("user1_task", "User 1 Task", lambda x: None "result1", user_context=test_user_context))
asyncio.run(manager.start_task("user2_task", "User 2 Task", lambda x: None "result2", user_context=test_user_context_2))

    # User 1 should only see their tasks
user1_tasks = manager.list_tasks(user_context=test_user_context)
assert len(user1_tasks) == 1
assert user1_tasks[0].task_id == "user1_task"

    # User 2 should only see their tasks
user2_tasks = manager.list_tasks(user_context=test_user_context_2)
assert len(user2_tasks) == 1
assert user2_tasks[0].task_id == "user2_task"

@pytest.mark.asyncio
    async def test_task_manager_metrics_isolation(self, test_user_context, test_user_context_2):
"""Test that task metrics don't leak user information."""
manager = SecureBackgroundTaskManager(enforce_user_context=True)

    async def test_task():
await asyncio.sleep(0.01)  # Brief delay
await asyncio.sleep(0)
return "completed"

            # Start tasks for both users
await manager.start_task("task1", "Task 1", test_task, user_context=test_user_context)
await manager.start_task("task2", "Task 2", test_task, user_context=test_user_context_2)

            # Get metrics
metrics = manager.get_metrics()

            # Metrics should show aggregate data without user details
assert metrics['total_tasks'] >= 2
assert 'user_ids' not in metrics  # Should not expose user IDs
assert 'task_details' not in metrics  # Should not expose task details


class TestContextSerialization:
    """Test security for context serialization."""

    def test_context_serialization_integrity(self, test_user_context):
        """Test that context serialization maintains integrity."""
        serializer = SecureContextSerializer()

    # Serialize context
        serialized = serializer.serialize_context(test_user_context)

    # Should be base64 encoded string
        assert isinstance(serialized, str)
        assert len(serialized) > 0

    # Deserialize context
        deserialized = serializer.deserialize_context(serialized)

    # Verify integrity
        assert deserialized.user_id == test_user_context.user_id
        assert deserialized.thread_id == test_user_context.thread_id
        assert deserialized.run_id == test_user_context.run_id
        assert deserialized.request_id == test_user_context.request_id

    def test_context_serialization_tampering_detection(self, test_user_context):
        """Test that context serialization detects tampering."""
        pass
        serializer = SecureContextSerializer()

    # Serialize context
        serialized = serializer.serialize_context(test_user_context)

    # Tamper with serialized data
        tampered = serialized[:-10] + "TAMPERED=="

    # Should fail to deserialize
        with pytest.raises((ContextSerializationError, json.JSONDecodeError, Exception)):
        serializer.deserialize_context(tampered)

    def test_context_serialization_cross_user_prevention(self, test_user_context, test_user_context_2):
        """Test that serialized contexts cannot be mixed between users."""
        serializer = SecureContextSerializer()

    # Serialize both contexts
        serialized1 = serializer.serialize_context(test_user_context)
        serialized2 = serializer.serialize_context(test_user_context_2)

    # Should produce different serialized strings
        assert serialized1 != serialized2

    # Deserialize
        deserialized1 = serializer.deserialize_context(serialized1)
        deserialized2 = serializer.deserialize_context(serialized2)

    # Verify no cross-contamination
        assert deserialized1.user_id == test_user_context.user_id
        assert deserialized2.user_id == test_user_context_2.user_id
        assert deserialized1.user_id != deserialized2.user_id

    def test_secure_task_payload_creation(self, test_user_context):
        """Test secure task payload creation and extraction."""
        pass
    # Create secure payload
        payload = create_secure_task_payload( )
        context=test_user_context,
        task_name="test_analytics",
        task_parameters={"data": "test_data", "user_specific": True}
    

    # Verify payload structure
        assert 'task_name' in payload
        assert 'task_parameters' in payload
        assert 'user_context' in payload
        assert 'created_at' in payload
        assert 'security_version' in payload

    Extract from payload
        task_name, task_params, extracted_context = extract_context_from_task_payload(payload)

    # Verify extraction
        assert task_name == "test_analytics"
        assert task_params['data'] == "test_data"
        assert extracted_context.user_id == test_user_context.user_id


class TestSecurityValidator:
        """Test security validator functionality."""

    def test_validator_detects_missing_context(self):
        """Test that validator detects missing user context."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        validator.clear_violations()  # Clear any previous violations

    # Should detect violation
        result = validator.validate_background_task_context( )
        task_name="test_task",
        task_id="test_123",
        user_context=None,
        require_context=True
    

        assert result is False
        assert len(validator.violations) == 1
        assert validator.violations[0].violation_type == SecurityViolationType.MISSING_CONTEXT

    def test_validator_strict_mode(self):
        """Test that validator raises exceptions in strict mode."""
        pass
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)

    # Should raise exception
        with pytest.raises(InvalidContextError):
        validator.validate_background_task_context( )
        task_name="test_task",
        task_id="test_123",
        user_context=None,
        require_context=True
        

    def test_validator_whitelisting(self):
        """Test that validator respects whitelisted tasks."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)

    # Whitelist task
        validator.whitelist_task("system_task", "System maintenance task")

    # Should pass even without context
        result = validator.validate_background_task_context( )
        task_name="system_task",
        task_id="sys_123",
        user_context=None,
        require_context=False
    

        assert result is True

    def test_validator_context_mismatch_detection(self, test_user_context):
        """Test that validator detects user context mismatches."""
        pass
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        validator.clear_violations()

    # Should detect mismatch
        result = validator.validate_background_task_context( )
        task_name="user_task",
        task_id="task_123",
        user_context=test_user_context,
        require_context=True,
        expected_user_id="different_user_id"
    

        assert result is False
        assert len(validator.violations) == 1
        assert validator.violations[0].violation_type == SecurityViolationType.CONTEXT_MISMATCH

    def test_security_required_decorator(self, test_user_context):
        """Test that security_required decorator works correctly."""

        # @pytest.fixture
    async def test_task(user_context:
        await asyncio.sleep(0)
        return ""

        # Should work with context
        result = asyncio.run(test_task(user_context=test_user_context))
        assert result == ""

        # Should fail without context (strict mode is on by default)
        with pytest.raises(InvalidContextError):
        asyncio.run(test_task())

    def test_validator_metrics_and_reporting(self, test_user_context):
        """Test validator metrics and reporting functionality."""
        pass
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        validator.clear_violations()

    # Create some violations
        validator.validate_background_task_context("task1", "id1", None, True)
        validator.validate_background_task_context("task2", "id2", test_user_context, True, "wrong_user")

    # Get summary
        summary = validator.get_violation_summary()

        assert summary['total_violations'] == 2
        assert SecurityViolationType.MISSING_CONTEXT in summary['violation_types']
        assert SecurityViolationType.CONTEXT_MISMATCH in summary['violation_types']

    # Generate report
        report = validator.generate_security_report()
        assert "BACKGROUND TASK SECURITY REPORT" in report
        assert "Total Violations: 2" in report


class TestCrossUserDataLeakagePrevention:
        """Test prevention of cross-user data leakage in background tasks."""

@pytest.mark.asyncio
    async def test_background_task_data_isolation(self, test_user_context, test_user_context_2):
"""Test that background tasks maintain data isolation between users."""
manager = SecureBackgroundTaskManager(enforce_user_context=True)

        # Store to simulate user-specific data
user_data = {}

async def user_specific_task(data_key: str, user_context: Optional[UserExecutionContext] = None):
if user_context:
        # Store data with user prefix to simulate isolation
storage_key = ""
user_data[storage_key] = ""
await asyncio.sleep(0)
return storage_key
return None

        # Start tasks for different users using proper async functions
async def task1_func():
await asyncio.sleep(0)
return await user_specific_task("secret_data", user_context=test_user_context)

async def task2_func():
await asyncio.sleep(0)
return await user_specific_task("secret_data", user_context=test_user_context_2)

task1 = await manager.start_task( )
"data_task_1", "User 1 Data Task",
task1_func,
user_context=test_user_context
    

task2 = await manager.start_task( )
"data_task_2", "User 2 Data Task",
task2_func,
user_context=test_user_context_2
    

    # Wait for completion
result1 = await manager.wait_for_task("data_task_1", user_context=test_user_context)
result2 = await manager.wait_for_task("data_task_2", user_context=test_user_context_2)

    # Verify data isolation
assert result1 == ""
assert result2 == ""
assert result1 != result2

    # Verify stored data is isolated
assert user_data[result1] == ""
assert user_data[result2] == ""

@pytest.mark.asyncio
    async def test_concurrent_user_task_isolation(self, test_user_context, test_user_context_2):
"""Test isolation when tasks run concurrently."""
pass
manager = SecureBackgroundTaskManager(enforce_user_context=True)

results = {}

async def concurrent_task(user_id: str, user_context: Optional[UserExecutionContext] = None):
pass
    # Simulate some processing time
await asyncio.sleep(0.01)

    # Store result with user validation
if user_context and user_context.user_id == user_id:
results[user_context.user_id] = ""
await asyncio.sleep(0)
return ""
else:
return "failed_validation"

            # Start concurrent tasks using proper async functions
async def concurrent_task1():
pass
await asyncio.sleep(0)
return await concurrent_task(test_user_context.user_id, user_context=test_user_context)

async def concurrent_task2():
pass
await asyncio.sleep(0)
return await concurrent_task(test_user_context_2.user_id, user_context=test_user_context_2)

task1 = await manager.start_task( )
"concurrent_1", "Concurrent Task 1",
concurrent_task1,
user_context=test_user_context
    

task2 = await manager.start_task( )
"concurrent_2", "Concurrent Task 2",
concurrent_task2,
user_context=test_user_context_2
    

    # Wait for both to complete concurrently
result1, result2 = await asyncio.gather( )
manager.wait_for_task("concurrent_1", user_context=test_user_context),
manager.wait_for_task("concurrent_2", user_context=test_user_context_2)
    

    # Verify isolation
assert result1 == ""
assert result2 == ""
assert results[test_user_context.user_id] == ""
assert results[test_user_context_2.user_id] == ""


class TestIntegrationSecurity:
        """Integration tests for end-to-end security."""

@pytest.mark.asyncio
    async def test_end_to_end_context_propagation(self, test_user_context):
"""Test end-to-end context propagation through multiple layers."""

        # Setup secure components
task_manager = SecureBackgroundTaskManager(enforce_user_context=True)
validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)
serializer = SecureContextSerializer()

        # Simulate a complex workflow
workflow_results = []

@pytest.fixture
async def analytics_task(event_data: Dict[str, Any], user_context: Optional[UserExecutionContext] = None):
    # Process analytics
workflow_results.append({ })
'step': 'analytics',
'user_id': user_context.user_id,
'event_data': event_data
    

await asyncio.sleep(0)
return ""

@pytest.fixture
async def report_task(analytics_result: str, user_context: Optional[UserExecutionContext] = None):
    # Generate report
workflow_results.append({ })
'step': 'report',
'user_id': user_context.user_id,
'analytics_result': analytics_result
    

await asyncio.sleep(0)
return ""

    # Execute workflow
event_data = {"prompt": "test message", "model": "gpt-4"}

    # Step 1: Analytics processing
analytics_result = await analytics_task(event_data, user_context=test_user_context)

    # Step 2: Report generation
report_result = await report_task(analytics_result, user_context=test_user_context)

    # Verify results
assert len(workflow_results) == 2
assert workflow_results[0]['user_id'] == test_user_context.user_id
assert workflow_results[1]['user_id'] == test_user_context.user_id
assert analytics_result == ""
assert report_result == ""

    # Verify no violations
assert len(validator.violations) == 0


if __name__ == "__main__":
pytest.main([__file__, "-v", "-s"])
pass
