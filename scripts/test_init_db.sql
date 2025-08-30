-- Test Database Initialization Script
-- Creates test databases and schemas for real service testing
-- Optimized for fast, repeatable test execution

-- Create additional test databases
CREATE DATABASE IF NOT EXISTS netra_test_auth;
CREATE DATABASE IF NOT EXISTS netra_test_backend; 

-- Grant permissions to test user
GRANT ALL PRIVILEGES ON DATABASE netra_test TO test_user;
GRANT ALL PRIVILEGES ON DATABASE netra_test_auth TO test_user;
GRANT ALL PRIVILEGES ON DATABASE netra_test_backend TO test_user;

-- Connect to main test database
\c netra_test;

-- Create test schema for user management
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS backend;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant schema permissions  
GRANT ALL ON SCHEMA auth TO test_user;
GRANT ALL ON SCHEMA backend TO test_user; 
GRANT ALL ON SCHEMA analytics TO test_user;

-- Users table for authentication tests
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- User sessions table
CREATE TABLE IF NOT EXISTS auth.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_agent TEXT,
    ip_address INET
);

-- API keys table
CREATE TABLE IF NOT EXISTS auth.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE
);

-- Organizations table for multi-tenant testing
CREATE TABLE IF NOT EXISTS backend.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Organization memberships
CREATE TABLE IF NOT EXISTS backend.organization_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES backend.organizations(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, organization_id)
);

-- AI agents table for agent testing
CREATE TABLE IF NOT EXISTS backend.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES backend.organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_config JSONB DEFAULT '{}',
    system_prompt TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Agent conversations
CREATE TABLE IF NOT EXISTS backend.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES backend.agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation messages
CREATE TABLE IF NOT EXISTS backend.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES backend.conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tool executions for agent testing
CREATE TABLE IF NOT EXISTS backend.tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES backend.conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES backend.messages(id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    parameters JSONB DEFAULT '{}',
    result JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- WebSocket connections tracking
CREATE TABLE IF NOT EXISTS backend.websocket_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'connected',
    metadata JSONB DEFAULT '{}',
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    disconnected_at TIMESTAMP WITH TIME ZONE,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    organization_id UUID REFERENCES backend.organizations(id),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id VARCHAR(255),
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Billing/usage tracking
CREATE TABLE IF NOT EXISTS analytics.usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES backend.organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    metric_type VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    dimensions JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON auth.users(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON auth.user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON auth.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON auth.user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_organizations_slug ON backend.organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organization_memberships_user ON backend.organization_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_organization_memberships_org ON backend.organization_memberships(organization_id);

CREATE INDEX IF NOT EXISTS idx_agents_org ON backend.agents(organization_id);
CREATE INDEX IF NOT EXISTS idx_agents_active ON backend.agents(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_conversations_agent ON backend.conversations(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON backend.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON backend.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON backend.messages(created_at);

CREATE INDEX IF NOT EXISTS idx_tool_executions_conversation ON backend.tool_executions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON backend.tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_websocket_connections_user ON backend.websocket_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_websocket_connections_status ON backend.websocket_connections(status);

CREATE INDEX IF NOT EXISTS idx_events_user ON analytics.events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_org ON analytics.events(organization_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON analytics.events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON analytics.events(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_org ON analytics.usage_metrics(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_type ON analytics.usage_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_recorded ON analytics.usage_metrics(recorded_at);

-- Create functions for common test operations
CREATE OR REPLACE FUNCTION reset_test_data() 
RETURNS void AS $$
BEGIN
    -- Delete in dependency order
    DELETE FROM analytics.usage_metrics;
    DELETE FROM analytics.events;
    DELETE FROM backend.websocket_connections;
    DELETE FROM backend.tool_executions;
    DELETE FROM backend.messages;
    DELETE FROM backend.conversations;
    DELETE FROM backend.agents;
    DELETE FROM backend.organization_memberships;
    DELETE FROM backend.organizations;
    DELETE FROM auth.api_keys;
    DELETE FROM auth.user_sessions;
    DELETE FROM auth.users;
    
    -- Reset sequences
    ALTER SEQUENCE IF EXISTS auth.users_id_seq RESTART WITH 1;
    ALTER SEQUENCE IF EXISTS backend.organizations_id_seq RESTART WITH 1;
END;
$$ LANGUAGE plpgsql;

-- Create test user for immediate testing
INSERT INTO auth.users (email, name, password_hash, is_active, is_superuser) 
VALUES (
    'test@netra.local',
    'Test User', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdCmUiGD.9K.9qS', -- 'test123'
    true,
    false
) ON CONFLICT (email) DO NOTHING;

-- Create test organization
INSERT INTO backend.organizations (name, slug, plan)
VALUES ('Test Organization', 'test-org', 'free')
ON CONFLICT (slug) DO NOTHING;

-- Link test user to test organization
INSERT INTO backend.organization_memberships (user_id, organization_id, role)
SELECT 
    u.id, 
    o.id, 
    'admin'
FROM auth.users u, backend.organizations o
WHERE u.email = 'test@netra.local' AND o.slug = 'test-org'
ON CONFLICT (user_id, organization_id) DO NOTHING;

-- Grant all permissions to test user for easy testing
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO test_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA backend TO test_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA backend TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO test_user;

-- Success message
SELECT 'Test database initialized successfully' as status;