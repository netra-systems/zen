#!/bin/bash

# Fix staging database permissions
# This script should be run in Google Cloud Shell

set -e

PROJECT_ID="netra-staging"
INSTANCE_ID="staging-shared-postgres"
DATABASE="netra_staging"

echo "🔧 Fixing database permissions for staging environment..."
echo "Project: $PROJECT_ID"
echo "Instance: $INSTANCE_ID" 
echo "Database: $DATABASE"

# Connect to the database and run the permission fixes
gcloud sql connect $INSTANCE_ID --user=postgres --project=$PROJECT_ID << 'EOF'
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
SELECT grantee, privilege_type 
FROM information_schema.table_privileges 
WHERE table_schema='public' AND grantee='postgres';

-- Exit psql
\q
EOF

echo "✅ Database permissions updated successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Restart the backend service to retry database initialization"
echo "2. Check service health at: https://netra-backend-staging-701982941522.us-central1.run.app/health"