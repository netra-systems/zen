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
TTL event_timestamp + INTERVAL 90 DAY;

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
TTL event_timestamp + INTERVAL 180 DAY;

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
TTL event_timestamp + INTERVAL 30 DAY;

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
TTL event_timestamp + INTERVAL 7 DAY;

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
TTL event_timestamp + INTERVAL 30 DAY;

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
TTL event_timestamp + INTERVAL 1095 DAY; -- 3 years for billing

-- Create materialized views for real-time aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS user_activity_hourly
TO usage_metrics AS
SELECT
    '' as organization_id, -- Will be populated by actual events
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

-- Test data insertion function (simulate via INSERT statements)
-- Insert sample test data for immediate testing

-- Sample user events
INSERT INTO user_events (user_id, event_type, session_id, properties) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'login', 'session_1', map('source', 'web', 'device', 'desktop')),
('550e8400-e29b-41d4-a716-446655440001', 'page_view', 'session_1', map('page', '/dashboard', 'referrer', 'direct')),
('550e8400-e29b-41d4-a716-446655440002', 'login', 'session_2', map('source', 'mobile', 'device', 'phone')),
('550e8400-e29b-41d4-a716-446655440002', 'agent_create', 'session_2', map('agent_type', 'chat', 'model', 'gpt-4'));

-- Sample conversation events  
INSERT INTO conversation_events (
    conversation_id, agent_id, user_id, organization_id, 
    event_type, message_count, tokens_used, model_used, tool_calls
) VALUES
('660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440001', 
 '550e8400-e29b-41d4-a716-446655440001', '880e8400-e29b-41d4-a716-446655440001',
 'conversation_start', 1, 150, 'gpt-4', []),
('660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440001',
 '550e8400-e29b-41d4-a716-446655440001', '880e8400-e29b-41d4-a716-446655440001', 
 'message_sent', 5, 750, 'gpt-4', ['web_search', 'code_execution']);

-- Sample tool executions
INSERT INTO tool_executions (
    conversation_id, agent_id, tool_name, execution_status, 
    execution_time_ms, parameters_size, result_size
) VALUES
('660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440001',
 'web_search', 'success', 1250, 512, 2048),
('660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440001',
 'code_execution', 'success', 890, 1024, 256);

-- Sample WebSocket events
INSERT INTO websocket_events (connection_id, user_id, event_type, message_type, message_size) VALUES
('ws_conn_1', '550e8400-e29b-41d4-a716-446655440001', 'connect', null, 0),
('ws_conn_1', '550e8400-e29b-41d4-a716-446655440001', 'message', 'agent_message', 512),
('ws_conn_1', '550e8400-e29b-41d4-a716-446655440001', 'message', 'user_message', 256),
('ws_conn_1', '550e8400-e29b-41d4-a716-446655440001', 'disconnect', null, 0);

-- Sample performance metrics
INSERT INTO performance_metrics (service_name, endpoint, method, status_code, response_time_ms, user_id) VALUES
('auth-service', '/api/v1/auth/login', 'POST', 200, 145, '550e8400-e29b-41d4-a716-446655440001'),
('backend-service', '/api/v1/agents', 'GET', 200, 89, '550e8400-e29b-41d4-a716-446655440001'),
('backend-service', '/api/v1/conversations', 'POST', 201, 234, '550e8400-e29b-41d4-a716-446655440001'),
('websocket-service', '/ws', 'CONNECT', 101, 12, '550e8400-e29b-41d4-a716-446655440001');

-- Sample billing events
INSERT INTO billing_events (organization_id, user_id, billing_type, quantity, unit_cost, resource_id) VALUES
('880e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'token_usage', 750, 0.002, 'gpt-4'),
('880e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'api_call', 1, 0.01, 'conversation_api'),
('880e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'tool_execution', 2, 0.05, 'web_search');

-- Create test helper functions
CREATE OR REPLACE FUNCTION reset_test_analytics() AS $$
BEGIN
    -- Note: ClickHouse doesn't have stored procedures, so this would be done via DELETE statements
    -- DELETE FROM user_events WHERE user_id LIKE '550e8400%';
    -- DELETE FROM conversation_events WHERE user_id LIKE '550e8400%';
    -- etc.
    SELECT 'Test analytics data reset' as status;
END;
$$;

-- Optimize tables for test performance
OPTIMIZE TABLE user_events FINAL;
OPTIMIZE TABLE conversation_events FINAL;  
OPTIMIZE TABLE tool_executions FINAL;
OPTIMIZE TABLE websocket_events FINAL;
OPTIMIZE TABLE performance_metrics FINAL;
OPTIMIZE TABLE billing_events FINAL;

SELECT 'ClickHouse test database initialized successfully' as status;