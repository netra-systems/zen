"""Utility functions for agent operations."""

import json
import re
from typing import Any, Dict, Optional


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks.
    
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
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # If direct parsing fails, try to find JSON-like content
        # Look for content between first { and last }
        start_idx = json_str.find('{')
        end_idx = json_str.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            try:
                json_content = json_str[start_idx:end_idx + 1]
                return json.loads(json_content)
            except json.JSONDecodeError:
                pass
    
    return None