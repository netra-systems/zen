# SSOT-incomplete-migration-agent-factory-singleton-blocking-golden-path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1142  
**Created:** 2025-09-14  
**Status:** DISCOVERY COMPLETE - PLANNING TESTS

## 🚨 CRITICAL SSOT VIOLATION SUMMARY

**BLOCKING GOLDEN PATH:** Users login ✅ but AI responses ❌ FAIL due to multi-user state contamination

### Root Cause Analysis
- **Location:** `/netra_backend/app/agents/supervisor/agent_instance_factory.py` lines 1165-1189
- **Production Issue:** `/netra_backend/app/dependencies.py` lines 31-34 uses singleton pattern
- **Violation Type:** Global singleton `_factory_instance` shared across all users
- **Impact:** Multi-user state bleeding preventing proper AI response isolation

### SSOT Violation Details
1. **Multi-User Contamination:** Shared factory state across users
2. **Session Leakage:** Database sessions and WebSocket emitters shared inappropriately  
3. **Incomplete Migration:** Correct per-request pattern exists but not used in production dependencies
4. **Golden Path Blocking:** AI responses contaminated with other users' state

### Required Fix
Replace `configure_agent_instance_factory()` singleton usage with `create_agent_instance_factory(user_context)` per-request pattern in `dependencies.py`

## PROGRESS TRACKING

### ✅ Step 0: DISCOVERY COMPLETE
- [x] SSOT audit identified critical agent factory singleton violation
- [x] GitHub issue #1142 created
- [x] Progress tracker (this file) created

### ✅ Step 1: DISCOVER AND PLAN TEST COMPLETE
- [x] 1.1 DISCOVER EXISTING: **EXCELLENT** - 176 test files already cover agent factory violations!
- [x] 1.2 PLAN ONLY: Minimal new tests needed (20% work) - existing coverage comprehensive

## 🎯 CRITICAL DISCOVERY: COMPREHENSIVE TEST COVERAGE EXISTS

### Existing Vulnerability Tests (READY TO PROVE VIOLATION)
**PRIMARY TESTS:** Already exist and should FAIL due to singleton contamination:
- `/tests/unit/agents/test_agent_instance_factory_singleton_violations_1116.py` - 8 tests proving contamination
- `/tests/integration/agents/test_agent_factory_user_isolation_integration.py` - 3 real-service integration tests
- `/tests/e2e/test_golden_path_multi_user_concurrent.py` - 3 end-to-end Golden Path tests

### Test Strategy: FAIL-THEN-PASS VALIDATION
**BEFORE SSOT FIX:** Existing tests should FAIL (proving singleton contamination)  
**AFTER SSOT FIX:** Same tests should PASS (proving per-request isolation)

### New Tests Required (20% of work)
1. **SSOT Migration Validation:** Tests proving per-request factory pattern works
2. **Dependencies.py Integration:** Tests proving FastAPI dependency injection works  
3. **Regression Prevention:** Automated scanning for singleton pattern reintroduction

### 🔄 Step 2: EXECUTE TEST PLAN (NEXT)
- [ ] Run existing vulnerability tests to PROVE singleton contamination exists
- [ ] Create minimal new SSOT validation tests (20% work)
- [ ] Validate test execution approach (unit/integration/e2e staging remote - NO DOCKER)

### ⏳ PENDING STEPS
- [ ] Step 3: PLAN REMEDIATION
- [ ] Step 4: EXECUTE REMEDIATION  
- [ ] Step 5: TEST FIX LOOP (comprehensive test suite ready!)
- [ ] Step 6: PR AND CLOSURE

## TEST EXECUTION STRATEGY
**COMPREHENSIVE EXISTING COVERAGE:** 176 test files protect against breaking changes!

**VALIDATION APPROACH:**
1. **PROVE VIOLATION:** Run existing tests (should FAIL due to singleton contamination)
2. **IMPLEMENT FIX:** Replace singleton with per-request pattern in dependencies.py
3. **PROVE SOLUTION:** Run same tests (should PASS proving user isolation works)

**KEY TEST COMMANDS:**
```bash
# Existing vulnerability tests (should FAIL before fix)
python -m pytest tests/unit/agents/test_agent_instance_factory_singleton_violations_1116.py -v
python -m pytest tests/integration/agents/test_agent_factory_user_isolation_integration.py -v  
python -m pytest tests/e2e/test_golden_path_multi_user_concurrent.py -v
```

## FILES TO MODIFY
1. `/netra_backend/app/dependencies.py` (CRITICAL - singleton usage removal)
2. `/netra_backend/app/agents/supervisor/agent_instance_factory.py` (validation/cleanup)
3. Tests protecting multi-user isolation (TBD in Step 1)

## SUCCESS CRITERIA
- [ ] All existing tests continue to pass
- [ ] New tests validate user isolation
- [ ] Golden path: users login → get AI responses ✅ works in multi-user environment
- [ ] No singleton patterns in agent factory production usage