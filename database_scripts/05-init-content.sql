-- Content and Corpus Tables
-- Purpose: Create corpus management, analysis, and content audit tables
-- Module: Content (adheres to 300-line limit)

-- References table
CREATE TABLE IF NOT EXISTS references (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    name VARCHAR NOT NULL,
    friendly_name VARCHAR NOT NULL,
    description VARCHAR,
    type VARCHAR NOT NULL,
    value VARCHAR NOT NULL,
    version VARCHAR NOT NULL DEFAULT '1.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for references
CREATE INDEX idx_references_name ON references(name);
CREATE INDEX idx_references_type ON references(type);
CREATE INDEX idx_references_created_at ON references(created_at);

-- Analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    name VARCHAR NOT NULL,
    description VARCHAR,
    status VARCHAR DEFAULT 'pending',
    created_by_id VARCHAR REFERENCES userbase(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for analyses
CREATE INDEX idx_analyses_name ON analyses(name);
CREATE INDEX idx_analyses_status ON analyses(status);
CREATE INDEX idx_analyses_created_by_id ON analyses(created_by_id);
CREATE INDEX idx_analyses_created_at ON analyses(created_at);

-- Analysis results table
CREATE TABLE IF NOT EXISTS analysis_results (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    analysis_id VARCHAR REFERENCES analyses(id) ON DELETE CASCADE,
    data JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for analysis results
CREATE INDEX idx_analysis_results_analysis_id ON analysis_results(analysis_id);
CREATE INDEX idx_analysis_results_created_at ON analysis_results(created_at);

-- Corpora table
CREATE TABLE IF NOT EXISTS corpora (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    name VARCHAR NOT NULL UNIQUE,
    description VARCHAR,
    table_name VARCHAR,
    status VARCHAR DEFAULT 'pending',
    domain VARCHAR DEFAULT 'general',
    metadata_ JSON,
    created_by_id VARCHAR REFERENCES userbase(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for corpora
CREATE INDEX idx_corpora_name ON corpora(name);
CREATE INDEX idx_corpora_status ON corpora(status);
CREATE INDEX idx_corpora_domain ON corpora(domain);
CREATE INDEX idx_corpora_created_by_id ON corpora(created_by_id);
CREATE INDEX idx_corpora_created_at ON corpora(created_at);

-- Corpus audit logs table
CREATE TABLE IF NOT EXISTS corpus_audit_logs (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR REFERENCES userbase(id) ON DELETE SET NULL,
    action VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    corpus_id VARCHAR,
    resource_type VARCHAR NOT NULL,
    resource_id VARCHAR,
    operation_duration_ms FLOAT,
    result_data JSON,
    
    -- Metadata fields
    user_agent VARCHAR,
    ip_address VARCHAR,
    request_id VARCHAR,
    session_id VARCHAR,
    configuration JSON DEFAULT '{}',
    performance_metrics JSON DEFAULT '{}',
    error_details JSON,
    compliance_flags VARCHAR[] DEFAULT '{}'
);

-- Create indexes for corpus audit logs
CREATE INDEX idx_corpus_audit_logs_timestamp ON corpus_audit_logs(timestamp);
CREATE INDEX idx_corpus_audit_logs_user_id ON corpus_audit_logs(user_id);
CREATE INDEX idx_corpus_audit_logs_action ON corpus_audit_logs(action);
CREATE INDEX idx_corpus_audit_logs_status ON corpus_audit_logs(status);
CREATE INDEX idx_corpus_audit_logs_corpus_id ON corpus_audit_logs(corpus_id);
CREATE INDEX idx_corpus_audit_logs_resource_type ON corpus_audit_logs(resource_type);
CREATE INDEX idx_corpus_audit_logs_resource_id ON corpus_audit_logs(resource_id);
CREATE INDEX idx_corpus_audit_logs_ip_address ON corpus_audit_logs(ip_address);
CREATE INDEX idx_corpus_audit_logs_request_id ON corpus_audit_logs(request_id);
CREATE INDEX idx_corpus_audit_logs_session_id ON corpus_audit_logs(session_id);

-- Add update triggers for updated_at columns
CREATE TRIGGER update_references_updated_at BEFORE UPDATE
    ON references FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analyses_updated_at BEFORE UPDATE
    ON analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_corpora_updated_at BEFORE UPDATE
    ON corpora FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo 'Content and corpus tables created successfully'