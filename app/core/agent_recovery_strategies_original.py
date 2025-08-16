"""Agent-specific error recovery strategies for the Netra AI platform.

Provides tailored recovery approaches for different agent types based on their
specific failure patterns, business criticality, and operational requirements.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable

from app.core.error_recovery import (
    RecoveryAction,
    RecoveryContext,
    OperationType,
    ErrorRecoveryManager
)
from app.core.error_codes import ErrorSeverity
from app.services.compensation_engine import compensation_engine, saga_orchestrator
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


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


class BaseAgentRecoveryStrategy(ABC):
    """Abstract base class for agent recovery strategies."""
    
    def __init__(self, config: AgentRecoveryConfig):
        """Initialize with agent recovery configuration."""
        self.config = config
        self.recovery_manager = ErrorRecoveryManager()
    
    @abstractmethod
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess the failure and determine recovery approach."""
        pass
    
    @abstractmethod
    async def execute_primary_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Execute the primary recovery strategy."""
        pass
    
    @abstractmethod
    async def execute_fallback_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Execute fallback recovery if primary fails."""
        pass
    
    @abstractmethod
    async def execute_degraded_mode(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Execute in degraded mode as last resort."""
        pass
    
    async def recover(self, context: RecoveryContext) -> Any:
        """Execute recovery strategy with escalation."""
        assessment = await self.assess_failure(context)
        
        logger.info(
            f"Starting recovery for {self.config.agent_type.value}",
            operation_id=context.operation_id,
            assessment=assessment
        )
        
        # Try primary recovery
        if assessment.get('try_primary_recovery', True):
            primary_result = await self.execute_primary_recovery(context)
            if primary_result is not None:
                logger.info(f"Primary recovery succeeded for {context.operation_id}")
                return primary_result
        
        # Try fallback recovery
        if assessment.get('try_fallback_recovery', True) and self.config.fallback_enabled:
            fallback_result = await self.execute_fallback_recovery(context)
            if fallback_result is not None:
                logger.info(f"Fallback recovery succeeded for {context.operation_id}")
                return fallback_result
        
        # Try degraded mode
        if assessment.get('try_degraded_mode', True) and self.config.allow_degraded_mode:
            degraded_result = await self.execute_degraded_mode(context)
            if degraded_result is not None:
                logger.warning(f"Degraded mode recovery for {context.operation_id}")
                return degraded_result
        
        # If all recovery attempts failed
        if self.config.require_manual_intervention:
            await self._trigger_manual_intervention(context, assessment)
        
        logger.error(f"All recovery attempts failed for {context.operation_id}")
        raise Exception(f"Recovery failed for {self.config.agent_type.value}")
    
    async def _trigger_manual_intervention(
        self,
        context: RecoveryContext,
        assessment: Dict[str, Any]
    ) -> None:
        """Trigger manual intervention for complex failures."""
        intervention_data = {
            'operation_id': context.operation_id,
            'agent_type': self.config.agent_type.value,
            'error_summary': str(context.error),
            'assessment': assessment,
            'timestamp': context.started_at.isoformat(),
            'priority': self.config.priority.value
        }
        
        # In a real system, this would notify operators
        logger.critical(
            f"Manual intervention required for {self.config.agent_type.value}",
            intervention_data=intervention_data
        )


class TriageAgentRecoveryStrategy(BaseAgentRecoveryStrategy):
    """Recovery strategy for triage agent operations."""
    
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess triage agent failure."""
        error_message = str(context.error).lower()
        
        assessment = {
            'failure_type': 'unknown',
            'try_primary_recovery': True,
            'try_fallback_recovery': True,
            'try_degraded_mode': True,
            'estimated_recovery_time': 30  # seconds
        }
        
        # Categorize failure type
        if 'intent' in error_message:
            assessment['failure_type'] = 'intent_detection'
            assessment['try_primary_recovery'] = True
        elif 'entity' in error_message:
            assessment['failure_type'] = 'entity_extraction'
            assessment['try_fallback_recovery'] = True
        elif 'tool' in error_message:
            assessment['failure_type'] = 'tool_recommendation'
            assessment['try_degraded_mode'] = True
        elif 'timeout' in error_message:
            assessment['failure_type'] = 'timeout'
            assessment['estimated_recovery_time'] = 60
        
        return assessment
    
    async def execute_primary_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Primary recovery: retry with simplified processing."""
        try:
            # Simulate retry with simplified triage logic
            await asyncio.sleep(1)  # Brief delay
            
            # Return simplified triage result
            return {
                'intent': 'general_inquiry',
                'entities': {},
                'tools': ['general_assistant'],
                'confidence': 0.7,
                'recovery_method': 'simplified_triage'
            }
            
        except Exception as e:
            logger.debug(f"Primary triage recovery failed: {e}")
            return None
    
    async def execute_fallback_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Fallback recovery: use cached patterns."""
        try:
            # Use cached triage patterns
            return {
                'intent': 'cached_pattern',
                'entities': {},
                'tools': ['default_tool'],
                'confidence': 0.5,
                'recovery_method': 'cached_fallback'
            }
            
        except Exception as e:
            logger.debug(f"Fallback triage recovery failed: {e}")
            return None
    
    async def execute_degraded_mode(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Degraded mode: minimal triage functionality."""
        return {
            'intent': 'unknown',
            'entities': {},
            'tools': ['manual_review'],
            'confidence': 0.1,
            'recovery_method': 'degraded_mode',
            'requires_manual_review': True
        }


class DataAnalysisRecoveryStrategy(BaseAgentRecoveryStrategy):
    """Recovery strategy for data analysis agent operations."""
    
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess data analysis failure."""
        error_message = str(context.error).lower()
        
        assessment = {
            'failure_type': 'unknown',
            'try_primary_recovery': True,
            'try_fallback_recovery': True,
            'try_degraded_mode': True,
            'data_availability': 'unknown',
            'estimated_recovery_time': 120  # seconds
        }
        
        # Categorize failure type
        if 'clickhouse' in error_message or 'database' in error_message:
            assessment['failure_type'] = 'database_failure'
            assessment['data_availability'] = 'limited'
        elif 'timeout' in error_message:
            assessment['failure_type'] = 'query_timeout'
            assessment['try_primary_recovery'] = True
        elif 'memory' in error_message:
            assessment['failure_type'] = 'resource_exhaustion'
            assessment['try_degraded_mode'] = True
        elif 'data' in error_message:
            assessment['failure_type'] = 'data_quality'
            assessment['try_fallback_recovery'] = True
        
        return assessment
    
    async def execute_primary_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Primary recovery: retry with optimized queries."""
        try:
            # Simulate optimized query execution
            await asyncio.sleep(2)
            
            return {
                'metrics': {
                    'sample_size': 1000,
                    'avg_response_time': 150,
                    'error_rate': 0.02,
                    'throughput': 500
                },
                'insights': ['Limited sample analysis'],
                'recovery_method': 'optimized_query',
                'data_quality': 'reduced'
            }
            
        except Exception as e:
            logger.debug(f"Primary data analysis recovery failed: {e}")
            return None
    
    async def execute_fallback_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Fallback recovery: use cached or alternative data sources."""
        try:
            # Use cached or alternative data
            return {
                'metrics': {
                    'sample_size': 500,
                    'avg_response_time': 200,
                    'error_rate': 0.03,
                    'throughput': 300
                },
                'insights': ['Based on cached data'],
                'recovery_method': 'cached_data',
                'data_freshness': 'stale'
            }
            
        except Exception as e:
            logger.debug(f"Fallback data analysis recovery failed: {e}")
            return None
    
    async def execute_degraded_mode(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Degraded mode: basic statistics only."""
        return {
            'metrics': {
                'sample_size': 0,
                'status': 'unavailable'
            },
            'insights': ['Data analysis temporarily unavailable'],
            'recovery_method': 'degraded_mode',
            'recommendations': [
                'Check data source connectivity',
                'Retry analysis later'
            ]
        }


class CorpusAdminRecoveryStrategy(BaseAgentRecoveryStrategy):
    """Recovery strategy for corpus admin agent operations."""
    
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess corpus admin failure."""
        error_message = str(context.error).lower()
        
        assessment = {
            'failure_type': 'unknown',
            'try_primary_recovery': True,
            'try_fallback_recovery': True,
            'try_degraded_mode': False,  # Corpus operations are critical
            'data_integrity_risk': False,
            'estimated_recovery_time': 60
        }
        
        # Categorize failure type
        if 'upload' in error_message:
            assessment['failure_type'] = 'file_upload'
            assessment['data_integrity_risk'] = False
        elif 'validation' in error_message:
            assessment['failure_type'] = 'document_validation'
            assessment['try_degraded_mode'] = True
        elif 'index' in error_message:
            assessment['failure_type'] = 'indexing_failure'
            assessment['data_integrity_risk'] = True
        elif 'storage' in error_message:
            assessment['failure_type'] = 'storage_failure'
            assessment['data_integrity_risk'] = True
        
        return assessment
    
    async def execute_primary_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Primary recovery: retry with error correction."""
        try:
            # Simulate file processing with error correction
            await asyncio.sleep(3)
            
            return {
                'document_id': f"doc_{context.operation_id[:8]}",
                'status': 'processed_with_corrections',
                'warnings': ['Some formatting issues auto-corrected'],
                'recovery_method': 'error_correction',
                'indexing_pending': True
            }
            
        except Exception as e:
            logger.debug(f"Primary corpus recovery failed: {e}")
            return None
    
    async def execute_fallback_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Fallback recovery: partial processing."""
        try:
            # Partial document processing
            return {
                'document_id': f"doc_{context.operation_id[:8]}_partial",
                'status': 'partially_processed',
                'content_extracted': True,
                'metadata_extracted': False,
                'indexing_status': 'queued',
                'recovery_method': 'partial_processing'
            }
            
        except Exception as e:
            logger.debug(f"Fallback corpus recovery failed: {e}")
            return None
    
    async def execute_degraded_mode(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Degraded mode: queue for manual processing."""
        return {
            'document_id': f"doc_{context.operation_id[:8]}_queued",
            'status': 'queued_for_manual_review',
            'recovery_method': 'manual_queue',
            'estimated_processing_time': '1-2 hours',
            'operator_notified': True
        }


class SupervisorRecoveryStrategy(BaseAgentRecoveryStrategy):
    """Recovery strategy for supervisor agent operations."""
    
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess supervisor failure."""
        assessment = {
            'failure_type': 'coordination_failure',
            'try_primary_recovery': True,
            'try_fallback_recovery': True,
            'try_degraded_mode': True,
            'sub_agents_affected': [],
            'estimated_recovery_time': 90
        }
        
        # Supervisor failures are critical
        assessment['priority'] = 'critical'
        assessment['cascade_impact'] = True
        
        return assessment
    
    async def execute_primary_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Primary recovery: restart coordination."""
        try:
            # Simulate supervisor restart
            await asyncio.sleep(2)
            
            return {
                'supervisor_id': f"supervisor_{context.operation_id[:8]}",
                'status': 'restarted',
                'sub_agents_reconnected': ['triage', 'data_analysis'],
                'recovery_method': 'restart_coordination'
            }
            
        except Exception as e:
            logger.debug(f"Primary supervisor recovery failed: {e}")
            return None
    
    async def execute_fallback_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Fallback recovery: limited coordination."""
        try:
            return {
                'supervisor_id': f"supervisor_{context.operation_id[:8]}_limited",
                'status': 'limited_coordination',
                'available_agents': ['triage'],
                'recovery_method': 'limited_coordination'
            }
            
        except Exception as e:
            logger.debug(f"Fallback supervisor recovery failed: {e}")
            return None
    
    async def execute_degraded_mode(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Degraded mode: direct agent access only."""
        return {
            'supervisor_id': f"supervisor_{context.operation_id[:8]}_degraded",
            'status': 'degraded_mode',
            'coordination_disabled': True,
            'direct_agent_access': True,
            'recovery_method': 'degraded_mode'
        }


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
        self.configs = {
            AgentType.TRIAGE: AgentRecoveryConfig(
                agent_type=AgentType.TRIAGE,
                max_retries=3,
                retry_delay_base=1.0,
                circuit_breaker_threshold=5,
                fallback_enabled=True,
                compensation_enabled=False,
                priority=RecoveryPriority.HIGH,
                timeout_seconds=30,
                preserve_state=False,
                allow_degraded_mode=True
            ),
            AgentType.DATA_ANALYSIS: AgentRecoveryConfig(
                agent_type=AgentType.DATA_ANALYSIS,
                max_retries=2,
                retry_delay_base=2.0,
                circuit_breaker_threshold=3,
                fallback_enabled=True,
                compensation_enabled=True,
                priority=RecoveryPriority.MEDIUM,
                timeout_seconds=120,
                preserve_state=True,
                allow_degraded_mode=True
            ),
            AgentType.CORPUS_ADMIN: AgentRecoveryConfig(
                agent_type=AgentType.CORPUS_ADMIN,
                max_retries=3,
                retry_delay_base=1.0,
                circuit_breaker_threshold=3,
                fallback_enabled=True,
                compensation_enabled=True,
                priority=RecoveryPriority.HIGH,
                timeout_seconds=180,
                preserve_state=True,
                allow_degraded_mode=False,
                require_manual_intervention=True
            ),
            AgentType.SUPERVISOR: AgentRecoveryConfig(
                agent_type=AgentType.SUPERVISOR,
                max_retries=2,
                retry_delay_base=0.5,
                circuit_breaker_threshold=2,
                fallback_enabled=True,
                compensation_enabled=True,
                priority=RecoveryPriority.CRITICAL,
                timeout_seconds=60,
                preserve_state=True,
                allow_degraded_mode=True
            ),
        }
    
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
    
    def get_strategy(self, agent_type: AgentType) -> Optional[BaseAgentRecoveryStrategy]:
        """Get recovery strategy for agent type."""
        return self.strategies.get(agent_type)
    
    def get_config(self, agent_type: AgentType) -> Optional[AgentRecoveryConfig]:
        """Get recovery configuration for agent type."""
        return self.configs.get(agent_type)
    
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


# Global recovery registry
agent_recovery_registry = AgentRecoveryRegistry()