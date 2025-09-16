"""Database Sync Test Helpers - Small Function Utilities

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)  
2. Business Goal: Provide 25-line compliant helper functions for database sync testing
3. Value Impact: Enables modular testing architecture that reduces technical debt
4. Revenue Impact: Faster debugging saves $5K+ monthly in development time

Module Architecture Compliance: Under 300 lines, functions under 8 lines
"""

import asyncio
from datetime import datetime


async def sync_user_to_backend(validator, user_id):
    """Sync user from Auth to Backend."""
    auth_user = await validator.auth_service.get_user(user_id)
    await validator.backend_service.sync_user_from_auth(auth_user)


async def insert_user_creation_event(validator, user_id):
    """Insert user creation event in ClickHouse."""
    event_data = {'event_type': 'user_created', 'source': 'auth_service'}
    await validator.clickhouse.insert_user_event(user_id, event_data)


async def verify_sync_consistency(validator, user_id):
    """Verify eventual consistency achieved."""
    is_synced = await validator.verify_auth_backend_sync(user_id)
    assert is_synced, "Eventual consistency failed for user sync"


async def verify_metrics_consistency(validator, user_id, expected_count):
    """Verify metrics consistency."""
    metrics_accurate = await validator.verify_clickhouse_accuracy(user_id, expected_count)
    assert metrics_accurate, "Eventual consistency failed for metrics"


async def create_sync_task(validator, index):
    """Create individual sync task."""
    from tests.e2e.database_sync_fixtures import (
        create_performance_user_data,
    )
    user_data = create_performance_user_data(index)
    user_id = await validator.auth_service.create_user(user_data)
    auth_user = await validator.auth_service.get_user(user_id)
    await validator.backend_service.sync_user_from_auth(auth_user)
    return user_id


async def create_migration_users(sync_validator):
    """Create migration test users."""
    from tests.e2e.database_sync_fixtures import (
        create_migration_user_data,
    )
    test_users = []
    for i in range(3):
        user_data = create_migration_user_data(i)
        user_id = await sync_validator.auth_service.create_user(user_data)
        test_users.append(user_id)
    return test_users


async def execute_migration(sync_validator, test_users):
    """Execute test migration for all users."""
    for user_id in test_users:
        auth_user = await sync_validator.auth_service.get_user(user_id)
        success = await sync_validator.backend_service.sync_user_from_auth(auth_user)
        if not success:
            return False
    return True


async def verify_migration_integrity(sync_validator, test_users):
    """Verify migration integrity for all users."""
    for user_id in test_users:
        is_synced = await sync_validator.verify_auth_backend_sync(user_id)
        assert is_synced, f"User {user_id} migration integrity failed"


def measure_performance_duration(start_time):
    """Calculate performance duration."""
    return (datetime.now() - start_time).total_seconds()


def validate_performance_results(duration, results, expected_count):
    """Validate performance test results."""
    assert duration < 5.0, f"Sync took {duration}s, expected <5s"
    assert all(not isinstance(r, Exception) for r in results), "Sync failures detected"
    assert len(results) == expected_count, "Not all users synced"


async def verify_auth_backend_consistency(sync_validator, user_id):
    """Verify Auth-Backend sync consistency."""
    is_synced = await sync_validator.verify_auth_backend_sync(user_id)
    assert is_synced, "Auth-Backend user sync failed"


async def verify_backend_user_exists(sync_validator, user_id, test_user_data):
    """Verify Backend user exists with correct data."""
    backend_user = await sync_validator.backend_service.get_user(user_id)
    assert backend_user is not None, "User not found in Backend"
    assert backend_user['email'] == test_user_data['email'], "Email mismatch"


async def verify_clickhouse_metrics(sync_validator, user_id, expected_count):
    """Verify ClickHouse metrics accuracy."""
    is_accurate = await sync_validator.verify_clickhouse_accuracy(user_id, expected_count)
    assert is_accurate, "ClickHouse metrics not accurate"


async def verify_event_types(sync_validator, user_id, expected_event_type):
    """Verify event types in metrics."""
    metrics = await sync_validator.clickhouse.get_user_metrics(user_id)
    assert all(m['event_type'] == expected_event_type for m in metrics), "Event type mismatch"


async def setup_cache_test(sync_validator, user_id, test_user_data):
    """Setup cache test with user data."""
    import json
    cache_key = f"user:{user_id}"
    user_json = json.dumps(test_user_data)
    await sync_validator.redis.set(cache_key, user_json, ex=300)
    return cache_key, user_json


async def verify_initial_cache(sync_validator, cache_key, user_json):
    """Verify initial cache consistency."""
    is_consistent = await sync_validator.verify_cache_consistency(cache_key, user_json)
    assert is_consistent, "Initial cache not consistent"


async def update_user_and_invalidate_cache(sync_validator, user_id, test_user_data, cache_key):
    """Update user and invalidate cache."""
    updated_data = test_user_data.copy()
    updated_data['full_name'] = "Updated User Name"
    await sync_validator.auth_service.update_user(user_id, updated_data)
    await sync_validator.redis.delete(cache_key)


async def verify_cache_invalidation(sync_validator, cache_key):
    """Verify cache was properly invalidated."""
    cached_value = await sync_validator.redis.get(cache_key)
    assert cached_value is None, "Cache not properly invalidated"
