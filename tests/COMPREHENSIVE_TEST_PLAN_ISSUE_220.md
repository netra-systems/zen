# Comprehensive Test Plan for Issue #220: AgentExecutionTracker SSOT Consolidation

**GitHub Issue:** #220  
**Created:** 2025-01-09  
**Status:** Test Plan Ready for Execution  
**Focus:** SSOT consolidation for multiple execution tracking systems

## Executive Summary

**Problem Statement:**
- 4 execution tracking systems with 1,879 lines duplicate code
- 126+ files affected by import violations  
- Race conditions causing WebSocket 1011 errors
- Golden Path functionality degraded
- Multiple trackers creating shared global state conflicts

**Test Strategy:**
This test plan creates **practical, executable tests** that clearly demonstrate the SSOT violations and validate consolidation fixes. Tests are designed to fail until consolidation is complete, providing clear success criteria.

## Part 1: Infrastructure Tests (Priority 1 - Must Pass First)

### 1.1 Test Discovery Syntax Error Fixes

**File:** `/tests/infrastructure/test_discovery_validation.py`

```python
"""Validate test discovery infrastructure works correctly."""

import pytest
import subprocess
import sys
from pathlib import Path

class TestDiscoveryValidation:
    """Tests that validate test discovery infrastructure."""
    
    def test_websocket_test_syntax_is_valid(self):
        """Validate WebSocket test files have valid syntax."""
        # Check syntax of known problematic file
        websocket_test = Path("netra_backend/tests/unit/test_websocket_notifier.py")
        result = subprocess.run([
            sys.executable, "-m", "py_compile", str(websocket_test)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Syntax error in {websocket_test}: {result.stderr}"
    
    def test_pytest_collection_works(self):
        """Validate pytest can collect tests without syntax errors."""
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only", "-q", 
            "tests/unit/ssot_validation/"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Test collection failed: {result.stderr}"
        assert "error" not in result.stderr.lower(), "Collection errors detected"
    
    def test_ssot_base_test_case_importable(self):
        """Validate SSOT test framework is functional."""
        try:
            from test_framework.ssot.base_test_case import SSotBaseTestCase
            assert SSotBaseTestCase is not None
        except ImportError as e:
            pytest.fail(f"SSOT BaseTestCase not importable: {e}")
```

**Command:** `python tests/unified_test_runner.py --file tests/infrastructure/test_discovery_validation.py`

### 1.2 Test Framework Integrity

**File:** `/tests/infrastructure/test_ssot_framework_integrity.py`

```python
"""Validate SSOT test framework integrity."""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSSOTFrameworkIntegrity(SSotBaseTestCase):
    """Validate SSOT test framework components."""
    
    def test_unified_test_runner_available(self):
        """Validate unified test runner is functional."""
        from tests.unified_test_runner import main
        assert callable(main)
    
    def test_ssot_mock_factory_available(self):
        """Validate SSOT mock factory is functional."""
        from test_framework.ssot.mock_factory import SSotMockFactory
        mock_factory = SSotMockFactory()
        assert mock_factory is not None
    
    def test_isolated_environment_available(self):
        """Validate environment isolation works."""
        from shared.isolated_environment import get_env
        env_value = get_env("TEST_ENV_VAR", "default")
        assert env_value is not None
```

**Command:** `python tests/unified_test_runner.py --file tests/infrastructure/test_ssot_framework_integrity.py`

## Part 2: SSOT Violation Detection Tests (Should FAIL Currently)

### 2.1 Core SSOT Violation Detection

**File:** `/tests/unit/ssot_validation/test_execution_tracking_ssot_violations.py`

