# E2E Testing on Staging Environment - Setup Guide

## Overview

Running E2E tests against staging.netrasystems.ai requires specific authentication setup due to security restrictions. This document explains the requirements and provides clear instructions.

## Current Test Status

✅ **Basic Health Tests**: All staging services are healthy and accessible
- Backend: `https://netra-backend-staging-pnovr5vsba-uc.a.run.app` (200ms response)
- Auth Service: `https://netra-auth-service-pnovr5vsba-uc.a.run.app` (172ms response) 
- Frontend: `https://netra-frontend-staging-pnovr5vsba-uc.a.run.app` (204ms response)

❌ **Authenticated E2E Tests**: Require E2E_OAUTH_SIMULATION_KEY environment variable

## Authentication Requirements

### Why E2E_OAUTH_SIMULATION_KEY is Required

Staging environment uses production-level security. For automated testing without OAuth flow, an E2E bypass mechanism is implemented with:

1. **Secure bypass key** stored in Google Secrets Manager
2. **Environment validation** (staging only)  
3. **Audit logging** of all bypass attempts
4. **Token expiry** (15-minute standard JWT expiry)

### Getting the E2E Bypass Key

The bypass key is stored in Google Secrets Manager under `e2e-bypass-key`. To access it:

```bash
# If you have access to netra-staging project
gcloud secrets versions access latest --secret="e2e-bypass-key" --project="netra-staging"
```

### Setting Up for E2E Tests

1. **Export the environment variable**:
```bash
export E2E_OAUTH_SIMULATION_KEY="your-key-from-secrets-manager"
export ENVIRONMENT=staging
export STAGING_AUTH_URL=https://api.staging.netrasystems.ai
```

2. **Run authenticated E2E tests**:
```bash
python unified_test_runner.py --categories e2e --env staging --real-llm
```

## What Works Without E2E_OAUTH_SIMULATION_KEY

You can run these tests without authentication:

1. **Health validation tests**:
```bash
python tests/e2e/integration/test_staging_health_validation.py
```

2. **Service accessibility tests**:
```bash
python unified_test_runner.py --categories smoke --env staging
```

3. **CORS and connectivity tests** (public endpoints)

## What Requires E2E_OAUTH_SIMULATION_KEY

These test categories need authentication:

- WebSocket connection tests
- API endpoint tests (protected routes)
- User session management tests  
- Agent execution tests
- Thread creation/management tests
- Full user journey tests

## Security Setup Script

Use the provided setup script to configure bypass key:

```bash
python scripts/setup_E2E_OAUTH_SIMULATION_KEY.py --project netra-staging
```

This script will:
- Generate a secure bypass key
- Store it in Google Secrets Manager
- Grant proper service account access
- Provide usage instructions

## Quick Test Commands

```bash
# Test staging health (no auth required)
python tests/e2e/integration/test_staging_health_validation.py

# Test with bypass key (full E2E)
export E2E_OAUTH_SIMULATION_KEY="your-key"
python unified_test_runner.py --categories e2e --env staging --real-llm

# Test bypass mechanism directly
python tests/e2e/staging_auth_bypass.py
```

## Troubleshooting

### "E2E_OAUTH_SIMULATION_KEY not provided" Error
```bash
export E2E_OAUTH_SIMULATION_KEY="$(gcloud secrets versions access latest --secret=e2e-bypass-key --project=netra-staging)"
```

### "Invalid E2E bypass key" Error
- Verify key matches Google Secrets Manager
- Check staging environment is correctly set
- Ensure service account has secretmanager.secretAccessor role

### Services Not Available Error
- All staging services are currently healthy
- Check network connectivity and firewall rules
- Verify staging URLs in test configuration

## Current Staging Service Status

As of latest test run:
- ✅ Backend Service: Healthy (189ms response time)
- ✅ Auth Service: Ready (172ms response time)  
- ✅ Frontend: Accessible (204ms response time)
- ✅ CORS Configuration: Properly configured
- ✅ Performance: All services respond within 5-second baseline

## For Developers

If you need to run E2E tests regularly:

1. Request access to `netra-staging` Google Cloud project
2. Get the bypass key from secrets manager
3. Add to your `.env.staging` file (git-ignored)
4. Use the unified test runner with `--env staging` flag

## Security Notes

- Never commit bypass keys to version control
- Keys should be rotated monthly  
- All bypass usage is logged and monitored
- Only works in staging environment (disabled in production)