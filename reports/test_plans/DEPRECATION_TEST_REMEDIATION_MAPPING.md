# Deprecation Test-to-Remediation Mapping - Step 5

**Created:** 2025-01-14
**Purpose:** Maps failing deprecation tests to specific remediation actions
**Status:** Ready for Implementation

## Test Results Summary

**From Step 4 Test Execution:**
- **Total Tests**: 20 tests created
- **Currently FAILING**: 6 tests (designed to fail, reproducing deprecation patterns)
- **Currently PASSING**: 14 tests (showing correct migration patterns)

## Failing Test Mapping to Remediation Actions

### 1. Configuration Import Deprecation Tests

#### Test: `test_deprecated_logging_import_detection`
**Status**: FAILING (by design - reproduces deprecation)
**Location**: `tests/unit/deprecation_cleanup/test_configuration_import_deprecation.py`

**Deprecation Reproduced**:
```
shared.logging.unified_logger_factory is deprecated.
Use 'from shared.logging.unified_logging_ssot import get_logger' instead.
```

**Remediation Action**: Phase 1.1 - Configuration Import Migration
- **File**: `shared/logging/__init__.py`
- **Change**: Remove deprecated import from `unified_logger_factory`
- **Expected Result**: Test should PASS after remediation

#### Test: `test_websocket_logging_deprecation`
**Status**: FAILING (by design - reproduces deprecation)
**Location**: `tests/unit/deprecation_cleanup/test_configuration_import_deprecation.py`

**Deprecation Reproduced**:
```
netra_backend.app.logging_config is deprecated.
Use 'from shared.logging.unified_logging_ssot import get_logger' instead.
```

**Remediation Action**: Phase 1.1 - WebSocket Emitter Logging Migration
- **File**: `netra_backend/app/websocket_core/unified_emitter.py`
- **Line**: 33
- **Change**: Replace `from netra_backend.app.logging_config import central_logger`
- **Expected Result**: Test should PASS after remediation

### 2. Factory Pattern Migration Tests

#### Test: `test_deprecated_supervisor_factory_import`
**Status**: FAILING (by design - reproduces deprecation)
**Location**: `tests/unit/deprecation_cleanup/test_factory_pattern_migration_deprecation.py`

**Deprecation Reproduced**:
```
SupervisorExecutionEngineFactory is deprecated.
Use UnifiedExecutionEngineFactory instead.
```

**Remediation Action**: Phase 2.1 - Factory Pattern Migration
- **Scope**: Multiple files using SupervisorExecutionEngineFactory
- **Change**: Systematic replacement with UnifiedExecutionEngineFactory
- **Expected Result**: Test should PASS after all factory migrations complete

#### Test: `test_deprecated_user_context_factory_pattern`
**Status**: FAILING (by design - reproduces deprecation)
**Location**: `tests/unit/deprecation_cleanup/test_factory_pattern_migration_deprecation.py`

**Deprecation Reproduced**:
User context factory isolation deprecation warnings

**Remediation Action**: Phase 2.1 - User Context Factory Migration
- **Focus**: Multi-user isolation preservation during factory migration
- **Validation**: User context isolation tests must continue passing
- **Expected Result**: Test should PASS with proper isolation maintained

### 3. Pydantic Configuration Tests

#### Test: `test_deprecated_pydantic_class_config`
**Status**: FAILING (by design - reproduces deprecation)
**Location**: `tests/unit/deprecation_cleanup/test_pydantic_configuration_deprecation.py`

**Deprecation Reproduced**:
```
Support for class-based `config` is deprecated, use ConfigDict instead.
Deprecated in Pydantic V2.0 to be removed in V3.0.
```

**Remediation Action**: Phase 3.1 - Pydantic ConfigDict Migration
- **Files**: 11 files with `class Config:` patterns
- **Priority File**: `netra_backend/app/mcp_client/models.py` (6 models)
- **Change**: Convert all `class Config:` to `model_config = ConfigDict(...)`
- **Expected Result**: Test should PASS after all models migrated

#### Test: `test_deprecated_json_encoders_pattern`
**Status**: FAILING (by design - reproduces deprecation)
**Location**: `tests/unit/deprecation_cleanup/test_pydantic_configuration_deprecation.py`

**Deprecation Reproduced**:
```
`json_encoders` is deprecated. See https://docs.pydantic.dev/2.11/concepts/serialization/#custom-serializers for alternatives.
```

**Remediation Action**: Phase 3.1 - JSON Encoder Migration
- **Scope**: Part of Pydantic ConfigDict migration
- **Change**: Update JSON encoder patterns to Pydantic v2 approach
- **Expected Result**: Test should PASS after encoder pattern updates

## Passing Test Validation

### Tests Already Passing (Showing Correct Patterns)

These tests validate that our target patterns work correctly:

1. **`test_correct_ssot_logging_import`** ✅ PASSING
   - Validates: `from shared.logging.unified_logging_ssot import get_logger`
   - Confirms: Target pattern works correctly

2. **`test_correct_unified_factory_usage`** ✅ PASSING
   - Validates: UnifiedExecutionEngineFactory usage
   - Confirms: Target factory pattern is functional

3. **`test_correct_pydantic_configdict_usage`** ✅ PASSING
   - Validates: `model_config = ConfigDict(...)` pattern
   - Confirms: Target Pydantic pattern works

4. **`test_websocket_manager_canonical_import`** ✅ PASSING
   - Validates: Canonical WebSocketManager import path
   - Confirms: Target import pattern is correct

