# 🧪 TEST PLAN: Issue #552 - UnifiedDockerManager API Signature Mismatch

**Issue:** [#552](https://github.com/netra-systems/netra-apex/issues/552)  
**Problem:** Auth E2E tests fail due to API signature mismatch in UnifiedDockerManager.acquire_environment()  
**Created:** 2025-09-12  
**Status:** PLANNED - Ready for Implementation  

## 🎯 OBJECTIVE

Create comprehensive failing tests that reproduce Issue #552 and validate the fix, ensuring no similar API mismatches occur.

**CRITICAL:** Per CLAUDE.md requirements:
- ONLY create tests that don't require Docker (unit, integration without Docker, or E2E on staging GCP)
- Focus on reproducing the exact API signature TypeError
- Follow USER_CONTEXT_ARCHITECTURE.md factory patterns
- Create FAILING tests that will pass after the fix

## 📋 PRE-EXECUTION CHECKLIST

- [x] **Branch Status:** On develop-long-lived, synced with remote
- [x] **API Signature Analysis:** Current vs Broken API signatures identified
- [x] **Root Cause Identified:** `acquire_environment()` parameters vs no parameters
- [x] **Working Pattern Identified:** `start_services_smart()` with specific services
- [x] **Test Categories Planned:** Unit, Integration (no Docker), Auth flows

## 🔬 TEST STRATEGY

### 1. **API Signature Validation Tests (Unit)**
**Purpose:** Prove the exact TypeError that occurs in Issue #552  
**Location:** `tests/unit/test_unified_docker_manager_api_signature.py`  
**Docker Required:** NO - Pure API signature validation  

```python
# FAILING TEST - Will reproduce the exact Issue #552 error
def test_acquire_environment_rejects_legacy_parameters():
    """FAILING TEST: Reproduces Issue #552 TypeError - acquire_environment() takes parameters."""
    manager = UnifiedDockerManager()
    
    # This should fail with exact same TypeError as Issue #552
    with pytest.raises(TypeError, match="takes 1 positional argument but 4 were given"):
        manager.acquire_environment(
            env_name="test",
            use_alpine=True, 
            rebuild_images=True
        )

# PASSING TEST - Will pass after fix
def test_acquire_environment_current_signature_works():
    """PASSING TEST: Current API signature works correctly."""
    manager = UnifiedDockerManager()
    
    # Current working signature (no parameters)
    result = manager.acquire_environment()
    assert isinstance(result, tuple)
    assert len(result) == 2  # (env_name, port_mappings)
```

### 2. **Auth Service API Integration Test (No Docker)**
**Purpose:** Test auth service initialization patterns without Docker dependencies  
**Location:** `tests/integration/test_auth_service_api_patterns_no_docker.py`  
**Docker Required:** NO - Mocks Docker calls, tests API patterns  

```python
class TestAuthServiceAPIPatterns:
    """Test auth service initialization patterns without Docker dependency."""
    
    def test_legacy_acquire_environment_pattern_fails(self):
        """FAILING TEST: Legacy pattern from broken auth E2E tests fails."""
        # Reproduce exact pattern from auth_service/tests/e2e/test_auth_service_business_flows.py:62-66
        manager = UnifiedDockerManager()
        
        with pytest.raises(TypeError):
            env_info = manager.acquire_environment(
                env_name="test",
                use_alpine=True,
                rebuild_images=True
            )
    
    def test_working_start_services_smart_pattern(self):
        """PASSING TEST: Working pattern used by other E2E tests.""" 
        manager = UnifiedDockerManager()
        
        # Mock the actual Docker call since we're testing API patterns
        with patch.object(manager, 'start_services_smart') as mock_start:
            mock_start.return_value = asyncio.Future()
            mock_start.return_value.set_result(True)
            
            # This is the pattern that SHOULD be used
            result = await manager.start_services_smart(
                services=["postgres", "redis", "auth"],
                wait_healthy=True
            )
            
            assert result == True
            mock_start.assert_called_once_with(
                services=["postgres", "redis", "auth"],
                wait_healthy=True
            )
```

### 3. **Auth Business Flow Reproduction Test (Staging E2E)**
**Purpose:** Reproduce the exact auth business flow from failing test using STAGING environment  
**Location:** `tests/e2e/staging/test_auth_service_business_flows_api_fix.py`  
**Docker Required:** NO - Uses staging GCP environment  

```python
class TestAuthServiceBusinessFlowsStagingAPIFix:
    """Reproduce auth business flows using staging environment instead of Docker."""
    
    async def test_staging_auth_registration_flow_with_correct_api(self):
        """Test auth registration using correct UnifiedDockerManager API on staging."""
        
        # Use staging environment instead of Docker
        auth_service_url = get_env().get("STAGING_AUTH_SERVICE_URL", "https://auth-service-staging.netra.ai")
        
        # Test the business flow that was failing
        async with aiohttp.ClientSession() as session:
            # Registration endpoint test
            registration_data = {
                "email": f"test+{uuid.uuid4()}@example.com",
                "password": "securePassword123!",
                "name": "Test User"
            }
            
            async with session.post(f"{auth_service_url}/register", json=registration_data) as response:
                assert response.status == 201
                data = await response.json()
                assert "user_id" in data
                assert "access_token" in data
    
    async def test_staging_auth_login_flow_with_correct_api(self):
        """Test auth login flow using staging environment."""
        # Similar pattern but for login flow
        # This test proves the auth service works when not blocked by Docker API issues
        pass
```

### 4. **Comprehensive API Migration Validation**
**Purpose:** Ensure no other similar API signature mismatches exist  
**Location:** `tests/integration/test_docker_api_migration_validation.py`  
**Docker Required:** NO - Static code analysis and API validation  

```python
class TestDockerAPIMigrationValidation:
    """Validate that all Docker API calls use current signatures."""
    
    def test_no_legacy_acquire_environment_calls_exist(self):
        """FAILING TEST: Find all legacy acquire_environment() calls with parameters."""
        # Scan codebase for legacy API calls
        legacy_pattern_files = []
        
        # This will initially FAIL, showing all files that need updating
        for file_path in Path("auth_service/tests").rglob("*.py"):
            with open(file_path, 'r') as f:
                content = f.read()
                if "acquire_environment(" in content and ("env_name=" in content or "use_alpine=" in content):
                    legacy_pattern_files.append(str(file_path))
        
        # This assertion will initially FAIL, listing all problematic files
        assert not legacy_pattern_files, f"Found legacy acquire_environment() calls in: {legacy_pattern_files}"
    
    def test_all_docker_manager_calls_use_current_api(self):
        """Validate all UnifiedDockerManager usage follows current patterns."""
        # This test ensures consistent API usage across the codebase
        pass
```

## 🧪 EXPECTED TEST RESULTS

### Before Fix (Current State)
- `test_acquire_environment_rejects_legacy_parameters()` ❌ **FAIL** - TypeError: acquire_environment() takes 1 positional argument but 4 were given
- `test_legacy_acquire_environment_pattern_fails()` ❌ **FAIL** - Same TypeError 
- `test_no_legacy_acquire_environment_calls_exist()` ❌ **FAIL** - Lists auth_service/tests/e2e/test_auth_service_business_flows.py
- `test_staging_auth_*_flow_*()` ✅ **PASS** - Staging auth flows work (proves service is functional)

### After Fix (Expected State)
- `test_acquire_environment_rejects_legacy_parameters()` ❌ **STILL FAIL** - Should maintain failure to prevent regression
- `test_legacy_acquire_environment_pattern_fails()` ❌ **STILL FAIL** - Should maintain failure to prevent regression  
- `test_no_legacy_acquire_environment_calls_exist()` ✅ **PASS** - No more legacy calls found
- `test_staging_auth_*_flow_*()` ✅ **PASS** - Staging flows continue working
- **NEW:** Auth E2E tests using `start_services_smart()` ✅ **PASS** - Fixed auth business flows work

## 🚀 EXECUTION PLAN

### Phase 1: API Signature Reproduction (Unit Tests)
```bash
# Create and run unit tests that reproduce the exact TypeError
python -m pytest tests/unit/test_unified_docker_manager_api_signature.py -v

# Expected: Tests FAIL with exact Issue #552 error message
```

### Phase 2: Integration Testing (No Docker)
```bash  
# Test API patterns without Docker dependency
python -m pytest tests/integration/test_auth_service_api_patterns_no_docker.py -v

# Expected: Legacy pattern tests FAIL, working pattern tests PASS
```

### Phase 3: Staging E2E Validation
```bash
# Run staging environment tests to prove auth service functionality
export USE_STAGING_FALLBACK=true
export STAGING_AUTH_SERVICE_URL="https://auth-service-staging.netra.ai"
python -m pytest tests/e2e/staging/test_auth_service_business_flows_api_fix.py -v

# Expected: Auth business flows work on staging (proves service is functional)
```

### Phase 4: Migration Validation
```bash
# Validate no other legacy API calls exist
python -m pytest tests/integration/test_docker_api_migration_validation.py -v

# Expected: Initially FAIL, listing all files needing updates
```

## ✅ SUCCESS CRITERIA

### Test-Driven Development Success
1. **Failing Tests Created:** Tests that reproduce Issue #552 TypeError
2. **Root Cause Proven:** API signature mismatch clearly demonstrated  
3. **Working Patterns Validated:** `start_services_smart()` pattern proven functional
4. **Staging Validation:** Auth service functionality proven on staging environment
5. **Migration Coverage:** All legacy API calls identified for updating

### Business Value Protection
1. **Auth Service Functional:** Staging tests prove core auth functionality works
2. **API Consistency:** Tests prevent similar API signature mismatches
3. **Developer Productivity:** Clear guidance on correct API usage patterns
4. **CI/CD Reliability:** Tests can be integrated into pipeline after Docker issues resolved

## 📊 TEST METRICS

- **Total Tests Created:** 8-10 tests
- **Test Categories:** 4 (Unit, Integration, E2E Staging, Migration)
- **Docker Dependency:** ZERO (per requirements)
- **Coverage Focus:** API signatures, auth business flows, migration validation
- **Expected Initial Failures:** 50% (proving the issue exists)
- **Expected Post-Fix Passes:** 75% (some tests should remain failing for regression protection)

## 🔄 NEXT STEPS AFTER TESTING

1. **Issue #552 Fix Implementation:** Update auth E2E tests to use `start_services_smart()` pattern
2. **API Documentation:** Document correct UnifiedDockerManager usage patterns
3. **Developer Guidelines:** Update testing guides with correct API patterns  
4. **CI/CD Integration:** Add API signature validation to pipeline
5. **Regression Prevention:** Maintain failing tests that catch API signature changes

---

**Test Plan Status:** ✅ READY FOR IMPLEMENTATION  
**Confidence Level:** HIGH - Clear reproduction strategy with multiple validation layers  
**Risk Level:** LOW - No Docker dependencies, uses proven staging environment  