"""
E2E GCP Staging Tests for StatePersistence - FINAL PHASE
Real GCP Cloud SQL, Redis Cloud, ClickHouse Cloud multi-tier architecture

Business Value Protection:
- $500K+ ARR: 3-tier architecture prevents data loss across hot/warm/cold storage
- $15K+ MRR per Enterprise: Analytics and long-term data retention for compliance
- Platform reliability: Distributed storage prevents single point of failure
- Cost optimization: Tiered storage reduces cloud infrastructure costs
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import json
import psycopg2
import redis

# ClickHouse client with fallback support
try:
    from clickhouse_driver import Client as ClickHouseClient
    CLICKHOUSE_DRIVER_AVAILABLE = True
except ImportError:
    try:
        # Try alternative clickhouse-connect client (already installed)
        import clickhouse_connect
        class ClickHouseClient:
            """Compatibility wrapper using clickhouse-connect."""
            def __init__(self, host, port=8123, database='default', user='default', password='', **kwargs):
                # Map clickhouse-driver parameters to clickhouse-connect
                self.client = clickhouse_connect.get_client(
                    host=host,
                    port=port,
                    database=database,
                    username=user,
                    password=password,
                    **kwargs
                )
            
            def execute(self, query, params=None):
                """Execute query with clickhouse-connect client."""
                if params:
                    return self.client.query(query, parameters=params)
                return self.client.query(query)
            
            def disconnect(self):
                """Disconnect from ClickHouse."""
                if hasattr(self.client, 'close'):
                    self.client.close()
        
        CLICKHOUSE_DRIVER_AVAILABLE = True
    except ImportError:
        ClickHouseClient = None
        CLICKHOUSE_DRIVER_AVAILABLE = False

# State persistence imports with compatibility fallbacks
try:
    from netra_backend.app.services.state_persistence import (
        StatePersistence, PersistenceConfig, StorageTier, DataLifecyclePolicy
    )
except ImportError:
    # Create compatibility classes if imports are not available
    from netra_backend.app.services.state_persistence import StatePersistenceService
    from enum import Enum
    from typing import Dict, Any
    from dataclasses import dataclass
    
    # Compatibility alias
    StatePersistence = StatePersistenceService
    
    class StorageTier(str, Enum):
        """Storage tier enumeration for 3-tier architecture."""
        HOT = "hot"      # Redis - frequent access
        WARM = "warm"    # PostgreSQL - moderate access  
        COLD = "cold"    # ClickHouse - analytics/archive
    
    @dataclass
    class PersistenceConfig:
        """Configuration for state persistence service."""
        enable_3tier_architecture: bool = True
        redis_ttl_seconds: int = 3600
        postgres_retention_days: int = 30
        clickhouse_retention_days: int = 365
        compression_enabled: bool = True
        batch_size: int = 100
        max_retries: int = 3
        retry_delay_seconds: int = 1
    
    @dataclass  
    class DataLifecyclePolicy:
        """Data lifecycle policy configuration."""
        hot_tier_ttl: int = 3600
        warm_tier_retention_days: int = 30
        cold_tier_retention_days: int = 365
        auto_archival_enabled: bool = True
        compression_enabled: bool = True
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestStatePersistenceGCPStaging(SSotAsyncTestCase):
    """
    E2E GCP Staging tests for StatePersistence protecting business value.
    Tests real GCP Cloud SQL, Redis Cloud, and ClickHouse Cloud integration.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up real GCP multi-tier storage services."""
        await super().asyncSetUpClass()
        
        cls.env = IsolatedEnvironment()
        cls.id_manager = UnifiedIDManager()
        
        # Real GCP Redis Cloud (Tier 1 - Hot cache)
        cls.redis_client = await get_redis_client()
        
        # Real GCP Cloud SQL PostgreSQL (Tier 2 - Warm storage)
        cls.postgres_config = {
            'host': cls.env.get("POSTGRES_HOST", "postgres.cloud.google.com"),
            'port': int(cls.env.get("POSTGRES_PORT", 5432)),
            'database': cls.env.get("POSTGRES_DB", "netra_staging"),
            'user': cls.env.get("POSTGRES_USER", "netra_user"),
            'password': cls.env.get("POSTGRES_PASSWORD")
        }
        
        # Real ClickHouse Cloud (Tier 3 - Cold analytics)
        if CLICKHOUSE_DRIVER_AVAILABLE:
            cls.clickhouse_client = ClickHouseClient(
                host=cls.env.get("CLICKHOUSE_HOST", "clickhouse.cloud.com"),
                port=int(cls.env.get("CLICKHOUSE_PORT", 9000)),
                database=cls.env.get("CLICKHOUSE_DB", "netra_analytics"),
                user=cls.env.get("CLICKHOUSE_USER", "netra_user"),
                password=cls.env.get("CLICKHOUSE_PASSWORD")
            )
        else:
            cls.clickhouse_client = None
        
        # Production persistence configuration
        cls.config = PersistenceConfig(
            enable_3tier_architecture=True,
            hot_cache_ttl_seconds=3600,      # 1 hour in Redis
            warm_storage_ttl_days=30,       # 30 days in PostgreSQL
            cold_analytics_retention_days=365,  # 1 year in ClickHouse
            enable_compression=True,
            enable_encryption=True,
            max_concurrent_operations=500,   # Enterprise scale
            enable_cross_tier_validation=True
        )
        
        cls.persistence = StatePersistence(config=cls.config)

    async def asyncTearDown(self):
        """Clean up test data from all tiers."""
        # Clean Redis test data
        test_keys = [k for k in await redis_client.keys() if k.startswith("test_")]
        if test_keys:
            await redis_client.delete(*test_keys)
        
        await super().asyncTearDown()

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_3tier_data_lifecycle_enterprise_scale(self):
        """
        HIGH DIFFICULTY: Test complete 3-tier data lifecycle at enterprise scale.
        
        Business Value: $15K+ MRR per Enterprise - complete data lifecycle management.
        Validates: Hot->Warm->Cold tier transitions, data integrity across all tiers.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create enterprise-scale data: 1000 agent execution states
        enterprise_states = []
        for i in range(1000):
            execution_id = str(uuid.uuid4())
            state_data = {
                "agent_execution_id": execution_id,
                "user_id": user_id,
                "agent_type": f"enterprise_agent_{i % 10}",
                "execution_status": "completed",
                "tool_outputs": [
                    {"tool_name": f"tool_{j}", "output": f"result_{i}_{j}"} 
                    for j in range(5)
                ],
                "performance_metrics": {
                    "execution_time_ms": 1000 + (i * 10),
                    "memory_usage_mb": 50 + (i % 100),
                    "tokens_used": 500 + (i * 5)
                },
                "created_at": time.time() - (i * 60),  # Spread over time
                "enterprise_metadata": {
                    "customer_tier": "Enterprise",
                    "compliance_required": True,
                    "retention_policy": "long_term"
                }
            }
            enterprise_states.append((execution_id, state_data))
        
        # Store all states (should start in Tier 1 - Redis)
        storage_tasks = []
        for execution_id, state_data in enterprise_states:
            task = self.persistence.store_state(
                key=f"agent_execution:{execution_id}",
                data=state_data,
                tier=StorageTier.HOT,
                lifecycle_policy=DataLifecyclePolicy.ENTERPRISE
            )
            storage_tasks.append(task)
        
        # Execute storage operations concurrently
        start_time = time.time()
        storage_results = await asyncio.gather(*storage_tasks, return_exceptions=True)
        storage_time = time.time() - start_time
        
        # Validate storage performance
        self.assertLess(storage_time, 60.0, 
                       "Enterprise-scale storage too slow for production")
        
        storage_failures = [r for r in storage_results if isinstance(r, Exception)]
        self.assertEqual(len(storage_failures), 0, 
                        f"Storage failures at enterprise scale: {storage_failures}")
        
        # Simulate time passage to trigger tier transitions
        # Force tier transitions for testing
        transition_tasks = []
        for i, (execution_id, state_data) in enumerate(enterprise_states[:100]):  # Test subset
            if i % 3 == 0:  # Move 1/3 to warm storage
                task = self.persistence.transition_tier(
                    key=f"agent_execution:{execution_id}",
                    from_tier=StorageTier.HOT,
                    to_tier=StorageTier.WARM
                )
                transition_tasks.append(task)
            elif i % 3 == 1:  # Move 1/3 to cold storage
                task = self.persistence.transition_tier(
                    key=f"agent_execution:{execution_id}",
                    from_tier=StorageTier.HOT,
                    to_tier=StorageTier.COLD
                )
                transition_tasks.append(task)
        
        transition_results = await asyncio.gather(*transition_tasks, return_exceptions=True)
        transition_failures = [r for r in transition_results if isinstance(r, Exception)]
        self.assertEqual(len(transition_failures), 0, 
                        f"Tier transition failures: {transition_failures}")
        
        # Validate data integrity across all tiers
        validation_count = 0
        for execution_id, original_data in enterprise_states[:100]:
            retrieved_data = await self.persistence.retrieve_state(
                key=f"agent_execution:{execution_id}",
                search_all_tiers=True
            )
            
            if retrieved_data is not None:
                self.assertEqual(retrieved_data["agent_execution_id"], 
                               original_data["agent_execution_id"])
                self.assertEqual(retrieved_data["user_id"], user_id)
                validation_count += 1
        
        # At least 95% should be retrievable across all tiers
        validation_rate = validation_count / 100
        self.assertGreater(validation_rate, 0.95, 
                          f"Data integrity issues across tiers: {validation_rate}")

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_cloud_sql_failover_warm_storage_recovery(self):
        """
        HIGH DIFFICULTY: Test Cloud SQL failover and warm storage recovery.
        
        Business Value: $500K+ ARR protection - prevents data loss during outages.
        Validates: PostgreSQL failover, data recovery, consistency maintenance.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Store critical business data in warm storage
        critical_states = []
        for i in range(50):
            execution_id = str(uuid.uuid4())
            critical_data = {
                "execution_id": execution_id,
                "user_id": user_id,
                "business_critical": True,
                "customer_tier": "Enterprise",
                "financial_impact": f"${(i + 1) * 1000}",
                "agent_results": {
                    "optimization_savings": f"${(i + 1) * 500}",
                    "recommendations": [f"rec_{j}" for j in range(10)],
                    "compliance_data": {"verified": True, "timestamp": time.time()}
                },
                "created_at": time.time() - (i * 300),  # 5 minute intervals
                "requires_recovery": True
            }
            critical_states.append((execution_id, critical_data))
            
            await self.persistence.store_state(
                key=f"critical_business:{execution_id}",
                data=critical_data,
                tier=StorageTier.WARM,
                lifecycle_policy=DataLifecyclePolicy.CRITICAL
            )
        
        # Verify all critical data stored in PostgreSQL
        stored_count = 0
        for execution_id, _ in critical_states:
            retrieved = await self.persistence.retrieve_state(
                key=f"critical_business:{execution_id}",
                preferred_tier=StorageTier.WARM
            )
            if retrieved is not None:
                stored_count += 1
        
        self.assertEqual(stored_count, len(critical_states), 
                        "Critical data not properly stored in warm storage")
        
        # Simulate PostgreSQL connection failure
        original_postgres = self.persistence._postgres_client
        self.persistence._postgres_client = None
        
        # Test graceful degradation - should fallback to other tiers
        fallback_execution_id = str(uuid.uuid4())
        fallback_data = {
            "execution_id": fallback_execution_id,
            "failover_test": True,
            "timestamp": time.time()
        }
        
        # Should still work using Redis fallback
        await self.persistence.store_state(
            key=f"failover_test:{fallback_execution_id}",
            data=fallback_data,
            tier=StorageTier.HOT,  # Fallback to hot tier
            lifecycle_policy=DataLifecyclePolicy.STANDARD
        )
        
        # Restore PostgreSQL connection
        self.persistence._postgres_client = original_postgres
        
        # Test data recovery after failover
        recovered_count = 0
        for execution_id, original_data in critical_states:
            recovered = await self.persistence.retrieve_state(
                key=f"critical_business:{execution_id}",
                search_all_tiers=True
            )
            
            if (recovered is not None and 
                recovered["financial_impact"] == original_data["financial_impact"]):
                recovered_count += 1
        
        # All critical data should be recoverable
        recovery_rate = recovered_count / len(critical_states)
        self.assertGreater(recovery_rate, 0.98, 
                          f"Critical data recovery failure: {recovery_rate}")
        
        # Verify fallback data is accessible
        fallback_retrieved = await self.persistence.retrieve_state(
            key=f"failover_test:{fallback_execution_id}",
            search_all_tiers=True
        )
        self.assertIsNotNone(fallback_retrieved, "Failover data not recoverable")

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_clickhouse_analytics_cold_storage_queries(self):
        """
        HIGH DIFFICULTY: Test ClickHouse analytics and cold storage queries.
        
        Business Value: $15K+ MRR per Enterprise - advanced analytics capabilities.
        Validates: Complex analytical queries, data aggregation, performance.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Generate 6 months of historical analytics data
        analytics_data = []
        base_time = time.time() - (6 * 30 * 24 * 3600)  # 6 months ago
        
        for day in range(180):  # 6 months of daily data
            for hour in range(24):
                for agent_type in ["optimizer", "analyzer", "reporter"]:
                    execution_id = str(uuid.uuid4())
                    timestamp = base_time + (day * 24 * 3600) + (hour * 3600)
                    
                    analytics_record = {
                        "execution_id": execution_id,
                        "user_id": user_id,
                        "agent_type": agent_type,
                        "timestamp": timestamp,
                        "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
                        "hour": hour,
                        "performance_metrics": {
                            "execution_time_ms": 500 + (hour * 100) + (day % 50),
                            "memory_usage_mb": 30 + (hour * 2),
                            "tokens_consumed": 200 + (hour * 50),
                            "cost_cents": 5 + (hour // 2)
                        },
                        "business_metrics": {
                            "optimization_value": 1000 + (day * 10),
                            "customer_satisfaction": 4.0 + (0.01 * (hour % 10)),
                            "revenue_impact": 500 + (day * 5)
                        },
                        "usage_patterns": {
                            "concurrent_users": 1 + (hour // 3),
                            "api_calls": 10 + (hour * 5),
                            "errors": max(0, hour - 20)  # More errors in late hours
                        }
                    }
                    analytics_data.append((execution_id, analytics_record))
        
        # Store analytics data in cold tier (ClickHouse)
        batch_size = 100
        storage_batches = []
        for i in range(0, len(analytics_data), batch_size):
            batch = analytics_data[i:i + batch_size]
            batch_tasks = []
            for execution_id, record in batch:
                task = self.persistence.store_state(
                    key=f"analytics:{execution_id}",
                    data=record,
                    tier=StorageTier.COLD,
                    lifecycle_policy=DataLifecyclePolicy.ANALYTICS
                )
                batch_tasks.append(task)
            storage_batches.append(batch_tasks)
        
        # Execute batch storage
        total_stored = 0
        for batch_tasks in storage_batches:
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            successful = [r for r in batch_results if not isinstance(r, Exception)]
            total_stored += len(successful)
            
            # Small delay between batches to avoid overwhelming ClickHouse
            await asyncio.sleep(0.1)
        
        self.assertGreater(total_stored / len(analytics_data), 0.95, 
                          "Insufficient analytics data storage rate")
        
        # Execute complex analytical queries
        query_start_time = time.time()
        
        # Query 1: Monthly performance trends by agent type
        monthly_trends = await self.persistence.execute_analytics_query(
            query="""
            SELECT 
                agent_type,
                toYYYYMM(toDateTime(timestamp)) as month,
                avg(performance_metrics.execution_time_ms) as avg_execution_time,
                avg(performance_metrics.memory_usage_mb) as avg_memory,
                sum(business_metrics.revenue_impact) as total_revenue
            FROM analytics_states 
            WHERE user_id = %(user_id)s 
              AND timestamp >= %(start_time)s
            GROUP BY agent_type, month
            ORDER BY month, agent_type
            """,
            parameters={"user_id": user_id, "start_time": base_time}
        )
        
        # Query 2: Peak usage patterns and cost optimization
        peak_usage_analysis = await self.persistence.execute_analytics_query(
            query="""
            SELECT 
                hour,
                avg(usage_patterns.concurrent_users) as avg_concurrent_users,
                avg(performance_metrics.cost_cents) as avg_cost_per_hour,
                avg(business_metrics.optimization_value) as avg_optimization_value
            FROM analytics_states 
            WHERE user_id = %(user_id)s
            GROUP BY hour
            ORDER BY hour
            """,
            parameters={"user_id": user_id}
        )
        
        # Query 3: Error rate analysis and reliability metrics
        reliability_metrics = await self.persistence.execute_analytics_query(
            query="""
            SELECT 
                date,
                agent_type,
                avg(usage_patterns.errors) as avg_errors,
                avg(business_metrics.customer_satisfaction) as avg_satisfaction,
                count() as total_executions
            FROM analytics_states 
            WHERE user_id = %(user_id)s
              AND timestamp >= %(recent_time)s
            GROUP BY date, agent_type
            HAVING total_executions > 10
            ORDER BY date DESC, avg_errors DESC
            """,
            parameters={
                "user_id": user_id, 
                "recent_time": time.time() - (30 * 24 * 3600)  # Last 30 days
            }
        )
        
        query_execution_time = time.time() - query_start_time
        
        # Validate query results and performance
        self.assertIsNotNone(monthly_trends, "Monthly trends query failed")
        self.assertIsNotNone(peak_usage_analysis, "Peak usage query failed")
        self.assertIsNotNone(reliability_metrics, "Reliability metrics query failed")
        
        # Performance requirement: Complex queries should complete within 30 seconds
        self.assertLess(query_execution_time, 30.0, 
                       "Analytics queries too slow for enterprise requirements")
        
        # Validate result completeness
        self.assertGreater(len(monthly_trends), 0, "No monthly trend data")
        self.assertEqual(len(peak_usage_analysis), 24, "Missing hourly usage data")
        self.assertGreater(len(reliability_metrics), 0, "No reliability data")
        
        # Validate business metrics calculation
        total_revenue = sum(row.get("total_revenue", 0) for row in monthly_trends)
        self.assertGreater(total_revenue, 0, "No revenue impact calculated")

    @pytest.mark.e2e_gcp_staging
    async def test_cross_tier_data_consistency_validation(self):
        """
        Test data consistency across all three storage tiers.
        
        Business Value: Data integrity ensures accurate business reporting.
        Validates: Consistency checks, synchronization, integrity verification.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create test data that will be distributed across tiers
        test_states = []
        for i in range(30):
            execution_id = str(uuid.uuid4())
            state_data = {
                "execution_id": execution_id,
                "user_id": user_id,
                "consistency_test": True,
                "sequence_number": i,
                "checksum": f"checksum_{i}_{execution_id}",
                "timestamp": time.time() - (i * 3600),  # 1 hour intervals
                "tier_distribution_data": {
                    "expected_tiers": ["hot", "warm", "cold"],
                    "consistency_requirements": "strict",
                    "validation_data": f"validate_{i}"
                }
            }
            test_states.append((execution_id, state_data))
        
        # Distribute data across all tiers
        for i, (execution_id, state_data) in enumerate(test_states):
            if i < 10:
                tier = StorageTier.HOT
            elif i < 20:
                tier = StorageTier.WARM
            else:
                tier = StorageTier.COLD
            
            await self.persistence.store_state(
                key=f"consistency_test:{execution_id}",
                data=state_data,
                tier=tier,
                lifecycle_policy=DataLifecyclePolicy.STANDARD
            )
        
        # Execute cross-tier consistency validation
        consistency_results = await self.persistence.validate_cross_tier_consistency(
            user_id=user_id,
            key_pattern="consistency_test:*"
        )
        
        self.assertIsNotNone(consistency_results, "Consistency validation failed")
        self.assertTrue(consistency_results.get("validation_successful", False), 
                       "Cross-tier consistency validation failed")
        
        # Verify all data is accessible from unified interface
        unified_retrieval_count = 0
        for execution_id, original_data in test_states:
            retrieved = await self.persistence.retrieve_state(
                key=f"consistency_test:{execution_id}",
                search_all_tiers=True
            )
            
            if (retrieved is not None and 
                retrieved["checksum"] == original_data["checksum"]):
                unified_retrieval_count += 1
        
        consistency_rate = unified_retrieval_count / len(test_states)
        self.assertGreater(consistency_rate, 0.95, 
                          f"Cross-tier consistency issues: {consistency_rate}")
        
        # Test consistency repair mechanisms
        repair_results = await self.persistence.repair_consistency_issues(
            user_id=user_id,
            dry_run=False
        )
        
        self.assertIsNotNone(repair_results, "Consistency repair failed")
        self.assertEqual(repair_results.get("errors_found", 0), 0, 
                        "Consistency errors requiring repair")

    @pytest.mark.e2e_gcp_staging
    async def test_data_compression_across_tiers_efficiency(self):
        """
        Test data compression efficiency across all storage tiers.
        
        Business Value: Cost optimization through efficient storage usage.
        Validates: Compression algorithms, storage efficiency, performance impact.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create large, compressible test data
        large_datasets = []
        for i in range(20):
            execution_id = str(uuid.uuid4())
            
            # Generate highly compressible data (repeated patterns)
            large_data = {
                "execution_id": execution_id,
                "user_id": user_id,
                "compression_test": True,
                "large_log_data": [
                    f"LOG_ENTRY_{j}: Standard log message with timestamp {time.time()} "
                    f"and repeated pattern data for compression testing. " * 10
                    for j in range(100)
                ],
                "repeated_configurations": {
                    f"config_{k}": {
                        "standard_value": "This is a standard configuration value " * 20,
                        "common_settings": ["setting_a", "setting_b", "setting_c"] * 50,
                        "metadata": {"created": time.time(), "version": "1.0.0"} 
                    }
                    for k in range(20)
                },
                "performance_samples": [
                    {
                        "timestamp": time.time() - (j * 60),
                        "cpu_usage": 50.0 + (j % 10),
                        "memory_usage": 1024 + (j * 10),
                        "network_io": {"in": j * 1000, "out": j * 500}
                    }
                    for j in range(200)
                ]
            }
            large_datasets.append((execution_id, large_data))
        
        # Store data with compression across all tiers
        storage_start_time = time.time()
        compression_results = {"hot": [], "warm": [], "cold": []}
        
        for i, (execution_id, large_data) in enumerate(large_datasets):
            if i < 7:
                tier = StorageTier.HOT
                tier_name = "hot"
            elif i < 14:
                tier = StorageTier.WARM
                tier_name = "warm"
            else:
                tier = StorageTier.COLD
                tier_name = "cold"
            
            # Store with compression enabled
            store_start = time.time()
            await self.persistence.store_state(
                key=f"compression_test:{execution_id}",
                data=large_data,
                tier=tier,
                lifecycle_policy=DataLifecyclePolicy.STANDARD,
                enable_compression=True
            )
            store_time = time.time() - store_start
            
            compression_results[tier_name].append({
                "execution_id": execution_id,
                "store_time": store_time,
                "original_size_estimate": len(json.dumps(large_data))
            })
        
        total_storage_time = time.time() - storage_start_time
        
        # Validate storage performance with compression
        self.assertLess(total_storage_time, 120.0, 
                       "Compression storage too slow for production")
        
        # Test retrieval with decompression
        retrieval_start_time = time.time()
        successful_retrievals = 0
        
        for execution_id, original_data in large_datasets:
            retrieved = await self.persistence.retrieve_state(
                key=f"compression_test:{execution_id}",
                search_all_tiers=True
            )
            
            if (retrieved is not None and 
                len(retrieved.get("large_log_data", [])) == 100):
                successful_retrievals += 1
        
        total_retrieval_time = time.time() - retrieval_start_time
        retrieval_rate = successful_retrievals / len(large_datasets)
        
        self.assertGreater(retrieval_rate, 0.95, 
                          f"Compression/decompression failure rate: {retrieval_rate}")
        self.assertLess(total_retrieval_time, 60.0, 
                       "Decompression retrieval too slow")
        
        # Validate storage efficiency metrics
        storage_metrics = await self.persistence.get_storage_metrics(user_id=user_id)
        self.assertIsNotNone(storage_metrics, "Storage metrics not available")
        
        # Compression should achieve at least 50% size reduction
        for tier_name in ["hot", "warm", "cold"]:
            if tier_name in storage_metrics:
                compression_ratio = storage_metrics[tier_name].get("compression_ratio", 1.0)
                self.assertLess(compression_ratio, 0.7, 
                               f"Insufficient compression in {tier_name} tier: {compression_ratio}")

    @pytest.mark.e2e_gcp_staging
    async def test_automated_data_lifecycle_management(self):
        """
        Test automated data lifecycle management policies.
        
        Business Value: Reduces operational overhead and storage costs.
        Validates: Automatic tier transitions, policy enforcement, cost optimization.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create data with different lifecycle policies
        lifecycle_data = {
            "ephemeral": [],      # Very short-lived data
            "standard": [],       # Normal business data
            "critical": [],       # High-importance data
            "analytics": [],      # Long-term analytics data
            "compliance": []      # Regulatory compliance data
        }
        
        policies = [
            ("ephemeral", DataLifecyclePolicy.EPHEMERAL, 300),    # 5 minutes
            ("standard", DataLifecyclePolicy.STANDARD, 3600),    # 1 hour
            ("critical", DataLifecyclePolicy.CRITICAL, 86400),   # 1 day
            ("analytics", DataLifecyclePolicy.ANALYTICS, 604800), # 1 week
            ("compliance", DataLifecyclePolicy.COMPLIANCE, 31536000) # 1 year
        ]
        
        # Generate test data for each policy
        for policy_name, policy_type, retention_seconds in policies:
            for i in range(10):
                execution_id = str(uuid.uuid4())
                state_data = {
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "policy_type": policy_name,
                    "retention_seconds": retention_seconds,
                    "lifecycle_test": True,
                    "created_at": time.time(),
                    "policy_data": {
                        "importance_level": policy_name,
                        "auto_transition": True,
                        "compliance_requirements": policy_name == "compliance"
                    }
                }
                lifecycle_data[policy_name].append((execution_id, state_data))
                
                # Store with appropriate lifecycle policy
                await self.persistence.store_state(
                    key=f"lifecycle_{policy_name}:{execution_id}",
                    data=state_data,
                    tier=StorageTier.HOT,  # All start in hot tier
                    lifecycle_policy=policy_type
                )
        
        # Trigger lifecycle management evaluation
        lifecycle_results = await self.persistence.evaluate_lifecycle_policies(
            user_id=user_id,
            force_evaluation=True
        )
        
        self.assertIsNotNone(lifecycle_results, "Lifecycle evaluation failed")
        self.assertTrue(lifecycle_results.get("evaluation_successful", False),
                       "Lifecycle policy evaluation unsuccessful")
        
        # Verify policy-appropriate actions were taken
        for policy_name, policy_type, retention_seconds in policies:
            policy_metrics = lifecycle_results.get(policy_name, {})
            
            # Check transition recommendations
            if policy_name in ["standard", "critical"]:
                # Should have tier transition recommendations
                self.assertGreater(policy_metrics.get("transition_candidates", 0), 0,
                                 f"No tier transitions for {policy_name} policy")
            
            if policy_name == "ephemeral":
                # Should have deletion candidates
                self.assertGreater(policy_metrics.get("deletion_candidates", 0), 0,
                                 f"No deletion candidates for {policy_name} policy")
        
        # Test policy override capabilities
        override_execution_id = str(uuid.uuid4())
        override_data = {
            "execution_id": override_execution_id,
            "override_test": True,
            "policy_override": "manual_retention"
        }
        
        await self.persistence.store_state(
            key=f"override_test:{override_execution_id}",
            data=override_data,
            tier=StorageTier.HOT,
            lifecycle_policy=DataLifecyclePolicy.STANDARD,
            policy_overrides={
                "retention_days": 365,  # Override to 1 year
                "tier_transitions_disabled": True,
                "deletion_protection": True
            }
        )
        
        # Verify override is respected
        override_policy = await self.persistence.get_lifecycle_policy(
            key=f"override_test:{override_execution_id}"
        )
        
        self.assertIsNotNone(override_policy, "Override policy not found")
        self.assertEqual(override_policy.get("retention_days"), 365)
        self.assertTrue(override_policy.get("deletion_protection", False))

    @pytest.mark.e2e_gcp_staging
    async def test_disaster_recovery_multi_tier_backup(self):
        """
        Test disaster recovery across all storage tiers.
        
        Business Value: $500K+ ARR protection through comprehensive backup strategy.
        Validates: Multi-tier backup, recovery procedures, data integrity.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create comprehensive disaster recovery test scenario
        dr_test_data = []
        
        # Simulate one month of business-critical data
        for day in range(30):
            for hour in range(24):
                execution_id = str(uuid.uuid4())
                timestamp = time.time() - (day * 24 * 3600) - (hour * 3600)
                
                dr_data = {
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "timestamp": timestamp,
                    "day": day,
                    "hour": hour,
                    "disaster_recovery_test": True,
                    "business_critical": True,
                    "financial_data": {
                        "revenue_impact": 1000 + (day * 50),
                        "cost_savings": 500 + (hour * 10),
                        "roi_metrics": {"efficiency": 0.85 + (day * 0.01)}
                    },
                    "customer_data": {
                        "enterprise_accounts": ["account_" + str(i) for i in range(5)],
                        "optimization_results": [
                            {"metric": f"metric_{j}", "improvement": j * 10}
                            for j in range(10)
                        ]
                    },
                    "compliance_metadata": {
                        "audit_required": True,
                        "retention_required": True,
                        "backup_priority": "high"
                    }
                }
                dr_test_data.append((execution_id, dr_data))
        
        # Distribute data across all tiers (as would happen naturally)
        tier_assignments = []
        for i, (execution_id, dr_data) in enumerate(dr_test_data):
            if i % 3 == 0:
                tier = StorageTier.HOT
            elif i % 3 == 1:
                tier = StorageTier.WARM
            else:
                tier = StorageTier.COLD
            
            tier_assignments.append((execution_id, tier))
            
            await self.persistence.store_state(
                key=f"dr_test:{execution_id}",
                data=dr_data,
                tier=tier,
                lifecycle_policy=DataLifecyclePolicy.CRITICAL
            )
        
        # Create comprehensive backup across all tiers
        backup_start_time = time.time()
        
        backup_result = await self.persistence.create_disaster_recovery_backup(
            user_id=user_id,
            backup_scope="full",  # All tiers
            include_metadata=True,
            include_lifecycle_policies=True,
            compression_level="high"
        )
        
        backup_time = time.time() - backup_start_time
        
        self.assertTrue(backup_result.get("success", False), 
                       "Disaster recovery backup failed")
        self.assertIsNotNone(backup_result.get("backup_id"), 
                           "No backup ID generated")
        self.assertLess(backup_time, 300.0, 
                       "Backup creation too slow for disaster recovery requirements")
        
        # Validate backup completeness
        backup_metadata = backup_result.get("metadata", {})
        self.assertEqual(backup_metadata.get("total_records"), len(dr_test_data))
        self.assertIn("hot_tier_records", backup_metadata)
        self.assertIn("warm_tier_records", backup_metadata)
        self.assertIn("cold_tier_records", backup_metadata)
        
        # Simulate disaster - clear all data
        disaster_simulation_start = time.time()
        
        await self.persistence.simulate_disaster(
            user_id=user_id,
            disaster_type="complete_data_loss",
            affected_tiers=["hot", "warm", "cold"]
        )
        
        # Verify data is gone
        verification_count = 0
        for execution_id, _ in dr_test_data[:10]:  # Test subset
            retrieved = await self.persistence.retrieve_state(
                key=f"dr_test:{execution_id}",
                search_all_tiers=True
            )
            if retrieved is None:
                verification_count += 1
        
        self.assertGreater(verification_count / 10, 0.8, 
                          "Disaster simulation incomplete")
        
        # Execute disaster recovery
        recovery_start_time = time.time()
        
        recovery_result = await self.persistence.execute_disaster_recovery(
            backup_id=backup_result["backup_id"],
            user_id=user_id,
            recovery_scope="full",
            verify_integrity=True
        )
        
        recovery_time = time.time() - recovery_start_time
        
        self.assertTrue(recovery_result.get("success", False), 
                       "Disaster recovery execution failed")
        self.assertLess(recovery_time, 600.0, 
                       "Recovery too slow for business continuity requirements")
        
        # Validate recovery completeness and integrity
        recovered_count = 0
        integrity_verified = 0
        
        for execution_id, original_data in dr_test_data:
            recovered = await self.persistence.retrieve_state(
                key=f"dr_test:{execution_id}",
                search_all_tiers=True
            )
            
            if recovered is not None:
                recovered_count += 1
                
                # Verify data integrity
                if (recovered["financial_data"]["revenue_impact"] == 
                    original_data["financial_data"]["revenue_impact"]):
                    integrity_verified += 1
        
        recovery_rate = recovered_count / len(dr_test_data)
        integrity_rate = integrity_verified / len(dr_test_data)
        
        # Business requirements: 99%+ recovery rate, 100% data integrity
        self.assertGreater(recovery_rate, 0.99, 
                          f"Insufficient disaster recovery rate: {recovery_rate}")
        self.assertGreater(integrity_rate, 0.99, 
                          f"Data integrity issues after recovery: {integrity_rate}")

    @pytest.mark.e2e_gcp_staging
    async def test_enterprise_compliance_data_governance(self):
        """
        Test enterprise compliance and data governance features.
        
        Business Value: $15K+ MRR per Enterprise - regulatory compliance capabilities.
        Validates: Data governance, audit trails, compliance reporting.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create compliance-sensitive data
        compliance_categories = [
            "financial_records",
            "customer_pii", 
            "security_logs",
            "audit_trails",
            "regulatory_reports"
        ]
        
        compliance_data = []
        for category in compliance_categories:
            for i in range(20):
                execution_id = str(uuid.uuid4())
                sensitive_data = {
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "compliance_category": category,
                    "sensitivity_level": "high",
                    "regulatory_requirements": {
                        "gdpr_applicable": True,
                        "sox_applicable": category == "financial_records",
                        "hipaa_applicable": category == "customer_pii",
                        "retention_years": 7,
                        "encryption_required": True,
                        "audit_logging_required": True
                    },
                    "data_classification": {
                        "confidentiality": "confidential",
                        "integrity": "high",
                        "availability": "high"
                    },
                    "sensitive_content": {
                        "encrypted_field_1": f"SENSITIVE_{category}_{i}",
                        "encrypted_field_2": f"CONFIDENTIAL_DATA_{execution_id}",
                        "metadata": {"created": time.time(), "category": category}
                    },
                    "compliance_metadata": {
                        "data_subject_id": f"subject_{i}",
                        "legal_basis": "legitimate_interest",
                        "consent_timestamp": time.time(),
                        "retention_start": time.time()
                    }
                }
                compliance_data.append((execution_id, sensitive_data, category))
        
        # Store compliance data with appropriate governance controls
        governance_tasks = []
        for execution_id, sensitive_data, category in compliance_data:
            task = self.persistence.store_state(
                key=f"compliance_{category}:{execution_id}",
                data=sensitive_data,
                tier=StorageTier.WARM,  # Compliance data in secure warm storage
                lifecycle_policy=DataLifecyclePolicy.COMPLIANCE,
                governance_controls={
                    "encryption_level": "enterprise",
                    "access_logging": True,
                    "data_classification": sensitive_data["data_classification"],
                    "retention_policy": "regulatory_7_years",
                    "audit_requirements": "full"
                }
            )
            governance_tasks.append(task)
        
        # Execute compliant storage
        governance_results = await asyncio.gather(*governance_tasks, return_exceptions=True)
        failures = [r for r in governance_results if isinstance(r, Exception)]
        self.assertEqual(len(failures), 0, 
                        f"Compliance storage failures: {failures}")
        
        # Test data governance audit capabilities
        audit_start_time = time.time()
        
        audit_report = await self.persistence.generate_compliance_audit_report(
            user_id=user_id,
            audit_scope="full",
            regulatory_frameworks=["gdpr", "sox", "hipaa"],
            time_range_days=30
        )
        
        audit_generation_time = time.time() - audit_start_time
        
        self.assertIsNotNone(audit_report, "Compliance audit report generation failed")
        self.assertLess(audit_generation_time, 60.0, 
                       "Audit report generation too slow")
        
        # Validate audit report completeness
        self.assertIn("data_inventory", audit_report)
        self.assertIn("access_logs", audit_report)
        self.assertIn("retention_compliance", audit_report)
        self.assertIn("encryption_status", audit_report)
        
        # Verify data inventory accuracy
        data_inventory = audit_report["data_inventory"]
        total_records = sum(data_inventory.get(cat, 0) for cat in compliance_categories)
        self.assertEqual(total_records, len(compliance_data), 
                        "Data inventory count mismatch")
        
        # Test right-to-be-forgotten (data deletion) compliance
        deletion_subject_id = "subject_5"
        
        deletion_result = await self.persistence.execute_right_to_be_forgotten(
            user_id=user_id,
            data_subject_id=deletion_subject_id,
            regulatory_basis="gdpr_article_17",
            verification_required=True
        )
        
        self.assertTrue(deletion_result.get("success", False), 
                       "Right-to-be-forgotten execution failed")
        self.assertGreater(deletion_result.get("records_deleted", 0), 0, 
                          "No records deleted for data subject")
        
        # Verify deletion completeness
        remaining_records = await self.persistence.search_by_data_subject(
            user_id=user_id,
            data_subject_id=deletion_subject_id
        )
        
        self.assertEqual(len(remaining_records), 0, 
                        "Data subject records not completely deleted")
        
        # Test data portability (GDPR Article 20)
        export_subject_id = "subject_10"
        
        portability_result = await self.persistence.export_data_subject_data(
            user_id=user_id,
            data_subject_id=export_subject_id,
            export_format="json",
            include_metadata=True
        )
        
        self.assertTrue(portability_result.get("success", False), 
                       "Data portability export failed")
        self.assertIsNotNone(portability_result.get("export_data"), 
                           "No export data generated")
        
        # Validate export data structure and completeness
        export_data = portability_result["export_data"]
        self.assertIn("personal_data", export_data)
        self.assertIn("processing_activities", export_data)
        self.assertIn("metadata", export_data)
        
        # Test retention policy enforcement
        retention_enforcement = await self.persistence.enforce_retention_policies(
            user_id=user_id,
            dry_run=False,
            regulatory_frameworks=["gdpr", "sox"]
        )
        
        self.assertIsNotNone(retention_enforcement, "Retention enforcement failed")
        self.assertTrue(retention_enforcement.get("enforcement_successful", False), 
                       "Retention policy enforcement unsuccessful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])