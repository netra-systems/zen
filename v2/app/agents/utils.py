"""Utility functions for agent operations."""

import json
import re
from typing import Any, Dict, Optional


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks and various formatting issues.
    
    Args:
        response: The raw LLM response string
        
    Returns:
        Parsed JSON object or None if parsing fails
    """
    if not response:
        return None
    
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
        lambda s: json.loads(fix_common_json_errors(s))
    ]
    
    for strategy in strategies:
        try:
            result = strategy(json_str)
            if result is not None:
                return result
        except (json.JSONDecodeError, ValueError, AttributeError, IndexError):
            continue
    
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