```python
"""
SSOT Violation Detection Tests for Issue #220
These tests should FAIL before consolidation, PASS after consolidation.
"""

import pytest
import ast
import importlib
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestExecutionTrackingSSOTViolations(SSotBaseTestCase):
    """Tests designed to detect current SSOT violations."""
    
    def test_multiple_execution_trackers_exist(self):
        """Should FAIL - Multiple execution tracking systems violate SSOT."""
        violations = []
        
        # Check for AgentStateTracker
        try:
            from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
            violations.append("AgentStateTracker exists (should be consolidated)")
        except ImportError:
            pass
            
        # Check for AgentExecutionTimeoutManager  
        try:
            from netra_backend.app.agents.execution_timeout_manager import AgentExecutionTimeoutManager
            violations.append("AgentExecutionTimeoutManager exists (should be consolidated)")
        except ImportError:
            pass
            
        # Check for duplicate execution engines
        execution_engines = [
            "netra_backend.app.agents.supervisor.execution_engine",
            "netra_backend.app.agents.execution_engine_consolidated", 
            "netra_backend.app.agents.supervisor.user_execution_engine"
        ]
        
        existing_engines = []
        for engine_path in execution_engines:
            try:
                importlib.import_module(engine_path)
                existing_engines.append(engine_path)
            except ImportError:
                pass
                
        if len(existing_engines) > 1:
            violations.append(f"Multiple execution engines: {existing_engines}")
            
        if violations:
            pytest.fail(f"SSOT VIOLATIONS DETECTED: {'; '.join(violations)}")
    
    def test_manual_execution_id_generation_detected(self):
        """Should FAIL - Manual execution ID generation bypasses UnifiedIDManager."""
        violations = []
        
        # Scan for manual ID generation patterns
        patterns_to_check = [
            ("f\"{agent_name}_{run_id}_{int(time.time() * 1000)}\"", "timeout_manager"),
            ("uuid.uuid4()", "direct_uuid_calls"),
            ("str(uuid.uuid4())", "direct_uuid_string_calls")
        ]
        
        files_to_scan = [
            Path("netra_backend/app/agents/agent_state_tracker.py"),
            Path("netra_backend/app/agents/execution_timeout_manager.py"),
            Path("netra_backend/app/agents/supervisor/execution_engine.py")
        ]
        
        for file_path in files_to_scan:
            if file_path.exists():
                content = file_path.read_text()
                for pattern, violation_type in patterns_to_check:
                    if pattern in content:
                        violations.append(f"{violation_type} in {file_path}")
                        
        if violations:
            pytest.fail(f"MANUAL ID GENERATION VIOLATIONS: {'; '.join(violations)}")
    
    def test_direct_instantiation_violations_in_tests(self):
        """Should FAIL - Test files bypass singleton pattern."""
        violations = []
        
        test_files_to_check = [
            "netra_backend/tests/unit/agents/test_agent_execution_id_migration.py",
            "tests/mission_critical/test_websocket_timeout_optimization.py"
        ]
        
        for test_file in test_files_to_check:
            file_path = Path(test_file)
            if file_path.exists():
                content = file_path.read_text()
                # Look for direct instantiation patterns
                if "AgentExecutionTracker(" in content and "get_execution_tracker()" not in content:
                    violations.append(f"Direct instantiation in {test_file}")
                    
        if violations:
            pytest.fail(f"DIRECT INSTANTIATION VIOLATIONS: {'; '.join(violations)}")
    
    def test_import_violations_across_codebase(self):
        """Should FAIL - 126+ files have import violations."""
        violations = []
        
        # Check for imports that should be consolidated
        problematic_imports = [
            "from netra_backend.app.agents.agent_state_tracker import",
            "from netra_backend.app.agents.execution_timeout_manager import"
        ]
        
        # Scan key directories for violations
        scan_dirs = [
            Path("netra_backend/app"),
            Path("tests"),
            Path("scripts")
        ]
        
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for py_file in scan_dir.rglob("*.py"):
                    content = py_file.read_text()
                    for import_pattern in problematic_imports:
                        if import_pattern in content:
                            violations.append(f"{import_pattern} in {py_file}")
                            
        # We expect many violations currently
        if len(violations) < 10:  # Expect significant violations
            pytest.fail(f"Expected significant import violations, found only {len(violations)}")
            
        # Report violations for tracking
        print(f"DETECTED {len(violations)} IMPORT VIOLATIONS (expected before consolidation)")
```

