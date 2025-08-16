-- Agent and Assistant Tables
-- Purpose: Create AI agent, assistant, thread, and message related tables
-- Module: Agents (adheres to 300-line limit)

-- Assistants table
CREATE TABLE IF NOT EXISTS assistants (
    id VARCHAR PRIMARY KEY,
    object VARCHAR NOT NULL DEFAULT 'assistant',
    created_at INTEGER NOT NULL,
    name VARCHAR,
    description VARCHAR,
    model VARCHAR NOT NULL,
    instructions VARCHAR,
    tools JSON NOT NULL DEFAULT '[]',
    file_ids VARCHAR[] NOT NULL DEFAULT '{}',
    metadata_ JSON
);

-- Create indexes for assistants
CREATE INDEX idx_assistants_created_at ON assistants(created_at);
CREATE INDEX idx_assistants_model ON assistants(model);

-- Threads table for conversation contexts
CREATE TABLE IF NOT EXISTS threads (
    id VARCHAR PRIMARY KEY,
    object VARCHAR NOT NULL DEFAULT 'thread',
    created_at INTEGER NOT NULL,
    metadata_ JSON
);

-- Create indexes for threads
CREATE INDEX idx_threads_created_at ON threads(created_at);

-- Runs table for execution tracking
CREATE TABLE IF NOT EXISTS runs (
    id VARCHAR PRIMARY KEY,
    object VARCHAR NOT NULL DEFAULT 'thread.run',
    created_at INTEGER NOT NULL,
    thread_id VARCHAR NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    assistant_id VARCHAR NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    status VARCHAR NOT NULL,
    required_action JSON,
    last_error JSON,
    expires_at INTEGER,
    started_at INTEGER,
    cancelled_at INTEGER,
    failed_at INTEGER,
    completed_at INTEGER,
    model VARCHAR,
    instructions VARCHAR,
    tools JSON NOT NULL DEFAULT '[]',
    file_ids VARCHAR[] NOT NULL DEFAULT '{}',
    metadata_ JSON
);

-- Create indexes for runs
CREATE INDEX idx_runs_thread_id ON runs(thread_id);
CREATE INDEX idx_runs_assistant_id ON runs(assistant_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_created_at ON runs(created_at);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR PRIMARY KEY,
    object VARCHAR NOT NULL DEFAULT 'thread.message',
    created_at INTEGER NOT NULL,
    thread_id VARCHAR NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL,
    content JSON NOT NULL,
    assistant_id VARCHAR REFERENCES assistants(id) ON DELETE SET NULL,
    run_id VARCHAR REFERENCES runs(id) ON DELETE SET NULL,
    file_ids VARCHAR[] NOT NULL DEFAULT '{}',
    metadata_ JSON
);

-- Create indexes for messages
CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_assistant_id ON messages(assistant_id);
CREATE INDEX idx_messages_run_id ON messages(run_id);
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Steps table for run step tracking
CREATE TABLE IF NOT EXISTS steps (
    id VARCHAR PRIMARY KEY,
    object VARCHAR NOT NULL DEFAULT 'thread.run.step',
    created_at INTEGER NOT NULL,
    run_id VARCHAR NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    assistant_id VARCHAR NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    thread_id VARCHAR NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    step_details JSON NOT NULL,
    last_error JSON,
    expired_at INTEGER,
    cancelled_at INTEGER,
    failed_at INTEGER,
    completed_at INTEGER,
    metadata_ JSON
);

-- Create indexes for steps
CREATE INDEX idx_steps_run_id ON steps(run_id);
CREATE INDEX idx_steps_assistant_id ON steps(assistant_id);
CREATE INDEX idx_steps_thread_id ON steps(thread_id);
CREATE INDEX idx_steps_type ON steps(type);
CREATE INDEX idx_steps_status ON steps(status);
CREATE INDEX idx_steps_created_at ON steps(created_at);

-- Apex Optimizer Agent run tracking
CREATE TABLE IF NOT EXISTS apex_optimizer_agent_runs (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    run_id VARCHAR NOT NULL,
    step_name VARCHAR NOT NULL,
    step_input JSON,
    step_output JSON,
    run_log VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for apex optimizer runs
CREATE INDEX idx_apex_optimizer_runs_run_id ON apex_optimizer_agent_runs(run_id);
CREATE INDEX idx_apex_optimizer_runs_timestamp ON apex_optimizer_agent_runs(timestamp);

-- Apex Optimizer Agent run reports
CREATE TABLE IF NOT EXISTS apex_optimizer_agent_run_reports (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    run_id VARCHAR NOT NULL UNIQUE,
    report VARCHAR NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for apex optimizer reports
CREATE INDEX idx_apex_optimizer_reports_run_id ON apex_optimizer_agent_run_reports(run_id);
CREATE INDEX idx_apex_optimizer_reports_timestamp ON apex_optimizer_agent_run_reports(timestamp);

\echo 'Agent and assistant tables created successfully'