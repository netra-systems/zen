# SSOT-regression-websocket-url-env-var-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/507
**Priority:** P0 (Critical/Blocking - Golden Path Broken)
**Created:** 2025-09-11

## Problem Statement
Duplicate and conflicting WebSocket URL environment variables create configuration confusion that directly blocks the Golden Path user flow (users login → get AI responses):

- `NEXT_PUBLIC_WS_URL` (canonical)
- `NEXT_PUBLIC_WEBSOCKET_URL` (competing/duplicate)

## Business Impact
- **Golden Path Blocking:** WebSocket connection failures prevent AI responses
- **Revenue Risk:** Core chat functionality (90% of platform value) affected  
- **Configuration Chaos:** Developers unsure which variable to use
- **Environment Inconsistency:** Different vars used across dev/staging/prod

## Work Progress Tracker

### ✅ Step 0: SSOT Audit Complete
- [x] Identified critical WebSocket URL environment variable duplication
- [x] Created GitHub issue #507
- [x] Created local tracking file

### ✅ Step 1.1: Discover Existing WebSocket Tests (COMPLETED)
- [x] 1.1 Discover existing WebSocket configuration tests
- [x] Found 46 identified tests across 6 critical areas
- [x] Identified 3 critical SSOT violation patterns in existing tests
- [x] Assessed test impact categories: 6 must fail, 25+ should pass, 15+ need creation

#### Test Discovery Summary:
**Existing Test Categories Found:**
- **Environment Variable Validation**: 3 core tests with SSOT violations
- **Golden Path Protection**: 15+ WebSocket connectivity tests  
- **Configuration Monitoring**: 6+ drift detection tests
- **Deployment Validation**: 4+ GCP deployment tests
- **Authentication Integration**: 8+ WebSocket auth tests
- **SSOT Infrastructure**: 10+ configuration tests

**Critical SSOT Violations in Tests:**
- **Pattern 1**: Dual variable definition in test setup (3 files)
- **Pattern 2**: Deployment validation enforcing both variables (2 files)  
- **Pattern 3**: Configuration drift monitoring both variables (1 file)

### ✅ Step 1.2: Plan New SSOT Validation Tests (COMPLETED)
- [x] Initial test planning completed
- [x] Detailed test implementation specifications

#### New SSOT Test Plan:
**Test Distribution:**
- **20% Unit Tests**: Environment variable SSOT validation (4 test classes)
- **60% Integration Tests**: Real WebSocket connection validation (4 test classes) 
- **20% E2E Tests**: Golden Path SSOT protection (2 test classes)

**Key Test Classes to Create:**
1. `TestWebSocketURLSSOTValidation` - Unit validation
2. `TestWebSocketSSOTIntegration` - Service integration  
3. `TestWebSocketSSOTConnectionValidation` - Real connection tests
4. `TestWebSocketSSOTGoldenPathProtection` - E2E validation

**Expected Test Outcomes:**
- **Pre-SSOT Fix**: 6 tests must fail (dual-variable detection)
- **Post-SSOT Fix**: 15 new SSOT tests pass, 25+ Golden Path tests pass
- **Business Protection**: $500K+ ARR Golden Path validated via staging E2E

### ✅ Step 2: Execute Test Plan (COMPLETED)
- [x] Create new SSOT tests for WebSocket configuration 
- [x] Validate test execution (non-docker)

#### New SSOT Tests Created:
**Test Distribution Implemented:**
- **Unit Tests**: 4 test classes (`tests/unit/websocket/ssot/`)
  - `TestWebSocketURLSSOTValidation` - Core SSOT violation detection
  - `TestWebSocketConfigurationSSOTConsistency` - Configuration consistency
- **Integration Tests**: 2 test classes (`tests/integration/websocket/ssot/`)
  - `TestWebSocketSSOTServiceIntegration` - Service integration
  - `TestWebSocketSSOTConnectionValidation` - Real connection tests
- **E2E Tests**: 1 test class (`tests/e2e/websocket/ssot/`)
  - `TestWebSocketSSOTGoldenPathProtection` - Golden Path validation

