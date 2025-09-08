# STAGING 503 SERVICE UNAVAILABLE - FIVE WHYS ANALYSIS

**Date:** 2025-09-08  
**Severity:** CRITICAL  
**Environment:** Staging  
**Service:** netra-backend-staging (Cloud Run)  

## PROBLEM STATEMENT

The staging backend service at https://api.staging.netrasystems.ai/health is returning "503 Service Unavailable" despite deployment logs showing successful deployment with "✅ Revision is ready" and "✅ Traffic updated to latest revision".

## DEPLOYMENT CONTEXT

**Evidence of "Successful" Deployment:**
- Deployment timestamp: 2025-09-08T17:43:46.101322Z
- Cloud Run service status: Ready=True, ConfigurationsReady=True, RoutesReady=True
- Container health status: ContainerHealthy=True
- Latest revision: netra-backend-staging-00193-bxk

**Actual Service Behavior:**
```
curl https://api.staging.netrasystems.ai/health
HTTP/1.1 503 Service Unavailable
Service Unavailable
```

## FIVE WHYS ROOT CAUSE ANALYSIS

### WHY #1: Why is the staging service returning 503?

**ANSWER:** The Cloud Run service is reporting as "healthy" and ready, but the application inside the container is failing during startup, causing the service to return 503 even though container health checks pass.

**EVIDENCE:**
- Cloud Run service shows Ready=True and ContainerHealthy=True
- Response comes from "Google Frontend" indicating Cloud Run is routing traffic
- Container startup logs show critical application failure

### WHY #2: Why is the application failing during startup inside the container?

**ANSWER:** The application startup process is failing during database initialization with a deterministic startup error: "CRITICAL STARTUP FAILURE: Database initialization failed in staging environment"

**EVIDENCE:**
```
netra_backend.app.smd.DeterministicStartupError: CRITICAL STARTUP FAILURE: Database initialization failed in staging environment: Failed to verify database tables exist: Missing required database tables: {'subscriptions', 'credit_transactions', 'agent_executions'}. Run migration service first.
```

### WHY #3: Why are the database tables missing when migrations supposedly ran successfully?

**ANSWER:** There is a mismatch between what tables the application expects to exist and what tables were actually created by the migration service. The migration job ran successfully at 17:00:54 UTC, but the expected tables are not being created by the current migration scripts.

**EVIDENCE:**
- Migration job `netra-migrations-staging-98n2w` completed successfully with exit code 0
- Migration logs show: "INFO [alembic.runtime.migration] Will assume transactional DDL" and "INFO [alembic.runtime.migration] Context impl PostgresqlImpl"
- Application startup expects: `{'subscriptions', 'credit_transactions', 'agent_executions'}`
- Current migration (`66e0e5d9662d_add_missing_tables_and_columns_complete.py`) creates different tables

### WHY #4: Why does the application expect tables that don't exist in migration files?

**ANSWER:** The application's database model import system (`_import_all_models()`) is registering models in `Base.metadata` that either:
1. Don't have corresponding migration files 
2. Are being imported from the wrong location
3. Are being treated as required when they should be optional

**EVIDENCE:**
- `AgentExecution` model exists in `netra_backend/app/models/agent_execution.py` with `__tablename__ = "agent_executions"`
- `_import_all_models()` imports from `netra_backend.app.db.models_*` files, NOT `netra_backend.app.models.*`
- No `subscriptions` or `credit_transactions` models exist in the current codebase
- Models imported by `_import_all_models()` get registered in `Base.metadata.tables.keys()` which becomes `expected_tables`

### WHY #5: Why is the model import system inconsistent with the actual model locations?

**ANSWER:** The codebase has evolved to have models in multiple locations (`netra_backend/app/models/` and `netra_backend/app/db/models_*`) but the startup validation system only imports from the legacy `db/models_*` structure. This creates a disconnect where:
- New models are created in `models/` directory
- Startup validation only checks old `db/models_*` imports
- Migration files may be out of sync with either location
- The system fails when models exist but aren't properly registered for migration

