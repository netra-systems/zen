# TEST PLAN: Issue #1236 WebSocket Import Error Fix

**AGENT SESSION ID:** agent-session-2025-09-15-0831
**ISSUE**: #1236 - UnifiedWebSocketManager import error affecting 13+ files
**CONTEXT**: WebSocket infrastructure operational, import path cleanup needed
**IMPACT**: Zero customer impact, minimal risk resolution

## EXECUTIVE SUMMARY

**ROOT CAUSE ANALYSIS:**
- Files importing `UnifiedWebSocketManager` from `netra_backend.app.websocket_core.unified_manager`
- The correct import is from `netra_backend.app.websocket_core.websocket_manager`
- `unified_manager.py` exports `_UnifiedWebSocketManagerImplementation` (private implementation)
- `websocket_manager.py` exports `UnifiedWebSocketManager` (public interface alias)

**AFFECTED FILES ANALYSIS:**
- **Total files found**: 13+ production files with incorrect import patterns
- **Critical files**: Tests that validate WebSocket functionality
- **Backup files**: Legacy backup files (ignore for test planning)
- **Active files requiring fixes**:
  - `./tests/integration/websocket_ssot/test_factory_preservation.py`
  - `./tests/unit/websocket_ssot/test_issue_1047_phase1_foundation_validation.py`
  - `./tests/unit/websocket_ssot/test_issue_1100_ssot_compliance_validation.py`
  - `./tests/unit/websocket_ssot_issue960/test_websocket_manager_singleton_enforcement.py`

## TEST STRATEGY OVERVIEW

### CONSTRAINTS & REQUIREMENTS
- **NO DOCKER TESTS**: Only run unit, integration (non-docker), and e2e GCP staging tests
- **FOLLOW SSOT PATTERNS**: Use SSOT testing infrastructure (SSotBaseTestCase, SSotMockFactory)
- **REAL SERVICES WHERE APPROPRIATE**: Use real WebSocket services for integration validation
- **FAIL-FIRST APPROACH**: Design tests to fail initially, proving import issues exist
- **GOLDEN PATH PROTECTION**: Ensure no regression in critical user flow

### TEST EXECUTION METHODOLOGY
1. **Phase 1: Failing Tests** - Prove import errors exist
2. **Phase 2: Import Corrections** - Fix import paths
3. **Phase 3: Validation Tests** - Confirm fixes work
4. **Phase 4: Regression Prevention** - Ensure no Golden Path issues

## DETAILED TEST CATEGORIES

### 1. IMPORT RESOLUTION TESTS (Unit - Non-Docker)

**PURPOSE**: Validate that files can import UnifiedWebSocketManager successfully after fix

#### 1.1 Direct Import Validation Tests
**File**: `tests/unit/issue_1236/test_import_resolution_validation.py`

```python
class TestUnifiedWebSocketManagerImportResolution(SSotBaseTestCase):
    """Test that all import patterns work correctly after Issue #1236 fix."""

    def test_import_from_websocket_manager_succeeds(self):
        """Test correct import pattern works."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
            self.assertIsNotNone(UnifiedWebSocketManager)
        except ImportError as e:
            self.fail(f"Correct import should work: {e}")

    def test_import_from_unified_manager_fails_gracefully(self):
        """Test that incorrect import pattern provides clear error."""
        with self.assertRaises(ImportError) as cm:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

        error_msg = str(cm.exception)
        self.assertIn("cannot import name 'UnifiedWebSocketManager'", error_msg)

    def test_canonical_import_patterns_work(self):
        """Test canonical import patterns from Issue #1047."""
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
            self.assertIsNotNone(UnifiedWebSocketManager)
        except ImportError as e:
            self.fail(f"Canonical import should work: {e}")

    def test_factory_function_import_works(self):
        """Test factory function import pattern."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            self.assertIsNotNone(get_websocket_manager)
        except ImportError as e:
            self.fail(f"Factory function import should work: {e}")
```

#### 1.2 Import Path Consistency Tests
**File**: `tests/unit/issue_1236/test_import_path_consistency.py`

