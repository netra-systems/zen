-- Create missing tables for staging environment
-- This fixes the immediate 503 issue by creating tables that migration failed to create

-- Create agent_executions table
CREATE TABLE IF NOT EXISTS agent_executions (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    input_data JSON,
    output_data JSON,
    error_message TEXT,
    tokens_used INTEGER,
    api_calls_made INTEGER,
    cost_cents INTEGER,
    thread_id VARCHAR(50),
    workflow_id VARCHAR(50),
    execution_context JSON,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create indexes for agent_executions
CREATE INDEX IF NOT EXISTS ix_agent_executions_agent_id ON agent_executions(agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_status ON agent_executions(status);
CREATE INDEX IF NOT EXISTS ix_agent_executions_thread_id ON agent_executions(thread_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_user_id ON agent_executions(user_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_workflow_id ON agent_executions(workflow_id);

-- Create credit_transactions table  
CREATE TABLE IF NOT EXISTS credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    amount FLOAT NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    plan_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Ensure alembic version is set correctly
INSERT INTO alembic_version (version_num) VALUES ('882759db46ce') 
ON CONFLICT (version_num) DO NOTHING;