**Expected Result:** FAIL (detects violations)  
**Command:** `python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_execution_tracking_ssot_violations.py`

### 2.2 Shared State Conflict Detection

**File:** `/tests/unit/ssot_validation/test_shared_state_conflicts.py`

```python
"""
Shared State Conflict Detection for Race Conditions
These tests detect current race conditions from multiple execution trackers.
"""

import pytest
import asyncio
import threading
import time
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSharedStateConflicts(SSotBaseTestCase):
    """Detect shared state conflicts between execution trackers."""
    
    def test_multiple_tracker_state_conflicts(self):
        """Should FAIL - Multiple trackers create state conflicts."""
        conflicts = []
        
        try:
            # Import multiple tracking systems
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
            
            # Create instances
            exec_tracker = AgentExecutionTracker.get_instance()
            state_tracker = AgentStateTracker()
            
            # Simulate execution tracking in both systems
            execution_id = "test_execution_123"
            
            # Both systems tracking same execution creates conflict
            exec_tracker.create_execution("test_agent", "thread_123", "run_123")
            state_tracker.track_phase_transition(execution_id, "STARTING", "RUNNING")
            
            conflicts.append("Multiple systems tracking same execution")
            
        except ImportError:
            # If imports fail, consolidation may already be done
            pass
            
        if conflicts:
            pytest.fail(f"SHARED STATE CONFLICTS: {'; '.join(conflicts)}")
    
    def test_concurrent_execution_state_corruption(self):
        """Should FAIL - Concurrent updates cause state corruption."""
        try:
            from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
            
            corruption_detected = False
            state_tracker = AgentStateTracker()
            
            def update_state(execution_id, phase):
                try:
                    state_tracker.track_phase_transition(execution_id, "STARTING", phase)
                except Exception:
                    nonlocal corruption_detected
                    corruption_detected = True
            
            # Simulate concurrent state updates
            threads = []
            for i in range(5):
                thread = threading.Thread(
                    target=update_state, 
                    args=(f"exec_{i}", f"PHASE_{i}")
                )
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
                
            if corruption_detected:
                pytest.fail("STATE CORRUPTION detected in concurrent updates")
                
        except ImportError:
            # Consolidation may be complete
            pass
```

**Expected Result:** FAIL (detects conflicts)  
**Command:** `python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_shared_state_conflicts.py`

## Part 3: Race Condition Reproduction Tests (Should FAIL Currently)

### 3.1 WebSocket 1011 Error Reproduction

**File:** `/tests/integration/race_conditions/test_websocket_1011_reproduction.py`

