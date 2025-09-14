"""
REMEDIATION FIX: Supervisor Agent Modern - Compatibility Import for Issue #861

This file was missing and causing integration test import failures.
It provides backward compatibility for tests expecting supervisor_agent_modern imports.

The actual implementation is in supervisor_ssot.py, which contains the SSOT version.
This file simply re-exports the SSOT classes to maintain test compatibility.

Business Value:
- Segment: All - $500K+ ARR Protection
- Goal: Enable integration test execution
- Impact: Fixes 3 missing system component import failures
- Revenue Impact: Prevents test infrastructure gaps from blocking deployment
"""

from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

# Backward compatibility aliases for tests that expect different names
SupervisorAgentModern = SupervisorAgent  # Some tests import this name

# Export all the classes tests might expect
__all__ = [
    'SupervisorAgent',
    'SupervisorAgentModern'
]