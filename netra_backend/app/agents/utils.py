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

# Import JSON utilities from unified handler
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer,
    safe_json_loads,
    safe_json_dumps,
)

# Create compatibility shims for old function names using proper SSOT handlers
def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM response using SSOT handler."""
    parser = LLMResponseParser()
    result = parser.safe_json_parse(response, None)
    return result if isinstance(result, dict) else None

def extract_partial_json(response: str) -> Optional[Dict[str, Any]]:
    """Extract partial JSON from response using SSOT recovery mechanisms."""
    error_fixer = JSONErrorFixer()
    return error_fixer.recover_truncated_json(response)

def fix_common_json_errors(json_str: str) -> str:
    """Fix common JSON errors using SSOT handler."""
    error_fixer = JSONErrorFixer()
    return error_fixer.fix_common_json_errors(json_str)

def preprocess_llm_response(response: str) -> str:
    """Preprocess LLM response for JSON extraction."""
    return response.strip()

def recover_truncated_json(json_str: str) -> Optional[Dict[str, Any]]:
    """Attempt to recover truncated JSON using SSOT handler."""
    error_fixer = JSONErrorFixer()
    return error_fixer.recover_truncated_json(json_str)

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