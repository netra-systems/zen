-- Setup script for dedicated test environment database
-- Creates test schema and tables for isolated real LLM testing

-- Create test database schema
CREATE SCHEMA IF NOT EXISTS netra_test;

-- Set search path to test schema
SET search_path = netra_test, public;

-- Create test users table
CREATE TABLE IF NOT EXISTS netra_test.users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    permissions TEXT[] DEFAULT '{}',
    tier VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create test threads table
CREATE TABLE IF NOT EXISTS netra_test.threads (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES netra_test.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    optimization_focus VARCHAR(100),
    metadata JSONB DEFAULT '{}'
);

-- Create test messages table
CREATE TABLE IF NOT EXISTS netra_test.messages (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) REFERENCES netra_test.threads(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    tokens_used INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    cost DECIMAL(10, 4) DEFAULT 0.0000
);

-- Create test metrics table for performance tracking
CREATE TABLE IF NOT EXISTS netra_test.metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 2) DEFAULT 0.00,
    avg_response_time_ms INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    model_usage JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create test models table for tracking available models
CREATE TABLE IF NOT EXISTS netra_test.models (
    id VARCHAR(100) PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    cost_per_1k_tokens DECIMAL(8, 6) NOT NULL,
    avg_response_time_ms INTEGER DEFAULT 0,
    performance_rating VARCHAR(20) DEFAULT 'medium',
    use_cases TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create test corpus entries table
CREATE TABLE IF NOT EXISTS netra_test.corpus_entries (
    id VARCHAR(255) PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    quality_score DECIMAL(3, 2) DEFAULT 0.00,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usage_count INTEGER DEFAULT 0,
    effectiveness_rating VARCHAR(20) DEFAULT 'medium'
);

-- Create test supply chain configurations table
CREATE TABLE IF NOT EXISTS netra_test.supply_chain_configs (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    configuration JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create test cache entries table for KV cache simulation
CREATE TABLE IF NOT EXISTS netra_test.cache_entries (
    id VARCHAR(255) PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    cache_key VARCHAR(500) NOT NULL,
    cache_value JSONB NOT NULL,
    ttl INTEGER DEFAULT 3600, -- TTL in seconds
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Create test benchmarks table
CREATE TABLE IF NOT EXISTS netra_test.benchmarks (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    test_scenarios JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_run TIMESTAMP WITH TIME ZONE,
    results JSONB DEFAULT '{}'
);

-- Create test workflow templates table
CREATE TABLE IF NOT EXISTS netra_test.workflow_templates (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,
    estimated_duration_ms INTEGER DEFAULT 0,
    success_rate DECIMAL(3, 2) DEFAULT 0.00,
    average_cost DECIMAL(10, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_test_threads_user_id ON netra_test.threads(user_id);
CREATE INDEX IF NOT EXISTS idx_test_threads_status ON netra_test.threads(status);
CREATE INDEX IF NOT EXISTS idx_test_messages_thread_id ON netra_test.messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_test_messages_created_at ON netra_test.messages(created_at);
CREATE INDEX IF NOT EXISTS idx_test_metrics_date ON netra_test.metrics(date);
CREATE INDEX IF NOT EXISTS idx_test_cache_entries_category ON netra_test.cache_entries(category);
CREATE INDEX IF NOT EXISTS idx_test_cache_entries_expires_at ON netra_test.cache_entries(expires_at);
CREATE INDEX IF NOT EXISTS idx_test_corpus_category ON netra_test.corpus_entries(category);
CREATE INDEX IF NOT EXISTS idx_test_supply_chain_active ON netra_test.supply_chain_configs(is_active);

-- Create function to automatically update expires_at based on TTL
CREATE OR REPLACE FUNCTION netra_test.update_cache_expiry()
RETURNS TRIGGER AS $$
BEGIN
    NEW.expires_at = NEW.created_at + (NEW.ttl * interval '1 second');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically set expiry time for cache entries
DROP TRIGGER IF EXISTS trigger_update_cache_expiry ON netra_test.cache_entries;
CREATE TRIGGER trigger_update_cache_expiry
    BEFORE INSERT OR UPDATE ON netra_test.cache_entries
    FOR EACH ROW EXECUTE FUNCTION netra_test.update_cache_expiry();

-- Create function to update last_accessed time
CREATE OR REPLACE FUNCTION netra_test.update_cache_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = NOW();
    NEW.hit_count = COALESCE(OLD.hit_count, 0) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up expired cache entries
CREATE OR REPLACE FUNCTION netra_test.cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM netra_test.cache_entries WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions for test user (assuming test database user exists)
-- GRANT ALL PRIVILEGES ON SCHEMA netra_test TO netra_test_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA netra_test TO netra_test_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA netra_test TO netra_test_user;

-- Log setup completion
INSERT INTO netra_test.benchmarks (id, name, description, test_scenarios)
VALUES (
    'setup_verification',
    'Database Setup Verification',
    'Verifies that test database setup completed successfully',
    '{"setup_time": "' || NOW() || '", "status": "completed"}'
) ON CONFLICT (id) DO UPDATE SET
    test_scenarios = '{"setup_time": "' || NOW() || '", "status": "completed"}',
    last_run = NOW();

-- Create a health check function
CREATE OR REPLACE FUNCTION netra_test.health_check()
RETURNS TABLE(
    table_name TEXT,
    row_count BIGINT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'users'::TEXT,
        (SELECT COUNT(*) FROM netra_test.users),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'threads'::TEXT,
        (SELECT COUNT(*) FROM netra_test.threads),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'messages'::TEXT,
        (SELECT COUNT(*) FROM netra_test.messages),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'metrics'::TEXT,
        (SELECT COUNT(*) FROM netra_test.metrics),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'models'::TEXT,
        (SELECT COUNT(*) FROM netra_test.models),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'corpus_entries'::TEXT,
        (SELECT COUNT(*) FROM netra_test.corpus_entries),
        'healthy'::TEXT
    UNION ALL
    SELECT 
        'cache_entries'::TEXT,
        (SELECT COUNT(*) FROM netra_test.cache_entries WHERE expires_at > NOW()),
        'healthy'::TEXT;
END;
$$ LANGUAGE plpgsql;