"""
Test ClickHouse User Isolation - Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (Multi-tenant SaaS)
- Business Goal: Ensure complete data isolation between users
- Value Impact: Critical for data privacy and compliance (GDPR, SOC2)
- Strategic Impact: Enables enterprise sales with guaranteed data security (+$50K ARR)

This test suite validates ClickHouse user data isolation, ensuring no data leakage
between users in the multi-tenant analytics platform.
"""
import pytest
import asyncio
import uuid
from typing import Dict, List, Any
from netra_backend.app.db.clickhouse import get_clickhouse_client, get_clickhouse_service
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.configuration_validator import validate_test_config

class TestClickHouseUserIsolationIntegration(BaseIntegrationTest):
    """Test ClickHouse user data isolation and multi-tenancy."""

    def setup_method(self):
        """Setup test environment for user isolation testing."""
        validate_test_config('backend')
        self.isolation_table = f'isolation_test_{uuid.uuid4().hex[:8]}'
        self.test_users = ['enterprise_user_alpha', 'enterprise_user_beta', 'enterprise_user_gamma']

    async def cleanup_isolation_table(self):
        """Cleanup isolation test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'DROP TABLE IF EXISTS {self.isolation_table}')
        except Exception as e:
            print(f'Warning: Failed to cleanup isolation table: {e}')

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_user_data_complete_isolation(self):
        """Test complete data isolation between enterprise users.
        
        Critical for enterprise compliance and data security guarantees.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"\n                CREATE TABLE IF NOT EXISTS {self.isolation_table} (\n                    record_id UUID DEFAULT generateUUIDv4(),\n                    user_id String,\n                    tenant_id String,\n                    sensitive_data String,\n                    personal_info String,\n                    business_metrics String,\n                    created_at DateTime64(3) DEFAULT now64(3),\n                    security_level String DEFAULT 'confidential'\n                ) ENGINE = MergeTree()\n                PARTITION BY user_id  \n                ORDER BY (user_id, created_at, record_id)\n                ")
                sensitive_data_sets = {'enterprise_user_alpha': {'tenant_id': 'tenant_alpha_001', 'sensitive_data': 'Alpha Company Financial Report Q4 2024', 'personal_info': 'John Alpha, CEO, john.alpha@alphacompany.com', 'business_metrics': 'Revenue: $2.5M, Profit: $450K, Growth: 23%'}, 'enterprise_user_beta': {'tenant_id': 'tenant_beta_002', 'sensitive_data': 'Beta Corp Customer Database Export', 'personal_info': 'Sarah Beta, CTO, sarah.beta@betacorp.com', 'business_metrics': 'Users: 50K, Churn: 3.2%, LTV: $890'}, 'enterprise_user_gamma': {'tenant_id': 'tenant_gamma_003', 'sensitive_data': 'Gamma Industries Trade Secrets Document', 'personal_info': 'Michael Gamma, Director, m.gamma@gammaindustries.com', 'business_metrics': 'Patents: 45, R&D Budget: $1.8M, Innovation Score: 94%'}}
                for user_id, data in sensitive_data_sets.items():
                    for record_num in range(10):
                        await client.execute(f'\n                            INSERT INTO {self.isolation_table} \n                            (user_id, tenant_id, sensitive_data, personal_info, business_metrics)\n                            VALUES (%(user_id)s, %(tenant_id)s, %(sensitive_data)s, %(personal_info)s, %(business_metrics)s)\n                        ', {'user_id': user_id, 'tenant_id': data['tenant_id'], 'sensitive_data': f"{data['sensitive_data']} - Record {record_num}", 'personal_info': f"{data['personal_info']} - Entry {record_num}", 'business_metrics': f"{data['business_metrics']} - Data Point {record_num}"})
                await asyncio.sleep(0.3)
                for user_id in self.test_users:
                    user_data = await client.execute(f'\n                        SELECT user_id, tenant_id, sensitive_data, personal_info \n                        FROM {self.isolation_table}\n                        WHERE user_id = %(user_id)s\n                    ', {'user_id': user_id})
                    assert len(user_data) == 10, f'User {user_id} should have exactly 10 records'
                    for record in user_data:
                        assert record['user_id'] == user_id, f"Record belongs to wrong user: {record['user_id']}"
                        expected_tenant = sensitive_data_sets[user_id]['tenant_id']
                        assert record['tenant_id'] == expected_tenant, f'Wrong tenant ID for user {user_id}'
                        for other_user, other_data in sensitive_data_sets.items():
                            if other_user != user_id:
                                other_sensitive = other_data['sensitive_data'].split(' - Record')[0]
                                assert other_sensitive not in record['sensitive_data'], f"Data leakage: {other_user}'s data found in {user_id}'s records"
                for i, user_id in enumerate(self.test_users):
                    other_users = [u for j, u in enumerate(self.test_users) if j != i]
                    cross_user_query = await client.execute(f'\n                        SELECT COUNT(*) as count \n                        FROM {self.isolation_table}\n                        WHERE user_id = %(user_id)s AND tenant_id IN %(other_tenants)s\n                    ', {'user_id': user_id, 'other_tenants': [sensitive_data_sets[u]['tenant_id'] for u in other_users]})
                    assert cross_user_query[0]['count'] == 0, f'Cross-tenant data leak detected for user {user_id}'
                user_aggregates = await client.execute(f'\n                    SELECT \n                        user_id,\n                        tenant_id,\n                        COUNT(*) as record_count,\n                        COUNT(DISTINCT tenant_id) as unique_tenants\n                    FROM {self.isolation_table}\n                    GROUP BY user_id, tenant_id\n                    ORDER BY user_id\n                ')
                assert len(user_aggregates) == 3, 'Should have aggregates for 3 users'
                for agg in user_aggregates:
                    assert agg['record_count'] == 10, f"User {agg['user_id']} should have 10 records"
                    assert agg['unique_tenants'] == 1, f"User {agg['user_id']} should have only 1 tenant"
        finally:
            await self.cleanup_isolation_table()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_user_cache_isolation_through_service(self):
        """Test user cache isolation through ClickHouse service layer.
        
        Ensures cached data maintains strict user isolation.
        """
        try:
            service = get_clickhouse_service()
            await service.initialize()
            service.clear_cache()
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.isolation_table} (\n                    user_id String,\n                    confidential_data String,\n                    access_timestamp DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, access_timestamp)\n                ')
                confidential_datasets = {'cache_user_alpha': "Alpha's confidential business intelligence data", 'cache_user_beta': "Beta's proprietary customer analytics", 'cache_user_gamma': "Gamma's secret competitive analysis"}
                for user_id, data in confidential_datasets.items():
                    await client.execute(f'\n                        INSERT INTO {self.isolation_table} (user_id, confidential_data)\n                        VALUES (%(user_id)s, %(confidential_data)s)\n                    ', {'user_id': user_id, 'confidential_data': data})
                await asyncio.sleep(0.1)
                cache_test_query = f'\n                    SELECT user_id, confidential_data \n                    FROM {self.isolation_table}\n                    WHERE user_id = %(user_id)s\n                '
                user_results = {}
                for user_id in confidential_datasets.keys():
                    result = await service.execute(cache_test_query, {'user_id': user_id}, user_id=user_id)
                    user_results[user_id] = result
                    assert len(result) == 1, f'User {user_id} should have 1 record'
                    assert result[0]['confidential_data'] == confidential_datasets[user_id]
                for user_id in confidential_datasets.keys():
                    cached_result = await service.execute(cache_test_query, {'user_id': user_id}, user_id=user_id)
                    assert cached_result == user_results[user_id], f'Cached data mismatch for user {user_id}'
                    for other_user_id, other_data in confidential_datasets.items():
                        if other_user_id != user_id:
                            assert other_data not in str(cached_result), f"Cache contamination: {other_user_id}'s data in {user_id}'s cache"
                for user_id in confidential_datasets.keys():
                    user_cache_stats = service.get_cache_stats(user_id)
                    assert user_cache_stats['user_id'] == user_id, 'Cache stats should be user-specific'
                    assert user_cache_stats['user_cache_entries'] >= 1, 'User should have cache entries'
                test_user = 'cache_user_alpha'
                other_users = ['cache_user_beta', 'cache_user_gamma']
                service.clear_cache(test_user)
                test_user_stats = service.get_cache_stats(test_user)
                assert test_user_stats['user_cache_entries'] == 0, f'Cache should be cleared for {test_user}'
                for other_user in other_users:
                    other_stats = service.get_cache_stats(other_user)
                    assert other_stats['user_cache_entries'] >= 1, f'Cache should remain for {other_user}'
        finally:
            await self.cleanup_isolation_table()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_multi_user_isolation(self):
        """Test user isolation under concurrent multi-user operations.
        
        Critical for ensuring data security under high-load multi-tenant scenarios.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.isolation_table} (\n                    operation_id String,\n                    user_id String,\n                    session_id String,\n                    private_data String,\n                    timestamp DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                PARTITION BY user_id\n                ORDER BY (user_id, timestamp, operation_id)\n                ')

                async def execute_user_operations(user_id: str, session_id: str, operation_count: int):
                    """Execute operations for a specific user concurrently."""
                    async with get_clickhouse_client(bypass_manager=True) as user_client:
                        operations_data = []
                        for i in range(operation_count):
                            operation_data = {'operation_id': f'{user_id}_op_{i}', 'user_id': user_id, 'session_id': session_id, 'private_data': f'Private data for {user_id} - Operation {i} - Session {session_id}'}
                            await user_client.execute(f'\n                                INSERT INTO {self.isolation_table} \n                                (operation_id, user_id, session_id, private_data)\n                                VALUES (%(operation_id)s, %(user_id)s, %(session_id)s, %(private_data)s)\n                            ', operation_data)
                            operations_data.append(operation_data)
                            await asyncio.sleep(0.01)
                        user_verification = await user_client.execute(f'\n                            SELECT operation_id, user_id, session_id, private_data\n                            FROM {self.isolation_table}\n                            WHERE user_id = %(user_id)s AND session_id = %(session_id)s\n                        ', {'user_id': user_id, 'session_id': session_id})
                        return user_verification
                concurrent_sessions = [execute_user_operations('concurrent_user_1', 'session_001', 15), execute_user_operations('concurrent_user_2', 'session_002', 12), execute_user_operations('concurrent_user_3', 'session_003', 18), execute_user_operations('concurrent_user_1', 'session_004', 8)]
                results = await asyncio.gather(*concurrent_sessions)
                await asyncio.sleep(0.3)
                expected_counts = [15, 12, 18, 8]
                for i, result in enumerate(results):
                    assert len(result) == expected_counts[i], f'Session {i} should have {expected_counts[i]} operations, got {len(result)}'
                isolation_verification = await client.execute(f'\n                    SELECT \n                        user_id,\n                        session_id,\n                        COUNT(*) as operation_count,\n                        COUNT(DISTINCT operation_id) as unique_operations\n                    FROM {self.isolation_table}\n                    GROUP BY user_id, session_id\n                    ORDER BY user_id, session_id\n                ')
                expected_sessions = [('concurrent_user_1', 'session_001', 15), ('concurrent_user_1', 'session_004', 8), ('concurrent_user_2', 'session_002', 12), ('concurrent_user_3', 'session_003', 18)]
                assert len(isolation_verification) == 4, 'Should have 4 user sessions'
                for i, verification in enumerate(isolation_verification):
                    expected_user, expected_session, expected_count = expected_sessions[i]
                    assert verification['user_id'] == expected_user
                    assert verification['session_id'] == expected_session
                    assert verification['operation_count'] == expected_count
                    assert verification['unique_operations'] == expected_count, 'All operations should be unique'
                cross_contamination_check = await client.execute(f'\n                    SELECT \n                        user_id,\n                        COUNT(DISTINCT SUBSTRING(private_data, 1, 20)) as data_patterns\n                    FROM {self.isolation_table}\n                    GROUP BY user_id\n                ')
                for check in cross_contamination_check:
                    user_id = check['user_id']
                    data_patterns = check['data_patterns']
                    assert data_patterns <= 2, f'User {user_id} has too many data patterns, possible contamination'
        finally:
            await self.cleanup_isolation_table()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')