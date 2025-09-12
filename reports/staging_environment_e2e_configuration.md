# Staging Environment E2E Configuration Requirements

**Date**: 2025-01-08  
**Purpose**: Configure staging environment for proper E2E testing support after Factory SSOT and Auth fixes  
**Business Impact**: Enables testing of $120K+ MRR WebSocket chat functionality in staging

## Required Environment Variables

### Core E2E Testing Variables
```bash
# Primary E2E testing indicators
E2E_TESTING=1
STAGING_E2E_TEST=1
E2E_TEST_ENV=staging

# E2E OAuth simulation key for bypass
E2E_OAUTH_SIMULATION_KEY=staging_e2e_bypass_key_12345

# Test execution indicators (for pytest compatibility)
PYTEST_RUNNING=0  # Only set to 1 during actual pytest runs
```

### Environment Detection Variables
```bash
# Core environment identification
ENVIRONMENT=staging

# GCP Cloud Run indicator (automatically set by GCP)
K_SERVICE=netra-backend  # Set automatically by Cloud Run

# Database and service configuration
DATABASE_URL=postgresql://[staging-credentials]
REDIS_URL=redis://[staging-redis]
```

### WebSocket Testing Configuration
```bash
# WebSocket-specific E2E support
WEBSOCKET_E2E_ENABLED=true
WEBSOCKET_AUTH_BYPASS_STAGING=true

# Testing timeouts and retry settings
E2E_AUTH_TIMEOUT=30
E2E_WEBSOCKET_TIMEOUT=45
```

## GCP Cloud Run Deployment Configuration

### Container Environment Variables
```yaml
# In your Cloud Run service configuration
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      containers:
      - image: gcr.io/netra-staging/backend
        env:
        - name: ENVIRONMENT
          value: "staging"
        - name: E2E_TESTING
          value: "1"
        - name: STAGING_E2E_TEST
          value: "1"
        - name: E2E_TEST_ENV
          value: "staging"
        - name: E2E_OAUTH_SIMULATION_KEY
          valueFrom:
            secretKeyRef:
              name: staging-secrets
              key: e2e-oauth-key
```

### Secret Configuration
```bash
# Create staging secrets for E2E testing
gcloud secrets create staging-e2e-oauth-key --data-file=e2e_key.txt --project=netra-staging

# Grant access to Cloud Run service
gcloud secrets add-iam-policy-binding staging-e2e-oauth-key \
    --member="serviceAccount:staging-backend@netra-staging.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Header Configuration for Load Balancer

### GCP Load Balancer Header Forwarding
```yaml
# Ensure E2E test headers are forwarded to backend
# In your load balancer configuration
forwarded_headers:
  - "X-E2E-Test"
  - "X-Test-Environment" 
  - "X-Test-Type"
  - "X-Test-Mode"
  - "Authorization"
```

### Ingress Configuration (if using GKE)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Forwarded-Headers: X-E2E-Test,X-Test-Environment";
```

## Test Client Configuration

### WebSocket Client Headers
```javascript
// Example WebSocket client configuration for E2E tests
const headers = {
    'X-E2E-Test': 'true',
    'X-Test-Environment': 'staging',
    'X-Test-Type': 'e2e',
    'Authorization': 'Bearer staging-e2e-user-003-token'
};

const ws = new WebSocket('wss://staging.netrasystems.ai/websocket', {
    headers: headers
});
```

### HTTP Client Headers
```python
# Example requests configuration for E2E tests
headers = {
    'X-E2E-Test': 'true',
    'X-Test-Environment': 'staging',
    'X-Test-Type': 'e2e',
    'Authorization': 'Bearer staging-e2e-user-003-token'
}

response = requests.post('https://staging.netrasystems.ai/api/test', headers=headers)
```

## Validation Steps

### 1. Environment Variable Verification
```bash
# Check if staging environment has required variables
curl -H "X-E2E-Test: true" https://staging.netrasystems.ai/health/e2e-config

# Expected response:
{
    "e2e_testing_enabled": true,
    "environment": "staging", 
    "e2e_detection_methods": {
        "via_headers": true,
        "via_environment": true
    },
    "bypass_enabled": true
}
```

