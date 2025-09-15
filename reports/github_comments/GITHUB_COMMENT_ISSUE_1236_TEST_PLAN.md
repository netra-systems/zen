# TEST PLAN: Issue #1236 WebSocket Import Error Fix

**🎯 AGENT SESSION:** agent-session-2025-09-15-0831
**📋 STATUS:** Test Plan Complete - Ready for Implementation
**🔧 RISK LEVEL:** Minimal (Zero customer impact, import path cleanup only)

## 🔍 ROOT CAUSE CONFIRMED

**ISSUE ANALYSIS:**
- **13+ files** importing `UnifiedWebSocketManager` from wrong module: `unified_manager.py`
- **Correct import** should be from: `websocket_manager.py`
- `unified_manager.py` exports `_UnifiedWebSocketManagerImplementation` (private)
- `websocket_manager.py` exports `UnifiedWebSocketManager` (public alias)

**AFFECTED ACTIVE FILES:**
- `./tests/integration/websocket_ssot/test_factory_preservation.py`
- `./tests/unit/websocket_ssot/test_issue_1047_phase1_foundation_validation.py`
- `./tests/unit/websocket_ssot/test_issue_1100_ssot_compliance_validation.py`
- `./tests/unit/websocket_ssot_issue960/test_websocket_manager_singleton_enforcement.py`

## 📋 TEST STRATEGY OVERVIEW

### ✅ CONSTRAINT COMPLIANCE
- **NO DOCKER**: Unit, integration (non-docker), e2e GCP staging only
- **SSOT PATTERNS**: Uses SSotBaseTestCase, SSotMockFactory
- **REAL SERVICES**: Integration tests use real WebSocket services where appropriate
- **FAIL-FIRST**: Tests designed to fail initially, proving import issues exist

### 🎯 TEST CATEGORIES

#### 1. **IMPORT RESOLUTION TESTS** (Unit - Non-Docker)
**Purpose**: Validate import corrections work
- **Direct Import Validation**: Test correct vs incorrect import patterns
- **Import Path Consistency**: Verify module exports and aliases
- **Canonical Pattern Validation**: Test Issue #1047 canonical imports

#### 2. **WEBSOCKET MANAGER FUNCTIONALITY** (Integration - Non-Docker)
**Purpose**: Confirm manager works after import corrections
- **Manager Instantiation**: Test factory functions and direct imports
- **Cross-Service Integration**: Agent registry and bridge factory compatibility
- **Basic Operations**: Validate core WebSocket manager methods

#### 3. **MISSION CRITICAL TESTS** (E2E GCP Staging)
**Purpose**: Ensure no Golden Path regression
- **Golden Path Validation**: WebSocket events still work
- **Agent Execution Integration**: Execution engine WebSocket integration preserved
- **Business Value Protection**: $500K+ ARR chat functionality maintained

#### 4. **REGRESSION PREVENTION** (Unit - Non-Docker)
**Purpose**: Prevent future import path issues
- **Import Path Linting**: Scan for problematic import patterns
- **Export Consistency**: Validate websocket_manager.py exports

## 🚀 EXECUTION STRATEGY

### **PHASE 1: PROVING ISSUES EXIST** (Pre-Fix)
```bash
# Should FAIL - proving import issues exist
python tests/unified_test_runner.py --test-file tests/unit/websocket_ssot_issue960/test_websocket_manager_singleton_enforcement.py

python tests/unified_test_runner.py --test-file tests/integration/websocket_ssot/test_factory_preservation.py
```

### **PHASE 2: VALIDATION** (Post-Fix)
```bash
# Should PASS - confirming fixes work
python tests/unified_test_runner.py --category unit --test-pattern "*issue_1236*"

python tests/unified_test_runner.py --category integration --test-pattern "*issue_1236*" --real-services

python tests/unified_test_runner.py --category mission_critical --test-pattern "*issue_1236*" --env staging
```

## 🎯 SUCCESS CRITERIA

### **PRIMARY (Must Have)**
- [ ] **Import Resolution**: All `UnifiedWebSocketManager` imports work from correct path
- [ ] **No Import Errors**: Zero ImportError exceptions for WebSocket manager imports
- [ ] **Existing Tests Pass**: Previously failing tests now pass
- [ ] **Golden Path Preserved**: No regression in critical WebSocket functionality

### **SECONDARY (Should Have)**
- [ ] **Factory Function Works**: `get_websocket_manager()` operational
- [ ] **Cross-Service Integration**: Agent registry/bridge factory compatibility maintained
- [ ] **Alias Consistency**: `UnifiedWebSocketManager` correctly points to implementation
- [ ] **Regression Prevention**: Linting tests prevent future issues

## 💼 BUSINESS VALUE PROTECTION

**✅ ZERO CUSTOMER IMPACT**: No disruption to chat functionality
**✅ $500K+ ARR PROTECTED**: WebSocket infrastructure supporting revenue preserved
**✅ DEVELOPMENT VELOCITY**: Import issues don't block developer productivity
**✅ GOLDEN PATH OPERATIONAL**: End-to-end user flow remains functional

## 📁 DELIVERABLES

**📋 COMPLETE TEST PLAN**: `TEST_PLAN_ISSUE_1236_WEBSOCKET_IMPORT_FIX.md`
- 4 test categories with specific test files
- Detailed test execution methodology
- Success criteria and business value validation
- Risk mitigation and rollback strategy

**🔄 NEXT STEPS:**
1. **Create failing tests** proving import issues exist
2. **Implement import path corrections** for affected files
3. **Run validation tests** confirming fixes work
4. **Update GitHub issue** with test results

---

**GENERATED**: 2025-09-15 08:31 UTC
**METHODOLOGY**: Following reports/testing/TEST_CREATION_GUIDE.md and CLAUDE.md testing best practices
**GOLDEN PATH PRIORITY**: WebSocket infrastructure critical for AI chat interactions