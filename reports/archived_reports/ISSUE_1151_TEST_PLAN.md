# Issue #1151 Comprehensive Test Plan

## 🎯 Test Plan Overview

**Objective**: Validate the fix for Issue #1151 - missing `is_docker_available` function in `tests.mission_critical.websocket_real_test_base`

**Business Impact**: Ensure $500K+ ARR Golden Path first message experience tests are functional

**Fix Validation**: Confirm the newly added `is_docker_available()` function resolves test collection failures

## 📋 Test Categories & Scope

### 1. Unit Tests - Function Behavior Validation
**Purpose**: Test the newly added `is_docker_available()` function works correctly in isolation
**Infrastructure**: None required
**Execution Mode**: Local testing without Docker

#### Test 1.1: Function Exists and Is Importable
```python
def test_is_docker_available_function_exists():
    """Verify is_docker_available function can be imported successfully."""
    from tests.mission_critical.websocket_real_test_base import is_docker_available
    assert callable(is_docker_available)
    assert is_docker_available.__doc__ is not None
```

#### Test 1.2: Function Returns Boolean
```python
def test_is_docker_available_returns_boolean():
    """Verify function returns boolean value."""
    from tests.mission_critical.websocket_real_test_base import is_docker_available
    result = is_docker_available()
    assert isinstance(result, bool)
```

#### Test 1.3: Function Handles Docker Unavailable Gracefully
```python
def test_is_docker_available_handles_docker_unavailable():
    """Test function behavior when Docker is not available."""
    # This will naturally test the case if Docker is not running
    from tests.mission_critical.websocket_real_test_base import is_docker_available
    result = is_docker_available()
    # Should not raise exception regardless of Docker state
    assert result in [True, False]
```

#### Test 1.4: Function Uses SSOT UnifiedDockerManager
```python
def test_is_docker_available_uses_ssot_manager():
    """Verify function delegates to UnifiedDockerManager (SSOT pattern)."""
    from tests.mission_critical.websocket_real_test_base import is_docker_available
    from test_framework.unified_docker_manager import UnifiedDockerManager

    # Function should use the same logic as UnifiedDockerManager
    manager = UnifiedDockerManager()
    manager_result = manager.is_docker_available()
    function_result = is_docker_available()

    # Results should be consistent
    assert manager_result == function_result
```

### 2. Integration Tests - Import Resolution Validation
**Purpose**: Verify previously failing imports now succeed
**Infrastructure**: None required
**Execution Mode**: Test collection and import validation

#### Test 2.1: Mission Critical Test File Imports Successfully
```python
def test_first_message_experience_imports_resolve():
    """Test that test_first_message_experience.py imports resolve without errors."""
    import importlib.util
    import sys
    from pathlib import Path

    # Import the previously failing test file
    test_file = Path(__file__).parent.parent / "tests" / "mission_critical" / "test_first_message_experience.py"

    spec = importlib.util.spec_from_file_location("test_first_message_experience", test_file)
    module = importlib.util.module_from_spec(spec)

    # This should not raise ImportError
    spec.loader.exec_module(module)

    # Verify the specific import that was failing
    assert hasattr(module, 'is_docker_available')
```

#### Test 2.2: All Required Functions Available in websocket_real_test_base
```python
def test_websocket_real_test_base_complete_interface():
    """Verify all expected functions are available in websocket_real_test_base."""
    from tests.mission_critical import websocket_real_test_base

    # Functions that should be available for mission-critical tests
    required_functions = [
        'is_docker_available',           # NEW - Issue #1151 fix
        'require_docker_services',       # Existing
        'require_docker_services_smart', # Existing
        'RealWebSocketTestConfig',       # Existing class
        'send_test_agent_request'        # Existing function
    ]

    for func_name in required_functions:
        assert hasattr(websocket_real_test_base, func_name), f"Missing {func_name}"
        attr = getattr(websocket_real_test_base, func_name)
        assert callable(attr) or isinstance(attr, type), f"{func_name} is not callable or class"
```

#### Test 2.3: Import Pattern Consistency
```python
def test_import_pattern_consistency():
    """Verify import patterns are consistent across mission-critical tests."""
    from tests.mission_critical.websocket_real_test_base import (
        is_docker_available,
        RealWebSocketTestConfig,
        send_test_agent_request
    )

    # All imports should resolve without error
    assert callable(is_docker_available)
    assert isinstance(RealWebSocketTestConfig, type)
    assert callable(send_test_agent_request)
```

### 3. End-to-End Tests - Mission Critical Test Collection
**Purpose**: Confirm mission-critical WebSocket tests can be collected and executed
**Infrastructure**: None required for collection, optional Docker for execution
**Execution Mode**: Test discovery and collection validation

#### Test 3.1: Mission Critical Tests Are Discoverable
```bash
# Test collection of mission-critical tests
python -m pytest tests/mission_critical/ --collect-only -q
```

#### Test 3.2: First Message Experience Test Collection
```bash
# Specifically test the previously failing file
python -m pytest tests/mission_critical/test_first_message_experience.py --collect-only -v
```

#### Test 3.3: WebSocket Test Suite Collection
```bash
# Test collection of all WebSocket-related mission-critical tests
python -m pytest tests/mission_critical/ -k "websocket" --collect-only -v
```

