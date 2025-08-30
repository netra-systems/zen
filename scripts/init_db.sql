-- Initialize Netra Database
-- This script runs in the context of the POSTGRES_DB database (netra_dev)
CREATE SCHEMA IF NOT EXISTS public;

-- Create netra role if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'netra') THEN
        CREATE ROLE netra WITH LOGIN SUPERUSER PASSWORD 'netra123';
    END IF;
END
$$;

-- Create postgres role if it doesn't exist (for compatibility)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'netra123';
    END IF;
END
$$;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant comprehensive permissions
GRANT ALL ON SCHEMA public TO netra;
GRANT ALL ON ALL TABLES IN SCHEMA public TO netra;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO netra;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO netra;

-- Grant future object permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO netra;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO netra;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO netra;

-- Make netra a superuser for development environment (only if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'netra') THEN
        ALTER ROLE netra SUPERUSER;
    END IF;
END
$$;

-- Initial setup complete
SELECT 'Database initialized successfully' as status;
