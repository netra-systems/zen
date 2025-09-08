-- Fix database permissions for netra_staging database
-- This script should be run as the postgres superuser

-- Connect to the netra_staging database
\c netra_staging;

-- Grant all necessary permissions to postgres user on netra_staging database
GRANT ALL PRIVILEGES ON DATABASE netra_staging TO postgres;

-- Grant all permissions on all tables and sequences (current and future)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Grant permissions for future tables and sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;

-- Ensure postgres user can create tables
GRANT CREATE ON SCHEMA public TO postgres;

-- Show current permissions
\dp