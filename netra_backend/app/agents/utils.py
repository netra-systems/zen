# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4.1 claude-sonnet-4-20250514
# Context: Updated imports for modular JSON utilities - maintains backward compatibility
# Git: anthony-aug-13-2 | clean
# Change: Refactor | Scope: Component | Risk: Low
# Session: architecture-compliance | Seq: 4
# Review: Pending | Score: 95
# ================================
"""Utility functions for agent operations - compliant with 25-line limit."""

from typing import Any, Dict, Optional

# Import all JSON extraction functions from refactored module
from netra_backend.app.agents.utils_json_extraction import (
    extract_json_from_response,
    extract_partial_json,
    fix_common_json_errors,
    preprocess_llm_response,
    recover_truncated_json,
)

# Re-export for backward compatibility
__all__ = [
    'preprocess_llm_response',
    'extract_json_from_response', 
    'fix_common_json_errors',
    'recover_truncated_json',
    'extract_partial_json',
    'extract_thread_id'
]


def extract_thread_id(state: Any, run_id: Optional[str] = None) -> Optional[str]:
    """Extract thread ID from state object with fallback priority.
    
    Checks in priority order:
    1. chat_thread_id attribute
    2. thread_id attribute  
    3. run_id parameter as fallback
    
    Args:
        state: State object that may contain thread ID attributes
        run_id: Optional fallback run ID
        
    Returns:
        Thread ID string or None if not found
    """
    return (
        getattr(state, 'chat_thread_id', None) or 
        getattr(state, 'thread_id', None) or 
        run_id
    )