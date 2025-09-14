"""
Tool Recommender Module - Backward Compatibility for ToolDiscoverySubAgent

This module provides backward compatibility for tests that expect a ToolRecommender class
in the triage_sub_agent module. Following SSOT principles, this re-exports functionality
from the consolidated UnifiedTriageAgent instead of duplicating implementation.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for existing test imports
- Re-exports from SSOT UnifiedTriageAgent tool recommendation functionality
- DO NOT add new functionality here - extend UnifiedTriageAgent instead

Business Value:
- Maintains test stability during SSOT consolidation
- Enables continuous integration testing without breaking changes
- Supports gradual migration to SSOT patterns
"""

from typing import Any, Dict, List, Optional

# Import from SSOT location
from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent,
    ExtractedEntities,
    ToolRecommendation
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ToolRecommender:
    """
    Backward compatibility wrapper for tool recommendation functionality.

    DEPRECATED: This class is maintained for backward compatibility only.
    New code should use UnifiedTriageAgent._recommend_tools() directly.

    This wrapper delegates to UnifiedTriageAgent to maintain SSOT compliance
    while preserving existing test interfaces.
    """

    def __init__(self):
        """Initialize ToolRecommender with SSOT delegation."""
        logger.info("ToolRecommender compatibility layer initialized - delegating to UnifiedTriageAgent")
        self._unified_triage_agent = None

    def _get_unified_agent(self) -> UnifiedTriageAgent:
        """Get or create UnifiedTriageAgent instance."""
        if self._unified_triage_agent is None:
            self._unified_triage_agent = UnifiedTriageAgent(
                llm_manager=None,  # Not needed for tool recommendation
                tool_dispatcher=None,  # Not needed for tool recommendation
                context=None
            )
        return self._unified_triage_agent

    def recommend_tools(self, category: str, entities: Optional[ExtractedEntities] = None) -> ToolRecommendation:
        """
        Recommend tools for a given category and entities.

        DEPRECATED: Use UnifiedTriageAgent._recommend_tools() directly.

        Args:
            category: Tool category to find tools for
            entities: Optional extracted entities for context

        Returns:
            ToolRecommendation with tools and scores
        """
        logger.warning(
            "ToolRecommender.recommend_tools is deprecated. "
            "Use UnifiedTriageAgent._recommend_tools() directly for new code."
        )

        if entities is None:
            entities = ExtractedEntities(models_mentioned=[], metrics_mentioned=[])

        unified_agent = self._get_unified_agent()
        return unified_agent._recommend_tools(category, entities)

    def get_tool_categories(self) -> List[str]:
        """
        Get available tool categories.

        DEPRECATED: Use UnifiedTriageAgent category constants directly.

        Returns:
            List of available tool categories
        """
        logger.warning(
            "ToolRecommender.get_tool_categories is deprecated. "
            "Use UnifiedTriageAgent category constants directly."
        )

        return [
            "Workload Analysis",
            "Cost Optimization",
            "Performance Optimization",
            "Model Selection",
            "Supply Catalog Management",
            "Monitoring & Reporting",
            "Quality Optimization"
        ]

    def validate_tools(self, tools: List[str]) -> Dict[str, bool]:
        """
        Validate that tools exist and are available.

        DEPRECATED: Tool validation should be handled by UnifiedToolDispatcher.

        Args:
            tools: List of tool names to validate

        Returns:
            Dict mapping tool names to validation status
        """
        logger.warning(
            "ToolRecommender.validate_tools is deprecated. "
            "Use UnifiedToolDispatcher for tool validation."
        )

        # Stub implementation for backward compatibility
        # In a real system, this would delegate to UnifiedToolDispatcher
        return {tool: True for tool in tools}


# Export for backward compatibility
__all__ = ["ToolRecommender"]