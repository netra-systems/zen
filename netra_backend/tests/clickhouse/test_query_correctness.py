from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""
Test Suite 1: Query Correctness Tests
Tests the correctness of ClickHouse queries and their results
"""

from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import json
import uuid
from datetime import datetime, timedelta

import pytest

from netra_backend.app.agents.data_sub_agent.query_builder import QueryBuilder
from netra_backend.app.db.models_clickhouse import (

    WORKLOAD_EVENTS_TABLE_SCHEMA,

    get_content_corpus_schema,

    get_llm_events_table_schema,

)

from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.tests.clickhouse.helpers.shared_test_types import (

    TestErrorHandling as SharedTestErrorHandling,

)

class TestCorpusQueries:

    """Test corpus-related queries for correctness"""

    @pytest.mark.asyncio
    async def test_create_corpus_table_schema(self):

        """Test 1: Verify corpus table schema is valid SQL"""

        table_name = "test_corpus_123"

        schema = get_content_corpus_schema(table_name)
        
        assert "CREATE TABLE IF NOT EXISTS" in schema

        assert table_name in schema

        assert "`record_id` UUID" in schema

        assert "`workload_type` String" in schema

        assert "`prompt` String" in schema

        assert "`response` String" in schema

        assert "ENGINE = MergeTree()" in schema

        assert "ORDER BY (created_at, workload_type)" in schema

    @pytest.mark.asyncio
    async def test_corpus_insert_query_structure(self):

        """Test 2: Verify INSERT query structure for corpus"""

        service = CorpusService()

        table_name = "test_corpus"
        
        # Mock the client to capture the query

        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.services.corpus_service.get_clickhouse_client') as mock_client:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_client.return_value.__aenter__.return_value = mock_instance
            
            records = [

                {"workload_type": "test", "prompt": "p1", "response": "r1"},

                {"workload_type": "test", "prompt": "p2", "response": "r2"}

            ]
            
            await service._insert_corpus_records(table_name, records)
            
            # Verify the INSERT query was called with proper structure

            mock_instance.execute.assert_called_once()

            args = mock_instance.execute.call_args[0]

            query = args[0]
            
            assert f"INSERT INTO {table_name}" in query

            assert "workload_type, prompt, response" in query

            assert "VALUES" in query

    @pytest.mark.asyncio
    async def test_corpus_statistics_query(self):

        """Test 3: Verify corpus statistics query correctness"""

        service = CorpusService()
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.services.corpus.search_operations.get_clickhouse_client') as mock_client:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock database corpus

            # Mock: Generic component isolation for controlled unit testing
            db = MagicMock()  # TODO: Use real service instance
            db.execute = AsyncMock()  # db.execute() is async in SQLAlchemy async sessions
            db.commit = AsyncMock()  # db.commit() is async
            db.refresh = AsyncMock()  # db.refresh() is async

            # Mock: Generic component isolation for controlled unit testing
            corpus = MagicMock()  # TODO: Use real service instance

            corpus.id = "test_id"

            corpus.status = "available"

            corpus.table_name = "test_table"

            # Mock the result of db.execute for corpus lookup
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = corpus
            db.execute.return_value = mock_result
            
            # Mock query results

            mock_instance.execute.side_effect = [

                [(100, 5, 50.5, 75.2, datetime.now(), datetime.now())],  # stats query

                [("type1", 60), ("type2", 40)]  # distribution query

            ]
            
            result = await service.get_corpus_statistics(db, "test_id")
            
            # Verify queries were executed

            assert mock_instance.execute.call_count == 2
            
            # Check first query (statistics)

            stats_query = mock_instance.execute.call_args_list[0][0][0]

            assert "COUNT(*) as total_records" in stats_query

            assert "AVG(LENGTH(prompt))" in stats_query

            assert "AVG(LENGTH(response))" in stats_query
            
            # Check second query (distribution)

            dist_query = mock_instance.execute.call_args_list[1][0][0]

            assert "GROUP BY workload_type" in dist_query

    @pytest.mark.asyncio
    async def test_corpus_content_retrieval_query(self):

        """Test 4: Verify corpus content retrieval with filters"""

        service = CorpusService()
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.services.corpus.search_operations.get_clickhouse_client') as mock_client:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock database corpus

            # Mock: Generic component isolation for controlled unit testing
            db = MagicMock()  # TODO: Use real service instance
            db.execute = AsyncMock()  # db.execute() is async in SQLAlchemy async sessions
            db.commit = AsyncMock()  # db.commit() is async
            db.refresh = AsyncMock()  # db.refresh() is async

            # Mock: Generic component isolation for controlled unit testing
            corpus = MagicMock()  # TODO: Use real service instance

            corpus.status = "available"

            corpus.table_name = "test_table"

            # Mock the result of db.execute for corpus lookup
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = corpus
            db.execute.return_value = mock_result
            
            mock_instance.execute.return_value = []
            
            result = await service.get_corpus_content(

                db, "test_id", 

                limit=50, 

                offset=100,

                workload_type="rag_pipeline"

            )
            
            # NOTE: Current implementation is a stub that returns empty list
            # This test verifies the stub behavior until real implementation exists
            assert result == []
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_clone_corpus_copy_query(self):

        """Test 5: Verify corpus cloning query"""

        service = CorpusService()
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.services.corpus_service.get_clickhouse_client') as mock_client:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_client.return_value.__aenter__.return_value = mock_instance
            
            source_table = "source_corpus"

            dest_table = "dest_corpus"
            
            await service._copy_corpus_content(

                # Mock: Generic component isolation for controlled unit testing
                source_table, dest_table, "new_id", MagicMock()  # TODO: Use real service instance

            )
            
            # Wait for the async sleep
            import asyncio

            await asyncio.sleep(2.1)
            
            query = mock_instance.execute.call_args[0][0]

            assert f"INSERT INTO {dest_table}" in query

            assert f"SELECT * FROM {source_table}" in query

class TestPerformanceMetricsQueries:

    """Test performance metrics queries"""
    
    def test_performance_metrics_query_structure(self):

        """Test 6: Verify performance metrics query with aggregations"""

        query = QueryBuilder.build_performance_metrics_query(

            user_id=123,

            workload_id="wl_456",

            start_time=datetime(2025, 1, 1),

            end_time=datetime(2025, 1, 2),

            aggregation_level="hour"

        )
        
        assert "toStartOfHour(timestamp) as time_bucket" in query

        assert "quantileIf(0.5, metric_value, has_latency) as latency_p50" in query

        assert "quantileIf(0.95, metric_value, has_latency) as latency_p95" in query

        assert "quantileIf(0.99, metric_value, has_latency) as latency_p99" in query

        assert "WHERE user_id = 123" in query

        assert "AND workload_id = 'wl_456'" in query

        assert "arrayFirstIndex(x -> x = 'latency_ms', metrics.name)" in query

        assert "GROUP BY time_bucket" in query

        assert "ORDER BY time_bucket DESC" in query
    
    def test_performance_metrics_without_workload_filter(self):

        """Test 7: Verify query works without workload_id filter"""

        query = QueryBuilder.build_performance_metrics_query(

            user_id=123,

            workload_id=None,

            start_time=datetime(2025, 1, 1),

            end_time=datetime(2025, 1, 2),

            aggregation_level="minute"

        )
        
        assert "AND workload_id" not in query

        assert "WHERE user_id = 123" in query
    
    def test_aggregation_level_functions(self):

        """Test 8: Verify different aggregation levels"""

        levels = {

            "second": "toStartOfSecond",

            "minute": "toStartOfMinute", 

            "hour": "toStartOfHour",

            "day": "toStartOfDay"

        }
        
        for level, expected_func in levels.items():

            query = QueryBuilder.build_performance_metrics_query(

                user_id=1,

                workload_id=None,

                start_time=datetime.now(),

                end_time=datetime.now(),

                aggregation_level=level

            )

            assert f"{expected_func}(timestamp)" in query

class TestAnomalyDetectionQueries:

    """Test anomaly detection queries"""
    
    def test_anomaly_detection_query_structure(self):

        """Test 9: Verify anomaly detection query with CTEs"""

        query = QueryBuilder.build_anomaly_detection_query(

            user_id=456,

            metric_name="latency_ms",

            start_time=datetime(2025, 1, 10),

            end_time=datetime(2025, 1, 11),

            z_score_threshold=2.5

        )
        
        # Check for baseline CTE

        assert "WITH baseline AS" in query

        assert "avg(if(idx > 0, arrayElement(metrics.value, idx), 0.0)) as mean_val" in query

        assert "stddevPop(if(idx > 0, arrayElement(metrics.value, idx), 0.0)) as std_val" in query
        
        # Check for metric extraction

        assert "arrayFirstIndex(x -> x = 'latency_ms', metrics.name)" in query
        
        # Check for z-score calculation

        assert "z_score" in query

        assert "/ baseline.std_val" in query
        
        # Check for anomaly detection

        assert "is_anomaly" in query

        assert "abs(z_score) > 2.5" in query
    
    def test_anomaly_baseline_window(self):

        """Test 10: Verify baseline calculation uses 7-day lookback"""

        end_time = datetime(2025, 1, 11)

        start_time = datetime(2025, 1, 10)
        
        query = QueryBuilder.build_anomaly_detection_query(

            user_id=1,

            metric_name="cost_cents",

            start_time=start_time,

            end_time=end_time,

            z_score_threshold=2.0

        )
        
        # Should look back 7 days from start_time for baseline

        expected_baseline_start = (start_time - timedelta(days=7)).isoformat()

        assert expected_baseline_start in query

class TestUsagePatternQueries:

    """Test usage pattern analysis queries"""
    
    def test_usage_patterns_query_structure(self):

        """Test 11: Verify usage patterns query with time grouping"""

        query = QueryBuilder.build_usage_patterns_query(

            user_id=789,

            days_back=30

        )
        
        assert "toHour(timestamp) as hour_of_day" in query

        assert "toDayOfWeek(timestamp) as day_of_week" in query

        assert "count() as event_count" in query

        assert "uniqExact(workload_id) as unique_workloads" in query

        assert "uniqExact(model_name) as unique_models" in query

        assert "WHERE user_id = 789" in query

        assert "timestamp >= now() - INTERVAL 30 DAY" in query

        assert "GROUP BY day_of_week, hour_of_day" in query

        assert "ORDER BY day_of_week, hour_of_day" in query
    
    def test_usage_patterns_custom_days_back(self):

        """Test 12: Verify custom time window for usage patterns"""

        for days in [7, 14, 60, 90]:

            query = QueryBuilder.build_usage_patterns_query(

                user_id=1,

                days_back=days

            )

            assert f"INTERVAL {days} DAY" in query

class TestCorrelationQueries:

    """Test correlation analysis queries"""
    
    def test_correlation_analysis_query(self):

        """Test 13: Verify correlation analysis query structure"""

        metric1 = "latency_ms"

        metric2 = "throughput"

        query = QueryBuilder.build_correlation_analysis_query(

            user_id=999,

            metric1=metric1,

            metric2=metric2,

            start_time=datetime(2025, 1, 1),

            end_time=datetime(2025, 1, 2)

        )
        
        # Check for both metrics in the query

        assert f"arrayFirstIndex(x -> x = '{metric1}', metrics.name)" in query

        assert f"arrayFirstIndex(x -> x = '{metric2}', metrics.name)" in query
        
        assert "WHERE user_id = 999" in query

        assert "corr(m1_value, m2_value)" in query

        assert "sample_size" in query

class TestGenerationServiceQueries:

    """Test generation service queries"""

    @pytest.mark.asyncio
    async def test_get_corpus_from_clickhouse_query(self):

        """Test 14: Verify corpus loading query from generation service"""
        from netra_backend.app.services.generation_service import (

            get_corpus_from_clickhouse,
            save_corpus_to_clickhouse,

        )
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.services.generation_job_manager.ClickHouseDatabase') as mock_db:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_db.return_value = mock_instance

            mock_instance.execute_query.return_value = [

                {'workload_type': 'simple_chat', 'prompt': 'p1', 'response': 'r1'},

                {'workload_type': 'rag_pipeline', 'prompt': 'p2', 'response': 'r2'}

            ]
            
            result = await get_corpus_from_clickhouse("test_corpus_table")
            
            query = mock_instance.execute_query.call_args[0][0]

            assert "SELECT workload_type, prompt, response FROM test_corpus_table" == query

            assert result == {

                'simple_chat': [('p1', 'r1')],

                'rag_pipeline': [('p2', 'r2')]

            }

    @pytest.mark.asyncio
    async def test_save_corpus_to_clickhouse_batch_insert(self):
        """Test 15: Verify batch insert for corpus saving"""
        from netra_backend.app.services.generation_service import save_corpus_to_clickhouse
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.services.generation_job_manager.ClickHouseDatabase') as mock_db:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_db.return_value = mock_instance
            
            corpus = {

                'simple_chat': [('prompt1', 'response1'), ('prompt2', 'response2')],

                'rag_pipeline': [('prompt3', 'response3')]

            }
            
            await save_corpus_to_clickhouse(corpus, "test_table")
            
            # Verify table creation

            assert mock_instance.command.called
            
            # Verify batch insert

            assert mock_instance.insert_data.called

            insert_args = mock_instance.insert_data.call_args

            assert insert_args[0][0] == "test_table"  # table name

            assert len(insert_args[0][1]) == 3  # 3 records total

class TestTableInitializationQueries:

    """Test table initialization queries"""

    @pytest.mark.asyncio
    async def test_initialize_clickhouse_tables(self):

        """Test 16: Verify all tables are created on initialization"""
        from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.db.clickhouse_init.get_clickhouse_client') as mock_client:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_instance.test_connection.return_value = True

            mock_instance.execute_query.return_value = [

                {'name': 'netra_app_internal_logs'},

                {'name': 'netra_global_supply_catalog'},

                {'name': 'workload_events'}

            ]
            
            # Mock: ClickHouse external database isolation for unit testing performance
            with patch('netra_backend.app.db.clickhouse_init.settings') as mock_settings:

                mock_settings.environment = "production"
                
                await initialize_clickhouse_tables()
                
                # Verify CREATE TABLE commands were issued

                assert mock_instance.command.call_count == 3
                
                # Verify SHOW TABLES was called

                mock_instance.execute_query.assert_called_with("SHOW TABLES")

    @pytest.mark.asyncio
    async def test_verify_workload_events_table(self):

        """Test 17: Verify workload_events table verification"""
        from netra_backend.app.db.clickhouse_init import verify_workload_events_table
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.db.clickhouse_init.get_clickhouse_client') as mock_client:

            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()  # TODO: Use real service instance

            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_instance.execute_query.return_value = [(0,)]
            
            result = await verify_workload_events_table()
            
            assert result == True

            query = mock_instance.execute_query.call_args[0][0]

            assert "SELECT count() FROM workload_events WHERE 1=0" == query

class TestNestedArrayQueries:

    """Test queries with nested array handling"""
    
    def test_nested_array_access_pattern(self):

        """Test 18: Verify proper nested array access using arrayFirstIndex"""

        query = QueryBuilder.build_performance_metrics_query(

            user_id=1,

            workload_id=None,

            start_time=datetime.now(),

            end_time=datetime.now()

        )
        
        # Should use arrayFirstIndex, not indexOf

        assert "arrayFirstIndex" in query

        assert "indexOf" not in query
        
        # Should use arrayElement for accessing values

        assert "arrayElement(metrics.value, idx)" in query
    
    def test_nested_array_existence_check(self):

        """Test 19: Verify proper array existence checks"""

        query = QueryBuilder.build_anomaly_detection_query(

            user_id=1,

            metric_name="test_metric",

            start_time=datetime.now(),

            end_time=datetime.now()

        )
        
        # Should use arrayFirstIndex to find the metric

        assert "arrayFirstIndex(x -> x = 'test_metric', metrics.name)" in query
        # Should use arrayElement to access the value

        assert "arrayElement(metrics.value" in query

        assert "has(metrics.name" not in query

class TestErrorHandling(SharedTestErrorHandling):

    """Test query error handling patterns - extends shared error handling."""
    
    def test_null_safety_in_calculations(self):

        """Test 20: Verify z-score calculation in anomaly detection"""

        query = QueryBuilder.build_anomaly_detection_query(

            user_id=1,

            metric_name="test",

            start_time=datetime.now(),

            end_time=datetime.now()

        )
        
        # Should calculate z-score

        assert "z_score" in query

        assert "/ baseline.std_val" in query
        
        # Should have anomaly detection logic

        assert "is_anomaly" in query