"""Core Message Persistence E2E Tests

Tests database persistence for messages and threads with real database
operations. No mocks used for database or message handlers.

Business Value: Ensures reliable data persistence for user conversations
"""

from datetime import datetime, timezone
from uuid import uuid4
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.db.repositories.agent_repository import (
    MessageRepository,
    ThreadRepository,
)
from netra_backend.app.handlers.example_message_handler import ExampleMessageHandler
from tests.e2e.database_consistency_fixtures import (
    database_test_session,
)
from tests.e2e.example_message_test_helpers import (
    BASIC_COST_OPTIMIZATION,
    create_example_message_request,
    create_message_data,
    create_thread_data,
)


@pytest.fixture
@pytest.mark.e2e
async def test_thread_repo(database_test_session):
    """Get thread repository with test database session"""
    return ThreadRepository(database_test_session)


@pytest.fixture
@pytest.mark.e2e
async def test_message_repo(database_test_session):
    """Get message repository with test database session"""
    return MessageRepository(database_test_session)


@pytest.fixture
@pytest.mark.e2e
async def test_user_id():
    """Generate test user ID"""
    return f"test_user_{uuid4()}"


@pytest.mark.e2e
class ThreadPersistenceTests:
    """Test thread persistence in database"""

    @pytest.mark.e2e
    async def test_thread_creation(self, thread_repo, test_user_id):
        """Test basic thread creation"""
        thread_data = create_thread_data(test_user_id)
        thread = await thread_repo.create(thread_data)
        assert thread.id == thread_data["id"]
        assert thread.metadata_["user_id"] == test_user_id

    @pytest.mark.e2e
    async def test_thread_retrieval(self, thread_repo, test_user_id):
        """Test thread retrieval by ID"""
        thread_data = create_thread_data(test_user_id)
        created = await thread_repo.create(thread_data)
        retrieved = await thread_repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.e2e
    async def test_thread_metadata_persistence(self, thread_repo, test_user_id):
        """Test thread metadata is persisted correctly"""
        metadata = {"category": "cost-optimization", "complexity": "intermediate"}
        thread_data = create_thread_data(test_user_id, metadata)
        thread = await thread_repo.create(thread_data)
        retrieved = await thread_repo.get_by_id(thread.id)
        assert retrieved.metadata_["category"] == "cost-optimization"

    @pytest.mark.e2e
    async def test_multiple_threads_per_user(self, thread_repo, test_user_id):
        """Test multiple threads for same user"""
        threads = []
        for i in range(3):
            thread_data = create_thread_data(test_user_id)
            thread = await thread_repo.create(thread_data)
            threads.append(thread)
        
        for thread in threads:
            retrieved = await thread_repo.get_by_id(thread.id)
            assert retrieved.metadata_["user_id"] == test_user_id


@pytest.mark.e2e
class MessagePersistenceTests:
    """Test message persistence in database"""

    @pytest.mark.e2e
    async def test_message_creation(self, message_repo, thread_repo, test_user_id):
        """Test basic message creation and persistence"""
        thread_data = create_thread_data(test_user_id)
        thread = await thread_repo.create(thread_data)
        
        message_data = create_message_data(thread.id, "Test message content")
        message = await message_repo.create(message_data)
        assert message.thread_id == thread.id
        assert message.role == "user"

    @pytest.mark.e2e
    async def test_message_content_structure(self, message_repo, thread_repo, test_user_id):
        """Test message content structure persistence"""
        thread_data = create_thread_data(test_user_id)
        thread = await thread_repo.create(thread_data)
        
        message_data = create_message_data(thread.id, "Complex content test")
        message = await message_repo.create(message_data)
        retrieved = await message_repo.get_by_id(message.id)
        assert len(retrieved.content) == 1
        assert retrieved.content[0]["text"] == "Complex content test"

    @pytest.mark.e2e
    async def test_assistant_response_persistence(self, message_repo, thread_repo, test_user_id):
        """Test assistant response message persistence"""
        thread_data = create_thread_data(test_user_id)
        thread = await thread_repo.create(thread_data)
        
        metadata = {"agent_name": "Cost Optimization Agent", "processing_time_ms": 1500}
        message_data = create_message_data(
            thread.id, 
            "Optimization recommendations", 
            role="assistant",
            metadata=metadata
        )
        message = await message_repo.create(message_data)
        assert message.role == "assistant"
        assert message.metadata_["agent_name"] == "Cost Optimization Agent"

    @pytest.mark.e2e
    async def test_messages_by_thread_retrieval(self, message_repo, thread_repo, test_user_id):
        """Test retrieving all messages for a thread"""
        thread_data = create_thread_data(test_user_id)
        thread = await thread_repo.create(thread_data)
        
        for i in range(3):
            message_data = create_message_data(thread.id, f"Message {i}")
            await message_repo.create(message_data)
        
        messages = await message_repo.get_by_thread_id(thread.id)
        assert len(messages) == 3
        assert all(msg.thread_id == thread.id for msg in messages)


@pytest.mark.e2e
class ThreadMessageRelationshipTests:
    """Test thread-message relationship integrity"""

    @pytest.mark.e2e
    async def test_thread_message_relationship(self, thread_repo, message_repo, test_user_id):
        """Test thread-message relationship integrity"""
        thread_data = create_thread_data(test_user_id)
        thread = await thread_repo.create(thread_data)
        
        message_data = create_message_data(thread.id, "Relationship test")
        message = await message_repo.create(message_data)
        
        assert message.thread_id == thread.id
        thread_messages = await message_repo.get_by_thread_id(thread.id)
        assert len(thread_messages) == 1
        assert thread_messages[0].id == message.id

    @pytest.mark.e2e
    async def test_orphaned_message_prevention(self, message_repo):
        """Test that messages cannot be created without valid thread"""
        message_data = create_message_data("non_existent_thread", "Orphaned message")
        
        with pytest.raises(Exception):
            await message_repo.create(message_data)

    @pytest.mark.e2e
    async def test_data_timestamps_consistency(self, thread_repo, message_repo, test_user_id):
        """Test timestamp consistency between threads and messages"""
        base_time = int(datetime.now(timezone.utc).timestamp())
        
        thread_data = create_thread_data(test_user_id)
        thread_data["created_at"] = base_time
        thread = await thread_repo.create(thread_data)
        
        message_data = create_message_data(thread.id, "Timestamp test")
        message_data["created_at"] = base_time + 1
        message = await message_repo.create(message_data)
        
        assert message.created_at >= thread.created_at


@pytest.mark.e2e
class ExampleMessageIntegrationTests:
    """Test integration between handlers and persistence"""

    @pytest.mark.e2e
    async def test_end_to_end_message_flow(self, test_user_id):
        """Test complete message flow from handler to database"""
        handler = ExampleMessageHandler()
        request = create_example_message_request(BASIC_COST_OPTIMIZATION, user_id=test_user_id)
        response = await handler.handle_example_message(request)
        assert response.status == "completed"
        assert response.processing_time_ms is not None

    @pytest.mark.e2e
    async def test_message_metadata_tracking(self, test_user_id):
        """Test example message metadata tracking"""
        handler = ExampleMessageHandler()
        request = create_example_message_request(
            "Test metadata tracking",
            category="model-selection",
            complexity="advanced",
            business_value="retention",
            user_id=test_user_id
        )
        response = await handler.handle_example_message(request)
        assert response.message_id == request["example_message_id"]
        if response.status == "completed" and response.business_insights:
            assert response.business_insights["business_value_type"] == "retention"
