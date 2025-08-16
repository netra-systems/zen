"""
Agent recovery registry and coordination.
Manages registration and execution of agent recovery strategies.
"""

from typing import Dict, Optional, Any

from app.core.error_recovery import RecoveryContext
from app.logging_config import central_logger
from .agent_recovery_types import AgentType, AgentRecoveryConfig, create_all_default_configs
from .agent_recovery_base import BaseAgentRecoveryStrategy
from .agent_recovery_strategies import (
    TriageAgentRecoveryStrategy,
    DataAnalysisRecoveryStrategy,
    CorpusAdminRecoveryStrategy,
    SupervisorRecoveryStrategy
)

logger = central_logger.get_logger(__name__)


class AgentRecoveryRegistry:
    """Registry for agent recovery strategies."""
    
    def __init__(self):
        """Initialize recovery registry."""
        self.strategies: Dict[AgentType, BaseAgentRecoveryStrategy] = {}
        self.configs: Dict[AgentType, AgentRecoveryConfig] = {}
        
        # Initialize default configurations
        self._setup_default_configs()
        self._register_default_strategies()
    
    def _setup_default_configs(self) -> None:
        """Set up default recovery configurations for each agent type."""
        self.configs = create_all_default_configs()
    
    def _register_default_strategies(self) -> None:
        """Register default recovery strategies."""
        self.strategies = {
            AgentType.TRIAGE: TriageAgentRecoveryStrategy(
                self.configs[AgentType.TRIAGE]
            ),
            AgentType.DATA_ANALYSIS: DataAnalysisRecoveryStrategy(
                self.configs[AgentType.DATA_ANALYSIS]
            ),
            AgentType.CORPUS_ADMIN: CorpusAdminRecoveryStrategy(
                self.configs[AgentType.CORPUS_ADMIN]
            ),
            AgentType.SUPERVISOR: SupervisorRecoveryStrategy(
                self.configs[AgentType.SUPERVISOR]
            ),
        }
    
    def register_strategy(
        self,
        agent_type: AgentType,
        strategy: BaseAgentRecoveryStrategy
    ) -> None:
        """Register custom recovery strategy."""
        self.strategies[agent_type] = strategy
        logger.info(f"Registered recovery strategy for {agent_type.value}")
    
    def register_config(
        self,
        agent_type: AgentType,
        config: AgentRecoveryConfig
    ) -> None:
        """Register custom recovery configuration."""
        self.configs[agent_type] = config
        logger.info(f"Registered recovery config for {agent_type.value}")
    
    def get_strategy(self, agent_type: AgentType) -> Optional[BaseAgentRecoveryStrategy]:
        """Get recovery strategy for agent type."""
        return self.strategies.get(agent_type)
    
    def get_config(self, agent_type: AgentType) -> Optional[AgentRecoveryConfig]:
        """Get recovery configuration for agent type."""
        return self.configs.get(agent_type)
    
    def list_registered_agents(self) -> list[AgentType]:
        """Get list of agent types with registered strategies."""
        return list(self.strategies.keys())
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get status of the recovery registry."""
        return {
            'total_strategies': len(self.strategies),
            'total_configs': len(self.configs),
            'registered_agents': [agent.value for agent in self.strategies.keys()],
            'agent_priorities': {
                agent.value: config.priority.value 
                for agent, config in self.configs.items()
            }
        }
    
    async def recover_agent_operation(
        self,
        agent_type: AgentType,
        context: RecoveryContext
    ) -> Any:
        """Execute recovery for specific agent type."""
        strategy = self.get_strategy(agent_type)
        if not strategy:
            logger.error(f"No recovery strategy found for {agent_type.value}")
            raise ValueError(f"No recovery strategy for {agent_type.value}")
        
        return await strategy.recover(context)
    
    async def batch_recover_operations(
        self,
        recovery_requests: list[tuple[AgentType, RecoveryContext]]
    ) -> Dict[str, Any]:
        """Execute recovery for multiple agent operations."""
        results = {}
        failed_recoveries = []
        
        for agent_type, context in recovery_requests:
            try:
                result = await self.recover_agent_operation(agent_type, context)
                results[context.operation_id] = {
                    'agent_type': agent_type.value,
                    'status': 'recovered',
                    'result': result
                }
            except Exception as e:
                failed_recoveries.append({
                    'agent_type': agent_type.value,
                    'operation_id': context.operation_id,
                    'error': str(e)
                })
        
        return {
            'successful_recoveries': results,
            'failed_recoveries': failed_recoveries,
            'total_attempts': len(recovery_requests),
            'success_rate': len(results) / len(recovery_requests) if recovery_requests else 0
        }
    
    def validate_registry(self) -> Dict[str, Any]:
        """Validate registry configuration and completeness."""
        validation_results = {
            'is_valid': True,
            'issues': [],
            'recommendations': []
        }
        
        # Check for missing strategies
        missing_strategies = set(AgentType) - set(self.strategies.keys())
        if missing_strategies:
            validation_results['issues'].append({
                'type': 'missing_strategies',
                'agents': [agent.value for agent in missing_strategies]
            })
            validation_results['is_valid'] = False
        
        # Check for missing configs
        missing_configs = set(AgentType) - set(self.configs.keys())
        if missing_configs:
            validation_results['issues'].append({
                'type': 'missing_configs',
                'agents': [agent.value for agent in missing_configs]
            })
            validation_results['is_valid'] = False
        
        # Check config consistency
        for agent_type in self.strategies.keys():
            if agent_type not in self.configs:
                validation_results['issues'].append({
                    'type': 'strategy_without_config',
                    'agent': agent_type.value
                })
                validation_results['is_valid'] = False
        
        return validation_results


# Global recovery registry instance
agent_recovery_registry = AgentRecoveryRegistry()