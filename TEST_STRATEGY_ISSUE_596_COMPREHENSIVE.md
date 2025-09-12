# 🚨 Issue #596 SSOT Environment Variable Violations - Comprehensive Test Strategy

## Executive Summary

**Status**: SSOT environment variable violations blocking Golden Path authentication flow
**Impact**: Users cannot login → get AI responses ($500K+ ARR impact)  
**Critical Files**: 3 core infrastructure files using direct `os.environ`/`os.getenv` instead of SSOT IsolatedEnvironment

## Root Cause Analysis

### SSOT Violations Identified
1. **`auth_startup_validator.py`** (Lines 507-516) - Fallback pattern using direct `os.environ`
2. **`unified_secrets.py`** (Lines 52, 69) - Direct `os.getenv()` calls 
3. **`unified_corpus_admin.py`** (Lines 155, 281) - Direct `os.getenv()` calls

### Golden Path Impact
- JWT secret mismatches preventing user authentication
- Race conditions in Cloud Run environment initialization  
- Inconsistent environment variable resolution across components

## Test Strategy Overview

### Test Philosophy
**Primary Goal**: Create failing tests that reproduce the SSOT violations and Golden Path authentication failures

**Test Categories**:
1. **Unit Tests** - Detect individual SSOT violations
2. **Integration Tests** - Test environment variable resolution patterns  
3. **E2E GCP Staging Tests** - Validate Golden Path authentication flow

### Success Criteria
- Tests initially FAIL to prove the violations exist
- Tests can run without Docker (unit, integration non-docker, E2E staging)
- Tests follow `reports/testing/TEST_CREATION_GUIDE.md` patterns
- Tests validate business impact ($500K+ ARR Golden Path protection)

## Detailed Test Plan

### 1. Unit Tests - SSOT Violation Detection

#### 1.1 Auth Startup Validator SSOT Violations
**File**: `tests/unit/environment/test_auth_startup_validator_ssot_violations.py`

```python
"""
Unit Tests: Auth Startup Validator SSOT Violations

Purpose: Detect and reproduce os.environ fallback violations in AuthStartupValidator
Expected: These tests should FAIL initially to prove violations exist
"""

class TestAuthStartupValidatorSSOTViolations(BaseUnitTest):
    
    @pytest.mark.unit
    async def test_FAILING_env_var_resolution_uses_direct_os_environ(self):
        """
        TEST EXPECTATION: FAIL - Proves direct os.environ usage
        
        This test demonstrates the SSOT violation in auth_startup_validator.py 
        where _get_env_with_fallback() uses direct os.environ access.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set JWT_SECRET_KEY only in os.environ, NOT in IsolatedEnvironment
            test_jwt_key = "test-jwt-secret-direct-access"
            with patch.dict(os.environ, {'JWT_SECRET_KEY': test_jwt_key}):
                # Ensure NOT in isolated environment 
                env.delete('JWT_SECRET_KEY')
                assert env.get('JWT_SECRET_KEY') is None
                
                # Create validator - this should NOT find JWT_SECRET_KEY
                # But if it does, it proves direct os.environ access (SSOT violation)
                validator = AuthStartupValidator()
                
                # Call the private method that has SSOT violation
                fallback_value = validator._get_env_with_fallback('JWT_SECRET_KEY')
                
                # THIS ASSERTION SHOULD FAIL - proving SSOT violation
                assert fallback_value is None, (
                    f"SSOT VIOLATION: Found JWT_SECRET_KEY='{fallback_value}' "
                    f"via direct os.environ fallback instead of IsolatedEnvironment"
                )
                
        finally:
            env.disable_isolation()
            
    @pytest.mark.unit  
    async def test_FAILING_jwt_validation_bypass_via_fallback(self):
        """
        TEST EXPECTATION: FAIL - Proves JWT validation can be bypassed
        
        This test shows how the os.environ fallback creates authentication
        vulnerabilities by bypassing proper environment isolation.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Scenario: JWT secret exists in os.environ but not isolated env
            # This creates inconsistent JWT validation behavior
            malicious_jwt_key = "bypassed-secret-key"
            
            with patch.dict(os.environ, {'JWT_SECRET_KEY': malicious_jwt_key}):
                env.delete('JWT_SECRET_KEY')  # Not in isolated environment
                
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Find JWT validation result
                jwt_result = next((r for r in results 
                                 if r.component == AuthComponent.JWT_CONFIG), None)
                
                # THIS SHOULD FAIL - JWT validation should NOT succeed 
                # when secret only exists in os.environ fallback
                assert not jwt_result.valid, (
                    "CRITICAL SSOT VIOLATION: JWT validation succeeded using "
                    "os.environ fallback, bypassing IsolatedEnvironment isolation"
                )
                
        finally:
            env.disable_isolation()
```

