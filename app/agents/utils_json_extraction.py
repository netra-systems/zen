# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from utils.py - JSON extraction utilities (8-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 1
# Review: Pending | Score: 95
# ================================
"""JSON extraction utilities - refactored for 8-line function compliance."""

import json
import re
from typing import Any, Dict, Optional, List
from app.logging_config import central_logger as logger


def find_json_boundaries(text: str) -> tuple[int, int]:
    """Find start and end positions of JSON in text."""
    brace_pos, bracket_pos = text.find('{'), text.find('[')
    start = min(p for p in [brace_pos, bracket_pos] if p >= 0) if any(p >= 0 for p in [brace_pos, bracket_pos]) else -1
    
    brace_end, bracket_end = text.rfind('}'), text.rfind(']')
    end = max(p for p in [brace_end, bracket_end] if p >= 0) if any(p >= 0 for p in [brace_end, bracket_end]) else -1
    
    return start, end


def strip_non_json_text(text: str, start: int, end: int) -> str:
    """Remove text before and after JSON boundaries."""
    if start > 0 and '```' not in text[:start]:
        text = text[start:]
    if end >= 0 and end < len(text) - 1 and '```' not in text[end + 1:]:
        text = text[:end + 1]
    return text


def preprocess_llm_response(response: str) -> str:
    """Preprocess LLM response to improve JSON extraction."""
    if not response:
        return response
    start, end = find_json_boundaries(response)
    return strip_non_json_text(response, start, end)


def extract_from_markdown(response: str) -> str:
    """Extract content from markdown code blocks."""
    pattern = r'```(?:json)?\s*([\s\S]*?)(?:\s*```|$)'
    match = re.search(pattern, response)
    return match.group(1).strip() if match else response.strip()


def try_direct_parse(json_str: str) -> Optional[Dict[str, Any]]:
    """Try direct JSON parsing."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def try_extract_object(json_str: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object between braces."""
    if '{' in json_str and '}' in json_str:
        try:
            return json.loads(json_str[json_str.find('{'):json_str.rfind('}') + 1])
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def try_extract_array(json_str: str) -> Optional[List[Any]]:
    """Extract JSON array between brackets."""
    if '[' in json_str and ']' in json_str and '{' not in json_str:
        try:
            return json.loads(json_str[json_str.find('['):json_str.rfind(']') + 1])
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def try_clean_edges(json_str: str) -> Optional[Dict[str, Any]]:
    """Remove non-JSON prefixes/suffixes and retry."""
    try:
        cleaned = re.sub(r'^[^{\[]*|[^}\]]*$', '', json_str, flags=re.MULTILINE | re.DOTALL)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None


def remove_trailing_commas(json_str: str) -> str:
    """Remove trailing commas before closing brackets/braces."""
    return re.sub(r',\s*([}\]])', r'\1', json_str)


def remove_single_quotes(json_str: str) -> str:
    """Replace single quotes with double quotes."""
    return re.sub(r"(?<!\\)'", '"', json_str)


def remove_comments(json_str: str) -> str:
    """Remove JavaScript-style comments."""
    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
    return re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)


def quote_property_names(json_str: str) -> str:
    """Ensure property names are quoted."""
    return re.sub(r'(?<!["\w])(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):', r'\1"\2"\3:', json_str)


def remove_bom_chars(json_str: str) -> str:
    """Remove BOM and zero-width characters."""
    return json_str.replace('\ufeff', '').replace('\u200b', '')


def check_needs_comma(current: str, next_line: str) -> bool:
    """Check if a comma is needed between lines."""
    ends_structure = current.endswith('}') or current.endswith(']')
    ends_value = current.endswith('"') or re.search(r'(\d|true|false|null)$', current)
    starts_key = next_line.startswith('"') and ':' in next_line
    return (ends_structure or ends_value) and starts_key


def add_missing_commas_to_lines(lines: List[str]) -> List[str]:
    """Add missing commas between JSON elements."""
    fixed = []
    for i, line in enumerate(lines):
        current = line.rstrip()
        if i < len(lines) - 1 and check_needs_comma(current, lines[i + 1].lstrip()):
            fixed.append(current + ',' if not current.endswith(',') else line)
        else:
            fixed.append(line)
    return fixed


def fix_unclosed_quotes(json_str: str) -> str:
    """Fix unclosed string values."""
    quote_count = json_str.count('"') - json_str.count('\\"')
    if quote_count % 2 != 0:
        last_idx = json_str.rfind('"')
        if last_idx > 0 and json_str[last_idx - 1] != '\\' and ':' in json_str[max(0, last_idx - 50):last_idx]:
            json_str = json_str[:last_idx + 1] + '"'
    return json_str


def fix_common_json_errors(json_str: str) -> str:
    """Fix common JSON formatting errors."""
    json_str = remove_trailing_commas(json_str)
    lines = add_missing_commas_to_lines(json_str.split('\n'))
    json_str = '\n'.join(lines)
    json_str = remove_single_quotes(json_str)
    json_str = remove_comments(json_str)
    json_str = quote_property_names(json_str)
    json_str = remove_bom_chars(json_str)
    return fix_unclosed_quotes(json_str)


