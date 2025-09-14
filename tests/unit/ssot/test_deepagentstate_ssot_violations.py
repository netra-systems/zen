"""
FAILING TESTS: DeepAgentState SSOT Violation Detection (Issue #871)

These tests MUST initially FAIL to prove the SSOT violation exists:
- DEPRECATED: netra_backend/app/agents/state.py:164 (20+ files importing)
- SSOT SOURCE: netra_backend/app/schemas/agent_models.py:119 (authoritative)

These tests will PASS only AFTER SSOT remediation is complete.
"""

import pytest
from typing import Type, get_origin, get_args
import inspect
import sys

class TestDeepAgentStateSSotViolation:
    """Test suite proving DeepAgentState SSOT violation exists"""

    def test_deepagentstate_import_conflict_violation(self):
        """
        FAILING TEST: Proves SSOT violation - both import paths exist and create different objects

        Expected: FAIL initially (different objects exist)
        After Fix: PASS (single SSOT source)
        """
        # Import both versions to prove duplication exists
        try:
            from netra_backend.app.agents.state import DeepAgentState as DeprecatedState
            deprecated_exists = True
            deprecated_module = inspect.getmodule(DeprecatedState)
        except ImportError:
            deprecated_exists = False
            deprecated_module = None

        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState
            ssot_exists = True
            ssot_module = inspect.getmodule(SsotState)
        except ImportError:
            ssot_exists = False
            ssot_module = None

        # Both should exist currently (proving duplication)
        assert deprecated_exists, "Deprecated DeepAgentState should exist in agents.state module"
        assert ssot_exists, "SSOT DeepAgentState should exist in schemas.agent_models module"

        # This assertion will FAIL initially - proving SSOT violation
        # After remediation, both imports should point to the same object
        assert DeprecatedState is SsotState, (
            f"SSOT VIOLATION DETECTED: DeepAgentState has duplicate definitions!\n"
            f"  - Deprecated: {deprecated_module.__file__ if deprecated_module else 'None'}\n"
            f"  - SSOT Source: {ssot_module.__file__ if ssot_module else 'None'}\n"
            f"  - Different objects: {id(DeprecatedState)} != {id(SsotState)}\n"
            f"REMEDIATION: All imports should use netra_backend.app.schemas.agent_models.DeepAgentState"
        )

    def test_deepagentstate_module_path_violation(self):
        """
        FAILING TEST: Proves deprecated module path still exists when it should be removed

        Expected: FAIL initially (deprecated path still importable)
        After Fix: PASS (deprecated path removed, only SSOT exists)
        """
        # Check if deprecated path is still importable (should fail during SSOT violation)
        deprecated_importable = True
        try:
            from netra_backend.app.agents.state import DeepAgentState as DeprecatedState
        except ImportError:
            deprecated_importable = False

        # SSOT source should always work
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState
            ssot_importable = True
        except ImportError:
            ssot_importable = False

        # During SSOT violation, deprecated should be importable (that's the problem!)
        if deprecated_importable and ssot_importable:
            pytest.fail(
                "SSOT VIOLATION: Both deprecated and SSOT paths are importable! "
                "Only SSOT path should exist after remediation."
            )
        elif not deprecated_importable and ssot_importable:
            # This is the desired end state after remediation
            assert True, "SSOT REMEDIATION COMPLETE: Only SSOT path exists"
        elif deprecated_importable and not ssot_importable:
            pytest.fail("CRITICAL ERROR: SSOT source missing!")
        else:
            pytest.fail("CRITICAL ERROR: Neither version importable!")

    def test_deprecated_warning_documentation(self):
        """
        FAILING TEST: Validates deprecated class has proper warnings

        Expected: FAIL initially (deprecated class exists with warnings)
        After Fix: N/A (deprecated class removed)
        """
        try:
            from netra_backend.app.agents.state import DeepAgentState as DeprecatedState

            # Deprecated class should have warning docstring
            docstring = DeprecatedState.__doc__ or ""

            assert "DEPRECATED" in docstring, "Deprecated class should have DEPRECATED warning"
            assert "CRITICAL DEPRECATION WARNING" in docstring, "Should have critical warning"
            assert "user isolation risks" in docstring, "Should mention user isolation risks"
            assert "MIGRATION REQUIRED" in docstring, "Should have migration guidance"

        except ImportError:
            # If import fails, the deprecated version has been removed (good!)
            pytest.skip("Deprecated DeepAgentState has been successfully removed")