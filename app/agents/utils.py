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
from typing import Any, Dict, Optional, Union
from app.logging_config import central_logger as logger



def preprocess_llm_response(response: str) -> str:
    """
    Preprocess LLM response to improve JSON extraction success rate.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Preprocessed response
    """
    if not response:
        return response
    
    # Remove common LLM artifacts that break JSON parsing
    processed = response
    
    # Remove any text before the first { or [
    json_start = -1
    brace_pos = processed.find('{')
    bracket_pos = processed.find('[')
    
    if brace_pos >= 0 and bracket_pos >= 0:
        json_start = min(brace_pos, bracket_pos)
    elif brace_pos >= 0:
        json_start = brace_pos
    elif bracket_pos >= 0:
        json_start = bracket_pos
    
    if json_start > 0:
        # Check if there's explanatory text before the JSON
        before_json = processed[:json_start]
        if not '```' in before_json:  # Don't remove markdown markers
            processed = processed[json_start:]
    
    # Remove any text after the last } or ]
    json_end = -1
    brace_pos = processed.rfind('}')
    bracket_pos = processed.rfind(']')
    
    if brace_pos >= 0 and bracket_pos >= 0:
        json_end = max(brace_pos, bracket_pos)
    elif brace_pos >= 0:
        json_end = brace_pos
    elif bracket_pos >= 0:
        json_end = bracket_pos
    
    if json_end >= 0 and json_end < len(processed) - 1:
        # Check if there's explanatory text after the JSON
        after_json = processed[json_end + 1:]
        if not '```' in after_json:  # Don't remove markdown markers
            processed = processed[:json_end + 1]
    
    return processed

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
    
    # Preprocess the response first
    response = preprocess_llm_response(response)
    
    # Log large responses for debugging
    if len(response) > 15000:
        logger.debug(f"Attempting to extract JSON from large response: {len(response)} characters")
    
    # Remove markdown code blocks if present
    # Pattern matches ```json ... ``` or ``` ... ```
    pattern = r'```(?:json)?\s*([\s\S]*?)(?:\s*```|$)'
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
        
        # Strategy 2: Try to fix common JSON errors first (moved up in priority)
        lambda s: json.loads(fix_common_json_errors(s)),
        
        # Strategy 3: Find content between first { and last }
        lambda s: json.loads(s[s.find('{'):s.rfind('}') + 1]) if '{' in s and '}' in s else None,
        
        # Strategy 4: Find content between first [ and last ] (for array responses)
        lambda s: json.loads(s[s.find('['):s.rfind(']') + 1]) if '[' in s and ']' in s and '{' not in s else None,
        
        # Strategy 5: Remove common prefixes/suffixes and retry
        lambda s: json.loads(re.sub(r'^[^{\[]*|[^}\]]*$', '', s, flags=re.MULTILINE | re.DOTALL)),
        
        # Strategy 6: Handle truncated JSON by attempting recovery
        lambda s: recover_truncated_json(s, max_retries)
    ]
    
    last_error = None
    for i, strategy in enumerate(strategies):
        try:
            result = strategy(json_str)
            if result is not None:
                if i > 0:  # Log which strategy succeeded
                    logger.debug(f"Successfully extracted JSON using strategy {i+1}")
                    if i == 1:  # Strategy 2: fix_common_json_errors
                        logger.info(f"JSON extraction required error fixing (strategy 2) for response of {len(response)} chars")
                return result
        except (json.JSONDecodeError, ValueError, AttributeError, IndexError) as e:
            if i == 0 and isinstance(e, json.JSONDecodeError):
                # Log the specific error from direct parsing
                logger.debug(f"Direct JSON parsing failed: {e.msg} at line {e.lineno} col {e.colno} (char {e.pos})")
            last_error = e
            continue
    
    # If all strategies fail, check if partial extraction might work
    # Before logging as a complete failure
    partial = extract_partial_json(response)
    if partial and len(partial) > 5:  # If we can extract meaningful partial data
        logger.debug(
            f"Full JSON extraction failed but partial extraction available. "
            f"Response length: {len(response)} chars. "
            f"Last error: {last_error}. "
        )
    else:
        # Only log as warning if both full and partial extraction fail
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
    
    # Fix missing commas between elements (common in large generated JSON)
    # Be more careful to avoid breaking valid JSON
    
    # Split into lines for better control
    lines = json_str.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if this line ends a JSON value and the next line starts a new key
        if i < len(lines) - 1:
            current_line = line.rstrip()
            next_line = lines[i + 1].lstrip()
            
            # Check various patterns for missing commas
            needs_comma = False
            
            # Pattern 1: Line ends with } or ] and next line has a key
            if (current_line.endswith('}') or current_line.endswith(']')) and next_line.startswith('"') and ':' in next_line:
                needs_comma = True
            
            # Pattern 2: Line ends with a string value and next line has a key
            elif current_line.endswith('"') and next_line.startswith('"') and ':' in next_line:
                needs_comma = True
            
            # Pattern 3: Line ends with number/boolean and next line has a key
            elif (re.search(r'(\d|true|false|null)$', current_line) and 
                  next_line.startswith('"') and ':' in next_line):
                needs_comma = True
            
            if needs_comma and not current_line.endswith(','):
                current_line = current_line + ','
                fixed_lines.append(current_line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    json_str = '\n'.join(fixed_lines)
    
    # Replace single quotes with double quotes (careful with string values)
    # This is a simple approach, may need refinement for complex cases
    json_str = re.sub(r"(?<!\\)'", '"', json_str)
    
    # Remove comments (// and /* */)
    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # Fix unescaped quotes inside string values - improved approach
    # Look for patterns like: "key": "value with "quotes" inside"
    # We need to be careful not to break valid JSON
    
    # First pass: Handle obvious cases where quotes appear within string values
    # Pattern: "key": "..."word"..." -> "key": "...\"word\"..."
    lines = json_str.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check if line contains a key-value pair with potential unescaped quotes
        if ':' in line and line.count('"') > 4:
            # Try to identify the key and value boundaries
            colon_idx = line.find(':')
            if colon_idx > 0:
                # Find the value part after the colon
                value_part = line[colon_idx + 1:].strip()
                if value_part.startswith('"'):
                    # Find the real end of the value (should be before comma or end of line)
                    # Count quotes to detect unescaped ones
                    quote_positions = [i for i, c in enumerate(value_part) if c == '"']
                    if len(quote_positions) > 2:
                        # There might be unescaped quotes
                        # Keep first and last, escape the middle ones
                        new_value_part = value_part
                        for i in range(1, len(quote_positions) - 1):
                            pos = quote_positions[i]
                            if pos > 0 and new_value_part[pos - 1] != '\\':
                                # This quote is not escaped, escape it
                                new_value_part = new_value_part[:pos] + '\\' + new_value_part[pos:]
                                # Adjust positions for the added backslash
                                quote_positions = [p + 1 if p > pos else p for p in quote_positions]
                        
                        line = line[:colon_idx + 1] + ' ' + new_value_part
        
        fixed_lines.append(line)
    
    json_str = '\n'.join(fixed_lines)
    
    # Ensure property names are quoted (but be careful not to quote already quoted names)
    # Match unquoted property names and quote them
    json_str = re.sub(r'(?<!["\w])(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):', r'\1"\2"\3:', json_str)
    
    # Remove any BOM or zero-width characters
    json_str = json_str.replace('\ufeff', '').replace('\u200b', '')
    
    # Fix truncated strings - if we have an odd number of quotes, close the last one
    quote_count = json_str.count('"') - json_str.count('\\"')
    if quote_count % 2 != 0:
        # Find the last unescaped quote
        last_quote_idx = json_str.rfind('"')
        if last_quote_idx > 0 and json_str[last_quote_idx - 1] != '\\':
            # Check if we're in a value context (after a colon)
            before_quote = json_str[max(0, last_quote_idx - 50):last_quote_idx]
            if ':' in before_quote:
                # We're likely in a value, close it
                json_str = json_str[:last_quote_idx + 1] + '"'
    
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
    except json.JSONDecodeError as initial_error:
        logger.debug(f"Initial parse failed: {initial_error}")
    
    # Clean up the string first
    json_str = fix_common_json_errors(json_str)
    
    # Try again after cleanup
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    for attempt in range(max_retries):
        try:
            # Create a working copy
            working_str = json_str
            
            # Count open/close brackets and braces
            open_braces = working_str.count('{')
            close_braces = working_str.count('}')
            open_brackets = working_str.count('[')
            close_brackets = working_str.count(']')
            
            # Build closing sequence
            closing_sequence = ''
            
            # Handle incomplete string values (look for unclosed quotes)
            quote_count = working_str.count('"') - working_str.count('\\"')
            if quote_count % 2 != 0:
                # Find the last unescaped quote
                last_quote_idx = working_str.rfind('"')
                if last_quote_idx > 0 and (last_quote_idx == 0 or working_str[last_quote_idx - 1] != '\\'):
                    # Check if this is likely an opening quote for a value
                    before_quote = working_str[max(0, last_quote_idx-50):last_quote_idx]
                    if ':' in before_quote:
                        closing_sequence += '"'
            
            # Close any incomplete arrays or objects
            # Check if we're in the middle of an array or object
            last_open_bracket = working_str.rfind('[')
            last_close_bracket = working_str.rfind(']')
            last_open_brace = working_str.rfind('{')
            last_close_brace = working_str.rfind('}')
            
            # If the last structural character is an opening one, we might need to close an element
            if last_open_bracket > max(last_close_bracket, last_open_brace, last_close_brace):
                # We're in an array, might need to close current element
                if working_str.rstrip().endswith(','):
                    # Remove trailing comma
                    working_str = working_str.rstrip()[:-1]
            elif last_open_brace > max(last_close_brace, last_open_bracket, last_close_bracket):
                # We're in an object, might need to close current element
                if working_str.rstrip().endswith(','):
                    # Remove trailing comma
                    working_str = working_str.rstrip()[:-1]
            
            # Add missing brackets and braces
            closing_sequence += ']' * (open_brackets - close_brackets)
            closing_sequence += '}' * (open_braces - close_braces)
            
            # Try to parse with closing sequence
            attempted_json = working_str + closing_sequence
            result = json.loads(attempted_json)
            
            logger.info(f"Successfully recovered truncated JSON on attempt {attempt + 1} with closing: {closing_sequence}")
            return result
            
        except json.JSONDecodeError as e:
            # Log the specific error for debugging
            logger.debug(f"Recovery attempt {attempt + 1} failed at position {e.pos}: {e.msg}")
            
            # Try more aggressive recovery
            if attempt < max_retries - 1:
                # Strategy 1: Remove the last incomplete element
                last_comma = json_str.rfind(',')
                if last_comma > 0:
                    # Check what comes after the comma
                    after_comma = json_str[last_comma + 1:].strip()
                    
                    # If it looks like an incomplete element, remove it
                    if after_comma and not after_comma.startswith('}') and not after_comma.startswith(']'):
                        json_str = json_str[:last_comma]
                        json_str = json_str.rstrip()
                        continue
                
                # Strategy 2: Truncate at the error position if it's near the end
                if e.pos and e.pos > len(json_str) * 0.8:  # Error in last 20% of string
                    json_str = json_str[:e.pos].rstrip()
                    # Remove any trailing incomplete elements
                    if json_str.endswith(','):
                        json_str = json_str[:-1]
                    continue
    
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
    
    # First, try to extract complete JSON objects/arrays for complex fields
    complex_patterns = [
        # Extract complete arrays: "key": [...]
        (r'"([^"]+)"\s*:\s*(\[[^\]]*\])', 'array'),
        # Extract complete objects: "key": {...}
        (r'"([^"]+)"\s*:\s*({[^}]*})', 'object'),
    ]
    
    for pattern, field_type in complex_patterns:
        matches = re.finditer(pattern, response, re.DOTALL)
        for match in matches:
            key = match.group(1)
            value_str = match.group(2)
            
            # Try to parse the complex value
            try:
                value = json.loads(value_str)
                partial_result[key] = value
            except json.JSONDecodeError:
                # Try to fix and parse again
                try:
                    fixed_value = fix_common_json_errors(value_str)
                    value = json.loads(fixed_value)
                    partial_result[key] = value
                except:
                    # If it fails, try to extract as string
                    partial_result[key] = value_str
    
    # Define patterns for simple key-value pairs
    simple_patterns = [
        # Pattern for quoted keys with string values: "key": "value"
        r'"([^"]+)"\s*:\s*"([^"]*?)"(?=[,}\]]|\s*")',
        # Pattern for quoted keys with numeric/boolean values: "key": 123 or "key": true
        r'"([^"]+)"\s*:\s*(\d+\.?\d*|true|false|null)(?=[,}\]]|\s)',
        # Pattern for unquoted keys (fallback): key: "value" or key: value
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*("[^"]*"|[^,}\]\s]+)'
    ]
    
    for pattern in simple_patterns:
        matches = re.finditer(pattern, response)
        for match in matches:
            key = match.group(1)
            value_str = match.group(2).strip()
            
            # Skip if we already have this key from complex patterns
            if key in partial_result:
                continue
            
            # Try to parse the value
            try:
                # Remove quotes if present
                if value_str.startswith('"') and value_str.endswith('"'):
                    value = value_str[1:-1]
                elif value_str in ['true', 'false', 'null']:
                    value = json.loads(value_str)
                elif re.match(r'^\d+\.?\d*$', value_str):
                    # It's a number
                    value = json.loads(value_str)
                else:
                    # Use as string
                    value = value_str
            except (json.JSONDecodeError, ValueError) as e:
                # Use as string if parsing fails
                logger.debug(f"Failed to parse value for key '{key}': {e}")
                value = value_str
            
            partial_result[key] = value
    
    # Special handling for specific known fields that might be truncated
    if 'actions' not in partial_result or not isinstance(partial_result.get('actions'), list):
        # Try to extract actions array even if truncated
        actions_match = re.search(r'"actions"\s*:\s*\[([^\]]*)', response, re.DOTALL)
        if actions_match:
            actions_str = '[' + actions_match.group(1)
            # Try to close the array and parse
            try:
                # Count open/close braces in the actions string
                open_braces = actions_str.count('{')
                close_braces = actions_str.count('}')
                
                # Close any open objects
                if open_braces > close_braces:
                    actions_str += '}' * (open_braces - close_braces)
                
                # Close the array
                if not actions_str.rstrip().endswith(']'):
                    actions_str += ']'
                
                actions = json.loads(fix_common_json_errors(actions_str))
                if isinstance(actions, list):
                    partial_result['actions'] = actions
            except:
                # If we can't parse it, at least indicate we tried
                partial_result['actions'] = []
    
    # Check if we have required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in partial_result]
        if missing_fields:
            logger.warning(f"Partial extraction missing required fields: {missing_fields}. Found: {list(partial_result.keys())}")
            # Don't return None, return what we have
    
    return partial_result if partial_result else None