#### 1.2 Unified Secrets SSOT Violations  
**File**: `tests/unit/environment/test_unified_secrets_ssot_violations.py`

```python
"""
Unit Tests: Unified Secrets SSOT Violations

Purpose: Detect direct os.getenv() usage in UnifiedSecrets class
Expected: These tests should FAIL initially to prove violations exist
"""

class TestUnifiedSecretsSSOTViolations(BaseUnitTest):
    
    @pytest.mark.unit
    def test_FAILING_get_secret_uses_direct_os_getenv(self):
        """
        TEST EXPECTATION: FAIL - Proves direct os.getenv() usage
        
        This test demonstrates the SSOT violation in unified_secrets.py line 52
        where get_secret() uses direct os.getenv() instead of IsolatedEnvironment.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set secret only in os.environ, NOT in IsolatedEnvironment
            secret_key = "TEST_SECRET_KEY"
            secret_value = "direct-os-getenv-value"
            
            with patch.dict(os.environ, {secret_key: secret_value}):
                # Ensure NOT in isolated environment
                env.delete(secret_key)
                assert env.get(secret_key) is None
                
                # Create UnifiedSecrets instance
                secrets = UnifiedSecrets()
                
                # This should NOT find the secret if using SSOT properly
                # But if it does, it proves direct os.getenv() usage
                found_secret = secrets.get_secret(secret_key)
                
                # THIS ASSERTION SHOULD FAIL - proving SSOT violation
                assert found_secret is None, (
                    f"SSOT VIOLATION: UnifiedSecrets.get_secret() found "
                    f"'{secret_key}' = '{found_secret}' via direct os.getenv() "
                    f"instead of using IsolatedEnvironment SSOT pattern"
                )
                
        finally:
            env.disable_isolation()
```

#### 1.3 Unified Corpus Admin SSOT Violations
**File**: `tests/unit/environment/test_unified_corpus_admin_ssot_violations.py`

```python
"""
Unit Tests: Unified Corpus Admin SSOT Violations

Purpose: Detect direct os.getenv() usage in corpus administration
Expected: These tests should FAIL initially to prove violations exist  
"""

class TestUnifiedCorpusAdminSSOTViolations(BaseUnitTest):
    
    @pytest.mark.unit
    async def test_FAILING_corpus_path_uses_direct_os_getenv(self):
        """
        TEST EXPECTATION: FAIL - Proves direct os.getenv() usage
        
        This test demonstrates the SSOT violation in unified_corpus_admin.py line 155
        where create_user_corpus_context() uses direct os.getenv().
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set CORPUS_BASE_PATH only in os.environ
            corpus_path = "/test/direct/corpus/path"
            
            with patch.dict(os.environ, {'CORPUS_BASE_PATH': corpus_path}):
                env.delete('CORPUS_BASE_PATH')
                assert env.get('CORPUS_BASE_PATH') is None
                
                # Create test user context
                user_context = UserExecutionContext(
                    user_id=UserID("test-user-123"),
                    agent_context={}
                )
                
                # This function uses direct os.getenv() - SSOT violation
                enhanced_context = create_user_corpus_context(
                    context=user_context,
                    corpus_base_path=None  # Force fallback to os.getenv
                )
                
                # Extract the corpus path from enhanced context
                corpus_metadata = enhanced_context.agent_context
                found_corpus_path = corpus_metadata.get('corpus_base_path')
                
                # THIS ASSERTION SHOULD FAIL - proving SSOT violation  
                assert found_corpus_path != corpus_path, (
                    f"SSOT VIOLATION: create_user_corpus_context() found "
                    f"CORPUS_BASE_PATH = '{found_corpus_path}' via direct "
                    f"os.getenv() instead of IsolatedEnvironment"
                )
                
        finally:
            env.disable_isolation()
```

