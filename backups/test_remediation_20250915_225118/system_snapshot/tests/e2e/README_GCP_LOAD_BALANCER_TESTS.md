# GCP Load Balancer Header Validation E2E Tests

## Overview

This directory contains comprehensive E2E tests that validate the fix for **GitHub Issue #113: GCP Load Balancer authentication header stripping**. These tests ensure that the terraform-gcp-staging/load-balancer.tf configuration properly forwards authentication headers to prevent regression.

## Test Files

### 1. `test_gcp_load_balancer_header_validation.py` (PRIMARY)
**Comprehensive load balancer header validation tests**

**Key Tests:**
- `test_gcp_load_balancer_preserves_authorization_header()` - **PRIMARY regression prevention**
- `test_gcp_load_balancer_preserves_e2e_bypass_header()` - E2E testing header preservation  
- `test_complete_golden_path_through_gcp_load_balancer()` - Full business value validation ($120K+ MRR protection)
- `test_gcp_load_balancer_websocket_auth_flow()` - WebSocket-specific validation
- `test_multi_user_isolation_through_gcp_load_balancer()` - Multi-user scenarios
- `test_terraform_header_forwarding_configuration()` - Validates terraform fix deployment
- `test_load_balancer_timeout_configuration()` - Validates timeout settings
- `test_cors_header_configuration()` - Validates CORS headers work through load balancer

### 2. `test_websocket_gcp_staging_infrastructure.py` (ENHANCED)
**WebSocket-specific infrastructure validation with regression prevention**

**Enhanced with:**
- `test_websocket_header_stripping_regression_prevention()` - Specific GitHub issue #113 regression test

## Business Value Protection

These tests protect against:
- **100% authentication failures** that block all user chat functionality
- **$120K+ MRR loss** from complete Golden Path failure
- **WebSocket 1011 errors** that prevent real-time communication
- **Multi-user isolation violations** that could cause data leakage

## Running the Tests

### Run Load Balancer Tests (Primary)
```bash
# All load balancer header validation tests
python tests/unified_test_runner.py --file tests/e2e/test_gcp_load_balancer_header_validation.py --real-services

# Specific critical regression test
python tests/unified_test_runner.py --test test_gcp_load_balancer_preserves_authorization_header --real-services
```

### Run WebSocket Infrastructure Tests (Complementary)
```bash
# All WebSocket GCP staging tests including regression prevention
python tests/unified_test_runner.py --file tests/e2e/test_websocket_gcp_staging_infrastructure.py --real-services

# Specific GitHub issue #113 regression test
python tests/unified_test_runner.py --test test_websocket_header_stripping_regression_prevention --real-services
```

### Run Both Test Suites Together
```bash
# Comprehensive load balancer validation
python tests/unified_test_runner.py \
  --file tests/e2e/test_gcp_load_balancer_header_validation.py \
  --file tests/e2e/test_websocket_gcp_staging_infrastructure.py \
  --real-services --env staging
```

## Infrastructure Requirements

### Pre-requisites
- **GCP staging environment** must be deployed
- **Load balancer terraform configuration** must include header forwarding fixes
- **Staging domains** must be accessible:
  - `https://api.staging.netrasystems.ai`
  - `https://auth.staging.netrasystems.ai`
  - `https://app.staging.netrasystems.ai`
- **WebSocket endpoint** must be available: `wss://api.staging.netrasystems.ai/ws`

### Expected Infrastructure Configuration
The tests validate that the following terraform configuration is properly deployed:

```terraform
# In terraform-gcp-staging/load-balancer.tf
resource "google_compute_url_map" "https_lb" {
  # CRITICAL FIX: Header transformations for WebSocket support
  header_action {
    request_headers_to_add {
      header_name  = "X-Forwarded-Proto"
      header_value = "https"
      replace      = false
    }
    
    # ADD MISSING: Authorization header preservation
    request_headers_to_remove = []  # Ensure no critical headers are removed
  }
}

resource "google_compute_backend_service" "api_backend" {
  # CRITICAL FIX: Preserve headers for WebSocket upgrade
  custom_request_headers = [
    "X-Forwarded-Proto: https",
    "Connection: upgrade",
    "Upgrade: websocket"
  ]
}
```

## Test Failure Diagnostics

### If Authorization Header Tests Fail
**Root Cause:** Load balancer is stripping Authorization headers
**Fix:** Add header preservation to terraform-gcp-staging/load-balancer.tf
**Symptom:** 401/403 errors or WebSocket handshake failures

### If WebSocket Tests Fail
**Root Cause:** WebSocket upgrade headers being stripped
**Fix:** Add WebSocket-specific header forwarding
**Symptom:** WebSocket 1011 errors or connection timeouts

### If E2E Bypass Tests Fail
**Root Cause:** X-E2E-Bypass headers being stripped
**Fix:** Add E2E testing header preservation
**Symptom:** E2E tests failing in staging environment

## Critical Success Criteria

✅ **HARD FAIL Requirements:**
- Authorization headers MUST flow through load balancer
- WebSocket upgrade MUST work with authentication
- Multi-user isolation MUST be preserved
- Golden Path business value MUST be protected
- No regression of GitHub issue #113 symptoms

❌ **Failure Indicators:**
- WebSocket 1011 errors
- 401/403 errors with valid tokens
- E2E test failures in staging
- User isolation violations
- Header stripping error messages

## Emergency Response

If tests fail indicating GitHub issue #113 regression:

1. **IMMEDIATE:** Check terraform-gcp-staging/load-balancer.tf deployment status
2. **VALIDATE:** Ensure header forwarding configuration is applied
3. **ESCALATE:** Alert infrastructure team about load balancer configuration
4. **MONITOR:** Run tests continuously until infrastructure is fixed

## Compliance

- **CLAUDE.MD E2E AUTH COMPLIANCE:** ✅ All tests use real authentication
- **Real Services:** ✅ Tests connect to actual GCP staging infrastructure  
- **Hard Fail Validation:** ✅ Tests fail loudly when header stripping detected
- **Business Value Protection:** ✅ Golden Path validation included