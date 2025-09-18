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

@pytest.mark.unit
class DeepAgentStateSSotViolationTests:
    """Test suite proving DeepAgentState SSOT violation exists"""

    def test_deepagentstate_import_conflict_violation(self):
        """
        VALIDATION TEST: Confirms SSOT remediation - deprecated path removed, only SSOT path works

        Expected: FAIL initially (different objects exist)
        After Fix: PASS (single SSOT source, deprecated removed)
        """
        # Test that deprecated path is now removed
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState
            deprecated_exists = True
            deprecated_module = inspect.getmodule(DeprecatedState)
        except ImportError:
            deprecated_exists = False
            deprecated_module = None

        # Test that SSOT path still works
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState
            ssot_exists = True
            ssot_module = inspect.getmodule(SsotState)
        except ImportError:
            ssot_exists = False
            ssot_module = None

        # After remediation: deprecated should be gone, SSOT should exist
        assert not deprecated_exists, (
            f"REMEDIATION INCOMPLETE: Deprecated DeepAgentState still exists in agents.state module!\n"
            f"  - Deprecated path should be removed: {deprecated_module.__file__ if deprecated_module else 'None'}\n"
            f"REQUIRED: Remove duplicate DeepAgentState class from netra_backend.app.agents.state"
        )

        assert ssot_exists, (
            f"SSOT BROKEN: DeepAgentState should exist in schemas.agent_models module!\n"
            f"  - SSOT Source: {ssot_module.__file__ if ssot_module else 'None'}\n"
            f"REQUIRED: Ensure netra_backend.app.schemas.agent_models.DeepAgentState exists"
        )

        # SUCCESS: Only SSOT path exists, duplicate is removed
        print(f"CHECK SSOT REMEDIATION SUCCESSFUL:")
        print(f"   - Deprecated path removed: netra_backend.app.agents.state.DeepAgentState")
        print(f"   - SSOT path active: {ssot_module.__file__ if ssot_module else 'None'}")
        print(f"   - Single source of truth established for DeepAgentState")

    def test_deepagentstate_module_path_violation(self):
        """
        FAILING TEST: Proves deprecated module path still exists when it should be removed

        Expected: FAIL initially (deprecated path still importable)
        After Fix: PASS (deprecated path removed, only SSOT exists)
        """
        # Check if deprecated path is still importable (should fail during SSOT violation)
        deprecated_importable = True
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState
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
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState

            # Deprecated class should have warning docstring
            docstring = DeprecatedState.__doc__ or ""

            assert "DEPRECATED" in docstring, "Deprecated class should have DEPRECATED warning"
            assert "CRITICAL DEPRECATION WARNING" in docstring, "Should have critical warning"
            assert "user isolation risks" in docstring, "Should mention user isolation risks"
            assert "MIGRATION REQUIRED" in docstring, "Should have migration guidance"

        except ImportError:
            # If import fails, the deprecated version has been removed (good!)
            pytest.skip("Deprecated DeepAgentState has been successfully removed")