**Test Execution Commands Ready:**
```bash
# Unit SSOT validation
python tests/unified_test_runner.py --category unit --pattern "*websocket*ssot*"

# Integration with real services  
python tests/unified_test_runner.py --category integration --real-services --env staging --pattern "*websocket*ssot*"

# E2E Golden Path protection
python tests/unified_test_runner.py --category e2e --env staging --pattern "*golden_path*websocket*"
```

**Expected Test Behavior:**
- **Currently**: Tests MUST FAIL (detecting dual variables by design)
- **After SSOT Fix**: Tests MUST PASS (confirming consolidation successful)

### ✅ Step 3: Plan SSOT Remediation (COMPLETED)
- [x] Plan consolidation to single canonical variable
- [x] Plan elimination of duplicate references
- [x] Created comprehensive 5-phase remediation strategy
- [x] Conducted complete file audit across codebase
- [x] Identified risk areas and mitigation strategies

#### SSOT Remediation Strategy:
**Current State:** Duplicate variables causing Golden Path confusion
- **Canonical:** `NEXT_PUBLIC_WS_URL` (94 occurrences)
- **Duplicate:** `NEXT_PUBLIC_WEBSOCKET_URL` (47 occurrences) 
- **Total Affected Files:** 141+ across entire codebase

**5-Phase Migration Plan:**
1. **Phase 1:** Environment Configuration Consolidation (HIGH RISK)
   - Target: All `.env*` files, Docker configurations, deployment scripts
   - Standardize on `NEXT_PUBLIC_WS_URL` as canonical variable

2. **Phase 2:** Frontend Code Migration (CRITICAL - Golden Path Impact)
   - Target: `frontend/lib/unified-api-config.ts` and WebSocket connection code
   - Fix staging environment variable resolution

3. **Phase 3:** Test Infrastructure Cleanup (MEDIUM RISK)
   - Target: 40+ test files using deprecated variable
   - Update SSOT validation tests to pass

4. **Phase 4:** Documentation and Validation Scripts (LOW RISK)
   - Target: Documentation, validation scripts, monitoring
   - Update deployment verification checklists

5. **Phase 5:** Final Validation and Cleanup (SAFETY NET)
   - Target: Complete system validation and Golden Path testing
   - Deploy to staging for comprehensive validation

**Risk Mitigation:**
- **Atomic Changes:** Each phase deployable independently
- **Staging First:** All changes validated before production
- **Rollback Ready:** Each phase reversible within 5 minutes
- **Golden Path Protection:** Continuous chat functionality monitoring

### ⏳ Step 4: Execute SSOT Remediation (PENDING)
- [ ] Implement WebSocket URL SSOT consolidation
- [ ] Update all references to use canonical variable

### ⏳ Step 5: Test Fix Loop (PENDING)
- [ ] Run all tests and fix any failures
- [ ] Validate Golden Path WebSocket connectivity

### ⏳ Step 6: PR and Closure (PENDING)
- [ ] Create PR linking to issue #507
- [ ] Ensure all acceptance criteria met

## Files Identified for Remediation
- Frontend WebSocket connection logic
- Environment configuration files (.env, .env.example, etc.)
- Docker compose configurations
- Deployment scripts
- Any hardcoded WebSocket URL references

## Test Strategy
- Focus on unit, integration (non-docker), and e2e staging GCP tests
- ~20% new SSOT validation tests, ~60% updating existing tests, ~20% validating fixes
- Ensure Golden Path WebSocket connectivity tests pass

## Acceptance Criteria
- [ ] Single WebSocket URL environment variable across codebase
- [ ] All WebSocket connections use canonical configuration (`NEXT_PUBLIC_WS_URL`)
- [ ] Golden Path WebSocket connectivity restored
- [ ] Tests validate WebSocket connection stability
- [ ] No configuration conflicts between environments

## Notes
- This is a P0 critical issue that directly impacts $500K+ ARR
- Golden Path must remain functional throughout remediation
- All changes must be atomic and not introduce breaking changes