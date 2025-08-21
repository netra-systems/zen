"""
Agent recovery registry and coordination.
Manages registration and execution of agent recovery strategies.
"""

from typing import Dict, Optional, Any

from app.core.error_recovery import RecoveryContext
from app.logging_config import central_logger
from netra_backend.app.agent_recovery_types import AgentType, AgentRecoveryConfig, create_all_default_configs
from netra_backend.app.agent_recovery_base import BaseAgentRecoveryStrategy
from netra_backend.app.agent_recovery_strategies import (
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
        triage_strategies = self._create_triage_strategies()
        data_strategies = self._create_data_analysis_strategies()
        self.strategies = {**triage_strategies, **data_strategies}

    def _create_triage_strategies(self) -> Dict[AgentType, BaseAgentRecoveryStrategy]:
        """Create triage and corpus admin strategies."""
        return {
            AgentType.TRIAGE: TriageAgentRecoveryStrategy(self.configs[AgentType.TRIAGE]),
            AgentType.CORPUS_ADMIN: CorpusAdminRecoveryStrategy(self.configs[AgentType.CORPUS_ADMIN])
        }

    def _create_data_analysis_strategies(self) -> Dict[AgentType, BaseAgentRecoveryStrategy]:
        """Create data analysis and supervisor strategies."""
        return {
            AgentType.DATA_ANALYSIS: DataAnalysisRecoveryStrategy(self.configs[AgentType.DATA_ANALYSIS]),
            AgentType.SUPERVISOR: SupervisorRecoveryStrategy(self.configs[AgentType.SUPERVISOR])
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
        basic_stats = self._get_basic_registry_stats()
        agent_info = self._get_agent_priority_info()
        return {**basic_stats, **agent_info}

    def _get_basic_registry_stats(self) -> Dict[str, Any]:
        """Get basic registry statistics."""
        return {
            'total_strategies': len(self.strategies),
            'total_configs': len(self.configs),
            'registered_agents': [agent.value for agent in self.strategies.keys()]
        }

    def _get_agent_priority_info(self) -> Dict[str, Any]:
        """Get agent priority information."""
        return {
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
        results, failed_recoveries = await self._process_recovery_requests(recovery_requests)
        return self._build_batch_recovery_summary(results, failed_recoveries, recovery_requests)

    async def _process_recovery_requests(
        self, recovery_requests: list[tuple[AgentType, RecoveryContext]]
    ) -> tuple[Dict[str, Any], list[Dict[str, Any]]]:
        """Process all recovery requests and collect results."""
        results = {}
        failed_recoveries = []
        for agent_type, context in recovery_requests:
            await self._process_single_recovery_request(agent_type, context, results, failed_recoveries)
        return results, failed_recoveries

    async def _process_single_recovery_request(
        self, agent_type: AgentType, context: RecoveryContext, 
        results: Dict[str, Any], failed_recoveries: list[Dict[str, Any]]
    ) -> None:
        """Process a single recovery request."""
        try:
            result = await self.recover_agent_operation(agent_type, context)
            self._record_successful_recovery(results, context, agent_type, result)
        except Exception as e:
            self._record_failed_recovery(failed_recoveries, agent_type, context, e)

    def _record_successful_recovery(
        self, results: Dict[str, Any], context: RecoveryContext, 
        agent_type: AgentType, result: Any
    ) -> None:
        """Record a successful recovery operation."""
        results[context.operation_id] = {
            'agent_type': agent_type.value,
            'status': 'recovered',
            'result': result
        }

    def _record_failed_recovery(
        self, failed_recoveries: list[Dict[str, Any]], agent_type: AgentType,
        context: RecoveryContext, error: Exception
    ) -> None:
        """Record a failed recovery operation."""
        failed_recoveries.append({
            'agent_type': agent_type.value,
            'operation_id': context.operation_id,
            'error': str(error)
        })

    def _build_batch_recovery_summary(
        self, results: Dict[str, Any], failed_recoveries: list[Dict[str, Any]],
        recovery_requests: list[tuple[AgentType, RecoveryContext]]
    ) -> Dict[str, Any]:
        """Build summary of batch recovery operation."""
        return {
            'successful_recoveries': results,
            'failed_recoveries': failed_recoveries,
            'total_attempts': len(recovery_requests),
            'success_rate': len(results) / len(recovery_requests) if recovery_requests else 0
        }
    
    def validate_registry(self) -> Dict[str, Any]:
        """Validate registry configuration and completeness."""
        validation_results = self._init_validation_results()
        self._check_missing_strategies(validation_results)
        self._check_missing_configs(validation_results)
        self._check_config_consistency(validation_results)
        return validation_results
    
    def _init_validation_results(self) -> Dict[str, Any]:
        """Initialize validation results structure."""
        return {
            'is_valid': True,
            'issues': [],
            'recommendations': []
        }
    
    def _check_missing_strategies(self, validation_results: Dict[str, Any]) -> None:
        """Check for missing recovery strategies."""
        missing_strategies = set(AgentType) - set(self.strategies.keys())
        if missing_strategies:
            self._add_missing_strategies_issue(validation_results, missing_strategies)
    
    def _add_missing_strategies_issue(self, validation_results: Dict[str, Any], missing_strategies: set) -> None:
        """Add missing strategies issue to validation results."""
        validation_results['issues'].append({
            'type': 'missing_strategies',
            'agents': [agent.value for agent in missing_strategies]
        })
        validation_results['is_valid'] = False
    
    def _check_missing_configs(self, validation_results: Dict[str, Any]) -> None:
        """Check for missing recovery configurations."""
        missing_configs = set(AgentType) - set(self.configs.keys())
        if missing_configs:
            self._add_missing_configs_issue(validation_results, missing_configs)
    
    def _add_missing_configs_issue(self, validation_results: Dict[str, Any], missing_configs: set) -> None:
        """Add missing configs issue to validation results."""
        validation_results['issues'].append({
            'type': 'missing_configs',
            'agents': [agent.value for agent in missing_configs]
        })
        validation_results['is_valid'] = False
    
    def _check_config_consistency(self, validation_results: Dict[str, Any]) -> None:
        """Check for strategies without corresponding configs."""
        for agent_type in self.strategies.keys():
            if agent_type not in self.configs:
                self._add_config_consistency_issue(validation_results, agent_type)
    
    def _add_config_consistency_issue(self, validation_results: Dict[str, Any], agent_type: AgentType) -> None:
        """Add config consistency issue to validation results."""
        validation_results['issues'].append({
            'type': 'strategy_without_config',
            'agent': agent_type.value
        })
        validation_results['is_valid'] = False


# Global recovery registry instance
agent_recovery_registry = AgentRecoveryRegistry()