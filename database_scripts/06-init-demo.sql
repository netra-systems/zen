-- Demo Tables
-- Purpose: Create demo-related tables for enterprise demonstrations
-- Module: Demo (adheres to 450-line limit)

-- Demo sessions table
CREATE TABLE IF NOT EXISTS demo_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR REFERENCES userbase(id) ON DELETE SET NULL,
    industry VARCHAR(50) NOT NULL,
    company_name VARCHAR(255),
    company_size VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    progress_percentage FLOAT NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for demo sessions
CREATE INDEX idx_demo_sessions_user_id ON demo_sessions(user_id);
CREATE INDEX idx_demo_sessions_industry ON demo_sessions(industry);
CREATE INDEX idx_demo_sessions_status ON demo_sessions(status);
CREATE INDEX idx_demo_sessions_started_at ON demo_sessions(started_at);

-- Demo interactions table
CREATE TABLE IF NOT EXISTS demo_interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    message TEXT,
    response TEXT,
    agents_involved VARCHAR[],
    metrics JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER
);

-- Create indexes for demo interactions
CREATE INDEX idx_demo_interactions_session_id ON demo_interactions(session_id);
CREATE INDEX idx_demo_interactions_type ON demo_interactions(interaction_type);
CREATE INDEX idx_demo_interactions_timestamp ON demo_interactions(timestamp);

-- Demo scenarios table
CREATE TABLE IF NOT EXISTS demo_scenarios (
    id SERIAL PRIMARY KEY,
    industry VARCHAR(50) NOT NULL,
    scenario_name VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    optimization_scenarios JSONB,
    typical_metrics JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_demo_scenarios_industry_name UNIQUE(industry, scenario_name)
);

-- Create indexes for demo scenarios
CREATE INDEX idx_demo_scenarios_industry ON demo_scenarios(industry);
CREATE INDEX idx_demo_scenarios_active ON demo_scenarios(is_active);

-- Demo metrics table
CREATE TABLE IF NOT EXISTS demo_metrics (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    baseline_value FLOAT NOT NULL,
    optimized_value FLOAT NOT NULL,
    improvement_percentage FLOAT NOT NULL,
    confidence_score FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for demo metrics
CREATE INDEX idx_demo_metrics_session_id ON demo_metrics(session_id);
CREATE INDEX idx_demo_metrics_type ON demo_metrics(metric_type);
CREATE INDEX idx_demo_metrics_timestamp ON demo_metrics(timestamp);

-- Demo exports table
CREATE TABLE IF NOT EXISTS demo_exports (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR REFERENCES userbase(id) ON DELETE SET NULL,
    export_format VARCHAR(20) NOT NULL,
    file_path VARCHAR(500),
    file_url VARCHAR(500),
    sections_included VARCHAR[],
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for demo exports
CREATE INDEX idx_demo_exports_session_id ON demo_exports(session_id);
CREATE INDEX idx_demo_exports_user_id ON demo_exports(user_id);
CREATE INDEX idx_demo_exports_status ON demo_exports(status);
CREATE INDEX idx_demo_exports_created_at ON demo_exports(created_at);

-- Demo feedback table
CREATE TABLE IF NOT EXISTS demo_feedback (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR REFERENCES userbase(id) ON DELETE SET NULL,
    rating INTEGER,
    feedback_text TEXT,
    would_recommend BOOLEAN,
    conversion_intent VARCHAR(50),
    metadata JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for demo feedback
CREATE INDEX idx_demo_feedback_session_id ON demo_feedback(session_id);
CREATE INDEX idx_demo_feedback_user_id ON demo_feedback(user_id);
CREATE INDEX idx_demo_feedback_rating ON demo_feedback(rating);
CREATE INDEX idx_demo_feedback_submitted_at ON demo_feedback(submitted_at);

-- Add update triggers for updated_at columns
CREATE TRIGGER update_demo_sessions_updated_at BEFORE UPDATE
    ON demo_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_demo_scenarios_updated_at BEFORE UPDATE
    ON demo_scenarios FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default demo scenarios
INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
VALUES 
('financial', 'fraud_detection', 'AI-powered fraud detection optimization', 
 'Analyze fraud detection workloads for financial services...', 
 '{"strategies": ["Model Selection", "Caching", "Batch Processing"]}',
 '{"baseline": {"latency_ms": 300, "accuracy": 0.85}, "optimized": {"latency_ms": 100, "accuracy": 0.92}}'),

('healthcare', 'diagnostic_ai', 'Medical diagnostic AI optimization',
 'Optimize diagnostic AI workloads for healthcare...',
 '{"strategies": ["Accuracy Enhancement", "Compliance", "Speed Optimization"]}',
 '{"baseline": {"latency_ms": 500, "accuracy": 0.88}, "optimized": {"latency_ms": 200, "accuracy": 0.95}}'),

('ecommerce', 'recommendation_engine', 'Product recommendation optimization',
 'Enhance recommendation engine performance for e-commerce...',
 '{"strategies": ["Personalization", "Real-time Processing", "Cost Reduction"]}',
 '{"baseline": {"latency_ms": 200, "conversion": 0.02}, "optimized": {"latency_ms": 50, "conversion": 0.035}}'),

('manufacturing', 'predictive_maintenance', 'Predictive maintenance AI optimization',
 'Optimize predictive maintenance models for manufacturing...',
 '{"strategies": ["Anomaly Detection", "Resource Optimization", "Downtime Prevention"]}',
 '{"baseline": {"prediction_accuracy": 0.75, "false_positives": 0.15}, "optimized": {"prediction_accuracy": 0.90, "false_positives": 0.05}}'),

('technology', 'code_generation', 'AI code generation optimization',
 'Optimize code generation and development assistance...',
 '{"strategies": ["Model Routing", "Context Management", "Output Quality"]}',
 '{"baseline": {"generation_time": 5000, "quality_score": 0.80}, "optimized": {"generation_time": 1500, "quality_score": 0.92}}')
ON CONFLICT (industry, scenario_name) DO NOTHING;

\echo 'Demo tables created successfully'