## 🧪 **TEST PLAN - Systematic Deprecation Cleanup Validation**

### 📋 **TESTING STRATEGY OVERVIEW**

**3-Phase Approach**: Reproduction (failing) → Migration (progressive) → Validation (passing)
- **Phase 1**: Tests FAIL by reproducing deprecation warnings
- **Phase 2**: Tests progressively PASS as migrations complete
- **Phase 3**: All tests PASS with zero deprecation warnings

### 🎯 **PRIORITY-BASED PATTERN COVERAGE**

#### **Priority 1 - Golden Path Critical** (Immediate Focus)

1. **Configuration Import Deprecation Tests**
   - **Target**: User execution context import patterns
   - **Test**: `test_user_execution_context_deprecation_warnings.py`
   - **Expected**: FAIL initially with specific import deprecation warnings

2. **Factory Pattern Migration Tests**
   - **Target**: `SupervisorExecutionEngineFactory` → `UnifiedExecutionEngineFactory`
   - **Test**: `test_execution_factory_migration_validation.py`
   - **Expected**: FAIL initially with factory deprecation warnings

3. **Pydantic Configuration Tests**
   - **Target**: `class Config:` → `model_config = ConfigDict(...)`
   - **Test**: `test_pydantic_config_migration_warnings.py`
   - **Expected**: FAIL initially with Pydantic deprecation warnings

#### **Priority 2 - Infrastructure Stability**

4. **DateTime UTC Deprecation Tests**
   - **Target**: `datetime.utcnow()` → `datetime.now(datetime.UTC)`
   - **Test**: `test_datetime_utc_deprecation_warnings.py`
   - **Expected**: FAIL initially with 308+ files showing warnings

5. **Environment Detector Tests**
   - **Target**: `environment_detector` → `environment_constants`
   - **Test**: `test_environment_detector_migration.py`
   - **Expected**: FAIL initially with environment import warnings

### 🛡️ **GOLDEN PATH PROTECTION STRATEGY**

**Concurrent Validation Approach**:
- **WebSocket Event Validation**: All 5 critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- **Multi-User Isolation**: Factory pattern migrations preserve user context isolation
- **Chat Functionality**: End-to-end business value delivery maintained during cleanup

**Protection Tests**:
```bash
# Run Golden Path protection tests parallel with deprecation tests
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_golden_path_deprecation_protection.py
```

### 🏗️ **TEST INFRASTRUCTURE INTEGRATION**

**SSOT Compliance**:
- **BaseTestCase**: All tests inherit from `SSotBaseTestCase`
- **Mock Factory**: Uses `SSotMockFactory` (no ad-hoc mocks)
- **Test Runner**: Executed through `tests/unified_test_runner.py`
- **Real Services**: Integration tests use real PostgreSQL/Redis (non-docker)

**Test Categories**:
- **Unit Tests**: Isolated deprecation pattern detection
- **Integration Tests**: Real service integration with deprecation validation
- **E2E Staging**: End-to-end validation in GCP staging environment

### ⚡ **EXECUTION COMMANDS**

```bash
# Phase 1 - Reproduce deprecations (should FAIL)
python tests/unified_test_runner.py --category unit --pattern "*deprecation*"

# Phase 2 - Validate migration progress
python tests/unified_test_runner.py --category integration --pattern "*deprecation*" --real-services

# Phase 3 - Golden Path validation (staging)
python tests/unified_test_runner.py --category e2e --pattern "*golden_path*deprecation*" --env staging

# Continuous Golden Path Protection
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### 🔍 **SPECIFIC TEST BEHAVIORS**

1. **Reproduction Phase**: Tests capture specific deprecation warnings using `pytest.warns()`
2. **Migration Phase**: Tests validate both old patterns fail and new patterns work
3. **Validation Phase**: Tests confirm zero deprecation warnings and full functionality

### 📊 **SUCCESS METRICS**

- **Phase 1 Success**: All deprecation tests FAIL with captured warnings
- **Phase 2 Success**: Progressive test passing as patterns migrate
- **Phase 3 Success**: 100% test passing with zero deprecation warnings
- **Golden Path Protection**: $500K+ ARR functionality preserved throughout

### ⚠️ **RISK MITIGATION**

- **Fail-Fast Strategy**: Stop immediately if Golden Path functionality breaks
- **Concurrent Testing**: Run business-critical tests parallel with deprecation cleanup
- **Rollback Ready**: Maintain reproduction tests as regression prevention
- **SSOT Compliance**: Follow established testing patterns to prevent new technical debt

---
**Test Plan by agent-session-20250914-1106 | Following TEST_CREATION_GUIDE.md and CLAUDE.md best practices**