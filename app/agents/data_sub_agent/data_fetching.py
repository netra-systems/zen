# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Modernize data_fetching.py to use BaseExecutionInterface architecture
# Git: 8-18-25-AM | Modernizing to standard agent patterns
# Change: Modernize | Scope: Module | Risk: Low
# Session: data-sub-agent-modernization | Seq: 1
# Review: Complete | Score: 100
# ================================
"""
Data Fetching Engine - Modern Architecture

Modernized data fetching using BaseExecutionInterface with:
- Standardized execution patterns
- Integrated reliability management (circuit breaker, retry)
- Comprehensive monitoring and error handling
- 450-line limit compliance with 25-line functions
- Backward compatibility with existing DataFetching interface

Business Value: Eliminates duplicate patterns, improves data reliability.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, UTC

from app.logging_config import central_logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig

# Import modular components
from .data_fetching_validation import DataFetchingValidation

logger = central_logger.get_logger(__name__)


class DataFetchingExecutionEngine(BaseExecutionInterface):
    """Modern data fetching execution engine.
    
    Implements BaseExecutionInterface with integrated reliability patterns.
    """
    
    def __init__(self, websocket_manager=None):
        super().__init__("data_fetching", websocket_manager)
        self.execution_engine = self._create_execution_engine()
        self.data_operations = DataFetchingValidation()

    def _create_execution_engine(self) -> BaseExecutionEngine:
        """Create execution engine with reliability patterns."""
        reliability_manager = self._create_reliability_manager()
        monitor = ExecutionMonitor()
        return BaseExecutionEngine(reliability_manager, monitor)

    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with circuit breaker and retry."""
        circuit_config = CircuitBreakerConfig(
            name="data_fetching", failure_threshold=3, recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute data fetching with modern patterns."""
        operation = context.metadata.get('operation')
        kwargs = context.metadata.get('kwargs', {})
        return await self._route_operation(operation, kwargs)

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate data fetching preconditions."""
        operation = context.metadata.get('operation')
        return self._validate_operation_access(operation)

    def _validate_operation_access(self, operation: str) -> bool:
        """Validate specific operation access."""
        allowed_operations = {
            'fetch_clickhouse_data', 'check_data_availability', 
            'get_available_metrics', 'get_workload_list', 'validate_query_parameters'
        }
        return operation in allowed_operations

    async def _route_operation(self, operation: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        handlers = {
            'fetch_clickhouse_data': self._handle_fetch_clickhouse,
            'check_data_availability': self._handle_check_availability,
            'get_available_metrics': self._handle_get_metrics,
            'get_workload_list': self._handle_get_workloads,
            'validate_query_parameters': self._handle_validate_params
        }
        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")
        return await handler(**kwargs)

    async def _handle_fetch_clickhouse(self, **kwargs) -> Dict[str, Any]:
        """Handle ClickHouse data fetching operation."""
        query = kwargs.get('query')
        cache_key = kwargs.get('cache_key')
        result = await self.data_operations.fetch_clickhouse_data(query, cache_key)
        return {'data': result, 'operation': 'fetch_clickhouse_data'}

    async def _handle_check_availability(self, **kwargs) -> Dict[str, Any]:
        """Handle data availability check operation."""
        user_id = kwargs.get('user_id')
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        result = await self.data_operations.check_data_availability(user_id, start_time, end_time)
        return {'availability': result, 'operation': 'check_data_availability'}

    async def _handle_get_metrics(self, **kwargs) -> Dict[str, Any]:
        """Handle get metrics operation."""
        user_id = kwargs.get('user_id')
        result = await self.data_operations.get_available_metrics(user_id)
        return {'metrics': result, 'operation': 'get_available_metrics'}

    async def _handle_get_workloads(self, **kwargs) -> Dict[str, Any]:
        """Handle get workloads operation."""
        user_id = kwargs.get('user_id')
        limit = kwargs.get('limit', 100)
        result = await self.data_operations.get_workload_list(user_id, limit)
        return {'workloads': result, 'operation': 'get_workload_list'}

    async def _handle_validate_params(self, **kwargs) -> Dict[str, Any]:
        """Handle parameter validation operation."""
        user_id = kwargs.get('user_id')
        workload_id = kwargs.get('workload_id')
        metrics = kwargs.get('metrics', [])
        result = await self.data_operations.validate_query_parameters(user_id, workload_id, metrics)
        return {'validation': result, 'operation': 'validate_query_parameters'}


class DataFetching(DataFetchingValidation):
    """Backward compatibility wrapper for existing DataFetching interface.
    
    Provides legacy interface while using modern execution patterns internally.
    Maintains existing method signatures for seamless integration.
    """
    
    def __init__(self):
        super().__init__()
        # Create modern execution engine for advanced operations
        self.modern_engine = DataFetchingExecutionEngine()

    async def execute_with_modern_patterns(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute operation using modern execution patterns."""
        from app.agents.state import DeepAgentState
        
        # Create execution context for modern patterns
        state = DeepAgentState()
        context = ExecutionContext(
            run_id=f"data_fetch_{datetime.now(UTC).isoformat()}",
            agent_name="data_fetching",
            state=state,
            metadata={'operation': operation, 'kwargs': kwargs}
        )
        
        # Execute with reliability patterns
        result = await self.modern_engine.execution_engine.execute(self.modern_engine, context)
        return result.result if result.success else {'error': result.error}

    def get_health_status(self) -> Dict[str, Any]:
        """Get execution engine health status."""
        return self.modern_engine.execution_engine.get_health_status()