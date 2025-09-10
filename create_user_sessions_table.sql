-- Create user_sessions table in netra_test database
-- Based on staging_init.sql but adapted for test environment

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas for service separation
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS backend;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Users table (auth schema) - Create if not exists
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

-- CRITICAL: User sessions table (auth schema) - This is what we need!
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON auth.users(created_at);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON auth.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON auth.user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON auth.user_sessions(expires_at);

-- Create test user for validation
INSERT INTO auth.users (id, email, username, is_active, is_verified, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'test-user@example.com',
    'test_user',
    TRUE,
    TRUE,
    '{"role": "test_user", "environment": "test", "created_by": "user_sessions_remediation"}'::jsonb
) ON CONFLICT (email) DO NOTHING;

-- Verification queries
SELECT 'auth.users table created' as status, COUNT(*) as user_count FROM auth.users;
SELECT 'auth.user_sessions table created' as status, 
       COUNT(*) as session_count FROM auth.user_sessions;

-- Verify table structure
SELECT 'user_sessions table structure:' as info;
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'auth' AND table_name = 'user_sessions'
ORDER BY ordinal_position;