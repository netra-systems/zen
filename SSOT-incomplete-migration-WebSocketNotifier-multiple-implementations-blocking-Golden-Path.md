# SSOT-incomplete-migration-WebSocketNotifier Multiple Implementations Blocking Golden Path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/216  
**Status:** In Progress - Step 0 Complete  
**Priority:** CRITICAL  
**Business Impact:** $500K+ ARR chat functionality at risk  

## Progress Tracking

### ✅ Step 0: SSOT AUDIT COMPLETE
- **DISCOVERED**: Multiple WebSocketNotifier implementations
- **IMPACT**: 214 files with inconsistent patterns
- **PRIMARY SSOT**: `/netra_backend/app/services/agent_websocket_bridge.py:2748`
- **DEPRECATED**: `/netra_backend/app/agents/supervisor/websocket_notifier.py` (REMOVE)

### ✅ Step 1: DISCOVER AND PLAN TEST COMPLETE
- **DISCOVERED**: 110 WebSocketNotifier test files across all categories
- **MISSION CRITICAL**: 24 tests protecting $500K+ ARR business value
- **TEST DISTRIBUTION**: 60% updates (66 files), 20% new SSOT tests (22 files), 20% failing tests (22 files)
- **STRATEGY**: Phased execution using staging GCP and unit tests (no Docker dependency)
- **VIOLATIONS**: 3 different import paths across 110 test files requiring standardization

### 📋 Step 2: EXECUTE TEST PLAN (Next)
- **TODO**: Create 22 new SSOT validation tests (20% of strategy)
- **TODO**: Create 22 failing tests reproducing SSOT violations
- **TODO**: Run test validation without Docker (staging GCP + unit tests)
- **TODO**: Validate test strategy before proceeding to remediation

### 📋 Step 3: PLAN REMEDIATION (Pending)

### 📋 Step 4: EXECUTE REMEDIATION (Pending)

### 📋 Step 5: TEST FIX LOOP (Pending)

### 📋 Step 6: PR AND CLOSURE (Pending)

---

## Critical SSOT Violations Identified

### 1. Multiple Implementations (CRITICAL)
- **Primary**: `/netra_backend/app/services/agent_websocket_bridge.py:2748` (KEEP)
- **Secondary**: `/netra_backend/app/agents/supervisor/websocket_notifier.py` (REMOVE)
- **Risk**: Runtime conflicts, user isolation failures

### 2. Import Path Violations (HIGH)
- **214 files** using 3+ different import paths
- **Inconsistent**: Legacy vs modern factory patterns
- **Risk**: Developer confusion, maintenance overhead

### 3. Factory Pattern Violations (HIGH)
- **Legacy**: Direct `WebSocketNotifier(websocket_manager)` instantiation
- **Modern**: Factory-created via `UserWebSocketEmitter`
- **Risk**: User isolation breakdown, race conditions

### 4. Deprecated Code Active (MEDIUM)
- **Status**: Marked deprecated but still used
- **Files**: 214 active references to deprecated implementation
- **Risk**: Technical debt, confusion

---

## Remediation Strategy

### Phase 1: SSOT Consolidation
1. Keep `AgentWebSocketBridge.WebSocketNotifier` as SSOT
2. Remove `/netra_backend/app/agents/supervisor/websocket_notifier.py`
3. Update all 214 import references

### Phase 2: Import Standardization
1. Single import path standardization
2. Test infrastructure SSOT
3. Remove duplicate mock implementations

### Phase 3: User Isolation Enforcement
1. Factory-only creation enforcement
2. Legacy code removal
3. Runtime validation for user isolation

---

## Files Requiring Immediate Attention

### Critical Priority (P0)
- `/netra_backend/app/agents/supervisor/websocket_notifier.py` - **REMOVE**
- `/netra_backend/app/services/agent_websocket_bridge.py` - **ENHANCE as SSOT**
- `/netra_backend/app/agents/supervisor/execution_engine.py` - **Update imports**

### High Priority (P1)
- `/netra_backend/app/agents/supervisor/agent_instance_factory.py` - **Factory enforcement**
- All test files with `WebSocketNotifier` imports - **Standardize mocks**

---

## Success Metrics
- **Import Consolidation**: 214 files → 1 canonical import path
- **Implementation Count**: 2 implementations → 1 SSOT implementation
- **Factory Usage**: 100% factory-created instances
- **User Isolation**: 100% user-bound WebSocket emitters
- **WebSocket Event Delivery**: >99.9% success rate

---

*Last Updated: 2025-09-10 - SSOT Gardener Process*