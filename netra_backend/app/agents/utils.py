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
    'extract_partial_json'
]