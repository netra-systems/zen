# Issue #1278 Infrastructure Remediation Plan

**PRIORITY:** P0 CRITICAL - Golden Path Blocked
**BUSINESS IMPACT:** $500K+ ARR services offline
**STATUS:** Infrastructure health below 70% (failing threshold)
**GENERATED:** 2025-09-15 20:06 UTC

---

## Executive Summary

**CONFIRMED ISSUE STATUS:**
- ✅ VPC connector connectivity failures (error code 10035)
- ✅ Cloud SQL connections at 88% utilization (critical threshold)
- ✅ Infrastructure health below 70% (failing threshold)
- ✅ Golden Path completely blocked (users cannot login → get AI responses)
- ✅ HTTP 503 Service Unavailable errors across critical endpoints
- ✅ Dual revision deployment causing resource contention

**ROOT CAUSE CONFIRMED:**
Based on comprehensive log analysis and infrastructure assessment:

1. **VPC Connector Issues**: Capacity/connectivity failures blocking Redis and Cloud SQL access
2. **Dual Revision Deployment**: Two active revisions (00749-6tr, 00750-69k) causing resource contention
3. **Cloud SQL Resource Constraints**: 88% utilization triggering connection failures
4. **Network Routing Failures**: Load balancer health checks failing with 2-12 second latencies
5. **Empty Logging Payloads**: 92% of error logs missing diagnostic information

---

## Immediate Infrastructure Fixes (P0 CRITICAL)

### 1. Resolve Dual Revision Deployment State
**ISSUE:** Two active Cloud Run revisions causing resource contention and 503 errors
**ROOT CAUSE:** Incomplete deployment or rollback scenario

**IMPLEMENTATION:**
```bash
# 1. Check current revision status
gcloud run revisions list --service=netra-backend-staging --region=us-central1 --project=netra-staging

# 2. Identify active revisions and traffic allocation
gcloud run services describe netra-backend-staging --region=us-central1 --project=netra-staging --format="yaml"

# 3. Route 100% traffic to latest revision and delete old revision
gcloud run services update-traffic netra-backend-staging \
  --to-revisions=netra-backend-staging-00750-69k=100 \
  --region=us-central1 \
  --project=netra-staging

# 4. Delete old revision to free resources
gcloud run revisions delete netra-backend-staging-00749-6tr \
  --region=us-central1 \
  --project=netra-staging \
  --quiet
```

**VALIDATION:**
```bash
# Verify single active revision
gcloud run revisions list --service=netra-backend-staging --region=us-central1 --project=netra-staging --filter="status.conditions.type=Active"

# Test health endpoint immediately
curl -v https://api.staging.netrasystems.ai/health
```

### 2. VPC Connector Validation and Recreation
**ISSUE:** VPC connector capacity/connectivity issues blocking database access
**ROOT CAUSE:** Connector overload or misconfiguration

**IMPLEMENTATION:**
```bash
# 1. Check VPC connector status
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 \
  --project=netra-staging

# 2. Check connector utilization and health
gcloud logging read \
  'resource.type="vpc_access_connector" AND
   resource.labels.connector_name="staging-connector" AND
   timestamp>="2025-09-15T18:00:00Z"' \
  --project=netra-staging \
  --limit=50

# 3. If connector is overloaded, scale up capacity
gcloud compute networks vpc-access connectors update staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --max-instances=20 \
  --min-instances=4

# 4. If connector is failing, recreate it
# NOTE: This will cause brief service interruption
gcloud compute networks vpc-access connectors delete staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --quiet

# Apply terraform to recreate
cd terraform-gcp-staging
terraform apply -target=google_vpc_access_connector.staging_connector
```

**VALIDATION:**
```bash
# Verify connector operational
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --format="value(state)"

# Should return: READY
```

### 3. Cloud SQL Connection Optimization
**ISSUE:** Cloud SQL at 88% utilization causing connection failures
**ROOT CAUSE:** Connection pool exhaustion or query performance issues

**IMPLEMENTATION:**
```bash
# 1. Check current Cloud SQL connections
gcloud sql instances describe netra-staging-db \
  --project=netra-staging \
  --format="yaml" | grep -A 10 "settings:"

# 2. Increase max connections if needed
gcloud sql instances patch netra-staging-db \
  --project=netra-staging \
  --database-flags=max_connections=200

# 3. Check for long-running queries
gcloud sql operations list \
  --instance=netra-staging-db \
  --project=netra-staging \
  --filter="status=RUNNING"

# 4. Review connection pooling settings in application
# Update database timeout to 600s as per Issue #1278 requirements
```

