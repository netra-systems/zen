# Staging Environment Testing

## Overview

The Netra platform includes comprehensive staging environment tests that validate deployment configurations and integration with the actual staging environment at `staging.netrasystems.ai`.

## Staging Environment URLs

- **App**: https://app.staging.netrasystems.ai
- **API**: https://api.staging.netrasystems.ai
- **Auth**: https://auth.staging.netrasystems.ai
- **Frontend**: https://staging.netrasystems.ai
- **WebSocket**: wss://api.staging.netrasystems.ai/ws

## Running Staging Tests

### Quick Start

```bash
# Run standard staging tests (5-10 minutes)
python scripts/test_staging.py

# Run quick health checks only (2-3 minutes)
python scripts/test_staging.py --quick

# Run comprehensive staging tests (10-15 minutes)
python scripts/test_staging.py --full
```

### Using Test Runner

```bash
# Run staging tests with test runner
python unified_test_runner.py --level staging --env staging

# Run real staging environment tests
python unified_test_runner.py --level staging-real --env staging

# Quick staging validation
python unified_test_runner.py --level staging-quick --env staging
```

## Test Levels

### staging-real
- **Duration**: 5-10 minutes
- **Purpose**: Validate actual staging deployment health and functionality
- **Tests**: Health checks, CORS, deployment, LLM integration, observability, resources, WebSocket

### staging
- **Duration**: 10-15 minutes  
- **Purpose**: Comprehensive staging configuration and GCP resource validation
- **Tests**: All staging configuration tests including database, secrets, migrations

### staging-quick
- **Duration**: 2-3 minutes
- **Purpose**: Fast staging health check for deployment verification
- **Tests**: Secret manager integration and health checks only

## Environment Configuration

### Automatic Configuration

The test runner automatically configures the following environment variables:

```bash
ENVIRONMENT=staging
STAGING_URL=https://app.staging.netrasystems.ai
STAGING_API_URL=https://api.staging.netrasystems.ai
STAGING_AUTH_URL=https://auth.staging.netrasystems.ai
STAGING_FRONTEND_URL=https://staging.netrasystems.ai
WS_BASE_URL=wss://api.staging.netrasystems.ai/ws
GCP_PROJECT_ID=netra-ai-staging
GCP_REGION=us-central1
```

### Manual Configuration

You can also set up the environment manually:

```bash
# Windows
set STAGING_URL=https://app.staging.netrasystems.ai
set STAGING_API_URL=https://api.staging.netrasystems.ai
set STAGING_AUTH_URL=https://auth.staging.netrasystems.ai
set STAGING_FRONTEND_URL=https://staging.netrasystems.ai

# Linux/Mac
export STAGING_URL=https://app.staging.netrasystems.ai
export STAGING_API_URL=https://api.staging.netrasystems.ai
export STAGING_AUTH_URL=https://auth.staging.netrasystems.ai
export STAGING_FRONTEND_URL=https://staging.netrasystems.ai
```

### Using Environment File

Create or use `.env.staging.test` for persistent configuration:

```bash
# Load staging environment
source .env.staging.test  # Linux/Mac
# or manually set variables on Windows
```

## Test Categories

### Health Checks
- Main health endpoint validation
- Liveness and readiness probes
- Component health checks
- Metrics endpoint validation
- Circuit breaker behavior
- Timeout handling

### CORS Configuration
- Preflight requests
- Allowed origins validation
- Headers and methods
- WebSocket CORS
- Blocked origin handling

### Deployment Tests
- Blue-green deployment readiness
- Canary deployment support
- Zero-downtime deployment
- Graceful shutdown
- Version headers
- Rollback readiness

### LLM Integration
- Anthropic API connectivity
- Gemini API connectivity
- OpenAI API connectivity
- Streaming responses
- Rate limiting
- Error handling

### Observability
- Prometheus metrics
- Distributed tracing
- Structured logging
- Custom metrics
- Alert endpoints
- Error tracking

### Resource Limits
- CPU limits validation
- Memory limits validation
- Connection pooling
- Rate limiting
- Request size limits
- Timeout configurations

### WebSocket Load Balancer
- Connection distribution
- Sticky sessions
- Health-based routing
- Graceful disconnection
- Reconnection handling
- Message routing

## GCP Integration Tests

These tests require GCP credentials and validate:

- Cloud SQL proxy connectivity
- Secret Manager integration
- Database migrations
- Multi-service secrets
- Redis lifecycle
- Terraform consistency

To run GCP integration tests, set:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## CI/CD Integration

### GitHub Actions

Add to your workflow:

```yaml
- name: Run Staging Tests
  run: |
    python unified_test_runner.py --level staging-quick --env staging
  env:
    STAGING_URL: https://app.staging.netrasystems.ai
    STAGING_API_URL: https://api.staging.netrasystems.ai
    STAGING_AUTH_URL: https://auth.staging.netrasystems.ai
    STAGING_FRONTEND_URL: https://staging.netrasystems.ai
```

### Pre-deployment Validation

```bash
# Run before deploying to staging
python scripts/test_staging.py --quick

# Run after deployment
python scripts/test_staging.py --full
```

## Test Results

Typical results for a healthy staging environment:

- **staging-quick**: ~8 tests passed, ~6 skipped (GCP-specific)
- **staging-real**: ~55 tests passed, ~45 skipped (requires credentials)
- **staging**: ~100 tests total, varies based on credentials

## Troubleshooting

### Common Issues

1. **Connection timeouts**: Check if staging environment is accessible
2. **Authentication failures**: Verify API keys and credentials
3. **CORS errors**: Ensure your origin is in allowed list
4. **GCP tests skipped**: Set GOOGLE_APPLICATION_CREDENTIALS

### Debug Mode

Run with verbose output:
```bash
python unified_test_runner.py --level staging --env staging -v
```

## Adding New Staging Tests

1. Add test file to `app/tests/integration/staging_config/`
2. Inherit from `StagingConfigTestBase`
3. Use staging URLs from class attributes
4. Add to appropriate test level in `test_config.py`

Example:
```python
from .base import StagingConfigTestBase

class TestNewFeature(StagingConfigTestBase):
    def test_staging_feature(self):
        # Test uses self.staging_api_url automatically
        response = await self.assert_service_healthy(
            self.staging_api_url, 
            '/api/v1/feature'
        )
        self.assertEqual(response['status'], 'healthy')
```

## Best Practices

1. **Use staging-quick for rapid validation**
2. **Run staging-real before production deployments**
3. **Include staging tests in CI/CD pipelines**
4. **Monitor test trends over time**
5. **Keep tests focused on external behavior**
6. **Don't test implementation details**
7. **Use real services when possible**

## Integration with Comprehensive Tests

Staging tests are now included in the comprehensive test suite:

```bash
# Runs all tests including staging
python unified_test_runner.py --level comprehensive
```

This ensures staging environment validation is part of pre-release testing.