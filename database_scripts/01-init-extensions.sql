-- PostgreSQL Extensions Initialization
-- Purpose: Install required PostgreSQL extensions for the application
-- Module: Extensions (adheres to 450-line limit)

-- UUID generation support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions for secure storage
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Trigram similarity search for text matching
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Additional useful extensions for production

-- JSON Schema validation (if available)
CREATE EXTENSION IF NOT EXISTS "pg_jsonschema" WITH SCHEMA public;

-- Statistics extension for better query planning
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA public;

-- Row-level security (already built-in, but ensure it's enabled)
ALTER DATABASE CURRENT SET row_security = on;

-- Performance configuration for production use
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '8MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET max_connections = 200;

-- Logging configuration for monitoring
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 500;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET log_temp_files = 0;

-- Apply configuration changes
SELECT pg_reload_conf();

\echo 'PostgreSQL extensions installed successfully'