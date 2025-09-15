"""Example Isolated Database Tests

Demonstrates comprehensive database isolation system usage.
Shows patterns for reliable, fast, isolated testing.

**Business Value Justification (BVJ):**
- Segment: Engineering Quality Example
- Business Goal: Demonstrate 100% reliable isolated testing patterns
- Value Impact: Reference implementation for all test development
- Revenue Impact: Faster development cycles, zero test pollution issues

Each function  <= 8 lines, file  <= 300 lines.
"""
import asyncio
from shared.isolated_environment import IsolatedEnvironment
import sys
from datetime import UTC, datetime
from pathlib import Path
import pytest
from sqlalchemy import text
from netra_backend.tests.isolated_test_config import isolated_clickhouse, isolated_full_stack, isolated_postgres, isolated_test_config, with_database_snapshots, with_isolated_postgres

class TestPostgreSQLIsolation:
    """Test PostgreSQL database isolation functionality."""

    @pytest.mark.asyncio
    async def test_basic_isolation(self, isolated_postgres):
        """Test basic PostgreSQL isolation works correctly."""
        session, config = isolated_postgres
        result = await session.execute(text('SELECT current_database()'))
        db_name = result.scalar()
        assert config.test_id.replace('-', '_') in db_name
        result = await session.execute(text("\n            SELECT count(*) FROM information_schema.tables \n            WHERE table_schema = 'public'\n        "))
        table_count = result.scalar()
        assert table_count >= 3

    @pytest.mark.asyncio
    async def test_seeded_data(self):
        """Test PostgreSQL with seeded test data."""
        async with with_isolated_postgres('seeded_test', 'user_management', 'minimal') as (session, config):
            result = await session.execute(text('SELECT count(*) FROM test_users'))
            user_count = result.scalar()
            assert user_count == 3
            result = await session.execute(text('SELECT email FROM test_users LIMIT 1'))
            email = result.scalar()
            assert '@' in email and '.' in email

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, isolated_postgres):
        """Test transaction rollback isolation."""
        session, config = isolated_postgres
        isolator = config._isolators['postgres']
        result = await session.execute(text('SELECT count(*) FROM test_users'))
        initial_count = result.scalar()
        async with isolator.rollback_test_context(config.test_id) as rollback_session:
            await rollback_session.execute(text("\n                INSERT INTO test_users (email, full_name) VALUES ('rollback@test.com', 'Rollback User')\n            "))
            result = await rollback_session.execute(text('SELECT count(*) FROM test_users'))
            count_in_transaction = result.scalar()
            assert count_in_transaction == initial_count + 1
        await session.commit()
        result = await session.execute(text('SELECT count(*) FROM test_users'))
        final_count = result.scalar()
        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_data_validation(self, isolated_postgres):
        """Test database state validation."""
        session, config = isolated_postgres
        validation_results = await config.validate_database_state()
        assert 'postgres' in validation_results
        postgres_results = validation_results['postgres']
        assert postgres_results['status'] in ['passed', 'warning']
        assert postgres_results['summary']['failed_checks'] == 0

class TestClickHouseIsolation:
    """Test ClickHouse database isolation functionality."""

    @pytest.mark.asyncio
    async def test_basic_clickhouse_isolation(self, isolated_clickhouse):
        """Test basic ClickHouse isolation."""
        client, database_name, config = isolated_clickhouse
        assert config.test_id.replace('-', '_') in database_name
        result = client.query('SELECT 1')
        assert result.result_rows[0][0] == 1
        tables = client.query(f'SHOW TABLES FROM {database_name}')
        table_names = [row[0] for row in tables.result_rows]
        assert 'test_logs' in table_names

    @pytest.mark.asyncio
    async def test_clickhouse_data_insertion(self, isolated_clickhouse):
        """Test ClickHouse data insertion and querying."""
        client, database_name, config = isolated_clickhouse
        test_data = [[1, datetime.now(UTC), 'INFO', 'Test message 1', 'test'], [2, datetime.now(UTC), 'ERROR', 'Test message 2', 'test']]
        client.insert(f'{database_name}.test_logs', test_data)
        result = client.query(f'SELECT count(*) FROM {database_name}.test_logs')
        count = result.result_rows[0][0]
        assert count == 2
        result = client.query(f'SELECT level FROM {database_name}.test_logs WHERE id = 2')
        level = result.result_rows[0][0]
        assert level == 'ERROR'

class TestFullStackIsolation:
    """Test full database stack isolation (PostgreSQL + ClickHouse)."""

    @pytest.mark.asyncio
    async def test_cross_database_consistency(self, isolated_full_stack):
        """Test consistency between PostgreSQL and ClickHouse."""
        test_env = isolated_full_stack
        postgres_session = test_env['postgres_session']
        clickhouse_client = test_env['clickhouse_client']
        clickhouse_database = test_env['clickhouse_database']
        pg_result = await postgres_session.execute(text('SELECT count(*) FROM test_users'))
        pg_user_count = pg_result.scalar()
        ch_result = clickhouse_client.query(f'\n            SELECT uniq(user_id) FROM {clickhouse_database}.test_events\n        ')
        ch_user_count = ch_result.result_rows[0][0]
        assert ch_user_count <= pg_user_count
        assert ch_user_count > 0

    @pytest.mark.asyncio
    async def test_snapshot_restoration(self, isolated_full_stack):
        """Test database snapshot restoration."""
        test_env = isolated_full_stack
        postgres_session = test_env['postgres_session']
        config = test_env['config']
        snapshots = test_env['snapshots']
        result = await postgres_session.execute(text('SELECT count(*) FROM test_users'))
        initial_count = result.scalar()
        await postgres_session.execute(text("\n            INSERT INTO test_users (email, full_name) VALUES ('snapshot@test.com', 'Snapshot User')\n        "))
        await postgres_session.commit()
        result = await postgres_session.execute(text('SELECT count(*) FROM test_users'))
        modified_count = result.scalar()
        assert modified_count == initial_count + 1
        await config.restore_snapshot(snapshots['postgres'])
        await postgres_session.commit()
        result = await postgres_session.execute(text('SELECT count(*) FROM test_users'))
        restored_count = result.scalar()
        assert restored_count == initial_count

