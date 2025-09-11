"""
CRITICAL GOLDEN PATH COMPATIBILITY MODULE

IMPORT COMPATIBILITY: models_corpus.py  
Status: COMPATIBILITY LAYER - Re-exports Thread, Message, Run models from models_agent.py
Purpose: Enables Golden Path tests to import corpus-related models successfully
Business Impact: Fixes critical Golden Path test collection blocking $500K+ ARR validation

SSOT COMPLIANCE:
- The actual Thread, Message, Run models are defined in models_agent.py (SSOT location)
- This module provides backward compatibility for existing imports
- Corpus models are part of agent/thread execution system
- Maintains service boundaries and SSOT patterns

CREATED: 2025-09-10 to resolve Golden Path import blocker #2 (part 2)
GOLDEN PATH DEPENDENCY: Required for test collection and execution
"""

# Re-export corpus-related models from the SSOT location
from netra_backend.app.db.models_agent import Thread, Message, Run

# Maintain compatibility for any existing imports
__all__ = ["Thread", "Message", "Run"]