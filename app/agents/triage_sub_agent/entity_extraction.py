# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from triage_sub_agent_legacy.py - Entity extraction (8-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 5
# Review: Pending | Score: 95
# ================================
"""Entity extraction utilities - compliant with 8-line limit."""

import re
from typing import List, Dict, Any
from app.agents.triage_sub_agent.models import ExtractedEntities


def get_model_patterns() -> List[str]:
    """Get patterns for AI model detection."""
    return [
        r'gpt-?[0-9]+\.?[0-9]*(?:-?turbo)?',
        r'claude-?[0-9]+(?:-[a-z]+)?',
        r'llama-?[0-9]+(?:b)?(?:-[a-z]+)?',
        r'mistral', r'gemini(?:-[a-z]+)?',
        r'anthropic', r'openai', r'palm-?[0-9]*'
    ]


def extract_models(request: str, entities: ExtractedEntities) -> None:
    """Extract model names from request."""
    request_lower = request.lower()
    for pattern in get_model_patterns():
        matches = re.findall(pattern, request_lower)
        entities.models_mentioned.extend(matches)


def get_metric_keywords() -> List[str]:
    """Get keywords for metric detection."""
    return ['latency', 'throughput', 'cost', 'accuracy', 'error',
            'response time', 'tokens', 'requests per second', 'rps', 'memory']


def extract_metrics(request: str, entities: ExtractedEntities) -> None:
    """Extract metrics from request."""
    request_lower = request.lower()
    for keyword in get_metric_keywords():
        if keyword in request_lower:
            entities.metrics_mentioned.append(keyword)


def classify_number(num: str, context: str) -> Dict[str, str]:
    """Classify a numerical value based on context."""
    if _is_time_type(num, context):
        return {"type": "time", "value": num}
    elif _is_percentage_type(num, context):
        return {"type": "percentage", "value": _format_percentage(num)}
    return _classify_token_rate_or_numeric(num, context)


def _classify_token_rate_or_numeric(num: str, context: str) -> Dict[str, str]:
    """Classify as token, rate, or numeric type."""
    if _is_token_type(context):
        return {"type": "tokens", "value": num}
    elif _is_rate_type(context):
        return {"type": "rate", "value": num}
    return _create_numeric_type(num)


def _is_time_type(num: str, context: str) -> bool:
    """Check if number represents time value."""
    return 'ms' in context[:10] or num.endswith(('ms', 's'))


def _is_percentage_type(num: str, context: str) -> bool:
    """Check if number represents percentage."""
    return '%' in context[:5] or num.endswith('%')


def _format_percentage(num: str) -> str:
    """Format percentage value correctly."""
    return num if num.endswith('%') else num + '%'


def _is_token_type(context: str) -> bool:
    """Check if number represents tokens."""
    return 'token' in context[:20].lower()


def _is_rate_type(context: str) -> bool:
    """Check if number represents rate."""
    return 'RPS' in context[:10] or 'requests' in context[:20].lower()


def _create_numeric_type(num: str) -> Dict[str, str]:
    """Create generic numeric type classification."""
    return {"type": "numeric", "value": num}


def extract_numbers(request: str, entities: ExtractedEntities) -> None:
    """Extract numerical values as thresholds/targets."""
    pattern = r'\b\d+(?:\.\d+)?(?:\s*(?:ms|s|%|tokens?|requests?|RPS|USD|dollars?))?'
    numbers = re.findall(pattern, request)
    for num in numbers:
        context = request[request.find(num):]
        classified = classify_number(num, context)
        if classified["type"] in ["time", "tokens", "rate"]:
            entities.thresholds.append(classified)
        elif classified["type"] == "percentage":
            entities.targets.append(classified)


def get_time_patterns() -> List[str]:
    """Get patterns for time range detection."""
    return [
        r'last\s+(\d+)\s+(hours?|days?|weeks?|months?)',
        r'past\s+(\d+)\s+(hours?|days?|weeks?|months?)',
        r'(\d{4}-\d{2}-\d{2})',
        r'today|yesterday|this\s+week|last\s+week'
    ]


def extract_time_ranges(request: str, entities: ExtractedEntities) -> None:
    """Extract time ranges from request."""
    request_lower = request.lower()
    for pattern in get_time_patterns():
        matches = re.findall(pattern, request_lower)
        for match in matches:
            entities.time_ranges.append({"pattern": match})


def extract_entities_from_request(request: str) -> ExtractedEntities:
    """Extract all entities from user request."""
    entities = ExtractedEntities()
    extract_models(request, entities)
    extract_metrics(request, entities)
    extract_numbers(request, entities)
    extract_time_ranges(request, entities)
    return entities