"""Modern Execution Interface Implementation for DataSubAgent

Separates BaseExecutionInterface methods to maintain 450-line limit.
Provides standardized execution patterns with modern reliability.

Business Value: Modular modern execution patterns for data analysis.
"""

from typing import Dict, Any, Optional
from app.logging_config import central_logger
from app.agents.base.interface import ExecutionContext
from app.schemas.strict_types import TypedAgentResult

logger = central_logger.get_logger(__name__)


class DataSubAgentModernExecution:
    """Modern execution interface methods for DataSubAgent."""
    
    def __init__(self, agent):
        self.agent = agent
    
    async def cleanup_modern_components(self, state, run_id: str) -> None:
        """Cleanup modern execution components."""
        logger.debug(f"Modern component cleanup completed for run_id: {run_id}")
    
    async def validate_data_analysis_preconditions(self, context: ExecutionContext) -> bool:
        """Validate specific data analysis preconditions."""
        state = context.state
        if not state or not state.user_request:
            return False
        if not self._is_data_related_request(state.user_request):
            return False
        return True
    
    def _is_data_related_request(self, user_request: str) -> bool:
        """Check if request is data analysis related."""
        data_keywords = ["data", "analysis", "query", "database", "clickhouse", "metric"]
        request_lower = user_request.lower()
        return any(keyword in request_lower for keyword in data_keywords)
    
    async def log_precondition_validation(self, context: ExecutionContext, 
                                        is_valid: bool) -> None:
        """Log precondition validation results."""
        status_msg = "valid" if is_valid else "invalid"
        logger.info(f"DataSubAgent precondition validation: {status_msg} for run_id: {context.run_id}")
    
    async def track_modern_execution_start(self, context: ExecutionContext) -> None:
        """Track execution start with modern monitoring."""
        self.agent.execution_monitor.start_execution(context)
        await self.agent.send_status_update(context, "initializing", "Starting data analysis")
    
    async def execute_legacy_data_analysis(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute legacy data analysis workflow."""
        result = await self.agent.execution_manager.execute(
            context.state, context.run_id, context.stream_updates
        )
        return self._convert_legacy_result_to_dict(result)
    
    def _convert_legacy_result_to_dict(self, legacy_result: TypedAgentResult) -> Dict[str, Any]:
        """Convert legacy TypedAgentResult to modern dict format."""
        return {
            "success": legacy_result.success,
            "data": legacy_result.data if hasattr(legacy_result, 'data') else None,
            "metadata": legacy_result.metadata if hasattr(legacy_result, 'metadata') else {},
            "error": getattr(legacy_result, 'error', None)
        }
    
    async def finalize_modern_execution(self, context: ExecutionContext, 
                                      result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize successful execution with modern monitoring."""
        await self.agent.send_status_update(context, "completed", "Data analysis completed")
        return result
    
    async def handle_modern_execution_error(self, context: ExecutionContext, 
                                          error: Exception) -> Dict[str, Any]:
        """Handle execution errors with modern error handling."""
        self.agent.execution_monitor.record_error(context, error)
        await self.agent.send_status_update(context, "failed", f"Analysis failed: {str(error)}")
        return {"success": False, "error": str(error), "data": None}