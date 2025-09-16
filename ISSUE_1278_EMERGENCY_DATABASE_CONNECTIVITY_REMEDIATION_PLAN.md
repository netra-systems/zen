# Issue #1278 Emergency Database Connectivity Remediation Plan

**Created:** 2025-09-15 20:45
**Priority:** P0 CRITICAL - Emergency Database Connectivity Outage
**Business Impact:** $500K+ ARR services offline in staging environment
**Root Cause:** Regression of Issue #1263 database timeout/VPC connector configuration

## EMERGENCY STATUS

**CURRENT STATE:** CRITICAL DATABASE CONNECTIVITY OUTAGE
- **Staging Environment:** Complete database connectivity failure
- **Chat Functionality:** OFFLINE (90% of business value affected)
- **Test Infrastructure:** Also failing due to environment configuration issues
- **User Impact:** Unable to login or get AI responses in staging

## EXECUTIVE SUMMARY

Issue #1278 is a confirmed regression of Issue #1263's database timeout and VPC connector fixes. The staging environment has lost database connectivity, causing complete service outage. Analysis shows:

1. **VPC Connector Issues:** Potential capacity constraints or configuration drift
2. **Database Timeout Regression:** Staging timeouts may have reverted from 75.0s to lower values
3. **Cloud SQL Connectivity:** Network routing issues between Cloud Run and Cloud SQL
4. **Environment Configuration:** Missing or incorrect environment variables

## PHASE 1: IMMEDIATE EMERGENCY FIXES (0-2 hours)

### 1.1 Database Timeout Configuration Restoration (30 minutes)

**Priority:** IMMEDIATE - Apply known working configuration from Issue #1263

#### Commands to Execute:
```bash
# 1. Verify current timeout configuration in staging
python -c "
from netra_backend.app.core.database_timeout_config import get_database_timeout_config
config = get_database_timeout_config('staging')
print('Current staging timeout config:', config)
"

# 2. Check if timeout regression occurred
# Expected values from Issue #1263 resolution:
# - initialization_timeout: 75.0s (was increased from 25.0s)
# - connection_timeout: 35.0s
# - pool_timeout: 45.0s
```

#### Remediation Actions:
1. **Validate timeout configuration** in `C:\netra-apex\netra_backend\app\core\database_timeout_config.py`
2. **Confirm staging values** match Issue #1263 resolution:
   - `initialization_timeout: 75.0` (NOT 25.0 or 15.0)
   - `connection_timeout: 35.0` (NOT 15.0 or 20.0)
   - `pool_timeout: 45.0` (NOT 30.0)

**Expected Fix:** If timeout values have regressed, they must be restored to Issue #1263 working values.

### 1.2 VPC Connector Configuration Validation (45 minutes)

**Priority:** CRITICAL - VPC connector required for Cloud SQL access

#### Infrastructure Validation Commands:
```bash
# 1. Check VPC connector status
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 --project=netra-staging

# 2. Verify VPC connector capacity
gcloud compute networks vpc-access connectors list \
  --project=netra-staging --filter="name:staging-connector"

# 3. Check Cloud Run service VPC configuration
gcloud run services describe netra-backend-staging \
  --region=us-central1 --project=netra-staging \
  --format="yaml(spec.template.metadata.annotations)"
```

#### Expected Configuration:
- **VPC Connector Name:** `staging-connector`
- **VPC Egress:** `all-traffic`
- **Network:** `staging-vpc`
- **IP CIDR Range:** `10.1.0.0/28`
- **Status:** `READY` with sufficient capacity

#### Remediation Actions:
1. **If VPC connector is down:** Redeploy using Terraform configuration
2. **If connector capacity is exhausted:** Scale up min/max instances
3. **If Cloud Run missing VPC annotations:** Redeploy with correct VPC settings

### 1.3 Cloud SQL Instance Health Check (30 minutes)

**Priority:** HIGH - Verify database service availability

#### Health Check Commands:
```bash
# 1. Check Cloud SQL instance status
gcloud sql instances describe netra-staging-db --project=netra-staging

# 2. Verify connection limits and current connections
gcloud sql instances get-connection-info netra-staging-db --project=netra-staging

# 3. Test direct connectivity from Cloud Shell
gcloud sql connect netra-staging-db --user=netra_user --project=netra-staging
```