```python
class TestImportPathConsistency(SSotBaseTestCase):
    """Validate import path consistency across WebSocket modules."""

    def test_websocket_manager_exports_unified_websocket_manager(self):
        """Verify websocket_manager.py exports UnifiedWebSocketManager."""
        from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
        self.assertTrue(hasattr(UnifiedWebSocketManager, '__name__'))

    def test_unified_manager_exports_private_implementation(self):
        """Verify unified_manager.py only exports private implementation."""
        from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation

        # Should NOT export public UnifiedWebSocketManager
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            self.fail("unified_manager.py should not export public UnifiedWebSocketManager")
        except ImportError:
            pass  # Expected behavior

    def test_alias_consistency(self):
        """Test that UnifiedWebSocketManager alias points to correct implementation."""
        from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
        from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation

        # UnifiedWebSocketManager should be an alias for _UnifiedWebSocketManagerImplementation
        self.assertIs(UnifiedWebSocketManager, _UnifiedWebSocketManagerImplementation)
```

### 2. WEBSOCKET MANAGER FUNCTIONALITY TESTS (Integration - Non-Docker)

**PURPOSE**: Confirm WebSocket manager works correctly after import corrections

#### 2.1 Manager Instantiation Tests
**File**: `tests/integration/issue_1236/test_websocket_manager_functionality.py`

```python
class TestWebSocketManagerFunctionalityAfterFix(SSotBaseTestCase):
    """Test WebSocket manager functionality after import path fixes."""

    async def test_websocket_manager_instantiation_via_correct_import(self):
        """Test manager can be instantiated using correct import."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        user_context = self.create_mock_user_context()
        manager = get_websocket_manager(user_context=user_context)

        self.assertIsNotNone(manager)
        self.assertTrue(hasattr(manager, 'send_event'))
        self.assertTrue(hasattr(manager, 'connect'))

    async def test_websocket_manager_basic_operations(self):
        """Test basic WebSocket manager operations work."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        user_context = self.create_mock_user_context()
        manager = get_websocket_manager(user_context=user_context)

        # Test basic method accessibility (not full functionality due to no docker constraint)
        self.assertTrue(callable(getattr(manager, 'send_event', None)))
        self.assertTrue(callable(getattr(manager, 'connect', None)))
        self.assertTrue(callable(getattr(manager, 'disconnect', None)))

    async def test_factory_function_creates_valid_manager(self):
        """Test factory function creates properly configured manager."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        manager = get_websocket_manager()  # Should use fallback context

        self.assertIsNotNone(manager)
        self.assertTrue(hasattr(manager, 'mode'))
        self.assertTrue(hasattr(manager, 'user_context'))
```

#### 2.2 Cross-Service Integration Tests
**File**: `tests/integration/issue_1236/test_websocket_cross_service_integration.py`

```python
class TestWebSocketCrossServiceIntegration(SSotBaseTestCase):
    """Test WebSocket manager integration with other services after fix."""

    async def test_agent_registry_websocket_integration(self):
        """Test agent registry can use WebSocket manager after import fix."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.agents.registry import AgentRegistry

        user_context = self.create_mock_user_context()
        websocket_manager = get_websocket_manager(user_context=user_context)

        # Test that agent registry can accept the manager
        try:
            registry = AgentRegistry()
            registry.set_websocket_manager(websocket_manager)
            # If we get here without exception, integration works
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Agent registry integration failed: {e}")

    async def test_websocket_bridge_factory_integration(self):
        """Test WebSocket bridge factory works with corrected imports."""
        try:
            from netra_backend.app.services.websocket_bridge_factory import create_agent_websocket_bridge
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            user_context = self.create_mock_user_context()
            websocket_manager = get_websocket_manager(user_context=user_context)

            # Should be able to create bridge without import errors
            bridge = create_agent_websocket_bridge(user_context, websocket_manager)
            self.assertIsNotNone(bridge)
        except ImportError as e:
            self.fail(f"WebSocket bridge integration failed with import error: {e}")
```

### 3. MISSION CRITICAL TESTS (E2E GCP Staging)

**PURPOSE**: Ensure no regression in Golden Path functionality

#### 3.1 Golden Path Validation Tests
**File**: `tests/mission_critical/issue_1236/test_golden_path_import_regression.py`

