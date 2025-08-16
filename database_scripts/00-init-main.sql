-- Main PostgreSQL Database Initialization Script
-- Purpose: Orchestrate modular table creation for fresh database setup
-- 
-- ULTRA DEEP THINK: This replaces migration-based initialization with
-- direct CREATE TABLE commands for fresh PostgreSQL databases.
-- Modules are kept under 300 lines per architecture requirements.

-- Set configuration
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;
SET timezone = 'UTC';

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO PUBLIC;

-- Execute modular initialization scripts in dependency order
\echo 'Initializing PostgreSQL Extensions...'
\i 01-init-extensions.sql

\echo 'Creating User and Authentication Tables...'
\i 02-init-users-auth.sql

\echo 'Creating Agent and Assistant Tables...'
\i 03-init-agents.sql

\echo 'Creating Supply Research Tables...'
\i 04-init-supply.sql

\echo 'Creating Content and Corpus Tables...'
\i 05-init-content.sql

\echo 'Creating Demo Tables...'
\i 06-init-demo.sql

\echo 'Creating Performance Indexes...'
\i 07-init-indexes.sql

\echo 'Database initialization complete!'
\echo 'All tables created successfully with proper foreign key relationships.'