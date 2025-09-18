"""
ISSUE #863 PHASE 3: SSOT Registry Re-Export - COMPLETE CONSOLIDATION

✅ SSOT COMPLIANCE: This module now directly re-exports the supervisor AgentRegistry classes
   to ensure both import paths resolve to the EXACT SAME class objects.

⚠️  MIGRATION RECOMMENDED: While both paths work, prefer the canonical import:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

Business Value Justification (BVJ):
- Segment: Platform Infrastructure  
- Business Goal: Complete SSOT compliance while maintaining backward compatibility
- Value Impact: Supports $500K+ ARR chat functionality with zero breaking changes
- Strategic Impact: Foundation for all agent-based business value delivery

CRITICAL: This registry supports the Golden Path user flow:
Users login → AI agents process requests → Users receive AI responses

SSOT ACHIEVEMENT: Both import paths now resolve to identical class objects.
"""

from shared.logging.unified_logging_ssot import get_logger
import warnings
import threading
from typing import Dict, Optional

# Setup logging
logger = get_logger(__name__)

# ISSUE #863 PHASE 3: Direct re-export for SSOT compliance
# Import and re-export all classes from supervisor registry so both paths resolve to same objects
try:
    # Import ALL classes and functions from supervisor registry
    from netra_backend.app.agents.supervisor.agent_registry import (
        AgentRegistry,
        AgentType,
        AgentStatus,
        AgentInfo,
        get_agent_registry
    )
    
    # Re-export the exact same classes - no wrapper, no compatibility layer
    # This ensures both import paths resolve to identical class objects
    
    logger.info("Issue #863 Phase 3: SSOT re-export successful - classes directly imported from supervisor registry")
    SSOT_CONSOLIDATION_SUCCESS = True
    
except ImportError as e:
    logger.error(f"Issue #863 Phase 3: Failed to import supervisor AgentRegistry for SSOT re-export: {e}")
    SSOT_CONSOLIDATION_SUCCESS = False
    
    # Fallback definitions only if supervisor registry unavailable
    from enum import Enum
    from dataclasses import dataclass, field
    from datetime import datetime
    from typing import Dict, Any, Optional, List, Union
    
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

    @dataclass
    class AgentInfo:
        """Agent information structure."""
        agent_id: str
        agent_type: AgentType
        name: str
        description: str
        status: AgentStatus = AgentStatus.IDLE
        created_at: datetime = field(default_factory=datetime.now)
        last_active: datetime = field(default_factory=datetime.now)
        execution_count: int = 0
        error_count: int = 0
        metadata: Dict[str, Any] = field(default_factory=dict)
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary for serialization."""
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "name": self.name,
                "description": self.description,
                "status": self.status.value,
                "created_at": self.created_at.isoformat(),
                "last_active": self.last_active.isoformat(),
                "execution_count": self.execution_count,
                "error_count": self.error_count,
                "metadata": self.metadata
            }
    
    # Placeholder registry for fallback
    class AgentRegistry:
        """Placeholder registry - supervisor registry unavailable."""
        
        def __init__(self):
            self._agents = {}
            self._websocket_manager = None
            
        def register_agent(self, agent_type, name, description="", metadata=None, agent_instance=None):
            return f"{agent_type.value}_fallback"
            
        def get_agent_info(self, agent_id):
            return None
            
        def update_agent_status(self, agent_id, status):
            return False
            
        def get_available_agents(self, agent_type=None):
            return []
            
        def cleanup_inactive_agents(self):
            pass
    
    def get_agent_registry(llm_manager=None, tool_dispatcher=None):
        """Placeholder function - supervisor registry unavailable."""
        return AgentRegistry()

# Issue deprecation warning when this module is imported
warnings.warn(
    "MIGRATION RECOMMENDED: Use canonical import 'from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry' "
    "instead of 'from netra_backend.app.agents.registry import AgentRegistry'. "
    "Both paths work but canonical path is preferred for clarity.",
    DeprecationWarning,
    stacklevel=2
)

# ISSUE #1116 REMEDIATION: Phase 1 Singleton to User-Scoped Factory Migration
# Replace global singleton with user-scoped factory for multi-user safety

class AgentRegistryFactory:
    """User-scoped AgentRegistry factory for multi-user isolation.

    CRITICAL SECURITY: Prevents cross-user data contamination by ensuring
    each user gets their own isolated AgentRegistry instance.

    Business Value: Enables $500K+ ARR multi-user chat functionality
    with enterprise-grade user isolation.
    """

    def __init__(self):
        """Initialize factory with per-user registry storage."""
        self._user_registries: Dict[str, AgentRegistry] = {}
        self._lock = threading.Lock()

    def get_registry(self, user_context: Optional[str] = None) -> AgentRegistry:
        """Get user-scoped AgentRegistry instance.

        Args:
            user_context: User identifier for isolation (optional for backward compatibility)

        Returns:
            AgentRegistry: Isolated registry for the user
        """
        # Default context for backward compatibility
        if user_context is None:
            user_context = "default_global"

        with self._lock:
            if user_context not in self._user_registries:
                self._user_registries[user_context] = AgentRegistry()
            return self._user_registries[user_context]

    def clear_user_registry(self, user_context: str) -> None:
        """Clear registry for specific user (cleanup after session ends)."""
        with self._lock:
            self._user_registries.pop(user_context, None)

# Factory instance for creating user-scoped registries
_agent_registry_factory = AgentRegistryFactory()

def _get_global_agent_registry():
    """DEPRECATED: Get the global agent registry instance.

    MIGRATION PATH: This maintains backward compatibility.
    New code should use get_user_agent_registry(user_context) instead.
    """
    return _agent_registry_factory.get_registry(user_context=None)

def get_user_agent_registry(user_context: Optional[str] = None) -> AgentRegistry:
    """Get user-scoped agent registry for multi-user safety.

    Args:
        user_context: User identifier for isolation

    Returns:
        AgentRegistry: Isolated registry for the user
    """
    return _agent_registry_factory.get_registry(user_context)

# Module-level agent_registry for backward compatibility
agent_registry = _get_global_agent_registry()

# Convenience functions for common operations (maintained for backward compatibility)
def register_agent(agent_type, name: str, description: str = "", metadata=None, agent_instance=None) -> str:
    """Register an agent with the global registry."""
    return agent_registry.register_agent(agent_type, name, description, metadata, agent_instance)

def get_agent_info(agent_id: str):
    """Get agent info from the global registry."""
    return agent_registry.get_agent_info(agent_id)

def update_agent_status(agent_id: str, status) -> bool:
    """Update agent status in the global registry."""
    return agent_registry.update_agent_status(agent_id, status)

def get_available_agents(agent_type=None):
    """Get available agents from the global registry."""
    return agent_registry.get_available_agents(agent_type)

def cleanup_inactive_agents():
    """Clean up inactive agents in the global registry."""
    agent_registry.cleanup_inactive_agents()

async def list_available_agents(agent_type=None):
    """List available agents from the global registry - compatibility method."""
    return agent_registry.get_available_agents(agent_type)

# Export all public classes and functions for backward compatibility
__all__ = [
    'AgentRegistry',
    'AgentInfo',
    'AgentStatus',
    'AgentType',
    'agent_registry',
    'get_agent_registry',
    'register_agent',
    'get_agent_info',
    'update_agent_status',
    'get_available_agents',
    'cleanup_inactive_agents',
    'list_available_agents'
]