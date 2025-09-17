class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''Comprehensive Test Suite for Background Task User Context Isolation'

        SECURITY CRITICAL: These tests validate that all background tasks maintain proper
        UserExecutionContext isolation and prevent data leakage between users.

        Test Coverage:
        - Analytics service event processing isolation
        - Background task manager context propagation
        - Context serialization security
        - WebSocket background task isolation
        - Security validator functionality
        - Cross-user data access prevention
        '''
        '''

        import asyncio
        import pytest
        import uuid
        from datetime import datetime, timezone
        from typing import Dict, Any, Optional
        from shared.isolated_environment import IsolatedEnvironment

        from analytics_service.analytics_core.services.event_processor import EventProcessor, ProcessorConfig
        from analytics_service.analytics_core.models.events import AnalyticsEvent, EventType, EventCategory, EventBatch
        from netra_backend.app.services.secure_background_task_manager import SecureBackgroundTaskManager, SecureBackgroundTask
        from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
        from shared.context_serialization import SecureContextSerializer, ContextSerializationError
        from shared.background_task_security_validator import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        BackgroundTaskSecurityValidator, SecurityViolationType, security_required
        

        # Test fixtures and utilities

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
    

        @pytest.fixture
    def sample_analytics_event(test_user_context) -> AnalyticsEvent:
        """Create a sample analytics event."""
        return AnalyticsEvent( )
        event_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        event_type=EventType.CHAT_INTERACTION,
        event_category=EventCategory.USER_ACTION,
        event_action="chat_message",
        user_id=test_user_context.user_id,
        session_id=test_user_context.thread_id,
        properties={"prompt_text": "Test message", "model_used": "gpt-4"}
    

        @pytest.fixture
    def mock_clickhouse():
        """Mock ClickHouse manager."""
        websocket = TestWebSocketConnection()
        mock.initialize_schema.return_value = True
        mock.insert_data.return_value = 1
        mock.health_check.return_value = True
        return mock

        @pytest.fixture
    def mock_redis():
        """Mock Redis manager."""
        pass
        websocket = TestWebSocketConnection()
        mock.initialize.return_value = True
        mock.check_rate_limit.return_value = True
        mock.add_hot_prompt.return_value = True
        mock.health_check.return_value = True
        return mock


class TestAnalyticsEventProcessorSecurity:
        """Test security for analytics event processor background tasks."""

@pytest.mark.asyncio
    async def test_event_processor_requires_user_context(self, mock_clickhouse, mock_redis, sample_analytics_event):
"""Test that event processor enforces user context requirement."""
config = ProcessorConfig(require_user_context=True)
processor = EventProcessor(mock_clickhouse, mock_redis, config)

        # Should fail without user context
with pytest.raises(InvalidContextError, match="UserExecutionContext is mandatory"):
await processor.process_event(sample_analytics_event, user_context=None)

@pytest.mark.asyncio
    async def test_event_processor_validates_user_id_match(self, mock_clickhouse, mock_redis, test_user_context, test_user_context_2):
"""Test that event processor validates user ID matches context."""
pass
config = ProcessorConfig(require_user_context=True)
processor = EventProcessor(mock_clickhouse, mock_redis, config)

                # Create event for user 1
event = AnalyticsEvent( )
event_id=str(uuid.uuid4()),
timestamp=datetime.now(timezone.utc),
event_type=EventType.CHAT_INTERACTION,
event_category=EventCategory.USER_ACTION,
event_action="chat_message",
user_id=test_user_context.user_id,
session_id=test_user_context.thread_id,
properties={"prompt_text": "Test message"}
                

                # Should fail with different user context
result = await processor.process_event(event, user_context=test_user_context_2)
assert result is False

@pytest.mark.asyncio
    async def test_event_processor_batch_context_isolation(self, mock_clickhouse, mock_redis, test_user_context):
"""Test that batch processing maintains user context isolation."""
config = ProcessorConfig(require_user_context=True)
processor = EventProcessor(mock_clickhouse, mock_redis, config)

                    # Create batch of events for the user
events = []
for i in range(3):
event = AnalyticsEvent( )
event_id=str(uuid.uuid4()),
timestamp=datetime.now(timezone.utc),
event_type=EventType.CHAT_INTERACTION,
event_category=EventCategory.USER_ACTION,
event_action="chat_message",
user_id=test_user_context.user_id,
session_id=test_user_context.thread_id,
properties={"prompt_text": ""}
                        
events.append(event)

batch = EventBatch(events=events)

                        # Should succeed with proper context
result = await processor.process_batch(batch, user_context=test_user_context)
assert result.processed_count == 3
assert result.failed_count == 0

@pytest.mark.asyncio
    async def test_event_processor_worker_context_propagation(self, mock_clickhouse, mock_redis, test_user_context, sample_analytics_event):
"""Test that background worker maintains user context."""
pass
config = ProcessorConfig(require_user_context=True, batch_size=1)
processor = EventProcessor(mock_clickhouse, mock_redis, config)

await processor.initialize()
await processor.start()

try:
                                # Process event with context
result = await processor.process_event(sample_analytics_event, user_context=test_user_context)
assert result is True

                                # Wait for processing
await asyncio.sleep(0.1)

                                # Verify processing occurred
assert processor._processed_count > 0

finally:
    pass
await processor.stop()


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
"""Test that users cannot access each other's tasks."""'
manager = SecureBackgroundTaskManager(enforce_user_context=True)

    async def test_task():
await asyncio.sleep(0)
return "test_result"

                                # Start task for user 1
task1 = await manager.start_task("user1_task", "User 1 Task", test_task, user_context=test_user_context)

                                # User 2 should not be able to access user 1's task'
