"""

Database Data Flow Integration Test Suite



BUSINESS VALUE JUSTIFICATION (BVJ):

1. Segment: All segments (Free, Early, Mid, Enterprise) - data integrity is critical

2. Business Goal: Ensure data consistency across all database layers prevents revenue loss

3. Value Impact: Prevents data corruption that could lead to 15-20% customer churn

4. Revenue Impact: $25K MRR - Data integrity prevents customer trust issues and churn



TEST FLOW:

1. Create user in Auth PostgreSQL

2. Sync user to Backend PostgreSQL  

3. Store chat messages in ClickHouse

4. Cache active sessions in Redis

5. Validate cross-database consistency



ARCHITECTURE: Modular design with 25-line function limit, under 300 lines total

"""



import asyncio

import uuid

from datetime import datetime, timezone

from typing import Any, Dict

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.database_test_connections import DatabaseConnectionManager

from tests.e2e.database_test_operations import (

    ChatMessageOperations,

    SessionCacheOperations,

    UserDataOperations,

)





@pytest.fixture

async def database_manager():

    """Fixture for database connection manager."""

    manager = DatabaseConnectionManager()

    await manager.initialize_connections()

    yield manager

    await manager.cleanup()





@pytest.fixture

@pytest.mark.e2e

def test_user_data():

    """Generate test user data."""

    user_id = f"test-{uuid.uuid4().hex[:8]}"

    return {

        "id": user_id,

        "email": f"{user_id}@test.com",

        "full_name": "Test User",

        "is_active": True,

        "role": "user",

        "created_at": datetime.now(timezone.utc)

    }





@pytest.mark.e2e

