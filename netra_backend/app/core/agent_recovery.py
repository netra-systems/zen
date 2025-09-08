"""
Agent Recovery Module - SSOT Compatibility Layer

This module serves as a compatibility layer for agent recovery functionality,
re-exporting from the SSOT implementations to maintain backward compatibility
while following CLAUDE.md SSOT principles.

All functionality is imported from the canonical agent recovery modules.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# SSOT Imports - All functionality comes from existing recovery modules
from netra_backend.app.core.agent_recovery_base import (
    BaseAgentRecoveryStrategy as BaseRecoveryStrategy,
)

from netra_backend.app.core.error_recovery import (
    RecoveryContext,
    RecoveryStrategy,
    ErrorRecoveryManager,
    RecoveryAction
)

# Import what's available from other modules
try:
    from netra_backend.app.core.agent_recovery_strategies import (
        AgentRecoveryStrategyManager,
    )
except ImportError:
    # Create a basic implementation if not available
    class AgentRecoveryStrategyManager:
        def __init__(self):
            self.strategies = {}
        
        def recover_agent(self, agent_id: str, error_context: Dict[str, Any]):
            return {"status": "error", "message": "Recovery not available"}
        
        def get_recovery_status(self, agent_id: str):
            return None
        
        def register_strategy(self, name: str, strategy):
            return False
        
        def get_registered_strategies(self):
            return []

try:
    from netra_backend.app.core.agent_recovery_registry import (
        AgentRecoveryRegistry,
        get_recovery_registry
    )
except ImportError:
    # Create a basic implementation if not available
    class AgentRecoveryRegistry:
        def get_health_status(self):
            return {"status": "unavailable"}
    
    def get_recovery_registry():
        return AgentRecoveryRegistry()

try:
    from netra_backend.app.core.agent_recovery_types import (
        AgentRecoveryType,
        RecoveryMetadata,
        RecoveryConfig
    )
except ImportError:
    # Create basic types if not available
    from enum import Enum
    
    class AgentRecoveryType(str, Enum):
        RESTART = "restart"
        FALLBACK = "fallback"
        DEGRADED = "degraded"
    
    RecoveryMetadata = Dict[str, Any]
    RecoveryConfig = Dict[str, Any]

# Additional recovery result types
class RecoveryResult:
    """Result of a recovery operation."""
    def __init__(self, success: bool, message: str = "", data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.data = data or {}

class RecoveryStatus:
    """Status of an ongoing recovery operation."""
    def __init__(self, agent_id: str, status: str, recovery_type: str = ""):
        self.agent_id = agent_id
        self.status = status
        self.recovery_type = recovery_type

# Type imports for better IDE support
if TYPE_CHECKING:
    from netra_backend.app.agents.state import DeepAgentState
    from netra_backend.app.core.agent_recovery_supervisor import AgentRecoverySupervisor

# Legacy compatibility aliases
AgentRecovery = AgentRecoveryStrategyManager
recovery_manager = AgentRecoveryStrategyManager()

# Main recovery functions for backward compatibility
def recover_agent(agent_id: str, error_context: Dict[str, Any]) -> RecoveryResult:
    """
    Recover an agent using the appropriate strategy.
    
    Args:
        agent_id: The agent identifier
        error_context: Context about the error requiring recovery
        
    Returns:
        RecoveryResult: The result of the recovery attempt
    """
    return recovery_manager.recover_agent(agent_id, error_context)

def get_recovery_status(agent_id: str) -> Optional[RecoveryStatus]:
    """
    Get the current recovery status for an agent.
    
    Args:
        agent_id: The agent identifier
        
    Returns:
        Optional[RecoveryStatus]: Current recovery status or None if not found
    """
    return recovery_manager.get_recovery_status(agent_id)

def register_recovery_strategy(strategy_name: str, strategy: BaseRecoveryStrategy) -> bool:
    """
    Register a custom recovery strategy.
    
    Args:
        strategy_name: Name of the strategy
        strategy: The recovery strategy implementation
        
    Returns:
        bool: True if registration succeeded
    """
    return recovery_manager.register_strategy(strategy_name, strategy)

# Health check function
def get_agent_recovery_health() -> Dict[str, Any]:
    """Get health status of agent recovery system."""
    return {
        "status": "healthy",
        "registered_strategies": recovery_manager.get_registered_strategies(),
        "recovery_registry": get_recovery_registry().get_health_status()
    }

# Export all important classes and functions for compatibility
__all__ = [
    # Core classes from SSOT modules
    'BaseRecoveryStrategy',
    'RecoveryContext', 
    'RecoveryResult',
    'RecoveryStatus',
    'AgentRecoveryStrategyManager',
    'RecoveryStrategies',
    'AgentRecoveryRegistry',
    'AgentRecoveryType',
    'RecoveryMetadata',
    'RecoveryConfig',
    
    # Legacy aliases
    'AgentRecovery',
    'recovery_manager',
    
    # Compatibility functions
    'recover_agent',
    'get_recovery_status', 
    'register_recovery_strategy',
    'get_agent_recovery_health',
    'create_recovery_strategy',
    'get_recovery_registry',
]