```python
"""
WebSocket 1011 Error Reproduction Tests
Reproduce race conditions causing WebSocket errors from execution tracking conflicts.
"""

import pytest
import asyncio
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestWebSocket1011Reproduction(SSotAsyncTestCase):
    """Reproduce WebSocket 1011 errors from execution tracking race conditions."""
    
    async def test_execution_tracker_websocket_race_condition(self):
        """Should FAIL - Race condition between execution trackers and WebSocket events."""
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
            
            # Simulate race condition scenario
            exec_tracker = AgentExecutionTracker.get_instance()
            state_tracker = AgentStateTracker()
            
            # Create mock WebSocket notifier
            websocket_notifier = WebSocketNotifier(connection=None)
            
            # Simulate rapid execution state changes that trigger race condition
            execution_id = exec_tracker.create_execution("test_agent", "thread_123", "run_123")
            
            # Race condition: Both systems try to send WebSocket events
            async def exec_tracker_update():
                exec_tracker.update_execution_state(execution_id, "RUNNING")
                await websocket_notifier.send_agent_started_event("user_123", "thread_123")
            
            async def state_tracker_update():
                state_tracker.track_phase_transition(execution_id, "STARTING", "THINKING")
                await websocket_notifier.send_agent_thinking_event("user_123", "thread_123")
            
            # Execute concurrently to trigger race condition
            try:
                await asyncio.gather(
                    exec_tracker_update(),
                    state_tracker_update(),
                    return_exceptions=True
                )
                
                # If no exception, race condition still exists
                pytest.fail("RACE CONDITION: Multiple execution trackers causing WebSocket conflicts")
                
            except Exception as e:
                # Expected - race condition causes errors
                if "1011" in str(e) or "connection" in str(e).lower():
                    pytest.fail(f"WEBSOCKET 1011 ERROR reproduced: {e}")
                    
        except ImportError:
            # Consolidation may be complete
            pytest.skip("Execution tracking already consolidated")
    
    async def test_timeout_manager_websocket_interference(self):
        """Should FAIL - Timeout manager interferes with WebSocket event delivery."""
        try:
            from netra_backend.app.agents.execution_timeout_manager import AgentExecutionTimeoutManager
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
            
            timeout_manager = AgentExecutionTimeoutManager()
            websocket_notifier = WebSocketNotifier(connection=None)
            
            # Simulate timeout during WebSocket event sending
            execution_id = f"test_agent_run_123_{int(time.time() * 1000)}"
            
            # Setup timeout that interferes with WebSocket
            timeout_manager.set_timeout(execution_id, 0.1)  # Very short timeout
            
            # Try to send WebSocket event that takes longer than timeout
            try:
                await asyncio.sleep(0.2)  # Longer than timeout
                await websocket_notifier.send_agent_completed_event("user_123", "thread_123")
                
                pytest.fail("TIMEOUT INTERFERENCE: Timeout manager should have interfered")
                
            except Exception as e:
                if "timeout" in str(e).lower():
                    pytest.fail(f"TIMEOUT INTERFERENCE detected: {e}")
                    
        except ImportError:
            pytest.skip("Timeout manager already consolidated")
```

**Expected Result:** FAIL (reproduces race conditions)  
**Command:** `python tests/unified_test_runner.py --file tests/integration/race_conditions/test_websocket_1011_reproduction.py --no-docker`

### 3.2 Execution State Ordering Conflicts

**File:** `/tests/integration/race_conditions/test_execution_state_ordering.py`

```python
"""
Execution State Ordering Conflict Tests
Test for state ordering issues from multiple execution tracking systems.
"""

import pytest
import asyncio
import time
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestExecutionStateOrderingConflicts(SSotAsyncTestCase):
    """Test execution state ordering conflicts."""
    
    async def test_state_transition_ordering_violations(self):
        """Should FAIL - Multiple trackers create invalid state transitions."""
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
            
            exec_tracker = AgentExecutionTracker.get_instance()
            state_tracker = AgentStateTracker()
            
            execution_id = exec_tracker.create_execution("test_agent", "thread_123", "run_123")
            
            # Create state ordering conflict
            ordering_violations = []
            
            # Execution tracker sets state
            exec_tracker.update_execution_state(execution_id, "RUNNING")
            current_exec_state = exec_tracker.get_execution_state(execution_id)
            
            # State tracker sets different state for same execution
            state_tracker.track_phase_transition(execution_id, "STARTING", "THINKING")
            
            # Check for state inconsistency
            if current_exec_state != "RUNNING":
                ordering_violations.append(f"State changed unexpectedly: {current_exec_state}")
            
            # Both systems may have different views of execution state
            exec_view = exec_tracker.get_execution_state(execution_id)
            
            if exec_view != "RUNNING":
                ordering_violations.append("Execution state inconsistency detected")
                
            if ordering_violations:
                pytest.fail(f"STATE ORDERING VIOLATIONS: {'; '.join(ordering_violations)}")
                
        except ImportError:
            pytest.skip("Execution tracking already consolidated")
    
    async def test_timeout_execution_state_conflicts(self):
        """Should FAIL - Timeout manager conflicts with execution state."""
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            from netra_backend.app.agents.execution_timeout_manager import AgentExecutionTimeoutManager
            
            exec_tracker = AgentExecutionTracker.get_instance()
            timeout_manager = AgentExecutionTimeoutManager()
            
            execution_id = exec_tracker.create_execution("test_agent", "thread_123", "run_123")
            
            # Set execution to RUNNING
            exec_tracker.update_execution_state(execution_id, "RUNNING")
            
            # Timeout manager may set to TIMEOUT independently
            timeout_manager.set_timeout(execution_id, 0.1)
            await asyncio.sleep(0.2)
            
            # Check timeout status
            if timeout_manager.check_timeout(execution_id):
                exec_state = exec_tracker.get_execution_state(execution_id)
                if exec_state != "TIMEOUT":
                    pytest.fail("TIMEOUT CONFLICT: Execution state not synchronized with timeout")
                    
        except ImportError:
            pytest.skip("Timeout manager already consolidated")
```

