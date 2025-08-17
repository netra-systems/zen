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


def _create_triage_config(agent_type: AgentType) -> AgentRecoveryConfig:
    """Create triage agent recovery configuration."""
    return AgentRecoveryConfig(
        agent_type=agent_type, max_retries=3, retry_delay_base=1.0,
        circuit_breaker_threshold=5, fallback_enabled=True, compensation_enabled=False,
        priority=RecoveryPriority.HIGH, timeout_seconds=30, preserve_state=True,
        allow_degraded_mode=True, require_manual_intervention=False
    )

def _create_data_analysis_config(agent_type: AgentType) -> AgentRecoveryConfig:
    """Create data analysis agent recovery configuration."""
    return AgentRecoveryConfig(
        agent_type=agent_type, max_retries=5, retry_delay_base=2.0,
        circuit_breaker_threshold=10, fallback_enabled=True, compensation_enabled=True,
        priority=RecoveryPriority.MEDIUM, timeout_seconds=120, preserve_state=True,
        allow_degraded_mode=True, require_manual_intervention=False
    )

def _create_corpus_admin_config(agent_type: AgentType) -> AgentRecoveryConfig:
    """Create corpus admin agent recovery configuration."""
    return AgentRecoveryConfig(
        agent_type=agent_type, max_retries=3, retry_delay_base=1.5,
        circuit_breaker_threshold=7, fallback_enabled=True, compensation_enabled=True,
        priority=RecoveryPriority.HIGH, timeout_seconds=60, preserve_state=True,
        allow_degraded_mode=False, require_manual_intervention=True
    )

def _create_supervisor_config(agent_type: AgentType) -> AgentRecoveryConfig:
    """Create supervisor agent recovery configuration."""
    return AgentRecoveryConfig(
        agent_type=agent_type, max_retries=2, retry_delay_base=0.5,
        circuit_breaker_threshold=3, fallback_enabled=True, compensation_enabled=False,
        priority=RecoveryPriority.CRITICAL, timeout_seconds=15, preserve_state=True,
        allow_degraded_mode=True, require_manual_intervention=False
    )

def _get_config_factory_map() -> dict:
    """Get mapping of agent types to their config factory functions."""
    return {
        AgentType.TRIAGE: _create_triage_config,
        AgentType.DATA_ANALYSIS: _create_data_analysis_config,
        AgentType.CORPUS_ADMIN: _create_corpus_admin_config,
        AgentType.SUPERVISOR: _create_supervisor_config
    }

def create_default_config(agent_type: AgentType) -> AgentRecoveryConfig:
    """Create default configuration for agent type."""
    config_factories = _get_config_factory_map()
    factory = config_factories.get(agent_type, _create_triage_config)
    return factory(agent_type)


def create_all_default_configs() -> dict[AgentType, AgentRecoveryConfig]:
    """Create default configurations for all agent types."""
    return {
        agent_type: create_default_config(agent_type)
        for agent_type in AgentType
    }