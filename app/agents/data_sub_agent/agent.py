"""Modernized DataSubAgent with BaseExecutionInterface Integration

Clean modern implementation following BaseExecutionInterface pattern:
- Standardized execution workflow with reliability management
- Comprehensive monitoring and error handling
- Circuit breaker protection and retry logic
- Modular component architecture under 300 lines

Business Value: Data analysis critical for customer insights - HIGH revenue impact
BVJ: Growth & Enterprise | Customer Intelligence | +20% performance fee capture
"""

from typing import Dict, Optional, Any
import time

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.schemas.strict_types import TypedAgentResult
from app.core.type_validators import agent_type_safe
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.input_validation import validate_agent_input
from app.logging_config import central_logger as logger

# Modern Base Components
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus,
    WebSocketManagerProtocol
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor

# Modular Data Sub Agent Components
from .data_sub_agent_core import DataSubAgentCore
from .data_sub_agent_helpers import DataSubAgentHelpers


class DataSubAgent(BaseSubAgent, BaseExecutionInterface):
    """Advanced data gathering and analysis agent with ClickHouse integration."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None) -> None:
        self._init_base_interfaces(llm_manager, websocket_manager)
        self._init_core_systems(tool_dispatcher, reliability_manager)
        self._init_component_helpers()
    
    def _init_base_interfaces(self, llm_manager: LLMManager, 
                            websocket_manager: Optional[WebSocketManagerProtocol]) -> None:
        """Initialize base interfaces and agent identity."""
        BaseSubAgent.__init__(self, llm_manager, name="DataSubAgent", 
                            description="Advanced data gathering and analysis agent with ClickHouse integration.")
        BaseExecutionInterface.__init__(self, "DataSubAgent", websocket_manager)
    
    def _init_core_systems(self, tool_dispatcher: ToolDispatcher, 
                          reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize core systems and execution engine."""
        self.tool_dispatcher = tool_dispatcher
        self._init_data_sub_agent_core()
        self._init_modern_execution_engine(reliability_manager)
        
    def _init_data_sub_agent_core(self) -> None:
        """Initialize core data analysis components."""
        self.core = DataSubAgentCore(self.llm_manager)
        
    def _init_modern_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize modern execution engine with reliability patterns."""
        if not reliability_manager:
            reliability_manager = self.core.create_reliability_manager()
        self._setup_execution_components(reliability_manager)
        
    def _setup_execution_components(self, reliability_manager: ReliabilityManager) -> None:
        """Setup modern execution components."""
        monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, monitor)
        self.execution_monitor = monitor
        
    def _init_component_helpers(self) -> None:
        """Initialize component helpers for delegation and operations."""
        self.helpers = DataSubAgentHelpers(self)
        self._setup_delegation_support()
        
    def _setup_delegation_support(self) -> None:
        """Setup delegation support for backward compatibility."""
        # Expose key components for backward compatibility
        self.cache_manager = self.helpers.cache_manager
        self.data_processor = self.helpers.data_processor
        self.corpus_operations = self.helpers.corpus_operations
        
    # Modern BaseExecutionInterface Implementation
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for data analysis."""
        try:
            return await self.core.validate_data_analysis_preconditions(context)
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}", exc_info=True)
            return False
            
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute data analysis core logic with modern patterns."""
        return await self.core.execute_data_analysis(context)
    
    # Main execution methods for backward compatibility
    @validate_agent_input('DataSubAgent')
    @agent_type_safe
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute data analysis with backward compatibility."""
        return await self.helpers.execute_legacy_analysis(state, run_id, stream_updates)
        
    async def execute_with_modern_patterns(self, state: DeepAgentState, run_id: str,
                                         stream_updates: bool = False) -> ExecutionResult:
        """Execute using modern execution patterns."""
        context = self._create_execution_context(state, run_id, stream_updates)
        return await self.execution_engine.execute(self, context)
        
    def _create_execution_context(self, state: DeepAgentState, run_id: str,
                                stream_updates: bool) -> ExecutionContext:
        """Create execution context for modern patterns."""
        return ExecutionContext(run_id, self.agent_name, state, stream_updates)
    
    # Data operations delegation to helpers
    async def _fetch_clickhouse_data(self, query: str, cache_key: Optional[str] = None):
        """Execute ClickHouse query with caching support."""
        return await self.helpers.fetch_clickhouse_data(query, cache_key)
        
    def cache_clear(self) -> None:
        """Clear cache for test compatibility."""
        self.helpers.clear_cache()
        
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send real-time update via WebSocket."""
        await self.helpers.send_websocket_update(run_id, update)
    
    # Health and status monitoring
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive agent health status."""
        core_health = self.core.get_health_status()
        execution_health = self.execution_engine.get_health_status()
        return {"core": core_health, "execution": execution_health}
        
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Enhanced cleanup with cache management."""
        await super().cleanup(state, run_id)
        await self.helpers.cleanup_resources(time.time())
    
    # Dynamic delegation for backward compatibility
    def __getattr__(self, name: str):
        """Dynamic delegation to helpers for backward compatibility."""
        if hasattr(self.helpers, name):
            return getattr(self.helpers, name)
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

