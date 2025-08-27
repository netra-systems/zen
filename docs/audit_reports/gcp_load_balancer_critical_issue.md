# GCP Load Balancer Critical Configuration Issue - Staging Environment

**Date:** 2025-08-27  
**Severity:** CRITICAL  
**Environment:** Staging (*.staging.netrasystems.ai)  
**Impact:** Complete service outage - application non-functional

## Executive Summary

The GCP Load Balancer in staging is incorrectly configured, causing HTTPS-to-HTTP protocol downgrade and WebSocket connection failures. This results in browser security blocks (mixed content) making the application completely unusable.

## Critical Issues Identified

### 1. HTTPS → HTTP Protocol Downgrade
**Evidence:**
- Frontend requests: `https://api.staging.netrasystems.ai/api/threads`
- Browser blocks: `http://api.staging.netrasystems.ai/api/threads`
- Error: "Mixed Content: The page was loaded over HTTPS, but requested an insecure resource"

**Root Cause:**
- Load balancer terminating SSL but forwarding as HTTP to backend
- Missing protocol preservation headers
- Backend service not configured for HTTPS ingress

### 2. WebSocket Connection Failures
**Evidence:**
- WSS connection attempts: `wss://api.staging.netrasystems.ai/ws`
- Failure: Error code 1006 (abnormal closure)
- Authentication errors immediately after handshake

**Root Cause:**
- Load balancer not configured for WebSocket protocol upgrade
- Missing WebSocket-specific headers preservation
- Potential timeout on long-lived connections

### 3. CORS Preflight Failures
**Evidence:**
- OPTIONS requests failing or returning incorrect headers
- Authentication headers being stripped

**Root Cause:**
- Load balancer not properly handling CORS preflight requests
- Backend CORS configuration not matching load balancer behavior

## Staging-Specific Remediation Actions

### IMMEDIATE ACTION #1: Fix Load Balancer Backend Configuration

**Via GCP Console:**
```bash
# 1. Navigate to Load Balancing
gcloud compute backend-services list --project=netra-staging

# 2. Update backend service protocol
gcloud compute backend-services update netra-backend-service \
  --project=netra-staging \
  --protocol=HTTPS \
  --global

# 3. Update health checks to use HTTPS
gcloud compute health-checks update https netra-backend-health \
  --project=netra-staging \
  --port=8080 \
  --request-path=/health
```

### IMMEDIATE ACTION #2: Configure WebSocket Support

**Update Backend Service Configuration:**
```yaml
apiVersion: cloud.google.com/v1
kind: BackendConfig
metadata:
  name: netra-backend-config
  namespace: staging
spec:
  timeoutSec: 3600  # 1 hour for WebSocket connections
  connectionDraining:
    drainingTimeoutSec: 60
  sessionAffinity:
    affinityType: "GENERATED_COOKIE"
    affinityCookieTtlSec: 3600
  customRequestHeaders:
    headers:
    - "X-Forwarded-Proto: {scheme}"
    - "X-Forwarded-For: {client_ip}"
    - "X-Real-IP: {client_ip}"
```

**Apply to Cloud Run Service:**
```bash
gcloud run services update netra-backend \
  --project=netra-staging \
  --region=us-central1 \
  --annotations='run.googleapis.com/config-files=backend-config.yaml' \
  --ingress=all \
  --allow-unauthenticated
```

### IMMEDIATE ACTION #3: Update Cloud Run Service for HTTPS

**Deploy with HTTPS Configuration:**
```bash
# Update service with proper configuration
gcloud run deploy netra-backend \
  --project=netra-staging \
  --region=us-central1 \
  --image=gcr.io/netra-staging/netra-backend:latest \
  --port=8080 \
  --ingress=all \
  --allow-unauthenticated \
  --set-env-vars="FORCE_HTTPS=true,ENVIRONMENT=staging" \
  --service-account=netra-backend-sa@netra-staging.iam.gserviceaccount.com \
  --max-instances=10 \
  --min-instances=1 \
  --cpu=2 \
  --memory=4Gi \
  --timeout=3600
```

### ACTION #4: Configure NEG (Network Endpoint Group) for WebSocket

```bash
# Create or update NEG for Cloud Run
gcloud compute network-endpoint-groups create netra-backend-neg \
  --project=netra-staging \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=netra-backend

# Attach to backend service
gcloud compute backend-services add-backend netra-backend-service \
  --project=netra-staging \
  --global \
  --network-endpoint-group=netra-backend-neg \
  --network-endpoint-group-region=us-central1
```

