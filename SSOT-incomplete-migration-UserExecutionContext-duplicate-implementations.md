# SSOT-incomplete-migration-UserExecutionContext-duplicate-implementations

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/210  
**Status:** In Progress  
**SSOT Focus:** UserExecutionContext duplicate implementations blocking golden path

## CRITICAL SSOT VIOLATIONS IDENTIFIED

### 1. Multiple UserExecutionContext Implementations (Critical - Regression)
- `/netra_backend/app/models/user_execution_context.py` (26 lines, basic dataclass)
- `/netra_backend/app/agents/supervisor/user_execution_context.py` (379 lines, immutable with validation)
- `/netra_backend/app/services/user_execution_context.py` (1382 lines, MEGA CLASS with full features)
- `/netra_backend/app/agents/supervisor/execution_factory.py` (57 lines, factory-specific version)

### 2. Inconsistent Factory Patterns (Critical - Incomplete Migration)
- Multiple factory methods with different signatures
- Missing `create_for_user()` implementations
- Different validation rules across factories

### 3. Direct Instantiation Bypassing SSOT (Critical - Recent Change)
- 1000+ direct `UserExecutionContext(...)` calls
- Tests bypassing SSOT factory patterns
- Missing security validation

## GOLDEN PATH IMPACT
$500K+ ARR at risk - violations block:
1. Login Phase: Inconsistent context creation
2. WebSocket Connection: Wrong factory patterns prevent real-time communication
3. Agent Execution: Missing validation causes runtime errors
4. AI Response Delivery: Event routing fails due to inconsistent context fields

## TESTS STATUS

### DISCOVERY COMPLETE ✅
- **908 files** reference UserExecutionContext across codebase
- **68 existing test files** specifically test UserExecutionContext functionality  
- **1 mission critical test** designed to fail: `tests/mission_critical/test_execution_engine_ssot_consolidation_issues.py`
- **HIGH RISK:** Tests importing from multiple UserExecutionContext locations will break
- **MEDIUM RISK:** Integration tests relying on specific factory patterns
- **LOW RISK:** Pure business logic tests should survive

### TEST STRATEGY PLANNED ✅
**7 New SSOT Tests (20% of effort):**
1. SSOT Import Compliance validation
2. SSOT Factory Pattern validation  
3. SSOT User Isolation Consistency
4. SSOT Golden Path Protection
5. SSOT Backwards Compatibility
6. Staging SSOT Golden Path (E2E)
7. SSOT Performance validation

**Success Criteria:**
- Mission critical test PASSES (currently FAILS)
- Single import path for UserExecutionContext
- 100% pass rate on mission critical tests
- Golden path preserved (login → AI response)

## REMEDIATION PLAN STATUS
- [x] Step 1: Discover and plan tests ✅
- [ ] Step 2: Execute test plan (20% new SSOT tests) 🔄
- [ ] Step 3: Plan SSOT remediation
- [ ] Step 4: Execute remediation
- [ ] Step 5: Test fix loop until all pass
- [ ] Step 6: PR and closure

## NEXT ACTIONS
1. Discover existing tests protecting UserExecutionContext
2. Plan new SSOT tests for violations (20% of work)
3. Execute SSOT remediation maintaining system stability

**Last Updated:** 2025-01-09