### 2. Integration Tests - Environment Resolution Patterns

#### 2.1 Cross-Component Environment Consistency
**File**: `tests/integration/environment/test_ssot_environment_consistency.py`

```python  
"""
Integration Tests: SSOT Environment Variable Consistency

Purpose: Test environment variable resolution across multiple components
Expected: Detect inconsistencies in environment variable access patterns
"""

class TestSSOTEnvironmentConsistency(BaseIntegrationTest):
    
    @pytest.mark.integration
    async def test_FAILING_jwt_secret_inconsistency_across_components(self):
        """
        TEST EXPECTATION: FAIL - Proves inconsistent JWT secret resolution
        
        This test shows how different components resolve JWT_SECRET_KEY
        differently, leading to authentication failures in Golden Path.
        """
        env = get_env() 
        env.enable_isolation()
        
        try:
            # Scenario: JWT secret in os.environ but isolated env has different value
            os_jwt_secret = "os-environ-jwt-secret"
            isolated_jwt_secret = "isolated-env-jwt-secret"
            
            with patch.dict(os.environ, {'JWT_SECRET_KEY': os_jwt_secret}):
                env.set('JWT_SECRET_KEY', isolated_jwt_secret, 'test')
                
                # Test multiple components
                auth_validator = AuthStartupValidator()
                secrets_manager = UnifiedSecrets()
                jwt_manager = get_jwt_secret_manager()
                
                # Get JWT secrets from different components
                validator_secret = auth_validator._get_env_with_fallback('JWT_SECRET_KEY')
                secrets_secret = secrets_manager.get_secret('JWT_SECRET_KEY')
                jwt_secret = jwt_manager.get_secret()
                
                # These should all be the same (isolated env value)
                # But if they differ, it proves inconsistent SSOT compliance
                secrets_set = {validator_secret, secrets_secret, jwt_secret}
                
                # THIS ASSERTION SHOULD FAIL - proving inconsistency
                assert len(secrets_set) == 1, (
                    f"SSOT CONSISTENCY VIOLATION: JWT_SECRET_KEY resolved "
                    f"differently across components: "
                    f"AuthValidator='{validator_secret}', "
                    f"UnifiedSecrets='{secrets_secret}', "
                    f"JWTManager='{jwt_secret}'"
                )
                
        finally:
            env.disable_isolation()
            jwt_manager.clear_cache()
```

#### 2.2 Auth Service Integration with Environment Violations
**File**: `tests/integration/environment/test_auth_service_environment_violations.py`

```python
"""
Integration Tests: Auth Service Environment Variable Violations

Purpose: Test auth service behavior with SSOT violations
Expected: Demonstrate auth failures due to environment inconsistencies
"""

class TestAuthServiceEnvironmentViolations(BaseIntegrationTest):
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_FAILING_auth_service_startup_with_env_violations(self, real_services_fixture):
        """
        TEST EXPECTATION: FAIL - Proves auth service startup failures
        
        This test shows how SSOT environment violations cause auth service
        startup failures, blocking the Golden Path login flow.
        """
        env = get_env()
        env.enable_isolation() 
        
        try:
            # Create environment scenario that triggers SSOT violations
            # Set AUTH_SERVICE_URL only in os.environ
            auth_url = "http://localhost:8081"
            
            with patch.dict(os.environ, {'AUTH_SERVICE_URL': auth_url}):
                env.delete('AUTH_SERVICE_URL')
                
                # Try to initialize auth service components
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Find auth service connectivity result  
                auth_service_result = next((r for r in results 
                                          if r.component == AuthComponent.AUTH_SERVICE_CONNECTIVITY), 
                                         None)
                
                # THIS SHOULD FAIL - auth service connectivity should fail
                # when URL only available via os.environ fallback
                assert not auth_service_result.valid, (
                    f"SSOT VIOLATION: Auth service connectivity succeeded "
                    f"using os.environ fallback for AUTH_SERVICE_URL, "
                    f"bypassing IsolatedEnvironment isolation"
                )
                
        finally:
            env.disable_isolation()
```

### 3. E2E GCP Staging Tests - Golden Path Authentication

#### 3.1 Golden Path Authentication Flow with SSOT Violations
**File**: `tests/e2e/gcp_staging_environment/test_golden_path_auth_ssot_violations.py`