### ACTION #5: Update URL Map Rules

```bash
# Update URL map to handle WebSocket upgrade
gcloud compute url-maps edit netra-url-map --project=netra-staging
```

Add WebSocket path matcher:
```yaml
pathMatchers:
- name: websocket-matcher
  defaultService: global/backendServices/netra-backend-service
  pathRules:
  - paths: ["/ws", "/ws/*", "/websocket", "/websocket/*"]
    service: global/backendServices/netra-backend-service
    routeAction:
      timeout: 3600s
      corsPolicy:
        allowOrigins: ["https://app.staging.netrasystems.ai"]
        allowMethods: ["GET", "POST", "OPTIONS"]
        allowHeaders: ["*"]
        allowCredentials: true
```

### ACTION #6: Frontend Emergency Patch (Temporary)

While waiting for infrastructure fixes, deploy this frontend patch:

**File:** `frontend/lib/api-request-wrapper.ts`
```typescript
// Emergency staging fix - force HTTPS
export function ensureHttpsUrl(url: string): string {
  if (typeof window !== 'undefined' && 
      window.location.hostname.includes('staging.netrasystems.ai')) {
    return url.replace(/^http:/, 'https:').replace(/^ws:/, 'wss:');
  }
  return url;
}
```

### ACTION #7: Verify SSL Certificates

```bash
# Check SSL certificate status
gcloud compute ssl-certificates describe netra-staging-cert \
  --project=netra-staging

# If expired or missing, create new
gcloud compute ssl-certificates create netra-staging-cert-new \
  --project=netra-staging \
  --domains=app.staging.netrasystems.ai,api.staging.netrasystems.ai,auth.staging.netrasystems.ai
```

## Validation Steps

### 1. Test HTTPS Backend Connection
```bash
# Should return HTTPS URL in Location header if any redirects
curl -I https://api.staging.netrasystems.ai/health

# Should see X-Forwarded-Proto: https
curl -v https://api.staging.netrasystems.ai/health 2>&1 | grep -i x-forwarded
```

### 2. Test WebSocket Connection
```javascript
// Run in browser console
const testWs = new WebSocket('wss://api.staging.netrasystems.ai/ws');
testWs.onopen = () => console.log('SUCCESS: WebSocket connected');
testWs.onerror = (e) => console.error('FAIL: WebSocket error', e);
testWs.onclose = (e) => console.log('WebSocket closed', e.code, e.reason);
```

### 3. Test CORS Headers
```bash
curl -X OPTIONS https://api.staging.netrasystems.ai/api/threads \
  -H "Origin: https://app.staging.netrasystems.ai" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v 2>&1 | grep -i access-control
```

## Monitoring Dashboard Commands

```bash
# Monitor load balancer logs
gcloud logging read "resource.type=http_load_balancer AND resource.labels.forwarding_rule_name=netra-staging-forwarding-rule" \
  --project=netra-staging \
  --limit=50 \
  --format=json | jq '.[] | {timestamp: .timestamp, status: .httpRequest.status, protocol: .httpRequest.protocol, path: .httpRequest.requestUrl}'

# Monitor backend service health
gcloud compute backend-services get-health netra-backend-service \
  --project=netra-staging \
  --global
```

## Rollback Plan

If issues persist after changes:

1. **Revert to HTTP internally** (not recommended):
   ```bash
   gcloud compute backend-services update netra-backend-service \
     --project=netra-staging \
     --protocol=HTTP \
     --global
   ```

2. **Create new load balancer** from scratch with correct configuration

3. **Use Cloud Run direct URL** temporarily:
   - Update frontend to use: `https://netra-backend-xxxxx-uc.a.run.app`

## Success Criteria

- [ ] No mixed content errors in browser console
- [ ] WebSocket connections establish and maintain for >60 seconds
- [ ] All API calls use HTTPS throughout the chain
- [ ] CORS preflight requests return proper headers
- [ ] Authentication flow works end-to-end
- [ ] Real-time updates via WebSocket functional

## Escalation Path

1. **First 15 minutes:** Try emergency frontend patch
2. **Next 30 minutes:** Apply load balancer configuration fixes
3. **If still failing:** Create new load balancer from scratch
4. **Emergency:** Switch to Cloud Run direct URLs (bypass load balancer)

## Contact Information

- **Infrastructure Lead:** DevOps Team
- **GCP Project:** netra-staging (Project ID: 701982941522)
- **Region:** us-central1
- **Support Ticket:** File under "Critical - Production Down"