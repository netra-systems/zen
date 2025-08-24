"""
RED TEAM TEST 11: Message Persistence and Retrieval

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real integration issues.
This test validates that messages are properly stored in the database and retrieved correctly.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Data Integrity, User Trust, Platform Reliability
- Value Impact: Lost or corrupted messages directly impact user conversations and platform trust
- Strategic Impact: Core data persistence foundation for chat functionality

Testing Level: L3 (Real services, real databases, minimal mocking)
Expected Initial Result: FAILURE (exposes real message persistence gaps)
"""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with error handling
try:
    from netra_backend.app.core.configuration.base import get_unified_config
except ImportError:
    def get_unified_config():
        from types import SimpleNamespace
        return SimpleNamespace(database_url="postgresql://test:test@localhost:5432/netra_test")

# ThreadService exists
from netra_backend.app.services.thread_service import ThreadService

# Import models with fallbacks
try:
    from netra_backend.app.db.models_user import User
except ImportError:
    from netra_backend.app.db.models import User

try:
    from netra_backend.app.db.models_agent import Thread, Message
except ImportError:
    from netra_backend.app.db.models import Thread, Message

try:
    from netra_backend.app.db.session import get_db_session
except ImportError:
    from netra_backend.app.db.database_manager import DatabaseManager
    get_db_session = lambda: DatabaseManager().get_session()

try:
    from test_framework.real_services_test_fixtures import create_real_test_user
except ImportError:
    # Mock test user creation
    def create_real_test_user():
        from types import SimpleNamespace
        return SimpleNamespace(id="test-user-id", email="test@example.com")