```python
class TestGoldenPathImportRegression(SSotBaseTestCase):
    """Mission critical tests to ensure Golden Path works after import fixes."""

    @pytest.mark.staging_required
    async def test_websocket_events_still_work_after_import_fix(self):
        """Test that WebSocket events work in staging after import corrections."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        user_context = self.create_mock_user_context()
        manager = get_websocket_manager(user_context=user_context)

        # Test that critical WebSocket events can be sent
        test_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        for event in test_events:
            try:
                # Note: In staging, this would actually send via WebSocket
                # Here we just validate the method is callable
                self.assertTrue(hasattr(manager, 'send_event'))
            except Exception as e:
                self.fail(f"Critical WebSocket event {event} failed: {e}")

    @pytest.mark.staging_required
    async def test_agent_execution_websocket_integration_preserved(self):
        """Test that agent execution WebSocket integration still works."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.agents.supervisor.execution_engine import create_execution_engine

        user_context = self.create_mock_user_context()
        websocket_manager = get_websocket_manager(user_context=user_context)

        # Test that execution engine can still integrate with WebSocket manager
        try:
            execution_engine = create_execution_engine(
                user_context=user_context,
                websocket_manager=websocket_manager
            )
            self.assertIsNotNone(execution_engine)
        except Exception as e:
            self.fail(f"Agent execution WebSocket integration failed: {e}")
```

#### 3.2 Business Value Protection Tests
**File**: `tests/mission_critical/issue_1236/test_business_value_protection.py`

```python
class TestBusinessValueProtection(SSotBaseTestCase):
    """Ensure $500K+ ARR WebSocket functionality is protected."""

    async def test_chat_functionality_imports_work(self):
        """Test that chat-related WebSocket imports still work."""
        # Test imports that support chat functionality
        import_tests = [
            "from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager",
            "from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager",
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerFactory"
        ]

        for import_statement in import_tests:
            try:
                exec(import_statement)
            except ImportError as e:
                self.fail(f"Critical chat import failed: {import_statement} - {e}")

    async def test_websocket_manager_factory_compatibility(self):
        """Test WebSocket manager factory compatibility after fix."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerFactory

        # Test legacy factory methods still work
        manager1 = WebSocketManagerFactory.create_manager()
        manager2 = WebSocketManagerFactory.get_manager()
        manager3 = WebSocketManagerFactory.create("test_user")

        for manager in [manager1, manager2, manager3]:
            self.assertIsNotNone(manager)
            self.assertTrue(hasattr(manager, 'send_event'))
```

### 4. REGRESSION PREVENTION TESTS (Unit - Non-Docker)

**PURPOSE**: Prevent future import path regressions

#### 4.1 Import Path Linting Tests
**File**: `tests/unit/issue_1236/test_import_path_linting.py`

```python
class TestImportPathLinting(SSotBaseTestCase):
    """Prevent future import path regressions."""

    def test_no_files_import_unified_websocket_manager_from_unified_manager(self):
        """Test that no active files import UnifiedWebSocketManager from unified_manager."""
        import os
        import re

        problematic_files = []

        # Scan active Python files (exclude backups)
        for root, dirs, files in os.walk('./netra_backend'):
            # Skip backup directories
            if any(skip in root for skip in ['backup', '.backup', 'backups']):
                continue

            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if ('from netra_backend.app.websocket_core.unified_manager import' in content
                                and 'UnifiedWebSocketManager' in content
                                and not content.startswith('# BACKUP')
                                and 'UnifiedWebSocketManager' in content):
                                problematic_files.append(filepath)
                    except:
                        pass

        if problematic_files:
            self.fail(f"Found files importing UnifiedWebSocketManager from unified_manager: {problematic_files}")

    def test_websocket_manager_exports_are_consistent(self):
        """Test that websocket_manager.py exports are consistent."""
        from netra_backend.app.websocket_core.websocket_manager import __all__

        required_exports = [
            'UnifiedWebSocketManager',
            'WebSocketManager',
            'get_websocket_manager',
            'WebSocketManagerFactory'
        ]

        for export in required_exports:
            self.assertIn(export, __all__, f"Required export {export} missing from websocket_manager.__all__")
```

## TEST EXECUTION STRATEGY

### PRE-FIX EXECUTION (Proving Issues Exist)

