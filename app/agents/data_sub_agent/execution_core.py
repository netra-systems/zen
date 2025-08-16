"""Core execution workflow coordination for DataSubAgent."""

from typing import Dict, Any, Callable
from app.logging_config import central_logger as logger


class ExecutionCore:
    """Core execution workflow coordinator."""
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
    
    async def execute_analysis(
        self,
        state: "DeepAgentState",
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any,
        metrics_analyzer: Any
    ) -> None:
        """Main execution method coordinating analysis workflow."""
        try:
            await self._execute_analysis_workflow(state, run_id, stream_updates, send_update_fn, data_ops)
        except Exception as e:
            logger.error(f"DataSubAgent execution failed: {e}")
            await self._handle_execution_error(state, run_id, stream_updates, send_update_fn, e)
    
    async def _execute_analysis_workflow(
        self, state: "DeepAgentState", run_id: str, stream_updates: bool, send_update_fn: Callable, data_ops: Any
    ) -> None:
        """Execute the complete analysis workflow."""
        await self._send_initial_update(run_id, stream_updates, send_update_fn)
        params = self.engine.parameter_processor.extract_analysis_params(state)
        result = await self.engine.analysis_router.perform_complete_analysis(params, run_id, stream_updates, send_update_fn, data_ops)
        self._store_result_in_state(state, result)
        await self._send_completion_update(run_id, stream_updates, send_update_fn, result)
        logger.info(f"DataSubAgent completed analysis for run_id: {run_id}")
    
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
    
    async def _handle_execution_error(
        self, state: 'DeepAgentState', run_id: str, stream_updates: bool, send_update_fn: Callable, error: Exception
    ) -> None:
        """Handle execution errors using fallback mechanisms."""
        await self.engine.fallback_handler.handle_execution_error(state, run_id, stream_updates, send_update_fn, error)
    
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