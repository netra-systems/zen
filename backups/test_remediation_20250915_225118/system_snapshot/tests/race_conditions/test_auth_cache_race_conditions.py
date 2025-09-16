"""Test AuthClientCache race condition fixes.

This focused test validates the user-scoped thread safety enhancements
to the AuthClientCache without complex dependencies.
"""
import asyncio
import pytest
import time
from netra_backend.app.clients.auth_client_cache import AuthClientCache
from shared.isolated_environment import IsolatedEnvironment

class AuthClientCacheRaceConditionsTests:
    """Test AuthClientCache race condition fixes."""

    @pytest.fixture
    def auth_cache(self):
        """Create AuthClientCache instance for testing."""
        return AuthClientCache(default_ttl=300)

    @pytest.mark.asyncio
    async def test_concurrent_user_cache_access(self, auth_cache):
        """Test concurrent access to user-scoped cache prevents race conditions."""
        users = [f'user_{i}' for i in range(10)]
        keys_per_user = 5

        async def set_user_data(user_id: str, key_suffix: int):
            """Set data for a specific user concurrently."""
            key = f'test_key_{key_suffix}'
            value = f'test_value_{user_id}_{key_suffix}_{time.time()}'
            await auth_cache.set_user_scoped(user_id, key, value)
            return (user_id, key, value)

        async def get_user_data(user_id: str, key_suffix: int):
            """Get data for a specific user concurrently."""
            key = f'test_key_{key_suffix}'
            value = await auth_cache.get_user_scoped(user_id, key)
            return (user_id, key, value)
        set_tasks = []
        expected_values = {}
        for user in users:
            for key_suffix in range(keys_per_user):
                task = set_user_data(user, key_suffix)
                set_tasks.append(task)
        set_results = await asyncio.gather(*set_tasks)
        for user_id, key, value in set_results:
            if user_id not in expected_values:
                expected_values[user_id] = {}
            expected_values[user_id][key] = value
        get_tasks = []
        for user in users:
            for key_suffix in range(keys_per_user):
                task = get_user_data(user, key_suffix)
                get_tasks.append(task)
        get_results = await asyncio.gather(*get_tasks)
        for user_id, key, retrieved_value in get_results:
            expected_value = expected_values[user_id][key]
            assert retrieved_value == expected_value, f'Race condition detected! User {user_id}, key {key}: expected {expected_value}, got {retrieved_value}'

    @pytest.mark.asyncio
    async def test_concurrent_user_cache_operations_isolation(self, auth_cache):
        """Test that concurrent operations on different users are isolated."""
        user1, user2 = ('user_1', 'user_2')
        operations_per_user = 20

        async def user_operations(user_id: str, op_count: int):
            """Perform mixed operations for a user."""
            results = []
            for i in range(op_count):
                key = f'isolation_key_{i}'
                value = f'isolation_value_{user_id}_{i}'
                await auth_cache.set_user_scoped(user_id, key, value)
                retrieved = await auth_cache.get_user_scoped(user_id, key)
                if i % 3 == 0:
                    deleted = await auth_cache.delete_user_scoped(user_id, key)
                    results.append((key, value, retrieved, deleted))
                else:
                    results.append((key, value, retrieved, None))
            return results
        user1_task = user_operations(user1, operations_per_user)
        user2_task = user_operations(user2, operations_per_user)
        user1_results, user2_results = await asyncio.gather(user1_task, user2_task)
        assert len(user1_results) == operations_per_user
        assert len(user2_results) == operations_per_user
        for key, original_value, retrieved_value, was_deleted in user1_results:
            if was_deleted is None:
                assert retrieved_value == original_value, f'User1 data corrupted: {key}'
        for key, original_value, retrieved_value, was_deleted in user2_results:
            if was_deleted is None:
                assert retrieved_value == original_value, f'User2 data corrupted: {key}'

    @pytest.mark.asyncio
    async def test_user_lock_isolation(self, auth_cache):
        """Test that user-specific locks provide proper isolation."""
        users = [f'user_{i}' for i in range(5)]
        locks = {}
        for user in users:
            lock1 = await auth_cache._get_user_lock(user)
            lock2 = await auth_cache._get_user_lock(user)
            assert lock1 is lock2, f'User {user} got different lock instances'
            locks[user] = lock1
        user_lock_ids = {user: id(lock) for user, lock in locks.items()}
        assert len(set(user_lock_ids.values())) == len(users), 'Users sharing locks - isolation broken'

    @pytest.mark.asyncio
    async def test_legacy_interface_compatibility(self, auth_cache):
        """Test that legacy interface still works alongside new user-scoped methods."""
        await auth_cache.set('legacy_key', 'legacy_value')
        legacy_value = await auth_cache.get('legacy_key')
        assert legacy_value == 'legacy_value', 'Legacy interface broken'
        await auth_cache.set_user_scoped('test_user', 'user_key', 'user_value')
        user_value = await auth_cache.get_user_scoped('test_user', 'user_key')
        assert user_value == 'user_value', 'User-scoped interface broken'
        legacy_value_after = await auth_cache.get('legacy_key')
        user_value_after = await auth_cache.get_user_scoped('test_user', 'user_key')
        assert legacy_value_after == 'legacy_value', 'Legacy value corrupted by user-scoped operations'
        assert user_value_after == 'user_value', 'User-scoped value corrupted by legacy operations'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')