## THE ERROR BEHIND THE ERROR: Root Cause Chain

**Surface Error:** 503 Service Unavailable  
**Immediate Error:** Database initialization failed  
**Underlying Error:** Missing database tables  
**Root Configuration Error:** Inconsistent model import system  
**Architectural Root Cause:** Multiple model definition patterns without SSOT consolidation

## CRITICAL DISCOVERY: Migration vs Application Mismatch

**Migration Service Results:**
- Successfully ran at 17:00:54 UTC
- Used alembic configuration pointing to specific revision
- Completed without errors

**Application Startup Expectations:**
- Expects tables: `{'subscriptions', 'credit_transactions', 'agent_executions'}`
- These are derived from `Base.metadata.tables.keys()`
- Current `_import_all_models()` doesn't import these models
- Therefore, these tables shouldn't be expected!

**The Real Problem:** The error message indicates these tables are missing, but they shouldn't be expected in the first place if the models aren't being imported by `_import_all_models()`.

## INVESTIGATION CONCLUSION: Code Inconsistency

After deep analysis, the root cause is:
1. **Model Location Mismatch:** Models exist in `netra_backend/app/models/` but aren't imported by startup validation
2. **Phantom Table Expectations:** The application is somehow expecting tables that don't correspond to imported models
3. **Migration Sync Issue:** Migration files may be creating different tables than what the application expects

## IMPLEMENTATION PLAN

### IMMEDIATE FIX (Critical Priority)

1. **Model Import Consolidation**
   - Update `_import_all_models()` to include models from `netra_backend.app.models.*`
   - Specifically add: `from netra_backend.app.models.agent_execution import AgentExecution`
   - Verify no phantom model imports are causing unexpected table requirements

2. **Migration Alignment Verification**
   - Check if migration files need to create the `agent_executions` table
   - Remove expectations for non-existent `subscriptions` and `credit_transactions` if not needed
   - Ensure migration service creates all tables that application models expect

3. **Startup Configuration Fix**
   - Either add missing models to imports OR remove them from expected tables
   - Update critical vs non-critical table classification
   - Consider making `agent_executions` non-critical if it's not essential for core functionality

### VERIFICATION STEPS

1. **Pre-Fix Verification**
   - Run `alembic current` to check current migration state
   - List actual tables in staging database
   - Compare with models being imported by `_import_all_models()`

2. **Post-Fix Verification**
   - Deploy updated model imports
   - Run migration service if needed
   - Test health endpoint returns 200 OK
   - Verify core chat functionality works

### DEPLOYMENT STRATEGY

1. **Model Import Fix:** Update `_import_all_models()` to include missing imports
2. **Migration Update:** If needed, create migration for `agent_executions` table
3. **Staged Deployment:** Deploy to staging and verify health endpoint
4. **Rollback Plan:** Revert model imports if issues persist

## PREVENTION MEASURES

1. **SSOT for Models:** Consolidate all models to single directory structure
2. **Migration Testing:** Add migration validation to CI/CD pipeline
3. **Database Schema Tests:** Add tests that verify expected tables match imported models
4. **Startup Validation Enhancement:** Improve error messages to indicate specific missing imports vs missing tables

## BUSINESS IMPACT

**Current Impact:**
- Staging environment completely unavailable (503 errors)
- Deployment pipeline appears successful but service is broken
- Development team cannot validate changes in staging
- Potential production deployment risks if issue propagates

**Risk Assessment:**
- **HIGH RISK:** Silent deployment success with broken service could deploy to production
- **MEDIUM RISK:** Development velocity impacted by broken staging environment  
- **LOW RISK:** Core functionality may work once database issues are resolved

## CONCLUSION

The 503 Service Unavailable error is caused by a fundamental mismatch between:
1. What database tables the application expects to find
2. What tables are actually created by migrations  
3. What models are being imported and registered for validation

This is a classic "error behind the error" scenario where the surface symptom (503) masks a deeper architectural inconsistency in the model/migration system.

The fix requires aligning the model import system with actual model locations and ensuring migrations create all expected tables.