**APPLICATION CONFIG UPDATE:**
```python
# netra_backend/app/core/configuration/database.py
DATABASE_CONFIG = {
    "connection_timeout": 600,  # Extended timeout
    "pool_size": 20,           # Increased pool size
    "max_overflow": 40,        # Allow overflow connections
    "pool_pre_ping": True,     # Validate connections
    "pool_recycle": 3600       # Recycle connections hourly
}
```

---

## Environment Configuration Fixes (P0 CRITICAL)

### 1. Staging Environment Variable Validation
**ISSUE:** Environment configuration gaps causing service failures

**IMPLEMENTATION:**
```bash
# 1. Validate critical environment variables are set
gcloud run services describe netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --format="yaml" | grep -A 50 "env:"

# 2. Update service with critical missing variables
gcloud run services update netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --set-env-vars="VPC_CONNECTOR_TIMEOUT=600,DATABASE_TIMEOUT=600"

# 3. Ensure demo mode is disabled for staging
gcloud run services update netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --set-env-vars="DEMO_MODE=0"
```

### 2. SSL Certificate and Domain Validation
**ISSUE:** SSL certificate failures for *.netrasystems.ai domains

**IMPLEMENTATION:**
```bash
# 1. Check SSL certificate status
gcloud compute ssl-certificates list --project=netra-staging

# 2. Verify certificate covers required domains
gcloud compute ssl-certificates describe staging-ssl-cert \
  --project=netra-staging \
  --format="value(subjectAlternativeNames[])"

# 3. Test SSL connectivity
openssl s_client -connect api.staging.netrasystems.ai:443 -servername api.staging.netrasystems.ai
```

---

## Service Recovery and Validation (P1 HIGH)

### 1. Staged Service Restart Approach
**ISSUE:** Services need coordinated restart to apply fixes

**IMPLEMENTATION:**
```bash
# 1. Restart backend service with new configuration
gcloud run services replace-traffic netra-backend-staging \
  --to-latest \
  --region=us-central1 \
  --project=netra-staging

# 2. Wait for service to become ready
sleep 30

# 3. Validate health endpoint
for i in {1..10}; do
  echo "Health check attempt $i"
  curl -f https://api.staging.netrasystems.ai/health || echo "Failed"
  sleep 5
done

# 4. Restart auth service if needed
gcloud run services replace-traffic auth-service-staging \
  --to-latest \
  --region=us-central1 \
  --project=netra-staging
```

### 2. Golden Path Restoration Validation
**ISSUE:** End-to-end user flow must be validated

**VALIDATION SCRIPT:**
```bash
#!/bin/bash
# Golden Path Validation Script

echo "=== Golden Path Validation ==="

# 1. Health Check
echo "1. Testing health endpoint..."
curl -f https://api.staging.netrasystems.ai/health
if [ $? -eq 0 ]; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed"
  exit 1
fi

# 2. WebSocket Connection
echo "2. Testing WebSocket endpoint..."
timeout 10 wscat -c wss://api-staging.netrasystems.ai/ws
if [ $? -eq 0 ]; then
  echo "✅ WebSocket connection successful"
else
  echo "❌ WebSocket connection failed"
fi

# 3. Database Connectivity
echo "3. Testing database connectivity..."
curl -f https://api.staging.netrasystems.ai/health/db
if [ $? -eq 0 ]; then
  echo "✅ Database connectivity confirmed"
else
  echo "❌ Database connectivity failed"
fi

# 4. Redis Connectivity
echo "4. Testing Redis connectivity..."
curl -f https://api.staging.netrasystems.ai/health/redis
if [ $? -eq 0 ]; then
  echo "✅ Redis connectivity confirmed"
else
  echo "❌ Redis connectivity failed"
fi

echo "=== Golden Path Validation Complete ==="
```

### 3. Performance Monitoring Implementation
**ISSUE:** Real-time monitoring needed to track recovery

**IMPLEMENTATION:**
```bash
# 1. Set up log-based metrics for 503 errors
gcloud logging metrics create http_503_errors \
  --description="Count of HTTP 503 errors" \
  --log-filter='resource.type="cloud_run_revision" AND httpRequest.status=503' \
  --project=netra-staging

# 2. Create alerting policy for critical errors
gcloud alpha monitoring policies create \
  --policy-from-file=alert-policy-503-errors.yaml \
  --project=netra-staging

# 3. Monitor VPC connector health
gcloud logging metrics create vpc_connector_errors \
  --description="VPC connector errors" \
  --log-filter='resource.type="vpc_access_connector" AND severity>=ERROR' \
  --project=netra-staging
```

---

