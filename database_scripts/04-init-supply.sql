-- Supply Research Tables
-- Purpose: Create AI supply research, model catalog, and research session tables
-- Module: Supply (adheres to 300-line limit)

-- Basic supplies table
CREATE TABLE IF NOT EXISTS supplies (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    name VARCHAR NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for supplies
CREATE INDEX idx_supplies_name ON supplies(name);
CREATE INDEX idx_supplies_created_at ON supplies(created_at);

-- Supply options table
CREATE TABLE IF NOT EXISTS supply_options (
    id SERIAL PRIMARY KEY,
    provider VARCHAR NOT NULL,
    family VARCHAR NOT NULL,
    name VARCHAR NOT NULL UNIQUE,
    hosting_type VARCHAR DEFAULT 'api_provider',
    cost_per_million_tokens_usd JSON NOT NULL,
    quality_score FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for supply options
CREATE INDEX idx_supply_options_name ON supply_options(name);
CREATE INDEX idx_supply_options_provider ON supply_options(provider);
CREATE INDEX idx_supply_options_family ON supply_options(family);

-- AI Supply Items table for detailed model information
CREATE TABLE IF NOT EXISTS ai_supply_items (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    provider VARCHAR NOT NULL,
    model_name VARCHAR NOT NULL,
    model_version VARCHAR,
    pricing_input NUMERIC(10, 4),
    pricing_output NUMERIC(10, 4),
    pricing_currency VARCHAR DEFAULT 'USD',
    context_window INTEGER,
    max_output_tokens INTEGER,
    capabilities JSON,
    availability_status VARCHAR DEFAULT 'available',
    api_endpoints JSON,
    performance_metrics JSON,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    research_source VARCHAR,
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for AI supply items
CREATE INDEX idx_ai_supply_items_provider ON ai_supply_items(provider);
CREATE INDEX idx_ai_supply_items_model_name ON ai_supply_items(model_name);
CREATE INDEX idx_ai_supply_items_availability ON ai_supply_items(availability_status);
CREATE INDEX idx_ai_supply_items_created_at ON ai_supply_items(created_at);

-- Research sessions table
CREATE TABLE IF NOT EXISTS research_sessions (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    query TEXT NOT NULL,
    session_id VARCHAR,
    status VARCHAR DEFAULT 'pending',
    research_plan JSON,
    questions_answered JSON,
    raw_results JSON,
    processed_data JSON,
    citations JSON,
    initiated_by VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Create indexes for research sessions
CREATE INDEX idx_research_sessions_status ON research_sessions(status);
CREATE INDEX idx_research_sessions_initiated_by ON research_sessions(initiated_by);
CREATE INDEX idx_research_sessions_created_at ON research_sessions(created_at);

-- Supply update logs table
CREATE TABLE IF NOT EXISTS supply_update_logs (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    supply_item_id VARCHAR NOT NULL REFERENCES ai_supply_items(id) ON DELETE CASCADE,
    field_updated VARCHAR NOT NULL,
    old_value JSON,
    new_value JSON,
    research_session_id VARCHAR REFERENCES research_sessions(id) ON DELETE SET NULL,
    update_reason VARCHAR,
    updated_by VARCHAR NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for supply update logs
CREATE INDEX idx_supply_update_logs_supply_item_id ON supply_update_logs(supply_item_id);
CREATE INDEX idx_supply_update_logs_research_session_id ON supply_update_logs(research_session_id);
CREATE INDEX idx_supply_update_logs_updated_by ON supply_update_logs(updated_by);
CREATE INDEX idx_supply_update_logs_updated_at ON supply_update_logs(updated_at);

-- Add update triggers for updated_at columns
CREATE TRIGGER update_supplies_updated_at BEFORE UPDATE
    ON supplies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supply_options_updated_at BEFORE UPDATE
    ON supply_options FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo 'Supply research tables created successfully'