5. **`test_user_context_isolation_maintained`** ✅ PASSING
   - Validates: Multi-user context isolation
   - Confirms: Business-critical isolation preserved

## Remediation Validation Strategy

### Phase 1 Validation (Golden Path Critical)
After implementing Phase 1 remediations:

```bash
# Run the specific failing tests that should now pass
python -m pytest tests/unit/deprecation_cleanup/test_configuration_import_deprecation.py::test_deprecated_logging_import_detection -v
python -m pytest tests/unit/deprecation_cleanup/test_configuration_import_deprecation.py::test_websocket_logging_deprecation -v

# Validate Golden Path functionality maintained
python tests/mission_critical/test_websocket_agent_events_suite.py

# Check for remaining configuration deprecations
python -m pytest tests/unit/test_pytest_collection_warnings_issue_999.py -v --tb=short | grep -i deprecation
```

**Success Criteria**:
- Both configuration deprecation tests now PASS
- Zero deprecation warnings from shared.logging imports
- Zero deprecation warnings from WebSocket emitter
- All WebSocket events still delivered

### Phase 2 Validation (Factory Pattern)
After implementing Phase 2 remediations:

```bash
# Run the factory migration tests that should now pass
python -m pytest tests/unit/deprecation_cleanup/test_factory_pattern_migration_deprecation.py::test_deprecated_supervisor_factory_import -v
python -m pytest tests/unit/deprecation_cleanup/test_factory_pattern_migration_deprecation.py::test_deprecated_user_context_factory_pattern -v

# Validate multi-user isolation still works
python -m pytest tests/unit/deprecation_cleanup/test_factory_pattern_migration_deprecation.py::test_user_context_isolation_maintained -v
```

**Success Criteria**:
- Both factory deprecation tests now PASS
- User isolation test continues to PASS
- No SupervisorExecutionEngineFactory references in production code

### Phase 3 Validation (Pydantic Configuration)
After implementing Phase 3 remediations:

```bash
# Run the Pydantic deprecation tests that should now pass
python -m pytest tests/unit/deprecation_cleanup/test_pydantic_configuration_deprecation.py::test_deprecated_pydantic_class_config -v
python -m pytest tests/unit/deprecation_cleanup/test_pydantic_configuration_deprecation.py::test_deprecated_json_encoders_pattern -v

# Validate model functionality preserved
python -c "
from netra_backend.app.mcp_client.models import MCPConnection
import json
conn = MCPConnection(server_name='test', transport='http')
print('Model creation and serialization successful')
print(conn.model_dump_json()[:100] + '...')
"
```

**Success Criteria**:
- Both Pydantic deprecation tests now PASS
- All model creation and serialization works
- Zero PydanticDeprecatedSince20 warnings

## Complete System Validation

After all phases complete, run comprehensive validation:

```bash
# All deprecation tests should now pass
python -m pytest tests/unit/deprecation_cleanup/ -v

# Original pytest collection warnings test
python -m pytest tests/unit/test_pytest_collection_warnings_issue_999.py -v --tb=short

# Mission critical functionality validation
python tests/mission_critical/test_websocket_agent_events_suite.py

# Broader system health check
python tests/unified_test_runner.py --categories smoke integration --fast-fail
```

**Final Success Criteria**:
- **All 20 deprecation tests PASS** (6 remediated + 14 already passing)
- **Zero deprecation warnings** in pytest collection output
- **Golden Path functionality 100% preserved**
- **Business-critical features maintained**

## Progress Tracking

### Phase 1 Progress (Week 1)
- [ ] `test_deprecated_logging_import_detection` - FAILING → PASSING
- [ ] `test_websocket_logging_deprecation` - FAILING → PASSING
- [ ] Validate: Golden Path WebSocket events still work
- [ ] Validate: Chat functionality maintains business value

### Phase 2 Progress (Week 2)
- [ ] `test_deprecated_supervisor_factory_import` - FAILING → PASSING
- [ ] `test_deprecated_user_context_factory_pattern` - FAILING → PASSING
- [ ] Validate: `test_user_context_isolation_maintained` - continues PASSING
- [ ] Validate: Multi-user scenarios work correctly

### Phase 3 Progress (Week 3)
- [ ] `test_deprecated_pydantic_class_config` - FAILING → PASSING
- [ ] `test_deprecated_json_encoders_pattern` - FAILING → PASSING
- [ ] Validate: All Pydantic models serialize correctly
- [ ] Validate: Data validation functionality preserved

### Phase 4 Progress (Week 4)
- [ ] Address pytest collection constructor warnings
- [ ] Improve test discovery reliability
- [ ] Final system-wide deprecation audit

## Risk Assessment by Test

| Test | Risk Level | Golden Path Impact | Mitigation |
|------|------------|-------------------|------------|
| `test_websocket_logging_deprecation` | HIGH | Direct impact on WebSocket events | Test all 5 critical events before/after |
| `test_deprecated_supervisor_factory_import` | MEDIUM | Affects user isolation | Comprehensive multi-user testing |
| `test_deprecated_logging_import_detection` | LOW | Shared utility function | Standard import testing |
| `test_deprecated_user_context_factory_pattern` | MEDIUM | User context isolation | User isolation validation suite |
| `test_deprecated_pydantic_class_config` | LOW | Data model validation | Model creation/serialization testing |
| `test_deprecated_json_encoders_pattern` | LOW | JSON serialization | Serialization testing |

---

*This mapping provides direct traceability from failing tests to specific remediation actions, ensuring systematic and complete deprecation cleanup.*