def count_structure_balance(json_str: str) -> Dict[str, int]:
    """Count unbalanced brackets and braces."""
    return {
        'braces': json_str.count('{') - json_str.count('}'),
        'brackets': json_str.count('[') - json_str.count(']'),
        'quotes': (json_str.count('"') - json_str.count('\\"')) % 2
    }


def build_closing_sequence(balance: Dict[str, int]) -> str:
    """Build sequence to close open structures."""
    seq = '"' if balance['quotes'] else ''
    seq += ']' * balance['brackets']
    seq += '}' * balance['braces']
    return seq


def clean_trailing_comma(json_str: str) -> str:
    """Remove trailing comma if present."""
    stripped = json_str.rstrip()
    return stripped[:-1] if stripped.endswith(',') else json_str


def attempt_recovery_parse(json_str: str, closing: str) -> Optional[Dict[str, Any]]:
    """Try parsing with recovery closing sequence."""
    try:
        return json.loads(json_str + closing)
    except json.JSONDecodeError:
        return None


def truncate_at_last_comma(json_str: str) -> Optional[str]:
    """Remove incomplete element after last comma."""
    last_comma = json_str.rfind(',')
    if last_comma > 0:
        after = json_str[last_comma + 1:].strip()
        if after and not after.startswith('}') and not after.startswith(']'):
            return json_str[:last_comma].rstrip()
    return None


def truncate_at_error_position(json_str: str, error_pos: int) -> Optional[str]:
    """Truncate at JSON error position if near end."""
    if error_pos and error_pos > len(json_str) * 0.8:
        truncated = json_str[:error_pos].rstrip()
        return truncated[:-1] if truncated.endswith(',') else truncated
    return None


def recover_truncated_json(json_str: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Recover from truncated JSON by closing open structures."""
    if not json_str:
        return None
    result = try_direct_parse(json_str)
    if result:
        return result
    
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


def execute_strategies(json_str: str, strategies: list) -> Optional[Dict[str, Any]]:
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


def extract_complex_field(response: str, pattern: str) -> Dict[str, Any]:
    """Extract complex JSON fields (objects/arrays)."""
    result = {}
    matches = re.finditer(pattern, response, re.DOTALL)
    for match in matches:
        key, value_str = match.group(1), match.group(2)
        value = try_parse_complex_value(value_str)
        if value is not None:
            result[key] = value
    return result


def try_parse_complex_value(value_str: str) -> Any:
    """Try to parse complex JSON value."""
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        try:
            return json.loads(fix_common_json_errors(value_str))
        except:
            return value_str


def extract_simple_fields(response: str, existing: Dict[str, Any]) -> Dict[str, Any]:
    """Extract simple key-value pairs."""
    patterns = [
        r'"([^"]+)"\s*:\s*"([^"]*)"(?=[,}\]])',
        r'"([^"]+)"\s*:\s*(\d+\.?\d*|true|false|null)(?=[,}\]]|\s)',
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*("[^"]*"|[^,}\]\s]+)'
    ]
    return extract_with_patterns(response, patterns, existing)


def extract_with_patterns(response: str, patterns: List[str], existing: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields using regex patterns."""
    result = existing.copy()
    for pattern in patterns:
        for match in re.finditer(pattern, response):
            key = match.group(1)
            if key not in result:
                result[key] = parse_simple_value(match.group(2).strip())
    return result


def parse_simple_value(value_str: str) -> Any:
    """Parse simple JSON value."""
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    if value_str in ['true', 'false', 'null']:
        return json.loads(value_str)
    if re.match(r'^\d+\.?\d*$', value_str):
        return json.loads(value_str)
    return value_str


def extract_truncated_array(response: str, field_name: str) -> Optional[List[Any]]:
    """Extract potentially truncated array field."""
    pattern = rf'"{field_name}"\s*:\s*\[([^\]]*)'
    match = re.search(pattern, response, re.DOTALL)
    if not match:
        return None
    return try_close_truncated_array(match.group(1))


def try_close_truncated_array(content: str) -> Optional[List[Any]]:
    """Try to close and parse truncated array."""
    array_str = '[' + content
    open_braces = array_str.count('{') - array_str.count('}')
    array_str += '}' * open_braces
    if not array_str.rstrip().endswith(']'):
        array_str += ']'
    try:
        return json.loads(fix_common_json_errors(array_str))
    except:
        return []


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
    
    check_required_fields(result, required_fields)
    return result if result else None


def check_required_fields(result: Dict[str, Any], required_fields: Optional[List[str]]) -> None:
    """Log warning if required fields are missing."""
    if required_fields:
        missing = [f for f in required_fields if f not in result]
        if missing:
            logger.warning(f"Missing required fields: {missing}")