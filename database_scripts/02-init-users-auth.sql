-- User and Authentication Tables
-- Purpose: Create user management and authentication related tables
-- Module: Users & Auth (adheres to 450-line limit)

-- Main user table (using 'userbase' to match SQLAlchemy models)
CREATE TABLE IF NOT EXISTS userbase (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    email VARCHAR NOT NULL UNIQUE,
    full_name VARCHAR,
    hashed_password VARCHAR,
    picture VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    
    -- Admin permission fields
    role VARCHAR DEFAULT 'standard_user',
    permissions JSON DEFAULT '{}',
    is_developer BOOLEAN DEFAULT false,
    
    -- Plan and tool permission fields
    plan_tier VARCHAR DEFAULT 'free',
    plan_expires_at TIMESTAMP WITH TIME ZONE,
    feature_flags JSON DEFAULT '{}',
    tool_permissions JSON DEFAULT '{}',
    
    -- Plan billing fields
    plan_started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    auto_renew BOOLEAN DEFAULT false,
    payment_status VARCHAR DEFAULT 'active',
    trial_period BOOLEAN DEFAULT false
);

-- Create indexes for user table
CREATE INDEX idx_userbase_email ON userbase(email);
CREATE INDEX idx_userbase_full_name ON userbase(full_name);
CREATE INDEX idx_userbase_role ON userbase(role);
CREATE INDEX idx_userbase_plan_tier ON userbase(plan_tier);
CREATE INDEX idx_userbase_is_active ON userbase(is_active);
CREATE INDEX idx_userbase_created_at ON userbase(created_at);

-- Secrets table for encrypted user credentials
CREATE TABLE IF NOT EXISTS secrets (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    user_id VARCHAR NOT NULL REFERENCES userbase(id) ON DELETE CASCADE,
    key VARCHAR NOT NULL,
    encrypted_value VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for secrets table
CREATE INDEX idx_secrets_user_id ON secrets(user_id);
CREATE INDEX idx_secrets_key ON secrets(key);
CREATE UNIQUE INDEX idx_secrets_user_key ON secrets(user_id, key);

-- Tool usage logging table
CREATE TABLE IF NOT EXISTS tool_usage_logs (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    user_id VARCHAR NOT NULL REFERENCES userbase(id) ON DELETE CASCADE,
    tool_name VARCHAR NOT NULL,
    category VARCHAR,
    execution_time_ms INTEGER DEFAULT 0,
    tokens_used INTEGER,
    cost_cents INTEGER,
    status VARCHAR NOT NULL,
    plan_tier VARCHAR NOT NULL,
    permission_check_result JSON,
    arguments JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for tool usage logs
CREATE INDEX idx_tool_usage_logs_user_id ON tool_usage_logs(user_id);
CREATE INDEX idx_tool_usage_logs_tool_name ON tool_usage_logs(tool_name);
CREATE INDEX idx_tool_usage_logs_category ON tool_usage_logs(category);
CREATE INDEX idx_tool_usage_logs_status ON tool_usage_logs(status);
CREATE INDEX idx_tool_usage_logs_created_at ON tool_usage_logs(created_at);
CREATE INDEX idx_tool_usage_logs_plan_tier ON tool_usage_logs(plan_tier);

-- Add update trigger for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_userbase_updated_at BEFORE UPDATE
    ON userbase FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_secrets_updated_at BEFORE UPDATE
    ON secrets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo 'User and authentication tables created successfully'