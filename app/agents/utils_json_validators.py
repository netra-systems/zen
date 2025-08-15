# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4.1 claude-sonnet-4-20250514
# Context: JSON validation and error fixing functions - split from utils_json_extraction.py (300-line compliance)
# Git: anthony-aug-13-2 | clean
# Change: Refactor | Scope: Component | Risk: Low
# Session: architecture-compliance | Seq: 2
# Review: Pending | Score: 95
# ================================
"""JSON validation and error fixing utilities - focused on validation operations."""

import json
import re
from typing import Any, Dict, Optional, List
from app.logging_config import central_logger as logger


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
        if last_idx > 0 and json_str[last_idx - 1] != '\\':
            if ':' in json_str[max(0, last_idx - 50):last_idx]:
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


def check_required_fields(result: Dict[str, Any], required_fields: Optional[List[str]]) -> bool:
    """Check if all required fields are present."""
    if required_fields:
        missing = [f for f in required_fields if f not in result]
        if missing:
            logger.warning(f"Missing required fields: {missing}")
            return False
    return True


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