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

# Import the backward compatibility class from agent.py
from netra_backend.app.agents.triage_sub_agent.agent import (
    TriageSubAgent,
    create_triage_agent
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
    "TriageSubAgent",  # Added for backward compatibility
    "create_triage_agent",  # Added for backward compatibility
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