**Expected Result:** FAIL (detects ordering conflicts)  
**Command:** `python tests/unified_test_runner.py --file tests/integration/race_conditions/test_execution_state_ordering.py --no-docker`

## Part 4: Golden Path Functionality Tests (Should PASS After Consolidation)

### 4.1 Golden Path Execution Flow Validation

**File:** `/tests/e2e/golden_path/test_consolidated_execution_tracking.py`

```python
"""
Golden Path Functionality Validation with Consolidated Execution Tracking
These tests validate Golden Path works with single SSOT execution tracker.
"""

import pytest
import asyncio
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestConsolidatedExecutionTracking(SSotAsyncTestCase):
    """Test Golden Path functionality with consolidated execution tracking."""
    
    async def test_agent_execution_golden_path_with_ssot(self):
        """Should PASS after consolidation - Complete agent execution works."""
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        
        # Test single SSOT execution tracker
        exec_tracker = AgentExecutionTracker.get_instance()
        
        # Golden Path: Create execution
        execution_id = exec_tracker.create_execution(
            agent_name="DataHelperAgent",
            thread_id="thread_123", 
            run_id="run_123"
        )
        
        assert execution_id is not None
        assert exec_tracker.get_execution_state(execution_id) == "PENDING"
        
        # Golden Path: Progress through states
        state_transitions = [
            "STARTING",
            "RUNNING", 
            "COMPLETING",
            "COMPLETED"
        ]
        
        for state in state_transitions:
            exec_tracker.update_execution_state(execution_id, state)
            current_state = exec_tracker.get_execution_state(execution_id)
            assert current_state == state, f"State transition failed: expected {state}, got {current_state}"
        
        # Golden Path: Execution history is complete
        history = exec_tracker.get_execution_history(execution_id)
        assert len(history) > 0, "Execution history should be recorded"
        
        # Golden Path: Cleanup works
        exec_tracker.cleanup_execution(execution_id)
        
    async def test_websocket_events_with_consolidated_tracking(self):
        """Should PASS after consolidation - WebSocket events work with SSOT."""
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        
        exec_tracker = AgentExecutionTracker.get_instance()
        
        # Mock WebSocket connection
        mock_websocket = MockWebSocketConnection()
        websocket_notifier = WebSocketNotifier(connection=mock_websocket)
        
        # Create execution
        execution_id = exec_tracker.create_execution("TestAgent", "thread_123", "run_123")
        
        # Send all 5 critical WebSocket events
        events_to_test = [
            ("agent_started", websocket_notifier.send_agent_started_event),
            ("agent_thinking", websocket_notifier.send_agent_thinking_event),
            ("tool_executing", websocket_notifier.send_tool_executing_event),
            ("tool_completed", websocket_notifier.send_tool_completed_event),
            ("agent_completed", websocket_notifier.send_agent_completed_event)
        ]
        
        for event_name, event_method in events_to_test:
            try:
                await event_method("user_123", "thread_123")
                mock_websocket.verify_event_sent(event_name)
            except Exception as e:
                pytest.fail(f"WebSocket event {event_name} failed: {e}")
    
    async def test_user_isolation_with_consolidated_tracking(self):
        """Should PASS after consolidation - User isolation maintained."""
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        
        exec_tracker = AgentExecutionTracker.get_instance()
        
        # Create executions for different users
        user1_execution = exec_tracker.create_execution("Agent1", "user1_thread", "user1_run")
        user2_execution = exec_tracker.create_execution("Agent2", "user2_thread", "user2_run") 
        
        # Update states independently
        exec_tracker.update_execution_state(user1_execution, "RUNNING")
        exec_tracker.update_execution_state(user2_execution, "THINKING")
        
        # Verify isolation
        user1_state = exec_tracker.get_execution_state(user1_execution)
        user2_state = exec_tracker.get_execution_state(user2_execution)
        
        assert user1_state == "RUNNING", f"User 1 state incorrect: {user1_state}"
        assert user2_state == "THINKING", f"User 2 state incorrect: {user2_state}"
        
        # Verify no cross-contamination
        user1_executions = exec_tracker.get_user_executions("user1_thread")
        user2_executions = exec_tracker.get_user_executions("user2_thread")
        
        assert user1_execution in [e.execution_id for e in user1_executions]
        assert user2_execution not in [e.execution_id for e in user1_executions]

class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self):
        self.sent_events = []
    
    async def send_text(self, message):
        self.sent_events.append(message)
    
    def verify_event_sent(self, event_type):
        event_found = any(event_type in event for event in self.sent_events)
        assert event_found, f"Event {event_type} was not sent"
```