class TestPerformanceIsolation:
    """Test performance scenarios with isolated databases."""

    @pytest.mark.asyncio
    async def test_large_dataset_isolation(self):
        """Test isolation with larger datasets."""
        async with with_isolated_postgres('large_test', 'user_management', 'performance') as (session, config):
            result = await session.execute(text('SELECT count(*) FROM test_users'))
            user_count = result.scalar()
            assert user_count == 100
            start_time = datetime.now(UTC)
            result = await session.execute(text('\n                SELECT u.full_name, count(t.id) as thread_count\n                FROM test_users u\n                LEFT JOIN test_threads t ON u.id = t.user_id\n                GROUP BY u.id, u.full_name\n                ORDER BY thread_count DESC\n                LIMIT 10\n            '))
            end_time = datetime.now(UTC)
            duration_ms = (end_time - start_time).total_seconds() * 1000
            assert duration_ms < 1000
            results = result.fetchall()
            assert len(results) == 10

    @pytest.mark.asyncio
    async def test_concurrent_isolation(self):
        """Test multiple isolated databases can run concurrently."""

        async def create_isolated_test(test_name: str) -> int:
            async with with_isolated_postgres(test_name, 'basic', 'minimal') as (session, config):
                result = await session.execute(text('SELECT count(*) FROM test_users'))
                return result.scalar()
        tasks = [create_isolated_test(f'concurrent_test_{i}') for i in range(3)]
        results = await asyncio.gather(*tasks)
        assert all((count == 3 for count in results))

class TestSnapshotSystem:
    """Test database snapshot system functionality."""

    @pytest.mark.asyncio
    async def test_snapshot_creation_and_restoration(self):
        """Test complete snapshot lifecycle."""
        async with with_database_snapshots('snapshot_lifecycle') as test_env:
            postgres_session = test_env['postgres_session']
            reset_func = test_env['reset_to_clean_state']
            await postgres_session.execute(text("\n                INSERT INTO test_users (email, full_name) \n                VALUES ('snapshot1@test.com', 'User 1'), ('snapshot2@test.com', 'User 2')\n            "))
            await postgres_session.commit()
            result = await postgres_session.execute(text('SELECT count(*) FROM test_users'))
            count_with_data = result.scalar()
            assert count_with_data >= 2
            await reset_func()
            result = await postgres_session.execute(text('SELECT count(*) FROM test_users'))
            count_after_reset = result.scalar()
            assert count_after_reset < count_with_data

    @pytest.mark.asyncio
    async def test_multiple_snapshots(self, isolated_postgres):
        """Test creating and managing multiple snapshots."""
        session, config = isolated_postgres
        snapshot1 = await config.create_snapshot('postgres', 'empty_state')
        await session.execute(text("\n            INSERT INTO test_users (email, full_name) VALUES ('user1@test.com', 'User 1')\n        "))
        await session.commit()
        snapshot2 = await config.create_snapshot('postgres', 'with_user')
        await session.execute(text("\n            INSERT INTO test_users (email, full_name) VALUES ('user2@test.com', 'User 2')\n        "))
        await session.commit()
        result = await session.execute(text('SELECT count(*) FROM test_users'))
        current_count = result.scalar()
        await config.restore_snapshot(snapshot1)
        result = await session.execute(text('SELECT count(*) FROM test_users'))
        restored_count = result.scalar()
        assert restored_count < current_count

class TestValidationSystem:
    """Test database state validation system."""

    @pytest.mark.asyncio
    async def test_isolation_validation(self, isolated_postgres):
        """Test isolation validation works correctly."""
        session, config = isolated_postgres
        validation_results = await config.validate_database_state()
        postgres_results = validation_results['postgres']
        isolation_checks = [detail for detail in postgres_results['details'] if 'isolation' in detail['check_name']]
        assert len(isolation_checks) > 0
        isolation_passed = any((check['passed'] for check in isolation_checks))
        assert isolation_passed

    @pytest.mark.asyncio
    async def test_data_consistency_validation(self, isolated_full_stack):
        """Test data consistency validation across databases."""
        test_env = isolated_full_stack
        config = test_env['config']
        validation_results = await config.validate_database_state()
        assert 'postgres' in validation_results
        assert 'clickhouse' in validation_results
        pg_status = validation_results['postgres']['status']
        ch_status = validation_results['clickhouse']['status']
        assert pg_status in ['passed', 'warning']
        assert ch_status in ['passed', 'warning']
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')