# Load Balancer Endpoint Remediation Plan
**Comprehensive System Remediation for E2E Test Load Balancer Compliance**

## Executive Summary

**CRITICAL INFRASTRUCTURE ISSUE**: E2E tests currently use direct Cloud Run endpoints instead of load balancer endpoints, creating a fundamental mismatch between test scenarios and actual user experience.

**Business Impact**:
- Tests validate different infrastructure path than users experience
- Load balancer issues (SSL, routing, headers) go undetected
- Staging environment doesn't match production architecture
- False confidence in deployment readiness

**Root Cause Analysis**:
1. **Configuration Drift**: URLConstants.STAGING_BACKEND_URL uses `netra-backend-staging-pnovr5vsba-uc.a.run.app`
2. **Test Framework Inconsistency**: 20+ files contain direct Cloud Run URLs
3. **Mixed Domain Usage**: Some services use proper domains (auth.staging.netrasystems.ai) while others don't
4. **Legacy URL Patterns**: Test files have hardcoded Cloud Run URLs from early development

## Current State Assessment

### Configuration SSOT Issues
**File**: `netra_backend/app/core/network_constants.py`
```python
# PROBLEMATIC: Direct Cloud Run URLs
STAGING_BACKEND_URL: Final[str] = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
STAGING_FRONTEND_URL: Final[str] = "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app"
STAGING_WEBSOCKET_URL: Final[str] = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws"

# CORRECT: Load balancer endpoints
STAGING_AUTH_URL: Final[str] = "https://auth.staging.netrasystems.ai"
```

### Test Framework Issues
**File**: `tests/e2e/e2e_test_config.py`
```python
# PROBLEMATIC: Direct Cloud Run URLs in staging config
backend_url="https://netra-backend-staging-pnovr5vsba-uc.a.run.app",
api_url="https://netra-backend-staging-pnovr5vsba-uc.a.run.app/api",
websocket_url="wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws",
```

### Affected Files (20+ identified)
1. **Core Configuration Files**:
   - `netra_backend/app/core/network_constants.py` (CRITICAL SSOT)
   - `tests/e2e/e2e_test_config.py` (Test SSOT)

2. **E2E Test Files**:
   - `tests/e2e/test_staging_api_with_auth.py`
   - `tests/e2e/test_auth_service_staging.py`
   - `tests/e2e/test_auth_flow_comprehensive.py`
   - `tests/e2e/staging/run_100_tests*.py`
   - `tests/e2e/integration/test_staging_*.py`
   - Multiple other staging test files

3. **Configuration Data Files**:
   - `SPEC/generated/string_literals.json`
   - `config/staging_test_report.json`

## Remediation Strategy

### Phase 1: Configuration SSOT Updates (CRITICAL FOUNDATION)

**PRIORITY: IMMEDIATE** - This must be completed first as it's the foundation for all other changes.

#### 1.1 Update Network Constants (PRIMARY SSOT)
**File**: `netra_backend/app/core/network_constants.py`

**Changes Required**:
```python
class URLConstants:
    # BEFORE (Problematic)
    STAGING_BACKEND_URL: Final[str] = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
    STAGING_FRONTEND_URL: Final[str] = "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app"
    STAGING_WEBSOCKET_URL: Final[str] = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws"
    
    # AFTER (Load Balancer Endpoints)
    STAGING_BACKEND_URL: Final[str] = "https://api.staging.netrasystems.ai"
    STAGING_FRONTEND_URL: Final[str] = "https://app.staging.netrasystems.ai"
    STAGING_WEBSOCKET_URL: Final[str] = "wss://api.staging.netrasystems.ai/ws"
    
    # MAINTAIN (Already correct)
    STAGING_AUTH_URL: Final[str] = "https://auth.staging.netrasystems.ai"
```

**Domain Mapping Strategy**:
- Backend API: `api.staging.netrasystems.ai` (consistent with .env.staging.template)
- Frontend: `app.staging.netrasystems.ai` (consistent with OAuth redirects)
- Auth Service: `auth.staging.netrasystems.ai` (already correct)
- WebSocket: `wss://api.staging.netrasystems.ai/ws`

