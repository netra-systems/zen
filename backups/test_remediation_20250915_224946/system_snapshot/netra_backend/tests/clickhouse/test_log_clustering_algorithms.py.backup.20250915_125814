"""
Log Clustering Algorithms Tests
Test log clustering and pattern mining
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

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
                    '[a-f0-9]{8]-[a-f0-9]{4]-[a-f0-9]{4]-[a-f0-9]{4]-[a-f0-9]{12]', 'UUID'
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

    def test_log_frequency_analysis(self):
        """Test log frequency analysis for pattern identification"""
        frequency_query = """
        WITH message_analysis AS (
            SELECT 
                component,
                level,
                message,
                count() as frequency,
                toStartOfHour(min(timestamp)) as first_occurrence,
                toStartOfHour(max(timestamp)) as last_occurrence,
                uniq(JSONExtractString(metadata, 'user_id')) as unique_users_affected,
                -- Extract common error patterns
                CASE 
                    WHEN message LIKE '%Exception%' THEN 'exception'
                    WHEN message LIKE '%timeout%' OR message LIKE '%timed out%' THEN 'timeout'
                    WHEN message LIKE '%connection%' AND message LIKE '%failed%' THEN 'connection_error'
                    WHEN message LIKE '%permission%' OR message LIKE '%access%' THEN 'permission_error'
                    ELSE 'other'
                END as error_category
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 24 HOUR
                AND level IN ('ERROR', 'WARNING')
            GROUP BY component, level, message
        )
        SELECT 
            error_category,
            component,
            level,
            sum(frequency) as total_occurrences,
            count() as unique_message_types,
            sum(unique_users_affected) as total_users_affected,
            min(first_occurrence) as category_first_seen,
            max(last_occurrence) as category_last_seen,
            avg(frequency) as avg_frequency_per_message_type
        FROM message_analysis
        GROUP BY error_category, component, level
        ORDER BY total_occurrences DESC
        """
        
        is_valid, error = validate_clickhouse_query(frequency_query)
        assert is_valid, f"Frequency analysis query failed: {error}"

    def test_log_similarity_clustering(self):
        """Test advanced log similarity clustering using string functions"""
        similarity_query = """
        WITH log_features AS (
            SELECT 
                message,
                component,
                level,
                -- Extract key features for clustering
                length(message) as message_length,
                length(splitByChar(' ', message)) as word_count,
                -- Count special characters that might indicate structure
                length(message) - length(replaceRegexpAll(message, '[^0-9]', '')) as digit_count,
                length(message) - length(replaceRegexpAll(message, '[^A-Z]', '')) as uppercase_count,
                -- Extract first few words as signature
                arraySlice(splitByChar(' ', message), 1, 5) as first_words,
                count() as occurrence_count
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 6 HOUR
            GROUP BY message, component, level
            HAVING occurrence_count > 1
        ),
        similarity_clusters AS (
            SELECT 
                arrayStringConcat(first_words, ' ') as message_signature,
                component,
                level,
                avg(message_length) as avg_message_length,
                avg(word_count) as avg_word_count,
                sum(occurrence_count) as cluster_size,
                count() as messages_in_cluster,
                groupArray(message)[1:3] as sample_messages
            FROM log_features
            GROUP BY message_signature, component, level
            HAVING cluster_size > 5
        )
        SELECT 
            message_signature,
            component,
            level,
            cluster_size,
            messages_in_cluster,
            avg_message_length,
            sample_messages,
            -- Calculate cluster density (how similar messages are)
            cluster_size / nullIf(messages_in_cluster, 0) as cluster_density
        FROM similarity_clusters
        ORDER BY cluster_size DESC
        """
        
        is_valid, error = validate_clickhouse_query(similarity_query)
        assert is_valid, f"Similarity clustering query failed: {error}"

    def test_temporal_pattern_mining(self):
        """Test temporal pattern mining in log sequences"""
        temporal_query = """
        WITH log_sequences AS (
            SELECT 
                JSONExtractString(metadata, 'request_id') as request_id,
                component,
                level,
                message,
                timestamp,
                lag(component) OVER (PARTITION BY JSONExtractString(metadata, 'request_id') ORDER BY timestamp) as prev_component,
                lag(level) OVER (PARTITION BY JSONExtractString(metadata, 'request_id') ORDER BY timestamp) as prev_level,
                lead(component) OVER (PARTITION BY JSONExtractString(metadata, 'request_id') ORDER BY timestamp) as next_component,
                lead(level) OVER (PARTITION BY JSONExtractString(metadata, 'request_id') ORDER BY timestamp) as next_level
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 6 HOUR
                AND JSONExtractString(metadata, 'request_id') != ''
        ),
        pattern_sequences AS (
            SELECT 
                concat(ifNull(prev_component, ''), '->', component, '->', ifNull(next_component, '')) as component_sequence,
                concat(ifNull(prev_level, ''), '->', level, '->', ifNull(next_level, '')) as level_sequence,
                count() as pattern_frequency,
                uniq(request_id) as unique_requests,
                groupArray(request_id)[1:5] as sample_request_ids
            FROM log_sequences
            WHERE prev_component IS NOT NULL OR next_component IS NOT NULL
            GROUP BY component_sequence, level_sequence
            HAVING pattern_frequency > 10
        )
        SELECT 
            component_sequence,
            level_sequence,
            pattern_frequency,
            unique_requests,
            sample_request_ids,
            -- Calculate pattern strength (how often this sequence occurs vs total sequences)
            pattern_frequency / (SELECT sum(pattern_frequency) FROM pattern_sequences) as pattern_strength
        FROM pattern_sequences
        ORDER BY pattern_frequency DESC
        """
        
        is_valid, error = validate_clickhouse_query(temporal_query)
        assert is_valid, f"Temporal pattern mining query failed: {error}"

    def test_log_anomaly_clustering(self):
        """Test clustering of anomalous log patterns"""
        anomaly_query = """
        WITH log_stats AS (
            SELECT 
                component,
                level,
                toStartOfHour(timestamp) as hour,
                count() as hourly_count,
                uniq(message) as unique_messages,
                uniq(JSONExtractString(metadata, 'user_id')) as unique_users
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 48 HOUR
            GROUP BY component, level, hour
        ),
        baseline_stats AS (
            SELECT 
                component,
                level,
                avg(hourly_count) as avg_hourly_count,
                stddevPop(hourly_count) as stddev_hourly_count,
                avg(unique_messages) as avg_unique_messages,
                avg(unique_users) as avg_unique_users
            FROM log_stats
            WHERE hour < now() - INTERVAL 6 HOUR  -- Exclude recent hours for baseline
            GROUP BY component, level
        ),
        anomalous_periods AS (
            SELECT 
                ls.hour,
                ls.component,
                ls.level,
                ls.hourly_count,
                ls.unique_messages,
                ls.unique_users,
                bs.avg_hourly_count,
                bs.stddev_hourly_count,
                (ls.hourly_count - bs.avg_hourly_count) / nullIf(bs.stddev_hourly_count, 0) as count_z_score,
                CASE 
                    WHEN abs((ls.hourly_count - bs.avg_hourly_count) / nullIf(bs.stddev_hourly_count, 0)) > 3 THEN 'extreme_anomaly'
                    WHEN abs((ls.hourly_count - bs.avg_hourly_count) / nullIf(bs.stddev_hourly_count, 0)) > 2 THEN 'moderate_anomaly'
                    ELSE 'normal'
                END as anomaly_level
            FROM log_stats ls
            INNER JOIN baseline_stats bs ON ls.component = bs.component AND ls.level = bs.level
            WHERE ls.hour >= now() - INTERVAL 6 HOUR
        )
        SELECT 
            anomaly_level,
            component,
            level,
            count() as anomaly_period_count,
            avg(count_z_score) as avg_anomaly_severity,
            max(hourly_count) as max_count_in_anomaly,
            groupArray(hour)[1:5] as sample_anomaly_hours
        FROM anomalous_periods
        WHERE anomaly_level != 'normal'
        GROUP BY anomaly_level, component, level
        ORDER BY avg_anomaly_severity DESC
        """
        
        is_valid, error = validate_clickhouse_query(anomaly_query)
        assert is_valid, f"Anomaly clustering query failed: {error}"