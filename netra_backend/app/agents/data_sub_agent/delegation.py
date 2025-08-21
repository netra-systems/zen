"""Modern Delegation Interface for DataSubAgent

Modernized with BaseExecutionInterface patterns:
- Standardized execution context handling
- ReliabilityManager integration
- ExecutionMonitor support
- Structured error handling
- Zero breaking changes

Business Value: Enhanced reliability and monitoring for delegation patterns.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.logging_config import central_logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus
)
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class ModernAgentDelegation(BaseExecutionInterface):
    """Modern delegation interface with BaseExecutionInterface patterns.
    
    Enhanced delegation with:
    - Standardized execution patterns
    - Reliability management
    - Performance monitoring
    - Structured error handling
    """
    
    def __init__(self, agent_instance, extended_ops) -> None:
        """Initialize with modern execution capabilities."""
        super().__init__(f"{agent_instance.__class__.__name__}Delegation")
        self.agent = agent_instance
        self.extended_ops = extended_ops
        self._initialize_modern_components()
    
    def _initialize_modern_components(self) -> None:
        """Initialize reliability and monitoring components."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.execution_monitor = ExecutionMonitor()
    
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="delegation_circuit", failure_threshold=5, recovery_timeout=30
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute delegation core logic with modern patterns."""
        operation = context.metadata.get("operation")
        data = context.metadata.get("data", {})
        
        if operation == "process_internal":
            return await self._process_internal(data)
        elif operation == "process_with_retry":
            return await self.process_with_retry(data)
        else:
            return await self._execute_default_delegation(context)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate delegation execution preconditions."""
        if not context.metadata.get("operation"):
            return False
        return self.extended_ops is not None
    
    async def _execute_default_delegation(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute default delegation workflow."""
        return {"success": True, "message": "Default delegation executed"}
    
    async def _process_internal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process internal data with modern reliability patterns."""
        context = self._create_delegation_context("process_internal", data)
        return await self._execute_with_reliability(context, 
            lambda: self.extended_ops._process_internal(data))
    
    async def process_with_retry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with retry using modern reliability patterns."""
        context = self._create_delegation_context("process_with_retry", data)
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops.process_with_retry(data))
    
    async def process_with_cache(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with cache using modern reliability patterns."""
        context = self._create_delegation_context("process_with_cache", data)
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops.process_with_cache(data))
    
    async def process_batch_safe(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch safely with modern reliability patterns."""
        context = self._create_delegation_context("process_batch_safe", {"batch": batch})
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops.process_batch_safe(batch))
    
    async def process_concurrent(self, items: List[Dict[str, Any]], max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Process concurrent items with modern reliability patterns."""
        context = self._create_delegation_context("process_concurrent", 
            {"items": items, "max_concurrent": max_concurrent})
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops.process_concurrent(items, max_concurrent))
    
    async def process_stream(self, dataset, chunk_size: int = 100):
        """Process stream with modern monitoring."""
        start_time = time.time()
        try:
            result = self.extended_ops.process_stream(dataset, chunk_size)
            self._track_stream_success(start_time)
            return result
        except Exception as e:
            self._track_stream_error(start_time, e)
            raise
    
    async def process_and_persist(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and persist with modern reliability patterns."""
        context = self._create_delegation_context("process_and_persist", data)
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops.process_and_persist(data))
    
    async def handle_supervisor_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle supervisor request with modern reliability patterns."""
        context = self._create_delegation_context("handle_supervisor_request", request)
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops.handle_supervisor_request(request))
    
    async def enrich_data_external(self, data: Dict[str, Any], external: bool = False) -> Dict[str, Any]:
        """Enhanced data enrichment with modern reliability patterns."""
        if external:
            context = self._create_delegation_context("enrich_data_extended", 
                {"data": data, "external": external})
            return await self._execute_with_reliability(context,
                lambda: self.extended_ops.enrich_data_extended(data, external))
        return self._enrich_data_locally(data)
    
    def _enrich_data_locally(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich data locally without external dependencies."""
        enriched = data.copy()
        enriched["metadata"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": data.get("source", "unknown"),
            "enriched": True
        }
        return enriched
    
    async def _transform_with_pipeline(self, data: Dict[str, Any], pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform data with pipeline using modern reliability patterns."""
        context = self._create_delegation_context("transform_with_pipeline", 
            {"data": data, "pipeline": pipeline})
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops._transform_with_pipeline(data, pipeline))
    
    async def _apply_operation(self, data: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        """Apply operation with modern reliability patterns."""
        context = self._create_delegation_context("apply_operation", 
            {"data": data, "operation": operation})
        return await self._execute_with_reliability(context,
            lambda: self.extended_ops._apply_operation(data, operation))
    
    async def save_state(self) -> None:
        """Save state with modern error handling."""
        try:
            await self.extended_ops.save_state()
            logger.info("State saved successfully via delegation")
        except Exception as e:
            logger.error(f"State save failed via delegation: {e}")
            raise
    
    async def load_state(self) -> None:
        """Load state with modern error handling."""
        try:
            await self.extended_ops.load_state()
            logger.info("State loaded successfully via delegation")
        except Exception as e:
            logger.error(f"State load failed via delegation: {e}")
            raise
    
    async def recover(self) -> None:
        """Recover with modern error handling."""
        try:
            await self.extended_ops.recover()
            logger.info("Recovery completed successfully via delegation")
        except Exception as e:
            logger.error(f"Recovery failed via delegation: {e}")
            raise
    
    async def _analyze_performance_metrics(self, user_id: int, workload_id: str, time_range) -> Dict[str, Any]:
        """Analyze performance metrics with modern delegation patterns."""
        context = self._create_delegation_context("analyze_performance_metrics", 
            {"user_id": user_id, "workload_id": workload_id, "time_range": time_range})
        return await self._execute_analysis_operation(context, "analyze_performance_metrics",
            user_id, workload_id, time_range)
    
    async def _detect_anomalies(self, user_id: int, metric_name: str, time_range, threshold: float = 2.5) -> Dict[str, Any]:
        """Detect anomalies with modern delegation patterns."""
        context = self._create_delegation_context("detect_anomalies", 
            {"user_id": user_id, "metric_name": metric_name, "time_range": time_range, "threshold": threshold})
        return await self._execute_analysis_operation(context, "detect_anomalies",
            user_id, metric_name, time_range, threshold)
    
    async def _analyze_usage_patterns(self, user_id: int, days_back: int = 7) -> Dict[str, Any]:
        """Analyze usage patterns with modern delegation patterns."""
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        time_range = (start_time, end_time)
        
        context = self._create_delegation_context("analyze_usage_patterns", 
            {"user_id": user_id, "days_back": days_back})
        return await self._execute_analysis_operation(context, "analyze_usage_patterns",
            user_id, time_range)
    
    async def _analyze_correlations(self, user_id: int, metric1: str, metric2: str, time_range) -> Dict[str, Any]:
        """Analyze correlations with modern delegation patterns."""
        metrics = [metric1, metric2]
        context = self._create_delegation_context("analyze_correlations", 
            {"user_id": user_id, "metric1": metric1, "metric2": metric2, "time_range": time_range})
        return await self._execute_analysis_operation(context, "analyze_correlations",
            user_id, metrics, time_range)
    
    async def _execute_analysis_operation(self, context: ExecutionContext, 
                                        operation_name: str, *args) -> Dict[str, Any]:
        """Execute analysis operation with reliability patterns."""
        from .analysis_operations import AnalysisOperations
        return await self._execute_with_reliability(context, 
            lambda: self._create_and_execute_analysis_ops(operation_name, *args))
    
    async def _create_and_execute_analysis_ops(self, operation_name: str, *args) -> Dict[str, Any]:
        """Create analysis operations instance and execute method."""
        from .analysis_operations import AnalysisOperations
        ops = AnalysisOperations(
            self.agent.query_builder, self.agent.analysis_engine,
            self.agent.clickhouse_ops, self.agent.redis_manager
        )
        return await getattr(ops, operation_name)(*args)
    
    def _create_delegation_context(self, operation: str, data: Dict[str, Any]) -> ExecutionContext:
        """Create execution context for delegation operations."""
        from app.agents.state import DeepAgentState
        mock_state = DeepAgentState(user_request=f"delegation_{operation}")
        return ExecutionContext(
            run_id=f"delegation_{operation}_{int(time.time())}",
            agent_name=self.agent_name,
            state=mock_state,
            metadata={"operation": operation, "data": data}
        )
    
    async def _execute_with_reliability(self, context: ExecutionContext, 
                                       operation_func) -> Dict[str, Any]:
        """Execute operation with reliability patterns."""
        start_time = time.time()
        try:
            result = await self._execute_reliable_operation(context, operation_func, start_time)
            return result.result if hasattr(result, 'result') else result
        except Exception as e:
            self._handle_reliability_error(context, e, start_time)
            raise
    
    async def _execute_reliable_operation(self, context: ExecutionContext,
                                        operation_func, start_time: float):
        """Execute operation with reliability manager."""
        result = await self.reliability_manager.execute_with_reliability(
            context, operation_func
        )
        execution_time = (time.time() - start_time) * 1000
        self.execution_monitor.record_success(context, execution_time)
        return result
    
    def _handle_reliability_error(self, context: ExecutionContext, 
                                error: Exception, start_time: float) -> None:
        """Handle reliability execution errors."""
        execution_time = (time.time() - start_time) * 1000
        self.execution_monitor.record_error(context, error, execution_time)
    
    def _track_stream_success(self, start_time: float) -> None:
        """Track successful stream processing."""
        execution_time = (time.time() - start_time) * 1000
        logger.info(f"Stream processing completed in {execution_time:.2f}ms")
    
    def _track_stream_error(self, start_time: float, error: Exception) -> None:
        """Track stream processing error."""
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Stream processing failed after {execution_time:.2f}ms: {error}")


# Backward compatibility alias
AgentDelegation = ModernAgentDelegation