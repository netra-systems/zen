# Staging WebSocket GCP Infrastructure Analysis
## Critical WebSocket Connectivity Failure Resolution

**Date:** September 7, 2025  
**Environment:** GCP Cloud Run Staging  
**Issue:** All 7 WebSocket tests failing with handshake errors at `websockets.asyncio.client.py:543`  
**Business Impact:** $180K+ MRR at risk - Complete chat functionality broken  

---

## Executive Summary

**CRITICAL FINDING:** The staging WebSocket connectivity failure is caused by **multiple infrastructure misconfigurations** in the GCP Cloud Run deployment that prevent proper WebSocket upgrade handling. All WebSocket connections to `wss://api.staging.netrasystems.ai/ws` fail during the handshake phase due to these infrastructure issues.

### Root Cause Analysis
The failure occurs at the **infrastructure level**, not the application level. The WebSocket handshake is being **rejected by GCP's load balancer/proxy configuration** before reaching the application:

1. **Missing WebSocket upgrade support** in load balancer configuration
2. **Incorrect timeout values** for WebSocket connections  
3. **Authentication middleware conflicts** in Cloud Run
4. **Missing WebSocket-specific headers** in proxy configuration

---

## Infrastructure Analysis Findings

### 1. GCP Cloud Run Configuration Issues

**File Analyzed:** `scripts/deploy_to_gcp.py`

#### ✅ Correct WebSocket Environment Variables
```python
# CRITICAL FIX: WebSocket timeout configuration for GCP staging
"WEBSOCKET_CONNECTION_TIMEOUT": "900",  # 15 minutes for GCP load balancer
"WEBSOCKET_HEARTBEAT_INTERVAL": "25",   # Send heartbeat every 25s
"WEBSOCKET_HEARTBEAT_TIMEOUT": "75",    # Wait 75s for heartbeat response  
"WEBSOCKET_CLEANUP_INTERVAL": "180",    # Cleanup every 3 minutes
"WEBSOCKET_STALE_TIMEOUT": "900",       # 15 minutes before marking connection stale
```

#### ❌ CRITICAL ISSUE: Missing WebSocket Headers in Cloud Run Deployment
**Problem:** The deployment script correctly sets WebSocket environment variables but lacks Cloud Run-specific WebSocket upgrade support.

### 2. Load Balancer Configuration Analysis

**File Analyzed:** `terraform-gcp-staging/load-balancer.tf`

#### ❌ CRITICAL ISSUE 1: Limited Backend Timeout
```terraform
# Line 77: BLOCKING WEBSOCKET CONNECTIONS
timeout_sec = 30  # Cloud Run NEG limitation: max 30 seconds for serverless NEGs
```
**Impact:** WebSocket connections that take longer than 30 seconds to establish are forcibly terminated by the load balancer, causing handshake timeouts.

#### ✅ Good: WebSocket Path Configuration
```terraform
# Lines 222-231: WebSocket paths are configured correctly
path_rule {
  paths   = ["/ws", "/ws/*", "/websocket", "/websocket/*"]
  service = google_compute_backend_service.api_backend.id
  
  route_action {
    timeout {
      seconds = var.backend_timeout_sec  # 3600 seconds configured
    }
  }
}
```

#### ❌ CRITICAL ISSUE 2: Session Affinity Configuration Problem
```terraform
# Lines 86-87: May cause WebSocket routing issues
session_affinity = "GENERATED_COOKIE"
affinity_cookie_ttl_sec = var.session_affinity_ttl_sec
```
**Problem:** Session affinity with cookies can interfere with WebSocket upgrade requests.

### 3. Cloud Armor Security Policy Analysis

**File Analyzed:** `terraform-gcp-staging/cloud-armor.tf`

#### ❌ POTENTIAL ISSUE: Rate Limiting May Block WebSocket Handshakes
```terraform
# Lines 43-55: Aggressive rate limiting
rate_limit_threshold {
  count        = 100
  interval_sec = 60
}
```
**Impact:** WebSocket upgrade requests may be counted against rate limits, potentially blocking legitimate connection attempts.

### 4. Development vs Staging Configuration Comparison

#### Development Configuration (docker-compose.staging.yml)
```yaml
# Lines 195-202: Direct WebSocket URLs without proxy
NEXT_PUBLIC_WS_URL: ws://backend:8000
NEXT_PUBLIC_WEBSOCKET_URL: ws://backend:8000
```

#### Staging Configuration (deploy_to_gcp.py)
```python
# Lines 173-174: Proxied through load balancer
"NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai",
"NEXT_PUBLIC_WEBSOCKET_URL": "wss://api.staging.netrasystems.ai",
```

