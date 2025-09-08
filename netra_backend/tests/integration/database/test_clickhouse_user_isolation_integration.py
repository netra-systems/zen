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
        validate_test_config("backend")
        self.isolation_table = f"isolation_test_{uuid.uuid4().hex[:8]}"
        self.test_users = [
            "enterprise_user_alpha",
            "enterprise_user_beta", 
            "enterprise_user_gamma"
        ]

    async def cleanup_isolation_table(self):
        """Cleanup isolation test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"DROP TABLE IF EXISTS {self.isolation_table}")
        except Exception as e:
            print(f"Warning: Failed to cleanup isolation table: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_user_data_complete_isolation(self):
        """Test complete data isolation between enterprise users.
        
        Critical for enterprise compliance and data security guarantees.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create table for multi-tenant data isolation
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.isolation_table} (
                    record_id UUID DEFAULT generateUUIDv4(),
                    user_id String,
                    tenant_id String,
                    sensitive_data String,
                    personal_info String,
                    business_metrics String,
                    created_at DateTime64(3) DEFAULT now64(3),
                    security_level String DEFAULT 'confidential'
                ) ENGINE = MergeTree()
                PARTITION BY user_id  
                ORDER BY (user_id, created_at, record_id)
                """)
                
                # Insert sensitive data for each test user
                sensitive_data_sets = {
                    "enterprise_user_alpha": {
                        "tenant_id": "tenant_alpha_001",
                        "sensitive_data": "Alpha Company Financial Report Q4 2024",
                        "personal_info": "John Alpha, CEO, john.alpha@alphacompany.com",
                        "business_metrics": "Revenue: $2.5M, Profit: $450K, Growth: 23%"
                    },
                    "enterprise_user_beta": {
                        "tenant_id": "tenant_beta_002", 
                        "sensitive_data": "Beta Corp Customer Database Export",
                        "personal_info": "Sarah Beta, CTO, sarah.beta@betacorp.com",
                        "business_metrics": "Users: 50K, Churn: 3.2%, LTV: $890"
                    },
                    "enterprise_user_gamma": {
                        "tenant_id": "tenant_gamma_003",
                        "sensitive_data": "Gamma Industries Trade Secrets Document",
                        "personal_info": "Michael Gamma, Director, m.gamma@gammaindustries.com", 
                        "business_metrics": "Patents: 45, R&D Budget: $1.8M, Innovation Score: 94%"
                    }
                }
                
                # Insert data for each user/tenant
                for user_id, data in sensitive_data_sets.items():
                    for record_num in range(10):  # 10 records per user
                        await client.execute(f"""
                            INSERT INTO {self.isolation_table} 
                            (user_id, tenant_id, sensitive_data, personal_info, business_metrics)
                            VALUES (%(user_id)s, %(tenant_id)s, %(sensitive_data)s, %(personal_info)s, %(business_metrics)s)
                        """, {
                            'user_id': user_id,
                            'tenant_id': data['tenant_id'],
                            'sensitive_data': f"{data['sensitive_data']} - Record {record_num}",
                            'personal_info': f"{data['personal_info']} - Entry {record_num}",
                            'business_metrics': f"{data['business_metrics']} - Data Point {record_num}"
                        })
                
                # Wait for data to be available
                await asyncio.sleep(0.3)
                
                # Test 1: Verify each user can only access their own data
                for user_id in self.test_users:
                    user_data = await client.execute(f"""
                        SELECT user_id, tenant_id, sensitive_data, personal_info 
                        FROM {self.isolation_table}
                        WHERE user_id = %(user_id)s
                    """, {'user_id': user_id})
                    
                    # Each user should have exactly 10 records
                    assert len(user_data) == 10, f"User {user_id} should have exactly 10 records"
                    
                    # All records should belong to the correct user
                    for record in user_data:
                        assert record['user_id'] == user_id, f"Record belongs to wrong user: {record['user_id']}"
                        
                        # Verify tenant isolation
                        expected_tenant = sensitive_data_sets[user_id]['tenant_id']
                        assert record['tenant_id'] == expected_tenant, f"Wrong tenant ID for user {user_id}"
                        
                        # Verify no cross-contamination of sensitive data
                        for other_user, other_data in sensitive_data_sets.items():
                            if other_user != user_id:
                                # Other users' data should NOT appear in this user's records
                                other_sensitive = other_data['sensitive_data'].split(' - Record')[0]
                                assert other_sensitive not in record['sensitive_data'], \
                                    f"Data leakage: {other_user}'s data found in {user_id}'s records"
                
                # Test 2: Verify cross-user queries return no results
                for i, user_id in enumerate(self.test_users):
                    other_users = [u for j, u in enumerate(self.test_users) if j != i]
                    
                    # Query for other users' data should return empty
                    cross_user_query = await client.execute(f"""
                        SELECT COUNT(*) as count 
                        FROM {self.isolation_table}
                        WHERE user_id = %(user_id)s AND tenant_id IN %(other_tenants)s
                    """, {
                        'user_id': user_id,
                        'other_tenants': [sensitive_data_sets[u]['tenant_id'] for u in other_users]
                    })
                    
                    assert cross_user_query[0]['count'] == 0, \
                        f"Cross-tenant data leak detected for user {user_id}"
                
                # Test 3: Verify aggregate queries maintain isolation
                user_aggregates = await client.execute(f"""
                    SELECT 
                        user_id,
                        tenant_id,
                        COUNT(*) as record_count,
                        COUNT(DISTINCT tenant_id) as unique_tenants
                    FROM {self.isolation_table}
                    GROUP BY user_id, tenant_id
                    ORDER BY user_id
                """)
                
                assert len(user_aggregates) == 3, "Should have aggregates for 3 users"
                
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
            
            # Clear all caches to start fresh
            service.clear_cache()
            
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create table for cache isolation testing
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.isolation_table} (
                    user_id String,
                    confidential_data String,
                    access_timestamp DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (user_id, access_timestamp)
                """)
                
                # Insert confidential data for each user
                confidential_datasets = {
                    "cache_user_alpha": "Alpha's confidential business intelligence data",
                    "cache_user_beta": "Beta's proprietary customer analytics", 
                    "cache_user_gamma": "Gamma's secret competitive analysis"
                }
                
                for user_id, data in confidential_datasets.items():
                    await client.execute(f"""
                        INSERT INTO {self.isolation_table} (user_id, confidential_data)
                        VALUES (%(user_id)s, %(confidential_data)s)
                    """, {'user_id': user_id, 'confidential_data': data})
                
                await asyncio.sleep(0.1)
                
                # Test cache isolation for each user
                cache_test_query = f"""
                    SELECT user_id, confidential_data 
                    FROM {self.isolation_table}
                    WHERE user_id = %(user_id)s
                """
                
                # Execute queries for each user to populate their individual caches
                user_results = {}
                for user_id in confidential_datasets.keys():
                    # First execution (populates cache for this user)
                    result = await service.execute(
                        cache_test_query, 
                        {'user_id': user_id}, 
                        user_id=user_id
                    )
                    user_results[user_id] = result
                    
                    assert len(result) == 1, f"User {user_id} should have 1 record"
                    assert result[0]['confidential_data'] == confidential_datasets[user_id]
                
                # Test cache isolation - each user should only see their cached data
                for user_id in confidential_datasets.keys():
                    # Second execution (should hit cache)
                    cached_result = await service.execute(
                        cache_test_query,
                        {'user_id': user_id},
                        user_id=user_id
                    )
                    
                    # Verify cache returns correct user's data
                    assert cached_result == user_results[user_id], \
                        f"Cached data mismatch for user {user_id}"
                    
                    # Verify no cross-contamination in cache
                    for other_user_id, other_data in confidential_datasets.items():
                        if other_user_id != user_id:
                            assert other_data not in str(cached_result), \
                                f"Cache contamination: {other_user_id}'s data in {user_id}'s cache"
                
                # Test cache stats isolation
                for user_id in confidential_datasets.keys():
                    user_cache_stats = service.get_cache_stats(user_id)
                    assert user_cache_stats['user_id'] == user_id, "Cache stats should be user-specific"
                    assert user_cache_stats['user_cache_entries'] >= 1, "User should have cache entries"
                
                # Test cache clearing isolation  
                test_user = "cache_user_alpha"
                other_users = ["cache_user_beta", "cache_user_gamma"]
                
                # Clear cache for one user only
                service.clear_cache(test_user)
                
                # Verify only target user's cache was cleared
                test_user_stats = service.get_cache_stats(test_user)
                assert test_user_stats['user_cache_entries'] == 0, f"Cache should be cleared for {test_user}"
                
                # Other users' caches should remain
                for other_user in other_users:
                    other_stats = service.get_cache_stats(other_user)
                    assert other_stats['user_cache_entries'] >= 1, f"Cache should remain for {other_user}"
                
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
                # Create table for concurrent isolation testing
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.isolation_table} (
                    operation_id String,
                    user_id String,
                    session_id String,
                    private_data String,
                    timestamp DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                PARTITION BY user_id
                ORDER BY (user_id, timestamp, operation_id)
                """)
                
                # Define concurrent user operations
                async def execute_user_operations(user_id: str, session_id: str, operation_count: int):
                    """Execute operations for a specific user concurrently."""
                    async with get_clickhouse_client(bypass_manager=True) as user_client:
                        operations_data = []
                        
                        # Insert operations for this user
                        for i in range(operation_count):
                            operation_data = {
                                'operation_id': f"{user_id}_op_{i}",
                                'user_id': user_id,
                                'session_id': session_id,
                                'private_data': f"Private data for {user_id} - Operation {i} - Session {session_id}"
                            }
                            
                            await user_client.execute(f"""
                                INSERT INTO {self.isolation_table} 
                                (operation_id, user_id, session_id, private_data)
                                VALUES (%(operation_id)s, %(user_id)s, %(session_id)s, %(private_data)s)
                            """, operation_data)
                            
                            operations_data.append(operation_data)
                            
                            # Add small delay to increase concurrency overlap
                            await asyncio.sleep(0.01)
                        
                        # Verify user can only access their own data
                        user_verification = await user_client.execute(f"""
                            SELECT operation_id, user_id, session_id, private_data
                            FROM {self.isolation_table}
                            WHERE user_id = %(user_id)s AND session_id = %(session_id)s
                        """, {'user_id': user_id, 'session_id': session_id})
                        
                        return user_verification
                
                # Run concurrent operations for multiple users
                concurrent_sessions = [
                    execute_user_operations("concurrent_user_1", "session_001", 15),
                    execute_user_operations("concurrent_user_2", "session_002", 12),
                    execute_user_operations("concurrent_user_3", "session_003", 18),
                    execute_user_operations("concurrent_user_1", "session_004", 8),  # Same user, different session
                ]
                
                # Execute all operations concurrently
                results = await asyncio.gather(*concurrent_sessions)
                
                # Wait for all data to be committed
                await asyncio.sleep(0.3)
                
                # Verify isolation results
                expected_counts = [15, 12, 18, 8]
                for i, result in enumerate(results):
                    assert len(result) == expected_counts[i], \
                        f"Session {i} should have {expected_counts[i]} operations, got {len(result)}"
                
                # Verify cross-user isolation after concurrent operations
                isolation_verification = await client.execute(f"""
                    SELECT 
                        user_id,
                        session_id,
                        COUNT(*) as operation_count,
                        COUNT(DISTINCT operation_id) as unique_operations
                    FROM {self.isolation_table}
                    GROUP BY user_id, session_id
                    ORDER BY user_id, session_id
                """)
                
                expected_sessions = [
                    ("concurrent_user_1", "session_001", 15),
                    ("concurrent_user_1", "session_004", 8),
                    ("concurrent_user_2", "session_002", 12),
                    ("concurrent_user_3", "session_003", 18)
                ]
                
                assert len(isolation_verification) == 4, "Should have 4 user sessions"
                
                for i, verification in enumerate(isolation_verification):
                    expected_user, expected_session, expected_count = expected_sessions[i]
                    assert verification['user_id'] == expected_user
                    assert verification['session_id'] == expected_session  
                    assert verification['operation_count'] == expected_count
                    assert verification['unique_operations'] == expected_count, "All operations should be unique"
                
                # Verify no data leakage between users
                cross_contamination_check = await client.execute(f"""
                    SELECT 
                        user_id,
                        COUNT(DISTINCT SUBSTRING(private_data, 1, 20)) as data_patterns
                    FROM {self.isolation_table}
                    GROUP BY user_id
                """)
                
                for check in cross_contamination_check:
                    user_id = check['user_id']
                    data_patterns = check['data_patterns']
                    
                    # Each user should only have their own data patterns
                    # (multiple sessions may create some variation, but should be limited)
                    assert data_patterns <= 2, f"User {user_id} has too many data patterns, possible contamination"
                
        finally:
            await self.cleanup_isolation_table()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])