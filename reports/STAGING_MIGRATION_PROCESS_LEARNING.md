# Staging Database Migration Process Learning Report

**Date**: 2025-09-08  
**Issue**: Backend service failing on startup due to missing database tables in staging  
**Resolution**: Successful migration using Cloud Run Job  

## Problem Analysis

### Initial Issue
- Backend service `netra-backend-staging` was failing during startup
- Error: `Failed to create tables: {'subscriptions', 'credit_transactions', 'agent_executions'}`
- Root cause: Staging database was not up-to-date with latest migrations

### Error Logs from Backend
```
netra_backend.app.smd.DeterministicStartupError: CRITICAL STARTUP FAILURE: Database initialization failed in staging environment: Failed to ensure database tables exist: Failed to create tables: {'subscriptions', 'credit_transactions', 'agent_executions'}
```

## Solution Implemented

### 1. Created Dedicated Migration Cloud Run Job
- **Job Name**: `netra-migrations-staging`
- **Image**: `gcr.io/netra-staging/netra-backend-staging:latest` (reused existing backend image)
- **Configuration**:
  - Memory: 512Mi
  - CPU: 1
  - Timeout: 600s
  - Cloud SQL Connector: `netra-staging:us-central1:staging-shared-postgres`

### 2. Secrets Configuration
```bash
--set-secrets "POSTGRES_HOST=postgres-host-staging:latest"
--set-secrets "POSTGRES_PORT=postgres-port-staging:latest"
--set-secrets "POSTGRES_DB=postgres-db-staging:latest"
--set-secrets "POSTGRES_USER=postgres-user-staging:latest"
--set-secrets "POSTGRES_PASSWORD=postgres-password-staging:latest"
```

### 3. Migration Command
```bash
--command "sh" --args "-c,cd /app && python -m alembic -c netra_backend/alembic.ini upgrade head"
```

## Key Technical Insights

### Cloud SQL Connection Requirements
- **Critical**: Cloud Run Jobs MUST have `--set-cloudsql-instances` configured to connect to Cloud SQL
- Without this configuration, jobs fail with: `connection to server on socket "/cloudsql/..." failed: No such file or directory`

### Migration Job Architecture Benefits
- **Separation of Concerns**: Database migrations run independently from application startup
- **Reliability**: Migration failures don't impact application deployment
- **Auditability**: Clear migration history and logs in separate Cloud Run Job

### Command Syntax Learning
- **Wrong**: `--command "python" --args "-c,cd /app && ..."`  (SyntaxError: invalid syntax)
- **Correct**: `--command "sh" --args "-c,cd /app && python -m alembic ..."`

## Migration Results

### Successful Execution
- Migration job executed successfully: `netra-migrations-staging-s4gp2`
- Exit code: 0 (success)
- Database revision confirmed: `add_deleted_at_001 (head)`

### Verification Commands
```bash
# Deploy migration job
gcloud run jobs deploy netra-migrations-staging \
  --image gcr.io/netra-staging/netra-backend-staging:latest \
  --region us-central1 --project netra-staging \
  --set-cloudsql-instances "netra-staging:us-central1:staging-shared-postgres"

# Execute migration
gcloud run jobs execute netra-migrations-staging --region us-central1 --project netra-staging --wait

# Verify current revision
gcloud run jobs execute netra-check-revision --region us-central1 --project netra-staging --wait
```

## Outstanding Issues

### Backend Service Still Failing
Even after successful migration, backend service continues to fail with same error:
```
Failed to create tables: {'credit_transactions', 'subscriptions', 'agent_executions'}
```

### Potential Root Causes
1. **Database Connection Issues**: Backend may be connecting to different database instance
2. **Schema Mismatch**: Backend expecting different table structure
3. **Migration Not Applied to Correct Database**: Migration may have run against wrong schema/database
4. **Table Creation Logic**: Backend's table creation logic may not recognize existing tables

## Next Steps
1. Investigate backend database connection configuration
2. Verify backend and migration job connect to same database instance
3. Check table existence directly in staging database
4. Consider backend service restart/redeploy

## Learnings for Future

### SSOT Migration Process
- Use existing `scripts/run_cloud_migrations.py` for future migrations
- Ensure `docker/migration.alpine.Dockerfile` exists (not `migrations.alpine.Dockerfile`)
- Always include Cloud SQL connector configuration

### Separate Migration from Application
- Database migrations should be separate Cloud Run Jobs
- Backend services should only verify database state, not create tables
- Clear separation between schema management and application deployment

## File Updates Made
- Updated `scripts/run_cloud_migrations.py` to fix Dockerfile filename
- Added Windows encoding SSOT import for Unicode handling