"""Triage Sub Agent Module

Enhanced triage agent with advanced categorization and caching capabilities.
This module provides comprehensive request analysis, entity extraction, and intelligent routing.
"""

from netra_backend.app.agents.triage_sub_agent.core import TriageCore
from netra_backend.app.agents.triage_sub_agent.entity_extractor import EntityExtractor
from netra_backend.app.agents.triage_sub_agent.intent_detector import IntentDetector
from netra_backend.app.agents.triage_sub_agent.models import (
    Complexity,
    ExtractedEntities,
    KeyParameters,
    Priority,
    SuggestedWorkflow,
    ToolRecommendation,
    TriageMetadata,
    TriageResult,
    UserIntent,
    ValidationStatus,
)
from netra_backend.app.agents.triage_sub_agent.tool_recommender import ToolRecommender
from netra_backend.app.agents.triage_sub_agent.validator import RequestValidator

# Note: TriageSubAgent is imported directly where needed to avoid circular imports
# Preferred: from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent

# Import TriageSubAgent for convenience - avoid if circular imports occur
try:
    from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
    __all__ = [
        "Priority",
        "Complexity",
        "KeyParameters",
        "ExtractedEntities",
        "UserIntent",
        "SuggestedWorkflow",
        "ToolRecommendation",
        "ValidationStatus",
        "TriageMetadata",
        "TriageResult",
        "EntityExtractor",
        "RequestValidator",
        "IntentDetector",
        "ToolRecommender",
        "TriageCore",
        "TriageSubAgent"
    ]
except ImportError:
    # Fall back to original list if circular import occurs
    __all__ = [
        "Priority",
        "Complexity",
        "KeyParameters",
        "ExtractedEntities",
        "UserIntent",
        "SuggestedWorkflow",
        "ToolRecommendation",
        "ValidationStatus",
        "TriageMetadata",
        "TriageResult",
        "EntityExtractor",
        "RequestValidator",
        "IntentDetector",
        "ToolRecommender",
        "TriageCore"
    ]