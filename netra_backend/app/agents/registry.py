"""
Agent Registry Module - SSOT Compatibility Wrapper

DEPRECATED: This module provides compatibility for legacy AgentRegistry imports.

🚨 SSOT CONSOLIDATION: All new code should use:
- netra_backend.app.agents.supervisor.agent_registry.AgentRegistry

This file provides backward compatibility only and will be removed in a future version.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Maintain Golden Path stability during SSOT consolidation
- Value Impact: Protects $500K+ ARR during AgentRegistry migration
- Strategic Impact: Enables safe SSOT consolidation without breaking existing imports

CRITICAL: This registry supports the Golden Path user flow:
Users login → AI agents process requests → Users receive AI responses
"""

import warnings
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.llm_manager import LLMManager

# Import the canonical SSOT AgentRegistry
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry as CanonicalAgentRegistry,
    BaseAgentRegistry
)

# Import enums from the canonical implementation
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentStatus, AgentType
except ImportError:
    # Fallback enums if not available in canonical implementation
    from enum import Enum

    class AgentStatus(Enum):
        """Agent status enumeration."""
        IDLE = "idle"
        BUSY = "busy"
        INITIALIZING = "initializing"
        ERROR = "error"
        OFFLINE = "offline"

    class AgentType(Enum):
        """Agent type enumeration."""
        SUPERVISOR = "supervisor"
        TRIAGE = "triage"
        DATA_HELPER = "data_helper"
        OPTIMIZER = "optimizer"
        RESEARCHER = "researcher"
        ANALYST = "analyst"
        SYNTHETIC_DATA = "synthetic_data"
        CORPUS_ADMIN = "corpus_admin"

# Re-export for backward compatibility
__all__ = ['AgentRegistry', 'AgentStatus', 'AgentType']

from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)


class AgentRegistry(CanonicalAgentRegistry):
    """COMPATIBILITY WRAPPER: Legacy AgentRegistry interface.

    DEPRECATED: This class is a compatibility shim only.

    All new code should use:
    - netra_backend.app.agents.supervisor.agent_registry.AgentRegistry

    This wrapper delegates all operations to the canonical AgentRegistry
    while providing the expected interface for legacy code.
    """

    def __init__(self,
                 llm_manager: Optional['LLMManager'] = None,
                 tool_dispatcher_factory: Optional[callable] = None,
                 websocket_manager=None):
        """Initialize compatibility wrapper by delegating to canonical AgentRegistry.

        Args:
            llm_manager: LLM manager for agent creation
            tool_dispatcher_factory: Factory for creating tool dispatchers
            websocket_manager: WebSocket manager for real-time updates
        """
        # Issue deprecation warning
        warnings.warn(
            "AgentRegistry from netra_backend.app.agents.registry is deprecated. "
            "Use AgentRegistry from netra_backend.app.agents.supervisor.agent_registry instead. "
            "This compatibility wrapper will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )

        logger.warning(
            "🚨 COMPATIBILITY MODE: Using legacy AgentRegistry import path. "
            "Please update imports to use netra_backend.app.agents.supervisor.agent_registry.AgentRegistry. "
            "This compatibility wrapper will be removed in a future version."
        )

        # Delegate to canonical implementation (canonical doesn't accept websocket_manager in constructor)
        super().__init__(
            llm_manager=llm_manager,
            tool_dispatcher_factory=tool_dispatcher_factory
        )

        # Set websocket manager separately if provided
        # NOTE: The canonical implementation handles websocket managers per user session
        if websocket_manager is not None:
            # Store for backward compatibility, but actual websocket handling is per-user in canonical impl
            logger.info("WebSocket manager provided to compatibility wrapper - will be handled per user session")

        logger.info("✅ AgentRegistry compatibility wrapper initialized")


# Legacy AgentInfo is not needed as canonical implementation uses different patterns
AgentInfo = None