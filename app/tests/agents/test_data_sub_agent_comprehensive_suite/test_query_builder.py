"""
Tests for QueryBuilder class methods
"""

import pytest
from datetime import datetime
from app.agents.data_sub_agent import QueryBuilder


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