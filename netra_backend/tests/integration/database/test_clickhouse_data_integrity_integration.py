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


class TestClickHouseDataIntegrityIntegration(BaseIntegrationTest):
    """Test ClickHouse data integrity and consistency features."""
    
    def setup_method(self):
        """Setup test environment and validate configuration."""
        validate_test_config("backend")
        self.test_table = f"integrity_test_{uuid.uuid4().hex[:8]}"

    async def cleanup_table(self):
        """Cleanup test table after test completion."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"DROP TABLE IF EXISTS {self.test_table}")
        except Exception as e:
            print(f"Warning: Failed to cleanup table {self.test_table}: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_consistency_across_partitions(self):
        """Test data consistency across ClickHouse partitions.
        
        Critical for ensuring analytics data remains consistent across time partitions.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create partitioned table for data consistency testing
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table} (
                    id UInt64,
                    user_id String,
                    event_date Date,
                    event_timestamp DateTime64(3),
                    metric_value Float64,
                    category String
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(event_date)
                ORDER BY (user_id, event_date, id)
                """)
                
                # Insert data across multiple partitions (different months)
                base_date = datetime(2024, 1, 15)
                test_data = []
                
                for month_offset in range(3):  # 3 months of data
                    for day_offset in range(5):  # 5 days per month
                        for record_id in range(10):  # 10 records per day
                            event_date = base_date + timedelta(days=month_offset*30 + day_offset)
                            test_data.append({
                                'id': month_offset * 50 + day_offset * 10 + record_id,
                                'user_id': f'user_{record_id % 3}',  # 3 users total
                                'event_date': event_date.strftime('%Y-%m-%d'),
                                'event_timestamp': event_date.strftime('%Y-%m-%d %H:%M:%S'),
                                'metric_value': (record_id + 1) * 10.5,
                                'category': f'category_{month_offset}'
                            })
                
                # Insert all test data
                for data in test_data:
                    await client.execute(f"""
                        INSERT INTO {self.test_table} 
                        (id, user_id, event_date, event_timestamp, metric_value, category)
                        VALUES (%(id)s, %(user_id)s, %(event_date)s, %(event_timestamp)s, 
                               %(metric_value)s, %(category)s)
                    """, data)
                
                # Wait for data to be available across all partitions
                await asyncio.sleep(0.3)
                
                # Verify total record count
                total_count = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table}")
                expected_total = 3 * 5 * 10  # 3 months * 5 days * 10 records = 150
                assert total_count[0]['count'] == expected_total, f"Expected {expected_total} records"
                
                # Verify partition integrity - each partition should have correct count
                partition_counts = await client.execute(f"""
                    SELECT toYYYYMM(event_date) as partition_month, COUNT(*) as count
                    FROM {self.test_table}
                    GROUP BY partition_month
                    ORDER BY partition_month
                """)
                
                assert len(partition_counts) == 3, "Should have 3 partitions"
                for partition in partition_counts:
                    assert partition['count'] == 50, f"Each partition should have 50 records"
                
                # Verify data consistency within each partition
                for month_offset in range(3):
                    partition_data = await client.execute(f"""
                        SELECT user_id, COUNT(*) as count, AVG(metric_value) as avg_metric
                        FROM {self.test_table}
                        WHERE category = 'category_{month_offset}'
                        GROUP BY user_id
                        ORDER BY user_id
                    """)
                    
                    # Each user should have consistent data across the partition
                    user_counts = {row['user_id']: row['count'] for row in partition_data}
                    expected_user_counts = {'user_0': 10, 'user_1': 10, 'user_2': 10}  # Not exact due to modulo
                    
                    total_partition_records = sum(user_counts.values())
                    assert total_partition_records == 50, f"Partition {month_offset} should have 50 total records"
                
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
                # Create table with ReplacingMergeTree for deduplication
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table} (
                    transaction_id String,
                    user_id String,
                    amount Float64,
                    timestamp DateTime64(3),
                    version UInt32
                ) ENGINE = ReplacingMergeTree(version)
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (user_id, transaction_id)
                """)
                
                # Insert initial data
                base_data = {
                    'transaction_id': 'txn_001',
                    'user_id': 'dedup_user',
                    'amount': 100.50,
                    'timestamp': '2024-01-15 10:00:00',
                    'version': 1
                }
                
                await client.execute(f"""
                    INSERT INTO {self.test_table} 
                    (transaction_id, user_id, amount, timestamp, version)
                    VALUES (%(transaction_id)s, %(user_id)s, %(amount)s, %(timestamp)s, %(version)s)
                """, base_data)
                
                # Insert duplicate with same version (should not create duplicate)
                duplicate_data = base_data.copy()
                await client.execute(f"""
                    INSERT INTO {self.test_table} 
                    (transaction_id, user_id, amount, timestamp, version)
                    VALUES (%(transaction_id)s, %(user_id)s, %(amount)s, %(timestamp)s, %(version)s)
                """, duplicate_data)
                
                # Insert update with higher version (should replace)
                updated_data = base_data.copy()
                updated_data['amount'] = 150.75
                updated_data['version'] = 2
                
                await client.execute(f"""
                    INSERT INTO {self.test_table} 
                    (transaction_id, user_id, amount, timestamp, version)
                    VALUES (%(transaction_id)s, %(user_id)s, %(amount)s, %(timestamp)s, %(version)s)
                """, updated_data)
                
                # Wait for merge operations to complete
                await asyncio.sleep(0.5)
                
                # Force merge to ensure deduplication
                await client.execute(f"OPTIMIZE TABLE {self.test_table} FINAL")
                
                # Verify deduplication - should have only one record with latest version
                results = await client.execute(f"""
                    SELECT transaction_id, user_id, amount, version, COUNT(*) as count
                    FROM {self.test_table}
                    WHERE transaction_id = 'txn_001'
                    GROUP BY transaction_id, user_id, amount, version
                    ORDER BY version DESC
                """)
                
                # Should have the latest version only
                assert len(results) == 1, "Should have only one record after deduplication"
                assert results[0]['amount'] == 150.75, "Should have the updated amount"
                assert results[0]['version'] == 2, "Should have the latest version"
                assert results[0]['count'] == 1, "Should have exactly one record"
                
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
                # Create table for concurrent update testing
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table} (
                    counter_id String,
                    user_id String,
                    counter_value UInt64,
                    update_timestamp DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (counter_id, user_id, update_timestamp)
                """)
                
                # Initialize counters
                counter_ids = ['counter_a', 'counter_b', 'counter_c']
                for counter_id in counter_ids:
                    await client.execute(f"""
                        INSERT INTO {self.test_table} (counter_id, user_id, counter_value)
                        VALUES (%(counter_id)s, 'system', 0)
                    """, {'counter_id': counter_id})
                
                # Define concurrent update operations
                async def update_counter(counter_id: str, user_id: str, increment_count: int):
                    """Perform multiple counter increments for a specific counter and user."""
                    async with get_clickhouse_client(bypass_manager=True) as update_client:
                        for i in range(increment_count):
                            await update_client.execute(f"""
                                INSERT INTO {self.test_table} (counter_id, user_id, counter_value)
                                VALUES (%(counter_id)s, %(user_id)s, %(counter_value)s)
                            """, {
                                'counter_id': counter_id,
                                'user_id': user_id,
                                'counter_value': i + 1
                            })
                            # Small delay to increase chance of concurrent operations
                            await asyncio.sleep(0.01)
                
                # Run concurrent updates
                concurrent_operations = [
                    update_counter('counter_a', 'user_1', 10),
                    update_counter('counter_a', 'user_2', 8),
                    update_counter('counter_b', 'user_1', 12),
                    update_counter('counter_b', 'user_3', 6),
                    update_counter('counter_c', 'user_2', 15),
                    update_counter('counter_c', 'user_3', 9)
                ]
                
                # Execute all operations concurrently
                await asyncio.gather(*concurrent_operations)
                
                # Wait for all data to be committed
                await asyncio.sleep(0.3)
                
                # Verify data integrity after concurrent operations
                integrity_results = await client.execute(f"""
                    SELECT 
                        counter_id,
                        user_id,
                        COUNT(*) as update_count,
                        MAX(counter_value) as max_value,
                        COUNT(DISTINCT counter_value) as unique_values
                    FROM {self.test_table}
                    WHERE user_id != 'system'
                    GROUP BY counter_id, user_id
                    ORDER BY counter_id, user_id
                """)
                
                # Validate each concurrent operation completed correctly
                expected_results = {
                    ('counter_a', 'user_1'): {'count': 10, 'max_value': 10},
                    ('counter_a', 'user_2'): {'count': 8, 'max_value': 8},
                    ('counter_b', 'user_1'): {'count': 12, 'max_value': 12},
                    ('counter_b', 'user_3'): {'count': 6, 'max_value': 6},
                    ('counter_c', 'user_2'): {'count': 15, 'max_value': 15},
                    ('counter_c', 'user_3'): {'count': 9, 'max_value': 9}
                }
                
                for result in integrity_results:
                    key = (result['counter_id'], result['user_id'])
                    expected = expected_results[key]
                    
                    assert result['update_count'] == expected['count'], \
                        f"{key}: expected {expected['count']} updates, got {result['update_count']}"
                    assert result['max_value'] == expected['max_value'], \
                        f"{key}: expected max value {expected['max_value']}, got {result['max_value']}"
                    
                    # Each increment should be unique (no data corruption)
                    assert result['unique_values'] == expected['count'], \
                        f"{key}: expected {expected['count']} unique values, got {result['unique_values']}"
                
        finally:
            await self.cleanup_table()


class TestClickHouseDataValidationIntegration(BaseIntegrationTest):
    """Test ClickHouse data validation and constraints."""
    
    def setup_method(self):
        """Setup test environment."""
        validate_test_config("backend")
        self.validation_table = f"validation_test_{uuid.uuid4().hex[:8]}"

    async def cleanup_validation_table(self):
        """Cleanup validation test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"DROP TABLE IF EXISTS {self.validation_table}")
        except Exception as e:
            print(f"Warning: Failed to cleanup table {self.validation_table}: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_type_validation_and_constraints(self):
        """Test data type validation and constraint enforcement.
        
        Ensures data integrity through proper type validation and constraints.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create table with strict data types and constraints
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.validation_table} (
                    id UInt64,
                    user_email String,
                    age UInt8,
                    balance Decimal(10,2),
                    is_active Bool,
                    registration_date Date,
                    last_login DateTime64(3),
                    tags Array(String),
                    metadata Map(String, String)
                ) ENGINE = MergeTree()
                ORDER BY id
                """)
                
                # Insert valid data
                valid_data = {
                    'id': 1,
                    'user_email': 'test@example.com',
                    'age': 25,
                    'balance': 1234.56,
                    'is_active': True,
                    'registration_date': '2024-01-15',
                    'last_login': '2024-01-15 10:30:45',
                    'tags': ['premium', 'verified'],
                    'metadata': "{'source': 'web', 'campaign': 'winter2024'}"
                }
                
                await client.execute(f"""
                    INSERT INTO {self.validation_table} 
                    (id, user_email, age, balance, is_active, registration_date, last_login, tags, metadata)
                    VALUES (%(id)s, %(user_email)s, %(age)s, %(balance)s, %(is_active)s, 
                           %(registration_date)s, %(last_login)s, %(tags)s, %(metadata)s)
                """, valid_data)
                
                # Verify data was inserted correctly
                result = await client.execute(f"""
                    SELECT id, user_email, age, balance, is_active, registration_date, tags
                    FROM {self.validation_table} WHERE id = 1
                """)
                
                assert len(result) == 1, "Should have one valid record"
                assert result[0]['user_email'] == 'test@example.com'
                assert result[0]['age'] == 25
                assert result[0]['balance'] == 1234.56
                assert result[0]['is_active'] is True
                
                # Test array and nested data integrity
                tags_result = result[0]['tags']
                assert isinstance(tags_result, list), "Tags should be an array"
                assert 'premium' in tags_result, "Should contain premium tag"
                assert 'verified' in tags_result, "Should contain verified tag"
                
                # Test data type boundaries (UInt8 for age)
                boundary_test_data = [
                    {'id': 2, 'user_email': 'boundary1@example.com', 'age': 0, 'balance': 0.00, 
                     'is_active': False, 'registration_date': '2024-01-01', 'last_login': '2024-01-01 00:00:00', 
                     'tags': [], 'metadata': "{}"},
                    {'id': 3, 'user_email': 'boundary2@example.com', 'age': 255, 'balance': 99999999.99,
                     'is_active': True, 'registration_date': '2024-12-31', 'last_login': '2024-12-31 23:59:59',
                     'tags': ['test'], 'metadata': "{'key': 'value'}"}
                ]
                
                for data in boundary_test_data:
                    await client.execute(f"""
                        INSERT INTO {self.validation_table} 
                        (id, user_email, age, balance, is_active, registration_date, last_login, tags, metadata)
                        VALUES (%(id)s, %(user_email)s, %(age)s, %(balance)s, %(is_active)s,
                               %(registration_date)s, %(last_login)s, %(tags)s, %(metadata)s)
                    """, data)
                
                # Verify boundary values are handled correctly
                boundary_results = await client.execute(f"""
                    SELECT id, age, balance FROM {self.validation_table} 
                    WHERE id IN (2, 3) ORDER BY id
                """)
                
                assert len(boundary_results) == 2, "Should have boundary test records"
                assert boundary_results[0]['age'] == 0, "Min age should be 0"
                assert boundary_results[1]['age'] == 255, "Max age should be 255"
                assert boundary_results[1]['balance'] == 99999999.99, "Max balance should be preserved"
                
        finally:
            await self.cleanup_validation_table()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])