**Priority:** P0 - CRITICAL
**Type:** Active Development Issue
**Service:** netra-backend-staging
**Time Range:** 2025-09-16 00:43-01:43 UTC (5:43-6:43 PM PDT Sept 15)

## Problem
Containers repeatedly calling exit(3) causing service unavailability cycles. 9 incidents in last hour.

**Error Pattern:**
```
Container called exit(3).
```

## Impact
- ❌ Service containers cannot stay running
- ❌ Automatic restart cycles every ~7 minutes
- ❌ Complete service downtime periods
- 💰 Service availability SLA violation

## Evidence

### Latest Container Exit Log
```json
{
  "insertId": "68c8c079000d3f33d5b1a727",
  "textPayload": "Container called exit(3).",
  "timestamp": "2025-09-16T01:42:17.868096Z",
  "severity": "WARNING",
  "labels": {
    "container_name": "netra-backend-staging-1",
    "instanceId": "0069c7a98824795ed4cca76950d82f38b005d1f6faae180462eb5c736860f476e381f153ee39b01b8bc5afdebe971b31",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00742-b95",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  }
}
```

### Time Pattern Analysis
- **9 container exit(3) incidents** in 1-hour window (00:43-01:43 UTC Sept 16)
- **Container restart cycles** every ~7 minutes
- **Consistent revision**: netra-backend-staging-00742-b95
- **Environment**: Staging with VPC connectivity enabled

## Root Cause Analysis

**Container exit(3) is a SYMPTOM of underlying startup failures:**

### Primary Root Cause: Missing Monitoring Module (Cluster 1)
- **Import failure**: `ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'`
- **Location**: `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py:23`
- **Result**: Application cannot start → container exits cleanly with code 3

### Secondary Root Cause: Database Connectivity (Historical)
- **SMD Phase 3**: Database initialization timeouts
- **Connection issues**: Cloud SQL connectivity via VPC connector
- **Result**: FastAPI lifespan failure → container exit code 3

## Relationship to Other Issues

### Directly Caused By:
- **Monitoring Module Issue**: Missing `gcp_error_reporter` exports causing import failures
- Container cannot start due to middleware setup failure
- Clean exit with code 3 indicates configuration/dependency issue (not crash)

### Related Infrastructure Issues:
- Database connectivity timeouts (Issue #1263, #1278)
- SMD orchestration failures causing startup abort
- FastAPI lifespan context breakdown

## Container Exit Code 3 Significance
- **Code 3**: Configuration or dependency issue (not application crash)
- **Clean Exit**: Proper error handling, not unexpected termination
- **Restart Trigger**: Cloud Run attempts automatic restart
- **Cycle Pattern**: Restart → Same error → Exit(3) → Restart

## Immediate Actions Required

### Priority 0 (URGENT - Deploy Immediately)
1. **Deploy monitoring module fix** - Resolve import failure causing exit(3)
2. **Verify container startup** - Confirm containers stay running
3. **Monitor restart cycles** - Ensure exit(3) pattern stops
4. **Validate service health** - Check load balancer marks service healthy

### Priority 1 (Post-Resolution Monitoring)
1. **Container lifecycle monitoring** - Alert on exit code patterns
2. **Startup success rate tracking** - Monitor application initialization
3. **Exit code analysis** - Distinguish between crash vs clean exit scenarios
4. **Restart frequency alerts** - Track abnormal restart patterns

## Expected Resolution

**After monitoring module deployment:**
- ✅ Container exit(3) frequency drops to 0
- ✅ Containers maintain running state
- ✅ Restart cycles eliminated
- ✅ Service availability restored

## Monitoring Alerts

### Container Health Metrics:
- **Exit Code 3 Frequency**: 0 occurrences in 10-minute window
- **Container Restart Rate**: <1 restart per hour per instance
- **Application Startup Success**: >95% success rate
- **Service Availability**: >99% uptime

### Alert Triggers:
- Container exit code 3 >3 times in 5 minutes
- Container restart rate >5 per hour
- Application startup failure rate >10%

---

## Container Runtime Environment

**Cloud Run Configuration:**
- **Service**: netra-backend-staging
- **Revision**: netra-backend-staging-00742-b95
- **Location**: us-central1
- **VPC**: Enabled with staging-connector
- **Resource Limits**: Standard Cloud Run limits

**Exit Code 3 Context:**
- Indicates proper error handling during startup failure
- Application detects configuration issue and exits cleanly
- Cloud Run interprets as deployment issue and attempts restart
- Creates restart loop until underlying issue resolved

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>