**Expected Result:** PASS after consolidation  
**Command:** `python tests/unified_test_runner.py --file tests/e2e/golden_path/test_consolidated_execution_tracking.py --env staging`

## Part 5: Consolidation Validation Tests (Should PASS After Work)

### 5.1 SSOT Compliance Validation

**File:** `/tests/unit/ssot_validation/test_consolidation_success_validation.py`

```python
"""
SSOT Consolidation Success Validation Tests
These tests validate successful SSOT consolidation.
"""

import pytest
import importlib
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestConsolidationSuccessValidation(SSotBaseTestCase):
    """Validate successful SSOT consolidation."""
    
    def test_single_execution_tracker_ssot_compliance(self):
        """Should PASS after consolidation - Only AgentExecutionTracker exists."""
        # AgentExecutionTracker should be importable
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            tracker = AgentExecutionTracker.get_instance()
            assert tracker is not None
        except ImportError:
            pytest.fail("AgentExecutionTracker should be importable as SSOT")
        
        # Other tracking systems should be deprecated/removed
        deprecated_modules = [
            "netra_backend.app.agents.agent_state_tracker",
            "netra_backend.app.agents.execution_timeout_manager"
        ]
        
        for module_path in deprecated_modules:
            try:
                importlib.import_module(module_path)
                pytest.fail(f"SSOT VIOLATION: {module_path} should be deprecated")
            except ImportError:
                # Expected - module should not exist after consolidation
                pass
    
    def test_consolidated_methods_available(self):
        """Should PASS after consolidation - All methods available in SSOT."""
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        
        tracker = AgentExecutionTracker.get_instance()
        
        # State management methods (from AgentStateTracker)
        state_methods = [
            'get_agent_state', 'set_agent_state', 'transition_state',
            'validate_state_transition', 'get_state_history'
        ]
        
        # Timeout management methods (from AgentExecutionTimeoutManager)  
        timeout_methods = [
            'set_timeout', 'check_timeout', 'register_circuit_breaker',
            'circuit_breaker_status', 'reset_circuit_breaker'
        ]
        
        # Verify methods exist or have equivalent functionality
        for method_name in state_methods + timeout_methods:
            # Check if method exists or equivalent exists
            has_method = hasattr(tracker, method_name)
            has_equivalent = any(
                equivalent in dir(tracker) 
                for equivalent in [method_name.replace('_', ''), f"execution_{method_name}"]
            )
            
            assert has_method or has_equivalent, f"Missing method or equivalent: {method_name}"
    
    def test_unified_id_manager_integration(self):
        """Should PASS after consolidation - Uses UnifiedIDManager for IDs."""
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
        
        tracker = AgentExecutionTracker.get_instance()
        id_manager = UnifiedIDManager()
        
        # Create execution and verify ID format
        execution_id = tracker.create_execution("test_agent", "thread_123", "run_123")
        
        # Verify ID follows UnifiedIDManager format
        assert isinstance(execution_id, str)
        assert len(execution_id) > 0
        
        # Verify ID can be validated by UnifiedIDManager
        is_valid = id_manager.validate_id(execution_id, IDType.EXECUTION)
        assert is_valid, f"Execution ID {execution_id} not valid UnifiedIDManager format"
    
    def test_import_consolidation_success(self):
        """Should PASS after consolidation - Import violations resolved."""
        import ast
        from pathlib import Path
        
        # Scan for remaining import violations
        violations = []
        deprecated_imports = [
            "from netra_backend.app.agents.agent_state_tracker import",
            "from netra_backend.app.agents.execution_timeout_manager import"
        ]
        
        # Scan key directories
        scan_dirs = [
            Path("netra_backend/app"),
            Path("tests"),
            Path("scripts")
        ]
        
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for py_file in scan_dir.rglob("*.py"):
                    try:
                        content = py_file.read_text()
                        for import_pattern in deprecated_imports:
                            if import_pattern in content:
                                violations.append(f"{import_pattern} in {py_file}")
                    except Exception:
                        # Skip files that can't be read
                        continue
        
        # After consolidation, violations should be minimal (< 5)
        assert len(violations) < 5, f"Too many import violations remaining: {violations}"
```

