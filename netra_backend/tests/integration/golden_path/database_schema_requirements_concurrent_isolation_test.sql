-- Database Schema Requirements for Concurrent Agent Transaction Isolation Test
-- File: test_database_transaction_isolation_concurrent_agents.py
--
-- This SQL file defines the required database tables and indexes needed
-- to run the comprehensive transaction isolation tests.
--
-- CRITICAL: These tables are required for testing PostgreSQL ACID properties
-- and transaction isolation during concurrent agent executions.

-- =============================================================================
-- Core User and Thread Management Tables
-- =============================================================================

-- Users table (if not exists)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Threads table (if not exists)
CREATE TABLE IF NOT EXISTS threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent execution results table
CREATE TABLE IF NOT EXISTS agent_execution_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    run_id UUID NOT NULL,
    message_data JSONB,
    result_data JSONB,
    execution_time DECIMAL(10,6),
    success BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Thread messages table
CREATE TABLE IF NOT EXISTS thread_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    message_content TEXT NOT NULL,
    agent_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent execution states for recovery testing
CREATE TABLE IF NOT EXISTS agent_execution_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Transaction Isolation Test Tables
-- =============================================================================

-- Shared resources table for deadlock testing
CREATE TABLE IF NOT EXISTS shared_resources (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cached resources table for cache-database consistency testing
CREATE TABLE IF NOT EXISTS cached_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Concurrent test data table for isolation level testing
CREATE TABLE IF NOT EXISTS concurrent_test_data (
    id VARCHAR(100) PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Phantom read test table for SERIALIZABLE isolation testing
CREATE TABLE IF NOT EXISTS phantom_read_test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(100) NOT NULL,
    record_index INTEGER NOT NULL,
    value VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Indexes for Performance and Concurrency Testing
-- =============================================================================

-- Performance indexes for user and thread lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
CREATE INDEX IF NOT EXISTS idx_threads_active ON threads(is_active) WHERE is_active = true;

-- Performance indexes for agent execution queries
CREATE INDEX IF NOT EXISTS idx_agent_execution_results_user_thread 
    ON agent_execution_results(user_id, thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_execution_results_agent_id 
    ON agent_execution_results(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_execution_results_success 
    ON agent_execution_results(success);

-- Performance indexes for thread messages
CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_id 
    ON thread_messages(thread_id, created_at);

-- Performance indexes for execution states
CREATE INDEX IF NOT EXISTS idx_agent_execution_states_execution_id 
    ON agent_execution_states(execution_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_execution_states_user_thread 
    ON agent_execution_states(user_id, thread_id);

-- Indexes for transaction isolation test tables
CREATE INDEX IF NOT EXISTS idx_shared_resources_name ON shared_resources(name);
CREATE INDEX IF NOT EXISTS idx_cached_resources_key ON cached_resources(key);
CREATE INDEX IF NOT EXISTS idx_concurrent_test_data_value ON concurrent_test_data(value);
CREATE INDEX IF NOT EXISTS idx_phantom_read_test_dataset 
    ON phantom_read_test(dataset_id, record_index);

-- =============================================================================
-- Table Constraints and Data Integrity
-- =============================================================================

-- Add unique constraints for data integrity
ALTER TABLE agent_execution_states 
    ADD CONSTRAINT unique_execution_user_thread_agent 
    UNIQUE (execution_id, user_id, thread_id, agent_id, created_at);

-- Add check constraints for data validation
ALTER TABLE concurrent_test_data 
    ADD CONSTRAINT check_positive_version 
    CHECK (version > 0);

ALTER TABLE shared_resources 
    ADD CONSTRAINT check_non_negative_value 
    CHECK (value >= 0);

-- =============================================================================
-- Functions for Transaction Testing
-- =============================================================================

-- Function to simulate processing delay in transactions
CREATE OR REPLACE FUNCTION simulate_processing_delay(delay_seconds DECIMAL DEFAULT 0.1) 
RETURNS VOID AS $$
BEGIN
    PERFORM pg_sleep(delay_seconds);
END;
$$ LANGUAGE plpgsql;

-- Function to get current transaction isolation level
CREATE OR REPLACE FUNCTION get_transaction_isolation_level() 
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('transaction_isolation');
END;
$$ LANGUAGE plpgsql;

-- Function to check for active locks (for deadlock analysis)
CREATE OR REPLACE FUNCTION get_active_locks() 
RETURNS TABLE(
    locktype TEXT,
    database_name TEXT,
    relation_name TEXT,
    mode TEXT,
    granted BOOLEAN,
    pid INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.locktype::TEXT,
        d.datname::TEXT as database_name,
        COALESCE(c.relname, 'N/A')::TEXT as relation_name,
        l.mode::TEXT,
        l.granted,
        l.pid
    FROM pg_locks l
    LEFT JOIN pg_database d ON l.database = d.oid
    LEFT JOIN pg_class c ON l.relation = c.oid
    WHERE l.pid != pg_backend_pid()  -- Exclude current session
    ORDER BY l.granted, l.pid;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Test Data Cleanup Procedures
-- =============================================================================

-- Procedure to clean up test data (use with caution)
CREATE OR REPLACE FUNCTION cleanup_concurrent_isolation_test_data() 
RETURNS VOID AS $$
BEGIN
    -- Clean up in reverse dependency order
    DELETE FROM agent_execution_states WHERE execution_id LIKE '%test%';
    DELETE FROM thread_messages WHERE message_content LIKE '%test%' OR message_content LIKE '%should be rolled back%';
    DELETE FROM agent_execution_results WHERE agent_id LIKE '%test%';
    DELETE FROM phantom_read_test WHERE dataset_id LIKE '%test%';
    DELETE FROM concurrent_test_data WHERE id LIKE '%test%';
    DELETE FROM cached_resources WHERE key LIKE '%test%';
    DELETE FROM shared_resources WHERE id LIKE '%test%';
    DELETE FROM threads WHERE title LIKE '%test%';
    DELETE FROM users WHERE email LIKE '%test%';
    
    -- Reset sequences if needed
    -- This ensures clean state between test runs
    RAISE NOTICE 'Concurrent isolation test data cleaned up successfully';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Performance and Monitoring Views
-- =============================================================================

-- View for monitoring concurrent transaction performance
CREATE OR REPLACE VIEW concurrent_transaction_metrics AS
SELECT 
    DATE_TRUNC('minute', created_at) as time_bucket,
    COUNT(*) as total_executions,
    COUNT(*) FILTER (WHERE success = true) as successful_executions,
    COUNT(*) FILTER (WHERE success = false) as failed_executions,
    AVG(execution_time) as avg_execution_time,
    MAX(execution_time) as max_execution_time,
    COUNT(DISTINCT user_id) as concurrent_users,
    COUNT(DISTINCT agent_id) as agents_used
FROM agent_execution_results 
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', created_at)
ORDER BY time_bucket DESC;

-- View for deadlock and conflict analysis
CREATE OR REPLACE VIEW transaction_conflict_analysis AS
SELECT 
    agent_id,
    COUNT(*) as total_attempts,
    COUNT(*) FILTER (WHERE success = true) as successes,
    COUNT(*) FILTER (WHERE success = false) as failures,
    (COUNT(*) FILTER (WHERE success = false)::FLOAT / COUNT(*)::FLOAT * 100) as failure_rate_percent,
    AVG(execution_time) as avg_execution_time
FROM agent_execution_results 
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY agent_id
ORDER BY failure_rate_percent DESC;

-- =============================================================================
-- Database Configuration for Optimal Concurrency Testing
-- =============================================================================

-- Set recommended PostgreSQL settings for concurrency testing
-- (These would typically be set in postgresql.conf)

-- Enable detailed logging of deadlocks for analysis
-- log_lock_waits = on
-- deadlock_timeout = 1s
-- log_statement = 'all'  -- Use carefully, only for testing

-- Optimize for concurrent transactions
-- max_connections = 100
-- shared_buffers = 256MB
-- effective_cache_size = 1GB
-- work_mem = 4MB
-- maintenance_work_mem = 64MB

-- Enable transaction isolation level monitoring
-- log_min_duration_statement = 100  -- Log slow queries

-- =============================================================================
-- Comments and Documentation
-- =============================================================================

COMMENT ON TABLE users IS 'Core user table for authentication and user context isolation testing';
COMMENT ON TABLE threads IS 'Thread management table for conversation context and multi-user isolation';
COMMENT ON TABLE agent_execution_results IS 'Results of agent executions with transaction metadata';
COMMENT ON TABLE agent_execution_states IS 'Intermediate states for agent execution recovery testing';
COMMENT ON TABLE shared_resources IS 'Shared resources for deadlock and contention testing';
COMMENT ON TABLE cached_resources IS 'Resources with both database and cache storage for consistency testing';
COMMENT ON TABLE concurrent_test_data IS 'Data table for testing various transaction isolation levels';
COMMENT ON TABLE phantom_read_test IS 'Dataset for testing phantom read prevention under SERIALIZABLE isolation';

COMMENT ON FUNCTION simulate_processing_delay(DECIMAL) IS 'Simulates processing delay to increase concurrency conflicts';
COMMENT ON FUNCTION get_transaction_isolation_level() IS 'Returns current transaction isolation level for validation';
COMMENT ON FUNCTION get_active_locks() IS 'Returns active database locks for deadlock analysis';
COMMENT ON FUNCTION cleanup_concurrent_isolation_test_data() IS 'Cleans up test data - use with caution';

COMMENT ON VIEW concurrent_transaction_metrics IS 'Performance metrics for concurrent transaction analysis';
COMMENT ON VIEW transaction_conflict_analysis IS 'Analysis of transaction conflicts and failure rates by agent type';

-- =============================================================================
-- Usage Instructions
-- =============================================================================

/*
To set up the database for concurrent isolation testing:

1. Run this entire SQL file against your PostgreSQL test database:
   psql -d netra_test -f database_schema_requirements_concurrent_isolation_test.sql

2. Verify tables were created:
   \dt

3. Check that indexes were created:
   \di

4. Verify functions were created:
   \df

5. Run the test:
   python tests/unified_test_runner.py --test-file netra_backend/tests/integration/golden_path/test_database_transaction_isolation_concurrent_agents.py --real-services

6. Clean up after testing (optional):
   SELECT cleanup_concurrent_isolation_test_data();

7. Monitor test performance:
   SELECT * FROM concurrent_transaction_metrics;
   SELECT * FROM transaction_conflict_analysis;
*/