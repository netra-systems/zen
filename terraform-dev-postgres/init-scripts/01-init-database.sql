-- PostgreSQL Initialization Script for Netra Development
-- This script runs automatically when the container starts

-- Create application user if not exists
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_user
      WHERE usename = 'netra_app'
   ) THEN
      CREATE USER netra_app WITH PASSWORD 'changeme';
   END IF;
END
$$;

-- Grant necessary privileges
GRANT CONNECT ON DATABASE netra_dev TO netra_app;
GRANT USAGE ON SCHEMA public TO netra_app;
GRANT CREATE ON SCHEMA public TO netra_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO netra_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO netra_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO netra_app;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON TABLES TO netra_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON SEQUENCES TO netra_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON FUNCTIONS TO netra_app;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create test database for testing
CREATE DATABASE netra_test;
GRANT ALL PRIVILEGES ON DATABASE netra_test TO netra_app;

-- Performance tuning for development
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET max_connections = 100;

-- Enable query performance insights
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 100;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Apply configuration changes
SELECT pg_reload_conf();