# E2E Tests GCP Secrets Integration Plan

## Overview

Plan to update ALL E2E tests to support GCP Secrets Manager bypass key integration for seamless staging testing.

## Current Status

✅ **Unified Test Runner**: Auto-fetches E2E bypass key from GCP Secrets Manager  
✅ **E2E Configuration**: Updated staging URLs  
✅ **Health Validation**: Working on staging  
❌ **Individual E2E Tests**: Need to be updated to use GCP secrets integration  
❌ **Auth Endpoints**: E2E auth endpoint may need implementation on staging  

## Implementation Plan

### Phase 1: Core Infrastructure (COMPLETED)
- [x] Unified test runner auto-configuration
- [x] GCP Secrets Manager integration
- [x] Staging service URL configuration
- [x] Documentation and troubleshooting guides

### Phase 2: E2E Test Updates (IN PROGRESS)

#### 2.1 Authentication Integration Tests
**Files to Update:**
- `tests/e2e/test_staging_api_with_auth.py`
- `tests/e2e/test_auth_service_staging.py` 
- `tests/e2e/test_auth_flow_comprehensive.py`
- `tests/e2e/integration/test_staging_oauth_authentication.py`

**Changes Required:**
- Use StagingAuthHelper with auto-configured bypass key
- Remove hardcoded localhost URLs
- Add GCP service endpoint validation
- Integrate with staging-specific test data

#### 2.2 WebSocket Tests
**Files to Update:**
- `tests/e2e/integration/test_staging_websocket_messaging.py`
- All WebSocket-related E2E tests

**Changes Required:**
- Use wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws
- Integrate staging authentication
- Update connection timeout for GCP services

#### 2.3 Service Integration Tests  
**Files to Update:**
- `tests/e2e/integration/test_staging_health_validation.py` (already working)
- `tests/e2e/integration/test_staging_complete_e2e.py`
- `tests/e2e/integration/test_external_service_resilience.py`

**Changes Required:**
- Validate against real GCP staging services
- Remove Docker dependencies
- Add GCP-specific error handling

#### 2.4 Configuration Tests
**Files to Update:**
- `tests/e2e/test_staging_auth_config.py`
- `tests/e2e/test_environment_config.py`
- `tests/e2e/staging/test_environment_configuration.py`

**Changes Required:**
- Validate GCP Secrets Manager integration
- Test staging environment variable configuration
- Verify service discovery mechanisms

### Phase 3: Staging Service Endpoints (INVESTIGATION NEEDED)

#### 3.1 E2E Auth Endpoint Implementation
**Investigation Required:**
- Check if `/auth/e2e/test-auth` endpoint exists on staging auth service
- Verify bypass key validation logic
- Ensure proper CORS configuration

**Implementation Options:**
1. **Add endpoint to staging auth service** (Recommended)
2. **Use alternative auth mechanism for E2E tests**
3. **Mock auth for non-authenticated E2E tests**

#### 3.2 Service-Specific Endpoints
**Validation Needed:**
- WebSocket authentication on staging
- API endpoint availability 
- Rate limiting configuration

### Phase 4: CI/CD Integration

#### 4.1 GitHub Actions Integration
```yaml
- name: Run E2E Tests on Staging
  env:
    GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_SA_KEY }}
  run: |
    gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
    python unified_test_runner.py --categories e2e --env staging --real-llm
```

#### 4.2 Automated Test Reporting
- GCP Operations Suite integration
- Slack notifications for test results
- Performance regression detection

## Technical Architecture

### GCP Secrets Manager Integration
```python
# Auto-configured in unified test runner
def _configure_staging_e2e_auth(self):
    result = subprocess.run(
        ['gcloud', 'secrets', 'versions', 'access', 'latest', 
         '--secret=e2e-bypass-key', '--project=netra-staging'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        bypass_key = result.stdout.strip()
        env.set('E2E_OAUTH_SIMULATION_KEY', bypass_key, 'staging_e2e_auth')
```

### Staging Service URLs
```python
STAGING_SERVICES = {
    'backend': 'https://netra-backend-staging-pnovr5vsba-uc.a.run.app',
    'auth': 'https://auth.staging.netrasystems.ai',
    'frontend': 'https://netra-frontend-staging-pnovr5vsba-uc.a.run.app',
    'websocket': 'wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws'
}
```

## Implementation Tasks

### Task 1: Update Authentication Tests
**Assignee**: Auth Agent  
**Scope**: Update all auth-related E2E tests to use GCP secrets integration  
**Files**: ~5 test files  
**Estimated Time**: 2-3 hours  

### Task 2: Update WebSocket Tests
**Assignee**: WebSocket Agent  
**Scope**: Update WebSocket E2E tests for staging environment  
**Files**: ~3 test files  
**Estimated Time**: 1-2 hours  

### Task 3: Update Service Integration Tests
**Assignee**: Integration Agent  
**Scope**: Update service integration tests for GCP staging  
**Files**: ~4 test files  
**Estimated Time**: 2-3 hours  

### Task 4: Investigate Staging Auth Endpoints
**Assignee**: Investigation Agent  
**Scope**: Determine if E2E auth endpoints need implementation  
**Deliverable**: Technical analysis and recommendation  
**Estimated Time**: 1 hour  

## Success Criteria

1. **All E2E tests run successfully on staging** with single command
2. **No hardcoded localhost URLs** in E2E tests
3. **Automatic GCP secrets integration** without manual setup
4. **Comprehensive error handling** for GCP service issues
5. **CI/CD integration** for automated staging testing
6. **Performance baselines** established for staging services

## Risk Mitigation

### Risk 1: E2E Auth Endpoint Missing
**Mitigation**: Implement endpoint on staging auth service or use alternative auth method

### Risk 2: GCP Service Rate Limiting
**Mitigation**: Implement exponential backoff and proper error handling

### Risk 3: Network Latency Issues
**Mitigation**: Increase timeouts for GCP services, add retry logic

## Monitoring and Observability

### Health Checks
- Automated staging service health validation
- GCP Secrets Manager access verification
- Network connectivity monitoring

### Performance Metrics
- E2E test execution time on staging
- Service response times
- Error rates and failure patterns

## Documentation Updates

1. **Update existing E2E test documentation**
2. **Create staging-specific troubleshooting guides**
3. **Add GCP integration examples**
4. **Update CI/CD pipeline documentation**

## Next Steps

1. **Create sub-agents for each implementation task**
2. **Start with authentication tests (highest priority)**
3. **Investigate staging auth endpoint implementation**
4. **Run comprehensive validation after each phase**
5. **Update documentation and monitoring**

This plan ensures systematic updating of all E2E tests to work seamlessly with GCP Secrets Manager and staging services, enabling true production-parity testing.