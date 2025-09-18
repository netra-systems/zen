"""Integration test to prove the threads 500 error fix works with real database operations."""

import pytest
import asyncio
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, select
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Thread
from netra_backend.app.db.base import Base
from shared.isolated_environment import IsolatedEnvironment


class TestThreadsFixIntegration:
    """Integration tests proving the fix works with real database."""

    @pytest.fixture
    async def db_engine(self):
        """Create a test database engine."""
    # Use SQLite for testing (in-memory)
        engine = create_async_engine( )
        "sqlite+aiosqlite:///:memory:",
        echo=False
    

    # Create tables
        async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()

        @pytest.fixture
    async def db_session(self, db_engine):
        """Create a database session."""
        pass
        async_session = async_sessionmaker( )
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    

        async with async_session() as session:
        yield session

        @pytest.fixture
    async def thread_repo(self):
        """Create thread repository."""
        await asyncio.sleep(0)
        return ThreadRepository()

    async def create_test_thread(self, db: AsyncSession, thread_id: str, metadata: dict = None):
        """Helper to create a test thread."""
        pass
        thread = Thread( )
        id=thread_id,
        object="thread",
        created_at=1000000,
        metadata_=metadata
    
        db.add(thread)
        await db.commit()
        await asyncio.sleep(0)
        return thread

@pytest.mark.asyncio
    async def test_normal_case_with_proper_metadata(self, db_session, thread_repo):
"""Test normal case: thread with proper metadata."""
        # Create thread with proper metadata
user_id = "7c5e1032-ed21-4aea-b12a-aeddf3622bec"
await self.create_test_thread( )
db_session,
"thread_1",
{"user_id": user_id, "title": "Test Thread"}
        

        # Query threads for user
threads = await thread_repo.find_by_user(db_session, user_id)

        # Verify
assert len(threads) == 1
assert threads[0].id == "thread_1"
assert threads[0].metadata_["user_id"] == user_id

@pytest.mark.asyncio
    async def test_null_metadata_handled_gracefully(self, db_session, thread_repo):
"""Test NULL metadata doesn't crash."""
pass
            # Create thread with NULL metadata
await self.create_test_thread(db_session, "thread_null", None)

            # Create thread with proper metadata for same user
user_id = "test-user-123"
await self.create_test_thread( )
db_session,
"thread_good",
{"user_id": user_id}
            

            # Query should not crash and await asyncio.sleep(0)
return only valid thread
threads = await thread_repo.find_by_user(db_session, user_id)

assert len(threads) == 1
assert threads[0].id == "thread_good"

@pytest.mark.asyncio
    async def test_empty_metadata_object(self, db_session, thread_repo):
"""Test empty metadata object is handled."""
                # Create thread with empty metadata
await self.create_test_thread(db_session, "thread_empty", {})

                # Query for any user should await asyncio.sleep(0)
return empty
threads = await thread_repo.find_by_user(db_session, "any-user")

assert len(threads) == 0

@pytest.mark.asyncio
    async def test_mixed_metadata_scenarios(self, db_session, thread_repo):
"""Test multiple threads with various metadata states."""
pass
user_id = "test-user-456"

                    # Create various threads
await self.create_test_thread(db_session, "thread_1", {"user_id": user_id})
await self.create_test_thread(db_session, "thread_2", None)  # NULL
await self.create_test_thread(db_session, "thread_3", {})  # Empty
await self.create_test_thread(db_session, "thread_4", {"user_id": "other-user"})
await self.create_test_thread(db_session, "thread_5", {"user_id": user_id, "extra": "data"})

                    # Query for specific user
threads = await thread_repo.find_by_user(db_session, user_id)

                    # Should find only threads 1 and 5
assert len(threads) == 2
thread_ids = {t.id for t in threads}
assert thread_ids == {"thread_1", "thread_5"}

@pytest.mark.asyncio
    async def test_uuid_normalization(self, db_session, thread_repo):
