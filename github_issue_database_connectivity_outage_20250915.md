# New GitHub Issue - Database Connectivity Outage

## Issue Details

**Title:** GCP-regression | P0 | Database connectivity failure causing complete staging outage

**Labels:** claude-code-generated-issue, database, cloud-sql, staging, critical

**Body:**

## Summary
Complete database connectivity failure in staging environment causing continuous application restart cycles and service unavailability. This is blocking the Golden Path user flow and requires immediate infrastructure intervention.

## Error Details
- **Time Range**: 2025-09-15T20:37:44 UTC to 2025-09-15T21:37:44 UTC
- **Frequency**: 50+ errors in 1 hour
- **Service**: netra-backend-staging
- **Impact**: Golden Path completely blocked
- **Service URL**: https://netra-backend-staging-pnovr5vsba-uc.a.run.app

## Key Error Messages

### Database Connection Timeouts
```
Database initialization timeout after 25.0s in staging environment
```

### Cloud SQL Socket Failures
```
connection to server on socket "/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432" failed: server closed the connection unexpectedly
```

### Migration Failures
```
Failed to run migrations: (psycopg2.OperationalError)
```

### Application Startup Failures
```
Application startup failed. Exiting.
uvicorn-compatible session middleware error: CRITICAL STARTUP FAILURE
```

### Health Check Failures
```
HTTP GET /health -> 503, latency: 13.045507683s
Multiple 503 responses from https://api.staging.netrasystems.ai/health
Latencies ranging from 3.6s to 67.2s (extremely high)
```

## Technical Details
- **Cloud SQL Instance**: `netra-staging:us-central1:staging-shared-postgres`
- **Cloud SQL Socket**: `/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432`
- **Timeout Configuration**: 25.0s initialization timeout
- **Error Type**: psycopg2.OperationalError
- **Environment**: staging
- **Container Exit**: exit(3) - startup failure

## Sample Log Entry
```
2025-09-15T21:37:17.707244+00:00 | ERROR | netra-backend-staging
uvicorn-compatible session middleware error: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.
```

## Business Impact
- **Service Availability**: 0% - Complete outage
- **Core Chat Functionality**: Offline
- **User Login**: Blocked
- **Revenue Risk**: $500K+ ARR Golden Path services unavailable
- **Development Pipeline**: E2E testing blocked

## Related Issues Context
This appears to be a regression or continuation of previously addressed database connectivity issues:
- Related to Issue #1263 (VPC connector fixes) - marked as resolved
- Related to Issue #1278 (Database timeout & FastAPI lifespan) - ongoing infrastructure escalation

## Infrastructure Analysis Required
1. **Cloud SQL Instance Health**: Validate `netra-staging:us-central1:staging-shared-postgres` status
2. **VPC Connector Status**: Check staging-connector configuration and health
3. **Network Connectivity**: Validate Cloud Run → VPC → Cloud SQL routing
4. **GCP Regional Services**: Review any service degradation or maintenance

## Immediate Actions Needed
- [ ] Validate Cloud SQL instance is running and accessible
- [ ] Check VPC connector configuration and status
- [ ] Review GCP service status for regional issues
- [ ] Verify network routing between Cloud Run and Cloud SQL
- [ ] Consider temporary failover or instance restart if needed

## Priority: P0 Critical
This is a complete staging environment outage affecting core business functionality and blocking all development workflows.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>