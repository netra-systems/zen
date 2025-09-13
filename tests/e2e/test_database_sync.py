"""Phase 5: Database Sync Testing - Cross-Database Consistency



CRITICAL CONTEXT: Data consistency across PostgreSQL, ClickHouse, and Redis

prevents customer data corruption and support tickets that impact revenue.



SUCCESS CRITERIA:

- User data consistency between Auth and Backend services

- Metrics data accuracy in ClickHouse

- Cache consistency with database changes

- Migration safety and rollback capability

- Eventual consistency patterns validated



Business Value Justification (BVJ):

1. Segment: All customer segments (Free, Early, Mid, Enterprise)

2. Business Goal: Prevent data inconsistencies that cause support tickets and churn

3. Value Impact: Reduces support costs by 80% through proactive consistency testing

4. Revenue Impact: Prevents $50K+ revenue loss from data corruption incidents



Module Architecture Compliance: Under 300 lines, functions under 8 lines

"""



import asyncio

from datetime import datetime

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.database_sync_fixtures import (

    DatabaseSyncValidator,

    create_eventual_consistency_user,

    create_test_user_data,

)

from tests.e2e.database_sync_helpers import (

    create_migration_users,

    create_sync_task,

    insert_user_creation_event,

    measure_performance_duration,

    setup_cache_test,

    sync_user_to_backend,

    update_user_and_invalidate_cache,

    execute_migration,

    validate_performance_results,

    verify_auth_backend_consistency,

    verify_backend_user_exists,

    verify_cache_invalidation,

    verify_clickhouse_metrics,

    verify_event_types,

    verify_initial_cache,

    verify_metrics_consistency,

    verify_migration_integrity,

    verify_sync_consistency,

)





@pytest.mark.e2e

class TestDatabaseSync:

    """Phase 5: Database sync consistency tests."""

    

    @pytest.fixture

    @pytest.mark.e2e

    def test_user_data(self):

        """Generate test user data."""

        return create_test_user_data()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_auth_backend_user_sync(self, sync_validator, test_user_data):

        """Test 1: User data consistency between Auth and Backend."""

        user_id = await sync_validator.auth_service.create_user(test_user_data)

        auth_user = await sync_validator.auth_service.get_user(user_id)

        await sync_validator.backend_service.sync_user_from_auth(auth_user)

        await verify_auth_backend_consistency(sync_validator, user_id)

        await verify_backend_user_exists(sync_validator, user_id, test_user_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_clickhouse_metrics_sync(self, sync_validator, test_user_data):

        """Test 2: Metrics data accuracy in ClickHouse."""

        user_id = await sync_validator.auth_service.create_user(test_user_data)

        auth_user = await sync_validator.auth_service.get_user(user_id)

        await sync_validator.backend_service.sync_user_from_auth(auth_user)

        await self._insert_test_metrics(sync_validator, user_id)

        await verify_clickhouse_metrics(sync_validator, user_id, 2)

        await verify_event_types(sync_validator, user_id, 'tool_usage')

    

    async def _insert_test_metrics(self, sync_validator, user_id):

        """Insert test metrics events."""

        event_data = {'event_type': 'tool_usage', 'tool_name': 'optimizer'}

        await sync_validator.clickhouse.insert_user_event(user_id, event_data)

        await sync_validator.clickhouse.insert_user_event(user_id, event_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_redis_cache_invalidation(self, sync_validator, test_user_data):

        """Test 3: Cache consistency with database changes."""

        user_id = await sync_validator.auth_service.create_user(test_user_data)

        cache_key, user_json = await setup_cache_test(sync_validator, user_id, test_user_data)

        await verify_initial_cache(sync_validator, cache_key, user_json)

        await update_user_and_invalidate_cache(sync_validator, user_id, test_user_data, cache_key)

        await verify_cache_invalidation(sync_validator, cache_key)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_database_migration_integrity(self, sync_validator):

        """Test 4: Migration safety and rollback."""

        test_users = await create_migration_users(sync_validator)

        migration_success = await execute_migration(sync_validator, test_users)

        assert migration_success, "Migration failed"

        await verify_migration_integrity(sync_validator, test_users)





@pytest.mark.e2e

class TestDatabaseSyncPerformance:

    """Performance tests for database synchronization."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_concurrent_user_sync_performance(self):

        """Test concurrent user synchronization performance."""

        validator = DatabaseSyncValidator()

        sync_tasks = [create_sync_task(validator, i) for i in range(20)]

        start_time = datetime.now()

        results = await asyncio.gather(*sync_tasks, return_exceptions=True)

        duration = measure_performance_duration(start_time)

        validate_performance_results(duration, results, 20)





@pytest.mark.e2e

class TestEventualConsistency:

    """Test eventual consistency patterns."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_eventual_consistency_convergence(self):

        """Test eventual consistency convergence across services."""

        validator = DatabaseSyncValidator()

        user_data = create_eventual_consistency_user()

        user_id = await validator.auth_service.create_user(user_data)

        await asyncio.sleep(0.1)  # Simulate network delay

        await sync_user_to_backend(validator, user_id)

        await asyncio.sleep(0.1)  # Simulate processing delay

        await insert_user_creation_event(validator, user_id)

        await verify_sync_consistency(validator, user_id)

        await verify_metrics_consistency(validator, user_id, 1)

