"""
Tests for DataSubAgent analysis methods - performance metrics, anomaly detection, usage patterns
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.agents.data_sub_agent.agent import DataSubAgent


class TestDataSubAgentAnalysis:
    """Test DataSubAgent analysis methods"""
    
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
    async def test_analyze_performance_metrics_minute_aggregation(self, agent, sample_performance_data):
        """Test analyzing performance metrics with minute aggregation"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_performance_data
            
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
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert result["status"] == "no_data"
        
    @pytest.mark.asyncio
    async def test_detect_anomalies_with_anomalies(self, agent, sample_anomaly_data):
        """Test anomaly detection with anomalies present"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_anomaly_data
            
            result = await agent._detect_anomalies(
                user_id=1,
                metric_name="latency_ms",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2)),
                z_score_threshold=3.0
            )
            
        assert "anomalies" in result
        assert result["anomalies_detected"] == 1
        assert result["anomaly_percentage"] == 50.0
        
    @pytest.mark.asyncio
    async def test_detect_anomalies_no_anomalies(self, agent):
        """Test anomaly detection with no anomalies"""
        mock_data = [
            {'timestamp': f'2024-01-01T12:{i:02d}:00', 'value': 50.0,
             'avg_value': 50.0, 'std_value': 10.0, 'z_score': 0.0}
            for i in range(10)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._detect_anomalies(
                user_id=1,
                metric_name="latency_ms",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert result["anomalies_detected"] == 0
        assert result["anomaly_percentage"] == 0.0
        
    @pytest.mark.asyncio
    async def test_analyze_usage_patterns_no_data(self, agent):
        """Test usage pattern analysis with no data"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            
            result = await agent._analyze_usage_patterns(user_id=1, days_back=7)
            
        assert result["status"] == "no_data"
        
    @pytest.mark.asyncio
    async def test_analyze_usage_patterns_with_data(self, agent, sample_usage_patterns):
        """Test usage pattern analysis with data"""
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_usage_patterns
            
            result = await agent._analyze_usage_patterns(user_id=1, days_back=7)
            
        assert "hourly_patterns" in result
        assert "peak_hour" in result
        assert result["peak_hour"] == 11
        assert "low_hour" in result
        assert result["low_hour"] == 9
        
    @pytest.mark.asyncio
    async def test_analyze_correlations_insufficient_data(self, agent):
        """Test correlation analysis with insufficient data"""
        mock_data = [
            {'metric1': 1.0, 'metric2': 2.0}  # Only 1 data point
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_correlations(
                user_id=1,
                metric1="latency_ms",
                metric2="throughput",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert result["status"] == "insufficient_data"
        
    @pytest.mark.asyncio
    async def test_analyze_correlations_with_correlation(self, agent):
        """Test correlation analysis with strong correlation"""
        mock_data = [
            {'metric1': float(i), 'metric2': float(i * 2)}
            for i in range(10)
        ]
        
        with patch.object(agent, '_fetch_clickhouse_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await agent._analyze_correlations(
                user_id=1,
                metric1="latency_ms",
                metric2="throughput",
                time_range=(datetime(2024, 1, 1), datetime(2024, 1, 2))
            )
            
        assert "correlation_coefficient" in result
        assert result["correlation_coefficient"] == pytest.approx(1.0, rel=0.01)
        assert result["correlation_strength"] == "strong"