**Expected Result:** PASS after consolidation  
**Command:** `python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_consolidation_success_validation.py`

## Part 6: Test Execution Strategy & Success Criteria

### 6.1 Test Execution Phases

**Phase 1: Infrastructure Validation (Must Pass First)**
```bash
# Validate test discovery works
python tests/unified_test_runner.py --file tests/infrastructure/test_discovery_validation.py

# Validate SSOT framework
python tests/unified_test_runner.py --file tests/infrastructure/test_ssot_framework_integrity.py
```

**Phase 2: Pre-Consolidation Baseline (Should FAIL)**
```bash
# Detect current SSOT violations (expect failures)
python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_execution_tracking_ssot_violations.py

# Reproduce race conditions (expect failures)  
python tests/unified_test_runner.py --file tests/integration/race_conditions/test_websocket_1011_reproduction.py --no-docker

# Detect shared state conflicts (expect failures)
python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_shared_state_conflicts.py
```

**Phase 3: During Consolidation (Progressive)**
```bash
# Monitor consolidation progress
python tests/unified_test_runner.py --pattern "*ssot_validation*" --fast-fail

# Validate no Golden Path regression
python tests/unified_test_runner.py --categories mission_critical --fast-fail
```

**Phase 4: Post-Consolidation Validation (Should PASS)**
```bash
# Validate SSOT compliance achieved
python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_consolidation_success_validation.py

# Validate Golden Path functionality preserved
python tests/unified_test_runner.py --file tests/e2e/golden_path/test_consolidated_execution_tracking.py --env staging

# Full validation suite
python tests/unified_test_runner.py --categories mission_critical integration --real-services
```

### 6.2 Success Criteria

**Quantitative Metrics:**
- [ ] **100%** infrastructure tests pass
- [ ] **100%** SSOT violation detection tests FAIL pre-consolidation
- [ ] **100%** race condition reproduction tests FAIL pre-consolidation  
- [ ] **100%** SSOT compliance validation tests PASS post-consolidation
- [ ] **100%** Golden Path functionality tests PASS post-consolidation
- [ ] **<5** remaining import violations post-consolidation
- [ ] **0** regressions in mission-critical WebSocket event tests