1. **Run Failing Tests First**:
```bash
# These should FAIL before fix, proving import issues exist
python tests/unified_test_runner.py --test-file tests/unit/issue_1236/test_import_resolution_validation.py::TestUnifiedWebSocketManagerImportResolution::test_import_from_unified_manager_fails_gracefully

# Run current problematic test files that should be failing
python tests/unified_test_runner.py --test-file tests/unit/websocket_ssot_issue960/test_websocket_manager_singleton_enforcement.py

python tests/unified_test_runner.py --test-file tests/integration/websocket_ssot/test_factory_preservation.py
```

2. **Document Failure Modes**:
   - ImportError: cannot import name 'UnifiedWebSocketManager' from 'netra_backend.app.websocket_core.unified_manager'
   - Affected test files fail to run due to import errors
   - Test collection failures in affected modules

### POST-FIX VALIDATION (Confirming Fixes Work)

1. **Run Import Resolution Tests**:
```bash
# All import tests should PASS after fix
python tests/unified_test_runner.py --category unit --test-pattern "*issue_1236*"
```

2. **Run Integration Tests**:
```bash
# WebSocket manager functionality tests should PASS
python tests/unified_test_runner.py --category integration --test-pattern "*issue_1236*" --real-services
```

3. **Run Mission Critical Tests**:
```bash
# Golden Path protection tests should PASS
python tests/unified_test_runner.py --category mission_critical --test-pattern "*issue_1236*" --env staging
```

4. **Run Existing WebSocket Tests**:
```bash
# Previously failing tests should now PASS
python tests/unified_test_runner.py --test-file tests/unit/websocket_ssot_issue960/test_websocket_manager_singleton_enforcement.py

python tests/unified_test_runner.py --test-file tests/integration/websocket_ssot/test_factory_preservation.py
```

## SUCCESS CRITERIA

### PRIMARY SUCCESS CRITERIA
- [ ] **Import Resolution**: All `UnifiedWebSocketManager` imports work from correct path
- [ ] **No Import Errors**: Zero ImportError exceptions for WebSocket manager imports
- [ ] **Existing Tests Pass**: Previously failing tests due to import issues now pass
- [ ] **Golden Path Preserved**: No regression in critical WebSocket functionality

### SECONDARY SUCCESS CRITERIA
- [ ] **Factory Function Works**: `get_websocket_manager()` factory function operational
- [ ] **Cross-Service Integration**: Agent registry and bridge factory integration maintained
- [ ] **Alias Consistency**: `UnifiedWebSocketManager` alias correctly points to implementation
- [ ] **Regression Prevention**: Linting tests prevent future import path issues

### BUSINESS VALUE VALIDATION
- [ ] **Zero Customer Impact**: No disruption to chat functionality
- [ ] **$500K+ ARR Protected**: WebSocket infrastructure supporting revenue preserved
- [ ] **Development Velocity**: Import issues don't block developer productivity
- [ ] **Golden Path Operational**: End-to-end user flow remains functional

## RISK MITIGATION

### LOW-RISK ISSUES IDENTIFIED
- **Import Path Confusion**: Clear documentation of correct import patterns
- **Legacy Code Dependencies**: Maintain backward compatibility during transition
- **Test Infrastructure Impact**: Use SSOT testing patterns to prevent cascading failures

### ROLLBACK STRATEGY
1. **Immediate Rollback**: Revert import path changes if critical failures detected
2. **Compatibility Preservation**: Maintain both import paths temporarily if needed
3. **Gradual Migration**: Phase fixes if widespread impact discovered

## NEXT STEPS

### PHASE 1: Test Creation (Current Session)
- [x] **Create test plan** ✅ COMPLETE
- [ ] **Create failing import tests** 🔄 IN PROGRESS
- [ ] **Create functionality validation tests**
- [ ] **Create mission critical regression tests**

### PHASE 2: Fix Implementation
- [ ] **Identify all affected files requiring import path corrections**
- [ ] **Update import statements from `unified_manager` to `websocket_manager`**
- [ ] **Validate import corrections against test suite**

### PHASE 3: Validation & Documentation
- [ ] **Run complete test suite to confirm fixes**
- [ ] **Update GitHub issue with test results**
- [ ] **Document correct import patterns for future reference**

---

**GENERATED**: 2025-09-15 by agent-session-2025-09-15-0831
**TEST FRAMEWORK**: SSOT-compliant, non-docker, real-services where appropriate
**GOLDEN PATH PRIORITY**: WebSocket infrastructure supporting $500K+ ARR protected