#### 1.2 Update CORS Configuration
**Impact**: CORS origins must include load balancer domains

**Files Affected**:
- `netra_backend/app/core/network_constants.py` (URLConstants.get_cors_origins)
- Service startup configuration files

**Required Updates**:
```python
# Add load balancer domains to CORS origins
def get_cors_origins(cls, environment: str = "development") -> list[str]:
    if environment == "staging":
        return [
            "https://app.staging.netrasystems.ai",  # Load balancer frontend
            "https://api.staging.netrasystems.ai",  # Load balancer backend
            cls.build_http_url(port=ServicePorts.FRONTEND_DEFAULT)  # Local dev
        ]
```

### Phase 2: Test Framework Remediation

#### 2.1 Update E2E Test Configuration SSOT
**File**: `tests/e2e/e2e_test_config.py`

**Changes Required**:
```python
def get_staging_config() -> E2ETestConfig:
    return E2ETestConfig(
        environment=TestEnvironment.STAGING,
        # BEFORE (Direct Cloud Run)
        # backend_url="https://netra-backend-staging-pnovr5vsba-uc.a.run.app",
        # api_url="https://netra-backend-staging-pnovr5vsba-uc.a.run.app/api",
        # websocket_url="wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws",
        
        # AFTER (Load Balancer Endpoints)
        backend_url="https://api.staging.netrasystems.ai",
        api_url="https://api.staging.netrasystems.ai/api",
        websocket_url="wss://api.staging.netrasystems.ai/ws",
        
        # MAINTAIN (Already correct)
        auth_url="https://auth.staging.netrasystems.ai",
        frontend_url="https://app.staging.netrasystems.ai",
    )
```

#### 2.2 Test File Migration Strategy

**Automated Migration Approach**:
1. **Search Pattern**: `netra-backend-staging-pnovr5vsba-uc.a.run.app`
2. **Replace With**: `api.staging.netrasystems.ai`
3. **Search Pattern**: `netra-frontend-staging-pnovr5vsba-uc.a.run.app`
4. **Replace With**: `app.staging.netrasystems.ai`

**Files Requiring Updates** (20+ identified):
- All files in `tests/e2e/staging/`
- All files in `tests/e2e/integration/` with staging URLs
- Specific critical test files identified in assessment

**Migration Commands** (to be run after infrastructure setup):
```bash
# Backend URL migration
find tests/ -name "*.py" -exec sed -i 's/netra-backend-staging-pnovr5vsba-uc\.a\.run\.app/api.staging.netrasystems.ai/g' {} \;

# Frontend URL migration
find tests/ -name "*.py" -exec sed -i 's/netra-frontend-staging-pnovr5vsba-uc\.a\.run\.app/app.staging.netrasystems.ai/g' {} \;
```

### Phase 3: Infrastructure Configuration Requirements

#### 3.1 GCP Load Balancer Configuration

**Required Load Balancer Setup**:

1. **API Load Balancer** (`api.staging.netrasystems.ai`):
   - **Backend Service**: Points to Cloud Run backend service
   - **Health Check**: `/health` endpoint
   - **SSL Certificate**: Managed certificate for `api.staging.netrasystems.ai`
   - **Headers**: Preserve original headers for authentication

2. **Frontend Load Balancer** (`app.staging.netrasystems.ai`):
   - **Backend Service**: Points to Cloud Run frontend service  
   - **Health Check**: Frontend health endpoint
   - **SSL Certificate**: Managed certificate for `app.staging.netrasystems.ai`
   - **Static Content**: Proper caching headers

3. **WebSocket Support**:
   - **Protocol Upgrade**: HTTP to WebSocket upgrade support
   - **Session Affinity**: Maintain connection to same backend
   - **Timeout Configuration**: Appropriate WebSocket timeouts

#### 3.2 DNS Configuration

**Required DNS Records**:
```
api.staging.netrasystems.ai    -> GCP Load Balancer IP (API)
app.staging.netrasystems.ai    -> GCP Load Balancer IP (Frontend)  
auth.staging.netrasystems.ai   -> Current Auth Service (MAINTAIN)
```