## Prevention Measures (P2 MEDIUM)

### 1. Infrastructure Monitoring Improvements
**IMPLEMENTATION:**

```yaml
# alert-policy-503-errors.yaml
displayName: "HTTP 503 Error Rate Alert"
conditions:
  - displayName: "503 Error Rate > 5%"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND httpRequest.status=503'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 5
      duration: "300s"
alertStrategy:
  autoClose: "86400s"
notificationChannels:
  - "projects/netra-staging/notificationChannels/EMAIL_ALERT"
```

### 2. Capacity Planning Implementation
**IMPLEMENTATION:**

```bash
# 1. Set up capacity monitoring dashboard
gcloud monitoring dashboards create \
  --config-from-file=infrastructure-capacity-dashboard.json \
  --project=netra-staging

# 2. Implement auto-scaling rules
gcloud run services update netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --max-instances=100 \
  --min-instances=2 \
  --concurrency=80
```

### 3. Alert Threshold Optimization
**THRESHOLDS:**
- HTTP 503 errors: Alert at >5% error rate over 5 minutes
- Database connections: Alert at >75% utilization
- VPC connector: Alert at >80% capacity
- WebSocket failures: Alert at >10% failure rate
- Response latency: Alert at >10 second P95

---

## Execution Plan

### Phase 1: Immediate Stabilization (0-30 minutes)
```bash
# Execute in order - DO NOT SKIP STEPS

# Step 1: Fix dual revision deployment
echo "=== PHASE 1: IMMEDIATE STABILIZATION ==="
echo "Step 1: Resolving dual revision deployment..."
gcloud run services update-traffic netra-backend-staging \
  --to-revisions=netra-backend-staging-00750-69k=100 \
  --region=us-central1 \
  --project=netra-staging

# Step 2: Delete old revision
echo "Step 2: Removing old revision..."
gcloud run revisions delete netra-backend-staging-00749-6tr \
  --region=us-central1 \
  --project=netra-staging \
  --quiet

# Step 3: Immediate health check
echo "Step 3: Testing immediate recovery..."
curl -f https://api.staging.netrasystems.ai/health
```

### Phase 2: Infrastructure Validation (30-60 minutes)
```bash
echo "=== PHASE 2: INFRASTRUCTURE VALIDATION ==="

# Step 1: VPC connector health check
echo "Step 1: Checking VPC connector..."
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 \
  --project=netra-staging

# Step 2: Scale VPC connector if needed
echo "Step 2: Scaling VPC connector..."
gcloud compute networks vpc-access connectors update staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --max-instances=20 \
  --min-instances=4

# Step 3: Database optimization
echo "Step 3: Optimizing database connections..."
gcloud sql instances patch netra-staging-db \
  --project=netra-staging \
  --database-flags=max_connections=200
```

### Phase 3: Service Recovery (60-90 minutes)
```bash
echo "=== PHASE 3: SERVICE RECOVERY ==="

# Step 1: Update service configuration
echo "Step 1: Updating service configuration..."
gcloud run services update netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --set-env-vars="VPC_CONNECTOR_TIMEOUT=600,DATABASE_TIMEOUT=600,DEMO_MODE=0"

# Step 2: Restart services
echo "Step 2: Restarting services..."
gcloud run services replace-traffic netra-backend-staging \
  --to-latest \
  --region=us-central1 \
  --project=netra-staging

# Step 3: Comprehensive validation
echo "Step 3: Running Golden Path validation..."
./golden-path-validation.sh
```

### Phase 4: Monitoring Setup (90-120 minutes)
```bash
echo "=== PHASE 4: MONITORING SETUP ==="

# Step 1: Create error metrics
gcloud logging metrics create http_503_errors \
  --description="Count of HTTP 503 errors" \
  --log-filter='resource.type="cloud_run_revision" AND httpRequest.status=503' \
  --project=netra-staging

# Step 2: Set up alerting
gcloud alpha monitoring policies create \
  --policy-from-file=alert-policy-503-errors.yaml \
  --project=netra-staging

# Step 3: Validate monitoring
echo "Step 3: Validating monitoring setup..."
gcloud logging metrics list --project=netra-staging
```

---

## Rollback Procedures

### If Phase 1 Fails (Dual Revision Fix)
```bash
# Rollback: Restore original traffic split
gcloud run services update-traffic netra-backend-staging \
  --to-revisions=netra-backend-staging-00749-6tr=50,netra-backend-staging-00750-69k=50 \
  --region=us-central1 \
  --project=netra-staging

# Investigate why latest revision is failing
gcloud logging read \
  'resource.type="cloud_run_revision" AND
   resource.labels.revision_name="netra-backend-staging-00750-69k" AND
   severity>=ERROR' \
  --project=netra-staging \
  --limit=20
```

