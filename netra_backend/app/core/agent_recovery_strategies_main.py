"""
Agent recovery strategies main module.
Re-exports from modular agent recovery system components.
"""

# Import types for backward compatibility
# Import base strategy
from netra_backend.app.core.agent_recovery_base import BaseAgentRecoveryStrategy
from netra_backend.app.core.agent_recovery_corpus import CorpusAdminRecoveryStrategy
from netra_backend.app.core.agent_recovery_data import DataAnalysisRecoveryStrategy

# Import registry
from netra_backend.app.core.agent_recovery_registry import (
    AgentRecoveryRegistry,
    agent_recovery_registry,
)
from netra_backend.app.core.agent_recovery_supervisor import SupervisorRecoveryStrategy

# Import specific strategies from focused modules
from netra_backend.app.core.agent_recovery_triage import TriageAgentRecoveryStrategy
from netra_backend.app.core.agent_recovery_types import (
    AgentRecoveryConfig,
    AgentType,
    RecoveryPriority,
)

# Re-export for backward compatibility
__all__ = [
    "AgentType",
    "RecoveryPriority", 
    "AgentRecoveryConfig",
    "BaseAgentRecoveryStrategy",
    "TriageAgentRecoveryStrategy",
    "DataAnalysisRecoveryStrategy",
    "CorpusAdminRecoveryStrategy",
    "SupervisorRecoveryStrategy",
    "AgentRecoveryRegistry",
    "agent_recovery_registry"
]