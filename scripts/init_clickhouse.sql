-- Initialize ClickHouse Analytics Database
CREATE DATABASE IF NOT EXISTS netra_analytics;

USE netra_analytics;

-- Create tables for analytics
CREATE TABLE IF NOT EXISTS events (
    timestamp DateTime,
    event_type String,
    user_id String,
    session_id String,
    data String
) ENGINE = MergeTree()
ORDER BY (timestamp, event_type, user_id);

SELECT 'ClickHouse initialized successfully' as status;
