"""Modular execution engine for DataSubAgent with component-based architecture."""

from typing import Any, Callable
from app.llm.llm_manager import LLMManager
from app.logging_config import central_logger as logger

# Import modular components
from .execution_core import ExecutionCore
from .execution_parameters import ParameterProcessor
from .execution_analysis import AnalysisRouter
from .execution_fallbacks import ExecutionFallbackHandler


class ExecutionEngine:
    """Modular execution engine with component-based architecture."""
    
    def __init__(self, clickhouse_ops: Any, query_builder: Any, analysis_engine: Any, redis_manager: Any, llm_manager: LLMManager) -> None:
        """Initialize execution engine with dependencies."""
        self._setup_engine(clickhouse_ops, query_builder, analysis_engine, redis_manager, llm_manager)
        
    def _setup_engine(self, clickhouse_ops: Any, query_builder: Any, analysis_engine: Any, redis_manager: Any, llm_manager: LLMManager) -> None:
        """Setup execution engine with dependencies and components."""
        self._assign_core_dependencies(clickhouse_ops, query_builder, analysis_engine, redis_manager, llm_manager)
        self._init_modular_components()
    
    def _assign_core_dependencies(
        self, clickhouse_ops: Any, query_builder: Any, analysis_engine: Any, 
        redis_manager: Any, llm_manager: LLMManager
    ) -> None:
        """Assign core dependencies to instance variables."""
        self._assign_data_components(clickhouse_ops, query_builder, analysis_engine)
        self._assign_manager_components(redis_manager, llm_manager)
        
    def _assign_data_components(self, clickhouse_ops: Any, query_builder: Any, analysis_engine: Any) -> None:
        """Assign data-related components."""
        self.clickhouse_ops = clickhouse_ops
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        
    def _assign_manager_components(self, redis_manager: Any, llm_manager: LLMManager) -> None:
        """Assign manager components."""
        self.redis_manager = redis_manager
        self.llm_manager = llm_manager
        
    def _init_modular_components(self) -> None:
        """Initialize modular execution components."""
        self.core = ExecutionCore(self)
        self.parameter_processor = ParameterProcessor(self)
        self.analysis_router = AnalysisRouter(self)
        self.fallback_handler = ExecutionFallbackHandler(self)
    
    async def execute_analysis(self, state: "DeepAgentState", run_id: str, stream_updates: bool, send_update_fn: Callable, data_ops: Any, metrics_analyzer: Any) -> None:
        """Main execution method coordinating analysis workflow."""
        await self._delegate_core_execution(state, run_id, stream_updates, send_update_fn, data_ops, metrics_analyzer)
        
    async def _delegate_core_execution(self, state, run_id, stream_updates, send_update_fn, data_ops, metrics_analyzer) -> None:
        """Delegate execution to core component."""
        await self.core.execute_analysis(state, run_id, stream_updates, send_update_fn, data_ops, metrics_analyzer)
    
    def get_fallback_health_status(self):
        """Get health status of fallback mechanisms."""
        return self.fallback_handler.get_fallback_health_status()