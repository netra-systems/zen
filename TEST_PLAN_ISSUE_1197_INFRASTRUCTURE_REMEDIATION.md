# TEST PLAN: Issue #1197 Foundational Infrastructure Remediation

**Generated:** 2025-09-16  
**Phase:** Infrastructure Foundation - Pre-Dependency Completion  
**Business Impact:** $500K+ ARR protection through test infrastructure stability  
**Priority:** P0 CRITICAL - Unblocks comprehensive test validation  

## Executive Summary

✅ **STRATEGY:** Focus on foundational infrastructure items that CAN be completed immediately  
✅ **APPROACH:** Non-docker priority with unit, integration, and e2e staging tests  
✅ **METHODOLOGY:** Following TEST_OPERATIONS_RUNBOOK.md and SSOT testing patterns  
❌ **BLOCKING:** Dependency resolution (Issues #1181-1186) required for full Issue #1197  

## Current State Analysis

### Infrastructure Assessment ✅

**Strengths:**
- ✅ `isolated_env` fixture implementation exists and functional  
- ✅ Mission critical tests collecting properly (9 tests in revenue protection)  
- ✅ Unified test runner operational with orchestration system  
- ✅ SSOT testing framework 94.5% compliant  
- ✅ Test framework properly structured with fixtures  

### Critical Infrastructure Issues ❌

**P0 (IMMEDIATE) - Can Be Fixed Now:**

1. **Import Path Resolution** - IMMEDIATE FIX AVAILABLE  
   - Missing `netra_backend.app.websocket_core.events.WebSocketEventManager`  
   - Tests reference non-existent module path  
   - **Impact:** Test collection failures preventing execution  
   - **Solution:** Create events.py module or update import paths  

2. **WebSocket Import Inconsistencies** - IMMEDIATE FIX AVAILABLE  
   - Tests import from `netra_backend.app.websocket_core.events` (doesn't exist)  
   - Actual WebSocket functionality in other modules  
   - **Impact:** Integration test failures  
   - **Solution:** Standardize import paths to existing modules  

3. **Configuration Alignment** - IMMEDIATE FIX AVAILABLE  
   - Staging environment configuration mismatches  
   - Port and URL inconsistencies between test and runtime  
   - **Impact:** E2E staging tests cannot connect  
   - **Solution:** Align test configuration with staging reality  

**P1 (DEPENDENCY-BLOCKED) - Cannot Fix Until Dependencies Resolved:**

4. **SSOT WebSocket Manager Fragmentation**  
   - Multiple WebSocket manager implementations causing conflicts  
   - **BLOCKED BY:** Issues #1181, #1182, #1186  
   - **Cannot proceed:** Until dependency consolidation complete  

5. **Auth Service Integration**  
   - Authentication flow disruptions affecting tests  
   - **BLOCKED BY:** Issue #1183 WebSocket Event Validation  
   - **Cannot proceed:** Until auth coordination fixed  

## TEST PLAN STRUCTURE

### PHASE 1: Infrastructure Remediation (IMMEDIATE - 1 day)

**Objective:** Fix foundational issues that can be resolved without dependency completion  
**Priority:** P0 CRITICAL  
**Can Start:** Immediately  

#### Task 1.1: Import Path Resolution (2 hours)

**Problem:** Missing `WebSocketEventManager` module causing test collection failures  

**Tests to Create:**
```bash
# Test file: tests/infrastructure/test_import_path_resolution.py
```

**Test Strategy:**
1. **Failing Test First:** Create test that reproduces import path errors  
2. **Fix Implementation:** Create missing events.py or update imports  
3. **Validation Test:** Ensure all affected tests can import successfully  

**Expected Behavior:**
- **Initially:** Test FAILS with ModuleNotFoundError  
- **After Fix:** Test PASSES with proper imports resolved  

**Test Execution:**
```bash
# Reproduce the issue
python3 -m pytest tests/integration/test_issue_1176_golden_path_websocket_race_conditions.py --collect-only

# Run infrastructure test
python3 -m pytest tests/infrastructure/test_import_path_resolution.py -v

# Validate fix
python3 -m pytest --collect-only tests/integration/ | grep "ERROR" | wc -l  # Should be 0
```

**Success Criteria:**
- [ ] All WebSocket integration tests can import successfully  
- [ ] No ModuleNotFoundError in test collection  
- [ ] Import paths follow SSOT patterns  

#### Task 1.2: Configuration Alignment (2 hours)

**Problem:** Staging configuration mismatches preventing test connectivity  

**Tests to Create:**
```bash
# Test file: tests/infrastructure/test_staging_configuration_alignment.py
```

**Test Strategy:**
1. **Configuration Validation Test:** Test staging connectivity with current config  
2. **Fix Configuration:** Align test config with staging reality  
3. **Connectivity Test:** Validate staging services reachable from tests  

**Expected Behavior:**
- **Initially:** Test FAILS with connection errors to staging  
- **After Fix:** Test PASSES with successful staging connectivity  

**Test Execution:**
```bash
# Test staging connectivity
python3 -m pytest tests/infrastructure/test_staging_configuration_alignment.py --environment=staging -v

# Validate configuration consistency
python3 -m pytest tests/e2e/staging/ --collect-only --environment=staging
```

**Success Criteria:**
- [ ] Staging environment reachable from tests  
- [ ] Configuration consistency between test and runtime  
- [ ] E2E staging tests can collect successfully  

#### Task 1.3: SSOT Testing Framework Validation (1 hour)

**Problem:** Ensure test framework follows SSOT patterns properly  

**Tests to Create:**
```bash
# Test file: tests/infrastructure/test_ssot_framework_compliance.py
```

**Test Strategy:**
1. **Framework Compliance Test:** Validate SSOT patterns in test infrastructure  
2. **Fixture Validation:** Ensure isolated_env fixture works properly  
3. **Import Compliance:** Check absolute import patterns  

**Expected Behavior:**
- **Always:** Tests PASS showing proper SSOT compliance  
- **Regression Detection:** Tests FAIL if SSOT violations introduced  

**Test Execution:**
```bash
# Test SSOT compliance
python3 -m pytest tests/infrastructure/test_ssot_framework_compliance.py -v

# Validate fixture functionality
python3 -m pytest tests/mission_critical/test_isolated_environment_compliance.py -v
```

**Success Criteria:**
- [ ] SSOT compliance maintained above 94%  
- [ ] All fixtures functioning properly  
- [ ] No relative import violations  

#### Task 1.4: Test Collection Validation (1 hour)

**Problem:** Ensure comprehensive test collection works after fixes  

**Tests to Create:**
```bash
# Test file: tests/infrastructure/test_collection_validation.py
```

**Test Strategy:**
1. **Collection Test:** Test that all test categories collect without errors  
2. **Category Validation:** Ensure test markers and categories work  
3. **Runner Integration:** Validate unified test runner functionality  

**Expected Behavior:**
- **Initially:** Some tests may fail collection due to import issues  
- **After Fix:** All tests collect successfully  

**Test Execution:**
```bash
# Test collection across categories
python3 -m pytest --collect-only tests/unit/ tests/integration/ tests/mission_critical/

# Validate unified test runner
python3 tests/unified_test_runner.py --list-categories
```

**Success Criteria:**
- [ ] All test categories collect without errors  
- [ ] Unified test runner shows all categories  
- [ ] No import or fixture errors in collection  

### PHASE 2: Non-Docker Test Validation (IMMEDIATE - 2 hours)

**Objective:** Execute tests that don't require Docker to validate infrastructure fixes  
**Priority:** P0 CRITICAL  
**Can Start:** After Phase 1 completion  

#### Task 2.1: Unit Test Execution

**Test Execution:**
```bash
# Run unit tests without Docker dependency
python3 -m pytest tests/unit/ -m "not docker_required" --tb=short

# Focus on configuration and auth unit tests
python3 -m pytest tests/unit/test_auth_validation_helpers.py tests/unit/test_factory_consolidation.py -v
```

**Success Criteria:**
- [ ] Unit tests execute without import errors  
- [ ] Configuration tests pass  
- [ ] No fixture-related failures  

#### Task 2.2: Mission Critical Test Execution

**Test Execution:**
```bash
# Run mission critical tests
python3 -m pytest tests/mission_critical/test_websocket_agent_events_revenue_protection.py -v

# Validate isolated environment compliance
python3 -m pytest tests/mission_critical/test_isolated_environment_compliance.py -v
```

**Success Criteria:**
- [ ] Mission critical tests execute successfully  
- [ ] WebSocket event tests collect and run  
- [ ] Environment isolation working properly  

#### Task 2.3: Integration Test Subset

**Test Execution:**
```bash
# Run integration tests that don't need Docker
python3 -m pytest tests/integration/ -m "not docker_required and not gcp_required" --tb=short

# Test specific integration scenarios
python3 -m pytest tests/integration/startup/ -m "not docker_required" -v
```

**Success Criteria:**
- [ ] Integration tests execute without Docker  
- [ ] Startup integration tests functional  
- [ ] No dependency-blocked test failures  

### PHASE 3: Staging Environment Test Foundation (CAN START - 4 hours)

**Objective:** Validate staging environment connectivity and test foundation  
**Priority:** P1 HIGH  
**Can Start:** After Phase 1 configuration fixes  

#### Task 3.1: Staging Connectivity Validation

**Test Execution:**
```bash
# Test staging environment connectivity
python3 -m pytest tests/e2e/staging/ -m "connectivity_check" --environment=staging -v

# Validate staging configuration
python3 -m pytest tests/infrastructure/test_staging_configuration_alignment.py --environment=staging -v
```

**Success Criteria:**
- [ ] Staging services reachable  
- [ ] Authentication working in staging  
- [ ] Database connectivity functional  

#### Task 3.2: E2E Test Foundation

**Test Execution:**
```bash
# Run E2E tests that don't require full system integration
python3 -m pytest tests/e2e/ -m "not requires_agent_system" --environment=staging -v

# Test basic WebSocket connectivity
python3 -m pytest tests/e2e/test_websocket_dev_docker_connection.py --environment=staging -v
```

**Success Criteria:**
- [ ] Basic E2E functionality working  
- [ ] WebSocket connections to staging successful  
- [ ] Foundation ready for full E2E testing  

## TEST EXECUTION COMMANDS

### Quick Infrastructure Validation
```bash
# After Phase 1 fixes - verify infrastructure health
python3 -m pytest tests/infrastructure/ -v

# Validate test collection works
python3 -m pytest --collect-only | grep "ERROR" | wc -l  # Should be 0

# Test unified test runner functionality
python3 tests/unified_test_runner.py --category unit --no-coverage --fast-fail
```

### Progressive Test Execution
```bash
# Step 1: Infrastructure tests
python3 -m pytest tests/infrastructure/ -v

# Step 2: Unit tests (non-Docker)
python3 -m pytest tests/unit/ -m "not docker_required" --tb=short

# Step 3: Mission critical tests
python3 -m pytest tests/mission_critical/ -v

# Step 4: Integration tests (non-Docker)
python3 -m pytest tests/integration/ -m "not docker_required" --tb=short

# Step 5: Staging E2E foundation
python3 -m pytest tests/e2e/staging/ --environment=staging -v
```

### Non-Docker Priority Execution
```bash
# Focus on tests that can run immediately without Docker infrastructure
python3 tests/unified_test_runner.py --categories "unit,mission_critical" --no-docker

# Staging remote tests (no local Docker needed)
python3 tests/unified_test_runner.py --category e2e --environment=staging --remote-services
```

## SUCCESS CRITERIA

### Phase 1: Infrastructure Remediation ✅
- [ ] All import path errors resolved  
- [ ] Test collection succeeds without errors  
- [ ] Staging configuration aligned with reality  
- [ ] SSOT testing patterns maintained  
- [ ] Unified test runner operational  

### Phase 2: Non-Docker Test Validation ✅
- [ ] Unit tests execute successfully (>95% pass rate)  
- [ ] Mission critical tests operational  
- [ ] Integration test subset functional  
- [ ] No fixture or import-related failures  

### Phase 3: Staging Foundation ✅
- [ ] Staging environment connectivity validated  
- [ ] E2E test foundation operational  
- [ ] WebSocket connections to staging successful  
- [ ] Ready for full system testing when dependencies resolved  

## BLOCKED ITEMS (Cannot Proceed Until Dependencies)

### WebSocket System Integration
**BLOCKED BY:** Issues #1181, #1182, #1183, #1186  
- WebSocket Manager SSOT consolidation  
- Event validation system completion  
- UserExecutionEngine SSOT migration  
- MessageRouter consolidation  

**CANNOT TEST UNTIL RESOLVED:**
- Full Golden Path E2E flows  
- Multi-user isolation validation  
- Complete agent execution workflows  
- Comprehensive WebSocket event delivery  

### Full Agent System Testing
**BLOCKED BY:** Agent orchestration dependencies  
- Complete agent execution workflows  
- Tool dispatcher integration  
- State persistence validation  
- Performance validation under load  

## RISK MITIGATION

### High-Priority Risks
1. **Import Path Changes** - Create backward compatibility where possible  
2. **Configuration Drift** - Use environment-specific validation  
3. **Test Isolation** - Ensure no cross-test pollution  
4. **Staging Availability** - Have fallback test strategies  

### Contingency Plans
1. **Gradual Execution** - Start with smallest test subsets  
2. **Isolation Testing** - Run test categories independently  
3. **Mock Fallbacks** - Use mocks only if staging unavailable  
4. **Documentation** - Document all discovered issues for dependency work  

## TIMELINE SUMMARY

| Phase | Duration | Focus | Can Start |
|-------|----------|-------|-----------|
| Phase 1: Infrastructure | 6 hours | Import paths, config, SSOT | **IMMEDIATELY** |
| Phase 2: Non-Docker Tests | 2 hours | Unit, mission critical, integration subset | **IMMEDIATELY** |
| Phase 3: Staging Foundation | 4 hours | Staging connectivity, E2E foundation | **AFTER P1** |
| **Total Immediate Work** | **12 hours** | **Foundation for dependency completion** | **1-2 days** |

## BUSINESS IMPACT

### Immediate Value Delivery
- **Test Infrastructure Stability:** Prevents test execution failures  
- **Developer Productivity:** Enables immediate test-driven development  
- **Foundation for Completion:** Sets stage for full Issue #1197 completion  
- **Risk Mitigation:** Identifies and resolves infrastructure blockers  

### Revenue Protection
- **$500K+ ARR Protection:** Ensures test validation capability maintained  
- **Quality Assurance:** Maintains testing standards during dependency work  
- **Deployment Readiness:** Infrastructure ready for staging validation  
- **Customer Trust:** Maintains platform reliability through testing  

---

**Plan Status:** ✅ READY FOR IMMEDIATE EXECUTION  
**Business Priority:** 🚨 P0 CRITICAL - Infrastructure foundation required  
**Next Action:** Begin Phase 1 Task 1.1 - Import Path Resolution  
**Dependency Note:** This plan focuses ONLY on items that can be completed immediately without waiting for Issues #1181-1186 resolution  