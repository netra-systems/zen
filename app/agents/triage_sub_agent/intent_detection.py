# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from triage_sub_agent_legacy.py - Intent detection (8-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 6
# Review: Pending | Score: 95
# ================================
"""Intent detection utilities - compliant with 8-line limit."""

from typing import Dict, List
from app.agents.triage_sub_agent.models import UserIntent


def get_intent_keywords() -> Dict[str, List[str]]:
    """Get mapping of intents to keywords."""
    return {
        "analyze": ["analyze", "analysis", "examine", "investigate", "understand"],
        "optimize": ["optimize", "improve", "enhance", "reduce", "increase"],
        "configure": ["configure", "set", "update", "change", "modify"],
        "report": ["report", "show", "display", "visualize", "dashboard"],
        "troubleshoot": ["fix", "debug", "troubleshoot", "resolve", "issue"],
        "compare": ["compare", "versus", "vs", "difference", "better"],
        "predict": ["predict", "forecast", "estimate", "project"],
        "recommend": ["recommend", "suggest", "advise", "best"]
    }


def detect_admin_mode(request: str) -> bool:
    """Detect if request is for admin operations."""
    admin_keywords = [
        "admin", "administrator", "corpus", "synthetic data",
        "generate data", "manage corpus", "create corpus",
        "delete corpus", "export corpus", "import corpus"
    ]
    return any(keyword in request.lower() for keyword in admin_keywords)


def find_matching_intents(request_lower: str) -> List[str]:
    """Find all matching intents in request."""
    found = []
    for intent, keywords in get_intent_keywords().items():
        if any(keyword in request_lower for keyword in keywords):
            found.append(intent)
    return found


def check_action_required(intents: List[str]) -> bool:
    """Check if any intent requires action."""
    action_intents = ["optimize", "configure", "troubleshoot"]
    return any(intent in action_intents for intent in intents)


def determine_intent(request: str) -> UserIntent:
    """Determine user intent from request."""
    request_lower = request.lower()
    found_intents = find_matching_intents(request_lower)
    
    primary = found_intents[0] if found_intents else "analyze"
    secondary = found_intents[1:] if len(found_intents) > 1 else []
    action_required = check_action_required(found_intents)
    
    return UserIntent(
        primary_intent=primary,
        secondary_intents=secondary,
        action_required=action_required
    )