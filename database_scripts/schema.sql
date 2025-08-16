-- PostgreSQL Complete Schema
-- Auto-generated from modular initialization scripts
-- This file shows the complete schema but actual initialization uses modular files

-- NOTE: For fresh database initialization, use:
-- psql -U netra_app -d netra_dev -f database_scripts/00-init-main.sql

-- The modular approach ensures:
-- 1. Files stay under 300 lines (architecture requirement)
-- 2. Clear dependency order
-- 3. Easy maintenance and updates
-- 4. No migration needed for fresh installs

\echo 'This is a reference schema file.'
\echo 'For actual initialization, use: 00-init-main.sql'
\echo 'which orchestrates the modular initialization scripts.'

-- Include all modular scripts for reference
\i 01-init-extensions.sql
\i 02-init-users-auth.sql
\i 03-init-agents.sql
\i 04-init-supply.sql
\i 05-init-content.sql
\i 06-init-demo.sql
\i 07-init-indexes.sql