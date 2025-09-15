# SSOT-incomplete-migration-agent-instance-factory-singleton-blocks-golden-path

## 🚨 CRITICAL: Agent Instance Factory Singleton Blocking Multi-User Golden Path

**Business Impact**: CRITICAL - $500K+ ARR chat functionality compromised by user context leakage

**Issue Created**: https://github.com/netra-systems/netra-apex/issues/1116

**Progress Tracker**: SSOT-incomplete-migration-agent-instance-factory-singleton-blocks-golden-path.md

---

## DISCOVERY SUMMARY

**Location**: `netra_backend/app/agents/supervisor/agent_instance_factory.py:1135-1190`

### The Problem
- **Singleton Pattern**: `_factory_instance` with global state causes user context leakage
- **Shared Factory**: `get_agent_instance_factory()` creates single factory shared between all users  
- **CRITICAL SECURITY**: User A's chat responses delivered to User B
- **WebSocket Events**: Delivered to wrong users in multi-user scenarios

### Golden Path Impact
- ❌ Agent execution state contamination between concurrent users
- ❌ Chat responses routed to incorrect users (data leakage)  
- ❌ WebSocket events broadcast to wrong connections
- ❌ Enterprise security vulnerability blocks $500K+ ARR deployment

### SSOT Solution Available
**Lines 1136-1162**: NEW SSOT pattern `create_agent_instance_factory(user_context)` already implemented

### Immediate Fix Required
Replace all `get_agent_instance_factory()` calls with `create_agent_instance_factory(user_context)`

---

## WORK IN PROGRESS

### Step 0: ✅ DISCOVERY COMPLETE
- [x] SSOT audit identified critical singleton pattern violation
- [x] Confirmed SSOT solution already exists in codebase
- [x] Business impact assessment: $500K+ ARR at risk

### Step 1: DISCOVER AND PLAN TESTS - TODO
- [ ] Find existing tests protecting against singleton pattern violations
- [ ] Plan new tests to reproduce user context leakage
- [ ] Plan multi-user concurrent testing validation

### Step 2: EXECUTE TEST PLAN - TODO
- [ ] Create failing tests demonstrating the SSOT violation
- [ ] Run validation tests without Docker

### Step 3: PLAN REMEDIATION - TODO
- [ ] Plan migration from singleton to per-request factory pattern
- [ ] Identify all call sites requiring updates

### Step 4: EXECUTE REMEDIATION - TODO
- [ ] Replace singleton usage with SSOT pattern
- [ ] Update all imports and call sites

### Step 5: TEST FIX LOOP - TODO
- [ ] Verify all tests pass after SSOT remediation
- [ ] Run startup tests (non-docker)
- [ ] Fix any import or startup issues

### Step 6: PR AND CLOSURE - TODO
- [ ] Create PR linking to this issue
- [ ] Cross-link issue to close on PR merge

---

## CRITICAL FILES

1. `netra_backend/app/agents/supervisor/agent_instance_factory.py` (Lines 1135-1190)
2. All imports of `get_agent_instance_factory()` - REPLACE with per-request pattern
3. WebSocket agent integration points requiring user context isolation

---

**Created**: 2025-09-14
**Priority**: P0 - Blocks multi-user golden path functionality
**Labels**: ssot, golden-path, security, p0