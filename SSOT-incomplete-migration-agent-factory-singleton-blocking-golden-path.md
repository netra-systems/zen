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

### 🔄 Step 1: DISCOVER AND PLAN TEST (IN PROGRESS)
- [ ] 1.1 DISCOVER EXISTING: Find existing tests protecting against breaking changes
- [ ] 1.2 PLAN ONLY: Plan unit/integration/e2e tests for SSOT refactor validation

### ⏳ PENDING STEPS
- [ ] Step 2: EXECUTE TEST PLAN (20% new SSOT tests)
- [ ] Step 3: PLAN REMEDIATION
- [ ] Step 4: EXECUTE REMEDIATION  
- [ ] Step 5: TEST FIX LOOP
- [ ] Step 6: PR AND CLOSURE

## TEST REQUIREMENTS
Focus on:
- Agent factory user isolation tests
- Multi-user concurrent execution validation
- WebSocket event delivery isolation
- Golden path end-to-end user flow testing

## FILES TO MODIFY
1. `/netra_backend/app/dependencies.py` (CRITICAL - singleton usage removal)
2. `/netra_backend/app/agents/supervisor/agent_instance_factory.py` (validation/cleanup)
3. Tests protecting multi-user isolation (TBD in Step 1)

## SUCCESS CRITERIA
- [ ] All existing tests continue to pass
- [ ] New tests validate user isolation
- [ ] Golden path: users login → get AI responses ✅ works in multi-user environment
- [ ] No singleton patterns in agent factory production usage