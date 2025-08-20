-- Performance Indexes
-- Purpose: Create additional performance indexes and constraints
-- Module: Indexes (adheres to 450-line limit)

-- Composite indexes for common query patterns

-- User-related composite indexes
CREATE INDEX idx_userbase_email_active ON userbase(email, is_active) WHERE is_active = true;
CREATE INDEX idx_userbase_plan_active ON userbase(plan_tier, is_active) WHERE is_active = true;

-- Tool usage analytics indexes
CREATE INDEX idx_tool_usage_user_tool_date ON tool_usage_logs(user_id, tool_name, created_at DESC);
CREATE INDEX idx_tool_usage_date_status ON tool_usage_logs(created_at DESC, status);

-- Thread and message performance indexes
CREATE INDEX idx_messages_thread_created ON messages(thread_id, created_at DESC);
CREATE INDEX idx_runs_thread_status ON runs(thread_id, status);

-- Supply research performance indexes
CREATE INDEX idx_ai_supply_provider_model ON ai_supply_items(provider, model_name);
CREATE INDEX idx_research_sessions_status_date ON research_sessions(status, created_at DESC);

-- Corpus management indexes
CREATE INDEX idx_corpus_audit_user_action_date ON corpus_audit_logs(user_id, action, timestamp DESC);
CREATE INDEX idx_corpora_status_domain ON corpora(status, domain);

-- Demo performance indexes
CREATE INDEX idx_demo_sessions_industry_status ON demo_sessions(industry, status);
CREATE INDEX idx_demo_interactions_session_time ON demo_interactions(session_id, timestamp DESC);

-- Partial indexes for active/pending records
CREATE INDEX idx_analyses_pending ON analyses(created_at) WHERE status = 'pending';
CREATE INDEX idx_research_sessions_pending ON research_sessions(created_at) WHERE status = 'pending';
CREATE INDEX idx_demo_sessions_active ON demo_sessions(started_at) WHERE status = 'active';

-- Foreign key constraint validation
ALTER TABLE secrets VALIDATE CONSTRAINT secrets_user_id_fkey;
ALTER TABLE tool_usage_logs VALIDATE CONSTRAINT tool_usage_logs_user_id_fkey;
ALTER TABLE messages VALIDATE CONSTRAINT messages_thread_id_fkey;
ALTER TABLE runs VALIDATE CONSTRAINT runs_thread_id_fkey;
ALTER TABLE supply_update_logs VALIDATE CONSTRAINT supply_update_logs_supply_item_id_fkey;

-- Add check constraints for data integrity
ALTER TABLE userbase ADD CONSTRAINT check_plan_tier 
    CHECK (plan_tier IN ('free', 'pro', 'enterprise', 'developer'));

ALTER TABLE userbase ADD CONSTRAINT check_payment_status 
    CHECK (payment_status IN ('active', 'suspended', 'cancelled'));

ALTER TABLE tool_usage_logs ADD CONSTRAINT check_status 
    CHECK (status IN ('success', 'error', 'permission_denied', 'rate_limited'));

ALTER TABLE analyses ADD CONSTRAINT check_analysis_status 
    CHECK (status IN ('pending', 'running', 'completed', 'failed'));

ALTER TABLE research_sessions ADD CONSTRAINT check_research_status 
    CHECK (status IN ('pending', 'researching', 'processing', 'completed', 'failed'));

ALTER TABLE demo_sessions ADD CONSTRAINT check_demo_status 
    CHECK (status IN ('active', 'completed', 'abandoned'));

ALTER TABLE demo_sessions ADD CONSTRAINT check_progress_percentage 
    CHECK (progress_percentage >= 0 AND progress_percentage <= 100);

-- Statistics target for frequently queried columns
ALTER TABLE userbase ALTER COLUMN email SET STATISTICS 1000;
ALTER TABLE userbase ALTER COLUMN plan_tier SET STATISTICS 500;
ALTER TABLE messages ALTER COLUMN thread_id SET STATISTICS 1000;
ALTER TABLE tool_usage_logs ALTER COLUMN user_id SET STATISTICS 1000;
ALTER TABLE tool_usage_logs ALTER COLUMN tool_name SET STATISTICS 500;

-- Analyze tables to update statistics
ANALYZE userbase;
ANALYZE secrets;
ANALYZE tool_usage_logs;
ANALYZE assistants;
ANALYZE threads;
ANALYZE messages;
ANALYZE runs;
ANALYZE steps;
ANALYZE apex_optimizer_agent_runs;
ANALYZE apex_optimizer_agent_run_reports;
ANALYZE supplies;
ANALYZE supply_options;
ANALYZE ai_supply_items;
ANALYZE research_sessions;
ANALYZE supply_update_logs;
ANALYZE references;
ANALYZE analyses;
ANALYZE analysis_results;
ANALYZE corpora;
ANALYZE corpus_audit_logs;
ANALYZE demo_sessions;
ANALYZE demo_interactions;
ANALYZE demo_scenarios;
ANALYZE demo_metrics;
ANALYZE demo_exports;
ANALYZE demo_feedback;

\echo 'Performance indexes and constraints created successfully'
\echo 'Database initialization complete!'