# Staging E2E Test Guide

## Overview

This guide documents the E2E testing system for the deployed staging environment. These tests make **real API and WebSocket calls** directly to the deployed staging services on GCP Cloud Run.

**IMPORTANT**: The auth bypass mechanism **ONLY simulates the Google OAuth flow** for testing purposes. It does not bypass authentication - valid JWT tokens are still required for all API and WebSocket calls.

## Architecture

### Deployed Staging Services

The staging environment consists of three main services deployed on GCP Cloud Run:

- **Backend**: `https://netra-backend-staging-701982941522.us-central1.run.app`
- **Auth Service**: `https://netra-auth-service-701982941522.us-central1.run.app`
- **Frontend**: `https://netra-frontend-staging-701982941522.us-central1.run.app`
- **WebSocket**: `wss://netra-backend-staging-701982941522.us-central1.run.app/ws`

### Test Components

```
tests/e2e/
├── staging_config.py              # Centralized staging URLs and configuration
├── staging_auth_client.py         # Auth client that simulates OAuth flow
├── staging_websocket_client.py    # WebSocket client for real-time testing
├── test_staging_e2e_comprehensive.py  # Comprehensive test suite
└── run_staging_tests.py          # Test runner script
```

## Setup

### 1. Environment Variables

```bash
# Required: E2E bypass key (stored in GCP Secrets Manager)
export E2E_BYPASS_KEY="<your-bypass-key>"

# Set environment to staging
export ENVIRONMENT="staging"
```

### 2. Install Dependencies

```bash
pip install httpx websockets pytest pytest-asyncio
```

## Running Tests

### Quick Tests (Default)

Run basic connectivity and auth tests:

```bash
python tests/run_staging_tests.py
```

### Full Test Suite

Run all staging tests including slow tests:

```bash
python tests/run_staging_tests.py --full
```

### Specific Test Categories

```bash
# Authentication tests only
python tests/run_staging_tests.py --auth

# API tests only
python tests/run_staging_tests.py --api

# WebSocket tests only
python tests/run_staging_tests.py --ws
```

### Using Pytest Directly

```bash
# Run all staging tests
ENVIRONMENT=staging pytest tests/e2e/test_staging_e2e_comprehensive.py -v

# Run specific test class
ENVIRONMENT=staging pytest tests/e2e/test_staging_e2e_comprehensive.py::TestStagingAuthentication -v

# Run with markers
ENVIRONMENT=staging pytest -m "staging and not slow" tests/e2e/
```

## Test Categories

### 1. Health Checks
- Validates all services are healthy
- Checks response times
- Verifies service dependencies

### 2. Authentication Tests
- OAuth flow simulation via bypass
- Token generation and validation
- Refresh token flow
- Invalid token rejection

### 3. API Endpoint Tests
- User profile endpoints
- Chat creation and retrieval
- Agent endpoints
- Error handling

### 4. WebSocket Tests
- Connection establishment
- Message sending/receiving
- Chat flow
- Agent interactions
- Concurrent connections

### 5. End-to-End Scenarios
- Complete user journey
- Multi-user scenarios
- Error recovery
- Rate limiting

## How Auth Bypass Works

The auth bypass mechanism **simulates** what happens after a successful Google OAuth login:

1. **Test Request**: Test sends request to `/auth/e2e/test-auth` with bypass key
2. **User Creation**: Auth service creates/retrieves a test user as if they logged in via OAuth
3. **Token Generation**: Valid JWT tokens are generated using the same mechanism as real OAuth
4. **Normal Auth Flow**: All subsequent requests use standard JWT authentication

**This is NOT a security bypass** - it's a testing mechanism that simulates the OAuth provider's response.

## Example Test Flow

```python
import asyncio
from tests.e2e.staging_auth_client import StagingAuthClient, StagingAPIClient
from tests.e2e.staging_websocket_client import StagingWebSocketClient

async def test_staging_flow():
    # 1. Get auth token (simulates OAuth login)
    auth_client = StagingAuthClient()
    tokens = await auth_client.get_auth_token(
        email="test@staging.netrasystems.ai"
    )
    
    # 2. Make authenticated API calls
    api_client = StagingAPIClient(auth_client)
    api_client.current_token = tokens["access_token"]
    response = await api_client.get("/api/v1/user/profile")
    
    # 3. Connect WebSocket with auth
    ws_client = StagingWebSocketClient(auth_client)
    await ws_client.connect(token=tokens["access_token"])
    
    # 4. Send messages
    await ws_client.send_chat_message("Hello staging!")
    
    # 5. Clean up
    await ws_client.disconnect()

asyncio.run(test_staging_flow())
```

## Troubleshooting

### Connection Errors

If you see connection errors:
1. Check that staging services are deployed: `gcloud run services list`
2. Verify URLs in `staging_config.py` match deployed services
3. Check for Cloud Run cold starts (retry after a few seconds)

### Authentication Errors

If authentication fails:
1. Verify `E2E_BYPASS_KEY` is set correctly
2. Check the key exists in GCP Secrets Manager
3. Ensure auth service is deployed and healthy

### WebSocket Issues

If WebSocket connections fail:
1. Verify the backend service supports WebSocket upgrade
2. Check that authentication token is valid
3. Look for CORS or firewall issues

### Rate Limiting

The staging environment has rate limiting enabled:
- 100 requests per minute per IP
- WebSocket connections limited to 10 per user
- Implement retry logic with exponential backoff

## CI/CD Integration

Add to your CI/CD pipeline:

```yaml
# GitHub Actions example
staging-e2e-tests:
  runs-on: ubuntu-latest
  env:
    E2E_BYPASS_KEY: ${{ secrets.E2E_BYPASS_KEY }}
    ENVIRONMENT: staging
  steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
    - run: pip install -r requirements.txt
    - run: python tests/run_staging_tests.py --full
```

## Security Considerations

1. **E2E Bypass Key**: 
   - Store in GCP Secrets Manager
   - Rotate regularly
   - Never commit to code

2. **Test User Isolation**:
   - Test users are marked with `e2e-test` in email
   - Automatically cleaned up after 24 hours
   - Cannot access production data

3. **Rate Limiting**:
   - Tests respect rate limits
   - Use dedicated test quotas where possible

## Monitoring

Monitor staging test results:
- Check test execution logs in CI/CD
- Monitor staging service health dashboards
- Set up alerts for test failures

## Best Practices

1. **Always test against deployed services** - Never mock staging endpoints
2. **Use real authentication flow** - Auth bypass only simulates OAuth provider
3. **Handle cold starts** - Staging services may have cold start delays
4. **Clean up resources** - Always disconnect WebSockets and logout
5. **Test incrementally** - Run quick tests first, then comprehensive
6. **Monitor costs** - Staging tests consume real GCP resources

## Support

For issues with staging tests:
1. Check service health: `python tests/run_staging_tests.py --skip-connectivity`
2. Review logs in GCP Cloud Logging
3. Contact DevOps team for infrastructure issues