```python
"""
E2E GCP Staging Tests: Golden Path Authentication with SSOT Violations

Purpose: Test complete Golden Path user flow with environment violations
Expected: Demonstrate authentication failures blocking $500K+ ARR flow
"""

class TestGoldenPathAuthSSOTViolations(BaseStagingE2ETest):
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_FAILING_user_login_with_jwt_env_violations(self):
        """
        TEST EXPECTATION: FAIL - Proves Golden Path authentication blocked
        
        This test demonstrates how SSOT environment violations prevent
        the core business flow: Users login → get AI responses.
        
        Business Impact: $500K+ ARR at risk due to authentication failures.
        """
        # This test runs against GCP staging environment
        staging_config = self.get_staging_config()
        
        try:
            # Create test user for Golden Path flow
            test_user_email = "golden-path-test@example.com"
            
            # Step 1: User attempts to login (Golden Path start)
            auth_response = await self.attempt_user_login(
                email=test_user_email,
                environment="staging"
            )
            
            # THIS SHOULD FAIL - login should fail due to JWT env violations
            assert not auth_response.success, (
                f"CRITICAL BUSINESS IMPACT: User login succeeded despite "
                f"SSOT environment violations. This suggests the violations "
                f"may not be blocking Golden Path, requiring deeper investigation."
            )
            
            if auth_response.success:
                # If login succeeds, test the full Golden Path to find where it breaks
                token = auth_response.token
                
                # Step 2: User connects to WebSocket (chat interface)
                websocket_url = f"{staging_config['websocket_url']}/ws"
                
                async with WebSocketTestClient(
                    url=websocket_url,
                    token=token
                ) as ws_client:
                    
                    # Step 3: User sends message to agent (core business value)
                    await ws_client.send_json({
                        "type": "agent_request",
                        "agent": "triage_agent",
                        "message": "Help me optimize costs"
                    })
                    
                    # Collect WebSocket events
                    events = []
                    try:
                        async with asyncio.timeout(30):  # 30 second timeout
                            async for event in ws_client.receive_events():
                                events.append(event)
                                if event.get("type") == "agent_completed":
                                    break
                    except asyncio.TimeoutError:
                        pass
                    
                    # Analyze where the Golden Path breaks
                    event_types = [e.get("type") for e in events]
                    
                    # Expected Golden Path events
                    expected_events = [
                        "agent_started",
                        "agent_thinking", 
                        "tool_executing",
                        "tool_completed",
                        "agent_completed"
                    ]
                    
                    missing_events = [e for e in expected_events if e not in event_types]
                    
                    if missing_events:
                        pytest.fail(
                            f"GOLDEN PATH BLOCKED: Missing WebSocket events {missing_events}. "
                            f"SSOT environment violations may be preventing agent execution. "
                            f"Events received: {event_types}"
                        )
                    
                    # If all events present, check for actual AI response
                    final_event = events[-1] if events else None
                    if not final_event or final_event.get("type") != "agent_completed":
                        pytest.fail(
                            f"GOLDEN PATH INCOMPLETE: No agent_completed event. "
                            f"Environment violations preventing AI response delivery."
                        )
                        
                    # Verify business value delivered  
                    result = final_event.get("data", {}).get("result")
                    if not result or not result.get("content"):
                        pytest.fail(
                            f"GOLDEN PATH FAILURE: Agent completed but delivered no "
                            f"business value. SSOT violations may be affecting "
                            f"agent execution context."
                        )
                        
        except Exception as e:
            # Expected failure - document the specific failure mode
            pytest.fail(
                f"GOLDEN PATH BLOCKED: Authentication/WebSocket failure due to "
                f"SSOT environment violations. Error: {str(e)}. "
                f"Business Impact: $500K+ ARR user flow non-functional."
            )
```

#### 3.2 Environment Variable Propagation in Cloud Run
**File**: `tests/e2e/gcp_staging_environment/test_cloud_run_env_propagation.py`

