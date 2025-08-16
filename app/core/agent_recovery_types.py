"""
Agent recovery types and configuration classes.
Defines core types and configuration for agent recovery strategies.
"""

from dataclasses import dataclass
from enum import Enum


class AgentType(Enum):
    """Types of agents in the system."""
    TRIAGE = "triage"
    DATA_ANALYSIS = "data_analysis"
    CORPUS_ADMIN = "corpus_admin"
    SUPPLY_RESEARCHER = "supply_researcher"
    OPTIMIZATION = "optimization"
    REPORTING = "reporting"
    SUPERVISOR = "supervisor"
    SYNTHETIC_DATA = "synthetic_data"


class RecoveryPriority(Enum):
    """Priority levels for recovery operations."""
    CRITICAL = "critical"    # Must recover immediately
    HIGH = "high"           # Recover quickly
    MEDIUM = "medium"       # Recover when resources available
    LOW = "low"            # Best effort recovery


@dataclass
class AgentRecoveryConfig:
    """Configuration for agent-specific recovery strategies."""
    agent_type: AgentType
    max_retries: int
    retry_delay_base: float
    circuit_breaker_threshold: int
    fallback_enabled: bool
    compensation_enabled: bool
    priority: RecoveryPriority
    timeout_seconds: int
    
    # Specific configurations
    preserve_state: bool = True
    allow_degraded_mode: bool = True
    require_manual_intervention: bool = False


def create_default_config(agent_type: AgentType) -> AgentRecoveryConfig:
    """Create default configuration for agent type."""
    base_configs = {
        AgentType.TRIAGE: AgentRecoveryConfig(
            agent_type=agent_type,
            max_retries=3,
            retry_delay_base=1.0,
            circuit_breaker_threshold=5,
            fallback_enabled=True,
            compensation_enabled=False,
            priority=RecoveryPriority.HIGH,
            timeout_seconds=30,
            preserve_state=True,
            allow_degraded_mode=True,
            require_manual_intervention=False
        ),
        AgentType.DATA_ANALYSIS: AgentRecoveryConfig(
            agent_type=agent_type,
            max_retries=5,
            retry_delay_base=2.0,
            circuit_breaker_threshold=10,
            fallback_enabled=True,
            compensation_enabled=True,
            priority=RecoveryPriority.MEDIUM,
            timeout_seconds=120,
            preserve_state=True,
            allow_degraded_mode=True,
            require_manual_intervention=False
        ),
        AgentType.CORPUS_ADMIN: AgentRecoveryConfig(
            agent_type=agent_type,
            max_retries=3,
            retry_delay_base=1.5,
            circuit_breaker_threshold=7,
            fallback_enabled=True,
            compensation_enabled=True,
            priority=RecoveryPriority.HIGH,
            timeout_seconds=60,
            preserve_state=True,
            allow_degraded_mode=False,
            require_manual_intervention=True
        ),
        AgentType.SUPERVISOR: AgentRecoveryConfig(
            agent_type=agent_type,
            max_retries=2,
            retry_delay_base=0.5,
            circuit_breaker_threshold=3,
            fallback_enabled=True,
            compensation_enabled=False,
            priority=RecoveryPriority.CRITICAL,
            timeout_seconds=15,
            preserve_state=True,
            allow_degraded_mode=True,
            require_manual_intervention=False
        )
    }
    
    return base_configs.get(agent_type, base_configs[AgentType.TRIAGE])


def create_all_default_configs() -> dict[AgentType, AgentRecoveryConfig]:
    """Create default configurations for all agent types."""
    return {
        agent_type: create_default_config(agent_type)
        for agent_type in AgentType
    }