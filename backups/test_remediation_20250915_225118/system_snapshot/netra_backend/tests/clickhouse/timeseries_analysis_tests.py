"""
ClickHouse Time Series Analysis Tests
Tests time-series analysis capabilities and anomaly detection
"""

from netra_backend.app.db.clickhouse_query_fixer import validate_clickhouse_query

class TestTimeSeriesAnalysis:
    """Test time-series analysis capabilities"""
    
    def test_moving_average_calculation(self):
        """Test moving average calculation for metrics"""
        query = """
        WITH time_series AS (
            SELECT 
                toStartOfMinute(timestamp) as minute,
                avg(arrayElement(metrics.value, 
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 24 HOUR
                AND arrayExists(x -> x = 'latency_ms', metrics.name)
            GROUP BY minute
        )
        SELECT 
            minute,
            avg_latency,
            avg(avg_latency) OVER (
                ORDER BY minute 
                ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
            ) as moving_avg_6min,
            avg(avg_latency) OVER (
                ORDER BY minute 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW  
            ) as moving_avg_1hour
        FROM time_series
        ORDER BY minute DESC
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Moving average query failed: {error}"
    
    def test_anomaly_detection_with_zscore(self):
        """Test anomaly detection using z-score"""
        query = """
        WITH baseline AS (
            SELECT 
                avg(arrayElement(metrics.value, 
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as mean_latency,
                stddevPop(arrayElement(metrics.value,
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as stddev_latency
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 7 DAY
                AND timestamp < now() - INTERVAL 1 HOUR
                AND arrayExists(x -> x = 'latency_ms', metrics.name)
        ),
        recent_data AS (
            SELECT 
                timestamp,
                workload_id,
                arrayElement(metrics.value,
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name)) as latency
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
                AND arrayExists(x -> x = 'latency_ms', metrics.name)
        )
        SELECT 
            rd.timestamp,
            rd.workload_id,
            rd.latency,
            b.mean_latency,
            b.stddev_latency,
            (rd.latency - b.mean_latency) / nullIf(b.stddev_latency, 0) as z_score,
            CASE 
                WHEN abs((rd.latency - b.mean_latency) / nullIf(b.stddev_latency, 0)) > 3 THEN 'critical'
                WHEN abs((rd.latency - b.mean_latency) / nullIf(b.stddev_latency, 0)) > 2 THEN 'warning'
                ELSE 'normal'
            END as anomaly_level
        FROM recent_data rd
        CROSS JOIN baseline b
        ORDER BY z_score DESC
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Anomaly detection query failed: {error}"