-- Fix NULL metadata in threads table for GCP staging environment
-- This script updates all threads with NULL metadata to have a valid JSON object
-- Run this against the staging database to fix 500 errors

-- First, check how many threads have NULL metadata
SELECT COUNT(*) as null_metadata_count 
FROM threads 
WHERE metadata IS NULL;

-- Update all threads with NULL metadata to have empty JSON object
UPDATE threads 
SET metadata = '{}'::jsonb 
WHERE metadata IS NULL;

-- Add NOT NULL constraint to prevent future NULL values
-- Note: Only run this after the UPDATE above
ALTER TABLE threads 
ALTER COLUMN metadata SET DEFAULT '{}'::jsonb,
ALTER COLUMN metadata SET NOT NULL;

-- Verify the fix
SELECT COUNT(*) as remaining_null_count 
FROM threads 
WHERE metadata IS NULL;

-- Check a sample of updated threads
SELECT id, user_id, title, created_at, metadata 
FROM threads 
WHERE metadata = '{}'::jsonb 
LIMIT 5;