#### Expected Status:
- **Instance State:** `RUNNABLE`
- **Connection Limit:** Not exceeded (should be <100 connections)
- **Network Configuration:** Private IP enabled, authorized networks configured
- **Backup Status:** Recent successful backup

#### Remediation Actions:
1. **If instance is down:** Start Cloud SQL instance
2. **If connection limit exceeded:** Kill idle connections or scale up instance
3. **If network configuration wrong:** Fix authorized networks and private IP

### 1.4 Environment Variable Validation (15 minutes)

**Priority:** HIGH - Ensure proper staging environment configuration

#### Configuration Check Commands:
```bash
# 1. Check Cloud Run environment variables
gcloud run services describe netra-backend-staging \
  --region=us-central1 --project=netra-staging \
  --format="yaml(spec.template.spec.containers[0].env)"

# 2. Verify Secret Manager secrets
gcloud secrets versions access latest --secret="database-url" --project=netra-staging
gcloud secrets versions access latest --secret="jwt-secret-key" --project=netra-staging
```

#### Required Environment Variables:
- `ENVIRONMENT=staging`
- `DATABASE_URL=postgresql+asyncpg://[connection_string]`
- `JWT_SECRET_KEY=[from_secret_manager]`
- `REDIS_URL=[staging_redis_instance]`

#### Remediation Actions:
1. **Missing variables:** Add to Cloud Run deployment configuration
2. **Incorrect values:** Update Secret Manager secrets
3. **Wrong environment:** Ensure `ENVIRONMENT=staging` is set

## PHASE 2: INFRASTRUCTURE RESTORATION (2-4 hours)

### 2.1 VPC Connector Deployment Verification (60 minutes)

**Terraform Configuration Check:**
```bash
# 1. Navigate to Terraform directory
cd C:\netra-apex\terraform-gcp-staging

# 2. Verify VPC connector configuration
terraform plan -target=google_vpc_access_connector.staging_connector

# 3. Apply if needed
terraform apply -target=google_vpc_access_connector.staging_connector
```

**Expected Terraform Output:**
- VPC connector exists and is configured correctly
- No changes needed (infrastructure matches code)
- If changes detected: Apply immediately

### 2.2 Cloud Run Service Redeployment (90 minutes)

**Deploy with VPC Connector Configuration:**
```bash
# 1. Deploy backend service with emergency fixes
python scripts/deploy_to_gcp.py \
  --project netra-staging \
  --build-local \
  --services backend \
  --emergency-mode

# 2. Verify deployment success
python scripts/validate_staging_deployment.py --service backend

# 3. Check health endpoints
curl -f https://backend.staging.netrasystems.ai/health
```

**Critical Deployment Parameters:**
- VPC connector: `staging-connector`
- VPC egress: `all-traffic`
- Memory: `4Gi` (increased for WebSocket reliability)
- CPU: `4` (increased for async processing)
- Min instances: `1` (ensure always running)

### 2.3 Database Connection Pool Configuration (30 minutes)

**Pool Optimization for Issue #1278:**
```python
# Apply Cloud SQL capacity-aware configuration
# File: netra_backend/app/core/database_timeout_config.py
# Lines 318-329: Reduced pool sizes for VPC connector capacity

pool_config = {
    "pool_size": 10,              # Reduced from 15
    "max_overflow": 15,           # Reduced from 25
    "pool_timeout": 90.0,         # Increased from 60.0
    "vpc_connector_capacity_buffer": 5,
    "capacity_safety_margin": 0.8
}
```

**Remediation Action:** Ensure pool configuration respects VPC connector and Cloud SQL capacity limits.

## PHASE 3: SYSTEM RESTORATION VALIDATION (4-6 hours)

### 3.1 Service Health Validation (60 minutes)

