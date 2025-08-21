"""Corpus admin agent recovery strategy imports.

Import CorpusAdminRecoveryStrategy from single source of truth.
Re-exports for backward compatibility.
"""

from netra_backend.app.interfaces_agent_recovery import CorpusAdminRecoveryStrategy

# Re-export for backward compatibility
__all__ = ['CorpusAdminRecoveryStrategy']