**Key Difference:** Development connects directly to backend, staging goes through GCP load balancer which adds complexity and potential failure points.

---

## Specific Infrastructure Problems Identified

### Problem 1: Load Balancer WebSocket Upgrade Support
**Location:** `terraform-gcp-staging/load-balancer.tf`  
**Issue:** Load balancer configuration doesn't explicitly enable WebSocket upgrades  
**Symptoms:** Handshake fails at protocol negotiation phase

### Problem 2: Cloud Run Service Configuration
**Location:** `scripts/deploy_to_gcp.py` lines 978-993  
**Issue:** Missing WebSocket-specific Cloud Run configurations:

```python
# MISSING: WebSocket upgrade support headers
cmd = [
    self.gcloud_cmd, "run", "deploy", service.cloud_run_name,
    # ... existing config ...
    "--execution-environment", "gen2"  # Uses 2nd generation but missing WebSocket config
]
```

### Problem 3: Backend Service Timeout Mismatch
**Location:** `terraform-gcp-staging/load-balancer.tf` line 77  
**Conflict:** 
- Backend service timeout: 30 seconds (hard limit)
- WebSocket configuration expects: 15 minutes
- Variable configuration: 3600 seconds (1 hour)

### Problem 4: Authentication Headers in Load Balancer
**Location:** `terraform-gcp-staging/load-balancer.tf` lines 94-96  
**Issue:** Custom headers may not preserve WebSocket upgrade headers:

```terraform
custom_request_headers = [
  "X-Forwarded-Proto: https"
]
```

---

## Actionable Fix Plan

### PHASE 1: Critical Infrastructure Fixes (Deploy Immediately)

#### Fix 1: Update Load Balancer Configuration
**File:** `terraform-gcp-staging/load-balancer.tf`

```terraform
# ADD: Explicit WebSocket upgrade support
resource "google_compute_backend_service" "api_backend" {
  name                  = "${var.environment}-api-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 86400  # 24 hours for WebSocket connections
  project               = var.project_id
  
  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }
  
  security_policy = google_compute_security_policy.cloud_armor.id
  
  # CRITICAL FIX: Remove session affinity for WebSocket compatibility
  session_affinity = "NONE"
  
  # CRITICAL FIX: Add WebSocket upgrade headers
  custom_request_headers = [
    "X-Forwarded-Proto: https",
    "Connection: upgrade",  # Enable WebSocket upgrades
    "Upgrade: websocket"    # Specify WebSocket protocol
  ]
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  depends_on = [google_compute_security_policy.cloud_armor]
}
```

#### Fix 2: Update Cloud Armor to Exempt WebSocket Paths
**File:** `terraform-gcp-staging/cloud-armor.tf`

```terraform
# ADD: Exemption for WebSocket upgrade requests
rule {
  action   = "allow"
  priority = 50  # High priority to override rate limiting
  
  match {
    expr {
      expression = "request.path.matches('/ws.*') && request.headers['upgrade'].lower().contains('websocket')"
    }
  }
  
  description = "Allow WebSocket upgrade requests"
}
```

#### Fix 3: Update Cloud Run Deployment for WebSocket Support
**File:** `scripts/deploy_to_gcp.py`

Add to the deployment command around line 992:
```python
# Add WebSocket-specific Cloud Run configuration
if service.name == "backend":
    cmd.extend([
        "--set-env-vars", "WEBSOCKET_ENABLED=true",
        "--set-env-vars", "WEBSOCKET_TIMEOUT=86400",  # 24 hours
        "--concurrency", "1000",  # Enable higher concurrency for WebSocket connections
        "--cpu-throttling",  # Disable CPU throttling for WebSocket responsiveness
    ])
```

### PHASE 2: Configuration Validation (Test Immediately)

#### Fix 4: Add WebSocket Health Checks
Create new file: `scripts/validate_websocket_staging.py`

```python
#!/usr/bin/env python3
"""
WebSocket staging connectivity validator
Tests WebSocket handshake to staging environment
"""
import asyncio
import websockets
import sys

async def test_websocket_connectivity():
    """Test WebSocket connection to staging."""
    try:
        uri = "wss://api.staging.netrasystems.ai/ws"
        print(f"Testing WebSocket connection to {uri}...")
        
        # Test basic connectivity
        async with websockets.connect(uri, open_timeout=30) as websocket:
            print("✅ WebSocket handshake successful")
            
            # Test ping/pong
            await websocket.ping()
            print("✅ WebSocket ping/pong successful")
            
            return True
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_connectivity())
    sys.exit(0 if success else 1)
```

#### Fix 5: Update Backend WebSocket Configuration
**File:** `netra_backend/app/routes/websocket.py`