**Comprehensive Health Check:**
```bash
# 1. All service health endpoints
curl -f https://backend.staging.netrasystems.ai/health
curl -f https://auth.staging.netrasystems.ai/health
curl -f https://app.staging.netrasystems.ai/

# 2. Database connectivity test
python -c "
import asyncio
from netra_backend.app.db.database_manager import get_database_manager
async def test_db():
    db = get_database_manager()
    result = await db.health_check()
    print('Database health:', result)
asyncio.run(test_db())
"

# 3. WebSocket functionality test
python tests/mission_critical/test_websocket_agent_events_suite.py
```

**Success Criteria:**
- All health endpoints return 200 OK
- Database connections establish within timeout limits
- WebSocket events working correctly
- No CRITICAL errors in logs

### 3.2 Golden Path User Flow Test (45 minutes)

**End-to-End Validation:**
```bash
# 1. Test complete user authentication flow
python tests/e2e/test_auth_backend_desynchronization.py

# 2. Test chat functionality
python tests/e2e/test_websocket_dev_docker_connection.py

# 3. Test agent execution
python tests/mission_critical/test_websocket_agent_events_suite.py
```

**Success Criteria:**
- Users can login successfully
- Chat interface loads and responds
- AI agents return meaningful responses
- Real-time progress updates work

### 3.3 Performance Monitoring Setup (30 minutes)

**Enable Connection Monitoring:**
```python
# Register connection performance monitoring
from netra_backend.app.core.database_timeout_config import (
    register_connection_alert_handler,
    log_connection_performance_summary
)

def alert_handler(environment, alert_data):
    if alert_data['level'] == 'critical':
        print(f"CRITICAL DB ALERT in {environment}: {alert_data['message']}")

register_connection_alert_handler(alert_handler)
log_connection_performance_summary('staging')
```

**Monitoring Setup:** Ensure alerts fire for connection times >20s warning, >25s critical.

## SPECIFIC COMMANDS FOR IMMEDIATE EXECUTION

### Emergency Fix Sequence (Execute in Order):

```bash
# STEP 1: Check current staging database timeout configuration
python -c "
from netra_backend.app.core.database_timeout_config import get_database_timeout_config
config = get_database_timeout_config('staging')
print('Current staging config:', config)
expected = {'initialization_timeout': 75.0, 'connection_timeout': 35.0, 'pool_timeout': 45.0}
for key, expected_val in expected.items():
    actual_val = config.get(key, 0)
    status = 'OK' if actual_val == expected_val else 'REGRESSION'
    print(f'{key}: {actual_val}s (expected {expected_val}s) - {status}')
"

# STEP 2: Redeploy backend with emergency database timeout configuration
python scripts/deploy_to_gcp.py \
  --project netra-staging \
  --build-local \
  --services backend \
  --check-apis \
  --emergency-deployment

# STEP 3: Validate VPC connector configuration
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --format="table(name,state,ipCidrRange,minInstances,maxInstances)"

# STEP 4: Test database connectivity immediately
python -c "
import asyncio
from netra_backend.app.smd import create_deterministic_startup_manager
async def test_startup():
    startup_manager = create_deterministic_startup_manager()
    try:
        result = await startup_manager.initialize_database_connections('staging', timeout=75.0)
        print('Database startup result:', result)
    except Exception as e:
        print('Database startup failed:', str(e))
asyncio.run(test_startup())
"

# STEP 5: Validate staging health endpoints
curl -f https://backend.staging.netrasystems.ai/health && echo "Backend: OK" || echo "Backend: FAILED"
curl -f https://auth.staging.netrasystems.ai/health && echo "Auth: OK" || echo "Auth: FAILED"
```

### Emergency Rollback Commands (If Fixes Fail):

```bash
# ROLLBACK OPTION 1: Revert to last known working deployment
python scripts/deploy_to_gcp.py --project netra-staging --rollback

# ROLLBACK OPTION 2: Deploy with maximum timeout values
# Edit database_timeout_config.py to use production timeouts (90.0s) for staging
# Then redeploy with extended timeouts

# ROLLBACK OPTION 3: Scale down and restart services
gcloud run services update netra-backend-staging \
  --min-instances=0 \
  --max-instances=1 \
  --region=us-central1 \
  --project=netra-staging

sleep 30

gcloud run services update netra-backend-staging \
  --min-instances=1 \
  --max-instances=10 \
  --region=us-central1 \
  --project=netra-staging
```

