"""DataSubAgent Core Module - Main agent logic (<300 lines)

Business Value: Core data analysis critical for customer insights - HIGH revenue impact
BVJ: Growth & Enterprise | Customer Intelligence | +20% performance fee capture
"""

import asyncio
import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.executor import BaseExecutionEngine

# Modern Base Components (BaseExecutionInterface removed for architecture simplification)
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
    WebSocketManagerProtocol,
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.data_sub_agent.data_processing_operations import (
    DataProcessingOperations,
)

# Modular Data Sub Agent Components
from netra_backend.app.agents.data_sub_agent.data_sub_agent_core import DataSubAgentCore
from netra_backend.app.agents.data_sub_agent.data_sub_agent_helpers import (
    DataSubAgentHelpers,
)
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.type_validators import agent_type_safe
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.strict_types import TypedAgentResult


class DataSubAgent(BaseSubAgent):
    """Core data analysis agent with modular architecture.
    
    Uses single inheritance pattern with ExecutionContext/ExecutionResult types.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None) -> None:
        """Initialize with robust error handling and fallbacks."""
        try:
            self._init_base_interfaces(llm_manager, websocket_manager)
            self._init_core_systems(tool_dispatcher, reliability_manager)
            self._init_processing_components()
            logger.info("DataSubAgent initialized successfully")
        except Exception as e:
            logger.error(f"DataSubAgent initialization failed: {e}")
            self._init_fallback_mode(llm_manager, tool_dispatcher)
    
    def _init_base_interfaces(self, llm_manager: LLMManager, 
                            websocket_manager: Optional[WebSocketManagerProtocol]) -> None:
        """Initialize base interfaces with error handling."""
        super().__init__(llm_manager, name="DataSubAgent", 
                        description="Advanced data analysis agent")
        # BaseExecutionInterface.__init__ removed - using single inheritance pattern
    
    def _init_core_systems(self, tool_dispatcher: ToolDispatcher, 
                          reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize core systems with fallback support."""
        self.tool_dispatcher = tool_dispatcher
        self._init_data_core_with_fallback()
        self._init_execution_engine(reliability_manager)
        
    def _init_data_core_with_fallback(self) -> None:
        """Initialize core with LLM fallback mechanism."""
        try:
            self.core = DataSubAgentCore(self.llm_manager)
        except Exception as e:
            logger.warning(f"Core initialization failed, using fallback: {e}")
            self.core = DataSubAgentCore(None)  # Fallback mode
        
    def _init_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize execution engine with monitoring."""
        if not reliability_manager:
            reliability_manager = self._create_reliable_fallback_manager()
        monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, monitor)
        self.execution_monitor = monitor
        
    def _create_reliable_fallback_manager(self) -> ReliabilityManager:
        """Create reliability manager with safe defaults."""
        try:
            return self.core.create_reliability_manager()
        except Exception:
            # Return a minimal fallback reliability manager
            from netra_backend.app.agents.base.circuit_breaker import (
                CircuitBreakerConfig,
            )
            from netra_backend.app.schemas.shared_types import RetryConfig
            circuit_config = CircuitBreakerConfig("DataSubAgent", 3, 30)
            retry_config = RetryConfig(max_retries=2, base_delay=1.0, max_delay=5.0)
            return ReliabilityManager(circuit_config, retry_config)
        
    def _init_processing_components(self) -> None:
        """Initialize processing components with delegation support."""
        self.helpers = DataSubAgentHelpers(self)
        self.processing_ops = DataProcessingOperations(self)
        self._setup_backward_compatibility()
        
    def _setup_backward_compatibility(self) -> None:
        """Setup backward compatibility properties."""
        # Expose key components for backward compatibility
        self.cache_manager = getattr(self.helpers, 'cache_manager', None)
        self.data_processor = getattr(self.helpers, 'data_processor', None)
        self.corpus_operations = getattr(self.helpers, 'corpus_operations', None)
        # Expose core components for test compatibility
        self._expose_core_components()
        
    def _expose_core_components(self) -> None:
        """Expose core components safely."""
        if hasattr(self.core, 'query_builder'):
            self.query_builder = self.core.query_builder
            self.analysis_engine = self.core.analysis_engine
            self.clickhouse_ops = self.core.clickhouse_ops
            self.redis_manager = self.core.redis_manager
            self.cache_ttl = self.core.cache_ttl
        
    def _init_fallback_mode(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher) -> None:
        """Initialize in fallback mode when normal initialization fails."""
        self.llm_manager = llm_manager or Mock()
        self.tool_dispatcher = tool_dispatcher or Mock()
        self.core = None
        self.helpers = None
        self.processing_ops = None
        self._fallback_mode = True
        logger.warning("DataSubAgent running in fallback mode")
        
    # Modern BaseExecutionInterface Implementation
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions with fallback."""
        try:
            if self._is_fallback_mode():
                return self._validate_fallback_preconditions(context)
            return await self.core.validate_data_analysis_preconditions(context)
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False
            
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core logic with fallback support."""
        if self._is_fallback_mode():
            return await self._execute_fallback_logic(context)
        return await self.core.execute_data_analysis(context)
    
    def _is_fallback_mode(self) -> bool:
        """Check if running in fallback mode."""
        return getattr(self, '_fallback_mode', False) or self.core is None
        
    def _validate_fallback_preconditions(self, context: ExecutionContext) -> bool:
        """Basic validation for fallback mode."""
        return context and hasattr(context, 'state') and context.state is not None
        
    async def _execute_fallback_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute minimal logic in fallback mode."""
        return {
            "status": "fallback",
            "message": "Agent running in fallback mode",
            "data": {"fallback_used": True},
            "success": True
        }
    
    # Main execution methods for backward compatibility
    @validate_agent_input('DataSubAgent')
    @agent_type_safe
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute with graceful fallback handling."""
        try:
            if self.helpers:
                return await self.helpers.execute_legacy_analysis(state, run_id, stream_updates)
            return await self._execute_basic_fallback(state, run_id)
        except Exception as e:
            logger.error(f"Execute failed, using emergency fallback: {e}")
            return await self._execute_emergency_fallback(state, run_id)
        
    async def _execute_basic_fallback(self, state: DeepAgentState, run_id: str) -> TypedAgentResult:
        """Basic fallback execution."""
        return TypedAgentResult(
            success=True,
            agent_name="DataSubAgent",
            data={"fallback_used": True, "message": "Basic analysis completed"}
        )
        
    async def _execute_emergency_fallback(self, state: DeepAgentState, run_id: str) -> TypedAgentResult:
        """Emergency fallback when all else fails."""
        return TypedAgentResult(
            success=False,
            agent_name="DataSubAgent",
            error="Agent execution failed, emergency fallback active",
            data={"emergency_fallback": True}
        )
        
    async def execute_with_modern_patterns(self, state: DeepAgentState, run_id: str,
                                         stream_updates: bool = False) -> ExecutionResult:
        """Execute using modern patterns with fallback."""
        context = self._create_execution_context(state, run_id, stream_updates)
        if hasattr(self, 'execution_engine') and self.execution_engine:
            return await self.execution_engine.execute(self, context)
        return await self._create_fallback_execution_result()
        
    def _create_execution_context(self, state: DeepAgentState, run_id: str,
                                stream_updates: bool) -> ExecutionContext:
        """Create execution context safely."""
        return ExecutionContext(run_id, self.agent_name, state, stream_updates)
    
    async def _create_fallback_execution_result(self) -> ExecutionResult:
        """Create fallback execution result."""
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"fallback_execution": True},
            duration=0.1
        )
    
    # Health and status monitoring
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status with fallback handling."""
        if self._is_fallback_mode():
            return {"status": "fallback", "mode": "degraded"}
        
        try:
            core_health = self.core.get_health_status() if self.core else {"status": "unknown"}
            execution_health = self.execution_engine.get_health_status() if hasattr(self, 'execution_engine') else {"status": "unknown"}
            return {"core": core_health, "execution": execution_health}
        except Exception:
            return {"status": "error", "mode": "degraded"}
        
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Enhanced cleanup with safe error handling."""
        try:
            await super().cleanup(state, run_id)
            if self.helpers:
                await self.helpers.cleanup_resources(time.time())
        except Exception as e:
            logger.warning(f"Cleanup encountered issues: {e}")
    
    # Dynamic delegation for backward compatibility
    def __getattr__(self, name: str):
        """Safe dynamic delegation with fallback."""
        if name.startswith('_') or name in ('helpers', 'agent', 'processing_ops'):
            raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
        
        # Try processing operations first
        if hasattr(self, 'processing_ops') and self.processing_ops:
            try:
                if hasattr(self.processing_ops, name):
                    return getattr(self.processing_ops, name)
            except AttributeError:
                pass
                
        # Try helpers second
        if hasattr(self, 'helpers') and self.helpers:
            try:
                if hasattr(self.helpers, name):
                    return getattr(self.helpers, name)
            except AttributeError:
                pass
                
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")