class TestMessagePersistenceAndRetrieval:
    """
    RED TEAM TEST 11: Message Persistence and Retrieval
    
    Tests the critical path of message storage and thread message listing.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.fixture
    async def test_user_and_thread(self, real_database_session):
        """Create a real test user and thread for testing."""
        # Create test user directly in database
        test_user_id = str(uuid.uuid4())
        test_thread_id = str(uuid.uuid4())
        
        user = User(
            id=test_user_id,
            email=f"msgtest_{secrets.token_urlsafe(8)}@example.com",
            name="Message Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        thread = Thread(
            id=test_thread_id,
            user_id=test_user_id,
            title="Test Thread for Message Persistence",
            description="Testing message persistence and retrieval",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(user)
        real_database_session.add(thread)
        await real_database_session.commit()
        
        return {
            "user_id": test_user_id,
            "thread_id": test_thread_id,
            "user": user,
            "thread": thread
        }

    @pytest.mark.asyncio
    async def test_01_basic_message_storage_fails(self, real_database_session, test_user_and_thread):
        """
        Test 11A: Basic Message Storage (EXPECTED TO FAIL)
        
        Tests that messages can be created and stored in the database.
        This will likely FAIL because:
        1. Message creation API may not exist
        2. Database schema may be incomplete
        3. Message model may not be properly defined
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        # Create message directly in database to test storage
        test_message = Message(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            user_id=user_id,
            content="This is a test message for persistence testing",
            role="user",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        try:
            # FAILURE EXPECTED HERE - Message model may not exist or be incomplete
            real_database_session.add(test_message)
            await real_database_session.commit()
            
            # Verify message was stored
            stored_message = await real_database_session.execute(
                select(Message).where(Message.id == test_message.id)
            )
            retrieved_message = stored_message.scalar_one_or_none()
            
            assert retrieved_message is not None, "Message was not stored in database"
            assert retrieved_message.content == test_message.content, "Message content not stored correctly"
            assert retrieved_message.thread_id == thread_id, "Message thread_id not stored correctly"
            assert retrieved_message.user_id == user_id, "Message user_id not stored correctly"
            
        except Exception as e:
            pytest.fail(f"Message storage failed: {e}")

    @pytest.mark.asyncio
    async def test_02_message_api_creation_fails(self, real_test_client, test_user_and_thread):
        """
        Test 11B: Message Creation via API (EXPECTED TO FAIL)
        
        Tests that messages can be created through the API endpoint.
        Will likely FAIL because:
        1. Message creation endpoint may not exist
        2. Authentication may not be working
        3. Request validation may be incomplete
        """
        thread_id = test_user_and_thread["thread_id"]
        
        # Generate test JWT token (simplified for testing)
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user_and_thread["user_id"],
            "exp": int(time.time()) + 3600
        }
        test_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        message_data = {
            "content": "Test message created via API",
            "role": "user"
        }
        
        auth_headers = {"Authorization": f"Bearer {test_token}"}
        
        # Try to create message via API - will likely fail
        response = real_test_client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json=message_data,
            headers=auth_headers
        )
        
        # FAILURE EXPECTED HERE
        assert response.status_code == 201, f"Message creation API failed: {response.status_code} - {response.text}"
        
        message_response = response.json()
        assert "id" in message_response, "Created message should have an ID"
        assert message_response["content"] == message_data["content"], "Message content not returned correctly"
        assert message_response["thread_id"] == thread_id, "Thread ID not returned correctly"

    @pytest.mark.asyncio
    async def test_03_thread_message_listing_fails(self, real_test_client, real_database_session, test_user_and_thread):
        """
        Test 11C: Thread Message Listing (EXPECTED TO FAIL)
        
        Tests that messages can be retrieved for a specific thread.
        Will likely FAIL because:
        1. Message listing endpoint may not exist
        2. Query logic may be incomplete
        3. Response serialization may fail
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        # Create multiple test messages in database
        messages = []
        for i in range(5):
            message = Message(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                user_id=user_id,
                content=f"Test message {i+1} for listing test",
                role="user" if i % 2 == 0 else "assistant",
                created_at=datetime.now(timezone.utc) + timedelta(seconds=i),
                updated_at=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
            messages.append(message)
            real_database_session.add(message)
        
        await real_database_session.commit()
        
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {"user_id": user_id, "exp": int(time.time()) + 3600}
        test_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        auth_headers = {"Authorization": f"Bearer {test_token}"}
        
        # Try to list messages via API - will likely fail
        response = real_test_client.get(
            f"/api/v1/threads/{thread_id}/messages",
            headers=auth_headers
        )
        
        # FAILURE EXPECTED HERE
        assert response.status_code == 200, f"Message listing API failed: {response.status_code} - {response.text}"
        
        messages_response = response.json()
        assert isinstance(messages_response, list), "Messages response should be a list"
        assert len(messages_response) == 5, f"Expected 5 messages, got {len(messages_response)}"
        
        # Verify message ordering (should be chronological)
        for i, msg in enumerate(messages_response):
            assert "id" in msg, f"Message {i} missing ID"
            assert "content" in msg, f"Message {i} missing content"
            assert "created_at" in msg, f"Message {i} missing created_at"

    @pytest.mark.asyncio
    async def test_04_message_ordering_fails(self, real_database_session, test_user_and_thread):
        """
        Test 11D: Message Ordering (EXPECTED TO FAIL)
        
        Tests that messages are retrieved in correct chronological order.
        Will likely FAIL because:
        1. Ordering logic may not be implemented
        2. Database indexes may be missing
        3. Query may not handle timestamps correctly
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        # Create messages with specific timestamps
        base_time = datetime.now(timezone.utc)
        test_messages = []
        
        for i in range(3):
            message = Message(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                user_id=user_id,
                content=f"Message {i+1} - created at {base_time + timedelta(minutes=i)}",
                role="user",
                created_at=base_time + timedelta(minutes=i),
                updated_at=base_time + timedelta(minutes=i)
            )
            test_messages.append(message)
            real_database_session.add(message)
        
        await real_database_session.commit()
        
        # Query messages ordered by creation time
        query_result = await real_database_session.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.asc())
        )
        retrieved_messages = query_result.scalars().all()
        
        # FAILURE EXPECTED HERE - ordering may not work
        assert len(retrieved_messages) == 3, f"Expected 3 messages, got {len(retrieved_messages)}"
        
        # Verify chronological order
        for i, msg in enumerate(retrieved_messages):
            expected_content = f"Message {i+1} - created at {base_time + timedelta(minutes=i)}"
            assert msg.content == expected_content, f"Message {i} not in correct order: {msg.content}"
            
            if i > 0:
                assert msg.created_at > retrieved_messages[i-1].created_at, f"Message {i} timestamp not greater than previous"

    @pytest.mark.asyncio
    async def test_05_message_pagination_fails(self, real_test_client, real_database_session, test_user_and_thread):
        """
        Test 11E: Message Pagination (EXPECTED TO FAIL)
        
        Tests that message listing supports pagination for large conversations.
        Will likely FAIL because:
        1. Pagination may not be implemented
        2. Limit/offset parameters may not be handled
        3. Response metadata may be missing
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        # Create many messages to test pagination
        messages = []
        for i in range(25):
            message = Message(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                user_id=user_id,
                content=f"Pagination test message {i+1:02d}",
                role="user" if i % 2 == 0 else "assistant",
                created_at=datetime.now(timezone.utc) + timedelta(seconds=i),
                updated_at=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
            messages.append(message)
            real_database_session.add(message)
        
        await real_database_session.commit()
        
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {"user_id": user_id, "exp": int(time.time()) + 3600}
        test_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        auth_headers = {"Authorization": f"Bearer {test_token}"}
        
        # Test pagination parameters - will likely fail
        response = real_test_client.get(
            f"/api/v1/threads/{thread_id}/messages?limit=10&offset=0",
            headers=auth_headers
        )
        
        # FAILURE EXPECTED HERE
        assert response.status_code == 200, f"Paginated message listing failed: {response.text}"
        
        page1_response = response.json()
        assert isinstance(page1_response, (list, dict)), "Paginated response should be list or dict with metadata"
        
        if isinstance(page1_response, list):
            # Simple list response
            assert len(page1_response) == 10, f"Expected 10 messages in first page, got {len(page1_response)}"
        else:
            # Response with metadata
            assert "data" in page1_response, "Paginated response should have 'data' field"
            assert "total" in page1_response, "Paginated response should have 'total' field"
            assert len(page1_response["data"]) == 10, f"Expected 10 messages in first page"
            assert page1_response["total"] == 25, "Total count should be 25"

    @pytest.mark.asyncio
    async def test_06_message_persistence_durability_fails(self, real_database_session, test_user_and_thread):
        """
        Test 11F: Message Persistence Durability (EXPECTED TO FAIL)
        
        Tests that messages persist correctly through database operations.
        Will likely FAIL because:
        1. Transaction handling may be incomplete
        2. Database constraints may not be enforced
        3. Data integrity checks may be missing
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        # Create message with specific data
        message_id = str(uuid.uuid4())
        original_content = "Original message content for durability test"
        
        message = Message(
            id=message_id,
            thread_id=thread_id,
            user_id=user_id,
            content=original_content,
            role="user",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Store message and commit
        real_database_session.add(message)
        await real_database_session.commit()
        
        # Close and reopen session to simulate persistence
        await real_database_session.close()
        
        # Create new session
        config = get_unified_config()
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            async with async_session() as new_session:
                # Try to retrieve message from new session
                query_result = await new_session.execute(
                    select(Message).where(Message.id == message_id)
                )
                persisted_message = query_result.scalar_one_or_none()
                
                # FAILURE EXPECTED HERE - persistence may not work
                assert persisted_message is not None, "Message was not persisted across sessions"
                assert persisted_message.content == original_content, "Message content not persisted correctly"
                assert persisted_message.thread_id == thread_id, "Thread ID not persisted correctly"
                assert persisted_message.user_id == user_id, "User ID not persisted correctly"
                assert persisted_message.role == "user", "Message role not persisted correctly"
                
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_07_concurrent_message_creation_fails(self, real_database_session, test_user_and_thread):
        """
        Test 11G: Concurrent Message Creation (EXPECTED TO FAIL)
        
        Tests that multiple messages can be created concurrently without data corruption.
        Will likely FAIL because:
        1. Concurrency control may not be implemented
        2. Database locking may cause deadlocks
        3. Transaction isolation may be insufficient
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        async def create_message(session: AsyncSession, content: str) -> str:
            """Create a single message in the database."""
            message = Message(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                user_id=user_id,
                content=content,
                role="user",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            session.add(message)
            await session.commit()
            return message.id
        
        # Create multiple sessions for concurrent operations
        config = get_unified_config()
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Create 10 concurrent messages
            tasks = []
            for i in range(10):
                async with async_session() as session:
                    task = create_message(session, f"Concurrent message {i+1}")
                    tasks.append(task)
            
            # FAILURE EXPECTED HERE - concurrent operations may fail
            message_ids = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for exceptions
            successful_creates = 0
            exceptions = []
            
            for result in message_ids:
                if isinstance(result, Exception):
                    exceptions.append(str(result))
                else:
                    successful_creates += 1
            
            # At least 80% should succeed
            success_rate = successful_creates / 10
            assert success_rate >= 0.8, f"Concurrent message creation failed: {success_rate*100:.1f}% success rate. Exceptions: {exceptions[:3]}"
            
            # Verify all messages were actually stored
            async with async_session() as verify_session:
                count_result = await verify_session.execute(
                    text("SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id"),
                    {"thread_id": thread_id}
                )
                stored_count = count_result.scalar()
                
                assert stored_count >= successful_creates, f"Only {stored_count} messages stored, expected at least {successful_creates}"
                
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_08_message_retrieval_performance_fails(self, real_database_session, test_user_and_thread):
        """
        Test 11H: Message Retrieval Performance (EXPECTED TO FAIL)
        
        Tests that message retrieval performs adequately with realistic data volumes.
        Will likely FAIL because:
        1. Database indexes may be missing
        2. Query optimization may be poor
        3. N+1 query problems may exist
        """
        thread_id = test_user_and_thread["thread_id"]
        user_id = test_user_and_thread["user_id"]
        
        # Create large number of messages to test performance
        messages = []
        batch_size = 100
        
        for i in range(500):  # 500 messages for performance testing
            message = Message(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                user_id=user_id,
                content=f"Performance test message {i+1} with some longer content to simulate real messages. This content should be representative of actual user messages in a conversation thread.",
                role="user" if i % 2 == 0 else "assistant",
                created_at=datetime.now(timezone.utc) + timedelta(seconds=i),
                updated_at=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
            messages.append(message)
            
            # Add in batches to avoid overwhelming the database
            if len(messages) >= batch_size:
                for msg in messages:
                    real_database_session.add(msg)
                await real_database_session.commit()
                messages = []
        
        # Add remaining messages
        if messages:
            for msg in messages:
                real_database_session.add(msg)
            await real_database_session.commit()
        
        # Test retrieval performance
        start_time = time.time()
        
        query_result = await real_database_session.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.desc())
            .limit(50)
        )
        retrieved_messages = query_result.scalars().all()
        
        end_time = time.time()
        query_duration = end_time - start_time
        
        # FAILURE EXPECTED HERE - performance may be poor
        assert len(retrieved_messages) == 50, f"Expected 50 messages, got {len(retrieved_messages)}"
        assert query_duration < 1.0, f"Query took {query_duration:.3f}s, expected < 1.0s (performance issue)"
        
        # Verify correct ordering (newest first)
        for i in range(1, len(retrieved_messages)):
            assert retrieved_messages[i].created_at <= retrieved_messages[i-1].created_at, \
                f"Messages not properly ordered: {i-1}={retrieved_messages[i-1].created_at}, {i}={retrieved_messages[i].created_at}"


# Additional utility class for message testing
class RedTeamMessageTestUtils:
    """Utility methods for Red Team message testing."""
    
    @staticmethod
    def generate_test_message(thread_id: str, user_id: str, content: str = None) -> Message:
        """Generate a test message with realistic data."""
        if content is None:
            content = f"Test message generated at {datetime.now(timezone.utc).isoformat()}"
        
        return Message(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            user_id=user_id,
            content=content,
            role="user",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    @staticmethod
    async def verify_message_in_database(session: AsyncSession, message_id: str) -> bool:
        """Verify a message exists in the database."""
        try:
            result = await session.execute(
                select(Message).where(Message.id == message_id)
            )
            return result.scalar_one_or_none() is not None
        except Exception:
            return False
    
    @staticmethod
    async def count_thread_messages(session: AsyncSession, thread_id: str) -> int:
        """Count messages in a specific thread."""
        result = await session.execute(
            text("SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id"),
            {"thread_id": thread_id}
        )
        return result.scalar() or 0
