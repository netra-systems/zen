# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored to comply with 8-line function limit - imports from utils_json_extraction
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 2
# Review: Pending | Score: 95
# ================================
"""Utility functions for agent operations - compliant with 8-line limit."""

from typing import Any, Dict, Optional

# Import all JSON extraction functions from refactored module
from app.agents.utils_json_extraction import (
    preprocess_llm_response,
    extract_json_from_response,
    fix_common_json_errors,
    recover_truncated_json,
    extract_partial_json
)

# Re-export for backward compatibility
__all__ = [
    'preprocess_llm_response',
    'extract_json_from_response', 
    'fix_common_json_errors',
    'recover_truncated_json',
    'extract_partial_json'
]