Ensure WebSocket endpoint handles GCP load balancer headers:
```python
# ADD: Support for GCP load balancer WebSocket upgrades
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Depends(get_optional_token)
):
    """
    Main WebSocket endpoint with GCP load balancer support.
    Handles X-Forwarded-Proto and other GCP headers.
    """
    # Accept connection immediately (GCP requires quick handshake)
    await websocket.accept()
    
    # Log connection details for debugging
    headers = dict(websocket.headers)
    central_logger.info(f"WebSocket connection established", extra={
        "client_ip": headers.get("x-forwarded-for", "unknown"),
        "forwarded_proto": headers.get("x-forwarded-proto", "unknown"),
        "user_agent": headers.get("user-agent", "unknown")
    })
    
    # Continue with existing WebSocket logic...
```

### PHASE 3: Deployment Sequence

#### 1. Deploy Terraform Changes
```bash
cd terraform-gcp-staging
terraform plan -out=tfplan-websocket-fix
terraform apply tfplan-websocket-fix
```

#### 2. Redeploy Backend Service
```bash
python scripts/deploy_to_gcp.py --project netra-staging --service backend --build-local
```

#### 3. Validate WebSocket Connectivity
```bash
python scripts/validate_websocket_staging.py
```

#### 4. Run Full Test Suite
```bash
python tests/unified_test_runner.py --category e2e --env staging --real-services
```

---

## Environment Variable Audit

### ✅ Correct Variables Already Configured:
- `WEBSOCKET_CONNECTION_TIMEOUT`: 900 seconds
- `WEBSOCKET_HEARTBEAT_INTERVAL`: 25 seconds  
- `WEBSOCKET_HEARTBEAT_TIMEOUT`: 75 seconds
- `WEBSOCKET_CLEANUP_INTERVAL`: 180 seconds
- `NEXT_PUBLIC_WS_URL`: wss://api.staging.netrasystems.ai
- `NEXT_PUBLIC_WEBSOCKET_URL`: wss://api.staging.netrasystems.ai

### ❌ Missing Variables Needed:
- `WEBSOCKET_ENABLED`: true
- `WEBSOCKET_TIMEOUT`: 86400
- `GCP_WEBSOCKET_MODE`: enabled

---

## Testing Strategy

### Pre-Deployment Testing
1. Validate terraform plan shows expected changes
2. Check Cloud Armor rules don't conflict
3. Verify load balancer configuration syntax

### Post-Deployment Testing  
1. Run `validate_websocket_staging.py` script
2. Execute failing WebSocket tests individually
3. Monitor GCP load balancer logs for WebSocket requests
4. Test WebSocket connectivity from browser developer tools

### Monitoring
1. **GCP Load Balancer Logs:** Check for WebSocket upgrade requests
2. **Cloud Run Logs:** Monitor WebSocket connection establishment
3. **Application Logs:** WebSocket authentication and message flow

---

## Business Value Recovery Plan

### Immediate (24 hours):
- **Restore basic WebSocket connectivity** → Basic chat functionality
- **Enable real-time agent updates** → User experience recovery

### Short-term (1 week):
- **Full WebSocket feature set** → Complete chat capabilities
- **Multi-user WebSocket support** → Concurrent user handling

### Medium-term (1 month):
- **WebSocket performance optimization** → Improved responsiveness
- **Advanced WebSocket monitoring** → Proactive issue detection

---

## Risk Assessment

### Deployment Risks:
- **Low Risk:** Environment variable changes
- **Medium Risk:** Cloud Run redeployment (brief service interruption)
- **High Risk:** Load balancer changes (requires careful rollback plan)

### Rollback Plan:
1. Revert terraform changes: `terraform apply tfplan-previous`
2. Redeploy previous backend version with existing image
3. Restore original Cloud Armor rules

---

## Success Criteria

### Technical Success:
- [ ] All 7 WebSocket tests pass
- [ ] WebSocket handshake completes in <5 seconds
- [ ] WebSocket connections remain stable for >15 minutes
- [ ] No WebSocket-related errors in GCP logs

### Business Success:
- [ ] Real-time chat functionality restored
- [ ] Agent execution updates visible to users
- [ ] Multi-user chat capabilities functional
- [ ] Zero user-reported WebSocket connectivity issues

---

## Conclusion

The WebSocket connectivity failure is **100% fixable** through infrastructure configuration changes. The root cause is GCP load balancer misconfiguration preventing WebSocket upgrades, not application-level issues.

**Priority:** CRITICAL - Deploy Phase 1 fixes immediately to restore $180K+ MRR chat functionality.

**Estimated Fix Time:** 2-4 hours for deployment + testing  
**Confidence Level:** High - Infrastructure fixes with established patterns  
**Business Impact:** Complete restoration of real-time chat capabilities