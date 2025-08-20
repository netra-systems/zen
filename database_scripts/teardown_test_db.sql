-- Teardown script for dedicated test environment database
-- Cleans up test data and optionally drops test schema

-- Set search path to test schema
SET search_path = netra_test, public;

-- Log teardown start
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'netra_test' AND table_name = 'benchmarks') THEN
        INSERT INTO netra_test.benchmarks (id, name, description, test_scenarios)
        VALUES (
            'teardown_start',
            'Database Teardown Start',
            'Marks the beginning of test database teardown',
            '{"teardown_time": "' || NOW() || '", "status": "started"}'
        ) ON CONFLICT (id) DO UPDATE SET
            test_scenarios = '{"teardown_time": "' || NOW() || '", "status": "started"}',
            last_run = NOW();
    END IF;
END $$;

-- Clean up test data in dependency order (preserve schema structure by default)

-- Truncate tables in reverse dependency order
TRUNCATE TABLE IF EXISTS netra_test.messages CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.threads CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.users CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.metrics CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.models CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.corpus_entries CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.supply_chain_configs CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.cache_entries CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.workflow_templates CASCADE;
TRUNCATE TABLE IF EXISTS netra_test.benchmarks CASCADE;

-- Reset sequences
DO $$
DECLARE
    seq_record RECORD;
BEGIN
    FOR seq_record IN 
        SELECT schemaname, sequencename 
        FROM pg_sequences 
        WHERE schemaname = 'netra_test'
    LOOP
        EXECUTE format('ALTER SEQUENCE %I.%I RESTART WITH 1', seq_record.schemaname, seq_record.sequencename);
    END LOOP;
END $$;

-- Optional: Drop all functions in test schema (uncomment if needed)
-- DO $$
-- DECLARE
--     func_record RECORD;
-- BEGIN
--     FOR func_record IN 
--         SELECT proname, oidvectortypes(proargtypes) as argtypes
--         FROM pg_proc 
--         WHERE pronamespace = 'netra_test'::regnamespace
--     LOOP
--         EXECUTE format('DROP FUNCTION IF EXISTS netra_test.%I(%s) CASCADE', func_record.proname, func_record.argtypes);
--     END LOOP;
-- END $$;

-- Optional: Complete schema drop (uncomment if needed for full cleanup)
-- WARNING: This will completely remove the test schema and all objects
-- DROP SCHEMA IF EXISTS netra_test CASCADE;

-- Alternative: Keep schema but drop all tables (uncomment if needed)
-- DO $$
-- DECLARE
--     table_record RECORD;
-- BEGIN
--     FOR table_record IN 
--         SELECT tablename 
--         FROM pg_tables 
--         WHERE schemaname = 'netra_test'
--     LOOP
--         EXECUTE format('DROP TABLE IF EXISTS netra_test.%I CASCADE', table_record.tablename);
--     END LOOP;
-- END $$;

-- Clean up any temporary files or connections if applicable
-- (This would be handled at the application level)

-- Log successful teardown completion
DO $$
BEGIN
    -- Only log if benchmarks table still exists (in case of partial teardown)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'netra_test' AND table_name = 'benchmarks') THEN
        INSERT INTO netra_test.benchmarks (id, name, description, test_scenarios)
        VALUES (
            'teardown_complete',
            'Database Teardown Complete',
            'Marks successful completion of test database teardown',
            '{"teardown_time": "' || NOW() || '", "status": "completed", "cleanup_type": "data_only"}'
        ) ON CONFLICT (id) DO UPDATE SET
            test_scenarios = '{"teardown_time": "' || NOW() || '", "status": "completed", "cleanup_type": "data_only"}',
            last_run = NOW();
    END IF;
END $$;

-- Display cleanup summary
SELECT 
    'Test database teardown completed' as message,
    NOW() as completion_time,
    'data_cleared' as cleanup_type,
    'schema_preserved' as schema_status;