-- ClickHouse Analytics Tables Migration
-- Purpose: Create analytics tables in netra_analytics database for compatibility
-- Version: 1.0.0

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS netra_analytics;

-- ========================================
-- PERFORMANCE_METRICS TABLE (Analytics Database)
-- ========================================
-- Simplified performance metrics for analytics queries
CREATE TABLE IF NOT EXISTS netra_analytics.performance_metrics
(
    -- Primary identifiers
    metric_id String,
    trace_id String,
    execution_id String,
    user_id String,
    
    -- Metric categorization
    metric_type String,
    metric_name String,
    metric_category String,
    
    -- Performance data
    value Float64,
    unit String,
    
    -- Timing breakdowns
    total_time_ms UInt32,
    llm_time_ms UInt32,
    tool_time_ms UInt32,
    database_time_ms UInt32,
    network_time_ms UInt32,
    processing_time_ms UInt32,
    
    -- Resource metrics
    cpu_percent Float32,
    memory_mb Float32,
    disk_io_mb Float32,
    network_io_mb Float32,
    
    -- LLM specific
    prompt_tokens UInt32,
    completion_tokens UInt32,
    total_tokens UInt32,
    model_name String,
    
    -- Context
    operation_name String,
    component_name String,
    metadata String,  -- JSON
    
    -- Timestamps
    timestamp DateTime64(3),
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (user_id, timestamp, metric_type)
PRIMARY KEY (user_id, timestamp)
TTL partition_date + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Indexes for performance_metrics
ALTER TABLE netra_analytics.performance_metrics
    ADD INDEX idx_metric_type metric_type TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_metric_name metric_name TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_component_name component_name TYPE set(50) GRANULARITY 4,
    ADD INDEX idx_user_id user_id TYPE set(100) GRANULARITY 4;

-- ========================================
-- EVENTS TABLE (Analytics Database)
-- ========================================
-- General events table for analytics
CREATE TABLE IF NOT EXISTS netra_analytics.events
(
    -- Primary identifiers
    event_id String DEFAULT generateUUIDv4(),
    user_id String,
    session_id String,
    
    -- Event details
    event_type String,
    event_name String,
    event_category String,
    
    -- Event data
    data String,  -- JSON payload
    
    -- Timestamps
    timestamp DateTime64(3) DEFAULT now64(3),
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (user_id, timestamp, event_type)
PRIMARY KEY (user_id, timestamp)
TTL partition_date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Indexes for events
ALTER TABLE netra_analytics.events
    ADD INDEX idx_event_type event_type TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_session_id session_id TYPE set(100) GRANULARITY 4;

-- ========================================
-- USER_METRICS_SUMMARY VIEW
-- ========================================
-- Aggregated user metrics for quick analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS netra_analytics.mv_user_metrics_summary
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date)
AS SELECT
    user_id,
    toDate(timestamp) as date,
    metric_type,
    count() as metric_count,
    avg(value) as avg_value,
    max(value) as max_value,
    min(value) as min_value,
    sum(total_tokens) as total_tokens_used
FROM netra_analytics.performance_metrics
GROUP BY user_id, date, metric_type;

-- ========================================
-- SYSTEM_HEALTH_METRICS TABLE
-- ========================================
-- System-wide health and performance tracking
CREATE TABLE IF NOT EXISTS netra_analytics.system_health_metrics
(
    -- Primary identifiers
    metric_id String DEFAULT generateUUIDv4(),
    service_name String,
    instance_id String,
    
    -- Health indicators
    status Enum8('healthy' = 1, 'degraded' = 2, 'unhealthy' = 3),
    health_score Float32,
    
    -- Performance metrics
    cpu_usage Float32,
    memory_usage Float32,
    disk_usage Float32,
    network_latency Float32,
    
    -- Service metrics
    request_rate Float32,
    error_rate Float32,
    success_rate Float32,
    avg_response_time Float32,
    
    -- Metadata
    metadata String,  -- JSON
    
    -- Timestamps
    timestamp DateTime64(3) DEFAULT now64(3),
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (service_name, timestamp)
PRIMARY KEY (service_name, timestamp)
TTL partition_date + INTERVAL 7 DAY
SETTINGS index_granularity = 8192;

-- Indexes for system_health_metrics
ALTER TABLE netra_analytics.system_health_metrics
    ADD INDEX idx_status status TYPE set(3) GRANULARITY 4,
    ADD INDEX idx_instance_id instance_id TYPE set(100) GRANULARITY 4;

-- ========================================
-- ERROR_ANALYTICS TABLE
-- ========================================
-- Simplified error tracking for analytics
CREATE TABLE IF NOT EXISTS netra_analytics.error_analytics
(
    -- Primary identifiers
    error_id String DEFAULT generateUUIDv4(),
    user_id String,
    trace_id String,
    
    -- Error details
    error_type String,
    error_code String,
    error_message String,
    severity String,
    
    -- Context
    service_name String,
    component_name String,
    function_name String,
    
    -- Metadata
    metadata String,  -- JSON
    
    -- Timestamps
    timestamp DateTime64(3) DEFAULT now64(3),
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (user_id, timestamp, error_type)
PRIMARY KEY (user_id, timestamp)
TTL partition_date + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Indexes for error_analytics
ALTER TABLE netra_analytics.error_analytics
    ADD INDEX idx_error_type error_type TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_severity severity TYPE set(10) GRANULARITY 4,
    ADD INDEX idx_component component_name TYPE set(50) GRANULARITY 4;