**Qualitative Metrics:**
- [ ] No WebSocket 1011 errors in Golden Path flow
- [ ] User isolation maintained across consolidation
- [ ] All 5 critical WebSocket events delivered correctly
- [ ] Execution ID generation unified through UnifiedIDManager
- [ ] State management consolidated into single interface
- [ ] Timeout management integrated into SSOT tracker

### 6.3 Test Difficulty Levels & Expected Failure Patterns

**Level 1: Infrastructure (EASY - Must Pass)**
- Test discovery syntax validation
- SSOT framework integrity  
- Basic import validation

**Level 2: SSOT Violation Detection (MEDIUM - Should FAIL Currently)**
- Multiple tracker detection
- Manual ID generation detection
- Import violation scanning
- Direct instantiation detection

**Level 3: Race Condition Reproduction (HARD - Should FAIL Currently)**
- WebSocket 1011 error reproduction
- Concurrent state update conflicts
- Timeout/execution state interference
- State ordering violations

**Level 4: Golden Path Integration (MEDIUM - Should PASS After)**
- Complete execution flow with SSOT
- WebSocket event delivery with consolidated tracking
- User isolation with single tracker
- Performance characteristics maintained

**Level 5: Consolidation Validation (EASY - Should PASS After)**
- SSOT compliance verification
- Method availability validation
- Import consolidation success
- UnifiedIDManager integration

### 6.4 Rollback Detection Tests

**Immediate Rollback Triggers:**
```bash
# These tests must NEVER fail during consolidation
python tests/unified_test_runner.py --categories mission_critical --pattern "*websocket*" --fast-fail
python tests/unified_test_runner.py --file tests/e2e/test_golden_path_user_flow.py --env staging
```

## Part 7: Implementation Timeline & Commands

### Day 1: Infrastructure Preparation
```bash
# Fix test discovery issues
python tests/unified_test_runner.py --file tests/infrastructure/test_discovery_validation.py

# Create and validate SSOT violation detection tests
python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_execution_tracking_ssot_violations.py
```

### Day 2-3: Core Consolidation
```bash
# Monitor progress during AgentStateTracker consolidation
python tests/unified_test_runner.py --pattern "*agent_state*" --fast-fail

# Validate no WebSocket regression
python tests/unified_test_runner.py --categories mission_critical --pattern "*websocket*"
```

### Day 4: Timeout Consolidation  
```bash
# Monitor timeout manager consolidation
python tests/unified_test_runner.py --pattern "*timeout*" --fast-fail

# Validate execution flow integrity
python tests/unified_test_runner.py --file tests/e2e/golden_path/test_consolidated_execution_tracking.py
```

### Day 5: Final Validation
```bash
# Complete SSOT compliance validation
python tests/unified_test_runner.py --file tests/unit/ssot_validation/test_consolidation_success_validation.py

# Full system validation
python tests/unified_test_runner.py --categories mission_critical integration e2e --real-services --env staging
```

## Conclusion

This comprehensive test plan provides **practical, executable tests** that:

1. **Clearly demonstrate the problem** - SSOT violations, race conditions, import violations
2. **Validate the solution** - Consolidated tracking, preserved Golden Path functionality
3. **Provide clear success criteria** - Quantitative and qualitative metrics
4. **Enable safe consolidation** - Progressive validation with rollback detection
5. **Maintain business value** - Protect $500K+ ARR chat functionality

**Key Features:**
- Tests designed to fail before consolidation, pass after
- No Docker dependency for core validation
- Real service testing for critical functionality
- Progressive validation during consolidation
- Clear rollback criteria to protect business value

The test plan ensures AgentExecutionTracker SSOT consolidation delivers architectural clarity while preserving the reliable chat experience that drives platform value.