### 2. WebSocket Connection Test
```python
# Test WebSocket connection with E2E headers
import asyncio
import websockets

async def test_e2e_websocket():
    headers = {
        'X-E2E-Test': 'true',
        'X-Test-Environment': 'staging',
        'Authorization': 'Bearer staging-e2e-user-003-token'
    }
    
    async with websockets.connect(
        'wss://staging.netrasystems.ai/websocket',
        extra_headers=headers
    ) as ws:
        # Should connect successfully without 1008/1011 errors
        welcome = await ws.recv()
        print(f"Connected: {welcome}")

asyncio.run(test_e2e_websocket())
```

### 3. E2E Test Suite Execution
```bash
# Run staging E2E tests to validate fixes
python tests/unified_test_runner.py \
    --category e2e \
    --env staging \
    --real-services \
    --target-modules test_websocket_events_staging test_agent_pipeline_staging
```

## Monitoring and Debugging

### Log Filters for E2E Testing
```bash
# GCP Cloud Logging filter for E2E test logs
resource.type="cloud_run_revision"
resource.labels.service_name="netra-backend"
jsonPayload.message:("E2E BYPASS" OR "STAGING ACCOMMODATION" OR "ENHANCED STAGING")
```

### Key Log Messages to Monitor
```
✅ Success Indicators:
- "E2E CONTEXT DETECTED: {'via_headers': True, 'via_environment': True}"
- "E2E BYPASS: Using mock authentication for E2E testing"
- "ENHANCED STAGING SUCCESS: UserExecutionContext validation passed"

❌ Failure Indicators:
- "E2E CONTEXT NOT DETECTED" (missing headers/env vars)
- "ENHANCED STAGING CRITICAL VALIDATION FAILED" (pattern recognition issues)
- "SSOT Auth failed" in WebSocket close messages (bypass not working)
```

### Debugging Commands
```bash
# Check staging environment variables
gcloud run services describe netra-backend \
    --platform managed \
    --region us-central1 \
    --format="value(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)"

# Check staging secrets
gcloud secrets versions list staging-e2e-oauth-key --project=netra-staging
```

## Security Considerations

### Production Safety
- E2E bypass is **ONLY** enabled in staging environment
- Production environment variables do **NOT** include E2E_TESTING=1
- E2E OAuth simulation key is staging-specific and invalid in production

### Access Controls
```bash
# Ensure E2E secrets are only accessible by staging services
gcloud secrets get-iam-policy staging-e2e-oauth-key

# Should only show staging service accounts, not production
```

### Monitoring Alerts
```yaml
# Alert if E2E bypass is somehow enabled in production
alert_policy:
  conditions:
    - display_name: "E2E Bypass in Production"
      condition_threshold:
        filter: 'resource.type="cloud_run_revision" jsonPayload.message:"E2E BYPASS" resource.labels.service_name!="staging"'
        comparison: COMPARISON_GREATER_THAN
        threshold_value: 0
```

## Deployment Checklist

- [ ] **Environment Variables**: All required E2E variables set in Cloud Run
- [ ] **Secrets**: E2E OAuth simulation key created and accessible
- [ ] **Load Balancer**: Header forwarding configured for E2E test headers
- [ ] **Monitoring**: Log filters and alerts configured  
- [ ] **Validation**: E2E test suite passes in staging environment
- [ ] **Security**: Production environment does NOT have E2E variables
- [ ] **Documentation**: Update deployment scripts with E2E configuration

## Troubleshooting Common Issues

### Issue: WebSocket 1008 Policy Violations Still Occurring
**Cause**: E2E context not being detected  
**Fix**: Check header forwarding and environment variable configuration

### Issue: Factory SSOT Validation Still Failing
**Cause**: Staging patterns not recognized  
**Fix**: Verify ENVIRONMENT=staging and K_SERVICE variables are set

### Issue: E2E Bypass Not Working
**Cause**: E2E context extraction failing  
**Fix**: Ensure both headers AND environment variables are properly configured

---

**Implementation Priority**: CRITICAL - Required to restore staging E2E testing capability  
**Estimated Deployment Time**: 2-4 hours including validation  
**Dependencies**: Fixes to Factory SSOT and Auth services must be deployed first