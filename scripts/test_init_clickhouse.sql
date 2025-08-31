-- ClickHouse Test Database Initialization
-- Creates test tables and schemas for analytics testing
-- Optimized for fast test execution with real data

-- Create test database if not exists
CREATE DATABASE IF NOT EXISTS netra_test_analytics;

-- Switch to test database
USE netra_test_analytics;

-- User activity events table
CREATE TABLE IF NOT EXISTS user_events (
    id UUID DEFAULT generateUUIDv4(),
    user_id UUID NOT NULL,
    organization_id Nullable(UUID),
    event_type LowCardinality(String) NOT NULL,
    event_timestamp DateTime64(3, 'UTC') DEFAULT now64(3),
    session_id String,
    properties Map(String, String) DEFAULT map(),
    user_agent Nullable(String),
    ip_address Nullable(IPv4),
    created_date Date MATERIALIZED toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (event_type, user_id, event_timestamp)
TTL toDateTime(event_timestamp) + INTERVAL 90 DAY;

-- Agent conversation analytics
CREATE TABLE IF NOT EXISTS conversation_events (
    id UUID DEFAULT generateUUIDv4(),
    conversation_id UUID NOT NULL,
    agent_id UUID NOT NULL, 
    user_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    event_type LowCardinality(String) NOT NULL,
    message_count UInt32 DEFAULT 0,
    tokens_used UInt32 DEFAULT 0,
    execution_time_ms UInt32 DEFAULT 0,
    model_used Nullable(String),
    tool_calls Array(String) DEFAULT [],
    event_timestamp DateTime64(3, 'UTC') DEFAULT now64(3),
    properties Map(String, String) DEFAULT map(),
    created_date Date MATERIALIZED toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(event_timestamp), organization_id)
ORDER BY (organization_id, agent_id, event_timestamp)
TTL toDateTime(event_timestamp) + INTERVAL 180 DAY;

-- Tool execution analytics
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID DEFAULT generateUUIDv4(),
    conversation_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    tool_name LowCardinality(String) NOT NULL,
    execution_status LowCardinality(String) NOT NULL,
    execution_time_ms UInt32 NOT NULL,
    parameters_size UInt32 DEFAULT 0,
    result_size UInt32 DEFAULT 0,
    error_message Nullable(String),
    retry_count UInt8 DEFAULT 0,
    event_timestamp DateTime64(3, 'UTC') DEFAULT now64(3),
    created_date Date MATERIALIZED toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (tool_name, execution_status, event_timestamp)
TTL toDateTime(event_timestamp) + INTERVAL 30 DAY;

-- WebSocket connection analytics
CREATE TABLE IF NOT EXISTS websocket_events (
    id UUID DEFAULT generateUUIDv4(),
    connection_id String NOT NULL,
    user_id Nullable(UUID),
    event_type LowCardinality(String) NOT NULL, -- 'connect', 'disconnect', 'message', 'error'
    message_type Nullable(String),
    message_size UInt32 DEFAULT 0,
    latency_ms Nullable(UInt32),
    error_code Nullable(String),
    user_agent Nullable(String),
    ip_address Nullable(IPv4),
    event_timestamp DateTime64(3, 'UTC') DEFAULT now64(3),
    created_date Date MATERIALIZED toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (event_type, connection_id, event_timestamp)
TTL toDateTime(event_timestamp) + INTERVAL 7 DAY;

-- Usage metrics aggregation table
CREATE TABLE IF NOT EXISTS usage_metrics (
    organization_id UUID NOT NULL,
    metric_type LowCardinality(String) NOT NULL,
    metric_date Date NOT NULL,
    metric_hour UInt8 NOT NULL, -- 0-23
    count UInt64 DEFAULT 0,
    sum_value Float64 DEFAULT 0,
    avg_value AggregateFunction(avg, Float64),
    min_value SimpleAggregateFunction(min, Float64),
    max_value SimpleAggregateFunction(max, Float64),
    percentiles AggregateFunction(quantiles(0.5, 0.95, 0.99), Float64),
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(metric_date)
ORDER BY (organization_id, metric_type, metric_date, metric_hour)
TTL metric_date + INTERVAL 365 DAY;

-- Performance monitoring table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID DEFAULT generateUUIDv4(),
    service_name LowCardinality(String) NOT NULL,
    endpoint String NOT NULL,
    method LowCardinality(String) NOT NULL,
    status_code UInt16 NOT NULL,
    response_time_ms UInt32 NOT NULL,
    request_size UInt32 DEFAULT 0,
    response_size UInt32 DEFAULT 0,
    user_id Nullable(UUID),
    trace_id Nullable(String),
    error_message Nullable(String),
    event_timestamp DateTime64(3, 'UTC') DEFAULT now64(3),
    created_date Date MATERIALIZED toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(event_timestamp), service_name)
ORDER BY (service_name, endpoint, event_timestamp)
TTL toDateTime(event_timestamp) + INTERVAL 30 DAY;

-- Billing and costs tracking
CREATE TABLE IF NOT EXISTS billing_events (
    id UUID DEFAULT generateUUIDv4(),
    organization_id UUID NOT NULL,
    user_id Nullable(UUID),
    billing_type LowCardinality(String) NOT NULL, -- 'token_usage', 'api_call', 'storage', etc.
    quantity Float64 NOT NULL,
    unit_cost Float64 DEFAULT 0,
    total_cost Float64 MATERIALIZED quantity * unit_cost,
    currency LowCardinality(String) DEFAULT 'USD',
    resource_id Nullable(String),
    metadata Map(String, String) DEFAULT map(),
    event_timestamp DateTime64(3, 'UTC') DEFAULT now64(3),
    billing_date Date MATERIALIZED toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(event_timestamp), organization_id)
ORDER BY (organization_id, billing_type, event_timestamp)
TTL toDateTime(event_timestamp) + INTERVAL 1095 DAY; -- 3 years for billing

-- Create materialized views for real-time aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS user_activity_hourly
TO usage_metrics AS
SELECT
    generateUUIDv4() as organization_id, -- Placeholder UUID for events without organization
    'user_activity' as metric_type,
    toDate(event_timestamp) as metric_date,
    toHour(event_timestamp) as metric_hour,
    count() as count,
    0 as sum_value,
    avgState(1.0) as avg_value,
    1.0 as min_value,
    1.0 as max_value,
    quantilesState(0.5, 0.95, 0.99)(1.0) as percentiles,
    now64(3) as updated_at
FROM user_events
GROUP BY metric_date, metric_hour;

CREATE MATERIALIZED VIEW IF NOT EXISTS conversation_metrics_hourly  
TO usage_metrics AS
SELECT
    organization_id,
    'conversation_activity' as metric_type,
    toDate(event_timestamp) as metric_date,
    toHour(event_timestamp) as metric_hour,
    count() as count,
    sum(tokens_used) as sum_value,
    avgState(toFloat64(tokens_used)) as avg_value,
    min(tokens_used) as min_value,
    max(tokens_used) as max_value,
    quantilesState(0.5, 0.95, 0.99)(toFloat64(tokens_used)) as percentiles,
    now64(3) as updated_at
FROM conversation_events
WHERE tokens_used > 0
GROUP BY organization_id, metric_date, metric_hour;

-- Test data will be inserted by seed scripts, not in init script

-- Test helper functions would be implemented in application code

-- Tables will be optimized after data insertion

SELECT 'ClickHouse test database initialized successfully' as status;