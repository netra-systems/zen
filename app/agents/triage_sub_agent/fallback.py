# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from triage_sub_agent_legacy.py - Fallback categorization (8-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 9
# Review: Pending | Score: 95
# ================================
"""Fallback categorization utilities - compliant with 8-line limit."""

from typing import Dict
from app.agents.triage_sub_agent.models import (
    TriageResult, Priority, Complexity, TriageMetadata
)
from app.agents.triage_sub_agent.entity_extraction import extract_entities_from_request
from app.agents.triage_sub_agent.intent_detection import determine_intent
from app.agents.triage_sub_agent.tool_recommendation import recommend_tools


def get_fallback_categories() -> Dict[str, str]:
    """Get fallback category mappings."""
    return {
        "optimize": "Cost Optimization",
        "performance": "Performance Optimization",
        "analyze": "Workload Analysis",
        "configure": "Configuration & Settings",
        "report": "Monitoring & Reporting",
        "model": "Model Selection",
        "supply": "Supply Catalog Management",
        "quality": "Quality Optimization"
    }


def find_best_category(request_lower: str) -> str:
    """Find best matching category from keywords."""
    for keyword, category in get_fallback_categories().items():
        if keyword in request_lower:
            return category
    return "General Inquiry"


def create_fallback_metadata() -> TriageMetadata:
    """Create metadata for fallback result."""
    return TriageMetadata(
        triage_duration_ms=0,
        fallback_used=True,
        retry_count=0
    )


def fallback_categorization(request: str) -> TriageResult:
    """Simple fallback categorization when LLM fails."""
    category = find_best_category(request.lower())
    entities = extract_entities_from_request(request)
    intent = determine_intent(request)
    
    return TriageResult(
        category=category,
        confidence_score=0.5,
        priority=Priority.MEDIUM,
        complexity=Complexity.MODERATE,
        extracted_entities=entities,
        user_intent=intent,
        tool_recommendations=recommend_tools(category, entities),
        metadata=create_fallback_metadata()
    )