-- Staging Database Initialization Script
-- Initializes PostgreSQL database for staging environment
-- CRITICAL: Must support request isolation patterns

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS netra_staging;

-- Connect to staging database
\c netra_staging;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas for service separation
CREATE SCHEMA IF NOT EXISTS backend;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set default schema search path
ALTER DATABASE netra_staging SET search_path TO backend, auth, analytics, public;

-- Users table (auth schema)
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- User sessions table (auth schema) - CRITICAL for request isolation
CREATE TABLE IF NOT EXISTS auth.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Threads table (backend schema) - CRITICAL for user isolation
CREATE TABLE IF NOT EXISTS backend.threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE
);

-- Messages table (backend schema)  
CREATE TABLE IF NOT EXISTS backend.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES backend.threads(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'user', -- 'user', 'assistant', 'system'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Agent executions table (backend schema) - CRITICAL for isolation tracking
CREATE TABLE IF NOT EXISTS backend.agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES backend.threads(id) ON DELETE CASCADE,
    agent_type VARCHAR(100) NOT NULL,
    agent_instance_id UUID NOT NULL, -- Unique per execution for isolation
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result_data JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Isolation tracking fields
    memory_usage_mb INTEGER,
    execution_time_ms INTEGER,
    cleanup_completed BOOLEAN DEFAULT FALSE
);

-- Request isolation metrics (analytics schema)
CREATE TABLE IF NOT EXISTS analytics.request_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    memory_usage_mb INTEGER,
    cpu_usage_percent DECIMAL(5,2),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance and isolation queries
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON auth.users(created_at);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON auth.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON auth.user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON auth.user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_threads_user_id ON backend.threads(user_id);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON backend.threads(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON backend.messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON backend.messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON backend.messages(created_at);

-- CRITICAL: Indexes for request isolation monitoring
CREATE INDEX IF NOT EXISTS idx_agent_executions_user_id ON backend.agent_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_instance_id ON backend.agent_executions(agent_instance_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_status ON backend.agent_executions(status);
CREATE INDEX IF NOT EXISTS idx_agent_executions_started_at ON backend.agent_executions(started_at);

CREATE INDEX IF NOT EXISTS idx_request_metrics_user_id ON analytics.request_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_request_metrics_timestamp ON analytics.request_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_request_metrics_endpoint ON analytics.request_metrics(endpoint);

-- Functions for request isolation monitoring
CREATE OR REPLACE FUNCTION analytics.get_concurrent_requests(
    time_window_minutes INTEGER DEFAULT 5
) RETURNS TABLE (
    concurrent_requests BIGINT,
    avg_response_time NUMERIC,
    error_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as concurrent_requests,
        AVG(response_time_ms) as avg_response_time,
        (COUNT(*) FILTER (WHERE status_code >= 400) * 100.0 / COUNT(*)) as error_rate
    FROM analytics.request_metrics
    WHERE timestamp > NOW() - (time_window_minutes || ' minutes')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Function to check for request isolation violations
CREATE OR REPLACE FUNCTION backend.check_isolation_violations(
    time_window_minutes INTEGER DEFAULT 10
) RETURNS TABLE (
    user_id UUID,
    agent_instance_id UUID,
    violation_type TEXT,
    violation_count BIGINT
) AS $$
BEGIN
    -- Check for agent instances shared between users (CRITICAL violation)
    RETURN QUERY
    SELECT 
        ae1.user_id,
        ae1.agent_instance_id,
        'shared_agent_instance' as violation_type,
        COUNT(*) as violation_count
    FROM backend.agent_executions ae1
    JOIN backend.agent_executions ae2 ON ae1.agent_instance_id = ae2.agent_instance_id
    WHERE ae1.user_id != ae2.user_id
        AND ae1.started_at > NOW() - (time_window_minutes || ' minutes')::INTERVAL
        AND ae2.started_at > NOW() - (time_window_minutes || ' minutes')::INTERVAL
    GROUP BY ae1.user_id, ae1.agent_instance_id;

    -- Check for sessions without proper cleanup
    RETURN QUERY
    SELECT 
        user_id,
        NULL::UUID as agent_instance_id,
        'uncleaned_session' as violation_type,
        COUNT(*) as violation_count
    FROM auth.user_sessions
    WHERE expires_at < NOW()
        AND is_active = TRUE
        AND last_accessed < NOW() - (time_window_minutes || ' minutes')::INTERVAL
    GROUP BY user_id;
END;
$$ LANGUAGE plpgsql;

-- Create staging test user for validation
INSERT INTO auth.users (id, email, username, is_active, is_verified, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'staging-test@example.com',
    'staging_test',
    TRUE,
    TRUE,
    '{"role": "test_user", "environment": "staging", "created_by": "staging_init_script"}'::jsonb
) ON CONFLICT (email) DO NOTHING;

-- Create sample thread for testing
INSERT INTO backend.threads (id, user_id, title, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'Staging Test Thread',
    '{"purpose": "staging_validation", "auto_created": true}'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- Update table statistics for query optimization
ANALYZE auth.users;
ANALYZE auth.user_sessions;
ANALYZE backend.threads;
ANALYZE backend.messages;
ANALYZE backend.agent_executions;
ANALYZE analytics.request_metrics;

-- Set up row-level security (optional for staging, required for production)
-- ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE backend.threads ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE backend.messages ENABLE ROW LEVEL SECURITY;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA backend TO netra_staging;
GRANT USAGE ON SCHEMA auth TO netra_staging;
GRANT USAGE ON SCHEMA analytics TO netra_staging;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA backend TO netra_staging;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO netra_staging;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO netra_staging;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA backend TO netra_staging;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO netra_staging;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO netra_staging;

-- Create monitoring views for staging validation
CREATE OR REPLACE VIEW analytics.staging_health AS
SELECT 
    'database_connections' as metric,
    COUNT(*) as value,
    NOW() as timestamp
FROM pg_stat_activity
WHERE datname = 'netra_staging'

UNION ALL

SELECT 
    'active_sessions' as metric,
    COUNT(*) as value,
    NOW() as timestamp
FROM auth.user_sessions
WHERE is_active = TRUE AND expires_at > NOW()

UNION ALL

SELECT 
    'active_threads' as metric,
    COUNT(*) as value,
    NOW() as timestamp
FROM backend.threads
WHERE is_active = TRUE

UNION ALL

SELECT 
    'running_agents' as metric,
    COUNT(*) as value,
    NOW() as timestamp
FROM backend.agent_executions
WHERE status IN ('pending', 'running');

-- Log successful initialization
INSERT INTO analytics.request_metrics (
    request_id,
    endpoint,
    method,
    status_code,
    response_time_ms,
    metadata
) VALUES (
    uuid_generate_v4(),
    '/database/init',
    'POST',
    200,
    0,
    '{"event": "staging_database_initialized", "timestamp": "' || NOW()::text || '"}'::jsonb
);

-- Final validation query
SELECT 
    'Staging database initialization completed successfully' as status,
    NOW() as timestamp,
    (SELECT COUNT(*) FROM auth.users) as total_users,
    (SELECT COUNT(*) FROM backend.threads) as total_threads;