# E2E Test Environment Configuration Guide

## Overview
This guide explains how to run E2E tests against both local Docker and staging GCP environments using the SSOT configuration system.

## SSOT Configuration
All E2E tests now use a Single Source of Truth (SSOT) configuration module located at `tests/e2e/e2e_test_config.py`. This ensures consistent configuration across all tests and enables seamless switching between environments.

## Running Tests

### Against Local Environment (Default)
```bash
# Default - runs against local Docker
python tests/unified_test_runner.py --category e2e --real-services

# Or run individual test files
python tests/e2e/test_real_agent_context_management.py
python tests/e2e/test_real_agent_corpus_admin.py
python tests/e2e/test_real_agent_supply_researcher.py
python tests/e2e/test_real_agent_tool_execution.py
```

### Against Staging Environment
```bash
# Set environment variable to use staging
export E2E_TEST_ENV=staging  # On Linux/Mac
set E2E_TEST_ENV=staging     # On Windows

# Then run tests as normal
python tests/unified_test_runner.py --category e2e --real-services

# Or run individual test files
python tests/e2e/test_real_agent_context_management.py
```

### Using pytest directly
```bash
# Local environment (default)
pytest tests/e2e/test_real_agent_*.py -v --real-services

# Staging environment
E2E_TEST_ENV=staging pytest tests/e2e/test_real_agent_*.py -v -m staging
```

## Environment Configuration

### Local Environment (Default)
- **Backend URL**: http://localhost:8000
- **WebSocket URL**: ws://localhost:8000/ws
- **Auth URL**: http://localhost:8081
- **Database**: PostgreSQL on port 5434 (test port)
- **Redis**: Port 6381 (test port)
- **Uses Docker Compose**: Automatically started by test runner

### Staging Environment
- **Backend URL**: https://netra-backend-staging-pnovr5vsba-uc.a.run.app
- **WebSocket URL**: wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws
- **Auth URL**: https://auth.staging.netrasystems.ai (when deployed)
- **Frontend URL**: https://app.staging.netrasystems.ai (when deployed)
- **Requires**: Network connectivity to GCP staging

## Updated Test Files
The following E2E test files have been updated to support both environments:

1. **test_real_agent_context_management.py**
   - Tests agent context isolation and multi-user support
   - Validates factory patterns and user boundaries

2. **test_real_agent_corpus_admin.py**
   - Tests corpus administration agent capabilities
   - Validates document management and classification

3. **test_real_agent_supply_researcher.py**
   - Tests supply chain research agent workflows
   - Validates data processing and analysis

4. **test_real_agent_tool_execution.py**
   - Tests tool execution and WebSocket events
   - Validates all 5 required WebSocket events

## Key Features

### Automatic Environment Detection
Tests automatically detect the target environment based on:
1. `force_environment` parameter in code
2. `E2E_TEST_ENV` environment variable
3. Default to "local" if not specified

### Environment Availability Checking
Tests automatically skip if the target environment is not available:
```python
if not config.is_available():
    pytest.skip(f"{environment} environment not available")
```

### Parameterized Fixtures
Test fixtures support both environments:
```python
@pytest.fixture(params=["local", "staging"])
async def test_fixture(request):
    config = get_e2e_config(force_environment=request.param)
    # ... fixture setup
```

## WebSocket Event Validation
All tests validate the 5 required WebSocket events (per CLAUDE.md):
- `agent_started`: User sees agent began processing
- `agent_thinking`: Real-time reasoning visibility
- `tool_executing`: Tool usage transparency
- `tool_completed`: Tool results display
- `agent_completed`: User knows when response is ready

## Authentication Configuration

### Local Testing
- Default test credentials are used
- No authentication required for WebSocket connections

### Staging Testing
Optional authentication tokens can be configured:
```bash
export STAGING_TEST_API_KEY=your_api_key
export STAGING_TEST_JWT_TOKEN=your_jwt_token
```

## Performance Thresholds
The SSOT configuration includes environment-specific performance thresholds:

### Local Environment
- Connection timeout: 10 seconds
- First event max delay: 15 seconds
- Agent completion timeout: 120 seconds

### Staging Environment
- Connection timeout: 15 seconds (network latency)
- First event max delay: 20 seconds
- Agent completion timeout: 120 seconds

## Troubleshooting

### Tests Skip Staging
If staging tests are being skipped:
1. Check network connectivity to GCP
2. Verify staging environment is deployed
3. Check health endpoint: https://netra-backend-staging-pnovr5vsba-uc.a.run.app/health

### Environment Not Detected
Verify environment variable is set correctly:
```python
python -c "from tests.e2e.e2e_test_config import get_e2e_config; print(get_e2e_config().environment)"
```

### WebSocket Connection Issues
For staging WebSocket issues:
1. Check if auth is required (currently disabled)
2. Verify WebSocket URL is accessible
3. Check for CORS or firewall restrictions

## Best Practices

1. **Default to Local**: Always test locally first before staging
2. **Use Real Services**: Tests use real services (NO MOCKS per CLAUDE.md)
3. **Validate Events**: Always check for all 5 required WebSocket events
4. **Check Availability**: Tests automatically skip unavailable environments
5. **Environment Isolation**: Each test creates isolated user contexts

## Business Value
This SSOT configuration enables:
- **$600K+ ARR Protection**: Multi-user isolation testing
- **Platform Stability**: Consistent testing across environments
- **Development Velocity**: Easy switching between local and staging
- **Quality Assurance**: Comprehensive E2E testing before production