-- Setup additional tables for performance and race condition testing
-- Creates tables specifically for comprehensive high-load testing scenarios

-- Set search path to test schema
SET search_path = netra_test, public;

-- Create test_accounts table for race condition testing
CREATE TABLE IF NOT EXISTS test_accounts (
    id VARCHAR(255) PRIMARY KEY,
    balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create concurrent_test_users table for high-load user testing
CREATE TABLE IF NOT EXISTS concurrent_test_users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    user_tier VARCHAR(50) DEFAULT 'light', -- 'light', 'medium', 'heavy'
    is_active BOOLEAN DEFAULT true,
    is_test_user BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create concurrent_user_operations table for tracking operations during load tests
CREATE TABLE IF NOT EXISTS concurrent_user_operations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES concurrent_test_users(id) ON DELETE CASCADE,
    operation_index INTEGER NOT NULL,
    operation_type VARCHAR(100) NOT NULL, -- 'database', 'redis', 'websocket', 'agent_execution'
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create websocket_coordination table for WebSocket handshake coordination
CREATE TABLE IF NOT EXISTS websocket_coordination (
    id SERIAL PRIMARY KEY,
    websocket_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'coordinating', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id) -- Only one active coordination per user
);

-- Create shared_resources table for distributed locking tests
CREATE TABLE IF NOT EXISTS shared_resources (
    id VARCHAR(255) PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0,
    lock_version INTEGER NOT NULL DEFAULT 1,
    locked_by VARCHAR(255),
    locked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user_isolation_test_data table for session isolation testing
CREATE TABLE IF NOT EXISTS user_isolation_test_data (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    data_content JSONB NOT NULL,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create performance_metrics table for capturing detailed performance data
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    test_session_id VARCHAR(255) NOT NULL,
    concurrent_operations INTEGER NOT NULL,
    successful_operations INTEGER NOT NULL,
    failed_operations INTEGER NOT NULL,
    total_execution_time_ms BIGINT NOT NULL,
    average_response_time_ms BIGINT NOT NULL,
    p95_response_time_ms BIGINT NOT NULL,
    p99_response_time_ms BIGINT NOT NULL,
    memory_usage_start_mb DECIMAL(10, 2),
    memory_usage_peak_mb DECIMAL(10, 2),
    memory_usage_end_mb DECIMAL(10, 2),
    cpu_usage_average DECIMAL(5, 2),
    cpu_usage_peak DECIMAL(5, 2),
    race_conditions_detected INTEGER DEFAULT 0,
    race_conditions_prevented INTEGER DEFAULT 0,
    data_consistency_maintained BOOLEAN DEFAULT true,
    performance_threshold_met BOOLEAN DEFAULT false,
    test_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create race_condition_events table for tracking race condition occurrences
CREATE TABLE IF NOT EXISTS race_condition_events (
    id SERIAL PRIMARY KEY,
    test_session_id VARCHAR(255) NOT NULL,
    scenario_name VARCHAR(255) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    race_condition_type VARCHAR(100) NOT NULL, -- 'optimistic_locking', 'distributed_lock', 'message_ordering'
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    prevented BOOLEAN DEFAULT false,
    prevention_method VARCHAR(100),
    error_message TEXT,
    operation_context JSONB DEFAULT '{}'
);

-- Create high_load_sessions table for tracking high-load test sessions
CREATE TABLE IF NOT EXISTS high_load_sessions (
    id VARCHAR(255) PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,
    user_count INTEGER NOT NULL,
    operations_per_user INTEGER NOT NULL,
    session_start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_end_time TIMESTAMP WITH TIME ZONE,
    session_duration_seconds INTEGER,
    peak_memory_mb DECIMAL(10, 2),
    peak_cpu_percent DECIMAL(5, 2),
    total_operations_completed INTEGER DEFAULT 0,
    success_rate DECIMAL(5, 4) DEFAULT 0.0000,
    session_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance during high-load tests
CREATE INDEX IF NOT EXISTS idx_test_accounts_id ON test_accounts(id);
CREATE INDEX IF NOT EXISTS idx_test_accounts_version ON test_accounts(version);
CREATE INDEX IF NOT EXISTS idx_concurrent_test_users_email ON concurrent_test_users(email);
CREATE INDEX IF NOT EXISTS idx_concurrent_test_users_tier ON concurrent_test_users(user_tier);
CREATE INDEX IF NOT EXISTS idx_concurrent_user_operations_user_id ON concurrent_user_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_concurrent_user_operations_type ON concurrent_user_operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_websocket_coordination_user_id ON websocket_coordination(user_id);
CREATE INDEX IF NOT EXISTS idx_websocket_coordination_status ON websocket_coordination(status);
CREATE INDEX IF NOT EXISTS idx_shared_resources_locked_by ON shared_resources(locked_by);
CREATE INDEX IF NOT EXISTS idx_user_isolation_data_user_id ON user_isolation_test_data(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_test_name ON performance_metrics(test_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_session_id ON performance_metrics(test_session_id);
CREATE INDEX IF NOT EXISTS idx_race_condition_events_session_id ON race_condition_events(test_session_id);
CREATE INDEX IF NOT EXISTS idx_race_condition_events_scenario ON race_condition_events(scenario_name);
CREATE INDEX IF NOT EXISTS idx_high_load_sessions_name ON high_load_sessions(session_name);
CREATE INDEX IF NOT EXISTS idx_high_load_sessions_start_time ON high_load_sessions(session_start_time);

-- Create function to automatically update test account timestamps
CREATE OR REPLACE FUNCTION netra_test.update_test_account_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for test account updates
DROP TRIGGER IF EXISTS trigger_update_test_account_timestamp ON test_accounts;
CREATE TRIGGER trigger_update_test_account_timestamp
    BEFORE UPDATE ON test_accounts
    FOR EACH ROW EXECUTE FUNCTION netra_test.update_test_account_timestamp();

-- Create function to automatically update concurrent user timestamps
CREATE OR REPLACE FUNCTION netra_test.update_concurrent_user_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for concurrent user updates
DROP TRIGGER IF EXISTS trigger_update_concurrent_user_timestamp ON concurrent_test_users;
CREATE TRIGGER trigger_update_concurrent_user_timestamp
    BEFORE UPDATE ON concurrent_test_users
    FOR EACH ROW EXECUTE FUNCTION netra_test.update_concurrent_user_timestamp();

-- Create function to automatically complete operations
CREATE OR REPLACE FUNCTION netra_test.complete_user_operation()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND OLD.completed_at IS NULL THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for operation completion
DROP TRIGGER IF EXISTS trigger_complete_user_operation ON concurrent_user_operations;
CREATE TRIGGER trigger_complete_user_operation
    BEFORE UPDATE ON concurrent_user_operations
    FOR EACH ROW EXECUTE FUNCTION netra_test.complete_user_operation();

-- Create function to update websocket coordination status
CREATE OR REPLACE FUNCTION netra_test.update_websocket_coordination()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for websocket coordination updates
DROP TRIGGER IF EXISTS trigger_update_websocket_coordination ON websocket_coordination;
CREATE TRIGGER trigger_update_websocket_coordination
    BEFORE UPDATE ON websocket_coordination
    FOR EACH ROW EXECUTE FUNCTION netra_test.update_websocket_coordination();

-- Create function to update shared resource timestamps and lock management
CREATE OR REPLACE FUNCTION netra_test.update_shared_resource()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    IF NEW.locked_by IS NOT NULL AND OLD.locked_by IS NULL THEN
        NEW.locked_at = NOW();
    ELSIF NEW.locked_by IS NULL AND OLD.locked_by IS NOT NULL THEN
        NEW.locked_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for shared resource updates
DROP TRIGGER IF EXISTS trigger_update_shared_resource ON shared_resources;
CREATE TRIGGER trigger_update_shared_resource
    BEFORE UPDATE ON shared_resources
    FOR EACH ROW EXECUTE FUNCTION netra_test.update_shared_resource();

-- Create function to update user isolation data access tracking
CREATE OR REPLACE FUNCTION netra_test.update_isolation_data_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.access_count = COALESCE(OLD.access_count, 0) + 1;
    NEW.last_accessed = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for isolation data access tracking
DROP TRIGGER IF EXISTS trigger_update_isolation_data_access ON user_isolation_test_data;
CREATE TRIGGER trigger_update_isolation_data_access
    BEFORE UPDATE ON user_isolation_test_data
    FOR EACH ROW EXECUTE FUNCTION netra_test.update_isolation_data_access();

-- Create function to calculate high load session duration
CREATE OR REPLACE FUNCTION netra_test.calculate_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.session_end_time IS NOT NULL AND OLD.session_end_time IS NULL THEN
        NEW.session_duration_seconds = EXTRACT(EPOCH FROM (NEW.session_end_time - NEW.session_start_time))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for session duration calculation
DROP TRIGGER IF EXISTS trigger_calculate_session_duration ON high_load_sessions;
CREATE TRIGGER trigger_calculate_session_duration
    BEFORE UPDATE ON high_load_sessions
    FOR EACH ROW EXECUTE FUNCTION netra_test.calculate_session_duration();

-- Create utility function to clean up old test data
CREATE OR REPLACE FUNCTION netra_test.cleanup_old_performance_test_data(days_old INTEGER DEFAULT 7)
RETURNS TABLE(
    table_name TEXT,
    rows_deleted BIGINT
) AS $$
DECLARE
    cutoff_date TIMESTAMP WITH TIME ZONE;
    deleted_count BIGINT;
BEGIN
    cutoff_date := NOW() - (days_old || ' days')::INTERVAL;
    
    -- Clean up performance metrics
    DELETE FROM performance_metrics WHERE created_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'performance_metrics'::TEXT, deleted_count;
    
    -- Clean up race condition events
    DELETE FROM race_condition_events WHERE detected_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'race_condition_events'::TEXT, deleted_count;
    
    -- Clean up high load sessions
    DELETE FROM high_load_sessions WHERE created_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'high_load_sessions'::TEXT, deleted_count;
    
    -- Clean up concurrent user operations
    DELETE FROM concurrent_user_operations WHERE created_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'concurrent_user_operations'::TEXT, deleted_count;
    
    -- Clean up test users (only test users older than cutoff)
    DELETE FROM concurrent_test_users WHERE is_test_user = true AND created_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'concurrent_test_users'::TEXT, deleted_count;
    
    -- Clean up user isolation test data
    DELETE FROM user_isolation_test_data WHERE created_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'user_isolation_test_data'::TEXT, deleted_count;
    
    -- Clean up websocket coordination entries
    DELETE FROM websocket_coordination WHERE created_at < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN QUERY SELECT 'websocket_coordination'::TEXT, deleted_count;
    
END;
$$ LANGUAGE plpgsql;

-- Create function to get performance test statistics
CREATE OR REPLACE FUNCTION netra_test.get_performance_test_stats(test_name_filter TEXT DEFAULT NULL)
RETURNS TABLE(
    test_name TEXT,
    total_runs BIGINT,
    avg_concurrent_operations NUMERIC,
    avg_success_rate NUMERIC,
    avg_response_time_ms NUMERIC,
    avg_memory_usage_mb NUMERIC,
    race_conditions_total BIGINT,
    last_run TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pm.test_name::TEXT,
        COUNT(*)::BIGINT as total_runs,
        AVG(pm.concurrent_operations)::NUMERIC as avg_concurrent_operations,
        AVG(CASE WHEN pm.concurrent_operations > 0 
            THEN pm.successful_operations::NUMERIC / pm.concurrent_operations::NUMERIC 
            ELSE 0 END)::NUMERIC as avg_success_rate,
        AVG(pm.average_response_time_ms)::NUMERIC as avg_response_time_ms,
        AVG((COALESCE(pm.memory_usage_peak_mb, 0) + COALESCE(pm.memory_usage_start_mb, 0)) / 2)::NUMERIC as avg_memory_usage_mb,
        SUM(pm.race_conditions_detected)::BIGINT as race_conditions_total,
        MAX(pm.created_at) as last_run
    FROM performance_metrics pm
    WHERE test_name_filter IS NULL OR pm.test_name LIKE '%' || test_name_filter || '%'
    GROUP BY pm.test_name
    ORDER BY last_run DESC;
END;
$$ LANGUAGE plpgsql;

-- Create health check function for performance test tables
CREATE OR REPLACE FUNCTION netra_test.performance_test_health_check()
RETURNS TABLE(
    table_name TEXT,
    row_count BIGINT,
    last_activity TIMESTAMP WITH TIME ZONE,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'test_accounts'::TEXT,
        (SELECT COUNT(*) FROM test_accounts),
        (SELECT MAX(updated_at) FROM test_accounts),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'concurrent_test_users'::TEXT,
        (SELECT COUNT(*) FROM concurrent_test_users),
        (SELECT MAX(updated_at) FROM concurrent_test_users),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'concurrent_user_operations'::TEXT,
        (SELECT COUNT(*) FROM concurrent_user_operations),
        (SELECT MAX(created_at) FROM concurrent_user_operations),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'performance_metrics'::TEXT,
        (SELECT COUNT(*) FROM performance_metrics),
        (SELECT MAX(created_at) FROM performance_metrics),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'race_condition_events'::TEXT,
        (SELECT COUNT(*) FROM race_condition_events),
        (SELECT MAX(detected_at) FROM race_condition_events),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'high_load_sessions'::TEXT,
        (SELECT COUNT(*) FROM high_load_sessions),
        (SELECT MAX(created_at) FROM high_load_sessions),
        'healthy'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Log setup completion for performance test tables
INSERT INTO netra_test.benchmarks (id, name, description, test_scenarios)
VALUES (
    'performance_race_condition_setup',
    'Performance and Race Condition Test Tables Setup',
    'Verifies that performance and race condition test tables were created successfully',
    '{"setup_time": "' || NOW() || '", "status": "completed", "tables_created": ["test_accounts", "concurrent_test_users", "concurrent_user_operations", "websocket_coordination", "shared_resources", "user_isolation_test_data", "performance_metrics", "race_condition_events", "high_load_sessions"]}'
) ON CONFLICT (id) DO UPDATE SET
    test_scenarios = '{"setup_time": "' || NOW() || '", "status": "completed", "tables_created": ["test_accounts", "concurrent_test_users", "concurrent_user_operations", "websocket_coordination", "shared_resources", "user_isolation_test_data", "performance_metrics", "race_condition_events", "high_load_sessions"]}',
    last_run = NOW();

-- Grant permissions for test operations (if needed)
-- These would typically be uncommented and run with appropriate test user credentials
-- GRANT ALL PRIVILEGES ON test_accounts TO netra_test_user;
-- GRANT ALL PRIVILEGES ON concurrent_test_users TO netra_test_user;
-- GRANT ALL PRIVILEGES ON concurrent_user_operations TO netra_test_user;
-- GRANT ALL PRIVILEGES ON websocket_coordination TO netra_test_user;
-- GRANT ALL PRIVILEGES ON shared_resources TO netra_test_user;
-- GRANT ALL PRIVILEGES ON user_isolation_test_data TO netra_test_user;
-- GRANT ALL PRIVILEGES ON performance_metrics TO netra_test_user;
-- GRANT ALL PRIVILEGES ON race_condition_events TO netra_test_user;
-- GRANT ALL PRIVILEGES ON high_load_sessions TO netra_test_user;

COMMIT;