## VALIDATION CRITERIA FOR RESOLUTION

### Critical Success Metrics:
1. **Database Connectivity:** Connection establishment <35s consistently
2. **Service Health:** All health endpoints return 200 within 10s
3. **Golden Path:** Complete user login → AI response flow works
4. **WebSocket Events:** All 5 business-critical events firing correctly
5. **No Regressions:** Test suite passes without infrastructure failures

### Business Success Metrics:
1. **Chat Functionality:** Users receive meaningful AI responses
2. **Response Time:** AI responses generated within 30s
3. **User Experience:** No timeout errors or connection failures
4. **System Stability:** 30 minutes of continuous operation without errors

## EXPECTED RESOLUTION TIMELINE

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| **Emergency Fixes** | 2 hours | Database timeout + VPC connector restoration |
| **Infrastructure** | 2 hours | Redeployment with correct configuration |
| **Validation** | 2 hours | End-to-end testing and monitoring setup |
| **Total** | **6 hours** | Complete service restoration |

## PREVENTION MEASURES

### Immediate (Post-Resolution):
1. **Monitoring Alerts:** Set up proactive database timeout monitoring
2. **Configuration Management:** Lock staging timeout configuration
3. **Health Checks:** Enhanced health endpoints with VPC connector status
4. **Documentation:** Update runbooks with Issue #1278 resolution steps

### Long-term (Next Sprint):
1. **Automated Recovery:** Auto-scaling and auto-remediation for VPC connector issues
2. **Capacity Planning:** VPC connector capacity monitoring and alerting
3. **Environment Parity:** Ensure staging configuration matches production patterns
4. **Regression Testing:** Automated tests to prevent Issue #1263 regression

## ESCALATION PLAN

### If Emergency Fixes Fail (2 hours):
1. **Executive Notification:** Alert engineering leadership of critical outage
2. **External Support:** Engage Google Cloud Support for VPC connector issues
3. **Alternative Architecture:** Consider temporary bypass of VPC connector
4. **Business Continuity:** Prepare communication for user impact

### If Infrastructure Restoration Fails (4 hours):
1. **Architecture Review:** Evaluate alternative VPC connector configuration
2. **Cloud SQL Migration:** Consider different Cloud SQL configuration
3. **Staging Rebuild:** Complete infrastructure rebuild if necessary
4. **Production Impact Assessment:** Ensure production is protected from same issue

## RESPONSIBLE PARTIES

- **Primary Owner:** Platform Engineering Team
- **Escalation Contact:** Engineering Leadership
- **Business Stakeholder:** Product Team (user impact communication)
- **External Support:** Google Cloud Support (VPC connector expertise)

---

## APPENDIX: Issue #1263 Resolution Reference

### Working Configuration (DO NOT CHANGE):
```python
# File: netra_backend/app/core/database_timeout_config.py
# Lines 258-270: CRITICAL staging configuration

"staging": {
    "initialization_timeout": 75.0,    # CRITICAL: Do not reduce
    "table_setup_timeout": 25.0,       # Extended for load conditions
    "connection_timeout": 35.0,        # VPC connector peak scaling delays
    "pool_timeout": 45.0,              # Connection pool + VPC delays
    "health_check_timeout": 20.0,      # Compound infrastructure checks
}
```

### VPC Connector Configuration (DO NOT CHANGE):
```bash
# Cloud Run annotations that MUST be present:
run.googleapis.com/vpc-access-connector=staging-connector
run.googleapis.com/vpc-access-egress=all-traffic
```

### Cloud SQL Pool Configuration (DO NOT CHANGE):
```python
# File: netra_backend/app/core/database_timeout_config.py
# Lines 318-329: Capacity-aware configuration

"pool_config": {
    "pool_size": 10,              # Reduced for VPC connector capacity
    "max_overflow": 15,           # Reduced for Cloud SQL limits
    "pool_timeout": 90.0,         # Extended for compound delays
    "capacity_safety_margin": 0.8 # Use only 80% of available connections
}
```

**CRITICAL WARNING:** Any changes to these values may cause immediate regression to Issue #1278 database connectivity outage.

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>