#### 3.3 SSL Certificate Requirements

**Managed Certificates** (GCP):
- `api.staging.netrasystems.ai`
- `app.staging.netrasystems.ai`
- `auth.staging.netrasystems.ai` (existing)

**Certificate Validation**:
- Domain ownership verification
- HTTP-01 or DNS-01 challenge completion
- Certificate propagation validation

### Phase 4: Migration Implementation Plan

#### 4.1 Pre-Migration Validation
**Checklist**:
- [ ] Load balancer infrastructure deployed
- [ ] DNS records configured and propagated
- [ ] SSL certificates issued and active
- [ ] Health checks passing through load balancer
- [ ] CORS configuration allows load balancer domains

#### 4.2 Phased Rollout Strategy

**Stage 1: Configuration Updates (Non-Breaking)**
1. Update `network_constants.py` with load balancer URLs
2. Update `e2e_test_config.py` with new endpoints
3. **Validation**: Manual verification that load balancers work
4. **Rollback Plan**: Revert to Cloud Run URLs if load balancer fails

**Stage 2: Test File Migration (Comprehensive)**
1. Run automated migration scripts on test files
2. Update string literal indexes
3. **Validation**: Run subset of E2E tests to verify connectivity
4. **Rollback Plan**: Revert test file changes if validation fails

**Stage 3: Full Validation**
1. Run complete E2E test suite
2. Validate all WebSocket connections work through load balancer
3. Verify authentication flows work end-to-end
4. Performance testing to ensure no regression

#### 4.3 Validation Checkpoints

**Infrastructure Validation**:
```bash
# DNS Resolution
nslookup api.staging.netrasystems.ai
nslookup app.staging.netrasystems.ai

# SSL Certificate Validation
curl -I https://api.staging.netrasystems.ai/health
curl -I https://app.staging.netrasystems.ai

# Load Balancer Health Check
curl -v https://api.staging.netrasystems.ai/health
```

**Application Validation**:
```bash
# E2E Test Subset
python tests/unified_test_runner.py --category e2e --real-services --env staging --pattern "*staging*" --head-limit 5

# WebSocket Validation  
python tests/mission_critical/test_websocket_connection_through_load_balancer.py

# Auth Flow Validation
python tests/e2e/test_auth_flow_comprehensive.py
```

### Phase 5: Compliance Monitoring

#### 5.1 CI/CD Pipeline Integration

**Pre-commit Hooks**:
```python
# Prevent direct Cloud Run URLs in new code
def check_cloud_run_urls(file_content):
    forbidden_patterns = [
        r'\.a\.run\.app',
        r'netra-backend-staging-pnovr5vsba-uc\.a\.run\.app',
        r'netra-frontend-staging-pnovr5vsba-uc\.a\.run\.app'
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, file_content):
            raise ValueError(f"Direct Cloud Run URL detected: {pattern}")
```

**Automated Testing**:
```python
# tests/mission_critical/test_no_direct_cloudrun_urls_in_staging_e2e.py
def test_no_direct_cloudrun_urls_in_e2e_tests():
    """Ensure E2E tests use load balancer endpoints only"""
    e2e_files = glob.glob("tests/e2e/**/*.py", recursive=True)
    violations = []
    
    for file_path in e2e_files:
        with open(file_path, 'r') as f:
            content = f.read()
            if '.a.run.app' in content:
                violations.append(file_path)
    
    assert not violations, f"Direct Cloud Run URLs found in: {violations}"
```

#### 5.2 Ongoing Compliance

**Weekly Validation**:
- Run compliance test suite
- Verify DNS resolution and SSL certificates
- Performance baseline comparison

**Documentation Updates**:
- Update developer guidelines
- Add load balancer troubleshooting guide
- Document rollback procedures

## Risk Assessment and Mitigation

### High-Risk Areas

1. **WebSocket Connection Failures**:
   - **Risk**: Load balancer may not handle WebSocket upgrades correctly
   - **Mitigation**: Extensive WebSocket testing before full rollout
   - **Rollback**: Keep Cloud Run WebSocket endpoints as fallback

