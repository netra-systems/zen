# GCP-new | P1 | Container startup failures - exit(3) during backend deployment

## Summary

**CRITICAL**: Container exit(3) failures causing service restart cycles and deployment instability. This is a **secondary effect** of the P0 monitoring module import failure (Cluster 1 root cause).

## Business Impact

- **Severity**: P1 - High priority infrastructure issue
- **Service Status**: Intermittent availability with restart cycles
- **Duration**: 2025-09-16T00:43-01:43 UTC (Multiple cycles)
- **Container**: netra-backend-staging-1
- **Pattern**: 9+ container exit(3) incidents in 1-hour window
- **Customer Impact**: Service interruptions during restart cycles

## Technical Analysis

### Root Cause Linkage to Cluster 1
**PRIMARY ROOT CAUSE**: Missing Monitoring Module Import (Cluster 1)
- **Import failure**: `ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'`
- **Location**: `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py:23`
- **Result**: Application startup failure → Container exits cleanly with code 3

### Container Exit Pattern
**Exit Code 3 Significance**:
- **Clean Exit**: Indicates configuration/dependency issue (not application crash)
- **Restart Trigger**: Cloud Run automatically attempts restart
- **Cycle Pattern**: Startup → Import failure → Exit(3) → Cloud Run restart → Repeat
- **Frequency**: Every ~7 minutes

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

### Container Restart Cycles
- **Time Window**: 2025-09-16T00:43-01:43 UTC (1 hour)
- **Exit Events**: 9+ container exit(3) incidents
- **Restart Frequency**: ~7 minute intervals
- **Consistent Revision**: netra-backend-staging-00742-b95
- **Environment**: Staging with VPC connectivity enabled

## Impact Analysis

### Infrastructure Impact
- ❌ **Container Stability**: Containers cannot maintain running state
- ❌ **Restart Cycles**: Automatic restart attempts every ~7 minutes
- ❌ **Service Interruptions**: Brief downtime periods during restarts
- ❌ **Resource Waste**: Unnecessary compute cycles during restart loops

### Service Availability Impact
- **Load Balancer**: Intermittent unhealthy instance marking
- **User Experience**: Potential 503 responses during restart windows
- **SLA Risk**: Service availability degradation
- **Monitoring**: False positive alerts from restart events

## Relationship to Other Issues

### Direct Dependency on Cluster 1 (P0 - Root Cause)
**Monitoring Module Import Failure** → **Container Exit(3) Cycles**

The container exit failures are a **symptom** of the underlying monitoring module import issue:

1. **Application Startup**: FastAPI attempts to initialize
2. **Middleware Loading**: `gcp_auth_context_middleware.py` imports monitoring functions
3. **Import Failure**: `ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'`
4. **Startup Abort**: Application cannot continue initialization
5. **Clean Exit**: Container exits with code 3 (configuration issue)
6. **Restart Loop**: Cloud Run detects failure and restarts container

### Related Infrastructure Issues
- Database connectivity timeouts (Issues #1263, #1278)
- SMD orchestration failures
- FastAPI lifespan context issues

## Resolution Strategy

### Primary Resolution (Dependency)
**RESOLVE CLUSTER 1 FIRST**: Deploy monitoring module import fix
- File: `/app/netra_backend/app/services/monitoring/__init__.py`
- Fix: Add missing exports for `set_request_context`, `clear_request_context`
- Expected Result: Container startup succeeds → Exit(3) cycles stop

### Secondary Validation
**Monitor Container Health Post-Fix**:
1. **Startup Success**: Containers start and remain running
2. **Exit Pattern**: Container exit(3) frequency drops to 0
3. **Restart Cycles**: Abnormal restart patterns eliminated
4. **Service Health**: Load balancer marks instances as healthy

## Immediate Actions Required

### Priority 0 (URGENT - After Cluster 1 Fix)
1. **Monitor Container Behavior**: Track exit(3) frequency post-deployment
2. **Validate Startup Stability**: Confirm containers maintain running state
3. **Check Restart Patterns**: Ensure restart cycles are eliminated
4. **Service Health Verification**: Validate load balancer health checks

### Priority 1 (Ongoing Monitoring)
1. **Container Lifecycle Alerts**: Alert on abnormal exit code patterns
2. **Startup Success Tracking**: Monitor application initialization success rate
3. **Restart Frequency Monitoring**: Track container restart patterns
4. **Exit Code Analysis**: Distinguish between crash vs configuration issues

## Expected Resolution Timeline

### After Cluster 1 Deployment:
- **Immediate** (0-15 minutes): Container exit(3) patterns stop
- **Short-term** (15-60 minutes): Containers maintain stable running state
- **Medium-term** (1-24 hours): Zero abnormal restart cycles
- **Long-term** (24+ hours): Stable service availability

## Monitoring and Alerts

### Success Metrics
- **Container Exit Code 3**: 0 occurrences in 10-minute windows
- **Container Restart Rate**: <1 restart per hour per instance
- **Application Startup Success**: >99% success rate
- **Service Availability**: >99.5% uptime

### Alert Thresholds
- **Critical**: Container exit code 3 >3 times in 5 minutes
- **Warning**: Container restart rate >3 per hour
- **Info**: Application startup failure rate >5%

## Container Runtime Environment

**Cloud Run Configuration**:
- **Service**: netra-backend-staging
- **Revision**: netra-backend-staging-00742-b95
- **Location**: us-central1
- **VPC**: Enabled with staging-connector
- **Resource Limits**: Standard Cloud Run configuration

**Exit Code 3 Context**:
- Proper error handling during startup failure detection
- Clean application shutdown rather than crash/kill
- Cloud Run restart loop until underlying dependency resolved

## Related Issues and Dependencies

### Direct Dependencies
- **Cluster 1 Monitoring Module Issue**: Must be resolved first
- Root cause import failure causing container startup abort

### Historical Context
- Database connectivity timeout issues (Issues #1263, #1278)
- SMD Phase 3 orchestration improvements
- Application startup sequence hardening

## Validation Checklist

### Post-Resolution Verification
- [ ] Container exit(3) frequency = 0 in 1-hour window
- [ ] Container instances maintain running state >4 hours
- [ ] No abnormal restart patterns in Cloud Run logs
- [ ] Load balancer health checks consistently pass
- [ ] Application startup logs show successful initialization
- [ ] No ModuleNotFoundError entries in application logs

---

**Issue Classification**: `claude-code-generated-issue`
**Cluster**: CLUSTER 2 - CONTAINER EXIT FAILURES
**Root Cause Dependency**: CLUSTER 1 - MONITORING MODULE IMPORT FAILURE
**Priority**: P1 High (Secondary effect of P0 root cause)
**Component**: Cloud Run, Container Runtime, Application Startup
**Resolution Dependency**: Must resolve Cluster 1 monitoring module issue first

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>