### If Phase 2 Fails (VPC Connector)
```bash
# Rollback: Restore original VPC connector settings
gcloud compute networks vpc-access connectors update staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --max-instances=10 \
  --min-instances=2

# If database changes fail
gcloud sql instances patch netra-staging-db \
  --project=netra-staging \
  --database-flags=max_connections=100
```

### If Phase 3 Fails (Service Recovery)
```bash
# Rollback: Remove problematic environment variables
gcloud run services update netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --remove-env-vars="VPC_CONNECTOR_TIMEOUT,DATABASE_TIMEOUT"

# Force rollback to previous working revision
gcloud run services update-traffic netra-backend-staging \
  --to-revisions=netra-backend-staging-00749-6tr=100 \
  --region=us-central1 \
  --project=netra-staging
```

---

## Success Criteria

### Phase 1 Success Metrics
- ✅ Single active Cloud Run revision
- ✅ HTTP 503 errors eliminated
- ✅ Health endpoint responding < 2 seconds
- ✅ No revision-related resource contention

### Phase 2 Success Metrics
- ✅ VPC connector status: READY
- ✅ Database connections < 75% utilization
- ✅ No VPC connectivity errors in logs
- ✅ SSL certificates valid for all domains

### Phase 3 Success Metrics
- ✅ WebSocket connections successful
- ✅ Golden Path validation passes end-to-end
- ✅ All health endpoints operational
- ✅ No service startup errors

### Phase 4 Success Metrics
- ✅ Error monitoring active
- ✅ Alert policies configured
- ✅ Capacity thresholds established
- ✅ Dashboard monitoring operational

---

## Post-Remediation Validation

### Comprehensive Health Check
```bash
#!/bin/bash
# Post-Remediation Validation Script

echo "=== POST-REMEDIATION VALIDATION ==="

# 1. Service Health
echo "1. Checking service health..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.staging.netrasystems.ai/health)
if [ "$HEALTH_STATUS" = "200" ]; then
  echo "✅ Health endpoint: OK"
else
  echo "❌ Health endpoint: FAILED ($HEALTH_STATUS)"
fi

# 2. WebSocket Connectivity
echo "2. Testing WebSocket connectivity..."
timeout 10 wscat -c wss://api-staging.netrasystems.ai/ws -x '{"type":"ping"}' > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "✅ WebSocket: OK"
else
  echo "❌ WebSocket: FAILED"
fi

# 3. Database Connectivity
echo "3. Testing database connectivity..."
DB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.staging.netrasystems.ai/health/db)
if [ "$DB_STATUS" = "200" ]; then
  echo "✅ Database: OK"
else
  echo "❌ Database: FAILED ($DB_STATUS)"
fi

# 4. VPC Connector Status
echo "4. Checking VPC connector..."
VPC_STATUS=$(gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 \
  --project=netra-staging \
  --format="value(state)" 2>/dev/null)
if [ "$VPC_STATUS" = "READY" ]; then
  echo "✅ VPC Connector: READY"
else
  echo "❌ VPC Connector: $VPC_STATUS"
fi

# 5. Error Rate Check
echo "5. Checking recent error rates..."
ERROR_COUNT=$(gcloud logging read \
  'resource.type="cloud_run_revision" AND httpRequest.status=503 AND timestamp>="'$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')'"' \
  --project=netra-staging \
  --format="value(timestamp)" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
  echo "✅ Error Rate: No 503 errors in last 5 minutes"
else
  echo "⚠️ Error Rate: $ERROR_COUNT 503 errors in last 5 minutes"
fi

echo "=== VALIDATION COMPLETE ==="
```

---

## Contact and Escalation

### Immediate Escalation Triggers
- Any step fails with rollback unsuccessful
- Service remains unavailable after Phase 1
- VPC connector cannot be restored
- Database connections remain above 90%

### Success Confirmation
Upon successful completion:
1. All health endpoints responding < 2 seconds
2. WebSocket connections successful
3. Zero HTTP 503 errors for 10 minutes
4. Database utilization < 75%
5. Golden Path validation passes end-to-end

**BUSINESS IMPACT RESOLUTION:** Successful execution restores $500K+ ARR services and unblocks Golden Path user flow (login → AI responses).

---

**Document Status:** READY FOR EXECUTION
**Estimated Total Time:** 2 hours
**Risk Level:** MEDIUM (with comprehensive rollback procedures)
**Business Priority:** P0 CRITICAL