"""
ClickHouse Log Clustering and Pattern Analysis Tests
Tests log clustering algorithms and pattern mining
"""

from netra_backend.app.db.clickhouse_query_fixer import validate_clickhouse_query

class TestLogClusteringAlgorithms:
    """Test log clustering and pattern mining"""
    
    def test_log_clustering_with_similarity(self):
        """Test log clustering using similarity metrics"""
        query = """
        WITH log_signatures AS (
            SELECT 
                message,
                -- Extract template by replacing numbers and UUIDs
                replaceRegexpAll(
                    replaceRegexpAll(message, '[0-9]+', 'NUM'),
                    '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', 'UUID'
                ) as template,
                count() as occurrence_count,
                min(timestamp) as first_seen,
                max(timestamp) as last_seen,
                arraySlice(groupArray(JSONExtractString(metadata, 'request_id')), 1, 10) as sample_requests
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY message, template
            HAVING occurrence_count > 1
        ),
        clusters AS (
            SELECT 
                template,
                sum(occurrence_count) as total_occurrences,
                count() as unique_messages,
                min(first_seen) as cluster_first_seen,
                max(last_seen) as cluster_last_seen,
                arraySlice(groupArray(arrayElement(sample_requests, 1)), 1, 5) as cluster_samples
            FROM log_signatures
            GROUP BY template
            HAVING total_occurrences > 10
        )
        SELECT * FROM clusters
        ORDER BY total_occurrences DESC
        LIMIT 100
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Log clustering query failed: {error}"
    
    def test_error_cascade_detection(self):
        """Test detection of error cascades in logs"""
        query = """
        WITH error_windows AS (
            SELECT 
                toStartOfMinute(timestamp) as minute,
                component,
                count() as error_count,
                groupArray(message)[1:5] as sample_errors,
                uniq(JSONExtractString(metadata, 'user_id')) as affected_users
            FROM netra_app_internal_logs
            WHERE level = 'ERROR'
                AND timestamp >= now() - INTERVAL 6 HOUR
            GROUP BY minute, component
        ),
        cascades AS (
            SELECT 
                e1.minute as start_minute,
                e1.component as source_component,
                e2.component as affected_component,
                e1.error_count as source_errors,
                e2.error_count as cascade_errors,
                e2.affected_users
            FROM error_windows e1
            INNER JOIN error_windows e2 
                ON e2.minute >= e1.minute 
                AND e2.minute <= e1.minute + INTERVAL 5 MINUTE
                AND e1.component != e2.component
            WHERE e1.error_count > 10
                AND e2.error_count > e1.error_count * 0.5
        )
        SELECT * FROM cascades
        ORDER BY start_minute DESC, source_errors DESC
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Error cascade query failed: {error}"