```python
"""
E2E GCP Staging Tests: Cloud Run Environment Variable Propagation

Purpose: Test environment variable propagation in Cloud Run with SSOT violations  
Expected: Demonstrate environment inconsistencies in production-like environment
"""

class TestCloudRunEnvPropagation(BaseStagingE2ETest):
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_FAILING_env_var_consistency_across_cloud_run_services(self):
        """
        TEST EXPECTATION: FAIL - Proves environment inconsistency in Cloud Run
        
        This test validates that environment variables are consistently
        available across all Cloud Run services, or demonstrates failures.
        """
        staging_config = self.get_staging_config()
        
        # Test critical environment variables across services
        critical_env_vars = [
            "JWT_SECRET_KEY",
            "AUTH_SERVICE_URL", 
            "CORPUS_BASE_PATH",
            "SERVICE_ID"
        ]
        
        service_endpoints = [
            f"{staging_config['backend_url']}/health/env-check",
            f"{staging_config['auth_url']}/health/env-check"
        ]
        
        env_consistency_results = {}
        
        for service_url in service_endpoints:
            try:
                # Call health check endpoint that reports environment status
                response = await self.http_client.get(
                    service_url,
                    headers={"X-Health-Check": "env-vars"}
                )
                
                if response.status_code == 200:
                    env_status = response.json()
                    env_consistency_results[service_url] = env_status
                else:
                    env_consistency_results[service_url] = {"error": f"HTTP {response.status_code}"}
                    
            except Exception as e:
                env_consistency_results[service_url] = {"error": str(e)}
        
        # Analyze consistency across services
        inconsistencies = []
        
        for env_var in critical_env_vars:
            var_values = {}
            
            for service_url, env_data in env_consistency_results.items():
                if "error" not in env_data:
                    var_values[service_url] = env_data.get(env_var)
            
            # Check if all services report the same value
            unique_values = set(var_values.values())
            if len(unique_values) > 1:
                inconsistencies.append({
                    "env_var": env_var,
                    "values_by_service": var_values
                })
        
        # THIS SHOULD FAIL if there are SSOT violations causing inconsistencies
        assert not inconsistencies, (
            f"SSOT ENVIRONMENT VIOLATIONS: Environment variables inconsistent "
            f"across Cloud Run services: {inconsistencies}. "
            f"This proves SSOT violations are causing production issues."
        )
```

## Test Execution Plan

### Phase 1: Unit Test Validation (No Docker Required)
```bash
# Run unit tests to detect SSOT violations
python tests/unified_test_runner.py --category unit --pattern "*ssot*violations*"

# Expected: All tests should FAIL initially, proving violations exist
```

### Phase 2: Integration Test Validation (No Docker Required)  
```bash
# Run integration tests for environment consistency
python tests/unified_test_runner.py --category integration --pattern "*environment*"

# Expected: Tests fail showing inconsistent environment resolution
```

### Phase 3: E2E GCP Staging Validation
```bash
# Run E2E tests against GCP staging environment
python tests/unified_test_runner.py --category e2e --env staging --pattern "*golden*path*auth*"

# Expected: Golden Path authentication flow fails due to SSOT violations
```

## Business Value Justification (BVJ)

**Segment**: All (Free, Early, Mid, Enterprise, Platform)  
**Business Goal**: Stability - Protect $500K+ ARR Golden Path functionality  
**Value Impact**: Ensures users can login → get AI responses (90% of platform value)  
**Strategic Impact**: SSOT compliance prevents cascade failures and authentication vulnerabilities

## Expected Test Results

### Initial Test Run (Before Fix)
- ❌ **Unit Tests**: FAIL - Proving SSOT violations exist  
- ❌ **Integration Tests**: FAIL - Showing environment inconsistencies
- ❌ **E2E Tests**: FAIL - Golden Path authentication blocked

### Post-Fix Test Run (After SSOT Compliance)
- ✅ **Unit Tests**: PASS - No more direct os.environ usage
- ✅ **Integration Tests**: PASS - Consistent environment resolution  
- ✅ **E2E Tests**: PASS - Golden Path authentication working

## Success Metrics

- **Test Coverage**: 3 critical files with SSOT violations covered
- **Failure Reproduction**: Tests reliably reproduce authentication failures  
- **Business Protection**: $500K+ ARR Golden Path flow validated
- **SSOT Compliance**: All environment access through IsolatedEnvironment pattern
- **Production Readiness**: E2E staging tests confirm fix effectiveness

---

**Test Strategy Created**: 2025-09-12  
**Issue**: #596 SSOT Environment Variable Violations  
**Priority**: P0 - Critical Golden Path blocking issue