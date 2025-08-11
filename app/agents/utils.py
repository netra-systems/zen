# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:05.517910+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to agent support files
# Git: v6 | 2c55fb99 | dirty (32 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: 3338d1f9-246a-461a-8cae-a81a10615db4 | Seq: 3
# Review: Pending | Score: 85
# ================================
"""Utility functions for agent operations."""

import json
import re
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def extract_json_from_response(response: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks, truncation, and various formatting issues.
    
    Args:
        response: The raw LLM response string
        max_retries: Maximum number of recovery attempts for truncated JSON
        
    Returns:
        Parsed JSON object or None if parsing fails
    """
    if not response:
        return None
    
    # Log large responses for debugging
    if len(response) > 15000:
        logger.debug(f"Attempting to extract JSON from large response: {len(response)} characters")
    
    # Remove markdown code blocks if present
    # Pattern matches ```json ... ``` or ``` ... ```
    pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(pattern, response)
    
    if match:
        # Extract content from code block
        json_str = match.group(1).strip()
    else:
        # Try to parse the response directly
        json_str = response.strip()
    
    # Remove any leading/trailing text before/after JSON
    # This handles cases where the LLM adds explanatory text
    json_str = json_str.strip()
    
    # Try multiple strategies to extract JSON
    strategies = [
        # Strategy 1: Direct parsing
        lambda s: json.loads(s),
        
        # Strategy 2: Find content between first { and last }
        lambda s: json.loads(s[s.find('{'):s.rfind('}') + 1]) if '{' in s and '}' in s else None,
        
        # Strategy 3: Find content between first [ and last ] (for array responses)
        lambda s: json.loads(s[s.find('['):s.rfind(']') + 1]) if '[' in s and ']' in s else None,
        
        # Strategy 4: Remove common prefixes/suffixes and retry
        lambda s: json.loads(re.sub(r'^[^{\[]*|[^}\]]*$', '', s, flags=re.MULTILINE | re.DOTALL)),
        
        # Strategy 5: Try to fix common JSON errors
        lambda s: json.loads(fix_common_json_errors(s)),
        
        # Strategy 6: Handle truncated JSON by attempting recovery
        lambda s: recover_truncated_json(s, max_retries)
    ]
    
    last_error = None
    for i, strategy in enumerate(strategies):
        try:
            result = strategy(json_str)
            if result is not None:
                if i > 2:  # Log if we needed advanced strategies
                    logger.info(f"Successfully extracted JSON using strategy {i+1}")
                return result
        except (json.JSONDecodeError, ValueError, AttributeError, IndexError) as e:
            last_error = e
            continue
    
    # If all strategies fail, log the failure with details
    logger.warning(
        f"Failed to extract JSON from response. "
        f"Response length: {len(response)} chars. "
        f"Last error: {last_error}. "
        f"First 200 chars: {response[:200]}"
    )
    
    return None


def fix_common_json_errors(json_str: str) -> str:
    """
    Attempt to fix common JSON formatting errors.
    
    Args:
        json_str: Potentially malformed JSON string
        
    Returns:
        Fixed JSON string
    """
    # Remove trailing commas before closing brackets/braces
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # Replace single quotes with double quotes (careful with string values)
    # This is a simple approach, may need refinement for complex cases
    json_str = re.sub(r"(?<!\\)'", '"', json_str)
    
    # Remove comments (// and /* */)
    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # Ensure property names are quoted
    # Match unquoted property names and quote them
    json_str = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):', r'\1"\2"\3:', json_str)
    
    # Remove any BOM or zero-width characters
    json_str = json_str.replace('\ufeff', '').replace('\u200b', '')
    
    return json_str


def recover_truncated_json(json_str: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Attempt to recover from truncated JSON by intelligently closing open structures.
    
    Args:
        json_str: Potentially truncated JSON string
        max_retries: Maximum number of recovery attempts
        
    Returns:
        Recovered JSON object or None if recovery fails
    """
    if not json_str:
        return None
    
    # First, try to parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # Clean up the string first
    json_str = fix_common_json_errors(json_str)
    
    for attempt in range(max_retries):
        try:
            # Count open/close brackets and braces
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            
            # Build closing sequence
            closing_sequence = ''
            
            # Handle incomplete string values (look for unclosed quotes)
            if json_str.count('"') % 2 != 0:
                # Find the last quote and check if it's part of an incomplete value
                last_quote_idx = json_str.rfind('"')
                if last_quote_idx > 0:
                    # Check if this is likely an opening quote for a value
                    before_quote = json_str[max(0, last_quote_idx-10):last_quote_idx]
                    if ':' in before_quote or ',' in before_quote:
                        closing_sequence += '"'
            
            # Add missing brackets and braces
            closing_sequence += ']' * (open_brackets - close_brackets)
            closing_sequence += '}' * (open_braces - close_braces)
            
            # Try to parse with closing sequence
            attempted_json = json_str + closing_sequence
            result = json.loads(attempted_json)
            
            logger.info(f"Successfully recovered truncated JSON on attempt {attempt + 1}")
            return result
            
        except json.JSONDecodeError as e:
            # Try more aggressive recovery
            if attempt < max_retries - 1:
                # Remove the last incomplete element
                # Find the last comma and truncate after it
                last_comma = json_str.rfind(',')
                if last_comma > 0:
                    json_str = json_str[:last_comma]
                    # Remove trailing whitespace
                    json_str = json_str.rstrip()
                    continue
            
            logger.debug(f"Recovery attempt {attempt + 1} failed: {e}")
    
    return None


def extract_partial_json(response: str, required_fields: list = None) -> Optional[Dict[str, Any]]:
    """
    Extract partial JSON from response, ensuring required fields are present.
    This is useful when the full response is truncated but we can salvage important parts.
    
    Args:
        response: The raw LLM response string
        required_fields: List of required field names to extract
        
    Returns:
        Partial JSON object with available fields or None
    """
    if not response:
        return None
    
    partial_result = {}
    
    # Define common patterns for extracting key-value pairs
    patterns = [
        # Pattern for quoted keys: "key": "value" or "key": value
        r'"(\w+)"\s*:\s*("[^"]*"|[^,}\]]+)',
        # Pattern for unquoted keys: key: "value" or key: value
        r'(\w+)\s*:\s*("[^"]*"|[^,}\]]+)'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, response)
        for match in matches:
            key = match.group(1)
            value_str = match.group(2).strip()
            
            # Try to parse the value
            try:
                # Remove quotes if present
                if value_str.startswith('"') and value_str.endswith('"'):
                    value = value_str[1:-1]
                else:
                    # Try to parse as JSON (number, boolean, etc.)
                    value = json.loads(value_str)
            except (json.JSONDecodeError, ValueError) as e:
                # Use as string if parsing fails
                logger.debug(f"Failed to parse value as JSON: {e}")
                value = value_str
            
            partial_result[key] = value
    
    # Check if we have required fields
    if required_fields:
        if not all(field in partial_result for field in required_fields):
            logger.warning(f"Partial extraction missing required fields. Found: {list(partial_result.keys())}")
            return None
    
    return partial_result if partial_result else None