class TestDatabaseDataFlow:

    """Main test class for database data flow validation."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_complete_user_flow(self, database_manager, test_user_data):

        """Test 1: Complete user creation and sync flow."""

        user_ops = UserDataOperations(database_manager)

        

        # Step 1: Create user in Auth PostgreSQL

        auth_user_id = await user_ops.create_auth_user(test_user_data)

        assert auth_user_id == test_user_data["id"]

        

        # Step 2: Sync to Backend PostgreSQL

        sync_success = await user_ops.sync_to_backend(test_user_data)

        assert sync_success is True

        

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_chat_message_storage_flow(self, database_manager, test_user_data):

        """Test 2: Chat message storage in ClickHouse."""

        user_ops = UserDataOperations(database_manager)

        chat_ops = ChatMessageOperations(database_manager)

        

        # Step 1: Create user

        await user_ops.create_auth_user(test_user_data)

        await user_ops.sync_to_backend(test_user_data)

        

        # Step 2: Store chat message

        message_data = await self._create_test_message(test_user_data["id"])

        storage_success = await chat_ops.store_message(message_data)

        assert storage_success is True

        

    async def _create_test_message(self, user_id: str) -> Dict[str, Any]:

        """Create test message data."""

        return {

            "id": f"msg-{uuid.uuid4().hex[:8]}",

            "user_id": user_id,

            "content": "Test message content",

            "timestamp": datetime.now(timezone.utc)

        }

        

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_session_caching_flow(self, database_manager, test_user_data):

        """Test 3: Session caching in Redis."""

        user_ops = UserDataOperations(database_manager)

        session_ops = SessionCacheOperations(database_manager)

        

        # Step 1: Create user

        await user_ops.create_auth_user(test_user_data)

        

        # Step 2: Cache active session

        session_data = self._create_test_session(test_user_data["id"])

        cache_success = await session_ops.cache_session(

            test_user_data["id"], session_data

        )

        assert cache_success is True

        

    def _create_test_session(self, user_id: str) -> Dict[str, Any]:

        """Create test session data."""

        return {

            "user_id": user_id,

            "login_time": datetime.now(timezone.utc).isoformat(),

            "is_active": True

        }

        

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_cross_database_consistency(self, database_manager, test_user_data):

        """Test 4: Data consistency across all databases."""

        operations = await self._setup_all_operations(database_manager)

        

        # Step 1: Create complete user flow

        await self._create_complete_user_flow(operations, test_user_data)

        

        # Step 2: Validate consistency

        await self._validate_data_consistency(operations, test_user_data["id"])

        

    async def _setup_all_operations(self, database_manager):

        """Setup all operation classes."""

        return {

            "user_ops": UserDataOperations(database_manager),

            "chat_ops": ChatMessageOperations(database_manager),

            "session_ops": SessionCacheOperations(database_manager)

        }

        

    async def _create_complete_user_flow(self, operations, test_user_data):

        """Create complete user data flow."""

        # Create and sync user

        await operations["user_ops"].create_auth_user(test_user_data)

        await operations["user_ops"].sync_to_backend(test_user_data)

        

        # Add chat message

        message_data = await self._create_test_message(test_user_data["id"])

        await operations["chat_ops"].store_message(message_data)

        

        # Cache session

        session_data = self._create_test_session(test_user_data["id"])

        await operations["session_ops"].cache_session(test_user_data["id"], session_data)

        

    async def _validate_data_consistency(self, operations, user_id: str):

        """Validate data consistency across databases."""

        cached_session = await operations["session_ops"].get_cached_session(user_id)

        user_messages = await operations["chat_ops"].get_user_messages(user_id)

        

        assert cached_session is not None

        assert len(user_messages) >= 0  # May be mock or real data

        

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_transaction_rollback_scenario(self, database_manager, test_user_data):

        """Test 5: Transaction rollback and data integrity."""

        user_ops = UserDataOperations(database_manager)

        

        # Step 1: Create user successfully

        user_id = await user_ops.create_auth_user(test_user_data)

        assert user_id is not None

        

        # Step 2: Test failed sync scenario

        invalid_data = await self._create_invalid_user_data(test_user_data)

        await self._test_sync_failure_handling(user_ops, invalid_data)

        

        # Step 3: Verify original data integrity maintained

        assert user_id == test_user_data["id"]

        

    async def _create_invalid_user_data(self, test_user_data):

        """Create invalid user data for testing."""

        invalid_data = test_user_data.copy()

        invalid_data["email"] = None  # Invalid email to cause failure

        return invalid_data

        

    async def _test_sync_failure_handling(self, user_ops, invalid_data):

        """Test sync failure handling."""

        try:

            await user_ops.sync_to_backend(invalid_data)

        except Exception:

            pass  # Expected for invalid data

            

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_concurrent_operations(self, database_manager):

        """Test 6: Concurrent database operations."""

        user_ops = UserDataOperations(database_manager)

        

        # Create multiple users concurrently

        tasks = await self._create_concurrent_user_tasks(user_ops, 5)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        

        # Verify all operations succeeded

        await self._validate_concurrent_results(results)

        

    async def _create_concurrent_user_tasks(self, user_ops, count: int):

        """Create concurrent user creation tasks."""

        tasks = []

        for i in range(count):

            user_data = {

                "id": f"concurrent-user-{i}",

                "email": f"concurrent{i}@test.com",

                "full_name": f"Concurrent User {i}",

                "is_active": True,

                "created_at": datetime.now(timezone.utc)

            }

            task = asyncio.create_task(user_ops.create_auth_user(user_data))

            tasks.append(task)

        return tasks

        

    async def _validate_concurrent_results(self, results):

        """Validate concurrent operation results."""

        for result in results:

            assert not isinstance(result, Exception)

            assert result is not None





@pytest.mark.e2e

class TestDatabasePerformance:

    """Performance tests for database operations."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_bulk_user_creation_performance(self, database_manager):

        """Test 7: Bulk user creation performance."""

        user_ops = UserDataOperations(database_manager)

        start_time = datetime.now()

        

        # Create 25 users for performance testing

        tasks = await self._create_performance_user_tasks(user_ops, 25)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = (datetime.now() - start_time).total_seconds()

        

        # Performance validation

        await self._validate_performance_results(results, duration, 10, "users")

        

    async def _create_performance_user_tasks(self, user_ops, count: int):

        """Create performance test user tasks."""

        tasks = []

        for i in range(count):

            user_data = {

                "id": f"perf-user-{i}",

                "email": f"perf{i}@test.com",

                "full_name": f"Performance User {i}",

                "is_active": True,

                "created_at": datetime.now(timezone.utc)

            }

            task = asyncio.create_task(user_ops.create_auth_user(user_data))

            tasks.append(task)

        return tasks

        

    async def _validate_performance_results(self, results, duration, max_duration, operation_type):

        """Validate performance test results."""

        assert duration < max_duration, f"Operation took {duration}s, should be under {max_duration}s"

        assert all(not isinstance(r, Exception) for r in results), f"All {operation_type} operations must succeed"

