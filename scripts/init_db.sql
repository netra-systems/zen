-- Initialize Netra Database
CREATE SCHEMA IF NOT EXISTS public;

-- Create the netra user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'netra') THEN
        CREATE ROLE netra WITH LOGIN PASSWORD 'netra123';
    END IF;
END
$$;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions
GRANT ALL ON SCHEMA public TO netra;
GRANT ALL ON ALL TABLES IN SCHEMA public TO netra;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO netra;

-- Initial setup complete
SELECT 'Database initialized successfully' as status;
