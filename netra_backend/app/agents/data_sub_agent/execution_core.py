"""Core execution workflow coordination for DataSubAgent.

Modernized with BaseExecutionInterface pattern:
- Standardized execution patterns
- Integrated reliability management
- Comprehensive error handling
- Performance monitoring
- Circuit breaker protection

Business Value: Data analysis critical for customer insights - HIGH revenue impact
BVJ: Growth & Enterprise | Customer Intelligence | +20% performance fee capture
"""

from typing import Dict, Any, Callable, Optional
from app.logging_config import central_logger as logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus,
    WebSocketManagerProtocol
)
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.error_handler import ExecutionErrorHandler
from app.schemas.shared_types import RetryConfig
from app.agents.base.circuit_breaker import CircuitBreakerConfig


class ExecutionCore(BaseExecutionInterface):
    """Core execution workflow coordinator with modern patterns."""
    
    def __init__(self, execution_engine, websocket_manager: Optional[WebSocketManagerProtocol] = None):
        super().__init__("DataSubAgent", websocket_manager)
        self.engine = execution_engine
        self._init_modern_components()
        
    def _init_modern_components(self) -> None:
        """Initialize modern execution components."""
        self._init_reliability_manager()
        self._init_monitoring()
        self._init_error_handler()
        
    def _init_reliability_manager(self) -> None:
        """Initialize reliability manager with optimized settings."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration for data operations."""
        return CircuitBreakerConfig(
            name="DataExecutionCore",
            failure_threshold=5,
            recovery_timeout=30
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration for data operations."""
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
        
    def _init_monitoring(self) -> None:
        """Initialize execution monitoring."""
        self.execution_monitor = ExecutionMonitor(max_history_size=1000)
        
    def _init_error_handler(self) -> None:
        """Initialize error handling."""
        self.error_handler = ExecutionErrorHandler()
    
    async def execute_analysis(
        self,
        state: "DeepAgentState",
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any,
        metrics_analyzer: Any = None
    ) -> ExecutionResult:
        """Main execution method coordinating analysis workflow."""
        context = self._create_execution_context(state, run_id, stream_updates)
        
        try:
            return await self._execute_with_modern_patterns(context, data_ops, send_update_fn)
        except Exception as e:
            return await self._handle_modern_execution_error(context, e, send_update_fn)
            
    def _create_execution_context(self, state, run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context from parameters."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.agent_name,
            state=state,
            stream_updates=stream_updates
        )
        
    async def _execute_with_modern_patterns(self, context: ExecutionContext, 
                                          data_ops: Any, send_update_fn: Callable) -> ExecutionResult:
        """Execute with modern reliability patterns."""
        return await self.reliability_manager.execute_with_reliability(
            context, lambda: self._execute_core_analysis(context, data_ops, send_update_fn)
        )
        
    async def _execute_core_analysis(self, context: ExecutionContext, 
                                   data_ops: Any, send_update_fn: Callable) -> ExecutionResult:
        """Execute core analysis logic."""
        self.execution_monitor.start_execution(context)
        
        try:
            result = await self._perform_data_analysis(context, data_ops, send_update_fn)
            execution_result = self._create_success_result(result)
            self.execution_monitor.complete_execution(context, execution_result)
            return execution_result
        except Exception as e:
            self.execution_monitor.record_error(context, e)
            raise
            
    async def _perform_data_analysis(self, context: ExecutionContext, 
                                   data_ops: Any, send_update_fn: Callable) -> Dict[str, Any]:
        """Perform the actual data analysis."""
        await self._send_initial_update(context.run_id, context.stream_updates, send_update_fn)
        params = self.engine.parameter_processor.extract_analysis_params(context.state)
        result = await self.engine.analysis_router.perform_complete_analysis(
            params, context.run_id, context.stream_updates, send_update_fn, data_ops
        )
        self._store_result_in_state(context.state, result)
        await self._send_completion_update(context.run_id, context.stream_updates, send_update_fn, result)
        return result
        
    def _create_success_result(self, result: Dict[str, Any]) -> ExecutionResult:
        """Create successful execution result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=result,
            execution_time_ms=0.0
        )
        
    async def _handle_modern_execution_error(self, context: ExecutionContext, 
                                           error: Exception, send_update_fn: Callable) -> ExecutionResult:
        """Handle execution error using modern error handler."""
        logger.error(f"DataSubAgent execution failed: {error}")
        await self._handle_legacy_execution_error(
            context.state, context.run_id, context.stream_updates, send_update_fn, error
        )
        return await self.error_handler.handle_execution_error(error, context)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute agent-specific core logic (BaseExecutionInterface implementation)."""
        params = self.engine.parameter_processor.extract_analysis_params(context.state)
        result = await self.engine.analysis_router.perform_complete_analysis(
            params, context.run_id, context.stream_updates, 
            lambda rid, update: self.send_status_update(context, update.get('status', 'processing'), 
                                                       update.get('message', 'Processing...')), 
            None  # data_ops will be provided by caller
        )
        self._store_result_in_state(context.state, result)
        logger.info(f"DataSubAgent completed analysis for run_id: {context.run_id}")
        return result
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions (BaseExecutionInterface implementation)."""
        try:
            return await self._validate_analysis_preconditions(context)
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False
            
    async def _validate_analysis_preconditions(self, context: ExecutionContext) -> bool:
        """Validate data analysis specific preconditions."""
        if not hasattr(self.engine, 'parameter_processor'):
            return False
        if not hasattr(self.engine, 'analysis_router'):
            return False
        if not context.state:
            return False
        return True
    
    async def _send_initial_update(
        self,
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable
    ) -> None:
        """Send initial status update."""
        if stream_updates:
            await send_update_fn(run_id, {
                "status": "started",
                "message": "Starting advanced data analysis..."
            })
    
    def _store_result_in_state(self, state: 'DeepAgentState', result: Dict[str, Any]) -> None:
        """Store analysis result in agent state."""
        state.data_result = result
    
    async def _send_completion_update(
        self,
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        result: Dict[str, Any]
    ) -> None:
        """Send completion update."""
        if stream_updates:
            await send_update_fn(run_id, {
                "status": "completed",
                "message": "Advanced data analysis completed successfully",
                "result": result
            })
    
    async def _handle_legacy_execution_error(
        self, state: 'DeepAgentState', run_id: str, stream_updates: bool, send_update_fn: Callable, error: Exception
    ) -> None:
        """Handle execution errors using legacy fallback mechanisms."""
        if hasattr(self.engine, 'fallback_handler'):
            await self.engine.fallback_handler.handle_execution_error(state, run_id, stream_updates, send_update_fn, error)
            
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including modern components."""
        return {
            "execution_core": "healthy",
            "reliability_manager": self.reliability_manager.get_health_status(),
            "execution_monitor": self.execution_monitor.get_health_status(),
            "components": self._get_component_status()
        }
        
    def _get_component_status(self) -> Dict[str, bool]:
        """Get component availability status."""
        return {
            "parameter_processor": hasattr(self.engine, 'parameter_processor'),
            "analysis_router": hasattr(self.engine, 'analysis_router'),
            "fallback_handler": hasattr(self.engine, 'fallback_handler')
        }
    
    async def send_progress_update(
        self,
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        message: str
    ) -> None:
        """Send progress update."""
        if stream_updates:
            await send_update_fn(run_id, {
                "status": "analyzing",
                "message": message
            })