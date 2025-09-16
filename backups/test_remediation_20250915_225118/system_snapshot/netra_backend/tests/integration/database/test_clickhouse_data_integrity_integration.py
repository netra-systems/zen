"""
Test ClickHouse Data Integrity - Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Ensure 100% data consistency and reliability  
- Value Impact: Prevents data corruption incidents (saves $10K+ per incident)
- Strategic Impact: Builds customer trust in analytics accuracy

This test suite validates ClickHouse data integrity, consistency, and reliability
with real database connections under various operational scenarios.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from netra_backend.app.db.clickhouse import get_clickhouse_client, get_clickhouse_service
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.configuration_validator import validate_test_config

class ClickHouseDataIntegrityIntegrationTests(BaseIntegrationTest):
    """Test ClickHouse data integrity and consistency features."""

    def setup_method(self):
        """Setup test environment and validate configuration."""
        validate_test_config('backend')
        self.test_table = f'integrity_test_{uuid.uuid4().hex[:8]}'

    async def cleanup_table(self):
        """Cleanup test table after test completion."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'DROP TABLE IF EXISTS {self.test_table}')
        except Exception as e:
            print(f'Warning: Failed to cleanup table {self.test_table}: {e}')

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_consistency_across_partitions(self):
        """Test data consistency across ClickHouse partitions.
        
        Critical for ensuring analytics data remains consistent across time partitions.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_table} (\n                    id UInt64,\n                    user_id String,\n                    event_date Date,\n                    event_timestamp DateTime64(3),\n                    metric_value Float64,\n                    category String\n                ) ENGINE = MergeTree()\n                PARTITION BY toYYYYMM(event_date)\n                ORDER BY (user_id, event_date, id)\n                ')
                base_date = datetime(2024, 1, 15)
                test_data = []
                for month_offset in range(3):
                    for day_offset in range(5):
                        for record_id in range(10):
                            event_date = base_date + timedelta(days=month_offset * 30 + day_offset)
                            test_data.append({'id': month_offset * 50 + day_offset * 10 + record_id, 'user_id': f'user_{record_id % 3}', 'event_date': event_date.strftime('%Y-%m-%d'), 'event_timestamp': event_date.strftime('%Y-%m-%d %H:%M:%S'), 'metric_value': (record_id + 1) * 10.5, 'category': f'category_{month_offset}'})
                for data in test_data:
                    await client.execute(f'\n                        INSERT INTO {self.test_table} \n                        (id, user_id, event_date, event_timestamp, metric_value, category)\n                        VALUES (%(id)s, %(user_id)s, %(event_date)s, %(event_timestamp)s, \n                               %(metric_value)s, %(category)s)\n                    ', data)
                await asyncio.sleep(0.3)
                total_count = await client.execute(f'SELECT COUNT(*) as count FROM {self.test_table}')
                expected_total = 3 * 5 * 10
                assert total_count[0]['count'] == expected_total, f'Expected {expected_total} records'
                partition_counts = await client.execute(f'\n                    SELECT toYYYYMM(event_date) as partition_month, COUNT(*) as count\n                    FROM {self.test_table}\n                    GROUP BY partition_month\n                    ORDER BY partition_month\n                ')
                assert len(partition_counts) == 3, 'Should have 3 partitions'
                for partition in partition_counts:
                    assert partition['count'] == 50, f'Each partition should have 50 records'
                for month_offset in range(3):
                    partition_data = await client.execute(f"\n                        SELECT user_id, COUNT(*) as count, AVG(metric_value) as avg_metric\n                        FROM {self.test_table}\n                        WHERE category = 'category_{month_offset}'\n                        GROUP BY user_id\n                        ORDER BY user_id\n                    ")
                    user_counts = {row['user_id']: row['count'] for row in partition_data}
                    expected_user_counts = {'user_0': 10, 'user_1': 10, 'user_2': 10}
                    total_partition_records = sum(user_counts.values())
                    assert total_partition_records == 50, f'Partition {month_offset} should have 50 total records'
        finally:
            await self.cleanup_table()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_deduplication_and_idempotency(self):
        """Test data deduplication and idempotent operations.
        
        Ensures duplicate data insertion doesn't corrupt analytics results.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_table} (\n                    transaction_id String,\n                    user_id String,\n                    amount Float64,\n                    timestamp DateTime64(3),\n                    version UInt32\n                ) ENGINE = ReplacingMergeTree(version)\n                PARTITION BY toYYYYMM(timestamp)\n                ORDER BY (user_id, transaction_id)\n                ')
                base_data = {'transaction_id': 'txn_001', 'user_id': 'dedup_user', 'amount': 100.5, 'timestamp': '2024-01-15 10:00:00', 'version': 1}
                await client.execute(f'\n                    INSERT INTO {self.test_table} \n                    (transaction_id, user_id, amount, timestamp, version)\n                    VALUES (%(transaction_id)s, %(user_id)s, %(amount)s, %(timestamp)s, %(version)s)\n                ', base_data)
                duplicate_data = base_data.copy()
                await client.execute(f'\n                    INSERT INTO {self.test_table} \n                    (transaction_id, user_id, amount, timestamp, version)\n                    VALUES (%(transaction_id)s, %(user_id)s, %(amount)s, %(timestamp)s, %(version)s)\n                ', duplicate_data)
                updated_data = base_data.copy()
                updated_data['amount'] = 150.75
                updated_data['version'] = 2
                await client.execute(f'\n                    INSERT INTO {self.test_table} \n                    (transaction_id, user_id, amount, timestamp, version)\n                    VALUES (%(transaction_id)s, %(user_id)s, %(amount)s, %(timestamp)s, %(version)s)\n                ', updated_data)
                await asyncio.sleep(0.5)
                await client.execute(f'OPTIMIZE TABLE {self.test_table} FINAL')
                results = await client.execute(f"\n                    SELECT transaction_id, user_id, amount, version, COUNT(*) as count\n                    FROM {self.test_table}\n                    WHERE transaction_id = 'txn_001'\n                    GROUP BY transaction_id, user_id, amount, version\n                    ORDER BY version DESC\n                ")
                assert len(results) == 1, 'Should have only one record after deduplication'
                assert results[0]['amount'] == 150.75, 'Should have the updated amount'
                assert results[0]['version'] == 2, 'Should have the latest version'
                assert results[0]['count'] == 1, 'Should have exactly one record'
        finally:
            await self.cleanup_table()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_integrity_under_concurrent_updates(self):
        """Test data integrity under concurrent update operations.
        
        Critical for multi-user platform ensuring data doesn't get corrupted.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_table} (\n                    counter_id String,\n                    user_id String,\n                    counter_value UInt64,\n                    update_timestamp DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (counter_id, user_id, update_timestamp)\n                ')
                counter_ids = ['counter_a', 'counter_b', 'counter_c']
                for counter_id in counter_ids:
                    await client.execute(f"\n                        INSERT INTO {self.test_table} (counter_id, user_id, counter_value)\n                        VALUES (%(counter_id)s, 'system', 0)\n                    ", {'counter_id': counter_id})

                async def update_counter(counter_id: str, user_id: str, increment_count: int):
                    """Perform multiple counter increments for a specific counter and user."""
                    async with get_clickhouse_client(bypass_manager=True) as update_client:
                        for i in range(increment_count):
                            await update_client.execute(f'\n                                INSERT INTO {self.test_table} (counter_id, user_id, counter_value)\n                                VALUES (%(counter_id)s, %(user_id)s, %(counter_value)s)\n                            ', {'counter_id': counter_id, 'user_id': user_id, 'counter_value': i + 1})
                            await asyncio.sleep(0.01)
                concurrent_operations = [update_counter('counter_a', 'user_1', 10), update_counter('counter_a', 'user_2', 8), update_counter('counter_b', 'user_1', 12), update_counter('counter_b', 'user_3', 6), update_counter('counter_c', 'user_2', 15), update_counter('counter_c', 'user_3', 9)]
                await asyncio.gather(*concurrent_operations)
                await asyncio.sleep(0.3)
                integrity_results = await client.execute(f"\n                    SELECT \n                        counter_id,\n                        user_id,\n                        COUNT(*) as update_count,\n                        MAX(counter_value) as max_value,\n                        COUNT(DISTINCT counter_value) as unique_values\n                    FROM {self.test_table}\n                    WHERE user_id != 'system'\n                    GROUP BY counter_id, user_id\n                    ORDER BY counter_id, user_id\n                ")
                expected_results = {('counter_a', 'user_1'): {'count': 10, 'max_value': 10}, ('counter_a', 'user_2'): {'count': 8, 'max_value': 8}, ('counter_b', 'user_1'): {'count': 12, 'max_value': 12}, ('counter_b', 'user_3'): {'count': 6, 'max_value': 6}, ('counter_c', 'user_2'): {'count': 15, 'max_value': 15}, ('counter_c', 'user_3'): {'count': 9, 'max_value': 9}}
                for result in integrity_results:
                    key = (result['counter_id'], result['user_id'])
                    expected = expected_results[key]
                    assert result['update_count'] == expected['count'], f"{key}: expected {expected['count']} updates, got {result['update_count']}"
                    assert result['max_value'] == expected['max_value'], f"{key}: expected max value {expected['max_value']}, got {result['max_value']}"
                    assert result['unique_values'] == expected['count'], f"{key}: expected {expected['count']} unique values, got {result['unique_values']}"
        finally:
            await self.cleanup_table()

class ClickHouseDataValidationIntegrationTests(BaseIntegrationTest):
    """Test ClickHouse data validation and constraints."""

    def setup_method(self):
        """Setup test environment."""
        validate_test_config('backend')
        self.validation_table = f'validation_test_{uuid.uuid4().hex[:8]}'

    async def cleanup_validation_table(self):
        """Cleanup validation test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'DROP TABLE IF EXISTS {self.validation_table}')
        except Exception as e:
            print(f'Warning: Failed to cleanup table {self.validation_table}: {e}')

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_type_validation_and_constraints(self):
        """Test data type validation and constraint enforcement.
        
        Ensures data integrity through proper type validation and constraints.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.validation_table} (\n                    id UInt64,\n                    user_email String,\n                    age UInt8,\n                    balance Decimal(10,2),\n                    is_active Bool,\n                    registration_date Date,\n                    last_login DateTime64(3),\n                    tags Array(String),\n                    metadata Map(String, String)\n                ) ENGINE = MergeTree()\n                ORDER BY id\n                ')
                valid_data = {'id': 1, 'user_email': 'test@example.com', 'age': 25, 'balance': 1234.56, 'is_active': True, 'registration_date': '2024-01-15', 'last_login': '2024-01-15 10:30:45', 'tags': ['premium', 'verified'], 'metadata': "{'source': 'web', 'campaign': 'winter2024'}"}
                await client.execute(f'\n                    INSERT INTO {self.validation_table} \n                    (id, user_email, age, balance, is_active, registration_date, last_login, tags, metadata)\n                    VALUES (%(id)s, %(user_email)s, %(age)s, %(balance)s, %(is_active)s, \n                           %(registration_date)s, %(last_login)s, %(tags)s, %(metadata)s)\n                ', valid_data)
                result = await client.execute(f'\n                    SELECT id, user_email, age, balance, is_active, registration_date, tags\n                    FROM {self.validation_table} WHERE id = 1\n                ')
                assert len(result) == 1, 'Should have one valid record'
                assert result[0]['user_email'] == 'test@example.com'
                assert result[0]['age'] == 25
                assert result[0]['balance'] == 1234.56
                assert result[0]['is_active'] is True
                tags_result = result[0]['tags']
                assert isinstance(tags_result, list), 'Tags should be an array'
                assert 'premium' in tags_result, 'Should contain premium tag'
                assert 'verified' in tags_result, 'Should contain verified tag'
                boundary_test_data = [{'id': 2, 'user_email': 'boundary1@example.com', 'age': 0, 'balance': 0.0, 'is_active': False, 'registration_date': '2024-01-01', 'last_login': '2024-01-01 00:00:00', 'tags': [], 'metadata': '{}'}, {'id': 3, 'user_email': 'boundary2@example.com', 'age': 255, 'balance': 99999999.99, 'is_active': True, 'registration_date': '2024-12-31', 'last_login': '2024-12-31 23:59:59', 'tags': ['test'], 'metadata': "{'key': 'value'}"}]
                for data in boundary_test_data:
                    await client.execute(f'\n                        INSERT INTO {self.validation_table} \n                        (id, user_email, age, balance, is_active, registration_date, last_login, tags, metadata)\n                        VALUES (%(id)s, %(user_email)s, %(age)s, %(balance)s, %(is_active)s,\n                               %(registration_date)s, %(last_login)s, %(tags)s, %(metadata)s)\n                    ', data)
                boundary_results = await client.execute(f'\n                    SELECT id, age, balance FROM {self.validation_table} \n                    WHERE id IN (2, 3) ORDER BY id\n                ')
                assert len(boundary_results) == 2, 'Should have boundary test records'
                assert boundary_results[0]['age'] == 0, 'Min age should be 0'
                assert boundary_results[1]['age'] == 255, 'Max age should be 255'
                assert boundary_results[1]['balance'] == 99999999.99, 'Max balance should be preserved'
        finally:
            await self.cleanup_validation_table()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')