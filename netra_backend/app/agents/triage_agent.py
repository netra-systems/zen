"""
TriageAgent compatibility module.

This module provides backward compatibility for imports expecting 'triage_agent'.
The actual implementation is in triage_sub_agent package.

Business Value:
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Maintain test compatibility during refactoring
- Value Impact: Ensures tests continue to work with legacy import paths
- Strategic Impact: Supports gradual migration to new agent structure
"""

# Import the actual TriageSubAgent from its current location
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent

# Create alias for backward compatibility
TriageAgent = TriageSubAgent

# Export for direct import
__all__ = ['TriageAgent', 'TriageSubAgent']