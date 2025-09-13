# SSOT-incomplete-migration-execution-engine-factory-chaos

**GitHub Issue:** [#710](https://github.com/netra-systems/netra-apex/issues/710)
**Priority:** P0 (Critical/blocking - Golden Path broken)
**Created:** 2025-09-12
**Status:** DISCOVERY COMPLETE

## Progress Tracker

### ✅ COMPLETED
- [x] **SSOT Audit Discovery**: Identified 6+ duplicate ExecutionEngine factory implementations
- [x] **GitHub Issue Created**: Issue #710 created with P0 priority
- [x] **Progress Tracker**: SSOT-incomplete-migration-execution-engine-factory-chaos.md created

### 🔄 IN PROGRESS
- [ ] **Test Discovery and Planning**: Identify existing tests protecting against breaking changes

### 📋 PENDING
- [ ] **Execute Test Plan**: Create 20% new SSOT tests for validation
- [ ] **Plan SSOT Remediation**: Design factory consolidation strategy
- [ ] **Execute SSOT Remediation**: Implement single authoritative factory
- [ ] **Test Fix Loop**: Ensure all tests pass after remediation
- [ ] **PR Creation**: Create pull request to close issue

## CRITICAL SSOT Violations Found

### 🚨 Execution Engine Factory Chaos
**Files with duplicate factory implementations:**
1. `netra_backend/app/agents/supervisor/execution_engine_unified_factory.py`
2. `netra_backend/app/agents/supervisor/execution_engine_factory.py` (MODIFIED)
3. `netra_backend/app/agents/supervisor/execution_factory.py`
4. `netra_backend/app/agents/supervisor/agent_instance_factory.py` (MODIFIED)
5. Additional factory patterns throughout agent system

### Business Impact
- **BLOCKS GOLDEN PATH**: Users login → get AI responses flow failing
- **$500K+ ARR AT RISK**: Chat functionality unreliable
- **WebSocket Race Conditions**: Event loss causing customer failures
- **Active Development Conflict**: Git modifications to affected files

### Golden Path Failure Mode
1. User logs in successfully ✅
2. User sends chat message ✅
3. **FAILURE**: Agent execution engine creation inconsistent ❌
4. **FAILURE**: WebSocket events lost due to factory race conditions ❌
5. **FAILURE**: User receives no AI response ❌

## Test Plan (To Be Developed)

### Existing Tests to Protect
- TBD: Discover existing tests that must continue passing

### New SSOT Tests Needed (~20% of effort)
- TBD: Tests validating single factory pattern
- TBD: Tests ensuring WebSocket event delivery
- TBD: Golden Path end-to-end validation

## Remediation Strategy (To Be Planned)

### SSOT Consolidation Goals
1. **Single Authority**: Choose ONE execution engine factory as SSOT
2. **Migration Plan**: Move all consumers to SSOT factory
3. **Cleanup**: Remove all duplicate implementations
4. **Validation**: Ensure Golden Path reliability

## Testing Status
- **Docker Dependency**: Will use non-docker tests (unit, integration without docker, e2e on staging GCP)
- **Real Services**: Prefer real services over mocks for integration testing
- **Mission Critical**: Must pass WebSocket agent events suite

## Success Criteria
- [ ] Only ONE execution engine factory exists
- [ ] All agent creation uses SSOT factory
- [ ] WebSocket events reliably delivered
- [ ] Golden Path test passes: users login → get AI responses
- [ ] All existing tests continue to pass

---
**Last Updated:** 2025-09-12
**Next Action:** Test Discovery and Planning (Step 1)