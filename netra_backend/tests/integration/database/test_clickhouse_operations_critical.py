"""
Test ClickHouse Operations Critical - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal, Enterprise
- Business Goal: Data integrity and analytics reliability
- Value Impact: Ensures critical data operations function properly
- Strategic Impact: Foundation for data-driven insights and decision making

CRITICAL REQUIREMENTS:
- Tests real ClickHouse database operations
- Validates data integrity and query performance  
- Ensures analytics pipeline reliability
- No mocks - uses real ClickHouse service
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from test_framework.ssot.no_docker_mode_detector import skip_if_no_docker_and_services_unavailable_async
from shared.isolated_environment import get_env

from netra_backend.app.db.clickhouse import ClickHouseClient
from netra_backend.app.db.clickhouse_initializer import ClickHouseInitializer
from netra_backend.app.db.clickhouse_schema import ClickHouseSchema
from netra_backend.app.db.models_clickhouse import (
    EventRecord, 
    MetricsRecord,
    UserActivityRecord
)


class TestClickHouseOperationsCritical(SSotBaseTestCase):
    """
    Critical ClickHouse operations tests.
    
    Tests core database operations that are essential for business value:
    - Data insertion and retrieval
    - Query performance under load
    - Schema management and migration
    - Data integrity validation
    - Analytics query correctness
    """
    
    def __init__(self):
        """Initialize ClickHouse operations test suite."""
        super().__init__()
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_database = f"test_clickhouse_{uuid.uuid4().hex[:8]}"
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
    async def setup_test_environment(self) -> ClickHouseClient:
        """Set up isolated test environment with real ClickHouse."""
        # Initialize ClickHouse client with test configuration
        clickhouse_url = self.env.get("CLICKHOUSE_URL", "http://localhost:8123")
        clickhouse_host = self.env.get("CLICKHOUSE_HOST", "localhost")
        clickhouse_port = int(self.env.get("CLICKHOUSE_PORT", "8123"))
        
        client = ClickHouseClient(
            host=clickhouse_host,
            port=clickhouse_port,
            database=self.test_database
        )
        
        # Initialize test database schema
        initializer = ClickHouseInitializer(client)
        await initializer.create_database(self.test_database)
        await initializer.initialize_tables()
        
        return client
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @skip_if_no_docker_and_services_unavailable_async("clickhouse")
    async def test_clickhouse_event_insertion_and_retrieval(self):
        """
        Test critical event insertion and retrieval operations.
        
        BUSINESS CRITICAL: Event tracking is core to analytics and user insights.
        Failure means loss of critical business data.
        """
        client = await self.setup_test_environment()
        
        try:
            # Create test event records
            test_events = [
                EventRecord(
                    event_id=f"evt_{i}_{uuid.uuid4().hex[:6]}",
                    user_id=self.test_user_id,
                    event_type="user_action",
                    event_data={
                        "action": f"test_action_{i}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {"test": True, "sequence": i}
                    },
                    created_at=datetime.now(timezone.utc)
                ) for i in range(10)
            ]
            
            # Insert events in batch (critical for performance)
            start_time = datetime.now()
            insert_result = await client.insert_events_batch(test_events)
            insert_duration = (datetime.now() - start_time).total_seconds()
            
            # Validate insertion performance (business critical)
            assert insert_result.success, f"Event batch insertion failed: {insert_result.error}"
            assert insert_result.inserted_count == 10, f"Expected 10 events, inserted {insert_result.inserted_count}"
            assert insert_duration < 2.0, f"Insert took too long: {insert_duration}s (max: 2.0s)"
            
            # Wait for data propagation (ClickHouse eventual consistency)
            await asyncio.sleep(1.0)
            
            # Retrieve events and validate data integrity
            retrieved_events = await client.get_user_events(
                user_id=self.test_user_id,
                limit=20
            )
            
            assert len(retrieved_events) == 10, f"Expected 10 events, got {len(retrieved_events)}"
            
            # Validate each event's data integrity
            for i, event in enumerate(retrieved_events):
                assert event.user_id == self.test_user_id
                assert event.event_type == "user_action"
                assert "test_action_" in event.event_data["action"]
                assert event.event_data["metadata"]["test"] is True
                
            # Test query performance (critical for real-time analytics)
            query_start = datetime.now()
            event_count = await client.get_user_event_count(
                user_id=self.test_user_id,
                event_type="user_action"
            )
            query_duration = (datetime.now() - query_start).total_seconds()
            
            assert event_count == 10
            assert query_duration < 1.0, f"Query too slow: {query_duration}s (max: 1.0s)"
            
        finally:
            # Cleanup test data
            await client.cleanup_test_data(user_id=self.test_user_id)
            await client.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @skip_if_no_docker_and_services_unavailable_async("clickhouse")
    async def test_clickhouse_metrics_aggregation_accuracy(self):
        """
        Test metrics aggregation accuracy for business reporting.
        
        BUSINESS CRITICAL: Inaccurate metrics lead to wrong business decisions.
        Financial impact of data errors can be severe.
        """
        client = await self.setup_test_environment()
        
        try:
            # Create test metrics with known values for validation
            test_metrics = []
            expected_sum = 0
            expected_avg = 0
            
            for i in range(20):
                value = i * 10 + 100  # Values: 100, 110, 120, ..., 290
                expected_sum += value
                
                metric = MetricsRecord(
                    metric_id=f"metric_{i}_{uuid.uuid4().hex[:6]}",
                    user_id=self.test_user_id,
                    metric_name="test_business_metric",
                    metric_value=float(value),
                    dimensions={
                        "category": "test",
                        "sequence": i,
                        "batch": "phase_5_test"
                    },
                    recorded_at=datetime.now(timezone.utc) - timedelta(minutes=i)
                )
                test_metrics.append(metric)
            
            expected_avg = expected_sum / 20
            
            # Insert metrics batch
            insert_result = await client.insert_metrics_batch(test_metrics)
            assert insert_result.success, f"Metrics insertion failed: {insert_result.error}"
            assert insert_result.inserted_count == 20
            
            # Wait for data propagation
            await asyncio.sleep(1.5)
            
            # Test aggregation accuracy - SUM
            sum_result = await client.aggregate_metrics(
                user_id=self.test_user_id,
                metric_name="test_business_metric",
                aggregation_type="SUM",
                time_range_hours=24
            )
            
            assert abs(sum_result - expected_sum) < 0.01, f"SUM aggregation incorrect: expected {expected_sum}, got {sum_result}"
            
            # Test aggregation accuracy - AVG  
            avg_result = await client.aggregate_metrics(
                user_id=self.test_user_id,
                metric_name="test_business_metric", 
                aggregation_type="AVG",
                time_range_hours=24
            )
            
            assert abs(avg_result - expected_avg) < 0.01, f"AVG aggregation incorrect: expected {expected_avg}, got {avg_result}"
            
            # Test aggregation accuracy - COUNT
            count_result = await client.aggregate_metrics(
                user_id=self.test_user_id,
                metric_name="test_business_metric",
                aggregation_type="COUNT",
                time_range_hours=24
            )
            
            assert count_result == 20, f"COUNT aggregation incorrect: expected 20, got {count_result}"
            
            # Test MIN/MAX accuracy
            min_result = await client.aggregate_metrics(
                user_id=self.test_user_id,
                metric_name="test_business_metric",
                aggregation_type="MIN", 
                time_range_hours=24
            )
            
            max_result = await client.aggregate_metrics(
                user_id=self.test_user_id,
                metric_name="test_business_metric",
                aggregation_type="MAX",
                time_range_hours=24
            )
            
            assert min_result == 100.0, f"MIN incorrect: expected 100, got {min_result}"
            assert max_result == 290.0, f"MAX incorrect: expected 290, got {max_result}"
            
        finally:
            await client.cleanup_test_data(user_id=self.test_user_id)
            await client.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @skip_if_no_docker_and_services_unavailable_async("clickhouse")
    async def test_clickhouse_query_performance_under_load(self):
        """
        Test query performance under realistic load conditions.
        
        BUSINESS CRITICAL: Poor query performance impacts user experience
        and can cause system timeouts in production.
        """
        client = await self.setup_test_environment()
        
        try:
            # Create substantial dataset (1000 records)
            large_dataset = []
            user_ids = [f"user_{i}_load_test" for i in range(10)]
            
            for user_idx, user_id in enumerate(user_ids):
                for record_idx in range(100):
                    activity = UserActivityRecord(
                        activity_id=f"activity_{user_idx}_{record_idx}_{uuid.uuid4().hex[:4]}",
                        user_id=user_id,
                        activity_type="data_query",
                        activity_data={
                            "query_type": "analytics",
                            "processing_time": record_idx * 10 + 50,
                            "result_count": record_idx + 10,
                            "user_sequence": user_idx
                        },
                        created_at=datetime.now(timezone.utc) - timedelta(minutes=record_idx)
                    )
                    large_dataset.append(activity)
            
            # Insert large dataset in batches (realistic load)
            batch_size = 200
            total_inserted = 0
            
            for i in range(0, len(large_dataset), batch_size):
                batch = large_dataset[i:i + batch_size]
                insert_result = await client.insert_user_activities_batch(batch)
                assert insert_result.success, f"Batch {i//batch_size + 1} insertion failed"
                total_inserted += insert_result.inserted_count
            
            assert total_inserted == 1000, f"Expected 1000 records, inserted {total_inserted}"
            
            # Wait for data propagation
            await asyncio.sleep(2.0)
            
            # Test concurrent queries (realistic load simulation)
            query_tasks = []
            
            for user_id in user_ids[:5]:  # Test with 5 concurrent users
                # Complex aggregation query
                task1 = client.aggregate_user_activities(
                    user_id=user_id,
                    activity_type="data_query",
                    aggregation="COUNT",
                    time_range_hours=24
                )
                
                # Range query with sorting
                task2 = client.get_user_activities_in_range(
                    user_id=user_id,
                    start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                    end_time=datetime.now(timezone.utc),
                    limit=50,
                    order_by="created_at DESC"
                )
                
                query_tasks.extend([task1, task2])
            
            # Execute all queries concurrently
            start_time = datetime.now()
            results = await asyncio.gather(*query_tasks, return_exceptions=True)
            total_duration = (datetime.now() - start_time).total_seconds()
            
            # Validate performance requirements
            assert total_duration < 10.0, f"Concurrent queries too slow: {total_duration}s (max: 10.0s)"
            
            # Validate all queries succeeded
            failed_queries = [r for r in results if isinstance(r, Exception)]
            assert len(failed_queries) == 0, f"Query failures: {failed_queries}"
            
            # Validate query result accuracy
            count_results = [r for i, r in enumerate(results) if i % 2 == 0]  # Aggregation results
            range_results = [r for i, r in enumerate(results) if i % 2 == 1]   # Range query results
            
            for count in count_results:
                assert count == 100, f"Incorrect activity count: expected 100, got {count}"
            
            for activities in range_results:
                assert isinstance(activities, list), "Range query should return list"
                assert len(activities) <= 50, f"Too many results: {len(activities)} (max: 50)"
            
        finally:
            # Cleanup large dataset
            for user_id in user_ids:
                await client.cleanup_test_data(user_id=user_id)
            await client.close()
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    @skip_if_no_docker_and_services_unavailable_async("clickhouse")
    async def test_clickhouse_data_consistency_validation(self):
        """
        Test data consistency across operations and time.
        
        BUSINESS CRITICAL: Data inconsistency corrupts business reporting
        and analytics, leading to incorrect business decisions.
        """
        client = await self.setup_test_environment()
        
        try:
            # Create controlled dataset with known relationships
            event_records = []
            metric_records = []
            activity_records = []
            
            # Create related records with consistent timestamps
            base_time = datetime.now(timezone.utc)
            
            for i in range(5):
                event_time = base_time - timedelta(minutes=i)
                
                # Event record
                event = EventRecord(
                    event_id=f"consistency_event_{i}",
                    user_id=self.test_user_id,
                    event_type="business_transaction", 
                    event_data={
                        "transaction_amount": 100 + i * 10,
                        "currency": "USD",
                        "consistency_id": f"consistency_{i}"
                    },
                    created_at=event_time
                )
                event_records.append(event)
                
                # Related metric record
                metric = MetricsRecord(
                    metric_id=f"consistency_metric_{i}",
                    user_id=self.test_user_id,
                    metric_name="transaction_value",
                    metric_value=float(100 + i * 10),
                    dimensions={
                        "consistency_id": f"consistency_{i}",
                        "currency": "USD"
                    },
                    recorded_at=event_time
                )
                metric_records.append(metric)
                
                # Related activity record
                activity = UserActivityRecord(
                    activity_id=f"consistency_activity_{i}",
                    user_id=self.test_user_id,
                    activity_type="transaction_processing",
                    activity_data={
                        "processed_amount": 100 + i * 10,
                        "consistency_id": f"consistency_{i}",
                        "processing_status": "completed"
                    },
                    created_at=event_time + timedelta(seconds=30)  # Processing delay
                )
                activity_records.append(activity)
            
            # Insert all records
            event_result = await client.insert_events_batch(event_records)
            metric_result = await client.insert_metrics_batch(metric_records)  
            activity_result = await client.insert_user_activities_batch(activity_records)
            
            assert all(r.success for r in [event_result, metric_result, activity_result]), \
                "One or more insertions failed"
            
            # Wait for data propagation
            await asyncio.sleep(1.5)
            
            # Validate data consistency across tables
            events = await client.get_user_events(
                user_id=self.test_user_id,
                event_type="business_transaction"
            )
            
            metrics = await client.get_user_metrics(
                user_id=self.test_user_id,
                metric_name="transaction_value"
            )
            
            activities = await client.get_user_activities(
                user_id=self.test_user_id,
                activity_type="transaction_processing"
            )
            
            # Validate record counts match
            assert len(events) == 5, f"Expected 5 events, got {len(events)}"
            assert len(metrics) == 5, f"Expected 5 metrics, got {len(metrics)}"
            assert len(activities) == 5, f"Expected 5 activities, got {len(activities)}"
            
            # Validate data relationships and consistency
            for i in range(5):
                expected_amount = 100 + i * 10
                consistency_id = f"consistency_{i}"
                
                # Find related records
                related_event = next(
                    (e for e in events if e.event_data.get("consistency_id") == consistency_id),
                    None
                )
                related_metric = next(
                    (m for m in metrics if m.dimensions.get("consistency_id") == consistency_id),
                    None
                )
                related_activity = next(
                    (a for a in activities if a.activity_data.get("consistency_id") == consistency_id),
                    None
                )
                
                # Validate all related records exist
                assert related_event is not None, f"Missing event for consistency_id {consistency_id}"
                assert related_metric is not None, f"Missing metric for consistency_id {consistency_id}"
                assert related_activity is not None, f"Missing activity for consistency_id {consistency_id}"
                
                # Validate data consistency across records
                event_amount = related_event.event_data["transaction_amount"]
                metric_amount = related_metric.metric_value
                activity_amount = related_activity.activity_data["processed_amount"]
                
                assert event_amount == expected_amount, \
                    f"Event amount inconsistent: expected {expected_amount}, got {event_amount}"
                assert metric_amount == expected_amount, \
                    f"Metric amount inconsistent: expected {expected_amount}, got {metric_amount}"  
                assert activity_amount == expected_amount, \
                    f"Activity amount inconsistent: expected {expected_amount}, got {activity_amount}"
            
            # Test aggregate consistency
            total_transaction_value = sum(100 + i * 10 for i in range(5))  # 600
            
            aggregated_metrics = await client.aggregate_metrics(
                user_id=self.test_user_id,
                metric_name="transaction_value",
                aggregation_type="SUM",
                time_range_hours=1
            )
            
            assert abs(aggregated_metrics - total_transaction_value) < 0.01, \
                f"Aggregate inconsistent: expected {total_transaction_value}, got {aggregated_metrics}"
            
        finally:
            await client.cleanup_test_data(user_id=self.test_user_id)
            await client.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @skip_if_no_docker_and_services_unavailable_async("clickhouse")
    async def test_clickhouse_schema_migration_integrity(self):
        """
        Test schema migration maintains data integrity.
        
        BUSINESS CRITICAL: Schema changes must not corrupt existing data.
        Data loss during migrations can have severe business impact.
        """
        client = await self.setup_test_environment()
        
        try:
            # Insert data in original schema
            original_events = [
                EventRecord(
                    event_id=f"migration_test_{i}",
                    user_id=self.test_user_id,
                    event_type="schema_test",
                    event_data={
                        "original_field": f"value_{i}",
                        "numeric_field": i * 100
                    },
                    created_at=datetime.now(timezone.utc)
                ) for i in range(3)
            ]
            
            insert_result = await client.insert_events_batch(original_events)
            assert insert_result.success, f"Original data insertion failed: {insert_result.error}"
            
            # Wait for data propagation
            await asyncio.sleep(1.0)
            
            # Verify original data exists
            original_data = await client.get_user_events(
                user_id=self.test_user_id,
                event_type="schema_test"
            )
            assert len(original_data) == 3, f"Original data missing: expected 3, got {len(original_data)}"
            
            # Simulate schema migration (add new column with default)
            schema = ClickHouseSchema()
            migration_result = await schema.add_column_with_default(
                table_name="events",
                column_name="migration_field",
                column_type="String",
                default_value="'migrated'"
            )
            assert migration_result.success, f"Schema migration failed: {migration_result.error}"
            
            # Verify original data still accessible and intact
            post_migration_data = await client.get_user_events(
                user_id=self.test_user_id,
                event_type="schema_test"
            )
            
            assert len(post_migration_data) == 3, \
                f"Data lost during migration: expected 3, got {len(post_migration_data)}"
            
            # Validate original data integrity preserved
            for i, event in enumerate(post_migration_data):
                assert event.event_data["original_field"] == f"value_{i}", \
                    f"Original data corrupted: {event.event_data}"
                assert event.event_data["numeric_field"] == i * 100, \
                    f"Numeric data corrupted: {event.event_data}"
            
            # Test inserting data with new schema
            new_schema_events = [
                EventRecord(
                    event_id=f"post_migration_{i}",
                    user_id=self.test_user_id,
                    event_type="schema_test",
                    event_data={
                        "original_field": f"new_value_{i}",
                        "numeric_field": i * 200,
                        "migration_field": "explicitly_set"
                    },
                    created_at=datetime.now(timezone.utc)
                ) for i in range(2)
            ]
            
            new_insert_result = await client.insert_events_batch(new_schema_events)
            assert new_insert_result.success, f"Post-migration insertion failed: {new_insert_result.error}"
            
            # Wait and verify all data
            await asyncio.sleep(1.0)
            
            final_data = await client.get_user_events(
                user_id=self.test_user_id,
                event_type="schema_test"
            )
            
            assert len(final_data) == 5, f"Final data count wrong: expected 5, got {len(final_data)}"
            
            # Validate mixed schema data coexists correctly
            original_records = [e for e in final_data if "migration_field" not in e.event_data or e.event_data["migration_field"] == "migrated"]
            new_records = [e for e in final_data if e.event_data.get("migration_field") == "explicitly_set"]
            
            assert len(original_records) == 3, f"Original records corrupted: {len(original_records)}"
            assert len(new_records) == 2, f"New records missing: {len(new_records)}"
            
        finally:
            await client.cleanup_test_data(user_id=self.test_user_id)
            await client.close()


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])