"""
Triage Sub-Agent Module

Backward compatibility module for existing tests and imports.
This module provides access to the SSOT triage functionality.

Following SSOT principles, this module imports from the unified triage agent
instead of duplicating functionality.
"""

from typing import Any, Dict, List, Optional
from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent,
    UnifiedTriageAgentFactory,
    TriageConfig
)

# Import models from the SSOT location
from netra_backend.app.agents.triage.models import (
    Priority,
    Complexity,
    ExtractedEntities,
    UserIntent,
    ToolRecommendation,
    TriageResult,
    TriageMetadata,
    KeyParameters,
    SuggestedWorkflow
)

# Export for backward compatibility
__all__ = [
    "UnifiedTriageAgent",
    "UnifiedTriageAgentFactory", 
    "TriageConfig",
    "Priority",
    "Complexity",
    "ExtractedEntities",
    "UserIntent",
    "ToolRecommendation",
    "TriageResult",
    "TriageMetadata",
    "KeyParameters",
    "SuggestedWorkflow"
]