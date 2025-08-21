# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4.1 claude-sonnet-4-20250514
# Context: Main JSON extraction interface - refactored for 450-line compliance
# Git: anthony-aug-13-2 | clean
# Change: Refactor | Scope: Component | Risk: Low
# Session: architecture-compliance | Seq: 3
# Review: Pending | Score: 95
# ================================
"""Main JSON extraction interface - coordinates parsing and validation modules."""

import json
from typing import Any, Dict, Optional, List, Callable
from netra_backend.app.logging_config import central_logger as logger

# Import functions from specialized modules
from netra_backend.app.agents.utils_json_parsers import (
    try_direct_parse,
    try_extract_object,
    try_extract_array,
    try_clean_edges,
    extract_from_markdown,
    attempt_recovery_parse,
    extract_truncated_array,
    extract_complex_field,
    extract_simple_fields
)
from netra_backend.app.agents.utils_json_validators import (
    fix_common_json_errors,
    count_structure_balance,
    build_closing_sequence,
    clean_trailing_comma,
    truncate_at_last_comma,
    truncate_at_error_position,
    check_required_fields,
    preprocess_llm_response
)




def recover_truncated_json(json_str: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Recover from truncated JSON by closing open structures."""
    if not json_str:
        return None
    result = try_direct_parse(json_str)
    if result:
        return result
    return attempt_recovery_with_fixes(json_str, max_retries)


def attempt_recovery_with_fixes(json_str: str, max_retries: int) -> Optional[Dict[str, Any]]:
    """Apply fixes then iterate recovery attempts."""
    json_str = fix_common_json_errors(json_str)
    result = try_direct_parse(json_str)
    if result:
        return result
    return attempt_recovery_iterations(json_str, max_retries)


def attempt_recovery_iterations(json_str: str, max_retries: int) -> Optional[Dict[str, Any]]:
    """Iterate recovery attempts with different strategies."""
    for attempt in range(max_retries):
        result = try_recovery_with_closing(json_str, attempt)
        if result:
            return result
        json_str = apply_recovery_strategy(json_str, attempt)
        if json_str is None:
            break
    return None


def try_recovery_with_closing(json_str: str, attempt: int) -> Optional[Dict[str, Any]]:
    """Try recovery by adding closing sequence."""
    working = clean_trailing_comma(json_str)
    balance = count_structure_balance(working)
    closing = build_closing_sequence(balance)
    result = attempt_recovery_parse(working, closing)
    if result:
        logger.info(f"Recovered JSON on attempt {attempt + 1} with: {closing}")
    return result


def apply_recovery_strategy(json_str: str, attempt: int) -> Optional[str]:
    """Apply progressive recovery strategies."""
    if attempt == 0:
        return truncate_at_last_comma(json_str)
    elif attempt == 1:
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            return truncate_at_error_position(json_str, e.pos)
    return None


def extract_json_from_response(response: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM response with multiple strategies."""
    if not response:
        return None
    response = preprocess_llm_response(response)
    json_str = extract_from_markdown(response)
    result = try_extraction_strategies(json_str, max_retries)
    if not result:
        log_extraction_failure(response, json_str)
    return result


def try_extraction_strategies(json_str: str, max_retries: int) -> Optional[Dict[str, Any]]:
    """Try multiple JSON extraction strategies."""
    strategies = [
        try_direct_parse,
        lambda s: try_direct_parse(fix_common_json_errors(s)),
        try_extract_object,
        try_extract_array,
        try_clean_edges,
        lambda s: recover_truncated_json(s, max_retries)
    ]
    return execute_strategies(json_str, strategies)


def execute_strategies(json_str: str, strategies: List[Callable[[str], Optional[Dict[str, Any]]]]) -> Optional[Dict[str, Any]]:
    """Execute extraction strategies in order."""
    for i, strategy in enumerate(strategies):
        try:
            result = strategy(json_str)
            if result is not None:
                if i > 0:
                    logger.debug(f"JSON extracted using strategy {i+1}")
                return result
        except Exception as e:
            logger.debug(f"Strategy {i+1} failed: {e}")
    return None


def log_extraction_failure(response: str, json_str: str) -> None:
    """Log JSON extraction failure with context."""
    partial = extract_partial_json(response)
    if partial and len(partial) > 5:
        logger.debug(f"Full extraction failed, partial available. Length: {len(response)}")
    else:
        logger.warning(f"Failed to extract JSON. Length: {len(response)}, Preview: {response[:200]}")


def extract_partial_json(response: str, required_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Extract partial JSON from response."""
    if not response:
        return None
    result = extract_complex_field(response, r'"([^"]+)"\s*:\s*(\[[^\]]*\])')
    result.update(extract_complex_field(response, r'"([^"]+)"\s*:\s*({[^}]*})'))
    result = extract_simple_fields(response, result)
    if 'actions' not in result:
        actions = extract_truncated_array(response, 'actions')
        if actions is not None:
            result['actions'] = actions
    has_required_fields = check_required_fields(result, required_fields)
    return result if result and has_required_fields else None