2. **Authentication Header Propagation**:
   - **Risk**: Load balancer strips or modifies auth headers
   - **Mitigation**: Header preservation configuration + validation tests
   - **Rollback**: Configure load balancer to forward all headers

3. **Performance Degradation**:
   - **Risk**: Additional hop through load balancer increases latency
   - **Mitigation**: Performance baseline testing + monitoring
   - **Rollback**: Revert to direct Cloud Run if latency exceeds threshold

### Medium-Risk Areas

1. **DNS Propagation Delays**:
   - **Risk**: DNS changes not propagated globally
   - **Mitigation**: Wait for full propagation before migration
   - **Timeline**: Allow 24-48 hours for full DNS propagation

2. **SSL Certificate Issues**:
   - **Risk**: Managed certificates fail to provision
   - **Mitigation**: Pre-validate certificate provisioning
   - **Alternative**: Manual certificate upload if managed fails

### Low-Risk Areas

1. **CORS Configuration**:
   - **Risk**: CORS blocks load balancer domains
   - **Mitigation**: Update CORS before migration
   - **Fix**: Quick configuration update if issues arise

## Implementation Timeline

### Phase 1: Infrastructure Setup (Week 1)
- **Days 1-2**: Deploy GCP Load Balancers
- **Days 3-4**: Configure DNS records
- **Days 5-7**: SSL certificate provisioning and validation

### Phase 2: Configuration Updates (Week 2) 
- **Days 1-2**: Update network_constants.py and e2e_test_config.py
- **Days 3-4**: Manual validation of load balancer functionality
- **Days 5-7**: Limited E2E testing with new endpoints

### Phase 3: Test Migration (Week 3)
- **Days 1-2**: Automated migration of test files
- **Days 3-5**: Comprehensive E2E test validation
- **Days 6-7**: Performance testing and optimization

### Phase 4: Monitoring and Compliance (Week 4)
- **Days 1-3**: CI/CD pipeline integration
- **Days 4-5**: Documentation updates
- **Days 6-7**: Team training and knowledge transfer

## Success Metrics

### Technical Metrics
- **100%** of E2E tests use load balancer endpoints
- **0** direct Cloud Run URLs in staging test files
- **< 5%** performance regression compared to direct endpoints
- **99.9%** SSL certificate validity across all staging domains

### Operational Metrics  
- **< 10 seconds** additional deployment validation time
- **< 2 minutes** time to detect load balancer issues
- **< 5 minutes** time to rollback if necessary

### Business Metrics
- **100%** confidence that staging mirrors production architecture
- **Improved** staging deployment reliability
- **Reduced** production incident risk from infrastructure mismatches

## Rollback Strategy

### Immediate Rollback (< 5 minutes)
1. Revert `network_constants.py` to Cloud Run URLs
2. Revert `e2e_test_config.py` to Cloud Run URLs  
3. Deploy reverted configuration
4. Validate core functionality

### Comprehensive Rollback (< 30 minutes)
1. Revert all test file changes using git
2. Update string literal indexes
3. Run E2E test validation
4. Document rollback reason and lessons learned

### Infrastructure Rollback
- **DNS**: Revert to Cloud Run endpoints (if load balancer completely fails)
- **Load Balancer**: Keep infrastructure but update code to bypass
- **Certificates**: Maintain for future retry

## Conclusion

This remediation plan addresses a critical infrastructure mismatch that undermines the reliability of our staging environment testing. By implementing load balancer endpoints across all E2E tests, we ensure that:

1. **Tests validate the same infrastructure path users experience**
2. **Load balancer issues are caught before production**  
3. **Staging environment truly mirrors production architecture**
4. **Development velocity increases through reliable staging validation**

The phased approach minimizes risk while ensuring comprehensive coverage. The compliance monitoring prevents regression and maintains architectural integrity over time.

**RECOMMENDATION**: Begin Phase 1 infrastructure setup immediately, as the 20+ affected test files represent a significant technical debt that increases deployment risk with every staging release.