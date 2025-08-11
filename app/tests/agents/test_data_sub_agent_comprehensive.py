"""
Comprehensive tests for DataSubAgent achieving 100% coverage
Tests all methods including QueryBuilder, AnalysisEngine, and DataSubAgent
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, PropertyMock
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Import the classes to test
from app.agents.data_sub_agent import (
    DataSubAgent, 
    QueryBuilder, 
    AnalysisEngine
)
from app.agents.state import DeepAgentState


class TestQueryBuilder:
    """Test QueryBuilder class methods"""
    
    def test_build_performance_metrics_query_minute_aggregation(self):
        """Test performance metrics query with minute aggregation"""
        query = QueryBuilder.build_performance_metrics_query(
            user_id=1,
            workload_id="test_workload",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 13, 0, 0),
            aggregation_level="minute"
        )
        assert "toStartOfMinute" in query
        assert "workload_id = 'test_workload'" in query
        assert "user_id = 1" in query
        
    def test_build_performance_metrics_query_hour_aggregation(self):
        """Test performance metrics query with hour aggregation"""
        query = QueryBuilder.build_performance_metrics_query(
            user_id=2,
            workload_id=None,  # Test without workload filter
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 1, 2, 0, 0, 0),
            aggregation_level="hour"
        )
        assert "toStartOfHour" in query
        # When workload_id == None, the filter string is empty but workload_id column still appears in SELECT
        assert "AND workload_id" not in query  # Check no filter is applied
        assert "user_id = 2" in query
        
    def test_build_performance_metrics_query_day_aggregation(self):
        """Test performance metrics query with day aggregation"""
        query = QueryBuilder.build_performance_metrics_query(
            user_id=3,
            workload_id="daily_workload",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            aggregation_level="day"
        )
        assert "toStartOfDay" in query
        assert "workload_id = 'daily_workload'" in query
        
    def test_build_performance_metrics_query_second_aggregation(self):
        """Test performance metrics query with second aggregation"""
        query = QueryBuilder.build_performance_metrics_query(
            user_id=4,
            workload_id="second_workload",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 1, 0),
            aggregation_level="second"
        )
        assert "toStartOfSecond" in query
        
    def test_build_performance_metrics_query_invalid_aggregation(self):
        """Test performance metrics query with invalid aggregation defaults to minute"""
        query = QueryBuilder.build_performance_metrics_query(
            user_id=5,
            workload_id="test",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            aggregation_level="invalid"
        )
        assert "toStartOfMinute" in query  # Should default to minute
        
    def test_build_anomaly_detection_query(self):
        """Test anomaly detection query builder"""
        query = QueryBuilder.build_anomaly_detection_query(
            user_id=1,
            metric_name="latency_ms",
            start_time=datetime(2024, 1, 8),
            end_time=datetime(2024, 1, 9),
            z_score_threshold=2.5
        )
        assert "latency_ms" in query
        assert "z_score" in query
        assert "2.5" in query
        assert "user_id = 1" in query
        
    def test_build_correlation_analysis_query(self):
        """Test correlation analysis query builder"""
        query = QueryBuilder.build_correlation_analysis_query(
            user_id=2,
            metric1="latency_ms",
            metric2="throughput",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )
        assert "latency_ms" in query
        assert "throughput" in query
        assert "corr(" in query
        assert "user_id = 2" in query
        
    def test_build_usage_patterns_query(self):
        """Test usage patterns query builder"""
        query = QueryBuilder.build_usage_patterns_query(
            user_id=3,
            days_back=30
        )
        assert "toDayOfWeek" in query
        assert "toHour" in query
        assert "user_id = 3" in query
        assert "INTERVAL 30 DAY" in query
        
    def test_build_usage_patterns_query_custom_days(self):
        """Test usage patterns query with custom days"""
        query = QueryBuilder.build_usage_patterns_query(
            user_id=4,
            days_back=7
        )
        assert "INTERVAL 7 DAY" in query


class TestAnalysisEngine:
    """Test AnalysisEngine class methods"""
    
    def test_calculate_statistics_empty(self):
        """Test statistics calculation with empty data"""
        stats = AnalysisEngine.calculate_statistics([])
        assert stats["count"] == 0
        assert stats["mean"] == 0
        assert stats["median"] == 0
        assert stats["std_dev"] == 0
        
    def test_calculate_statistics_single_value(self):
        """Test statistics calculation with single value"""
        stats = AnalysisEngine.calculate_statistics([5.0])
        assert stats["count"] == 1
        assert stats["mean"] == 5.0
        assert stats["median"] == 5.0
        assert stats["min"] == 5.0
        assert stats["max"] == 5.0
        
    def test_calculate_statistics_multiple_values(self):
        """Test statistics calculation with multiple values"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        stats = AnalysisEngine.calculate_statistics(values)
        assert stats["count"] == 10
        assert stats["mean"] == 5.5
        assert stats["median"] == 5.5
        assert stats["min"] == 1.0
        assert stats["max"] == 10.0
        assert stats["p25"] == pytest.approx(3.25, rel=0.01)
        assert stats["p75"] == pytest.approx(7.75, rel=0.01)
        assert stats["p95"] == pytest.approx(9.55, rel=0.01)
        assert stats["p99"] == pytest.approx(9.91, rel=0.01)
        
    def test_detect_trend_insufficient_data(self):
        """Test trend detection with insufficient data"""
        values = [1.0, 2.0]
        timestamps = [datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 1)]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == False
        assert trend["reason"] == "insufficient_data"
        
    def test_detect_trend_no_time_variation(self):
        """Test trend detection with no time variation"""
        values = [1.0, 2.0, 3.0]
        timestamps = [datetime(2024, 1, 1, 12, 0)] * 3  # Same timestamp
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == False
        assert trend["reason"] == "no_time_variation"
        
    def test_detect_trend_increasing(self):
        """Test trend detection with increasing values"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 12, 15),
            datetime(2024, 1, 1, 12, 30),
            datetime(2024, 1, 1, 12, 45),
            datetime(2024, 1, 1, 13, 0)
        ]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == True
        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0
        
    def test_detect_trend_decreasing(self):
        """Test trend detection with decreasing values"""
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 12, 15),
            datetime(2024, 1, 1, 12, 30),
            datetime(2024, 1, 1, 12, 45),
            datetime(2024, 1, 1, 13, 0)
        ]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == True
        assert trend["direction"] == "decreasing"
        assert trend["slope"] < 0
        
    def test_detect_trend_weak(self):
        """Test trend detection with weak correlation"""
        values = [1.0, 2.0, 1.5, 2.5, 2.0]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 12, 15),
            datetime(2024, 1, 1, 12, 30),
            datetime(2024, 1, 1, 12, 45),
            datetime(2024, 1, 1, 13, 0)
        ]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        if trend["has_trend"]:
            assert trend["strength"] in ["weak", "moderate"]
            
    def test_detect_seasonality_insufficient_data(self):
        """Test seasonality detection with insufficient data"""
        values = [1.0] * 10  # Less than 24 points
        timestamps = [datetime(2024, 1, 1, i, 0) for i in range(10)]
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        assert seasonality["has_seasonality"] == False
        assert seasonality["reason"] == "insufficient_data"
        
    def test_detect_seasonality_insufficient_hourly_coverage(self):
        """Test seasonality detection with insufficient hourly coverage"""
        # Create 24 data points but only in 6 different hours
        values = []
        timestamps = []
        for hour in range(6):
            for _ in range(4):
                values.append(float(hour))
                timestamps.append(datetime(2024, 1, 1, hour, 0))
        
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        assert seasonality["has_seasonality"] == False
        assert seasonality["reason"] == "insufficient_hourly_coverage"
        
    def test_detect_seasonality_with_pattern(self):
        """Test seasonality detection with daily pattern"""
        values = []
        timestamps = []
        # Create data with clear hourly pattern over 2 days
        for day in range(2):
            for hour in range(24):
                # Peak at noon, low at midnight
                value = 100 + 50 * np.sin((hour - 6) * np.pi / 12)
                values.append(value)
                timestamps.append(datetime(2024, 1, day + 1, hour, 0))
                
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        assert seasonality["has_seasonality"] == True
        assert "daily_pattern" in seasonality
        assert "peak_hour" in seasonality["daily_pattern"]
        assert "low_hour" in seasonality["daily_pattern"]
        
    def test_detect_seasonality_no_pattern(self):
        """Test seasonality detection with no pattern"""
        values = []
        timestamps = []
        # Create random data
        np.random.seed(42)
        for day in range(2):
            for hour in range(24):
                values.append(100.0 + np.random.randn())  # Small variation
                timestamps.append(datetime(2024, 1, day + 1, hour, 0))
                
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        # With small random variation, should not detect seasonality
        assert seasonality["has_seasonality"] == False
        
    def test_identify_outliers_insufficient_data(self):
        """Test outlier identification with insufficient data"""
        outliers = AnalysisEngine.identify_outliers([1.0, 2.0, 3.0])
        assert outliers == []
        
    def test_identify_outliers_iqr_method(self):
        """Test outlier identification using IQR method"""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]  # 100 is an outlier
        outliers = AnalysisEngine.identify_outliers(values, method="iqr")
        assert 9 in outliers  # Index of value 100
        
    def test_identify_outliers_zscore_method(self):
        """Test outlier identification using Z-score method"""
        values = [10, 11, 12, 13, 14, 15, 16, 17, 18, 50]  # 50 is an outlier
        outliers = AnalysisEngine.identify_outliers(values, method="zscore")
        assert 9 in outliers  # Index of value 50
        
    def test_identify_outliers_zscore_no_variance(self):
        """Test outlier identification with no variance"""
        values = [5.0] * 10  # All same values
        outliers = AnalysisEngine.identify_outliers(values, method="zscore")
        assert outliers == []
        
    def test_identify_outliers_invalid_method(self):
        """Test outlier identification with invalid method"""
        values = [1, 2, 3, 4, 5, 100]
        outliers = AnalysisEngine.identify_outliers(values, method="invalid")
        assert outliers == []  # Should return empty list for invalid method


class TestDataSubAgent:
    """Test DataSubAgent class methods"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for DataSubAgent"""
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        return mock_llm_manager, mock_tool_dispatcher
    
    @pytest.fixture
    def agent(self, mock_dependencies):
        """Create DataSubAgent instance with mocked dependencies"""
        mock_llm_manager, mock_tool_dispatcher = mock_dependencies
        with patch('app.agents.data_sub_agent.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        return agent
    
    def test_initialization(self, mock_dependencies):
        """Test DataSubAgent initialization"""
        mock_llm_manager, mock_tool_dispatcher = mock_dependencies
        
        with patch('app.agents.data_sub_agent.RedisManager') as mock_redis:
            mock_redis.return_value = Mock()
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        assert agent.name == "DataSubAgent"
        assert agent.description == "Advanced data gathering and analysis agent with ClickHouse integration."
        assert agent.tool_dispatcher == mock_tool_dispatcher
        assert agent.query_builder != None
        assert agent.analysis_engine != None
        assert agent.cache_ttl == 300
        
    def test_initialization_redis_failure(self, mock_dependencies):
        """Test DataSubAgent initialization when Redis fails"""
        mock_llm_manager, mock_tool_dispatcher = mock_dependencies
        
        with patch('app.agents.data_sub_agent.RedisManager') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        assert agent.redis_manager == None
        
    @pytest.mark.asyncio
    async def test_get_cached_schema_success(self, agent):
        """Test getting cached schema information"""
        with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.execute_query = AsyncMock(return_value=[
                ("column1", "String"),
                ("column2", "Int32")
            ])
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Clear the cache first
            agent._get_cached_schema.cache_clear()
            
            result = await agent._get_cached_schema("test_table")
            
        assert result != None
        assert result["table"] == "test_table"
        assert len(result["columns"]) == 2
        assert result["columns"][0]["name"] == "column1"
        assert result["columns"][0]["type"] == "String"
        
    @pytest.mark.asyncio
    async def test_get_cached_schema_failure(self, agent):
        """Test getting cached schema with error"""
        with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.execute_query = AsyncMock(side_effect=Exception("Query failed"))
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Clear the cache first
            agent._get_cached_schema.cache_clear()
            
            result = await agent._get_cached_schema("test_table")
            
        assert result == None
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_with_cache_hit(self, agent):
        """Test fetching ClickHouse data with cache hit"""
        agent.redis_manager = Mock()
        agent.redis_manager.get = AsyncMock(return_value='[{"col1": "value1"}]')
        
        result = await agent._fetch_clickhouse_data("SELECT * FROM test", "cache_key")
        
        assert result == [{"col1": "value1"}]
        agent.redis_manager.get.assert_called_once_with("cache_key")
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_cache_miss(self, agent):
        """Test fetching ClickHouse data with cache miss"""
        agent.redis_manager = Mock()
        agent.redis_manager.get = AsyncMock(return_value=None)
        agent.redis_manager.set = AsyncMock()
        
        with patch('app.agents.data_sub_agent.create_workload_events_table_if_missing', new_callable=AsyncMock):
            with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
                mock_result = Mock()
                mock_result._fields = ["col1", "col2"]
                
                mock_client_instance = AsyncMock()
                mock_client_instance.execute_query = AsyncMock(return_value=[
                    ("value1", "value2"),
                    ("value3", "value4")
                ])
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                result = await agent._fetch_clickhouse_data("SELECT * FROM test", "cache_key")
                
        assert len(result) == 2
        assert result[0] == {0: "value1", 1: "value2"}
        agent.redis_manager.set.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_no_cache(self, agent):
        """Test fetching ClickHouse data without caching"""
        agent.redis_manager = None
        
        with patch('app.agents.data_sub_agent.create_workload_events_table_if_missing', new_callable=AsyncMock):
            with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.execute_query = AsyncMock(return_value=[])
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                result = await agent._fetch_clickhouse_data("SELECT * FROM test")
                
        assert result == []
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_error(self, agent):
        """Test fetching ClickHouse data with error"""
        with patch('app.agents.data_sub_agent.create_workload_events_table_if_missing', new_callable=AsyncMock):
            with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.execute_query = AsyncMock(side_effect=Exception("Query failed"))
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                result = await agent._fetch_clickhouse_data("SELECT * FROM test")
                
        assert result == None
        
    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_no_data(self, agent):
        """Test analyzing performance metrics with no data"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            
            result = await agent._analyze_performance_metrics(
                user_id=1,
                workload_id="test",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert result["status"] == "no_data"
        assert "message" in result
        
    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_minute_aggregation(self, agent):
        """Test analyzing performance metrics with minute aggregation"""
        mock_data = [
            {
                'time_bucket': '2024-01-01T12:00:00',
                'event_count': 100,
                'latency_p50': 50.0,
                'latency_p95': 95.0,
                'latency_p99': 99.0,
                'avg_throughput': 1000.0,
                'peak_throughput': 2000.0,
                'error_rate': 0.5,
                'total_cost': 10.0,
                'unique_workloads': 5
            }
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            # Time range less than 1 hour for minute aggregation
            result = await agent._analyze_performance_metrics(
                user_id=1,
                workload_id="test",
                time_range=(datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 30))
            )
            
        assert "time_range" in result
        assert result["time_range"]["aggregation_level"] == "minute"
        assert "summary" in result
        assert result["summary"]["total_events"] == 100
        assert "latency" in result
        assert "throughput" in result
        
    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_hour_aggregation(self, agent):
        """Test analyzing performance metrics with hour aggregation"""
        mock_data = [
            {'time_bucket': f'2024-01-01T{i:02d}:00:00', 'event_count': 100, 
             'latency_p50': 50.0, 'avg_throughput': 1000.0, 'error_rate': 0.5, 
             'total_cost': 10.0, 'unique_workloads': 5}
            for i in range(12)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            # Time range of 12 hours for hour aggregation
            result = await agent._analyze_performance_metrics(
                user_id=1,
                workload_id="test",
                time_range=(datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 12, 0))
            )
            
        assert result["time_range"]["aggregation_level"] == "hour"
        assert "trends" in result  # Should have trend analysis with 12 data points
        
    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_day_aggregation(self, agent):
        """Test analyzing performance metrics with day aggregation"""
        mock_data = [
            {'time_bucket': f'2024-01-{i:02d}T00:00:00', 'event_count': 100,
             'latency_p50': 50.0, 'avg_throughput': 1000.0, 'error_rate': 0.5,
             'total_cost': 10.0, 'unique_workloads': 5}
            for i in range(1, 8)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            # Time range of 7 days for day aggregation
            result = await agent._analyze_performance_metrics(
                user_id=1,
                workload_id="test",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 8))
            )
            
        assert result["time_range"]["aggregation_level"] == "day"
        
    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_with_seasonality(self, agent):
        """Test analyzing performance metrics with seasonality detection"""
        # Create 24+ data points for seasonality detection
        mock_data = [
            {'time_bucket': f'2024-01-01T{i:02d}:00:00', 'event_count': 100,
             'latency_p50': 50.0 + i, 'avg_throughput': 1000.0, 'error_rate': 0.5,
             'total_cost': 10.0, 'unique_workloads': 5}
            for i in range(24)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_performance_metrics(
                user_id=1,
                workload_id="test",
                time_range=(datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0))
            )
            
        assert "seasonality" in result
        
    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_with_outliers(self, agent):
        """Test analyzing performance metrics with outlier detection"""
        mock_data = [
            {'time_bucket': f'2024-01-01T12:{i:02d}:00', 'event_count': 100,
             'latency_p50': 50.0 if i < 9 else 500.0,  # Last value is outlier
             'avg_throughput': 1000.0, 'error_rate': 0.5,
             'total_cost': 10.0, 'unique_workloads': 5}
            for i in range(10)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_performance_metrics(
                user_id=1,
                workload_id="test",
                time_range=(datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 10))
            )
            
        assert "outliers" in result
        assert "latency_outliers" in result["outliers"]
        
    @pytest.mark.asyncio
    async def test_detect_anomalies_no_data(self, agent):
        """Test anomaly detection with no data"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            
            result = await agent._detect_anomalies(
                user_id=1,
                metric_name="latency_ms",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2)),
                z_score_threshold=2.0
            )
            
        assert result["status"] == "no_anomalies"
        assert result["threshold"] == 2.0
        
    @pytest.mark.asyncio
    async def test_detect_anomalies_found(self, agent):
        """Test anomaly detection with anomalies found"""
        mock_data = [
            {'timestamp': f'2024-01-01T12:{i:02d}:00', 'metric_value': 100.0 * (i + 1),
             'z_score': 2.5 + i * 0.1, 'is_anomaly': True}
            for i in range(5)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._detect_anomalies(
                user_id=1,
                metric_name="latency_ms",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2)),
                z_score_threshold=2.0
            )
            
        assert result["status"] == "anomalies_found"
        assert result["anomaly_count"] == 5
        assert len(result["anomalies"]) == 5
        assert result["anomalies"][0]["severity"] == "medium"
        assert result["anomalies"][-1]["severity"] == "high"  # z_score > 3
        
    @pytest.mark.asyncio
    async def test_analyze_correlations_insufficient_metrics(self, agent):
        """Test correlation analysis with insufficient metrics"""
        result = await agent._analyze_correlations(
            user_id=1,
            metrics=["latency_ms"],  # Only one metric
            time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
        )
        
        assert "error" in result
        assert "2 metrics required" in result["error"]
        
    @pytest.mark.asyncio
    async def test_analyze_correlations_success(self, agent):
        """Test successful correlation analysis"""
        mock_data = [{
            'correlation_coefficient': 0.85,
            'sample_size': 100,
            'metric1_avg': 50.0,
            'metric1_std': 10.0,
            'metric2_avg': 1000.0,
            'metric2_std': 200.0
        }]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_correlations(
                user_id=1,
                metrics=["latency_ms", "throughput"],
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert "correlations" in result
        assert "latency_ms_vs_throughput" in result["correlations"]
        correlation = result["correlations"]["latency_ms_vs_throughput"]
        assert correlation["coefficient"] == 0.85
        assert correlation["strength"] == "strong"
        assert correlation["direction"] == "positive"
        
    @pytest.mark.asyncio
    async def test_analyze_correlations_weak(self, agent):
        """Test correlation analysis with weak correlation"""
        mock_data = [{
            'correlation_coefficient': 0.25,
            'sample_size': 100,
            'metric1_avg': 50.0,
            'metric1_std': 10.0,
            'metric2_avg': 1000.0,
            'metric2_std': 200.0
        }]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_correlations(
                user_id=1,
                metrics=["latency_ms", "throughput"],
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        correlation = result["correlations"]["latency_ms_vs_throughput"]
        assert correlation["strength"] == "weak"
        
    @pytest.mark.asyncio
    async def test_analyze_correlations_multiple_pairs(self, agent):
        """Test correlation analysis with multiple metric pairs"""
        mock_data = [{
            'correlation_coefficient': -0.6,
            'sample_size': 100,
            'metric1_avg': 50.0,
            'metric1_std': 10.0,
            'metric2_avg': 1000.0,
            'metric2_std': 200.0
        }]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_correlations(
                user_id=1,
                metrics=["latency_ms", "throughput", "error_rate"],
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert len(result["correlations"]) == 3  # 3 pairs for 3 metrics
        assert "strongest_correlation" in result
        
    @pytest.mark.asyncio
    async def test_analyze_usage_patterns_no_data(self, agent):
        """Test usage pattern analysis with no data"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            
            result = await agent._analyze_usage_patterns(user_id=1, days_back=30)
            
        assert result["status"] == "no_data"
        
    @pytest.mark.asyncio
    async def test_analyze_usage_patterns_success(self, agent):
        """Test successful usage pattern analysis"""
        mock_data = [
            {
                'day_of_week': dow,
                'hour_of_day': hour,
                'event_count': 100,
                'unique_workloads': 5,
                'unique_models': 3,
                'total_cost': 10.0
            }
            for dow in range(1, 8)
            for hour in range(24)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_usage_patterns(user_id=1, days_back=30)
            
        assert "summary" in result
        assert "daily_patterns" in result
        assert "hourly_distribution" in result
        assert result["period"] == "Last 30 days"
        assert "Monday" in result["daily_patterns"]
        
    @pytest.mark.asyncio
    async def test_send_update_with_ws_manager(self, agent):
        """Test sending WebSocket update with manager"""
        agent.ws_manager = Mock()
        agent.ws_manager.send_agent_update = AsyncMock()
        
        await agent._send_update("run_123", {"status": "test"})
        
        agent.ws_manager.send_agent_update.assert_called_once_with(
            "run_123", "DataSubAgent", {"status": "test"}
        )
        
    @pytest.mark.asyncio
    async def test_send_update_without_ws_manager(self, agent):
        """Test sending WebSocket update without manager"""
        agent.ws_manager = None
        
        # Should not raise an error
        await agent._send_update("run_123", {"status": "test"})
        
    @pytest.mark.asyncio
    async def test_send_update_with_error(self, agent):
        """Test sending WebSocket update with error"""
        agent.ws_manager = Mock()
        agent.ws_manager.send_agent_update = AsyncMock(side_effect=Exception("WebSocket error"))
        
        # Should not raise an error
        await agent._send_update("run_123", {"status": "test"})
        
    @pytest.mark.asyncio
    async def test_execute_optimize_intent(self, agent):
        """Test execute with optimize intent"""
        state = DeepAgentState()
        state.user_request = "Optimize my workload"
        state.triage_result = {
            "intent": {"primary": "optimize"},
            "key_parameters": {
                "user_id": 1,
                "workload_id": "test_workload",
                "metrics": ["latency_ms", "error_rate"],
                "time_range": "last_hour"
            }
        }
        
        mock_perf_data = {"performance": "data"}
        mock_anomaly_data = {"anomaly_count": 0}
        
        with patch.object(agent, '_analyze_performance_metrics', new_callable=AsyncMock) as mock_perf:
            with patch.object(agent, '_detect_anomalies', new_callable=AsyncMock) as mock_anomaly:
                mock_perf.return_value = mock_perf_data
                mock_anomaly.return_value = mock_anomaly_data
                
                await agent.execute(state, "run_123", stream_updates=False)
                
        assert state.data_result != None
        assert state.data_result["analysis_type"] == "optimize"
        assert "performance" in state.data_result["results"]
        
    @pytest.mark.asyncio
    async def test_execute_analyze_intent(self, agent):
        """Test execute with analyze intent"""
        state = DeepAgentState()
        state.user_request = "Analyze my data"
        state.triage_result = {
            "intent": {"primary": "analyze"},
            "key_parameters": {
                "user_id": 2,
                "metrics": ["latency_ms", "throughput"],
                "time_range": "last_24_hours"
            }
        }
        
        mock_correlation_data = {"correlations": {}}
        mock_usage_data = {"usage_patterns": {}}
        
        with patch.object(agent, '_analyze_correlations', new_callable=AsyncMock) as mock_corr:
            with patch.object(agent, '_analyze_usage_patterns', new_callable=AsyncMock) as mock_usage:
                mock_corr.return_value = mock_correlation_data
                mock_usage.return_value = mock_usage_data
                
                await agent.execute(state, "run_123", stream_updates=True)
                
        assert state.data_result["analysis_type"] == "analyze"
        assert "correlations" in state.data_result["results"]
        assert "usage_patterns" in state.data_result["results"]
        
    @pytest.mark.asyncio
    async def test_execute_monitor_intent(self, agent):
        """Test execute with monitor intent"""
        state = DeepAgentState()
        state.user_request = "Monitor my metrics"
        state.triage_result = {
            "intent": {"primary": "monitor"},
            "key_parameters": {
                "user_id": 3,
                "metrics": ["latency_ms", "throughput", "error_rate"],
                "time_range": "last_week"
            }
        }
        
        mock_anomaly_data = {"anomaly_count": 5}
        
        with patch.object(agent, '_detect_anomalies', new_callable=AsyncMock) as mock_anomaly:
            mock_anomaly.return_value = mock_anomaly_data
            
            await agent.execute(state, "run_123", stream_updates=False)
            
        assert state.data_result["analysis_type"] == "monitor"
        assert "latency_ms_monitoring" in state.data_result["results"]
        assert "throughput_monitoring" in state.data_result["results"]
        assert "error_rate_monitoring" in state.data_result["results"]
        
    @pytest.mark.asyncio
    async def test_execute_general_intent(self, agent):
        """Test execute with general/unknown intent"""
        state = DeepAgentState()
        state.user_request = "Help me with my data"
        state.triage_result = {
            "intent": {"primary": "general"},
            "key_parameters": {
                "user_id": 4,
                "time_range": "last_month"
            }
        }
        
        mock_perf_data = {"performance": "data"}
        mock_usage_data = {"usage_patterns": {}}
        
        with patch.object(agent, '_analyze_performance_metrics', new_callable=AsyncMock) as mock_perf:
            with patch.object(agent, '_analyze_usage_patterns', new_callable=AsyncMock) as mock_usage:
                mock_perf.return_value = mock_perf_data
                mock_usage.return_value = mock_usage_data
                
                await agent.execute(state, "run_123", stream_updates=False)
                
        assert state.data_result["analysis_type"] == "general"
        assert "performance" in state.data_result["results"]
        assert "usage_patterns" in state.data_result["results"]
        
    @pytest.mark.asyncio
    async def test_execute_with_exception_fallback(self, agent):
        """Test execute with exception triggering fallback"""
        state = DeepAgentState()
        state.user_request = "Analyze my data"
        state.triage_result = {"intent": {"primary": "analyze"}}
        
        # Mock the LLM manager for fallback
        agent.llm_manager.ask_llm = AsyncMock(return_value='{"fallback": true}')
        
        with patch.object(agent, '_analyze_performance_metrics', new_callable=AsyncMock) as mock_perf:
            mock_perf.side_effect = Exception("Database connection failed")
            
            await agent.execute(state, "run_123", stream_updates=True)
            
        assert state.data_result != None
        assert state.data_result.get("fallback") == True
        
    @pytest.mark.asyncio
    async def test_execute_with_invalid_llm_response(self, agent):
        """Test execute with invalid LLM response in fallback"""
        state = DeepAgentState()
        state.user_request = "Analyze my data"
        state.triage_result = {"intent": {"primary": "analyze"}}
        
        # Mock the LLM manager to return invalid JSON
        agent.llm_manager.ask_llm = AsyncMock(return_value='Invalid JSON response')
        
        with patch.object(agent, '_analyze_performance_metrics', new_callable=AsyncMock) as mock_perf:
            mock_perf.side_effect = Exception("Database connection failed")
            
            await agent.execute(state, "run_123", stream_updates=False)
            
        assert state.data_result != None
        assert state.data_result["collection_status"] == "fallback"
        assert "error" in state.data_result
        
    @pytest.mark.asyncio
    async def test_process_data(self, agent):
        """Test process_data compatibility method"""
        data = {"test": "data", "value": 123}
        result = await agent.process_data(data)
        
        assert result["processed"] == True
        assert result["data"] == data
        
    @pytest.mark.asyncio
    async def test_process_data_empty(self, agent):
        """Test process_data with empty data"""
        with pytest.raises(ValueError, match="No data provided"):
            await agent.process_data({})
            
    @pytest.mark.asyncio
    async def test_process_data_none(self, agent):
        """Test process_data with None"""
        with pytest.raises(ValueError, match="No data provided"):
            await agent.process_data(None)
            
    def test_validate_data_valid(self, agent):
        """Test _validate_data with valid data"""
        data = {"input": "test", "type": "text"}
        assert agent._validate_data(data) == True
        
    def test_validate_data_missing_input(self, agent):
        """Test _validate_data with missing input field"""
        data = {"type": "text"}
        assert agent._validate_data(data) == False
        
    def test_validate_data_missing_type(self, agent):
        """Test _validate_data with missing type field"""
        data = {"input": "test"}
        assert agent._validate_data(data) == False
        
    def test_validate_data_empty(self, agent):
        """Test _validate_data with empty data"""
        assert agent._validate_data({}) == False
        
    def test_validate_data_none(self, agent):
        """Test _validate_data with None"""
        assert agent._validate_data(None) == False
        
    @pytest.mark.asyncio
    async def test_transform_data_json(self, agent):
        """Test _transform_data with JSON type"""
        data = {"type": "json", "content": '{"key": "value"}'}
        result = await agent._transform_data(data)
        
        assert result["transformed"] == True
        assert result["type"] == "json"
        assert result["parsed"] == {"key": "value"}
        
    @pytest.mark.asyncio
    async def test_transform_data_invalid_json(self, agent):
        """Test _transform_data with invalid JSON"""
        data = {"type": "json", "content": 'invalid json'}
        result = await agent._transform_data(data)
        
        assert result["transformed"] == True
        assert result["type"] == "json"
        assert "parsed" not in result
        
    @pytest.mark.asyncio
    async def test_transform_data_non_json(self, agent):
        """Test _transform_data with non-JSON type"""
        data = {"type": "text", "content": "plain text"}
        result = await agent._transform_data(data)
        
        assert result["transformed"] == True
        assert result["type"] == "text"
        assert "parsed" not in result
        
    @pytest.mark.asyncio
    async def test_enrich_data_basic(self, agent):
        """Test enrich_data basic functionality"""
        data = {"content": "test", "source": "api"}
        result = await agent.enrich_data(data)
        
        assert "metadata" in result
        assert "timestamp" in result["metadata"]
        assert result["metadata"]["source"] == "api"
        
    @pytest.mark.asyncio
    async def test_enrich_data_external(self, agent):
        """Test enrich_data with external flag"""
        data = {"content": "test"}
        result = await agent.enrich_data(data, external=True)
        
        assert "additional" in result
        assert result["additional"] == "data"
        
    @pytest.mark.asyncio
    async def test_enrich_data_no_source(self, agent):
        """Test enrich_data without source field"""
        data = {"content": "test"}
        result = await agent.enrich_data(data)
        
        assert result["metadata"]["source"] == "unknown"
        
    @pytest.mark.asyncio
    async def test_process_batch(self, agent):
        """Test process_batch method"""
        batch = [
            {"id": 1, "data": "item1"},
            {"id": 2, "data": "item2"},
            {"id": 3, "data": "item3"}
        ]
        
        results = await agent.process_batch(batch)
        
        assert len(results) == 3
        for result in results:
            assert result["processed"] == True
            
    @pytest.mark.asyncio
    async def test_process_batch_empty(self, agent):
        """Test process_batch with empty batch"""
        results = await agent.process_batch([])
        assert results == []
        
    @pytest.mark.asyncio
    async def test_apply_operation(self, agent):
        """Test _apply_operation method"""
        data = {"content": "test"}
        operation = {"operation": "normalize"}
        
        result = await agent._apply_operation(data, operation)
        
        assert result["processed"] == True
        assert result["operation"] == "normalize"
        assert result["data"] == data
        
    @pytest.mark.asyncio
    async def test_transform_with_pipeline(self, agent):
        """Test _transform_with_pipeline method"""
        data = {"content": "test"}
        pipeline = [
            {"operation": "normalize"},
            {"operation": "validate"},
            {"operation": "enrich"}
        ]
        
        result = await agent._transform_with_pipeline(data, pipeline)
        
        assert result["processed"] == True
        assert result["operation"] == "enrich"  # Last operation
        
    @pytest.mark.asyncio
    async def test_transform_with_pipeline_empty(self, agent):
        """Test _transform_with_pipeline with empty pipeline"""
        data = {"content": "test"}
        result = await agent._transform_with_pipeline(data, [])
        
        assert result == data  # Should return unchanged
        
    @pytest.mark.asyncio
    async def test_process_internal(self, agent):
        """Test _process_internal method"""
        data = {"content": "test"}
        result = await agent._process_internal(data)
        
        assert result["success"] == True
        assert result["data"] == data
        
    @pytest.mark.asyncio
    async def test_process_with_retry_success_first_try(self, agent):
        """Test process_with_retry succeeds on first try"""
        data = {"content": "test"}
        result = await agent.process_with_retry(data)
        
        assert result["success"] == True
        
    @pytest.mark.asyncio
    async def test_process_with_retry_success_after_failures(self, agent):
        """Test process_with_retry succeeds after failures"""
        agent.config = {'max_retries': 3}
        data = {"content": "test"}
        
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                {"success": True, "data": data}
            ]
            
            result = await agent.process_with_retry(data)
            
        assert result["success"] == True
        assert mock_process.call_count == 3
        
    @pytest.mark.asyncio
    async def test_process_with_retry_all_failures(self, agent):
        """Test process_with_retry fails after max retries"""
        agent.config = {'max_retries': 2}
        data = {"content": "test"}
        
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Persistent error")
            
            with pytest.raises(Exception, match="Persistent error"):
                await agent.process_with_retry(data)
                
        assert mock_process.call_count == 2
        
    @pytest.mark.asyncio
    async def test_process_batch_safe_mixed_results(self, agent):
        """Test process_batch_safe with mixed valid/invalid items"""
        batch = [
            {"id": 1, "valid": True, "data": "item1"},
            {"id": 2, "valid": False, "data": "item2"},
            {"id": 3, "valid": True, "data": "item3"}
        ]
        
        results = await agent.process_batch_safe(batch)
        
        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_process_batch_safe_with_exception(self, agent):
        """Test process_batch_safe handling exceptions"""
        batch = [{"id": 1, "data": "item1"}]
        
        with patch.object(agent, 'process_data', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            results = await agent.process_batch_safe(batch)
            
        assert results[0]["status"] == "error"
        assert "Processing failed" in results[0]["message"]
        
    @pytest.mark.asyncio
    async def test_process_with_cache_hit(self, agent):
        """Test process_with_cache with cache hit"""
        data = {"id": "test_cache"}
        
        # First call populates cache
        result1 = await agent.process_with_cache(data)
        
        # Second call should use cache
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            result2 = await agent.process_with_cache(data)
            
        assert result1 == result2
        mock_process.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_process_with_cache_different_keys(self, agent):
        """Test process_with_cache with different cache keys"""
        data1 = {"id": "cache1"}
        data2 = {"id": "cache2"}
        
        result1 = await agent.process_with_cache(data1)
        result2 = await agent.process_with_cache(data2)
        
        # Different IDs should have different cache entries
        assert result1["data"]["id"] == "cache1"
        assert result2["data"]["id"] == "cache2"
        
    @pytest.mark.asyncio
    async def test_process_and_stream(self, agent):
        """Test process_and_stream method"""
        data = {"content": "stream test"}
        mock_ws = Mock()
        mock_ws.send = AsyncMock()
        
        await agent.process_and_stream(data, mock_ws)
        
        mock_ws.send.assert_called_once()
        sent_data = mock_ws.send.call_args[0][0]
        parsed = json.loads(sent_data)
        assert parsed["processed"] == True
        
    @pytest.mark.asyncio
    async def test_process_and_persist(self, agent):
        """Test process_and_persist method"""
        data = {"content": "persist test"}
        
        result = await agent.process_and_persist(data)
        
        assert result["processed"] == True
        assert result["persisted"] == True
        assert result["id"] == "saved_123"
        
    @pytest.mark.asyncio
    async def test_handle_supervisor_request_process_data(self, agent):
        """Test handle_supervisor_request with process_data action"""
        callback = AsyncMock()
        request = {
            "action": "process_data",
            "data": {"content": "supervisor data"},
            "callback": callback
        }
        
        result = await agent.handle_supervisor_request(request)
        
        assert result["status"] == "completed"
        callback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_supervisor_request_no_callback(self, agent):
        """Test handle_supervisor_request without callback"""
        request = {
            "action": "unknown_action",
            "data": {"content": "test"}
        }
        
        result = await agent.handle_supervisor_request(request)
        
        assert result["status"] == "completed"
        
    @pytest.mark.asyncio
    async def test_process_concurrent(self, agent):
        """Test process_concurrent method"""
        items = [{"id": i} for i in range(5)]
        
        results = await agent.process_concurrent(items, max_concurrent=2)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["data"]["id"] == i
            
    @pytest.mark.asyncio
    async def test_process_concurrent_empty(self, agent):
        """Test process_concurrent with empty list"""
        results = await agent.process_concurrent([], max_concurrent=10)
        assert results == []
        
    @pytest.mark.asyncio
    async def test_process_stream(self, agent):
        """Test process_stream generator method"""
        dataset = range(250)
        chunks = []
        
        async for chunk in agent.process_stream(dataset, chunk_size=100):
            chunks.append(chunk)
            
        assert len(chunks) == 3
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        assert len(chunks[2]) == 50
        
    @pytest.mark.asyncio
    async def test_process_stream_exact_chunks(self, agent):
        """Test process_stream with exact chunk size"""
        dataset = range(200)
        chunks = []
        
        async for chunk in agent.process_stream(dataset, chunk_size=100):
            chunks.append(chunk)
            
        assert len(chunks) == 2
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        
    @pytest.mark.asyncio
    async def test_save_state(self, agent):
        """Test save_state method"""
        agent.state = {"key": "value", "count": 42}
        
        # Should not raise
        await agent.save_state()
        
        assert agent.state == {"key": "value", "count": 42}
        
    @pytest.mark.asyncio
    async def test_save_state_no_existing(self, agent):
        """Test save_state without existing state"""
        if hasattr(agent, 'state'):
            delattr(agent, 'state')
            
        await agent.save_state()
        
        assert agent.state == {}
        
    @pytest.mark.asyncio
    async def test_load_state(self, agent):
        """Test load_state method"""
        await agent.load_state()
        
        assert hasattr(agent, 'state')
        assert isinstance(agent.state, dict)
        
    @pytest.mark.asyncio
    async def test_load_state_existing(self, agent):
        """Test load_state with existing state"""
        agent.state = {"existing": "data"}
        
        await agent.load_state()
        
        # In the stub implementation, it doesn't overwrite
        assert agent.state == {"existing": "data"}
        
    @pytest.mark.asyncio
    async def test_recover(self, agent):
        """Test recover method"""
        with patch.object(agent, 'load_state', new_callable=AsyncMock) as mock_load:
            await agent.recover()
            
        mock_load.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.agents.data_sub_agent", "--cov-report=term-missing"])