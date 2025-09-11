# Redis SSOT Violation Test Plan - Issue #226

> **Generated:** 2025-09-11 | **Issue:** [#226](https://github.com/netra-systems/netra-apex/issues/226)
> 
> **Purpose:** Comprehensive testing strategy for detecting and validating Redis import violations
> 
> **Status:** 59 remaining violations after Phase 1A completion

---

## Executive Summary

### Test Strategy Overview
This test plan addresses the remaining 59 Redis import violations in issue #226 by creating targeted tests that:
1. **Detect existing violations** without Docker dependency
2. **Validate SSOT compliance** after fixes
3. **Prevent regressions** through CI/CD enforcement  
4. **Guide migration** with clear failure modes

### Key Testing Principles
- **Real Services First:** Use actual Redis where possible, avoid mocks
- **No Docker Dependency:** All tests must run without Docker for CI/CD
- **Failing First:** Tests initially fail to demonstrate violations
- **Clear Messages:** Specific error messages guide developers to fixes

---

## Current Violation Analysis

### Primary Violation Patterns Identified

#### 1. Direct RedisManager() Instantiation (26+ files)
**Pattern:** `RedisManager()` instead of using singleton `redis_manager`
```python
# VIOLATION (Current)
redis_manager = RedisManager()

# CORRECT (SSOT)
from netra_backend.app.redis_manager import redis_manager
```

#### 2. Deprecated Import Patterns (50+ test files)  
**Pattern:** Using compatibility layers instead of SSOT imports
```python
# VIOLATIONS (Current)
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
from auth_service.auth_core.redis_manager import AuthRedisManager

# CORRECT (SSOT)
from netra_backend.app.redis_manager import redis_manager, RedisManager
```

#### 3. Analytics Service SSOT Violations
**Pattern:** Analytics service not fully migrated to SSOT pattern
```python
# NEEDS MIGRATION
from analytics_service.redis_manager import AnalyticsRedisManager
```

---

## Test Plan Details

### 1. Violation Detection Tests

#### 1.1. Import Pattern Detection Test
**Purpose:** Detect all remaining deprecated import patterns
**Type:** Unit Test (No Docker Required)
**Expected Initial Result:** FAIL (59 violations detected)

**Test File:** `tests/mission_critical/test_redis_import_violations.py`

```python
class TestRedisImportViolations:
    def test_no_deprecated_redis_imports(self):
        """Test that no files use deprecated Redis import patterns."""
        violations = self._scan_for_violations()
        assert len(violations) == 0, (
            f"Found {len(violations)} Redis import violations:\n"
            + "\n".join([f"  {file}:{line} - {pattern}" for file, line, pattern in violations])
            + "\n\nUse SSOT import: from netra_backend.app.redis_manager import redis_manager"
        )
    
    def test_no_direct_redis_manager_instantiation(self):
        """Test that no files directly instantiate RedisManager()."""
        violations = self._scan_for_direct_instantiation()
        assert len(violations) == 0, (
            f"Found {len(violations)} direct RedisManager() instantiations:\n"
            + "\n".join([f"  {file}:{line}" for file, line in violations])
            + "\n\nUse singleton: from netra_backend.app.redis_manager import redis_manager"
        )
```

#### 1.2. SSOT Compliance Test
**Purpose:** Validate that all Redis access goes through SSOT
**Type:** Integration Test (No Docker Required)
**Expected Initial Result:** FAIL (non-SSOT patterns detected)

**Test File:** `tests/integration/test_redis_ssot_compliance.py`

```python
class TestRedisSSOTCompliance:
    def test_all_redis_access_through_ssot(self):
        """Test that all Redis access uses SSOT pattern."""
        non_ssot_files = self._find_non_ssot_redis_usage()
        assert len(non_ssot_files) == 0, (
            f"Found non-SSOT Redis usage in {len(non_ssot_files)} files:\n"
            + "\n".join(non_ssot_files)
        )
    
    def test_redis_manager_singleton_consistency(self):
        """Test that redis_manager is consistently the same instance."""
        from netra_backend.app.redis_manager import redis_manager
        
        # Import from different potential paths
        instances = []
        instances.append(redis_manager)
        
        # Verify all are the same instance
        for i, instance in enumerate(instances[1:], 1):
            assert instance is instances[0], (
                f"Redis manager instance {i} is not the same as SSOT instance"
            )
```

### 2. Migration Validation Tests

#### 2.1. Functionality Preservation Test
**Purpose:** Ensure SSOT migration doesn't break existing functionality
**Type:** Integration Test (Real Redis - GCP Staging)
**Expected Initial Result:** PASS (functionality works, imports wrong)

**Test File:** `tests/integration/test_redis_migration_validation.py`

```python
class TestRedisMigrationValidation:
    async def test_auth_redis_functionality_preserved(self):
        """Test that auth Redis functionality works after SSOT migration."""
        from netra_backend.app.redis_manager import redis_manager
        
        # Test session management
        session_key = "test_session_12345"
        session_data = {"user_id": "user_123", "permissions": ["read", "write"]}
        
        await redis_manager.set_json(session_key, session_data, expire=3600)
        retrieved_data = await redis_manager.get_json(session_key)
        
        assert retrieved_data == session_data
        await redis_manager.delete(session_key)
    
    async def test_cache_redis_functionality_preserved(self):
        """Test that cache Redis functionality works after SSOT migration."""
        from netra_backend.app.redis_manager import redis_manager
        
        # Test caching operations
        cache_key = "test_cache_item"
        cache_value = {"computed_result": "expensive_operation_result"}
        
        await redis_manager.set_json(cache_key, cache_value, expire=1800)
        cached_result = await redis_manager.get_json(cache_key)
        
        assert cached_result == cache_value
        await redis_manager.delete(cache_key)
```

#### 2.2. Deprecation Warning Test
**Purpose:** Ensure compatibility layers show appropriate warnings
**Type:** Unit Test (No Docker Required)  
**Expected Initial Result:** PASS (warnings are shown)

**Test File:** `tests/unit/test_redis_deprecation_warnings.py`

```python
class TestRedisDeprecationWarnings:
    def test_auth_redis_manager_shows_warning(self):
        """Test that auth_service redis imports show deprecation warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Import that should trigger warning
            from auth_service.auth_core.redis_manager import AuthRedisManager
            
            assert len(w) > 0
            assert any("DEPRECATED" in str(warning.message) for warning in w)
            assert any("netra_backend.app.redis_manager" in str(warning.message) for warning in w)
    
    def test_cache_redis_manager_shows_warning(self):
        """Test that cache redis imports show deprecation warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
            
            assert len(w) > 0
            assert any("DEPRECATED" in str(warning.message) for warning in w)
```

### 3. CI/CD Enforcement Tests

#### 3.1. Pre-Commit Validation Test
**Purpose:** Block commits that introduce new Redis violations
**Type:** Static Analysis Test (No Docker Required)
**Expected Initial Result:** Configuration needed

**Test File:** `tests/ci_cd/test_redis_pre_commit_validation.py`

```python
class TestRedisPreCommitValidation:
    def test_git_hooks_prevent_redis_violations(self):
        """Test that git hooks prevent Redis import violations."""
        # This test validates the pre-commit hook configuration
        hook_content = self._read_pre_commit_config()
        
        assert "redis-ssot-check" in hook_content, (
            "Pre-commit hook missing Redis SSOT validation"
        )
    
    def test_ci_pipeline_includes_redis_checks(self):
        """Test that CI pipeline includes Redis violation checks."""
        ci_config = self._read_ci_config()
        
        assert "test_redis_import_violations" in ci_config, (
            "CI pipeline missing Redis violation tests"
        )
```

#### 3.2. Regression Prevention Test
**Purpose:** Ensure fixes don't regress over time
**Type:** Integration Test (No Docker Required)
**Expected Initial Result:** FAIL initially, PASS after fixes

**Test File:** `tests/regression/test_redis_ssot_regression_prevention.py`

```python
class TestRedisSSOTRegressionPrevention:
    def test_no_new_redis_violations_since_baseline(self):
        """Test that no new Redis violations are introduced."""
        baseline_violations = 59  # Current known violations
        current_violations = self._count_current_violations()
        
        assert current_violations <= baseline_violations, (
            f"New Redis violations detected! Current: {current_violations}, "
            f"Baseline: {baseline_violations}. "
            f"New violations: {current_violations - baseline_violations}"
        )
    
    def test_violation_count_decreases_over_time(self):
        """Test that violation count only decreases, never increases."""
        violation_history = self._load_violation_history()
        
        if len(violation_history) > 1:
            latest_count = violation_history[-1]['count']
            previous_count = violation_history[-2]['count']
            
            assert latest_count <= previous_count, (
                f"Violation count increased from {previous_count} to {latest_count}"
            )
```

### 4. Performance Impact Tests

#### 4.1. SSOT Performance Test
**Purpose:** Ensure SSOT pattern doesn't degrade performance
**Type:** Performance Test (Real Redis - GCP Staging)
**Expected Initial Result:** PASS (SSOT should be equal/better performance)

**Test File:** `tests/performance/test_redis_ssot_performance.py`

```python
class TestRedisSSOTPerformance:
    async def test_ssot_redis_performance_baseline(self):
        """Test that SSOT Redis performance meets baseline requirements."""
        from netra_backend.app.redis_manager import redis_manager
        
        # Performance test parameters
        num_operations = 1000
        max_avg_latency_ms = 50
        
        start_time = time.time()
        
        for i in range(num_operations):
            await redis_manager.set(f"perf_test_{i}", f"value_{i}")
            await redis_manager.get(f"perf_test_{i}")
            await redis_manager.delete(f"perf_test_{i}")
        
        end_time = time.time()
        avg_latency_ms = ((end_time - start_time) / num_operations) * 1000
        
        assert avg_latency_ms < max_avg_latency_ms, (
            f"SSOT Redis performance degraded: {avg_latency_ms:.2f}ms > {max_avg_latency_ms}ms"
        )
```

---

## Test Execution Strategy

### Phase 1: Detection (Current State Validation)
**Goal:** Identify all 59 remaining violations
**Expected Result:** All tests FAIL, providing clear guidance

```bash
# Run violation detection tests
python -m pytest tests/mission_critical/test_redis_import_violations.py -v

# Expected output:
# FAILED: Found 26 direct RedisManager() instantiations
# FAILED: Found 33 deprecated import patterns
```

### Phase 2: Migration Validation (During Fixes)
**Goal:** Validate each fix preserves functionality
**Expected Result:** Functionality tests PASS, compliance tests gradually improve

```bash
# Run migration validation tests
python -m pytest tests/integration/test_redis_migration_validation.py -v

# Run compliance tests to track progress
python -m pytest tests/integration/test_redis_ssot_compliance.py -v
```

### Phase 3: Enforcement (Post-Fix)
**Goal:** Prevent future regressions
**Expected Result:** All tests PASS, CI/CD blocks violations

```bash
# Run full Redis SSOT test suite
python -m pytest tests/ -k "redis" -v

# Run in CI/CD pipeline
python tests/unified_test_runner.py --category redis_ssot --fast-fail
```

### Non-Docker Test Execution
All tests designed to run without Docker for CI/CD compatibility:

```bash
# Unit tests (no external dependencies)
python -m pytest tests/unit/test_redis_deprecation_warnings.py

# Integration tests (GCP staging Redis)
REDIS_URL=redis://staging-redis:6379 python -m pytest tests/integration/test_redis_migration_validation.py

# Static analysis tests (filesystem only)
python -m pytest tests/ci_cd/test_redis_pre_commit_validation.py
```

---

## Expected Test Failure Modes

### Initial State (Before Fixes)
1. **Import Violations:** 59 violations detected across 26+ files
2. **Direct Instantiation:** Multiple `RedisManager()` calls found
3. **Non-SSOT Usage:** Test files using deprecated patterns
4. **Missing Warnings:** Some compatibility layers not showing deprecation warnings

### During Migration
1. **Partial Compliance:** Violation count decreases but not zero
2. **Functionality Maintained:** All functional tests continue to pass
3. **Performance Stable:** No degradation in Redis operation times

### Post-Fix (Success State)
1. **Zero Violations:** All import pattern tests pass
2. **Full SSOT Compliance:** All Redis access through single source
3. **Deprecation Warnings:** Clear guidance for any remaining compatibility usage
4. **CI/CD Protection:** New violations blocked by automated checks

---

## Success Criteria

### Immediate Success (Phase 1)
- [ ] **Violation Detection:** Tests accurately identify all 59 violations
- [ ] **Clear Guidance:** Error messages guide developers to correct imports
- [ ] **Non-Docker Execution:** All tests run without Docker dependency
- [ ] **CI/CD Ready:** Tests can be integrated into automated pipeline

### Migration Success (Phase 2)
- [ ] **Functionality Preserved:** All Redis operations continue working
- [ ] **Progressive Improvement:** Violation count decreases with each fix
- [ ] **Performance Maintained:** No degradation in Redis operation speed
- [ ] **Clear Warnings:** Deprecated imports show helpful guidance

### Long-term Success (Phase 3)
- [ ] **Zero Violations:** All files use SSOT Redis import patterns
- [ ] **Regression Prevention:** CI/CD blocks new violations
- [ ] **Developer Experience:** Clear error messages and documentation
- [ ] **System Stability:** Redis operations reliable and consistent

---

## CI/CD Integration Plan

### Pre-Commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: redis-ssot-check
        name: Redis SSOT Compliance Check
        entry: python tests/mission_critical/test_redis_import_violations.py
        language: system
        files: \.py$
        fail_fast: true
```

### GitHub Actions Integration
```yaml
# .github/workflows/redis-ssot-validation.yml
name: Redis SSOT Validation
on: [push, pull_request]
jobs:
  redis-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Redis SSOT Tests
        run: |
          python -m pytest tests/mission_critical/test_redis_import_violations.py
          python -m pytest tests/integration/test_redis_ssot_compliance.py
```

### Daily Regression Monitoring
```bash
# Daily cron job to track violation count
python tests/regression/test_redis_ssot_regression_prevention.py --update-baseline
```

---

## Implementation Timeline

### Week 1: Test Infrastructure
- [ ] Create violation detection tests
- [ ] Set up non-Docker test execution
- [ ] Implement static analysis scanning
- [ ] Create baseline measurement tools

### Week 2: Migration Support  
- [ ] Create migration validation tests
- [ ] Implement functionality preservation tests
- [ ] Set up performance monitoring
- [ ] Create developer guidance tools

### Week 3: CI/CD Integration
- [ ] Set up pre-commit hooks
- [ ] Integrate with GitHub Actions
- [ ] Create regression monitoring
- [ ] Implement automated reporting

### Week 4: Validation & Documentation
- [ ] Run full test suite validation
- [ ] Document test execution procedures
- [ ] Create developer migration guide
- [ ] Set up ongoing monitoring

---

## Files to Create/Modify

### New Test Files
1. `tests/mission_critical/test_redis_import_violations.py`
2. `tests/integration/test_redis_ssot_compliance.py`  
3. `tests/integration/test_redis_migration_validation.py`
4. `tests/unit/test_redis_deprecation_warnings.py`
5. `tests/ci_cd/test_redis_pre_commit_validation.py`
6. `tests/regression/test_redis_ssot_regression_prevention.py`
7. `tests/performance/test_redis_ssot_performance.py`

### Configuration Files
1. `.pre-commit-config.yaml` (update)
2. `.github/workflows/redis-ssot-validation.yml` (new)
3. `pyproject.toml` (update test configuration)

### Utility Scripts
1. `scripts/scan_redis_violations.py` (static analysis)
2. `scripts/track_redis_violation_progress.py` (monitoring)
3. `scripts/validate_redis_ssot_compliance.py` (validation)

---

## GitHub Issue Update Plan

### Issue #226 Comment Template

```markdown
## Redis SSOT Violation Test Plan - Ready for Implementation

### Test Strategy Summary
Created comprehensive test plan to detect and validate the remaining 59 Redis import violations:

**Test Categories:**
- ✅ **Violation Detection Tests** - Identify all deprecated import patterns  
- ✅ **SSOT Compliance Tests** - Validate proper SSOT usage
- ✅ **Migration Validation Tests** - Ensure functionality preservation
- ✅ **CI/CD Enforcement Tests** - Prevent future regressions

**Key Features:**
- 🔧 **No Docker Dependency** - All tests run without Docker for CI/CD
- 📊 **Clear Failure Modes** - Specific error messages guide developers
- 🚀 **Real Services** - Use actual Redis where possible, minimal mocks
- 🛡️ **Regression Prevention** - Automated checks block new violations

### Next Steps
1. **Implement Detection Tests** - Create tests that identify all 59 violations
2. **Set up CI/CD Integration** - Add pre-commit hooks and GitHub Actions
3. **Begin Migration** - Use tests to guide systematic fixes
4. **Monitor Progress** - Track violation count reduction over time

### Expected Timeline
- **Week 1:** Test infrastructure setup
- **Week 2:** Migration support tools  
- **Week 3:** CI/CD integration
- **Week 4:** Validation and documentation

See full test plan: [`reports/testing/REDIS_SSOT_VIOLATION_TEST_PLAN_ISSUE_226.md`](reports/testing/REDIS_SSOT_VIOLATION_TEST_PLAN_ISSUE_226.md)
```

---

*Generated by Netra Apex Test Planning System v2.1.0 - Redis SSOT Migration Support*