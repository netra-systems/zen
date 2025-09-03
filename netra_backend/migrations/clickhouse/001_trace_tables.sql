-- ClickHouse Trace Tables Migration
-- Purpose: Create comprehensive trace storage for agent executions, events, metrics, and errors
-- Partitioning: By month for efficient data management and querying
-- Version: 1.0.0

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS netra_traces;

-- ========================================
-- 1. AGENT_EXECUTIONS TABLE
-- ========================================
-- Tracks complete agent execution lifecycle with all metadata
CREATE TABLE IF NOT EXISTS netra_traces.agent_executions
(
    -- Primary identifiers
    trace_id String,
    execution_id String,
    correlation_id String,
    user_id String,
    organization_id String,
    
    -- Agent metadata
    agent_type String,
    agent_name String,
    agent_version String,
    parent_agent_id String,
    
    -- Execution details
    status Enum8('pending' = 1, 'running' = 2, 'completed' = 3, 'failed' = 4, 'cancelled' = 5),
    start_time DateTime64(3),
    end_time Nullable(DateTime64(3)),
    duration_ms UInt32,
    
    -- Request/Response
    request_payload String,  -- JSON
    response_payload String,  -- JSON
    error_message Nullable(String),
    error_stack Nullable(String),
    
    -- Resource usage
    cpu_time_ms UInt32,
    memory_mb UInt32,
    token_count UInt32,
    tool_calls_count UInt32,
    
    -- Metadata
    environment String,
    service_version String,
    metadata String,  -- JSON for extensibility
    tags Array(String),
    
    -- Timestamps
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (trace_id, start_time, user_id)
PRIMARY KEY (trace_id, start_time)
TTL partition_date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Indexes for agent_executions
ALTER TABLE netra_traces.agent_executions
    ADD INDEX idx_user_id user_id TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_correlation_id correlation_id TYPE set(1000) GRANULARITY 4,
    ADD INDEX idx_agent_type agent_type TYPE set(50) GRANULARITY 4,
    ADD INDEX idx_status status TYPE set(5) GRANULARITY 4,
    ADD INDEX idx_tags tags TYPE bloom_filter(0.01) GRANULARITY 4;

-- ========================================
-- 2. AGENT_EVENTS TABLE
-- ========================================
-- Captures all WebSocket and tool events during execution
CREATE TABLE IF NOT EXISTS netra_traces.agent_events
(
    -- Primary identifiers
    event_id String,
    trace_id String,
    execution_id String,
    correlation_id String,
    user_id String,
    
    -- Event details
    event_type Enum8(
        'agent_started' = 1,
        'agent_thinking' = 2,
        'tool_executing' = 3,
        'tool_completed' = 4,
        'agent_completed' = 5,
        'websocket_sent' = 6,
        'websocket_received' = 7,
        'error_occurred' = 8,
        'custom' = 9
    ),
    event_name String,
    event_category String,
    
    -- Event data
    event_payload String,  -- JSON
    tool_name Nullable(String),
    tool_input Nullable(String),  -- JSON
    tool_output Nullable(String),  -- JSON
    
    -- Timing
    timestamp DateTime64(3),
    duration_ms Nullable(UInt32),
    sequence_number UInt32,
    
    -- Metadata
    session_id String,
    client_id String,
    metadata String,  -- JSON
    
    -- Timestamps
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (trace_id, timestamp, sequence_number)
PRIMARY KEY (trace_id, timestamp)
TTL partition_date + INTERVAL 60 DAY
SETTINGS index_granularity = 8192;

-- Indexes for agent_events
ALTER TABLE netra_traces.agent_events
    ADD INDEX idx_event_type event_type TYPE set(10) GRANULARITY 4,
    ADD INDEX idx_event_name event_name TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_tool_name tool_name TYPE set(50) GRANULARITY 4,
    ADD INDEX idx_user_id user_id TYPE set(100) GRANULARITY 4;

-- ========================================
-- 3. PERFORMANCE_METRICS TABLE
-- ========================================
-- Detailed performance breakdowns for optimization
CREATE TABLE IF NOT EXISTS netra_traces.performance_metrics
(
    -- Primary identifiers
    metric_id String,
    trace_id String,
    execution_id String,
    user_id String,
    
    -- Metric categorization
    metric_type Enum8(
        'latency' = 1,
        'throughput' = 2,
        'resource' = 3,
        'llm' = 4,
        'database' = 5,
        'network' = 6,
        'custom' = 7
    ),
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
ORDER BY (trace_id, timestamp, metric_type)
PRIMARY KEY (trace_id, timestamp)
TTL partition_date + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Indexes for performance_metrics
ALTER TABLE netra_traces.performance_metrics
    ADD INDEX idx_metric_type metric_type TYPE set(7) GRANULARITY 4,
    ADD INDEX idx_metric_name metric_name TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_component_name component_name TYPE set(50) GRANULARITY 4;

-- ========================================
-- 4. TRACE_CORRELATIONS TABLE
-- ========================================
-- Maps parent-child relationships and dependencies
CREATE TABLE IF NOT EXISTS netra_traces.trace_correlations
(
    -- Primary identifiers
    correlation_id String,
    parent_trace_id String,
    child_trace_id String,
    
    -- Relationship details
    relationship_type Enum8(
        'parent_child' = 1,
        'sibling' = 2,
        'dependency' = 3,
        'triggered_by' = 4,
        'related' = 5
    ),
    relationship_name String,
    
    -- Execution context
    parent_agent_type String,
    child_agent_type String,
    depth_level UInt8,
    
    -- Timing
    parent_start_time DateTime64(3),
    child_start_time DateTime64(3),
    overlap_duration_ms UInt32,
    
    -- Metadata
    context String,  -- JSON
    tags Array(String),
    
    -- Timestamps
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (parent_trace_id, child_trace_id, created_at)
PRIMARY KEY (parent_trace_id, child_trace_id)
TTL partition_date + INTERVAL 60 DAY
SETTINGS index_granularity = 8192;

-- Indexes for trace_correlations
ALTER TABLE netra_traces.trace_correlations
    ADD INDEX idx_child_trace child_trace_id TYPE set(1000) GRANULARITY 4,
    ADD INDEX idx_correlation correlation_id TYPE set(1000) GRANULARITY 4,
    ADD INDEX idx_relationship_type relationship_type TYPE set(5) GRANULARITY 4;

-- ========================================
-- 5. ERROR_LOGS TABLE
-- ========================================
-- Comprehensive error tracking and debugging
CREATE TABLE IF NOT EXISTS netra_traces.error_logs
(
    -- Primary identifiers
    error_id String,
    trace_id String,
    execution_id String,
    user_id String,
    
    -- Error categorization
    error_type Enum8(
        'validation' = 1,
        'authentication' = 2,
        'authorization' = 3,
        'network' = 4,
        'database' = 5,
        'llm' = 6,
        'tool' = 7,
        'timeout' = 8,
        'rate_limit' = 9,
        'system' = 10,
        'unknown' = 11
    ),
    error_code String,
    error_category String,
    severity Enum8('debug' = 1, 'info' = 2, 'warning' = 3, 'error' = 4, 'critical' = 5),
    
    -- Error details
    error_message String,
    error_stack String,
    error_context String,  -- JSON
    
    -- Location information
    service_name String,
    component_name String,
    function_name String,
    file_path String,
    line_number UInt32,
    
    -- Recovery information
    is_recoverable Bool,
    retry_count UInt8,
    max_retries UInt8,
    recovery_action String,
    
    -- Impact
    affected_users Array(String),
    affected_features Array(String),
    business_impact String,
    
    -- Metadata
    environment String,
    version String,
    metadata String,  -- JSON
    tags Array(String),
    
    -- Timestamps
    timestamp DateTime64(3),
    created_at DateTime64(3) DEFAULT now64(3),
    partition_date Date DEFAULT toDate(created_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (trace_id, timestamp, severity)
PRIMARY KEY (trace_id, timestamp)
TTL partition_date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Indexes for error_logs
ALTER TABLE netra_traces.error_logs
    ADD INDEX idx_error_type error_type TYPE set(11) GRANULARITY 4,
    ADD INDEX idx_severity severity TYPE set(5) GRANULARITY 4,
    ADD INDEX idx_error_code error_code TYPE set(100) GRANULARITY 4,
    ADD INDEX idx_component component_name TYPE set(50) GRANULARITY 4;

-- ========================================
-- 6. MATERIALIZED VIEWS FOR COMMON QUERIES
-- ========================================

-- View for execution summary by user
CREATE MATERIALIZED VIEW IF NOT EXISTS netra_traces.mv_user_execution_summary
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date, agent_type)
AS SELECT
    user_id,
    toDate(start_time) as date,
    agent_type,
    count() as execution_count,
    avg(duration_ms) as avg_duration_ms,
    max(duration_ms) as max_duration_ms,
    min(duration_ms) as min_duration_ms,
    sum(token_count) as total_tokens,
    sum(tool_calls_count) as total_tool_calls,
    countIf(status = 'completed') as successful_count,
    countIf(status = 'failed') as failed_count
FROM netra_traces.agent_executions
GROUP BY user_id, date, agent_type;

-- View for error patterns
CREATE MATERIALIZED VIEW IF NOT EXISTS netra_traces.mv_error_patterns
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, error_type, error_code)
AS SELECT
    toDate(timestamp) as date,
    error_type,
    error_code,
    error_category,
    severity,
    count() as error_count,
    uniqExact(user_id) as affected_users_count,
    uniqExact(trace_id) as affected_traces_count,
    any(error_message) as sample_message
FROM netra_traces.error_logs
GROUP BY date, error_type, error_code, error_category, severity;

-- View for performance trends
CREATE MATERIALIZED VIEW IF NOT EXISTS netra_traces.mv_performance_trends
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, hour, metric_type, component_name)
AS SELECT
    toDate(timestamp) as date,
    toHour(timestamp) as hour,
    metric_type,
    component_name,
    avg(value) as avg_value,
    quantile(0.5)(value) as p50_value,
    quantile(0.95)(value) as p95_value,
    quantile(0.99)(value) as p99_value,
    max(value) as max_value,
    count() as sample_count
FROM netra_traces.performance_metrics
GROUP BY date, hour, metric_type, component_name;

-- View for agent interaction patterns
CREATE MATERIALIZED VIEW IF NOT EXISTS netra_traces.mv_agent_interactions
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, parent_agent_type, child_agent_type)
AS SELECT
    toDate(created_at) as date,
    parent_agent_type,
    child_agent_type,
    relationship_type,
    count() as interaction_count,
    avg(overlap_duration_ms) as avg_overlap_ms,
    max(depth_level) as max_depth
FROM netra_traces.trace_correlations
GROUP BY date, parent_agent_type, child_agent_type, relationship_type;

-- ========================================
-- 7. DISTRIBUTED TABLES (for cluster deployments)
-- ========================================
-- Note: Uncomment these when deploying to a ClickHouse cluster

-- CREATE TABLE IF NOT EXISTS netra_traces.agent_executions_distributed AS netra_traces.agent_executions
-- ENGINE = Distributed('netra_cluster', 'netra_traces', 'agent_executions', rand());

-- CREATE TABLE IF NOT EXISTS netra_traces.agent_events_distributed AS netra_traces.agent_events
-- ENGINE = Distributed('netra_cluster', 'netra_traces', 'agent_events', rand());

-- CREATE TABLE IF NOT EXISTS netra_traces.performance_metrics_distributed AS netra_traces.performance_metrics
-- ENGINE = Distributed('netra_cluster', 'netra_traces', 'performance_metrics', rand());

-- CREATE TABLE IF NOT EXISTS netra_traces.trace_correlations_distributed AS netra_traces.trace_correlations
-- ENGINE = Distributed('netra_cluster', 'netra_traces', 'trace_correlations', rand());

-- CREATE TABLE IF NOT EXISTS netra_traces.error_logs_distributed AS netra_traces.error_logs
-- ENGINE = Distributed('netra_cluster', 'netra_traces', 'error_logs', rand());

-- ========================================
-- 8. GRANTS AND PERMISSIONS
-- ========================================
-- Note: Adjust usernames according to your setup

-- GRANT SELECT, INSERT ON netra_traces.* TO 'netra_writer';
-- GRANT SELECT ON netra_traces.* TO 'netra_reader';
-- GRANT ALL ON netra_traces.* TO 'netra_admin';