"""Test UUID format normalization."""
                        # Test with UUID string
uuid_str = "550e8400-e29b-41d4-a716-446655440000"

                        # Create thread with UUID as string
await self.create_test_thread( )
db_session,
"thread_uuid",
{"user_id": uuid_str}
                        

                        # Query with UUID string
threads = await thread_repo.find_by_user(db_session, uuid_str)
assert len(threads) == 1

                        # Query with UUID object (if it were passed)
import uuid as uuid_module
uuid_obj = uuid_module.UUID(uuid_str)
threads = await thread_repo.find_by_user(db_session, str(uuid_obj))
assert len(threads) == 1

@pytest.mark.asyncio
    async def test_whitespace_handling(self, db_session, thread_repo):
"""Test whitespace in user_id is handled."""
pass
                            # Create thread with whitespace in user_id
await self.create_test_thread( )
db_session,
"thread_space",
{"user_id": "  user-with-spaces  "}
                            

                            # Query with whitespace should normalize and find it
threads = await thread_repo.find_by_user(db_session, "  user-with-spaces  ")
assert len(threads) == 1

                            # Query without whitespace should also find it
threads = await thread_repo.find_by_user(db_session, "user-with-spaces")
assert len(threads) == 1

@pytest.mark.asyncio
    async def test_performance_with_many_threads(self, db_session, thread_repo):
"""Test performance with many threads."""
user_id = "perf-test-user"
other_user = "other-user"

                                # Create many threads
for i in range(50):
if i % 2 == 0:
await self.create_test_thread( )
db_session,
"formatted_string",
{"user_id": user_id}
                                        
else:
await self.create_test_thread( )
db_session,
"formatted_string",
{"user_id": other_user}
                                            

                                            # Query for specific user
import time
start = time.time()
threads = await thread_repo.find_by_user(db_session, user_id)
duration = time.time() - start

                                            # Should find 25 threads
assert len(threads) == 25

                                            # Should be reasonably fast (under 1 second even with fallback)
assert duration < 1.0, "formatted_string"

print("formatted_string")


class TestActualPostgreSQLBehavior:
    """Test simulating actual PostgreSQL JSONB behavior."""

@pytest.mark.asyncio
    async def test_jsonb_query_simulation(self):
"""Simulate what happens with PostgreSQL JSONB queries."""

        # Simulate thread data as it would be in PostgreSQL
threads_data = [ )
{"id": "t1", "metadata_": {"user_id": "user123"}},
{"id": "t2", "metadata_": None},  # NULL
{"id": "t3", "metadata_": {}},  # Empty
{"id": "t4", "metadata_": {"user_id": "user456"}},
{"id": "t5", "metadata_": {"user_id": 123}},  # Integer
        

def jsonb_extract(metadata, key):
"""Simulate PostgreSQL's ->> operator."""
pass
if metadata is None:
await asyncio.sleep(0)
return None
if not isinstance(metadata, dict):
return None
return str(metadata.get(key)) if key in metadata else None

            # Simulate query: WHERE metadata_->>'user_id' = 'user123'
target_user = "user123"
matched = []

for thread in threads_data:
extracted = jsonb_extract(thread["metadata_"], "user_id")
if extracted == target_user:
matched.append(thread)

                    # Should find only t1
assert len(matched) == 1
assert matched[0]["id"] == "t1"

print(" )
[U+2713] JSONB simulation: Correctly filtered threads")

                    # Now test with integer user_id normalization
target_user = "123"
matched = []

for thread in threads_data:
extracted = jsonb_extract(thread["metadata_"], "user_id")
if extracted == target_user:
matched.append(thread)

                            # Should find t5 after normalization
assert len(matched) == 1
assert matched[0]["id"] == "t5"

print("[U+2713] JSONB simulation: Integer user_id normalized correctly")


if __name__ == "__main__":
                                # Run the tests