task_access = manager.get_task("user1_task", user_context=test_user_context_2)
assert task_access is None

                                # User 1 should be able to access their own task
task_access = manager.get_task("user1_task", user_context=test_user_context)
assert task_access is not None

def test_task_manager_list_tasks_isolation(self, test_user_context, test_user_context_2):
    pass
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


class TestContextSerialization:
        """Test security for context serialization."""

    def test_context_serialization_integrity(self, test_user_context):
        """Test that context serialization maintains integrity."""
        serializer = SecureContextSerializer()

    # Serialize context
        serialized = serializer.serialize_context(test_user_context)

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
        with pytest.raises(ContextSerializationError):
        serializer.deserialize_context(tampered)

    def test_context_serialization_cross_user_prevention(self, test_user_context, test_user_context_2):
        """Test that serialized contexts cannot be mixed between users."""
        serializer = SecureContextSerializer()

    # Serialize both contexts
        serialized1 = serializer.serialize_context(test_user_context)
        serialized2 = serializer.serialize_context(test_user_context_2)

    # Deserialize
        deserialized1 = serializer.deserialize_context(serialized1)
        deserialized2 = serializer.deserialize_context(serialized2)

    # Verify no cross-contamination
        assert deserialized1.user_id == test_user_context.user_id
        assert deserialized2.user_id == test_user_context_2.user_id
        assert deserialized1.user_id != deserialized2.user_id


class TestSecurityValidator:
        """Test security validator functionality."""

    def test_validator_detects_missing_context(self):
        """Test that validator detects missing user context."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)

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

    def test_security_required_decorator(self, test_user_context):
        """Test that security_required decorator works correctly."""

        # @pytest.fixture
    async def test_task(user_context:
        pass
        await asyncio.sleep(0)
        return ""

        # Should work with context
        result = asyncio.run(test_task(user_context=test_user_context))
        assert result == ""

        # Should fail without context
        with pytest.raises(InvalidContextError):
        asyncio.run(test_task())


class TestCrossUserDataLeakagePrevention:
        """Test prevention of cross-user data leakage in background tasks."""

@pytest.mark.asyncio
    async def test_analytics_cross_user_isolation(self, mock_clickhouse, mock_redis, test_user_context, test_user_context_2):
"""Test that analytics processing prevents cross-user data access."""
config = ProcessorConfig(require_user_context=True)
processor = EventProcessor(mock_clickhouse, mock_redis, config)

        # Create events for different users
event1 = AnalyticsEvent( )
event_id=str(uuid.uuid4()),
timestamp=datetime.now(timezone.utc),
event_type=EventType.CHAT_INTERACTION,
event_category=EventCategory.USER_ACTION,
event_action="chat_message",
user_id=test_user_context.user_id,
session_id=test_user_context.thread_id,
properties={"prompt_text": "User 1 message"}
        

event2 = AnalyticsEvent( )
event_id=str(uuid.uuid4()),
timestamp=datetime.now(timezone.utc),
event_type=EventType.CHAT_INTERACTION,
event_category=EventCategory.USER_ACTION,
event_action="chat_message",
user_id=test_user_context_2.user_id,
session_id=test_user_context_2.thread_id,
properties={"prompt_text": "User 2 message"}
        

        # Process events with correct contexts
result1 = await processor.process_event(event1, user_context=test_user_context)
result2 = await processor.process_event(event2, user_context=test_user_context_2)

assert result1 is True
assert result2 is True

        # Try to process event1 with user2's context (should fail)'
result_cross = await processor.process_event(event1, user_context=test_user_context_2)
assert result_cross is False

@pytest.mark.asyncio
    async def test_background_task_data_isolation(self, test_user_context, test_user_context_2):
"""Test that background tasks maintain data isolation between users."""
pass
manager = SecureBackgroundTaskManager(enforce_user_context=True)

            # Store to simulate user-specific data
user_data = {}

async def user_specific_task(data_key: str, user_context: Optional[UserExecutionContext] = None):
pass
if user_context:
        # Store data with user prefix to simulate isolation
storage_key = ""
user_data[storage_key] = ""
await asyncio.sleep(0)
return storage_key
return None

        # Start tasks for different users
task1 = await manager.start_task( )
"data_task_1", "User 1 Data Task",
lambda x: None user_specific_task("secret_data", user_context=test_user_context),
user_context=test_user_context
        

task2 = await manager.start_task( )
"data_task_2", "User 2 Data Task",
lambda x: None user_specific_task("secret_data", user_context=test_user_context_2),
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


class TestIntegrationSecurity:
        """Integration tests for end-to-end security."""

@pytest.mark.asyncio
    async def test_end_to_end_context_propagation(self, mock_clickhouse, mock_redis, test_user_context):
"""Test end-to-end context propagation through multiple layers."""

        # Setup secure components
task_manager = SecureBackgroundTaskManager(enforce_user_context=True)
validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)
serializer = SecureContextSerializer()

        # Simulate a complex workflow
workflow_results = []

@pytest.fixture
async def analytics_task(event_data: Dict[str, Any], user_context: Optional[UserExecutionContext] = None):
    # Validate context
validator.validate_background_task_context( )
"analytics_processing",
"",
user_context,
require_context=True
    

    # Process analytics
workflow_results.append({ })
'step': 'analytics',
'user_id': user_context.user_id,
'event_data': event_data
    

await asyncio.sleep(0)
return ""

@pytest.fixture
async def report_task(analytics_result: str, user_context: Optional[UserExecutionContext] = None):
    # Validate context
validator.validate_background_task_context( )
"report_generation",
"",
user_context,
require_context=True
    

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
    pass
pytest.main([__file__, "-v", "-s"])
pass

'''
))