### 4. Regression Tests - Existing Functionality
**Purpose**: Ensure no regressions in existing WebSocket test infrastructure
**Infrastructure**: Docker available (if testing actual functionality)
**Execution Mode**: Staging/non-Docker testing

#### Test 4.1: Existing Docker Detection Functions Still Work
```python
def test_existing_docker_functions_unaffected():
    """Verify existing Docker detection functions are not broken."""
    from tests.mission_critical.websocket_real_test_base import (
        require_docker_services,
        require_docker_services_smart
    )

    # Functions should be callable (though may skip if Docker unavailable)
    assert callable(require_docker_services)
    assert callable(require_docker_services_smart)
```

#### Test 4.2: UnifiedDockerManager Integration
```python
def test_unified_docker_manager_integration():
    """Test integration between new function and existing UnifiedDockerManager."""
    from test_framework.unified_docker_manager import UnifiedDockerManager
    from tests.mission_critical.websocket_real_test_base import is_docker_available

    # Create manager instance
    manager = UnifiedDockerManager()

    # Both should provide consistent results
    manager_available = manager.is_docker_available()
    function_available = is_docker_available()

    # Results should match (both use same underlying Docker detection)
    assert manager_available == function_available
```

#### Test 4.3: WebSocket Test Base Functionality
```python
def test_websocket_test_base_core_functionality():
    """Verify core WebSocket test base functionality remains intact."""
    from tests.mission_critical.websocket_real_test_base import RealWebSocketTestConfig

    # Should be able to create config instances
    config = RealWebSocketTestConfig()
    assert hasattr(config, 'backend_url')
    assert hasattr(config, 'websocket_url')
    assert hasattr(config, 'connection_timeout')
```

## 🚀 Execution Strategy

### Phase 1: Local Validation (No Docker Required)
1. **Function Interface Testing**: Validate new function exists and behaves correctly
2. **Import Resolution**: Confirm all imports resolve successfully
3. **SSOT Compliance**: Verify integration with UnifiedDockerManager

### Phase 2: Collection Testing (No Docker Required)
1. **Test Discovery**: Confirm pytest can discover mission-critical tests
2. **Import Validation**: Verify no ImportError during collection
3. **Interface Completeness**: Validate all expected functions available

### Phase 3: Integration Validation (Staging/Mock)
1. **End-to-End Flow**: Test complete first message experience flow on staging
2. **WebSocket Events**: Validate all 5 critical agent events on staging
3. **Performance Validation**: Confirm 45s SLA compliance on staging

### Phase 4: Regression Prevention (No Docker Required)
1. **Backwards Compatibility**: Ensure existing functionality unchanged
2. **SSOT Patterns**: Verify no violations introduced
3. **Business Value Protection**: Confirm $500K+ ARR features intact

## 📝 Test Execution Commands

### Unit Tests
```bash
# Test the new function behavior
python -m pytest tests/unit/test_issue_1151_function_validation.py -v

# Test import resolution
python -m pytest tests/integration/test_issue_1151_import_validation.py -v
```

### Collection Tests
```bash
# Mission-critical test collection
python -m pytest tests/mission_critical/ --collect-only --tb=short

# Specific previously failing test
python -m pytest tests/mission_critical/test_first_message_experience.py --collect-only -v
```

### Staging E2E Tests (if Docker unavailable)
```bash
# First message experience on staging
USE_STAGING_FALLBACK=true python -m pytest tests/mission_critical/test_first_message_experience.py -v

# WebSocket events validation on staging
USE_STAGING_FALLBACK=true python -m pytest tests/mission_critical/ -k "websocket" -v
```

## ✅ Success Criteria

### Primary Success Criteria (Must Pass)
- [ ] `is_docker_available` function is importable from `tests.mission_critical.websocket_real_test_base`
- [ ] `test_first_message_experience.py` imports resolve without ImportError
- [ ] Mission-critical WebSocket tests can be collected successfully
- [ ] Function returns consistent boolean values
- [ ] SSOT pattern compliance (delegates to UnifiedDockerManager)

### Secondary Success Criteria (Should Pass)
- [ ] All existing WebSocket test functionality remains intact
- [ ] No regression in other mission-critical test imports
- [ ] First message experience tests can execute on staging environment
- [ ] WebSocket event validation works correctly
- [ ] Performance SLA validation functions properly

### Business Value Validation
- [ ] Golden Path first message experience testing is functional
- [ ] $500K+ ARR user onboarding flow can be validated
- [ ] Real-time WebSocket event delivery can be tested
- [ ] Multi-user concurrent testing infrastructure works
- [ ] SSOT compliance maintained across test infrastructure

## 🎯 Expected Outcomes

1. **Immediate**: Test collection errors resolved, imports work correctly
2. **Short-term**: Mission-critical tests executable, business value protected
3. **Long-term**: Robust WebSocket testing infrastructure supporting production quality validation

## 📚 Documentation References

- **CLAUDE.md**: Real services mandate and testing philosophy
- **TEST_CREATION_GUIDE.md**: Test creation patterns and SSOT requirements
- **DEFINITION_OF_DONE_CHECKLIST.md**: WebSocket module validation requirements
- **USER_CONTEXT_ARCHITECTURE.md**: Factory patterns and user isolation requirements

---

**Test Plan Created**: 2025-09-14
**Issue Reference**: #1151
**Business Priority**: P1 - Critical Golden Path functionality
**Estimated Execution Time**: 30 minutes full validation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>